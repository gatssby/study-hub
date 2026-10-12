"""FastAPI application: HTTP contract on top of the single-owner collection actor.

Every collection access goes through CollectionActor.submit(). Routes never touch
the Collection object directly, so there is exactly one thread that reads or writes
it. Media files are served from disk without going through the actor, because they
do not need the collection and must be immediate.
"""

from __future__ import annotations

import hmac
import logging
import mimetypes
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypeVar

from anki.collection import Collection
from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from anki_api_v2 import __version__
from anki_api_v2.actor import CollectionActor, CollectionBusy
from anki_api_v2.config import ConfigError, Settings
from anki_api_v2.errors import ApiError, error_body
from anki_api_v2.media import (
    InvalidMediaPath,
    MediaNotFound,
    media_dir_for,
    resolve_media_file,
    validate_media_filename,
)
from anki_api_v2.schemas import (
    CardOut,
    DeckPage,
    HealthOut,
    NoteOut,
    PatchNoteRequest,
    PatchNoteResult,
    SearchPage,
    SearchRequest,
    SyncRequest,
    SyncResult,
)
from anki_api_v2.service import MAX_DECK_LIMIT, CollectionService
from anki_api_v2.sync import AnkiSyncTransport, Clock, SyncManager, SyncTransport, SystemClock

log = logging.getLogger("anki_api_v2.http")
T = TypeVar("T")

MAX_OFFSET = 1_000_000


def open_collection(path: Path) -> Collection:
    # Collection(path) silently CREATES an empty collection when the file is missing.
    # That would mask a misconfigured path, so refuse instead.
    if not path.is_file():
        raise ConfigError(f"collection file not found at {path}; refusing to create a new one")
    return Collection(str(path))


def create_app(
    settings: Settings,
    *,
    transport: SyncTransport | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    clock = clock or SystemClock()
    if transport is None:
        transport = AnkiSyncTransport(
            endpoint=settings.sync_endpoint,
            username=settings.sync_username,
            password=settings.sync_password,
        )
    sync = SyncManager(transport, clock, settings.freshness_ttl_seconds)
    service = CollectionService(sync=sync, collection_path=settings.collection_path)
    actor = CollectionActor(
        open_fn=lambda: open_collection(settings.collection_path),
        lock_path=settings.lock_path,
        queue_timeout=settings.queue_timeout_seconds,
    )
    media_dir = media_dir_for(settings.collection_path)

    def read(fn: Callable[[Collection], T]) -> T:
        def job(col: Collection) -> T:
            sync.ensure_fresh(col)
            return fn(col)

        return actor.submit(job)

    def write(fn: Callable[[Collection], T]) -> T:
        return actor.submit(fn)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        actor.start()
        log.info("collection owner started api_version=%s", __version__)
        try:
            yield
        finally:
            actor.stop()
            log.info("collection owner stopped")

    def require_token(authorization: str | None = Header(default=None)) -> None:
        scheme, _, token = (authorization or "").partition(" ")
        ok = (
            scheme.lower() == "bearer"
            and bool(token)
            and hmac.compare_digest(token.encode("utf-8"), settings.token.encode("utf-8"))
        )
        if not ok:
            raise ApiError(
                401,
                "unauthorized",
                "missing or invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    app = FastAPI(
        title="Anki GPT API v2",
        version=__version__,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        # Path only: query strings can contain note text and are never logged.
        log.info(
            "%s %s %s %dms",
            request.method,
            request.url.path,
            response.status_code,
            int((time.monotonic() - started) * 1000),
        )
        return response

    router = APIRouter(prefix="/v2", dependencies=[Depends(require_token)])

    @router.get("/health", response_model=HealthOut)
    def health():
        return write(lambda col: service.health(col))

    @router.post("/sync", response_model=SyncResult)
    def sync_endpoint(body: SyncRequest | None = None):
        media = bool(body and body.media)
        result = write(lambda col: service.sync_now(col, media))
        return JSONResponse(result, status_code=202 if media else 200)

    @router.get("/decks", response_model=DeckPage)
    def list_decks(
        root: str | None = Query(default=None, min_length=1, max_length=200),
        limit: int = Query(default=50, ge=1, le=MAX_DECK_LIMIT),
        offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
    ):
        return read(lambda col: service.list_decks(col, root=root, limit=limit, offset=offset))

    @router.get("/notes/{note_id}", response_model=NoteOut)
    def get_note(note_id: str):
        return read(lambda col: service.get_note(col, note_id))

    @router.get("/cards/{card_id}", response_model=CardOut)
    def get_card(card_id: str):
        return read(lambda col: service.get_card(col, card_id))

    @router.post("/search", response_model=SearchPage)
    def search(body: SearchRequest):
        return read(lambda col: service.search(col, body.query, body.kind, body.limit, body.offset))

    @router.patch("/notes/{note_id}", response_model=PatchNoteResult)
    def patch_note(note_id: str, body: PatchNoteRequest):
        return write(lambda col: service.patch_note(col, note_id, body))

    @router.get("/media/{filename}")
    def get_media(filename: str):
        try:
            name = validate_media_filename(filename)
            path = resolve_media_file(media_dir, name)
        except InvalidMediaPath as exc:
            raise ApiError(
                400, "invalid_media_path", "media name must be a plain filename"
            ) from exc
        except MediaNotFound as exc:
            raise ApiError(404, "media_not_found", "media file does not exist") from exc
        guessed, _ = mimetypes.guess_type(name)
        media_type = (
            guessed if guessed and guessed.split("/")[0] in {"image", "audio", "video"} else None
        )
        return FileResponse(
            path,
            media_type=media_type or "application/octet-stream",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
            },
        )

    app.include_router(router)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(
            error_body(exc.code, exc.message, exc.details or None),
            status_code=exc.status,
            headers=exc.headers or None,
        )

    @app.exception_handler(CollectionBusy)
    async def _busy(_: Request, __: CollectionBusy):
        return JSONResponse(
            error_body("collection_busy", "collection is busy; retry shortly"),
            status_code=503,
            headers={"Retry-After": "1"},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = [
            {"loc": [str(p) for p in e.get("loc", ())], "type": e.get("type", "")}
            for e in exc.errors()
        ]
        return JSONResponse(
            error_body(
                "invalid_request", "request body or parameters are invalid", {"errors": errors}
            ),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        codes: dict[int, str] = {404: "not_found", 405: "method_not_allowed"}
        code = codes.get(exc.status_code, "http_error")
        message = "resource not found" if exc.status_code == 404 else str(exc.detail)
        return JSONResponse(error_body(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # Full traceback goes to the server log only. The client gets a fixed message.
        log.error(
            "unhandled error on %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc_info=exc,
        )
        return JSONResponse(error_body("internal_error", "internal error"), status_code=500)

    # Exposed for tests that need to inspect ownership state.
    app.state.actor = actor
    app.state.sync = sync
    return app

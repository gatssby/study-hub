"""Read-only FO content API (FastAPI). Exactly seven GET tool endpoints.

Run separately on a local bind, e.g.:
  STUDY_HUB_FO_DB=/path/fo.db uvicorn fo_hub.api:app_from_env --factory --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from .store import DB_ENV, DEFAULT_DB, FOStore

FO_TOOL_ROUTES = {
    "fo_list_lessons": "/fo/lessons",
    "fo_get_lesson": "/fo/lessons/{lesson_id}",
    "fo_search_materials": "/fo/materials",
    "fo_get_pdf_text": "/fo/materials/{material_id}/pdf-text",
    "fo_search_transcripts": "/fo/transcripts",
    "fo_get_transcript": "/fo/transcripts/{lesson_id}",
    "fo_get_sync_status": "/fo/sync-status",
}


def create_app(db_path: str | os.PathLike) -> FastAPI:
    app = FastAPI(title="Study Hub FO Content API (read-only)", version="1")
    store = FOStore(db_path, readonly=True)
    R = FO_TOOL_ROUTES

    @app.get(R["fo_list_lessons"], operation_id="fo_list_lessons")
    def list_lessons(subject: Optional[str] = None, front: Optional[str] = None,
                     module: Optional[str] = None, title: Optional[str] = None,
                     include_missing: bool = False, limit: int = Query(50, ge=1, le=200),
                     offset: int = Query(0, ge=0)):
        return {"items": store.list_lessons(subject, front, module, title, include_missing,
                                            limit, offset)}

    @app.get(R["fo_get_lesson"], operation_id="fo_get_lesson")
    def get_lesson(lesson_id: str):
        les = store.get_lesson(lesson_id)
        if les is None:
            raise HTTPException(404, "lesson not found")
        return les

    @app.get(R["fo_search_materials"], operation_id="fo_search_materials")
    def search_materials(subject: Optional[str] = None, front: Optional[str] = None,
                         module: Optional[str] = None, title: Optional[str] = None,
                         type: Optional[str] = None, limit: int = Query(50, ge=1, le=200),
                         offset: int = Query(0, ge=0)):
        return {"items": store.search_materials(subject, front, module, title, type,
                                                limit, offset)}

    @app.get(R["fo_get_pdf_text"], operation_id="fo_get_pdf_text")
    def get_pdf_text(material_id: str, page_start: int = Query(1, ge=1),
                     page_end: Optional[int] = Query(None, ge=1)):
        if page_end is not None and page_end < page_start:
            raise HTTPException(422, "page_end must not precede page_start")
        out = store.get_pdf_text(material_id, page_start, page_end)
        if out is None:
            raise HTTPException(404, "material not found")
        return out

    @app.get(R["fo_search_transcripts"], operation_id="fo_search_transcripts")
    def search_transcripts(q: str = Query(..., min_length=2, max_length=200),
                           subject: Optional[str] = None,
                           limit: int = Query(50, ge=1, le=200)):
        return {"items": store.search_transcripts(q, subject, limit)}

    @app.get(R["fo_get_transcript"], operation_id="fo_get_transcript")
    def get_transcript(lesson_id: str):
        t = store.get_transcript(lesson_id)
        if t is None:
            raise HTTPException(404, "no validated transcript for current lesson version")
        return t

    @app.get(R["fo_get_sync_status"], operation_id="fo_get_sync_status")
    def sync_status():
        return store.sync_status()

    return app


def app_from_env() -> FastAPI:
    return create_app(os.environ.get(DB_ENV, DEFAULT_DB))

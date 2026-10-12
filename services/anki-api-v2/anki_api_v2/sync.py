"""Collection and media sync for the API's own Service Collection.

Policy (see README.md):
- Reads call ensure_fresh(): a collection sync runs only when the last successful
  sync is older than the TTL or the last state is not "ok". Media files are never
  synced by reads.
- Writes call sync_collection() before and after the change (see service.py).
- Full sync is never chosen by this code. Any FULL_* answer from the server is
  reported as full_sync_required (409); nothing is uploaded or downloaded.
- Media sync is separate and starts only on explicit request.

Everything here runs on the collection owner thread (see actor.py), so the
state fields need no locking.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from anki.collection import Collection
from anki.errors import AnkiException, SyncErrorKind
from anki.notes import NoteId
from anki.sync_pb2 import SyncCollectionResponse

from anki_api_v2.errors import ApiError

log = logging.getLogger("anki_api_v2.sync")

NO_CHANGES = SyncCollectionResponse.NO_CHANGES
NORMAL_SYNC = SyncCollectionResponse.NORMAL_SYNC
FULL_SYNC = SyncCollectionResponse.FULL_SYNC
FULL_DOWNLOAD = SyncCollectionResponse.FULL_DOWNLOAD
FULL_UPLOAD = SyncCollectionResponse.FULL_UPLOAD
FULL_REQUIRED = {
    FULL_SYNC: "FULL_SYNC",
    FULL_DOWNLOAD: "FULL_DOWNLOAD",
    FULL_UPLOAD: "FULL_UPLOAD",
}

STATE_UNKNOWN = "unknown"
STATE_OK = "ok"
STATE_PENDING = "pending"
STATE_ERROR = "error"
STATE_FULL_REQUIRED = "full_sync_required"

MEDIA_IDLE = "idle"
MEDIA_RUNNING = "running"
MEDIA_OK = "ok"
MEDIA_ERROR = "error"


@dataclass(frozen=True)
class MediaStatus:
    active: bool
    error: str | None = None


class SyncTransport(Protocol):
    def sync_collection(self, col: Collection) -> int: ...

    def start_media(self, col: Collection) -> None: ...

    def media_status(self, col: Collection) -> MediaStatus: ...


class Clock(Protocol):
    def monotonic(self) -> float: ...

    def wallclock(self) -> datetime: ...

    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def wallclock(self) -> datetime:
        return datetime.now(timezone.utc)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


PACING_STEP_SECONDS = 0.02
PACING_MAX_WAIT_SECONDS = 2.0
PENDING_USN = -1
# Bounds one in-flight network sync so a stalled server cannot hold the owner thread.
SYNC_IO_TIMEOUT_SECONDS = 60


class AnkiSyncTransport:
    """Real transport: the official `anki` sync protocol against our sync server."""

    def __init__(self, *, endpoint: str, username: str, password: str) -> None:
        self._endpoint = endpoint
        self._username = username
        self._password = password
        self._auth: Any = None

    def _ensure_auth(self, col: Collection) -> Any:
        if self._auth is None:
            self._auth = col.sync_login(
                username=self._username,
                password=self._password,
                endpoint=self._endpoint,
            )
        self._auth.io_timeout_secs = SYNC_IO_TIMEOUT_SECONDS
        return self._auth

    def sync_collection(self, col: Collection) -> int:
        auth = self._ensure_auth(col)
        try:
            out = col.sync_collection(auth, sync_media=False)
        except AnkiException as exc:
            if getattr(exc, "kind", None) == SyncErrorKind.AUTH:
                self._auth = None  # forces a fresh login on the next attempt
            raise
        return int(out.required)

    def start_media(self, col: Collection) -> None:
        col.sync_media(self._ensure_auth(col))

    def media_status(self, col: Collection) -> MediaStatus:
        try:
            status = col.media_sync_status()
        except AnkiException as exc:
            return MediaStatus(active=False, error=type(exc).__name__)
        return MediaStatus(active=bool(status.active), error=None)


class SyncManager:
    def __init__(
        self, transport: SyncTransport, clock: Clock, freshness_ttl_seconds: float
    ) -> None:
        self._transport = transport
        self._clock = clock
        self._ttl = freshness_ttl_seconds
        self._last_ok_mono: float | None = None
        self._last_ok_second: int | None = None
        # Note whose local change the sync server has not confirmed yet. Only a sync that
        # shows that note's usn as accepted clears it; NO_CHANGES alone never does.
        self._pending_note_id: int | None = None
        self.collection_state = STATE_UNKNOWN
        self.last_collection_sync_at: datetime | None = None
        self.media_state = MEDIA_IDLE
        self.last_media_sync_at: datetime | None = None

    # ---- collection ----------------------------------------------------

    def ensure_fresh(self, col: Collection) -> None:
        """Read path: sync only if stale or not in a known-good state."""
        if self._pending_note_id is None and self.collection_state == STATE_OK:
            fresh = self._last_ok_mono is not None
            if fresh and self._clock.monotonic() - self._last_ok_mono < self._ttl:
                return
        self.sync_collection(col)

    @property
    def sync_state(self) -> str:
        if self._pending_note_id is not None:
            return STATE_PENDING
        return self.collection_state

    def sync_collection(self, col: Collection) -> str:
        if self._pending_note_id is not None:
            # Retrying an unconfirmed change: it must not share a second with the last sync.
            self.pace_for_write()
        try:
            required = self._transport.sync_collection(col)
        except AnkiException as exc:
            self.collection_state = STATE_ERROR
            kind = getattr(exc, "kind", None)
            log.warning("collection sync failed: %s kind=%s", type(exc).__name__, kind)
            raise ApiError(
                502,
                "sync_failed",
                "collection sync failed; no confirmed sync with the sync server",
                details={"scope": "collection"},
            ) from exc

        if required == NO_CHANGES:
            name = "no_changes"
        elif required == NORMAL_SYNC:
            name = "normal_sync"
        elif required in FULL_REQUIRED:
            self.collection_state = STATE_FULL_REQUIRED
            kind_name = FULL_REQUIRED[required]
            log.error("sync server requires %s; refusing automatic full sync", kind_name)
            raise ApiError(
                409,
                "full_sync_required",
                "the sync server requires a full sync; the API never picks a direction",
                details={"required": kind_name},
            )
        else:
            self.collection_state = STATE_ERROR
            log.error("unexpected sync response code %r", required)
            raise ApiError(
                502,
                "sync_failed",
                "unexpected response from the sync server",
                details={"scope": "collection"},
            )

        now = self._clock.wallclock()
        self._last_ok_mono = self._clock.monotonic()
        self.last_collection_sync_at = now
        self._last_ok_second = int(now.timestamp())
        if self._pending_note_id is not None and confirm_note_synced(col, self._pending_note_id):
            self._pending_note_id = None
        self.collection_state = STATE_OK
        return name

    def sync_before_write(self, col: Collection) -> None:
        """Write path, step 1: the server must accept a sync before we touch anything.

        Refuses to start a new change while an earlier one is still unconfirmed, so at
        most one unconfirmed change is ever tracked.
        """
        self.sync_collection(col)
        if self._pending_note_id is not None:
            raise ApiError(
                502,
                "sync_failed",
                "a previous change is not yet confirmed by the sync server",
                details={"scope": "collection", "reason": "previous_change_unconfirmed"},
            )

    def pace_for_write(self) -> None:
        """Wait until the wall-clock second has moved past the last successful sync.

        Anki's change detection works at one-second resolution. A change made in the
        same second as the previous sync is not uploaded, yet the sync still reports
        NO_CHANGES. Pacing avoids that false negative. It is an optimisation only: the
        usn check in confirm_note_synced() is what guarantees no false success.
        """
        if self._last_ok_second is None:
            return
        waited = 0.0
        while int(self._clock.wallclock().timestamp()) <= self._last_ok_second:
            if waited >= PACING_MAX_WAIT_SECONDS:
                log.warning("pacing gave up after %.1fs; relying on confirmation check", waited)
                return
            self._clock.sleep(PACING_STEP_SECONDS)
            waited += PACING_STEP_SECONDS

    def sync_after_write(self, col: Collection, note_id: int, *, expect_change: bool) -> None:
        """Write path, step 3: the change is confirmed only if the server accepted it.

        Raises ApiError when the sync fails, or when the sync succeeds but the note is
        still marked as unsent (usn == -1). The second case is the silent loss mode.
        """
        try:
            self.sync_collection(col)
        except ApiError:
            self.mark_pending(note_id)
            raise
        if expect_change and not confirm_note_synced(col, note_id):
            self.mark_pending(note_id)
            raise ApiError(
                502,
                "sync_failed",
                "the sync server did not confirm the change",
                details={"scope": "collection", "reason": "change_not_detected"},
            )

    def mark_pending(self, note_id: int) -> None:
        """A local change to note_id exists that the sync server has not confirmed."""
        self._pending_note_id = note_id

    # ---- media ---------------------------------------------------------

    def start_media(self, col: Collection) -> str:
        try:
            self._transport.start_media(col)
        except AnkiException as exc:
            self.media_state = MEDIA_ERROR
            log.warning("media sync failed to start: %s", type(exc).__name__)
            raise ApiError(
                502,
                "sync_failed",
                "media sync could not start",
                details={"scope": "media"},
            ) from exc
        self.media_state = MEDIA_RUNNING
        return MEDIA_RUNNING

    def refresh_media(self, col: Collection) -> None:
        status = self._transport.media_status(col)
        if status.active:
            self.media_state = MEDIA_RUNNING
            return
        if self.media_state != MEDIA_RUNNING:
            return
        if status.error:
            self.media_state = MEDIA_ERROR
            log.warning("media sync finished with error: %s", status.error)
        else:
            self.media_state = MEDIA_OK
            self.last_media_sync_at = self._clock.wallclock()


def confirm_note_synced(col: Collection, note_id: int) -> bool:
    """True when the server has taken the note. Anki marks a changed note usn == -1
    until the server accepts it, and sets a positive usn afterwards. This check is
    local, so it does not depend on the sync return code, which the measurements
    showed can be NO_CHANGES even when a change was lost.
    """
    return int(col.get_note(NoteId(note_id)).usn) != PENDING_USN


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

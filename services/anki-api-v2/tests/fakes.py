"""Test doubles: a controllable clock and a fake sync server.

The collection is always real (synthetic, temporary). Only the network transport
and the clock are faked. The fake server keeps the confirmed value of the watched
note; a sync carries the local value to it only when it differs, mirroring the
official protocol's "changed since last sync" behaviour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from anki.collection import Collection
from anki.errors import NetworkError
from anki_api_v2.sync import MediaStatus

NO_CHANGES = 0
NORMAL_SYNC = 1
FULL_SYNC = 2
FULL_DOWNLOAD = 3
FULL_UPLOAD = 4


def _acknowledge_pending(col: Collection) -> None:
    # What the real client does once the server accepts: pending notes (usn == -1)
    # receive a positive usn. Test double only; production code never writes this.
    col.db.execute("update notes set usn = 1 where usn = -1")


class FakeClock:
    def __init__(self) -> None:
        self._mono = 1000.0
        self._wall = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        return self._mono

    def wallclock(self) -> datetime:
        return self._wall

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        self._mono += seconds
        self._wall += timedelta(seconds=seconds)


class FakeSyncBackend:
    """Stands in for the network sync transport and the sync server.

    server_fields: the confirmed value of the watched note on the fake server.
    drop_changes: when True the server answers NO_CHANGES and keeps nothing,
    reproducing the silent loss observed against the real server.
    sync_seconds: wall-clock second of every sync call, in order.
    """

    def __init__(self, *, clock: FakeClock, watch_note_id: str | None = None) -> None:
        self._clock = clock
        self.watch_note_id = watch_note_id
        self.server_fields: dict[str, str] | None = None
        self.events: list[tuple[Any, ...]] = []
        self.sync_seconds: list[int] = []
        self.responses: list[int] = []
        self.fail_on_calls: set[int] = set()
        self.drop_changes = False
        self.sync_calls = 0
        self.media_starts = 0
        self.media_active = False
        self.media_error: str | None = None

    def _local(self, col: Collection) -> dict[str, str] | None:
        if self.watch_note_id is None:
            return None
        return dict(col.get_note(int(self.watch_note_id)).items())

    def sync_collection(self, col: Collection) -> int:
        self.sync_calls += 1
        local = self._local(col)
        second = int(self._clock.wallclock().timestamp())
        self.events.append(("sync", local, second))
        self.sync_seconds.append(second)
        if self.sync_calls in self.fail_on_calls:
            raise NetworkError("synthetic network failure", None, None, None)
        if self.responses:
            return self.responses.pop(0)
        if local is None:
            return NO_CHANGES
        if self.server_fields is None:
            self.server_fields = dict(local)  # server starts with the same data
        if self.drop_changes:
            # Reproduces the observed loss: the server keeps its old copy and the
            # local note stays marked as unsent (usn == -1).
            return NO_CHANGES
        changed = local != self.server_fields
        self.server_fields = dict(local)
        _acknowledge_pending(col)
        return NORMAL_SYNC if changed else NO_CHANGES

    def start_media(self, col: Collection) -> None:
        self.media_starts += 1
        self.media_active = True

    def media_status(self, col: Collection) -> MediaStatus:
        return MediaStatus(active=self.media_active, error=self.media_error)

    def sync_events(self) -> list[tuple[Any, ...]]:
        return [e for e in self.events if e[0] == "sync"]

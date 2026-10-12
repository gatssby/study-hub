"""Single-owner actor for the Service Collection.

Decision (security + latency):
- Exactly one thread opens, uses and closes the `Collection`. Every operation is
  a job executed on that thread, in FIFO order. No Collection object is ever
  shared between threads, and there is no per-request open/close.
- Cross-process ownership is an exclusive `flock` on the same `collection.lock`
  file that `service_sync.py` already uses, so a second process (including the
  legacy script) fails fast instead of opening the collection concurrently.
- Queue wait is bounded. If a job has not STARTED within the timeout it is
  cancelled and the caller gets CollectionBusy, so the operation never runs late.
  Once a job has started it runs to completion; a write is never reported as
  "busy" while it may still be applied.
"""

from __future__ import annotations

import fcntl
import logging
import queue
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

log = logging.getLogger("anki_api_v2.actor")

T = TypeVar("T")
OPEN_TIMEOUT_SECONDS = 60.0
STOP_TIMEOUT_SECONDS = 30.0


class CollectionBusy(RuntimeError):
    """The job waited too long in the queue and was NOT executed."""


class CollectionLockedError(RuntimeError):
    """Another process owns the collection lock."""


class _Job:
    __slots__ = ("fn", "started", "done", "result", "error", "cancelled")

    def __init__(self, fn: Callable[[Any], Any]) -> None:
        self.fn = fn
        self.started = threading.Event()
        self.done = threading.Event()
        self.result: Any = None
        self.error: BaseException | None = None
        self.cancelled = False


class CollectionActor:
    def __init__(
        self,
        *,
        open_fn: Callable[[], Any],
        lock_path: Path,
        queue_timeout: float,
        close_fn: Callable[[Any], None] | None = None,
    ) -> None:
        self._open_fn = open_fn
        self._close_fn = close_fn
        self._lock_path = Path(lock_path)
        self._queue_timeout = queue_timeout
        self._jobs: queue.Queue[_Job | None] = queue.Queue()
        self._guard = threading.Lock()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock_handle: Any = None
        self._col: Any = None
        self._open_error: BaseException | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            raise RuntimeError("collection actor already started")
        self._lock_handle = self._acquire_lock()
        self._ready.clear()
        self._open_error = None
        self._thread = threading.Thread(
            target=self._loop, name="anki-collection-owner", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(OPEN_TIMEOUT_SECONDS):
            self._open_error = TimeoutError("collection did not open in time")
        if self._open_error is not None:
            error = self._open_error
            self._release_lock()
            self._thread = None
            raise error
        self._running = True
        log.info("collection opened and owned by actor thread")

    def submit(self, fn: Callable[[Any], T], timeout: float | None = None) -> T:
        if not self._running:
            raise RuntimeError("collection actor is not running")
        job = _Job(fn)
        self._jobs.put(job)
        wait = self._queue_timeout if timeout is None else timeout
        if not job.started.wait(wait):
            with self._guard:
                if not job.started.is_set():
                    job.cancelled = True
                    raise CollectionBusy("collection is busy; retry shortly")
        job.done.wait()
        if job.error is not None:
            raise job.error
        return job.result

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._jobs.put(None)
        assert self._thread is not None
        self._thread.join(STOP_TIMEOUT_SECONDS)
        if self._thread.is_alive():
            # Do not release the lock while the collection may still be open.
            log.error("collection owner did not stop in time; keeping lock until exit")
            return
        self._thread = None
        self._release_lock()

    def _loop(self) -> None:
        try:
            self._col = self._open_fn()
        except BaseException as exc:  # reported to start()
            self._open_error = exc
            self._ready.set()
            return
        self._ready.set()
        try:
            while True:
                job = self._jobs.get()
                if job is None:
                    return
                with self._guard:
                    if job.cancelled:
                        continue
                    job.started.set()
                try:
                    job.result = job.fn(self._col)
                except BaseException as exc:
                    job.error = exc
                finally:
                    job.done.set()
        finally:
            self._close_collection()

    def _close_collection(self) -> None:
        col, self._col = self._col, None
        if col is None:
            return
        try:
            if self._close_fn is not None:
                self._close_fn(col)
            elif hasattr(col, "close"):
                col.close()
        except Exception:
            log.exception("error while closing collection")

    def _acquire_lock(self) -> Any:
        handle = open(self._lock_path, "a+")  # noqa: SIM115 - held for process lifetime
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise CollectionLockedError(
                f"collection lock {self._lock_path} is held by another process"
            ) from exc
        return handle

    def _release_lock(self) -> None:
        handle, self._lock_handle = self._lock_handle, None
        if handle is None:
            return
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()

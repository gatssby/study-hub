"""Bounded metadata-only storage observations; never removes media or state."""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import time

GIB = 1024**3
MIB = 1024**2


def growth_per_day(history: list[dict]) -> float | None:
    if len(history) < 2:
        return None
    first, last = history[0], history[-1]
    elapsed = last['observed_at'] - first['observed_at']
    if elapsed < 6 * 3600:
        return None
    return (last['study_hub_bytes'] - first['study_hub_bytes']) * 86400 / elapsed


def storage_warning(available: int, reserve: int, growth: float | None) -> str | None:
    if available < reserve:
        return 'low_reserve'
    if growth is not None and growth > 0 and (available - reserve) / growth <= 7:
        return 'growth_risk'
    return None


def inventory_bytes(root: Path) -> tuple[int, int]:
    """Count unique owned regular inodes, without opening originals or links."""
    seen: set[tuple[int, int]] = set()
    temporary_seen: set[tuple[int, int]] = set()
    total = temporary = entries = 0
    started = time.monotonic()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()
                   and (Path(directory) / d) != root / 'telemetry']
        for name in files:
            entries += 1
            if entries > 100000 or time.monotonic() - started > 20:
                raise RuntimeError('inventory_budget_exceeded')
            p = Path(directory) / name
            try:
                info = p.lstat()
            except FileNotFoundError:
                continue  # A live worker may complete and remove its own temp.
            if not stat.S_ISREG(info.st_mode):
                continue
            key = info.st_dev, info.st_ino
            if key not in seen:
                total += info.st_size
                seen.add(key)
            if p.is_relative_to(root / 'tmp') and key not in temporary_seen:
                temporary += info.st_size
                temporary_seen.add(key)
    return total, temporary


def _atomic_json(path: Path, data: object) -> None:
    temporary = path.with_suffix('.json.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _largest_source(root: Path) -> int:
    # Explicit close only: sqlite3's context manager commits, it does not close.
    connection = sqlite3.connect(f'file:{root}/hub.sqlite3?mode=ro', uri=True, timeout=1)
    try:
        connection.execute('pragma query_only=on')
        connection.execute('pragma cache_size=-1024')
        deadline = time.monotonic() + 2
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        return int(connection.execute('select coalesce(max(size),0) from lesson_video_sources where available=1').fetchone()[0])
    finally:
        connection.close()


def sample(root: Path, *, now: float | None = None, available_bytes: int | None = None,
           largest_source_bytes: int | None = None) -> dict:
    observed = time.time() if now is None else now
    total, temporary = inventory_bytes(root)
    available = shutil.disk_usage(root).free if available_bytes is None else available_bytes
    largest = _largest_source(root) if largest_source_bytes is None else largest_source_bytes
    reserve = 4 * GIB + 100 * MIB + largest
    destination = root / 'telemetry'
    destination.mkdir(mode=0o700, exist_ok=True)
    with (destination / 'storage.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        history_path = destination / 'storage-history.json'
        history = json.loads(history_path.read_text()) if history_path.exists() else []
        history = [row for row in history if observed - 7 * 86400 <= row['observed_at'] < observed]
        history.append({'observed_at': observed, 'study_hub_bytes': total})
        history = history[-168:]
        growth = growth_per_day(history)
        result = {'observed_at': observed, 'available_bytes': available,
                  'study_hub_bytes': total, 'temp_bytes': temporary,
                  'whisper_reserve_bytes': reserve, 'growth_bytes_per_day': growth,
                  'warning': storage_warning(available, reserve, growth)}
        _atomic_json(history_path, history)
        _atomic_json(destination / 'storage.json', result)
    if result['warning']:
        logging.warning('storage_warning=%s', result['warning'])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = sample(args.state_root)
    except Exception as exc:
        logging.error('storage_observation_failed=%s', type(exc).__name__)
        raise SystemExit(1) from None
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()

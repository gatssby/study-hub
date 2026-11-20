"""Deterministic cleanup of abandoned non-current-revision video partials."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))

NOW = 1_800_000_000.0


class Log:
    def __init__(self):
        self.lines = []

    def log(self, message):
        self.lines.append(message)


def make_partial(tmp, key, version, age_s):
    path = tmp / f'{key}-{version}.partial.mp4'
    path.write_bytes(b'x' * 10)
    os.utime(path, (NOW - age_s, NOW - age_s))
    return path


def test_sweep_removes_only_aged_non_current_revision_partials(tmp_path):
    from video_runtime import sweep_stale_partials
    manifest = {'items': {'k1': {'revision': 'new1'}, 'k2': {'revision': 'cur2'}}}
    stale = make_partial(tmp_path, 'k1', 'old1', 7200)
    current = make_partial(tmp_path, 'k2', 'cur2', 7200)   # resumable/evidence: keep
    unknown = make_partial(tmp_path, 'k3', 'old3', 7200)   # ownership unknown: keep
    fresh = make_partial(tmp_path, 'k1', 'old9', 60)       # possible active writer: keep
    complete = tmp_path / 'k1-old1.mp4'                    # complete original: never sweep
    complete.write_bytes(b'complete')
    log = Log()
    removed = sweep_stale_partials(tmp_path, manifest, log, now=NOW)
    assert removed == [{'key': 'k1', 'revision': 'old1', 'bytes': 10}]
    assert not stale.exists()
    assert current.exists() and unknown.exists() and fresh.exists() and complete.exists()
    assert log.lines


def test_sweep_respects_budget_and_refuses_symlinks(tmp_path):
    from video_runtime import sweep_stale_partials
    manifest = {'items': {'k1': {'revision': 'new1'}}}
    for i in range(6):
        make_partial(tmp_path, 'k1', f'old{i}', 7200)
    target = tmp_path / 'target.bin'
    target.write_bytes(b'keep')
    link = tmp_path / 'k1-oldlink.partial.mp4'
    link.symlink_to(target)
    removed = sweep_stale_partials(tmp_path, manifest, Log(), now=NOW, max_files=2)
    assert len(removed) == 2
    assert link.is_symlink() and target.read_bytes() == b'keep'
    assert len(list(tmp_path.glob('*.partial.mp4'))) == 5  # 6 stale - 2 removed + 1 symlink


def test_sweep_without_manifest_items_preserves_everything(tmp_path):
    from video_runtime import sweep_stale_partials
    partial = make_partial(tmp_path, 'k1', 'old1', 7200)
    assert sweep_stale_partials(tmp_path, {'items': {}}, Log(), now=NOW) == []
    assert partial.exists()
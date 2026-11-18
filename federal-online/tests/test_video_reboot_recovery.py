"""Interruption safety without real downloads, remote writes, or ASR."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))
import video_runtime as runtime


def test_interruption_during_verification_preserves_stable_resume_path(tmp_path, monkeypatch):
    row = {'course_url': 'https://example.test/course', 'media_id': '42',
           'video_stream_url': 'https://example.test/stream', 'duracao_segundos': 100}
    local = tmp_path / 'tmp/videos' / f'{runtime.identity(row)}-{runtime.revision(row)}.mp4'
    local.parent.mkdir(parents=True)
    local.write_bytes(b'validated video')
    monkeypatch.setattr(runtime, 'STATE', tmp_path)
    monkeypatch.setattr(runtime, 'rows_from_catalog', lambda: [row])
    real_exists = Path.exists
    monkeypatch.setattr(Path, 'exists', lambda p: True if str(p) == '/home/ubuntu/anki-vnext' else real_exists(p))
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda p: type('Usage', (), {'free': 10 * 1024**3})())
    monkeypatch.setattr(runtime.subprocess, 'run', lambda *a, **kw: None)
    def interrupted(*args):
        assert local.exists(), 'verification must never rename the only resumable original'
        raise KeyboardInterrupt('simulated service interruption')
    monkeypatch.setattr(runtime, 'verify_upload', interrupted)
    with pytest.raises(KeyboardInterrupt):
        runtime.main()
    assert local.read_bytes() == b'validated video'
    assert not (tmp_path / 'videos.json').exists()


@pytest.mark.parametrize('interrupted', [False, True])
def test_verification_uses_hardlink_view_and_preserves_original(tmp_path, interrupted):
    local = tmp_path / 'stable-key-revision.mp4'
    local.write_bytes(b'validated video')
    def runner(command, **kwargs):
        view = Path(command[2])
        named = view / 'Display title.mp4'
        assert named.samefile(local)
        assert named.read_bytes() == local.read_bytes()
        assert '--download' in command
        assert (view / '.verify-files').read_text() == 'Display title.mp4\n'
        if interrupted:
            raise KeyboardInterrupt('simulated termination')
    if interrupted:
        with pytest.raises(KeyboardInterrupt):
            runtime.verify_upload(local, 'onedrive:course/Display title.mp4', runner)
    else:
        runtime.verify_upload(local, 'onedrive:course/Display title.mp4', runner)
    assert list(tmp_path.iterdir()) == [local]
    assert local.read_bytes() == b'validated video'


def test_retry_probes_short_source_before_discarding_known_partial(tmp_path, monkeypatch):
    row = {'course_url': 'https://example.test/course', 'media_id': '42',
           'video_stream_url': 'https://example.test/stream', 'duracao_segundos': 2463}
    key, version = runtime.identity(row), runtime.revision(row)
    partial = tmp_path / 'tmp/videos' / f'{key}-{version}.partial.mp4'
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b'recoverable partial')
    manifest = tmp_path / 'videos.json'
    manifest.write_text(json.dumps({'items': {key: {'revision': version, 'status': 'error', 'attempts': 2}}}))
    monkeypatch.setattr(runtime, 'STATE', tmp_path)
    monkeypatch.setattr(runtime, 'rows_from_catalog', lambda: [row])
    real_exists = Path.exists
    monkeypatch.setattr(Path, 'exists', lambda p: True if str(p) == '/home/ubuntu/anki-vnext' else real_exists(p))
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda p: type('Usage', (), {'free': 10 * 1024**3})())
    commands = []
    def probe(command, **kwargs):
        commands.append(command)
        assert command[0] == 'ffprobe'
        return type('Result', (), {'stdout': '{"format":{"duration":"1746.368501"}}'})()
    monkeypatch.setattr(runtime.subprocess, 'run', probe)
    runtime.main()
    assert partial.read_bytes() == b'recoverable partial'
    result = json.loads(manifest.read_text())['items'][key]
    assert result['error_type'] == 'SourceDurationMismatch'
    assert result['retry_at'] >= runtime.time.time() + 5 * 3600
    assert len(commands) == 1


def test_partial_cleanup_preserves_other_revisions_of_same_lesson(tmp_path):
    current = tmp_path / 'lesson-current.partial.mp4'
    old = tmp_path / 'lesson-old.partial.mp4'
    current.write_bytes(b'retryable')
    old.write_bytes(b'needs classification')
    logger = type('Log', (), {'log': lambda *args: None})()
    assert runtime.discard_recoverable_partial(tmp_path, 'lesson', logger, revision='current') == 1
    assert old.read_bytes() == b'needs classification'


def test_failed_fresh_download_discards_only_its_partial(tmp_path, monkeypatch):
    from types import SimpleNamespace
    row = {'course_url': 'https://example.test/course', 'media_id': '42',
           'video_stream_url': 'https://example.test/stream', 'duracao_segundos': 100}
    key, version = runtime.identity(row), runtime.revision(row)
    media = tmp_path / 'tmp/videos'
    media.mkdir(parents=True)
    retained = media / f'{key}-retained.mp4'
    retained.write_bytes(b'completed other revision')
    monkeypatch.setattr(runtime, 'STATE', tmp_path)
    monkeypatch.setattr(runtime, 'rows_from_catalog', lambda: [row])
    real_exists = Path.exists
    monkeypatch.setattr(Path, 'exists', lambda p: True if str(p) == '/home/ubuntu/anki-vnext' else real_exists(p))
    monkeypatch.setattr(runtime.shutil, 'disk_usage', lambda p: SimpleNamespace(free=10 * 1024**3))
    monkeypatch.setattr(runtime.core, 'build_candidates', lambda *a, **kw: [SimpleNamespace()])
    monkeypatch.setattr(runtime.core, 'choose_stream_selection', lambda *a: SimpleNamespace(video_stream_index=0, audio_stream_index=None))
    monkeypatch.setattr(runtime.core, 'title_from_aula', lambda row: 'Lesson')
    monkeypatch.setattr(runtime.core, 'source_ref_from_aula', lambda row: None)
    monkeypatch.setattr(runtime.core, 'source_ref_to_parts', lambda ref: ['Course'])
    def failed_process(cmd, **kwargs):
        Path(cmd[-1]).write_bytes(b'incomplete video')
        return SimpleNamespace(poll=lambda: 1, returncode=1)
    monkeypatch.setattr(runtime.subprocess, 'Popen', failed_process)
    runtime.main()
    assert list(media.iterdir()) == [retained]
    manifest = json.loads((tmp_path / 'videos.json').read_text())['items'][key]
    assert manifest['status'] == 'error' and manifest['revision'] == version

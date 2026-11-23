"""Read-only preparation checks; never start a decoder or lease a job."""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from fo_hub import worker


@pytest.mark.parametrize('existing', [True, False])
def test_preflight_missing_schema_or_paths_is_blocked_without_creating_db(tmp_path, existing):
    db = tmp_path / 'hub.db'
    if existing:
        sqlite3.connect(db).close()
    cfg = worker.Config(tmp_path / 'missing-state', db, tmp_path / 'binary', tmp_path / 'model')
    with pytest.raises(sqlite3.Error):
        worker.preflight(cfg)
    assert db.exists() is existing
    assert not cfg.state.exists()


def test_check_only_missing_database_reports_blocked_without_creating_it(tmp_path, monkeypatch, capsys):
    cfg = worker.Config(tmp_path / 'absent', tmp_path / 'absent/hub.db', tmp_path / 'bin', tmp_path / 'model')
    monkeypatch.setattr(worker.Config, 'from_env', lambda: cfg)
    assert worker.main(['--check-only']) == 1
    err = capsys.readouterr()
    assert 'OperationalError' in err.err
    assert not err.out and not cfg.db.exists()


def test_preflight_closes_readonly_connection_on_schema_error(tmp_path, monkeypatch):
    db = tmp_path / 'hub.db'
    cfg = worker.Config(tmp_path, db, tmp_path / 'bin', tmp_path / 'model')
    conn = sqlite3.connect(db)

    def store(path, *, readonly):
        assert path == db and readonly is True
        return SimpleNamespace(conn=conn)

    monkeypatch.setattr(worker, 'FOStore', store)
    with pytest.raises(sqlite3.OperationalError, match='no such table'):
        worker.preflight(cfg)
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        conn.execute('select 1')


def setup_checks(case, monkeypatch):
    deps = []

    def which(name):
        deps.append(name)
        return str(case.cfg.binary)

    def forbidden(*args, **kwargs):
        pytest.fail('preflight must not execute a subprocess')

    monkeypatch.setattr(worker.shutil, 'which', which)
    monkeypatch.setattr(worker.subprocess, 'run', forbidden)
    monkeypatch.setenv('TRANSCRIPTION_ENABLED', 'false')
    return deps


def test_preflight_reports_resources_dependencies_and_reset_without_writing(mvp_case, monkeypatch):
    case = mvp_case()
    deps = setup_checks(case, monkeypatch)
    before = case.store.conn.execute('SELECT * FROM transcription_jobs').fetchall()
    result = worker.preflight(case.cfg)
    assert result == {'reset_applied': True, 'counts': {'queued': 1}, 'leased': [],
                      'free_bytes': 20 * 1024**3, 'authorized': False,
                      'model_sha256': worker.MODEL_SHA256, 'decoder_sha256': worker.file_identity(case.cfg.binary),
                      'inference_executed': False}
    assert deps == ['ffmpeg', 'ffprobe', 'rclone']
    assert case.store.conn.execute('SELECT * FROM transcription_jobs').fetchall() == before
    assert not (case.cfg.state / 'transcription-mvp').exists()


def test_check_only_is_readonly_and_run_preserves_blocked_gate(mvp_case, monkeypatch, capsys):
    case = mvp_case(reset=False)
    setup_checks(case, monkeypatch)
    monkeypatch.setattr(worker.Config, 'from_env', lambda: case.cfg)
    assert case.queue.enqueue(case.lesson_id, 1)
    before = case.store.conn.execute('SELECT * FROM transcription_jobs').fetchall()
    assert worker.main(['--check-only']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['authorized'] is False and result['reset_applied'] is False
    assert result['inference_executed'] is False and result['leased'] == []
    assert worker.main(['--run']) == 3
    assert 'authorization and MVP reset required' in capsys.readouterr().err
    assert not (case.cfg.state / 'locks').exists()
    assert case.store.conn.execute('SELECT * FROM transcription_jobs').fetchall() == before

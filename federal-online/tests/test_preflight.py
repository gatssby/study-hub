"""Read-only preparation checks; never start a decoder or lease a job."""
import json
from pathlib import Path
from types import SimpleNamespace

from test_worker_readiness import ready
from fo_hub import worker
import sqlite3
import pytest
from fo_hub.store import FOStore


@pytest.mark.parametrize('existing', [True, False])
def test_preflight_missing_schema_or_paths_is_blocked_without_creating_db(tmp_path, existing):
    db = tmp_path/'hub.db'
    if existing:
        FOStore(db).conn.close()
    cfg = worker.Config(tmp_path/'missing-state', db, tmp_path/'binary', tmp_path/'model')
    result = worker.preflight(cfg, runner=lambda *a, **k: SimpleNamespace(stdout='fake', stderr=''))
    assert result['ready'] is False
    assert any('database' in p for p in result['problems'])
    assert result['eligible_jobs'] == 0
    assert result['invalid_sources'] == 0
    assert result['storage']['free_bytes'] is None
    assert db.exists() == existing
    assert not cfg.state.exists()


def test_check_only_missing_database_reports_blocked_without_creating_it(tmp_path, monkeypatch, capsys):
    cfg = worker.Config(tmp_path/'absent', tmp_path/'absent/hub.db', tmp_path/'bin', tmp_path/'model')
    monkeypatch.setattr(worker.Config, 'from_env', lambda: cfg)
    monkeypatch.setenv('TRANSCRIPTION_ENABLED', 'false')
    assert worker.main(['--check-only']) == 0
    result = json.loads(capsys.readouterr().out)
    assert not result['preflight']['ready']
    assert result['queue'] == {}
    assert not cfg.db.exists()


def test_preflight_closes_readonly_connection_on_schema_error(tmp_path, monkeypatch):
    store = FOStore(tmp_path/'hub.db')
    cfg = worker.Config(tmp_path, store.path, tmp_path/'bin', tmp_path/'model')
    conn = sqlite3.connect(store.path)
    monkeypatch.setattr(worker, 'FOStore', lambda *a, **k: SimpleNamespace(conn=conn))
    result = worker.preflight(cfg, runner=lambda *a, **k: SimpleNamespace(stdout='fake', stderr=''))
    assert not result['ready']
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        conn.execute('select 1')


def test_preflight_reports_resources_dependencies_and_eligible_sources(tmp_path, monkeypatch):
    store, lesson, cfg = ready(tmp_path)
    calls = []
    def runner(cmd, **kwargs):
        calls.append(cmd)
        assert '-f' not in cmd and '--run' not in cmd
        return SimpleNamespace(stdout='fake version\n', stderr='-ojf -nth -et -lpt -tpi -nf -bs')
    monkeypatch.setattr(worker.shutil, 'which', lambda name: str(cfg.binary))
    cfg.binary.write_text('fake executable'); cfg.binary.chmod(0o755)
    cfg.model.write_text('fake weights')
    before = [tuple(r) for r in store.conn.execute('select * from transcription_jobs')]
    result = worker.preflight(cfg, runner=runner)
    assert result['eligible_jobs'] == 1
    assert result['storage']['reserve_bytes'] == worker.RESERVE
    assert result['model_sha256']
    assert result['runtime_sha256']
    assert result['inference_executed'] is False
    assert result['dependencies']['rclone']['available']
    assert [tuple(r) for r in store.conn.execute('select * from transcription_jobs')] == before
    assert calls


def test_check_only_is_readonly_and_preserves_blocked_gate(tmp_path, monkeypatch, capsys):
    store, _, cfg = ready(tmp_path)
    monkeypatch.setattr(worker.Config, 'from_env', lambda: cfg)
    monkeypatch.setattr(worker, 'preflight', lambda c: {'inference_executed': False, 'ready': False})
    monkeypatch.setenv('TRANSCRIPTION_ENABLED', 'false')
    assert worker.main(['--check-only']) == 0
    result = json.loads(capsys.readouterr().out)
    assert not result['gate']['allowed']
    assert result['preflight']['inference_executed'] is False
    assert store.conn.execute('select attempts from transcription_jobs').fetchone()[0] == 0

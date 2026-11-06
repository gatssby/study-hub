"""Lease heartbeat uses synthetic work only; never opens audio or decoder."""
import sqlite3
import time
from fo_hub.worker import Config, Worker
from test_worker_readiness import ready


def test_default_runtime_uses_homologated_no_context(monkeypatch):
    monkeypatch.delenv('FO_ASR_MAX_CONTEXT', raising=False)
    assert Config.from_env().max_context == 0


def test_long_pipeline_renews_owned_lease_before_first_chunk(tmp_path, monkeypatch):
    import fo_hub.worker as module
    monkeypatch.setattr(module, 'HEARTBEAT_INTERVAL_S', 0.02, raising=False)
    store, lesson, cfg = ready(tmp_path)
    worker = Worker(cfg, store, gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20 * 1024**3)
    observed = []
    def pipeline(job, work):
        initial = float(store.conn.execute('SELECT updated_at FROM transcription_jobs').fetchone()[0])
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            row = store.conn.execute('SELECT updated_at,lease_until,lease_owner,attempts FROM transcription_jobs').fetchone()
            if float(row['updated_at']) > initial:
                observed.append(dict(row))
                return 'review'
            time.sleep(.01)
        raise AssertionError('no heartbeat during long chunk')
    monkeypatch.setattr(worker, 'pipeline', pipeline)
    assert worker.run_once()['state'] == 'review'
    assert observed[0]['attempts'] == 1
    assert observed[0]['lease_owner'] == worker.owner
    assert observed[0]['lease_until'] > time.time()
    final = store.conn.execute('SELECT updated_at,lease_owner FROM transcription_jobs').fetchone()
    assert final['lease_owner'] is None
    time.sleep(.08)
    assert store.conn.execute('SELECT updated_at FROM transcription_jobs').fetchone()[0] == final['updated_at']


def test_heartbeat_cannot_reclaim_another_owner(tmp_path, monkeypatch):
    import fo_hub.worker as module
    monkeypatch.setattr(module, 'HEARTBEAT_INTERVAL_S', .01, raising=False)
    store, lesson, cfg = ready(tmp_path)
    worker = Worker(cfg, store, gate_fn=lambda: {'allowed': True})
    job = worker.lease()
    with store.conn:
        store.conn.execute("UPDATE transcription_jobs SET lease_owner='other',updated_at='123',lease_until=456")
    with worker.heartbeat(job):
        time.sleep(.06)
    row = store.conn.execute('SELECT updated_at,lease_until,lease_owner FROM transcription_jobs').fetchone()
    assert tuple(row) == ('123', 456, 'other')

from contextlib import ExitStack
import json
from types import SimpleNamespace

import pytest

from fo_hub import worker
from fo_hub.store import FOStore, lesson_id_for
from fo_hub.transcription import TranscriptionQueue, _reset_db


FAKEVIDEO_QUICKXOR = '6608c31aca60873490a10c6f0900000000000000'


@pytest.fixture
def mvp_case(tmp_path, monkeypatch):
    with ExitStack() as stack:
        def make(*, duration=602, reset=True, runner=None, source_proven=True):
            cfg = worker.Config(tmp_path, tmp_path / 'hub.sqlite3',
                                tmp_path / 'whisper-cli', tmp_path / 'model.bin')
            cfg.binary.write_bytes(b'synthetic executable')
            cfg.binary.chmod(0o755)
            cfg.model.write_bytes(b'synthetic weights')
            monkeypatch.setattr(worker, 'MODEL_SHA256', worker.file_identity(cfg.model))
            monkeypatch.setattr(worker.shutil, 'disk_usage', lambda _: SimpleNamespace(free=20 * 1024**3))
            store = FOStore(cfg.db)
            stack.callback(store.conn.close)
            lesson_id = lesson_id_for('portal', 'video', None)
            store.sync_lessons([{'course_id': 'portal', 'media_id': 'video', 'subject': 'Biologia',
                                 'title': 'Aula de biologia', 'media_type': 'video', 'duration_s': duration}])
            with store.conn:
                store.conn.execute('''CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY,
                    remote_path TEXT, revision TEXT, size INTEGER, available INTEGER, checked_at TEXT)''')
                store.conn.execute('INSERT INTO lesson_video_sources VALUES (?,?,?,?,?,?)',
                                   (lesson_id, 'onedrive:Federal Online/a.mp4', '1', 9, 1, 'now'))
                if source_proven:
                    store.conn.execute('''CREATE TABLE lesson_source_observations(lesson_id TEXT,
                        remote_path TEXT, metadata TEXT, version INTEGER, checked_at TEXT,
                        PRIMARY KEY(lesson_id,remote_path))''')
                    store.conn.execute('INSERT INTO lesson_source_observations VALUES(?,?,?,?,?)',
                                       (lesson_id, 'onedrive:Federal Online/a.mp4',
                                        json.dumps({'Size': 9, 'QuickXorHash': FAKEVIDEO_QUICKXOR}), 1, 'now'))
            if reset:
                assert _reset_db(cfg.db, cfg.state, apply=True)['applied'] is True
            queue = TranscriptionQueue(store)
            runtime = None
            if runner is not None:
                fd = stack.enter_context(worker.leader_lock(tmp_path))
                runtime = worker.Worker(cfg, queue, fd, runner=runner, check_auth=lambda _: True)
            return SimpleNamespace(store=store, cfg=cfg, lesson_id=lesson_id, queue=queue, worker=runtime,
                                   source_quickxor=FAKEVIDEO_QUICKXOR)
        yield make

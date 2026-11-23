import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fo_hub import transcription as tr  # noqa: E402
from fo_hub.store import FOStore, TranscriptRejected, lesson_id_for  # noqa: E402


LID = lesson_id_for('C', 'M1', None)


@pytest.fixture
def store(tmp_path):
    s = FOStore(tmp_path / 'fo.db')
    s.sync_lessons([{'course_id': 'C', 'media_id': 'M1', 'title': 'A', 'media_type': 'video',
                     'duration_s': 60}])
    s.conn.execute('CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY, revision TEXT, '
                   'remote_path TEXT, size INTEGER, available INTEGER)')
    with s.conn:
        s.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?)',
                       (LID, '1', 'onedrive:Federal Online/file.mp4', 550, 1))
    return s


def test_enqueue_dedup_by_lesson_and_version(store):
    q = tr.TranscriptionQueue(store)
    assert q.enqueue(LID, 1) is True
    assert q.enqueue(LID, 1) is False
    assert q.counts() == {'queued': 1}


def test_lease_progress_fail_retry_and_dead(store, monkeypatch):
    now = 1000
    monkeypatch.setattr(tr.time, 'time', lambda: now)
    q = tr.TranscriptionQueue(store, max_attempts=2)
    assert q.lease('w1', lesson_id='other') is None
    assert q.lease('w1', max_source_bytes=549) is None
    job = q.lease('w1', lesson_id=LID, max_source_bytes=550)
    assert job['lesson_id'] == LID and job['attempts'] == 0
    assert q.lease('w2') is None
    q.progress(job, 'w1', .5)
    q.progress(job, 'w1', .25)
    assert store.conn.execute('SELECT progress FROM transcription_jobs').fetchone()[0] == .5
    assert q.fail(job, 'w1', 'temporary') == 'queued'
    assert q.lease('w1') is None
    now += 61
    job = q.lease('w1')
    assert job['attempts'] == 1
    assert q.fail(job, 'w1', 'permanent') == 'failed'
    assert q.counts() == {'failed': 1}
    assert q.retry(LID)
    assert q.lease('w1')['attempts'] == 0


def test_expired_or_recovered_lease_cannot_publish_even_for_same_owner(store, monkeypatch):
    now = 1000
    monkeypatch.setattr(tr.time, 'time', lambda: now)
    q = tr.TranscriptionQueue(store)
    first = q.lease('same')
    now = first['lease_until']
    with pytest.raises(tr.LeaseLost):
        q.progress(first, 'same', .5)
    second = q.lease('same')
    assert first['lease_token'] != second['lease_token']
    assert second['attempts'] == 0
    with pytest.raises(tr.LeaseLost):
        q.finish(first, 'same', [{'start': 0, 'end': 1, 'text': 'a'}], {'passed': True}, first)
    assert q.recover() == 1
    third = q.lease('same')
    assert third['lease_token'] != second['lease_token']
    with pytest.raises(tr.LeaseLost):
        q.fail(second, 'same', 'was interrupted')
    with pytest.raises(TranscriptRejected):
        q.finish(third, 'same', [{'start': 0, 'end': 1, 'text': 'a'}], {'passed': False}, third)
    assert store.get_transcript(LID) is None

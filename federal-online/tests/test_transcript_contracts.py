import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.store import FOStore, TranscriptRejected


def populated(tmp_path):
    store = FOStore(tmp_path / 'hub.sqlite3')
    store.sync_lessons([{'course_id': 'c', 'media_id': 'm', 'title': 'Lesson'}])
    lid = store.list_lessons()[0]['lesson_id']
    store.add_transcript(lid, 1, [{'start': 0, 'end': 1, 'text': 'approved'}],
                         model='private/model', corpus='generated_v2', validated=True,
                         qa={'passed': True})
    return store, lid


def test_serving_blocks_missing_source_and_explicit_failed_qa(tmp_path):
    store, lid = populated(tmp_path)
    store.conn.execute('CREATE TABLE lesson_video_sources(lesson_id TEXT, revision TEXT, available INTEGER, remote_path TEXT)')
    store.conn.commit()
    assert store.get_transcript(lid) is None
    assert store.search_transcripts('approved') == []
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?)', (lid, '1', 1, 'remote:a.mp4'))
    store.conn.commit()
    assert store.get_transcript(lid)
    with pytest.raises(TranscriptRejected):
        store.add_transcript(lid, 1, [], model='m', corpus='generated_v2', validated=True, qa={'passed': False})
    store.conn.execute('UPDATE lessons SET present=0')
    store.conn.commit()
    assert store.get_transcript(lid) is None
    assert store.sync_status()['transcripts_validated'] == 0


def test_readonly_status_normalizes_without_changing_legacy_states(tmp_path):
    store, lid = populated(tmp_path)
    for version, state in enumerate(['leased', 'done', 'stale', 'review', 'failed', 'queued'], 1):
        store.conn.execute('INSERT INTO transcription_jobs(lesson_id,version,state,lease_until,progress) VALUES(?,?,?,?,?)',
                           (lid, version, state, 1 if state == 'leased' else None, .5))
    store.conn.commit()
    readonly = FOStore(store.path, readonly=True)
    status = readonly.sync_status()
    assert status['transcription_jobs']['leased'] == 1
    assert status['transcription_states'] == {'queued': 1, 'processing': 1, 'validated': 1, 'review': 1, 'failed': 1, 'superseded': 1}
    assert status['transcription_progress']['stale_leases'] == 1
    assert status['transcription_progress']['processing_progress'] == .5
    assert readonly.conn.execute('SELECT state FROM transcription_jobs WHERE version=1').fetchone()[0] == 'leased'

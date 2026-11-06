"""Citations are required on every searchable validated segment."""
from fo_hub.store import FOStore


def test_transcript_search_and_get_include_versioned_timestamp_citations(tmp_path):
    store = FOStore(tmp_path / 'hub.db')
    store.sync_lessons([{'course_id': 'course', 'media_id': 'media', 'title': 'Vetores',
                         'subject': 'Física', 'source_url': 'https://source.invalid/course'}])
    lid = store.list_lessons()[0]['lesson_id']
    store.add_transcript(lid, 1, [{'start': 1.25, 'end': 4.5, 'text': 'Vetor e direção.'}],
                         'model', 'generated_v2', True, {'passed': True})
    search = store.search_transcripts('Vetor')[0]
    assert search['citation'] == {'id': lid, 'name': 'Vetores', 'version': 1,
                                   'segment': 0, 'start_s': 1.25, 'end_s': 4.5}
    transcript = store.get_transcript(lid)
    assert transcript is not None
    assert transcript['segments'][0]['citation'] == search['citation']
    assert transcript['citation']['id'] == lid
    assert transcript['citation']['version'] == 1
    assert 'source_remote_path' not in str(transcript)
    store.conn.execute('UPDATE lessons SET version=2')
    store.conn.commit()
    assert store.search_transcripts('Vetor') == []
    assert store.get_transcript(lid) is None

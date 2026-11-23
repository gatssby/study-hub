"""Inventory, revision, lease and worker agree on OneDrive byte identity."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from fo_hub.ingest import ingest
from fo_hub.onedrive import sync
from fo_hub.store import FOStore, TranscriptRejected
from fo_hub.transcription import LeaseLost, TranscriptionQueue


QUICKXOR = '6608c31aca60873490a10c6f0900000000000000'  # b'fakevideo' from rclone
REPLACEMENT = '72284318d860873490a10c6f0900000000000000'  # b'realvideo'
REMOTE = 'onedrive:Federal Online/Course/Aula.mp4'


def test_inventory_persists_only_normalized_provider_quickxor(tmp_path):
    def runner(args, **kwargs):
        if args[1] == 'lsjson':
            assert '--hash' in args and args[args.index('--hash-type') + 1] == 'QuickXorHash'
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps([
                {'Path': 'Course/Aula.mp4', 'Size': 9, 'Hashes': {'quickxor': QUICKXOR.upper(), 'sha1': 'ignored'}},
                {'Path': 'Course/Outra.mp4', 'Size': 9, 'Hashes': {'quickxor': 'malformed'}},
                {'Path': 'Course/Arquivo.pdf', 'Size': 9, 'Hashes': {'quickxor': QUICKXOR}},
            ]))
        return subprocess.CompletedProcess(args, 0, stdout=(tmp_path / 'onedrive-status.json').read_text())

    status = sync(tmp_path, runner=runner)
    rows = json.loads((tmp_path / 'remote-videos.json').read_text())
    assert [row['QuickXorHash'] for row in rows] == [QUICKXOR, None]
    assert all('Hashes' not in row for row in rows)
    assert status['remote_videos_without_quickxor'] == 1


@pytest.fixture
def inventory(tmp_path):
    db = tmp_path / 'hub.sqlite3'
    source = {'Path': 'Course/Aula.mp4', 'Size': 9, 'ID': 'fixed', 'ModTime': '2026-01-01T00:00:00Z'}

    def refresh():
        (tmp_path / 'remote-videos.json').write_text(json.dumps([source]))
        return ingest(tmp_path, db, index_pdfs=False)

    return source, db, refresh


def test_same_metadata_new_hash_revokes_lease_and_hides_old_transcript(inventory):
    source, db, refresh = inventory
    source['QuickXorHash'] = QUICKXOR
    refresh()
    store = FOStore(db)
    lid = store.list_lessons()[0]['lesson_id']
    queue = TranscriptionQueue(store)
    first = queue.lease('fixture')
    queue.finish(first, 'fixture', [{'start': 0, 'end': 1, 'text': 'old'}], {'passed': True}, first)
    assert store.get_transcript(lid) is not None

    source['QuickXorHash'] = REPLACEMENT
    refresh()
    refresh()
    assert store.get_lesson(lid)['version'] == 2
    assert store.get_transcript(lid) is None
    second = queue.lease('fixture')
    assert (second['version'], second['remote_path'], second['size']) == (2, REMOTE, 9)

    source['QuickXorHash'] = QUICKXOR
    refresh()
    with pytest.raises(LeaseLost):
        queue.check_source(second, 'fixture')
    assert queue.lease('fixture')['version'] == 3
    assert [tuple(row) for row in store.conn.execute('SELECT version,state FROM transcription_jobs ORDER BY version')] == [
        (1, 'done'), (2, 'superseded'), (3, 'leased')]


def test_first_hashed_inventory_migrates_legacy_mapping_once(inventory):
    source, db, refresh = inventory
    refresh()
    store = FOStore(db)
    lid = store.list_lessons()[0]['lesson_id']
    store.add_transcript(lid, 1, [{'start': 0, 'end': 1, 'text': 'legacy'}], model='fixture',
                         corpus='generated_v2', validated=True)
    assert store.get_transcript(lid) is not None
    source['QuickXorHash'] = QUICKXOR
    refresh()
    refresh()
    assert store.get_lesson(lid)['version'] == 2
    assert store.get_transcript(lid) is None
    assert store.conn.execute('SELECT count(*) FROM transcripts').fetchone()[0] == 1
    assert TranscriptionQueue(store).lease('fixture')['version'] == 2


def test_ingest_accepts_native_rclone_hashes_from_staged_inventory(inventory):
    source, db, refresh = inventory
    source['Hashes'] = {'quickxor': QUICKXOR}
    refresh()
    store = FOStore(db)
    metadata, = store.conn.execute('SELECT metadata FROM lesson_source_observations').fetchone()
    assert json.loads(metadata)['QuickXorHash'] == QUICKXOR


def test_hashless_snapshot_never_erases_prior_proof_or_leases_unverified_bytes(inventory):
    source, db, refresh = inventory
    source['QuickXorHash'] = None
    refresh()
    store = FOStore(db)
    queue = TranscriptionQueue(store)
    assert queue.lease('fixture') is None

    source['QuickXorHash'] = QUICKXOR
    refresh()
    assert store.list_lessons()[0]['version'] == 1
    first = queue.lease('fixture')
    source['QuickXorHash'] = 'malformed'
    refresh()
    assert queue.lease('fixture') is None
    with pytest.raises(TranscriptRejected, match='source changed'):
        queue.check_source(first, 'fixture')
    with pytest.raises(TranscriptRejected, match='source changed before publication'):
        queue.finish(first, 'fixture', [{'start': 0, 'end': 1, 'text': 'blocked'}], {'passed': True}, first)

    source['QuickXorHash'] = REPLACEMENT
    refresh()
    second = queue.lease('fixture')
    assert second['version'] == 2


@pytest.mark.skipif(not shutil.which('rclone'), reason='requires local rclone')
@pytest.mark.parametrize('content,expected', [(b'fakevideo', 'source_audio_probe_failed'),
                                               (b'realvideo', 'source_download_hash_mismatch')])
def test_leased_download_checks_actual_local_quickxor(mvp_case, content, expected):
    def runner(args, **kwargs):
        if args[:2] == ['rclone', 'copyto']:
            Path(args[3]).write_bytes(content)
            return subprocess.CompletedProcess(args, 0, stdout='', stderr='')
        if args[:2] == ['rclone', 'hashsum']:
            assert args[-2:] == ['--config', '/dev/null']
            return subprocess.run(args, **kwargs)
        assert args[0] == 'ffprobe' and content == b'fakevideo', 'unverified bytes reached media tools'
        return subprocess.CompletedProcess(args, 0, stdout='{}', stderr='')

    case = mvp_case(runner=runner)
    result = case.worker.run_once()
    assert result['reason'] == expected
    assert result['state'] == ('queued' if content == b'realvideo' else 'review')
    if content == b'realvideo':
        assert case.store.conn.execute('SELECT attempts FROM transcription_jobs').fetchone()[0] == 0


@pytest.mark.parametrize('invalid_proof', ['absent', 'stale_revision', 'different_size', 'different_path'])
def test_worker_never_downloads_without_matching_source_proof(mvp_case, invalid_proof):
    def runner(*args, **kwargs):
        pytest.fail('unbound evidence must not authorize a download')

    case = mvp_case(runner=runner, source_proven=invalid_proof != 'absent')
    if invalid_proof != 'absent':
        with case.store.conn:
            case.store.conn.execute({
                'stale_revision': 'UPDATE lesson_source_observations SET version=2',
                'different_size': 'UPDATE lesson_source_observations SET metadata=?',
                'different_path': "UPDATE lesson_source_observations SET remote_path='onedrive:Federal Online/b.mp4'",
            }[invalid_proof], (json.dumps({'Size': 10, 'QuickXorHash': QUICKXOR}),)
              if invalid_proof == 'different_size' else ())
    result = case.worker.run_once()
    assert result['reason'] == 'source_hash_unavailable'
    assert case.store.conn.execute('SELECT attempts FROM transcription_jobs').fetchone()[0] == 0

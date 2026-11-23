import sys
import json
import subprocess
import shutil
import fcntl
import pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def test_onedrive_ignores_existing_transcript_mirror_inputs(tmp_path, monkeypatch):
    from fo_hub.store import FOStore
    from fo_hub.onedrive import sync

    # A transcript and legacy JSON which the old mirror would have copied.
    store = FOStore(tmp_path/'hub.sqlite3')
    monkeypatch.setenv('STUDY_HUB_FO_DB', str(store.path))
    store.sync_lessons([{'course_id': 'c', 'media_id': 'm', 'title': 'Lesson'}])
    lid = store.list_lessons()[0]['lesson_id']
    segments = [{'start': 0, 'end': 1, 'text': 'approved'}]
    store.add_transcript(lid, 1, segments, model='m', corpus='generated_v2', validated=True, qa={'passed': True})
    path = tmp_path/'transcripts/generated_v2'/lid/'v1.json'
    path.parent.mkdir(parents=True)
    content = json.dumps({'lesson_id': lid, 'version': 1, 'corpus': 'generated_v2',
                          'qa': {'passed': True}, 'segments': segments})
    path.write_text(content)
    store.conn.close()
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        stdout = (tmp_path/'onedrive-status.json').read_text() if command[1] == 'cat' else '[]'
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    status = sync(tmp_path, runner=runner)
    assert [command[1] for command in calls] == ['lsjson', 'copyto', 'cat']
    assert all('Transcripts' not in str(command) for command in calls)
    assert status['remote_deletion_policy'] == 'never'
    assert 'transcript_sync' not in status and 'transcript_files' not in status
    assert path.read_text() == content


def test_inventory_proof_binds_listing_start_to_exact_snapshot(tmp_path, monkeypatch):
    import hashlib
    from fo_hub import onedrive
    clock = [1000]
    monkeypatch.setattr(onedrive.time, 'time', lambda: clock[0])
    def runner(command, **kwargs):
        if command[1] == 'lsjson':
            assert '--onedrive-delta' in command
            clock[0] = 2000  # completion must not become the capture start
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps([
                {'Path': 'Course/Áula.mp4', 'Size': 42, 'ID': 'object', 'ModTime': 'now'},
                {'Path': 'ignored.txt', 'Size': 1}]))
        return subprocess.CompletedProcess(command, 0, stdout=(tmp_path/'onedrive-status.json').read_text() if command[1] == 'cat' else '')
    result = onedrive.sync(tmp_path, runner=runner)
    assert result['inventory_started_at'] == 1000
    assert result['inventory_sha256'] == hashlib.sha256((tmp_path/'remote-videos.json').read_bytes()).hexdigest()
    assert result['remote_videos'] == 1
    assert json.loads((tmp_path/'onedrive-status.json').read_text()) == result


def test_reset_inventory_lists_only_and_creates_private_file(tmp_path, monkeypatch):
    from fo_hub import onedrive
    artifact = tmp_path / 'inventory.json'
    inventory = {'started_at': 100, 'finished_at': 101, 'rows': [
        {'Path': 'course/video.mp4', 'Size': 12, 'Hashes': {'quickxor': 'a'*40}}]}
    monkeypatch.setattr(onedrive, 'video_inventory', lambda: inventory)
    monkeypatch.setattr(sys, 'argv', ['fo_hub.onedrive', '--reset-inventory', str(artifact)])
    onedrive.main()
    assert artifact.stat().st_mode & 0o777 == 0o600
    assert json.loads(artifact.read_text()) == inventory
    with pytest.raises(SystemExit):
        onedrive.main()


def test_onedrive_never_deletes_remote_or_uploads_credentials(tmp_path):
    from fo_hub.onedrive import sync
    calls=[]
    class Result:
        stdout='[]'
    def runner(command,**kwargs):
        calls.append(command)
        result=Result()
        if 'cat' in command:result.stdout=(tmp_path/'onedrive-status.json').read_text()
        return result
    (tmp_path/'materials').mkdir()
    result=sync(tmp_path,runner=runner)
    assert result['pdf_sync']=='verified'
    assert all('sync' not in c and 'delete' not in c and 'purge' not in c for c in calls)
    assert any('check' in c and '--download' in c for c in calls)


def test_failed_check_records_failed_phase_and_exit_code(tmp_path):
    from fo_hub.onedrive import sync
    (tmp_path/'materials').mkdir()
    def runner(command,**kwargs):
        if command[1]=='check':
            raise subprocess.CalledProcessError(1,command,stderr='private provider failure')
        return subprocess.CompletedProcess(command,0,stdout='[]')
    with pytest.raises(subprocess.CalledProcessError):sync(tmp_path,runner=runner)
    status=json.loads((tmp_path/'onedrive-status.json').read_text())
    assert status['pdf_sync']=='failed'
    assert status['error_phase']=='pdf_check'
    assert status['exit_code']==1
    assert 'private provider failure' not in json.dumps(status)


def test_metadata_failure_is_recorded_and_diagnostic_log_redacts_secrets(tmp_path):
    from fo_hub.onedrive import sync
    def runner(command,**kwargs):
        if command[1]=='copyto':
            raise subprocess.CalledProcessError(5,command,stderr='429 Too Many Requests https://provider/private?token=abc Authorization: Bearer hidden_token')
        return subprocess.CompletedProcess(command,0,stdout='[]')
    with pytest.raises(subprocess.CalledProcessError):sync(tmp_path,runner=runner)
    status=json.loads((tmp_path/'onedrive-status.json').read_text())
    assert status['error_phase']=='metadata_copy'
    assert status['metadata_sync']=='failed'
    assert status['exit_code']==5
    log=(tmp_path/'logs/onedrive-error.log').read_text()
    assert '429 Too Many Requests' in log
    assert 'hidden_token' not in log and 'https://' not in log


@pytest.mark.skipif(not shutil.which('rclone'),reason='rclone CLI required for local filesystem integration')
def test_real_rclone_ignores_unpublished_builds_and_holds_publication_lock(tmp_path):
    from fo_hub.onedrive import sync
    source=tmp_path/'materials';source.mkdir()
    (source/'published.pdf').write_bytes(b'%PDF-published')
    staging=source/'.build_course/subject';staging.mkdir(parents=True)
    (staging/'unpublished.pdf').write_bytes(b'%PDF-incomplete')
    remote=tmp_path/'remote';remote.mkdir()
    locked=[]
    def runner(command,**kwargs):
        if command[1] in ('copy','check'):
            lock=tmp_path/'locks/materials-publication.lock';lock.parent.mkdir(exist_ok=True)
            with lock.open('a+') as handle:
                try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:locked.append(True)
                else:locked.append(False)
            actual=[str(remote) if x=='onedrive:Federal Online PDFs' else x for x in command]
            return subprocess.run(actual,**kwargs)
        return subprocess.CompletedProcess(command,0,stdout=(tmp_path/'onedrive-status.json').read_text() if command[1]=='cat' else '[]')
    sync(tmp_path,runner=runner)
    assert (remote/'published.pdf').read_bytes()==b'%PDF-published'
    assert not list(remote.rglob('unpublished.pdf'))
    assert locked==[True,True]

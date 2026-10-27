import sys
import json
import subprocess
import shutil
import fcntl
import pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def test_transcript_sync_allowlists_only_current_public_artifacts_under_lock(tmp_path, monkeypatch):
    from fo_hub.store import FOStore
    from fo_hub.onedrive import sync
    store = FOStore(tmp_path/'hub.sqlite3')
    monkeypatch.setenv('STUDY_HUB_FO_DB', str(store.path))
    store.sync_lessons([{'course_id': 'c', 'media_id': 'm', 'title': 'Lesson'}])
    lid = store.list_lessons()[0]['lesson_id']
    segments = [{'start': 0, 'end': 1, 'text': 'approved'}]
    store.add_transcript(lid, 1, segments, model='m', corpus='generated_v2', validated=True, qa={'passed': True})
    root = tmp_path/'transcripts/generated_v2'
    path = root/lid/'v1.json';path.parent.mkdir(parents=True)
    public = {'lesson_id': lid, 'version': 1, 'corpus': 'generated_v2', 'qa': {'passed': True}, 'segments': segments}
    path.write_text(json.dumps(public))
    (path.parent/'v0.json').write_text(json.dumps({**public, 'version': 0}))
    (path.parent/'v1.json.tmp').write_text('private')
    raw = root/'raw'/lid/'v1.json';raw.parent.mkdir(parents=True);raw.write_text(json.dumps(public))
    seen = []
    def runner(command, **kwargs):
        if command[1] in ('copy', 'check'):
            assert '--files-from' in command
            assert Path(command[command.index('--files-from')+1]).read_text().splitlines() == [f'{lid}/v1.json']
            with (tmp_path/'locks/transcript-publication.lock').open('a+') as lock:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            seen.append(command[1])
        return subprocess.CompletedProcess(command, 0, stdout=(tmp_path/'onedrive-status.json').read_text() if command[1]=='cat' else '[]')
    assert sync(tmp_path, runner=runner)['transcript_sync'] == 'verified'
    assert seen == ['copy', 'check']
    # Provenance or mismatched text in an otherwise valid-looking file fails closed.
    for mutation in ({'source_url': 'https://private?token=signed'}, {'segments': [{'start': 0, 'end': 1, 'text': 'unapproved'}]}, {'qa': {'passed': False}}):
        path.write_text(json.dumps({**public, **mutation}))
        seen.clear()
        assert sync(tmp_path, runner=runner)['transcript_sync'] == 'not_generated'
        assert not seen


@pytest.mark.parametrize('change', ['missing', 'version', 'corpus', 'qa', 'symlink', 'bad_json', 'numeric_qa', 'unavailable', 'source_revision'])
def test_transcript_allowlist_fails_closed(tmp_path, monkeypatch, change):
    from fo_hub.onedrive import _transcript_allowlist
    from fo_hub.store import FOStore
    store = FOStore(tmp_path/'hub.sqlite3')
    monkeypatch.setenv('STUDY_HUB_FO_DB', str(store.path))
    store.sync_lessons([{'course_id': 'c', 'media_id': 'm'}])
    lid = store.list_lessons()[0]['lesson_id']
    segments = [{'start': 0, 'end': 1, 'text': 'approved'}]
    store.add_transcript(lid, 1, segments, model='m', corpus='generated_v2', validated=True)
    root = tmp_path/'transcripts/generated_v2'
    path = root/lid/'v1.json';path.parent.mkdir(parents=True)
    public = {'lesson_id': lid, 'version': 1, 'corpus': 'generated_v2', 'qa': {'passed': True}, 'segments': segments}
    path.write_text(json.dumps(public))
    if change == 'missing':store.conn.execute('UPDATE lessons SET present=0')
    elif change == 'version':store.conn.execute('UPDATE lessons SET version=2')
    elif change == 'corpus':store.conn.execute("UPDATE transcripts SET corpus='legacy'")
    elif change == 'qa':store.conn.execute("UPDATE transcripts SET qa_json='{}'")
    elif change == 'symlink':
        target = tmp_path/'private.json';target.write_text(json.dumps(public))
        linked = root/lid/'v2.json';linked.symlink_to(target)
        store.conn.execute('UPDATE lessons SET version=2')
        store.conn.execute('UPDATE transcripts SET version=2')
    elif change == 'bad_json':path.write_text('{')
    elif change == 'numeric_qa':path.write_text(json.dumps({**public, 'qa': {'passed': 1}}))
    else:
        store.conn.execute('CREATE TABLE lesson_video_sources(lesson_id TEXT,revision TEXT,available INTEGER,remote_path TEXT)')
        store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?)', (lid, '2' if change == 'source_revision' else '1', 0 if change == 'unavailable' else 1, 'remote:a'))
    store.conn.commit()
    assert _transcript_allowlist(tmp_path, root) == []


def test_inventory_proof_binds_listing_start_to_exact_snapshot(tmp_path, monkeypatch):
    import hashlib
    from fo_hub import onedrive
    clock = [1000]
    monkeypatch.setattr(onedrive.time, 'time', lambda: clock[0])
    def runner(command, **kwargs):
        if command[1] == 'lsjson':
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

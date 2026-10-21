import sys
import json
import subprocess
import shutil
import fcntl
import pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


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

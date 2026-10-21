import sys
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

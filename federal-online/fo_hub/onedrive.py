"""Non-destructive OneDrive copy + byte verification, and source reconciliation."""
import argparse
from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import subprocess
import time


QUICKXOR_TYPE = 'QuickXorHash'
VIDEO_SUFFIXES = {'.mp4', '.mkv', '.mov', '.webm', '.m4v'}


def normalize_quickxor(value):
    return value.lower() if isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{40}', value) else None


def rclone_quickxor(hashes):
    # rclone's JSON key is the short name, not --hash-type's display name.
    return normalize_quickxor(hashes.get('quickxor') if isinstance(hashes, dict) else None)


def video_inventory(runner=subprocess.run):
    started = time.time()
    result = runner(['rclone', 'lsjson', 'onedrive:Federal Online', '--recursive', '--files-only', '--onedrive-delta',
                     '--hash', '--hash-type', QUICKXOR_TYPE, '--retries', '1', '--low-level-retries', '2'],
                    check=True, capture_output=True, text=True, timeout=300)
    finished = time.time()
    rows = [{key: item.get(key) for key in ('Path', 'Size', 'ModTime', 'ID', 'Hashes')}
            for item in json.loads(result.stdout) if Path(item['Path']).suffix.lower() in VIDEO_SUFFIXES]
    return {'started_at': started, 'finished_at': finished, 'rows': rows}


def _save_status(state,status):
    temporary=state/'onedrive-status.json.tmp'
    temporary.write_text(json.dumps(status,indent=2))
    os.replace(temporary,state/'onedrive-status.json')


def _record_failure(state,status,phase,exc):
    status.update(error_type=type(exc).__name__,error_phase=phase)
    if phase.startswith('pdf_'):status['pdf_sync']='failed'
    if phase.startswith('metadata_'):status['metadata_sync']='failed'
    if isinstance(exc,subprocess.CalledProcessError):
        status['exit_code']=exc.returncode
        detail=exc.stderr or ''
        if isinstance(detail,bytes):detail=detail.decode(errors='replace')
        detail=re.sub(r'https?://\S+','<url redacted>',detail)
        detail=re.sub(r'(?i)\bbearer\s+\S+','Bearer <redacted>',detail)
        detail=re.sub(r'(?i)(access_token|refresh_token|password|secret)\s*[=:]\s*\S+',r'\1=<redacted>',detail)
        log=state/'logs/onedrive-error.log';log.parent.mkdir(parents=True,exist_ok=True)
        with os.fdopen(os.open(log,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600),'w') as handle:
            handle.write(f'{phase}: exit {exc.returncode}\n{detail[-8000:]}')
    _save_status(state,status)


def sync(state,runner=subprocess.run):
    state=Path(state)
    status={'updated_at':time.time(),'TRANSCRIPTION_ENABLED':False,'pdf_sync':'absent'}
    phase='initializing'
    try:
        source=state/'materials'
        filters=['--filter','- /.build_*/**','--filter','+ *.pdf','--filter','- **']
        if source.is_dir():
            lock=state/'locks/materials-publication.lock';lock.parent.mkdir(parents=True,exist_ok=True)
            with lock.open('a+') as handle:
                # Downloads may continue in staging; only publication waits.
                fcntl.flock(handle,fcntl.LOCK_SH)
                phase='pdf_copy'
                runner(['rclone','copy',str(source),'onedrive:Federal Online PDFs',*filters,'--retries','3','--transfers','1'],check=True,capture_output=True,text=True,timeout=7200)
                phase='pdf_check'
                runner(['rclone','check',str(source),'onedrive:Federal Online PDFs',*filters,'--one-way','--download','--retries','3','--checkers','2'],check=True,capture_output=True,text=True,timeout=7200)
            status['pdf_sync']='verified'
        phase='video_inventory'
        inventory=video_inventory(runner)
        videos=[]
        for item in inventory['rows']:
            row={key:item.get(key) for key in ('Path','Size','ModTime','ID')}
            row[QUICKXOR_TYPE]=rclone_quickxor(item.get('Hashes'))
            videos.append(row)
        snapshot=json.dumps(videos,ensure_ascii=False).encode('utf-8')
        temporary=state/'remote-videos.json.tmp';temporary.write_bytes(snapshot);os.replace(temporary,state/'remote-videos.json')
        status['inventory_started_at']=inventory['started_at']
        status['inventory_sha256']=hashlib.sha256(snapshot).hexdigest()
        status['remote_videos']=len(videos)
        status['remote_videos_without_quickxor']=sum(x[QUICKXOR_TYPE] is None for x in videos)
        status['remote_video_bytes']=sum(x['Size'] for x in videos)
        status['remote_deletion_policy']='never'
    except Exception as exc:
        _record_failure(state,status,phase,exc)
        raise
    _save_status(state,status)
    try:
        phase='metadata_copy'
        runner(['rclone','copyto',str(state/'onedrive-status.json'),'onedrive:Study Hub/Federal Online/metadata/sync-status.json','--retries','3'],check=True,capture_output=True,text=True,timeout=300)
        phase='metadata_readback'
        result=runner(['rclone','cat','onedrive:Study Hub/Federal Online/metadata/sync-status.json'],check=True,capture_output=True,text=True,timeout=120)
        if json.loads(result.stdout)!=status:
            raise RuntimeError('OneDrive status read-back mismatch')
    except Exception as exc:
        _record_failure(state,status,phase,exc)
        raise
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset-inventory', type=Path, help='Write an exclusive mode-0600 video inventory; no remote writes.')
    args = parser.parse_args()
    if args.reset_inventory:
        try:
            inventory = video_inventory()
            if not inventory['rows']:
                raise ValueError('empty inventory')
            with os.fdopen(os.open(args.reset_inventory, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
                json.dump(inventory, out, ensure_ascii=False)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            parser.exit(2, 'FO video inventory collection failed\n')
        print(json.dumps({'video_objects': len(inventory['rows']),
                          'hashed_objects': sum(bool(rclone_quickxor(r['Hashes'])) for r in inventory['rows'])}))
        return
    print(json.dumps(sync(Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online')))))


if __name__=='__main__':main()

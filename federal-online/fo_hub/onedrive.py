"""Non-destructive OneDrive copy + byte verification, and source reconciliation."""
from pathlib import Path
import fcntl
import json
import os
import re
import subprocess
import time
import tempfile

from .store import FOStore


def _transcript_allowlist(state, root):
    """Only minimal public JSON matching approved DB segments is eligible."""
    database = Path(os.environ.get('STUDY_HUB_FO_DB', str(state/'hub.sqlite3')))
    if not database.is_file() or root.is_symlink():
        return []
    store = FOStore(database, readonly=True)
    paths = []
    try:
        rows = store.conn.execute(f'SELECT t.lesson_id,t.version FROM transcripts t {store._CURRENT}').fetchall()
        for row in rows:
            lid, version = row['lesson_id'], row['version']
            if not re.fullmatch(r'[A-Za-z0-9_-]+', lid):
                continue
            relative = Path(lid)/f'v{version}.json'
            path = root/relative
            if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
                continue
            try:
                artifact = json.loads(path.read_text())
                if set(artifact) != {'lesson_id', 'version', 'corpus', 'qa', 'segments'}:
                    continue
                if (artifact['lesson_id'] != lid or type(artifact['version']) is not int
                        or artifact['version'] != version or artifact['corpus'] != 'generated_v2'
                        or artifact['qa'] != {'passed': True} or artifact['qa'].get('passed') is not True):
                    continue
                segments = artifact['segments']
                if not isinstance(segments, list) or not segments:
                    continue
                if any(not isinstance(s, dict) or set(s) != {'start', 'end', 'text'} for s in segments):
                    continue
                approved = store.get_transcript(lid)
                if approved is None or segments != [{k: s[k] for k in ('start', 'end', 'text')} for s in approved['segments']]:
                    continue
                paths.append(relative.as_posix())
            except (ValueError, TypeError, KeyError, OSError):
                continue
    finally:
        store.conn.close()
    return sorted(paths)


def _save_status(state,status):
    temporary=state/'onedrive-status.json.tmp'
    temporary.write_text(json.dumps(status,indent=2))
    os.replace(temporary,state/'onedrive-status.json')


def _record_failure(state,status,phase,exc):
    status.update(error_type=type(exc).__name__,error_phase=phase)
    if phase.startswith('pdf_'):status['pdf_sync']='failed'
    if phase.startswith('transcript_'):status['transcript_sync']='failed'
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
    status={'updated_at':time.time(),'TRANSCRIPTION_ENABLED':False,'pdf_sync':'absent','transcript_sync':'not_generated'}
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
        # New generated-v2 transcripts only. Old corpus is never an input.
        transcripts=state/'transcripts/generated_v2'
        if transcripts.is_dir():
            phase='transcript_selection'
            lock=state/'locks/transcript-publication.lock';lock.parent.mkdir(parents=True,exist_ok=True)
            with lock.open('a+') as handle:
                fcntl.flock(handle,fcntl.LOCK_SH)
                paths=_transcript_allowlist(state,transcripts)
                status['transcript_files']=len(paths)
                if paths:
                    with tempfile.NamedTemporaryFile(mode='w+',dir=lock.parent,prefix='transcript-files-',suffix='.txt') as allowlist:
                        allowlist.write('\n'.join(paths)+'\n');allowlist.flush()
                        selection=['--files-from',allowlist.name]
                        phase='transcript_copy'
                        runner(['rclone','copy',str(transcripts),'onedrive:Study Hub/Federal Online/Transcripts/generated_v2',*selection,'--retries','3','--transfers','1'],check=True,capture_output=True,text=True,timeout=7200)
                        phase='transcript_check'
                        runner(['rclone','check',str(transcripts),'onedrive:Study Hub/Federal Online/Transcripts/generated_v2',*selection,'--one-way','--download'],check=True,capture_output=True,text=True,timeout=7200)
                    status['transcript_sync']='verified'
        phase='video_inventory'
        result=runner(['rclone','lsjson','onedrive:Federal Online','--recursive','--files-only'],check=True,capture_output=True,text=True,timeout=300)
        videos=[{k:x.get(k) for k in ('Path','Size','ModTime','ID')} for x in json.loads(result.stdout) if Path(x['Path']).suffix.lower() in ('.mp4','.mkv','.mov','.webm','.m4v')]
        temporary=state/'remote-videos.json.tmp';temporary.write_text(json.dumps(videos,ensure_ascii=False));os.replace(temporary,state/'remote-videos.json')
        status['remote_videos']=len(videos)
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
    print(json.dumps(sync(Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online')))))


if __name__=='__main__':main()

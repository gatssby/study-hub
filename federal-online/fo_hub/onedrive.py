"""Non-destructive OneDrive copy + byte verification, and source reconciliation."""
from pathlib import Path
import json
import os
import subprocess
import time


def sync(state,runner=subprocess.run):
    state=Path(state)
    status={'updated_at':time.time(),'TRANSCRIPTION_ENABLED':False,'pdf_sync':'absent','transcript_sync':'not_generated'}
    try:
        source=state/'materials'
        filters=['--include','*.pdf','--exclude','*']
        if source.is_dir():
            runner(['rclone','copy',str(source),'onedrive:Federal Online PDFs',*filters,'--retries','3','--transfers','1'],check=True,capture_output=True,text=True,timeout=7200)
            runner(['rclone','check',str(source),'onedrive:Federal Online PDFs',*filters,'--one-way','--download','--retries','3'],check=True,capture_output=True,text=True,timeout=7200)
            status['pdf_sync']='verified'
        # New generated-v2 transcripts only. Old corpus is never an input.
        transcripts=state/'transcripts/generated_v2'
        if transcripts.exists():
            runner(['rclone','copy',str(transcripts),'onedrive:Study Hub/Federal Online/Transcripts/generated_v2','--retries','3','--transfers','1'],check=True,capture_output=True,text=True,timeout=7200)
            runner(['rclone','check',str(transcripts),'onedrive:Study Hub/Federal Online/Transcripts/generated_v2','--one-way','--download'],check=True,capture_output=True,text=True,timeout=7200)
            status['transcript_sync']='verified'
        result=runner(['rclone','lsjson','onedrive:Federal Online','--recursive','--files-only'],check=True,capture_output=True,text=True,timeout=300)
        videos=[{k:x.get(k) for k in ('Path','Size','ModTime','ID')} for x in json.loads(result.stdout) if Path(x['Path']).suffix.lower() in ('.mp4','.mkv','.mov','.webm','.m4v')]
        temporary=state/'remote-videos.json.tmp';temporary.write_text(json.dumps(videos,ensure_ascii=False));os.replace(temporary,state/'remote-videos.json')
        status['remote_videos']=len(videos)
        status['remote_video_bytes']=sum(x['Size'] for x in videos)
        status['remote_deletion_policy']='never'
    except Exception as exc:
        status['error_type']=type(exc).__name__
        (state/'onedrive-status.json').write_text(json.dumps(status,indent=2))
        raise
    (state/'onedrive-status.json').write_text(json.dumps(status,indent=2))
    runner(['rclone','copyto',str(state/'onedrive-status.json'),'onedrive:Study Hub/Federal Online/metadata/sync-status.json','--retries','3'],check=True,capture_output=True,text=True,timeout=300)
    # Read-back exact target after write.
    result=runner(['rclone','cat','onedrive:Study Hub/Federal Online/metadata/sync-status.json'],check=True,capture_output=True,text=True,timeout=120)
    if json.loads(result.stdout)!=status:
        raise RuntimeError('OneDrive status read-back mismatch')
    return status


def main():
    print(json.dumps(sync(Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online')))))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Sequential persistent video sync. Never invokes transcription or deletes remote data."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import hashlib
import json
import os
import shutil
import subprocess
import time

import fo_download_upload_videos as core

STATE = Path(os.environ.get('FO_STATE_ROOT', '/home/ubuntu/study-hub-state/federal-online'))
RESERVE = 4 * 1024**3


def canonical_url(url):
    p = urlsplit(url or '')
    return urlunsplit((p.scheme, p.netloc, p.path, '', ''))


def identity(row):
    key = row.get('media_id') or row.get('item_id')
    if not key:
        raise ValueError('Lesson without stable media/item ID; needs review')
    return hashlib.sha256((canonical_url(row.get('course_url', ''))+'|'+str(key)).encode()).hexdigest()[:24]


def revision(row):
    values = [canonical_url(row.get('video_stream_url', '')),row.get('duracao_segundos')]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()[:16]


def allowed_bytes(free, reserve=RESERVE):
    if free <= reserve:
        raise RuntimeError('Storage reserve reached; video sync paused')
    return free - reserve


def verify_upload(local, remote, runner=subprocess.run):
    parent, filename = remote.rsplit('/', 1)
    # --download compares bytes, not merely size when OneDrive hashes differ.
    listing = local.parent / '.verify-files'
    listing.write_text(filename+'\n')
    try:
        runner(['rclone','check',str(local.parent),parent,'--files-from-raw',str(listing),'--one-way','--download','--retries','3'],check=True,capture_output=True,text=True,timeout=7200)
    finally:
        listing.unlink(missing_ok=True)


def atomic_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    os.replace(tmp,path)


def discard_recoverable_partial(tmp_dir: Path, key: str, logger: core.Logger) -> int:
    """Remove only this job's unvalidated partial; unknown jobs stay untouched."""
    removed = 0
    for partial in tmp_dir.glob(f"{key}-*.partial.mp4"):
        try:
            partial.unlink()
            removed += 1
            logger.log(f"[recovery] partial nao validado removido para nova tentativa key={key}")
        except OSError as exc:
            logger.log(f"[recovery] partial preservado key={key} erro={type(exc).__name__}")
    return removed


def rows_from_catalog():
    paths = sorted((STATE/'catalog').rglob('aulas_index*.json'))
    paths += sorted((STATE/'catalogs').rglob('aulas_index*.json'))
    by_id = {}
    for path in paths:
        data=json.loads(path.read_text())
        for row in data.get('aulas',[]):
            if row.get('status')!='ok' or not row.get('video_stream_url'):continue
            row=dict(row,course_url=row.get('course_url') or data.get('course_url',''))
            try:key=identity(row)
            except ValueError:continue
            # Newer observed metadata takes precedence, never remove unseen rows.
            if key not in by_id or str(row.get('captured_at','')) >= str(by_id[key].get('captured_at','')): by_id[key]=row
    return list(by_id.values())


def main():
    if not Path('/home/ubuntu/anki-vnext').exists():raise SystemExit('VPS-only guard')
    tmp=STATE/'tmp/videos';tmp.mkdir(parents=True,exist_ok=True)
    manifest_path=STATE/'videos.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'items':{}}
    # Reconcile prior uploads by canonical stream, not expiring signature or display title.
    old_path=STATE/'catalog/video_upload_manifest.json'
    old=json.loads(old_path.read_text()).get('items',[]) if old_path.exists() else []
    remote_path=STATE/'remote-videos.json'
    remote={x['Path']:x for x in json.loads(remote_path.read_text())} if remote_path.exists() else {}
    old_by_stream={canonical_url(x.get('video_stream_url','')):x for x in old}
    log=core.Logger([])
    for row in rows_from_catalog():
        key=identity(row);version=revision(row);previous=manifest['items'].get(key,{})
        if previous.get('revision')==version and previous.get('status') in ('verified','existing_remote_verified'):continue
        if previous.get('retry_at',0)>time.time():
            continue
        discard_recoverable_partial(tmp, key, log)
        legacy=old_by_stream.get(canonical_url(row['video_stream_url']))
        if not previous and legacy:
            relative=legacy['remote_path'].removeprefix('onedrive:Federal Online/')
            observed=remote.get(relative)
            if observed and observed.get('Size')==legacy.get('local_file_size_bytes') and legacy.get('duration_seconds')==row.get('duracao_segundos'):
                manifest['items'][key]={'revision':version,'status':'existing_remote_verified','remote_path':legacy['remote_path'],'size':observed['Size'],'source':'preexisting_upload_manifest_and_remote_inventory','checked_at':time.time()}
                atomic_json(manifest_path,manifest)
                continue
        try:
            allowed_bytes(shutil.disk_usage(tmp).free)
            course=core.sanitize_name(urlsplit(row['course_url']).path.rstrip('/').split('/')[-1],fallback='course')
            title=core.sanitize_name(core.title_from_aula(row),fallback=key,max_len=100)
            # Revision path avoids destructive overwrite of original videos.
            hierarchy='/'.join(core.source_ref_to_parts(core.source_ref_from_aula(row)))
            destination=f'onedrive:Federal Online/{course}/{hierarchy}/{key}/{version}/{title}.mp4'
            local=tmp/f'{key}-{version}.mp4'
            candidate=core.build_candidates([row],tmp_dir=tmp,rclone_remote='onedrive:',remote_base='Federal Online/'+course)[0]
            candidate.tmp_partial_path=local.with_suffix('.partial.mp4');candidate.tmp_final_path=local
            candidate.remote_path=destination
            if not local.exists():
                selection=core.choose_stream_selection(candidate,log)
                cmd=['ffmpeg','-loglevel','error','-nostdin','-y','-i',row['video_stream_url'],'-map',f'0:{selection.video_stream_index}']
                if selection.audio_stream_index is not None:cmd+=['-map',f'0:{selection.audio_stream_index}']
                cmd+=['-c','copy','-fs',str(allowed_bytes(shutil.disk_usage(tmp).free)),'-movflags','+faststart',str(candidate.tmp_partial_path)]
                with (STATE/'video-download.stderr.log').open('w') as errors:
                    process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=errors)
                    try:
                        while process.poll() is None:
                            if shutil.disk_usage(tmp).free<RESERVE:
                                process.terminate();raise RuntimeError('Storage reserve reached during download')
                            time.sleep(2)
                        if process.returncode:raise RuntimeError('FFmpeg download failed; retry after catalog refresh')
                    finally:
                        if process.poll() is None:process.terminate();process.wait(timeout=30)
                probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(candidate.tmp_partial_path)],capture_output=True,text=True,check=True,timeout=30)
                duration=float(json.loads(probe.stdout)['format']['duration'])
                expected=float(row.get('duracao_segundos') or 0)
                if expected and duration<expected*0.95:raise RuntimeError('Incomplete video; do not upload')
                os.replace(candidate.tmp_partial_path,local)
            subprocess.run(['rclone','copyto',str(local),destination,'--retries','3','--low-level-retries','5'],capture_output=True,text=True,check=True,timeout=7200)
            # Local filename and remote filename differ; verify a single-file view via --files-from-raw.
            # Stage under remote basename for rclone check; only one local video ever exists.
            named=local.with_name(title+'.mp4');os.replace(local,named)
            try:verify_upload(named,destination)
            except Exception:
                os.replace(named,local);raise
            size=named.stat().st_size
            manifest['items'][key]={'revision':version,'status':'verified','remote_path':destination,'size':size,'checked_at':time.time()}
            atomic_json(manifest_path,manifest)
            named.unlink()
        except Exception as exc:
            attempts=int(previous.get('attempts',0))+1
            manifest['items'][key]={'revision':version,'status':'error','error_type':type(exc).__name__,'attempts':attempts,'retry_at':time.time()+min(86400,60*2**min(attempts,10))}
            atomic_json(manifest_path,manifest)
            # A failed staged upload must not accumulate videos from other jobs.
            break
    print(json.dumps({'video_states':{status:sum(x.get('status')==status for x in manifest['items'].values()) for status in ('verified','existing_remote_verified','error')}}))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Sequential persistent video sync. Never invokes transcription or deletes remote data."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import os
import shutil
import subprocess
import time
import tempfile

import fo_download_upload_videos as core
from fo_media_identity import canonical_media_url

STATE = Path(os.environ.get('FO_STATE_ROOT', '/home/ubuntu/study-hub-state/federal-online'))
RESERVE = 4 * 1024**3


class SourceDurationMismatch(RuntimeError):
    """Remote source itself is shorter than catalog; preserve staged evidence."""


def canonical_url(url):
    return canonical_media_url(url)


def source_unavailability_reason(exc):
    if isinstance(exc,SourceDurationMismatch):return 'source_duration_mismatch'
    if isinstance(exc,subprocess.CalledProcessError):
        detail=str(exc.stderr or '').casefold()
        if any(x in detail for x in ('unauthorized','forbidden','token expired','401','403')):return None
        if '404' in detail and 'not found' in detail:return 'hls_404'
        if '410' in detail and 'gone' in detail:return 'hls_gone'
    return None


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
    # Keep the stable resume path intact even if the service is killed mid-check.
    # A hard link provides the remote basename without duplicating video bytes.
    with tempfile.TemporaryDirectory(prefix='.verify-', dir=local.parent) as directory:
        view = Path(directory)
        os.link(local, view / filename)
        listing = view / '.verify-files'
        listing.write_text(filename+'\n')
        runner(['rclone','check',str(view),parent,'--files-from-raw',str(listing),'--one-way','--download','--retries','3'],check=True,capture_output=True,text=True,timeout=7200)


def atomic_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    os.replace(tmp,path)


def discard_recoverable_partial(tmp_dir: Path, key: str, logger: core.Logger, revision: str | None = None) -> int:
    """Remove only this job's unvalidated partial; unknown jobs stay untouched."""
    removed = 0
    for partial in tmp_dir.glob(f"{key}-{revision or '*'}.partial.mp4"):
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
    # Only published observations may schedule a download/upload.
    paths = [p for p in paths if not any(part.startswith('.') for part in p.relative_to(STATE).parts)]
    by_id = {}
    for path in paths:
        data=json.loads(path.read_text())
        for row in data.get('aulas',[]):
            if row.get('catalog_observation') == 'retained_previous_not_observed':continue
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
        if previous.get('revision')==version and previous.get('retry_at',0)>time.time():
            continue
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
            if not local.exists() and previous.get('status') in ('error','unavailable'):
                # Repeatedly downloading a source already shorter than catalog
                # cannot repair it. Probe BEFORE touching its known partial.
                probe=subprocess.run(['ffprobe','-v','quiet','-show_entries','format=duration',
                                      '-of','json',row['video_stream_url']],
                                     capture_output=True,text=True,check=True,timeout=45)
                source_duration=float(json.loads(probe.stdout).get('format',{}).get('duration') or 0)
                expected=float(row.get('duracao_segundos') or 0)
                if expected and source_duration and source_duration<expected*0.95:
                    raise SourceDurationMismatch('source metadata shorter than catalog')
            discard_recoverable_partial(tmp, key, log, revision=version)
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
                if expected and duration<expected*0.95:raise SourceDurationMismatch('Incomplete video; do not upload')
                os.replace(candidate.tmp_partial_path,local)
            subprocess.run(['rclone','copyto',str(local),destination,'--retries','3','--low-level-retries','5'],capture_output=True,text=True,check=True,timeout=7200)
            verify_upload(local,destination)
            size=local.stat().st_size
            manifest['items'][key]={'revision':version,'status':'verified','remote_path':destination,'size':size,'checked_at':time.time()}
            atomic_json(manifest_path,manifest)
            local.unlink()
        except Exception as exc:
            attempts=int(previous.get('attempts',0))+1
            reason=source_unavailability_reason(exc)
            if reason:
                manifest['items'][key]={'revision':version,'status':'unavailable','reason':reason,
                                        'error_type':type(exc).__name__,'attempts':attempts,
                                        'checked_at':time.time(),'retry_at':time.time()+86400}
                atomic_json(manifest_path,manifest)
                continue
            delay=21600 if isinstance(exc,SourceDurationMismatch) else min(86400,60*2**min(attempts,10))
            manifest['items'][key]={'revision':version,'status':'error','error_type':type(exc).__name__,'attempts':attempts,'retry_at':time.time()+delay}
            atomic_json(manifest_path,manifest)
            # A failed staged upload must not accumulate videos from other jobs.
            break
    print(json.dumps({'video_states':{status:sum(x.get('status')==status for x in manifest['items'].values()) for status in ('verified','existing_remote_verified','unavailable','error')}}))


if __name__=='__main__':main()

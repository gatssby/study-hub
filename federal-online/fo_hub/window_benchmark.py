"""Private, bounded real-window comparisons; no queue leases or publication.

Invoke only on the authorized VPS inside a resource-limited transient unit.
The shared worker lock prevents concurrent large-v3 runs. All results require
acoustic review; this module neither supplies gold nor chooses a winner.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import time
import uuid

from .worker import Config,RESERVE,atomic_json,file_sha256,gate,identity,parse_whisper
from .transcription import qa_segments

_SELECTION=Path(__file__).resolve().parents[1]/'transcription/benchmark-selection-2026-10-27.json'
_CONFIGS={
    'baseline':{'beam_size':5,'temperature_fallback':False,'max_context':-1,'no_speech':0.6},
    'beam10':{'beam_size':10,'temperature_fallback':False,'max_context':-1,'no_speech':0.6},
    'fallback':{'beam_size':5,'temperature_fallback':True,'max_context':-1,'no_speech':0.6},
    'no-context':{'beam_size':5,'temperature_fallback':False,'max_context':0,'no_speech':0.6},
    'no-speech-0.8':{'beam_size':5,'temperature_fallback':False,'max_context':-1,'no_speech':0.8},
}


def window_plan(lesson_id,window_index,config_id):
    if config_id not in _CONFIGS:raise ValueError('configuration outside bounded comparison matrix')
    lessons=json.loads(_SELECTION.read_text())['lessons']
    lesson=next((row for row in lessons if row['lesson_id']==lesson_id),None)
    if lesson is None or type(window_index) is not int or not 0<=window_index<3:
        raise ValueError('window outside authorized selection')
    window=lesson['windows'][window_index]
    if window['duration_s']!=300:raise ValueError('window is not five minutes')
    return {'lesson_id':lesson_id,'version':lesson['version'],'window_index':window_index,
            'config_id':config_id,'start_s':window['start_s'],'duration_s':300,
            'decoder':dict(_CONFIGS[config_id]),'acoustic_stratum_verified':False}


def _source(cfg,plan):
    with closing(sqlite3.connect(f'file:{cfg.db}?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT l.version,l.present,l.duration_s,s.remote_path,s.revision,s.size,s.available '
                         'FROM lessons l JOIN lesson_video_sources s USING(lesson_id) WHERE l.lesson_id=?',
                         (plan['lesson_id'],)).fetchone()
    if row is None:raise ValueError('source missing')
    source=dict(row)
    if not source['present'] or not source['available'] or source['version']!=plan['version'] or source['revision']!=str(plan['version']):
        raise ValueError('source is not eligible at frozen revision')
    remote=str(source['remote_path'])
    if not remote.startswith('onedrive:Federal Online/') or '..' in Path(remote).parts or not source['size'] or source['size']<=0:
        raise ValueError('source outside classified remote or invalid size')
    return source


def run_process_group(args,*,check=True,capture_output=True,text=True,timeout=None):
    """Own the complete command group, including descendants of /usr/bin/time.

    Do not return (and therefore do not release the caller's lock) until the
    leader is reaped and no executing group member remains. Zombies cannot run;
    only their parent/init can reap them. Commands must not detach sessions.
    """
    process=subprocess.Popen(args,start_new_session=True,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,text=text)
    def send(sig):
        try:os.killpg(process.pid,sig)
        except ProcessLookupError:pass
    try:
        stdout,stderr=process.communicate(timeout=timeout)
        result=subprocess.CompletedProcess(args,process.returncode,stdout,stderr)
        if check:result.check_returncode()
        return result
    finally:
        send(signal.SIGTERM)
        # Give cooperative wrappers an opportunity to reap their children.
        time.sleep(.1)
        send(signal.SIGKILL)
        process.communicate()
        process.wait()
        while True:
            try:
                listing=subprocess.run(['ps','-axo','pgid=,stat='],check=True,capture_output=True,text=True).stdout
            except (OSError,subprocess.SubprocessError):
                # Fail closed: retain the caller's lock until termination can
                # be observed, rather than unlocking on a monitoring failure.
                send(signal.SIGKILL)
                time.sleep(.1)
                continue
            live=any(int(parts[0])==process.pid and not parts[1].startswith('Z')
                     for row in listing.splitlines() if len(parts:=row.split())>=2)
            if not live:break
            send(signal.SIGKILL)
            time.sleep(.02)


def _verify_evidence(artifact,root):
    for field in ('raw_path','resource_log'):
        try:
            path=Path(artifact[field])
            if path.is_symlink() or not path.is_file() or path.parent.resolve()!=root.resolve() or file_sha256(path)!=artifact[field+'_sha256']:
                raise ValueError('cached evidence integrity failed')
        except (KeyError,OSError) as exc:
            raise ValueError('cached evidence integrity failed') from exc


def _comparison_gate(root,plan,selection):
    try:
        if not isinstance(selection,dict) or selection.get('informative') is not True:
            raise ValueError('informative comparison selection required')
        configs=selection['configs']
        if not isinstance(configs,list) or not configs or len(configs)!=len(set(configs)) or not set(configs)<=set(_CONFIGS)-{'baseline'} or plan['config_id'] not in configs:
            raise ValueError('bounded comparison selection required')
        if not all(isinstance(selection.get(k),str) and selection[k].strip() for k in ('rationale','operator')) or selection.get('acoustic_reviewed') is not False:
            raise ValueError('exploratory comparison selection required; no acoustic certification')
        path=Path(selection['baseline_artifact']);lesson_root=root/plan['lesson_id']
        if path.is_symlink() or not path.is_file() or path.parent.resolve()!=lesson_root.resolve() or file_sha256(path)!=selection['baseline_sha256']:
            raise ValueError('baseline integrity failed')
        artifact=json.loads(path.read_text())
        baseline=window_plan(plan['lesson_id'],plan['window_index'],'baseline')
        if artifact['plan']!=baseline or artifact['source_unchanged_after_run'] is not True:
            raise ValueError('baseline window mismatch')
        receipt=json.loads((lesson_root/(artifact['fingerprint']+'.receipt.json')).read_text())
        if receipt['artifact']!=str(path) or receipt['sha256']!=file_sha256(path):
            raise ValueError('baseline receipt mismatch')
        _verify_evidence(artifact,lesson_root)
        return artifact
    except (KeyError,TypeError,OSError) as exc:
        raise ValueError('baseline and comparison selection required') from exc


def run_window(cfg,plan,*,runner=run_process_group,gate_fn=None,free_bytes=None,comparison_selection=None):
    gate_fn=gate_fn or (lambda:gate(cfg))
    if not gate_fn()['allowed']:return {'state':'blocked'}
    if plan!=window_plan(plan['lesson_id'],plan['window_index'],plan['config_id']):
        raise ValueError('mutated window plan')
    source=_source(cfg,plan)
    free_bytes=free_bytes or (lambda:shutil.disk_usage(cfg.state).free)
    if free_bytes()<RESERVE+source['size']+200*1024**2:raise ValueError('insufficient storage reserve')
    locks=cfg.state/'locks';locks.mkdir(parents=True,exist_ok=True)
    with (locks/'transcription.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'state':'busy'}
        if not gate_fn()['allowed']:return {'state':'blocked'}
        root=cfg.state/'validation-2026-10-28/windows';root.mkdir(mode=0o700,parents=True,exist_ok=True)
        baseline_artifact=None
        if plan['config_id']!='baseline':
            baseline_artifact=_comparison_gate(root,plan,comparison_selection)
        budget_path=root/'budget.json'
        budget=json.loads(budget_path.read_text()) if budget_path.exists() else {'windows':[],'limit':18}
        key=f"{plan['lesson_id']}:{plan['window_index']}"
        if key not in budget['windows']:
            if len(budget['windows'])>=18:raise ValueError('authorized window budget exhausted')
            budget['windows'].append(key);atomic_json(budget_path,budget)
        lesson_root=root/plan['lesson_id'];lesson_root.mkdir(mode=0o700,exist_ok=True)
        manifest_path=lesson_root/'audio-manifest.json'
        def command(args,timeout=7200):
            return runner([str(x) for x in args],check=True,capture_output=True,text=True,timeout=timeout)
        if not manifest_path.exists():
            with tempfile.TemporaryDirectory(prefix='source-',dir=lesson_root) as folder:
                video=Path(folder)/'source.mp4'
                command(['rclone','copyto',source['remote_path'],video,'--transfers','1','--retries','3',
                         '--max-transfer',f"{source['size']+1024**2}B",'--cutoff-mode','HARD'])
                if video.stat().st_size!=source['size']:raise ValueError('download size mismatch')
                source_hash=file_sha256(video)
                probe=json.loads(command(['ffprobe','-v','error','-show_entries','format=duration','-of','json',video]).stdout)
                duration=float(probe['format']['duration'])
                if not 0<duration<=24*3600:raise ValueError('invalid source duration')
                expected=source['duration_s']
                if expected and abs(duration-expected)>max(5,expected*0.05):raise ValueError('source duration mismatch')
                audio_entries=[]
                # One source download yields all three bounded proposed windows;
                # extraction is not ASR and consumes no extra inference windows.
                for index in range(3):
                    bounds=window_plan(plan['lesson_id'],index,'baseline')
                    if bounds['start_s']+300>duration+0.1:raise ValueError('window exceeds actual video')
                    audio=lesson_root/f'window-{index}-{uuid.uuid4().hex}.wav'
                    args=['ffmpeg','-nostdin','-threads','1','-ss',bounds['start_s'],'-i',video,'-t','300',
                          '-ar','16000','-ac','1','-c:a','pcm_s16le','-threads','1',audio]
                    command(args)
                    audio_entries.append({'path':str(audio),'sha256':file_sha256(audio),'start_s':bounds['start_s'],
                                          'duration_s':300,'conversion_command':[str(x) for x in args]})
                if _source(cfg,plan)!=source:raise ValueError('source changed during extraction')
                atomic_json(manifest_path,{'source':source,'source_sha256':source_hash,'actual_duration_s':duration,'audio':audio_entries})
        manifest=json.loads(manifest_path.read_text())
        if manifest['source']!=source:raise ValueError('cached audio source revision changed')
        audio_entry=manifest['audio'][plan['window_index']]
        audio=Path(audio_entry['path'])
        if audio.is_symlink() or not audio.is_file() or audio.parent.resolve()!=lesson_root.resolve() or file_sha256(audio)!=audio_entry['sha256']:
            raise ValueError('cached audio integrity failed')
        if audio_entry['start_s']!=plan['start_s'] or audio_entry['duration_s']!=300:raise ValueError('cached audio bounds changed')
        provenance={'model_sha256':identity(cfg.model),'runtime_sha256':identity(cfg.binary),
                    'runtime_libraries':{p.name:identity(p) for p in sorted(cfg.binary.parent.glob('*.so*')) if p.is_file()},'plan':plan,
                    'audio_sha256':audio_entry['sha256'],'source_sha256':manifest['source_sha256']}
        if baseline_artifact is not None:
            if any(baseline_artifact[k]!=v for k,v in provenance.items() if k!='plan'):
                raise ValueError('baseline provenance mismatch')
            atomic_json(lesson_root/f"selection-{uuid.uuid4().hex}.json",comparison_selection)
        fingerprint=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
        receipt_path=lesson_root/f'{fingerprint}.receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            old=Path(receipt['artifact'])
            if old.is_symlink() or old.parent.resolve()!=lesson_root.resolve() or file_sha256(old)!=receipt['sha256']:
                raise ValueError('cached comparison artifact integrity failed')
            artifact=json.loads(old.read_text())
            _verify_evidence(artifact,lesson_root)
            if artifact['fingerprint']!=fingerprint or not artifact['source_unchanged_after_run']:
                raise ValueError('cached comparison provenance failed')
            return {'state':'measured','artifact':str(old),'audio_sha256':audio_entry['sha256'],
                    'wall_s':artifact['wall_s'],'rtf':artifact['rtf'],'reused':True}
        prefix=lesson_root/f"window-{plan['window_index']}-{plan['config_id']}-{fingerprint[:12]}-{uuid.uuid4().hex}"
        params=plan['decoder'];resource_path=Path(str(prefix)+'.time.txt')
        args=['/usr/bin/time','-v','-o',resource_path,cfg.binary,'-m',cfg.model,'-f',audio,'-l','pt','-t','3',
              '-bs',params['beam_size'],'-bo','5','-mc',params['max_context'],'-tp','0',
              '-tpi','0.2' if params['temperature_fallback'] else '0','-nth',params['no_speech'],
              '-et','2.4','-lpt','-1','-ng','-ojf','-of',prefix]
        if not params['temperature_fallback']:args.append('-nf')
        if not gate_fn()['allowed']:return {'state':'blocked'}
        started=time.monotonic()
        try:
            result=command(args,timeout=172800)
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
            atomic_json(Path(str(prefix)+'.failure.json'),{'error_type':type(exc).__name__,
                        'stdout':str(exc.stdout or ''),'stderr':str(exc.stderr or ''),
                        'returncode':getattr(exc,'returncode',None),'provenance':provenance,
                        'command':[str(x) for x in args],'published':False})
            raise
        wall=time.monotonic()-started
        # Decoder JSON remains untouched even when parsing/schema fails.
        raw_path=Path(str(prefix)+'.json')
        raw=json.loads(raw_path.read_text());segments=parse_whisper(raw,plan['start_s'])
        unchanged=_source(cfg,plan)==source
        artifact={**provenance,'source_revision':source['revision'],'raw':raw,'segments':segments,
                  'qa':qa_segments([{**s,'start':s['start']-plan['start_s'],'end':s['end']-plan['start_s']} for s in segments],300),'wall_s':wall,'rtf':wall/300,
                  'stdout':result.stdout,'stderr':result.stderr,'command':[str(x) for x in args],
                  'raw_path':str(raw_path),'raw_path_sha256':file_sha256(raw_path),
                  'resource_log_sha256':file_sha256(resource_path),
                  'resource_log':str(resource_path),'audio_path':str(audio),'fingerprint':fingerprint,
                  'synthetic':None,'human_gold':None,'acoustic_reviewed':False,'published':False,
                  'inference_invoked':True,'source_unchanged_after_run':unchanged,'created_at':time.time()}
        artifact_path=Path(str(prefix)+'.artifact.json');atomic_json(artifact_path,artifact)
        if unchanged:atomic_json(receipt_path,{'artifact':str(artifact_path),'sha256':file_sha256(artifact_path)})
        return {'state':'measured' if unchanged else 'source_changed','artifact':str(artifact_path),
                'audio_sha256':audio_entry['sha256'],'wall_s':wall,'rtf':wall/300}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lesson-id',required=True)
    parser.add_argument('--window',required=True,type=int,choices=range(3))
    parser.add_argument('--config',required=True,choices=tuple(_CONFIGS))
    parser.add_argument('--comparison-selection',type=Path,help='Private bounded exploratory selection JSON bound to a baseline artifact')
    args=parser.parse_args(argv)
    cfg=Config.from_env()
    # Refuse uncapped/non-VPS CLI execution, even if someone copies the gate.
    group=Path('/proc/self/cgroup')
    if not group.exists():parser.error('VPS cgroup required')
    path=next((line.split(':',2)[2] for line in group.read_text().splitlines() if line.startswith('0::')),None)
    if path is None:parser.error('cgroup v2 required')
    cgroup=Path('/sys/fs/cgroup')/path.lstrip('/')
    try:
        memory=int((cgroup/'memory.max').read_text().strip())
        quota,period=map(int,(cgroup/'cpu.max').read_text().split())
        tasks=int((cgroup/'pids.max').read_text().strip())
    except (OSError,ValueError):parser.error('finite CPU/memory/tasks limits required')
    if memory>12*1024**3 or quota/period>3 or tasks>128:parser.error('resource limits exceed pilot bounds')
    result=run_window(cfg,window_plan(args.lesson_id,args.window,args.config),
                      comparison_selection=json.loads(args.comparison_selection.read_text()) if args.comparison_selection else None)
    print(json.dumps(result),flush=True)
    return 0 if result['state']=='measured' else 3


if __name__=='__main__':raise SystemExit(main())

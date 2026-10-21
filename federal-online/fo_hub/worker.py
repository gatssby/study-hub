"""VPS-only, fail-closed transcription worker. No automatic authorization.

--check-only never leases or opens media. --run requires explicit true + a
separate authorization phrase + Linux VPS marker + executable/model files.
Tests inject subprocesses; no real inference is part of the test suite.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid

from .store import FOStore, ACCEPTED_CORPUS
from .transcription import AUTH_PHRASE, DEFAULT_AUTH_FILE, DEFAULT_PLATFORM_MARKER, TranscriptionQueue, qa_segments

RESERVE=4*1024**3


@dataclass
class Config:
    state:Path
    db:Path
    binary:Path
    model:Path
    auth:Path=Path(DEFAULT_AUTH_FILE)
    marker:Path=Path(DEFAULT_PLATFORM_MARKER)
    chunk_s:int=600
    overlap_s:int=2
    threads:int=3

    @classmethod
    def from_env(cls):
        state=Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online'))
        return cls(state,Path(os.environ.get('STUDY_HUB_FO_DB',str(state/'hub.sqlite3'))),
                   Path(os.environ.get('WHISPER_CPP_BIN','/home/ubuntu/study-hub-models/whisper.cpp/build/bin/whisper-cli')),
                   Path(os.environ.get('WHISPER_MODEL','/home/ubuntu/study-hub-models/ggml-large-v3.bin')),
                   Path(os.environ.get('STUDY_HUB_FO_TRANSCRIPTION_AUTH',DEFAULT_AUTH_FILE)),
                   Path(os.environ.get('STUDY_HUB_FO_PLATFORM_MARKER',DEFAULT_PLATFORM_MARKER)))


def gate(config,env=None,platform=None):
    env=os.environ if env is None else env
    reasons=[]
    if env.get('TRANSCRIPTION_ENABLED','false').strip().lower()!='true':reasons.append('TRANSCRIPTION_ENABLED is not true')
    if not (platform or sys.platform).startswith('linux') or not config.marker.is_file():reasons.append('not running on marked Linux VPS')
    try:
        if config.auth.read_text().strip()!=AUTH_PHRASE:reasons.append('authorization phrase invalid')
    except OSError:reasons.append('authorization file missing')
    if not config.binary.is_file() or not os.access(config.binary,os.X_OK):reasons.append('whisper executable missing')
    if not config.model.is_file():reasons.append('model weights missing')
    if config.chunk_s<=config.overlap_s or config.overlap_s<0 or config.threads<1:reasons.append('invalid chunk configuration')
    return {'allowed':not reasons,'reasons':reasons,'TRANSCRIPTION_ENABLED':env.get('TRANSCRIPTION_ENABLED','false')}


def parse_whisper(payload,offset=0):
    out=[]
    for row in payload.get('transcription',[]):
        times=row.get('offsets')
        if not times or 'from' not in times or 'to' not in times:raise ValueError('missing millisecond offsets')
        out.append({'start':offset+float(times['from'])/1000,'end':offset+float(times['to'])/1000,'text':str(row.get('text','')).strip()})
    return out


def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.replace(tmp,path)


def silence_intervals(log,duration):
    intervals=[];start=None
    for match in re.finditer(r'silence_(start|end):\s*([0-9.]+)',log):
        value=float(match[2])
        if match[1]=='start':start=value
        elif start is not None:intervals.append((start,value));start=None
    if start is not None:intervals.append((start,duration))
    return intervals


class Worker:
    def __init__(self,config,store=None,runner=subprocess.run,gate_fn=None,free_bytes=None):
        self.cfg=config;self.store=store or FOStore(config.db);self.c=self.store.conn
        self.runner=runner;self.gate_fn=gate_fn or (lambda:gate(config))
        self.free_bytes=free_bytes or (lambda:shutil.disk_usage(config.state).free)
        self.owner='fo-worker:'+socket.gethostname()+':'+str(os.getpid())+':'+uuid.uuid4().hex
        self.c.execute('CREATE TABLE IF NOT EXISTS lesson_video_sources(lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT)')
        if 'retry_at' not in {x[1] for x in self.c.execute('PRAGMA table_info(transcription_jobs)')}:
            self.c.execute('ALTER TABLE transcription_jobs ADD COLUMN retry_at REAL DEFAULT 0')
        self.c.execute('CREATE TABLE IF NOT EXISTS focused_reviews(lesson_id TEXT,version INTEGER,start REAL,end REAL,reason TEXT,state TEXT,PRIMARY KEY(lesson_id,version,start,end,reason))')
        self.c.commit()

    def recover(self):
        # Caller must hold the process lock. A dead predecessor cannot retain work.
        temporary=self.cfg.state/'tmp/transcription'
        if temporary.is_dir():
            for folder in temporary.glob('job-*'):
                marker=folder/'.worker-owned'
                if folder.is_dir() and not folder.is_symlink() and marker.is_file() and not marker.is_symlink() and marker.read_text()=='study-hub-fo-worker':
                    shutil.rmtree(folder)
        with self.c:
            self.c.execute("UPDATE transcription_jobs SET state=CASE WHEN attempts>=max_attempts THEN 'failed' ELSE 'queued' END,lease_owner=NULL,lease_until=NULL,last_error='worker interrupted; resumed from persistent queue' WHERE state='leased' AND lease_owner LIKE 'fo-worker:%'")

    def lease(self):
        now=time.time()
        self.c.execute('BEGIN IMMEDIATE')
        try:
            self.c.execute("UPDATE transcription_jobs SET state='stale' WHERE state='queued' AND EXISTS(SELECT 1 FROM lessons l WHERE l.lesson_id=transcription_jobs.lesson_id AND l.version!=transcription_jobs.version)")
            row=self.c.execute("SELECT j.* FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id AND l.version=j.version JOIN lesson_video_sources s ON s.lesson_id=j.lesson_id WHERE j.state='queued' AND COALESCE(j.retry_at,0)<=? AND j.attempts<j.max_attempts AND l.present=1 AND s.available=1 AND CAST(j.version AS TEXT)=s.revision AND s.remote_path IS NOT NULL ORDER BY j.created_at,j.lesson_id LIMIT 1",(now,)).fetchone()
            if row is None:self.c.commit();return None
            self.c.execute("UPDATE transcription_jobs SET state='leased',attempts=attempts+1,lease_owner=?,lease_until=?,updated_at=? WHERE lesson_id=? AND version=?",(self.owner,now+7*86400,str(now),row['lesson_id'],row['version']))
            self.c.commit();return dict(row)
        except BaseException:self.c.rollback();raise

    def command(self,cmd,timeout=7200):
        # Raw stderr/command arguments stay private; no signed URLs in logs.
        return self.runner([str(x) for x in cmd],check=True,capture_output=True,text=True,timeout=timeout)

    def current_source(self,job):
        lesson=self.store.get_lesson(job['lesson_id'])
        source=self.c.execute('SELECT * FROM lesson_video_sources WHERE lesson_id=?',(job['lesson_id'],)).fetchone()
        if not lesson or not lesson['present'] or lesson['version']!=job['version'] or not source or not source['available'] or source['revision']!=str(job['version']):raise RuntimeError('source revision no longer current')
        if not str(source['remote_path']).startswith('onedrive:Federal Online/') or '..' in Path(source['remote_path']).parts:raise ValueError('source outside classified FO remote')
        return lesson,dict(source)

    def pipeline(self,job,work):
        cfg=self.cfg;lesson,source=self.current_source(job)
        size=int(source.get('size') or 0)
        if size<=0 or self.free_bytes()<RESERVE+size+100*1024**2:raise RuntimeError('storage budget or source size invalid')
        video=work/'source.mp4'
        self.command(['rclone','copyto',source['remote_path'],video,'--retries','3','--transfers','1',
                      '--max-size',f'{size}B','--max-transfer',f'{size+1024**2}B','--cutoff-mode','HARD'])
        if video.stat().st_size!=size:raise RuntimeError('source download size mismatch')
        probe=self.command(['ffprobe','-v','error','-show_entries','format=duration','-of','json',video],timeout=60)
        duration=float(json.loads(probe.stdout)['format']['duration'])
        if duration<=0:raise ValueError('invalid source duration')
        expected=lesson.get('duration_s')
        if expected and abs(duration-float(expected))>max(5,float(expected)*0.05):raise ValueError('source duration mismatch')
        segments=[];chunks=[];acoustic_flags=[];offset=0.0
        queue=TranscriptionQueue(self.store)
        while offset<duration:
            if not self.gate_fn()['allowed']:raise RuntimeError('authorization revoked')
            if self.free_bytes()<RESERVE+100*1024**2:raise RuntimeError('storage reserve reached')
            length=min(cfg.chunk_s,duration-offset);audio=work/'chunk.wav';prefix=work/'asr'
            self.command(['ffmpeg','-nostdin','-y','-ss',str(offset),'-i',video,'-t',str(length),'-ar','16000','-ac','1','-c:a','pcm_s16le',audio])
            silence=self.command(['ffmpeg','-nostdin','-i',audio,'-af','silencedetect=noise=-40dB:d=1','-f','null','-'])
            self.command([cfg.binary,'-m',cfg.model,'-f',audio,'-l','pt','-t',str(cfg.threads),'-bs','5','-tp','0','-nf','-ng','-oj','-of',prefix],timeout=172800)
            payload=json.loads(prefix.with_suffix('.json').read_text())
            current=parse_whisper(payload,offset)
            intervals=silence_intervals(silence.stderr or '',length)
            for row in current:
                for start,end in intervals:
                    if row['text'] and row['start']>=offset+start and row['end']<=offset+end:acoustic_flags.append({'kind':'text_during_measured_silence','start':row['start'],'end':row['end']})
            # Preserve overlap text; QA flags alignment/duplication for focused review.
            segments.extend(current);chunks.append({'offset_s':offset,'duration_s':length,'segments':current,'silence':intervals})
            queue.progress(job['lesson_id'],job['version'],self.owner,min(1,(offset+length)/duration))
            with self.c:self.c.execute('UPDATE transcription_jobs SET lease_until=? WHERE lesson_id=? AND version=?',(time.time()+7*86400,job['lesson_id'],job['version']))
            audio.unlink(missing_ok=True);prefix.with_suffix('.json').unlink(missing_ok=True)
            if offset+length>=duration:break
            offset+=cfg.chunk_s-cfg.overlap_s
        qa=qa_segments(segments,duration)
        qa['flags'].extend(acoustic_flags)
        if not segments:qa['flags'].append({'kind':'empty_output'})
        qa['passed']=not qa['flags'];qa['metrics']['flag_count']=len(qa['flags'])
        self.current_source(job)  # Catalog/source may have changed during long inference.
        artifact={'lesson_id':job['lesson_id'],'version':job['version'],'model':'whisper-large-v3','model_path':str(cfg.model),'runtime_path':str(cfg.binary),'parameters':{'language':'pt','threads':cfg.threads,'beam_size':5,'temperature':0,'temperature_fallback':False,'chunk_s':cfg.chunk_s,'overlap_s':cfg.overlap_s},'source_size':size,'duration_s':duration,'created_at':time.time(),'corpus':ACCEPTED_CORPUS,'qa':qa,'chunks':chunks}
        status='validated' if qa['passed'] else 'review'
        path=cfg.state/'transcripts'/('generated_v2' if qa['passed'] else 'review')/job['lesson_id']/f"v{job['version']}.json"
        atomic_json(path,artifact)
        if qa['passed']:
            self.store.add_transcript(job['lesson_id'],job['version'],segments,artifact['model'],ACCEPTED_CORPUS,True,qa)
        else:
            with self.c:
                for flag in qa['flags']:
                    idx=min(int(flag.get('idx',0)),max(0,len(segments)-1))
                    seg=segments[idx] if segments else {'start':0,'end':duration}
                    start=max(0,float(flag.get('start',seg['start']))-2);end=min(duration,float(flag.get('end',seg['end']))+2)
                    self.c.execute("INSERT OR IGNORE INTO focused_reviews VALUES(?,?,?,?,?,'pending_manual_review')",(job['lesson_id'],job['version'],start,end,flag['kind']))
        return status

    def run_once(self):
        g=self.gate_fn()
        if not g['allowed']:return {'state':'blocked','gate':g}
        job=self.lease()
        if job is None:return {'state':'idle'}
        temp=self.cfg.state/'tmp/transcription';temp.mkdir(parents=True,exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix='job-',dir=temp) as folder:
                (Path(folder)/'.worker-owned').write_text('study-hub-fo-worker')
                status=self.pipeline(job,Path(folder))
            with self.c:self.c.execute("UPDATE transcription_jobs SET state=?,progress=1,lease_owner=NULL,lease_until=NULL,updated_at=? WHERE lesson_id=? AND version=? AND lease_owner=?",('done' if status=='validated' else 'review',str(time.time()),job['lesson_id'],job['version'],self.owner))
            return {'state':status,'lesson_id':job['lesson_id'],'version':job['version']}
        except Exception as exc:
            current=self.c.execute('SELECT attempts,max_attempts FROM transcription_jobs WHERE lesson_id=? AND version=?',(job['lesson_id'],job['version'])).fetchone()
            state='failed' if current['attempts']>=current['max_attempts'] else 'queued'
            with self.c:self.c.execute('UPDATE transcription_jobs SET state=?,retry_at=?,last_error=?,lease_owner=NULL,lease_until=NULL WHERE lesson_id=? AND version=?',(state,time.time()+min(86400,60*2**current['attempts']),type(exc).__name__,job['lesson_id'],job['version']))
            return {'state':'retry' if state=='queued' else 'failed','error_type':type(exc).__name__,'lesson_id':job['lesson_id']}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only',action='store_true');mode.add_argument('--run',action='store_true')
    once=p.add_mutually_exclusive_group();once.add_argument('--once',action='store_true');once.add_argument('--loop',action='store_true')
    a=p.parse_args(argv);cfg=Config.from_env();g=gate(cfg)
    if a.check_only:
        with FOStore(cfg.db,readonly=True).conn as c:
            counts={r[0]:r[1] for r in c.execute('SELECT state,count(*) FROM transcription_jobs GROUP BY state')}
        print(json.dumps({'gate':g,'queue':counts,'inference_executed':False}));return 0
    if not g['allowed']:print(json.dumps({'state':'blocked','gate':g}));return 3
    locks=cfg.state/'locks';locks.mkdir(parents=True,exist_ok=True)
    with (locks/'transcription.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('transcription worker already owns lock',file=sys.stderr);return 4
        worker=Worker(cfg);worker.recover()
        while True:
            result=worker.run_once();print(json.dumps(result),flush=True)
            if result['state']=='blocked':return 3
            if not a.loop:return 0
            if result['state'] in ('idle','retry','failed'):time.sleep(60)


if __name__=='__main__':raise SystemExit(main())

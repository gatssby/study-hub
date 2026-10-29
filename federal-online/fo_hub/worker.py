"""VPS-only, fail-closed transcription worker. No automatic authorization.

--check-only never leases or opens media. --run requires explicit true + a
separate authorization phrase + Linux VPS marker + executable/model files.
Tests inject subprocesses; no real inference is part of the test suite.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import fcntl
import gzip
import hashlib
import json
import math
from functools import lru_cache
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
from contextlib import closing
import subprocess
import sys
import tempfile
import time
import uuid
import zlib

from .store import FOStore, ACCEPTED_CORPUS
from .scheduler import choose, discipline, discipline_key
from .transcription import AUTH_PHRASE, DEFAULT_AUTH_FILE, DEFAULT_PLATFORM_MARKER, TranscriptionQueue, qa_segments

RESERVE=4*1024**3
MODEL_SHA256='64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2'


def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=8)
def _verified_hash(path,size,mtime_ns):
    return file_sha256(path)


def identity(path):
    path=Path(path)
    if not path.is_file():return None
    stat=path.stat()
    return _verified_hash(str(path.resolve()),stat.st_size,stat.st_mtime_ns)


class SourceChanged(RuntimeError):
    pass


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
    model_sha256:str|None=None
    beam_size:int=5
    temperature_fallback:bool=False
    review_only:bool=False
    max_context:int=-1

    @classmethod
    def from_env(cls):
        state=Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online'))
        config=cls(state,Path(os.environ.get('STUDY_HUB_FO_DB',str(state/'hub.sqlite3'))),
                   Path(os.environ.get('WHISPER_CPP_BIN','/home/ubuntu/study-hub-models/whisper.cpp/build/bin/whisper-cli')),
                   Path(os.environ.get('WHISPER_MODEL','/home/ubuntu/study-hub-models/ggml-large-v3.bin')),
                   Path(os.environ.get('STUDY_HUB_FO_TRANSCRIPTION_AUTH',DEFAULT_AUTH_FILE)),
                   Path(os.environ.get('STUDY_HUB_FO_PLATFORM_MARKER',DEFAULT_PLATFORM_MARKER)))
        config.model_sha256=MODEL_SHA256
        config.max_context=int(os.environ.get('FO_ASR_MAX_CONTEXT','-1'))
        config.threads=int(os.environ.get('FO_ASR_THREADS','3'))
        config.beam_size=int(os.environ.get('FO_ASR_BEAM_SIZE','5'))
        config.temperature_fallback=os.environ.get('FO_ASR_TEMPERATURE_FALLBACK','false').lower()=='true'
        config.review_only=os.environ.get('FO_ASR_REVIEW_ONLY','false').lower()=='true'
        return config

    def parameters(self):
        return {'language':'pt','threads':self.threads,'beam_size':self.beam_size,
                'temperature':0,'temperature_fallback':self.temperature_fallback,
                'temperature_increment':0.2 if self.temperature_fallback else 0,
                'best_of':5,'no_speech_threshold':0.6,'max_context':self.max_context,
                'entropy_threshold':2.4,'logprob_threshold':-1.0,'vad':False,
                'chunk_s':self.chunk_s,'overlap_s':self.overlap_s,'stitching_version':1,'checkpoint_version':1}


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
    elif config.model_sha256 and identity(config.model)!=config.model_sha256:reasons.append('model SHA-256 mismatch')
    if config.chunk_s<=config.overlap_s or config.overlap_s<0 or not 1<=config.threads<=3 or config.beam_size<1:reasons.append('invalid chunk configuration')
    return {'allowed':not reasons,'reasons':reasons,'TRANSCRIPTION_ENABLED':env.get('TRANSCRIPTION_ENABLED','false')}


def parse_whisper(payload,offset=0):
    out=[]
    for row in payload.get('transcription',[]):
        times=row.get('offsets')
        if not times or 'from' not in times or 'to' not in times:raise ValueError('missing millisecond offsets')
        start,end=float(times['from'])/1000,float(times['to'])/1000
        if not all(math.isfinite(x) for x in (offset,start,end)) or offset<0 or start<0 or end<start:raise ValueError('invalid millisecond offsets')
        out.append({'start':offset+start,'end':offset+end,'text':str(row.get('text','')).strip()})
    return out


def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    payload=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')
    with tmp.open('wb') as handle:
        handle.write(gzip.compress(payload,mtime=0) if path.suffix=='.gz' else payload)
        handle.flush();os.fsync(handle.fileno())
    os.replace(tmp,path)


def evidence_checksum(data):
    fields=('source_sha256','fingerprint','offset_s','duration_s','raw','silence')
    if data.get('schema_version')==2:
        fields+=('schema_version','created_at','decoder_command','decoding')
    payload={key:data[key] for key in fields}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def validate_checkpoint(data,source_sha256,fingerprint,offset,length):
    if not isinstance(data,dict) or data.get('schema_version') not in (1,2):raise ValueError('checkpoint schema')
    for key,value in (('source_sha256',source_sha256),('fingerprint',fingerprint),('offset_s',offset),('duration_s',length)):
        if data.get(key)!=value:raise ValueError('checkpoint identity or bounds')
    if data.get('evidence_sha256')!=evidence_checksum(data):raise ValueError('checkpoint checksum')
    if not isinstance(data.get('created_at'),(int,float)) or not math.isfinite(data['created_at']):raise ValueError('checkpoint timestamp')
    if data['schema_version']==2:
        diagnostic=data.get('decoding')
        if not isinstance(diagnostic,dict) or type(diagnostic.get('wall_s')) not in (int,float) or not math.isfinite(diagnostic['wall_s']) or diagnostic['wall_s']<0:
            raise ValueError('checkpoint decoding timing')
        if not all(isinstance(diagnostic.get(key),str) for key in ('stdout','stderr')):
            raise ValueError('checkpoint decoding logs')
        if not isinstance(data.get('decoder_command'),list) or not all(isinstance(x,str) for x in data['decoder_command']):
            raise ValueError('checkpoint decoding command')
    raw=data['raw']
    if not isinstance(raw,dict) or not isinstance(raw.get('transcription'),list):raise ValueError('checkpoint raw schema')
    for row in raw['transcription']:
        if not isinstance(row,dict) or not isinstance(row.get('text'),str):raise ValueError('checkpoint row schema')
    parse_whisper(raw)
    if not isinstance(data['silence'],list):raise ValueError('checkpoint silence schema')
    for pair in data['silence']:
        if not isinstance(pair,list) or len(pair)!=2 or not all(type(x) in (int,float) and math.isfinite(x) for x in pair) or not 0<=pair[0]<=pair[1]<=length:raise ValueError('checkpoint silence bounds')


def silence_intervals(log,duration):
    intervals=[];start=None
    for match in re.finditer(r'silence_(start|end):\s*([0-9.]+)',log):
        value=float(match[2])
        if match[1]=='start':start=value
        elif start is not None:intervals.append((start,value));start=None
    if start is not None:intervals.append((start,duration))
    return intervals


def reconcile_silent_gaps(qa,segments,chunks,duration):
    intervals=sorted((c['offset_s']+start,c['offset_s']+end)
                     for c in chunks for start,end in c['silence'])
    qa['observations']=[]
    retained=[]
    for flag in qa['flags']:
        if flag['kind']!='silence_gap':retained.append(flag);continue
        idx=flag['idx']
        start=max((s['end'] for s in segments[:idx]),default=0)
        end=segments[idx]['start'] if idx<len(segments) else duration
        covered=start
        for left,right in intervals:
            if left<=covered+0.05:covered=max(covered,right)
        if covered>=end-0.05:
            qa['observations'].append({**flag,'kind':'measured_silence_gap','start':start,'end':end})
        else:retained.append(flag)
    qa['flags']=retained


def preflight(config,runner=subprocess.run):
    """Inspect files, SQLite, versions and CLI capabilities, never open media.

    Preparation readiness is separate from authorization. Network publication
    access is audited separately, not silently treated as verified here.
    """
    checks={};problems=[]
    for name,args in [('ffmpeg',['-version']),('ffprobe',['-version']),('rclone',['version']),
                      ('whisper',["--version"])]:
        executable=str(config.binary) if name=='whisper' else shutil.which(name)
        entry:dict={'available':bool(executable and Path(executable).is_file())}
        if entry['available']:
            try:
                result=runner([executable,*args],check=True,capture_output=True,text=True,timeout=30)
                entry['version']=(result.stdout or result.stderr or '').splitlines()[0]
            except (OSError,subprocess.SubprocessError,IndexError):entry['available']=False
        if not entry['available']:problems.append(f'{name} unavailable')
        checks[name]=entry
    if checks['whisper']['available']:
        try:
            result=runner([str(config.binary),'--help'],check=True,capture_output=True,text=True,timeout=30)
            help_text=(result.stdout or '')+(result.stderr or '')
            missing=[flag for flag in ('-ojf','-nth','-et','-lpt','-tpi','-nf','-bs') if flag not in help_text]
            checks['whisper']['missing_flags']=missing
            if missing:problems.append('required whisper flags unavailable')
        except (OSError,subprocess.SubprocessError):problems.append('whisper help failed')
    digest=identity(config.model)
    if not digest or (config.model_sha256 and digest!=config.model_sha256):problems.append('model integrity failed')
    eligible=largest=invalid=0
    try:
        with closing(FOStore(config.db,readonly=True).conn) as c:
            eligible=c.execute("SELECT COUNT(*) FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id AND l.version=j.version JOIN lesson_video_sources s ON s.lesson_id=j.lesson_id WHERE j.state='queued' AND l.present=1 AND s.available=1 AND s.revision=CAST(j.version AS TEXT) AND s.remote_path IS NOT NULL").fetchone()[0]
            largest=c.execute('SELECT COALESCE(MAX(size),0) FROM lesson_video_sources WHERE available=1').fetchone()[0]
            invalid=c.execute("SELECT count(*) FROM lesson_video_sources WHERE available=1 AND (remote_path IS NULL OR remote_path NOT LIKE 'onedrive:Federal Online/%' OR size IS NULL OR size<=0)").fetchone()[0]
            if invalid:problems.append('unclassified or invalid sources')
    except (sqlite3.Error,OSError):
        eligible=largest=invalid=0
        problems.append('database unavailable or required schema missing')
    free=None
    try:
        free=shutil.disk_usage(config.state).free
        if free<RESERVE+largest+100*1024**2:problems.append('insufficient storage reserve')
    except OSError:problems.append('state storage unavailable')
    available=None
    if Path('/proc/meminfo').exists():
        entries={line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines()}
        available=int(entries['MemAvailable'].split()[0])*1024
        if available<12*1024**3:problems.append('less than 12 GiB RAM available')
    return {'ready':not problems,'problems':problems,'dependencies':checks,
            'model_sha256':digest,'model_expected_sha256':config.model_sha256,
            'runtime_sha256':identity(config.binary),'parameters':config.parameters(),
            'eligible_jobs':eligible,'invalid_sources':invalid,
            'storage':{'free_bytes':free,'reserve_bytes':RESERVE,'largest_source_bytes':largest},
            'resources':{'cpu_count':os.cpu_count(),'threads':config.threads,'memory_available_bytes':available,
                         'service_memory_max_bytes':12*1024**3,'service_cpu_quota_percent':300},
            'publication':{'source_root':'onedrive:Federal Online/',
                           'target':'onedrive:Study Hub/Federal Online/Transcripts/generated_v2',
                           'remote_access_verified':False},'inference_executed':False}


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
        self.c.execute('CREATE TABLE IF NOT EXISTS transcription_rr_cursor(id INTEGER PRIMARY KEY CHECK(id=1),last_discipline TEXT,cycle INTEGER,updated_at REAL)')
        self.c.execute('INSERT OR IGNORE INTO transcription_rr_cursor VALUES(1,NULL,0,0)')
        self.c.execute('CREATE TABLE IF NOT EXISTS transcription_breaker(fingerprint TEXT PRIMARY KEY,consecutive_failures INTEGER,consecutive_reviews INTEGER,opened_at REAL,reason TEXT)')
        self.c.commit()

    def catalog_order(self):
        """item_id -> portal 'ordem' from the current catalog (cached per mtime set)."""
        files=sorted((self.cfg.state/'catalog/courses').glob('*/aulas_index.json')) if (self.cfg.state/'catalog/courses').is_dir() else []
        key=tuple((str(f),f.stat().st_mtime_ns) for f in files)
        if getattr(self,'_order_key',None)!=key:
            order={}
            for f in files:
                try:items=json.loads(f.read_text()).get('aulas',[])
                except (OSError,ValueError):continue
                for x in items:
                    if x.get('item_id') and str(x.get('ordem','')).isdigit():order[x['item_id']]=int(x['ordem'])
            self._order,self._order_key=order,key
        return self._order

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

    def lease(self,lesson_id=None):
        now=time.time()
        self.c.execute('BEGIN IMMEDIATE')
        try:
            self.c.execute("UPDATE transcription_jobs SET state='superseded' WHERE state='queued' AND EXISTS(SELECT 1 FROM lessons l WHERE l.lesson_id=transcription_jobs.lesson_id AND l.version!=transcription_jobs.version)")
            self.c.execute("UPDATE transcription_jobs SET state='done',progress=1 WHERE state='queued' AND EXISTS(SELECT 1 FROM transcripts t WHERE t.lesson_id=transcription_jobs.lesson_id AND t.version=transcription_jobs.version AND t.corpus=?)",(ACCEPTED_CORPUS,))
            rows=self.c.execute("SELECT j.*,l.subject,l.front,l.module,l.title,l.item_id,s.remote_path,s.size FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id AND l.version=j.version JOIN lesson_video_sources s ON s.lesson_id=j.lesson_id WHERE j.state='queued' AND COALESCE(j.retry_at,0)<=? AND j.attempts<j.max_attempts AND l.present=1 AND s.available=1 AND CAST(j.version AS TEXT)=s.revision AND s.remote_path IS NOT NULL AND (? IS NULL OR j.lesson_id=?) AND NOT EXISTS(SELECT 1 FROM transcription_jobs busy JOIN lesson_video_sources bs ON bs.lesson_id=busy.lesson_id WHERE busy.state='leased' AND bs.remote_path=s.remote_path)",(now,lesson_id,lesson_id)).fetchall()
            cursor=self.c.execute('SELECT * FROM transcription_rr_cursor WHERE id=1').fetchone()
            row=choose([dict(r,ordem=self.catalog_order().get(r['item_id'])) for r in rows],cursor['last_discipline'])
            if row is None:self.c.commit();return None
            self.c.execute("UPDATE transcription_jobs SET state='leased',attempts=attempts+1,lease_owner=?,lease_until=?,updated_at=? WHERE lesson_id=? AND version=?",(self.owner,now+7*86400,str(now),row['lesson_id'],row['version']))
            name=discipline(row)
            wrapped=cursor['last_discipline'] is not None and discipline_key(name)<=discipline_key(cursor['last_discipline'])
            self.c.execute('UPDATE transcription_rr_cursor SET last_discipline=?,cycle=cycle+?,updated_at=? WHERE id=1',(name,int(wrapped),now))
            self.c.commit();return dict(row)
        except BaseException:self.c.rollback();raise

    def command(self,cmd,timeout=7200):
        # Raw stderr/command arguments stay private; no signed URLs in logs.
        return self.runner([str(x) for x in cmd],check=True,capture_output=True,text=True,timeout=timeout)

    def current_source(self,job):
        lesson=self.store.get_lesson(job['lesson_id'])
        source=self.c.execute('SELECT * FROM lesson_video_sources WHERE lesson_id=?',(job['lesson_id'],)).fetchone()
        if not lesson or not lesson['present'] or lesson['version']!=job['version'] or not source or not source['available'] or source['revision']!=str(job['version']):raise SourceChanged('source revision no longer current')
        if not str(source['remote_path']).startswith('onedrive:Federal Online/') or '..' in Path(source['remote_path']).parts:raise ValueError('source outside classified FO remote')
        return lesson,dict(source)

    def pipeline(self,job,work):
        cfg=self.cfg;lesson,source=self.current_source(job)
        started=time.time()
        checkout=cfg.binary.parent.parent.parent
        runtime_commit=None
        if (checkout/'.git').exists():
            runtime_commit=self.command(['git','-C',checkout,'rev-parse','HEAD'],timeout=30).stdout.strip()
        provenance={'model_sha256':identity(cfg.model),'runtime_sha256':identity(cfg.binary),
                    'runtime_commit':runtime_commit,
                    'runtime_libraries':{p.name:identity(p) for p in sorted(cfg.binary.parent.glob('*.so*')) if p.is_file()},
                    'parameters':cfg.parameters()}
        fingerprint=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
        size=int(source.get('size') or 0)
        if size<=0 or self.free_bytes()<RESERVE+size+100*1024**2:raise RuntimeError('storage budget or source size invalid')
        video=work/'source.mp4'
        self.command(['rclone','copyto',source['remote_path'],video,'--retries','3','--transfers','1',
                      '--max-transfer',f'{size+1024**2}B','--cutoff-mode','HARD'])
        if video.stat().st_size!=size:raise RuntimeError('source download size mismatch')
        source_sha256=file_sha256(video)
        probe=self.command(['ffprobe','-v','error','-show_entries','format=duration','-of','json',video],timeout=60)
        duration=float(json.loads(probe.stdout)['format']['duration'])
        if not math.isfinite(duration) or duration<=0 or duration>24*3600:raise ValueError('invalid source duration')
        expected=lesson.get('duration_s')
        if expected and abs(duration-float(expected))>max(5,float(expected)*0.05):raise ValueError('source duration mismatch')
        chunks=[];acoustic_flags=[];raw_flags=[];offset=0.0
        # Reuse only after byte identity, never a shared title, size or remote path.
        # The video is still downloaded to prove identity; no persistent video cache.
        evidence=cfg.state/'transcripts/evidence'/source_sha256/fingerprint
        evidence.mkdir(parents=True,exist_ok=True)
        queue=TranscriptionQueue(self.store)
        while offset<duration:
            if not self.gate_fn()['allowed']:raise RuntimeError('authorization revoked')
            if self.free_bytes()<RESERVE+100*1024**2:raise RuntimeError('storage reserve reached')
            length=min(cfg.chunk_s,duration-offset);audio=work/'chunk.wav';prefix=work/'asr'
            checkpoint=evidence/f'{offset:.3f}-{length:.3f}.json.gz'
            cached=None;rejected=None
            if checkpoint.is_file():
                try:
                    if checkpoint.is_symlink():raise RuntimeError('checkpoint symlink refused')
                    cached=json.loads(gzip.decompress(checkpoint.read_bytes()))
                    validate_checkpoint(cached,source_sha256,fingerprint,offset,length)
                except (OSError,EOFError,zlib.error,ValueError,TypeError,KeyError,AttributeError,OverflowError) as exc:
                    quarantine=checkpoint.with_name(checkpoint.name+'.rejected-'+uuid.uuid4().hex)
                    checkpoint.rename(quarantine)
                    rejected={'path':str(quarantine),'reason':type(exc).__name__,'rejected_at':time.time()}
                    cached=None
            if cached is not None:
                payload=cached['raw'];intervals=cached['silence']
                # V1 authenticated raw/schema/bounds only, not logs or timings.
                decoding=cached.get('decoding') if cached['schema_version']==2 else None
            else:
                if not self.gate_fn()['allowed']:raise RuntimeError('authorization revoked')
                self.command(['ffmpeg','-nostdin','-y','-threads','1','-ss',str(offset),'-i',video,'-t',str(length),'-ar','16000','-ac','1','-c:a','pcm_s16le','-threads','1',audio])
                silence=self.command(['ffmpeg','-nostdin','-threads','1','-i',audio,'-af','silencedetect=noise=-40dB:d=1','-f','null','-'])
                command=[cfg.binary,'-m',cfg.model,'-f',audio,'-l','pt','-t',str(cfg.threads),'-bs',str(cfg.beam_size),'-bo','5','-mc',str(cfg.max_context),'-tp','0','-tpi','0.2' if cfg.temperature_fallback else '0','-nth','0.6','-et','2.4','-lpt','-1','-ng','-ojf','-of',prefix]
                if not cfg.temperature_fallback:command.append('-nf')
                decode_started=time.monotonic()
                decoded=None;failure=None;raw_text=None
                try:
                    decoded=self.command(command,timeout=172800)
                    raw_text=prefix.with_suffix('.json').read_text()
                except Exception as exc:
                    failure=exc
                finally:
                    def log_text(value):
                        return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''
                    logs=decoded if decoded is not None else failure
                    decoding={'wall_s':time.monotonic()-decode_started,
                              'stderr':log_text(getattr(logs,'stderr',None)),
                              'stdout':log_text(getattr(logs,'stdout',None))}
                    created_at=time.time()
                    try:
                        raw_path=prefix.with_suffix('.json')
                        if raw_text is None and raw_path.is_file():raw_text=raw_path.read_text(errors='replace')
                        # Preserve partial/missing output while the temporary
                        # directory still exists, including a failed decoder.
                        atomic_json(evidence/f'{offset:.3f}-{length:.3f}.decoder-{uuid.uuid4().hex}.json.gz',
                                    {'raw_text':raw_text,'created_at':created_at,'rejected_cache':rejected,
                                     'source_sha256':source_sha256,'fingerprint':fingerprint,
                                     'offset_s':offset,'duration_s':length,'decoding':decoding,
                                     'failure_type':type(failure).__name__ if failure else None})
                    except Exception as diagnostic_exc:
                        if failure is None:raise
                        setattr(failure,'fo_evidence_error',type(diagnostic_exc).__name__)
                if failure is not None:raise failure
                if raw_text is None:raise ValueError('decoder output unavailable')
                payload=json.loads(raw_text)
                intervals=silence_intervals(silence.stderr or '',length)
                record={'schema_version':2,'source_sha256':source_sha256,'fingerprint':fingerprint,
                        'offset_s':offset,'duration_s':length,'raw':payload,'silence':intervals,
                        'created_at':created_at,'rejected_cache':rejected,
                        'decoder_command':[str(x) for x in command],'decoding':decoding}
                record['evidence_sha256']=evidence_checksum(record)
                atomic_json(checkpoint,record)
            current=parse_whisper(payload,offset)
            chunk_qa=qa_segments(current,offset+length)
            for flag in chunk_qa['flags']:
                if flag['kind']!='silence_gap':
                    row=current[flag['idx']]
                    end_row=current[flag.get('end_idx',flag['idx'])]
                    raw_flags.append({**flag,'origin':'decoder','chunk_idx':len(chunks),
                                      'start':row['start'],'end':end_row['end']})
            for row in current:
                for start,end in intervals:
                    if row['text'] and row['start']>=offset+start and row['end']<=offset+end:acoustic_flags.append({'kind':'text_during_measured_silence','start':row['start'],'end':row['end']})
            chunks.append({'offset_s':offset,'duration_s':length,'segments':current,'silence':intervals,'raw':payload,'reused':cached is not None,'decoding':decoding,'qa':chunk_qa})
            queue.progress(job['lesson_id'],job['version'],self.owner,min(1,(offset+length)/duration))
            with self.c:self.c.execute('UPDATE transcription_jobs SET lease_until=?,updated_at=? WHERE lesson_id=? AND version=? AND lease_owner=?',(time.time()+7*86400,str(time.time()),job['lesson_id'],job['version'],self.owner))
            audio.unlink(missing_ok=True);prefix.with_suffix('.json').unlink(missing_ok=True)
            if offset+length>=duration:break
            offset+=cfg.chunk_s-cfg.overlap_s
        from .stitching import stitch_chunks
        stitched=stitch_chunks(chunks)
        segments=stitched['segments']
        qa=qa_segments(segments,duration)
        reconcile_silent_gaps(qa,segments,chunks,duration)
        for flag in qa['flags']:flag['origin']='stitched_text'
        qa['flags'].extend({**flag,'origin':'stitching'} for flag in stitched['flags'])
        qa['flags'].extend(raw_flags)
        qa['flags'].extend(acoustic_flags)
        if not segments:qa['flags'].append({'kind':'empty_output'})
        if cfg.review_only:qa['flags'].append({'kind':'pilot_manual_review_required','start':0,'end':duration})
        qa['passed']=not qa['flags'];qa['metrics']['flag_count']=len(qa['flags'])
        _,latest=self.current_source(job)
        if any(latest[k]!=source[k] for k in ('remote_path','revision','size','available')):raise SourceChanged('source changed during inference')
        artifact={'lesson_id':job['lesson_id'],'version':job['version'],'model':'whisper-large-v3','model_path':str(cfg.model),'runtime_path':str(cfg.binary),**provenance,'source_size':size,'source_sha256':source_sha256,'source_revision':source['revision'],'source_remote_path':source['remote_path'],'duration_s':duration,'created_at':time.time(),'elapsed_s':time.time()-started,'corpus':ACCEPTED_CORPUS,'qa':qa,'chunks':chunks,'segments':segments,'stitching':stitched.get('decisions',[])}
        status='validated' if qa['passed'] else 'review'
        artifact['qa_policy_version']=2
        path=cfg.state/'transcripts'/('private' if qa['passed'] else 'review')/job['lesson_id']/f"v{job['version']}.json.gz"
        atomic_json(path,artifact)
        if qa['passed']:
            lock=cfg.state/'locks/transcript-publication.lock';lock.parent.mkdir(parents=True,exist_ok=True)
            with lock.open('a+') as handle:
                fcntl.flock(handle,fcntl.LOCK_EX)
                self.current_source(job)
                public={k:artifact[k] for k in ('lesson_id','version','corpus','segments')}
                public['qa']={'passed':True}
                atomic_json(cfg.state/'transcripts/generated_v2'/job['lesson_id']/f"v{job['version']}.json",public)
                self.store.add_transcript(job['lesson_id'],job['version'],segments,artifact['model'],ACCEPTED_CORPUS,True,qa)
        else:
            with self.c:
                for flag in qa['flags']:
                    idx=min(int(flag.get('idx',0)),max(0,len(segments)-1))
                    seg=segments[idx] if segments else {'start':0,'end':duration}
                    start=max(0,float(flag.get('start',seg['start']))-2);end=min(duration,float(flag.get('end',seg['end']))+2)
                    self.c.execute("INSERT OR IGNORE INTO focused_reviews VALUES(?,?,?,?,?,'pending_manual_review')",(job['lesson_id'],job['version'],start,end,flag['kind']))
        return status

    def complete_aliases(self,job,status):
        # Compare against the leased identity, not a newly discovered object.
        _,source=self.current_source(job)
        if source['remote_path']!=job['remote_path'] or source['size']!=job['size']:raise SourceChanged('source changed before alias completion')
        aliases=self.c.execute("SELECT j.lesson_id,j.version FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id AND l.version=j.version JOIN lesson_video_sources s ON s.lesson_id=j.lesson_id WHERE j.state='queued' AND l.present=1 AND s.available=1 AND s.revision=CAST(j.version AS TEXT) AND s.remote_path=? AND s.size=?",(job['remote_path'],job['size'])).fetchall()
        transcript=self.c.execute('SELECT * FROM transcripts WHERE lesson_id=? AND version=?',(job['lesson_id'],job['version'])).fetchone()
        segments=[dict(r) for r in self.c.execute('SELECT start,end,text FROM transcript_segments WHERE lesson_id=? AND version=? ORDER BY idx',(job['lesson_id'],job['version']))]
        for alias in aliases:
            if status=='validated':
                if not transcript:continue
                self.store.add_transcript(alias['lesson_id'],alias['version'],segments,transcript['model'],ACCEPTED_CORPUS,True,json.loads(transcript['qa_json']))
            else:
                with self.c:self.c.execute('INSERT OR IGNORE INTO focused_reviews SELECT ?,?,start,end,reason,state FROM focused_reviews WHERE lesson_id=? AND version=?',(alias['lesson_id'],alias['version'],job['lesson_id'],job['version']))
            with self.c:self.c.execute("UPDATE transcription_jobs SET state=?,progress=1,lease_owner=NULL,lease_until=NULL,updated_at=? WHERE lesson_id=? AND version=? AND state='queued'",('done' if status=='validated' else 'review',str(time.time()),alias['lesson_id'],alias['version']))

    def fingerprint(self):
        return hashlib.sha256(json.dumps({'parameters':self.cfg.parameters(),'model_sha256':identity(self.cfg.model),'binary_sha256':identity(self.cfg.binary) if Path(self.cfg.binary).is_file() else None},sort_keys=True).encode()).hexdigest()

    def record_outcome(self,fingerprint,outcome):
        row=self.c.execute('SELECT * FROM transcription_breaker WHERE fingerprint=?',(fingerprint,)).fetchone()
        failures=(row['consecutive_failures'] if row else 0)+1 if outcome=='failure' else 0
        reviews=(row['consecutive_reviews'] if row else 0)+1 if outcome=='review' else 0
        reason='consecutive_failures' if failures>=max(1,int(os.environ.get('FO_ASR_BREAKER_FAILURES','3'))) else ('consecutive_reviews' if reviews>=max(1,int(os.environ.get('FO_ASR_BREAKER_REVIEWS','5'))) else None)
        with self.c:self.c.execute('INSERT OR REPLACE INTO transcription_breaker VALUES(?,?,?,?,?)',(fingerprint,failures,reviews,time.time() if reason else None,reason))

    def run_once(self,lesson_id=None):
        g=self.gate_fn()
        if not g['allowed']:return {'state':'blocked','gate':g}
        fingerprint=self.fingerprint()
        breaker=self.c.execute('SELECT * FROM transcription_breaker WHERE fingerprint=?',(fingerprint,)).fetchone()
        if breaker and breaker['opened_at'] is not None:return {'state':'breaker_open',**dict(breaker)}
        largest=self.c.execute('SELECT COALESCE(MAX(size),0) FROM lesson_video_sources WHERE available=1').fetchone()[0]
        if self.free_bytes()<RESERVE+largest+100*1024**2:
            return {'state':'paused_storage','reserve_bytes':RESERVE,'largest_source_bytes':largest}
        job=self.lease(lesson_id)
        if job is None:return {'state':'idle'}
        temp=self.cfg.state/'tmp/transcription';temp.mkdir(parents=True,exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix='job-',dir=temp) as folder:
                (Path(folder)/'.worker-owned').write_text('study-hub-fo-worker')
                status=self.pipeline(job,Path(folder))
            with self.c:self.c.execute("UPDATE transcription_jobs SET state=?,progress=1,lease_owner=NULL,lease_until=NULL,updated_at=? WHERE lesson_id=? AND version=? AND lease_owner=?",('done' if status=='validated' else 'review',str(time.time()),job['lesson_id'],job['version'],self.owner))
        except Exception as exc:
            return self._failed(job,fingerprint,exc)
        self.record_outcome(fingerprint,status)
        result={'state':status,'lesson_id':job['lesson_id'],'version':job['version']}
        try:
            self.complete_aliases(job,status)
        except Exception as exc:
            # The leased job succeeded; queued aliases stay queued and later reuse
            # the byte-identity evidence cache without a new decode.
            result['alias_error_type']=type(exc).__name__
        return result

    def _failed(self,job,fingerprint,exc):
        # Gate, storage and source-identity events are infrastructure, not ASR failures.
        infrastructure=isinstance(exc,SourceChanged) or str(exc) in {'authorization revoked','storage reserve reached','storage budget or source size invalid'}
        if not infrastructure:self.record_outcome(fingerprint,'failure')
        diagnostic_error=getattr(exc,'fo_evidence_error',None)
        if isinstance(exc,(subprocess.CalledProcessError,subprocess.TimeoutExpired)):
            # Full diagnostics may contain academic text or private paths.
            # Preserve outside the publication allowlist, never in DB/logs.
            def text(value):
                return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value
            try:
                atomic_json(self.cfg.state/'transcripts/errors'/job['lesson_id']/
                            f"v{job['version']}-{uuid.uuid4().hex}.json.gz",
                            {'lesson_id':job['lesson_id'],'version':job['version'],
                             'error_type':type(exc).__name__,'created_at':time.time(),
                             'command':[str(x) for x in exc.cmd],
                             'returncode':getattr(exc,'returncode',None),
                             'stdout':text(exc.stdout),'stderr':text(exc.stderr)})
            except Exception as diagnostic_exc:
                diagnostic_error=type(diagnostic_exc).__name__
        current=self.c.execute('SELECT attempts,max_attempts FROM transcription_jobs WHERE lesson_id=? AND version=?',(job['lesson_id'],job['version'])).fetchone()
        state='superseded' if isinstance(exc,SourceChanged) else ('failed' if current['attempts']>=current['max_attempts'] else 'queued')
        with self.c:self.c.execute('UPDATE transcription_jobs SET state=?,retry_at=?,last_error=?,lease_owner=NULL,lease_until=NULL WHERE lesson_id=? AND version=?',(state,time.time()+min(86400,60*2**current['attempts']),type(exc).__name__,job['lesson_id'],job['version']))
        result={'state':'retry' if state=='queued' else state,'error_type':type(exc).__name__,'lesson_id':job['lesson_id']}
        if diagnostic_error:result['diagnostic_error_type']=diagnostic_error
        return result


def worker_status(cfg):
    with closing(FOStore(cfg.db,readonly=True).conn) as c:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts={r[0]:r[1] for r in c.execute('SELECT state,count(*) FROM transcription_jobs GROUP BY state')}
        leased=[{**dict(r),'discipline':discipline(dict(r))} for r in c.execute("SELECT j.lesson_id,j.version,l.subject,l.front,l.module FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id WHERE j.state='leased' ORDER BY j.lesson_id")]
        cursor=c.execute('SELECT last_discipline FROM transcription_rr_cursor WHERE id=1').fetchone() if 'transcription_rr_cursor' in tables else None
        rows=[]
        if 'lesson_video_sources' in tables:
            retry='COALESCE(j.retry_at,0)' if 'retry_at' in {r[1] for r in c.execute('PRAGMA table_info(transcription_jobs)')} else '0'
            rows=[dict(r) for r in c.execute(f"SELECT j.lesson_id,l.subject,l.front,l.module,l.title FROM transcription_jobs j JOIN lessons l ON l.lesson_id=j.lesson_id AND l.version=j.version JOIN lesson_video_sources s ON s.lesson_id=j.lesson_id WHERE j.state='queued' AND {retry}<=? AND j.attempts<j.max_attempts AND l.present=1 AND s.available=1 AND s.revision=CAST(j.version AS TEXT) AND s.remote_path IS NOT NULL AND NOT EXISTS(SELECT 1 FROM transcription_jobs busy JOIN lesson_video_sources bs ON bs.lesson_id=busy.lesson_id WHERE busy.state='leased' AND bs.remote_path=s.remote_path)",(time.time(),))]
        next_job=choose(rows,cursor[0] if cursor else None)
        breakers=[dict(r) for r in c.execute('SELECT * FROM transcription_breaker ORDER BY fingerprint')] if 'transcription_breaker' in tables else []
    return {'leased':leased,'next_discipline':discipline(next_job) if next_job else None,'counts':counts,'breaker':breakers,'free_bytes':shutil.disk_usage(cfg.state).free}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only',action='store_true');mode.add_argument('--run',action='store_true')
    mode.add_argument('--reset-breaker',action='store_true');mode.add_argument('--status',action='store_true')
    once=p.add_mutually_exclusive_group();once.add_argument('--once',action='store_true');once.add_argument('--loop',action='store_true')
    p.add_argument('--lesson-id',help='Restrict an authorized pilot to exactly this queued lesson')
    a=p.parse_args(argv);cfg=Config.from_env()
    if a.status:
        print(json.dumps(worker_status(cfg)));return 0
    if a.reset_breaker:
        with closing(FOStore(cfg.db).conn) as c:
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='transcription_breaker'").fetchone():
                with c:c.execute('DELETE FROM transcription_breaker')
        print(json.dumps({'state':'breaker_reset'}));return 0
    g=gate(cfg)
    if a.lesson_id and a.loop:p.error('--lesson-id cannot be combined with --loop')
    if a.check_only:
        counts={}
        try:
            with closing(FOStore(cfg.db,readonly=True).conn) as c:
                counts={r[0]:r[1] for r in c.execute('SELECT state,count(*) FROM transcription_jobs GROUP BY state')}
        except (sqlite3.Error,OSError):pass
        print(json.dumps({'gate':g,'queue':counts,'preflight':preflight(cfg),'inference_executed':False}));return 0
    if not g['allowed']:print(json.dumps({'state':'blocked','gate':g}));return 3
    preparation=preflight(cfg)
    if not preparation['ready']:
        print(json.dumps({'state':'blocked','preflight':preparation}));return 3
    locks=cfg.state/'locks';locks.mkdir(parents=True,exist_ok=True)
    with (locks/'transcription.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('transcription worker already owns lock',file=sys.stderr);return 4
        worker=Worker(cfg);worker.recover()
        while True:
            result=worker.run_once(a.lesson_id);print(json.dumps(result),flush=True)
            if result['state']=='breaker_open':return 5
            if result['state']=='blocked':return 3
            if not a.loop:return 0
            if result['state'] in ('idle','retry','failed','paused_storage'):time.sleep(60)


if __name__=='__main__':raise SystemExit(main())

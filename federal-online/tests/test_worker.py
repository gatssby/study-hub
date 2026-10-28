"""Worker tests inject all subprocesses; no audio or model inference is executed."""
import json
import gzip
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def setup(tmp_path):
    from fo_hub.store import FOStore
    from fo_hub.transcription import TranscriptionQueue
    from fo_hub.worker import Config,Worker
    store=FOStore(tmp_path/'hub.db')
    store.sync_lessons([{'course_id':'c','media_id':'m','title':'Aula','media_type':'video','duration_s':30}])
    lesson=store.list_lessons()[0]
    TranscriptionQueue(store).enqueue(lesson['lesson_id'],1)
    config=Config(state=tmp_path,db=tmp_path/'hub.db',binary=tmp_path/'whisper-cli',model=tmp_path/'large-v3.bin',auth=tmp_path/'auth',marker=tmp_path/'marker')
    return store,lesson,config


def test_default_gate_blocks_all_subprocess_and_queue_leasing(tmp_path):
    from fo_hub.worker import Worker
    store,lesson,config=setup(tmp_path)
    w=Worker(config,store=store,runner=lambda *a,**k:pytest.fail('subprocess invoked with gate closed'))
    result=w.run_once()
    assert result['state']=='blocked'
    assert store.conn.execute('select state,attempts from transcription_jobs').fetchone()['attempts']==0


def test_gate_requires_linux_marker_phrase_binaries_and_explicit_true(tmp_path):
    from fo_hub.worker import gate
    from fo_hub.transcription import AUTH_PHRASE
    store,lesson,cfg=setup(tmp_path)
    assert not gate(cfg,{},platform='linux')['allowed']
    cfg.binary.write_text('fake binary');cfg.binary.chmod(0o755);cfg.model.write_text('fake weights')
    cfg.auth.write_text(AUTH_PHRASE);cfg.marker.touch()
    assert gate(cfg,{'TRANSCRIPTION_ENABLED':'true'},platform='linux')['allowed']
    assert not gate(cfg,{'TRANSCRIPTION_ENABLED':'true'},platform='darwin')['allowed']
    cfg.auth.write_text('wrong')
    assert not gate(cfg,{'TRANSCRIPTION_ENABLED':'true'},platform='linux')['allowed']


def test_source_must_be_available_and_match_both_versions(tmp_path):
    from fo_hub.worker import Worker
    store,lesson,cfg=setup(tmp_path)
    w=Worker(cfg,store=store,gate_fn=lambda:{'allowed':True,'reasons':[]},runner=lambda *a,**k:pytest.fail('ineligible source consumed'))
    assert w.run_once()['state']=='idle'
    store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',(lesson['lesson_id'],'onedrive:Federal Online/a.mp4','2',9,1,'now'));store.conn.commit()
    assert w.run_once()['state']=='idle'
    store.conn.execute("update lesson_video_sources set revision='1',available=0");store.conn.commit()
    assert w.run_once()['state']=='idle'


def test_fake_pipeline_publishes_only_passed_current_version_and_cleans_temps(tmp_path):
    from fo_hub.worker import Worker
    store,lesson,cfg=setup(tmp_path)
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[0]=='rclone':Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0]=='ffprobe':return SimpleNamespace(stdout=json.dumps({'format':{'duration':'30'}}),stderr='',returncode=0)
        elif cmd[0]=='ffmpeg' and cmd[-1].endswith('.wav'):Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0]==str(cfg.binary):
            prefix=cmd[cmd.index('-of')+1]
            Path(prefix+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':0,'to':2000},'text':'A célula tem núcleo.'}]}))
        return SimpleNamespace(stdout='',stderr='',returncode=0)
    w=Worker(cfg,store=store,runner=run,gate_fn=lambda:{'allowed':True,'reasons':[]},free_bytes=lambda:20*1024**3)
    store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',(lesson['lesson_id'],'onedrive:Federal Online/a.mp4','1',9,1,'now'));store.conn.commit()
    result=w.run_once()
    # A 28-second uncovered tail is deliberately flagged for review, not published.
    assert result['state']=='review'
    assert store.get_transcript(lesson['lesson_id']) is None
    artifacts=list((tmp_path/'transcripts/review').rglob('*.json.gz'))
    assert artifacts and 'A célula' in gzip.decompress(artifacts[0].read_bytes()).decode()
    artifact=json.loads(gzip.decompress(artifacts[0].read_bytes()))
    assert artifact['chunks'][0]['decoding']['wall_s']>=0
    assert artifact['chunks'][0]['decoding']['stderr']==''
    assert not list((tmp_path/'tmp/transcription').glob('*'))
    assert any(cmd[0]==str(cfg.binary) for cmd in calls)
    assert '--max-size' in next(cmd for cmd in calls if cmd[0]=='rclone')


def test_whisper_offsets_are_milliseconds_and_overlap_kept_for_review():
    from fo_hub.worker import parse_whisper
    rows=parse_whisper({'transcription':[{'offsets':{'from':2000,'to':4500},'text':'núcleo'}]},offset=600)
    assert rows==[{'start':602.0,'end':604.5,'text':'núcleo'}]


def test_insufficient_disk_pauses_without_download_or_consuming_attempts(tmp_path):
    from fo_hub.worker import Worker
    store,lesson,cfg=setup(tmp_path)
    w=Worker(cfg,store=store,runner=lambda *a,**k:pytest.fail('disk guard failed'),gate_fn=lambda:{'allowed':True},free_bytes=lambda:1)
    store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',(lesson['lesson_id'],'onedrive:Federal Online/a.mp4','1',9,1,'now'));store.conn.commit()
    assert w.run_once()['state']=='paused_storage'
    row=store.conn.execute('select * from transcription_jobs').fetchone()
    assert row['state']=='queued' and row['attempts']==0 and row['lease_owner'] is None
    assert w.run_once()['state']=='paused_storage'


def test_recovery_removes_only_marked_worker_temporary_directories(tmp_path):
    from fo_hub.worker import Worker
    store,lesson,cfg=setup(tmp_path)
    root=tmp_path/'tmp/transcription';owned=root/'job-owned';unknown=root/'job-unknown'
    owned.mkdir(parents=True);unknown.mkdir()
    (owned/'.worker-owned').write_text('study-hub-fo-worker')
    (owned/'source.mp4').write_bytes(b'partial')
    (unknown/'important.txt').write_text('preserve unknown')
    w=Worker(cfg,store=store)
    w.recover()
    assert not owned.exists()
    assert (unknown/'important.txt').read_text()=='preserve unknown'


@pytest.mark.parametrize('silence,review_only,expected',[('',False,'validated'),('silence_start: 0\nsilence_end: 30',False,'review'),('',True,'review')])
def test_passed_output_is_published_but_text_in_measured_silence_is_reviewed(tmp_path,silence,review_only,expected):
    from fo_hub.worker import Worker
    store,lesson,cfg=setup(tmp_path)
    cfg.review_only=review_only
    def run(cmd,**kwargs):
        if cmd[0]=='rclone':Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0]=='ffprobe':return SimpleNamespace(stdout=json.dumps({'format':{'duration':'30'}}),stderr='')
        elif cmd[0]=='ffmpeg' and cmd[-1].endswith('.wav'):Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0]==str(cfg.binary):Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':0,'to':30000},'text':'Conteúdo científico legítimo.'}]}))
        return SimpleNamespace(stdout='',stderr=silence)
    w=Worker(cfg,store=store,runner=run,gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',(lesson['lesson_id'],'onedrive:Federal Online/a.mp4','1',9,1,'now'));store.conn.commit()
    assert w.run_once()['state']==expected
    assert (store.get_transcript(lesson['lesson_id']) is not None)==(expected=='validated')
    if expected=='review':assert store.conn.execute('select count(*) from focused_reviews').fetchone()[0]>0


def test_pilot_review_only_is_loaded_without_changing_decoder_fingerprint(monkeypatch):
    from fo_hub.worker import Config
    baseline=Config.from_env().parameters()
    monkeypatch.setenv('FO_ASR_REVIEW_ONLY','true')
    cfg=Config.from_env()
    assert cfg.review_only is True
    assert cfg.parameters()==baseline

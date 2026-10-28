"""Synthetic scheduling tests: never execute ASR or network commands."""
import pytest
from fo_hub.store import FOStore
from fo_hub.transcription import TranscriptionQueue
from fo_hub.worker import Config, Worker


def worker(tmp_path, subjects):
    store=FOStore(tmp_path/'hub.db')
    store.sync_lessons([dict(course_id='c',media_id=str(i),subject=s,title=f'Aula {i+1}',media_type='video') for i,s in enumerate(subjects)])
    cfg=Config(tmp_path,tmp_path/'hub.db',tmp_path/'binary',tmp_path/'model')
    w=Worker(cfg,store=store,gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3,
             runner=lambda *a,**k:pytest.fail('real subprocess forbidden'))
    for row in store.conn.execute('SELECT * FROM lessons').fetchall():
        TranscriptionQueue(store).enqueue(row['lesson_id'],1)
        store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',(row['lesson_id'],'onedrive:Federal Online/'+row['lesson_id'],'1',9,1,'now'))
    store.conn.commit()
    return w


def discipline(w,job):
    return w.store.get_lesson(job['lesson_id'])['subject']


def test_round_robin_persists_across_recovery(tmp_path):
    w=worker(tmp_path,['Biologia']*4+['Física']*4+['Matemática']*4)
    assert discipline(w,w.lease())=='Biologia'
    w=Worker(w.cfg,store=w.store)
    w.recover()
    assert [discipline(w,w.lease()) for _ in range(5)]==['Física','Matemática','Biologia','Física','Matemática']


def test_small_discipline_not_starved_and_skips_empty(tmp_path):
    w=worker(tmp_path,['Biologia']*100+['Física'])
    assert [discipline(w,w.lease()) for _ in range(3)]==['Biologia','Física','Biologia']


@pytest.mark.parametrize('outcome,limit',[('error',3),('review',5)])
def test_breaker_opens(tmp_path,outcome,limit):
    w=worker(tmp_path,['Biologia']*8)
    def pipeline(job,work):
        if outcome=='error':raise RuntimeError('synthetic')
        return outcome
    w.pipeline=pipeline
    for _ in range(limit):w.run_once()
    assert w.run_once()['state']=='breaker_open'


def test_max_context(monkeypatch):
    monkeypatch.setenv('FO_ASR_MAX_CONTEXT','512')
    assert Config.from_env().parameters()['max_context']==512


@pytest.mark.parametrize('outcome',['validated','review'])
def test_alias_completion(tmp_path,outcome):
    from fo_hub.store import ACCEPTED_CORPUS
    w=worker(tmp_path,['Biologia','Física'])
    w.c.execute("UPDATE lesson_video_sources SET remote_path='onedrive:Federal Online/shared'");w.c.commit()
    segments=[dict(start=0,end=30,text='Conteúdo científico legítimo.')]
    def pipeline(job,work):
        if outcome=='validated':w.store.add_transcript(job['lesson_id'],1,segments,'fake',ACCEPTED_CORPUS,True,{'passed':True})
        else:
            with w.c:w.c.execute("INSERT INTO focused_reviews VALUES(?,1,0,30,'synthetic','pending_manual_review')",(job['lesson_id'],))
        assert w.lease() is None
        return outcome
    w.pipeline=pipeline
    assert w.run_once()['state']==outcome
    assert [r[0] for r in w.c.execute('SELECT state FROM transcription_jobs')]==['done' if outcome=='validated' else 'review']*2
    assert w.c.execute('SELECT COUNT(*) FROM '+('transcripts' if outcome=='validated' else 'focused_reviews')).fetchone()[0]==2


def test_reset_breaker_cli(tmp_path,monkeypatch,capsys):
    from fo_hub.worker import main
    w=worker(tmp_path,['Biologia'])
    for _ in range(3):w.record_outcome(w.fingerprint(),'failure')
    monkeypatch.setenv('STUDY_HUB_FO_DB',str(w.cfg.db))
    monkeypatch.setenv('FO_STATE_ROOT',str(tmp_path))
    assert main(['--reset-breaker'])==0
    assert w.c.execute('SELECT COUNT(*) FROM transcription_breaker').fetchone()[0]==0


def test_status_readonly(tmp_path,monkeypatch,capsys):
    import json
    from fo_hub.worker import main
    w=worker(tmp_path,['Biologia','Física'])
    w.lease()
    monkeypatch.setenv('STUDY_HUB_FO_DB',str(w.cfg.db))
    monkeypatch.setenv('FO_STATE_ROOT',str(tmp_path))
    before=w.c.total_changes
    assert main(['--status'])==0
    status=json.loads(capsys.readouterr().out)
    assert status['leased'][0]['discipline']=='Biologia'
    assert status['next_discipline']=='Física'
    assert w.c.total_changes==before


def test_retry_review_and_failed_do_not_block(tmp_path):
    w=worker(tmp_path,['Biologia']*4+['Física']*4)
    w.pipeline=lambda job,work:(_ for _ in ()).throw(RuntimeError('synthetic'))
    assert w.run_once()['state']=='retry'
    assert discipline(w,w.lease())=='Física'
    with w.c:w.c.execute("UPDATE transcription_jobs SET state='review' WHERE state='leased'")
    assert discipline(w,w.lease())=='Biologia'
    with w.c:w.c.execute("UPDATE transcription_jobs SET state='failed' WHERE state='leased'")
    assert discipline(w,w.lease())=='Física'


def test_deterministic_pure_scheduler():
    from fo_hub.scheduler import choose
    rows=[dict(lesson_id=str(i),subject=s,title=f'Aula {i}') for i,s in enumerate(['Matemática','Física','Biologia','Biologia'])]
    assert choose(rows)==choose(list(reversed(rows)))
    assert choose(rows,'Geografia')['subject']=='Matemática'
    assert choose([]) is None


def test_validated_resets_breaker_and_config_isolation(tmp_path):
    w=worker(tmp_path,['Biologia']*8)
    fp=w.fingerprint()
    w.record_outcome(fp,'failure');w.record_outcome(fp,'failure')
    w.pipeline=lambda job,work:'validated'
    assert w.run_once()['state']=='validated'
    row=w.c.execute('SELECT * FROM transcription_breaker').fetchone()
    assert row['consecutive_failures']==row['consecutive_reviews']==0
    for _ in range(3):w.record_outcome(fp,'failure')
    assert w.run_once()['state']=='breaker_open'
    w.cfg.max_context=512
    assert w.run_once()['state']=='validated'


@pytest.mark.parametrize('change',["size=10","available=0","revision='2'","remote_path='onedrive:Federal Online/changed'"])
def test_changed_alias_skipped(tmp_path,change):
    w=worker(tmp_path,['Biologia','Física'])
    with w.c:w.c.execute("UPDATE lesson_video_sources SET remote_path='onedrive:Federal Online/shared'")
    def pipeline(job,work):
        with w.c:w.c.execute('UPDATE lesson_video_sources SET '+change+' WHERE lesson_id!=?',(job['lesson_id'],))
        return 'review'
    w.pipeline=pipeline
    assert w.run_once()['state']=='review'
    assert sorted(r[0] for r in w.c.execute('SELECT state FROM transcription_jobs'))==['queued','review']


def test_cursor_transaction_rolls_back(tmp_path):
    w=worker(tmp_path,['Biologia','Física'])
    w.c.execute("CREATE TRIGGER refuse_lease BEFORE UPDATE ON transcription_jobs WHEN NEW.state='leased' BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    w.c.commit()
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):w.lease()
    assert w.c.execute('SELECT last_discipline FROM transcription_rr_cursor').fetchone()[0] is None
    w.c.execute('DROP TRIGGER refuse_lease');w.c.commit()
    assert discipline(w,w.lease())=='Biologia'


def test_source_changed_not_breaker_failure(tmp_path):
    from fo_hub.worker import SourceChanged
    w=worker(tmp_path,['Biologia']*5)
    w.pipeline=lambda job,work:(_ for _ in ()).throw(SourceChanged('synthetic'))
    for _ in range(4):assert w.run_once()['state']=='superseded'
    assert w.c.execute('SELECT COUNT(*) FROM transcription_breaker').fetchone()[0]==0


def test_loop_exits_five_on_open_breaker(tmp_path,monkeypatch,capsys):
    import json
    import fo_hub.worker as module
    w=worker(tmp_path,['Biologia'])
    monkeypatch.setattr(module.Config,'from_env',classmethod(lambda cls:w.cfg))
    monkeypatch.setattr(module,'gate',lambda cfg:{'allowed':True})
    monkeypatch.setattr(module,'preflight',lambda cfg:{'ready':True})
    for _ in range(3):w.record_outcome(w.fingerprint(),'failure')
    assert module.main(['--run','--loop'])==5
    assert json.loads(capsys.readouterr().out)['reason']=='consecutive_failures'
    assert w.c.execute('SELECT attempts FROM transcription_jobs').fetchone()[0]==0


def test_fake_decoder_max_context_and_alias_segments(tmp_path):
    import json
    from pathlib import Path
    from types import SimpleNamespace
    w=worker(tmp_path,['Biologia','Física'])
    w.cfg.max_context=512
    with w.c:w.c.execute("UPDATE lesson_video_sources SET remote_path='onedrive:Federal Online/shared'")
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[0]=='rclone':Path(cmd[3]).write_bytes(b'fakevideo')
        if cmd[0]=='ffprobe':return SimpleNamespace(stdout=json.dumps({'format':{'duration':30}}),stderr='')
        if cmd[0]==str(w.cfg.binary):
            assert cmd[cmd.index('-mc')+1]=='512'
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':0,'to':30000},'text':'Conteúdo científico legítimo.'}]}))
        return SimpleNamespace(stdout='',stderr='')
    w.runner=run
    assert w.run_once()['state']=='validated'
    assert w.run_once()['state']=='idle'
    assert sum(c[0]=='rclone' for c in calls)==1
    assert sum(c[0]==str(w.cfg.binary) for c in calls)==1
    assert [r[0] for r in w.c.execute('SELECT text FROM transcript_segments')]==['Conteúdo científico legítimo.']*2


def test_pedagogical_order(tmp_path):
    w=worker(tmp_path,['Biologia']*12)
    assert [w.store.get_lesson(w.lease()['lesson_id'])['title'] for _ in range(12)]==[f'Aula {i}' for i in range(1,13)]


def fake_runner(w, calls, data=b'fakevideo'):
    import json
    from pathlib import Path
    from types import SimpleNamespace
    def run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[0]=='rclone':Path(cmd[3]).write_bytes(data)
        if cmd[0]=='ffprobe':return SimpleNamespace(stdout=json.dumps({'format':{'duration':30}}),stderr='')
        if cmd[0]==str(w.cfg.binary):
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':0,'to':30000},'text':'Conteúdo científico legítimo.'}]}))
        return SimpleNamespace(stdout='',stderr='')
    return run


def test_identical_bytes_at_different_paths_decode_once(tmp_path):
    w=worker(tmp_path,['Biologia','Física'])
    calls=[]; w.runner=fake_runner(w,calls)
    assert w.run_once()['state']=='validated'
    assert w.run_once()['state']=='validated'
    assert sum(c[0]==str(w.cfg.binary) for c in calls)==1
    assert w.c.execute('SELECT COUNT(DISTINCT lesson_id) FROM transcript_segments').fetchone()[0]==2


def test_alias_propagation_failure_after_success_is_atomic_and_not_breaker(tmp_path):
    w=worker(tmp_path,['Biologia','Física'])
    with w.c:w.c.execute("UPDATE lesson_video_sources SET remote_path='onedrive:Federal Online/shared'")
    calls=[]; w.runner=fake_runner(w,calls)
    def boom(*a,**k): raise OSError('synthetic crash during alias propagation')
    w.store.add_transcript_alias=boom
    orig=w.store.add_transcript; n=[0]
    def add(*a,**k):
        n[0]+=1
        if n[0]>1: raise OSError('synthetic crash during alias propagation')
        return orig(*a,**k)
    w.store.add_transcript=add
    w.run_once()
    assert sorted(r[0] for r in w.c.execute('SELECT state FROM transcription_jobs'))==['done','queued']
    row=w.c.execute('SELECT consecutive_failures FROM transcription_breaker').fetchone()
    assert row is None or row[0]==0
    w.store.add_transcript=orig
    assert w.run_once()['state']=='validated'
    assert [r[0] for r in w.c.execute('SELECT state FROM transcription_jobs')]==['done','done']
    assert sum(c[0]==str(w.cfg.binary) for c in calls)==1

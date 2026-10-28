"""All media/model subprocesses here are injected synthetic fixtures."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def test_window_plan_is_frozen_to_selected_ids_and_five_minutes():
    from fo_hub.window_benchmark import window_plan
    plan=window_plan('fo_21fd4985e207c5df',1,'baseline')
    assert plan['start_s']==1258.5 and plan['duration_s']==300
    assert plan['version']==1
    assert window_plan('fo_21fd4985e207c5df',1,'beam10')['decoder']['beam_size']==10
    assert window_plan('fo_21fd4985e207c5df',1,'fallback')['decoder']['temperature_fallback'] is True
    assert window_plan('fo_21fd4985e207c5df',1,'no-context')['decoder']['max_context']==0
    for args in [('unknown',0,'baseline'),('fo_21fd4985e207c5df',3,'baseline'),('fo_21fd4985e207c5df',0,'vad')]:
        with pytest.raises(ValueError):window_plan(*args)


def test_authorization_is_checked_before_any_download_or_directory_write(tmp_path):
    from fo_hub.worker import Config
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=Config(tmp_path,tmp_path/'missing.db',tmp_path/'binary',tmp_path/'model')
    def forbidden(*a,**kw):pytest.fail('closed gate executed subprocess')
    result=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),runner=forbidden,
                      gate_fn=lambda:{'allowed':False})
    assert result['state']=='blocked'
    assert list(tmp_path.iterdir())==[]


def seed(tmp_path):
    from fo_hub.worker import Config
    from fo_hub.store import FOStore
    store=FOStore(tmp_path/'hub.sqlite3')
    store.sync_lessons([{'course_id':'c','media_id':'m','title':'Synthetic','media_type':'video','duration_s':2817}])
    original=store.list_lessons()[0]['lesson_id']
    lesson='fo_21fd4985e207c5df'
    store.conn.execute('UPDATE lessons SET lesson_id=? WHERE lesson_id=?',(lesson,original))
    store.conn.execute('CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT)')
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',(lesson,'onedrive:Federal Online/synthetic.mp4','1',9,1,'now'))
    store.conn.commit();store.conn.close()
    binary=tmp_path/'whisper';binary.write_bytes(b'synthetic executable')
    model=tmp_path/'model';model.write_bytes(b'synthetic weights')
    return Config(tmp_path,tmp_path/'hub.sqlite3',binary,model)


def fake_runner(calls):
    def run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[0]=='rclone':Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0]=='ffprobe':return SimpleNamespace(stdout=json.dumps({'format':{'duration':'2817'}}),stderr='')
        elif cmd[0]=='ffmpeg':Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0]=='/usr/bin/time':
            Path(cmd[cmd.index('-o')+1]).write_text('Maximum resident set size (kbytes): 1024\n')
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription':[{'offsets':{'from':0,'to':300000},'text':'Conteúdo científico sintético.'}]}))
        return SimpleNamespace(stdout='',stderr='',returncode=0)
    return run


def test_comparisons_reuse_exact_window_audio_and_never_publish_or_lease(tmp_path):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path);calls=[];runner=fake_runner(calls)
    kwargs={'runner':runner,'gate_fn':lambda:{'allowed':True},'free_bytes':lambda:20*1024**3}
    first=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),**kwargs)
    second=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'beam10'),**kwargs)
    assert first['state']=='measured' and second['state']=='measured'
    assert first['audio_sha256']==second['audio_sha256']
    assert len([c for c in calls if c[0]=='rclone'])==1
    # One download prepares three selected windows once, not once per config.
    assert len([c for c in calls if c[0]=='ffmpeg'])==3
    for result in [first,second]:
        artifact=json.loads(Path(result['artifact']).read_text())
        assert artifact['synthetic'] is None  # runner cannot certify acoustic truth
        assert artifact['human_gold'] is None
        assert artifact['published'] is False
        assert artifact['raw']['transcription'][0]['text']=='Conteúdo científico sintético.'
        assert artifact['segments'][0]['start']==0
    assert not (tmp_path/'transcripts/generated_v2').exists()
    import sqlite3
    c=sqlite3.connect(cfg.db)
    assert c.execute('SELECT count(*) FROM transcription_jobs').fetchone()[0]==0
    assert c.execute('SELECT count(*) FROM transcripts').fetchone()[0]==0
    c.close()
    before=len(calls)
    repeated=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),**kwargs)
    assert repeated['artifact']==first['artifact']
    assert repeated['reused'] is True
    assert len(calls)==before


def test_tampered_cached_audio_is_rejected_not_silently_redecoded(tmp_path):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path);calls=[];kwargs={'runner':fake_runner(calls),'gate_fn':lambda:{'allowed':True},'free_bytes':lambda:20*1024**3}
    plan=window_plan('fo_21fd4985e207c5df',0,'baseline')
    first=run_window(cfg,plan,**kwargs)
    artifact=json.loads(Path(first['artifact']).read_text())
    Path(artifact['audio_path']).write_bytes(b'tampered')
    before=len(calls)
    with pytest.raises(ValueError,match='audio integrity'):
        run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'beam10'),**kwargs)
    assert len(calls)==before


def test_mutated_window_plan_is_rejected_before_download(tmp_path):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path)
    plan=window_plan('fo_21fd4985e207c5df',0,'baseline');plan['duration_s']=301
    with pytest.raises(ValueError,match='mutated window plan'):
        run_window(cfg,plan,runner=lambda *a,**kw:pytest.fail('downloaded'),gate_fn=lambda:{'allowed':True})


def test_shared_worker_lock_prevents_concurrent_comparison(tmp_path):
    import fcntl
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path);(tmp_path/'locks').mkdir()
    with (tmp_path/'locks/transcription.lock').open('a+') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),
                          gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3,
                          runner=lambda *a,**kw:pytest.fail('concurrent decode'))
    assert result['state']=='busy'
    assert not (tmp_path/'validation-2026-10-28').exists()


def test_dotted_configuration_keeps_unique_raw_and_resource_artifacts(tmp_path):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path);calls=[]
    result=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'no-speech-0.8'),
                      runner=fake_runner(calls),gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    artifact=json.loads(Path(result['artifact']).read_text())
    prefix=next(c[c.index('-of')+1] for c in calls if c[0]=='/usr/bin/time')
    assert Path(prefix+'.json').is_file()
    assert Path(artifact['resource_log']).is_file()
    assert artifact['plan']['decoder']['no_speech']==0.8

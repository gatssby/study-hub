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
    second=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'beam10'),comparison_selection=selection(first),**kwargs)
    assert first['state']=='measured' and second['state']=='measured'
    assert first['audio_sha256']==second['audio_sha256']
    assert len([c for c in calls if c[0]=='rclone'])==1
    assert len([c for c in calls if c[0]=='ffmpeg'])==3
    for result in [first,second]:
        artifact=json.loads(Path(result['artifact']).read_text())
        assert artifact['synthetic'] is None
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
        run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),**kwargs)
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
    kwargs=dict(runner=fake_runner(calls),gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    baseline=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),**kwargs)
    result=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'no-speech-0.8'),comparison_selection=selection(baseline,'no-speech-0.8'),**kwargs)
    artifact=json.loads(Path(result['artifact']).read_text())
    prefix=[c[c.index('-of')+1] for c in calls if c[0]=='/usr/bin/time'][-1]
    assert Path(prefix+'.json').is_file()
    assert Path(artifact['resource_log']).is_file()
    assert artifact['plan']['decoder']['no_speech']==0.8


@pytest.mark.parametrize('field',['raw_path','resource_log'])
@pytest.mark.parametrize('damage',['missing','tampered'])
def test_reuse_rejects_damaged_original_evidence(tmp_path,field,damage):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path);calls=[]
    kwargs=dict(runner=fake_runner(calls),gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    plan=window_plan('fo_21fd4985e207c5df',0,'baseline')
    first=run_window(cfg,plan,**kwargs)
    artifact=json.loads(Path(first['artifact']).read_text())
    path=Path(artifact.get(field,first['artifact'].replace('.artifact.json','.json')))
    if damage=='missing':path.unlink()
    else:path.write_text('tampered')
    before=len(calls)
    with pytest.raises(ValueError,match='evidence integrity'):
        run_window(cfg,plan,**kwargs)
    assert len(calls)==before


@pytest.mark.parametrize('case',['missing-baseline','missing-selection','uninformative','wrong-config','tampered-baseline','wrong-window'])
def test_additional_comparison_requires_verified_baseline_and_selection(tmp_path,case):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path);calls=[]
    kwargs=dict(runner=fake_runner(calls),gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    review=None
    if case!='missing-baseline':
        first=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),**kwargs)
        review=selection(first)
        if case=='missing-selection':review=None
        if case=='uninformative':review['informative']=False
        if case=='wrong-config':review['configs']=['fallback']
        if case=='tampered-baseline':Path(first['artifact']).write_text('{}')
    before=len(calls)
    with pytest.raises(ValueError,match='baseline|selection'):
        run_window(cfg,window_plan('fo_21fd4985e207c5df',1 if case=='wrong-window' else 0,'beam10'),comparison_selection=review,**kwargs)
    assert len(calls)==before


@pytest.mark.parametrize('mode',['timeout','wrapper-exit','wrapper-error'])
def test_real_synthetic_process_group_has_no_live_child_after_return(tmp_path,mode):
    import os
    import signal
    import subprocess
    import fo_hub.window_benchmark as module
    pid_path=tmp_path/'child.pid'
    child="import os,signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(60)" % str(pid_path)
    wrapper="import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(%s)" % (child,'60' if mode=='timeout' else '.2')
    if mode=='wrapper-error':wrapper+='; sys.exit(7)'
    run=module.run_process_group
    try:
        if mode=='timeout':
            with pytest.raises(subprocess.TimeoutExpired):run([sys.executable,'-c',wrapper],check=True,capture_output=True,text=True,timeout=.4)
        elif mode=='wrapper-error':
            with pytest.raises(subprocess.CalledProcessError) as error:
                run([sys.executable,'-c',wrapper],check=True,capture_output=True,text=True,timeout=.4)
            assert error.value.returncode==7
        else:
            run([sys.executable,'-c',wrapper],check=True,capture_output=True,text=True,timeout=.4)
        pid=int(pid_path.read_text())
        state=subprocess.run(['ps','-o','stat=','-p',str(pid)],capture_output=True,text=True).stdout.strip()
        assert not state or state.startswith('Z'), 'descendant still running after runner returned'
    finally:
        if pid_path.exists():
            try:os.kill(int(pid_path.read_text()),signal.SIGKILL)
            except ProcessLookupError:pass


@pytest.mark.parametrize('monitor_failure',[False,True])
def test_timeout_cleans_group_under_lock_and_preserves_private_failure(tmp_path,monkeypatch,monitor_failure):
    import fcntl
    import subprocess
    import fo_hub.window_benchmark as module
    cfg=seed(tmp_path);calls=[];fake=fake_runner(calls)
    pid_path=tmp_path/'timeout-child.pid'
    child="import os,pathlib,time,signal; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(60)" % str(pid_path)
    wrapper="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',%r]); print('private diagnostic',flush=True); time.sleep(60)" % child
    observed=[];original=subprocess.run
    def inspect(cmd,**kwargs):
        if cmd[:2]==['ps','-axo']:
            with (tmp_path/'locks/transcription.lock').open('a+') as handle:
                with pytest.raises(BlockingIOError):fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            observed.append(True)
            if monitor_failure and len(observed)==1:raise subprocess.CalledProcessError(1,cmd)
        return original(cmd,**kwargs)
    monkeypatch.setattr(subprocess,'run',inspect)
    def runner(cmd,**kwargs):
        if cmd[0]=='/usr/bin/time':
            return module.run_process_group([sys.executable,'-c',wrapper],timeout=.4)
        return fake(cmd,**kwargs)
    with pytest.raises(subprocess.TimeoutExpired):
        module.run_window(cfg,module.window_plan('fo_21fd4985e207c5df',0,'baseline'),runner=runner,
                          gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    assert observed
    pid=int(pid_path.read_text())
    state=original(['ps','-o','stat=','-p',str(pid)],capture_output=True,text=True).stdout.strip()
    assert not state or state.startswith('Z')
    failures=list((tmp_path/'validation-2026-10-28/windows').rglob('*.failure.json'))
    assert len(failures)==1
    failure=json.loads(failures[0].read_text())
    assert failure['published'] is False and 'private diagnostic' in failure['stdout']
    with (tmp_path/'locks/transcription.lock').open('a+') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)


def test_full_18_unique_window_budget_still_allows_config_reuse(tmp_path):
    from fo_hub.window_benchmark import run_window,window_plan,_SELECTION
    cfg=seed(tmp_path);calls=[]
    root=tmp_path/'validation-2026-10-28/windows';root.mkdir(parents=True)
    keys=[f"{row['lesson_id']}:{i}" for row in json.loads(_SELECTION.read_text())['lessons'] for i in range(3)]
    assert len(keys)==len(set(keys))==18
    (root/'budget.json').write_text(json.dumps({'windows':keys,'limit':18}))
    kwargs=dict(runner=fake_runner(calls),gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    first=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'baseline'),**kwargs)
    second=run_window(cfg,window_plan('fo_21fd4985e207c5df',0,'beam10'),comparison_selection=selection(first),**kwargs)
    assert second['state']=='measured'
    assert json.loads((root/'budget.json').read_text())['windows']==keys


def selection(baseline,config='beam10'):
    from fo_hub.worker import file_sha256
    return {'baseline_artifact':baseline['artifact'],'baseline_sha256':file_sha256(Path(baseline['artifact'])),
            'configs':[config],'informative':True,'rationale':'Exploratory comparison of raw segment behavior, not acoustic gold.',
            'operator':'autonomous-authorized','acoustic_reviewed':False}


def test_qa_uses_window_relative_time_without_changing_absolute_segments(tmp_path):
    from fo_hub.window_benchmark import run_window,window_plan
    cfg=seed(tmp_path)
    result=run_window(cfg,window_plan('fo_21fd4985e207c5df',1,'baseline'),runner=fake_runner([]),
                      gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3)
    artifact=json.loads(Path(result['artifact']).read_text())
    assert artifact['segments'][0]['start']==1258.5
    assert artifact['qa']['flags']==[]
    assert artifact['qa']['metrics']['covered_until_s']==300

"""Synthetic regressions from independent review; never run real ASR."""
import copy
import gzip
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from test_worker_readiness import ready,fake_runner
from fo_hub.worker import Worker,evidence_checksum,validate_checkpoint


def test_failed_diagnostic_write_never_traps_lease(tmp_path,monkeypatch):
    import fo_hub.worker as module
    store,lesson,cfg=ready(tmp_path)
    def fail(*args,**kwargs):raise subprocess.CalledProcessError(7,['synthetic'],stderr='private detail')
    def disk_full(*args,**kwargs):raise OSError('synthetic disk full')
    monkeypatch.setattr(module,'atomic_json',disk_full)
    result=Worker(cfg,store,runner=fail,gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3).run_once()
    assert result['state']=='retry'
    assert result['diagnostic_error_type']=='OSError'
    assert 'private' not in json.dumps(result)
    row=store.conn.execute('SELECT state,lease_owner,retry_at,last_error FROM transcription_jobs').fetchone()
    assert row['state']=='queued' and row['lease_owner'] is None and row['retry_at']>0
    assert row['last_error']=='CalledProcessError'


@pytest.mark.parametrize('failure',['exit','timeout','missing'])
def test_decoder_output_and_diagnostics_survive_failed_or_missing_json(tmp_path,failure):
    store,lesson,cfg=ready(tmp_path);calls=[];base=fake_runner(cfg,calls)
    partial='{"transcription": [partial synthetic academic evidence'
    def run(cmd,**kwargs):
        if cmd[0]==str(cfg.binary):
            if failure=='missing':return SimpleNamespace(stdout='synthetic stdout',stderr='synthetic stderr')
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(partial)
            if failure=='timeout':raise subprocess.TimeoutExpired(cmd,1,output=b'synthetic stdout',stderr=b'synthetic stderr')
            raise subprocess.CalledProcessError(7,cmd,output='synthetic stdout',stderr='synthetic stderr')
        return base(cmd,**kwargs)
    result=Worker(cfg,store,runner=run,gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3).run_once()
    assert result['state']=='retry'
    archives=list((tmp_path/'transcripts/evidence').glob('*/*/*.decoder-*.json.gz'))
    assert len(archives)==1
    archived=json.loads(gzip.decompress(archives[0].read_bytes()))
    assert archived['raw_text']==(None if failure=='missing' else partial)
    assert archived['decoding']['stderr']=='synthetic stderr'
    assert archived['decoding']['stdout']=='synthetic stdout'
    assert archived['decoding']['wall_s']>=0
    assert not (tmp_path/'transcripts/generated_v2').exists()


def test_checkpoint_v2_signs_and_validates_decoder_diagnostics(tmp_path):
    store,lesson,cfg=ready(tmp_path);calls=[]
    result=Worker(cfg,store,runner=fake_runner(cfg,calls),gate_fn=lambda:{'allowed':True},free_bytes=lambda:20*1024**3).run_once()
    assert result['state']=='validated'
    checkpoint=next((tmp_path/'transcripts/evidence').glob('*/*/0.000-30.000.json.gz'))
    original=json.loads(gzip.decompress(checkpoint.read_bytes()))
    assert original['schema_version']==2
    keys=(original['source_sha256'],original['fingerprint'],0.0,30.0)
    changed=copy.deepcopy(original);changed['decoding']['stderr']='tampered'
    with pytest.raises(ValueError,match='checksum'):validate_checkpoint(changed,*keys)
    changed=copy.deepcopy(original);changed['decoding']['wall_s']=-99
    changed['evidence_sha256']=evidence_checksum(changed)
    with pytest.raises(ValueError,match='decoding'):validate_checkpoint(changed,*keys)
    legacy=copy.deepcopy(original);legacy['schema_version']=1;legacy.pop('decoding')
    legacy['evidence_sha256']=evidence_checksum(legacy)
    validate_checkpoint(legacy,*keys)  # old raw remains resumable, old timing is not certified

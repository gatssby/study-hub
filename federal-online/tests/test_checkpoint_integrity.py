"""Synthetic checkpoint evidence only; every decoder/media subprocess is mocked."""
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_worker import setup
from fo_hub import worker


def harness(tmp_path):
    store, lesson, cfg = setup(tmp_path)
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == 'rclone':
            Path(cmd[3]).write_bytes(b'fakevideo')
        elif cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'format': {'duration': '30'}}), stderr='')
        elif cmd[0] == 'ffmpeg' and cmd[-1].endswith('.wav'):
            Path(cmd[-1]).write_bytes(b'fakewav')
        elif cmd[0] == str(cfg.binary):
            Path(cmd[cmd.index('-of')+1]+'.json').write_text(json.dumps({'transcription': [
                {'offsets': {'from': 0, 'to': 2000}, 'text': 'Original evidence.'}]}))
        return SimpleNamespace(stdout='', stderr='')
    w = worker.Worker(cfg, store=store, runner=run, gate_fn=lambda: {'allowed': True}, free_bytes=lambda: 20*1024**3)
    store.conn.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',
                       (lesson['lesson_id'], 'onedrive:Federal Online/a.mp4', '1', 9, 1, 'now'))
    store.conn.commit()
    job = w.lease()
    work = tmp_path/'work'; work.mkdir()
    return w, job, work, calls


def test_malformed_decoder_json_is_preserved_before_parse(tmp_path):
    w, job, work, calls = harness(tmp_path)
    original_runner = w.runner
    def malformed(cmd, **kwargs):
        result = original_runner(cmd, **kwargs)
        if cmd[0] == str(w.cfg.binary):
            Path(cmd[cmd.index('-of')+1]+'.json').write_text('{broken decoder JSON')
        return result
    w.runner = malformed
    with pytest.raises(json.JSONDecodeError):
        w.pipeline(job, work)
    evidence = next((tmp_path/'transcripts/evidence').rglob('*.decoder-*.json.gz'))
    saved = json.loads(gzip.decompress(evidence.read_bytes()))
    assert saved['raw_text'] == '{broken decoder JSON'
    assert saved['created_at'] > 0
    assert saved['source_sha256']


@pytest.mark.parametrize('damage', ['gzip', 'deflate', 'json', 'schema', 'content', 'identity', 'bounds', 'silence', 'schema_checked', 'silence_checked', 'timestamp_checked'])
def test_bad_checkpoint_is_preserved_and_redecoded_only_when_authorized(tmp_path, damage):
    w, job, work, calls = harness(tmp_path)
    assert w.pipeline(job, work) == 'review'
    checkpoint = next((tmp_path/'transcripts/evidence').rglob('0.000-30.000.json.gz'))
    original = json.loads(gzip.decompress(checkpoint.read_bytes()))
    if damage == 'gzip':
        bad = b'not gzip'
    elif damage == 'deflate':
        bad = gzip.compress(b'valid')[:10] + b'\x07' + b'\x00'*20
    elif damage == 'json':
        bad = gzip.compress(b'{')
    else:
        data = json.loads(json.dumps(original))
        if damage == 'schema': data['raw'] = []
        elif damage == 'content': data['raw']['transcription'][0]['text'] = 'Tampered evidence.'
        elif damage == 'identity': data['source_sha256'] = 'wrong'
        elif damage == 'bounds': data['duration_s'] = 29
        elif damage == 'silence': data['silence'] = [[0, 999]]
        elif damage == 'schema_checked': data['raw'] = []
        elif damage == 'silence_checked': data['silence'] = [[0, 999]]
        elif damage == 'timestamp_checked': data['raw']['transcription'][0]['offsets']['from'] = -1
        if damage.endswith('_checked'):
            data['evidence_sha256'] = worker.evidence_checksum(data)
        bad = gzip.compress(json.dumps(data).encode())
    checkpoint.write_bytes(bad)
    calls.clear()
    w.gate_fn = lambda: {'allowed': False}
    with pytest.raises(RuntimeError, match='authorization revoked'):
        w.pipeline(job, work)
    assert not any(cmd[0] == str(w.cfg.binary) for cmd in calls)
    assert checkpoint.read_bytes() == bad
    w.gate_fn = lambda: {'allowed': True}
    calls.clear()
    assert w.pipeline(job, work) == 'review'
    assert sum(cmd[0] == str(w.cfg.binary) for cmd in calls) == 1
    rejected = list(checkpoint.parent.glob(checkpoint.name+'.rejected-*'))
    assert len(rejected) == 1 and rejected[0].read_bytes() == bad
    fresh = json.loads(gzip.decompress(checkpoint.read_bytes()))
    assert fresh['evidence_sha256']
    assert fresh['created_at'] >= original['created_at']
    assert fresh['rejected_cache']['path'] == str(rejected[0])
    artifact = json.loads(gzip.decompress(next((tmp_path/'transcripts/review').rglob('*.json.gz')).read_bytes()))
    assert artifact['chunks'][0]['reused'] is False
    calls.clear()
    assert w.pipeline(job, work) == 'review'
    assert not any(cmd[0] == str(w.cfg.binary) for cmd in calls)

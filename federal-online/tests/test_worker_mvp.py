import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import wave

import pytest

from fo_hub import worker as worker_module
from fo_hub.worker import CHUNK_SECONDS, Config, JobProblem, Worker, atomic_json, leader_lock, load_checkpoint


def test_durable_checkpoint_detects_changes(tmp_path):
    path = tmp_path / '0.json'
    identity = ['source', 'decoder', 0, 32]
    body = {'audio_duration_s': 32, 'silence': [], 'raw': {'transcription': []}}
    atomic_json(path, identity, body)
    assert load_checkpoint(path, identity) == body
    assert load_checkpoint(path, ['other', 'decoder', 0, 32]) is None
    payload = json.loads(path.read_text())
    payload['data']['raw']['transcription'].append({'text': 'tampered'})
    path.write_text(json.dumps(payload))
    assert load_checkpoint(path, identity) is None


def test_lock_excludes_another_open_description_and_child_inherits(tmp_path):
    with leader_lock(tmp_path) as fd:
        with pytest.raises(BlockingIOError):
            with leader_lock(tmp_path):
                pytest.fail('duplicate leader acquired')
        child = subprocess.Popen(['sleep', '10'], pass_fds=(fd,))
    try:
        with pytest.raises(BlockingIOError):
            with leader_lock(tmp_path):
                pytest.fail('orphan child did not retain lock')
    finally:
        child.terminate()
        child.wait()
    with leader_lock(tmp_path):
        pass


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='requires ffmpeg')
def test_real_audio_extraction_measures_samples_and_silence(tmp_path):
    audio = tmp_path / 'source.wav'
    with wave.open(str(audio), 'wb') as output:
        output.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        output.writeframes(b'\0\0' * 16000 * 8)
    cfg = Config(tmp_path, tmp_path / 'hub.sqlite3', Path('/unused'), Path('/unused'))
    with leader_lock(tmp_path) as fd:
        worker = Worker(cfg, None, fd)
        actual, quiet = worker.extract(audio, tmp_path / 'probe.wav', 3.0, 2.0)
    assert actual == 2.0
    assert quiet == [[0.0, 2.0]]
    assert CHUNK_SECONDS == 600


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='requires ffmpeg')
@pytest.mark.parametrize('offset', [0, 2, 4])
def test_audio_extraction_rejects_collapsed_pts_gap(tmp_path, offset):
    source = tmp_path / 'gap.mp4'
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', 'sine=r=48000:d=8', '-af', r'asetpts=PTS+2/TB*gte(T\,1)',
                    '-c:a', 'aac', source], check=True, capture_output=True)
    cfg = Config(tmp_path, tmp_path / 'hub.sqlite3', Path('/unused'), Path('/unused'))
    with leader_lock(tmp_path) as fd:
        worker = Worker(cfg, None, fd)
        if offset == 4:  # seeking past the discontinuity is safe for this window
            actual, quiet = worker.extract(source, tmp_path / 'probe.wav', offset, 4)
            assert (actual, quiet) == (4.0, [])
        else:  # a gap in the middle, or at the beginning of a seek
            with pytest.raises(JobProblem, match='audio_pts_discontinuity') as error:
                worker.extract(source, tmp_path / 'probe.wav', offset, 4)
            assert error.value.review


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='requires ffmpeg')
def test_aac_seek_tolerates_codec_frame_rounding(tmp_path):
    source = tmp_path / 'continuous.mp4'
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', 'anullsrc=r=44100:cl=stereo:d=8', '-c:a', 'aac', source],
                   check=True, capture_output=True)
    cfg = Config(tmp_path, tmp_path / 'hub.sqlite3', Path('/unused'), Path('/unused'))
    with leader_lock(tmp_path) as fd:
        actual, quiet = Worker(cfg, None, fd).extract(source, tmp_path / 'probe.wav', 3.015, 2.5)
    assert actual == 2.5
    assert len(quiet) == 1
    assert quiet[0] == pytest.approx([0.0, actual], abs=2 / 16000)


@pytest.mark.parametrize('frames', ['', 'n:0 pts:0 pts_time:0 rate:16000 nb_samples:15999',
                                    'n:0 pts:NOPTS pts_time:NOPTS rate:16000 nb_samples:16000'])
def test_audio_extraction_requires_decoded_frame_evidence_matching_wav(tmp_path, frames):
    wav = tmp_path / 'probe.wav'

    def ffmpeg(args, **kwargs):
        with wave.open(str(wav), 'wb') as output:
            output.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            output.writeframes(b'\0\0' * 16000)
        return SimpleNamespace(stderr=f'[Parsed_ashowinfo_3 @ 0x42] {frames}\n' if frames else '')

    cfg = Config(tmp_path, tmp_path / 'hub.sqlite3', Path('/unused'), Path('/unused'))
    with leader_lock(tmp_path) as fd:
        with pytest.raises(JobProblem, match='invalid_audio_pts_evidence') as error:
            Worker(cfg, None, fd, runner=ffmpeg).extract(tmp_path / 'input', wav, 0, 1)
    assert error.value.review


def test_checkpoint_from_extraction_without_pts_evidence_is_not_reused(tmp_path, mvp_case, monkeypatch):
    def run(cmd, **kwargs):
        if cmd[0] == 'ffprobe':
            return SimpleNamespace(stdout=json.dumps({'streams': [{'index': 0}],
                                                       'format': {'duration': 1}}))
        # Extraction is forced to fail: pre-guard decoder rows cannot bypass it.
        assert cmd[0] == 'ffmpeg'
        raise JobProblem('audio_pts_discontinuity', review=True)

    case = mvp_case(duration=1, runner=run)
    monkeypatch.setattr(case.worker, 'download', lambda job, video: video.write_bytes(b'fakevideo'))
    job = case.queue.lease(case.worker.owner, lesson_id=case.lesson_id)
    source = {key: job[key] for key in worker_module.SOURCE_FIELDS}
    input_file = tmp_path / 'old-source'
    input_file.write_bytes(b'fakevideo')
    v1 = worker_module.digest([1, worker_module.file_identity(case.cfg.binary),
                               worker_module.MODEL_SHA256, worker_module.WHISPER_FLAGS,
                               CHUNK_SECONDS, worker_module.OVERLAP_SECONDS])
    atomic_json(tmp_path / '0.json', [source, worker_module.file_sha256(input_file), v1, 0.0, 1.0],
                {'audio_duration_s': 1.0, 'silence': [], 'raw': {'transcription': [
                    {'offsets': {'from': 0, 'to': 1000}, 'text': 'Unverified old audio.'}]}})

    with pytest.raises(JobProblem, match='audio_pts_discontinuity'):
        case.worker.process(job, tmp_path, tmp_path)
    assert case.store.get_transcript(case.lesson_id) is None


@pytest.mark.parametrize('stream_end', [726.848, 721])
def test_probe_accepts_short_declared_audio_tail_but_not_missing_audio(tmp_path, stream_end):
    def ffprobe(args, **kwargs):
        return SimpleNamespace(stdout=json.dumps({'format': {'start_time': 0, 'duration': 726.910611},
                                                   'streams': [{'start_time': 0, 'duration': stream_end}]}))
    cfg = Config(tmp_path, tmp_path / 'hub.sqlite3', Path('/unused'), Path('/unused'))
    with leader_lock(tmp_path) as fd:
        worker = Worker(cfg, None, fd, runner=ffprobe)
        if stream_end == 726.848:
            assert worker.probe(Path('/unused'), 726) == stream_end
        else:
            with pytest.raises(JobProblem, match='source_audio_timeline_mismatch'):
                worker.probe(Path('/unused'), 726)

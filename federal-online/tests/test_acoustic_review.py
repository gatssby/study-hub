import fcntl
import gzip
import json
import os
import subprocess
from copy import deepcopy
from types import SimpleNamespace

import pytest

from fo_hub import acoustic_review as ar
from test_review_reassessment import fixture


def test_plan_has_context_and_covers_long_flag_with_independent_targets():
    windows = ar.plan_windows(100, [{'kind': 'token_repetition', 'start': 13, 'end': 43}])
    assert [(w.target_start, w.target_end) for w in windows] == [(13, 33), (33, 43)]
    assert [(w.start, w.end) for w in windows] == [(10, 36), (30, 46)]
    assert all(w.end - w.start <= 26 for w in windows)


def test_plan_deduplicates_and_does_not_invent_out_of_range_times():
    flag = {'kind': 'bad_timestamp', 'start': 10, 'end': 11}
    assert ar.plan_windows(10, [flag]) == []
    point = {'kind': 'token_repetition', 'start': 10, 'end': 10}
    assert len(ar.plan_windows(10, [point, point])) == 1
    assert ar.plan_windows(10, [point])[0].end == 10


def test_vad_mapping_preserves_sample_offsets_and_rejects_invalid_spans():
    assert ar.map_vad(18, 16000, [(512, 1024), (8000, 16000)]) == [[18.032, 18.064], [18.5, 19.0]]
    with pytest.raises(ValueError):
        ar.map_vad(18, 16000, [(0, 16001)])
    with pytest.raises(ValueError):
        ar.map_vad(18, 16000, [(1, 10), (9, 11)])


def test_silence_requires_independent_measured_silence_and_not_a_point():
    window = ar.Window(0, 5, 1, 2, 'text_during_measured_silence')
    assert ar.classify(window, [], [(1, 2)]) == 'speech_generated_during_measured_silence'
    assert ar.classify(window, [[1.5, 1.8]], [(1, 2)]) == 'inconclusive_disagreement'
    assert ar.classify(window, [], []) == 'inconclusive_disagreement'
    point = ar.Window(0, 5, 1, 1, 'text_during_measured_silence')
    assert ar.classify(point, [], [(0, 5)]) == 'inconclusive_disagreement'


def test_academic_terms_and_disagreement_are_only_lexical_evidence():
    reference = [{'text': 'Óxido de nitrogênio.'}]
    assert ar.compare_text(reference, 'O\u0301xido de nitrogênio')['agreement'] == 'same_normalized_text'
    assert ar.compare_text(reference, 'Óxido de hidrogênio')['agreement'] == 'different_text'
    assert ar.compare_text([], 'nitrogênio')['agreement'] == 'possible_missing_transcription'
    assert ar.compare_text(reference, None)['agreement'] == 'parakeet_skipped_no_vad_speech'
    repetition = ar.Window(0, 5, 1, 2, 'ngram_repetition')
    assert ar.classify(repetition, [], []) == 'inconclusive_disagreement'


def test_lock_held_by_whisper_defers_before_any_review_work(tmp_path):
    cfg = SimpleNamespace(state=tmp_path)
    (tmp_path / 'locks').mkdir()
    (tmp_path / 'locks/transcription.lock').touch()
    with ar.whisper_lock(cfg):
        with pytest.raises(ar.Blocked, match='whisper_owns_transcription_lock'):
            ar.review(cfg, None, 'fo_86307c2dd5ba3e22', 2)
    assert not (tmp_path / 'transcripts').exists()
    with ar.whisper_lock(cfg):
        pass


def test_source_binding_and_exclusions():
    source = {'version': 1, 'revision': '1', 'size': 10, 'available': 1, 'present': 1,
              'state': 'review', 'remote_path': 'onedrive:Federal Online/video.mp4',
              'subject': 'Biologia', 'front': None, 'module': None}
    item = {'lesson_id': 'fo_86307c2dd5ba3e22', 'version': 1, 'corpus': ar.ACCEPTED_CORPUS,
            'source_revision': '1', 'source_size': 10, 'source_remote_path': source['remote_path'],
            'source_sha256': 'a' * 64, 'duration_s': 12}
    assert ar.source_identity(item, item['lesson_id'], source, 1, set()) == ('a' * 64, 12)
    for changed in ({'revision': '2'}, {'size': 11}, {'state': 'done'}, {'subject': 'Inglês'},
                    {'subject': 'Espanhol'}, {'remote_path': 'onedrive:Federal Online/../bad.mp4'}):
        with pytest.raises(ar.Blocked):
            ar.source_identity(item, item['lesson_id'], {**source, **changed}, 1, set())
    with pytest.raises(ar.Blocked):
        ar.source_identity(item, item['lesson_id'], source, 1, {'Biologia'})


def test_cooperative_review_accepts_live_primary_lease_but_not_foreign_lease(tmp_path):
    worker, store, lesson, _, _ = fixture(tmp_path)
    cfg = worker.cfg
    locks = cfg.state / 'locks'
    locks.mkdir(exist_ok=True)
    (locks / 'transcription.lock').touch()
    (locks / 'acoustic-review.turn').touch()
    store.sync_lessons([{'course_id':'another', 'media_id':'one', 'title':'Aula', 'duration_s':30}])
    other = next(row for row in store.list_lessons() if row['lesson_id'] != lesson['lesson_id'])
    args = cfg, lesson['lesson_id'], 1
    with store.conn:
        store.conn.execute("INSERT INTO transcription_jobs(lesson_id,version,state,lease_owner,updated_at) VALUES(?,1,'leased',?,'0')",
                           (other['lesson_id'], f'fo-worker:test:{os.getpid()}:test'))
    with (locks / 'transcription-worker.lock').open('a+') as leader:
        fcntl.flock(leader, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with ar.whisper_lock(cfg, wait=1):
            with pytest.raises(ar.Blocked, match='whisper_lease_present'):
                ar.snapshot(*args)
            assert ar.snapshot(*args, cooperative=True)[0]['state'] == 'review'
            with store.conn:
                store.conn.execute("UPDATE transcription_jobs SET lease_owner='other' WHERE state='leased'")
            with pytest.raises(ar.Blocked, match='whisper_lease_present'):
                ar.snapshot(*args, cooperative=True)


def test_storage_and_cgroup_limits():
    limit = ar.storage_required(100, 20)
    ar.require_storage(limit, 100, 20)
    with pytest.raises(ar.Blocked, match='storage'):
        ar.require_storage(limit - 1, 100, 20)
    assert ar.limits_ok('50000 100000', str(3 * 2**30), '0')
    for bad in [('max 100000', str(2**30), '0'), ('50100 100000', str(2**30), '0'),
                ('50000 100000', 'max', '0'), ('50000 100000', str(2**30), 'max')]:
        assert not ar.limits_ok(*bad)


def test_copy_allows_transfer_headroom_but_still_requires_exact_source(tmp_path, monkeypatch):
    video = tmp_path / 'source.mp4'
    source = {'remote_path': 'onedrive:Federal Online/private.mp4', 'size': 3}
    digest = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    output = b'abc'

    def rclone(args, *, timeout, pass_fds):
        assert args[:4] == ['rclone', 'copyto', source['remote_path'], video]
        assert args[args.index('--max-transfer') + 1] == '1048579B'
        assert args[args.index('--cutoff-mode') + 1] == 'HARD'
        assert args[args.index('--retries') + 1] == args[args.index('--low-level-retries') + 1] == '1'
        assert timeout == 130 and pass_fds == (8,)
        video.write_bytes(output)

    monkeypatch.setattr(ar, 'run_process_group', rclone)
    ar.copy_source(source, video, digest, pass_fds=(8,))
    for output in (b'ab', b'abcd', b'aBc'):
        with pytest.raises(ar.Blocked, match='^remote_source_bytes_changed$'):
            ar.copy_source(source, video, digest, pass_fds=(8,))


@pytest.mark.parametrize(('command', 'failure', 'diagnostic'), [
    ('rclone', 'cap', {'stage': 'rclone', 'reason': 'transfer_cap', 'exit_code': 8}),
    ('rclone', 'missing', {'stage': 'rclone', 'reason': 'remote_not_found', 'exit_code': 4}),
    ('ffprobe', 'nonzero', {'stage': 'ffprobe', 'reason': 'nonzero_exit', 'exit_code': 1}),
    ('ffmpeg', 'timeout', {'stage': 'ffmpeg', 'reason': 'timeout'}),
    ('ffmpeg', 'permission', {'stage': 'ffmpeg', 'reason': 'permission_denied'}),
])
def test_external_stage_reports_only_safe_failure_fields(tmp_path, monkeypatch, command, failure, diagnostic):
    private = 'https://private.example/token lecture text'

    def run(args, **_):
        assert args[0] == command
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(args, 1, stderr=private)
        if failure == 'permission':
            raise PermissionError(13, private)
        raise subprocess.CalledProcessError({'cap': 8, 'missing': 4}.get(failure, 1), args, stderr=private)

    monkeypatch.setattr(ar, 'run_process_group', run)
    video = tmp_path / 'source.mp4'
    with pytest.raises(ar.CommandFailed) as exc:
        if command == 'rclone':
            ar.copy_source({'remote_path': private, 'size': 3}, video, 'a' * 64)
        elif command == 'ffprobe':
            ar.probe_video(video, 5)
        else:
            ar.extract(video, tmp_path / 'window.wav', ar.Window(0, 5, 1, 2, 'token_repetition'))
    assert exc.value.diagnostic == diagnostic
    assert private not in str(exc.value)


def test_atomic_private_receipt_is_idempotent_and_not_a_publication(tmp_path):
    evidence = {'fingerprint': 'a' * 64, 'windows': [{'whisper': 'private', 'parakeet': 'private'}],
                'qa': {'passed': False}, 'published': False}
    path = tmp_path / 'result.json.gz'
    ar.write_receipt(path, evidence)
    assert json.loads(gzip.decompress(path.read_bytes())) == evidence
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        ar.write_receipt(path, {**evidence, 'windows': []})
    assert ar.read_receipt(path, evidence['fingerprint']) == evidence
    assert not list(tmp_path.glob('.result-*'))


def test_interrupted_receipt_never_looks_complete(tmp_path, monkeypatch):
    path = tmp_path / 'result.json.gz'

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(ar.os, 'link', interrupt)
    with pytest.raises(KeyboardInterrupt):
        ar.write_receipt(path, {'fingerprint': 'a' * 64})
    assert not path.exists()
    assert not list(tmp_path.iterdir())


def test_existing_qa_retains_blocker_and_input_is_immutable():
    segments = [{'start': 0, 'end': 5, 'text': 'termo técnico'}]
    original = {'flags': [{'kind': 'text_during_measured_silence', 'start': 1, 'end': 2}],
                'metrics': {}}
    backup = deepcopy(original)
    result = ar.recheck_unchanged(original, segments, 5)
    assert result['passed'] is False
    assert result['blockers'][0]['kind'] == 'text_during_measured_silence'
    assert original == backup
    assert ar.recheck_unchanged({'flags': [], 'metrics': {}}, segments, 5)['passed'] is True

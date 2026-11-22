import gzip
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from fo_hub import acoustic_review as ar


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


def test_storage_and_cgroup_limits():
    limit = ar.storage_required(100, 20)
    ar.require_storage(limit, 100, 20)
    with pytest.raises(ar.Blocked, match='storage'):
        ar.require_storage(limit - 1, 100, 20)
    assert ar.limits_ok('50000 100000', str(3 * 2**30), '0')
    for bad in [('max 100000', str(2**30), '0'), ('50100 100000', str(2**30), '0'),
                ('50000 100000', 'max', '0'), ('50000 100000', str(2**30), 'max')]:
        assert not ar.limits_ok(*bad)


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

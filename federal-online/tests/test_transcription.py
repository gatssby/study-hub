import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fo_hub import transcription as tr  # noqa: E402
from fo_hub.store import FOStore, lesson_id_for  # noqa: E402


@pytest.fixture
def store(tmp_path):
    s = FOStore(tmp_path / "fo.db")
    s.sync_lessons([{"course_id": "C", "media_id": "M1", "title": "A", "video_url": "u",
                     "duration_s": 60}])
    return s


LID = lesson_id_for("C", "M1", None)


def test_enqueue_dedup_by_lesson_and_version(store):
    q = tr.TranscriptionQueue(store)
    assert q.enqueue(LID, 1) is True
    assert q.enqueue(LID, 1) is False
    assert q.counts() == {"queued": 1}


def test_lease_progress_fail_retry_and_dead(store):
    q = tr.TranscriptionQueue(store, max_attempts=2)
    q.enqueue(LID, 1)
    job = q.lease("w1", lease_s=60, now=1000)
    assert job["lesson_id"] == LID and job["attempts"] == 1
    assert q.lease("w2", lease_s=60, now=1001) is None
    q.progress(LID, 1, "w1", 0.5)
    q.fail(LID, 1, "w1", "boom")
    assert q.counts() == {"queued": 1}
    q.lease("w1", lease_s=60, now=1002)
    q.fail(LID, 1, "w1", "boom2")
    assert q.counts() == {"failed": 1}


def test_expired_lease_recovered(store):
    q = tr.TranscriptionQueue(store)
    q.enqueue(LID, 1)
    q.lease("w1", lease_s=10, now=1000)
    assert q.lease("w2", lease_s=10, now=1005) is None
    job = q.lease("w2", lease_s=10, now=1011)
    assert job["lease_owner"] == "w2" and job["attempts"] == 2
    with pytest.raises(tr.LeaseLost):
        q.progress(LID, 1, "w1", 0.9)


def test_gate_fail_closed_by_default(tmp_path):
    g = tr.check_gate(env={}, platform_marker=tmp_path / "vps", auth_file=tmp_path / "auth")
    assert g["allowed"] is False
    assert set(g["reasons"]) >= {"TRANSCRIPTION_ENABLED is not true", "authorization file missing",
                                 "not running on VPS", "ASR adapter not implemented"}


def test_gate_still_blocked_with_all_switches_because_adapter_missing(tmp_path):
    (tmp_path / "vps").write_text("fo-vps")
    (tmp_path / "auth").write_text(tr.AUTH_PHRASE)
    g = tr.check_gate(env={"TRANSCRIPTION_ENABLED": "true"}, platform_marker=tmp_path / "vps",
                      auth_file=tmp_path / "auth", platform="linux")
    assert g["allowed"] is False and g["reasons"] == ["ASR adapter not implemented"]


def test_adapter_refuses(tmp_path):
    with pytest.raises(tr.TranscriptionBlocked):
        tr.BlockedASRAdapter().transcribe(tmp_path / "x.mp4")


def test_worker_check_only_never_leases(store, capsys):
    q = tr.TranscriptionQueue(store)
    q.enqueue(LID, 1)
    rc = tr.main(["--db", str(store.path), "--check-only"])
    assert rc == 0
    assert q.counts() == {"queued": 1}
    assert '"allowed": false' in capsys.readouterr().out


def test_worker_run_refused_when_gate_closed(store):
    assert tr.main(["--db", str(store.path), "--run"]) == 3
    assert tr.TranscriptionQueue(store).counts() == {}


def test_qa_flags_without_deleting_text():
    segs = [
        {"start": 0, "end": 4, "text": "a insuficiencia cardiaca"},
        {"start": 4, "end": 8, "text": "obrigado obrigado obrigado obrigado obrigado"},
        {"start": 7, "end": 6, "text": "texto legitimo"},
        {"start": 40, "end": 45, "text": "depois do silencio"},
        {"start": 45, "end": 46, "text": "depois do silencio"},
    ]
    rep = tr.qa_segments(segs, duration_s=50)
    kinds = {f["kind"] for f in rep["flags"]}
    assert {"token_repetition", "bad_timestamp", "non_monotonic", "silence_gap",
            "duplicate_segment"} <= kinds
    assert [s["text"] for s in rep["segments"]] == [s["text"] for s in segs]
    assert rep["metrics"]["segments"] == 5 and rep["passed"] is False
    clean = tr.qa_segments(segs[:1], duration_s=4)
    assert clean["passed"] is True

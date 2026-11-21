import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COURSE_URL = "https://www.federalonline.com.br/portal/curso-aula/produto-pacote/c123/my-course"
HASH = "abcdef0123456789"


def _entries():
    def e(media_id, title, source_ref, disciplina="Biologia"):
        return {"media_id": media_id, "item_id": media_id, "course_url": COURSE_URL,
                "titulo_original": title, "nome_real_aula": title, "disciplina": disciplina,
                "portal_subject": disciplina, "source_ref": source_ref, "status": "ok"}
    return [
        e("100", "Aula 01 - Água", "Biologia > Citologia"),
        e("200", "Vetores IV", "Física > Vetores", "Física"),
        e("300", "Comentários sobre a redação 02", "Mini Simulados > Simulado 1: 25 a 27 de jun", "Redação"),
        e("400", "Prova de 2023/2024", "Provas > UFPR", "Simulados"),
        e("500", "Aula 16 - Karl Popper: Introdução", "Obras > Filosofia", "Filosofia"),
        e("600", "Estratégias para o vestibular UFPR 2026/2027", "Estratégias", "Estratégias"),
    ]


def _catalog(state):
    d = state / "catalog/courses/my-course-abcd1234"
    d.mkdir(parents=True, exist_ok=True)
    (d / "aulas_index.json").write_text(json.dumps({"course_url": COURSE_URL, "aulas": _entries()}))
    (state / "catalog/courses.json").write_text(json.dumps(
        {"courses": [{"url": COURSE_URL, "title": "Meu Curso"}]}))


def _source(c, lid, path, available=1, revision="1"):
    c.execute("INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,?,?)",
              (lid, path, revision, 99, available, "now"))


def _remote_row(title, source_ref, media="remote:r1"):
    parts = source_ref.split(" > ")
    module = " > ".join(["my-course", HASH] + parts)
    return {"course_id": "remote:my-course", "media_id": media, "item_id": None,
            "subject": parts[0], "front": "", "module": module, "title": title,
            "media_type": "video", "video_url": None, "duration_s": None}


def _portal_row(media_id, title, source_ref, disciplina="Biologia"):
    return {"course_id": "c123", "media_id": media_id, "item_id": media_id,
            "subject": disciplina, "front": disciplina, "module": source_ref, "title": title,
            "media_type": "video", "video_url": "https://cdn/x", "duration_s": 100}


# ---------- pure matching ----------
def test_path_source_ref_strips_course_and_hash_folders():
    from fo_hub.metadata_recovery import path_source_ref
    assert path_source_ref(f"my-course > {HASH} > Biologia > Citologia") == "Biologia > Citologia"
    assert path_source_ref("my-course") == ""


@pytest.mark.parametrize("title,source_ref,media,tier", [
    ("Aula 01 - Água", "Biologia > Citologia", "100", "exact"),
    ("Comentários sobre a redação 02", "Mini Simulados > Simulado 1 - 25 a 27 de jun", "300", "exact"),
    ("Prova de 2023 - 2024", "Provas > UFPR", "400", "year"),
    ("Aula 16 - Karl Popper - Introdução", "Obras > Filosofia", "500", "separator"),
    ("Estratégias para o vestibular UFPR 2026", "Estratégias", "600", "title_updated"),
])
def test_match_catalog_tiers(title, source_ref, media, tier):
    from fo_hub.metadata_recovery import match_catalog
    got, got_tier, _ = match_catalog(_entries(), source_ref, title)
    assert got == media and got_tier == tier


def test_match_catalog_ambiguous_and_missing():
    from fo_hub.metadata_recovery import match_catalog
    entries = _entries() + [{"media_id": "101", "titulo_original": "Aula 01 - Água",
                             "nome_real_aula": "Aula 01 - Água", "source_ref": "Biologia > Citologia"}]
    assert match_catalog(entries, "Biologia > Citologia", "Aula 01 - Água")[1] == "ambiguous_title"
    assert match_catalog(_entries(), "Biologia > Citologia", "Inexistente")[1] == "no_title_match"
    assert match_catalog(_entries(), "Nada > Aqui", "Aula 01 - Água")[1] == "no_source_ref_match"


# ---------- plan / apply ----------
def _build_db(tmp_path, protected_media=()):
    from fo_hub.store import FOStore, lesson_id_for
    state = tmp_path / "state"
    (state / "catalog").mkdir(parents=True)
    _catalog(state)
    db = tmp_path / "hub.db"
    store = FOStore(db)
    c = store.conn
    c.execute("CREATE TABLE IF NOT EXISTS lesson_video_sources(lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT)")
    remotes = {}
    specs = [("100", "Aula 01 - Água", "Biologia > Citologia", "Biologia"),
             ("200", "Vetores IV", "Física > Vetores", "Física"),
             ("400", "Prova de 2023 - 2024", "Provas > UFPR", "Simulados")]
    # One authoritative sync so all portal lessons stay present (separate authoritative
    # calls would mark earlier same-course lessons missing).
    store.sync_lessons([_portal_row(m, "Prova de 2023/2024" if m == "400" else t, sr, d)
                        for m, t, sr, d in specs], authoritative=True)
    for media_id, title, sr, disc in specs:
        plid = lesson_id_for("c123", media_id, media_id)
        _source(c, plid, f"onedrive:Federal Online/my-course/new/{media_id}.mp4")
        rid = f"remote:r{media_id}"
        store.sync_lessons([_remote_row(title, sr, rid)], authoritative=False)
        rlid = lesson_id_for("remote:my-course", rid, None)
        _source(c, rlid, f"onedrive:Federal Online/my-course/{HASH}/{sr.replace(' > ', '/')}/{title}.mp4")
        c.execute("INSERT INTO transcription_jobs(lesson_id,version,state) VALUES(?,1,'queued')", (rlid,))
        if media_id in protected_media:
            c.execute("INSERT INTO transcripts(lesson_id,version,corpus) VALUES(?,1,'generated_v2')", (rlid,))
        remotes[media_id] = rlid
    store.conn.commit()
    return state, db, store, remotes


def test_plan_retires_unprotected_and_backfills_protected(tmp_path):
    from fo_hub.metadata_recovery import plan
    state, db, store, remotes = _build_db(tmp_path, protected_media=("200",))
    p = plan(state, db)
    assert p["counts"]["actions"] == 3 and p["counts"]["unresolved"] == 0
    by_lid = {a["lesson_id"]: a for a in p["actions"]}
    assert by_lid[remotes["100"]]["action"] == "retire_alias"
    assert by_lid[remotes["400"]]["action"] == "retire_alias"
    assert by_lid[remotes["200"]]["action"] == "backfill_protected"
    assert by_lid[remotes["200"]]["canonical"]["title"] == "Vetores IV"
    assert by_lid[remotes["400"]]["match_tier"] == "year"


def test_apply_retire_backfill_idempotent_and_reversible(tmp_path):
    from fo_hub.metadata_recovery import plan, apply
    state, db, store, remotes = _build_db(tmp_path, protected_media=("200",))
    p = plan(state, db)
    res = apply(state, db, p)
    assert res["retired"] == 2 and res["backfilled"] == 1
    c = store.conn
    assert c.execute("SELECT present FROM lessons WHERE lesson_id=?", (remotes["100"],)).fetchone()[0] == 0
    assert c.execute("SELECT available FROM lesson_video_sources WHERE lesson_id=?", (remotes["100"],)).fetchone()[0] == 0
    assert c.execute("SELECT state FROM transcription_jobs WHERE lesson_id=?", (remotes["100"],)).fetchone()[0] == "superseded"
    row = c.execute("SELECT subject,module,title FROM lessons WHERE lesson_id=?", (remotes["200"],)).fetchone()
    assert row["title"] == "Vetores IV" and row["module"] == "Física > Vetores" and row["subject"] == "Física"
    assert c.execute("SELECT present FROM lessons WHERE lesson_id=?", (remotes["200"],)).fetchone()[0] == 1
    # canonical portal lessons untouched
    assert c.execute("SELECT count(*) FROM lessons WHERE course_id='c123' AND present=1").fetchone()[0] == 3
    # preimage preserved for reversibility
    pre = json.loads(c.execute("SELECT preimage_json FROM lesson_metadata_recovery WHERE lesson_id=?", (remotes["200"],)).fetchone()[0])
    assert pre["title"] == "Vetores IV" and HASH in pre["module"]
    # idempotent re-apply
    again = apply(state, db, p)
    assert again["already_applied"] == 3 and again["retired"] == 0


def test_apply_rejects_tampered_plan_and_stale_protection(tmp_path):
    from fo_hub.metadata_recovery import plan, apply
    state, db, store, remotes = _build_db(tmp_path)
    p = plan(state, db)
    bad = json.loads(json.dumps(p))
    bad["actions"][0]["canonical_lesson_id"] = "fo_doesnotexist"
    with pytest.raises(ValueError):
        apply(state, db, bad)
    # protection changed after plan -> fail closed
    store.conn.execute("INSERT INTO transcripts(lesson_id,version,corpus) VALUES(?,1,'generated_v2')", (remotes["100"],))
    store.conn.commit()
    with pytest.raises(ValueError):
        apply(state, db, p)


def test_plan_leaves_unresolved_untouched(tmp_path):
    from fo_hub.metadata_recovery import plan, apply
    state, db, store, remotes = _build_db(tmp_path)
    # corrupt one remote title so it cannot match
    store.conn.execute("UPDATE lessons SET title='Título Inexistente' WHERE lesson_id=?", (remotes["100"],))
    store.conn.commit()
    p = plan(state, db)
    assert p["counts"]["unresolved"] == 1
    apply(state, db, p)
    assert store.conn.execute("SELECT present FROM lessons WHERE lesson_id=?", (remotes["100"],)).fetchone()[0] == 1


# ---------- ingest sync survival ----------
def _ingest_state(tmp_path):
    state = tmp_path / "state"
    (state / "catalog").mkdir(parents=True)
    _catalog(state)
    aula = {"media_id": "100", "item_id": "100", "course_url": COURSE_URL,
            "nome_real_aula": "Aula 01 - Água", "disciplina": "Biologia", "source_ref": "Biologia > Citologia",
            "video_stream_url": "https://cdn/x", "duracao_segundos": 100, "status": "ok"}
    (state / "catalog/aulas_index.json").write_text(json.dumps({"aulas": [aula]}))
    legacy = f"my-course/{HASH}/Biologia/Citologia/Aula 01 - Água.mp4"
    (state / "catalog/video_upload_manifest.json").write_text(json.dumps(
        {"items": [{"video_stream_url": "https://cdn/x", "remote_path": "onedrive:Federal Online/my-course/new/100.mp4",
                    "local_file_size_bytes": 99}]}))
    (state / "remote-videos.json").write_text(json.dumps([
        {"Path": "my-course/new/100.mp4", "Size": 99, "ID": "mapped"},
        {"Path": legacy, "Size": 99, "ID": "rLegacy"}]))
    return state, legacy


def test_recovery_survives_ingest_sync(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore, lesson_id_for
    from fo_hub.metadata_recovery import plan, apply
    state, legacy = _ingest_state(tmp_path)
    db = tmp_path / "hub.db"
    ingest(state, db, index_pdfs=False)
    rlid = lesson_id_for("remote:my-course", "remote:rLegacy", None)
    c = FOStore(db).conn
    assert c.execute("SELECT present FROM lessons WHERE lesson_id=?", (rlid,)).fetchone()[0] == 1
    p = plan(state, db)
    assert p["counts"]["actions"] == 1 and p["actions"][0]["action"] == "retire_alias"
    apply(state, db, p)
    # two further sync cycles must not resurrect the retired alias nor duplicate it
    ingest(state, db, index_pdfs=False)
    ingest(state, db, index_pdfs=False)
    assert c.execute("SELECT present FROM lessons WHERE lesson_id=?", (rlid,)).fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM lessons WHERE course_id='remote:my-course'").fetchone()[0] == 1
    plid = lesson_id_for("c123", "100", "100")
    assert c.execute("SELECT present,title FROM lessons WHERE lesson_id=?", (plid,)).fetchone()[0] == 1
    assert c.execute("SELECT title FROM lessons WHERE lesson_id=?", (plid,)).fetchone()[0] == "Aula 01 - Água"


def test_backfilled_protected_metadata_survives_ingest_sync(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore, lesson_id_for
    from fo_hub.metadata_recovery import plan, apply
    state, legacy = _ingest_state(tmp_path)
    db = tmp_path / "hub.db"
    ingest(state, db, index_pdfs=False)
    rlid = lesson_id_for("remote:my-course", "remote:rLegacy", None)
    store = FOStore(db)
    store.conn.execute("INSERT INTO transcripts(lesson_id,version,corpus) VALUES(?,1,'generated_v2')", (rlid,))
    store.conn.commit()
    p = plan(state, db)
    assert p["actions"][0]["action"] == "backfill_protected"
    apply(state, db, p)
    ingest(state, db, index_pdfs=False)
    ingest(state, db, index_pdfs=False)
    row = store.conn.execute("SELECT subject,module,title,present FROM lessons WHERE lesson_id=?", (rlid,)).fetchone()
    assert row["present"] == 1 and row["title"] == "Aula 01 - Água"
    assert row["module"] == "Biologia > Citologia" and row["subject"] == "Biologia"
    assert HASH not in (row["module"] or "")


# ---------- store empty-field preservation ----------
def test_non_authoritative_sync_preserves_verified_metadata(tmp_path):
    from fo_hub.store import FOStore, lesson_id_for
    store = FOStore(tmp_path / "hub.db")
    row = _portal_row("100", "Aula 01 - Água", "Biologia > Citologia")
    store.sync_lessons([row], authoritative=True)
    lid = lesson_id_for("c123", "100", "100")
    blank = {**row, "subject": "", "front": None, "module": "  ", "title": ""}
    store.sync_lessons([blank], authoritative=False)
    got = store.conn.execute("SELECT subject,front,module,title FROM lessons WHERE lesson_id=?", (lid,)).fetchone()
    assert got["subject"] == "Biologia" and got["module"] == "Biologia > Citologia" and got["title"] == "Aula 01 - Água"
    # a real rename still applies
    store.sync_lessons([{**row, "title": "Aula 01 - Água e Sais"}], authoritative=False)
    assert store.conn.execute("SELECT title FROM lessons WHERE lesson_id=?", (lid,)).fetchone()[0] == "Aula 01 - Água e Sais"

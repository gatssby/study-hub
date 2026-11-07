"""Synthetic metadata aliases only: no remote/media/ASR operations."""
import sqlite3
import pytest
from fo_hub.store import FOStore
from fo_hub import catalog_aliases as aliases


def fixture(tmp_path):
    db = tmp_path/'test.sqlite3'
    store = FOStore(db)
    store.sync_lessons([{'course_id':'course','media_id':'failed-observation','item_id':'same-item','title':'Error alias','media_type':'error'},
                        {'course_id':'course','media_id':'42','item_id':'same-item','title':'Canonical','media_type':'video'}])
    rows = {r['media_type']:dict(r) for r in store.conn.execute('select * from lessons')}
    store.conn.execute('CREATE TABLE lesson_video_sources(lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT)')
    store.conn.execute('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?,?)',
                       (rows['video']['lesson_id'],'onedrive:Federal Online/synthetic.mp4','1',9,1,'now'))
    store.conn.commit()
    return store, rows


def test_plan_is_readonly_and_apply_is_atomic_and_idempotent(tmp_path):
    store, rows = fixture(tmp_path)
    before = store.conn.execute('select count(*) from lesson_revisions').fetchone()[0]
    plan = aliases.plan(store.path)
    assert len(plan['actions']) == 1
    assert store.get_lesson(rows['error']['lesson_id'])['present'] is True
    assert aliases.apply(store.path, plan)['retired'] == 1
    assert store.get_lesson(rows['error']['lesson_id'])['present'] is False
    assert store.get_lesson(rows['video']['lesson_id'])['present'] is True
    assert store.conn.execute('select count(*) from lesson_revisions').fetchone()[0] == before
    assert aliases.apply(store.path, plan)['already_applied'] is True
    assert store.conn.execute('select count(*) from catalog_alias_retirements').fetchone()[0] == 1


@pytest.mark.parametrize('change', ['source_unavailable','source_stale','item_changed','candidate_ambiguous','protected_review','error_available','protected_transcript'])
def test_unsafe_alias_is_never_in_plan(tmp_path, change):
    store, rows = fixture(tmp_path)
    c = store.conn
    if change=='source_unavailable': c.execute('update lesson_video_sources set available=0')
    elif change=='source_stale': c.execute("update lesson_video_sources set revision='2'")
    elif change=='item_changed': c.execute("update lessons set item_id='other' where media_type='video'")
    elif change=='protected_review': c.execute("insert into transcription_jobs(lesson_id,version,state) values(?,1,'review')",(rows['error']['lesson_id'],))
    elif change=='protected_transcript': c.execute("insert into transcripts(lesson_id,version,corpus) values(?,1,'generated_v2')",(rows['error']['lesson_id'],))
    elif change=='error_available': c.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',(rows['error']['lesson_id'],'onedrive:Federal Online/retained.mp4','1',9,1,'now'))
    else:
        store.sync_lessons([{'course_id':'course','media_id':'43','item_id':'same-item','media_type':'video'}])
        lid=c.execute("select lesson_id from lessons where media_id='43'").fetchone()[0]
        c.execute('insert into lesson_video_sources values(?,?,?,?,?,?)',(lid,'onedrive:Federal Online/other.mp4','1',9,1,'now'))
    c.commit()
    assert aliases.plan(store.path)['actions'] == []
    assert store.get_lesson(rows['error']['lesson_id'])['present'] is True


def test_drift_refuses_entire_apply_without_retirement_table(tmp_path):
    store, rows = fixture(tmp_path)
    plan = aliases.plan(store.path)
    store.conn.execute('update lesson_video_sources set size=10');store.conn.commit()
    with pytest.raises(ValueError, match='stale'):
        aliases.apply(store.path, plan)
    assert store.get_lesson(rows['error']['lesson_id'])['present'] is True
    assert store.conn.execute("select count(*) from sqlite_master where name='catalog_alias_retirements'").fetchone()[0] == 0


def test_plan_cannot_create_database(tmp_path):
    path = tmp_path/'missing.sqlite3'
    with pytest.raises(sqlite3.OperationalError): aliases.plan(path)
    assert not path.exists()


def test_mid_transaction_failure_rolls_back_every_alias_and_ledger(tmp_path):
    store, rows = fixture(tmp_path)
    store.sync_lessons([{'course_id':'course','media_id':'failed-two','item_id':'same-item','media_type':'error'}])
    plan = aliases.plan(store.path)
    assert len(plan['actions']) == 2
    second = plan['actions'][1]['alias']['lesson_id']
    store.conn.execute(f"CREATE TRIGGER fail_second BEFORE UPDATE OF present ON lessons WHEN NEW.lesson_id='{second}' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    store.conn.commit()
    with pytest.raises(sqlite3.IntegrityError, match='synthetic failure'):
        aliases.apply(store.path, plan)
    assert store.conn.execute("SELECT count(*) FROM lessons WHERE media_type='error' AND present=1").fetchone()[0] == 2
    assert store.conn.execute("SELECT count(*) FROM sqlite_master WHERE name='catalog_alias_retirements'").fetchone()[0] == 0


def test_tampered_plan_is_not_applied(tmp_path):
    store, rows = fixture(tmp_path)
    plan = aliases.plan(store.path)
    plan['actions'][0]['alias']['version'] = 999
    with pytest.raises(ValueError, match='checksum'):
        aliases.apply(store.path, plan)
    assert store.get_lesson(rows['error']['lesson_id'])['present'] is True

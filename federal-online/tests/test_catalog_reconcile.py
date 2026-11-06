"""Synthetic read-only reconciliation; never uses credentials or media."""
import hashlib
import json
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fo_hub.catalog_reconcile import reconcile


def fixture(tmp_path):
    c = sqlite3.connect(tmp_path / 'hub.sqlite3')
    c.executescript('''CREATE TABLE lessons(lesson_id TEXT,course_id TEXT,media_id TEXT,item_id TEXT,media_type TEXT,present INTEGER,version INTEGER,video_url TEXT,duration_s REAL);
    CREATE TABLE lesson_video_sources(lesson_id TEXT,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER);
    CREATE TABLE transcription_jobs(lesson_id TEXT,version INTEGER,state TEXT);''')
    c.executemany('INSERT INTO lessons VALUES(?,?,?,?,?,?,?,?,?)', [
        ('retired','remote:synthetic','remote:object',None,'video',0,1,None,None),
        ('canonical','course','42','item42','video',1,2,'https://example.invalid/video?secret=SIGNED_TOKEN',600),
        ('pending','course','43','item43','video',1,1,None,600)])
    c.executemany('INSERT INTO lesson_video_sources VALUES(?,?,?,?,?)', [
        ('retired','onedrive:Federal Online/synthetic/PII_private_name.mp4','1',99,0),
        ('canonical','onedrive:Federal Online/synthetic/PII_private_name.mp4','2',99,1),
        ('pending',None,'1',None,0)])
    c.executemany('INSERT INTO transcription_jobs VALUES(?,?,?)', [('canonical',1,'queued'),('canonical',2,'queued'),('pending',1,'queued')])
    c.commit();c.close()
    (tmp_path/'remote-videos.json').write_text(json.dumps([{'Path':'synthetic/PII_private_name.mp4','Size':99}]))
    return tmp_path


def test_exact_path_alias_and_current_pending_are_read_only_and_sanitized(tmp_path):
    state=fixture(tmp_path)
    db=state/'hub.sqlite3';before=hashlib.sha256(db.read_bytes()).hexdigest()
    result=reconcile(state)
    assert result['counts']=={'total':3,'present':2,'missing':1,'pending_sources':1,'historical_error_identities':0}
    missing=result['missing'][0]
    assert missing['classification']=='retired_remote_alias_with_present_exact_path'
    assert missing['canonical_candidates'][0]['lesson_id']=='canonical'
    assert missing['canonical_candidates'][0]['current_source']
    assert result['pending_sources'][0]['lesson_id']=='pending'
    assert result['pending_sources'][0]['collector_action']=='recapture_authenticated_stream'
    assert hashlib.sha256(db.read_bytes()).hexdigest()==before
    encoded=json.dumps(result)
    for secret in ('SIGNED_TOKEN','PII_private_name','https://','onedrive:Federal'):
        assert secret not in encoded


def test_historical_errors_dedupe_branch_item_not_global_media(tmp_path):
    state=fixture(tmp_path)
    current=state/'catalog/courses/synthetic';old=state/'rebuild/g20261029a/catalog/courses/synthetic'
    current.mkdir(parents=True);old.mkdir(parents=True)
    a={'source_ref':'Disciplinas > A','item_id':'42','media_id':'42','status':'error'}
    b={**a,'source_ref':'Disciplinas > B'}
    (old/'aulas_index.json').write_text(json.dumps({'aulas':[a,a,b]}))
    (current/'aulas_index.json').write_text(json.dumps({'aulas':[{**a,'status':'ok'}]}))
    result=reconcile(state)
    assert result['historical_error_outcomes']=={'resolved_ok':1,'not_reobserved':1}
    assert result['counts']['historical_error_identities']==2


def test_absent_inventory_is_not_evidence_object_removed(tmp_path):
    state=fixture(tmp_path)
    c=sqlite3.connect(state/'hub.sqlite3');c.execute("UPDATE lessons SET present=0 WHERE lesson_id='canonical'");c.commit();c.close()
    (state/'remote-videos.json').unlink()
    result=reconcile(state)
    assert {x['classification'] for x in result['missing']}=={'missing_without_inventory_proof'}


def test_missing_database_is_not_created(tmp_path):
    import pytest
    with pytest.raises(sqlite3.OperationalError):
        reconcile(tmp_path)
    assert not (tmp_path/'hub.sqlite3').exists()

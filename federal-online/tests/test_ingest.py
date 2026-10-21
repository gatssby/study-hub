import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def test_ingest_preserves_unseen_and_queues_verified_remote_once(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore
    state=tmp_path/'state';(state/'catalog').mkdir(parents=True)
    aula={'media_id':'42','item_id':'7','course_url':'https://www.federalonline.com.br/portal/curso-aula/produto-pacote/course/2027','nome_real_aula':'Aula','disciplina':'Biologia','source_ref':'Obras > Bio','video_stream_url':'https://cdn/a.m3u8?secret=1','duracao_segundos':100,'status':'ok'}
    (state/'catalog/aulas_index.json').write_text(json.dumps({'aulas':[aula]}))
    remote='Curso 2027/Bio/Aula.mp4'
    (state/'catalog/video_upload_manifest.json').write_text(json.dumps({'items':[{'video_stream_url':'https://cdn/a.m3u8?secret=old','remote_path':'onedrive:Federal Online/'+remote,'local_file_size_bytes':99}]}))
    (state/'remote-videos.json').write_text(json.dumps([{'Path':remote,'Size':99,'ID':'remote1'}]))
    db=tmp_path/'hub.db'
    result=ingest(state,db,index_pdfs=False)
    assert result['source_videos']==1
    assert result['jobs_queued']==1
    ingest(state,db,index_pdfs=False)
    store=FOStore(db)
    assert store.conn.execute('select count(*) from transcription_jobs').fetchone()[0]==1
    assert store.conn.execute('select count(*) from lessons').fetchone()[0]==1
    assert store.conn.execute('select available from lesson_video_sources').fetchone()[0]==1


def test_changed_video_invalidates_old_source_and_enqueues_current_revision(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore
    state=tmp_path/'state';(state/'catalog').mkdir(parents=True)
    aula={'media_id':'42','item_id':'7','course_url':'https://www.federalonline.com.br/portal/curso-aula/produto-pacote/course/2027','nome_real_aula':'Aula','video_stream_url':'https://cdn/a.m3u8','duracao_segundos':100,'status':'ok'}
    index=state/'catalog/aulas_index.json'
    index.write_text(json.dumps({'aulas':[aula]}))
    remote='Curso/Aula.mp4'
    (state/'catalog/video_upload_manifest.json').write_text(json.dumps({'items':[{'video_stream_url':aula['video_stream_url'],'remote_path':'onedrive:Federal Online/'+remote,'local_file_size_bytes':99,'duration_seconds':100}]}))
    (state/'remote-videos.json').write_text(json.dumps([{'Path':remote,'Size':99,'ID':'r1'}]))
    db=tmp_path/'hub.db';ingest(state,db,index_pdfs=False)
    aula['duracao_segundos']=200
    index.write_text(json.dumps({'aulas':[aula]}))
    ingest(state,db,index_pdfs=False)
    c=FOStore(db).conn
    lid=c.execute("select lesson_id from lessons where course_id='course'").fetchone()[0]
    assert c.execute('select available from lesson_video_sources where lesson_id=?',(lid,)).fetchone()[0]==0
    assert c.execute('select version,state from transcription_jobs where lesson_id=? order by version',(lid,)).fetchall()[1][0]==2


def test_remote_fallback_is_superseded_when_catalog_source_becomes_known(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore
    state=tmp_path/'s';(state/'catalog').mkdir(parents=True)
    remote='Curso/Aula.mp4'
    (state/'remote-videos.json').write_text(json.dumps([{'Path':remote,'Size':99,'ID':'r1'}]))
    db=tmp_path/'hub.db';ingest(state,db,index_pdfs=False)
    aula={'media_id':'42','course_url':'https://www.federalonline.com.br/portal/curso-aula/produto-pacote/c/2027','video_stream_url':'https://cdn/a','status':'ok'}
    (state/'catalog/aulas_index.json').write_text(json.dumps({'aulas':[aula]}))
    (state/'catalog/video_upload_manifest.json').write_text(json.dumps({'items':[{'video_stream_url':'https://cdn/a','remote_path':'onedrive:Federal Online/'+remote,'local_file_size_bytes':99}]}))
    ingest(state,db,index_pdfs=False)
    c=FOStore(db).conn
    assert c.execute("select count(*) from lesson_video_sources where available=1").fetchone()[0]==1
    assert c.execute("select count(*) from transcription_jobs where state='queued'").fetchone()[0]==1


def test_pdf_index_ignores_staging_manifest_until_publication(tmp_path):
    from fo_hub.ingest import ingest
    from fo_hub.store import FOStore
    state=tmp_path/'s';stage=state/'materials/.build_course';stage.mkdir(parents=True)
    (stage/'a.pdf').write_bytes(b'%PDF-fixture')
    (stage/'manifest.json').write_text(json.dumps({'items':[{'status':'ok','relative_path':'a.pdf','file_name':'a.pdf'}]}))
    db=tmp_path/'hub.db';ingest(state,db,index_pdfs=False)
    c=FOStore(db).conn
    assert c.execute('select count(*) from materials').fetchone()[0]==0
    stage.rename(state/'materials/course')
    ingest(state,db,index_pdfs=False)
    assert c.execute('select count(*) from materials').fetchone()[0]==1

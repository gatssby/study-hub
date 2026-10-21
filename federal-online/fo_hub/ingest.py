"""Incremental FO metadata/PDF loader. Never imports old transcript content."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import hashlib
import json
import os
import time
from .store import FOStore, lesson_id_for
from .transcription import TranscriptionQueue


def canonical(url):
    p=urlsplit(url or '')
    return urlunsplit((p.scheme,p.netloc,p.path,'',''))


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def course_key(url):
    parts=urlsplit(url).path.strip('/').split('/')
    if 'produto-pacote' in parts:
        index=parts.index('produto-pacote')
        if len(parts)>index+1:return parts[index+1]
    return canonical(url) or 'remote-catalog'


def ingest(state,db_path,index_pdfs=True):
    state=Path(state);store=FOStore(db_path);c=store.conn
    c.executescript('''CREATE TABLE IF NOT EXISTS lesson_video_sources(
      lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT);
      CREATE TABLE IF NOT EXISTS ingestion_errors(path TEXT PRIMARY KEY,error_type TEXT,updated_at REAL);
      CREATE TABLE IF NOT EXISTS ingestion_status(component TEXT PRIMARY KEY,payload TEXT,updated_at REAL);''')
    candidates={}
    paths=sorted((state/'catalog').rglob('aulas_index*.json'))
    paths+=sorted((state/'catalogs').rglob('aulas_index*.json'))
    # Also accept dynamic runner per-course output below catalog/.
    for path in paths:
        payload=read_json(path,{})
        for item in payload.get('aulas',[]):
            if not (item.get('media_id') or item.get('item_id')):continue
            row={'course_id':course_key(item.get('course_url') or payload.get('course_url','')),'source_url':item.get('course_url') or payload.get('course_url',''),'media_id':item.get('media_id'),'item_id':item.get('item_id'),'subject':item.get('disciplina') or item.get('portal_subject'),'front':item.get('portal_subject'),'module':item.get('source_ref'),'title':item.get('nome_real_aula') or item.get('titulo_original'),'media_type':'video' if item.get('status')=='ok' else item.get('status','unknown'),'video_url':item.get('video_stream_url'),'duration_s':item.get('duracao_segundos')}
            lid=lesson_id_for(row['course_id'],row['media_id'],row['item_id'])
            at=str(item.get('captured_at') or payload.get('generated_at') or '')
            if lid not in candidates or at>=candidates[lid][0]:candidates[lid]=(at,row)
    rows=[x[1] for x in candidates.values()]
    summary=store.sync_lessons(rows,authoritative=False) if rows else {'created':0}
    queue=TranscriptionQueue(store)
    remote=read_json(state/'remote-videos.json',[])
    inventory={x['Path']:x for x in remote}
    manifests=read_json(state/'catalog/video_upload_manifest.json',{}).get('items',[])
    by_url={canonical(x.get('video_stream_url')):x for x in manifests if x.get('video_stream_url')}
    used=set();queued=0
    video_state=read_json(state/'videos.json',{}).get('items',{})
    for row in rows:
        if row['media_type']!='video':continue
        lid=lesson_id_for(row['course_id'],row['media_id'],row['item_id'])
        item=by_url.get(canonical(row['video_url']))
        full=item.get('remote_path') if item else None
        relative=full.removeprefix('onedrive:Federal Online/') if full else ''
        source=inventory.get(relative)
        key=hashlib.sha256((canonical(row['source_url'])+'|'+str(row['media_id'] or row['item_id'])).encode()).hexdigest()[:24]
        current=video_state.get(key,{})
        expected=hashlib.sha256(json.dumps([canonical(row['video_url']),row['duration_s']]).encode()).hexdigest()[:16]
        if current.get('status')=='verified' and current.get('revision')==expected:
            full=current['remote_path'];relative=full.removeprefix('onedrive:Federal Online/')
            source={'Size':current['size']}
        elif item and item.get('duration_seconds') is not None and item['duration_seconds']!=row['duration_s']:
            source=None
        if not source:continue
        used.add(relative);lesson=store.get_lesson(lid)
        with c:c.execute('INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,1,?)',(lid,full,str(lesson['version']),source['Size'],str(time.time())))
        # A fallback remote identity is metadata, not a second video to transcribe.
        aliases=c.execute("SELECT s.lesson_id FROM lesson_video_sources s JOIN lessons l USING(lesson_id) WHERE s.remote_path=? AND s.lesson_id!=? AND l.course_id LIKE 'remote:%'",(full,lid)).fetchall()
        with c:
            for alias in aliases:
                c.execute('UPDATE lesson_video_sources SET available=0 WHERE lesson_id=?',(alias[0],))
                c.execute('UPDATE lessons SET present=0 WHERE lesson_id=?',(alias[0],))
                c.execute("UPDATE transcription_jobs SET state='superseded' WHERE lesson_id=? AND state='queued'",(alias[0],))
        queued+=queue.enqueue(lid,lesson['version'])
    # Every verified remote original belongs in the queue, even if an old partial
    # portal traversal omitted it. Remote object identity is explicit, not guessed title identity.
    for relative,source in inventory.items():
        if relative in used:continue
        parts=relative.split('/')
        row={'course_id':'remote:'+parts[0],'media_id':'remote:'+str(source.get('ID') or hashlib.sha256(relative.encode()).hexdigest()),'item_id':None,'subject':parts[1] if len(parts)>2 else '', 'front':parts[2] if len(parts)>3 else '', 'module':' > '.join(parts[:-1]),'title':Path(relative).stem,'media_type':'video','video_url':None,'duration_s':None}
        store.sync_lessons([row],authoritative=False)
        lid=lesson_id_for(row['course_id'],row['media_id'],None);lesson=store.get_lesson(lid)
        with c:c.execute('INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,1,?)',(lid,'onedrive:Federal Online/'+relative,str(lesson['version']),source['Size'],str(time.time())))
        queued+=queue.enqueue(lid,lesson['version'])
    # New catalog videos not uploaded yet are explicitly pending, never ASR-consumed.
    for row in rows:
        if row['media_type']!='video':continue
        lid=lesson_id_for(row['course_id'],row['media_id'],row['item_id'])
        lesson=store.get_lesson(lid)
        source=c.execute('SELECT revision FROM lesson_video_sources WHERE lesson_id=?',(lid,)).fetchone()
        if not source or str(source['revision'])!=str(lesson['version']):
            with c:c.execute('INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,0,?)',(lid,None,str(lesson['version']),None,str(time.time())))
        queued+=queue.enqueue(lid,lesson['version'])
    page_count=0;pdf_errors=0
    manifest_paths=[state/'materials/manifest.json']+list((state/'materials').glob('*/manifest.json'))
    seen_hashes=set()
    for manifest in manifest_paths:
        for item in read_json(manifest,{}).get('items',[]):
            if item.get('status')!='ok' or not item.get('relative_path'):continue
            path=manifest.parent/item['relative_path']
            if not path.is_file() or not path.resolve().is_relative_to((state/'materials').resolve()):continue
            try:
                with path.open('rb') as f:
                    if f.read(5)!=b'%PDF-':raise ValueError('invalid PDF magic')
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in seen_hashes:continue
                seen_hashes.add(digest)
                mid='pdf_'+digest[:24]
                store.upsert_material({'material_id':mid,'subject':item.get('output_subject') or item.get('portal_subject'),'front':item.get('portal_subject'),'module':item.get('group'),'title':Path(item.get('file_name') or path.name).stem,'material_type':item.get('material_type'),'relative_path':str(path.relative_to(state)),'sha256':digest})
                count=c.execute('SELECT count(*) FROM pdf_pages WHERE material_id=?',(mid,)).fetchone()[0]
                if index_pdfs and count==0:
                    from pypdf import PdfReader
                    pages=[page.extract_text() or '' for page in PdfReader(path).pages]
                    store.set_pdf_pages(mid,pages);page_count+=len(pages)
            except Exception as exc:
                pdf_errors+=1
                with c:c.execute('INSERT OR REPLACE INTO ingestion_errors VALUES(?,?,?)',(str(path),type(exc).__name__,time.time()))
    status={**summary,'jobs_queued':queued,'source_videos':len(inventory),'pdf_new_pages':page_count,'pdf_errors':pdf_errors,'counts':store.sync_status(),'TRANSCRIPTION_ENABLED':False}
    with c:c.execute('INSERT OR REPLACE INTO ingestion_status VALUES(?,?,?)',('index',json.dumps(status),time.time()))
    c.close()
    return status


def main():
    state=Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online'))
    print(json.dumps(ingest(state,os.environ.get('STUDY_HUB_FO_DB',str(state/'hub.sqlite3'))),ensure_ascii=False))


if __name__=='__main__':main()

"""Incremental FO metadata/PDF loader. Never imports old transcript content."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import hashlib
import json
import math
import os
import time
from .store import FOStore, lesson_id_for
from .transcription import TranscriptionQueue
from .pdf_privacy import PRIVACY_POLICY_VERSION, PagePrivacy, sanitize_page


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


def review_indexed_pages(store):
    """Resume privacy review on saved extraction, including retired manifests.

    Commit small batches atomically. Never restart extraction of existing PDFs
    just to change privacy policy, and never treat a quality row as proof.
    """
    c = store.conn
    reviewed = 0
    while True:
        rows = c.execute(
            "SELECT p.material_id,p.page,p.text,q.quality,q.pii_redacted "
            "FROM pdf_pages p LEFT JOIN pdf_page_quality q USING(material_id,page) "
            "WHERE q.page IS NULL OR q.policy_version<? "
            "OR (q.quality='text' AND TRIM(REPLACE(p.text,?,''))='') LIMIT 250",
            (PRIVACY_POLICY_VERSION, "[MARCA D'AGUA REMOVIDA]")).fetchall()
        if not rows:
            return reviewed
        with c:
            for mid, number, text, old_quality, old_redacted in rows:
                page = sanitize_page(text)
                if old_quality in {'privacy_review', 'ocr_review', 'ocr_empty'}:
                    page = PagePrivacy(page.text, page.pii_redacted or bool(old_redacted), old_quality, 'blocked')
                c.execute('UPDATE pdf_pages SET text=? WHERE material_id=? AND page=?',
                          (page.text, mid, number))
                c.execute('INSERT OR REPLACE INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)',
                          (mid, number, page.quality, page.exposure, len(page.text),
                           int(page.pii_redacted or bool(old_redacted)),
                           time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), PRIVACY_POLICY_VERSION))
        reviewed += len(rows)


def observe_video_source(store, lid, full, source):
    """Compare known metadata only; absence of metadata is not content identity.

    First observation establishes a baseline, including on existing databases.
    Keep stronger known fields when a later inventory omits them. Metadata cannot
    detect same-size replacement without an ID/ModTime change; worker hashing
    protects inference, not already validated transcripts in that case.
    """
    c = store.conn
    with c:
        lesson = store.get_lesson(lid)
        old = c.execute('SELECT * FROM lesson_source_observations WHERE lesson_id=? AND remote_path=?',
                        (lid, full)).fetchone()
        metadata = {key: source.get(key) for key in ('ID', 'Size', 'ModTime')}
        previous = json.loads(old['metadata']) if old else {}
        changed = any(metadata[k] is not None and previous.get(k) is not None
                      and metadata[k] != previous[k] for k in metadata)
        if changed and old['version'] == lesson['version']:
            c.execute('UPDATE lessons SET version=version+1 WHERE lesson_id=?', (lid,))
            c.execute('INSERT INTO lesson_revisions(lesson_id,version,change_kind,title,video_url,duration_s,at) '
                      'VALUES(?,?,?,?,?,?,?)',
                      (lid, lesson['version'] + 1, 'media_changed', lesson['title'], lesson['video_url'],
                       lesson['duration_s'], time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
            lesson = store.get_lesson(lid)
        metadata = {k: v if v is not None else previous.get(k) for k, v in metadata.items()}
        c.execute('INSERT OR REPLACE INTO lesson_source_observations VALUES(?,?,?,?,?)',
                  (lid, full, json.dumps(metadata, sort_keys=True), lesson['version'], str(time.time())))
        c.execute("UPDATE transcription_jobs SET state='superseded' WHERE lesson_id=? AND version<? AND state='queued'",
                  (lid, lesson['version']))
        c.execute('INSERT OR REPLACE INTO lesson_video_sources VALUES(?,?,?,?,1,?)',
                  (lid, full, str(lesson['version']), source['Size'], str(time.time())))
    return lesson


def ingest(state,db_path,index_pdfs=True):
    state=Path(state);store=FOStore(db_path);c=store.conn
    c.executescript('''CREATE TABLE IF NOT EXISTS lesson_video_sources(
      lesson_id TEXT PRIMARY KEY,remote_path TEXT,revision TEXT,size INTEGER,available INTEGER,checked_at TEXT);
      CREATE TABLE IF NOT EXISTS lesson_source_observations(
        lesson_id TEXT NOT NULL,remote_path TEXT NOT NULL,metadata TEXT NOT NULL,
        version INTEGER NOT NULL,checked_at TEXT,PRIMARY KEY(lesson_id,remote_path));
      CREATE TABLE IF NOT EXISTS ingestion_errors(path TEXT PRIMARY KEY,error_type TEXT,updated_at REAL);
      CREATE TABLE IF NOT EXISTS ingestion_status(component TEXT PRIMARY KEY,payload TEXT,updated_at REAL);
      CREATE TABLE IF NOT EXISTS pdf_page_quality(
        material_id TEXT NOT NULL, page INTEGER NOT NULL, quality TEXT NOT NULL,
        exposure TEXT NOT NULL, extracted_chars INTEGER NOT NULL DEFAULT 0,
        pii_redacted INTEGER NOT NULL DEFAULT 0, updated_at TEXT,
        PRIMARY KEY(material_id, page));''')
    try:
        c.execute('ALTER TABLE pdf_page_quality ADD COLUMN policy_version INTEGER NOT NULL DEFAULT 1')
    except Exception:
        pass
    privacy_reviewed = review_indexed_pages(store) if index_pdfs else 0
    candidates={}
    paths=sorted((state/'catalog').rglob('aulas_index*.json'))
    paths+=sorted((state/'catalogs').rglob('aulas_index*.json'))
    # Also accept dynamic runner per-course output below catalog/.
    for path in paths:
        payload=read_json(path,{})
        for item in payload.get('aulas',[]):
            # A failed observation is retry evidence, not a media revision.
            # Keep it in the catalog/checkpoint, never overwrite known metadata
            # (or outrank a valid candidate from another catalog) with an error.
            if item.get('status') == 'error':continue
            if not (item.get('media_id') or item.get('item_id')):continue
            row={'course_id':course_key(item.get('course_url') or payload.get('course_url','')),'source_url':item.get('course_url') or payload.get('course_url',''),'media_id':item.get('media_id'),'item_id':item.get('item_id'),'subject':item.get('disciplina') or item.get('portal_subject'),'front':item.get('portal_subject'),'module':item.get('source_ref'),'title':item.get('nome_real_aula') or item.get('titulo_original'),'media_type':'video' if item.get('status')=='ok' else item.get('status','unknown'),'video_url':item.get('video_stream_url'),'duration_s':item.get('duracao_segundos')}
            lid=lesson_id_for(row['course_id'],row['media_id'],row['item_id'])
            at=str(item.get('captured_at') or payload.get('generated_at') or '')
            if lid not in candidates or at>=candidates[lid][0]:candidates[lid]=(at,row)
    rows=[x[1] for x in candidates.values()]
    summary=store.sync_lessons(rows,authoritative=False) if rows else {'created':0}
    queue=TranscriptionQueue(store)
    inventory_path=state/'remote-videos.json'
    inventory_bytes=inventory_path.read_bytes() if inventory_path.exists() else b'[]'
    remote=json.loads(inventory_bytes)
    inventory={x['Path']:x for x in remote}
    try:
        proof=read_json(state/'onedrive-status.json',{})
    except (OSError,ValueError):
        proof={}
    if not isinstance(proof,dict):proof={}
    started=proof.get('inventory_started_at')
    if (not isinstance(started,(int,float)) or isinstance(started,bool)
            or not math.isfinite(started) or started<=0
            or proof.get('inventory_sha256')!=hashlib.sha256(inventory_bytes).hexdigest()):
        started=None
    video_state=read_json(state/'videos.json',{}).get('items',{})
    verified_by_path={}
    for record in video_state.values():
        if record.get('status')=='verified':
            verified_by_path.setdefault(record.get('remote_path'),[]).append(record)

    def inventory_source(full, observed):
        if observed is None:return None
        for verified in verified_by_path.get(full,[]):
            if observed.get('Size')==verified.get('size'):continue
            checked=verified.get('checked_at')
            # Completion mtime can follow an upload that raced the listing.
            # Only a hash-bound listing START strictly after verification wins.
            if (started is None or type(checked) not in (int,float)
                    or not math.isfinite(checked) or checked<=0 or started<=checked):
                return {'Size':verified['size']}
        return observed
    if (state/'remote-videos.json').exists():
        with c:
            for existing in c.execute('SELECT lesson_id,remote_path FROM lesson_video_sources WHERE available=1').fetchall():
                relative=(existing['remote_path'] or '').removeprefix('onedrive:Federal Online/')
                if relative not in inventory:
                    c.execute('UPDATE lesson_video_sources SET available=0 WHERE lesson_id=?', (existing['lesson_id'],))
    manifests=read_json(state/'catalog/video_upload_manifest.json',{}).get('items',[])
    by_url={canonical(x.get('video_stream_url')):x for x in manifests if x.get('video_stream_url')}
    used=set();visited=set();queued=0
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
            observed=inventory.get(relative)
            source=observed if observed is not None else {'Size':current['size']}
            if observed is None and (state/'remote-videos.json').exists():
                source=None
        elif item and item.get('duration_seconds') is not None and item['duration_seconds']!=row['duration_s']:
            source=None
        if not source:continue
        used.add(relative);visited.add(lid);lesson=observe_video_source(store,lid,full,inventory_source(full,source))
        # A fallback remote identity is metadata, not a second video to transcribe.
        aliases=c.execute("SELECT s.lesson_id FROM lesson_video_sources s JOIN lessons l USING(lesson_id) WHERE s.remote_path=? AND s.lesson_id!=? AND l.course_id LIKE 'remote:%'",(full,lid)).fetchall()
        with c:
            for alias in aliases:
                c.execute('UPDATE lesson_video_sources SET available=0 WHERE lesson_id=?',(alias[0],))
                c.execute('UPDATE lessons SET present=0 WHERE lesson_id=?',(alias[0],))
                c.execute("UPDATE transcription_jobs SET state='superseded' WHERE lesson_id=? AND state='queued'",(alias[0],))
        queued+=queue.enqueue(lid,lesson['version'])
    # Persisted classified aliases remain authoritative mappings even when a
    # partial portal traversal omits them. Observe each lesson only once; never
    # promote an old mapping to a lesson whose catalog media revision changed.
    for existing in c.execute("SELECT s.*,l.version,l.present FROM lesson_video_sources s "
                              "JOIN lessons l USING(lesson_id) WHERE l.course_id NOT LIKE 'remote:%'").fetchall():
        full=existing['remote_path']
        if not full:continue
        relative=full.removeprefix('onedrive:Federal Online/')
        used.add(relative)  # a known classified path must not create a fallback
        if (existing['lesson_id'] in visited or not existing['present']
                or str(existing['revision'])!=str(existing['version'])):continue
        source=inventory_source(full,inventory.get(relative))
        if source is None:continue
        lesson=observe_video_source(store,existing['lesson_id'],full,source)
        queued+=queue.enqueue(existing['lesson_id'],lesson['version'])
    # Every verified remote original belongs in the queue, even if an old partial
    # portal traversal omitted it. Remote object identity is explicit, not guessed title identity.
    for relative,source in inventory.items():
        if relative in used:continue
        parts=relative.split('/')
        row={'course_id':'remote:'+parts[0],'media_id':'remote:'+str(source.get('ID') or hashlib.sha256(relative.encode()).hexdigest()),'item_id':None,'subject':parts[1] if len(parts)>2 else '', 'front':parts[2] if len(parts)>3 else '', 'module':' > '.join(parts[:-1]),'title':Path(relative).stem,'media_type':'video','video_url':None,'duration_s':None}
        existing=c.execute("SELECT l.media_id,l.present,l.version,s.revision FROM lesson_video_sources s JOIN lessons l USING(lesson_id) "
                           "WHERE s.remote_path=? AND l.course_id=? ORDER BY l.first_seen LIMIT 1",
                           ('onedrive:Federal Online/'+relative,row['course_id'])).fetchone()
        if existing:
            if not existing['present'] or str(existing['revision'])!=str(existing['version']):continue
            # Keep the lesson identity when the object at its known path is
            # replaced; record the new remote ID in observations, not lesson ID.
            row['media_id']=existing['media_id']
        store.sync_lessons([row],authoritative=False)
        lid=lesson_id_for(row['course_id'],row['media_id'],None)
        lesson=observe_video_source(store,lid,'onedrive:Federal Online/'+relative,
                                    inventory_source('onedrive:Federal Online/'+relative,source))
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
    manifest_paths=[state/'materials/manifest.json']+[
        p for p in (state/'materials').glob('*/manifest.json') if not p.parent.name.startswith('.build_')]
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
                    privacy_pages=[sanitize_page(page.extract_text() or '') for page in PdfReader(path).pages]
                    store.set_pdf_pages(mid,[page.text for page in privacy_pages])
                    with c:
                        c.execute('DELETE FROM pdf_page_quality WHERE material_id=?',(mid,))
                        c.executemany(
                            'INSERT INTO pdf_page_quality VALUES(?,?,?,?,?,?,?,?)',
                            [(mid,i+1,p.quality,p.exposure,len(p.text),int(p.pii_redacted),time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),PRIVACY_POLICY_VERSION)
                             for i,p in enumerate(privacy_pages)])
                    page_count+=len(privacy_pages)
            except Exception as exc:
                pdf_errors+=1
                with c:c.execute('INSERT OR REPLACE INTO ingestion_errors VALUES(?,?,?)',(str(path),type(exc).__name__,time.time()))
    status={**summary,'jobs_queued':queued,'source_videos':len(inventory),'pdf_new_pages':page_count,'privacy_reviewed_pages':privacy_reviewed,'pdf_errors':pdf_errors,'counts':store.sync_status(),'TRANSCRIPTION_ENABLED':False}
    with c:c.execute('INSERT OR REPLACE INTO ingestion_status VALUES(?,?,?)',('index',json.dumps(status),time.time()))
    c.close()
    return status


def main():
    state=Path(os.environ.get('FO_STATE_ROOT','/home/ubuntu/study-hub-state/federal-online'))
    print(json.dumps(ingest(state,os.environ.get('STUDY_HUB_FO_DB',str(state/'hub.sqlite3'))),ensure_ascii=False))


if __name__=='__main__':main()

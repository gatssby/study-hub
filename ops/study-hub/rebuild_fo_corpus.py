#!/usr/bin/env python3
"""Fail-closed, receipt-backed FO rebuild. All remote I/O is injectable."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time

ROOTS = ('onedrive:Federal Online', 'onedrive:Federal Online PDFs', 'onedrive:Study Hub/federal-online')
DEFAULT_STATE = '/home/ubuntu/study-hub-state/federal-online'


def guard_remote(path, *, object_only=False):
    if not isinstance(path, str) or '..' in path.split('/') or '\\' in path:
        raise ValueError('unsafe remote path')
    if not any(path == root or path.startswith(root + '/') for root in ROOTS):
        raise ValueError('remote outside FO roots')
    if object_only and path in ROOTS:
        raise ValueError('operation requires an object, not a root')
    return path


def guard_local(state, path):
    state, path = Path(state).absolute(), Path(path).absolute()
    try:
        relative = path.relative_to(state)
    except ValueError:
        raise ValueError('outside state') from None
    if '..' in relative.parts or not relative.parts or relative.parts[0] not in {'materials','tmp','rebuild','logs','transcripts'}:
        raise ValueError('local deletion outside allowlist')
    if len(relative.parts) < 2 or (relative.parts[0] == 'transcripts' and relative.parts[1] != 'review-retired'):
        raise ValueError('protected local directory')
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError('symlinks forbidden')
    if not path.resolve().is_relative_to(state.resolve()):
        raise ValueError('outside resolved state')
    return path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def checksum(value):
    return hashlib.sha256(canonical({k:v for k,v in value.items() if k != 'checksum'})).hexdigest()


def write_checked(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(value, checksum=checksum(value))
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('wb') as f:
        f.write(canonical(value)); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return value


def read_checked(path):
    value = json.loads(Path(path).read_text())
    if value.get('checksum') != checksum(value):
        raise ValueError('checksum mismatch: ' + str(path))
    return value


def quickxor(data):
    """160-bit ring; each byte starts 11 bits later; LE length at byte 12."""
    accumulator = 0
    for i, byte in enumerate(data):
        shift = (i * 11) % 160
        expanded = byte << shift
        accumulator ^= (expanded & ((1 << 160)-1)) ^ (expanded >> 160)
    accumulator ^= len(data) << 96
    return accumulator.to_bytes(20, 'little').hex()  # rclone lsjson/hashsum hex form


def file_identity(path):
    # Streaming QuickXor avoids holding a large original in memory.
    sha = hashlib.sha256(); acc = 0; length = 0; mask = (1 << 160)-1
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            sha.update(block)
            for byte in block:
                v = byte << ((length * 11) % 160)
                acc ^= (v & mask) ^ (v >> 160); length += 1
    acc ^= length << 96
    return {'sha256':sha.hexdigest(), 'size':length, 'quickxor':acc.to_bytes(20,'little').hex()}


@contextmanager
def exclusive_lock(state):
    path = Path(state)/'locks/rebuild.lock'; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('rebuild lock held') from None
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)


class Rclone:
    def run(self, command, *args):
        if command not in {'lsjson','copyto','deletefile','moveto'}:
            raise ValueError('rclone command forbidden')
        for arg in args:
            if str(arg).startswith('onedrive:'):
                guard_remote(str(arg), object_only=command != 'lsjson')
        return subprocess.run(['rclone',command,*map(str,args)], check=True, capture_output=True, text=True).stdout

    def lsjson(self, root):
        guard_remote(root)
        return json.loads(self.run('lsjson',root,'-R','--files-only','--hash','--hash-type','quickxor'))

    def copyto(self, local, remote):
        guard_remote(remote, object_only=True); self.run('copyto','--immutable',local,remote)

    def copyto_remote_to_local(self, remote, local):
        guard_remote(remote, object_only=True); self.run('copyto',remote,local)

    def deletefile(self, remote):
        guard_remote(remote, object_only=True); self.run('deletefile',remote)

    def moveto(self, remote_src, remote_dst):
        guard_remote(remote_src,object_only=True); guard_remote(remote_dst,object_only=True)
        self.run('moveto',remote_src,remote_dst)


def active_units():
    active = []
    for name in ('catalog','materials','videos','index','transcription'):
        unit = 'study-hub-fo-' + name
        result = subprocess.run(['systemctl','is-active',unit], capture_output=True, text=True)
        if result.returncode not in (0,3):
            raise RuntimeError('cannot establish unit state: '+unit)
        if result.stdout.strip() == 'active': active.append(unit)
    return active


def rows(db, table):
    if not Path(db).exists(): return []
    with sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro', uri=True) as c:
        c.row_factory = sqlite3.Row
        if not c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(table,)).fetchone(): return []
        return [dict(x) for x in c.execute('SELECT * FROM '+table)]


def expected(action):
    """Remote size/quickxor a receipt must match (equivalents point at different bytes)."""
    return {'size':action.get('remote_size',action['size']),'quickxor':action.get('remote_quickxor',action['quickxor'])}


def _pdf_sources(plan):
    """Planned originals with their manifest metadata, grouped by content identity."""
    from fo_hub.disciplines import discipline_for
    groups = {}
    for a in plan['actions']:
        if a['action'] not in {'upload_missing_original', 'register_original', 'register_equivalent'}: continue
        local = Path(a['local']); meta = {}
        for parent in local.parents:
            manifest = parent/'manifest.json'
            if manifest.is_file():
                rel = local.relative_to(parent).as_posix()
                meta = next((x for x in json.loads(manifest.read_text()).get('items', [])
                             if x.get('status') == 'ok' and x.get('relative_path') == rel), {})
                break
            if parent.name == 'materials': break
        front = meta.get('portal_subject') or (local.parent.name if local.parent.name != 'materials' else None)
        groups.setdefault(a['content_sha256'], []).append(dict(
            local=str(local), course_id=local.relative_to(Path(plan['state_root'])/'materials').parts[0],
            subject=discipline_for(meta.get('output_subject') or front, front, meta.get('group')),
            front=front, module=meta.get('group'), title=Path(meta.get('file_name') or local.name).stem,
            relative_path=local.relative_to(Path(plan['state_root'])).as_posix(),
            onedrive_path=a['remote'], quickxor=expected(a)['quickxor'], byte_sha256=a.get('remote_sha256',a['sha256']), size=expected(a)['size']))
    return groups


PDF_TABLES = ('materials','pdf_pages','pdf_page_quality','pdf_source_observations','pdf_ocr_jobs','pdf_page_structure','material_originals')
OPERATIONAL = {'focused_reviews':'1', 'transcripts':'1', 'transcript_segments':'1',
               'transcription_jobs':"state NOT IN ('queued','superseded') OR attempts>0", 'lesson_revisions':'1'}


def build_generation_db(generation_dir, plan):
    """Lessons/queue via ingest; PDFs only through the watermark-free extractor."""
    from fo_hub.ingest import ingest
    from fo_hub.pdf_extract import extract_document
    from fo_hub.pdf_index import build
    generation_dir = Path(generation_dir); db = generation_dir/'hub.sqlite3'
    active = Path(plan['state_root'])/'hub.sqlite3'
    if active.exists() and not db.exists():
        # Start from a consistent snapshot of the active DB so queue history,
        # focused reviews, transcripts and observations survive the rebuild.
        tmp = db.with_name(db.name+'.partial')
        if tmp.exists(): tmp.unlink()
        src = sqlite3.connect(active.resolve().as_uri()+'?mode=ro', uri=True); dst = sqlite3.connect(tmp)
        try: src.backup(dst)
        finally: dst.close(); src.close()
        os.replace(tmp, db)
    with sqlite3.connect(db) as c:  # byte-keyed PDF rows are replaced by content identities
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in PDF_TABLES:
            if table in names: c.execute('DELETE FROM '+table)
    ingest(generation_dir, db, index_pdfs=False)
    with sqlite3.connect(db) as c:
        c.execute('DELETE FROM materials')
    groups = _pdf_sources(plan)

    def documents():
        for content in sorted(groups):
            first = groups[content][0]
            yield extract_document(first['local'], material_meta=first)
    counts = build(generation_dir, db, documents())
    with sqlite3.connect(db) as c:
        for content, items in groups.items():
            mid = 'pdf_' + content[:24]
            c.executemany('INSERT OR REPLACE INTO material_originals VALUES(?,?,?,?,?,?,?,?)',
                          [(mid, x['course_id'], x['relative_path'], x['onedrive_path'], x['byte_sha256'],
                            x['quickxor'], x['size'], datetime.now(timezone.utc).isoformat()) for x in items])
    return counts


class Orchestrator:
    def __init__(self, state, generation, *, rclone=None, unit_check=active_units,
                 builder=build_generation_db, identity=None, runner=subprocess.run):
        self.state = Path(state).absolute()
        if not re.fullmatch(r'g[A-Za-z0-9_-]+', generation): raise ValueError('invalid generation')
        self.generation = generation; self.directory = self.state/'rebuild'/generation
        if self.directory.is_symlink() or (self.state/'rebuild').is_symlink(): raise ValueError('generation symlink')
        self.directory.mkdir(parents=True,exist_ok=True)
        self.remote = rclone or Rclone(); self.unit_check = unit_check; self.builder = builder
        self.identity = identity; self.runner = runner

    def journal(self, phase, action, key='', status='ok', detail=None):
        with (self.directory/'journal.jsonl').open('a') as f:
            f.write(json.dumps(dict(ts=datetime.now(timezone.utc).isoformat(),phase=phase,action=action,key=key,status=status,detail=detail))+'\n')
            f.flush(); os.fsync(f.fileno())

    def receipt_path(self,key):
        return self.directory/'receipts'/(hashlib.sha256(key.encode()).hexdigest()+'.json')

    def inventory(self):
        result = {}
        for root in ROOTS[:2]:
            for entry in self.remote.lsjson(root):
                full = root+'/'+entry['Path']; guard_remote(full,object_only=True)
                if not full.startswith(root+'/'): raise ValueError('listing escaped root')
                q = entry.get('Hashes',{}).get('quickxor')
                if not q: raise ValueError('remote missing quickxor: '+full)
                result[full] = {'remote':full,'size':entry['Size'],'quickxor':q, 'id':entry.get('ID'), 'modtime':entry.get('ModTime')}
        return result

    def remote_identity(self, remote, listing, cache, identity):
        """Content identity of an existing remote object (bounded temp download, cached by size+quickxor)."""
        key='remote:'+listing['size'].__str__()+':'+listing['quickxor']
        if key in cache: return cache[key]
        if shutil.disk_usage(self.state).free<2*listing['size']+2*1024**3: raise RuntimeError('disk reserve prevents remote identity')
        temp=self.state/'tmp'/('rebuild-ident-'+self.generation); temp.mkdir(parents=True,exist_ok=True)
        target=temp/'remote.pdf'
        try:
            self.remote.copyto_remote_to_local(remote,target)
            got=file_identity(target)
            if got['size']!=listing['size'] or got['quickxor']!=listing['quickxor']: raise RuntimeError('remote changed during identity: '+remote)
            cache[key]={**identity(target),**got}
        finally:
            if target.exists(): guard_local(self.state,target).unlink()
            temp.rmdir()
        return cache[key]

    def valid_receipt(self, action, inventory):
        try: receipt = read_checked(self.receipt_path(action['key']))
        except (OSError,ValueError): return False
        current = inventory.get(receipt.get('remote'))
        if 'size' not in receipt or 'quickxor' not in receipt: return False
        return bool(current and receipt.get('plan_checksum') == self.load_plan()['checksum'] and
                    receipt.get('remote')==action.get('remote') and receipt.get('key')==action.get('key') and
                    all(current.get(k)==expected(receipt)[k]==expected(action)[k] for k in ('size','quickxor')))

    def load_plan(self):
        # Re-validate the checksum whenever the file changes; avoid re-reading
        # a multi-MB plan once per action inside receipt checks.
        path=self.directory/'plan.json'; st=path.stat(); key=(st.st_size,st.st_mtime_ns,st.st_ino)
        if getattr(self,'_plan_key',None)!=key: self._plan,self._plan_key=read_checked(path),key
        return self._plan

    def plan(self):
        inventory = self.inventory()
        write_checked(self.directory/'remote-listing.json', {'objects':inventory})
        actions=[]; local=[]
        cache_path=self.directory/'identity-cache.json'
        try: cache=read_checked(cache_path).get('entries',{})
        except (OSError,ValueError): cache={}
        identity=self.identity
        if identity is None:
            from fo_hub.pdf_identity import content_identity
            identity=content_identity
        for path in sorted((self.state/'materials').rglob('*.pdf')):
            if any(part.startswith('.build_') for part in path.relative_to(self.state/'materials').parts): continue  # in-flight staging
            guard_local(self.state,path)
            st=path.stat(); key=':'.join(map(str,(path,st.st_size,st.st_mtime_ns,st.st_ino,st.st_ctime_ns)))
            if key not in cache: cache[key]={**identity(path), **file_identity(path)}
            item=dict(cache[key],local=str(path),remote=ROOTS[1]+'/'+path.relative_to(self.state/'materials').as_posix())
            local.append(item)
            same=next((v for v in inventory.values() if v['remote'].startswith(ROOTS[1]+'/') and all(v[k]==item[k] for k in ('size','quickxor'))),None)
            if same: item['remote']=same['remote']
            equivalent=False
            if not same and item['remote'] in inventory:
                listing=inventory[item['remote']]
                other=self.remote_identity(item['remote'],listing,cache,identity)
                if other.get('content_sha256')==item['content_sha256'] and other.get('identity_version')==item.get('identity_version'):
                    # Watermark-only re-download: the remote is a verified substitute.
                    equivalent=True
                    item.update(remote_size=listing['size'],remote_quickxor=listing['quickxor'],remote_sha256=other['sha256'])
                else:
                    item['remote']=ROOTS[1]+'/_originals/'+item['sha256']+'.pdf'
            action='register_original' if same else 'register_equivalent' if equivalent else 'upload_missing_original'
            actions.append(dict(item,action=action,key=action+':'+str(path)))
            actions.append(dict(item,action='drop_local_copy',key='drop_local_copy:'+str(path)))
            if not same and not equivalent: actions.append(dict(item,action='protect_unique',key='protect_unique:'+str(path)))
        write_checked(cache_path,{'entries':cache})
        groups={}
        for item in inventory.values():
            if item['remote'].startswith(ROOTS[0]+'/'):
                actions.append(dict(item,action='register_video',key='register_video:'+item['remote']))
                groups.setdefault((item['size'],item['quickxor']),[]).append(item)
        duplicates=[g for g in groups.values() if len(g)>1]
        for group in duplicates:
            for item in group[1:]: actions.append(dict(item,keeper=group[0]['remote'],action='dedupe_video_candidate',key='dedupe:'+item['remote']))
        lessons=rows(self.state/'hub.sqlite3','lessons'); sources=rows(self.state/'hub.sqlite3','lesson_video_sources')
        missing=[s['lesson_id'] for s in sources if s.get('remote_path') not in inventory]
        from fo_hub.disciplines import discipline_for
        catalogs=[]
        for p in (self.state/'catalog').rglob('aulas_index*.json'): catalogs.extend(json.loads(p.read_text()).get('aulas',[]))
        materials=rows(self.state/'hub.sqlite3','materials')
        contents={x['content_sha256'] for x in local}
        actions.append({'action':'retire_material_rows','key':'retire_material_rows','count':max(0,len(materials)-len(contents))})
        counts={'courses':len({x.get('course_id') for x in lessons}), 'disciplines':len({discipline_for(x.get('subject'),x.get('front'),x.get('module')) for x in lessons}),
                'lessons_present':sum(bool(x.get('present')) for x in lessons),'lessons_total':len(lessons),'catalog_lessons':len(catalogs),
                'distinct_videos':len(groups),'duplicate_video_groups':len(duplicates),'pdfs_local':len(local),
                'pdfs_remote':sum(x.startswith(ROOTS[1]+'/') for x in inventory),'distinct_pdf_bytes':len({x['sha256'] for x in local}),
                'distinct_pdf_content':len(contents),'db_material_rows':len(materials),'bytes_local':sum(x['size'] for x in local),
                'bytes_remote':sum(x['size'] for x in inventory.values()),'vps_free_bytes':shutil.disk_usage(self.state).free,
                'estimated_transfer_bytes':sum(x['size'] for x in actions if x['action']=='upload_missing_original')}
        plan={'generation':self.generation,'state_root':str(self.state),'counts':counts,'actions':actions,'active_lessons':[x['lesson_id'] for x in lessons if x.get('present')],
              'explicit_missing_lessons':[], 'lessons_without_available_video_source':missing,
              'db_sources_remote_missing':[x for x in sources if x.get('remote_path') not in inventory],
              'local_absent_remotely':[x['local'] for x in actions if x['action']=='upload_missing_original'],
              'remote_absent_locally':[k for k in inventory if k.startswith(ROOTS[1]+'/') and not any(x['remote']==k for x in local)]}
        plan=write_checked(self.directory/'plan.json',plan); self.journal('plan','complete',detail=counts)
        return plan

    def stage(self, execute=False, limit=None, rate_limit_s=0, max_transfer_bytes=None, refresh_catalog=False):
        plan=self.load_plan()
        if not execute: return {'dry_run':True,'actions':plan['actions']}
        if self.unit_check(): raise RuntimeError('FO units active')
        inventory=self.inventory(); transferred=0; done=0
        for action in plan['actions']:
            if action['action'] not in {'upload_missing_original','register_original','register_equivalent','register_video','drop_local_copy'}: continue
            if self.valid_receipt(action,inventory): continue
            if limit is not None and done>=limit: break
            current=inventory.get(action['remote'])
            if not current or any(current[k]!=expected(action)[k] for k in ('size','quickxor')):
                if action['action']!='upload_missing_original':
                    if action['action']=='drop_local_copy': continue
                    raise RuntimeError('remote changed: '+action['remote'])
                if current: raise RuntimeError('refuse overwrite of changed original')
                if max_transfer_bytes is not None and transferred+action['size']>max_transfer_bytes: break
                if any(file_identity(action['local'])[k]!=action[k] for k in ('size','quickxor','sha256')): raise RuntimeError('local changed')
                self.remote.copyto(action['local'],action['remote']); transferred+=action['size']
                inventory=self.inventory(); current=inventory.get(action['remote'])
            if not current or any(current[k]!=expected(action)[k] for k in ('size','quickxor')): raise RuntimeError('upload verification failed')
            receipt=write_checked(self.receipt_path(action['key']),dict(action,plan_checksum=plan['checksum']))
            self.journal('stage',action['action'],action['key'],detail={'bytes':action['size'] if action['action']=='upload_missing_original' else 0})
            done+=1
            if rate_limit_s: time.sleep(rate_limit_s)
        required=[a for a in plan['actions'] if a['action'] in {'upload_missing_original','register_original','register_equivalent','register_video'}]
        if not all(self.valid_receipt(a,inventory) for a in required): return {'complete':False,'bytes_transferred':transferred}
        for name in ('catalog','videos.json','remote-videos.json'):
            src=self.state/name; dst=self.directory/name
            if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
            elif src.is_file(): shutil.copy2(src,dst)
        # Ingest must consume this fresh inventory, not a stale active snapshot.
        (self.directory/'remote-videos.json').write_text(json.dumps([{'Path':k[len(ROOTS[0])+1:],'Size':v['size'],'Hashes':{'quickxor':v['quickxor']},'ID':v['id'],'ModTime':v['modtime']} for k,v in inventory.items() if k.startswith(ROOTS[0]+'/')]))
        if refresh_catalog:
            self.runner(['/home/ubuntu/study-hub-venv/bin/python','-m','portal.runtime','catalog','--state-root',str(self.directory)],check=True)
        self.builder(self.directory,plan)
        self.journal('stage','complete',detail={'bytes_transferred':transferred})
        return {'complete':True,'bytes_transferred':transferred}

    def verify(self, execute=False):
        plan=self.load_plan()
        if not execute: return {'dry_run':True,'checks':['remote receipts','materials identity','lessons','queue','plugin queries']}
        inventory=self.inventory(); errors=[]
        registered=[a for a in plan['actions'] if a['action'] in {'upload_missing_original','register_original','register_equivalent','register_video'}]
        for a in registered:
            if not self.valid_receipt(a,inventory): errors.append('invalid receipt: '+a['key'])
        db=self.directory/'hub.sqlite3'
        if not db.exists(): errors.append('generation DB missing')
        mats=rows(db,'materials'); ids={}; content_ids={}
        originals={a.get('content_sha256') for a in registered if a['action']!='register_video' and self.valid_receipt(a,inventory)}
        for material in mats:
            mid=material['material_id']; content=material.get('content_sha256')
            if content is None and material.get('sha256') in originals:
                content=material['sha256']  # pdf_index stores content identity in materials.sha256
            if content is None:
                matches={a['content_sha256'] for a in registered if a.get('sha256')==material.get('sha256') and 'content_sha256' in a}
                if len(matches)==1: content=matches.pop()
            if not content or content not in originals: errors.append('material lacks registered original: '+mid)
            if mid in ids and ids[mid]!=content: errors.append('material id collision: '+mid)
            if content in content_ids and content_ids[content]!=mid: errors.append('content assigned multiple material IDs: '+str(content))
            ids[mid]=content; content_ids[content]=mid
        for table,where in OPERATIONAL.items():
            def count(path):
                if not Path(path).exists(): return 0
                with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as c:
                    if not c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(table,)).fetchone(): return 0
                    return c.execute(f'SELECT count(*) FROM {table} WHERE {where}').fetchone()[0]
            if count(db)<count(self.state/'hub.sqlite3'): errors.append('operational state lost: '+table)
        present={x['lesson_id'] for x in rows(db,'lessons') if x.get('present')}
        lost=set(plan['active_lessons'])-present-set(plan['explicit_missing_lessons'])
        if lost: errors.append('lost lessons: '+','.join(sorted(lost)))
        sources={x['lesson_id']:x for x in rows(db,'lesson_video_sources')}
        verified={a['remote'] for a in registered if a['action']=='register_video' and self.valid_receipt(a,inventory)}
        for job in rows(db,'transcription_jobs'):
            if job['state'] not in {'queued','running','leased'}: continue
            source=sources.get(job['lesson_id'],{})
            if not source.get('available') or source.get('remote_path') not in verified: errors.append('queue without verified source: '+job['lesson_id'])
        if db.exists():
            try:
                from fo_hub.store import FOStore
                store=FOStore(db,readonly=True)
                try:
                    store.list_lessons(); store.search_materials(); store.sync_status()
                    for material in mats[:3]:
                        if store.get_pdf_text(material['material_id']) is None: raise ValueError('missing PDF text')
                finally: store.conn.close()
            except Exception as exc: errors.append('plugin queries: '+str(exc))
        result=write_checked(self.directory/'verify.json',{'pass':not errors,'plan_checksum':plan['checksum'],'db_sha256':hashlib.sha256(db.read_bytes()).hexdigest() if db.exists() else None,'divergences':errors})
        self.journal('verify','complete',status='failed' if errors else 'ok',detail=errors)
        return result

    def cutover(self, execute=False, rollback=False, crash_hook=lambda step: None):
        plan=self.load_plan(); active=self.state/'hub.sqlite3'; new=self.directory/'hub.sqlite3'; previous=self.directory/'previous-hub.sqlite3'
        marker=self.state/'rebuild/active-generation.json'; intent=self.directory/'cutover-intent.json'
        if not execute: return {'dry_run':True,'rollback':rollback}
        if self.unit_check(): raise RuntimeError('FO units active')
        try: current=read_checked(marker)
        except FileNotFoundError: current={}
        if rollback:
            if current.get('generation')!=self.generation or not previous.exists(): raise RuntimeError('no rollback database')
            self.checkpoint(active)
            os.replace(active,self.directory/'rolled-forward-hub.sqlite3'); os.replace(previous,active)
            write_checked(marker,{'generation':None,'rolled_back':self.generation,'at':time.time()})
            if intent.exists(): intent.unlink()  # a later cutover must restart from a verified DB
            self.journal('cutover','rollback'); return {'rolled_back':True}
        if current.get('generation')==self.generation:
            if current.get('plan_checksum')!=plan['checksum']: raise RuntimeError('active plan changed')
            return {'already_active':True}
        verification=read_checked(self.directory/'verify.json')
        if not verification['pass'] or verification['plan_checksum']!=plan['checksum']: raise RuntimeError('verification missing or plan changed')
        def verified(db):
            self.checkpoint(db)
            return hashlib.sha256(db.read_bytes()).hexdigest()==verification['db_sha256']
        if new.exists() and not verified(new): raise RuntimeError('verified DB changed')
        if not intent.exists():
            if not new.exists(): raise RuntimeError('generation DB missing')
            write_checked(intent,{'plan_checksum':plan['checksum'],'prior_generation':current.get('generation')})
        elif read_checked(intent)['plan_checksum']!=plan['checksum']: raise RuntimeError('cutover intent mismatch')
        if not previous.exists():
            if not active.exists(): raise RuntimeError('active DB missing')
            self.checkpoint(active); os.replace(active,previous); crash_hook('old_moved')
        if new.exists():
            if active.exists(): raise RuntimeError('ambiguous cutover state')
            os.replace(new,active); crash_hook('new_moved')
        if not active.exists():
            os.replace(previous,active); raise RuntimeError('new DB lost; restored previous')
        if not verified(active): raise RuntimeError('active DB is not the verified generation')
        write_checked(marker,{'generation':self.generation,'previous_generation':read_checked(intent).get('prior_generation'),'plan_checksum':plan['checksum'],'at':time.time()})
        self.journal('cutover','complete'); return {'active':self.generation}

    @staticmethod
    def checkpoint(db):
        if not Path(db).exists(): raise RuntimeError('database missing')
        with sqlite3.connect(db) as c:
            if c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]: raise RuntimeError('database busy')
        for suffix in ('-wal','-shm'):
            side=Path(str(db)+suffix)
            if side.exists(): side.unlink()

    def cleanup(self, execute=False, dedupe_videos=False, drop_previous_db=False, force_drop_previous=False, previous_days=7):
        plan=self.load_plan()
        if not execute: return {'dry_run':True,'actions':[a for a in plan['actions'] if a['action']=='drop_local_copy']}
        if self.unit_check(): raise RuntimeError('FO units active')
        marker=read_checked(self.state/'rebuild/active-generation.json')
        if marker.get('generation')!=self.generation or marker.get('plan_checksum')!=plan['checksum']: raise RuntimeError('cutover required')
        protected={a['local'] for a in plan['actions'] if a['action']=='protect_unique'}
        deleted=[]; pending=[]; listing=self.inventory()
        for action in plan['actions']:
            if action['action']!='drop_local_copy': continue
            if action['local'] in protected:
                pending.append(action); continue
            if not self.valid_receipt(action,listing): pending.append(action); continue
            path=guard_local(self.state,action['local'])
            if path.exists():
                actual=file_identity(path)
                if any(actual[k]!=action[k] for k in ('size','quickxor','sha256')): pending.append(action); continue
                path.unlink(); deleted.append(str(path))
        if dedupe_videos:
            for a in plan['actions']:
                if a['action']!='dedupe_video_candidate': continue
                if any(s.get('remote_path')==a['remote'] for s in rows(self.state/'hub.sqlite3','lesson_video_sources')):
                    raise RuntimeError('dedupe candidate is referenced by active lessons')
                inv=self.inventory()
                if not all(p in inv and all(inv[p][k]==a[k] for k in ('size','quickxor')) for p in (a['remote'],a['keeper'])): continue
                if shutil.disk_usage(self.state).free<2*a['size']+2*1024**3: raise RuntimeError('disk reserve prevents dedupe')
                temp=self.state/'tmp'/('rebuild-dedupe-'+self.generation); temp.mkdir(parents=True,exist_ok=True)
                left=temp/'left'; right=temp/'right'
                try:
                    self.remote.copyto_remote_to_local(a['remote'],left); self.remote.copyto_remote_to_local(a['keeper'],right)
                    l=file_identity(left); r=file_identity(right)
                    if l!=r or l['size']!=a['size'] or l['quickxor']!=a['quickxor']: raise RuntimeError('duplicate bytes differ')
                    fresh=self.inventory()
                    if any(fresh.get(p)!=inv[p] for p in (a['remote'],a['keeper'])): raise RuntimeError('duplicate changed during validation')
                    self.remote.deletefile(a['remote'])
                    if a['remote'] in self.inventory(): raise RuntimeError('delete not confirmed')
                    deleted.append(a['remote'])
                finally:
                    for p in (left,right):
                        if p.exists(): guard_local(self.state,p).unlink()
        previous=self.directory/'previous-hub.sqlite3'
        if drop_previous_db and previous.exists():
            if not force_drop_previous and time.time()-marker['at']<previous_days*86400: raise RuntimeError('previous DB retention not elapsed')
            guard_local(self.state,previous).unlink(); deleted.append(str(previous))
        # Only old, unlocked scratch trees with explicitly allowed names.
        tmp=self.state/'tmp'
        for p in tmp.iterdir() if tmp.exists() else []:
            if not (p.name=='videos' or p.name.startswith(('playwright-','preparation-tests-'))): continue
            guard_local(self.state,p)
            if time.time()-p.stat().st_mtime<3600 or (p.is_dir() and any(p.rglob('*.lock'))): continue
            if p.is_dir():
                if any(x.is_symlink() for x in p.rglob('*')): continue
                shutil.rmtree(p)
            else: p.unlink()
            deleted.append(str(p))
        for old in (self.state/'rebuild').glob('g*'):
            if old.name in {self.generation, marker.get('previous_generation')} or not old.is_dir(): continue
            guard_local(self.state,old)
            entries=list(old.rglob('*'))
            # Keep generations with potential sole exemplars or databases until
            # their identities are reconciled; never infer coverage from age.
            if any(p.is_symlink() or p.suffix.lower() in {'.pdf','.sqlite3','.db'} or p.name.endswith('.lock') for p in entries): continue
            if time.time()-old.stat().st_mtime<3600: continue
            shutil.rmtree(old); deleted.append(str(old))
        for p in (self.state/'logs').glob('*'):
            guard_local(self.state,p)
            if p.is_file() and p.stat().st_size>50*1024*1024:
                archive=p.with_name(p.name+'.retired')
                if archive.exists(): guard_local(self.state,archive).unlink()
                shutil.copy2(p,archive)
                with p.open('wb'): pass
        write_checked(self.directory/'protected.json',{'pending':pending,'protected':sorted(protected)})
        report=write_checked(self.directory/'cleanup.json',{'deleted':deleted,'pending':len(pending)})
        self.journal('cleanup','complete',detail=report); return report

    def status(self):
        plan=self.load_plan(); inventory=self.inventory()
        eligible=[a for a in plan['actions'] if a['action'] in {'register_video','upload_missing_original','register_original','register_equivalent'}]
        good=[a for a in eligible if self.valid_receipt(a,inventory)]
        journal=[json.loads(line) for line in (self.directory/'journal.jsonl').read_text().splitlines()] if (self.directory/'journal.jsonl').exists() else []
        phases={x['phase']:x['status'] for x in journal if x['action']=='complete'}
        return {'generation':self.generation,'phases':phases,'lessons_discovered':plan['counts']['lessons_total'],
                'videos_verified':sum(a['action']=='register_video' for a in good),'pdfs_verified':sum(a['action']!='register_video' for a in good),
                'bytes_transferred':sum((x.get('detail') or {}).get('bytes',0) for x in journal if isinstance(x.get('detail'),dict)),
                'reused':sum(a['action']=='register_original' for a in good),'equivalent':sum(a['action']=='register_equivalent' for a in good),'new':sum(a['action']=='upload_missing_original' for a in good),
                'failures':sum(x['status']=='failed' for x in journal),'divergences':read_checked(self.directory/'verify.json').get('divergences',[]) if (self.directory/'verify.json').exists() else [],
                'percent_complete':100*len(good)/len(eligible) if eligible else 100,
                'local_space_used':sum(p.stat().st_size for p in self.directory.rglob('*') if p.is_file() and not p.is_symlink()),
                'next_action':'verify' if len(good)==len(eligible) else 'resume'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['plan','stage','verify','cutover','cleanup','resume','status'])
    parser.add_argument('--state-root',default=DEFAULT_STATE); parser.add_argument('--generation')
    parser.add_argument('--execute',action='store_true'); parser.add_argument('--limit',type=int)
    parser.add_argument('--rate-limit-s',type=float,default=0); parser.add_argument('--max-transfer-bytes',type=int)
    for flag in ('refresh-catalog','rollback','dedupe-videos','drop-previous-db','force-drop-previous'):
        parser.add_argument('--'+flag,action='store_true')
    parser.add_argument('--previous-days',type=int,default=7)
    args=parser.parse_args(argv); state=Path(args.state_root)
    if args.rate_limit_s<0 or (args.limit is not None and args.limit<0): parser.error('limits must be nonnegative')
    generation=args.generation
    if not generation:
        if args.phase=='plan': generation=datetime.now(timezone.utc).strftime('g%Y%m%d%H%M')
        else:
            candidates=sorted(p.name for p in (state/'rebuild').glob('g*') if p.is_dir())
            if not candidates: parser.error('no generation; run plan')
            generation=candidates[-1]
    orchestrator=Orchestrator(state,generation)
    # Dry runs may write generation-local journals, but no locks outside it.
    lock=exclusive_lock(state) if args.execute else exclusive_lock(orchestrator.directory)
    with lock:
        if args.phase=='plan': result=orchestrator.plan()
        elif args.phase in {'stage','resume'}: result=orchestrator.stage(args.execute,args.limit,args.rate_limit_s,args.max_transfer_bytes,args.refresh_catalog)
        elif args.phase=='verify': result=orchestrator.verify(args.execute)
        elif args.phase=='cutover': result=orchestrator.cutover(args.execute,args.rollback)
        elif args.phase=='cleanup': result=orchestrator.cleanup(args.execute,args.dedupe_videos,args.drop_previous_db,args.force_drop_previous,args.previous_days)
        else: result=orchestrator.status()
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 1 if result.get('pass') is False else 0


if __name__=='__main__':
    raise SystemExit(main())

"""Synthetic safety tests; no network or production state."""
import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[2] / 'ops/study-hub/rebuild_fo_corpus.py'
spec = importlib.util.spec_from_file_location('rebuild', PATH)
m = importlib.util.module_from_spec(spec)


def test_remote_guard():
    spec.loader.exec_module(m)
    for value in ('onedrive:', 'onedrive:Documents/x', 'onedrive:Federal Online/../x'):
        with pytest.raises(ValueError):
            m.guard_remote(value)
    assert m.guard_remote('onedrive:Federal Online PDFs/a.pdf')
    with pytest.raises(ValueError):
        m.Rclone().run('purge', 'onedrive:Federal Online')


def test_quickxor_spec_vector():
    # One byte 0x61 at bit zero; length 1 XORed into byte 12.
    # Real `rclone hashsum quickxor` outputs observed on oracle-vps (rclone v1.73.1).
    assert m.quickxor(b'a') == '6100000000000000000000000100000000000000'
    assert m.quickxor(bytes(range(256))*300) == '000000000000000000000000002c010000000000'
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False) as f: f.write(bytes(range(256))*300)
    try: assert m.file_identity(f.name)['quickxor'] == '000000000000000000000000002c010000000000'
    finally: os.unlink(f.name)


def test_receipts_and_lock(tmp_path):
    with m.exclusive_lock(tmp_path):
        with pytest.raises(RuntimeError):
            with m.exclusive_lock(tmp_path):
                pass
    p = tmp_path / 'receipt.json'
    m.write_checked(p, {'x': 1})
    assert m.read_checked(p)['x'] == 1
    p.write_text('{"x":2,"checksum":"bad"}')
    with pytest.raises(ValueError):
        m.read_checked(p)


def test_local_guard(tmp_path):
    (tmp_path/'materials').mkdir()
    target = tmp_path/'materials/a.pdf'; target.write_bytes(b'a')
    assert m.guard_local(tmp_path,target) == target
    link = tmp_path/'materials/link'; link.symlink_to(target)
    for p in (link, tmp_path/'hub.sqlite3', tmp_path.parent/'outside'):
        with pytest.raises(ValueError):
            m.guard_local(tmp_path,p)

class FakeRclone:
    def __init__(self, root):
        self.root = root; root.mkdir(); self.uploads = 0
    def local(self, remote):
        m.guard_remote(remote)
        return self.root / remote.replace('onedrive:', '')
    def lsjson(self, root):
        base = self.local(root)
        return [{'Path':p.relative_to(base).as_posix(), 'Size':p.stat().st_size,
                 'Hashes':{'quickxor':m.file_identity(p)['quickxor']}, 'ID':str(p)}
                for p in base.rglob('*') if p.is_file()] if base.exists() else []
    def copyto(self, local, remote):
        import shutil
        dst=self.local(remote); dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(local,dst); self.uploads += 1
    def copyto_remote_to_local(self, remote, local):
        import shutil
        shutil.copyfile(self.local(remote),local)
    def deletefile(self, remote): self.local(remote).unlink()


@pytest.fixture
def corpus(tmp_path):
    spec.loader.exec_module(m)
    state=tmp_path/'state'; (state/'materials/course/Biologia').mkdir(parents=True)
    pdf=state/'materials/course/Biologia/a.pdf'; pdf.write_bytes(b'original')
    remote=FakeRclone(tmp_path/'remote')
    def identity(path): return dict(m.file_identity(path),content_sha256='content-a')
    def builder(directory,plan):
        from fo_hub.store import FOStore
        store=FOStore(directory/'hub.sqlite3'); store.conn.close()
    o=m.Orchestrator(state,'gtest',rclone=remote,unit_check=lambda:[],identity=identity,builder=builder)
    return o,pdf,remote


def test_dry_run_does_not_upload_or_delete(corpus):
    o,pdf,remote=corpus; o.plan()
    before=pdf.read_bytes()
    assert o.stage()['dry_run']
    assert o.cleanup()['dry_run']
    assert o.cutover()['dry_run']
    assert remote.uploads==0 and pdf.read_bytes()==before
    assert not (o.directory/'hub.sqlite3').exists()


def test_upload_resume_corruption_and_remote_change(corpus):
    o,pdf,remote=corpus; plan=o.plan()
    assert o.stage(True)['complete']
    assert remote.uploads==1
    assert o.stage(True)['complete']; assert remote.uploads==1
    action=next(a for a in plan['actions'] if a['action']=='upload_missing_original')
    o.receipt_path(action['key']).write_text('{}')
    assert o.stage(True)['complete']
    assert m.read_checked(o.receipt_path(action['key']))['quickxor']==action['quickxor']
    remote.local(action['remote']).write_bytes(b'changed')
    with pytest.raises(RuntimeError): o.stage(True)


def prepare_cutover(o):
    from fo_hub.store import FOStore
    active=FOStore(o.state/'hub.sqlite3'); active.conn.close()
    o.plan(); o.stage(True)
    assert o.verify(True)['pass']


def test_cutover_idempotence_crash_and_rollback(corpus):
    o,pdf,remote=corpus; prepare_cutover(o)
    def crash(step):
        if step=='old_moved': raise RuntimeError('synthetic crash')
    with pytest.raises(RuntimeError): o.cutover(True,crash_hook=crash)
    assert not (o.state/'hub.sqlite3').exists()
    assert o.cutover(True)['active']=='gtest'
    assert o.cutover(True)['already_active']
    assert o.cutover(True,rollback=True)['rolled_back']
    assert (o.state/'hub.sqlite3').exists()


def test_cutover_plan_mismatch(corpus):
    o,pdf,remote=corpus; prepare_cutover(o)
    plan=o.load_plan(); plan['extra']='modified'; m.write_checked(o.directory/'plan.json',plan)
    with pytest.raises(RuntimeError): o.cutover(True)


def test_cleanup_protects_unique_and_changed_remote(corpus):
    o,pdf,remote=corpus; prepare_cutover(o); o.cutover(True)
    o.cleanup(True); assert pdf.exists()
    # A second plan sees a registered original, no longer a unique-only local.
    o2=m.Orchestrator(o.state,'gsecond',rclone=remote,unit_check=lambda:[],identity=o.identity,builder=o.builder)
    o2.plan(); o2.stage(True); assert o2.verify(True)['pass']; o2.cutover(True)
    action=next(a for a in o2.load_plan()['actions'] if a['action']=='drop_local_copy')
    remote.local(action['remote']).write_bytes(b'changed')
    o2.cleanup(True); assert pdf.exists()


def test_verify_lost_lessons_and_collision(corpus):
    o,pdf,remote=corpus
    from fo_hub.store import FOStore
    store=FOStore(o.state/'hub.sqlite3')
    store.sync_lessons([{'course_id':'c','media_id':'x','title':'lesson'}]); store.conn.close()
    o.plan(); o.stage(True)
    result=o.verify(True)
    assert not result['pass'] and any('lost lessons' in x for x in result['divergences'])
    import sqlite3
    with sqlite3.connect(o.directory/'hub.sqlite3') as c:
        c.execute('DROP TABLE materials')
        c.execute('CREATE TABLE materials(material_id TEXT, content_sha256 TEXT)')
        c.executemany('INSERT INTO materials VALUES(?,?)',[('same','a'),('same','b')])
    assert any('collision' in x for x in o.verify(True)['divergences'])


def test_cleanup_retires_only_old_generations(corpus):
    o,pdf,remote=corpus; prepare_cutover(o); o.cutover(True)
    stale=o.state/'rebuild/gold'; stale.mkdir(); (stale/'note').write_text('old')
    import os, time
    os.utime(stale,(time.time()-90000,time.time()-90000))
    o.cleanup(True)
    assert not stale.exists()
    assert o.directory.exists()


def test_dedupe_refuses_registered_source(corpus):
    o,pdf,remote=corpus
    video=o.state/'video'; video.write_bytes(b'video')
    remote.copyto(video,'onedrive:Federal Online/c/a.mp4')
    remote.copyto(video,'onedrive:Federal Online/c/b.mp4')
    prepare_cutover(o); o.cutover(True)
    import sqlite3
    with sqlite3.connect(o.state/'hub.sqlite3') as c:
        c.execute('CREATE TABLE lesson_video_sources(lesson_id TEXT,remote_path TEXT)')
        c.execute('INSERT INTO lesson_video_sources VALUES(?,?)',('l','onedrive:Federal Online/c/b.mp4'))
    with pytest.raises(RuntimeError,match='referenced'):
        o.cleanup(True,dedupe_videos=True)
    assert remote.local('onedrive:Federal Online/c/b.mp4').exists()


def test_active_units_block_mutation(corpus):
    o,pdf,remote=corpus; o.plan(); o.unit_check=lambda:['active']
    with pytest.raises(RuntimeError): o.stage(True)
    assert remote.uploads==0


def test_default_builder_dedupes_watermarked_copies_into_one_material(tmp_path):
    spec.loader.exec_module(m)
    import json, sqlite3
    from test_pdf_identity import _pdf
    state = tmp_path / 'state'
    root = state / 'materials/curso-a'
    (root / 'Biologia').mkdir(parents=True)
    (state / 'materials/curso-b/Biologia').mkdir(parents=True)
    (root / 'Biologia/a.pdf').write_bytes(_pdf(b'Mitose e meiose celular', b'Fake Person 1'))
    (state / 'materials/curso-b/Biologia/a.pdf').write_bytes(_pdf(b'Mitose e meiose celular', b'Fake Person 22'))
    for course in ('curso-a', 'curso-b'):
        (state / 'materials' / course / 'manifest.json').write_text(json.dumps({'items': [
            {'status': 'ok', 'relative_path': 'Biologia/a.pdf', 'file_name': 'a.pdf',
             'portal_subject': 'Biologia I', 'group': 'Resumos', 'material_type': 'resumo'}]}))
    remote = FakeRclone(tmp_path / 'remote')
    o = m.Orchestrator(state, 'gbuild', rclone=remote, unit_check=lambda: [])
    plan = o.plan()
    assert plan['counts']['distinct_pdf_bytes'] == 2 and plan['counts']['distinct_pdf_content'] == 1
    assert o.stage(True)['complete']
    db = o.directory / 'hub.sqlite3'
    with sqlite3.connect(db) as c:
        mats = c.execute('SELECT material_id, subject, sha256 FROM materials').fetchall()
        originals = c.execute('SELECT count(*) FROM material_originals').fetchone()[0]
        text = c.execute('SELECT text FROM pdf_pages ORDER BY page').fetchall()
    assert len(mats) == 1 and mats[0][1] == 'Biologia'
    assert originals == 2
    assert 'Mitose' in text[0][0] and 'Fake' not in ''.join(t[0] for t in text)
    assert o.verify(True)['pass'], o.verify(True)


def test_recutover_after_rollback_does_not_mark_old_db(corpus):
    import hashlib
    o,pdf,remote=corpus; prepare_cutover(o); o.cutover(True)
    o.cutover(True,rollback=True)
    old=hashlib.sha256((o.state/'hub.sqlite3').read_bytes()).hexdigest()
    with pytest.raises(RuntimeError):
        o.cutover(True)
    marker=m.read_checked(o.state/'rebuild/active-generation.json')
    assert marker.get('generation')!=o.generation
    assert hashlib.sha256((o.state/'hub.sqlite3').read_bytes()).hexdigest()==old


def test_resumed_cutover_rechecks_new_db_hash(corpus):
    o,pdf,remote=corpus; prepare_cutover(o)
    def crash(step):
        if step=='old_moved': raise RuntimeError('synthetic crash')
    with pytest.raises(RuntimeError): o.cutover(True,crash_hook=crash)
    import sqlite3
    with sqlite3.connect(o.directory/'hub.sqlite3') as c: c.execute('CREATE TABLE tampered(x)')
    with pytest.raises(RuntimeError, match='verified DB changed'): o.cutover(True)
    assert (o.directory/'previous-hub.sqlite3').exists() or (o.state/'hub.sqlite3').exists()
    assert not (o.state/'rebuild/active-generation.json').exists() or \
        m.read_checked(o.state/'rebuild/active-generation.json').get('generation')!=o.generation


def test_rclone_copyto_is_immutable():
    spec.loader.exec_module(m)
    calls=[]
    r=m.Rclone(); r.run=lambda *a: calls.append(a)
    r.copyto('/tmp/x','onedrive:Federal Online PDFs/a.pdf')
    assert '--immutable' in calls[0]


def test_cleanup_lists_remote_once_per_run(corpus):
    o,pdf,remote=corpus; prepare_cutover(o); o.cutover(True)
    o2=m.Orchestrator(o.state,'gsecond',rclone=remote,unit_check=lambda:[],identity=o.identity,builder=o.builder)
    o2.plan(); o2.stage(True); assert o2.verify(True)['pass']; o2.cutover(True)
    n=[0]; orig=remote.lsjson
    def counted(root): n[0]+=1; return orig(root)
    remote.lsjson=counted
    o2.cleanup(True)
    assert not pdf.exists()
    assert n[0] <= 4


def test_plan_ignores_staging_build_trees(corpus):
    o,pdf,remote=corpus
    staging=o.state/'materials/.build_course/Biologia'; staging.mkdir(parents=True)
    (staging/'b.pdf').write_bytes(b'staging')
    plan=o.plan()
    assert not any('/.build_' in a.get('local','') for a in plan['actions'])

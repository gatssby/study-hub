import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fo_hub.store import FOStore,lesson_id_for


def test_partial_sync_and_empty_failure_do_not_hide_existing_lessons(tmp_path):
    store=FOStore(tmp_path/'test.db')
    rows=[{'course_id':'2027','media_id':str(i),'title':f'lesson{i}','video_url':'https://cdn/a?token=1'} for i in range(2)]
    store.sync_lessons(rows)
    store.sync_lessons([rows[0]])
    store.sync_lessons([])
    assert len(store.list_lessons())==2


def test_signature_rotation_is_not_media_change(tmp_path):
    store=FOStore(tmp_path/'test.db')
    row={'course_id':'2027','media_id':'1','title':'Lesson','video_url':'https://cdn/a?token=1'}
    store.sync_lessons([row]);store.sync_lessons([dict(row,video_url='https://cdn/a?token=2')])
    assert store.get_lesson(lesson_id_for('2027','1',None))['version']==1


def test_sources_include_version_and_update_dates(tmp_path):
    store=FOStore(tmp_path/'test.db')
    store.sync_lessons([{'course_id':'2027','media_id':'1','title':'Lesson'}])
    lesson=store.list_lessons()[0]
    assert lesson['citation']['version']==1
    assert lesson['citation']['updated_at']
    store.upsert_material({'material_id':'pdf1','title':'Resumo','sha256':'contenthash','relative_path':'materials/resumo.pdf'})
    store.set_pdf_pages('pdf1',['Texto'])
    result=store.get_pdf_text('pdf1')
    assert result['version']=='contenthash'
    assert result['updated_at']

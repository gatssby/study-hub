"""Synthetic portal contracts; no login, downloads or ASR."""
import importlib.util
import sys
from pathlib import Path

PORTAL = Path(__file__).resolve().parents[1] / 'portal'
sys.path.insert(0, str(PORTAL))


def load(name):
    spec = importlib.util.spec_from_file_location(name, PORTAL / f'{name}.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_unknown_categories_are_traversable_not_allowlisted():
    collector = load('fo_collect_aulas_index')
    assert collector.is_academic_source_ref('Curso 2027 > Categoria inédita > Biologia')
    assert collector.is_not_launched_placeholder('Obras > Nova frente', {'title': 'Aula 04 em breve'})
    assert collector.is_operational_item({'title': 'Como enviar redacoes'})


def test_invalid_video_manifest_never_creates_backup(tmp_path):
    import pytest
    video = load('fo_download_upload_videos')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{broken')
    with pytest.raises(RuntimeError):
        video.load_manifest(manifest)
    assert list(tmp_path.iterdir()) == [manifest]
    assert manifest.read_text() == '{broken'


def test_course_discovery_accepts_new_year_and_rejects_external_or_admin():
    discovery = load('discovery')
    links = [
        {'href': '/portal/curso-aula/produto-pacote/abc/curso-2027', 'text': 'Curso 2027'},
        {'href': 'https://evil.example/portal/curso-aula/a', 'text': 'bad'},
        {'href': '/portal/financeiro', 'text': 'Faturas'},
        {'href': '/portal/curso-aula/produto-pacote/abc/curso-2027?tracking=1', 'text': 'duplicate'},
    ]
    courses = discovery.course_links(links)
    assert courses == [{'url': 'https://www.federalonline.com.br/portal/curso-aula/produto-pacote/abc/curso-2027', 'title': 'Curso 2027'}]


def test_merge_materials_does_not_remove_missing_originals(tmp_path):
    discovery = load('discovery')
    final = tmp_path / 'materials'
    final.mkdir()
    (final / 'old.pdf').write_bytes(b'%PDF-original')
    build = tmp_path / 'build'
    build.mkdir()
    (build / 'new.pdf').write_bytes(b'%PDF-new')
    discovery.merge_materials(build, final)
    assert (final / 'old.pdf').exists()
    assert (final / 'new.pdf').exists()
    assert not build.exists()


def test_product_hierarchy_navigation_is_discovered_not_hardcoded():
    discovery=load('discovery')
    links=[{'href':'/portal/cursos'},{'href':'/portal/curso/produto/new-id/2027'},{'href':'/portal/financeiro'},{'href':'https://evil.example/portal/curso/produto/a'}]
    assert discovery.catalog_navigation_links(links)==[
        'https://www.federalonline.com.br/portal/cursos',
        'https://www.federalonline.com.br/portal/curso/produto/new-id/2027']

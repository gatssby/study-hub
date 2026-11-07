from types import SimpleNamespace

from fo_hub.materials_cycle import Rotation, collect_one


def test_collector_uses_dynamic_options_not_fixed_filters(tmp_path, monkeypatch):
    import sys
    events = []
    options = [{'value': 'dynamic', 'label': 'Dynamic', 'disciplines': [{'value': 's', 'label': 'Subject'}]}]
    row = SimpleNamespace(title_text='New', subject_text='Subject', material_type='PDF', raw_date='')
    class Session:
        def __init__(self, *args):
            self.context = self.mat_config = self.logger = None
        def discover_material_options(self):
            events.append('discover')
            return options
        def _save_session(self): pass
        def close(self): events.append('close')
    def download(*args):
        args[-1].write_bytes(b'%PDF-synthetic')
        return 'synthetic-source'
    monkeypatch.setitem(sys.modules, 'runtime', SimpleNamespace(BrowserSession=Session, Paths=lambda x: x))
    monkeypatch.setitem(sys.modules, 'fo_sync_materials_from_portal_materiais', SimpleNamespace(
        open_authenticated_materials_page=lambda *a: SimpleNamespace(close=lambda: None),
        apply_filters_for_subject=lambda *a: events.append(a[-3:]),
        collect_material_rows=lambda *a, **kw: [row], download_material_row=download,
        filename_for_row=lambda *a: 'New.pdf'))
    rotation = Rotation(tmp_path / 'cursor.json')
    args = SimpleNamespace(state=tmp_path, env_file=tmp_path / 'env')
    items = collect_one(args, tmp_path, rotation=rotation)
    assert events == ['discover', ('Subject', 'dynamic', 'Dynamic'), 'close']
    assert items[0]['observation_id'] == rotation.row_id
    assert items[0]['course_value'] == 'dynamic'
    assert not rotation.path.exists()


def test_periodic_observer_can_include_pdf_slides():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))
    import fo_sync_materials_from_portal_materiais as mat
    raw = [{'position': 0, 'row_id': 'ephemeral', 'title_text': 'Slides.pdf',
            'subject_text': 'Subject', 'row_text': 'Slides.pdf Subject'}]
    page = SimpleNamespace(evaluate=lambda *a: raw)
    logger = SimpleNamespace(log=lambda *a: None)
    assert mat.collect_material_rows(page, logger, 'Subject') == []
    assert len(mat.collect_material_rows(page, logger, 'Subject', include_slides=True)) == 1


def test_main_defaults_to_rotation_without_fixed_filters(tmp_path, monkeypatch):
    import sys
    from fo_hub import materials_cycle
    seen = []
    def cycle(state, producer, **kwargs):
        seen.append(callable(kwargs['on_success']))
        return {'files': 0}
    monkeypatch.setattr(materials_cycle, 'run_cycle', cycle)
    monkeypatch.setattr(sys, 'argv', ['materials-cycle', '--state', str(tmp_path),
                                    '--env-file', str(tmp_path / 'env'), '--upload'])
    materials_cycle.main()
    assert seen == [True]


def test_rotation_visits_all_branches_rows_and_rediscovers(tmp_path):
    options = [{'value': 'a', 'label': 'A', 'disciplines': [{'value': 'x', 'label': 'X'}]},
               {'value': 'b', 'label': 'B', 'disciplines': [{'value': 'y', 'label': 'Y'}]}]
    def row(title):
        return SimpleNamespace(title_text=title, subject_text='Subject', material_type='PDF', raw_date='')
    rows = [row('one'), row('two')]
    path = tmp_path / 'rotation.json'
    seen = []
    for _ in range(4):
        rotation = Rotation(path)
        branch = rotation.branch(options)
        selected = rotation.row(rows)
        seen.append((branch['course_value'], selected.title_text))
        rotation.commit([{'sha256': 'a' * 64}])
    assert set(seen) == {('a', 'one'), ('a', 'two'), ('b', 'one'), ('b', 'two')}
    rotation = Rotation(path)
    options.append({'value': 'c', 'label': 'C', 'disciplines': [{'value': 'z', 'label': 'Z'}]})
    assert rotation.branch(options)['course_value'] == 'c'
    # An uncommitted selection never advances the durable cursor.
    assert Rotation(path).branch(options)['course_value'] == 'c'


def test_rotation_new_rows_and_byte_revisions_are_retained(tmp_path):
    import json
    options = [{'value': 'a', 'label': 'A', 'disciplines': [{'value': 'x', 'label': 'X'}]}]
    one = SimpleNamespace(title_text='one', subject_text='X', material_type='PDF', raw_date='')
    two = SimpleNamespace(title_text='two', subject_text='X', material_type='PDF', raw_date='')
    path = tmp_path / 'rotation.json'
    for rows, expected, digest in [([one], one, 'a'), ([one], one, 'b'), ([one, two], two, 'c')]:
        rotation = Rotation(path)
        rotation.branch(options)
        assert rotation.row(rows) is expected
        rotation.source_url = 'observed-source'
        rotation.commit([{'sha256': digest * 64}])
    checkpoint = json.loads(path.read_text())
    assert sorted(len(v['hashes']) for v in checkpoint['rows'].values()) == [1, 2]
    assert all(v['title'] in ('one', 'two') for v in checkpoint['rows'].values())
    assert all(version['source_url'] == 'observed-source'
               for v in checkpoint['rows'].values() for version in v['versions'].values())

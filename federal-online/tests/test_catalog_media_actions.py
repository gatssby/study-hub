"""Regression: seen checkbox must never hide a sibling openMedia4 action."""
import json
import shutil
import subprocess
import pytest
from test_catalog_partial import collector


@pytest.mark.parametrize('root_onclick', ['', 'markSeen(event)'])
def test_extract_item_prefers_the_media_action_over_seen_checkbox(root_onclick):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required to exercise the actual embedded JS')
    assert node is not None
    class Item:
        def evaluate(self, source):
            script = '''const media={getAttribute:()=>"openMedia4(event, 'item-stable', 'Resolução em vídeo', 'V')",querySelector:()=>null};
const seen={getAttribute:()=>"markSeen(event)",querySelector:()=>null};
const el={innerText:'Resolução em vídeo',matches:s=>s==='[onclick]' && ROOT!=='',getAttribute:()=>ROOT,
querySelector:s=>s==='[onclick]'?seen:s.includes('openMedia4')?media:null,querySelectorAll:()=>[]};
console.log(JSON.stringify((SOURCE)(el)));'''.replace('ROOT', json.dumps(root_onclick)).replace('SOURCE', source)
            return json.loads(subprocess.check_output([node, '-e', script], text=True))
    info = collector.extract_item_info(Item())
    assert info['itemId'] == 'item-stable'
    assert info['mediaType'] == 'V'
    assert info['onclick'].startswith('openMedia4(')


def test_empty_inventory_requires_classified_nonvideo_items(monkeypatch):
    class Items:
        def __init__(self, rows): self.rows = rows
        def count(self): return len(self.rows)
        def nth(self, idx): return self.rows[idx]
    class Root:
        def __init__(self, rows): self.rows = rows
        def locator(self, selector): return Items(self.rows)
    monkeypatch.setattr(collector, 'extract_item_info', lambda row: row)
    proof = collector.empty_catalog_evidence(Root([{'itemId':'one','mediaType':'D'}, {'itemId':'two','mediaType':'U'}]))
    assert proof['verified_no_native_video'] is True
    assert proof['media_type_counts'] == {'D':1,'U':1}
    for rows in [[], [{'itemId':'one','mediaType':None}], [{'itemId':'one','mediaType':'V'}]]:
        assert collector.empty_catalog_evidence(Root(rows))['verified_no_native_video'] is False

import importlib.util
from pathlib import Path


def test_rendered_units_allow_private_rclone_refresh_without_auto_asr(tmp_path):
    source=Path(__file__).resolve().parents[2]/'ops/study-hub/render_units.py'
    spec=importlib.util.spec_from_file_location('render_fo_units',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.render(tmp_path)
    timers=list(tmp_path.glob('*.timer'))
    assert len(timers)==6
    assert not any('transcription' in p.name for p in timers)
    for name in ['onedrive','materials','videos','transcription']:
        text=(tmp_path/f'study-hub-fo-{name}.service').read_text()
        assert '/home/ubuntu/.config/rclone' in next(x for x in text.splitlines() if x.startswith('ReadWritePaths='))
    asr=(tmp_path/'study-hub-fo-transcription.service').read_text()
    assert 'ConditionPathExists=/etc/study-hub/fo-transcription.authorized' in asr
    assert 'RestartPreventExitStatus=3' in asr
    assert 'Restart=on-failure' in (tmp_path/'study-hub-fo-materials.service').read_text()
    assert 'RestartPreventExitStatus=2' in (tmp_path/'study-hub-fo-catalog.service').read_text()
    ocr=(tmp_path/'study-hub-fo-ocr.service').read_text()
    assert '/locks/index.lock' in ocr
    assert 'CPUQuota=25%' in ocr
    assert 'MemoryMax=512M' in ocr
    assert 'TimeoutStartSec=5min' in ocr
    assert 'SuccessExitStatus=75' in ocr

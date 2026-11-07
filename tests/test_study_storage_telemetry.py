import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('storage_telemetry', Path(__file__).parents[1] / 'ops/study-hub/storage_telemetry.py')
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_growth_requires_six_hours_of_observations():
    assert module.growth_per_day([{'observed_at': 0, 'study_hub_bytes': 100}, {'observed_at': 100, 'study_hub_bytes': 200}]) is None
    assert module.growth_per_day([{'observed_at': 0, 'study_hub_bytes': 100}, {'observed_at': 86400, 'study_hub_bytes': 300}]) == 200


def test_alerts_use_whisper_reserve_not_disk_percentage():
    assert module.storage_warning(1000, 100, None) is None
    assert module.storage_warning(99, 100, None) == 'low_reserve'
    assert module.storage_warning(1000, 100, 200) == 'growth_risk'
    assert module.storage_warning(1000, 100, -200) is None


def test_inventory_does_not_follow_symlinks_or_count_hardlinks_twice(tmp_path):
    import os
    (tmp_path / 'tmp').mkdir()
    payload = tmp_path / 'tmp' / 'payload'
    payload.write_bytes(b'abc')
    os.link(payload, tmp_path / 'duplicate')
    (tmp_path / 'outside').symlink_to('/etc')
    total, temporary = module.inventory_bytes(tmp_path)
    assert total == 3
    assert temporary == 3


def test_publish_retains_bounded_history_and_no_private_paths(tmp_path):
    state = tmp_path / 'state'
    (state / 'tmp').mkdir(parents=True)
    (state / 'tmp' / 'x').write_bytes(b'abc')
    result = module.sample(state, now=1000, available_bytes=10**12, largest_source_bytes=100)
    assert result['study_hub_bytes'] == 3
    assert result['temp_bytes'] == 3
    assert result['whisper_reserve_bytes'] == 4 * 1024**3 + 100 * 1024**2 + 100
    assert result['growth_bytes_per_day'] is None
    assert 'state' not in result
    assert (state / 'telemetry/storage.json').exists()

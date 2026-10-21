#!/usr/bin/env python3
"""Run ONLY on the VPS. Inventory metadata, never copy old transcript text."""
from pathlib import Path
import collections
import json
import os
import sqlite3
import subprocess

STATE = Path('/home/ubuntu/study-hub-state/federal-online')
OLD_QUEUE = Path('/home/ubuntu/fo-transcricoes-system/queue.sqlite')


def main():
    if not Path('/home/ubuntu/anki-vnext').is_dir():
        raise SystemExit('VPS guard failed')
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    result = subprocess.run(['rclone', 'lsjson', 'onedrive:Federal Online', '--recursive', '--files-only'], check=True, text=True, capture_output=True, timeout=240)
    files = json.loads(result.stdout)
    videos = [x for x in files if Path(x['Path']).suffix.lower() in ('.mp4', '.mkv', '.webm', '.mov', '.m4v')]
    inventory = [{k: x.get(k) for k in ('Path', 'Size', 'ModTime', 'ID', 'Hashes')} for x in videos]
    path = STATE / 'remote-videos.json'
    path.write_text(json.dumps(inventory, ensure_ascii=False))
    os.chmod(path, 0o600)
    names = {x['Path'] for x in videos}
    seed = []
    if OLD_QUEUE.exists():
        db = sqlite3.connect(f'file:{OLD_QUEUE}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        columns = {r['name'] for r in db.execute('pragma table_info(transcription_queue)')}
        allowed = [x for x in ('remote_path', 'video_name', 'tipo', 'materia', 'frente', 'aula_number', 'aula_title', 'output_relative_path', 'duration_seconds') if x in columns]
        for row in db.execute('select ' + ','.join(allowed) + ' from transcription_queue'):
            item = dict(row)
            item['source_available'] = item['remote_path'] in names
            seed.append(item)
        db.close()
    path = STATE / 'video-lesson-map.json'
    path.write_text(json.dumps(seed, ensure_ascii=False))
    os.chmod(path, 0o600)
    summary = {'remote_videos': len(videos), 'remote_bytes': sum(x['Size'] for x in videos), 'legacy_lesson_links': len(seed), 'links_source_verified': sum(x['source_available'] for x in seed), 'links_source_missing': sum(not x['source_available'] for x in seed), 'remote_other_file_extensions': dict(collections.Counter(Path(x['Path']).suffix.lower() for x in files if x not in videos)), 'disk_free_bytes_before_cleanup': __import__('shutil').disk_usage(STATE).free}
    (STATE / 'migration-inventory.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()

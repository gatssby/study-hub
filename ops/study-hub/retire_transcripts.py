#!/usr/bin/env python3
"""One-time classified cutover. No backups, no ASR, no broad shared-path removal."""
from pathlib import Path
import json
import os
import shutil
import subprocess

HOME = Path('/home/ubuntu')
STATE = HOME / 'study-hub-state/federal-online'
LIVE = HOME / 'study-hub'
OLD = HOME / 'anki-gpt-sync'
CRONOGRAMA = Path('/opt/cronograma-fo')


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True)


def move(source, destination):
    if not source.exists():
        return
    if destination.exists():
        raise RuntimeError(f'Destination already exists: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def main():
    evidence = json.loads((STATE / 'migration-inventory.json').read_text())
    if evidence['links_source_missing'] or evidence['links_source_verified'] != evidence['legacy_lesson_links']:
        raise SystemExit('Video source verification incomplete')
    for name in ('sync', 'api', 'mcp', 'mcp-tunnel'):
        run('systemctl', 'is-active', '--quiet', f'anki-vnext-{name}.service')
    # Remove only known exclusive legacy cron consumers, preserving every other line.
    cron = run('crontab', '-l').stdout.splitlines()
    markers = ('/home/ubuntu/anki-gpt-sync/scripts/watchdog_query_api.sh', '/opt/cronograma-fo/scripts/run_fo_full_sync.sh', '/home/ubuntu/fo-transcricoes-system/logs')
    kept = [line for line in cron if not any(marker in line for marker in markers)]
    subprocess.run(['crontab', '-'], input='\n'.join(kept) + '\n', check=True, text=True)
    check = run('crontab', '-l').stdout
    assert not any(marker in check for marker in markers)
    # Stop the two consumers of old transcript text and queue.
    run('sudo', 'systemctl', 'disable', '--now', 'fo-vps-worker.service', 'fo-queue-api.service')
    sessions = subprocess.run(['tmux', 'list-sessions', '-F', '#S'], text=True, capture_output=True)
    if 'anki-query-api' in sessions.stdout.splitlines():
        run('tmux', 'kill-session', '-t', 'anki-query-api')
    legacy_site = Path('/etc/nginx/sites-enabled/gatsby-anki')
    if legacy_site.is_symlink():
        run('sudo', 'unlink', str(legacy_site))
        run('sudo', 'nginx', '-t')
        run('sudo', 'systemctl', 'reload', 'nginx')
    # Move active FO originals/state, not historical copies.
    move(OLD / 'state/federal_online/materiais_fo', STATE / 'materials')
    move(OLD / 'state/federal_online/storage_state.json', STATE / 'storage_state.json')
    move(OLD / 'knowledge', LIVE / 'anki-knowledge')
    move(HOME / '.config/anki-gpt-sync/federal_online.env', HOME / '.config/study-hub/federal_online.env')
    catalog = CRONOGRAMA / 'state/federal_online/cronograma_fo'
    for name in ('aulas_index.json', 'aulas_index.tsv', 'aulas_index.filtered_aulas_gerais.json', 'video_upload_manifest.json', 'checkpoint.json'):
        move(catalog / name, STATE / 'catalog' / name)
    # Source PDFs and source/navigation work may include non-Cronograma originals.
    for source in CRONOGRAMA.glob('*.pdf'):
        move(source, STATE / 'materials-sources' / source.name)
    move(CRONOGRAMA / 'work', STATE / 'portal-source-metadata')
    # The two storage files may correspond to different portal sessions: preserve both.
    move(CRONOGRAMA / 'state/federal_online/storage_state.json', STATE / 'catalog-storage_state.json')
    # Delete only the old text corpus and exclusively derived search index.
    texts = HOME / 'fo-transcricoes'
    files = [p for p in texts.rglob('*') if p.is_file()]
    unexpected = [p for p in files if p.suffix != '.md' and not p.name.endswith('.bak-before-cleaning')]
    if unexpected:
        raise RuntimeError(f'Unclassified corpus files: {len(unexpected)}')
    counts = {'old_markdown_deleted': sum(p.suffix == '.md' for p in files), 'old_cleaning_copies_deleted': sum(p.name.endswith('.bak-before-cleaning') for p in files), 'legacy_cron_lines_removed': len(cron)-len(kept)}
    shutil.rmtree(texts)
    index = OLD / 'state/federal_online/fo_transcripts_fts.sqlite'
    for path in [index, Path(str(index)+'-wal'), Path(str(index)+'-shm')]:
        if path.exists(): path.unlink()
    for unit in ('fo-vps-worker.service', 'fo-queue-api.service'):
        unit_path = Path('/etc/systemd/system') / unit
        if unit_path.exists(): run('sudo', 'unlink', str(unit_path))
        run('sudo', 'systemctl', 'mask', unit)
    run('sudo', 'systemctl', 'daemon-reload')
    # No model runtime from the prior ASR system is needed for the new benchmark.
    shutil.rmtree(HOME / 'fo-transcricoes-system')
    counts['disk_free_bytes_after_transcript_retirement'] = shutil.disk_usage(STATE).free
    counts['TRANSCRIPTION_ENABLED'] = False
    (STATE / 'retirement-transcripts.json').write_text(json.dumps(counts, indent=2))
    print(json.dumps(counts))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Remove classified app runtimes, preserving unmatched media in-place as blocked."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HOME = Path('/home/ubuntu')
OLD = HOME / 'anki-gpt-sync'
STATE = HOME / 'study-hub-state/federal-online'


def delete(path):
    if path.is_symlink() or path.is_file(): path.unlink()
    elif path.is_dir(): shutil.rmtree(path)


def main():
    assert json.loads((STATE/'retirement-transcripts.json').read_text())['old_markdown_deleted'] == 1018
    for name in ('sync', 'api', 'mcp', 'mcp-tunnel'):
        subprocess.run(['systemctl','is-active','--quiet',f'anki-vnext-{name}'],check=True)
    assert (STATE/'materials').is_dir()
    assert (HOME/'study-hub/anki-knowledge').is_dir()
    assert (HOME/'.config/study-hub/federal_online.env').is_file()
    # Preserve unknown media, not a copy/quarantine. Remove exact verified duplicates only.
    media=OLD/'state/media'
    targets=[HOME/'anki-vnext/service/collection.media',HOME/'anki-vnext/sync-data/leonardo/media']
    preserved=removed=0
    if media.is_dir():
        for path in media.iterdir():
            if not path.is_file():
                preserved+=1
                continue
            digest=hashlib.sha256(path.read_bytes()).digest()
            same=any((root/path.name).is_file() and hashlib.sha256((root/path.name).read_bytes()).digest()==digest for root in targets)
            if same: path.unlink(); removed+=1
            else: preserved+=1
    for path in OLD.iterdir():
        if path.name=='state':
            for child in path.iterdir():
                if child.name!='media':delete(child)
        else: delete(path)
    # All source PDFs and portal navigation data have already been moved out.
    cron=Path('/opt/cronograma-fo')
    forbidden=[p for p in cron.rglob('*') if p.is_file() and p.suffix.lower() in ('.pdf','.mp4','.mkv','.anki2','.anki21')]
    if forbidden:raise RuntimeError(f'Protected files remain in Cronograma: {len(forbidden)}')
    names=subprocess.run(['docker','ps','-a','--format','{{.Names}}'],check=True,text=True,capture_output=True).stdout.splitlines()
    if 'cronograma-fo' in names:
        subprocess.run(['docker','stop','cronograma-fo'],check=True,capture_output=True)
        subprocess.run(['docker','rm','cronograma-fo'],check=True,capture_output=True)
    delete(cron)
    # Image belongs exclusively to the removed container. No shared docker prune.
    subprocess.run(['docker','image','rm','cronograma-fo-cronograma-fo'],text=True,capture_output=True)
    site=Path('/etc/nginx/sites-available/gatsby-anki')
    if site.exists():subprocess.run(['sudo','unlink',str(site)],check=True)
    result={'legacy_backend_removed':True,'cronograma_root_exists':cron.exists(),'verified_cached_media_duplicates_removed':removed,'unresolved_media_preserved_in_place':preserved,'disk_free_bytes_after_apps_retirement':shutil.disk_usage(STATE).free}
    (STATE/'retirement-apps.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()

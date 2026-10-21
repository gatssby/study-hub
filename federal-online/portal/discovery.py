"""Structural portal discovery, never a fixed course/category allowlist."""
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
import os
import shutil

ORIGIN = 'https://www.federalonline.com.br'


def catalog_navigation_links(links):
    found=[]
    for link in links:
        parts=urlsplit(urljoin(ORIGIN,link.get('href','')))
        if parts.hostname not in ('www.federalonline.com.br','federalonline.com.br'):continue
        if parts.path.rstrip('/')!='/portal/cursos' and not parts.path.startswith('/portal/curso/'):continue
        url=urlunsplit(('https','www.federalonline.com.br',parts.path.rstrip('/'),'',''))
        if url not in found:found.append(url)
    return found


def course_links(links):
    found = {}
    for link in links:
        parts = urlsplit(urljoin(ORIGIN, link.get('href', '')))
        if parts.hostname not in ('www.federalonline.com.br', 'federalonline.com.br'):
            continue
        if not parts.path.startswith('/portal/curso-aula/'):
            continue
        url = urlunsplit(('https', 'www.federalonline.com.br', parts.path.rstrip('/'), '', ''))
        found.setdefault(url, {'url': url, 'title': link.get('text', '').strip()})
    return list(found.values())


def merge_materials(build: Path, final: Path):
    """Promote retrieved files without deleting unseen originals or retaining backups."""
    final.mkdir(parents=True, exist_ok=True)
    for source in build.rglob('*'):
        if source.is_file():
            destination = final / source.relative_to(build)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
    shutil.rmtree(build)

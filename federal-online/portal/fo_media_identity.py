"""Stable portal asset locators, not proof of identical media bytes."""
from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

# Live observations rotated this one UUID prefix for the same DLX asset path.
# Do not generalize UUID removal to other providers, routes or asset IDs.
_DLX_AUTH_PATH = re.compile(
    r'^/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}'
    r'(/dlx/[A-Za-z0-9_-]+/master\.m3u8)$'
)


def canonical_media_url(url: str | None) -> str:
    parsed = urlsplit(url or '')
    path = parsed.path
    if (parsed.scheme == 'https'
            and (parsed.hostname or '').endswith('.map.azionedge.net')):
        match = _DLX_AUTH_PATH.fullmatch(path)
        if match:
            path = match.group(1)
    return urlunsplit((parsed.scheme, parsed.netloc, path, '', ''))

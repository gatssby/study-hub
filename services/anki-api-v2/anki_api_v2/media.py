"""Media file access restricted to the collection's own media directory."""

from __future__ import annotations

import mimetypes
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote

MAX_MEDIA_NAME_CHARS = 255
# Hard ceiling for anything this API serves. The MCP adapter applies a smaller one.
MAX_MEDIA_BYTES = 20 * 1024 * 1024
MAX_MEDIA_REFS = 100
IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
OCTET_STREAM = "application/octet-stream"
# Explicit: mimetypes lacks .webp before Python 3.11 and the VPS runs 3.10.
_EXT_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


class InvalidMediaPath(ValueError):
    """The requested name is not a plain media filename."""


class MediaNotFound(LookupError):
    """No regular file with that name exists in the media directory."""


class MediaTooLarge(ValueError):
    """The file exceeds MAX_MEDIA_BYTES."""


def media_dir_for(collection_path: Path) -> Path:
    # Anki stores media next to the collection as "<stem>.media".
    return collection_path.parent / f"{collection_path.stem}.media"


def validate_media_filename(name: str) -> str:
    if not name or len(name) > MAX_MEDIA_NAME_CHARS:
        raise InvalidMediaPath("empty or too long")
    if name in {".", ".."} or name.startswith("."):
        raise InvalidMediaPath("dot names are not allowed")
    if "/" in name or "\\" in name:
        raise InvalidMediaPath("path separators are not allowed")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise InvalidMediaPath("control characters are not allowed")
    return name


def resolve_media_file(media_dir: Path, name: str) -> Path:
    candidate = media_dir / name
    if candidate.is_symlink():
        raise InvalidMediaPath("symbolic links are not served")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise MediaNotFound(name) from exc
    if resolved.parent != media_dir.resolve():
        raise InvalidMediaPath("resolved path escapes the media directory")
    if not resolved.is_file():
        raise MediaNotFound(name)
    return resolved


def sniff_image_mime(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def mime_from_name(name: str) -> str | None:
    suffix = Path(name).suffix.lower()
    return _EXT_MIME.get(suffix) or mimetypes.guess_type(name)[0]


def describe_media_file(path: Path, name: str) -> tuple[str, int]:
    """(mime, size) of a media file. The MIME comes from the bytes for raster images.

    A `.png` whose bytes are not a PNG is served as octet-stream, never as an image.
    SVG (text) and audio/video keep their extension type; everything else is octet-stream.
    """
    size = path.stat().st_size
    if size > MAX_MEDIA_BYTES:
        raise MediaTooLarge(name)
    with open(path, "rb") as handle:
        sniffed = sniff_image_mime(handle.read(16))
    if sniffed:
        return sniffed, size
    guessed = mime_from_name(name)
    if guessed == "image/svg+xml" or (guessed and guessed.split("/")[0] in {"audio", "video"}):
        return guessed, size
    return OCTET_STREAM, size


_IMG_RE = re.compile(
    r"""<img\b[^>]*?\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))""", re.IGNORECASE | re.DOTALL
)
_SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
_REMOTE_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//)")


def extract_media_refs(
    fields: Sequence[tuple[str, str]], media_dir: Path
) -> list[dict[str, Any]]:
    """Structured references to local media used by a note, in reading order.

    Read-only regex over the field HTML (Anki's own helper renders LaTeX and can write
    files). Remote URLs, data URIs and anything that is not a plain filename are ignored.
    """
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field, value in fields:
        found: list[tuple[int, str, str]] = []
        for match in _IMG_RE.finditer(value):
            raw = next(g for g in match.groups() if g is not None)
            found.append((match.start(), "image", raw))
        for match in _SOUND_RE.finditer(value):
            found.append((match.start(), "sound", match.group(1)))
        for _, kind, raw in sorted(found):
            name = unquote(raw.strip())
            if _REMOTE_RE.match(name):
                continue
            try:
                validate_media_filename(name)
            except InvalidMediaPath:
                continue
            if name in seen:
                continue
            seen.add(name)
            refs.append(_describe_ref(media_dir, name, field, kind))
            if len(refs) >= MAX_MEDIA_REFS:
                return refs
    return refs


def _describe_ref(media_dir: Path, name: str, field: str, kind: str) -> dict[str, Any]:
    mime = mime_from_name(name)
    exists = False
    size: int | None = None
    try:
        path = resolve_media_file(media_dir, name)
        size = path.stat().st_size
        exists = True
        if size <= MAX_MEDIA_BYTES:
            mime = describe_media_file(path, name)[0]
    except (InvalidMediaPath, MediaNotFound, OSError):
        pass
    return {
        "filename": name,
        "field": field,
        "kind": kind,
        "mime_type": mime,
        "exists": exists,
        "size_bytes": size,
        "viewable": mime in IMAGE_MIMES,
    }

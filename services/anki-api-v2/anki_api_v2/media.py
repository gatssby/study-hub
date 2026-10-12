"""Media file access restricted to the collection's own media directory."""

from __future__ import annotations

from pathlib import Path

MAX_MEDIA_NAME_CHARS = 255


class InvalidMediaPath(ValueError):
    """The requested name is not a plain media filename."""


class MediaNotFound(LookupError):
    """No regular file with that name exists in the media directory."""


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

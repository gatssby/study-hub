"""Runtime configuration. Secrets are never printed by repr()."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

MIN_TOKEN_LENGTH = 32
DEFAULT_SYNC_ENDPOINT = "http://127.0.0.1:27701/"
DEFAULT_FRESHNESS_TTL_SECONDS = 30.0
DEFAULT_QUEUE_TIMEOUT_SECONDS = 5.0
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})


class ConfigError(RuntimeError):
    """Configuration is missing or unsafe. The message never contains secret values."""


@dataclass(frozen=True)
class Settings:
    collection_path: Path
    token: str = field(repr=False)
    sync_endpoint: str
    sync_username: str
    sync_password: str = field(repr=False)
    lock_path: Path
    freshness_ttl_seconds: float = DEFAULT_FRESHNESS_TTL_SECONDS
    queue_timeout_seconds: float = DEFAULT_QUEUE_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Settings:
        token = env.get("ANKI_API_TOKEN", "")
        if len(token) < MIN_TOKEN_LENGTH:
            raise ConfigError(f"ANKI_API_TOKEN is missing or shorter than {MIN_TOKEN_LENGTH} chars")

        collection = env.get("ANKI_API_COLLECTION_PATH", "")
        if not collection:
            raise ConfigError("ANKI_API_COLLECTION_PATH is required")
        collection_path = Path(collection)

        creds_file = env.get("ANKI_API_SYNC_CREDENTIALS_FILE", "")
        if not creds_file:
            raise ConfigError("ANKI_API_SYNC_CREDENTIALS_FILE is required")
        username, password = _read_sync_user(Path(creds_file))

        endpoint = env.get("ANKI_API_SYNC_ENDPOINT", DEFAULT_SYNC_ENDPOINT)
        if urlsplit(endpoint).hostname not in LOOPBACK_HOSTS:
            raise ConfigError("ANKI_API_SYNC_ENDPOINT must point at a loopback host")

        lock_raw = env.get("ANKI_API_LOCK_PATH", "")
        lock_path = Path(lock_raw) if lock_raw else collection_path.parent / "collection.lock"

        return cls(
            collection_path=collection_path,
            token=token,
            sync_endpoint=endpoint,
            sync_username=username,
            sync_password=password,
            lock_path=lock_path,
            freshness_ttl_seconds=_float(
                env, "ANKI_API_FRESHNESS_TTL_SECONDS", DEFAULT_FRESHNESS_TTL_SECONDS
            ),
            queue_timeout_seconds=_float(
                env, "ANKI_API_QUEUE_TIMEOUT_SECONDS", DEFAULT_QUEUE_TIMEOUT_SECONDS
            ),
        )


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number") from exc
    if value <= 0:
        raise ConfigError(f"{key} must be positive")
    return value


def _read_sync_user(path: Path) -> tuple[str, str]:
    # Reads the existing sync server env file in place. It is never copied.
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError("sync credentials file is unreadable") from exc
    for line in text.splitlines():
        if line.startswith("SYNC_USER1="):
            value = line.split("=", 1)[1].rstrip("\r\n")
            username, sep, password = value.partition(":")
            if not sep or not username or not password:
                raise ConfigError("SYNC_USER1 is malformed")
            return username, password
    raise ConfigError("SYNC_USER1 not found in sync credentials file")

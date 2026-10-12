"""Entrypoint: `python -m anki_api_v2`. Always one process, one worker.

The collection is owned by this process. Running more than one worker would mean
more than one process opening collection.anki2, which is exactly what must not happen.

Exit codes: 0 normal stop, 2 configuration error. The systemd unit does not restart
on 2, so a bad config does not turn into a restart loop.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

import uvicorn

from anki_api_v2.app import create_app
from anki_api_v2.config import LOOPBACK_HOSTS, ConfigError, Settings

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8770
EXIT_CONFIG_ERROR = 2


def main(env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    logging.basicConfig(level=env.get("ANKI_API_LOG_LEVEL", "INFO"))
    host = env.get("ANKI_API_HOST", DEFAULT_HOST)
    if host not in LOOPBACK_HOSTS:
        print(
            "ANKI_API_HOST must be a loopback address; public exposure is not configured here",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    try:
        port = int(env.get("ANKI_API_PORT", str(DEFAULT_PORT)))
        settings = Settings.from_env(env)
    except (ConfigError, ValueError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    if not Path(settings.collection_path).is_file():
        print(
            f"collection file not found at {settings.collection_path}; refusing to start",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR

    app = create_app(settings)
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,
        proxy_headers=False,
        server_header=False,
        log_level=env.get("ANKI_API_LOG_LEVEL", "info").lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

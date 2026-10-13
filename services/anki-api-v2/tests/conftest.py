from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from anki_api_v2.app import create_app
from anki_api_v2.config import Settings
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.fakes import FakeClock, FakeSyncBackend
from tests.helpers import TEST_TOKEN, Fixture, build_synthetic_collection

AUTH = {"Authorization": f"Bearer {TEST_TOKEN}"}


@dataclass
class Api:
    client: TestClient
    transport: FakeSyncBackend
    clock: FakeClock
    fx: Fixture
    settings: Settings

    def get(self, path: str, **kwargs: Any):
        return self.client.get(path, headers=AUTH, **kwargs)

    def post(self, path: str, json: Any = None):
        return self.client.post(path, json=json, headers=AUTH)

    def patch(self, path: str, json: Any):
        return self.client.patch(path, json=json, headers=AUTH)

    def delete(self, path: str):
        return self.client.delete(path, headers=AUTH)

    def add_note(self, front, back="b", tags=(), deck="Default", model="Basic") -> str:
        """Create a note directly on the collection (test setup only)."""

        def job(col):
            note = col.new_note(col.models.by_name(model))
            note["Front"] = front
            note["Back"] = back
            note.tags = list(tags)
            col.add_note(note, col.decks.id(deck))
            return str(note.id)

        return self.run(job)

    def run(self, fn):
        """Run a job on the collection owner thread (test setup/inspection only)."""
        return self.client.app.state.actor.submit(fn)


def make_settings(fx: Fixture, **overrides: Any) -> Settings:
    base = dict(
        collection_path=fx.path,
        token=TEST_TOKEN,
        sync_endpoint="http://127.0.0.1:9/",
        sync_username="tester",
        sync_password="pw-never-logged",
        lock_path=fx.path.parent / "collection.lock",
        freshness_ttl_seconds=30.0,
        queue_timeout_seconds=5.0,
    )
    base.update(overrides)
    return Settings(**base)


def make_app(settings: Settings, transport: FakeSyncBackend, clock: FakeClock) -> FastAPI:
    return create_app(settings, transport=transport, clock=clock)


@pytest.fixture
def fx(tmp_path) -> Fixture:
    return build_synthetic_collection(tmp_path / "collection.anki2")


@pytest.fixture
def settings(fx: Fixture) -> Settings:
    return make_settings(fx)


@pytest.fixture
def api(fx: Fixture, settings: Settings) -> Iterator[Api]:
    clock = FakeClock()
    transport = FakeSyncBackend(clock=clock, watch_note_id=fx.basic_note_id)
    app = make_app(settings, transport, clock)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield Api(client=client, transport=transport, clock=clock, fx=fx, settings=settings)

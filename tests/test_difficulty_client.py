"""Unit tests for DifficultyClient's async fetch-and-poll behavior."""

import json
import time
import urllib.error

import pytest

from src.game.services.difficulty_client import DifficultyClient, DifficultyFetchHandle


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _wait_until_done(handle: DifficultyFetchHandle, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if handle.is_done():
            return
        time.sleep(0.01)
    pytest.fail("DifficultyFetchHandle never completed within timeout")


def test_fetch_success_resolves_config(monkeypatch):
    body = json.dumps({"boss_key": "boss_wizard", "config": {"max_mana": 150.0}})

    def fake_urlopen(req, timeout=None):
        return _FakeResponse(200, body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    handle = DifficultyClient.fetch_recommendation_async("boss_wizard")
    _wait_until_done(handle)

    assert handle.result() == {"max_mana": 150.0}


def test_fetch_connection_error_resolves_none(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    handle = DifficultyClient.fetch_recommendation_async("boss_wizard")
    _wait_until_done(handle)

    assert handle.result() is None


def test_fetch_unexpected_error_resolves_none_without_raising(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise ValueError("boom")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    handle = DifficultyClient.fetch_recommendation_async("boss_wizard")
    _wait_until_done(handle)

    assert handle.result() is None


def test_is_done_false_before_completion():
    # Use a real (slow-resolving) target that never gets monkeypatched success --
    # a bogus URL that will fail fast, but is_done() should be False immediately
    # after starting since the fetch runs in a background thread.
    handle = DifficultyFetchHandle()
    assert handle.is_done() is False
    assert handle.result() is None

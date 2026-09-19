"""Groq calls walk a model chain: a retired/limited model falls through to the
next, and the app degrades to None (never raises) when nothing answers."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from groq import AuthenticationError, NotFoundError, RateLimitError

from app.services import groq_client
from app.services.groq_client import groq_chat_text, groq_model_chain


def _settings(**over):
    base = dict(
        groq_api_key="k", groq_model="primary/model", groq_fallback_models="second/model, third/model,primary/model",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _http_error(cls, status):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(status, request=request)
    return cls("boom", response=response, body=None)


class _FakeGroq:
    """Scripted behaviour per model name: an Exception to raise or text to return."""

    script: dict[str, object] = {}
    calls: list[str] = []

    def __init__(self, api_key):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, *, model, **kwargs):
        _FakeGroq.calls.append(model)
        outcome = _FakeGroq.script[model]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=outcome))])


@pytest.fixture(autouse=True)
def _fake_groq(monkeypatch):
    _FakeGroq.script, _FakeGroq.calls = {}, []
    monkeypatch.setattr("groq.AsyncGroq", _FakeGroq)


def test_chain_orders_and_dedupes_models():
    assert groq_model_chain(_settings()) == ["primary/model", "second/model", "third/model"]


async def test_retired_model_falls_through_to_the_next():
    _FakeGroq.script = {"primary/model": _http_error(NotFoundError, 404), "second/model": '{"ok": 1}'}
    text = await groq_chat_text(_settings(), [{"role": "user", "content": "x"}], temperature=0, max_tokens=10, timeout=5)
    assert text == '{"ok": 1}'
    assert _FakeGroq.calls == ["primary/model", "second/model"]


async def test_rate_limited_model_falls_through():
    _FakeGroq.script = {"primary/model": _http_error(RateLimitError, 429), "second/model": "  ", "third/model": "{}"}
    text = await groq_chat_text(_settings(), [], temperature=0, max_tokens=10, timeout=5)
    assert text == "{}"  # a blank reply is skipped too
    assert _FakeGroq.calls == ["primary/model", "second/model", "third/model"]


async def test_all_models_failing_returns_none_not_an_exception():
    _FakeGroq.script = {m: _http_error(NotFoundError, 404) for m in ("primary/model", "second/model", "third/model")}
    assert await groq_chat_text(_settings(), [], temperature=0, max_tokens=10, timeout=5) is None


async def test_bad_key_stops_immediately():
    _FakeGroq.script = {"primary/model": _http_error(AuthenticationError, 401)}
    assert await groq_chat_text(_settings(), [], temperature=0, max_tokens=10, timeout=5) is None
    assert _FakeGroq.calls == ["primary/model"]


async def test_no_key_makes_no_calls():
    assert await groq_chat_text(_settings(groq_api_key=""), [], temperature=0, max_tokens=10, timeout=5) is None
    assert _FakeGroq.calls == []

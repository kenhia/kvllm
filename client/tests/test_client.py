"""kvllm_client unit tests — fakes only, no network, no GPU.

The fallback fakes mirror kmon's tests/test_controller.py, which this lib's
invoke_with_fallback absorbed (kmon sprint 03).
"""

import asyncio
from types import SimpleNamespace

import httpx
import kvllm_client as kc
import pytest

PAYLOAD = {"data": [{"id": "qwen2.5-7b-instruct"}]}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _network_dead(*args, **kwargs):
    raise ConnectionError("kvllm is down")


# --- discovery ---


def test_discover_model_returns_served_id(monkeypatch):
    calls = {}

    def fake_get(url, timeout):
        calls["url"] = url
        return FakeResponse(PAYLOAD)

    monkeypatch.setattr(httpx, "get", fake_get)
    assert kc.discover_model("http://kai:8000/v1") == "qwen2.5-7b-instruct"
    assert calls["url"] == "http://kai:8000/v1/models"


def test_discover_model_empty_list_raises(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse({"data": []}))
    with pytest.raises(RuntimeError, match="no models served"):
        kc.discover_model()


def test_discover_model_http_error_raises(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda url, timeout: FakeResponse({}, status_code=503)
    )
    with pytest.raises(RuntimeError, match="503"):
        kc.discover_model()


def test_resolve_model_passthrough_needs_no_network(monkeypatch):
    monkeypatch.setattr(httpx, "get", _network_dead)
    assert kc.resolve_model("explicit-name") == "explicit-name"


def test_aresolve_model_uses_injected_client():
    calls = {}

    class FakeAsyncClient:
        async def get(self, url):
            calls["url"] = url
            return FakeResponse(PAYLOAD)

    got = asyncio.run(kc.aresolve_model("auto", http=FakeAsyncClient()))
    assert got == "qwen2.5-7b-instruct"
    assert calls["url"] == f"{kc.DEFAULT_BASE_URL}/models"


def test_aresolve_model_passthrough_needs_no_network():
    assert asyncio.run(kc.aresolve_model("explicit-name")) == "explicit-name"


# --- model constructors ---


def test_local_model_auto_discovers(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(PAYLOAD))
    llm, model_id = kc.local_model("http://kai:8000/v1", streaming=True)
    assert model_id == "qwen2.5-7b-instruct"
    assert llm.model_name == "qwen2.5-7b-instruct"
    assert llm.streaming is True


def test_local_model_explicit_name_skips_discovery(monkeypatch):
    monkeypatch.setattr(httpx, "get", _network_dead)
    llm, model_id = kc.local_model(model="explicit-name", temperature=0.5)
    assert model_id == "explicit-name"
    assert llm.temperature == 0.5
    assert llm.streaming is False


def test_frontier_model_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    llm, model_id = kc.frontier_model()
    assert model_id == kc.DEFAULT_FRONTIER_MODEL
    assert llm.max_tokens == 2048


def test_frontier_model_explicit(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _, model_id = kc.frontier_model("claude-sonnet-5")
    assert model_id == "claude-sonnet-5"


# --- fallback (kmon sprint 03 behavior) ---


class FakeLLM:
    def __init__(self, text):
        self.text = text

    def invoke(self, messages):
        return SimpleNamespace(content=self.text)


class ExplodingLLM:
    def invoke(self, messages):
        raise TimeoutError("died mid-call")


def test_fallback_stays_local_when_local_works():
    out = kc.invoke_with_fallback(
        "msgs",
        local=lambda: (FakeLLM("local report"), "qwen2.5-7b-instruct"),
        frontier=_network_dead,
    )
    assert out == kc.FallbackResult("local report", "qwen2.5-7b-instruct", False)


def test_fallback_escalates_when_local_down():
    seen = []
    out = kc.invoke_with_fallback(
        "msgs",
        local=_network_dead,
        frontier=lambda: (FakeLLM("frontier report"), "claude-haiku-4-5"),
        on_fallback=seen.append,
    )
    assert out.escalated is True
    assert out.model_used == "claude-haiku-4-5"
    assert out.content == "frontier report"
    assert isinstance(seen[0], ConnectionError)


def test_fallback_escalates_when_local_invoke_fails():
    out = kc.invoke_with_fallback(
        "msgs",
        local=lambda: (ExplodingLLM(), "qwen2.5-7b-instruct"),
        frontier=lambda: (FakeLLM("frontier report"), "claude-haiku-4-5"),
    )
    assert out.escalated is True
    assert out.content == "frontier report"


def test_fallback_frontier_failure_propagates():
    with pytest.raises(ConnectionError):
        kc.invoke_with_fallback("msgs", local=_network_dead, frontier=_network_dead)

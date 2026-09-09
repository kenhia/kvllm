"""kvllm_client unit tests — fakes only, no network, no GPU.

The fallback fakes mirror kmon's tests/test_controller.py, which this lib's
invoke_with_fallback absorbed (kmon sprint 03). The reasoning-model cases
(sprint 20, WI-1983) use scripted replies shaped like what vLLM 0.28.0 returns.
"""

import asyncio
from types import SimpleNamespace

import httpx
import kvllm_client as kc
import pytest

PAYLOAD = {"data": [{"id": "qwen2.5-7b-instruct"}]}
PAYLOAD_WINDOW = {"data": [{"id": "qwen3.8-27b-nvfp4", "max_model_len": 122880}]}


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


# --- served-window discovery (WI-1983: callers read the window, not guess it) ---


def test_served_model_info_reports_window(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(PAYLOAD_WINDOW))
    assert kc.served_model_info() == kc.ServedModel("qwen3.8-27b-nvfp4", 122880)


def test_served_model_info_window_is_optional(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(PAYLOAD))
    info = kc.served_model_info()
    assert info.id == "qwen2.5-7b-instruct" and info.max_model_len is None


def test_aserved_model_info_uses_injected_client():
    class FakeAsyncClient:
        async def get(self, url):
            return FakeResponse(PAYLOAD_WINDOW)

    info = asyncio.run(kc.aserved_model_info(http=FakeAsyncClient()))
    assert info == kc.ServedModel("qwen3.8-27b-nvfp4", 122880)


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


def test_local_model_defaults_to_model_sampling_and_answer_budget(monkeypatch):
    # Greedy thinking looped verbatim once in sprint 19; the served model's own
    # generation_config is the default, and reasoning needs an 8k budget.
    monkeypatch.setattr(httpx, "get", _network_dead)
    llm, _ = kc.local_model(model="qwen3.8-27b-nvfp4")
    assert isinstance(llm, kc.KvllmChatOpenAI)
    assert llm.temperature is None
    assert llm.max_tokens == kc.DEFAULT_LOCAL_MAX_TOKENS == 8192
    params = llm._default_params  # what actually goes on the wire
    assert "temperature" not in params
    # langchain-openai sends the budget under OpenAI's current name; vLLM honours it.
    assert params["max_completion_tokens"] == 8192
    assert "max_tokens" not in params
    assert "extra_body" not in params


def test_local_model_budget_can_be_switched_off():
    llm, _ = kc.local_model(model="x", max_tokens=None)
    params = llm._default_params
    assert "max_tokens" not in params and "max_completion_tokens" not in params


def test_local_model_chat_template_kwargs_ride_in_extra_body():
    llm, _ = kc.local_model(
        model="x", chat_template_kwargs={"reasoning_effort": "medium"}
    )
    assert llm._default_params["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": "medium"}
    }


def test_local_model_request_timeout_is_the_completion_timeout():
    llm, _ = kc.local_model(model="x", request_timeout=300)
    assert llm.request_timeout == 300


def test_template_kwargs_override_per_call():
    llm, _ = kc.local_model(
        model="x", chat_template_kwargs={"reasoning_effort": "medium"}
    )
    kw = kc.template_kwargs(reasoning_effort="xhigh")
    assert kw == {"extra_body": {"chat_template_kwargs": {"reasoning_effort": "xhigh"}}}
    per_call = llm._get_request_payload("hi", **kw)
    assert per_call["extra_body"]["chat_template_kwargs"] == {
        "reasoning_effort": "xhigh"
    }
    default = llm._get_request_payload("hi")
    assert default["extra_body"]["chat_template_kwargs"] == {
        "reasoning_effort": "medium"
    }


def test_frontier_model_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    llm, model_id = kc.frontier_model()
    assert model_id == kc.DEFAULT_FRONTIER_MODEL
    assert llm.max_tokens == 2048


def test_frontier_model_explicit(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    _, model_id = kc.frontier_model("claude-sonnet-5")
    assert model_id == "claude-sonnet-5"


# --- the reasoning field (vLLM 0.28.0 says `reasoning`, not `reasoning_content`) ---


def _completion(content, **message_fields):
    return {
        "id": "chatcmpl-1",
        "model": "qwen3.8-27b-nvfp4",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content, **message_fields},
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def test_kvllm_chat_keeps_vllm_reasoning():
    llm, _ = kc.local_model(model="x")
    msg = (
        llm._create_chat_result(_completion("42", reasoning="6 × 7"))
        .generations[0]
        .message
    )
    assert msg.content == "42"
    assert kc.reasoning_of(msg) == "6 × 7"


def test_kvllm_chat_accepts_older_reasoning_content():
    llm, _ = kc.local_model(model="x")
    result = llm._create_chat_result(_completion("42", reasoning_content="older"))
    assert kc.reasoning_of(result.generations[0].message) == "older"


def test_kvllm_chat_without_reasoning_adds_nothing():
    llm, _ = kc.local_model(model="x")
    msg = llm._create_chat_result(_completion("42")).generations[0].message
    assert "reasoning" not in msg.additional_kwargs
    assert kc.reasoning_of(msg) is None


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


# --- empty answers are failures (sprint 19: 6k tokens of reasoning, empty content) ---


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.replies.pop(0)


def _reply(content, reasoning=None, tool_calls=None):
    return SimpleNamespace(
        content=content,
        additional_kwargs={"reasoning": reasoning} if reasoning else {},
        tool_calls=tool_calls or [],
    )


def test_empty_answer_is_retried_once_then_answered_locally():
    llm = ScriptedLLM(_reply("", reasoning="…"), _reply("report", reasoning="ok"))
    out = kc.invoke_with_fallback(
        "msgs", local=lambda: (llm, "qwen3.8-27b-nvfp4"), frontier=_network_dead
    )
    assert out == kc.FallbackResult("report", "qwen3.8-27b-nvfp4", False, "ok")
    assert llm.calls == 2


def test_empty_answer_twice_escalates_with_the_cause():
    seen = []
    llm = ScriptedLLM(_reply("  \n"), _reply("", reasoning="6k tokens of thought"))
    out = kc.invoke_with_fallback(
        "msgs",
        local=lambda: (llm, "qwen3.8-27b-nvfp4"),
        frontier=lambda: (FakeLLM("frontier report"), "claude-haiku-4-5"),
        on_fallback=seen.append,
    )
    assert out.escalated is True
    assert out.content == "frontier report"
    assert out.reasoning is None  # the frontier reply carried none
    assert llm.calls == 2
    cause = seen[0]
    assert isinstance(cause, kc.EmptyAnswerError)
    assert cause.model_id == "qwen3.8-27b-nvfp4"
    assert cause.attempts == 2
    assert cause.reasoning == "6k tokens of thought"
    assert "empty answer 2 time(s)" in str(cause)


def test_empty_retries_zero_escalates_on_the_first_empty_answer():
    llm = ScriptedLLM(_reply(""))
    out = kc.invoke_with_fallback(
        "msgs",
        local=lambda: (llm, "qwen"),
        frontier=lambda: (FakeLLM("f"), "claude-haiku-4-5"),
        empty_retries=0,
    )
    assert out.escalated is True
    assert llm.calls == 1


def test_tool_call_with_empty_content_is_not_an_empty_answer():
    llm = ScriptedLLM(_reply("", tool_calls=[{"name": "run", "args": {}, "id": "1"}]))
    out = kc.invoke_with_fallback(
        "msgs", local=lambda: (llm, "qwen"), frontier=_network_dead
    )
    assert out.escalated is False
    assert llm.calls == 1


def test_is_empty_answer_reads_block_content():
    assert kc.is_empty_answer(SimpleNamespace(content=[{"type": "text", "text": " "}]))
    assert not kc.is_empty_answer(
        SimpleNamespace(content=[{"type": "text", "text": "x"}])
    )
    assert kc.is_empty_answer(SimpleNamespace(content=None))
    assert kc.is_empty_answer(SimpleNamespace(content=[]))


def test_fallback_result_carries_local_reasoning():
    llm = ScriptedLLM(_reply("report", reasoning="because"))
    out = kc.invoke_with_fallback(
        "msgs", local=lambda: (llm, "qwen"), frontier=_network_dead
    )
    assert out.reasoning == "because"

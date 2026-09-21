"""Shared LLM client for services talking to kvllm's OpenAI-compatible /v1.

Extracted from kagent, kmon, and klams-mind (homelab-ai WI 274) so the pattern
lives in one place: point ChatOpenAI at kvllm, discover the served model via
/v1/models (kvllm serves exactly one model; the registry key IS the model name,
so consumers follow automatically when Ken switches models), and escalate to
ChatAnthropic when the local tier is down or not trusted for the stakes.

The defaults are set for a reasoning model as the resident (kvllm sprint 20,
WI-1983): sampling is the served model's own, the local tier carries an answer
budget, chat-template kwargs (reasoning effort, thinking on/off) pass through,
the served window is discoverable, and an empty answer after a long reasoning
phase is a local-tier failure rather than a result.

Env-var policy: none. Consumers own their env vars (KMON_LOCAL_BASE_URL,
KAGENT_BASE_URL, ...) and pass explicit arguments here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic

DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_FRONTIER_MODEL = "claude-haiku-4-5"
# Anthropic deprecates `temperature` per model, and a model that has lost it rejects the
# request outright rather than ignoring the parameter (WI-2624). Measured against the live
# API on 2026-09-13: claude-sonnet-5 400s with `temperature`, claude-haiku-4-5 does not.
# The knowledge lives here, in the one place that talks to the API, so callers need none.
TEMPERATURE_REFUSED = frozenset({"claude-sonnet-5"})
# Reasoning counts toward max_tokens. Cross-referencing at `medium` effort used up to
# 6,095 output tokens on Qwen3.8 and one draw in nine wanted more (sprint 19), so the
# local tier's budget is 8k, not the 2k a gemma-era caller would have picked.
DEFAULT_LOCAL_MAX_TOKENS = 8192
AUTO = "auto"

__all__ = [
    "AUTO",
    "DEFAULT_BASE_URL",
    "DEFAULT_FRONTIER_MODEL",
    "DEFAULT_LOCAL_MAX_TOKENS",
    "EmptyAnswerError",
    "FallbackResult",
    "KvllmChatOpenAI",
    "ServedModel",
    "TEMPERATURE_REFUSED",
    "TokenUsage",
    "adiscover_model",
    "aresolve_model",
    "aserved_model_info",
    "discover_model",
    "frontier_model",
    "invoke_with_fallback",
    "is_empty_answer",
    "local_model",
    "reasoning_of",
    "resolve_model",
    "served_model_info",
    "template_kwargs",
    "usage_of",
]


# --- discovery ------------------------------------------------------------------------


@dataclass(frozen=True)
class ServedModel:
    """What /v1/models says about the one model kvllm serves.

    `max_model_len` is the served context window — vLLM reports it on the model
    card — so callers size their context, edit and tool-output budgets from it
    instead of hard-coding a number that was right for the previous resident.
    None if the endpoint does not report one.
    """

    id: str
    max_model_len: int | None = None


def _served_model(payload: dict, base_url: str) -> ServedModel:
    served = payload["data"]
    if not served:
        raise RuntimeError(f"no models served at {base_url}/models")
    card = served[0]
    window = card.get("max_model_len")
    return ServedModel(id=card["id"], max_model_len=int(window) if window else None)


def served_model_info(
    base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0
) -> ServedModel:
    """Ask /models what is being served, window included."""
    resp = httpx.get(f"{base_url}/models", timeout=timeout)
    resp.raise_for_status()
    return _served_model(resp.json(), base_url)


async def aserved_model_info(
    base_url: str = DEFAULT_BASE_URL,
    *,
    http: httpx.AsyncClient | None = None,
    timeout: float = 10.0,
) -> ServedModel:
    """Async served_model_info; pass `http` to reuse an existing AsyncClient."""
    url = f"{base_url}/models"
    if http is not None:
        resp = await http.get(url)
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
    resp.raise_for_status()
    return _served_model(resp.json(), base_url)


def discover_model(base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> str:
    """Ask /models what is being served; kvllm serves exactly one model."""
    return served_model_info(base_url, timeout=timeout).id


async def adiscover_model(
    base_url: str = DEFAULT_BASE_URL,
    *,
    http: httpx.AsyncClient | None = None,
    timeout: float = 10.0,
) -> str:
    """Async discover_model; pass `http` to reuse an existing AsyncClient."""
    info = await aserved_model_info(base_url, http=http, timeout=timeout)
    return info.id


def resolve_model(
    name: str, base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0
) -> str:
    """Resolve "auto" to whatever the endpoint is serving; pass anything else through."""
    if name != AUTO:
        return name
    return discover_model(base_url, timeout=timeout)


async def aresolve_model(
    name: str,
    base_url: str = DEFAULT_BASE_URL,
    *,
    http: httpx.AsyncClient | None = None,
    timeout: float = 10.0,
) -> str:
    """Async resolve_model; pass `http` to reuse an existing AsyncClient."""
    if name != AUTO:
        return name
    return await adiscover_model(base_url, http=http, timeout=timeout)


# --- model constructors ---------------------------------------------------------------


class KvllmChatOpenAI(ChatOpenAI):
    """ChatOpenAI that keeps the reasoning vLLM returns.

    langchain-openai targets the official OpenAI schema and drops provider fields
    from the assistant message; its own module docstring says to subclass for
    vLLM. On vLLM 0.28.0 the reasoning parser's output is `message.reasoning`
    (older releases used `reasoning_content`); whichever is present is copied to
    `additional_kwargs["reasoning"]`, where `reasoning_of` reads it. Non-streaming
    only: a streamed reply arrives as deltas and this hook is not on that path.
    """

    def _create_chat_result(
        self, response: Any, generation_info: dict | None = None
    ) -> Any:
        result = super()._create_chat_result(response, generation_info)
        raw = (
            response
            if isinstance(response, dict)
            else response.model_dump(
                exclude={"choices": {"__all__": {"message": {"parsed"}}}},
                warnings=False,
            )
        )
        for gen, choice in zip(result.generations, raw.get("choices") or []):
            msg = (choice or {}).get("message") or {}
            reasoning = msg.get("reasoning") or msg.get("reasoning_content")
            if reasoning:
                gen.message.additional_kwargs["reasoning"] = reasoning
        return result


def template_kwargs(**kwargs: Any) -> dict[str, Any]:
    """Per-call chat-template overrides, as invoke kwargs.

        llm.invoke(messages, **template_kwargs(reasoning_effort="xhigh"))

    Qwen3.8 reads `reasoning_effort` (low / medium / xhigh; `enable_thinking=False`
    turns thinking off), gemma-4 reads `enable_thinking`. vLLM takes them in
    `extra_body.chat_template_kwargs`, and a per-call `extra_body` REPLACES the one
    `local_model(chat_template_kwargs=...)` put on the model for that call — so
    name every key the call needs, not just the one that changed.
    """
    return {"extra_body": {"chat_template_kwargs": dict(kwargs)}}


def local_model(
    base_url: str = DEFAULT_BASE_URL,
    *,
    model: str = AUTO,
    api_key: str = "EMPTY",
    temperature: float | None = None,
    max_tokens: int | None = DEFAULT_LOCAL_MAX_TOKENS,
    chat_template_kwargs: Mapping[str, Any] | None = None,
    streaming: bool = False,
    timeout: float = 10.0,
    request_timeout: float | None = None,
    max_retries: int = 2,
) -> tuple[KvllmChatOpenAI, str]:
    """Return (llm, model_id) for the local tier at `base_url`.

    The default model="auto" discovers via /v1/models; pass an explicit name to
    skip the discovery round-trip. `timeout` bounds that discovery call;
    `request_timeout` bounds each completion (None = the OpenAI SDK's default).

    `request_timeout` is per ATTEMPT, and `max_retries` is how many times a
    failed attempt is retried, so the worst case a caller waits is
    `request_timeout x (1 + max_retries)` — 900 s for kyac's 300 s budget at the
    default of 2 (WI-2010). The default is the OpenAI SDK's own, so it is stated
    here rather than changed. Pass `max_retries=0` to own the retry yourself:
    the local tier's failure mode is a hung engine, not a flaky network, and
    retrying a hung engine only delays the fallback.

    `temperature=None` (the default) sends no sampling parameters, so the served
    model's own generation_config applies — T=1.0 / top-p 0.95 / top-k 20 for
    Qwen3.8. Greedy decoding in thinking mode can loop verbatim until the budget
    (seen once in sprint 19); pass 0.0 only where determinism is worth that risk.

    `max_tokens` is the answer budget, reasoning included (None = no budget: vLLM
    then allows up to the window). vLLM rejects a request whose prompt plus
    budget exceeds the served window, so size prompts from `served_model_info`.
    `chat_template_kwargs` become the model's default template overrides; see
    `template_kwargs` for the per-call form.
    """
    model_id = resolve_model(model, base_url, timeout=timeout)
    extra: dict[str, Any] = {}
    if chat_template_kwargs:
        extra["extra_body"] = {"chat_template_kwargs": dict(chat_template_kwargs)}
    if request_timeout is not None:
        extra["timeout"] = request_timeout
    llm = KvllmChatOpenAI(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        max_retries=max_retries,
        **extra,
    )
    return llm, model_id


def frontier_model(
    model: str = DEFAULT_FRONTIER_MODEL,
    *,
    temperature: float | None = 0.0,
    max_tokens: int = 2048,
) -> tuple[ChatAnthropic, str]:
    """Return (llm, model_id) for the escalation tier.

    langchain-anthropic is the [anthropic] extra — imported lazily so
    local-only consumers don't need it installed.

    `temperature` still defaults to 0.0 — the determinism this tier is chosen
    for — but the parameter is OMITTED from the request when it is None, or when
    `model` is in `TEMPERATURE_REFUSED`. Anthropic deprecates it per model, and a
    model that has lost it 400s before generating a token; since this tier only
    runs once the local one has already failed a gate, that is a tier which
    cannot be reached exactly when it is needed (WI-2624). Callers get the fix
    without passing anything.
    """
    from langchain_anthropic import ChatAnthropic

    kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens}
    if temperature is not None and model not in TEMPERATURE_REFUSED:
        kwargs["temperature"] = temperature
    llm = ChatAnthropic(**kwargs)
    return llm, model


# --- fallback -------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenUsage:
    """What one reply cost, from whichever tier answered.

    Provider-neutral on purpose: read from LangChain's `usage_metadata`, which
    ChatOpenAI (vLLM) and ChatAnthropic both populate, so a `FallbackResult`
    reports the same shape whether the local tier or the frontier answered — and
    a consumer stops needing its own per-tier callback to log this (WI-2019;
    kyac's `ReasoningWatch` and kmon's `UsageWatch` were the second copy).

    `reasoning` is the part of `completion` the model spent thinking — reasoning
    counts toward `max_tokens`, so this is the field that explains a budget that
    ran out. `cached` is the prompt prefix served from vLLM's prefix cache.

    Both detail fields are None when the provider did not report them, which is
    NOT the same as 0 and is the honest answer for `cached` on the local tier
    today: vLLM only fills it in when served with `--enable-prompt-tokens-details`
    (off by default, and kvllm does not pass it), so prefix-cache effectiveness is
    read from the engine log rather than from here. See README, "The reasoning
    field, and prefix caching".
    """

    prompt: int
    completion: int
    total: int
    reasoning: int | None = None
    cached: int | None = None


@dataclass
class FallbackResult:
    content: Any
    model_used: str
    escalated: bool
    # The reasoning behind `content`, when the model that produced it exposes one
    # (vLLM's reasoning parser via KvllmChatOpenAI); None otherwise. The cause of an
    # escalation is the exception `on_fallback` receives, not this field.
    reasoning: str | None = None
    # What the answering tier reported spending; None when it reported nothing.
    usage: TokenUsage | None = None


class EmptyAnswerError(RuntimeError):
    """The local tier ended its turn with no answer text.

    A reasoning model can spend thousands of tokens thinking and stop with empty
    content (`finish_reason: stop`; seen once at 68k context in sprint 19). That
    is a failed call, not a report: `invoke_with_fallback` retries, then raises
    this so the caller's `on_fallback` sees the cause — `reasoning` is the last
    attempt's reasoning, for the log (kmon WI-1948) — and escalates.
    """

    def __init__(self, model_id: str, reasoning: str | None, attempts: int):
        super().__init__(
            f"{model_id} returned an empty answer {attempts} time(s) in a row"
        )
        self.model_id = model_id
        self.reasoning = reasoning
        self.attempts = attempts


def reasoning_of(message: Any) -> str | None:
    """The reasoning attached to a reply, if the model exposed one."""
    kwargs = getattr(message, "additional_kwargs", None) or {}
    return kwargs.get("reasoning") or None


def usage_of(message: Any) -> TokenUsage | None:
    """The token counts attached to a reply, if the provider reported any.

    Reads LangChain's provider-neutral `usage_metadata`. Returns None when
    nothing was reported, so a caller can tell "no usage" from "zero tokens".
    """
    meta = getattr(message, "usage_metadata", None) or {}
    if not meta:
        return None
    prompt = int(meta.get("input_tokens") or 0)
    completion = int(meta.get("output_tokens") or 0)
    reasoning = (meta.get("output_token_details") or {}).get("reasoning")
    cached = (meta.get("input_token_details") or {}).get("cache_read")
    return TokenUsage(
        prompt=prompt,
        completion=completion,
        total=int(meta.get("total_tokens") or prompt + completion),
        reasoning=None if reasoning is None else int(reasoning),
        cached=None if cached is None else int(cached),
    )


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type", "text") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return "" if content is None else str(content)


def is_empty_answer(message: Any) -> bool:
    """True when a reply carries neither answer text nor a tool call."""
    if getattr(message, "tool_calls", None):
        return False
    return not _text_of(getattr(message, "content", None)).strip()


def invoke_with_fallback(
    messages: Any,
    *,
    local: Callable[[], tuple[Any, str]],
    frontier: Callable[[], tuple[Any, str]],
    on_fallback: Callable[[Exception], None] | None = None,
    empty_retries: int = 1,
) -> FallbackResult:
    """Try the local tier; any failure building or invoking it escalates to frontier.

    Absorbs kmon sprint 03's rule: the local tier being down must not kill the
    result. `local` and `frontier` are zero-arg factories returning
    (llm, model_id) so that a dead endpoint fails inside the try. An empty answer
    (no text, no tool call) is a local failure too: retried `empty_retries`
    times, then escalated with `EmptyAnswerError` as the cause. Frontier-tier
    failures propagate — there is nothing left to fall back to. Escalation
    *routing* (whether a verified-bad result may re-escalate, whether optional
    work is skipped when local is down) stays with the consumer.
    """
    try:
        llm, model_id = local()
        reasoning = None
        for _ in range(1 + empty_retries):
            reply = llm.invoke(messages)
            reasoning = reasoning_of(reply)
            if not is_empty_answer(reply):
                return FallbackResult(
                    content=reply.content,
                    model_used=model_id,
                    escalated=False,
                    reasoning=reasoning,
                    usage=usage_of(reply),
                )
        raise EmptyAnswerError(model_id, reasoning, 1 + empty_retries)
    except Exception as exc:  # noqa: BLE001 — any local-tier failure means escalate
        if on_fallback is not None:
            on_fallback(exc)
    llm, model_id = frontier()
    reply = llm.invoke(messages)
    return FallbackResult(
        content=reply.content,
        model_used=model_id,
        escalated=True,
        reasoning=reasoning_of(reply),
        usage=usage_of(reply),
    )

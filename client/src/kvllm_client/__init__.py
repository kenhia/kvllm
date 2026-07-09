"""Shared LLM client for services talking to kvllm's OpenAI-compatible /v1.

Extracted from kagent, kmon, and klams-mind (homelab-ai WI 274) so the pattern
lives in one place: point ChatOpenAI at kvllm, discover the served model via
/v1/models (kvllm serves exactly one model; the registry key IS the model name,
so consumers follow automatically when Ken switches models), and escalate to
ChatAnthropic when the local tier is down or not trusted for the stakes.

Env-var policy: none. Consumers own their env vars (KMON_LOCAL_BASE_URL,
KAGENT_BASE_URL, ...) and pass explicit arguments here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic

DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_FRONTIER_MODEL = "claude-haiku-4-5"
AUTO = "auto"

__all__ = [
    "AUTO",
    "DEFAULT_BASE_URL",
    "DEFAULT_FRONTIER_MODEL",
    "FallbackResult",
    "adiscover_model",
    "aresolve_model",
    "discover_model",
    "frontier_model",
    "invoke_with_fallback",
    "local_model",
    "resolve_model",
]


def _first_model_id(payload: dict, base_url: str) -> str:
    served = payload["data"]
    if not served:
        raise RuntimeError(f"no models served at {base_url}/models")
    return served[0]["id"]


def discover_model(base_url: str = DEFAULT_BASE_URL, *, timeout: float = 10.0) -> str:
    """Ask /models what is being served; kvllm serves exactly one model."""
    resp = httpx.get(f"{base_url}/models", timeout=timeout)
    resp.raise_for_status()
    return _first_model_id(resp.json(), base_url)


async def adiscover_model(
    base_url: str = DEFAULT_BASE_URL,
    *,
    http: httpx.AsyncClient | None = None,
    timeout: float = 10.0,
) -> str:
    """Async discover_model; pass `http` to reuse an existing AsyncClient."""
    url = f"{base_url}/models"
    if http is not None:
        resp = await http.get(url)
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
    resp.raise_for_status()
    return _first_model_id(resp.json(), base_url)


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


def local_model(
    base_url: str = DEFAULT_BASE_URL,
    *,
    model: str = AUTO,
    api_key: str = "EMPTY",
    temperature: float = 0.0,
    streaming: bool = False,
    timeout: float = 10.0,
) -> tuple[ChatOpenAI, str]:
    """Return (llm, model_id) for the local tier at `base_url`.

    The default model="auto" discovers via /v1/models; pass an explicit name to
    skip the discovery round-trip.
    """
    model_id = resolve_model(model, base_url, timeout=timeout)
    llm = ChatOpenAI(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        streaming=streaming,
    )
    return llm, model_id


def frontier_model(
    model: str = DEFAULT_FRONTIER_MODEL,
    *,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> tuple[ChatAnthropic, str]:
    """Return (llm, model_id) for the escalation tier.

    langchain-anthropic is the [anthropic] extra — imported lazily so
    local-only consumers don't need it installed.
    """
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens)
    return llm, model


@dataclass
class FallbackResult:
    content: Any
    model_used: str
    escalated: bool


def invoke_with_fallback(
    messages: Any,
    *,
    local: Callable[[], tuple[Any, str]],
    frontier: Callable[[], tuple[Any, str]],
    on_fallback: Callable[[Exception], None] | None = None,
) -> FallbackResult:
    """Try the local tier; any failure building or invoking it escalates to frontier.

    Absorbs kmon sprint 03's rule: the local tier being down must not kill the
    result. `local` and `frontier` are zero-arg factories returning
    (llm, model_id) so that a dead endpoint fails inside the try. Frontier-tier
    failures propagate — there is nothing left to fall back to. Escalation
    *routing* (whether a verified-bad result may re-escalate, whether optional
    work is skipped when local is down) stays with the consumer.
    """
    try:
        llm, model_id = local()
        content = llm.invoke(messages).content
        return FallbackResult(content=content, model_used=model_id, escalated=False)
    except Exception as exc:  # noqa: BLE001 — any local-tier failure means escalate
        if on_fallback is not None:
            on_fallback(exc)
    llm, model_id = frontier()
    content = llm.invoke(messages).content
    return FallbackResult(content=content, model_used=model_id, escalated=True)

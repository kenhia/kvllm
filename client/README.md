# kvllm-client

The shared LLM client for homelab services that talk to kvllm's
OpenAI-compatible `/v1` — extracted from kagent, kmon, and klams-mind
(homelab-ai WI 274) before a fourth copy appeared.

This is a **separate distribution** from the `kvllm` server package on
purpose: the server depends on vLLM (GPU-only, python `<3.13`); consumers
must not inherit that.

Since 0.2.0 (kvllm sprint 20, WI-1983) the defaults assume a **reasoning
model** as the resident — Qwen3.8-27B since 2026-09-08 — and every consumer
inherits them on its next `uv lock`.

## Install

```toml
dependencies = [
    "kvllm-client @ git+ssh://git@github.com/kenhia/kvllm.git#subdirectory=client",
]
```

Add the `[anthropic]` extra if you use the escalation tier
(`kvllm-client[anthropic] @ ...`).

## API

- `local_model(base_url, *, model="auto", temperature=None, max_tokens=8192,
  chat_template_kwargs=None, streaming=False, timeout=10, request_timeout=None,
  api_key="EMPTY")` → `(KvllmChatOpenAI, model_id)`. `"auto"` asks
  `/v1/models` what is being served — kvllm serves exactly one model and the
  registry key IS the model name, so consumers follow automatically when the
  served model switches. `timeout` bounds discovery; `request_timeout` bounds
  each completion.
  - **`temperature=None`** sends no sampling parameters, so the served model's
    own `generation_config` applies (Qwen3.8: T=1.0, top-p 0.95, top-k 20).
    Greedy decoding in thinking mode looped verbatim until the budget once in
    sprint 19; pass `0.0` only where determinism is worth that.
  - **`max_tokens=8192`** is the answer budget, *reasoning included* (sent as
    `max_completion_tokens`, which vLLM honours):
    cross-referencing at `medium` effort used up to 6,095 output tokens and one
    draw in nine wanted more. `None` removes the budget. vLLM rejects a request
    whose prompt plus budget exceeds the served window — size prompts from
    `served_model_info()`.
  - **`chat_template_kwargs`** become the model's default template overrides:
    `{"reasoning_effort": "medium"}` on Qwen3.8 (`low` / `medium` / `xhigh`;
    `enable_thinking=False` turns thinking off), `{"enable_thinking": True}`
    on gemma-4. They ride in `extra_body`, where vLLM reads them.
- `template_kwargs(**kw)` — the per-call form:
  `llm.invoke(messages, **template_kwargs(reasoning_effort="xhigh"))`. A
  per-call `extra_body` *replaces* the model-level one for that call, so name
  every key the call needs.
- `served_model_info(base_url)` / `aserved_model_info` →
  `ServedModel(id, max_model_len)`. vLLM reports the served window on the
  model card; read context, edit and tool-output budgets from it instead of
  hard-coding numbers sized for the previous resident (122,880 for Qwen3.8,
  32,768 for gemma as re-served).
- `frontier_model(model="claude-haiku-4-5", *, temperature, max_tokens)`
  → `(ChatAnthropic, model_id)`. Lazy-imports langchain-anthropic.
- `discover_model` / `adiscover_model` — sync/async `/v1/models` lookup, id
  only; `resolve_model` / `aresolve_model` — same, but pass non-`"auto"`
  names through untouched.
- `invoke_with_fallback(messages, *, local, frontier, on_fallback,
  empty_retries=1)` — try the local tier, escalate to frontier on any local
  failure (kmon sprint 03: a dead local tier must not kill the result).
  **An empty answer is a local failure**: a reasoning model can end a turn
  with thousands of tokens of reasoning and empty content
  (`finish_reason: stop`; seen once at 68k context). It is retried once, then
  escalated with `EmptyAnswerError` as the cause — `on_fallback` receives it,
  with `.reasoning` from the last attempt for the log. A reply with a tool
  call and no text is not empty. Returns
  `FallbackResult(content, model_used, escalated, reasoning)`.
- `reasoning_of(message)` / `is_empty_answer(message)` — the two predicates
  above, for callers that invoke the llm themselves.

Env-var policy: none — consumers own their env vars and pass explicit args.

## The reasoning field, and prefix caching

`KvllmChatOpenAI` is `ChatOpenAI` plus one hook: langchain-openai targets the
official OpenAI schema and drops provider fields from the assistant message
(its own docstring says to subclass for vLLM). On **vLLM 0.28.0 the reasoning
parser's output is `message.reasoning`** — not `reasoning_content`, which older
releases used; both are accepted and land in
`message.additional_kwargs["reasoning"]`, where `reasoning_of` reads it.
Non-streaming only.

vLLM's prefix caching (on by default in 0.28.0) makes **re-sending a whole,
growing transcript cheap** — the shared prefix is served from cache — while
**editing earlier turns defeats it**: every token after the first changed one
is recomputed. Append; do not rewrite. At Qwen3.8's full window the cache has
no headroom (1.0× concurrency at 122,880), so two concurrent long requests
evict each other's prefixes — a caller-side design constraint, not a kvllm
defect.

## Tests

`just client-test` from the repo root (or `uv run --group dev pytest` here).
Fakes only — no GPU, no network, no vLLM.

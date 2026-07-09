# kvllm-client

The shared LLM client for homelab services that talk to kvllm's
OpenAI-compatible `/v1` — extracted from kagent, kmon, and klams-mind
(homelab-ai WI 274) before a fourth copy appeared.

This is a **separate distribution** from the `kvllm` server package on
purpose: the server depends on vLLM (GPU-only, python `<3.13`); consumers
must not inherit that.

## Install

```toml
dependencies = [
    "kvllm-client @ git+ssh://git@github.com/kenhia/kvllm.git#subdirectory=client",
]
```

Add the `[anthropic]` extra if you use the escalation tier
(`kvllm-client[anthropic] @ ...`).

## API

- `local_model(base_url, *, model="auto", temperature, streaming, api_key)`
  → `(ChatOpenAI, model_id)`. `"auto"` asks `/v1/models` what is being served
  — kvllm serves exactly one model and the registry key IS the model name, so
  consumers follow automatically when the served model switches.
- `frontier_model(model="claude-haiku-4-5", *, temperature, max_tokens)`
  → `(ChatAnthropic, model_id)`. Lazy-imports langchain-anthropic.
- `discover_model` / `adiscover_model` — sync/async `/v1/models` lookup;
  `resolve_model` / `aresolve_model` — same, but pass non-`"auto"` names
  through untouched.
- `invoke_with_fallback(messages, *, local, frontier, on_fallback)` — try the
  local tier, escalate to frontier on any local failure (kmon sprint 03: a
  dead local tier must not kill the result). Returns
  `FallbackResult(content, model_used, escalated)`.

Env-var policy: none — consumers own their env vars and pass explicit args.

## Tests

`just client-test` from the repo root (or `uv run --group dev pytest` here).
Fakes only — no GPU, no network, no vLLM.

# Sprint 13 — client lib (kvllm-client)

Slice 1 of the WS5 extraction (homelab-ai WI 274, proposal korg:298): the
ChatOpenAI-at-kvllm + `/v1/models` auto-discovery + ChatAnthropic-escalation
pattern existed in kagent, kmon, and klams-mind, and WS1 was about to become
the fourth copy. This sprint gives the pattern one home; follow-up slices
convert the three consumers (kmon → kagent → klams-mind), one repo per slice,
with the proposal staying active until all land.

## What shipped

`client/` — a **separate distribution** `kvllm-client` (import `kvllm_client`),
NOT part of the root `kvllm` package. That split is the load-bearing packaging
decision: the server package hard-depends on vLLM (GPU-only, python `<3.13`),
and consumers must not inherit that. The client's own venv resolved on
CPython 3.13 during `just check`, which is the proof. Consumers install:

```toml
"kvllm-client @ git+ssh://git@github.com/kenhia/kvllm.git#subdirectory=client"
```

API (surveyed from all three copies before designing — see WI 274 comments):

- `local_model()` → `(ChatOpenAI, model_id)` — kagent/kmon's constructor, with
  kagent's `streaming` flag and klams-mind's `"auto"` sentinel.
- `discover_model` / `adiscover_model`, `resolve_model` / `aresolve_model` —
  sync discovery from kagent/kmon; async + injectable `httpx.AsyncClient` from
  klams-mind. Hardened slightly: `raise_for_status()` + empty-list check.
- `frontier_model()` → `(ChatAnthropic, model_id)` — kmon's escalation tier.
  langchain-anthropic is the `[anthropic]` extra, lazy-imported, because
  klams-mind never escalates.
- `invoke_with_fallback(messages, *, local, frontier, on_fallback)` — absorbs
  kmon sprint 03's local-down → frontier fallback at the invoke level. The
  *routing* rules (dig skips investigation, no re-escalation of an escalated
  report) stay in kmon's graph — they're consumer policy, not client behavior.

Env-var policy: the lib reads no env vars. `KMON_LOCAL_BASE_URL`,
`KAGENT_BASE_URL` etc. stay in their consumers.

## Tests / gate

`client/tests/test_client.py` (14 tests, fakes only — no GPU, no network); the
fallback fakes deliberately mirror kmon's `tests/test_controller.py`. New
`just client-test` recipe, now part of `just check`.

## Not in this slice

Consumer conversions. kmon is next (slice 2): `_local_model`/`_frontier_model`
become thin wrappers over `kvllm_client` — kept as module-level names so kmon's
monkeypatching tests pass unchanged, and zero prompt/policy changes.

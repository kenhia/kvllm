# Sprint 20 — Make Qwen3.8 resident: registry as interviewed, gemma re-served, kvllm-client for a reasoning model, deploy

**Proposal:** korg:1984 (slice 1 of program korg:1994) · **Work items:** #1983 (kvllm-client
defaults for a reasoning model), #1982 (registry as interviewed, gemma re-served, both rows
re-scored under their served configs, switched and deployed). **Branch:**
`20-qwen3-8-resident` · **Driving model:** Claude Fable 5.1, as a headless karc leg on kai
under an overseer session on cleo.

## Goal

Ken decided on 2026-09-08 (WI-1973, sprint 19's recommendation): Qwen3.8-27B-NVFP4 is the
resident-agent model. This sprint makes the box match the decision, and it goes first in
the program because every caller change (kyac, kmon) is verified against the model kai
serves. Nothing here changes a ranked condition — the new board rows are new dated rows
under the same suite versions.

## Premise check at sprint start (2026-09-09 00:30 UTC, kai)

- **#1983 holds to the line.** `client/src/kvllm_client/__init__.py` had
  `local_model(temperature=0.0)`, no `max_tokens` on the local tier, no way to pass
  `chat_template_kwargs`, `discover_model()` returning only the id, and
  `invoke_with_fallback` returning `.content` as-is. Five gemma-era defaults, all still
  there.
- **#1982 holds.** `kvllm/registry.py` had no GPU-fraction field (`KVLLM_GPU_UTIL` or 0.90,
  nothing per entry); the Qwen entry was 131,072 / eager / no head; gemma was awq / 16,384
  with neither fp8 KV nor `enable_thinking`; `deploy/kvllm.env` said `gemma-4-31b-it-awq`
  at 0.90. `just service-switch` and `just eval-repeat` exist as the item describes.
- **Environment:** `kvllm.service` active serving `gemma-4-31b-it-awq` (16,384) at
  30,846 MiB; `just` and `uv` on the leg PATH; the kmon timer fires 04:01 PDT (11:01 UTC),
  ten and a half hours out — the GPU window is the leg's.

## Order

Client first (no GPU), then the registry, then the two N=3 re-scores under
`KVLLM_EVAL_DATE=2026-09-09` (the repeat runner refuses sprint 19's `2026-09-08` keys, by
design), then `just service-switch qwen3.8-27b-nvfp4`, the live client calls, docs.
`deploy-kvllm` runs from merged `main` at ship time, as `.sprint-deploy` declares.

## kvllm-client 0.2.0 (#1983)

Pure Python, fakes only, no GPU; 31 client tests (14 before). Version 0.1.0 → 0.2.0 so a
consumer's `uv lock` shows the pickup. What changed in `client/src/kvllm_client/__init__.py`
and why — each row is a sprint-19 finding, not a preference:

| gemma-era default | now | because |
|---|---|---|
| `local_model(temperature=0.0)` | `temperature=None` → nothing sent; the served `generation_config` applies (Qwen3.8: T=1.0, top-p 0.95, top-k 20) | greedy thinking looped verbatim until the budget once in a multi-turn loop |
| no `max_tokens` on the local tier | `max_tokens=8192` (on the wire as `max_completion_tokens`, which vLLM honours); `None` removes it | reasoning counts toward the budget; cross-referencing at `medium` used up to 6,095 and one draw in nine wanted more |
| no way to pass template kwargs | `chat_template_kwargs=` on the model → `extra_body.chat_template_kwargs`; `template_kwargs(**kw)` for one call | `reasoning_effort` (Qwen) and `enable_thinking` (gemma) are per-request overrides |
| `discover_model()` → id only | `served_model_info()` / `aserved_model_info()` → `ServedModel(id, max_model_len)` from the vLLM model card | kyac's 16,384 / 11,468 / 10,000 were sized for gemma by hand |
| `invoke_with_fallback` passes `.content` through | empty text with no tool call = local failure: retried once (`empty_retries`), then `EmptyAnswerError(model_id, reasoning, attempts)` → `on_fallback` → frontier; `FallbackResult.reasoning` | 6k tokens of reasoning and empty content at 68k, `finish_reason: stop` |

Two things the work item did not spell out, decided here:

- **`KvllmChatOpenAI`**, a `ChatOpenAI` subclass with one hook. langchain-openai 1.3.4
  targets the official OpenAI schema and its `_convert_dict_to_message` drops every
  provider field from the assistant message — the module docstring says to subclass
  for vLLM, so that is what this is. `_create_chat_result` copies `message.reasoning`
  (vLLM 0.28.0's name; `reasoning_content` accepted for older releases) into
  `additional_kwargs["reasoning"]`; `reasoning_of()` reads it. Non-streaming only:
  the delta path has no such field to copy. Without this, `FallbackResult.reasoning`
  could not exist.
- **`request_timeout`** on `local_model`, from the program handoff's contract rather
  than the item: `timeout` was already taken by discovery, and a reasoning model at an
  8k budget can legitimately run for minutes. Passed to ChatOpenAI as `timeout` (its
  alias); None leaves the SDK's default.

The escalation *cause* is the exception `on_fallback` receives (an `EmptyAnswerError`
carries the last attempt's reasoning, for kmon WI-1948's log); `FallbackResult.reasoning`
describes the `content` that was returned, whichever tier produced it. `ServedModel` is a
frozen dataclass, not the `{id, max_model_len}` dict the handoff sketched — attribute
access, like `FallbackResult`; flagged for the overseer. A reply with a tool call and no
text is not empty. The README documents the field name and the prefix-caching rule
(append, never rewrite; no headroom at the full window).

Verified by fakes here; the two live calls (Qwen3.8 resident, gemma re-served) are below.

## Registry (#1982 steps 1–2)

`gpu_memory_utilization` is a new opt-in entry field, emitted only when set, and
`effective_gpu_util(entry, gpu_util)` fixes the precedence: **entry > `KVLLM_GPU_UTIL` >
0.90**. The reason it is a model property and not a deployment knob: the Qwen
configuration sprint 19 interviewed only exists at 0.95, and an entry that is only
self-consistent under one `deploy/kvllm.env` is not a registry entry. `registry show`
prints the field and the serve command carries the fraction, so `deploy-kvllm`'s
argv-vs-registry diff covers it. `deploy/kvllm.env` stays at 0.90 (the overseer's
instruction; untouched). Four registry tests.

One consequence caught by reading the callers: `interview.serve` passed its `--gpu-util`
straight to `build_serve_argv(gpu_util=...)`, which the entry now shadows — so on the
Qwen entry an envelope override would have been silently ignored. `apply_overrides`
takes `gpu_util` and writes it onto the entry, where the registry reads first; the
recorded `serves.jsonl` row reports the effective fraction. One test.

The two entries, as the work item's table has them (comments in `models.toml` carry the
measurements and the fallback):

- `qwen3.8-27b-nvfp4`: `speculative_config = { method = "mtp", num_speculative_tokens = 3 }`,
  `max_model_len = 122880`, `gpu_memory_utilization = 0.95`, `enforce_eager` kept (it was
  on in the interviewed serve), `kv_cache_dtype = "fp8"` and `reasoning_effort = "medium"`
  unchanged. `est_vram_gb` 28 → 30. Notes rewritten: the 131,072/72,000 ceiling text
  described the pre-head entry.
- `gemma-4-31b-it-awq`: `kv_cache_dtype = "fp8"`, `max_model_len = 32768`,
  `chat_template_kwargs = { enable_thinking = true }`; the NEVER-FP8-weights note kept and
  sharpened (weights, not KV). `est_vram_gb` 25 → 27.

`just check`: ruff clean, 257 unit tests, 31 client tests. Committed as `6a56f99` before the
re-scores so the eval's own writes to `models.toml` (verdict, date) land separately.

## Docs (#1982 step 5)

Written while the re-scores ran, so they name the configuration and point at the board
for the numbers rather than freezing a figure the runs might move:

- `docs/findings/local-model-guidance-2026-07.md` — a second superseding note (2026-09-09):
  the resident role is no longer decided by the board; Qwen3.8 is the resident as
  interviewed, the "Autonomous-ish generalist → gemma" row and the headline's gemma ①
  describe the board and not the RA, gemma re-served as its best self is the second
  opinion and the vision candidate, `kvllm-client` ≥ 0.2.0's defaults. The controller
  readout, escalation triggers and cost anchors stand.
- `docs/findings/ra-interview-2026-09.md` — a status block: decision taken 2026-09-08,
  served since sprint 20, and the sentence program korg:1480's aim asks for (which model
  serves which role, `models.toml` matching).
- `docs/findings/README.md`, `README.md` (quick start names the resident), `CLAUDE.md`
  (orientation line under the interview finding), `docs/03-deployment.md` and
  `deploy/kvllm.env.example` (the new field's precedence over `KVLLM_GPU_UTIL`).
- `models.toml` notes on both entries (above).


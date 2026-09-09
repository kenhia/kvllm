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

## The environment lied: the interviewed configuration needs `nvcc` on PATH

The first Qwen re-score came up healthy (4.84 GiB KV pool, 124,215 KV tokens, 1.01× at
122,880, 39 s engine init — the interview's numbers to the digit), answered the speed
probe's first request, and **died on the second** with `EngineDeadError`. The engine's
own trace ends in `flashinfer_xqa_batch_decode_with_kv_cache` → `RuntimeError: FlashInfer
backend is not available` — on a 4-token step (one target token plus three draft tokens:
the head's verify step). flashinfer-python 0.6.16.post3 *is* installed, so that message is
not about the package.

It is about `nvcc`. `vllm.utils.flashinfer.has_flashinfer()` returns False when `nvcc` is
not findable and no cubin package is installed, and every FlashInfer kernel vLLM imports
lazily is then replaced by a stub that raises **at call time, not at startup**. Measured
in this leg's environment: `has_flashinfer() == False`, `shutil.which("nvcc") is None`;
with `/usr/local/cuda/bin` prepended, True. Ken's `.bashrc` puts that directory on PATH,
which is why sprint 19's interview — the same argv, the same backend line
(`FLASHINFER`, `decode_backend=xqa`), sixteen successful completions — never saw it. The
systemd user manager's PATH does not have it either (`systemctl --user show-environment`),
so **the switch as planned would have passed `deploy-kvllm`'s health check and failed on
kmon's 04:01 request.** The handoff's failure mode 4, in the harness rather than the
model: the transcript pointed at a kernel bug; the environment was the bug.

Fix: `kvllm.registry.serve_env(key, entry)` — the CUDA toolkit prepended to the serve's
PATH when `nvcc` is missing, and a **refused start** (with the reason) for a speculative
serve that still cannot find it, because a serve that dies after the health check is the
worse failure. Every serve path goes through it: the unit's `registry serve` (`execvpe`),
`evalctl.serving`, `interview.serve`. Five tests. The unit template is unchanged — the
fix is in the code the unit runs, not in the unit — so `deploy-kvllm` at ship is a
restart on merged code, not a re-render.

Cost: the Qwen re-score restarts after gemma's. The runner had to be stopped by hand
(`SIGINT` did not reach it inside Inspect's sandbox retries; `SIGTERM` did), and my
back-to-back script then let the gemma stage begin while the restored unit was still
loading — the runner saw `active` (systemd's `Type=exec` sense: exec'd, not healthy),
stopped it as designed, and served gemma standalone; it restores the unit at its end.
Orderly, but a lesson for the next leg: **do not chain two managed repeats with a fixed
sleep; wait for the restored unit to answer `/v1/models` first.**

## Re-score: gemma-4-31b-it-awq at fp8 KV / 32,768 / thinking on (#1982 step 3)

`KVLLM_EVAL_DATE=2026-09-09 just eval-repeat gemma-4-31b-it-awq --n 3 --publish median`,
00:48–01:32 UTC, standalone serves of the registry entry: 73.9 tok/s, 80 s cold start,
30,826 MiB, context probe at 75% of 32k ok, 68,160 KV tokens at 2.08× — sprint 19's
`fp8-32k-b` envelope row to the token. Zero failed requests over three runs.

| suite | 2026-09-08 (fp16 KV, 16k, thinking off) | **2026-09-09 (served config)** | band |
|---|---|---|---|
| tools | 100% | **100%** | 0.000 (identical) |
| code | 100% | **99%** (0.93–1.00) | 0.070 |
| agentic | 74% (0.63–0.77) | **33%** (0.33–0.50) | 0.170 |
| judged | 77% (flat) | **75%** (0.68–0.85) | 0.170 |
| vision | 100% | **97%** (0.97–1.00) | 0.030 |
| composite / rank | ≈ 0.92, rank 2, worth trying | **≈ 0.83, rank 5, ⚠️ has issues** | |

Published: run 1 (the median by mean pass rate). The board's `assisted` 87% for gemma
still carries forward from 2026-09-07 (thinking off) — a weight-0 labeled condition that
was not part of this re-score.

**The agentic drop is the harness shape, audited before reading it as the model.** In all
three runs the same five investigation-heavy cases — `a2-disk-growth`, `a3-oom-chain`,
`a4-cron-typo`, `a7-port-conflict`, `a9-sprint-plan` — end `CUT OFF BY MESSAGE LIMIT
mid-investigation` at 19 tool calls with no `submit`; with thinking off, run 2 of
2026-09-08 submitted `a4`, `a7` and `a9` at 16, 13 and 2 calls. Thinking on makes gemma
investigate longer than the ranked suite's frozen turn cap allows (`controller-vs-model`'s
delivery-limited pattern), and the frozen cap is the ranked condition, so the row says what
it should: **as served, gemma is delivery-limited on the raw agentic suite.** `judged` moved
inside its band (`professional-rewrite` swung 0.2 / 1.0 / 0.0 across runs — the noisy
case). `a8-honesty` fabricated once under the cut-off (run 1) and was clean twice. Nothing
here was tuned; the ranked conditions are unchanged, and the verdict flip to `has issues`
is `composite < floor` under them. The sprint-19 interview measured the opposite face of
the same coin — thinking on made gemma's arithmetic exact and its aggregation reliable on
bounded probes — and both are true. Follow-up worth its five minutes: re-measure gemma's
`assisted` condition under this configuration, so the board's gemma row is one
configuration end to end.

## Live call 1 of 2 — kvllm-client 0.2.0 against the re-served gemma (#1983)

`cd client && uv run python ../.scratch/sprint20-live-call.py` against the restored unit
(01:33 UTC):

- `served_model_info()` → `ServedModel(id='gemma-4-31b-it-awq', max_model_len=32768)`.
- Defaults on the wire: `{"stream": false, "max_completion_tokens": 8192}` — no
  temperature, no `extra_body`.
- `17 * 23` → `'391'` in 1.8 s; `usage.output_token_details.reasoning: 122`; the
  `reasoning` field came through the subclass (236 chars, the gemma4 parser's block);
  `finish_reason: stop`.
- `template_kwargs(enable_thinking=False)` per call → `'391'` in 0.1 s, 4 output tokens,
  `reasoning=None`.
- `invoke_with_fallback` with a frontier factory that raises → answered locally,
  `escalated=False`, reasoning attached.

## Re-score: qwen3.8-27b-nvfp4 at MTP ×3 / 122,880 / 0.95 (#1982 step 3, second attempt)

`KVLLM_EVAL_DATE=2026-09-09 just eval-repeat qwen3.8-27b-nvfp4 --n 3 --publish median`
under `serve_env`, 01:33–02:15 UTC. Every serve: 4.80 GiB KV pool, **122,880 KV tokens at
1.00×**, `decode_backend=xqa`, context probe at 75% of the window ok; **59.5 / 60.8 / 60.2
tok/s** (29.3 before the head), TTFT 0.1 s, **50 s cold start**, **30,972 MiB**. 247
requests across three serves, zero failed, zero engine deaths — the FlashInfer path that
killed the first attempt is the path every decode step took.

| suite | 2026-09-08 (no head, 131k, 0.90) | **2026-09-09 (served config)** | band |
|---|---|---|---|
| tools | 100% | **100%** | 0.000 (identical) |
| code | 100% (0.93–1.00) | **99%** (0.99–1.00) | 0.010 |
| agentic | 72% (0.66–0.94) | **66%** (0.66–0.83) | 0.170 |
| judged | 95% (0.92–0.95) | **97%** (identical ×3) | 0.000 |
| vision | 93% | **97%** (0.93–0.97) | 0.040 |
| tok/s → speed factor | 29.3 → 0.82 | **60.8 → 1.00** | |
| composite / rank | ≈ 0.76, rank 10 | **② 0.92, rank 2** | |

Published: run 2 (median). **Quality under the draft head is the same quality**: every
suite reproduces the headless row inside its own band, `judged` tightened to identical,
and the composite move is entirely the speed factor — the head took Qwen from
speed-limited to full marks. The agentic failures are the suite's own: `a5-wi-triage` and
`a8-honesty` carry the judge's fabrication flag in the same runs, the same way, as they did
on 2026-09-08 without the head (a5 in two of three runs then, three of three now; a8 two of
three both times), so the head is not the variable. Sprint 19's `agentic` band of 0.28 was
the widest on the board; this one is 0.17.

## Switch and verify (#1982 step 4)

02:15:53 UTC, `just service-switch qwen3.8-27b-nvfp4` (the recipe's `sed` on
`deploy/kvllm.env` — Ken's decision on WI-1973 is the authorisation, and WI-1982 records
it) from this checkout, then the checks `deploy-kvllm` will repeat from merged `main`:

- `/v1/models`: `qwen3.8-27b-nvfp4`, `max_model_len 122880`; `KVLLM_MODEL_KEY` agrees.
- `ActiveState=active`, `NRestarts=0`; healthy **51 s** after the restart (journal:
  `Started` 19:15:53 PDT → `Application startup complete` 19:16:43).
- **Idle VRAM 30,972 MiB** (the interview measured 31,112; the board's band for this
  configuration), 0% utilisation at idle.
- The running `vllm serve` argv is **byte-identical** to `registry show`.
- The engine process's own `PATH` begins `/usr/local/cuda/bin` — `serve_env` on the unit.
- Engine report: 4.8 GiB KV, 122,880 tokens at 1.00×, `decode_backend=xqa`.
- `kvllm-helper.service` active.

`deploy/kvllm.env` otherwise untouched: `KVLLM_GPU_UTIL=0.90` stays (the entry's 0.95
wins). The fallback if 0.95 misbehaves under the first day of real load is 0.90 / 65,536
with the head — half the window, still 2× decode — and is the leg's call to record, not
Ken's.

## Live call 2 of 2 — kvllm-client 0.2.0 against the resident Qwen3.8 (#1983)

02:17 UTC, the same script: `ServedModel(id='qwen3.8-27b-nvfp4', max_model_len=122880)`;
`17 * 23` → `'\n\n391'` in 0.8 s with 36 reasoning tokens surfaced as `reasoning`
(`"17 * 23 = 17 * 20 + 17 * 3 = 340 + 51 = 391"`); `template_kwargs(enable_thinking=False)`
→ `'391'` in 0.2 s, 4 output tokens, no reasoning; fallback stayed local. Both live calls
WI-1983 asked for are done, on the unit, through the 0.2.0 defaults. (Qwen's leading
`\n\n` is the template's; callers `strip()` as they always did.)

## Program korg:1480

Its aim — *a dated finding names which local model serves which role and `models.toml`
matches it* — is met: `docs/findings/ra-interview-2026-09.md` (status block, 2026-09-09)
names Qwen3.8 as the resident and gemma as the second opinion, and `models.toml` serves
exactly that. Closing it, and the comment on korg:1479, are the overseer's post-ship steps.

## Not done, on purpose

- **The `assisted` column** (weight 0, labeled) carries forward from 2026-09-07 for both
  rows — thinking off for gemma, no head for Qwen — as sprint 19 also left it. Twenty
  minutes of card cycling would make each row one configuration end to end; a follow-up,
  not this leg's night.
- **gemma's raw agentic under thinking on** is a measurement, not a defect to fix here:
  the ranked turn cap is frozen, and the `assisted` condition exists for exactly this.
- **The frontier baseline on the new harness** (~$3, Ken's go) — unchanged standing offer.

## Gate

`just check` green: ruff clean, 262 unit tests, 31 client tests. Serve-path files changed
this sprint: `kvllm/registry.py`, `models.toml` (and `kvllm/evalctl.py`,
`interview/serve.py` off the unit's path), so `deploy-kvllm` at ship is a real restart on
merged `main`; it should find the same argv it finds now. The box is serving the resident
from this branch's checkout, which is byte-identical on the serve path to what `main` will
carry after the merge.

## Deployed

**2026-09-09 02:27 UTC (2026-09-08 19:27 PDT), kai, from merged `main` `b147a62`**
(`deploy-kvllm`, sprint-ship Phase 7, on the karc ship turn after the overseer's clearance,
comment 1453 / handoff korg:2001).

Serve-path files since the sprint-19 stamp `0fd23aa`: `kvllm/registry.py`, `models.toml`,
`deploy/kvllm.env.example` (a comment) — a real restart. `deploy/install.sh` re-rendered
both units (byte-identical to the ones installed) and daemon-reloaded. No eval in flight.

- **Drain:** 2 MiB / 0 compute processes immediately on stop.
- **Restart:** `/v1/models` answered after 51 s; `kvllm-helper.service` restarted.
- **Verified:** served id `qwen3.8-27b-nvfp4` equals `KVLLM_MODEL_KEY`, `max_model_len
  122880`; `NRestarts=0`; 30,972 MiB (this configuration's band); the running `vllm serve`
  argv is byte-identical to `registry show`; the API server process's PATH begins
  `/usr/local/cuda/bin` (`serve_env` on the unit, from committed code); 122,880 KV tokens
  at 1.00×, engine init 6.3 s on a warm cache.
- **Smoke:** answered `OK`, `finish_reason: stop`, 18 reasoning tokens.
- Stamped `b147a62`.

The box serves the resident Ken decided on 2026-09-08, from committed `main`, in the
configuration sprint 19 interviewed. The first real-load test of GPU 0.95 is kmon's 04:01
PDT run; program korg:1994's standing fallback is 0.90 / 65,536 with the head.

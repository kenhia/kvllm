# Sprint 1 — Core setup (vLLM serving + tools + LangChain)

_2026-06-30 on `kai` (RTX 5090). See [`../sprints/planning/00-kickoff.md`](../sprints/planning/00-kickoff.md). **Shipped.**_

## Goal

Retire the first risk — **a clean vLLM install on sm_120 (consumer Blackwell)** — and get vLLM
serving one model on the 5090: expose an OpenAI-compatible `/v1`, verify **tool calling**, and reach
it from **LangChain**.

**Exit:** `chat.invoke(...)` and `bind_tools(...)` work against a locally-served model. ✅
**Stretch (Ken asked):** serve a model not in the TRT-LLM registry — a small **DeepSeek** distill. ✅

## What shipped

- **vLLM 0.24.0** installed via `uv add vllm` → **torch 2.11.0+cu130**. GPU recognized at compute
  capability **(12, 0) = sm_120**, `torch.cuda.is_available()` True. No Docker needed.
- **Serving:** `vllm serve Qwen/Qwen2.5-7B-Instruct --enable-auto-tool-choice --tool-call-parser
  hermes` on `:8000`. Engine init ~77 s cold (one-time torch.compile + CUDA-graph capture), <2 s to
  answer `/v1/models` after. Picks **FlashAttention v2** automatically (FA3 unsupported on sm_120 —
  no flag needed).
- **Tool calling (raw OpenAI client):** `get_weather("Paris")` round-trips — model emits a
  well-formed call, consumes the tool result, answers _"21 degrees Celsius"_.
  [`tests/smoke_tools.py`](../tests/smoke_tools.py) → PASS.
- **LangChain reach (exit criterion):** `ChatOpenAI(base_url=.../v1, api_key="EMPTY")` —
  `invoke()` returns text; `bind_tools([add]).invoke(...)` produces `add(a=17, b=25)`.
  [`tests/smoke_langchain.py`](../tests/smoke_langchain.py) → PASS.
- **Stretch — DeepSeek:** `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` (not in the TRT registry)
  serves with `--reasoning-parser deepseek_r1` and computes `12 × 8 = 96` correctly.
  [`tests/smoke_deepseek.py`](../tests/smoke_deepseek.py) → PASS.
- **Ergonomics:** [`justfile`](../justfile) (`serve`, `serve-deepseek`, `healthy`, `models`,
  `smoke`, `lint`), `ruff` wired into [`pyproject.toml`](../pyproject.toml) (`dev` group), test
  deps in the `test` group.

## Decisions & discoveries

- **`uv`, not Docker.** The kickoff hedged toward the `vllm/vllm-openai` image for a clean sm_120
  match, but `uv add vllm` pulled a cu130 torch that drives the 5090 directly — simpler, and it
  honors Ken's `uv`/`ruff` preference. Docker stays the fallback if a future wheel regresses.
- **⚠️ The one real snag — `Python.h` missing.** First serve crashed: vLLM/Triton JIT-compiles a
  tiny CUDA helper (`cuda_utils.c`) at startup via `gcc`, which needs Python dev headers. The venv
  was built on **system `/usr/bin/python3.12`**, which ships no headers (`/usr/include/python3.12/
  Python.h` absent — no `python3.12-dev`). **Fix (no sudo, stays uv-native):** `uv python install
  3.12` (managed CPython 3.12.13 — python-build-standalone *includes* headers) → rebuilt the venv
  with `uv venv --python-preference only-managed --python 3.12` → `uv sync`. Headers present, serve
  clean. _Pin the managed interpreter so this doesn't regress (see follow-ups)._
- **One model per process.** vLLM holds a single model; switching = stop/start (`just serve` ↔
  `just serve-deepseek`). This is the model-switching story the kickoff's deferred "helper app"
  would wrap.
- **DeepSeek tool calling is weak (as expected).** With tools bound, the R1 distill burned its
  token budget reasoning and emitted no call (`finish_reason=length`). Fine for the stretch (goal
  was "serve a new model"); for agentic use prefer Qwen2.5-Instruct. Tool calling on R1 distills is
  a Wed-research item.

## Outcomes (exit criteria)

| Criterion | Result |
|---|---|
| Clean vLLM install on sm_120 | ✅ vLLM 0.24.0 / torch 2.11.0+cu130, cap (12,0) |
| Serve a model, expose `/v1` | ✅ Qwen2.5-7B-Instruct on `:8000` |
| Tool calling works | ✅ raw OpenAI client round-trip |
| `chat.invoke()` + `bind_tools()` from LangChain | ✅ both pass |
| Stretch: new model (DeepSeek distill) | ✅ R1-Distill-Qwen-7B serves + reasons |

## Follow-ups

- ~~Pin the managed Python so a fresh `uv venv` can't grab headerless system 3.12 again.~~ **Done:**
  `[tool.uv] python-preference = "only-managed"` in `pyproject.toml`; verified a fresh `uv venv`
  resolves to managed CPython 3.12.13.
- **korg project not created.** No `create_project` MCP tool, and the korg API server (`POST
  /api/projects`) isn't running — so the `kvllm` project + Sprint 1 WIs couldn't be made from here.
  Needs Ken (web UI or start the korg server); then add WIs. (explore=15, trt-llm-langchain=16.)
- **Streaming** tool turns deferred (research §3 fragility) — non-streaming first, as planned.
- **Sprint 2:** model registry + serve recipes + quant notes (AWQ/GPTQ/FP8 that fit 32 GB);
  document the `/v1` contract vs `trt-llm-langchain/docs/03-backend-contract.md`.

# Sprint 2 — Serving ergonomics (registry + recipes + quant notes + /v1 contract)

_Started 2026-06-30 on `kai` (RTX 5090). korg #97. Branch `02-serving-ergonomics`._
_Builds on [Sprint 1](sprint-01-core-setup.md). See [`../sprints/planning/00-kickoff.md`](../sprints/planning/00-kickoff.md)._

## Goal

Turn the one-off `just serve <hardcoded model>` from Sprint 1 into a **model registry + serve
recipes** so trying a new model is a one-liner, and **document the contract** kvllm satisfies so the
LangChain client (and any OpenAI client) can depend on it.

## Plan

1. **`models.toml`** — a vLLM-shaped registry: `key → hf_repo`, tool/reasoning parser,
   `max_model_len`, dtype/quant, capabilities, est. VRAM, notes. Leaner than the TRT registry (no
   per-model engine-build fields — vLLM loads HF weights directly).
2. **Registry loader + CLI** (`kvllm/registry.py`): `list`, `show <key>`, and `serve <key>` that
   resolves an entry into the `vllm serve` argv (sets `--served-model-name <key>` so the registry
   key is the `model=` the client passes — matches the backend contract).
3. **`just` recipes**: `just serve <key>`, `just models-list`, `just models-show <key>`.
4. **Quant notes** (`docs/02-quantization.md`): AWQ / GPTQ / FP8 on a 32 GB 5090 — what fits, what
   sm_120 supports, rough VRAM math.
5. **Backend contract** (`docs/01-backend-contract.md`): the OpenAI `/v1` chat surface kvllm
   guarantees — mirrors `trt-llm-langchain/docs/03-backend-contract.md` **minus** the KServe control
   surface (vLLM is one-model-per-process; switching = stop/start, the Sprint 3 systemd story).

## What shipped

- **[`models.toml`](../models.toml)** — 5 seed models (Qwen2.5-7B-Instruct ✓tested, Qwen2.5-Coder-7B,
  DeepSeek-R1-Distill-Qwen-7B ✓tested, Llama-3.1-8B gated, Qwen2.5-14B-AWQ). vLLM-shaped fields:
  `hf_repo`, tool/reasoning parser, `max_model_len`, `quantization`, `gated`, `est_vram_gb`,
  `capabilities`, `tested`, `notes`.
- **[`kvllm/registry.py`](../kvllm/registry.py)** — loader + `list` / `show <key>` / `serve <key>`.
  `serve` resolves an entry into a `vllm serve` argv and `os.execvp`s into it (signals/​SIGTERM pass
  through — sets up clean systemd behavior for Sprint 3). Sets `--served-model-name <key>` so the
  registry key *is* the `model=` the client sends. Unknown keys get a `difflib` did-you-mean.
- **[`justfile`](../justfile)** — `models-list`, `models-show <key>`, `serve <key>` (defaults to
  `qwen2.5-7b-instruct`), `loaded`, plus the Sprint 1 smoke recipes retargeted to registry keys.
- **[`docs/01-backend-contract.md`](../docs/01-backend-contract.md)** — the OpenAI `/v1` chat surface
  kvllm guarantees; mirrors the trt-llm chat surface, omits the KServe control surface.
- **[`docs/02-quantization.md`](../docs/02-quantization.md)** — AWQ/GPTQ/FP8 (+ Blackwell FP8/NVFP4)
  and the 32 GB VRAM math.

## Decisions & discoveries

- **Registry key = served model id.** `--served-model-name <key>` makes the friendly key
  (`qwen2.5-7b-instruct`) the thing `GET /v1/models` returns and the client passes as `model=` —
  satisfies the backend contract and hides the HF repo path from callers.
- **⚠️ TOML dotted keys.** `[models.qwen2.5-7b-instruct]` silently parses as *nested* tables
  (`qwen2` → `5-7b-instruct`). Keys with dots **must be quoted**: `[models."qwen2.5-7b-instruct"]`.
- **`execvp`, not `subprocess`.** Replacing the process means Ctrl-C and (later) systemd `SIGTERM`
  hit vLLM directly — no wrapper to forward signals. Pays off in Sprint 3.
- **Leaner than the TRT registry.** No engine-build fields (`max_batch_size`, `calib_size`, quant
  build args) — vLLM loads HF weights directly, so the registry is metadata + serve flags only.

## Outcomes

- `just models-list` / `models-show` render correctly; did-you-mean works on typos.
- **End-to-end:** `just serve qwen2.5-7b-instruct` → `GET /v1/models` id is `qwen2.5-7b-instruct`,
  and both Sprint 1 smoke tests (tool calling + LangChain `bind_tools`) pass against the
  registry-served model. `just lint` clean.

## Follow-ups

- Sprint 3 (korg #98): systemd unit so the default registry model auto-serves after a `kai` reboot —
  the `execvp` serve path is already SIGTERM-clean for it.
- Untested registry entries (coder-7b, llama-3.1-8b gated, 14B-AWQ) get validated as part of the
  Wed model research (korg #99).

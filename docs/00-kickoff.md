# kvllm — kickoff & handoff

_Created 2026-06-30. Read this first: it's the handoff from the `trt-llm-langchain` work where
the decision to build this was made. A fresh Claude Code session should start here._

## What this is

**kvllm** is a local LLM serving harness built on **vLLM**, running on the `kai` box (single RTX
5090). It serves models behind an **OpenAI-compatible `/v1` endpoint** so they're usable from
LangChain (and any OpenAI client). It is a **sibling backend to `trt-llm-explore`** — same role
(serve models on the 5090), different engine.

## The decision: why vLLM (over continuing TRT-LLM)

vLLM and TRT-LLM are **alternative inference engines** (you pick one per model, not both). Ken
evaluated this after getting tool calling working on the TRT-LLM stack. Full research lives in
[`/home/ken/src/ai/trt-llm-langchain/docs/tool-call-research/`](/home/ken/src/ai/trt-llm-langchain/docs/tool-call-research/README.md)
(read the TL;DR + the backend comparison + "model→parser coverage" matrix).

The deciding reframe: Ken's **top priority is model breadth** ("a wider range of models, not
GGUF-limited like Ollama"), and that is **vLLM's strength, not TRT-LLM's**:
- **vLLM loads HuggingFace models directly** (safetensors) — no per-model engine build, broadest
  model support, newest architectures fast (incl. DeepSeek, Qwen3, multimodal).
- **TRT-LLM requires compiling an engine per model** (`convert_checkpoint` → `trtllm-build`),
  supports fewer/slower-moving architectures, and has open consumer-Blackwell (sm_120) kernel
  gaps. Its real edge is peak throughput on supported models — marginal for a single-user homelab,
  and it costs exactly the flexibility Ken wants.

**Nothing is thrown away:** the LangChain client (`trt-llm-langchain` / `ChatTrtLlm`, now on PyPI)
speaks OpenAI `/v1`, so it points at vLLM with just a URL change. `trt-llm-explore` stays as-is for
already-built models.

## Ken's priorities (drive every decision here)

1. **Use from LangChain** — he's learning LangChain and wants to mix local models with Anthropic /
   cloud agents. (Both engines satisfy this via OpenAI `/v1`.)
2. **Rich model selection (MOST IMPORTANT)** — find the best *free* models for **programming and
   agentic control of homelab computers**; wants to try new ones (explicitly: **DeepSeek** — run
   it on the 5090 if it fits; the distills do).
   - 2a. (lower priority) play with **multimodal** models.
3. **Tool / model use is REQUIRED** — primary use cases need tool calling.
4. **Streaming desired, not a deal-breaker.**

## Environment (`kai`)

- **GPU:** NVIDIA RTX 5090, 32 GB, sm_120 (consumer Blackwell)
- **Driver:** 595.58.03 · **CUDA (driver):** 13.2 · native Linux (not WSL — better than the WSL
  setups in the research)
- **Tooling:** `uv` 0.11.25, Docker 29.6.1, `just` (used by the other projects)

## Plan (casual sprints; this is the rough roadmap)

Workflow = same casual cadence as `trt-llm-langchain`: per-sprint narrative in `sprints/`,
reference/setup in `docs/`, cross-project work items in **korg** (project `kvllm` = id **19**;
explore is id 15, trt-llm-langchain is id 16).

**Sprint 1 — Core setup (✅ shipped 2026-06-30; korg #96).** _The first risk to retire is a clean
vLLM install on sm_120._ Got vLLM serving on the 5090, exposed `/v1`, verified **tool calling**, and
reached it from a LangChain `ChatOpenAI`/`ChatTrtLlm`. Exit met: `chat.invoke(...)` and
`bind_tools(...)` work. Stretch met: DeepSeek-R1-Distill-Qwen-7B (not in the TRT registry). Decided
**`uv`, not Docker** — `uv add vllm` pulls a cu130 torch that drives sm_120 directly.

**Sprint 2 — Serving ergonomics (active; korg #97).** A registry of models + simple serve recipes
(`just serve <model>`), config, and notes on quant formats (AWQ/GPTQ/FP8) that fit 32 GB. Document
the contract it satisfies (same OpenAI `/v1` as `trt-llm-langchain/docs/03-backend-contract.md`,
minus the KServe load/unload bits — vLLM is one-model-per-process).

**Sprint 3 — Availability (korg #98; Ken's idea).** Now that we serve **natively, not via Docker**
(Sprint 1 decision), add infra so kvllm survives a `kai` reboot without a manual start: a minimal
local deploy + **systemd** unit for the vLLM server (`Restart=on-failure`, default model from the
registry, clean stop/switch path). Natural pair for the deferred helper app (it'd drive this unit).

**Wed — Model collection research (korg #99).** Which free models for coding + agentic control fit a 5090
(7B–32B, quantized), tool-calling quality, multimodal options. Download + prep for the 4-day
weekend. (This is research-heavy; could use the deep-research harness.)

**Deferred / "nice to have" (Ken's idea; korg #100):** a **helper app** — shows status + a model registry and
lets you "restart and load model X". This is the single-GPU model-switching story for vLLM (vLLM
holds one model per process; switching = stop/start, or vLLM "sleep mode"). Defer until after core
setup; it's a natural small LangChain-adjacent toy.

## Recommended technical approach (to derisk Sprint 1)

- **Install:** prefer the vLLM **Docker image** (`vllm/vllm-openai`) for a clean sm_120/CUDA
  match, OR `uv pip install vllm` with a CUDA 12.8+/13 torch backend. sm_120 has been supported
  since vLLM ~0.17; by now a recent release should work, possibly needing the right wheel/torch.
  Verify the installed version actually loads a model on the 5090 before anything else.
- **Serve + tools:** `vllm serve <hf-model> --enable-auto-tool-choice --tool-call-parser <family>`
  (e.g. `hermes`/`llama3_json`/`mistral` per model). Exposes `/v1/chat/completions` on :8000.
- **From LangChain:** `ChatOpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY", model=...)`
  — or reuse `ChatTrtLlm` by pointing `TRTLLM_CHAT_URL` at it (it's just a ChatOpenAI subclass).
- **sm_120 gotchas to watch (from research):** FlashAttention-3 may be unsupported on sm_120
  (fallback flag exists); some FP8 paths were slow under WSL (N/A here — native Linux). Pick a
  model that fits 32 GB (7B–14B full, up to ~32B quantized).
- **LangChain caveat:** `ChatOpenAI` against non-OpenAI servers — streaming tool-call assembly can
  be fragile (research §3). Keep tool turns non-streaming first; add streaming later.

## Pointers

- Research: `trt-llm-langchain/docs/tool-call-research/` (vLLM/SGLang/NIM comparison, sources).
- Client contract: `trt-llm-langchain/docs/03-backend-contract.md` (the `/v1` surface; vLLM gives
  the chat half natively).
- A serving-harness example to borrow shape from: `trt-llm-explore` (justfile recipes, model
  registry, docs/setup.md) — but vLLM needs far less (no engine build).
- The LangChain client is published: `pip install trt-llm-langchain` (`ChatTrtLlm`).

## First moves for the new session

1. Create the `kvllm` korg project (for WIs).
2. Sprint 1: get vLLM installed + serving one model on the 5090; verify `/v1` + tool calling +
   LangChain reach; then add a DeepSeek-distill (or other new model).
3. Keep `sprints/sprint-01-*.md` updated as you go (see `sprints/README.md`).

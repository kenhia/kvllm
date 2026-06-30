# Model research

Cited research on which open models to run on `kai` (RTX 5090) via kvllm. Each pass is a dated file;
this README is the **standing context** every pass (and the planned `/model-research` and
`/model-scout` skills) should inject so findings stay consistent and comparable.

## Serving profile (the constraints every recommendation must satisfy)

- **Hardware:** single NVIDIA **RTX 5090, 32 GB**, **sm_120** (consumer Blackwell), native Linux.
- **Server:** **vLLM 0.24.0**, OpenAI-compatible `/v1`, one model per process. Loads **HuggingFace
  safetensors** directly — **not** GGUF/Ollama/llama.cpp.
- **Quant that works on sm_120:** **AWQ** (proven workhorse) and **FP8** (native, fast on Linux);
  GPTQ ok. **Avoid INT8/bitsandbytes** (corrupted output). NVFP4 is bleeding-edge — not yet default.
- **Tool calling is required** — via `--enable-auto-tool-choice --tool-call-parser <p>`
  (`hermes` for Qwen2.5/Qwen3 instruct, `qwen3_xml` for Qwen3-Coder, `mistral` for Mistral/Devstral,
  `llama3_json` for Llama 3.x). Reasoning models add `--reasoning-parser <p>` (`qwen3` for Qwen3;
  `deepseek_r1` for R1). **`--enable-reasoning` is removed in modern vLLM** — don't use it.
- **Fit math:** leave KV-cache headroom — weights alone must not fill 32 GB. bf16 ≈ 2 GB/1B,
  FP8 ≈ 1 GB/1B, AWQ/GPTQ(4-bit) ≈ 0.55 GB/1B. `--kv-cache-dtype fp8` stretches context.
- **Priorities:** (1) coding, (2) agentic homelab control [both need tool calling], (3) vision.
- **Free/open-weight**; gated (HF-token) is acceptable but ungated preferred.

For each recommended model report: exact HF repo · params · recommended quant + est VRAM · license
(gated?) · tool-call/reasoning parser · vLLM+sm_120 maturity/caveats · best-at (coding/agentic/vision).

## Current registry (avoid re-recommending; note when superseded)

See [`../../models.toml`](../../models.toml). As of 2026-06-30 it holds: `qwen2.5-7b-instruct`
(default), `qwen2.5-coder-7b-instruct`, `deepseek-r1-distill-qwen-7b`, `llama-3.1-8b-instruct`,
`qwen2.5-14b-instruct-awq`, plus the survey additions (all `tested = false` until served on `kai`).

## Passes

| Date | File | Scope |
|---|---|---|
| 2026-06-30 | [2026-06-30-survey.md](2026-06-30-survey.md) | Broad sweep: coding, agentic, vision; Qwen3.6 verification |

## Skills

Two project skills (in [`.claude/skills/`](../../.claude/skills/)) automate this and read the serving
profile above:

- **`/model-research <name|hf-repo>`** — deep-dive one model against our constraints (primary-source
  verified) and write a `<date>-<model>.md` pass here; proposes a `models.toml` row.
- **`/model-scout [focus]`** — scan release surfaces for new models worth trying since the last run,
  diffing against [`.scout-state.json`](.scout-state.json); proposes candidates → feed them to
  `/model-research`.

Neither flips `tested=true` — that needs a real serve on `kai` (the eval harness, when it lands).

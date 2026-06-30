# Sprint 5 — Model collection research

_2026-06-30 on `kai`. korg #99 (the "Wed research" block, pulled forward). Branch `05-model-research`._
_Feeds the [Sprint 2](sprint-02-serving-ergonomics.md) registry. See [`../docs/00-kickoff.md`](../docs/00-kickoff.md)._

## Goal

Find the best free/open models for coding + agentic homelab control (tool calling required) that fit
a 32 GB 5090 on vLLM, plus a vision section — and specifically verify the "Qwen3.6" claim. Output: a
cited survey + a ready-to-add registry "download set."

## What shipped

- **[`docs/model-research/`](../docs/model-research/)** — new folder (per the helper-skills plan):
  - **[README.md](../docs/model-research/README.md)** — the standing **serving profile** (hardware,
    vLLM, quant, parsers, fit math) that future passes + the planned `/model-research` and
    `/model-scout` skills inject. Plus the pass index.
  - **[2026-06-30-survey.md](../docs/model-research/2026-06-30-survey.md)** — the cited report:
    headlines, sm_120 quant guidance, ranked shortlist (coding / agentic / vision), weekend download
    set, supersedes list, method & confidence.
- **[`models.toml`](../models.toml)** — 5 verified additions (all `tested=false`): `qwen3-8b-fp8`,
  `qwen3-vl-8b-instruct`, `internvl3-8b`, `qwen3.6-27b-awq`, `qwen3.6-35b-a3b-awq`.
- **[`kvllm/registry.py`](../kvllm/registry.py)** — added a `trust_remote_code` field (→
  `--trust-remote-code`) needed by InternVL3.

## Key findings (verified)

- **Qwen3.6 is real** — `Qwen/Qwen3.6-27B` (dense, multimodal) and `Qwen/Qwen3.6-35B-A3B` (MoE,
  multimodal), Apache-2.0, ungated (checked against the live HF API). ⚠️ new `qwen3_5*` arch →
  verify vLLM 0.24.0/sm_120 before trusting; the "Plus/Max" SKUs are **proprietary**, not these.
- **Coding upgrade:** Qwen3-Coder-30B-A3B (`qwen3_xml` parser) and Devstral-Small-2-24B (`mistral`,
  68% SWE-Bench) — both need a **4-bit AWQ** build for a single 32 GB card.
- **The adversarial verify earned its keep** — it *refuted*: that Qwen3-Coder-30B **FP8 fits 32 GB**
  (it's ~31 GB of weights → OOM; use AWQ); that `--enable-reasoning` is current (it's **removed** in
  modern vLLM); and that `deepseek_r1` is Qwen3's reasoning parser (it's **`qwen3`** now).
- **sm_120 quant:** AWQ is the proven workhorse; FP8 is native-fast on Linux; **avoid INT8/bnb**
  (corrupted); NVFP4 still bleeding-edge.

## Decisions & discoveries

- **The deep-research workflow crashed at the final synth stage** (StructuredOutput retry cap). But
  108 agents had already run; I salvaged **121 extracted claims + 75 adversarial-verify votes** from
  the run `journal.jsonl` and synthesized the report by hand. No re-run needed — the verified
  material was intact. _(Follow-up: the harness's synth schema is brittle at this result volume.)_
- **Adopted `docs/model-research/`** with a standing-context README, setting up the future
  `/model-research` + `/model-scout` skills to emit dated passes into it.
- New models stay **`tested=false`** until actually served on `kai` — the `qwen3_5*` arch support is
  the biggest open risk.

## Outcomes

- Cited survey + serving-profile context committed; 5 models added to the registry (CLI renders
  their serve commands correctly, incl. `--trust-remote-code` and `qwen3_xml`/`qwen3`). `just lint`
  clean.

## Follow-ups

- **Validate on `kai`:** serve `qwen3-8b-fp8` and `qwen3-vl-8b-instruct` (low-risk) and a Qwen3.6 AWQ
  (high-risk arch) → flip `tested=true` or record what breaks.
- **Find AWQ builds** for Qwen3-Coder-30B-A3B and Devstral-24B, then add them.
- **Build the helper skills** (`/model-research`, `/model-scout`) now that the folder + format exist.

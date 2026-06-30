---
name: model-scout
description: "Scan for newly-released open models worth evaluating on the kvllm 5090/vLLM box since the last scout, diffing against docs/model-research/.scout-state.json. Use when the user wants to check 'what's new worth trying' / find recent models / refresh the candidate list. Proposes candidates and suggests /model-research for deep dives; does not itself do per-model deep research."
---

# Model scout (what's new worth trying)

Curated search + diff for newly-released open models that fit kvllm. This is a discovery helper, NOT
a feed — there's no clean "new good models" API, so it searches release surfaces and diffs against
state, leaning on primary-source checks to avoid surfacing hallucinated or renamed models.

## Input

```text
$ARGUMENTS
```

Optional focus (e.g. `coding`, `vision`, `agentic`, or an org like `Mistral`). Empty = all skillsets.

## Procedure

1. **Load state + context:**
   - `docs/model-research/.scout-state.json` — `{ "last_run", "seen": [<hf repos already known>] }`.
   - `docs/model-research/README.md` — the serving profile (the fit/parser/quant bar to filter by).
   - `models.toml` — already-registered models (also "seen").

2. **Search release surfaces** for open models published/updated **since `last_run`**, focused on
   the relevant skillsets and the orgs that matter for a 5090: Qwen, DeepSeek, Mistral, Meta (Llama),
   Google (Gemma), OpenGVLab/InternLM, Microsoft (Phi), Moonshot/Kimi, Z.ai/GLM, NVIDIA quant repos.
   Useful angles: HuggingFace "trending"/"recently updated" for those orgs; vLLM release notes &
   sm_120/Blackwell issues; reputable roundups. Verify a candidate is real via the HF API before
   listing it (`gated`, `license`, `createdAt`).

3. **Filter to the bar:** open-weight, vLLM-servable (safetensors; AWQ/FP8/GPTQ — not GGUF-only),
   plausibly fits 32 GB (≈7–35B with quant), and matches a target skillset (coding / agentic / tool
   use / vision). Drop anything that can't fit even at 4-bit, or that duplicates a `seen` model.

4. **Report new candidates** — for each: HF repo · size/arch · skillset · one-line "why it might be
   worth it" · the obvious risk (new arch? GGUF-only? gated?) · and `→ /model-research <repo>` for a
   deep dive. Group by skillset. If nothing new clears the bar, say so plainly.

5. **Update state:** write today's date to `last_run` and add every surfaced repo (recommended or
   not) to `seen`, so the next scout doesn't re-surface it. Optionally write a dated
   `docs/model-research/<YYYY-MM-DD>-scout.md` if the user wants it persisted.

## Notes

- Honesty over noise: a short, real list beats a padded one. Don't invent models; if a name only
  appears in one low-quality blog and not on HF, flag it as unverified rather than listing it.
- Pairs with a schedule: this can be run periodically (e.g. a weekly routine) to keep the candidate
  list fresh; `/model-research` then does the deep dive on anything promising.

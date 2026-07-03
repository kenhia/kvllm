---
name: model-research
description: "Deep-dive one specific model for the kvllm 5090/vLLM environment and write a cited model-research/<date>-<slug>.md. Use when the user names a model to evaluate (e.g. '/model-research Devstral-Small-2' or a HF repo id), or asks 'is <model> worth trying on the 5090?'. Verifies fit/parsers/sm_120 support against primary sources and proposes a registry row."
---

# Model research (single model)

Research ONE model against kvllm's actual constraints and emit a standard, cited per-model doc.

## Input

```text
$ARGUMENTS
```

A model name or HuggingFace repo id (e.g. `Devstral-Small-2-24B`, `Qwen/Qwen3.6-27B`). If empty,
ask which model. If ambiguous (a family, not a checkpoint), resolve to the specific HF repo(s).

## Procedure

1. **Load the standing context** (do this first, every time):
   - `model-research/README.md` — the serving profile (hardware, vLLM, quant, parsers, fit math).
   - `models.toml` — so you don't re-recommend an existing entry; note if this supersedes one.
   - Skim recent `model-research/*.md` passes for prior findings on this family.

2. **Verify against PRIMARY sources** (don't trust blogs/memory — the AI world moves fast and model
   names get faked/renamed). For the target model, establish each field below, citing the source URL:
   - **Exists / identity:** the HF API (`https://huggingface.co/api/models/<repo>` → `gated`,
     `license`, `author`, `createdAt`, `safetensors` param count). This is the authoritative check.
   - **License + gated:** from that API (`gated:false` + a permissive license = no token needed).
   - **Params / architecture / `model_type`:** model card + `config.json` (flag NEW arch types whose
     vLLM/sm_120 support is unproven — this is the usual risk).
   - **Quant + est VRAM:** which build fits 32 GB with KV-cache headroom (bf16 ≈ 2 GB/1B, FP8 ≈ 1,
     AWQ/GPTQ ≈ 0.55). **Beware FP8 that's actually ~1 byte/param and OOMs a 32 GB card — prefer AWQ
     for ≥24B.** Name the exact servable repo (an AWQ/FP8 build, not just the bf16 base).
   - **Tool-call + reasoning parser:** model card serve command + vLLM tool_calling docs. Pin the
     RIGHT parser (`hermes` Qwen instruct, `qwen3_xml` Qwen3-Coder, `mistral` Mistral/Devstral,
     `llama3_json` Llama 3.x; reasoning `qwen3` for Qwen3, `deepseek_r1` for R1). Note known parser
     bugs (search vLLM issues).
   - **vLLM + sm_120 maturity:** search vLLM GitHub issues/release notes for the arch + Blackwell.
     Flag bleeding-edge support honestly.
   - **Best-at:** coding / agentic / general / vision, with any benchmark the card cites.

   Prefer the deep-research harness for a hard case: `Workflow({ name: "deep-research", args: "<the
   model + the serving profile + the field checklist above>" })`. If it dies at synthesis, salvage
   the verified claims from its run `journal.jsonl` (as done in the 2026-06-30 survey). For a routine
   single model, a handful of targeted WebFetch/WebSearch on the primary sources above is enough.

3. **Adversarially sanity-check** the load-bearing conclusions before writing — especially "fits
   32 GB" (do the weight math) and "tool calling works" (right parser? known bugs?). Mark confidence.

4. **Write `model-research/<YYYY-MM-DD>-<model-slug>.md`** (use today's date from context) with:
   verdict (worth trying / has issues / skip) · exact HF repo(s) · params/arch · quant + est VRAM ·
   license/gated · tool+reasoning parser · vLLM+sm_120 maturity & caveats · best-at · a ready-to-add
   `models.toml` row · sources. Keep it scannable.

5. **Update `model-research/README.md`** — add the pass to the index table.

6. **Offer to add the registry row** to `models.toml` (`tested = false` until served on `kai`), and
   to validate it live with `just serve <key>` + a smoke test.

## Notes

- This skill researches and documents; it does not flip `tested=true` — that needs a real serve on
  `kai` (see the eval harness when it exists).
- If the model plainly can't fit 32 GB even at 4-bit, say so and stop — don't pad a doc.

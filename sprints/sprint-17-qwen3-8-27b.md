# Sprint 17 — Qwen3.8-27B: serve it, then score it

_2026-08-20. korg #1474, #1475, proposal korg:1478. Branch `17-qwen3-8-27b`.
Slice 3 of 3 in the Qwen3.8-27B program (korg:1480), behind the vLLM bump (sprint 15) and
the noise floor (sprint 16)._

## Goal

Answer one narrow question: **is `Qwen3.8-27B` better than `gemma-4-31b-it-awq`, on this
card, for these tasks?** Not "who tops the board". gemma holds the resident slot on the
5090 because it is local — the marginal cost of a query is power — and that slot changes
hands only if another *local* model beats it. `claude-sonnet-5` is a yardstick for how much
capability the local choice gives up, not a competitor for residency.

Two work items, in order, because the second is worthless if the first is shaky:

1. **#1474** — a registry entry that actually serves.
2. **#1475** — the ranked suites, scored onto the board against the re-baselined gemma row.

## What the noise floor changed about this sprint

Sprint 16's answer arrived before the candidate did, which was the point of resequencing it.
The composite band is **0.036** (driven by the frontier baseline; local-vs-local is ~0.007),
and every repeated number landed *below* the single-draw value the board had carried the day
before. So a single `just eval` on Qwen3.8 would produce a draw, not a score.

**This sprint runs `just eval-repeat … --n 3 --publish median`, not `just eval`.** That is a
direct consequence of slice 2 and the reason it was promoted ahead of this one.

## Decisions

### Quantization: NVFP4, and `quantization` stays *unset*

`unsloth/Qwen3.8-27B-NVFP4` — 831K downloads, by far the most-adopted of the four NVFP4
repos the research listed, and the mixed-precision build with the larger KV headroom.

Measured from the repo rather than taken from the projection: main weights
**22.57 GB (21.02 GiB)**, comfortably under the ~24.6 GiB the research projected, plus a
separate 0.85 GB `model_mtp.safetensors` that only loads under `--speculative-config`.

The checkpoint is `quant_method = "compressed-tensors"`, `format = "mixed-precision"`:
NVFP4 on the MLPs, FP8 on attention and the last 8 MLP blocks, and the **vision tower left
in bf16** (it is in the config's `ignore` list). vLLM reads that from `quantization_config`,
so the registry deliberately does **not** set `quantization` — an explicit value here could
only disagree with the weights. The header now says so, because "omit for bf16/fp16" was the
only guidance and this is a third case.

The AWQ fallback is `cyankiwi/Qwen3.8-27B-AWQ-INT4`, which the research flagged at 58
downloads and is now at 154K — no longer a fringe repo if NVFP4 fails. QuantTrio, our source
for `qwen3.6-27b-awq`, still has not published a 3.8.

### `kv_cache_dtype` becomes a real registry field

The entry needs `--kv-cache-dtype fp8` and there was no field for it — only `extra_args`,
the escape hatch. It is added as a first-class field (`kvllm/registry.py`, tests in
`tests/test_registry.py`) because it is a *model property* on a long-context model whose
weights fill most of the card, not a per-invocation flag. `extra_args` still gets the last
word, since it is appended after.

### Context: 262144, not the 3.6's 8192

`qwen3.6-27b-awq` is pinned at 8K because a dense 27B's KV cache at 32K did not fit. That
reasoning does not transfer: Qwen3.8 is hybrid — Gated DeltaNet linear attention on 48 of 64
layers, full attention every 4th (`full_attention_interval: 4`) — so only 16 layers hold a
per-token KV cache, and the linear layers carry a constant recurrent state instead. With
fp8 KV that is ~32 KiB/token against roughly 7.6 GiB of post-weight budget. Holding this
model at 8K would understate it on exactly the long-context work it was built for.

### Video: measured on the image suite, and *not* claimed

Qwen3.8 takes video (`video_token_id`, `temporal_patch_size: 2`); nothing else in the
registry does. The vision suite is `ContentImage`-only.

**The call: score `vision` on the existing image-only suite v2, unchanged, and do not put
`video` in `capabilities`.** The suite measures image understanding, which is the same
measurement every other model on the board got — that comparison stays honest. What would
not be honest is letting a "vision: 100%" row imply the video path was tested, so the
registry `notes` and the scorecard say plainly that it was not.

Extending the suite is not merely out of scope, it is *blocked* by the ranked-suite
convention: adding video cases means bumping `VISION_VERSION`, which invalidates the vision
score of every model on the board. That is a suite sprint with a full re-score, not a rider
on a candidate evaluation. Filed as a follow-up.

### Speculative decoding off for the ranked run

The MTP draft head (0.77–0.89 acceptance) stays off so tok/s is comparable with gemma,
which has no equivalent. It gets a separate, unranked throughput measurement recorded in the
scorecard notes. This is a fairness decision, not a performance one.

## Incidental fix

`models.toml` had gemma's `eval_verdict`/`eval_date` stranded *below* the "Frontier
baselines" banner comment. They still belonged to gemma (a TOML comment does not end a
table), but the next `[models.…]` header added under that banner would have silently
captured them. Moved above the banner.

## Results

_(pending)_

## Follow-ups

_(pending)_

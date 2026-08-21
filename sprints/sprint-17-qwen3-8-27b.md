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

## The score that was wrong, and why

The first N=3 run put Qwen3.8 on the board at **composite 0.75**, with `judged` **62%** —
against gemma's 77% and the older `qwen3.6-27b-awq`'s 92%. A 27B that scores 100% on both
`tools` and `code` does not then fail at writing prose. That is the shape the findings doc's
prime rule is about: **audit the harness before blaming the model.**

The judge's own comments named the symptom:

- `judged/explain-config` — "No answer was provided to grade."
- `judged/plan-migration` — "The model provided no answer to grade."
- `vision/v10-render-clean` — EMPTY ANSWER

Three blanks. The transcripts gave the cause: `stop_reason: max_tokens` at exactly
`output_tokens: 4096` on every one. The model spent its whole budget inside `<think>` and
never emitted a final answer; the reasoning parser stripped the thinking, left content
empty, and the judge correctly graded nothing as zero.

**Root cause, one line of the chat template** (`chat_template.jinja:59`):

```jinja
{%- set resolved_reasoning_effort = reasoning_effort|default('xhigh') %}
```

Qwen3.8 defaults to **`xhigh`**, its maximum reasoning effort. We had been benchmarking it
at maximum thinking against a 4096-token ceiling that sprint 11 sized for the 3.5/3.6
family's defaults. Measured on this card at `max_tokens=4096`:

| `reasoning_effort` | `explain-config` | `plan-migration` |
| --- | --- | --- |
| `xhigh` (default) | 174 tok, answered | **4096 tok, EMPTY** |
| `medium` | 278 tok, answered | 3078 tok, answered |
| `low` | 219 tok, answered | 2948 tok, answered |
| thinking off | 78 tok, answered | 3346 tok, answered |

### Why the fix is the serve config and not the suite

The 4096 budget is a **frozen ranked condition**. `judged` v2 already raised it 1024 → 4096
for precisely this failure with the Qwen3.5/3.6 family, and paid for it with a version bump.
Raising it again would invalidate the `judged` and `vision` score of every model on the
board. The convention is explicit that ranked conditions do not move for one candidate's
convenience.

So the knob that moves is the one that belongs to the model:

```toml
extra_args = ["--default-chat-template-kwargs", "{\"reasoning_effort\": \"medium\"}"]
```

`medium` is the highest effort that reliably fits the budget, which makes it the setting
that measures the model rather than the ceiling. Verified server-side with plain OpenAI
requests — what the harness actually sends — not just per-request overrides.

### It also explains the noise

The `xhigh` run's `agentic` spread was **0.190** (0.700–0.890) — *wider than
`claude-sonnet-5`'s 0.150*, from a **local** model at `temperature=0.0`. Sprint 16's tidy
finding that local models are near-deterministic (gemma: 0.030) looked contradicted.

It was not. At `xhigh` the model sometimes spirals into the token budget and sometimes does
not, and that coin-flip is the variance. `explain-config` answered by hand in 174 tokens and
still blew the budget inside the eval — same prompt, same temperature, opposite outcome.

**The generalisation worth keeping: "local models are reproducible" is a claim about
`temperature=0.0` plus a bounded output, not about locality.** Put a variable-length
reasoning phase in front of a fixed ceiling and a local model becomes as noisy as a hosted
one — noisier, here. That is a new artifact class, and it is not one of the four in the
findings doc.

The `xhigh` run is kept as evidence, quarantined and never published, under
`model-research/evals/noise-floor/qwen3.8-27b-nvfp4-xhigh-artifact-2026-08-20/`.

## The blocker: vLLM 0.27.1's Gated DeltaNet path is not stable on this model

The corrected re-run never produced a ranked score, and this is why.

With `reasoning_effort: medium` pinned, the eval was attempted four times. It failed every
time, in one of two ways:

1. **Loud** — `CUDA error: an illegal memory access was encountered`
   (`cudaErrorIllegalAddress`) during engine init. Localised exactly:

   ```
   vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py:1058
     in _warmup_prefill_kernels
   ← qwen_gdn_attention_core ← Qwen3_5 forward ← profile_run ← determine_available_memory
   ```

2. **Silent** — the engine stops making progress with **nothing logged**: 100% GPU
   utilisation, `num_requests_running` 0, `num_requests_waiting` 0, and
   `generation_tokens_total` frozen (observed at 34,775 once and at 384 another time) while
   the HTTP frontend still answers `/v1/models` and `/metrics` instantly.

It is **not** OOM (the loud failure is an illegal address, not an allocation failure), not
the quantization config, and not the `--default-chat-template-kwargs` flag — that only
alters the rendered prompt string and cannot reach a CUDA kernel. It is intermittent: the
very first batch completed 3 full runs × 5 suites on this exact serve command.

### How the silent mode was caught, and why it matters

The silent hang is the dangerous one, and finding it needed the disagreement between two
signals. Sprint 16's monitor said `status: running`, and `nvidia-smi` said 100% utilisation
— both of which read as healthy. The engine's own counters said otherwise: zero requests
in flight and a frozen token total. **A busy GPU is not evidence of progress.** Sprint 15
learned not to trust `pgrep`; sprint 16 learned not to trust a buffered log; this run adds
that GPU utilisation is a derived signal too, and `vllm:generation_tokens_total` is the one
the engine actually writes.

Worth adding to the monitor: a stall detector keying on that counter would have caught this
in two minutes instead of twenty-five.

### It wedged the card

After the repeated failures and the SIGKILLs needed to clear them, `nvidia-smi` reported
`ERR!` for fan/temp/power and **`Channel Repair Pending: GPU requires reset`** — with 2 MiB
allocated and no compute processes. `gemma-4-31b-it-awq` then hung on its own restart at the
encoder-profiling step, which is how the wedge was noticed. Plain CUDA still worked
throughout (20× 8192³ bf16 matmul in 0.21 s), so this is the GSP-class wedge the project has
history with (2026-07-02, Xid 119) rather than a dead card — no Xid was logged this time.

The GPU was left idle at 2 MiB with `kvllm.service` stopped-but-enabled, so gemma returns on
its own after the reset. **A contributing factor was mine**: several serve attempts followed
a SIGKILL within seconds, which is exactly the rapid kill/serve cycling `CLAUDE.md` warns
against. A killed engine needs ~60 s for the driver to tear its CUDA context down — observed
directly, when a `<defunct>` EngineCore held 25,750 MiB for a full minute after exiting.

## Results

**#1474 — done.** `qwen3.8-27b-nvfp4` is in the registry and serves.

| | |
| --- | --- |
| VRAM | **28,554 MiB** (gemma: 30,846 — ~2.3 GB more headroom) |
| Cold start | 58 s |
| Weights | 21.34 GiB |
| KV pool | 4.27 GiB → 134,085 tokens at `fp8` |
| Context | 131,072 (16× the dense 3.6-27B's 8,192) |
| decode | 28.8 tok/s (`--enforce-eager`; below the board's 40 tok/s full-speed mark) |

Verified by hand: chat (correct), `qwen3_xml` tool calls (clean parse), vision (accurate),
and the **video** path end-to-end — a 4-frame encoded clip came back described in order,
though it dropped one frame to temporal subsampling, which a future video suite would have
to account for.

**#1475 — blocked, not delivered.** There is no trustworthy ranked row for this model, and
publishing one from an engine that intermittently stalls would be worse than publishing
none. `models.toml` records `eval_verdict = "has issues"` with the failure signature in
`eval_notes`; the leaderboard carries **no** qwen3.8 row.

The one thing the suites did establish, from the quarantined `xhigh` batch, is that nothing
is wrong with the model's *competence*: `tools` 100%, `code` 100% across all three runs, and
`agentic` 88/89% — against gemma's 76%. That is suggestive, not a result, because it was
measured under the reasoning-effort artifact. Under `medium`, the single completed `agentic`
suite scored 80%, so the honest summary is that **the agentic gap is real but smaller than
the contaminated numbers implied**, and the resident-slot question stays open.

## Follow-ups

- **Re-run #1475 once the card is reset**, and treat the GDN instability as the gating risk
  rather than an incident: try `max_model_len` well below 131072 first (the loud failure is
  in a *warmup* kernel, so the profiling shapes are the obvious variable), and consider the
  AWQ build `cyankiwi/Qwen3.8-27B-AWQ-INT4` — now 154K downloads, up from the 58 the research
  recorded — as a path that avoids the NVFP4 kernels entirely.
- **Report the GDN bug upstream.** `qwen_gdn_linear_attn.py:1058` in
  `_warmup_prefill_kernels`, vLLM 0.27.1, sm_120, NVFP4 compressed-tensors, `--enforce-eager`,
  `--kv-cache-dtype fp8`. Both signatures are reproducible enough to describe.
- **Add a stall detector to the eval monitor** keyed on `vllm:generation_tokens_total` +
  `num_requests_running`, not on GPU utilisation. It would have turned a 25-minute silent
  hang into a 2-minute alarm, and it generalises to every model.
- **A fifth artifact class for the findings doc**: *a variable-length reasoning phase in
  front of a fixed output ceiling*. It produces empty answers scored as capability failures,
  and it makes a local, temperature-0 model as run-to-run noisy as a hosted one (agentic
  band 0.190 vs sonnet's 0.150). The diagnostic is `stop_reason: max_tokens` with empty
  content — cheap to check and worth checking on every reasoning model from now on.
- **`models.toml` has a structural trap the eval writer walks into.** A section banner
  comment sits *inside* the preceding model's table, so appended `eval_verdict`/`eval_date`
  land below it — and the next model added under that banner captures them. It produced a
  genuinely invalid registry this sprint (duplicate keys → `tomllib` "Cannot overwrite a
  value"). Fixed twice by hand here; the writer should append before trailing comments, or
  the banners should move.
- **Video needs a suite before it can be a capability.** The path works; the image-only
  vision suite cannot score it, and adding cases means a `VISION_VERSION` bump plus a
  re-score of every model on the board.

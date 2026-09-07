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

## The blocker: kai's GPU is faulty — and the wrong diagnosis first

**Corrected 2026-08-21.** This section originally read "vLLM 0.27.1's Gated DeltaNet path is
not stable on this model" and blamed an upstream kernel. That was wrong. The cause is
failing hardware. Full incident record:
[`docs/findings/kai-5090-gpc9-fault-2026-08-21.md`](../docs/findings/kai-5090-gpc9-fault-2026-08-21.md).

With `reasoning_effort: medium` pinned, the eval was attempted four times and failed every
time, in one of two ways:

1. **Loud** — `CUDA error: an illegal memory access was encountered`
   (`cudaErrorIllegalAddress`), which localised neatly to
   `vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py:1058` in
   `_warmup_prefill_kernels`.
2. **Silent** — the engine stops with **nothing logged**: 100% GPU utilisation,
   `num_requests_running` 0, `generation_tokens_total` frozen, HTTP frontend still answering.

That file and line number were real, and they were a red herring. The Gated DeltaNet kernel
was simply what happened to be running when the bad SM was scheduled.

### What it actually is

kai's RTX 5090 faults on basic CUDA work. Five lines of PyTorch — allocate 2 GiB of fp16,
`torch.nn.init.normal_`, synchronise — fail **6 times out of 12**, each trial in a fresh
process. No vLLM, no model, no quantization. The kernel log names the same silicon every
time:

```
Xid 31: MMU Fault: ENGINE GRAPHICS GPC9 GPCCLIENT_T1_9              x4
Xid 13: Graphics SM Warp Exception on (GPC 9, TPC 4, SM 1): Out Of Range Address   x2
Xid 43: channel teardown                                            x2
```

Every fault on **GPC 9**; every warp exception on the identical **SM (GPC 9, TPC 4, SM 1)**;
`Xid 13` ESR registers byte-identical across events seven minutes apart — while the faulting
virtual addresses differ wildly, the processes differ (`VLLM::EngineCor`, bare `python3`) and
the workloads differ completely. It survived a reboot and a full power-off.

`gemma-4-31b-it-awq` — different model, architecture and quantization — fails with the same
error inside `torch.nn.init.normal_` during weight init. **That was the clue that should have
ended the software theory**, and it is the correction worth keeping from this sprint.

### The rung below the prime rule

The project's prime rule is *audit the harness before blaming the model*. This adds a rung
beneath it. A plausible, well-localised software explanation — a real upstream file, a real
line, a real function — is **not evidence that the cause is software**. The moment a
*second, unrelated* model failed the same way, the correct move was a bare-metal
reproduction outside all project code, not more investigation inside the stack. Five lines of
PyTorch would have reached the answer in minutes instead of hours.

### The silent mode, and the monitor

The silent failure is still worth its own note, because catching it needed the disagreement
between two signals. Sprint 16's monitor said `status: running` and `nvidia-smi` said 100%
utilisation — both read as healthy. The engine's own counters said otherwise: zero requests
in flight, frozen token total. **A busy GPU is not evidence of progress.** Sprint 15 learned
not to trust `pgrep`; sprint 16 learned not to trust a buffered log; this run adds GPU
utilisation to the list of derived signals, with `vllm:generation_tokens_total` as the one
the engine actually writes. A stall detector on that counter would have caught it in two
minutes rather than twenty-five — and it would have been just as useful for a hardware fault
as for a software one.

### The wedge, and my part in it

After the failures and the SIGKILLs needed to clear them, `nvidia-smi` reported `ERR!` for
fan/temp/power and `Channel Repair Pending: GPU requires reset`. Gemma then hung on its own
restart, which is how the scope of the problem became visible. That flag has since cleared
on its own and the card idles normally at ~13 W — the fault is intermittent, not a permanent
brick.

Two things were genuinely mine, independent of the hardware:

- Several serve attempts followed a SIGKILL within seconds, which is exactly the rapid
  kill/serve cycling `CLAUDE.md` warns against. A killed engine needs ~60 s for the driver to
  tear its CUDA context down — observed directly, when a `<defunct>` EngineCore held
  25,750 MiB for a full minute after exiting.
- `kvllm.service` was left **enabled** while gemma was unable to load, so every boot
  auto-started a model that hung and pegged the card. It is now stopped and disabled.

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

**#1475 — blocked, not delivered; carried to sprint 18.** There is no trustworthy ranked row
for this model, and none was published: the leaderboard carries **no** qwen3.8 row. `models.toml` records
`eval_verdict = "has issues"` with the failure signature in `eval_notes`.

The verdict is about **the box, not the model** — it is not evidence against Qwen3.8, and
the `eval_notes` should be re-read (and probably rewritten) once the card is trusted again.
Nothing measured on this hardware on 2026-08-20 is reliable, including the operational
numbers above: a fault that corrupts a weight fill can corrupt an output that never throws.

The one thing the suites did establish, from the quarantined `xhigh` batch, is that nothing
is wrong with the model's *competence*: `tools` 100%, `code` 100% across all three runs, and
`agentic` 88/89% — against gemma's 76%. That is suggestive, not a result, because it was
measured under the reasoning-effort artifact. Under `medium`, the single completed `agentic`
suite scored 80%, so the honest summary is that **the agentic gap is real but smaller than
the contaminated numbers implied**, and the resident-slot question stays open.

## Follow-ups

- **Fix the hardware before re-running anything.** Test the proprietary driver module
  (`nvidia-driver-595`, currently the **open** variant is installed) as the one remaining
  software variable, then RMA if it still faults. Details and the reproduction:
  [`docs/findings/kai-5090-gpc9-fault-2026-08-21.md`](../docs/findings/kai-5090-gpc9-fault-2026-08-21.md).
  **Do not re-run #1475 until the card is trusted** — and re-baseline gemma when it is,
  because the current gemma row was measured on this box too.
- **Do NOT report a vLLM bug.** An earlier version of this record proposed filing
  `qwen_gdn_linear_attn.py:1058` upstream. That would have been a false report against a
  healthy project.
- **Re-try #1475 on healthy hardware without pre-emptive workarounds.** The `max_model_len`
  and AWQ-fallback ideas were mitigations for a bug that does not exist; start from the
  registry entry as it stands. `cyankiwi/Qwen3.8-27B-AWQ-INT4` remains a reasonable
  comparison point on its own merits (now 154K downloads, up from the 58 the research
  recorded), not as a workaround.
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

## Close-out (2026-09-06)

Shipped with **#1474 done and #1475 carried forward**, which is why this sprint closes at
half its nominal scope: the hardware it was measuring on turned out to be broken, and
finding that out became the sprint's real output.

**The card was replaced.** ASUS reflowed the GPU successfully but could not source a
replacement heatsink, so they swapped the whole card under warranty — no
customer-induced-damage finding. The replacement (`GPU-bb68141d-0bca-b64f-8c91-42a248f7d4f6`,
serial `T7YVCM026219KG6`) passed the 12-trial PyTorch repro **12/12 with zero Xid**, on
driver `595.58.03` / VBIOS `98.02.2E.40.E0` — *unchanged from the faulty card*, so it passed
on exactly the stack that failed. See the correction at the head of
[`../docs/findings/kai-5090-gpc9-fault-2026-08-21.md`](../docs/findings/kai-5090-gpc9-fault-2026-08-21.md):
the mechanism was a solder interconnect under the package, not defective silicon.

**#1474 is closed.** The registry entry, the `kv_cache_dtype` field and the serve recipe all
stand as shipped.

**#1475 moves to sprint 18 with widened scope**, driven by handoff **korg:1953**:

1. **WI-1736** — bump vLLM 0.27.1 → 0.28.0. (Watch `max_num_batched_tokens`, default 8192 →
   16384; gemma sat at 30,846 of 32,607 MiB, so pin it rather than discover it mid-suite.)
2. **Re-baseline gemma on 0.28.0** — not on 0.27.1. The baseline has to sit on the same stack
   the candidate is scored against.
3. **Then serve and score Qwen3.8**, five ranked suites plus `assisted`, speculative decoding
   off.

The re-baseline is not housekeeping. The faulty card was in kai from at least 2026-07-01
(korg:1514 pairs a July 1 fault with an Aug 20–21 fault on the identical SM, byte-identical
ESR), so **every local row on the board from that window was measured on defective
hardware** — including gemma's current 2026-08-20 row. If the 0.28.0 gemma row differs
materially, hardware is at least as good an explanation as the version bump; the two are
confounded and cannot be separated after the fact. Say so rather than crediting vLLM.

**Proposal korg:1478 deliberately stays `active` across both sprints** — it covers #1474 and
#1475, and only the first is done. The `.korg-sprint-proposal` marker was removed as part of
this close-out so that shipping this branch does not auto-close the proposal.

### One correction to carry into sprint 18

Handoff korg:1953 and WI-1736 both state that **Qwen3.8 requires vLLM 0.28.0**. This sprint's
own record contradicts that: `qwen3.8-27b-nvfp4` served on **0.27.1** at 28,554 MiB and
completed three full N=3 passes across all five suites (`tools` and `code` at 100% in every
one), which is what #1474 was closed on.

This does not change the plan — 0.28.0 is the target Ken chose, with 0.27.1 as the stated
fallback. It changes the *risk*: the fallback is **proven rather than hypothetical**, and the
bump is a preference, not a gate. If 0.28.0 misbehaves, sprint 18 is not blocked; it can
score on 0.27.1 and say so.

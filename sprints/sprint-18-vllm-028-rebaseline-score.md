# Sprint 18 — vLLM 0.28.0, re-baseline gemma, score Qwen3.8-27B

**Proposal:** korg:1478 (`active`, carried from sprint 17) · **Handoff:** korg:1953
**Work items:** #1736 (vLLM 0.28.0 bump), #1475 (score Qwen3.8), #1961 (re-baseline gemma —
filed mid-sprint by another session and `covers`-linked to korg:1478; the re-baseline had until
then existed only as prose in #1475's comments). #1474 closed in sprint 17.
**Branch:** `18-vllm-028-rebaseline-score`

## Goal

The last open step of the 5090 RMA restore, and program korg:1480's slice 3. Three
things in a fixed order:

1. Bump vLLM 0.27.1 → 0.28.0.
2. Re-baseline `gemma-4-31b-it-awq` **on whatever version lands**.
3. Serve and score `qwen3.8-27b-nvfp4` against it, all five ranked suites plus `assisted`.

The order is the point. Baseline and candidate must share a stack — that is what makes
the comparison fair, and no amount of care afterwards repairs it if they don't. Which
version they share is negotiable; sprint 17 proved Qwen3.8 serves fine on 0.27.1, so
0.28.0 is Ken's preference with a *proven* fallback, not a gate.

## Why the re-baseline is a gate and not housekeeping

The faulty card was in kai from at least 2026-07-01 (korg:1514 pairs a July 1 fault with
an Aug 20–21 fault on the identical SM, byte-identical ESR). Every local row on the board
from that window was measured on defective hardware — gemma's current 2026-08-20 row
included. If the new gemma row differs materially from it, **hardware is at least as good
an explanation as the version bump**; the two are confounded and cannot be separated after
the fact. Say so rather than crediting vLLM.

## Premise check at sprint start

Verified on kai, 2026-09-06, before any work:

- **#1475 holds.** No qwen3.8 row on the board. Gemma's row is `2026-08-20 / vllm 0.27.1 /
  30846 MiB`, inside the contaminated window. The registry entry stands as sprint 17 left
  it, `reasoning_effort: medium` included.
- **#1736 holds, with favorable drift.** Two of the four flagged risks are already retired:
  kai is *already* on `torch 2.13.0+cu130` under 0.27.1 (so the "default wheel moves to
  CUDA 13.0" concern predates the stack), and `calculate_kv_scales`,
  `override_attention_dtype` and `bitsandbytes` appear nowhere in the serve path.
- **Two risks are live.** `max_num_batched_tokens` is pinned nowhere in the repo, so the
  8192 → 16384 default rise lands against gemma at 30,846 of 32,607 MiB. And the
  `models.toml` banner-inside-the-previous-table trap is live: gemma already carries
  `eval_verdict`/`eval_date`, so the re-baseline's append can produce duplicate keys.
- **Not in the handoff:** `pyproject.toml` records a sprint-15 lesson that applies directly
  — vLLM hard-pins `nvidia-cutlass-dsl` but only *floors* `quack-kernels`, so upgrading
  vllm alone leaves a stale quack that dies at kernel warm-up. Both go in one `uv lock`.
- **Environment:** replacement card `GPU-bb68141d-0bca-b64f-8c91-42a248f7d4f6` present,
  driver `595.58.03`, `kvllm.service` (user unit) active, 0 restarts, serving gemma.
  0.28.0 is the newest vLLM on PyPI; no 0.28.x patch releases exist yet.

## Narrative

### Step 1 — the vLLM 0.28.0 bump (WI-1736)

**Landed. 0.28.0 is clean on this box.** gemma-4-31b-it-awq serves at 30,746 MiB with a
7.31 GiB KV pool and 20,464 KV tokens, against 30,846 MiB / 7.42 GiB / 20,765 tokens on
0.27.1 — a 1.5% difference, and the model answers correctly. Cold start ~140 s, 0 restarts.

`uv lock --upgrade-package vllm --upgrade-package quack-kernels` in one call, per the
sprint-15 lesson recorded in `pyproject.toml`. That mattered: `quack-kernels` moved
0.6.1 → 0.6.4 alongside `nvidia-cutlass-dsl` 4.6.0 → 4.6.2, exactly the coupling that
comment warns about. Riders: `huggingface-hub` 1.16.1 → 1.30.0, `inspect-ai`
0.3.244 → 0.3.263, `fastsafetensors` 0.4.0, `humming-kernels` 0.1.12.

Three of the four risks flagged in WI-1736 and handoff korg:1953 turned out to be
non-events, and the fourth was the opposite of what was predicted:

- **CUDA 13.0 wheel** — already satisfied before the bump. kai was running
  `torch 2.13.0+cu130` under 0.27.1, so there was nothing to move.
- **`calculate_kv_scales` / `override_attention_dtype` / `bitsandbytes`** — none appear in
  the serve path. Only two research write-ups mention bitsandbytes, as advice to avoid it.
- **`max_num_batched_tokens` 8192 → 16384** — see below. Real, but not in the direction
  anyone expected.

### The `max_num_batched_tokens` trap, which is the reverse of the documented one

The standing advice — from the 0.28.0 release notes, WI-1736 and the handoff — was to
**pin `max_num_batched_tokens` explicitly** so the default rise from 8192 to 16384 could
not silently eat gemma's headroom. I did that, defaulting it to the old 8192 and making it
overridable per entry.

**It broke gemma outright**, and it would have broken it on 0.27.1 too:

```
ValueError: To serve at least one request with the model's max seq len (16384),
13.76 GiB KV cache is needed, which is larger than the available KV cache memory (6.35 GiB).
```

**vLLM derives this value per model, and gemma-4's derived value is 2496** — 2048, raised
to accommodate a video input on a prefix-LM model. Not 8192, and not 16384. Forcing 8192
is a 3.3× increase over what the model actually resolves to; the extra activation memory
costs ~1.1 GiB of KV pool (7.42 → 6.35 GiB) and pushes engine startup below what a 16384
context needs. The engine never starts, so it fails loudly rather than silently — the one
mercy in it.

**The lesson generalises past this flag.** "Pin it so the default can't move under you"
is good instinct for a global default and actively wrong for a value the engine computes
per model: pinning replaces a correct per-model number with a plausible-looking constant.
The release note announcing a default change is describing the fallback for models that
have no derived value, not a number that applies to yours.

So `max_num_batched_tokens` is now a **first-class but opt-in** registry field
(`kvllm/registry.py`) — emitted only when an entry sets it, absent otherwise, with the
escape hatch available if some future model measurably needs it.

### The wrong turn, recorded because the audit rule is the point

Between those two states I misattributed the failure. gemma crash-looped immediately
after the bump, so I read it as 0.28.0's regression, wrote a detailed rejection into
`pyproject.toml` blaming 0.28.0's KV sizing for gemma-4's heterogeneous attention, and
reverted the pin to 0.27.1. **The revert did not fix it** — identical failure, identical
numbers, 13.76 GiB against 6.35 GiB. That is what exposed the real cause: the only
variable common to both was my own flag.

`docs/findings/evaluating-local-models.md`'s prime rule is *audit the harness before
blaming the model*. This is the same error one level down: I blamed the dependency before
auditing my own change, on the strength of the change being simultaneous with the
symptom. The cheap check that would have caught it immediately — serve the exact
pre-change command and see whether it works — is what eventually did, three serve cycles
later.

A useful diagnostic accident: `VLLM_USE_V2_MODEL_RUNNER=0` gave a *worse* KV pool
(4.54 GiB), which correctly ruled out 0.28.0's new V2 Model Runner as the culprit and
should have redirected suspicion at the flag sooner than it did.

### Step 1b — 0.28.0 evaluated, then NOT adopted, for a reason that is not serving

Having established that 0.28.0 serves gemma cleanly, adopting it turned out to be blocked
by the dependency graph rather than by the engine:

```
vllm==0.28.0    depends on click>=8.4.2
inspect-ai==0.3.244 depends on click<8.2.2      -> unsatisfiable
```

So taking 0.28.0 **forces `inspect-ai` to 0.3.263**, which in turn requires
`openai>=3.1.0`. That is not a serving change riding along with an eval change — it is the
reverse, and worse: **a serving-stack bump silently dragging the measurement instrument
forward.** The first re-baseline attempt died on exactly this, one suite into run 1:

```
PrerequisiteError: OpenAI Compatible API requires at least version 3.1.0 of package
openai (you have version 2.44.0 installed).
```

**Reverted to 0.27.1 for this sprint.** Ken's standing direction was *"continue moving
forward and only downgrade to 0.27.1 if we hit an issue"*, and handoff korg:1953
pre-authorises exactly this: *"If 0.28.0 misbehaves, you are not blocked — score on 0.27.1
and say so."*

The reasoning is specific to what this sprint is for. The re-baseline exists to answer
whether the defective card contaminated the board. Hardware and vLLM version were already
confounded and inseparable after the fact; adding the eval harness as a **third**
simultaneous change would have made the one question the sprint is asking unanswerable,
and would also have moved the board out from under sprint 16's noise floor (composite band
0.036), which every gap is read against.

`inspect-ai` is now **pinned** (`==0.3.244`, not floored) with that rationale in
`pyproject.toml`, so the coupling cannot re-fire as a silent rider on some future bump.
The resulting `uv.lock` delta is **one line** — the specifier — with no package versions
moved: the environment is byte-identical to sprint 17's.

**0.28.0 should be its own sprint**, taken together with the inspect-ai bump and a
re-measured noise floor. Filed as a follow-up.

### Step 2 — gemma re-baseline on the new card (WI-1475, widened scope)

`just eval-repeat gemma-4-31b-it-awq --n 3 --publish median`, published run 2 (median).

**The result is that there is no result, and that is the finding.**

| suite | 2026-08-20 (faulty card) | 2026-09-07 (new card) |
|---|---|---|
| agentic | 76% | 77% |
| assisted | 96% | 96% |
| code | 100% | 100% |
| judged | 77% | 77% |
| tools | 100% | 100% |
| vision | 100% | 100% |
| GPU MiB | 30,846 | 30,846 |
| tok/s | 73.0 | 72.9 |
| cold start | 92.0 s | 90.0 s |
| composite | 0.93 | 0.93 |

Every suite identical or within one point; the single point of agentic movement is well
inside that suite's own measured band of 0.110. tok/s reproduces to 0.1.

**So the defective card did not measurably contaminate gemma's board row.** Ken's *"a bit
of doubt toward the original evaluations"* is answered, in the reassuring direction, and
the answer is worth more than a changed number would have been: the July–August local rows
do not need wholesale re-measurement on suspicion of hardware. (WI-1502's stale-row retest
is about *version* staleness and is unaffected by this.)

**And the confound everyone braced for never existed.** The handoff and WI-1961 both
required the write-up to say that hardware and vLLM version are confounded and cannot be
separated after the fact — *"say so rather than crediting vLLM."* **That caveat does not
apply to this run.** Declining the 0.28.0 bump (above) meant gemma was re-measured on
vLLM 0.27.1, inspect-ai 0.3.244 and unchanged suites — the *same* stack as the 2026-08-20
row. **Only the card changed.**

That is precisely the de-confounding run WI-1961 specified and then wrote off as too
expensive once 0.28.0 looked landed:

> running gemma on **0.27.1** on the new card first, to isolate hardware from version …
> changing only the card answers *"how much did the faulty card corrupt our evaluations?"*
> for the whole board, not just gemma.

It came for free, as a side effect of a decision made for unrelated reasons. So the
result is not the hedged *"unchanged, but we cannot say whether hardware or version"* the
plan expected — it is the clean single-variable answer: **the replacement card reproduces
the faulty card's numbers, so the faulty card was not corrupting the evaluations.** That
generalises past gemma to the whole July–August window, which is what WI-1961 called the
real deliverable.

**A correction to sprint 17 falls out of the bands.** Sprint 17 attributed Qwen3.8's wide
`agentic` spread (0.190 at `xhigh`) to *"a variable-length reasoning phase in front of a
fixed ceiling"*, concluding that this is what erases local reproducibility. But gemma has
no reasoning phase at all and still bands **0.110 on `agentic`**, against 0.000 on all four
other suites — which are bit-identical across three runs. The reasoning phase is therefore
not the mechanism, or not the only one: **`agentic` is simply the noisy suite**, by a wide
margin, and any agentic gap under ~0.11 is not a finding regardless of which model produced
it. That materially raises the bar Qwen3.8's agentic advantage has to clear.

### Step 3 — Qwen3.8-27B scored (WI-1475, original scope)

`just eval-repeat qwen3.8-27b-nvfp4 --n 3 --publish median`. Served at **28,554 MiB**,
64 s cold start — reproducing sprint 17's figures exactly, with no illegal memory access
anywhere in three runs. That independently confirms sprint 17's corrected diagnosis: the
CUDA fault at `qwen_gdn_linear_attn.py:1058` was the failing card, not vLLM's Gated
DeltaNet path. Speculative decoding stayed off (no `--speculative-config`), per the
fairness decision.

**Board row: rank 9, composite ≈ 0.77**, against gemma at rank 2, ≈ 0.93.

Per-suite, both on the same stack, same card, same day:

| suite | gemma | band | qwen3.8 | band | read |
|---|---|---|---|---|---|
| `agentic` | 77% | 0.110 | 80% | 0.140 | **indistinguishable** — the 3-point gap is a quarter of either band |
| `code` | 100% | 0.000 | 100% | 0.000 | tie, both ceilinged |
| `judged` | 77% | 0.000 | 95% | 0.190 | qwen3.8 ahead, but see below |
| `tools` | 100% | 0.000 | 100% | 0.000 | tie, both ceilinged |
| `vision` | 100% | 0.000 | 93% | 0.040 | **gemma ahead**, and outside both bands |
| tok/s | 72.9 | | 29.1 | | gemma **2.5× faster** |
| GPU MiB | 30,846 | | 28,554 | | qwen3.8 2.3 GB lighter |
| cold start | 90 s | | 58 s | | qwen3.8 loads faster |

**The composite gap is almost entirely speed, not quality.** The formula is
`speed_factor × weighted mean`, with a speed floor of 10 and full credit at 40 tok/s.
gemma's 72.9 tok/s sits above the full-credit threshold and takes no penalty; Qwen3.8's
29.1 tok/s sits between floor and full and takes a large one. That single factor is what
moves Qwen3.8 from roughly gemma's quality neighbourhood to rank 9 — reading the composite
as a quality verdict would be a straightforward misreading of the board. The speed itself
is a consequence of `--enforce-eager` (no CUDA-graph capture, required on this card) plus
NVFP4 kernels on sm_120, with the MTP draft head deliberately disabled for comparability.

**The `judged` advantage is real in direction and unstable in size.** Qwen3.8's three
judged runs were 0.970, 0.950, 0.780 — a band of 0.190, the widest on the board. gemma's
were 0.770, 0.770, 0.770: bit-identical. So Qwen3.8 never scores *below* gemma on
`judged`, but the margin ranges from +0.01 to +0.20 depending on the draw. "Qwen3.8 is
better at judged" is supportable; "Qwen3.8 is +18 points at judged" is not — that is one
run's number quoted as if it were the effect size.

**Sprint 17's headline agentic advantage did not survive the healthy card.** The
quarantined batch suggested `agentic` 88–89% for Qwen3.8 against gemma's 76%. Measured
properly, it is 80% against 77%, inside the noise. The apparent 12-point lead was an
artifact of the contaminated run, and this is a second instance of the findings doc's
prime rule paying out.

**Board-row mechanics worth knowing:** `--publish median` publishes *one whole run* — the
one whose mean is the median — not a per-suite median composite. So the board row is run 2
in full (agentic 80%, judged 95%, vision 93%), which is internally coherent as a single
real run, while the band table's `median` column is computed per suite and can differ
(vision's per-suite median is 0.970). The row is a run, not a synthesis; that is the right
design, but the two numbers are not interchangeable.

### Quality with the speed factor removed — Qwen3.8 is second overall

Added 2026-09-07 after Ken asked what the comparison looks like if speed is set aside. The
scorer already separates this: `composite = speed_factor × base`, and `base` is the
quality-only weighted mean.

| model | quality (`base`) | speed factor | published |
|---|---|---|---|
| claude-sonnet-5 | 0.957 | 1.0 | 0.957 |
| **qwen3.8-27b-nvfp4** | **0.943** | **0.822** | 0.775 |
| gemma-4-31b-it-awq | 0.930 | 1.0 | 0.930 |
| claude-haiku-4-5 | 0.913 | 1.0 | 0.913 |
| qwen3.6-27b-awq | 0.848 | 1.0 | 0.848 |

**On quality alone Qwen3.8 ranks #2** — above gemma, above haiku, 0.014 behind sonnet-5.
Rank 9 is the 0.822 multiplier and nothing else.

**But it is a tie, not a win.** Per-run quality composites: gemma 0.906 / 0.930 / 0.930
(band 0.024), Qwen3.8 0.943 / 0.943 / 0.903 (band 0.040). Two of three Qwen runs beat every
gemma run and the third falls below all of them; the ranges overlap, and the +0.013 median
gap is a third of sprint 16's 0.036 composite band.

**Only two suites discriminate, and they point opposite ways.** Testing per-run *range
overlap* rather than comparing a difference to a band — the difference-vs-band test is too
crude and gets `judged` wrong:

| suite | gemma | qwen3.8 | verdict |
|---|---|---|---|
| tools | 1.00–1.00 | 1.00–1.00 | tie, ceilinged |
| code | 1.00–1.00 | 1.00–1.00 | tie, ceilinged |
| agentic | 0.66–0.77 | 0.66–0.80 | indistinguishable |
| `judged` | 0.77–0.77 | 0.78–0.97 | **Qwen wins outright** (no overlap) |
| `vision` | 1.00–1.00 | 0.93–0.97 | **gemma wins outright** (no overlap) |
| assisted | 0.63–0.88 | 0.80–0.88 | indistinguishable |

gemma's `judged` is pinned at 0.770 in all three runs and Qwen3.8's *worst* is 0.780, so
Qwen never loses that suite — a real win of uncertain size. Conversely gemma is a stable
100% on `vision` and Qwen never reaches it. By weight they nearly cancel: `judged`
contributes +0.016 to Qwen, `vision` −0.009 to gemma, `agentic` +0.007, netting +0.013.
Note `vision` carries **more** weight (0.15) than `judged` (0.10), so gemma's win is the
better-leveraged one.

**`tools` and `code` are dead ceilings** — 100% for both models in every run, and 65% of
the total weight. Between these two models they currently carry no discriminating
information at all, which is worth knowing before reading any composite as a capability
statement.

### Context capacity, which the board does not measure

| | gemma-4-31b-it-awq | qwen3.8-27b-nvfp4 |
|---|---|---|
| served context | 16,384 | 65,536 (registry 131,072) |
| KV pool | 7.42 GiB | 4.27 GiB |
| KV tokens | 20,765 | 129,615 |
| KV cost/token | ~375 KiB | ~34.5 KiB |
| concurrency at that context | 1.27× | 1.98× |

**Qwen3.8 holds 6.2× more context tokens in 58% of the VRAM — ~11× cheaper per token** —
because it is hybrid (16 of 64 layers keep a per-token KV cache) and serves with fp8 KV,
against gemma's dense full attention (head dims 256/512) at fp16 KV. gemma at 1.27×
concurrency can barely hold one full-length request and cannot go far past ~20k on this
card. No ranked suite measures this, and it is a real capability difference.

### The resident-slot answer

**Keep gemma-4-31b-it-awq resident.** It ties or beats Qwen3.8 on four of the five ranked
suites, is 2.5× faster, and the single suite where Qwen3.8 clearly leads is also its least
stable. Per the handoff's framing, *"these are indistinguishable, keep gemma resident"* is
the stronger result, and on quality that is very nearly what the numbers say — with speed
breaking the near-tie decisively in gemma's favour.

That said, the formal read of the result belongs to **korg:1479 / WI-1476**, deliberately a
separate slice. This sprint's job was to produce trustworthy numbers, and the raw per-case
output and judge rationales are kept under `eval-logs/` and
`model-research/evals/noise-floor/` for it.

### Step 3b — the `assisted` condition, which nearly got missed

`assisted` is **opt-in** (`evalrun._suites_for`: optional suites run only when named via
`--suite`), so neither model's five-suite run touched it. That had two consequences worth
catching:

- gemma's board `assisted: 96%` was a value **merged forward from 2026-08-20** — measured
  on the faulty card — and `merge_prior_suites` would have carried it silently onto a row
  dated 2026-09-07 and labelled a re-baseline.
- Qwen3.8 had no `assisted` value at all, against WI-1475's explicit scope of *"all five
  ranked suites plus the unranked `assisted` condition"*.

Run separately for both. `repeat.py` deserves credit here: its band table reports only
suites that were actually re-executed, so the merged-forward value was never mistaken for a
measurement with a spread of 0.

| model | runs | band | median | old board |
|---|---|---|---|---|
| gemma-4-31b-it-awq | 0.630, 0.870, 0.880 | **0.250** | 0.870 | 0.960 |
| qwen3.8-27b-nvfp4 | 0.800, 0.880, 0.800 | 0.080 | 0.800 | — |

**`assisted` is the noisiest thing on the board** at a 0.250 band — wider than `agentic`'s
0.110–0.140 and `judged`'s 0.190. gemma's median moved 0.960 → 0.870, but with a band that
wide the old value is comfortably inside noise, so this is *not* evidence of hardware
contamination; it is evidence that a single `assisted` run is close to uninformative. The
two models' ranges (0.630–0.880 and 0.800–0.880) overlap heavily: **indistinguishable.**

This also finishes off sprint 17's reproducibility framing. Sprint 17 attributed wide
spread to a variable-length reasoning phase in front of a fixed ceiling. gemma has no
reasoning phase and produces the widest band on the board. The agentic-family suites —
long multi-turn episodes with budgets and tool loops — are simply high-variance, whatever
the model.

### Step 3c — speculative decoding, measured unranked (WI-1475)

The MTP draft head, kept off for the ranked run so tok/s stays comparable with gemma.
Measured with `evalctl.measure_speed`, the same probe the board's tok/s comes from.

**It does not fit at the registry's context.** Enabling `--speculative-config` costs about
1.3 GiB of KV pool (4.27 → 2.99 GiB), and 131,072 context needs 4.88 GiB, so the engine
refuses to start (vLLM's own estimated ceiling: 72,000). Both arms were therefore measured
at `max_model_len 65536`, so context is not a confound between them:

| config | decode tok/s | TTFT s |
|---|---|---|
| speculative decoding **off** (control, 65536) | 29.4 | 0.09 |
| speculative decoding **on** (MTP, 3 tokens, 65536) | **54.1** | 0.11 |
| ranked board row (off, 131072) | 29.3 | 0.09 |

**1.84× on decode.** The control reproduces the ranked row's 29.3 tok/s, which confirms the
shorter context did not itself change the measurement.

This matters more than an unranked curiosity usually would, because **the composite gap
between these two models is almost entirely the speed factor**. That factor gives full
credit at 40 tok/s: Qwen3.8 at 29.3 is penalised, at 54.1 it would not be. Holding the
measured quality scores fixed, full speed credit puts its composite around **0.94** —
level with gemma's 0.93.

Three reasons that is a flag for korg:1479 and not a conclusion here:

1. **Quality under speculative decoding was not re-measured.** MTP verification is
   distribution-preserving in principle, and at temperature 0 the output should be
   unchanged, but this sprint did not verify it. Asserting the same scores at 54.1 tok/s is
   an assumption, not a measurement.
2. **It costs the long context** — 65,536 or less against the registry's 131,072. Whether
   that trade is acceptable depends on the use, which is Ken's call.
3. **The fairness decision stands for the ranked board.** gemma has no MTP head; leaving it
   on for a ranked row would compare a model with scaffolding to one without. That was the
   right call and this measurement does not overturn it — it says the ranked row understates
   what this model can do *on this box*, which is a different claim.

## Where it landed

**Board (2026-09-07, both on vLLM 0.27.1, new card, same day):**

| | gemma-4-31b-it-awq | qwen3.8-27b-nvfp4 |
|---|---|---|
| rank / composite | **2** / ≈ 0.93 | **9** / ≈ 0.78 |
| agentic | 77% (band 0.110) | 80% (band 0.140) |
| assisted | 87% (band 0.250) | 80% (band 0.080) |
| code | 100% (0.000) | 100% (0.000) |
| judged | 77% (0.000) | 95% (band 0.190) |
| tools | 100% (0.000) | 100% (0.000) |
| vision | 100% (0.000) | 93% (band 0.040) |
| tok/s | 72.9 | 29.3 (54.1 with MTP, unranked) |
| GPU MiB | 30,846 | 28,554 |

**Answers the sprint set out to get:**

1. **The faulty card did not contaminate the board.** gemma's re-baseline reproduces its
   2026-08-20 row to within a point on every suite, at identical VRAM and tok/s. The
   July–August local rows do not need re-measuring on hardware suspicion.
2. **The resident slot does not change.** gemma ties or beats Qwen3.8 on four of five
   ranked suites and is 2.5× faster as configured. Qwen3.8's one clear win, `judged`, is
   also its least stable measurement.
3. **vLLM 0.28.0 is evaluated but not adopted**, for a dependency-coupling reason rather
   than a serving one. Filed as WI-1962.

**Carry to korg:1479 / WI-1476 (reading the result), which is deliberately not this
sprint's job:**

- Qwen3.8's speed deficit is a *configuration* result, not a capability one — 1.84× is
  available from its MTP head, at the cost of the long context and with quality unverified
  under it. The ranked row understates the model on this box.
- `agentic`, `assisted` and (for Qwen3.8) `judged` all band far wider than sprint 16's
  composite figure of 0.036. Per-suite bands, not the composite band, are the right
  yardstick for per-suite gaps.

## Sprint-ship wiring added at the end of the sprint

`.sprint-defaults` (Ken's, gitignored — "PR, merge, local clean") and its
`.gitignore` entry ship with this sprint.

**kvllm turns out to have a real deploy need, so `.sprint-deploy` and
`.claude/skills/deploy-kvllm/` are added too.** Not a publish: consumers pull
`kvllm-client` as a **git dependency**
(`kvllm-client @ git+ssh://…#subdirectory=client`), so pushing `main` *is* the
distribution and there is no artefact to build.

The need is the *running service*. `kvllm.service` sets `WorkingDirectory` to
this checkout and execs `uv run python -m kvllm.registry serve
${KVLLM_MODEL_KEY}`, so it keeps executing whatever code it loaded at start.
Nothing in the workflow restarts it. **This sprint changed `build_serve_argv`** —
precisely the change that would otherwise land on `main` and sit inert on the
box until someone happened to restart it, with repo, board and running server
all disagreeing and nothing reporting it. Same shape as the failure kagviz's
deploy skill was written for (a served tree stamped with a branch commit for
three sprints).

The skill no-ops unless serve-path inputs actually changed since a stamp in the
git dir — most sprints here touch suites, eval code or docs, none of which the
served process executes — and it **refuses outright while an eval is in
flight**, because `just eval` orchestrates the service itself and a deploy
restart would fight it for the GPU an hour into a run. Restart order honours the
drain-to-zero rule.

**One bug found and fixed while verifying it**, worth recording because it would
have been invisible: the eval-in-flight check was written
`pgrep -f "kvllm.repeat|kvllm.evalrun"`, which **matches its own shell's command
line** and reports an eval running every time. A check that never passes is
indistinguishable from one that always fails — it would have refused every
deploy forever. Fixed to `pgrep -f "kvllm[.](repeat|evalrun)"`, the standard
bracket idiom, and verified in both directions: silent with no eval, and
detecting a process whose argv is `python -m kvllm.repeat …`.

Policy (Ken's call): restart with guardrails, rather than report-only.

## Follow-ups filed

- **WI-1962** — adopt vLLM 0.28.0 together with the inspect-ai bump; they are coupled
  through `click`. Includes the standing warning not to pin `max_num_batched_tokens`.

## Gate

`just check` green: ruff clean, 221 unit tests, 14 client-lib tests.

## Deployed

**2026-09-07, kai, from merged `main` `8566c0d`** — the first run of `deploy-kvllm`,
added by this sprint.

No stamp existed (first run), so the skill treated the tree as changed rather than
guessing. `deploy/` was unchanged, so the unit templates were not re-rendered; four
serve-path files had landed (`kvllm/registry.py`, `models.toml`, `pyproject.toml`,
`uv.lock`), which is exactly the case the restart exists for.

- **Eval guard:** clear, nothing in flight.
- **Drain:** 2 MiB / 0 compute processes within 10 s of stop.
- **Restart:** `kvllm.service` up in ~90 s, `kvllm-helper.service` restarted.
- **Verified:** `/v1/models` reports `gemma-4-31b-it-awq`, matching `KVLLM_MODEL_KEY`;
  `NRestarts=0`; 30,846 MiB, the expected band for gemma; and the running `vllm serve`
  argv is **byte-identical** to what `registry show` now produces — the check that
  proves this sprint's `max_num_batched_tokens` change is live and correctly emitting
  nothing for gemma.
- **Smoke:** answered `OK`, `finish_reason: stop`.
- Stamped `8566c0d`.

The box was already running equivalent code (the service was restarted by hand during
the sprint), so this restart changed no behaviour. It was still worth doing: it
establishes the stamp, and it exercised the deploy path end to end on its first use
rather than leaving it unproven until a sprint that depended on it.

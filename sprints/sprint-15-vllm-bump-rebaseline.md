# Sprint 15 — vLLM 0.26 bump + baseline refresh (gemma & sonnet-5)

_2026-08-20. korg #1472, #1473, proposal korg:1477. Branch `15-vllm-bump-rebaseline`.
Slice 1 of 3 in the Qwen3.8-27B program (korg:1480) — both eval slices are blocked on it._

## Goal

Get the stack onto a vLLM that can run Qwen3.8-27B's Gated DeltaNet layers, prove nothing
in the harness broke, and re-baseline the two leaders so the board stays trustworthy across
the version boundary. The #1/#2 gap is 0.01 (gemma-4-31b-it-awq 0.94, claude-sonnet-5 0.93,
both 2026-07-04) — a margin that cannot absorb drift from either direction.

Deliberately separated from the candidate eval: a version bump that silently shifts scores
is indistinguishable from a good challenger model.

## The version in the title is wrong, and finding that out was the first real work

The work item said "bump to 0.26.x". **`0.26.1` was never released to PyPI.** The only
0.26.x is 0.26.0 (2026-07-25); the next stables are 0.27.0 (2026-08-10) and 0.27.1
(2026-08-11). The `0.26.1rc1.dev608` build the vLLM recipe verified the consumer-Blackwell
NVFP4 path on is a dev build on the line *after* 0.26.0 — a line that never shipped as
0.26.1 and landed in 0.27.0 instead.

So landing 0.26.0 as written would have been a green sprint that left slice 2 still blocked.
**Landing target became 0.27.1.**

## Two-step bump, and why it was worth the extra step

The dependency surface made the risk asymmetric:

| target | torch | torchvision | flashinfer |
|---|---|---|---|
| 0.24.0 (was) | 2.11.0 | 0.26.0 | 0.6.12 |
| 0.26.0 | **2.11.0 — unchanged** | 0.26.0 | 0.6.14 |
| 0.27.1 | **2.13.0** | **0.28.0** | 0.6.16.post3 |

0.26.0 holds torch constant, so any breakage there is vLLM API churn. 0.27.1 is where the
torch/CUDA churn the work item predicted actually arrives, on an sm_120 card. Bumping in two
steps costs one extra `just check` (~1s) and buys unambiguous attribution.

It paid off immediately: **all the breakage was in step 1, and step 2 was clean.** The torch
2.11 → 2.13 jump — the thing flagged as the program's largest risk — cost nothing.

## The breakage was the resolver, not vLLM

Step 1 crash-looped the engine (systemd restart counter reached 25), failing in
`kernel_warmup` → `_warmup_ll_bf16_router_gemm` → `quack.layout_utils` with
`AttributeError: module 'cutlass.cute.core' has no attribute 'ThrMma'`.

Cause: `uv lock --upgrade-package vllm` upgrades *only* vllm and holds everything else at its
locked version where constraints allow. vLLM hard-pins `nvidia-cutlass-dsl[cu13]==4.6.0`, so
cutlass-dsl was forced 4.5.2 → 4.6.0 — but `quack-kernels` is specified as `>=0.4.0` with no
ceiling, so uv kept the locked 0.5.0 (2026-05-29), which predates cutlass-dsl 4.6.0
(2026-07-02) and references an API it removed, at import time.

Fix: `uv lock --upgrade-package vllm --upgrade-package quack-kernels`. The coupling is now
documented in `pyproject.toml` where the next person to bump will see it.

Worth noting for the findings doc: **the failure surfaced at kernel warm-up, well after model
load**, so it read as a serving bug rather than a dependency one. A fifth artifact class for
"audit the harness before blaming the model" — the harness here being the dependency graph.

## Provenance — scorecard schema v3

`#1473` asked for the re-baseline to record what produced each row. The board had only a
`date` column, which is exactly what let both kinds of drift hide.

- `vllm_version` (local rows) — read from the **serving endpoint's** `GET /version`, not this
  box's installed package. Under `--endpoint` the model may be served by another machine at
  another version; recording ours would be a confident lie.
- `model_id` + `model_created_at` (baseline rows) — from the Models API, which costs no
  tokens.

Both leaderboard renderers gained a `provenance` column; `leaderboard.json` carries the raw
fields. v2 cards have none of these and render `—` — unprovenanced, and visibly so.

Two things learned building it:

- **Inspect logs only the model string we asked for.** Verified against the 2026-07-04 sonnet
  logs: `model_usage` keys are the bare alias. Nothing on disk said which model produced a
  baseline row.
- **`created_at` is the load-bearing half, not the id.** Current-generation ids like
  `claude-sonnet-5` are complete as-is and never date-suffixed, so the id alone cannot reveal
  drift. Older generations differ — `claude-haiku-4-5` resolves to a dated `-20251001`
  snapshot.

## Re-baseline results

### gemma-4-31b-it-awq — reproduced within noise

| suite | 0.24.0 (2026-07-04) | 0.27.1 (2026-08-20) | delta |
|---|---|---|---|
| agentic | 0.84 | 0.88 | +0.040 |
| code | 1.00 | 1.00 | 0 |
| judged | 0.77 | 0.77 | 0 |
| tools | 1.00 | 1.00 | 0 |
| vision | 1.00 | 1.00 | 0 |

Four of five ranked suites were **bit-identical**. Decode speed was unchanged (73.2 → 73.1
tok/s), TTFT and cold start identical. VRAM rose 29,520 → 30,846 MiB (+1,326) — 0.27.1
allocates somewhat more at the same `gpu_memory_utilization`.

The whole agentic delta is two partial-credit judged episodes nudging up: `a2-disk-growth`
0.96 → 1.00 and `a6-wi-status-report` 0.68 → 0.92. `a3-oom-chain` failed identically at 0.0
in both runs — a reproducible failure, not noise. The judge is a pinned dated snapshot
(`claude-haiku-4-5-20251001`), so this is judge sampling variance on a partial-credit rubric,
not a stack change.

Composite 0.94 → 0.95.

`assisted` was re-run separately (it is optional and excluded from the default sweep, so the
first pass carried the 2026-07-03 score forward onto a card stamped `vllm_version: 0.27.1` —
mixed provenance on the one card whose point is provenance). Re-running it put every suite
log on 2026-08-20 under 0.27.1.

Its score moved much more than anything ranked: **0.75 → 0.96**. It is weight 0 by design —
a labeled alternate condition, shown but never ranked — so this does not touch the composite
or the #1 slot. Flagged rather than explained: the unassisted `agentic` suite moved only
+0.04 under the same pinned judge, so a +0.21 move on the assisted condition is worth a
second look before anyone reads meaning into the assisted-vs-agentic delta.

**Decision (the sprint's exit condition): the local board stays comparable across the bump,
so the remaining 15 local rows do NOT need re-running before slice 2.** They stay marked
unprovenanced (`—`) on the board, which is honest — they were measured under 0.24.0 — but
the gemma control says that boundary did not move scores.

### claude-sonnet-5 — the run I argued against, and the most informative one

Provenance came back `claude-sonnet-5 @2026-06-29` — published five days *before* the
2026-07-04 baseline and unmoved since. So the model was **not** republished, and the work
item's stated reason for the re-run (Anthropic changing the system prompt behind the API)
does not apply to direct Messages API calls, which carry only the system prompt Inspect
sends. I recommended skipping it; Ken ran it anyway. That was the right call.

| suite | 2026-07-04 | 2026-08-20 | delta |
|---|---|---|---|
| agentic | 0.77 | 0.91 | **+0.140** |
| judged | 0.85 | 0.92 | +0.070 |
| vision | 0.93 | 0.97 | +0.040 |
| code | 1.00 | 1.00 | 0 |
| tools | 1.00 | 1.00 | 0 |

**Every variable was held constant and the score still moved 0.14 on agentic.** The model
was not republished, suite versions are unchanged, the judge is a pinned dated snapshot, and
the vLLM bump is irrelevant to a hosted endpoint. There is nothing left for the delta to be
except run-to-run variance.

That is the sprint's most important result, and it is bad news for the premise. The proposal
opened with "a 0.01 gap cannot absorb two kinds of drift" — correct, but the drift that
matters is not versions on either side, it is **suite noise**, and at ±0.14 on a
25%-weighted suite (±0.035 on the composite from agentic alone) it dwarfs the gap by an
order of magnitude. Re-baselining does not fix that; repeated runs and a variance estimate do.

Consequence for the board as it stands: **claude-sonnet-5 retook #1 at 0.97, over gemma's
0.95.** That ordering should not be read as meaningful — it is well inside the noise this
same run measured.

### Bug found: `est $/run` has been undercounting

The re-run cost **$0.89**, not the $0.06 on the board — 15×. The old number was not stale
pricing, it was a partial count.

`_total_usage` sums the latest `.eval` log in each suite subdir under
`log_root = eval-logs/<model>/<date>/`. But `merge_prior_suites` carries suites forward from
earlier dates, and on the 2026-07-04 sonnet card three of five suites (agentic, code, tools)
point at logs under `2026-07-02`. Those tokens live in a different date dir and were never
counted — only `judged` and `vision` were. Old usage was 7,649 in / 2,776 out, which is
implausibly small for five suites; the full run is 31,381 in / 50,527 out / 322,568
cache-read / 101,463 cache-write.

The code comment states the opposite intent — "Usage/cost totals span ALL current suite logs
for this model/date (a partial --suite rerun must not shrink the reported full-suite cost)" —
so this is a comment asserting a property the implementation does not deliver. The fix is to
follow each suite's recorded `log` path from the card rather than globbing one date dir.

This matters beyond tidiness: the cost column is what answers "is the local model good enough
to stop paying for the frontier one", and it has been understating the frontier side for any
model assembled across multiple dates.

## Tests / gate

`just check` green at both checkpoints. 141 → 155 root tests (14 added for provenance),
14 client tests. `just smoke` (tool-call round-trip + LangChain reach) passed on 0.26.0 and
again on 0.27.1.

## Follow-ups

- `deploy/kvllm-helper.service.in` lacks `SuccessExitStatus=143`, so systemd marks the helper
  `failed` on every clean SIGTERM stop. Cosmetic, pre-existing, one line.
- `just loaded` calls bare `python`, which isn't on PATH in a non-login shell. Use `python3`
  or `uv run python`.
- The other 15 local rows on the board remain unprovenanced (`—`) and were measured under
  0.24.0. Whether they need re-running is the decision gated on gemma's result.

# Sprint 21 — Frontier baseline on the new harness: Sonnet 5 N=3, noise band re-measured

**Proposal:** korg:1998 (slice 1.5 of program korg:1994) · **Work item:** #1997 (Sonnet 5
re-baselined on the sprint-19 harness, N=3, the composite noise band re-measured).
**Branch:** `21-frontier-baseline` · **Driving model:** Claude Fable 5.1, as a headless karc
leg on kai under an overseer session on cleo.

## Goal

Sprint 19 moved the harness (vLLM 0.28.0, inspect-ai 0.3.263, anthropic 1.4.0) and
re-baselined both local rows on it; the frontier row was not re-run because a Sonnet round
costs ~$0.9 and needs Ken's go. Ken gave it on 2026-09-08 (WI-1997): Sonnet 5, N=3, ~$3,
Sonnet only. Two things hang on this row: `eval-config.toml`'s `[noise] composite_band`,
which the frontier baseline drives and which every `≈` on the board reads, and the
local-vs-frontier column, where sprint 20 just added two dated local rows under their served
configs and the reference row was the only one still on the 2026-08-20 stack.

API-only: no GPU, no serve, no restart. The resident stays up throughout.

## Premise check at sprint start (2026-09-09 02:34 UTC, kai)

- **#1997 holds to the line.** `[noise]` was `measured = "2026-08-20"`, `n = 3`,
  `composite_band = 0.036`; the Sonnet entry's `eval_date` was `2026-08-20`; the board's
  Sonnet row was the only reference row not dated on the sprint-19/20 stack.
  `kvllm/repeat.py` refuses provider-priced models without `--confirm-cost` and sets
  `manage_service = local and …`, so a `provider` entry never touches `kvllm.service`.
  No `claude-sonnet-5-all-2026-09-09` noise-floor key existed (the 2026-08-20 rows were
  keyed per suite, `agentic` and `judged`; this is the first all-suite Sonnet repeat).
- **Environment:** the resident `qwen3.8-27b-nvfp4` answering `/v1/models` at 122,880,
  `NRestarts=0`; ksandbox reachable (Docker 29.6.1); kmon's timer at 04:04 PDT, an hour
  and a half out — irrelevant to an API run, noted anyway.
- **One drift, favourable, caught before launch.** `eval-config.toml`'s pricing comment
  and the Sonnet entry's `notes` both said Sonnet 5's $2/$10 was an intro price reverting
  to $3/$15 after 2026-08-31 — which would have made every cost figure this sprint records
  1.5× understated. Checked against the live models overview
  (`platform.claude.com/docs/en/about-claude/models/overview`, 2026-09-09): Sonnet 5 is
  **$2 / $10 per MTok, no intro period mentioned**. The `[pricing]` rate is right; the two
  comments were wrong and are corrected below. Nothing else moved.

## The run

```
KVLLM_EVAL_DATE=2026-09-09 just eval-repeat claude-sonnet-5 --n 3 --publish median --confirm-cost
```

Launched 02:36 UTC, detached (`setsid nohup`, `PYTHONUNBUFFERED=1` — sprint 16's
block-buffering lesson), log at `.scratch/sprint21-sonnet-repeat.log`, watched by polling
the PID the runner wrote to `eval-logs/.run-state.json` rather than the shell's `$!`
(which was the `setsid` wrapper, dead in a second — the first monitor exited on it).
`--confirm-cost` on the strength of WI-1997; the gate printed `3 runs ≈ ~$2.51 (last full
run measured $0.84)`. Suites: tools, code, agentic, judged, vision — all five, so unlike
2026-08-20 the composite band this produces has every weighted suite repeated, `vision`
included (sprint 16's first follow-up). `KVLLM_EVAL_DATE=2026-09-09` is the same board
day as sprint 20's two local rows.

## The judge-token question, answered by reading the code first

WI-1502 comment 926 asked whether `_total_usage` folds the judge's tokens into the subject
model's cost, which would compress every frontier row's `est $/run` toward the same figure.
The code already answers it: `score.usage_from_log` buckets each log's `model_usage` by
exact model string — `anthropic/claude-sonnet-5` is the subject, everything else (the judge,
`anthropic/claude-haiku-4-5-20251001`) goes to `judge_usage` — and `est_cost_usd` is priced
from the subject bucket alone; `judge_cost_usd` is the other one. Every Sonnet card since
2026-08-20 carries both fields (judge ≈ $0.02/run). So for Sonnet the hypothesis is
structurally false, and the three runs below are the measurement that confirms the
mechanism produces stable numbers. For Haiku-as-subject the same exact-string split
separates `anthropic/claude-haiku-4-5` from the judge's dated id, so it should be clean too
— but that is WI-1502's retest to confirm, not this sprint's.

## Results — `claude-sonnet-5` ×3, 2026-09-09 (02:36–02:46 UTC, ~3 min a run)

Provenance `claude-sonnet-5 @2026-06-29`, unchanged since 2026-08-20. Suite versions
identical on both nights (tools 2, code 1, agentic 2, judged 2, vision 2), so the two
baselines are the same conditions on two harness stacks and two provider days.

| suite | run 1 | run 2 | run 3 | band | median | 2026-08-20 (published) |
|---|---|---|---|---|---|---|
| tools | 1.00 | 1.00 | 1.00 | 0.000 *(identical)* | 1.00 | 100% |
| code | 1.00 | 1.00 | 1.00 | 0.000 *(identical)* | 1.00 | 100% |
| agentic | 0.66 | 0.66 | 0.84 | **0.180** | 0.66 | 86% (0.73–0.88) |
| judged | 0.97 | 0.90 | 0.93 | **0.070** | 0.93 | 90% (0.88–0.92) |
| vision | 0.97 | 0.93 | 0.97 | **0.040** | 0.97 | 97% (never repeated) |
| composite | 0.920 | 0.908 | 0.955 | **0.047** | | 0.96 (0.927–0.963, band 0.036) |

**Published: run 1** (the median by mean pass rate: 0.898 / 0.920 / 0.948 → run 1). The
board now reads `claude-sonnet-5 ① 0.92` with `qwen3.8-27b-nvfp4 ② ≈ 0.92` (0.920 vs
0.917) — on the same harness, the same board day, the same suite versions, **the resident is
inside the noise band of the frontier baseline.** That is a fact about the board, not an RA
argument; the program handoff (korg:1995) says the board is not the instrument for that,
and it is not. `claude-haiku-4-5 ③ ≈ 0.91` still carries its 2026-07-04 row (WI-1502).

## Audit: read before believed (every case, three runs)

Per-case scores are in the run cards; the transcripts for the two suspicious patterns were
read in full.

- **Cut-offs, run 1 only:** `a3-oom-chain` (24 tool calls) and `a7-port-conflict` (25)
  ended `CUT OFF BY MESSAGE LIMIT` — the delivery-limited pattern gemma showed in sprint 20,
  here 2 of 27 case-runs, and never on 2026-08-20. Both passed 10/10 in runs 2 and 3. That
  one draw is most of run 1's 0.66 and the reason the agentic band is 0.18 rather than ~0.
- **`a5-wi-triage`, `a8-honesty`, `a9-sprint-plan` — the world contradicts the reference,
  and the judge scores the model's correct reading of the world as fabrication.** The prime
  rule, applied: in `a8` the base world's cron journal logs `CRON[6001]: (ken) CMD
  (/usr/local/bin/healthping.sh)` and the sandbox has no such file; Sonnet run 2 ran `cat`
  and `find` for it, got `No such file or directory`, and reported "one real problem —
  missing healthping.sh": judge 0/10, "fabricated a failure". In `a5` the world's own WI
  text says #105 is "DONE in practice — merged and deployed 7/1" and #102 is "BLOCKED on
  #105 … before it can go live"; Sonnet runs 1 and 2 said so and put #102 in ready:
  auto-zero, "claimed #102 blocker was resolved without evidence". In `a9` the base world's
  backup-sync journal reads `sync completed OK (2.1 GB, 31s)` on 7/2 while #201 says the
  sync has been failing since 6/30; Sonnet run 2 quoted the journal line and was scored as
  having "fabricated observed system state". Qwen's 2026-09-09 repeats fail `a5` three of
  three and `a8` two of three the same way; the artifact is symmetric across the frontier
  and local rows, so it does not bias the comparison, but it caps `agentic` for any model
  that cross-checks the world, and it was there on 2026-08-20 too (`a5` 0.64 / 0.28 / 0.0
  then). A fix is a ranked-condition change → agentic suite version bump → **WI-2005**.
  Sonnet's run-2 `a9` also scheduled the done item #206, which is a real fault the rubric
  correctly zeros; the two errors share a case, not a cause.
- **`a6-wi-status-report`** scored 0.96 in all three runs (judge 9/10, one minor
  deduction each time) — a stable partial, not a miss.
- `judged` moved 0.90–0.97 and `vision` 0.93–0.97, ordinary draws; `tools` and `code`
  were bit-identical three times, as in sprint 15 and 16.

**Cross-day, same conditions:** Sonnet's `agentic` median moved 0.86 → 0.66 between the
two nights (per run 0.73/0.88/0.86 → 0.66/0.66/0.84), wider than either night's
within-night band. Two run-1 cut-offs and two fabrication draws (`a8`, `a9` in run 2)
account for it case by case; nothing about `a1`–`a4` or `a6`–`a7` outside those draws
changed. This is the number sprint 16's second follow-up asked for — one data point on how
much of the frontier band is harness and how much is the provider moving under us — and
it says the within-night figure is a floor, as the config comment always claimed.

## Cost, per run, against the estimate

| run | subject tokens (in / out / cache read / cache write) | `est_cost_usd` | `judge_cost_usd` |
|---|---|---|---|
| 1 | 31,357 / 45,580 / 322,099 / 103,848 | **$0.84** | $0.021 |
| 2 | 31,344 / 47,363 / 291,657 / 84,635 | **$0.81** | $0.025 |
| 3 | 31,342 / 45,157 / 276,252 / 76,836 | **$0.76** | $0.023 |

Mean **$0.80 a run** at $2/$10 (subject $2.41 + judge $0.07 ≈ **$2.48 for the sprint**),
against the ~$0.9 estimate and 2026-08-20's $0.83–0.92. Input is constant to the token
(the suites are fixed), output varies 5%, and the cache figures are the agentic system
prompt being re-read — which is what the WI-1502 comment read as "cache-heavy". The
judge's ~15k input / 2k output tokens are tracked separately at ~$0.02 and are not in the
subject figure. **Comment 926's hypothesis is contradicted for Sonnet**: judge tokens do
not land in the subject's card, so Haiku's $0.93 recomputation cannot be explained by
judge leakage either — if it holds up on the field retest, Haiku genuinely uses ~2× the
tokens. Not chased further here.

## The band: 0.036 → 0.070 — the rule unchanged, the governing row changed

The Sonnet runs give 0.047 for the frontier row. The same-day all-suite bands for the two
local rows (sprint 20's repeats, scored with the board's own `composite()` —
`.scratch/sprint21-band.py`): `qwen3.8-27b-nvfp4` 0.911–0.951 (**0.040**),
`gemma-4-31b-it-awq` 0.801–0.871 (**0.070**). The 2026-08-20 rule is "a comparison
involves both models, so the noisier one governs"; its rationale for *which* row that was
— the hosted one, because a local model at temperature 0.0 is close to deterministic — was
a temperature-0.0 property, and since sprint 20 the local rows run at their served
generation configs, where `agentic` moves 0.17–0.18 for all three. Flagged to the overseer
as a ruling (korg:1998 comment 1459). **Ruled: `composite_band = 0.070`** — the rule
unchanged, the governing row now gemma — because a floor narrower than a measured local
band would let a local-vs-local gap be read as a finding, which is what the number exists
to prevent.

Board effect after `just board-rebuild`: one `≈` added over 0.047 (`qwen3.6-27b-awq 0.85
≈ claude-haiku-4-5 0.91`), and with it the **top five are one cluster** — sonnet 0.92,
qwen3.8 ≈ 0.92, haiku ≈ 0.91, qwen3.6-27b ≈ 0.85, gemma ≈ 0.83 (qwen3.6-35b at ≈ 0.82 was
already tied to gemma). Two of those five rows are dated on the old stack (WI-1502).

## Config, docs, board

- `eval-config.toml`: `[noise]` → `measured = "2026-09-09"`, `composite_band = 0.070`,
  comment rewritten — rule unchanged, governing row changed, the three per-suite bands
  beside it; the pricing comment corrected (no intro period); the header's `--rescore`
  reference (a flag that no longer exists) replaced by the new recipe.
- `justfile`: **`just board-rebuild`** — regenerates the leaderboard from the existing
  scorecards after a config edit, no model runs. The `[noise]` change needed it; the
  eval-config header had been pointing at a flag that was gone.
- `models.toml`: `eval_date = "2026-09-09"` on the Sonnet entry (written by the publish
  step); the `notes` pricing text corrected by hand.
- `docs/findings/evaluating-local-models.md`: a dated note under the noise-floor corollary
  — point 1 ("a hosted baseline is an order of magnitude noisier") superseded with the
  three bands and the cross-day figure; points 2 and 3 stand.
- `model-research/evals/`: `claude-sonnet-5-2026-09-09.{json,md}`, the three run cards
  and `summary.json`/`README.md` under `noise-floor/claude-sonnet-5-all-2026-09-09/`,
  leaderboard `.json/.md/.html` rebuilt (the `≈` note reads 0.070, N=3, 2026-09-09).
- Ranked conditions unchanged: nothing under `suites/` was touched.

## The resident, throughout

`kvllm.service` `NRestarts=0`, `ActiveState=active` at launch (02:36) and at the runner's
exit (02:46); `/v1/models` answered `qwen3.8-27b-nvfp4` / 122,880 both times. The runner
printed no `[orchestrate]` line — `manage_service` was false, as the code says it must be
for a `provider` entry.

## Deploy expectation at ship

`deploy-kvllm` diffs `SERVE_PATHS` from the stamp (`b147a62`) to merged `main`, and
`models.toml` is on that list. This sprint changes it — `eval_date` and `notes` on the
**Sonnet** entry, a baseline row the unit never serves — so the skill will see a serve-path
change and **restart the resident on an inert diff** (~51 s, its step 4 will find the
running argv byte-identical to `registry show`). Not a no-op, unless the overseer prefers
to hold the ship or the skill grows an exception for baseline entries; either is a call
outside this leg. Nothing else on the list changed.

## Follow-ups

- **WI-2005** — `a5`/`a8`/`a9`: fix the world (materialise the cron script, reconcile the
  WI text and the reference), bump the agentic suite version, re-run the three
  current-stack rows under it.
- **Haiku** stays with WI-1502; its cost figure is now the interesting one, since the
  judge-leak explanation is gone.
- `assisted` unchanged, as in sprints 19 and 20; not this leg's.

## Gate

`just check` green: ruff clean, 262 unit tests, 31 client tests. `.scratch/` and
`eval-logs/` are gitignored; the API key appears in no committed file and no log line.

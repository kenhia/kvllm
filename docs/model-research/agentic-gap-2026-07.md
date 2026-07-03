# The agentic gap, decomposed — 2026-07-03

_Calibration pass over the agentic-v2 transcripts from the full-coverage sweep. Question
(sprint 8): is the local 44%-vs-frontier-77% agentic gap an investigation failure, a
reporting failure, or a harness artifact? Answer: **all three, in separable populations** —
and two of the three have levers._

## The matrix (from scorecard case meta + transcript reads)

| model | agentic | submitted | cut off | judge when submitted | classification |
|---|---|---|---|---|---|
| claude-sonnet-5 | 77% | 9/9 | 0 | 7.9/10 | reference |
| claude-haiku-4-5 | 68% | 9/9 | 2 | 6.6/10 | reference |
| qwen3-vl-8b | 44% | 9/9 | 3 | 3.8/10 | **capability**: delivers, mediocre analysis |
| qwen2.5-14b-awq | 42% | 8/9 | 0 | 3.4/10 | capability |
| gpt-oss-20b | 38% | 8/9 | 5 | 5.1/10 | mixed: budget + mid analysis |
| gemma-4-12b-it | 32% | 3/9 | 6 | **9.3/10** | **delivery**: frontier analysis, no budget discipline |
| qwen2.5-7b | 28% | 8/9 | 1 | 2.1/10 | capability |
| qwen3.5-9b | 24% | 4/9 | 5 | 5.0/10 | delivery + mid |
| glm-4.7-flash | 19% | 2/9 | 7 | 6.5/10 | **delivery**: 25.7 calls/episode, never wraps |
| gemma-4-31b-awq | 12% | — | — | 10/10 (n=1) | **sample death** (7/8 ctx overflow) |
| devstral-small-2 | 11% | 1/9 | 8 | 10/10 (n=1) | **delivery** (extreme) |
| llama-3.1-8b | 11% | 8/9 | 0 | 0.4/10 | capability (floor) |
| qwen3.6-35b-a3b | 8% | — | — | 6.0 (n=1) | sample death (6/8) |
| qwen3.6-27b | 0% | — | — | — | sample death (9/9) |
| qwen2.5-coder-7b | 2% | 9/9 | 9 | 0.3/10 | capability floor + 4 fabrications |

## Failure mode 1 — sample death by context overflow (HARNESS BUG, fixed)

Models served with reduced `max_model_len` (the VRAM-fit recipe: 27B/35B at 8K, 31B at 16K)
outgrow their window mid-episode → vLLM 400 `maximum context length` → **Inspect records the
sample as errored, no score at all**. The model's whole investigation is discarded: the 27B
was running parallel bash calls and reading journals when it died, all 9 episodes; the 31B's
one surviving episode (a1) scored a **perfect 1.0 with judge 10/10**.

Fix shipped: `react(truncation="auto")` — conversation truncates and the episode continues.
Only engages where the sample would have died, so completed-episode scores are unchanged (no
version bump). **Re-run `--suite agentic` for: qwen3.6-27b-awq, gemma-4-31b-it-awq,
qwen3.6-35b-a3b-awq** — their current 0/12/8% are floors, not measurements.

## Failure mode 2 — delivery failure (REAL, but a different problem than "can't investigate")

The strongest 2026 models investigate at frontier quality — **gemma-4-12b's submitted
reports average 9.3/10, devstral and gemma-31b hit 10/10** — but they don't respect the
step budget: they keep investigating until the 40-message limit kills the episode
(gemma-12b 6/9 cut off, devstral 8/9, glm-4.7 7/9). GLM averages 25.7 tool calls per
episode; Sonnet averages 8.7 and always ships.

This is exactly the failure the Haiku calibration hit (18%→68% after limit 25→40 + a
step-budget sentence). The remaining lever is a **wrap-up nudge**: react's `on_continue`
hook can inject "N messages remain — submit your report now" near the limit. That's a suite
change (fair: every model gets it) → would need a version bump; logged as a follow-up
experiment. What it would measure better: analysis quality. What it would measure worse:
self-pacing — which a real homelab controller also needs. Decide before Phase 6.

## Failure mode 3 — capability (the verdict stands for these)

llama-3.1 (0.4/10), qwen2.5-coder (0.3/10, 4 fabrications), qwen2.5-7b (2.1/10) submit
promptly and write garbage — wrong culprit, invented causal chains, template answers.
qwen3-vl-8b, the "best local", is disciplined (9/9 submitted) but shallow (3.8/10). No
harness change rescues these; the gap to Haiku here is real model capability.

## What this means for the controller (sprint goal)

- The **planning slice** was already solved at frontier tier (a9, both baselines 9-10/10).
- The **investigation slice** now looks *partially* solvable locally: gemma-4-12b analyzes
  at frontier quality and needs pacing help, not intelligence. A controller design that
  pre-structures the investigation (checklist steps, bounded probes — same philosophy as
  the WI-triage pre-work tool, korg #105) plays directly to what locals CAN do.
- True frontier advantage is **self-directed long-horizon work** — knowing when to stop.

## Actions

- [x] `truncation="auto"` — fixes mode 1.
- [ ] Re-run agentic for the three sample-death models (after the judged sweep frees the GPU).
- [x] **`assisted` suite built** (2026-07-03) — the mode-2 lever, done right: same nine
  tasks/facts/judge as agentic, but under controller scaffolding — message limit 60 (vs 40),
  time limit 900s ("slower but capable" explicitly fits the hybrid plan), and a two-phase
  budget: investigation runs to limit−8, then the harness injects a wrap-up demand ("do not
  run more tools; submit() now") with 8 messages reserved for delivery. Weight 0.0 — shown
  on the board, never ranked; the ranked `agentic` column is untouched, so nothing skews.
  Opt-in: `just eval <key> --suite assisted` (excluded from `--all` sweeps and resume checks).
  **The assisted−agentic delta per model is the measurement**: how much of the frontier gap
  is pacing (controller-fixable) vs capability. Baselines should run it too — their delta
  ≈ 0 is the control. Predictions: gemma-4-12b jumps hard; llama-3.1 doesn't move.
- [ ] gemma-4-12b: watch as primary local-controller candidate once mode-1 rerun lands.

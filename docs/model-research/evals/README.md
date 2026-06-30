# Evals

Our own "worth trying / has issues / skip" testing of models **on `kai`** — not online leaderboard
scores, but whether a model actually serves, fits, and performs on the 5090.

**The human view:** open [`leaderboard.html`](leaderboard.html). Agent-friendly siblings:
[`leaderboard.json`](leaderboard.json) (source of truth) and [`leaderboard.md`](leaderboard.md).
Per-run detail lives in `<model>-<date>.{json,md}`.

## Run one

```sh
just eval qwen2.5-7b-instruct           # serve it, run the suites, score, write artifacts
just eval qwen3-vl-8b-instruct --suite tools   # one suite only
```

`just eval` **orchestrates the service**: it stops `kvllm.service` to free the GPU, serves the target
standalone, runs the operational gate + the suites matching the model's registry `capabilities`, then
restarts the service. It writes a scorecard, rebuilds the leaderboard, and stamps
`tested` / `eval_verdict` / `eval_date` back into [`../../../models.toml`](../../../models.toml).

## What's measured

- **Operational gate** (always): serves on sm_120, fits VRAM, cold-start seconds, tokens/sec. This is
  the main "has issues" detector — a model that won't serve here is `skip` no matter its online rep.
- **`tools`** (mechanical): a tool-calling battery — single/enum/integer args, `tool_choice=required`,
  a negative (don't-call-when-unneeded), a multi-turn round-trip, and parallel calls.

**Verdict:** `worth trying` (served + all suites ≥ 80%) · `has issues` (served, a suite below) ·
`skip` (didn't serve). Verdicts ride on objective checks; the LLM-judge (below) is for fuzzy quality.

## Planned (Sprint 7 follow-ups)

- **coding** suite — execute generated code against hidden tests in a **container** (Docker,
  `--network none`, limits) → pass@1.
- **vision** suite — labeled image Q&A (OCR / charts / GUI screenshots) for `vision` models.
- **agentic** suite — a scripted mock-tool homelab scenario (goal completion / error recovery).
- **LLM-judge** (hybrid) — a cloud Claude grades open-ended coding/agentic quality where mechanical
  scoring can't.

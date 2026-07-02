# Evals

Our own "worth trying / has issues / skip" testing of models **on `kai`** — not online leaderboard
scores, but whether a model actually serves, fits, and performs on the 5090. Harness v2 (Sprint 8)
runs suites as **Inspect AI** tasks ([`evals/`](../../../evals/)); design in
[`sprints/fable-planning/`](../../../sprints/fable-planning/README.md).

**The human view:** open [`leaderboard.html`](leaderboard.html). Agent-friendly siblings:
[`leaderboard.json`](leaderboard.json) (source of truth) and [`leaderboard.md`](leaderboard.md).
Per-run detail lives in `<model>-<date>.{json,md}`; full episode transcripts in `eval-logs/`
(gitignored — open with `uv run --group eval inspect view --log-dir eval-logs/<model>/<date>`).

## Run

```sh
just eval qwen2.5-7b-instruct              # serve it, gate, run its suites, score, write artifacts
just eval-all                              # sweep the registry (resumable; skips current + gate-skipped)
just eval <key> --suite tools              # one suite only
just eval <key> --endpoint http://host:8000/v1   # eval an already-served /v1 (no orchestration)
just eval-sandbox-smoke                    # prove the Docker sandbox path (mock model, no GPU)
```

`just eval` **orchestrates the service**: it stops `kvllm.service` to free the GPU, serves the
target standalone, runs the operational gate + the suites matching the model's registry
`capabilities`, then restarts the service. It writes a scorecard, rebuilds the leaderboard, and
stamps `tested` / `eval_verdict` / `eval_date` back into [`../../../models.toml`](../../../models.toml).
`just eval-all` resumes: models already scored on current suite versions are skipped (`--force`
reruns; gate-failed models need `--retry-skips`).

## What's measured

- **Operational gate** (always): serves on sm_120, fits VRAM, cold-start seconds, **TTFT** and
  **decode tok/s** (streamed, median of 3 — v1's single blended sample is gone). A model that
  won't serve here is `skip` no matter its online rep.
- **`tools` v2** (mechanical, 11 cases): single/enum/integer args, `tool_choice=required`, a
  negative don't-call case, multi-turn round-trip, parallel calls, **plus** array args, a
  distractor tool, tool-error recovery, and exact-argument adherence.

Suites are **versioned**; the leaderboard marks scores from older versions with † until re-run.

**Verdict:** `worth trying` (served + all suites ≥ 80% + decode ≥ 10 tok/s) · `has issues` ·
`skip` (didn't serve). Verdicts ride on objective checks; the LLM-judge (Phase 3) is for fuzzy
quality.

## Roadmap (sprints/fable-planning/05-roadmap.md)

- **coding** suite (Phase 2, spec ready) — sandboxed write-run-fix against hidden tests.
- **weighted leaderboard + judge** (Phase 3) — composite ranking via `eval-config.toml`.
- **agentic** suite + sandbox host (Phase 4) — fixture-homelab episodes.
- **vision** suite (Phase 5) — for `vision` models.

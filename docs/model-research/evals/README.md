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
just eval <key> --suite tools              # one suite only (--force re-runs it fresh)
just eval <key> --endpoint http://host:8000/v1   # eval an already-served /v1 (no orchestration)
just eval claude-haiku-4-5                 # frontier baseline: no GPU, runs the same suites, costs $
just eval-sandbox-smoke                    # prove the Docker sandbox path (mock model, no GPU)
```

`just eval` **orchestrates the service**: it stops `kvllm.service` to free the GPU, serves the
target standalone, runs the operational gate + the suites matching the model's registry
`capabilities`, then restarts the service. It writes a scorecard, rebuilds the leaderboard, and
stamps `tested` / `eval_verdict` / `eval_date` back into [`../../../models.toml`](../../../models.toml).
`just eval-all` resumes: models already scored on current suite versions are skipped (`--force`
reruns; gate-failed models need `--retry-skips`).

**Sandboxes run on `ksandbox`** (`[sandbox].docker_host` in
[`eval-config.toml`](../../../eval-config.toml); `DOCKER_HOST` env overrides, empty = local
Docker). The coding/agentic containers get their own machine — no CPU contention with vLLM, and
untrusted model-generated code stays off `kai`. Background:
[`fable-planning/04-sandbox-host.md`](../../../sprints/fable-planning/04-sandbox-host.md).

## What's measured

- **Operational gate** (always, local models): serves on sm_120, fits VRAM, cold-start seconds,
  **TTFT** and **decode tok/s** (streamed, median of 3), context probe at 75% of max_model_len.
- **`tools` v2** (mechanical, 11 cases): arg types, `tool_choice=required`, a negative
  don't-call case, multi-turn round-trip, parallel calls, array args, a distractor tool,
  tool-error recovery, exact-argument adherence.
- **`code` v1** (15 sandboxed tasks, c1–c4): write-run-fix against hidden tests in a
  network-off container.
- **`agentic` v2** (9 fixture-homelab episodes, a1–a9): investigate a "machine" through a real
  shell (systemd/korg/log shims), report findings — triage, root-cause chains, honesty under
  nothing-is-wrong, WI cross-referencing, and sprint planning (a9). Scored hybrid: mechanical
  checks + calibrated LLM judge.
- **`judged` v1** (12 free-form answers): calibrated Haiku judge (12/12 within ±1 of Ken's hand
  scores — see [`calibration/`](calibration/)).

Suites are **versioned**; the leaderboard marks scores from older versions with † until re-run.

**Ranking:** composite = speed_factor × weighted mean of suite scores
([`eval-config.toml`](../../../eval-config.toml) weights; re-weighting re-ranks without
re-running via `--rescore`). **Verdict:** `worth trying` · `has issues` (composite < 0.55, any
suite < 0.40, or decode ≤ 10 tok/s) · `skip` (didn't serve) · `baseline` 🌐 (API models —
ranked for comparison, never swept by `--all`, leaderboard shows **est $/run** from measured
token usage).

## Roadmap (sprints/fable-planning/05-roadmap.md)

- **vision** suite (Phase 5) — for `vision` models.
- VM layer on ksandbox (snapshot/revert full-machine episodes), computer-use after that.

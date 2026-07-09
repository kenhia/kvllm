# kvllm — agent orientation

Serving (vLLM on a 32 GB RTX 5090) + model evaluation (Inspect AI suites, calibrated judge,
weighted leaderboard). Human owner: Ken. Read this, then go straight to what you need.

## Read these before designing anything eval- or model-related

- `docs/findings/evaluating-local-models.md` — **evergreen lessons.** Prime rule: when a
  score looks wrong, audit the harness before blaming the model (four artifact classes
  documented). Also: frozen-ranked-suite + labeled-condition pattern, judge calibration.
- `docs/findings/local-model-guidance-2026-07.md` — dated role guide (which model for what)
  + the hybrid local/frontier architecture readout. Check the date; regenerate via evals if
  the landscape has moved.
- `model-research/evals/leaderboard.md` — current board. Scorecards sit next to it;
  `model-research/` is research output generally, `suites/` is suite source code.

## Conventions

- Sprint work happens on a branch named like the sprint doc (`sprints/sprint-NN-slug.md` →
  branch `NN-slug`), merged to `main` with `--no-ff` at close. korg tracks sprints as work
  items (kvllm project).
- `just check` (lint + unit tests + client-lib tests) must pass before any commit; suite changes also need
  `just test-agentic-suite` / `just test-coding-suite` (Docker, no GPU).
- Ranked suites are versioned — changing episode CONDITIONS needs a version bump; fixes
  that only affect would-have-crashed samples don't. Never tune conditions under a ranked
  number; add a weight-0 labeled condition instead (see `assisted` in `suites/agentic.py`).
- The judge's `calibrated = true` flag (eval-config.toml) is load-bearing: change the judge
  model → rerun the human calibration protocol (`model-research/evals/calibration/`).
- GPU discipline: one model per process; `just eval` orchestrates `kvllm.service` itself.
  Don't kill/serve rapidly (GSP wedge history); `nvidia-smi` should drain to ~0 between
  models. Sandboxes run remotely (`[sandbox].docker_host`) — Inspect episodes never execute
  on this box.
- Secrets: `ANTHROPIC_API_KEY` lives in `.env` (gitignored). Never commit `.env`,
  never echo the key.

## Quick map

`kvllm/` package (registry/serve, evalrun, evalctl, score, helper) · `client/` the
`kvllm-client` distribution (shared LLM client for kagent/kmon/klams-mind; own pyproject —
no vLLM dependency) · `suites/` Inspect
tasks + fixtures · `model-research/` outputs incl. `evals/` scorecards+board · `docs/`
usage docs + `findings/` · `sprints/` history + `planning/` architecture · `eval-logs/`
transcripts (gitignored).

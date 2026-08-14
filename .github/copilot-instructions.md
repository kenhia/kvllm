<!-- kproject:begin — managed by kprojects; do not edit inside this block -->
## kproject conventions

This project uses the kproject minimal harness
(<https://github.com/kenhia/kprojects>). Keep context small; prefer doing
over ceremony.

### Layout

- `sprints/` — the project's evolution, one record per PR-sized unit of
  work (a "sprint")
  - `planning/` — planning docs; at minimum `roadmap.md` (the general plan)
  - `review/` — more formal reviews as the project matures
  - sprint records: `###-<short-name>.md` for small projects, or a
    `###-<short-name>/` directory of files for larger/more formal ones
  - a sprint record is one informal narrative: goal, decisions, what
    shipped, follow-ups — written during the sprint, not after
- `docs/` — project documentation, architecture, usage
- `.scratch/` — git-ignored scratch space for user or agent ephemera;
  use it instead of /tmp
- `justfile` — dev recipes; default recipe is `@just --list`; `just check`
  runs the CI gates; `just deploy` (or variants) if the project deploys
- `.env` — git-ignored; tokens and environment vars

### Workflow

- One sprint ≈ one PR. Sprint proposals and work items are managed in
  `korg`; durable cross-project knowledge goes in `klams`.
- If the korg or klams MCP tools are unavailable in your session, say so
  up front — don't silently work around missing infrastructure.
- TDD preferred: write the failing test first when practical.

### Tooling preferences

- Python managed by `uv`; lint/format with `ruff`; typecheck with `ty`
  (astral toolchain)
- License is MIT unless specifically directed otherwise
<!-- kproject:end -->

## Project

kvllm — serving (vLLM on a 32 GB RTX 5090) + model evaluation (Inspect AI
suites, calibrated judge, weighted leaderboard). Human owner: Ken. Read this,
then go straight to what you need.

### Read these before designing anything eval- or model-related

- `docs/findings/evaluating-local-models.md` — **evergreen lessons.** Prime
  rule: when a score looks wrong, audit the harness before blaming the model
  (four artifact classes documented). Also: frozen-ranked-suite + labeled-
  condition pattern, judge calibration.
- `docs/findings/local-model-guidance-2026-07.md` — dated role guide (which
  model for what) + the hybrid local/frontier architecture readout. Check the
  date; regenerate via evals if the landscape has moved.
- `model-research/evals/leaderboard.md` — current board. Scorecards sit next to
  it; `model-research/` is research output generally, `suites/` is suite source
  code.

### Conventions

- Sprint records here predate the harness naming and keep it:
  `sprints/sprint-NN-slug.md` → branch `NN-slug` (not `###-<short-name>.md`).
  Merged to `main` with `--no-ff` at close. korg tracks sprints as work items
  (kvllm project).
- `just check` (lint + unit tests + client-lib tests) must pass before any
  commit; suite changes also need `just test-agentic-suite` /
  `just test-coding-suite` (Docker, no GPU).
- Ranked suites are versioned — changing episode CONDITIONS needs a version
  bump; fixes that only affect would-have-crashed samples don't. Never tune
  conditions under a ranked number; add a weight-0 labeled condition instead
  (see `assisted` in `suites/agentic.py`).
- The judge's `calibrated = true` flag (eval-config.toml) is load-bearing:
  change the judge model → rerun the human calibration protocol
  (`model-research/evals/calibration/`).
- GPU discipline: one model per process; `just eval` orchestrates
  `kvllm.service` itself. Don't kill/serve rapidly (GSP wedge history);
  `nvidia-smi` should drain to ~0 between models. Sandboxes run remotely
  (`[sandbox].docker_host`) — Inspect episodes never execute on this box.
- Secrets: `ANTHROPIC_API_KEY` lives in `.env` (gitignored). Never commit
  `.env`, never echo the key.

### Quick map

`kvllm/` package (registry/serve, evalrun, evalctl, score, helper) · `client/`
the `kvllm-client` distribution (shared LLM client for kagent/kmon/klams-mind;
own pyproject — no vLLM dependency) · `suites/` Inspect tasks + fixtures ·
`model-research/` outputs incl. `evals/` scorecards+board · `docs/` usage docs +
`findings/` · `sprints/` history + `planning/` architecture · `eval-logs/`
transcripts (gitignored).

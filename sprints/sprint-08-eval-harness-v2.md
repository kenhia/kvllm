# Sprint 8 — Eval harness v2 (Inspect AI, sandboxed agentic+coding, weighted leaderboard)

_2026-07-02 on `kai`. korg #104. Branch `08-eval-harness-v2`. Builds on
[Sprint 7](sprint-07-eval-harness.md). Planning in [`sprints/fable-planning/`](fable-planning/README.md)
(repo review, stack decision, suites/scoring design, sandbox-host plan, phased roadmap)._

## Goal

Turn the Sprint 7 MVP eval into the rich harness Ken wants: agentic + coding episodes in sandboxes,
frontier-model judging, a weighted composite leaderboard. This sprint covers **roadmap Phase 0**
(hygiene) — see [`fable-planning/05-roadmap.md`](fable-planning/05-roadmap.md) for the full phased
plan (Phase 1 — episode runner core + Inspect AI migration — is next).

## Plan (Phase 0, per the roadmap)

Review items 4, 7, 10 from [`fable-planning/01-current-state-review.md`](fable-planning/01-current-state-review.md):
commit the outstanding v1 eval results as a clean baseline; add unit tests for the eval package's
pure functions (none existed); fix the `--today` default (`"undated"` when run outside `just`).

## What shipped

- **Unit tests for `kvllm/eval/`** (37 tests, `tests/test_eval_suites.py` +
  `tests/test_eval_runner.py` + `tests/test_eval_report.py`): every `score_case` kind
  (tool_call/no_tool/parallel/multi_turn/unknown) + `_args_subset`, `_verdict`'s threshold/speed-cap
  logic, and `report.py`'s scorecard/leaderboard rendering + `models.toml` write-back (including a
  regression test for the Sprint 7 dotted-key bug).
- **`pytest` added to the `dev` dependency group**; `[tool.pytest.ini_options]` in `pyproject.toml`
  (`pythonpath = ["."]`) so tests import `kvllm` without an editable install.
- **`just test`** (`uv run --group dev --group eval --group test pytest tests/ -q` — needs all
  three groups: `tomlkit` for report tests, `openai` for runner import) and **`just check`**
  (`lint` then `test`).
- **`--today` now defaults to `date.today().isoformat()`** in `kvllm/eval/runner.py` instead of
  `"undated"`, so `python -m kvllm.eval <key>` run directly (not via `just eval`) still dates its
  scorecard sensibly.
- **Committed the outstanding v1 eval results**: 3 scorecards (`deepseek-r1-distill-qwen-7b`,
  `internvl3-8b`, `qwen2.5-coder-7b-instruct`) + refreshed leaderboard + `models.toml` verdicts,
  as their own commit — a clean baseline before harness v2 work starts.

## Decisions & discoveries

- **`just eval`/`just lint` already used `uv run --group dev`**, which — surprisingly — only
  activates the requested groups; a bare `uv sync --group dev` (not `uv run`) actively
  *uninstalls* other groups' packages. `just test` needs `--group dev --group eval --group test`
  together since the eval package pulls in `tomlkit` (eval) and `openai` (test, for
  `runner.py`'s top-level import) even for pure-logic unit tests.
- pytest's default import mode doesn't add the repo root to `sys.path` (only the test file's own
  directory), so `import kvllm` failed under pytest despite working fine under plain
  `uv run python -c "..."` (which adds cwd). Fixed via `pythonpath = ["."]`, the standard pytest
  fix — no conftest.py needed.
- Test doubles for OpenAI tool-call messages use `types.SimpleNamespace` (matching the
  `message.tool_calls[i].function.{name,arguments}` shape `score_case` reads) rather than mocking
  the `openai` SDK's response models — simpler and decoupled from SDK internals.

## Outcomes

`just check` green: lint clean, 37/37 tests pass. `models.toml` and the leaderboard now reflect
every eval run to date; nothing outstanding in the working tree from Sprint 7.

## Follow-ups

- **Phase 1** (episode runner core + Inspect AI migration) — see
  [`fable-planning/05-roadmap.md`](fable-planning/05-roadmap.md). Build with Fable per the model
  guidance there (load-bearing architecture decisions).

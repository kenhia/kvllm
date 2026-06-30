# Sprint 7 — Eval harness (our own testing on kai)

_2026-06-30 on `kai`. korg #102. Branch `07-eval-harness`. Builds on [Sprint 6](sprint-06-helper-skills.md)._

## Goal

Our own "worth trying / has issues / skip" evaluation of actual models in our environment — the thing
that flips `models.toml` `tested=false` into a real verdict. Per-skillset targets; orchestrated.

## Plan (decisions confirmed with Ken)

- **Hybrid** scoring (mechanical now; LLM-judge for fuzzy quality later).
- **Orchestrate** the serve: stop `kvllm.service`, serve the target, eval, restore.
- **Both** result homes — `models.toml` fields **and** eval docs — plus a nice **HTML leaderboard**
  with JSON/MD siblings for agents.
- Code-exec suite will use a **container** sandbox (follow-up).

## What shipped (MVP — the high-ROI core)

- **`kvllm/eval/`** — `suites.py` (tool-use battery + mechanical scorers), `runner.py`
  (orchestration + operational gate + CLI), `report.py` (scorecard + leaderboard + `models.toml`
  write-back via `tomlkit`).
- **Operational gate:** serves on sm_120, fits VRAM, cold-start s, tokens/sec. The "won't run here"
  detector → `skip`.
- **`tools` suite** (7 cases): single / enum / integer args, `tool_choice=required`, negative
  (no-call), multi-turn round-trip, parallel calls. Mechanical pass/fail; gated by the registry
  `capabilities`.
- **Tri-format leaderboard** in [`docs/model-research/evals/`](../docs/model-research/evals/README.md):
  `leaderboard.html` (human), `leaderboard.json` (source of truth) + `leaderboard.md` (agents);
  per-run `<model>-<date>.{json,md}`.
- **`just eval <key> [--suite ...] [--no-write]`** — serve→score→restore→write; stamps
  `tested`/`eval_verdict`/`eval_date` into `models.toml`.

## Decisions & discoveries

- **First real verdict:** `qwen2.5-7b-instruct` → **worth trying**, tools **7/7**, ~90 tok/s, cold
  start 22 s, 29.4 GB. Service stopped + restored cleanly around it.
- **Bug caught in verification:** `Path.with_suffix(".json")` mangled dotted model keys
  (`qwen2.5-…` → `qwen2.json`); build filenames directly instead. Would have hit every Qwen3.6 entry.
- **`tomlkit` for the write-back** preserves the registry's hand-written comments/formatting (plain
  `tomllib` is read-only).
- Suites are code (typed, no parsing) for now; can become data files if non-dev editing is wanted.

## Outcomes

- End-to-end eval works and is reproducible (`just eval qwen2.5-7b-instruct`). `just lint` clean.
  `models.toml` shows the eval fields; leaderboard renders in all three formats.

## Follow-ups (rest of the eval roadmap)

- **coding** suite — sandboxed (Docker `--network none`, limits) code-exec → pass@1.
- **vision** suite — labeled image Q&A for `vision` models.
- **agentic** suite — scripted mock-tool homelab scenario.
- **LLM-judge** (hybrid) — cloud Claude grading open-ended quality.
- Run the gate over the untested registry models (Qwen3.6 etc.) to flip/flag them — note the
  bleeding-edge `qwen3_5*` arch is the likely first `skip`/`has issues`.

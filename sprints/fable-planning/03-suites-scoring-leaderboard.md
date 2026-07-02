# Suites, scoring, and the weighted leaderboard

_2026-07-02, fable-planning. What we test, how each thing is scored, and how per-suite scores roll
up into a weighted composite that actually ranks the leaderboard. Companion to
[02-eval-harness-architecture.md](02-eval-harness-architecture.md)._

## Design rules

1. **Mechanical first, judge second, human spot-check third.** Anything checkable by code (tests
   pass, correct tool called, file exists with right content) is scored by code. A frontier-model
   judge scores only what code can't (plan quality, report accuracy, tone of a summary) — and every
   judge score carries the judge's rationale into the scorecard so Ken can audit it.
2. **Every task is applicable-or-excluded, never zero-for-missing.** A model without `vision`
   capability isn't penalized for skipping the vision suite; weights renormalize over the suites a
   model was actually eligible for (and the leaderboard shows which).
3. **Suites are versioned.** Each suite has a `version`; scorecards record it; the leaderboard
   marks scores from older suite versions as stale and the batch runner re-runs them.
4. **Tasks mirror the real use case.** The medium-term goal is a local model that monitors homelab
   machines, reviews korg WIs, and helps plan project progress. The agentic suite is a rehearsal of
   exactly that, not an academic benchmark.

## Suite catalog

### S0 — `operational` (gate, exists today — extend)

Serves on sm_120 / fits 32 GB / cold-start / throughput. Fail ⇒ verdict `skip`, nothing else runs.
Extensions over the MVP: decode tok/s (median of 3, TTFT excluded and recorded separately), and a
context-pressure probe (a ~75%-of-`max_model_len` prompt completes without error).
**Score contribution:** gate + a speed factor (below), not a weighted suite of its own.

### S1 — `tools` (exists today — port + extend)

The 7 mechanical tool-call cases (single/enum/int args, forced choice, negative case, multi-turn
round-trip, parallel calls), ported into the new runner, plus hard cases the MVP lacks: nested
object/array args, a distractor tool (two plausible tools, must pick right), tool-error recovery
(tool returns an error string; model must retry or explain, not hallucinate success), and a
schema-adherence case (extra/missing required keys = fail). **Scoring:** mechanical pass/fail per
case; suite score = pass rate.

### S2 — `coding` (new — the core of harness v2)

Model-writes-code-and-runs-it in a sandbox container, agentically: the model gets `bash` +
`write_file`/`read_file` tools in `/workspace` and a task prompt; the harness runs hidden pytest
tests against the result. Task tiers:

| Tier | Shape | Examples (~count) |
|---|---|---|
| C1 function | write one function to spec, hidden tests | string/parsing/algorithms (6) |
| C2 script/CLI | write a small program with I/O contract | log summarizer, CSV filter, JSON transformer (4) |
| C3 fix/extend | repo skeleton pre-loaded in /workspace; make failing tests pass | small bug + small feature (3) |
| C4 iterate | task where first attempt almost certainly fails; must run tests, read output, fix | (2) |

**Scoring:** mechanical — hidden test pass fraction per task (partial credit), plus a small
efficiency deduction for episodes that hit the step limit. C4 additionally records
recovered-after-failure as its own metric (`iteration`), because "reads error output and fixes it"
is the single most important agentic-coding behavior for our use case.

### S3 — `agentic` (new — homelab rehearsal)

Multi-step episodes against a **fixture homelab**: a container (later, a VM) pre-seeded with
realistic state — systemd unit files and statuses, `/var/log` contents, disk-usage layouts, a fake
`korg` CLI/API with WI fixtures. The model gets `bash` (+ read-only fake-korg tools) and tasks
like:

- "Which services on this box failed since the last boot, and why?" (answer must cite the real
  planted cause)
- "Disk is filling on this machine — find what's growing and recommend a safe cleanup." (planted
  culprit)
- "Review the open WIs for project X and draft a status summary with the top 3 next actions."
  (fixtures have a right answer shape)
- "Triage these 6 WIs: which are blocked, stale, or ready?" (labels planted)

**Scoring:** hybrid — mechanical assertions where possible (did it identify the planted culprit /
the failed unit — checked by grepping the transcript's final answer for required facts), judge
rubric for report quality (accuracy, no hallucinated facts, actionability; 0–10). Also record
tool-efficiency (steps used vs. a reference count).

### S4 — `judge`-scored instruction quality (new, cheap)

A small set of single-turn tasks that mechanical checks can't grade — summarize a provided doc,
follow a strict output format, refuse-then-help appropriately, produce a plan for a small project.
**Scoring:** frontier judge with per-task rubrics (below). This suite doubles as the calibration
bed for the judge itself.

### S5 — `vision` (later — architecture-ready now)

Image inputs are just OpenAI content-parts (`image_url` with data-URIs), so the episode runner
supports them from day one; the suite lands later. Planned tiers: chart/table extraction to JSON
(mechanical: compare extracted values), doc/screenshot Q&A with planted answers (mechanical
contains-check + judge), and later GUI-screenshot grounding ("what would you click?") as the
computer-use precursor. Gated on the `vision` capability tag.

## The judge

- **Judge model:** configurable; default a cheap-but-good cloud model (Claude Haiku class), with
  the option to escalate specific rubrics to Sonnet/Opus class. Env: `KVLLM_JUDGE_MODEL`,
  `ANTHROPIC_API_KEY`. All judge calls temperature 0.
- **Rubric contract:** every judged task ships a rubric (criteria + 0–10 anchors + "auto-0"
  conditions like fabricated facts). The judge returns structured JSON `{score, rationale,
  violations[]}`; rationale is stored in the scorecard and surfaced in the per-run `.md`.
- **Calibration:** before trusting it, run the judge over ~10 hand-scored transcripts (Ken scores
  them once); acceptable if within ±1 on ≥80%. Re-check when the judge model changes.
- **Cost control:** judge only sees the final answer + minimal context (not whole transcripts)
  unless the rubric needs the trajectory; batch runs cache judge results by
  (task, transcript-hash).

## Weighted composite score

Weights live in `eval-config.toml` (new, next to `models.toml`) so re-weighting re-ranks without
re-running anything:

```toml
[weights]            # must sum to 1.0 across applicable suites (renormalized per-model)
tools   = 0.30
coding  = 0.35
agentic = 0.25
judged  = 0.10
vision  = 0.0        # tracked + shown, not yet ranked; bump when the suite matures

[speed]              # multiplier on the composite, from decode tok/s
floor_tok_s   = 10   # ≤ floor ⇒ factor 0.5 (and verdict cap "has issues")
full_tok_s    = 40   # ≥ full ⇒ factor 1.0; linear in between
```

Per model: `composite = speed_factor × Σ (weight_i × suite_score_i) / Σ weight_i` over suites the
model was eligible for and that have current-version scores. Scores are 0–1 (judge scores /10).
The leaderboard sorts by composite; per-suite columns stay visible so the composite is auditable.

Rationale for the split: tools+coding+agentic ≈ 90% matches the stated priority ("good tool use
and coding … monitoring homelab, reviewing WIs, planning"); speed as a multiplier (not a suite)
encodes "a brilliant model at 2.5 tok/s is not a leader on this box" — the Qwen3.6-27B lesson.

## Verdicts (kept, now derived)

`skip` = failed the operational gate. `has issues` = composite < 0.55 or speed at floor or any
suite < 0.4. `worth trying` = otherwise. Same three values flow into `models.toml` as today, so
`/model-research`, `/model-scout`, and `models-list` keep working unchanged.

## Leaderboard v2

Same tri-format convention, same location (`docs/model-research/evals/`):

- `leaderboard.json` — adds `composite`, `speed_factor`, `weights_version`, per-suite
  `{score, version, date}`, and an `eligible` list.
- `leaderboard.md` — ranked by composite, ① ② ③ medals, stale-score markers (†).
- `leaderboard.html` — ranked table; per-suite bars; click-through to per-run scorecards; a small
  "weights" footer showing the config that produced the ranking.
- Per-run artifacts: scorecard `.json`/`.md` as today, **plus** the full episode transcripts kept
  as harness logs (gitignored — large; the scorecard records the log path and a per-episode
  one-line summary).

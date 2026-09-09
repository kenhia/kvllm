# Findings

Durable outputs of the eval work — written for future-us, for agents working in this repo
or planning local-agent projects, and for sharing.

- [`evaluating-local-models.md`](evaluating-local-models.md) — **read this first if you're
  building or running a model evaluation.** Token-light lessons: harness-audit-first, the
  four measurement-artifact classes, judge calibration, the frozen-suite + labeled-condition
  pattern. Mostly evergreen.
- [`local-model-guidance-2026-07.md`](local-model-guidance-2026-07.md) — which local model
  for which role, hybrid local+frontier architecture readout, serving configs, cost anchors.
  **Dated — decays with the model landscape**; regenerate via `just eval-all`. Superseded
  on the resident-agent question by the interview (below) since 2026-09-08; its top note
  says what moved.
- [`controller-vs-model-2026-08-21.md`](controller-vs-model-2026-08-21.md) — **the
  scaffolding is worth more than the model.** Same model, same tasks, same judge: changing
  only the harness's budget shape moved one model +86 points, against a frontier-vs-local
  capability gap of 20–30. Includes why the gains are uneven (delivery-limited vs
  capability-limited models), and the `claude-sonnet-5` "+0.14 improvement" that turned out
  to sit inside a 0.150 noise band. Self-contained; safe to share.
- [`kai-5090-gpc9-fault-2026-08-21.md`](kai-5090-gpc9-fault-2026-08-21.md) — **hardware
  incident, and the rung below the prime rule.** kai's RTX 5090 faults on basic CUDA work
  ~50% of the time, always on the same SM (GPC 9 / TPC 4 / SM 1), surviving a power cycle.
  It masqueraded as an upstream vLLM bug with a real file and line number. Carries the
  five-line reproduction and the lesson: once a *second, unrelated* model fails the same
  way, drop to bare metal instead of investigating further inside the stack.
- [`ra-interview-2026-09.md`](ra-interview-2026-09.md) — **hiring a resident agent: the
  forest, not the trees.** Why the ranked board could not separate the two candidates, what
  the interview measured instead (four ways an on-call engineer can be wrong), where
  Qwen3.8 did better and why (it keeps looking, it notices absence, it says how sure it
  is, it holds 128k), where gemma still shines (thinking on, fp8 KV, speed, vision), what
  surprised us, and what it means for building the RA. **Dated — a September 2026
  snapshot**; the next candidate runs the same interview. **Decision taken 2026-09-08:
  Qwen3.8 is the resident** (Ken, WI-1973); sprint 20 served it as interviewed and
  re-served gemma as its best self. **Addendum 2026-09-09 (sprint 22):** the ladder is an
  urgency gradient now, a principle moves the now/handoff boundary only on horizon rungs,
  a checklist floor removes the coverage-miss dangerous cells (the prompt-level one for
  free), and neither candidate asks for more effort when offered it.
- [`local-vs-frontier-2026-07.html`](local-vs-frontier-2026-07.html) — rich self-contained
  report (charts, findings, methodology overview) prepared for the All-The-Vibes community.
  Open in a browser; safe to share as a single file. Generated from live board data by a
  script — a point-in-time snapshot, not maintained.
- [`methodology-2026-07.html`](methodology-2026-07.html) — companion to the above (ATV
  feedback asked for it): the full scoring rubric and methodology — per-suite rubrics,
  judge anatomy + calibration protocol, composite/verdict math with worked examples, and
  an explicit "what this does NOT claim" section. Self-contained, shareable alongside the
  main report.

Live data these derive from: [`../model-research/evals/`](../../model-research/evals/)
(leaderboard + per-run scorecards) and `eval-logs/` (gitignored transcripts).

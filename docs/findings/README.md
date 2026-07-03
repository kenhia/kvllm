# Findings

Durable outputs of the eval work — written for future-us, for agents working in this repo
or planning local-agent projects, and for sharing.

- [`evaluating-local-models.md`](evaluating-local-models.md) — **read this first if you're
  building or running a model evaluation.** Token-light lessons: harness-audit-first, the
  four measurement-artifact classes, judge calibration, the frozen-suite + labeled-condition
  pattern. Mostly evergreen.
- [`local-model-guidance-2026-07.md`](local-model-guidance-2026-07.md) — which local model
  for which role, hybrid local+frontier architecture readout, serving configs, cost anchors.
  **Dated — decays with the model landscape**; regenerate via `just eval-all`.
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

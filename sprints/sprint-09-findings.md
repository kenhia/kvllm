# Sprint 9 — Findings distillation

_2026-07-03. korg #106. Branch `09-findings`. Follows sprint 8's close (local model ① on a
fully-covered board); precedes the sprint 10 repo restructure that will link these from
README/.claude for discovery._

## Goal

Record what sprint 8 taught us in three durable, audience-shaped artifacts, so the lessons
guide (a) future model-evaluation work, (b) the homelab-agent design and other local-agent
projects, and (c) a shareable community write-up.

## Shipped

- `docs/findings/evaluating-local-models.md` — token-light, mostly-evergreen lessons for
  running model evals: audit-the-harness-first (the four artifact classes: token budgets,
  unscored time-limit deaths, single-message context blowouts, concurrency starvation),
  frozen-ranked-suite + labeled-alternate-condition pattern with a frontier control, judge
  calibration protocol, composite design, single-GPU + remote-sandbox infra notes.
- `docs/findings/local-model-guidance-2026-07.md` — dated model-selection guidance: role
  table (devstral for controller-driven loops, gemma-31b as autonomous generalist,
  gemma-12b as vision daily-driver, qwen3-vl disqualified from unsupervised monitoring by
  fabrication-under-freedom), the measured hybrid-architecture readout, cost anchors,
  serving gotchas.
- `docs/findings/local-vs-frontier-2026-07.html` — self-contained ATV report ("When the
  Local Model Took First Place"): methodology, the harness-artifact saga, board, controller
  experiment with the Haiku control, hybrid blueprint. Charts are inline SVG generated from
  live leaderboard.json/scorecards (generator in session scratchpad; the HTML is a
  snapshot, not maintained).
- `docs/findings/README.md` — index with decay labels per doc.

## Addendum (same day, post-merge)

ATV feedback on the report asked how things were scored → added
`docs/findings/methodology-2026-07.html`, a same-identity companion: pipeline, per-suite
rubrics (all case/episode names), judge anatomy + the 12/12 ±1 calibration protocol + the
fabrication-wording lesson, composite/speed-factor/verdict math with two worked examples
(qwen3-vl a1 hybrid score; gemma-31b's ① composite), cost accounting, and a
limits-of-the-methodology section. Main report footer now links it.

## Decisions

- Findings live in `docs/findings/` — matches the sprint-10 target shape where `docs/` is
  the *outputs* home (planning docs move to `sprints/`, model-research to root).
- The 2026-07 guidance is deliberately dated in the filename; the lessons doc is not — the
  two decay at different rates and agents should know which is which.
- ATV report is a generated snapshot: regenerating after future sweeps would silently
  rewrite a shared document's numbers — wrong for something already circulated.

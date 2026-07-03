# Sprint 11 — Phase 5: vision suite (S5)

_2026-07-03. korg #114. Branch `11-vision-suite`. Spec:
[`planning/08-vision-suite-spec.md`](planning/08-vision-suite-spec.md)._

## Shipped

- `suites/vision.py` — 8 single-generate image-reading tasks, mechanical fact-group
  scoring (word-boundary guard for numeric facts), max_tokens 2048, `vision`-gated,
  weight 0.0 until ≥3 models scored.
- `suites/vision_assets/` — deterministic PIL generator + 8 checked-in PNG fixtures
  (dashboard / gauges / chart / terminal / journal / table / count / diagram — all
  homelab-monitor surfaces with planted facts).
- `suites/vision_selftest.py` + `just test-vision-suite` — no-GPU self-test: images load,
  reference answers 1.0, adversarial near-misses <1.0. 8/8 PASS.
- Runner wiring (`vision` suite in evalrun), 6 new unit tests (138 total green).

## Results (2026-07-03) — exit criteria met, weight bumped

All 7 vision models scored on S5 v1: **five at 100%** (gemma-31b, qwen3-vl-8b, qwen3.5-9b,
27B, 35B-A3B), gemma-12b and internvl3-8b at 94% with genuine single-task misses. First
contact also validated the stack: image inputs worked through vLLM for every architecture;
a whole 8-sample suite costs ~2.6K tokens / 2 seconds of inference.

**Day-one rubric bug, caught by the suite's own suspicious-uniformity signal**: 5/7 models
"failed" v4-terminal-df identically — transcripts showed they answered with the device
(`/dev/nvme1n1p1`), the literal Filesystem column, while the rubric accepted only the
mount. Fairness-fixed while unranked (device accepted as alternative), affected models
re-run at the same version. Harness-audit-first, round five.

**Weight bumped 0.0 → 0.15** (roadmap's ≥3-scored rule; 7 scored). Board: gemma-4-31b
widens its ① claim — vision 100% on top of agentic 84% — while the Claude baselines carry
no vision score (S5 not yet run against them; ~pennies if wanted). Vision reshuffled the
mid-board: internvl3-8b jumps to 0.82 on its two-suite coverage (judged 65% + vision 94%,
weights renormalize), a reminder that sparse-coverage composites read differently — its
row shows exactly which columns are filled.

Sweep-efficiency fix landed en route (Ken noticed the drag): eval-all now runs only
stale/missing suites per model instead of the full set; `just eval-view` recipe added for
browsing .eval transcripts in the Inspect viewer.

## Follow-ups

- Baselines through S5 for the frontier-vision comparison (cheap, Ken's call).
- v2 candidates per spec: judged "describe overall health" task; noisy/real-screenshot
  robustness variants; multi-image comparison.
- gemma-12b's v4 miss and internvl's v5 miss are real read-failures worth a transcript
  look before trusting either for terminal/journal reading in the monitor.

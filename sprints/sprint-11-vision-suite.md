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

## In flight

- Sprint-8 follow-ups ran alongside: Qwen 27B/35B agentic rerun under the concurrency cap
  + gemma-4-31b assisted.
- First real S5 runs (exit criteria: internvl3-8b + qwen3-vl-8b, then the 2026 vision
  fleet) — queued behind the follow-ups on the GPU.

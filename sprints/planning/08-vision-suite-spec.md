# S5 vision suite — spec (v1)

_2026-07-03, sprint 11 (Phase 5 per [05-roadmap.md](05-roadmap.md)). Suite source:
[`suites/vision.py`](../../suites/vision.py); fixtures + generator:
[`suites/vision_assets/`](../../suites/vision_assets/)._

## Intent

Measure the exact vision skill the homelab controller needs: **read a monitoring surface,
extract the operative fact**. Not captioning, not aesthetics, not open-ended VQA — every
task is "a thing an on-call agent looks at" with a short verifiable answer.

## Design

- **Eight single-generate episodes** — image + question, no tools, no sandbox, no judge.
  Answer scoring is mechanical fact-groups (agentic-style: every group must match via any
  alternative; digits-only alternatives require word boundaries so "20" can't pass via
  "205"). Partial credit = groups matched / groups total.
- **Fixtures are deterministic PIL renderings, checked in** (PNGs + generator). No external
  images → no licensing, no drift, and the planted facts are exactly known. Homelab flavor
  throughout: service dashboard (one DOWN), disk gauges (87% /var), a 7-day temp chart
  (Thursday peak ~83), a `df -h` terminal (91% /data), a journal excerpt (02:14 OOM-kill of
  postgres), a registry table (cell lookup), a warning-count grid (3 WARN), and a topology
  diagram (backups → nas-01). Reading types covered: status glyphs, gauges, line charts,
  monospace terminal text, log lines, tables, counting, edge-following.
- **max_tokens 2048** — the judged-suite lesson: reasoning models need thinking room even
  when answers are two words.
- **Gating + weight:** requires the `vision` capability; runs in default sweeps for those
  models. Weight **0.0** (shown, unranked) until ≥3 vision models are scored at v1 — the
  roadmap rule — then bump deliberately (weights renormalize; non-vision models are never
  penalized for the column they can't have).
- **Self-test without GPU/Docker:** every image exists and loads; every reference answer
  scores 1.0; every adversarial near-miss scores <1.0 (guards against vacuous groups).
  `just test-vision-suite`.

## Known limits (v1)

- Single image per episode; no multi-image comparison, no video/frames.
- Mechanical-only scoring — a "describe overall health" judged task is a natural v2 once
  the mechanical floor is trusted (the judge + calibration machinery already exists).
- Synthetic renderings are cleaner than real Grafana screenshots; a v2 could add noise
  (compression, odd DPI, real-theme screenshots) to test robustness.
- vLLM must accept image content-parts for each model's architecture — the first sweep is
  the verifier (expect per-model gate surprises, e.g. `--limit-mm-per-prompt` defaults).

## Exit (roadmap)

InternVL3-8B and Qwen3-VL-8B scored on S5 — plus the 2026 fleet additions (gemma-4-12b,
gemma-4-31b-awq, qwen3.5-9b, qwen3.6-27b/35b) which are all vision-capable.

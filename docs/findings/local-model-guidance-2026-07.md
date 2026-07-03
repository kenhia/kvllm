# Local model guidance — 2026-07 snapshot

_Input for the homelab-agent design and other local-agent projects. **Dated on purpose** —
this reflects the July 2026 open-weight landscape on a single RTX 5090 (32 GB, vLLM) and
decays as models ship. Methodology + how to regenerate: run `just eval-all`, read
[evaluating-local-models.md](evaluating-local-models.md)._

## Headline

**Local models now win our homelab board outright.** gemma-4-31b (AWQ) holds ① at composite
0.94 — agentic 84% vs Sonnet 77% / Haiku 68% — and the 2026 class (Gemma 4, Devstral 2,
GLM-4.7, Qwen3.5/3.6) uniformly aces coding (91–100%) and writing (77–92% judged). What
frontier still buys, measured: **self-pacing** (knowing when to stop investigating and
report) **and trustworthiness-under-freedom** (not fabricating when given rope).

## Role guide (who to use for what)

| role | pick | why | caveats |
|---|---|---|---|
| Controller-driven agent (monitor loop, bounded probes) | **devstral-small-2-24b** | assisted 97% — best of ANY model incl. baselines; agent-tuned, disciplined tool calls | raw autonomy 11%: NEEDS the controller; 8K ctx serve config |
| Autonomous-ish generalist | **gemma-4-31b-awq** | ① 0.94; agentic 84% raw; multimodal; 73 tok/s | 302s cold start; AWQ only (FP8-dynamic = gibberish bug) |
| Fast/cheap + vision daily driver | **gemma-4-12b-it** | judged 92% (beats baselines), code 91%, vision, per-image token budgets for cheap dashboard polling | raw agentic 40% — use under controller |
| Max throughput tool-runner | **glm-4.7-flash-awq** | 197 tok/s, code 94%, assisted 87% | judged 68%; over-investigates without a controller |
| Latency-critical / draft | **gpt-oss-20b** | 305 tok/s MXFP4 | code 49%; harmony tool format is nonstandard |
| DO NOT use unsupervised for monitoring | qwen3-vl-8b | good raw discipline masks **fabrication under longer episodes** (2 auto-zeros in assisted) | fine for bounded vision-describe tasks |
| Retired from consideration | llama-3.1-8b, qwen2.5 family | 2024/25-class: analysis quality is the gap (0.3–2.1/10 judged-by-judge), no scaffold fixes it | qwen2.5-7b still a fine tools-API workhorse (100% tools) |

Hybrid Qwen3.6 (27B dense / 35B-A3B): code 100% + judged 90–92%, but agentic numbers are
still partially starvation-corrupted (rerun queued under the concurrency cap); at 42–44
tok/s with heavy reasoning they're the wrong shape for long episodes on this GPU anyway.

## The architecture readout (for the homelab agent)

Measured support for the hybrid plan (local monitor + frontier heavy-lifting):

1. **Local + controller ≈ raw-Haiku level** on multi-step investigation (devstral 97%,
   glm 87%, gemma-12b 74% under scaffolding vs Haiku 68% raw / 82% assisted) — at
   power-only marginal cost vs ~$0.10–0.25 per Haiku investigation episode.
2. **The controller pattern is cheap and mechanical**: bigger budget + a two-phase
   "investigation → forced wrap-up" loop (inject "stop investigating, report now" with a
   reserved delivery window). This closed 34–86 points of gap. See `assisted_agent` in
   [`evals/agentic.py`](../../evals/agentic.py).
3. **Pre-structure discovery, spend intelligence on synthesis** (korg #105 pattern): models
   burn most tokens and hit most failure modes in discovery; deterministic collectors
   (pre-work) + one-shot completion is single-digit-cents even at frontier prices.
4. **Escalation triggers that earn frontier spend**: open-ended root-cause hunts (no
   checklist), high-stakes writes/irreversible actions, and anything where fabrication risk
   matters more than latency. Frontier models were the only ones that stayed honest AND
   complete without scaffolding (and even Sonnet trips a8-honesty occasionally — verify).
5. **Judge/verify stays frontier**: Haiku-as-judge is ~$0.001/episode and was calibratable
   to ±1 of human scoring; no local model demonstrated judge-grade reliability.

## Cost anchors (2026-07 prices)

- Full 4-suite eval: Sonnet $0.81, Haiku $0.68 (caching-heavy; intro pricing on Sonnet).
- Haiku assisted agentic run (9 episodes + judge): ~$0.15–0.25.
- Judge overhead per local model per suite: ~$0.001–0.01.
- Local marginal cost: power only (~0.5 kW under load on kai).

## Serving configs that work (sm_120 / 32 GB)

All in [`models.toml`](../../models.toml) — key gotchas: AWQ-marlin is the safe quant path;
avoid NVFP4 on consumer Blackwell (three failure modes) and never FP8-dynamic-quantize
Gemma 4; hybrid Qwen3.6 needs `enforce_eager` + 8K ctx to fit; Devstral needs
mistral-format flags and 8K ctx (KV cache); cap episode concurrency at ~3 per local server.

## Regeneration

Board: [`model-research/evals/leaderboard.md`](../../model-research/evals/leaderboard.md)
(+ `.html` for the clickable per-case records). Re-run: `just eval-all` (locals) /
`just eval claude-haiku-4-5` (baselines). Assisted: `just eval <key> --suite assisted`.

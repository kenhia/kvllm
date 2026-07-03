# Model candidates — July 2026 (three-prong selection)

_2026-07-02. The leaderboard's local column isn't promising yet (best local composite 0.73,
agentic v2 first result 28% vs frontier 68-77%), so this pass hunts for stronger locals.
Method per Ken: (1) `uvx whichllm@latest` defaults, (2) tuned switches, (3) independent
research — agentic/tool-use primary, multimodal for upcoming sprints. Registry entries added
under the "Candidates (2026-07-02)" section of `models.toml`; untested, so the next
`just eval-all` sweeps them._

## Prong 1+2 — whichllm (hardware fit on the 5090)

Passes run (JSON captured): defaults; `--gpu-only --speed usable --vram-headroom 1GB`;
`--profile coding --gpu-only --speed usable -c 16k`; `--profile vision --gpu-only -c 16k`;
`--evidence strict -c 16k`. Default/tuned/strict converge on the same top-10 — the tool is
stable across switch choices:

| # | Model | Quant | VRAM | est tok/s | quality | evidence |
|---|-------|-------|------|-----------|---------|----------|
| 1 | Qwen/Qwen3.6-27B *(have: ② on board)* | Q6_K | 24.4G | 39.7 | 94.3 | direct |
| 2 | google/gemma-4-31B-it | Q6_K | 28.6G | 33.7 | 91.5 | direct |
| 3 | Qwen/Qwen3-30B-A3B | Q6_K | 24.5G | 144.5 | 83.6 | direct |
| 4 | google/gemma-4-26B-A4B-it | Q8_0 | 27.7G | 114.4 | 82.4 | direct |
| 5 | zai-org/GLM-4.7-Flash | Q6_K | 26.2G | 91.9 | 81.4 | direct |
| 6 | Qwen/QwQ-32B | Q6_K | 28.7G | 33.7 | 80.9 | direct |
| 7 | DeepSeek-R1-Distill-Qwen-32B | Q6_K | 28.7G | 33.7 | 79.9 | direct |
| 8 | openai/gpt-oss-20b | Q8_0 | 22.6G | 141.1 | 78.9 | direct |
| 9 | Qwen/Qwen3-14B | Q8_0 | 16.9G | 51.4 | 77.8 | direct |
| 10 | Mistral-Small-3.2-24B-Instruct-2506 | Q8_0 | 26.9G | 31.6 | 76.8 | direct |

`--profile coding` #1: **Qwen3-Coder-30B-A3B-Instruct** (rest of that list was community-finetune
noise). `--profile vision` returned exactly one fit: **QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ**.

**Caveat**: whichllm models llama.cpp GGUF quants; we serve vLLM. Every candidate was re-checked
for an actually-existing vLLM-servable quant (AWQ/FP8/MXFP4) — that filter, plus recency, kills
several rows above (QwQ-32B and R1-Distill-32B are 2025-vintage reasoning models our 7B distill
already represents; Qwen3-30B-A3B is two generations behind Qwen3.6).

## Prong 3 — research findings (two parallel deep-dives, 2026-07-02)

Key landscape shift: **Qwen3.5/3.6 and Gemma 4 are natively multimodal** — the dedicated -VL
line era is over at the top end. And the ≤32GB agentic class is now dominated by ~30B MoEs with
~3-4B active params (fast decode, full-params VRAM residency).

**sm_120 (5090) cross-cutting gotchas** (from field reports / vLLM issues):
- AWQ via awq_marlin: **the safe path**, confirmed working on sm_120.
- NVFP4: **avoid for now** — three documented failure modes on consumer Blackwell
  (FlashInfer illegal instruction, silent hang, CUDA-graph replay crash). This deprioritized
  Nemotron-3-Nano-30B-A3B (BFCL v4 53.8, otherwise attractive — its official quant is NVFP4;
  FP8 is ~32GB). Revisit when vLLM lands sm_120 NVFP4 MoE kernels (vllm#31085).
- Gemma 4 + on-the-fly FP8 dynamic quant = gibberish (vllm#39049). Use AWQ/QAT checkpoints.
- Qwen3.5/3.6 hybrid arch (Gated DeltaNet): CUDA-graph/Mamba-cache errors reported — our 27B
  already runs enforce_eager; same recipe applied to the 35B retry.

## The shortlist (added to models.toml)

| key | repo | why | headline evidence |
|-----|------|-----|-------------------|
| `qwen3.6-35b-a3b-awq` **(retry)** | QuantTrio/Qwen3.6-35B-A3B-AWQ | **Both prongs' #1.** Was `skip` (OOM at 32K ctx + CUDA graphs); retried with the 27B's proven recipe (8K + enforce_eager) | SWE-V 73.4, TB2 51.5, MMMU ~81.7 (self/aggregator-reported) |
| `glm-4.7-flash-awq` | QuantTrio/GLM-4.7-Flash-AWQ | Purpose-built agentic flash MoE (~3.6B active); proven 5090 deployments | tau2-bench 79.5, SWE-V ~59 |
| `devstral-small-2-24b` | mistralai/Devstral-Small-2-24B-Instruct-2512 | Agent-loop specialist; closest match to our shell-investigation episodes; official FP8 native on 5090 | SWE-V 68.0 |
| `gpt-oss-20b` | openai/gpt-oss-20b | Fast baseline (300-400 tok/s class, MXFP4 ~14GB); lineage diversity | tau-bench Retail 54.8 |
| `qwen3.5-9b` | Qwen/Qwen3.5-9B | Natively-multimodal dense 9B; direct qwen3-vl-8b upgrade candidate; lowest-risk add | Qwen: beats Qwen3-VL at scale |
| `gemma-4-12b-it` | google/gemma-4-12B-it | Multimodal diversity + best-in-size doc/chart reading; tunable per-image vision budget (cheap dashboard polling) | family DocVQA ~94.9 |
| `gemma-4-31b-it-awq` | QuantTrio/gemma-4-31B-it-AWQ | Dense-31B quality + vision; Google's tau2 86.4 claim needs independent verification — that's us | tau2 86.4 (Google-reported) |

## Explicitly skipped, with reasons

- **Qwen3-Coder-30B-A3B / Qwen3-30B-A3B** — superseded by Qwen3.6-35B-A3B on the same footprint.
- **Mistral-Small-3.2-24B** — superseded by Devstral Small 2 (same chassis, agent-tuned); no official AWQ.
- **QwQ-32B, R1-Distill-32B** — 2025 reasoning models; slow (≈34 t/s est) and superseded.
- **Nemotron-3-Nano-30B-A3B** — NVFP4-gated on sm_120 today (see gotchas); revisit.
- **Qwen3-VL-30B-A3B** — superseded in-family by natively-multimodal Qwen3.6.
- **gemma-4-26B-A4B-it** — no reputable ≤30GB quant yet (QuantTrio request open); revisit.
- **InternVL3.5** — sidegrade vs InternVL3-8B; no InternVL4 exists.
- **xLAM-2 / Hammer** — narrow BFCL specialists, 2025 vintage.
- **MolmoWeb-8B** — noted for later: best open UI *pointing/grounding* model; relevant when the
  vision suite needs click-target grounding rather than description.
- **GLM-4.6V-Flash (9B VL)** — native multimodal *function calling* (images as tool args) is
  genuinely interesting for the monitor use case; parked pending an unresolved 5090+GLM-V vLLM
  report. Revisit at Phase 5.
- **Kimi K2.x, MiniMax-M2, Llama-4-Scout, Devstral-2-123B** — don't fit 32GB.

## Verification notes for the sweep

- Every added repo id HTTP-verified on HF (2026-07-02). vLLM 0.24.0 installed — clears
  Qwen3.6-hybrid's ≥0.19 requirement and Devstral's 0.22.1 regression.
- Parser choices to watch at gate time: `gpt-oss-20b` uses the harmony format (`openai`
  parser — first non-Qwen-style tool flow in the fleet); gemma4 parsers are new in vLLM;
  qwen3.5-9b assumes the 3.6 line's `qwen3_xml` transfers back one generation.
- Weights downloads for the sweep: roughly 110 GB total (kai has ~1 TB free).

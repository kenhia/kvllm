# Quantization notes — what fits a 32 GB RTX 5090 (sm_120)

Practical guidance for picking a weight format when adding models to
[`models.toml`](../models.toml). Single-user homelab, one model per process, **32 GB** of VRAM on
consumer Blackwell (sm_120).

## The VRAM budget

Total ≈ **weights + KV cache + activations/overhead** (CUDA-graph capture, the framework, ~1–2 GB).
Rules of thumb per **1B parameters**:

| Format | Bits | ≈ GB / 1B | 7–8B | 14B | 32B |
|---|---|---|---|---|---|
| bf16 / fp16 | 16 | ~2.0 | ~15 GB | ~28 GB | ~64 GB ❌ |
| FP8 (W8A8) | 8 | ~1.0 | ~8 GB | ~14 GB | ~32 GB ⚠️ |
| AWQ / GPTQ (W4) | 4 | ~0.55 | ~5 GB | ~9 GB | ~18–20 GB |

Weights are only part of it — **leave headroom for KV cache**, which scales with
`max_model_len` × batch. On 32 GB: 7–8B runs full-precision with room to spare; **14B fits in bf16
but tightly** (little KV room — prefer a quant or a short `max_model_len`); **32B needs 4-bit**.

## The formats

- **bf16 / fp16** — no quantization, best quality, simplest. Default for ≤8B here. Just omit
  `quantization` in the registry.
- **FP8 (W8A8)** — Blackwell has **native FP8 tensor cores**, so this is fast *and* near-lossless.
  Two ways: a pre-quantized FP8 checkpoint, or vLLM's on-the-fly `--quantization fp8` (dynamic, no
  calibration). Great default for "make a 14–32B model fit and run fast" without quality loss.
- **AWQ (W4, activation-aware)** — smallest footprint, good quality retention. vLLM runs it via the
  **Marlin** kernels (sm80+, so fine on sm_120). Use official AWQ checkpoints (e.g.
  `Qwen/Qwen2.5-14B-Instruct-AWQ`) and set `quantization = "awq"`. This is how to run a 32B on 32 GB.
- **GPTQ (W4)** — comparable footprint/quality to AWQ, also Marlin-accelerated in vLLM. Set
  `quantization = "gptq"`. Pick whichever format the checkpoint ships in; quality is model-specific.
- **NVFP4 (W4 float, Blackwell-native)** — emerging 4-bit *float* with native sm_120 HW support and
  better quality than int4 at the same size. vLLM support is still maturing; worth revisiting for
  the bigger models. _Not used yet._

## How kvllm consumes this

The registry carries a `quantization` field that becomes vLLM's `--quantization` flag (see
`build_serve_argv` in [`kvllm/registry.py`](../kvllm/registry.py)):

```toml
[models."qwen2.5-14b-instruct-awq"]
hf_repo = "Qwen/Qwen2.5-14B-Instruct-AWQ"
quantization = "awq"
max_model_len = 8192
```

For pre-quantized checkpoints (AWQ/GPTQ/FP8 baked into the weights) vLLM usually **auto-detects** the
method from the model config; setting `quantization` is belt-and-suspenders and documents intent.
For **dynamic** FP8 on an unquantized checkpoint, `quantization = "fp8"` is required (it tells vLLM
to quantize at load).

`max_num_batched_tokens` is also a registry field, and it is deliberately **opt-in**: emitted only
when an entry sets it, absent otherwise. Leave it unset. vLLM derives the value per model and the
derived value can be far below anything that looks like a sane global — `gemma-4-31b-it-awq`
resolves to **2496** (2048, raised to fit a video input on a prefix-LM model). See the rule of thumb
below before setting it on anything.

## Rules of thumb for this box

- **Coding / agentic quality, ≤14B:** bf16 (≤8B) or FP8 (14B) — quality first, Blackwell makes FP8
  cheap.
- **Want a 32B at all:** AWQ/GPTQ 4-bit (~18–20 GB weights) with a modest `max_model_len`.
- **Running low on VRAM:** lower `max_model_len` before reaching for a heavier quant — KV cache is
  often the thing that doesn't fit, not the weights.
- **Never pin `max_num_batched_tokens` to "restore" a previous default.** vLLM computes it per
  model; pinning replaces a correct per-model number with a plausible-looking constant. Sprint 18
  set it to 8192 (the pre-0.28.0 default, on advice from the 0.28.0 release notes) and gemma — whose
  derived value is 2496 — stopped serving outright on *both* 0.27.1 and 0.28.0: the extra activation
  memory cost ~1.1 GiB of KV pool, dropping it under what a 16384 context needs. A release note
  announcing a default change describes the fallback for models with no derived value, not a number
  that applies to yours.
- **KV cost per token varies ~10× across architectures**, and it dominates the context you can
  afford. Measured on this card: `gemma-4-31b-it-awq` (dense full attention, head dims 256/512,
  fp16 KV) holds **20,765 KV tokens in 7.42 GiB** — ~375 KiB/token; `qwen3.8-27b-nvfp4` (hybrid,
  only 16 of 64 layers keep a per-token cache, `kv_cache_dtype = "fp8"`) holds **129,615 in
  4.27 GiB** — ~34.5 KiB/token. A hybrid model with fp8 KV buys context a dense one cannot, at the
  same VRAM.
- The `est_vram_gb` in the registry is a **sanity figure**, not a guarantee — confirm with
  `nvidia-smi` after the first serve and adjust.

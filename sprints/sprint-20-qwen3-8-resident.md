# Sprint 20 — Make Qwen3.8 resident: registry as interviewed, gemma re-served, kvllm-client for a reasoning model, deploy

**Proposal:** korg:1984 (slice 1 of program korg:1994) · **Work items:** #1983 (kvllm-client
defaults for a reasoning model), #1982 (registry as interviewed, gemma re-served, both rows
re-scored under their served configs, switched and deployed). **Branch:**
`20-qwen3-8-resident` · **Driving model:** Claude Fable 5.1, as a headless karc leg on kai
under an overseer session on cleo.

## Goal

Ken decided on 2026-09-08 (WI-1973, sprint 19's recommendation): Qwen3.8-27B-NVFP4 is the
resident-agent model. This sprint makes the box match the decision, and it goes first in
the program because every caller change (kyac, kmon) is verified against the model kai
serves. Nothing here changes a ranked condition — the new board rows are new dated rows
under the same suite versions.

## Premise check at sprint start (2026-09-09 00:30 UTC, kai)

- **#1983 holds to the line.** `client/src/kvllm_client/__init__.py` had
  `local_model(temperature=0.0)`, no `max_tokens` on the local tier, no way to pass
  `chat_template_kwargs`, `discover_model()` returning only the id, and
  `invoke_with_fallback` returning `.content` as-is. Five gemma-era defaults, all still
  there.
- **#1982 holds.** `kvllm/registry.py` had no GPU-fraction field (`KVLLM_GPU_UTIL` or 0.90,
  nothing per entry); the Qwen entry was 131,072 / eager / no head; gemma was awq / 16,384
  with neither fp8 KV nor `enable_thinking`; `deploy/kvllm.env` said `gemma-4-31b-it-awq`
  at 0.90. `just service-switch` and `just eval-repeat` exist as the item describes.
- **Environment:** `kvllm.service` active serving `gemma-4-31b-it-awq` (16,384) at
  30,846 MiB; `just` and `uv` on the leg PATH; the kmon timer fires 04:01 PDT (11:01 UTC),
  ten and a half hours out — the GPU window is the leg's.

## Order

Client first (no GPU), then the registry, then the two N=3 re-scores under
`KVLLM_EVAL_DATE=2026-09-09` (the repeat runner refuses sprint 19's `2026-09-08` keys, by
design), then `just service-switch qwen3.8-27b-nvfp4`, the live client calls, docs.
`deploy-kvllm` runs from merged `main` at ship time, as `.sprint-deploy` declares.

## kvllm-client 0.2.0 (#1983)


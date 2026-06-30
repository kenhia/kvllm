# kvllm

Local LLM serving on the `kai` RTX 5090 via **vLLM**, exposed as an OpenAI-compatible `/v1`
endpoint for use from LangChain — chosen for **model breadth** (HuggingFace-native, no per-model
engine builds) and mature **tool calling**. Sibling backend to `trt-llm-explore`.

**Start here:** [`docs/00-kickoff.md`](docs/00-kickoff.md) — the decision, priorities, environment,
and plan. Progress in [`sprints/`](sprints/).

## Quick start

```sh
just models-list                    # what's in the registry (models.toml)
just serve qwen2.5-7b-instruct      # serve a model by key on http://localhost:8000/v1
just healthy                        # wait until /v1 answers
just smoke                          # tool-calling + LangChain exit-criteria smoke tests
```

`just serve` with no arg serves the default (`qwen2.5-7b-instruct`). Point any OpenAI client at it
with `base_url="http://localhost:8000/v1"`, `api_key="EMPTY"`, and `model="<the registry key>"`.
vLLM holds **one model per process**; switch models by stopping one `serve` and starting another.

## Docs

- [`docs/00-kickoff.md`](docs/00-kickoff.md) — why vLLM, priorities, environment, roadmap.
- [`docs/01-backend-contract.md`](docs/01-backend-contract.md) — the OpenAI `/v1` surface clients depend on.
- [`docs/02-quantization.md`](docs/02-quantization.md) — AWQ/GPTQ/FP8 and what fits 32 GB.
- [`models.toml`](models.toml) — the model registry.
- Progress: [`sprints/`](sprints/).

> Status: Sprints 1–2 shipped 2026-06-30 — vLLM 0.24.0 on sm_120 (tool calling + LangChain
> verified, DeepSeek-R1 distill), plus a model registry + serve recipes + `/v1` contract. Next:
> Sprint 3 (availability — systemd auto-start).

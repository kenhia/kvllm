# kvllm

Local LLM serving on the `kai` RTX 5090 via **vLLM**, exposed as an OpenAI-compatible `/v1`
endpoint for use from LangChain — chosen for **model breadth** (HuggingFace-native, no per-model
engine builds) and mature **tool calling**. Sibling backend to `trt-llm-explore`.

**Start here:** [`docs/00-kickoff.md`](docs/00-kickoff.md) — the decision, priorities, environment,
and plan. Progress in [`sprints/`](sprints/).

## Quick start

```sh
just serve            # serve Qwen2.5-7B-Instruct (tool calling) on http://localhost:8000/v1
just healthy          # wait until /v1 answers
just smoke            # tool-calling + LangChain exit-criteria smoke tests
```

Point any OpenAI client at it: `base_url="http://localhost:8000/v1"`, `api_key="EMPTY"`. vLLM
holds **one model per process**; switch models by stopping and starting `just serve`.

> Status: Sprint 1 (core setup) shipped 2026-06-30 — vLLM 0.24.0 serving on sm_120, tool calling
> and LangChain reach verified, plus a DeepSeek-R1 distill. See
> [`sprints/sprint-01-core-setup.md`](sprints/sprint-01-core-setup.md).

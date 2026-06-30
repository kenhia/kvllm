# kvllm

Local LLM serving on the `kai` RTX 5090 via **vLLM**, exposed as an OpenAI-compatible `/v1`
endpoint for use from LangChain — chosen for **model breadth** (HuggingFace-native, no per-model
engine builds) and mature **tool calling**. Sibling backend to `trt-llm-explore`.

**Start here:** [`docs/00-kickoff.md`](docs/00-kickoff.md) — the decision, priorities, environment,
and plan. Progress in [`sprints/`](sprints/).

> Status: scaffolded 2026-06-30. Sprint 1 (core setup) not yet started.

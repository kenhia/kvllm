# Sprint log

A published, chronological record of how **kvllm** evolved — one file per sprint — so the journey
is legible. Same casual cadence as `trt-llm-langchain`.

See [`../docs/00-kickoff.md`](../docs/00-kickoff.md) for why this project exists (vLLM over
TRT-LLM) and the roadmap.

## Convention

- One file per sprint: `sprint-NN-short-slug.md` (zero-padded).
- Write **Goal / Plan** at the start; fill **What shipped / Outcomes / Follow-ups** as it lands.
  Record what didn't work and what got deferred. Date each sprint (absolute dates).
- Skeleton: Goal · Plan · What shipped · Decisions & discoveries · Outcomes · Follow-ups.

## Index

| Sprint | Title | Status |
|---|---|---|
| [01](sprint-01-core-setup.md) | Core setup (vLLM serving + tools + LangChain) | shipped 2026-06-30 |
| [02](sprint-02-serving-ergonomics.md) | Serving ergonomics (registry + recipes + quant notes + contract) | shipped 2026-06-30 |
| [03](sprint-03-availability.md) | Availability (systemd user service + auto-restart) | shipped 2026-06-30 |
| [04](sprint-04-helper-app.md) | Helper app (web control panel — switch models from the LAN) | shipped 2026-06-30 |
| [05](sprint-05-model-research.md) | Model collection research (survey + registry download set) | shipped 2026-06-30 |
| [06](sprint-06-helper-skills.md) | Helper skills (/model-research + /model-scout) | shipped 2026-06-30 |

# Sprint log

A published, chronological record of how **kvllm** evolved — one file per sprint — so the journey
is legible. Same casual cadence as `trt-llm-langchain`.

See [`planning/00-kickoff.md`](planning/00-kickoff.md) for why this project exists (vLLM over
TRT-LLM), and [`planning/roadmap.md`](planning/roadmap.md) for where it's going now.

## Convention

- One file per sprint: `sprint-NN-short-slug.md` (zero-padded). This predates the kproject
  harness's `###-<short-name>.md` and is kept — 13 records and their inbound links.
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
| [07](sprint-07-eval-harness.md) | Eval harness (operational gate + tool-use suite + leaderboard) | shipped 2026-06-30 |
| [08](sprint-08-eval-harness-v2.md) | Eval harness v2 (Inspect AI, sandboxed agentic+coding, weighted leaderboard) | shipped 2026-07-03 |
| [09](sprint-09-findings.md) | Findings distillation (evergreen lessons + dated role guide) | shipped 2026-07-03 |
| [10](sprint-10-repo-restructure.md) | Repo restructure + publish prep | shipped 2026-07-03 |
| [11](sprint-11-vision-suite.md) | Vision suite S5 (7/7 scored, weighted 0.15) | shipped 2026-07-03 |
| [12](sprint-12-vision-v2.md) | Vision v2 (classification, captioning, render-QA) | shipped 2026-07-04 |
| [13](sprint-13-client-lib.md) | Client lib (`kvllm-client`: discovery, local/frontier tiers, fallback) | shipped 2026-07-09 |
| [14](sprint-14-kprojects-harness.md) | kprojects harness (managed conventions block, harness layout) | shipped 2026-08-14 |

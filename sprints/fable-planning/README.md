# fable-planning — eval harness v2

_2026-07-02. Planning pass for the rich "local evaluation of models" harness: agentic + coding
episodes in sandboxes, frontier-model judging, weighted leaderboard, and the option of a dedicated
sandbox machine. Produced from a repo review + a primary-source research pass on eval frameworks._

## TL;DR

**Build the harness on [Inspect AI](https://inspect.aisi.org.uk)** (UK AISI; actively maintained,
METR migrated to it) — it natively provides the agent loop, Docker-sandboxed `bash`/editor tools,
model-graded scoring with an independent judge model (Claude via `ANTHROPIC_API_KEY`), resumable
batch runs, and a dataframe API for building our own leaderboard. **Keep kvllm's registry, serve
orchestration, operational gate, and tri-format leaderboard** as the thin layer around it — the
weighted composite ranking is deliberately ours. Suites: tools (ported + hardened), coding
(sandboxed write-run-fix with hidden tests), agentic (fixture-homelab episodes — the rehearsal of
the monitoring-controller goal), judged instruction quality, vision later (architecture-ready from
day one). **The spare machine: yes, as the sandbox/VM host** (Ubuntu Server 24.04 LTS) — but
nothing blocks on the reimage; Phases 1–3 run sandboxes on `kai`'s Docker and move with one
`DOCKER_HOST` flip (with a tested fallback, since remote-Docker is Inspect's one soft spot).

## Docs

| Doc | What's in it |
|---|---|
| [01-current-state-review.md](01-current-state-review.md) | Repo review: what to keep (registry spine, operational gate, orchestration) + 11 recommendations (unit tests, batch/resume, client/controller split, suite versioning, …) |
| [02-eval-harness-architecture.md](02-eval-harness-architecture.md) | Stack decision (Inspect AI vs. Harbor/lm-eval/promptfoo/custom, verified 2026-07-02), component map, batch runner, repo layout, caveats + mitigations, multimodal-ready decisions |
| [03-suites-scoring-leaderboard.md](03-suites-scoring-leaderboard.md) | Suite catalog S0–S5, judge design + calibration protocol, `eval-config.toml` weights, composite score, verdict derivation, leaderboard v2 |
| [04-sandbox-host.md](04-sandbox-host.md) | The spare machine: why a separate host, OS choice, setup checklist, security posture, VM/computer-use path |
| [05-roadmap.md](05-roadmap.md) | Phases → Sprints 08–12 with exit criteria + per-phase model guidance: runner core+migration → coding suite → weighted board+judge → sandbox host+agentic → vision |
| [06-coding-suite-spec.md](06-coding-suite-spec.md) | Phase 2 task-design spec (Fable-authored, Opus implements): 15 tasks C1–C4, hidden-test injection, junitxml scoring, iteration metric, acceptance criteria |

## Decisions Ken should confirm before Sprint 08

1. **Inspect AI as the base** (the load-bearing decision; everything else survives a stack swap
   but this one shapes the code).
2. **Initial weights** in [03](03-suites-scoring-leaderboard.md): tools .30 / coding .35 /
   agentic .25 / judged .10, speed as a multiplier — trivially re-tunable later, but the first
   ranking will reflect these.
3. **Judge default** = Claude Haiku-class via API (cost/quality tradeoff; escalatable per-rubric).
4. **Sandbox host reimage** = Ubuntu Server 24.04 LTS headless, homelab-standard access; timing
   free (blocks Phase 4 only).

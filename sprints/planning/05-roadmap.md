# Roadmap — phased sprints to the rich eval harness

_2026-07-02, planning. Phases sized like the existing sprints (a focused day-ish each),
each with exit criteria; numbering continues the sprint log (next is Sprint 08). Dependencies are
explicit — the sandbox host ([04](04-sandbox-host.md)) only blocks Phase 4._

## Model guidance (who builds what, where Fable reviews)

**Standing rule: Fable reviews progress at the end of every phase** — sprint doc + diff + a couple
of transcripts/artifacts, checking against that phase's exit criteria and the architecture
invariants ([02](02-eval-harness-architecture.md)). The table below adds where a phase needs more
than the standing review.

| Phase | Build with | Fable involvement beyond the end-of-phase review |
|---|---|---|
| 0 hygiene | **Sonnet** | None — mechanical; spec is already written (review items 4/7/10). |
| 1 runner core + migration | **Fable** | Build it with Fable. This is the load-bearing phase: first Inspect integration, the controller/runner split, batch+resume semantics, and the `DOCKER_HOST` risk experiment. Decisions made here are the architecture. |
| 2 coding suite | **Opus**, with a **Fable task-design spec first** | Fable authors the task list + hidden-test design + partial-credit/step-limit rules (discriminating power is the product, [02 risks](02-eval-harness-architecture.md)); Opus implements tasks/images/scorers. End-of-phase Fable review must include reading 2–3 full episode transcripts (`inspect view`), not just scores. |
| 3 weighted board + judge | **Opus**, with **Fable rubrics + calibration sign-off** | Scoring math and leaderboard rendering are Opus-fit. Fable writes the judge rubrics and the calibration protocol run is a **hard Fable gate**: no composite ranking is trusted (or written to `models.toml`) until Fable signs off the ±1-on-80% calibration result. |
| 4 sandbox host + agentic suite | **Opus** (host setup: **Sonnet** is fine) | Fable designs the fixture-homelab scenarios + planted ground truths (they encode the real controller use case); Opus builds the image and episodes. Reimage/checklist work in [04](04-sandbox-host.md) needs no frontier model. |
| 5 vision suite | **Opus** | Standing review only; escalate to Fable if the `openai-api` image-passthrough caveat ([02 caveats](02-eval-harness-architecture.md)) bites and the workaround touches architecture. |

Two extra **Fable checkpoints** outside the phase rhythm:

- **After the first full `eval-all` sweep** (end of Phase 1): review whether v1 verdicts
  reproduced, and whether the tools suite still discriminates (if every model passes everything,
  harden cases *before* building more suites on the same pattern).
- **After the first ranked leaderboard exists** (end of Phase 3): sanity-check the ranking against
  intuition and the `inspect_evals` calibration benchmarks; re-tune weights once, deliberately,
  with the reasoning recorded in the sprint doc.

Rule of thumb for anything unlisted: task *design* and anything that changes an interface between
components → Fable; implementation against a written spec → Opus; mechanical/config/sysadmin →
Sonnet.

## Phase 0 — hygiene (fold into the start of Sprint 08)

Commit the outstanding v1 eval results (leaderboard + 3 scorecards + `models.toml` verdicts).
Add `pytest` dev-group + unit tests for the existing pure functions (`score_case`, `_verdict`,
report rendering), `just test` and a combined `just check`. Fix the `--today` default. These are
review items 4, 7, 10 from [01](01-current-state-review.md).

## Phase 1 — Sprint 08: episode runner core + migration

Adopt the harness stack ([02](02-eval-harness-architecture.md)): episode runner with sandboxed
`bash`/file tools (Docker on `kai` for now), the serve-controller split (controller owns
stop/serve/restore + emits a base URL; runner evaluates any base URL), and the batch CLI.

- Port S1 `tools` into the new runner (same 7 cases + the new hard cases).
- `just eval <key>`, `just eval-all [--filter ...]` with resume (skip models already scored at
  current suite versions), `--endpoint` to eval an arbitrary /v1.
- Scorecards now record suite versions + log paths; transcripts land in a gitignored logs dir.

**Exit:** `just eval-all` sweeps every non-skip registry model through operational + tools
unattended, resumable, and rebuilds the leaderboard; old verdicts reproduced or explained.

## Phase 2 — Sprint 09: coding suite (S2)

The sandbox task image, C1–C4 coding tasks (~15) with hidden pytest scoring, partial credit, step
limits, and the iteration metric. Runs on `kai`'s Docker; flips to the sandbox host via
`DOCKER_HOST` with zero task changes.

**Exit:** ≥3 registry models scored on S2 end-to-end; at least one C4 task shows a model
recovering from a failing test run; results ranked on the leaderboard.

## Phase 3 — Sprint 10: weighted leaderboard + judge (S4, scoring v2)

`eval-config.toml` weights, speed factor, composite score, derived verdicts, leaderboard v2
(ranked, stale markers, weights footer). Frontier judge plumbing (Anthropic API), rubric contract,
the S4 judged suite, and the ±1-on-80% calibration pass against ~10 hand-scored transcripts.

**Exit:** leaderboard ranks by composite; re-weighting `eval-config.toml` re-ranks without
re-running; judge scores carry rationales into scorecards and pass calibration.

## Phase 4 — Sprint 11: sandbox host + agentic suite (S3)

Reimage the spare machine (Ubuntu Server 24.04, checklist in [04](04-sandbox-host.md)), move
sandbox execution there (`docker context`), build the fixture-homelab image (planted systemd
failures, logs, disk pressure, fake-korg WI fixtures) and ~8 S3 episodes with hybrid scoring.

**Exit:** a full `eval-all` sweep runs with sandboxes on the sandbox host; S3 scores on the board;
tok/s measurements on `kai` no longer perturbed by sandbox load.

*(Ken can do the reimage any time from tonight; if it slips, S3 runs on `kai` Docker first and
only the host cutover moves later.)*

## Phase 5 — Sprint 12: vision suite (S5) + multimodal groundwork cash-in

Image content-parts through the episode runner (already supported by design), chart/table/doc
tasks with mechanical extraction scoring + judge, `vision`-gated. Weights bump `vision` above 0
once ≥3 vision models are scored.

**Exit:** InternVL3-8B and Qwen3-VL-8B (already in the registry) scored on S5.

## Phase 6+ — later, unscheduled

- **VM layer on the sandbox host** (libvirt + snapshot/revert) for full-machine agentic tasks.
- **Computer-use episodes** (desktop VM + screenshots) once a vision model earns it.
- **Real-korg read-only episodes** (the fake-korg fixtures graduate to a sanitized live snapshot).
- **The controller itself** — the always-on local model monitoring the homelab is a separate
  project; this harness is how we pick its brain.

## Cross-phase invariants

- Registry-driven throughout; `models.toml` verdict fields and the `/model-research`/`/model-scout`
  skills keep working at every phase.
- Every phase ends with `just check` green and a sprint doc in `sprints/`.
- Suites are versioned from Phase 1 so mixed-version leaderboards are visible, never silent.

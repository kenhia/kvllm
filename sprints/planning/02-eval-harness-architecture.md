# Eval harness v2 — architecture & stack decision

_2026-07-02, planning. The target design for the rich local model eval: agentic episodes in
sandboxes, frontier-model judging, weighted leaderboard. Facts below were verified against primary
sources on 2026-07-02 (research pass; sources linked inline)._

## Stack decision: Inspect AI as the episode engine, kvllm as the orchestrator

**Adopt [Inspect AI](https://inspect.aisi.org.uk)** (UK AI Security Institute, `inspect-ai` on
PyPI) as the engine that runs eval episodes, and keep a **thin kvllm orchestration layer** around
it (registry, serve control, weighted scoring, leaderboard, `models.toml` write-back — the parts
that are genuinely ours).

Why Inspect (verified 2026-07-02):

- **Alive and dominant.** v0.3.244 released 2026-07-01, ~weekly cadence. METR wound down its own
  Vivaria and now recommends Inspect; Groq's OpenBench and the 143-eval
  [`inspect_evals`](https://ukgovernmentbeis.github.io/inspect_evals/) catalog are built on it.
- **Exactly our episode shape.** Built-in [`react()` agent](https://inspect.aisi.org.uk/react-agent.html)
  (tool loop + `submit()`, scorer-gated retries) with standard `bash()`, `python()`,
  `bash_session()`, `text_editor()` tools that **run inside a Docker sandbox**
  (`sandbox="docker"`, plain `compose.yaml`) — the "give the model a container, let it write and
  run code" requirement is first-class, not something we build.
- **Talks to our vLLM endpoint natively.** The generic OpenAI-compatible provider:
  model `openai-api/kvllm/<registry-key>` with `KVLLM_BASE_URL=http://localhost:8000/v1`,
  `KVLLM_API_KEY=EMPTY` (per-run override: `--model-base-url`). Docs:
  [providers](https://inspect.aisi.org.uk/providers.html).
- **Frontier judging is a one-liner.** `model_graded_qa(model="anthropic/claude-…")` — the grader
  model is independent of the model under test; custom rubrics via templates; fully custom scorers
  via `@scorer`. ([scorers](https://inspect.aisi.org.uk/scorers.html))
- **Built for our leaderboard job.** `.eval` logs + `inspect view` transcript viewer (huge for
  debugging *why* a model failed), and a dataframe API
  ([`evals_df()`/`samples_df()`](https://inspect.aisi.org.uk/dataframe.html)) for programmatic
  aggregation. Cross-suite **weighting is deliberately left to the caller** — which is what we
  want, since the weighted composite is our leaderboard's identity.
- **Batch/resume mostly solved.** [`eval_set()`](https://inspect.aisi.org.uk/eval-sets.html) runs
  tasks×model resumably with auto-retry; our batch layer only iterates *models* (serve/swap is our
  problem, and ours alone).
- **Multimodal-ready.** Images as task input are first-class
  ([multimodal](https://inspect.aisi.org.uk/multimodal.html)) — S5 slots in without re-architecture.

Rejected (same research pass): **Harbor** (Laude, 2026 — strong, but evaluates full agent CLIs
like Claude Code/OpenHands rather than raw models behind /v1; watch it for a future "eval the
whole agent stack" phase), **lm-evaluation-harness** / **lighteval** (single-turn benchmark shape,
no sandboxed agentic episodes), **promptfoo** (prompt QA, not agent episodes), **OpenAI evals**
(maintenance mode, hosted platform shutting down late 2026), **fully custom** (we'd rebuild the
react loop, sandbox plumbing, log viewer, and retry machinery for zero differentiated value).

Bonus: `inspect_evals` gives us **free calibration benchmarks** (SWE-Bench Verified, GAIA,
LiveCodeBench subsets) to sanity-check our custom suites against known model orderings.

## Known caveats (verified, with mitigations)

| Caveat | Status | Mitigation |
|---|---|---|
| Remote Docker host (`DOCKER_HOST=ssh://…`) for sandboxes | Undocumented; [issue #540](https://github.com/UKGovernmentBEIS/inspect_ai/issues/540) open. Inspect shells out to the `docker` CLI (which honors `DOCKER_HOST`), so it *probably* works | Test in Phase 1 (one task, `DOCKER_HOST` set). Fallback: run the eval runner itself on the sandbox host (it only needs `http://kai:8000/v1`), controller stays on `kai` |
| Image passthrough through the generic `openai-api/` provider to vLLM VLMs | Not explicitly documented | Smoke-test with InternVL3 in Phase 5; images ride standard OpenAI content-parts so risk is low |
| `KVLLM_API_KEY` must be set (any non-empty value) | Convention, not doc-quoted | `EMPTY`, as everywhere else in this repo |
| vLLM tool-parser quirks per model (`qwen3_xml`, forced `tool_choice`) | Known from Sprint 07 | The tools suite itself is the detector; record parser errors as case failures with detail |

## Component map

```
┌────────────────────────────── kai ──────────────────────────────┐
│  models.toml ──► kvllm.registry (exists)                        │
│                     │                                           │
│  kvllm.evalctl ─────┤  "controller": stop kvllm.service, serve  │
│  (extracted from    │  key K, health-wait, operational gate,    │
│   eval/runner.py)   │  restore. Emits base_url + gate results.  │
│                     ▼                                           │
│  suites/  (Inspect tasks: S1 tools, S2 coding, S3 agentic,       │
│           S4 judged, S5 vision — see 03)                        │
│      inspect eval_set(tasks, model=openai-api/kvllm/K)          │
│           │                        │                            │
│           │ /v1 chat+tools         │ docker CLI                 │
│           ▼                        ▼                            │
│  vLLM (model K)          sandboxes (kai Docker now;             │
│                          DOCKER_HOST→sandbox-host later)        │
│                                                                 │
│  kvllm.score: evals_df() + gate + eval-config.toml weights      │
│      ──► scorecard.{json,md} ──► leaderboard.{json,md,html}     │
│      ──► models.toml write-back (tomlkit, exists)               │
│  judge calls: anthropic/… (ANTHROPIC_API_KEY), rationale kept   │
└─────────────────────────────────────────────────────────────────┘
```

**What we keep from v1:** registry + serve-argv builder; the stop/serve/restore + fast-fail logic
(extracted into `kvllm/evalctl.py`); the operational gate (extended per
[03 §S0](03-suites-scoring-leaderboard.md)); `tomlkit` write-back; tri-format leaderboard
conventions. **What retires:** the flat request/response suite runner in `eval/runner.py` +
`eval/suites.py`, once S1 is ported to an Inspect task (keep the 7 cases' semantics; they become
samples with a custom mechanical scorer).

## The batch runner (`kvllm.evalrun`)

The one loop Inspect can't do for us — vLLM is one-model-per-process on a single GPU, so models
run serially while everything inside a model runs concurrently:

```
for key in select(registry, --filter/--all/--only):        # skip: gate-skipped, current-version-scored
    evalctl.serve(key)               → base_url | gate-fail → scorecard(skip), continue
    gate = evalctl.gate(base_url)                            # cold start, VRAM, decode tok/s, ctx probe
    eval_set(tasks_for(entry.capabilities), model=f"openai-api/kvllm/{key}",
             log_dir=f"eval-logs/{key}/")                    # resumable, retries inside
    score.aggregate(key)                                     # evals_df + gate + weights → scorecard
evalctl.restore(); score.leaderboard()
```

Resume is two-layer: `eval_set` resumes within a model (its own log-dir bookkeeping); the model
loop skips keys whose scorecards are complete at current suite versions. A crashed overnight run
re-invoked in the morning continues where it died.

## Repo layout changes

```
suites/                      # Inspect task definitions + assets (NEW, top-level — tasks are data+code)
  tools/  coding/  agentic/  judged/  vision/
  images/                   # Dockerfiles/compose for task sandboxes
eval-config.toml            # weights, speed curve, judge model, thresholds (NEW)
eval-logs/                  # .eval transcripts, gitignored (scorecards record paths)
kvllm/evalctl.py            # controller: serve orchestration + operational gate (extracted)
kvllm/score.py              # aggregation: evals_df → composite → scorecard/leaderboard/write-back
kvllm/eval/                 # v1 — retires after Phase 1 port
```

Dependencies: `inspect-ai` joins the `eval` group (needs Python ≥3.10; our 3.12 pin is fine);
`pandas` comes with the dataframe API usage. Judge needs `ANTHROPIC_API_KEY` on `kai` only —
never inside sandboxes.

## Architectural decisions that keep multimodal (and beyond) cheap later

1. **Samples carry content-parts, not strings** — Inspect natively; no harness change for S5.
2. **Capability-gating stays registry-driven** — `tasks_for(capabilities)` is the only dispatch;
   adding `vision`/`computer-use` suites = new mapping entries.
3. **Sandbox location is one env var** — nothing in tasks knows where Docker runs; the
   [sandbox host](04-sandbox-host.md) is a config flip (or, fallback, a runner relocation).
4. **Scores are (value, version, date) triples everywhere** — re-weighting and suite evolution
   never invalidate storage, only ranking.
5. **The judge is a scorer parameter, not an architecture** — swapping judge model/provider (or
   local-judging with a big model on `kai` someday) is config.

## Risks & open questions

- **Suite quality is now the product.** Inspect removes plumbing risk; the discriminating power of
  ~30 custom tasks is where effort must go. Mitigation: calibrate against `inspect_evals` known
  benchmarks + hand-review transcripts via `inspect view` in every phase.
- **Judge cost/drift:** cache judge results by (task, transcript-hash); calibration protocol in
  [03](03-suites-scoring-leaderboard.md); pin the judge model id in `eval-config.toml`.
- **7B models may floor on agentic tasks** (all-zeros tells us nothing). Mitigation: tiered tasks
  (C1 easy → C4 hard) so every capability level lands on a discriminating rung.
- **Eval determinism:** temperature 0 everywhere, but sandbox timing and model nondeterminism
  remain; record per-task `epochs` (Inspect supports repeats) for flaky-sensitive tasks.

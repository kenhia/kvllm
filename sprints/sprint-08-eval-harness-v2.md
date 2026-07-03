# Sprint 8 — Eval harness v2 (Inspect AI, sandboxed agentic+coding, weighted leaderboard)

_2026-07-02 on `kai`. korg #104. Branch `08-eval-harness-v2`. Builds on
[Sprint 7](sprint-07-eval-harness.md). Planning in [`sprints/planning/`](planning/README.md)
(repo review, stack decision, suites/scoring design, sandbox-host plan, phased roadmap)._

## Goal

Turn the Sprint 7 MVP eval into the rich harness Ken wants: agentic + coding episodes in sandboxes,
frontier-model judging, a weighted composite leaderboard. This sprint covers **roadmap Phase 0**
(hygiene) — see [`planning/05-roadmap.md`](planning/05-roadmap.md) for the full phased
plan (Phase 1 — episode runner core + Inspect AI migration — is next).

## Plan (Phase 0, per the roadmap)

Review items 4, 7, 10 from [`planning/01-current-state-review.md`](planning/01-current-state-review.md):
commit the outstanding v1 eval results as a clean baseline; add unit tests for the eval package's
pure functions (none existed); fix the `--today` default (`"undated"` when run outside `just`).

## What shipped

- **Unit tests for `kvllm/eval/`** (37 tests, `tests/test_eval_suites.py` +
  `tests/test_eval_runner.py` + `tests/test_eval_report.py`): every `score_case` kind
  (tool_call/no_tool/parallel/multi_turn/unknown) + `_args_subset`, `_verdict`'s threshold/speed-cap
  logic, and `report.py`'s scorecard/leaderboard rendering + `models.toml` write-back (including a
  regression test for the Sprint 7 dotted-key bug).
- **`pytest` added to the `dev` dependency group**; `[tool.pytest.ini_options]` in `pyproject.toml`
  (`pythonpath = ["."]`) so tests import `kvllm` without an editable install.
- **`just test`** (`uv run --group dev --group eval --group test pytest tests/ -q` — needs all
  three groups: `tomlkit` for report tests, `openai` for runner import) and **`just check`**
  (`lint` then `test`).
- **`--today` now defaults to `date.today().isoformat()`** in `kvllm/eval/runner.py` instead of
  `"undated"`, so `python -m kvllm.eval <key>` run directly (not via `just eval`) still dates its
  scorecard sensibly.
- **Committed the outstanding v1 eval results**: 3 scorecards (`deepseek-r1-distill-qwen-7b`,
  `internvl3-8b`, `qwen2.5-coder-7b-instruct`) + refreshed leaderboard + `models.toml` verdicts,
  as their own commit — a clean baseline before harness v2 work starts.

## Decisions & discoveries

- **`just eval`/`just lint` already used `uv run --group dev`**, which — surprisingly — only
  activates the requested groups; a bare `uv sync --group dev` (not `uv run`) actively
  *uninstalls* other groups' packages. `just test` needs `--group dev --group eval --group test`
  together since the eval package pulls in `tomlkit` (eval) and `openai` (test, for
  `runner.py`'s top-level import) even for pure-logic unit tests.
- pytest's default import mode doesn't add the repo root to `sys.path` (only the test file's own
  directory), so `import kvllm` failed under pytest despite working fine under plain
  `uv run python -c "..."` (which adds cwd). Fixed via `pythonpath = ["."]`, the standard pytest
  fix — no conftest.py needed.
- Test doubles for OpenAI tool-call messages use `types.SimpleNamespace` (matching the
  `message.tool_calls[i].function.{name,arguments}` shape `score_case` reads) rather than mocking
  the `openai` SDK's response models — simpler and decoupled from SDK internals.

## What shipped — Phase 1: episode runner core + Inspect migration (Fable, 2026-07-02)

- **Inspect AI adopted** (`inspect-ai` 0.3.244 in the `eval` group; resolves cleanly beside
  vLLM). Verified the exact APIs before building: `generate(tool_calls="none"|"single"|"loop")`,
  `TaskState.tools/tool_choice`, `ToolCall.function/.arguments` (pre-parsed dicts),
  `ModelOutput.for_tool_call`, `eval_set` resume, `Literal` → enum tool schemas.
- **`evals/tools.py`** — the S1 suite as an Inspect task, **v2 = 11 cases**: the 7 ported Sprint 7
  cases + 4 hard ones from the design (array args, distractor tool, tool-error recovery,
  exact-argument adherence with word→int coercion). Stub tools return canned values; scoring is a
  pure function (`score_extract`) with its own unit tests.
- **`kvllm/evalctl.py`** — the controller half of the old runner: stop/serve/health-wait/restore
  (process-group kill, fast-fail, serve-log capture to `eval-logs/serve/`) + a real speed gate:
  streamed completions, **TTFT and decode tok/s split** (decode = (tokens−1)/(t_last−t_first)),
  median of 3. v1's single blended sample is gone.
- **`kvllm/score.py`** — schema-2 scorecards (suite `version` + Inspect log path per suite),
  verdict (same thresholds, now against decode tok/s), tri-format leaderboard with **† stale
  markers** for old-suite-version scores, v1-card fallbacks, `models.toml` write-back, and the
  `scorecard_current` resume predicate.
- **`kvllm/evalrun.py`** — the batch CLI: `just eval <key…>`, `just eval-all` (two-layer resume:
  scorecard-current skip at the model level, `eval_set` log-dir resume within a model,
  gate-`skip` models held behind `--retry-skips`), `--endpoint` to eval any served /v1 without
  orchestration, one-broken-model-doesn't-kill-the-sweep error handling.
- **`evals/sandbox_smoke.py` + `just eval-sandbox-smoke`** — proves Inspect executes bash in a
  Docker container *here* using a mock model (no GPU): scorer requires the marker in the **tool**
  message, so it can't pass without real sandbox execution. This is the go/no-go vehicle for the
  Phase 4 `DOCKER_HOST=ssh://` experiment.
- **v1 retired**: `kvllm/eval/` deleted; tests ported (`test_evals_tools.py`, `test_score.py`
  — 47 total, up from 37); `eval-logs/` gitignored; evals README rewritten.
- **Phase 2 spec written** (Fable → Opus handoff):
  [`planning/06-coding-suite-spec.md`](planning/06-coding-suite-spec.md) — 15 tasks
  (C1 functions ×6, C2 script-contract ×4, C3 fix/extend ×3, C4 iterate-to-green ×2),
  post-episode hidden-test injection, junitxml scoring with partial credit, the `recovered`
  iteration metric, suite self-test against reference solutions, acceptance criteria.

## Decisions & discoveries (Phase 1)

- **The bash() tool's parameter is `command`** (first sandbox smoke failed with a tool-parsing
  error on `cmd` — caught because the scorer checks the tool message, not the model's final text).
- **v2 exactly reproduced v1's per-case results** where they overlap. `qwen2.5-coder-7b-instruct`
  fails the same 4 of 7 (emits tool calls as ```` ```xml ````-fenced text the hermes parser can't
  extract — visible in the Inspect transcript) and also fails all 4 new hard cases → 3/11.
  `qwen2.5-7b-instruct` went **11/11**, `worth trying` reproduced, decode 105.5 tok/s,
  TTFT 0.02 s, cold 24 s. Orchestration stopped and restored the service cleanly around it.
- **Suites-for-capability mapping means `chat`/`reasoning`-only models are "current" with zero
  suites** — they get gate-only runs once and are then skipped; correct, but worth remembering
  when reading `eval-all` skip lines.
- eval-all selection verified without burning GPU-hours: 6 models queued (stale-v1 + untested),
  current + gate-skipped correctly held back. The actual sweep is an overnight job (~50 GB of
  downloads incl. the gated Llama) — deliberately not run in this session.

## Outcomes

`just check` green (47/47). Sandbox smoke PASS. One `--endpoint` run + one full orchestrated run
verified end-to-end; leaderboard v2 renders all three formats with stale markers; `models.toml`
verdicts intact. Ready for: the overnight `just eval-all` sweep, and Phase 2 implementation
against the spec.

## Incident — GPU wedged after the Phase 1 eval (2026-07-02, ~03:30–05:00)

The service restore after the orchestrated eval hung in CUDA-graph capture (healthy init = 5.8 s;
this one spun at 100% GPU for 57 min with no log output, `/v1` never opened). Diagnosis chain:
restart → hung again; SIGKILL by systemd → next start **crashed with
`CUDA error: an illegal memory access`** (kernel log: **Xid 13** Out-Of-Range Address) →
full NVIDIA module reload → *still* hung (py-spy: stuck in `profile_run/_dummy_run`), and the
other model now hung too → kernel log **Xid 119: GSP RPC timeout** + **Xid 154: "GPU Reset
Required"**. The GSP (on-card firmware CPU) wedged, which survives driver reloads; even `rmmod`
then jammed against it. PCI FLR attempt also blocked. **Resolution: reboot** (everything
auto-restores; linger + enabled units).

Probable trigger: the eval's rapid kill→restart cycle (standalone vLLM SIGTERM'd, service
started ~2 s later while VRAM was still draining) hitting a Blackwell/GSP fragility.

**Hardening shipped in response:**
- `evalrun` now manages the service **once per sweep** (stop before the first model, restore
  after the last) instead of per model — minimum GPU teardown/startup cycles, and faster sweeps.
- `evalctl.wait_gpu_drained()` — no serve ever starts until the previous one's VRAM is actually
  released (was: fixed 2 s sleep).
- SIGTERM grace 30 s → 60 s before SIGKILL (a SIGKILL'd CUDA proc is the suspected wedge vector).
- The restored service is **health-checked** (`wait_port_healthy`, 300 s) and a loud warning +
  nonzero exit on failure — tonight's hang went unnoticed for an hour because restore was
  fire-and-forget.

Live verification of the hardened path is pending the reboot.

## Full-registry sweep + Phase 1 checkpoint (2026-07-02, post-reboot)

Reboot cleared the GPU (hard power-off needed — the wedged `rmmod` blocked clean shutdown; zero
Xids since). Hardened orchestration verified twice, then `just eval-all` swept the 6 stale/untested
models unattended, restored the service, and passed the health check. Checkpoint findings:

- **Suite discrimination: good.** Spread is 27%–100%, and the sub-100% models fail *different,
  diagnostic* cases: `llama-3.1-8b` 10/11 (calls a tool on the no-tool case),
  `qwen2.5-14b-awq` 10/11 (won't parallelize), `qwen2.5-coder` 3/11 (```xml-fenced calls the
  hermes parser can't extract — v1-consistent, case-for-case).
- **v1 verdict overturned with data — `qwen3.6-27b-awq` is fine here: 45.5 decode tok/s**
  (TTFT 0.07 s), 11/11 tools → `worth trying`. v1's 2.5 tok/s is unreproducible post-reboot; the
  6-30 measurement was taken right after its CUDA-graph OOM, i.e. plausibly on an
  already-degraded GPU (same failure region as the wedge incident). Still serving
  `enforce_eager` — worth re-trying capture now (follow-up).
- **New gate catch: `qwen3-8b-fp8` → skip.** DeepGEMM FP8 kernel assert on sm_120
  (`Unknown SF transformation`) at engine init. The "FP8 native-fast on Blackwell" survey note
  didn't survive contact with this kernel path.
- Two harness bugs found by the sweep + fixed with tests: `measure_speed` missed reasoning-model
  streams (thinking-only deltas → no timing; now falls back to chunk-arrival timing, and warns
  instead of silently writing no speed — which had let the 27B dodge the speed-cap verdict),
  and `serve_error` surfaced re-raise wrapper lines instead of the root cause (now skips
  wrappers/`raise` lines; fp8's registry note carries the real DeepGEMM assert).

Registry after the sweep: 7 of 10 `worth trying`, 1 `has issues`, 2 `skip` — all data-backed.

## What shipped — Phase 2: S2 coding suite (Opus, 2026-07-02)

Implements [`planning/06-coding-suite-spec.md`](planning/06-coding-suite-spec.md): a
react agent codes in a Docker `/workspace` (bash tool), then a scorer injects hidden pytest tests
the model never saw, runs them in the sandbox, and scores partial credit from junit XML — never
from the model's claims.

- **`evals/coding_assets/`**: `Dockerfile` (python:3.12-slim + pinned pytest, non-root) +
  `compose.yaml` (`network_mode: none`, mem/cpu/pids caps); **15 tasks** — C1 single-function ×6,
  C2 script/IO-contract ×4, C3 fix-a-seeded-repo ×3, C4 iterate-to-green ×2. Each: `prompt.md`,
  `hidden/`, reference `solution/`, and (C2/C3/C4) `seed/`. Every seed verified to *fail* its
  visible tests (planted bugs real); every reference solution verified to *pass* its hidden tests.
- **`evals/coding.py`**: `coding()` task (per-tier message limits via `apply_limits`; time_limit
  600 s; bash timeout 120 s), `react(attempts=1)` (C4 measures *self*-iteration), and
  `coding_scorer` — post-episode hidden-test injection, ×0.9 hit-limit factor, and the `recovered`
  iteration metric. `parse_junit` / `extract_coding_signals` are pure (unit-tested).
- **Integration**: `code` registered in `kvllm.evalrun::_suites()`; `score.suite_from_log`
  generalized for partial-credit (float) scores + per-suite `iteration_rate`;
  `score.merge_prior_suites` folds prior suites forward so `--suite code` keeps a model's `tools`
  row on the leaderboard; each suite now runs in its own log subdir (`…/<date>/<cap>`) so
  cross-suite runs and `--force` don't collide.
- **`just test-coding-suite`** (`evals/coding_selftest.py`): seeds each reference solution, runs
  the real scorer, asserts `raw_frac == 1.0` ×15 **and** the sandbox has no network — all pass.
- **Tests**: 20 pure-function unit tests (66 total; `just check` green).

### Acceptance results (2026-07-02) — the suite discriminates, and a scoring artifact to resolve

| model | code pass_rate | tools (merged) | note |
|---|---|---|---|
| qwen2.5-7b-instruct | **0.48** | 100% | uses bash, solves 4 tasks to 100% hidden (slugify, dedupe, merge-intervals, jsonmerge) |
| qwen2.5-coder-7b-instruct | **0.05** | 27% | never calls a tool at all |

**The suite works and discriminates ~10×.** Both drop to `has issues` (agentic coding < 80%) —
honest: neither 7B is a competent coding *agent* here.

**Flagged for the Fable end-of-phase review (transcripts left in `eval-logs/<model>/2026-07-02/code/`):**

1. **qwen2.5-coder writes code in a ```python markdown block and never calls `bash` or
   `submit`** — it treats the agent task like a chat question (transcript: correct slugify code,
   in prose, zero tool calls). The "never trust the model's claims" trust rule paid off exactly
   here: it *says* "implemented and tested", the workspace is empty, hidden tests score 0.
2. **Neither 7B Qwen ever calls `submit()` (0/15 each)** — verified the submit instruction is
   present in both the react system prompt (`AgentPrompt` defaults survive `prompt=""`) and the
   task's user message, so this is model behavior, not a harness gap. Consequence: **every task is
   `hit_limit=True` → ×0.9, and because "fully-solved" is counted as `score ≥ 0.999`, a task
   qwen2.5-7b solved to 100% hidden shows as *not passed* (0/15 fully-solved despite pass_rate
   0.48).** The ranking number (pass_rate) is honest; the "N/15 passed" integer is misleading.
   **Recommend Phase 3 (scoring/weighted-composite) decide:** base the fully-solved count on
   `raw_frac`, and/or skip ×0.9 when `raw_frac == 1.0`, and/or tune the submit prompt for these
   models, and/or raise message limits. Left as-is now (spec mandates ×0.9-on-limit; scoring
   refinement is Phase 3's charter).
3. **`iteration_rate` did not populate** even though qwen2.5-7b ran the seeded visible tests on
   C3/C4 (`test_runs` 5–6): `saw_failing_run` never fired, so the failure-detection heuristic on
   bash tool output (`_output_indicates_failure`) needs validation against real pytest-failure
   output in the sandbox. Phase 3 follow-up.

## Decisions & discoveries (Phase 2)

- **Verified 4 spec `VERIFY` items empirically before building** (mock model + Docker, no GPU):
  `Sample.files` land in `/workspace` (WORKDIR), the network is off, sandbox
  `write_file`/`read_file` round-trip for hidden-test injection, and `react()` works as a
  top-level Task solver.
- **Real harness bug caught in the first acceptance run + fixed with a test:**
  `apply_limits(catch_errors=True)` *suppresses* the `LimitExceededError`, so
  `return await react(...)` inside the `with` returned `None` on a caught limit → inspect did
  `None.completed` and cancelled the whole run (first coder run errored, 0/8). Fix: assign inside
  the `with`, return the in-place-mutated state after it. Verified with a never-submits mock model.
- **Docker compose project names can't start with `_`** — the self-test's `@task` functions had
  to be renamed off leading underscores (`inspect-_net_task-…` = "invalid reference format").
- **Capability gate is load-bearing**: `--suite code` on `qwen2.5-7b-instruct` initially ran
  *nothing* because its registry caps were `["chat","tools"]` (no `code`). Added `code` to it (it
  does gold-standard tool calls and can write Python) as the coding-suite contrast — the capability
  gate correctly refused to run the suite until the model was tagged for it.
- **Minor (pre-existing, not fixed):** `tomlkit` write-back appends new `eval_*` keys after a
  model entry's *trailing comment block*, so `qwen2.5-14b-instruct-awq`'s verdict now sits visually
  below the survey comment. Still valid TOML (comments don't end a table; keys attach correctly —
  verified) — cosmetic only.

## Outcomes (Phase 2)

`just check` green (66 tests). `just test-coding-suite` PASS (15/15 reference solutions at 1.0 +
network-off). Both acceptance models scored end-to-end through the hardened orchestration (service
restored + health-checked each time); leaderboard shows the new `code` column beside merged `tools`
scores. Suite discriminates 0.05 vs 0.48. STOP per hand-off scope: no Phase 3, no eval-all, no reimage.

## Phase 2 Fable review (2026-07-02)

Approved with one finding overturned. #1 (coder never calls tools) and #2 (submit/×0.9/passed
distortion) confirmed via transcripts. **#3 was wrong**: `iteration_rate` populated fine — it is
**0.0**, a true measurement (Opus read the earlier capability-gated run). The richest transcript:
qwen2.5-7b on `c3-inventory` runs `pytest` **five times with zero edits between runs**, narrating
"the issue still persists" — it believes its prose descriptions of fixes are edits. Same
hallucinated-action pathology as the coder, one notch milder: greenfield-write works,
read-diagnose-edit doesn't. Exactly the discrimination S2 was designed to find.

## What shipped — Phase 3: composite, judge, gate extensions (Fable, 2026-07-02)

- **Coding scoring v2** (resolves review finding #2): ×0.9 only when a REAL limit fired
  (`LimitScope.limit_error` at runtime / `sample.limit` log-side); "ended without submit()" is
  recorded, not penalized. `passed` = raw_frac ≥ 0.999. `suite_from_log` recomputes canonically
  from logged evidence — both 7Bs re-scored from cached transcripts, no GPU re-runs
  (qwen2.5-7b code 48%→53%, its four fully-solved tasks now count).
- **`eval-config.toml` + composite**: weights (tools .30 / code .35 / agentic .25 / judged .10),
  speed curve (floor 10 → 0.5×, full 40 → 1.0×), verdict floors. `score.composite()` renormalizes
  over *eligible* suites (weight>0, current version, judged only when calibrated); gate-only
  models are unranked, not zero-ranked. **Verdict v2** derives from the composite — qwen2.5-7b
  promoted has-issues→worth-trying (0.75; a strong generalist with mediocre-but-real agentic
  coding isn't broken), coder stays has-issues via the suite floor (tools 27%).
- **Leaderboard v3**: ranked, ①②③ medals, composite column, weights footer;
  `evalrun --rebuild-board` re-ranks + refreshes stored verdicts after re-weighting — no re-runs.
- **S4 `judged` suite** (6 tasks: incident summary, strict JSON, migration plan, config
  explanation, constrained list, professional rewrite) with rubric + auto-zero + reference
  facts; mechanical pre-checks cap the score on objective format rules; judge =
  `[judge].model` (Haiku 4.5) returning structured score/rationale/violations → rationales in
  scorecards. Suites now declare a *required capability* (`judged` rides on `chat` — every
  model). Live on both 7Bs: **63%/62%** — close on general instruction-following (plausible for
  siblings), and the judge is sharp: it caught a fatal stale-dump data-loss flaw in a migration
  plan and a root-cause inversion in an incident summary, rubric-grounded.
- **Calibration bundle**: `model-research/evals/calibration/judged-sheet.md` (12 rows) for
  Ken to hand-score; **judged stays out of the composite until `[judge].calibrated = true`**
  (protocol: judge within ±1 on ≥80%). ANTHROPIC_API_KEY rides in the repo-local gitignored
  `.env` (just's dotenv-load).
- **Gate extensions**: `context_probe()` (75%-of-max_model_len prompt must complete;
  `ctx_probe_ok` recorded, failure caps the verdict — passed live), and v1-gate cards now count
  as stale in `--all` selection (deepseek/internvl re-measure next sweep).
- anthropic pinned ≥0.115 (inspect provider floor; venv had vllm's 0.113 → first judged run
  errored cleanly). 93 unit tests green.

## Decisions & discoveries (Phase 3)

- **Composite exposes the coverage story honestly**: models scored only on `tools` currently
  out-rank qwen2.5-7b (which also carries the much harder code suite) — renormalization means
  "fewer suites = friendlier composite" until coverage evens out. The fix is coverage, not math:
  `qwen3.6-27b-awq` now has the `code` cap and queues for the coding suite next sweep, and
  `judged` runs on everything.
- The judged 63/62 near-tie between siblings is expected; discrimination within this suite will
  come from stronger vs weaker model families (and the rationales already differentiate quality).
- models.toml cosmetic: moved the 14b's eval keys above the survey comment block (tomlkit
  appends after trailing comments; was valid TOML, read wrong).

## Judge calibration + Phase 4 build (Fable, 2026-07-02, while Ken preps ksandbox)

- **Calibration PASSED**: Ken hand-scored all 12 rows — 12/12 within ±1 (mean |Δ| 0.42);
  `[judge].calibrated = true`, judged now in the composite. Per Ken's feedback the sheet
  generator is now self-contained (task prompt + data + rubric inline; final capped score
  shown beside the judge's content score). Follow-up: judge grades rewrite tone ~1 pt harsher
  than Ken's no-pleasantries preference — "Ken's voice" rubric adjustment candidate.
- **S3 agentic suite built per the 07 spec** (deviation: fixture state is runner-readable —
  shims run as runner; the ground truth equals what the shims render, so no cheat surface):
  fixture-homelab image (`systemctl`/`journalctl`/`korg` shims over per-scenario JSON; real
  filesystem/process state via per-sample `setup` where the model touches it), 8 episodes,
  hybrid 0.6-mechanical/0.4-judge scoring with **fabrication → auto-0**. Self-test 8/8
  (every planted truth discoverable + reference reports score 1.0). Registered under the
  `tools` capability at agentic weight 0.25.
- **Acceptance: the suite discriminates within the competent-tools tier and re-ranked the
  fleet.** qwen2.5-7b **24%** vs llama-3.1 **9%**: llama fell ③ 0.91 → 0.54 `has issues`
  (template placeholder answers, fabricated a /tmp culprit, reported a box healthy while
  backup-sync was failed); qwen2.5-7b nailed a1 (facts 100%, judge 7/10) but fabricated on
  a3/a4 (invented `pg_config` and letsencrypt causes — the auto-0 fired) and emitted a
  **degenerate tool-call flood** on a7/a8 (135 identical `history | grep` calls in one
  message, no text). The scorer now names floods in the scorecard instead of "no answer".
- **Controller-readiness signal (the point of S3):** neither 7B/8B is close to being a
  trustworthy homelab monitor — they fabricate under uncertainty and degenerate under
  open-ended prompts. `a8-honesty` and the fabrication rule are load-bearing exactly as
  designed. 110 unit tests green.

## Frontier baselines + a9 sprint-planning eval (Fable, 2026-07-02, while Ken preps ksandbox)

Per Ken's two asks: (1) a work-selection/planning eval, (2) Claude baselines with real cost capture.

- **Frontier baselines**: registry entries can be API models (`provider` + `baseline = true`);
  `claude-haiku-4-5` and `claude-sonnet-5` added. Same suites, no serve/gate, verdict `baseline`
  (🌐); `--all` never runs them (no silent API spend); a baselines-only run leaves
  kvllm.service untouched. Token usage per run from inspect log stats (subject vs judge,
  separately) priced via the new `[pricing]` config — leaderboard gains **est $/run**; totals
  span all current suite logs so partial reruns can't shrink the reported cost.
  temperature=0.0 now applies to local models only (Sonnet 5 rejects non-default sampling);
  baselines run as-shipped (Sonnet 5 = adaptive thinking on).
- **a9-sprint-plan** (agentic v2): 6 fixlab WI fixtures with a planted backup-reliability
  cluster (201/202/203), off-theme filler (204), blocked (205), done-but-open (206); mandated
  `sprint:` closing line; mechanical checks (cluster ≥2, no blocked/done, 3–5 real items) +
  judge rubric ("a plan is a decision, not a list").
- **Baseline results — the local-vs-frontier gap, priced:**
  | model | tools | code | agentic | judged | full-suite est cost |
  |---|---|---|---|---|---|
  | claude-sonnet-5 | 100% | **100%** | **77%** | 85% | **$0.81** |
  | claude-haiku-4-5 | 100% | **100%** | 68% | 87% | **$0.68** |
  | best local (qwen2.5-7b) | 100% | 53% | 24%† (v1) | 62% | power only |
  Both baselines aced the coding suite the locals cratered on (15/15 each), and **both scored
  9–10/10 on a9 sprint planning** — the planning slice of the controller role is solved at
  frontier tier, unproven locally (locals re-run on the next sweep, agentic now v2†).
- **Calibrating the suite against thorough investigators** (three fixes, each verified):
  agentic message limit 25→40 + an explicit step budget in the prompt (Haiku burned 23
  messages probing and never reported — thoroughness was being scored as failure); systemctl
  shim gained `list-unit-files`; **Haiku caught a real fixture bug** — WI #201 described a
  live backup failure visible in every scenario, including the "healthy box" honesty task;
  it cross-referenced korg against systemd and reported our inconsistency as a finding. WIs
  are now scenario-scoped (`wi_sets`). Judge-prompt hardening: fabrication = detail that
  CONTRADICTS reference facts; observed-style detail from the model's real shell (metrics,
  log lines, korg output) is never fabrication — killed a false-positive storm that had
  zeroed legitimate 9–10/10 answers.
- Haiku agentic trajectory across calibration: 18% → 39% → 58% → 68% — the residual gap to
  Sonnet (77%) is model, not harness. a8-honesty still catches Sonnet fabricating specifics
  under an all-clear, and a5 catches both baselines putting the done-but-open WI in "ready".

## ksandbox cutover (Fable, 2026-07-02 — Ken reimaged, Fable flipped the switch)

Ken finished 04-sandbox-host checklist items 1–3 (Ubuntu 24.04 reimage, homelab-standard access,
Docker 29.6.1); specs turned out i5-13400F / 16 threads / 32 GB — comfortably above the 4–8
parallel-episode target. Cutover, in order:

- `docker context create sandbox --docker host=ssh://ken@ksandbox` + hello-world: OK.
- Remote `eval-sandbox-smoke`: **PASS in 7s** — `DOCKER_HOST=ssh://` works with Inspect despite
  being unofficial (inspect_ai #540); the fallback plan (runner on the sandbox host) stays
  unused.
- Remote agentic self-test: **9/9**. Remote coding self-test: **FAIL**, and it was real — the
  15-sample fan-out storms sshd with one fresh ssh connection per concurrent `docker compose`
  call, tripping `MaxStartups` (default 10): `kex_exchange_identification: Connection reset by
  peer` → "No services started". The 9-sample agentic suite had squeaked under the limit. Fixed
  both halves: **ControlMaster/ControlPersist multiplexing** for `Host ksandbox` in kai's
  `~/.ssh/config`, plus `MaxSessions 64` / `MaxStartups 64:30:128` in a sshd drop-in on
  ksandbox (multiplexed channels count against MaxSessions, default 10). Coding self-test then
  **15/15 + network-off probe**.
- Harness wiring: `[sandbox].docker_host` in eval-config.toml (env `DOCKER_HOST` overrides,
  empty = local Docker) — `_apply_sandbox_host()` in evalrun, unit-tested. No one has to
  remember an env var; `just eval` prints which sandbox host it picked.
- Proof run: `just eval qwen2.5-7b-instruct --suite agentic --force` — served on kai, all 9
  episodes ran **concurrently** on ksandbox (zero sandbox CPU on kai), judge scored, scorecard +
  board written, service restored. One sample hit a context-length 400 mid-episode and
  eval_set's retry recovered it. Two sharp edges surfaced: same-day logs from an older task
  manifest make eval_set refuse the log dir (`--force` clears exactly that suite dir — designed
  remedy); and the first agentic-v2 local result is sobering — **28% (1/9)** vs Haiku 68% /
  Sonnet 77%: a3 fabricated a causal chain (auto-zero), a7 degenerate-flooded 107 tool calls in
  one message, a9 scheduled the blocked WI. Only a8-honesty passed (10/10). The v1-stale † on
  the board was hiding most of this; the rest of the fleet gets refreshed in the overnight
  sweep.

## Candidate sweep + judged v2 (Fable, 2026-07-03)

The overnight `eval-all --retry-skips` (first run tripped on stale same-day logs → the
self-heal fix in b0fef15) delivered the first fully-covered board, with sandboxes on
ksandbox throughout. Then a results review caught two harness artifacts, both fixed and
re-run the same night:

- **judged v2** (max_tokens 1024 → 4096): the Qwen3.5/3.6 family burned the whole budget in
  `<think>` and submitted EMPTY answers — the judge was scoring blanks (0-17%). Post-fix:
  35B-A3B 0→90%, 27B 0→92%, 9B 17→42%. Verified by raw-sample inspection
  (stop_reason=max_tokens, reasoning 3180 chars, text len 0).
- **devstral ctx 32K → 8K**: FP8 weights left 1.69 GiB for a 5 GiB KV ask. Served fine at 8K:
  code 95%, judged 90%, composite 0.75.

Board after reruns: baselines ①② (0.94/0.91) — no local beats them yet;
**gemma-4-12b-it best local ③ 0.78** (judged 92% *beats both baselines*; multimodal);
35B-A3B #4 0.76 (code 100%); glm-4.7-flash 197 tok/s, gpt-oss-20b 305 tok/s.
**The agentic column is now THE local gap**: best local 44% (qwen3-vl-8b) vs frontier
68/77% — every 2026 candidate aces code and flunks multi-step investigation. Most locals
carry judged† (v1) pending a refresh sweep.

## A local takes ① + the assisted condition (Fable, 2026-07-03)

Fixing the two real sample-killers (time limit → scored-partial inside the solver; 4KB tool
output cap; then episode concurrency 3 for locals — 9-way parallelism against one 42 tok/s
vLLM had turned time budgets into queue-wait) rewrote the top of the board:

- **gemma-4-31b-awq: agentic 12% → 84%** — beats Haiku (68%) AND Sonnet (77%) on the ranked
  suite, and takes **① overall at 0.94**, edging Sonnet. "Actual leaders rise": with harness
  artifacts removed, a local earned #1 honestly.
- **Assisted condition** (controller scaffolding, unranked): Haiku's +14% (68→82%) is the
  generic-uplift control. Deltas above it are pacing rescue: **devstral +86% (11→97% — the
  highest agentic-condition score of ANY model incl. the baselines)**, glm-4.7 +53% (→87%),
  gemma-12b +34% (→74%). The agent-tuned 2026 class had the skills and lacked only the pacing.
- **qwen3-vl-8b assisted −14% is a finding, not noise**: with longer episodes it fabricated
  twice (auto-zeros) where raw limits had cut it off first. More rope reveals hallucination —
  disqualifying signal for the monitor role that the raw suite was masking.
- Hybrid Qwens (27B/35B) remain partially unscored even post-fix — concurrency starvation
  (now capped); one 8193-token truncation boundary one-off. Re-run queued.

**Hybrid-plan readout (Ken's framing — local monitor + frontier heavy-lifting):** under a
controller loop, devstral/glm/gemma-31b operate at-or-above raw-Haiku level on the fixture
homelab, at power-only cost. The frontier premium concentrates in self-pacing and
trustworthiness-under-freedom — exactly what the controller layer (and #105's pre-work
pattern) is designed to supply.

## Follow-ups (carried forward at close)

- Qwen hybrid rerun under the concurrency cap: `just eval qwen3.6-27b-awq
  qwen3.6-35b-a3b-awq --suite agentic --force` (their 11%/9% include unscored
  starvation deaths); optional `--suite assisted` for gemma-31b (does ① respond to
  scaffolding too?).
- Leaderboard est-$ column scopes to the latest date-dir (Haiku shows assisted-only $0.23);
  cost should merge across a card's contributing runs.
- ksandbox hygiene remaining (04-sandbox-host item 6): optional LAN-egress firewall; keep
  secrets/HF tokens off the box.
- "Ken's voice" rubric adjustment for professional-rewrite; `just gpu-health` recipe.
- Phase 5 (vision suite) — next feature sprint after the findings/restructure sprints.

## Sprint close (2026-07-03)

Exit state vs the goal ("rich eval harness where actual leaders rise"): **delivered and
proven** — four ranked suites + assisted condition, calibrated judge, weighted composite
with costs, frontier baselines, remote sandboxing on ksandbox, rich clickable board, and a
board where a local model (gemma-4-31b-awq, 0.94) holds ① honestly against priced Claude
baselines. 132 unit tests + fixture self-tests green. The harness survived three
review-fix-rerun cycles with strictly diminishing bug severity (token budget → time limit →
tool output → concurrency), which is the stability signal that says measurement, not
artifact. Findings distillation and repo restructure move to sprints 09/10.

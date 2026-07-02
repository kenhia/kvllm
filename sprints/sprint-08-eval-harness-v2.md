# Sprint 8 — Eval harness v2 (Inspect AI, sandboxed agentic+coding, weighted leaderboard)

_2026-07-02 on `kai`. korg #104. Branch `08-eval-harness-v2`. Builds on
[Sprint 7](sprint-07-eval-harness.md). Planning in [`sprints/fable-planning/`](fable-planning/README.md)
(repo review, stack decision, suites/scoring design, sandbox-host plan, phased roadmap)._

## Goal

Turn the Sprint 7 MVP eval into the rich harness Ken wants: agentic + coding episodes in sandboxes,
frontier-model judging, a weighted composite leaderboard. This sprint covers **roadmap Phase 0**
(hygiene) — see [`fable-planning/05-roadmap.md`](fable-planning/05-roadmap.md) for the full phased
plan (Phase 1 — episode runner core + Inspect AI migration — is next).

## Plan (Phase 0, per the roadmap)

Review items 4, 7, 10 from [`fable-planning/01-current-state-review.md`](fable-planning/01-current-state-review.md):
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
  [`fable-planning/06-coding-suite-spec.md`](fable-planning/06-coding-suite-spec.md) — 15 tasks
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

## Follow-ups
- **Phase 2** (coding suite): implement with **Opus** against
  [`fable-planning/06-coding-suite-spec.md`](fable-planning/06-coding-suite-spec.md).
- Context-pressure probe deferred from the gate (fable-planning/03 §S0) — add in Phase 3.
- Consider a `just gpu-health` recipe (Xid scan + drained check) for pre-sweep sanity.

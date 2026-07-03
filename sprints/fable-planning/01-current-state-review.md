# Current-state review — what's in the repo today

_2026-07-02, fable-planning. A pre-planning review of the whole repo (~1,300 lines of Python across
`registry.py`, `helper.py`, `eval/`, plus docs/sprints), feeding the eval-harness plan in
[02-eval-harness-architecture.md](02-eval-harness-architecture.md)._

## What's here

| Piece | State |
|---|---|
| `models.toml` + `kvllm/registry.py` | Model registry (9 entries) → `vllm serve` argv builder; `list/show/serve` CLI. |
| `deploy/` + systemd user units | `kvllm.service` (model) + `kvllm-helper.service` (panel); reboot-survival verified. |
| `kvllm/helper.py` | LAN control panel (FastAPI): status, switch model, start/stop. Token-gated, fails closed. |
| `kvllm/eval/` | Sprint-07 MVP: operational gate + 7-case tool-use suite + tri-format leaderboard + `models.toml` write-back. |
| `tests/` | Three network smoke scripts (tools, LangChain, DeepSeek) — exit criteria for Sprint 1, not unit tests. |
| `docs/`, `sprints/` | Strong narrative docs; `model-research/` is a working research pipeline with two skills (`/model-research`, `/model-scout`). |

## What's good (keep these properties)

- **The registry is the right spine.** One TOML file as the single source of "what can run here",
  with serve flags as data and `tomlkit` write-back that preserves hand comments. The eval harness
  v2 should stay registry-driven.
- **The operational gate is the highest-ROI eval idea in the MVP.** "Does it serve on sm_120, fit
  32 GB, and produce tokens at a usable rate?" already produced three real verdicts (including the
  35B OOM skip and the 27B "2.5 tok/s — has issues"). Keep it as stage 0 of every eval.
- **Serve orchestration works**: stop `kvllm.service` → serve target → eval → restore, with
  process-group kill and fast-fail when the serve process dies (caught a real OOM). This logic is
  worth extracting, not rewriting.
- **Tri-format outputs** (`.json` source of truth, `.md` for agents, `.html` for humans) is a good
  convention — harness v2 should keep it.
- Code quality is high for the size: docstrings state intent, errors are handled where they matter,
  `ruff` is clean, and the sprint log records the *why* (e.g. the `Path.with_suffix` bug).

## Gaps and recommendations

Ordered by how much they matter to the harness plan; (H) = addressed by the harness plan itself,
(R) = repo hygiene worth doing regardless.

1. **(H) One model per invocation, no batch/resume.** `just eval <key>` only. "Test all/subset of
   the registry" needs a run manifest: iterate keys, skip already-scored-at-this-suite-version,
   survive a crash mid-batch. Model swaps cost minutes each, so a full-registry run is an
   hours-long job that must be resumable.
2. **(H) Scoring is binary and unweighted.** A suite pass-rate ≥ 0.8 → "worth trying". There's no
   composite score, so the leaderboard can't rank — it can only sort alphabetically. Weighted
   scoring is a core requirement of harness v2 (see [03](03-suites-scoring-leaderboard.md)).
3. **(H) The eval client is welded to the serve orchestrator.** `runner.py` assumes
   `localhost:8000` and local `systemctl --user`. Splitting "make model X servable and give me a
   base URL" from "evaluate whatever is at this base URL" is a precondition for the sandbox host,
   for evaluating remote endpoints, and for pointing the same suites at a cloud model as a
   calibration baseline.
4. **(R) Zero unit tests.** `score_case`, `_args_subset`, `_verdict`, and the report renderers are
   pure functions — cheap to test, currently untested, and about to be extended. The
   `Path.with_suffix` bug (Sprint 07) is exactly the class of thing a 20-line pytest file catches.
   Add a `pytest` dep group and a `just test`; wire it into `just lint` → `just check`.
5. **(H) Throughput measurement is a single noisy sample.** `_measure_tps` times one 128-token
   completion including prefill. Fine as a gate; not fine as a leaderboard column that feeds a
   weighted score. v2 should measure decode tok/s (exclude time-to-first-token), median of 3, and
   record TTFT separately.
6. **(H) Suite results have no versioning.** Scorecards don't record which suite revision produced
   them, so when cases are added/changed, old and new pass-rates silently mix in the leaderboard.
   Add `suite_version` (or a content hash) per suite to the scorecard, and treat "scored on an
   older suite" as stale for ranking.
7. **(R) `--today` defaults to `"undated"`.** Only the justfile injects the date; running
   `python -m kvllm.eval` directly writes `*-undated.json` files that sort oddly in
   `_latest_scorecards`. Just default to `date.today().isoformat()` in the runner.
8. **(R) `_serve_error`'s pattern list ends with bare `"Error"`** — best-effort is fine, but it can
   surface an irrelevant line (e.g. a warning containing "Error") as *the* failure reason that then
   gets written into `models.toml` as `eval_notes`. Consider scanning only the tail of the log and
   preferring the last traceback.
9. **(R) No remote / no CI.** The repo has no git remote — nothing enforces `just lint` before a
   commit. Options: add a pre-commit hook running `ruff check + format --check` (+ pytest once it
   exists), and/or push to a private GitHub remote (the `/sprint-ship` skill already assumes `gh`).
10. **(R) Uncommitted eval results in the working tree** (leaderboard + three new scorecards +
    `models.toml` verdicts from post-Sprint-07 runs). Commit these before harness work starts so
    v1 results are a clean baseline.
11. **(Minor) `helper.py` `_v1_served_model` and eval both hardcode port 8000 defaults separately**
    — one `KVLLM_PORT` read; fine today, worth centralizing when the controller lands.

## Verdict

The repo is a healthy serving harness with an honest MVP eval bolted on. Nothing here needs a
rewrite; the eval harness v2 plan deliberately **reuses** the registry, the serve orchestration,
and the scorecard/leaderboard conventions, and **replaces** the flat request/response suite runner
with a real agentic episode runner (sandboxed code execution, multi-turn tool use, judge scoring).
See [02-eval-harness-architecture.md](02-eval-harness-architecture.md).

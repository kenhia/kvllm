# S2 coding suite — task-design spec (Phase 2, build with Opus)

_2026-07-02, planning. Authored by Fable per the model guidance in
[05-roadmap.md](05-roadmap.md): this spec makes the design decisions; Opus implements against it.
Read [02-eval-harness-architecture.md](02-eval-harness-architecture.md) first — Phase 1 shipped
the episode runner (`kvllm/evalrun.py` + `evals/`), and the Docker sandbox path is proven
(`just eval-sandbox-smoke` passes on kai). Where this spec says VERIFY, confirm the Inspect API
detail before relying on it; if reality disagrees with the spec, note it in the sprint doc and
pick the closest equivalent — do not redesign silently._

## Shape of the suite

- **Module:** `evals/coding.py` exporting `@task coding()` and `VERSION = 1`; assets in
  `evals/coding_assets/<task-id>/`. Register in `kvllm/evalrun.py::_suites()` under the registry
  capability **`code`** — nothing else in the harness changes.
- **Episode:** Inspect `react()` agent with the `bash()` tool (sandbox-backed), working in
  `/workspace`. Instructions template (same for all tiers):
  > You are working in /workspace inside a Linux container. {task_prompt}
  > Write your code, **run it to check it works**, and iterate until you're confident.
  > When done, call submit() with a one-line summary. There is no network access.
- `react(attempts=1)` — no scorer-gated retries; C4 measures *self*-iteration, and harness
  retries would contaminate that signal.
- **Limits:** `message_limit=30` (C1/C2) / `40` (C3/C4); `time_limit=600` per sample; bash exec
  timeout 120 s. Config: `GenerateConfig(temperature=0.0)`.
- **Sandbox:** `sandbox=("docker", "evals/coding_assets/compose.yaml")` — one service, image
  built from `evals/coding_assets/Dockerfile`: `python:3.12-slim` + `pytest` (pinned), non-root
  user, `network_mode: none`, `mem_limit: 2g`, `cpus: 2`, `pids_limit: 256`, writable
  `/workspace`. Nothing else installed — tasks are stdlib-only by design.
- **Workspace seeding:** C3/C4 skeletons ship via `Sample(files={...})` (VERIFY: files land
  relative to the sandbox working dir). **Hidden tests are NOT in `files`** — the scorer injects
  them post-episode (below).

## Scoring (mechanical)

Custom `@scorer` per sample, after the episode ends:

1. `sandbox().write_file()` each hidden test from `coding_assets/<task-id>/hidden/` into
   `/workspace/.hidden_tests/` (post-episode injection so the model can never read or game them).
2. `sandbox().exec(["python", "-m", "pytest", ".hidden_tests/", "-q", "--tb=no",
   "-p", "no:cacheprovider", "--junitxml=/workspace/.hidden_tests/report.xml"], timeout=120)`.
3. Read `report.xml` back and parse pass/fail counts from it (not from stdout regex — junitxml is
   the robust path). Task score = `passed / total` (**partial credit**), `× 0.9` if the episode
   hit its message/time limit.
4. `Score.value` = the float; `explanation` = the failed test names + last pytest line;
   `metadata` = `{"tier", "hit_limit", "test_runs", "recovered"}` where:
   - `test_runs` = count of bash commands in the transcript matching `pytest|python .*test`
   - `recovered` = at least one such run's tool output indicated failure AND the final hidden
     pass fraction ≥ 0.8 — this is the **iteration metric** (planning/03: the single most
     important agentic-coding behavior for our use case).
5. Suite `pass_rate` (mean of task scores) flows into the scorecard exactly like `tools`;
   additionally put `iteration_rate` (mean of `recovered` over C4 + any task with a failing run)
   in the suite dict — displayed in the per-run `.md`, not yet in the composite (Phase 3).

Trust rule: **never** score from the model's own claims ("all tests pass") — only from the
injected hidden run. The model may have modified `/workspace` arbitrarily; that's fine, the
hidden tests import/invoke its artifacts fresh.

## The 15 tasks

Every task ships: `prompt.md` (what the model sees), `hidden/test_*.py` (scoring), and
`solution/` (a reference implementation — **never enters the sandbox**; it exists so the suite
can be self-tested). Hidden tests: 6–12 asserts each, covering the stated edges; deterministic;
stdlib-only; each test file runnable standalone.

### C1 — single function (6 tasks, message_limit 30)

The model writes `/workspace/<name>.py` exposing one function. Hidden tests import it.

| id | contract | edges the hidden tests must cover |
|---|---|---|
| `c1-slugify` | `slugify(text) -> str`: lowercase, alnum runs joined by single `-`, no leading/trailing `-` | empty string, all-symbols → `""`, unicode letters dropped, repeated separators collapsed |
| `c1-parse-size` | `parse_size(s) -> int` bytes from `"1.5G" / "512M" / "3K" / "42"` (K/M/G = 1024ⁿ, case-insensitive, optional trailing `B`) | bare int, float value, `"1.5GB"`, whitespace, invalid → `ValueError` |
| `c1-merge-intervals` | `merge_intervals(pairs) -> list` of merged, sorted `(lo, hi)` | empty, single, touching (`[1,2],[2,3]`), fully nested, unsorted input |
| `c1-dedupe` | `dedupe(seq, key=None) -> list` first-occurrence order | key collisions, empty, all-dupes, key=str.lower |
| `c1-parse-duration` | `parse_duration(s) -> int` seconds from `"1h30m"`, `"90s"`, `"2h"`, `"45"` | bare seconds, order fixed h→m→s, zero, invalid unit → `ValueError` |
| `c1-tail-lines` | `tail_lines(path, n) -> list[str]` last n lines, no trailing `\n`s | n=0, n > file lines, empty file, no final newline |

### C2 — script with an I/O contract (4 tasks, message_limit 30)

The model writes `/workspace/<name>.py`; hidden tests run it via `subprocess` and assert on
exact stdout. Prompts specify the output format precisely (these are format-following tests as
much as coding tests). Input fixtures are seeded via `Sample(files=...)` so the model can test
against them.

| id | contract |
|---|---|
| `c2-logsum` | `python logsum.py <logfile>`: lines like `2026-07-01 12:00:01 ERROR msg…`; print `LEVEL count` per level (desc count, then alpha), then `top errors:` and the 3 most common ERROR messages as `count× msg` |
| `c2-csvfilter` | `python csvfilter.py <file> col=value [col=value…]`: print header + matching rows, preserving order and quoting (use the `csv` module both sides) |
| `c2-jsonmerge` | `python jsonmerge.py a.json b.json […]`: deep-merge (later wins, dicts recurse, arrays/scalars replace), print `json.dumps(result, indent=2, sort_keys=True)` |
| `c2-dumon` | `python dumon.py <threshold-mb>` reading `du -k`-style stdin (`<kib>\t<path>`): print paths over threshold as `<mb-rounded> MB  <path>`, largest first (homelab flavor) |

### C3 — fix/extend a seeded mini-repo (3 tasks, message_limit 40)

`Sample(files=...)` seeds `/workspace` with source + a **visible** test file where some tests
fail. Prompt: "make the tests in tests/ pass without changing the tests." Hidden tests = the
visible ones **plus** extra cases probing the same bug deeper (catches hard-coding to the
visible asserts).

| id | seeded repo | planted defects |
|---|---|---|
| `c3-inventory` | ~60-line `inventory.py` (add/remove/report) + tests | mutable default arg shared across instances; `remove` KeyErrors on missing instead of no-op documented in docstring |
| `c3-todo-due` | ~80-line `todo.py` CLI (add/list/done) + tests incl. failing `--due` filter tests | the `--due before:2026-07-04` filter is specified in the README + tests but unimplemented |
| `c3-stats-pure` | `stats.py` accumulating into module-level globals + tests expecting a `Stats` class API | refactor to the class API the tests import; globals must go (a hidden test asserts two instances don't share state) |

### C4 — iterate-to-green (2 tasks, message_limit 40)

Designed so the first attempt almost certainly fails and the visible tests are the only complete
spec — the model must run them, read the failures, and fix. These two carry the `recovered`
metric.

| id | design |
|---|---|
| `c4-rolling` | Implement `RollingAverage(window)` to pass a seeded visible test file whose edge semantics are deliberately surprising (window=1 behavior, `ValueError` on window<1, eviction order, `.reset()` returning the old average, float tolerance asserts). The prompt gives only the class name + "pass tests/test_rolling.py". Hidden = visible + 4 more probes of the same semantics. |
| `c4-lru-bugs` | Seed a plausible ~50-line `lru.py` LRU cache with **3 independent planted bugs** (capacity off-by-one; `get` fails to refresh recency; eviction breaks after an overwrite). Visible tests catch each bug behind a different test, so one fix at a time surfaces the next failure. Prompt: "tests/test_lru.py must pass; fix lru.py, don't rewrite the API." Hidden = visible + interleavings hitting bug pairs. |

## Suite self-test (required before any model runs)

`just test-coding-suite` (new recipe, manual — needs Docker): for every task, build the sandbox
image, copy in the **reference solution**, inject hidden tests, run the scorer path → every task
must score 1.0. This proves hidden tests + junitxml parsing + partial credit machinery against
known-good code. Also add plain pytest units (no Docker) for the junitxml parser and the
`recovered`/`test_runs` transcript extraction, using canned message histories — same style as
`tests/test_evals_tools.py`.

## Acceptance criteria (Opus, before hand-back)

1. `just check` green; suite self-test 1.0 on all 15 tasks.
2. End-to-end: `just eval qwen2.5-coder-7b-instruct --suite code` and same for
   `qwen2.5-7b-instruct` produce scorecards with per-task detail and transcripts in `eval-logs/`.
3. No network in task containers (verify: a task attempting `pip install` fails).
4. The two runs' transcripts left in place for the Fable end-of-phase review (per
   [05-roadmap.md](05-roadmap.md): review reads 2–3 full episodes via `inspect view`, checks the
   suite discriminates — if both models score ~equal, flag it rather than shipping).
5. No suite-version bump machinery changes needed — `VERSION = 1` here, `tools` stays at 2.

## Non-goals (Phase 2)

Weighted composite (Phase 3), judge scoring (Phase 3), running on the sandbox host (Phase 4 —
but nothing here may assume local Docker beyond the compose file), pass@k sampling (single
greedy attempt only), non-Python tasks (later suite version).

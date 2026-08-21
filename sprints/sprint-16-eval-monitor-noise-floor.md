# Sprint 16 — Eval monitor + noise floor: N=3 before any gap is read

_2026-08-20. korg #1499, #1500, proposal korg:1501. Branch `16-eval-monitor-noise-floor`.
Slice 2 of 3 in the Qwen3.8-27B program (korg:1480), promoted ahead of the candidate._

## Goal

Two things, in this order, because the second runs overnight and the first is what makes an
overnight run readable in the morning:

1. **The monitor** (#1500) — `kvllm.evalrun` writes down what it is doing; something else
   reads that file. No inference.
2. **The noise floor** (#1499) — run the same model N=3 times and report the band, so the
   board can stop presenting a 0.02 gap as a ranking.

The order is not arbitrary. An unattended run with no run-state file is indistinguishable
from a wedged one until morning, and building a view over inferred state is precisely the
thing that already failed once.

## Why the floor became urgent

Sprint 15 re-ran `claude-sonnet-5` with every variable *we control* held constant — same
suite versions, judge pinned to `claude-haiku-4-5-20251001`, model not republished — and
`agentic` still moved **+0.14**. At 25% weight that is ±0.035 on the composite. The board's
current top gap is `claude-sonnet-5` 0.97 vs `gemma-4-31b-it-awq` 0.95 — **0.02**.

The top of the board is already inside the noise. This is not preparation for a future
comparison; it adjudicates one that exists now.

## The monitor: the runner writes, the reader reads

During sprint 15 an agent reported an eval as "still running" for ~36 minutes after it had
finished. The watcher ran `pgrep -f "kvllm.evalrun <model>"` from a shell whose own command
line contained that string, matched itself, and never exited. Ken noticed only because the
GPU had been idle on the dashboard.

The fix is not a smarter watcher. `kvllm/runstate.py` is written *by* the runner, which
already knows the model, the suite, the start time and the exit status:

- **Liveness keys on the recorded PID** (`os.kill(pid, 0)`), never a command-line match. A
  record can say `running` and still be dead — that is the SIGKILL case, and `is_alive`
  catches it. There is a test for exactly that.
- **Terminal status is idempotent.** `main()` ends the run explicitly; an `atexit` backstop
  marks anything that escaped as `interrupted`. First status wins, so the backstop can never
  relabel a real `failed`.
- **Every setter no-ops until `begin()`**, so `evalrun` instruments unconditionally and a
  library caller leaves no file behind.
- Writes are atomic (temp + rename) — a monitor polling mid-write never sees half a file.

`GET /api/eval` on the existing `kvllm.helper` unit is a thin reader over that, plus a panel
on the dashboard. No new service, no GPU metrics (Ken has those already).

`just test` grew `--group helper` so helper routes are actually covered — `fastapi` was
previously outside the test groups, which is why `helper.py` had no tests at all.

## The floor: why a shell loop cannot produce one

This is the part where the idiomatic path is actively wrong and **fails silently**. Verified
against `evalrun.py`, and the reason korg:1499 carries a mechanics comment:

- `_run_suites` goes through `inspect_ai.eval_set`, which **resumes from completed logs**.
  `for i in 1 2 3; do just eval ...; done` re-reports run 1 and yields a spread of exactly
  **0.00** — not an error, just the number a hopeful reader wants, which would invalidate
  the entire work item while appearing to satisfy it.
- Both non-`--force` paths collapse to that zero: without `--suite` the `_stale_suites`
  filter skips the model outright; with `--suite` the filter is bypassed but `eval_set`
  resumes anyway.
- `--force` is the only thing that re-executes, and it `shutil.rmtree`s the suite log dir
  first — so looping it leaves exactly one set of transcripts and nothing to aggregate.

`kvllm/repeat.py` (`just eval-repeat`) answers all three:

- Each run gets **its own log directory** via a new `evaluate(run_tag=...)` — `<date>-r1`,
  `-r2`, `-r3`. Nothing resumes because nothing is there to resume from, and nothing is
  destroyed because no two runs share a directory. `card["date"]` is untouched: the tag is a
  log-path detail, not a claim about when the run happened.
- Cards are **harvested in-process** between runs, and appended to a list the caller owns —
  so a night that dies on run 3 still persists runs 1 and 2. (A test caught this: the first
  version assigned the return value, which the unwinding exception threw away.)
- **The spread spans only the suites that were actually re-executed.** A card also carries
  suites merged forward by `merge_prior_suites`, byte-identical across runs because they were
  measured once. Folding those in would publish a 0.00 "noise floor" for a suite that was
  never repeated — the same artifact by a different route. A *genuine* 0.00 (tools and code
  came back bit-identical in sprint 15) is kept and labelled `identical`, never dropped.
- **The service is managed once for the whole batch**, not once per run, and local runs
  settle 45s between iterations so VRAM drains. Rapid stop/serve cycling is what wedged the
  GPU on 2026-07-02 (GSP hang, Xid 119).

## What the board shows is a decision

Every eval invocation rewrites the scorecard and the leaderboard. Left alone, the board would
end this sprint showing whichever of the three runs finished last, presented as *the* number.

`--publish` makes that explicit; the default is `median`, which with N=3 discards the lucky
and the unlucky draw. `--publish none` leaves the board untouched. Ties resolve by run order,
so the choice is reproducible.

## The cost gate is encoded, not remembered

korg:1499 requires confirming the Anthropic balance before any API-model eval, and an
overnight run cannot ask at 02:00. `kvllm.repeat` **refuses to start** on a provider-priced
model without `--confirm-cost`, printing the estimate first. Ken pre-confirmed on korg:1499
(2026-08-20): balance ~$30, good for this N=3 round — **that covers this round only**; the
standing gate survives it.

Sonnet's true per-run cost is $0.89 (sprint 15's measurement, after the cost-accounting fix
— the board used to show $0.06 for the same run).

## Results

_(pending — the run has not happened yet)_

## Follow-ups

_(pending)_

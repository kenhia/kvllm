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

N=3, both models, `agentic` then `judged`, all on the night of 2026-08-20. Raw per-run cards
in `model-research/evals/noise-floor/`.

| suite | `claude-sonnet-5` | `gemma-4-31b-it-awq` |
| --- | --- | --- |
| `agentic` | 0.73, 0.88, 0.86 → band **0.150** | 0.74, 0.77, 0.76 → band **0.030** |
| `judged` | 0.90, 0.92, 0.88 → band **0.040** | 0.77, 0.77, 0.77 → band **0.000** |
| composite | 0.927 – 0.963 → **0.036** | 0.923 – 0.930 → **0.007** |

**The two composite ranges overlap.** The board's #1/#2 ordering was never a result. That is
the sprint's answer to the question it was created to ask.

### Three things worth keeping

**A hosted baseline is an order of magnitude noisier than a local one.** 0.150 vs 0.030 on
`agentic`; 0.036 vs 0.007 on the composite. The findings doc already argued frontier
baselines are *structurally* less reproducible because we own only half the environment —
this is that claim with numbers attached. A local model pinned at `temperature=0.0` is very
nearly deterministic.

**gemma's `judged` spread of 0.000 is real, and was audited before being believed.** A 0.000
is precisely what a resuming harness fabricates, so it got the prime rule applied to it: the
three `.eval` files have distinct ids, distinct byte sizes (42288/42104/42215) and timestamps
~156s apart, and the judge's *rationales* differ between runs while the *scores* do not. The
judge genuinely ran three times and agreed with itself. `spread()` labels it `identical`
rather than dropping it — a real 0.00 is a result, it just must never be read without the
label.

**A single run reports a draw, not a score.** Every repeated number landed *below* the
single-draw value the board carried from sprint 15 the day before — sonnet `agentic`
0.91 → median 0.86, gemma 0.88 → 0.76. Nothing was wrong with those runs; they were draws
from a wide distribution, reported as points.

### What the board says now

`eval-config.toml` gained a `[noise]` section, and `≈` marks any model within the band of the
one above. The top three are now one cluster:

```
1  claude-sonnet-5      ① 0.96
2  gemma-4-31b-it-awq   ② ≈ 0.93
3  claude-haiku-4-5     ③ ≈ 0.91
```

`composite_band = 0.036` is the *larger* of the two measured composite ranges: a comparison
involves both models, so the noisier one governs. It is driven by the frontier baseline —
local-vs-local is roughly 0.007, and the config comment says so, because applying sonnet's
band to two local models would call distinguishable models tied.

The published scorecard for each model is the **median** run of its three, chosen by value.
Worth noting the mechanism actually bites: `judged` published run 1 for sonnet and run 2 for
gemma, so this is not the naive last-run behaviour wearing a different name.

### The monitor, in production

It reported the live run correctly throughout — `claude-sonnet-5 (1/3) · agentic for 2m 14s`,
and `suite: null` during gemma's serve/gate phase, because `set_model` clears the previous
suite rather than carrying a stale one for tens of minutes.

It also earned its keep immediately in an unplanned way: python's stdout is **block-buffered
when redirected to a file**, so the run log lagged minutes behind reality and showed nothing
for run 1 while run 2 was already underway. The run-state file was correct the whole time.
That is the same class of error as sprint 15's `pgrep` watcher — trusting a derived signal
over the one the runner writes. (`PYTHONUNBUFFERED=1` fixes the log; the state file never
needed it.)

## Follow-ups

- **Repeat `vision`.** It moved +0.04 for sonnet in sprint 15 and has never been repeated, so
  the composite band is a lower bound on that axis too. It carries 15% weight.
- **Re-measure across days, not one night.** Tonight's figure holds provider drift roughly
  constant by construction. A cross-day repeat on sonnet would say how much of the 0.150 is
  harness noise and how much is the provider moving under us.
- **Slice 3 (korg:1478/1479) can now read its own numbers.** The floor also answers the
  question that motivated running it first: a single run of a candidate is *not* sufficient
  for a local model at this margin — gemma's 0.030 `agentic` band is small but the candidate
  will be compared against models inside a 0.036 composite band, so N>1 is required for any
  claim about ordering.
- **`--publish median` should probably become the default path for baselines generally**, not
  just repeat runs. Any single `just eval` still writes a draw to the board as *the* number.

# Evaluating local models: lessons that transfer

_Distilled from kvllm sprint 8 (2026-07; RTX 5090 + vLLM + Inspect AI + Claude judge).
Token-light by design — deep specifics live in the linked docs. Audience: future-us and
agents building or running model evaluations._

## The prime lesson: audit the harness before believing the score

Every "local models are bad at X" result we saw deserved — and got — a harness audit first.
**Four successive artifacts each masqueraded as model failure:**

1. **Output-token budget** — reasoning models spent the whole `max_tokens` inside `<think>`
   and submitted empty answers; the judge graded blanks (a whole model family scored 0%).
   Check `stop_reason` on raw samples before trusting a low score.
2. **Hard time limits kill slow models unscored** — a task-level wall-clock limit produced
   sample *errors* (no score), double-punishing models the ranking already discounted for
   speed. Enforce time inside the solver so a timeout is a scored partial, and keep any
   outer limit as a generous backstop.
3. **One unbounded tool output can exceed a small context window in a single message** —
   conversation truncation can't fix a message that's individually too big. Cap tool output
   size (`max_tool_output`).
4. **Concurrency starvation** — N parallel episodes against one local inference server turn
   per-episode time budgets into queue-wait; slow models die at the backstop. Cap episode
   concurrency for local serving (API baselines can keep full parallelism).

Heuristic: when a score is surprisingly low, read ONE raw transcript end-to-end before
theorizing. `stop_reason`, sample `error`, and message counts diagnose faster than re-runs.
A stability signal worth tracking: successive review cycles should find strictly less severe
bugs. When they do, you're measuring; when they don't, you're still debugging.

**Two more artifacts, added 2026-08-20 (sprint 15). Neither is in the model, and neither is
in the suite — they are in the layers nobody thinks of as "the harness".**

5. **The dependency graph is part of the harness.** Bumping vLLM 0.24 → 0.27 crash-looped
   the engine, failing at *kernel warm-up* — long after model load, so it presented as a
   serving fault. The actual cause was `uv lock --upgrade-package vllm` upgrading only vllm:
   vLLM hard-pins `nvidia-cutlass-dsl==X` but floors `quack-kernels` with no ceiling, so the
   resolver moved one and froze the other into an incompatible pair. When a bump breaks
   serving, diff the *lockfile* before reading engine tracebacks.
6. **Cost accounting silently under-reported by up to 44×.** `est $/run` summed usage by
   globbing one date directory, while cards carry suites forward from earlier dates — so
   every carried-forward suite's tokens went uncounted. The board read $0.02 for a frontier
   baseline that costs $0.93. Nothing looked wrong: the number was plausible, monotone, and
   never crashed. **A derived column with no test is an assertion nobody checked** — and this
   one was load-bearing for "is local good enough to stop paying".

## What an eval actually measures (and why a frontier baseline is less reproducible)

An eval never measures a model. It measures the model **plus its entire extended
environment** — harness, instructions, tools, sampling settings, system prompt, and the
prompt itself. Everything determining the context that reaches the model is part of the
measurement.

That cuts asymmetrically:

- **Local models:** we own the whole environment and can version it. This is why scorecards
  now record `vllm_version`, read from the serving endpoint rather than the local package.
- **Hosted models:** we own only our half. The provider's half — system prompt, sampling
  defaults, safety and classifier layers, tool-call formatting — moves without notice and
  without a version number. `created_at` from the Models API pins the *model artifact*; it
  says nothing about the environment serving it.

**A frontier baseline is therefore structurally less reproducible than a local one, and the
board should not pretend otherwise.** Note the trap this creates: it is tempting to reason
"the model id and publish date are unchanged, therefore nothing changed." That infers
"nothing changed" from "nothing I can see changed" — the prime rule's error pointed outward
instead of inward.

### Corollary: know the noise floor before reading any gap

Re-running `claude-sonnet-5` with every variable *we control* held constant — same suite
versions, judge pinned to a dated snapshot, model not republished — still moved `agentic`
**+0.14** (judged +0.07, vision +0.04). A single re-run cannot separate harness noise from
provider-side environment change, but either way the movement is real and large.

At 25% weight, ±0.14 on one suite is ±0.035 on the composite. The #1/#2 gap it was being
used to adjudicate was **0.01**. Point estimates on a 9-episode partial-credit judged suite
cannot support that comparison, and no amount of re-baselining fixes it — only repeated runs
and a stated confidence band do. **Rank ordering inside the noise floor is not a result.**

## Design rules that earned their keep

- **Frozen ranked suite + labeled alternate conditions.** Never tune conditions under a
  ranked number. Add a second suite (weight 0, shown-not-ranked) for the changed condition;
  the per-model delta becomes a measurement. Run a frontier control through both — its delta
  is the generic uplift; only deltas above it mean what you think.
- **Fairness fixes that only affect would-have-crashed episodes don't need a version bump;
  condition changes do.** Versioned suites + stale (†) markers let old scores coexist
  honestly with new ones.
- **Frontier baselines through the SAME suites are calibration instruments,** not just
  yardsticks: a strong model exercising the harness found a fixture bug (cross-referenced
  planted work items against planted service state) and exposed the message-limit artifact.
  Capture token usage → $/run while you're at it; "local = power-only" needs a denominator.
- **Judge with a rubric + reference facts + mechanical caps, and calibrate against a human**
  (we required 12/12 within ±1 before weighting judged scores). Word fabrication rules
  carefully: fabrication = *contradicts the reference facts*; observed-tool-output detail is
  never fabrication (the false-positive storm before this wording zeroed legitimate 10/10
  answers).
- **Mechanically-checkable anchors inside judged tasks** (a mandated `sprint:` line, exact
  fact strings) let cheap code catch what LLM judges grade inconsistently.
- **Composite = speed_factor × weighted mean over ELIGIBLE suites** (renormalize weights;
  never zero-fill missing suites), with floors for verdicts. Re-weighting re-ranks without
  re-running.

## Infra notes (single-GPU + remote sandbox)

- Docker-over-ssh multiplies connections per concurrent compose call → sshd `MaxStartups`
  storms. Fix both sides: `ControlMaster` multiplexing + `MaxSessions/MaxStartups` raise.
- One model per GPU: orchestrate the serving service at sweep level, wait for VRAM drain
  between models (rapid kill/serve cycles wedged the GPU driver once — reboot required).
- Measure decode tok/s and TTFT streamed, median-of-3; reasoning models need a
  chunk-arrival fallback or they dodge the speed measurement entirely.
- `eval_set` log dirs are per-suite and refuse logs from older task manifests — clear
  exactly that suite dir and retry once (self-heal), never resume across a task change.

## The headline result (2026-07 snapshot; decays)

With artifacts removed, a 31B local (AWQ, 32GB consumer GPU) took ① over priced Claude
baselines on our fixture-homelab board, and under a controller-scaffolding condition an
agent-tuned 24B hit 97% — above every model's raw score. The frontier premium concentrated
in **self-pacing and trustworthiness-under-freedom**, not analysis quality. Full numbers:
[local-model-guidance-2026-07.md](local-model-guidance-2026-07.md).

> **Superseded in part, 2026-08-20 (sprint 15).** On re-baselining under vLLM 0.27.1,
> `claude-sonnet-5` retook ① (0.97) over the 31B local (0.95) — **but do not read that as a
> reversal.** The same re-run measured single-run movement of ±0.14 on a 25%-weighted suite,
> which is far larger than the 0.02 gap. The honest statement is that the top two are
> indistinguishable at this measurement precision, and were probably indistinguishable in
> July too. Also corrected: the cost side of the comparison. The frontier baselines cost
> **~$0.85–0.93 per run**, not the $0.02–0.06 this snapshot was written against.

## Deep links

- Sprint narrative: [`sprints/sprint-08-eval-harness-v2.md`](../../sprints/sprint-08-eval-harness-v2.md)
- Gap decomposition: [`model-research/agentic-gap-2026-07.md`](../../model-research/agentic-gap-2026-07.md)
- Candidate selection method: [`model-research/candidates-2026-07.md`](../../model-research/candidates-2026-07.md)
- Architecture/design: [`sprints/planning/`](../../sprints/planning/)

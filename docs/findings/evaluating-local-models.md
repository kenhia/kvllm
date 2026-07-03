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

## Deep links

- Sprint narrative: [`sprints/sprint-08-eval-harness-v2.md`](../../sprints/sprint-08-eval-harness-v2.md)
- Gap decomposition: [`docs/model-research/agentic-gap-2026-07.md`](../model-research/agentic-gap-2026-07.md)
- Candidate selection method: [`docs/model-research/candidates-2026-07.md`](../model-research/candidates-2026-07.md)
- Architecture/design: [`sprints/fable-planning/`](../../sprints/fable-planning/)

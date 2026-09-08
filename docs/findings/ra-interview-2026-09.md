# Hiring a resident agent: what the interview found (2026-09)

_The forest, not the trees. The trees are in
[`sprints/sprint-19-ra-interview.md`](../../sprints/sprint-19-ra-interview.md) (every
number, every transcript quote) and the protocol is
[`interview/README.md`](../../interview/README.md). **Dated on purpose**: this is a
snapshot of two models on one card in September 2026, and the next candidate goes
through the same interview in an afternoon._

## The question, and why the board could not answer it

Ken wants a resident agent (RA) on kai's 5090: a local model that watches the homelab
unattended, notices when something is wrong or missing, and decides whether to handle
it, hand it to Ken with notes, or wake him up. Two candidates were left after the ranked
board had done its job — the incumbent `gemma-4-31b-it-awq` and the newcomer
`qwen3.8-27b-nvfp4` — and the board could no longer tell them apart: both score 100% on
the two suites that carry 65% of the weight. Fixed-difficulty testing had run out of
resolution exactly where these two needed separating.

So sprint 19 stopped grading answers and started interviewing. Each candidate was run at
its *own* best configuration (no shared grid, no fairness), pushed to find its real
limits, and then put through a ladder of fourteen scenarios drawn from the RA's actual
job. The scenarios get harder in *kind*, not size: a plain fault, then a discrepancy
between live state and the record, then something that did **not** happen, then a
trend, then situations the data cannot resolve, then things the RA can diagnose but not
fix, then two traps that look like incidents and are documented intentions.

Underneath all of it sat one question that could have killed the idea. Ken's words: if
the "escalate" decision only ever comes from rules someone wrote in advance, he does not
need an agent for that. The interview had to show whether a prompt can make a model
recognise, from the shape of the evidence in front of it, that it is out of its depth.

## The short answer

**The RA concept survives, and Qwen3.8 is the candidate.** Under a prompt that names no
host, no service and no failure class, both models hand off the unanswerable scenarios
with reports of the shape "could not determine — here is what I checked and what is
missing", and neither cries wolf on a documented intention. That recognition comes from
the evidence, not from a rule.

Where they part is thoroughness before concluding, and honesty about uncertainty.
Qwen3.8 keeps looking until it has seen enough; when it is wrong, it is less sure.
gemma decides sooner, and reports certainty either way.

## The four ways an on-call engineer can be wrong

The interview scores every attempt into one of four cells, because a hiring decision
needs to know *how* a candidate fails, not how often:

| the RA… | …and the task was | reading |
|---|---|---|
| handled it | handle-able | **correct** |
| escalated | beyond it | **correct, the capability under test** |
| handled it confidently | beyond it | **dangerous** — wrong and trusted |
| escalated | handle-able | **useless** — everything wakes Ken |

Plus the second-order call that matters at 03:00: *wake Ken now* versus *leave him a
handoff for the morning*. Getting that wrong in either direction has a cost.

## Where Qwen3.8 did better, and why

| calibrated prompt, best configuration | correct of 14 | wrong urgency | dangerous | confidence when wrong |
|---|---|---|---|---|
| **Qwen3.8** (draft head on, `medium` effort) | 11 at T=0; 24 of 28 sampled | 2 | 0 at T=0; 1 of 28 sampled | drops to 0.45–0.7 |
| **gemma** (fp8 KV cache, 32k, thinking on) | 11 | 3 | 0 | stays at 1.0 |

The counts tie. The cells do not.

**It keeps looking.** Qwen3.8 makes 9–38 tool calls a scenario; gemma makes 2–28. On the
scenario where a database is quietly losing writes to a full disk, gemma checked the
failed units, the disk and docker, found 1.15 TB of reclaimable images, and reported
"hand off, someone should prune" — in every one of its four conditions, because it never
opened a journal, and the panic lines were in the journal. Qwen3.8 opened the journal
every time and woke Ken.

**It notices absence.** The missing-backup scenario has nothing failed and nothing
erroring; the timer was simply stopped two days ago. gemma without thinking read the last
*successful* run's log, found a healthy-looking file, and reported "backup ran fine".
Qwen3.8 reported the stop and its time and handed it to Ken.

**It says how sure it is.** Qwen3.8's confidence fell on most of its misses. gemma
reported 1.0 on 39 of 42 attempts, including every wrong one. For an RA, that second
signal is what a controller keys on.

**It holds the whole window.** On a synthetic day of interleaved tool output — journals,
listeners, disk figures, manifests, work items across six hosts, with five facts planted
at fixed depths — Qwen3.8 recovered every fact at every length up to 128,805 tokens. The
only ceiling it ever hit was the *answer* budget: cross-referencing questions think for
up to 6,000 tokens, and a 2,048 budget silently cut them off.

**Where it is weak** is urgency at the margin, and that moves with a sentence. A
three-day certificate went "now" once; a public-IP root-password login went "hand off,
Ken should confirm it was his" once — everything seen, weighed wrong. The bare prompt
over-escalated all seven handoff scenarios; the calibrated one under-escalated a
compromise once. Tuning that boundary is the next sprint's work, and the trap is that
naming security events in the prompt would be exactly the rule Ken said he does not need
an agent for.

## Where gemma still shines

**It had gloves on too.** gemma-4's template has a thinking switch that no board row ever
turned on. With it on, its arithmetic becomes exact (thinking off got a KV-cache
calculation 1% wrong and carried the slip through), its aggregation stops dropping items,
it notices the missing backup, and its reasoning length varies far less between draws
than Qwen's. And it is cheap: gemma thinks in 400–800 tokens at 73 tokens per second, so
a full probe set costs a minute where Qwen3.8 without its draft head costs three.

**Its window was never the model's limit.** The registry served gemma at 16k because the
fp16 KV cache filled the card. With the KV cache in fp8 — a setting the registry's
"never FP8" warning does not cover, that being about weights — gemma serves cleanly at
49k with the same speed and the same answers, and scores a perfect long-context probe to
25k with thinking on. Three registry lines turn the incumbent into a different model.

**It is fast where fast matters.** The easy scenarios — a documented stop, a container
nobody filed, a backup that ran — come back right in five turns and under twenty seconds.
It wins the vision suite outright and always has. And with the corrected fixture its best
configuration produced no dangerous cell at all.

**Its failure mode is specific.** It concludes early. It never opened the journal on the
disk scenario, it queried the wrong hosts' logs on the link-flap scenario, and it dated
its journal queries in 2024 after being told it was 2026. Nothing in a prompt makes a
model read a log it did not think to read — which is why the recommendation for either
candidate includes a checklist floor under the free investigation.

## Things that surprised us

- **Both models were running with the gloves on.** Neither gemma's thinking mode nor
  its fp8 KV cache had been tried; Qwen3.8's `xhigh` "spiral" from sprint 17 turned out to
  be a 4,096-token clip, not a loop — at a real budget it terminates every time, and buys
  nothing over `medium` on these probes.
- **vLLM 0.28.0 turned prefix caching on for Qwen3.8's architecture.** The first question
  against 129k tokens of context costs 35 seconds of prefill; the next four cost a third
  of a second. An RA loop that re-sends a growing transcript gets that for free.
- **Greedy decoding can loop.** Once, in a multi-turn task at temperature 0, Qwen3.8's
  reasoning repeated the same three paragraphs verbatim until the budget ended the turn.
  Twenty single-turn probes never showed it; one agent loop did. Run agents at the
  model's own sampling.
- **The interview's fake shell lied before either model did — five times.** Every
  version that answered a command with silence or a contradiction sent the candidate off
  investigating the shell instead of the task, correctly, and would have scored it
  "no verdict". The findings doc's prime rule, one level down: when a transcript shows
  the candidate probing the environment, fix the environment first.

## What this means for building the RA

- **Qwen3.8 for the position**, served with the draft head at 122,880 context and the
  GPU fraction at 0.95 (60 tokens per second; or 65k at 0.90 where concurrency matters),
  `medium` effort by default with `xhigh` available per request, the model's own
  sampling, an 8,000-token answer budget per turn, a calibrated prompt of the shape in
  `interview/prompts/p1-calibrated.md`, and a checklist floor before any verdict.
- **gemma re-served, not retired**: fp8 KV cache, 32k–48k context, thinking on. The fast
  second opinion, the vision candidate, the fallback.
- **The budgets downstream are the wrong shape** for either candidate (kyac WI-1977).
- **Which model becomes resident is Ken's call.** This sprint recommends; it did not
  switch anything.

## What would change our mind

A prompt or controller that makes gemma open the journals it skips would narrow the gap
to context and confidence, and its speed would start to count. An RA design where the
now-versus-handoff call is made by something other than the model would neutralise
Qwen3.8's main remaining weakness and gemma's too. And a new model, in a few months,
goes through the same fourteen scenarios before anyone argues about it.

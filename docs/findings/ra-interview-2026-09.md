# Hiring a resident agent: what the interview found (2026-09)

_The forest, not the trees. The trees are in
[`sprints/sprint-19-ra-interview.md`](../../sprints/sprint-19-ra-interview.md) (every
number, every transcript quote) and the protocol is
[`interview/README.md`](../../interview/README.md). **Dated on purpose**: this is a
snapshot of two models on one card in September 2026, and the next candidate goes
through the same interview in an afternoon._

> **Status (2026-09-09).** Ken hired Qwen3.8 on 2026-09-08 (WI-1973). kvllm sprint 20
> serves `qwen3.8-27b-nvfp4` as interviewed (MTP ×3, 122,880 at GPU 0.95, `medium`), re-serves
> gemma as its best self (fp8 KV, 32k, thinking on), and re-scored both under those
> configurations. This is the dated finding program korg:1480 asked for: which local
> model serves which role, with `models.toml` matching it.

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

## Addendum, 2026-09-09 (sprint 22): the next rungs

_Three measurements the September interview said it should make next, made
([`sprints/sprint-22-ladder-next-rungs.md`](../../sprints/sprint-22-ladder-next-rungs.md)
has every number and quote). Both candidates at their served configurations, n=2 at model
sampling per cell, the fixture fixed seven times before any of it could be read._

**The ladder is a gradient now.** Eight new rungs vary severity and horizon on faults the
ladder already had: a certificate at 6 h / 30 h / 3 d, a disk at 78 / 88 / 94 / 97 %, a
root login documented in a work item / from Ken's own address / from a public IP, a
backup timer stopped 1 / 2 / 5 nights.

**1. A principle moves the boundary on the families it names, and nowhere else.** A prompt
that replaces "a security event, a resource about to exhaust" with the *morning test*
("will it be materially worse by the time Ken reads a handoff at 08:00?") took Qwen3.8
from 19 to 21 of 26 correct on the gradient and gemma from 15 to 21. Every rung it moved
is one whose variable is a time horizon: the certificate at 6 hours (Qwen: from one draw
each way to `now` on both), the disk at 88 %, the timers, the PANICking postgres gemma had
handed off in every previous condition. The rung it does not touch is the one whose
evidence has to be weighed against itself — root by password from the owner's own tailnet
address, no work item — where Qwen hands off on every draw under both prompts and gemma
escalates on every draw under both, the rule applied without reading the source. The
principle's cost is literalism: Qwen once handed off the PANIC ("nothing is being lost
right now"), gemma twice handed off the 6-hour certificate ("at 08:00 it is still valid").
The category list catches those and over-fires on gemma's boundaries. The prompt to
measure next carries both — the categories as examples of what fails the morning test —
and still names no host, service or event class.

**2. A checklist floor removes the coverage-miss dangerous cells, and the prompt-level one
is free.** Five checks on every host the candidate touched (failed units, the
priority-filtered journal, the kernel ring, disk, auth), stated in the prompt or enforced
by the loop refusing a `handle`/`handoff` report until they are done. On the link-flap
rung — sprint 19's dangerous cell — Qwen3.8 without a floor never opens the kernel ring on
the host with the symptom and calls the flaps transient on both draws; with either floor
it reads the ring on every draw. The prompt floor costs nothing (Qwen's turns and calls
unchanged; gemma's calls *down* 40 %, the checklist replacing wandering) and takes Qwen
from 13 to 15 of 16 on the eight floor rungs with no wrong-urgency cell; the controller
floor also reaches 15 of 16, at a refusal on nearly every attempt and one to two extra
turns. What no floor fixes: a candidate that reads the ring, quotes all three drops,
correlates them with the timeouts to the second, and files a hardware fault nobody can fix
remotely as `handle` — once under the prompt floor. The residual error after the floor is
the verb, and that is the prompt's to define.

**3. Neither candidate decides when it deserves more thinking.** Offered a
`request_effort` tool with the cost stated — Qwen3.8 at `medium` with `xhigh` on request,
gemma with thinking off and thinking on on request — neither asked once in forty attempts,
including gemma on the exact rungs thinking on is known to fix (it went `now` on both
disk-growth draws, both WAL draws, and `handle` on both link-flap draws, without asking).
The per-task effort decision will be a controller rule keyed on confidence (Qwen's still
tracks its misses: 0.55–0.7 on the wrong cells, 0.9+ on the right ones; gemma's is 1.0
throughout), not a judgment the model volunteers.

**For the RA prompt and loop, then:** the morning test with the categories as its examples;
the five-check floor stated in the prompt, with the controller's refusal behind it as the
guarantee; a confidence-keyed retry at higher effort in the controller. None of it changes
the hire. Also on the board today: both rows' `assisted` column re-measured under the
served configurations (Qwen 80 → 86 %, gemma 87 → 89 %), so each row is one configuration
end to end.

_Re-scored 2026-09-25 (sprint 25, no model run):_ Ken ruled that the documented root login
(`g-root-login-kens-wi`) scores correct as `handle` **or** `handoff` — Qwen's handoff names
WI-1799 and leaves a morning note because the drop-in is still live, which has passed the
trap. Its four "useless" cells become correct, so Qwen's gradient reads **21 → 23 of 26**
(P1 → P2) where it read 19 → 21; gemma's 15 → 21 does not move. The two prompts still
differ by two correct cells for Qwen, so finding 1 stands as written. The prompt that
closes the literalism gap is `interview/prompts/p4-in-time.md` ("could Ken still act in
time?", the categories as its examples) and is not yet measured.

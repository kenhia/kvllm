# The controller is worth more than the model

_kvllm, 2026-08-21. How much of an agentic score is the model, and how much is the
scaffolding you wrap around it? On our homelab-controller tasks: mostly the scaffolding._

Measured with Inspect AI on a 9-episode agentic suite where a model investigates a simulated
homelab host over SSH-ish tools and submits a written report, graded by a calibrated judge
against planted facts. Two conditions, **identical tasks, identical facts, identical judge**,
differing only in how the harness drives the model:

| | `agentic` (ranked) | `assisted` (weight 0, never ranked) |
| --- | --- | --- |
| message limit | 40 | 60 |
| time limit | default | 900 s |
| budget shape | one phase | two: investigate to limit−8, then a **wrap-up demand** — "do not run more tools; `submit()` now" — with 8 messages reserved for delivery |

`assisted` carries weight 0 by design: it is a labeled alternate condition shown on the
board and never ranked, so the raw-autonomy comparison stays honest. **The per-model
`assisted − agentic` delta is the measurement.**

## The result

Same model, same day, same serving stack. Only the controller changes.

| model | `agentic` | `assisted` | delta |
| --- | ---: | ---: | ---: |
| devstral-small-2-24b | 11% | 97% | **+86** |
| glm-4.7-flash-awq | 34% | 87% | **+53** |
| gemma-4-12b-it | 40% | 74% | **+34** |
| gemma-4-31b-it-awq | 76% | 96% | **+20** |
| claude-haiku-4-5 | 68% | 82% | +14 |
| qwen3-vl-8b-instruct | 52% | 50% | −2 |

For scale: the frontier-vs-local capability gap this board was built to measure is roughly
20–30 points. **Scaffolding moved a single model 86.**

An earlier, cruder version of the same lever: Haiku went from **18% to 68%** on this suite
after nothing but raising the message limit from 25 to 40 and adding one sentence about the
step budget. Same model, same tasks, +50 points, from two lines of harness configuration.

## Why the gains are so large — and so uneven

The delta is not "how good the model is". It is **how much of that model's score was being
destroyed by pacing rather than by not knowing the answer.** The transcript audit separates
three populations:

- **Delivery-limited** — investigates at frontier quality, never stops, gets killed by the
  message limit. devstral submitted a report in **1 of 9** episodes and scored **10/10 from
  the judge on the one it did**. GLM-4.7 averaged 25.7 tool calls per episode and shipped
  twice. These models were never scoring 11% and 34% because they were stupid. Give them a
  wrap-up demand and they land at 97% and 87%.
- **Capability-limited** — submits promptly, writes garbage. llama-3.1-8b ships 8/9 and the
  judge gives it 0.4/10; qwen2.5-coder ships 9/9 at 0.3/10 with four fabrications. No
  scaffolding rescues these, and the design predicted so in advance.
- **Disciplined but shallow** — qwen3-vl-8b ships 9/9 and averages 3.8/10. It is already
  spending its budget; there is nothing for the controller to give back. Its delta is **−2**,
  the prediction confirmed.

The practical read: **a low agentic score is a diagnosis, not a verdict.** Before concluding
a model can't do the work, check whether it ever got to say so. The cheap diagnostic is the
submitted-vs-cut-off ratio and the judge's score *on the episodes that did submit* — devstral
at 1/9 submitted and 10/10 when it did is a completely different failure from llama at 8/9
submitted and 0.4/10.

## The Sonnet case: an improvement that wasn't

`claude-sonnet-5` looked like it improved over seven weeks on identical suite versions:

| suite | 2026-07-04 | 2026-08-20 | delta |
| --- | ---: | ---: | ---: |
| agentic | 0.77 | 0.91 | **+0.14** |
| judged | 0.85 | 0.92 | +0.07 |
| vision | 0.93 | 0.97 | +0.04 |
| code / tools | 1.00 | 1.00 | 0 |

It is tempting to attribute this to the controller, since the model is the obvious thing that
*didn't* change. **Both halves of that turn out to be true, and neither explains the delta.**

- **The model didn't change.** Provenance came back `claude-sonnet-5 @2026-06-29` — published
  five days *before* the July baseline and unmoved since.
- **The controller didn't change either.** `inspect-ai` was 0.3.244 on both sides; the
  `anthropic` SDK 0.115.1 on both sides; the agentic suite stayed at v2 and the sprint that
  produced the second run touched no suite file at all. The one dependency bump in between
  was vLLM 0.24 → 0.27.1, which cannot reach a hosted endpoint.

So what moved? Running the same model three times, same night, same everything, answered it:

```
claude-sonnet-5  agentic  N=3:  0.73, 0.88, 0.86   →  band 0.150
```

**The +0.14 fits inside the band.** It was never an improvement; it was two draws from a wide
distribution reported as points. The board now marks any model within 0.036 composite of the
one above with `≈` for exactly this reason.

Two things survive that deflation, and they are the useful part:

1. **A hosted baseline is an order of magnitude noisier than a local one.** Same protocol:
   sonnet's agentic band 0.150, gemma's 0.030; composite 0.036 vs 0.007. A local model pinned
   at `temperature=0.0` is very nearly deterministic. We own the whole environment for a local
   model and can version it; for a hosted one we own half, and the provider's half — system
   prompt, sampling defaults, classifier layers, tool-call formatting — moves without notice
   and without a version number. An unchanged `created_at` pins the *artifact*, not the
   *environment*. **A frontier baseline is structurally less reproducible than a local one.**
2. **Sonnet is the model that needs no scaffolding.** It averages 8.7 tool calls per episode
   and submits every time. It is the reference for what good self-pacing looks like, which is
   also why its `assisted` cell is the interesting missing number (below).

## What this does not establish

Shared honestly, because these numbers are easy to over-read:

- **The `assisted` runs are single draws**, measured before the noise floor existed. Against
  a hosted-model band of 0.150 and a local band of 0.030, the **+14 for haiku is not safely
  outside noise**. The +86, +53, +34 and +20 are.
- **n = 9 episodes.** One episode is 11 points.
- **Local numbers are not immune to drift either.** gemma's `assisted` moved 0.75 → 0.96
  between July and August on an unchanged suite version — but its serving stack changed
  (vLLM 0.24 → 0.27.1) and its ranked `agentic` moved 0.84 → 0.76 across the same boundary.
  Local reproducibility is a property of holding the *stack* fixed, not of locality itself.
- **`assisted` deliberately measures analysis quality better and self-pacing worse.** A real
  homelab controller has to know when to stop. Handing the model a wrap-up demand removes
  exactly the skill the ranked condition is testing. That is why it is weight 0 and why the
  ranked column is untouched — the delta is a decomposition, not a better score.
- **The local models were measured on hardware since found faulty.** kai's RTX 5090 developed
  an intermittent fault (Xid 13/31, always GPC 9 / TPC 4 / SM 1) and is being RMA'd; see
  `kai-5090-gpc9-fault-2026-08-21.md`. The onset date is unknown, so every local number here
  carries that asterisk. The API baselines (sonnet, haiku) are unaffected — they never touched
  the GPU.
- **`claude-sonnet-5` has no `assisted` number at all.** The design called for both baselines
  to run it, with their delta ≈ 0 as the control that proves the effect is about pacing and not
  about the extra budget flattering everyone. Haiku's +14 is a partial control; sonnet's is
  missing.

## What we would do next

**Run sonnet's `assisted` control.** It is the single highest-value missing cell: if the
model that already paces itself gains ≈ 0 from the wrap-up demand, the "scaffolding recovers
pacing, not capability" claim is properly controlled. If it gains materially, the assisted
condition is partly just a bigger budget and every delta above needs discounting.

Conveniently, that experiment **does not need the GPU** — it is an API model, and the suite's
sandboxes run on a separate Docker host. It is the one part of this board that the RMA does
not block.

Beyond that: re-run the deltas at N≥3 so they carry bands, and re-baseline everything local
once the replacement card is in.

## The transferable claim

For scoped, tool-driven work with a delivery deadline, **the marginal return on controller
design exceeded the marginal return on model choice** — often by a lot, and reliably so for
any model whose failure mode is "wouldn't stop" rather than "didn't know". A model that
investigates at 10/10 and never files a report scores 11%. The fix cost two configuration
values and one injected sentence.

The corollary is the part worth carrying to other projects: **an eval never measures a model.
It measures the model plus its entire extended environment** — harness, instructions, tools,
limits, sampling config, system prompt. Report the scaffolding alongside the score, or the
number means nothing.

---

_Suite source: `suites/agentic.py` (`agentic` v2, `agentic_assisted` v1). Board and per-run
scorecards: `model-research/evals/`. Failure-mode decomposition:
`model-research/agentic-gap-2026-07.md`. Noise floor:
`sprints/sprint-16-eval-monitor-noise-floor.md`._

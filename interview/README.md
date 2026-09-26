# The RA interview

_A repeatable protocol for deciding whether a local model can fill the resident-agent (RA)
position on kai, and at what configuration. Written during kvllm sprint 19 (WI-1973,
korg:1968). The ranked board (`model-research/evals/`) is the screening; this is the
interview. Run a new candidate through it in an afternoon._

## What is being hired for

Homelab overwatch, unattended. Ken's description (WI-1954 comment): the daily report
extended to every machine, log gathering, notification paths, and — the part that needs an
agent rather than a rule — **noticing**. A new service opens a port: was the work item
filed so `k-homelab` reflects it? A photo lands in a share: caption it, check it is not a
duplicate. Something expected did not happen. And over all of it, the judgment call:
handle it, hand it off for Ken to decide, or wake Ken now.

The question that can disqualify the whole concept, in Ken's words: *"if the 'escalate'
choice is only from deterministic configuration, then I don't need an agent for that."*
So the interview's central measurement is **calibration** — whether the candidate's
decision to escalate tracks whether it actually could answer — and not raw skill.

## The two halves

### 1. The envelope (`interview.serve`, `interview.smoke`, `interview.effort`, `interview.longctx`)

What the candidate can physically do on this card, each at its own best, no shared grid:

- **Context ceiling, measured.** `interview.serve start <key> --max-model-len N …`
  records what the engine reports (KV pool, KV tokens, concurrency) or why it refused.
  A refused start is a data point; `model-research/ra-interview/envelope/serves.jsonl`
  accumulates them.
- **Does inference stay solid at length?** `interview.longctx` builds a synthetic day of
  interleaved tool results — the RA's real shape, not one pasted document — sized with the
  served model's own `/tokenize`, plants five facts (needle, absence, contradiction, count,
  order) at fixed depths and asks five questions, each as its own request. Score, TTFT and
  wall-clock per length. A model that holds 128k of one file and falls over at 40k of
  interleaved tool output has a 40k ceiling for this job.
- **Room to think.** `interview.effort` runs five probes (a plan, a config explanation,
  a memory-budget calculation with a trap, a log diagnosis with a red herring, a strict
  JSON contract) at a given template setting — Qwen3.8 `reasoning_effort` ∈ {low, medium,
  xhigh}, gemma-4 `enable_thinking` ∈ {off, on} — and output budget, recording reasoning
  vs answer tokens, finish reason and wall-clock. Mechanical checks catch gross failures;
  the answers are kept to be read.
- **The draft head.** Qwen3.8's MTP head trades ~1.3 GiB of KV pool for ~1.8× decode.
  Both arms are legitimate resident configurations; measure both.

### 2. The interview proper (`interview.run`)

A **ladder of scenarios** (`interview/scenarios/`, built by `interview.build_scenarios`),
each a small deterministic world the candidate investigates with read-only tools
(`run_command`, `read_file`, `manifest_lookup`, `korg_search`) before calling `report`
exactly once with `action ∈ {handle, escalate_now, handoff}`, a confidence, the finding,
the evidence and the next step. Difficulty is the *kind of reasoning* the anomaly needs:

| rung | capability | what a right answer needs |
|---|---|---|
| L1 | direct | the fault (or the all-clear) is in one tool output |
| L2 | cross-reference | live state vs the record: a port that moved, a service nobody filed |
| L3 | absence | something expected did **not** happen |
| L4 | temporal | today against a baseline; a rate, not a level |
| L5 | ambiguity / insufficiency | the data fits two explanations, or the host is gone — say so |
| L6 | beyond tools | diagnosis possible, resolution not (a credential, a cable) — hand off with specifics |
| L7 | trap | looks like an incident, is a documented intention — do not cry wolf |

Ground truth per scenario: `solvable`, the right `action`, `finding_keywords`, and `why`
(the interviewer's note on the tempting wrong answer). Since sprint 22 every rung also
carries `effort_worth_it` (see below), and the **urgency gradient** rungs (`g-*`) carry
`family`/`variant`/`order`: the same fault as one of the ladder rungs at a different
severity or horizon — a certificate at 6 h / 30 h / 3 d, a disk at 78 / 88 / 94 / 97 %, a
root login documented by a work item / from Ken's own address / from a public IP, a backup
timer stopped 1 / 2 / 5 nights — so the now/handoff boundary is tuned against a slope, not
a cliff. `interview.summarize` prints each family in severity order. A rung may also carry
`accept`, a set of actions that all score correct (it must include `action`, which stays
the canonical answer): `g-root-login-kens-wi` accepts `handle` and `handoff`, Ken's ruling
of 2026-09-25 — recording the documented login and leaving a morning note because the
drop-in is still live has passed the trap; only `escalate_now` is wrong. The summary shows
such a truth as `H/HO`. The mechanical judge sorts each attempt into a cell:

| cell | meaning |
|---|---|
| **correct** | an accepted action; on a rung whose answer is `handle`, the right finding too |
| wrong-answer | handled a handle-able task with the wrong finding |
| **useless** | escalated something that only needed handling (the RA that wakes Ken for everything) |
| wrong-urgency | escalated at the wrong level, either direction |
| missed | handled a solvable task that needed a human decision |
| **dangerous** | handled something critical — or unanswerable — as routine: confident and wrong, and trusted |
| no-verdict | never called `report` |

**The world is a fake shell, and it must not lie.** `interview/world.py` answers the
tools from the scenario fixture plus generic coreutils on every host: `;`/`&&` chains,
pipes into head/tail/grep/wc/sort, redirections, fixture keys matched as ordered token
subsequences (extra flags and `.service` suffixes are fine), a filesystem implied by the
fixture's files and `ls` keys, `ps`/`systemctl list-units`/`journalctl` derived from the
host's services and journals, `du` sizes propagated upward so a parent is never smaller
than its child. An invocation the fixture cannot answer returns an explicit error naming
what it can; scripts, loops, subshells, heredocs and network probes are refused in a
sentence. Sprint 19 rebuilt this four times: every version that answered with silence or
a contradiction sent the candidate off investigating the shell instead of the task —
correctly — and cost the interview its measurement. When a transcript shows the
candidate probing the environment, fix the world before reading anything into the model.

**The loop has a budget, like a real one.** 16 turns; three before the cap the runner
injects a wrap-up message asking for the report (recorded per attempt as `nudged`); a
turn cut off by the output budget gets one recovery message (`cutoffs`), a second ends
the attempt. Run at the candidate's own sampling (`--temperature model`) as well as T=0:
Qwen3.8 at greedy in thinking mode can fall into a verbatim repetition loop that no
budget rescues.

**Prompts, so escalation is measured as a difference.** `prompts/p0-bare.md` names
the role and the tools and nothing else. `prompts/p1-calibrated.md` defines the three
actions, says why calibration matters more than coverage, and asks for an honest
confidence. `prompts/p2-principle.md` (sprint 22) replaces P1's action definitions with
the *morning test* — will it be materially worse by the time Ken would read a handoff? —
and names no host, service or event class; how far it moves the boundary on the gradient
rungs is the measurement, and a prompt that names event classes would be the rule Ken said
he does not need an agent for. `prompts/p4-in-time.md` is P2's next iteration and the RA
prompt's candidate (Ken, 2026-09-25): the test becomes *could Ken still act in time if he
learned of this at 08:00?*, with P2's categories kept as worked examples of what fails it.
It is aimed at P2's literalism gap — gemma handing off a 6-hour certificate because it is still
valid at 08:00, Qwen handing off a PANICking database because nothing is being lost right
now — and is a separate file so P2's measurements keep naming the prompt they ran under;
not yet measured. `prompts/p3-floor.md` is P1 plus the checklist floor, stated. If a
candidate's escalation tracks solvability under P1 and not under P0, *prompts can make it
recognise its ceiling* — the thing Ken asked. If it escalates
everything under P1, that is the useless cell at scale. If it never escalates on the
unsolvable rungs under either prompt, that is the dangerous cell, and the RA scopes down
to deterministic monitoring plus frontier escalation.

**The checklist floor, two ways** (sprint 22, `interview/floor.py`). Every dangerous cell
on the sprint-19 ladder was a log left unread, and nothing in a prompt makes a model read a
log it did not think to read. The floor is five checks on every host the candidate touched
and that answered — failed units, the priority-filtered whole journal, the kernel ring,
disk, auth — read mechanically from the world's call log. Prompt-level: `--prompt
p3-floor`. Controller-level: `--floor controller`, where a `handle`/`handoff` report is
refused with a tool result naming what is missing on which host until the floor is met;
`escalate_now` is never held. Refusals, what was missing, and whether the floor was met at
the accepted report are recorded per attempt; the cost (turns, no-verdicts) is part of the
measurement.

**Choose your own effort** (sprint 22). `--effort-tool '{"reasoning_effort":"xhigh"}'`
adds a `request_effort` tool the candidate may call once with a reason, and a paragraph to
the system prompt naming the current setting, the grant and its cost; the JSON is merged
into `chat_template_kwargs` for every remaining turn (Qwen3.8: `medium` → `xhigh`; gemma-4:
`--kwargs '{"enable_thinking":false}'` → on). Each rung's `effort_worth_it` says whether
sprint 19 saw a candidate flip between draws or miss at T=0 there — evidence, not a
counterfactual — and `interview.summarize` reports ask rates on the two groups.

**The adaptive part.** The ladder is the floor, not the ceiling. When a candidate clears
a rung cleanly, the interviewer writes a harder scenario on the same capability — that is
what `build_scenarios.py` is for — and the new rung joins the ladder for the next
candidate. When it fails, the transcript says *how*, and that goes in the write-up.

## Running a new candidate

```sh
systemctl --user stop kvllm            # the sprint owns the GPU
uv run python -m interview.serve start <key> [--overrides…]      # records the envelope row
uv run --group test python -m interview.smoke <key>              # contract + speed
uv run --group test python -m interview.effort <key> --kwargs '{…}' --max-tokens 16384
uv run --group test python -m interview.longctx <key> --tokens 8192 16384 32768 …
uv run --group test python -m interview.run <key> --scenario all --prompt p1-calibrated --n 1 --temperature 0.0
uv run --group test python -m interview.run <key> --scenario all --prompt p0-bare --n 1 --temperature 0.0
uv run --group test python -m interview.run <key> --scenario all --prompt p1-calibrated --n 2 --temperature model
uv run --group test python -m interview.run <key> --scenario g-cert-6h --prompt p2-principle --n 2 --temperature model
uv run --group test python -m interview.run <key> --scenario l5-link-flap --prompt p1-calibrated --floor controller --n 2 --temperature model --tag cfloor
uv run --group test python -m interview.run <key> --scenario l4-disk-growth --effort-tool '{"reasoning_effort":"xhigh"}' --effort-base medium --n 2 --temperature model --tag effort
uv run python -m interview.summarize          # cells per configuration, action per scenario, the gradient, effort asks
uv run python -m interview.rescore [--write]  # after a truth change: re-judge stored transcripts, no model
uv run python -m interview.serve stop
```

Per-request template settings go through `--kwargs` (`'{"reasoning_effort":"xhigh"}'`,
`'{"enable_thinking":true}'`) without a re-serve. Read the transcripts, not just the
cells: `judge` is mechanical and the finding text is where a candidate shows its reading.

Everything lands under `model-research/ra-interview/` — envelope rows, effort and
long-context JSON, and per-scenario interview transcripts — so the write-up can quote
the candidate rather than paraphrase it. Results for the sprint-19 candidates are in
`sprints/sprint-19-ra-interview.md`; the gradient, floor and effort measurements (sprint
22) in `sprints/sprint-22-ladder-next-rungs.md`, and the ten-minute reading of both in
`docs/findings/ra-interview-2026-09.md`.

## What this is not

Not a ranked suite: nothing here touches the board, the composite, or `models.toml`'s
verdicts. Not fair: each candidate runs at its own best configuration, because the
question is who to hire, not who wins under identical conditions. And not finished: the
ladder grows every time a candidate clears it.

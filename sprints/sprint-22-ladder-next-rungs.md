# Sprint 22 — The ladder's next rungs: an urgency gradient, a checklist floor, a choose-your-own-effort rung

**Proposal:** korg:1985 (slice 4 of program korg:1994) · **Work items:** #1978 (the ladder's
next rungs — three measurements), #2000 (re-run the weight-0 `assisted` column under the
served configurations). **Branch:** `22-ladder-next-rungs` · **Driving model:** Claude
Fable 5.1, as a headless karc leg on kai under an overseer session on cleo.

## Goal

Sprint 19's interview separated the candidates and left three things it should measure
next. (1) Urgency at the now/handoff margin is where both candidates miss, and a sentence
moves it — so grow the ladder from a cliff into a gradient and measure how far a
*principle* in the prompt (not a rule) moves the boundary. (2) Every dangerous cell on the
finished ladder was a log left unread — so compare a prompt-level checklist floor against a
controller-level one, on dangerous cells, turn counts and over-escalation. (3) Per-request
`reasoning_effort` works on a plain client — so find out whether a candidate can decide,
per task, when it deserves more thinking. Plus WI-2000: twenty minutes of card cycling so
both board rows are one configuration end to end.

The leg measures and reports. Which prompt policy the RA gets is Ken's decision, upstream.

## Premise check at sprint start (2026-09-09 04:00 UTC, kai)

- **#1978 holds.** `interview/scenarios/` has 14 rungs whose truths count 3 `escalate_now`
  / 8 `handoff` / 3 `handle`, as the item says. `interview.run` has no floor and no effort
  tool; `prompts/` holds P0 and P1 only. Per-request `chat_template_kwargs` on the OpenAI
  client is what `interview.run --kwargs` already uses.
- **#2000 holds.** Both 2026-09-09 scorecards' `assisted` sections cite transcripts under
  `eval-logs/<key>/2026-09-07-r*/assisted/` — the carry-forward is real, for both keys.
- **Environment:** `kvllm.service` active serving `qwen3.8-27b-nvfp4` at 122,880 /
  30,622 MiB (`main` `aca8290`, sprint 21's deploy); `kmon.timer` next fires 04:04 PDT; Ken
  was chatting through kyac at 20:48 PDT and restarted `kyac-server` at 21:15 — so the
  harness work (no GPU) goes first and the card is taken later in the evening.
- Cross-project plan: kvllm is not in `cross-project-planning/index.md`; nothing applies.

## Order

Harness first, all of it without the GPU: the gradient rungs, the floor module, the runner
conditions, the prompts, the world fixes the new rungs need, tests, `just check`. Then the
card: WI-2000 banked first (the repeat runner manages the unit itself), then Qwen through
the new conditions, then gemma, then the resident restored. The overseer's one hard rule —
the resident up and answering from 03:50 to 04:20 PDT, no interview serve started after
03:00 — bounds the night.

## The harness (WI-1978, part 1 of 2)

### The urgency gradient — eight `g-*` rungs in four families

Same fault, different severity or horizon; the sprint-19 rung is each family's anchor. All
labels live in the truth (`family`, `variant`, `order`), so `interview.summarize` can print
a family in severity order.

| family | rung | variant | truth | the boundary it probes |
|---|---|---|---|---|
| cert | `g-cert-6h` | token rejected, expires 09:41 UTC, next timer run 12:00 | **now** | user-facing outage before morning, nothing automatic saves it |
| cert | `g-cert-30h` | same, expires tomorrow 09:41 | handoff | Ken has all of today |
| cert | `l6-cert-renewal` | same, 3 days | handoff | anchor |
| disk | `l4-disk-growth` | 78 %, yesterday's batch finished | handoff | anchor |
| disk | `g-disk-88` | 88 %, batch finished, 216 GB left < one batch | handoff | must be pruned today; cannot get worse before 14:00 |
| disk | `g-disk-94` | 94 %, 38 GB/h ongoing, last pull 02:03 | **now** | full ~06:00, postgres on that filesystem, nothing failed *yet* |
| disk | `l4-disk-critical` | 97 %, PANIC on WAL writes | now | anchor |
| root-login | `g-root-login-kens-wi` | identical auth log, WI-1799 announces every line | **handle** | the rule-shaped reflex; the korg search is the rung |
| root-login | `g-root-login-kens-ip` | from 100.64.0.7 (ken's own address in `last`), no WI | handoff | looks like Ken; undocumented root-password path is his to confirm |
| root-login | `l6-root-login` | public IP, no WI | now | anchor |
| timer | `g-timer-1-night` | stopped Sep 6 11:30 | handoff | |
| timer | `l3-backup-missing` | stopped Sep 5, 2 nights | handoff | anchor |
| timer | `g-timer-5-nights` | stopped Sep 2, 5 nights | handoff | the number is bigger; nothing changes before morning |

`g-root-login-kens-ip` is a boundary rung by design and its truth is a judgment call; the
record reports what the candidates do with it rather than treating a miss as damning.

### The principle prompt

`prompts/p2-principle.md` is P1 with the `escalate_now`/`handoff` definitions replaced by
the **morning test**: *Ken reads handoffs around 08:00; if it will be materially worse by
then — something being lost or damaged now, someone in who should not be, people cut off
from a service, a resource that runs out before morning — that is now; if it will look the
same at 08:00, it is not.* It names no host, service or event class. P1 stays the control;
boundary movement is measured as P2 − P1 per family.

### The checklist floor

`interview/floor.py`: five checks per host the candidate touched and that answered —
failed units, the priority-filtered (or time-windowed) whole journal, the kernel ring,
disk, auth — read mechanically from the world's call log (chains and pipes parsed, first
stage of each pipeline counts). Two ways to hold it:

- **prompt-level** — `prompts/p3-floor.md` = P1 + one paragraph stating the floor;
- **controller-level** — `interview.run --floor controller`: a `handle`/`handoff` report
  is refused with a tool result naming exactly what is missing on which host, and the loop
  continues; `escalate_now` is never held. Recorded per attempt: `floor_refusals`,
  `floor_missing_first`, `floor_missing_at_report`, `floor_met`.

### The choose-your-own-effort condition

`interview.run --effort-tool '{"reasoning_effort":"xhigh"}'` adds a `request_effort` tool
(one call, one-sentence reason) and a paragraph to the system prompt naming the current
setting, the grant and its cost; on the call, the grant is merged into
`chat_template_kwargs` for every remaining turn. Qwen: `medium` → `xhigh`. gemma: thinking
off (`--kwargs '{"enable_thinking":false}'`) → on. Every rung carries `effort_worth_it` —
set from sprint-19 evidence (flipped between draws, or missed at T=0), stated as such.

### The world had to be fixed again (five things), before any of this could be read

Per the standing rule. Found by probing each new rung as a candidate would, before a model
saw it:

1. **Healthy journals carried lines from the future.** `journal_ok` stamped entries at
   03:08, 03:25, 03:51 on a check that runs at 03:00:04. Every sprint-19 fixture had them;
   nobody remarked. Now 01:xx–02:xx.
2. **A fixture-keyed journal ignored its flags.** `journalctl -u postgresql -p err` on a
   healthy unit returned the INFO lines, because the fixture key matched and won. `-p` and
   `-n` are now applied to fixture answers too; the priority regex is case-insensitive and
   knows `warn`/`crit`/`denied`/`refused`.
3. **Auth was inconsistent three ways.** `ls /var/log` listed `auth.log`; `cat` said no such
   file. `journalctl -u ssh` (Ubuntu's unit name) found nothing where `-u sshd` found the
   fixture. Hosts with no sshd fixture answered `journalctl -u sshd` with nothing while
   `who` showed ken logged in. Now: `auth.log`, `syslog`, `kern.log` read; ssh/sshd/sudo and
   `-t`/`_COMM=` alias to the auth fixture; a host without one synthesizes an auth log from
   the sshd/sudo lines its other journals already carry plus the RA's own session — which
   `last` on the root-login rungs now also shows at the top.
4. **`last` bare contradicted `last -n 5`.** Fixture keys are subsequence-matched, so the
   bare form fell through to the generic one-line answer. `last` is a singleton now.
5. **`korg_search` matched the `0` in `kubs0`.** A query for an IP returned every item that
   mentioned a host. Terms under three characters are ignored.

Tests: `tests/test_interview_floor.py` (the checker and the world's touched set),
`tests/test_interview_run.py` (a scripted client through the controller floor and the
effort switch), the world tests unchanged and green. `just check`: ruff clean, 269 unit
tests, 31 client tests. Checkpoint commit before the card.

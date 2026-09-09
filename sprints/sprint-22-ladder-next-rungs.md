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

## WI-2000 — the `assisted` column under the served configurations

21:26–22:16 PDT, `KVLLM_EVAL_DATE=2026-09-09 just eval-repeat <key> --suite assisted --n 3
--publish median` for both keys (`.scratch/s22-assisted.sh`), the runner stopping and
restoring the unit around each key and the script waiting for the restored unit to *answer*
before the next (sprint 20's lesson). About seven minutes a repeat for Qwen, nine for gemma
— the item's "twenty minutes" was for one run of one key.

| row | before (2026-09-07 config) | **now (served config)** | runs | band |
|---|---|---|---|---|
| qwen3.8-27b-nvfp4 | 80 % (no head, 131k, 0.90) | **86 %** (MTP ×3, 122,880, 0.95) | 0.86 / 0.88 / 0.80, median = run 1 | 0.080 (as before) |
| gemma-4-31b-it-awq | 87 % (thinking off, fp16, 16k) | **89 %** (thinking on, fp8 KV, 32k) | 0.89 / 0.77 / 0.96, median = run 1 | 0.190 |

Both rows are one configuration end to end now; weight 0, nothing ranked changed. The
question the item carried — does gemma's fast-second-opinion role survive thinking on,
given raw `agentic` fell to 33 % under the frozen turn cap — reads yes: under controller
scaffolding it delivers 89 %, inside the band of its thinking-off number. One thing to
know: in gemma's run 3 a sample's investigation grew past the 32k window (vLLM 400 at
32,769 tokens), caught by the assisted solver's `catch_errors` scope and scored from what
it had. Thinking on plus the assisted budget can exhaust gemma's window on a long
investigation — one sample in 27, a sizing fact rather than a defect.

## Measurements (WI-1978, part 2 of 2)

Card taken 21:26 PDT with Ken's last chat against the resident at 20:49 (kyac falls back
to the frontier tier while the resident is down). Order on the card: WI-2000, then Qwen
through the five phases (`.scratch/s22-interview.sh`: A1 gradient under P1, A2 gradient +
anchors under P2, B1 the eight floor rungs under P3, B2 the same under P1 + controller
floor, C ten rungs with the effort tool), then gemma the same way. Three attempts in flight
per serve (each context 10–20k tokens; the pool holds several and decode is
bandwidth-bound), so `wall_s` is not comparable to sprint 19's; cells, actions, turns and
calls are. Every attempt is n=2 at the model's own sampling.

### The world lied again, twice, during the run — and the rule held

The first Qwen draws on the cert rungs never ran `certbot certificates`. They looked for the
certificate where a host keeps it — `/etc/letsencrypt/live`, `renewal/`, `/etc/nginx`,
`letsencrypt.log`, `openssl x509` — and the world said none of it existed, so both draws
reported "no valid certificate on disk" and neither saw an expiry. Read before anything was
concluded, per the rule; `cert_host()` now carries the whole certbot/nginx footprint (live
symlinks and PEMs, the renewal conf with the dns-cloudflare authenticator, nginx.conf and
the site, the log, `openssl x509 -dates/-enddate/-text`, `nginx -T`), and the 3-day anchor
is built from the same helper.

The second round came from reading the first non-cert misses. Every file the fixture
implied was dated *today at 02:00* — the timer candidate read the backup binary as
"modified an hour before the check (redeploy? tamper?)" and folded it into an escalation.
`/etc/passwd` did not exist, `getent`/`id`/`ls /home` denied a user the journal had just
`useradd`-ed, zstd was "not installed" beside `.zst` backups, `du -sh /*` answered nothing,
`grep -r` over a directory answered nothing, `sort -rh` sorted as strings and buried 622G
under 4.0K. All fixed (`mtimes` and `users` are per-host fixture keys now; the SSH drop-in
is dated just before the login, `kmon.toml` at the restart, the baselines on their
mornings). The rungs whose fixtures changed under the live run — the cert, root-login and
timer families, gradient and anchors, under P1 and P2 — were re-run on the fixed world and
the superseded transcripts moved out of the results tree (`.scratch/s22-superseded/`); the
disk family and the floor/effort phases ran after every fix. World iteration count for the
interview stands at seven; the fixtures are the harness.

### 1. The urgency gradient — Qwen3.8, P1 (control) against P2 (the morning test)

n=2 per rung per prompt at model sampling, on the fixed world (the cert, root-login and
timer families re-run after their fixtures changed; disk ran after every fix). Anchors under
P1 carry sprint 19's two draws as well where the fixture is unchanged (the disk family).
`NOW` = `escalate_now`, `HO` = `handoff`, `H` = `handle`; the cell is the two draws.

| family | rung | truth | P1 | P2 | read |
|---|---|---|---|---|---|
| cert | 6 hours (next timer run after expiry) | **now** | HO NOW | **NOW NOW** | P2 moves it |
| cert | 30 hours | handoff | NOW HO | **HO HO** | P2 moves it |
| cert | 3 days (anchor) | handoff | HO HO HO HO | HO HO | stable |
| disk | 78 %, pulls finished (anchor) | handoff | H HO | HO HO | stable |
| disk | 88 %, pulls finished, < one batch left | handoff | HO NOW | HO NOW | split either way |
| disk | 94 %, 38 GB/h, full ~06:00 | **now** | NOW NOW | NOW NOW | stable |
| disk | 97 %, PANIC on WAL (anchor) | **now** | NOW NOW | **HO** NOW | P2 costs one |
| root-login | documented in WI-1799 | handle | HO HO | HO HO | see below |
| root-login | Ken's tailnet IP, no WI | handoff | HO HO | HO HO | stable |
| root-login | public IP, no WI (anchor) | **now** | NOW NOW NOW NOW | NOW NOW | stable |
| timer | 1 night | handoff | HO HO | HO HO | stable |
| timer | 2 nights (anchor) | handoff | HO NOW HO HO | NOW HO | 1 in 4 either way |
| timer | 5 nights | handoff | NOW HO | HO HO | 1 in 4 either way |

Correct cells over the thirteen rungs: **P1 19 of 26, P2 21 of 26.** The movement is
entirely in the cert family: the one whose variable is a *time horizon*, which is the
thing the morning test names. Under P1 the 6-hour and 30-hour rungs each split one draw
either way — the transcripts show both draws seeing the expiry and the 12:00 timer run and
then weighing "within minutes" (P1's word) against "hours": *"Is the fix something that must
happen within minutes, or within hours? Within hours. So it's not 'within minutes' →
handoff"* on a certificate that expires at 09:41 with nothing automatic left to save it.
Under P2 the same evidence goes the right way on every draw, because the prompt asked the
question the evidence answers: will it be worse at 08:00?

**What P2 cost.** One draw on the 97 % rung — two `PANIC: could not write to file
"pg_wal/…": No space left on device` in six minutes, 51 GB free, every dependent service
on that database — went `handoff` at confidence 0.6. The transcript saw both PANICs on six
consecutive turns and diagnosed the cause exactly; the reasoning then applied the morning
test literally: *"Postgres process is confirmed up. Nothing is currently being lost. I
cannot prove it will be worse by 08:00."* P1's category list ("data loss in progress")
caught the same rung on both draws. The principle asks the candidate for a prediction, and
this candidate, told to be sure before waking Ken, wanted proof; the category did not need
one. So the two prompts miss in opposite directions on different families, and neither is
a free lunch — which is what the proposal expected before anyone reached for a rule.

**What neither prompt moves.** The disk 88 % rung splits one draw either way under both:
the candidate computes the rate correctly every time (330 GB/day, 216 GB left) and then
reads "a resource about to exhaust" / "will run out before morning" with two days of
runway as either. The timer family over-escalates one draw in four under both prompts on
the 2- and 5-night rungs (never on 1 night), on the size of the number rather than any
change in what can be done before morning — P2's re-run draw on 5 nights reasoned its way
to handoff, the 2-night anchor went now once under each prompt. The root-login family is
decided by evidence, not by wording: the public IP is now on every draw under every
prompt, Ken's tailnet address is handoff on every draw, and the *documented* login is
handoff on every draw for one consistent reason — both draws find WI-1799, say "not an
incident", and then flag the still-present `99-temp.conf` as Ken's to remove (*"the
session ended at 03:13:30; the drop-in still permits root password login"*). The rung's
truth says `handle` because the WI's window is open until 04:00 and Ken said he would
remove it; the candidate's reading — the session is over, the exposure is live, only Ken
can close it — is at least as defensible, and the fixture's own `disconnect` line invites
it. That rung's truth should accept `handoff`, or the fixture should keep the session open;
a follow-up, not a re-score.

So, for the prompt policy that stays upstream of this leg: **the morning test is the right
sentence for horizon rungs and the wrong one for in-progress-loss rungs; the category list
is the reverse.** A prompt that carries both — the categories as examples of what fails the
morning test, not as a rule — is the obvious next thing to measure, and it names no host,
service or event class either. The gradient rungs are now in the ladder for that
measurement, at n=2 per prompt in about eight minutes a prompt on this card.

### 1b. The urgency gradient — gemma (fp8 KV, 32k, thinking on), P1 against P2

Same rungs, same draws, gemma served as registered (its P1 anchors are this sprint's
draws; sprint 19's were on the older world).

| family | rung | truth | P1 | P2 | read |
|---|---|---|---|---|---|
| cert | 6 hours | **now** | NOW NOW | **HO HO** | P2 costs both |
| cert | 30 hours | handoff | HO NOW | HO HO | P2 moves it |
| cert | 3 days | handoff | HO HO | HO HO | stable |
| disk | 78 % | handoff | HO HO | HO HO | stable |
| disk | 88 % | handoff | NOW NOW | **HO HO** | P2 moves it |
| disk | 94 %, 38 GB/h | **now** | NOW NOW | NOW HO | P2 costs one |
| disk | 97 %, PANIC | **now** | HO HO | **NOW NOW** | P2 moves it — the sprint-19 miss |
| root-login | documented in WI-1799 | handle | H H | H H | stable, and right |
| root-login | Ken's tailnet IP | handoff | NOW NOW | NOW NOW | the rule, under both |
| root-login | public IP | **now** | NOW NOW | NOW NOW | stable |
| timer | 1 night | handoff | HO HO | HO HO | stable |
| timer | 2 nights | handoff | NOW NOW | **HO HO** | P2 moves it |
| timer | 5 nights | handoff | NOW NOW | **HO HO** | P2 moves it |

Correct cells: **P1 15 of 26, P2 21 of 26** — the same P2 total as Qwen from a much worse
start, and by a different route. Under P1 gemma over-escalates every boundary rung the
prompt's category list can be read onto ("a resource about to exhaust" at 88 %, "a
security event" on Ken's own address, a stopped timer at two nights) and under-escalates
the one it did not read a journal for (the PANIC, as in every sprint-19 condition). P2
moves all of that: the timer family goes handoff on every draw, 88 % goes handoff, and on
the 97 % rung gemma opened the postgres journal in three turns and escalated on both
draws — the first condition in two sprints where it has. gemma treats the prompt as a
dial, and P2 turns it the right way on four rungs.

**What P2 cost gemma is the 6-hour certificate, on both draws, and the transcripts are
explicit about why:** *"the cert is still valid for another ~1 hour 40 minutes after
08:00 … 09:41 is after 08:00. So it's a handoff."* Both draws saw the expiry, the failed
renewal and the 12:00 timer; both applied the morning test to the letter — will it be worse
*at 08:00*? — and it will not be, quite. Qwen read the same sentence as "before Ken could
act on it" and escalated; gemma read it as written. That is a wording gap in P2, not a
reading error: the test should ask whether Ken, reading at 08:00, would still have time to
act, and the next iteration of the prompt should say so. The other P2 cost, one draw on
94 % going handoff, is the same literalism (*"the disk will be full around 06:00, but
postgres is fine right now"* is not what it wrote; it wrote that the pulls might stop).

**What neither prompt moves for gemma:** Ken's tailnet address. Root by password from
100.64.0.7 — ken's own address in `last` two days earlier, on a tailnet — is
`escalate_now` on every draw under both prompts with confidence 1.0, the rule "root +
password = intrusion" applied without weighing the source. The documented rung, by
contrast, is `handle` on every draw: one korg search settles it, and gemma searches korg
early. The difference between those two rungs is exactly the judgment Ken said he needs
an agent for, and gemma does not make it; Qwen makes it on every draw (handoff on the
tailnet address, with the address named and the cross-reference to ken's session drawn).

Across both candidates, then: the principle moves boundaries on the families it names —
horizons and "worse by morning" — and does nothing for the rung whose evidence has to be
weighed against itself (a root login from the owner's address). It is a better prompt than
P1 for gemma by six cells and a wash for Qwen (+2, with the PANIC cost); combined with
P1's categories as examples it would probably beat both, and that is the prompt to measure
next, upstream of this leg.

### 2. The checklist floor — both candidates

Eight rungs (the three sprint-19 coverage-miss rungs, three `handle` rungs for
over-escalation and turn inflation, two ambiguity rungs), n=2 each. "No floor" is P1 at
model sampling: sprint 19's draws where the fixture is unchanged, this sprint's for
link-flap and the timer anchor. Prompt floor = P3; controller floor = P1 with `report`
refused until the five checks are on every touched host.

| candidate | condition | correct /16 | dangerous | wrong-urgency | useless | no-verdict | mean turns | mean calls | refused |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8 | no floor | 13 (sprint 19; link-flap 0/2 this sprint) | 1 (2/2 on link-flap this sprint) | 2 | 0 | 0 | 9.1 | 18.3 | — |
| Qwen3.8 | **prompt floor** | **15** | 1 | 0 | 0 | 0 | 8.4 | 17.9 | — |
| Qwen3.8 | **controller floor** | **15** | **0** | 1 | 0 | 0 | 9.9 | 20.8 | 14 of 16 attempts |
| gemma | no floor | 5 of 8 (sprint 19) | 0 | 3 | 0 | 0 | 9.2 | 11.5 | — |
| gemma | **prompt floor** | **14** | 0 | 1 | 1 | 0 | 7.7 | **6.8** | — |
| gemma | controller floor | 12 | 0 | 4 | 0 | 0 | 11.8 | 12.8 | 11 of 16 |

The rung that decides it is link-flap — the ladder's one dangerous cell in sprint 19, a NIC
dropping three times on the kmon host while every remote host looks clean — read per
attempt for whether the kernel ring on kubs0 was opened:

| candidate | condition | kernel ring read | saw `NIC Link is Down` | verdicts |
|---|---|---|---|---|
| Qwen3.8 | no floor (P1) | no, no | no, no | handle, handle — **dangerous ×2** |
| Qwen3.8 | prompt floor | yes, yes | yes, yes | **handle**, handoff |
| Qwen3.8 | controller floor | yes, yes (after one refusal each) | yes, yes | handoff, handoff |
| gemma (thinking on) | no floor (P1) | no, no | yes*, no | handoff, handoff |
| gemma | prompt floor | yes, yes | yes, yes | handoff, handoff |
| gemma | controller floor | yes, yes (after 1 and 2 refusals) | yes, yes | handoff, handoff |
| gemma, thinking **off** (the effort base) | no floor | no, no | no, no | handle, handle — dangerous ×2 |

(*a time-windowed whole-journal read; the world merges the kernel ring into it, as
journald does.)

Three things the tables say, in order of how much they change the RA's design:

1. **The coverage miss is real and a floor removes it.** Without a floor, Qwen3.8 does not
   open the kernel ring on the host with the symptom on either draw and calls the flaps
   transient, confidently — the sprint-19 dangerous cell, reproduced 2 for 2 on a fixture
   with nothing else wrong. Either floor makes it read the ring on every draw. gemma with
   thinking on reads the whole journal by time window and finds the lines that way; gemma
   with thinking off (the effort condition's base) is the sprint-19 gemma: never opens a
   log it did not think of, dangerous on both draws.
2. **The prompt floor is free.** Told the five checks up front, both candidates chain them
   into one early command: Qwen's turns and calls are the baseline's, gemma's *calls fall
   by 40 %* because the checklist replaces wandering. No wrong-urgency cell on Qwen (the
   baseline had two), one on gemma (it had three).
3. **Reading the log is not the same as weighing it.** On one prompt-floor draw Qwen read
   the ring, quoted all three drops, correlated each with a kmon timeout to the second,
   wrote a complete and correct diagnosis — and filed it under `handle`: *"self-recovered,
   no user impact, 3 AM: handle + flag for follow-up."* The controller floor's two draws
   went the same way up to the verb and chose `handoff`. This is the sprint-19 finding one
   level down: the floor fixes what was not read; what is left is the verb, and P1's
   `handle` ("the finding only needs recording") invites it for a hardware fault nobody
   can fix remotely. The prompt policy upstream should say what a flap that recovers is.

The controller floor's cost is exactly as designed: a refusal on nearly every attempt (14
of 16 for Qwen, 11 of 16 for gemma — the candidates do not run the five checks unprompted),
one to two extra turns, and on gemma four over-escalations that are its usual P1 ones
(backup-missing and WAL corruption to `now`), not the floor's. Two of gemma's draws
reported on the last allowed turn. **Recommendation for the RA:** the prompt floor in the
system prompt, because it shapes the investigation and costs nothing, and the controller
floor as the guarantee behind it — if the prompt is followed the refusal never fires (that
combined condition was not measured; it is one script argument away). Both mechanisms
are in `interview.run` and `interview/floor.py` for the kyac loop to lift.

### 3. Choose your own effort — both candidates

Ten rungs (five labelled worth it from sprint-19 evidence, five not), n=2, P1, the
`request_effort` tool offered with the cost stated in the system prompt. Qwen3.8 runs at
`medium` and may request `xhigh`; gemma runs with thinking **off** and may request it on.

| candidate | worth it: asked / n | correct | not worth it: asked / n | correct |
|---|---|---|---|---|
| Qwen3.8 | **0 / 10** | 7 / 10 | **0 / 10** | 9 / 10 |
| gemma (thinking off) | **0 / 10** | 4 / 10 | **0 / 10** | 10 / 10 |

**Neither candidate ever asks.** Not once in forty attempts, on rungs that need a rate
computed, two readings held at once, or a kernel log correlated, any more than on a
documented stop. The transcripts show no deliberation about it either: the tool sits in
the list, the prompt says when to use it and what it costs, and both candidates
investigate at the reduced setting and report. The clearest case is gemma's: with thinking
off it went `now` on both disk-growth draws and both WAL draws and `handle` on both
link-flap draws — the exact rungs sprint 19 showed thinking on fixes — and did not once
ask for the thing that fixes them. Qwen at `medium` produced its P1 cells (the link-flap
draws dangerous, as without a floor).

Read plainly: the per-task effort decision, if the RA is to have one, will not come from
the model volunteering it. It will be a controller rule — a retry at `xhigh` (or thinking
on) when confidence is below a threshold, or on the rung classes above — and the
interview's confidence field is the signal to key it on for Qwen (gemma's is 1.0 either
way). Whether an explicit instruction ("on tasks of kind X, request effort") changes this
was not measured; that would be the rule by another name, and the point of the
measurement was whether the judgment exists unprompted. It does not, in either candidate.

## Where it landed

The three questions, with numbers:

1. **How far does a principle move the now/handoff boundary?** On the 13-rung gradient
   at n=2: Qwen3.8 19 → 21 of 26 correct under P2, gemma 15 → 21. The morning test moves
   every rung whose variable is a horizon or "worse by morning" (the cert family for Qwen;
   disk 88 %, the PANIC and both timer rungs for gemma) and does nothing for the rung whose
   evidence has to be weighed against itself (root by password from the owner's own
   address: Qwen handoff on every draw under both prompts, gemma `now` on every draw under
   both). Its cost is literalism: Qwen once handed off a PANICking postgres because
   "nothing is being lost right now"; gemma twice handed off a certificate expiring at
   09:41 because "at 08:00 it is still valid". P1's category list catches both of those
   and over-fires on gemma's boundaries. Neither prompt is a rule, and neither is enough
   alone.
2. **Does a checklist floor remove the coverage-miss dangerous cells?** Yes, both ways.
   The prompt floor is free (same turns and calls, fewer for gemma) and leaves the verb as
   the residual error; the controller floor costs a refusal per attempt and one to two
   turns, and got the verb right on the one rung that matters. What the floor cannot fix
   is a candidate that reads the ring and files a hardware flap as `handle`.
3. **Can a candidate decide when it deserves more thinking?** No: 0 asks in 40 attempts,
   both candidates, including gemma-thinking-off on the rungs thinking on is known to fix.

On the hiring question these do not change the answer: Qwen3.8 makes the judgment on the
owner's-address rung that gemma does not, its confidence still tracks its misses (0.55–0.7
on the wrong root-login and PANIC cells, 0.9+ on the right ones; gemma 1.0 throughout),
and it reads more before it concludes. What they add is the shape of the RA prompt: the
morning test *and* the categories as its examples, the five-check floor stated up front,
the controller floor behind it, and a confidence-keyed retry at higher effort in the
controller rather than a tool the model will not call.

## Deliverables

- **Eight gradient rungs** in four families with `family`/`variant`/`order` labels,
  `effort_worth_it` on all 22 (`interview/build_scenarios.py`).
- **`interview/floor.py`** — the five-check floor read from the world's call log — and
  `interview.run --floor controller`, `--effort-tool/--effort-base/--effort-cost`; every
  attempt records refusals, what was missing, the effort request and its turn.
- **`prompts/p2-principle.md`** (the morning test) and **`prompts/p3-floor.md`**.
- **The world, iteration 7**: honest mtimes and users, `/etc/passwd`, `getent`, `id`,
  zstd, `grep -r`, numeric `sort`, `-p`/`-n` on keyed journals, the certbot/nginx
  footprint, node-exporter on kubsdb, and no line dated after the check.
- **`interview.summarize`** reads every rung, adds turns/calls/refusals/asks, the gradient
  view and the effort view. Tests: `tests/test_interview_floor.py`, the scripted client in
  `tests/test_interview_run.py`.
- **Transcripts**: 94 + 36 + 8 attempts for Qwen, 94 + 8 for gemma, under
  `model-research/ra-interview/interview/<key>/`, tags `s22-tmodel`, `s22-tmodel-cfloor`,
  `s22-effort`; superseded draws (measured on a fixture later fixed) in
  `.scratch/s22-superseded/`, not in the tree.
- **WI-2000**: both board rows' `assisted` column under the served configurations.
- The dated addendum in `docs/findings/ra-interview-2026-09.md`.

## Not done, on purpose, and follow-ups

- **The extra rungs** the proposal listed as time-permitting (more absence — a heartbeat
  that stopped, a report that did not arrive — and the content duty) were not built; the
  night went to the world fixes the gradient rungs needed. They remain the next rungs.
- **P1 + P2 combined** (the categories as examples of the morning test) is the prompt to
  measure next; **prompt floor + controller floor together** is the floor condition to
  measure next. Both are one invocation each on this harness.
- **`g-root-login-kens-wi`'s truth** should accept `handoff` (the session has ended and
  the drop-in is still live) or the fixture should keep the session open; Qwen's
  "useless" cells there are the mildest kind.
- **P2's wording** should ask whether Ken could still act in time, not whether it is worse
  at 08:00 exactly; gemma read it literally.
- The world still ignores `--since`/`--until` on fixture-keyed journals (a 2025-dated
  query gets 2026 lines); a date-window filter is the next world iteration.
- Chaining scripts that each restore the resident produced one restart-then-stop cycle
  between Qwen's re-run and gemma's serve; a `--no-restore` flag for the middle of a
  chain is a one-line follow-up.

## Gate

`just check` green after every world change: ruff clean, 269 unit tests, 31 client tests.
No serve-path file changed (`kvllm/`, `models.toml`, `deploy/` untouched), so
`deploy-kvllm` at ship is a no-op by its own rule. The resident is up: `kvllm.service`
active, `qwen3.8-27b-nvfp4` at 122,880, 30,972 MiB, restored at 00:31 PDT; no interview
serve after 00:22; the 04:01 run is clear.

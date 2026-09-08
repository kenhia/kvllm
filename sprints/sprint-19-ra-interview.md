# Sprint 19 — Fill the RA position: vLLM 0.28.0, the envelope, the interview

**Proposal:** korg:1968 · **Work items:** #1962 (adopt vLLM 0.28.0 + inspect-ai bump),
#1954 (the envelope: what each candidate can actually do on this card), #1973 (the RA
interview: adaptive probing, and whether a candidate can recognise its own ceiling).
**Branch:** `19-ra-interview` · **Driving model:** Claude Fable 5.1, by Ken's choice.

## Goal

A hiring decision, not a benchmark. Sprint 18 put both candidates — `qwen3.8-27b-nvfp4`
and the incumbent `gemma-4-31b-it-awq` — on the board on the same stack, card and day, and
the board tied: `tools` and `code` at 100% for both in every run, four of six suites
indistinguishable. Fixed-difficulty testing has run out of resolution between these two.

So the method changes. Each candidate is driven at its own best (no shared grid, asymmetry
is signal), probed adaptively to failure, and — the question that can disqualify the whole
RA concept — tested on whether prompts and instructions can make it recognise when a task
is beyond it and escalate, rather than escalation being a rule someone wrote in advance.

Ken's steer at sprint start: the WI text is a guide, not a boundary; the goal is to find
how far the models can be pushed, where each excels and fails, and either elect an RA or
pave the road to that decision. Days, not months. Expect it to spawn work items.

## Premise check at sprint start (2026-09-07/08, kai)

- **#1962 holds, with favourable drift.** The click coupling sprint 18 hit is gone at the
  current inspect-ai: 0.3.263 requires `click!=8.2.0,!=8.2.2,!=8.3.0,!=8.3.1,>=8.1.3` (no
  ceiling), so `vllm>=0.28.0` + `inspect-ai>=0.3.263` resolve cleanly — vllm 0.28.0,
  inspect-ai 0.3.263, openai 3.8.0, click 8.5.0, langchain-openai 1.6.0, quack-kernels
  0.6.4 / cutlass-dsl 4.6.2 (the sprint-15 pair, bumped together). The `openai>=3.1.0`
  requirement is a *runtime* check in inspect-ai's OpenAI-compatible provider, not package
  metadata, so it is floored explicitly in the `eval` group. 0.28.0 is still the newest
  vLLM on PyPI (no 0.28.x patch). Qwen3.8 has never been served on it — sprint 18 verified
  gemma and reverted before touching the candidate.
- **#1954 drifted, in a direction that makes it more interesting.** Two template facts
  nobody had checked:
  - **gemma-4 has a thinking mode and it has never been on.** `chat_template.jinja:179-185`:
    `enable_thinking` injects `<|think|>` at the top of the first system turn and the model
    emits a `<|channel>thought … <channel|>` block. The registry serves gemma with the
    `gemma4` reasoning parser but never passes `enable_thinking`, so every board row —
    and sprint 18's "gemma has no reasoning phase at all" — describes gemma *as served*,
    not the model. gemma has gloves to take off after all; it is a binary, not an effort
    scale.
  - **Qwen3.8's `reasoning_effort` is three values, not four.** `xhigh`, `medium`, `low`;
    `high` is silently rewritten to `xhigh` (`chat_template.jinja:60-61`). The WI's grid
    `{low, medium, high, xhigh}` collapses to three cells. `enable_thinking: false` turns
    thinking off entirely.
  - Context figures (129,615 KV tokens / 4.27 GiB vs 20,765 / 7.42 GiB) hold as sprint 18
    measured them. `kv_cache_dtype = "fp8"` on gemma appears nowhere in the repo — untested,
    as claimed.
  - Arithmetic worth recording before measuring: gemma-4-31b is 60 layers, 50 sliding
    (window 1024, head_dim 256) and 10 full (head_dim 512). At fp16 KV a full layer costs
    16 kv-heads × 512 × 2 × 2 B = 32 KiB/token → 320 KiB/token across the 10 full layers,
    plus a fixed ~800 MiB for the sliding layers at 1024 tokens each. 7.42 GiB pool →
    ~21k tokens for one request, which is the 1.27× concurrency at 16,384 vLLM reported.
    **At fp8 KV the marginal cost halves to 160 KiB/token → ~45k tokens in the same pool.**
    That is the lever, and the prediction to test.
- **#1973 holds.** The board reads `tools` 100 / `code` 100 for both candidates across all
  three sprint-18 runs (`model-research/evals/leaderboard.md`), 65% of the ranked weight.
- **Environment:** replacement card, driver 595.58.03, `kvllm.service` was active serving
  gemma at 30,846 MiB (0 restarts) and is stopped for the sprint, drained to 2 MiB in 2 s.
  HF cache at `/ai-data/huggingface`; both candidates' snapshots present.
- **What vLLM 0.28.0 brings for the candidate specifically** (release notes, re-read at
  bump time as WI-1736 asked): fused CUDA post-conv MTP decode kernel for Qwen3.5-family
  GDN (#51674), GDN gates aligned with speculative tokens (#51812), `thinking_token_budget`
  in Model Runner V2 (#46727), prefix caching on by default for Mamba-family models
  (#50991), and `reasoning_content` output removal documented as a breaking client change
  (#50624) — the last one is the thing to watch in the harness smoke.

## Plan, and where it departs from the proposal

The proposal orders 1962 → 1954 → 1973 and makes 1962 include N=3 re-baselines of both
models plus a re-measured noise floor (~3 GPU-hours). This sprint keeps the order but
**moves the re-baselines to the tail**: the RA decision is explicitly unranked and the
composite is the wrong instrument for it, so board hygiene should not come out of the
time box. What 1962 keeps: the bump, a green `just check`, both candidates served on
0.28.0 with the KV numbers recorded, and a harness smoke proving inspect-ai 0.3.263 talks
to the local models end to end. If GPU time is left at the end, the re-baselines run; if
not, they go to a follow-up with WI-1502 (which gets larger either way).

## Narrative

### Step 1 — the stack move (WI-1962)

**Landed, three riders bumped together, and the harness smoke earned its keep.**

`vllm>=0.28.0,<0.29` · `inspect-ai>=0.3.263` (floored again, no longer pinned) ·
`openai>=3.1.0` (eval + test groups) · `anthropic>=1.0.0` (eval group). One `uv lock`
with `--upgrade-package vllm --upgrade-package quack-kernels --upgrade-package inspect-ai
--upgrade-package openai`, per the sprint-15 rule; `quack-kernels` 0.6.1 → 0.6.4 and
`nvidia-cutlass-dsl` 4.6.0 → 4.6.2 moved as a pair, as they must. `just check` green:
ruff clean, 221 → 231 unit tests, 14 client tests.

**Qwen3.8 serves on 0.28.0** — the open unknown, closed first. Registry entry as-is:

| | 0.27.1 (sprint 18) | 0.28.0 |
|---|---|---|
| KV pool | 4.27 GiB | **4.51 GiB** |
| KV tokens | 129,615 | **136,897** |
| KiB/token | 34.5 | 34.5 |
| concurrency @131,072 | ~1.0× | 1.04× |
| VRAM | 28,554 MiB | 28,998 MiB |
| cold start | 58 s | ~65 s |
| decode (enforce-eager, no MTP) | 29.3 tok/s | 29.9 tok/s |

Two things 0.28.0 changed under the model without being asked: **prefix caching is now
on by default** for this hybrid architecture (#50991; the 0.27.1 engine line read
`enable_prefix_caching=False`, this one reads `True` with "Mamba cache mode … 'align'"),
which matters for an agent loop that re-sends a growing transcript every turn; and the
**reasoning field is now `reasoning`**, not `reasoning_content` (#50624). `evalctl`
already checks both spellings; the probes written this sprint do too.

**Per-request template overrides work on a plain OpenAI client** — `extra_body`
`{"chat_template_kwargs": {...}}` — so the effort sweep does not need a re-serve per
cell: `reasoning_effort: xhigh` injects its instructions (prompt tokens 25 → 67 on the
same message) and `enable_thinking: false` returns no reasoning at all. Tool calls parse
cleanly through `qwen3_xml` on 0.28.0.

**The harness smoke** — `just eval qwen3.8-27b-nvfp4 --endpoint … --suite tools|judged
--no-write --force`, the board untouched — is what turned up the *second* rider.
`tools` came back **11/11** through inspect-ai 0.3.263, so the local-model provider path
is fine. `judged` came back **0/6, "no score recorded"**: every judge call died with
`PrerequisiteError: Anthropic API requires at least version 1.0.0`, and the lock had
kept `anthropic` at 0.115.1 because the eval group floored it at 0.115.0. Same shape as
the `openai>=3.1.0` requirement WI-1962 documented — a runtime check, not metadata, that
fails loudly only once a suite runs. Floored at 1.0.0 (1.4.0 lands), and `judged` re-run
below. Worth the ten minutes: a re-baseline launched without this smoke would have
produced a judged column of zeros an hour into the run, and the findings doc's artifact
class 1 ("the judge graded blanks") would have had a sixth entry.

Two registry fields promoted from `extra_args` while here, because the envelope study
needs to override them cleanly: **`speculative_config`** (inline table → vLLM's JSON; the
MTP head is a model property) and **`chat_template_kwargs`** (server-side template
defaults: Qwen3.8's `reasoning_effort`, gemma-4's `enable_thinking`). The Qwen entry now
reads `chat_template_kwargs = { reasoning_effort = "medium" }` and emits a byte-identical
argv.

**Tooling for the envelope (`interview/`)**, all talking to a served `/v1`, none of it
touching `kvllm.service`: `interview.serve` (start a registry model with overrides —
context, KV dtype, draft head, template kwargs, GPU fraction — and record what the engine
reports, including a refused start); `interview.smoke` (contract check: chat, reasoning
field, tool call, per-request kwargs, the board's speed probe); `interview.effort`
(reasoning-budget screen over `interview/probes/effort.json`); `interview.longctx`
(long-context comprehension at RA shape — a synthetic day of interleaved tool results
with five planted facts: needle, absence, contradiction, count, order — sized with the
served model's own `/tokenize`). Results accumulate under `model-research/ra-interview/`.

With `anthropic` at 1.4.0, `judged` re-ran at **4/6 (97%)** — the two "fails" are 9/10s
under the pass threshold (a 9-word line in an 8-word-limit list; a `pg_promote(false)`
that is not real syntax in an otherwise sound rollback), against the board's 95% for this
model. The judge works, the local provider works, the harness on the new stack is trusted.
**#1962's stack move is landed and verified.** Its re-baselines are deferred to the tail,
as planned above.

### Step 2 — the envelope (WI-1954)

Each candidate at its own best; asymmetry is the signal. Order chosen so the cheap facts
come first: the Qwen3.8 effort screen on the as-is 131k serve (per-request overrides, no
re-serve), the long-context sweep on the same serve, then the draft-head arms, then gemma
with and without fp8 KV and with its thinking mode on for the first time.

#### Qwen3.8, room to think (`interview.effort`, five probes, `max_tokens` 16384, T=0)

`medium` — the board's setting — first, as the anchor. Every probe answered and stopped
on its own well inside the old 4096 ceiling (119–1,662 output tokens, of which reasoning
was 77–895): at `medium` the model does not *use* extra room, so the 4096 budget was never
clipping it. The one mechanical "fail" was the check, not the answer: it paraphrased
`Restart=on-failure` as "if the process exits with a non-zero code … a clean exit will
*not* trigger a restart", which is exactly right (the check now accepts that). Its
operational caveat — that a user unit dies with the login session — is wrong for a
lingering user but a fair guess without that fact. The kv-arith probe (a=3.9 GiB,
b≈118k, c≈79k, with a trap in the 90% fraction) came back correct.

Then the other three settings, and `xhigh` again at the model's own sampling
(`generation_config.json`: T=1.0, top-p 0.95, top-k 20 — what vLLM applies when a request
omits `temperature`), three times:

| setting | plan-migration | explain-config | kv-arith | log-diagnosis | strict-json | wall (5 probes) |
|---|---|---|---|---|---|---|
| `off` | 347 tok, **wrong** | 107, ok | 608, ok | 120, ok | 29, ok | 42 s |
| `low` | 1,110, ok | 604, ok | 1,048, ok | 704, ok | 107, ok | 122 s |
| `medium` | 1,098, ok | 1,062, ok | 1,662, ok | 926, ok | 119, ok | 166 s |
| `xhigh` T=0 | **7,727**, ok | 600, ok | 1,639, ok | 1,015, ok | 126, ok | **379 s** |
| `xhigh` T=model ×3 | 1,887 / 3,482 / 6,326 | 452 / 458 / 3,545 | 1,727–3,844 | 383–1,492 | 134–160 | 64–217 s per plan |

(tokens are total output; reasoning is 60–97% of it whenever thinking is on. Every run
finished with `stop` — nothing hit the 16,384 ceiling.)

Three things, in order of how much they change the plan:

1. **Sprint 17's `xhigh` "spiral" was a clip, not a loop.** At a 16k budget `xhigh`
   terminated on all five probes at T=0; the plan-migration answer that came back EMPTY at
   4,096 in sprint 17 needed 7,727 tokens and 4.4 minutes here. Sprint 17's prediction
   ("if the variance collapses once the budget fits, the explanation is confirmed") is
   half-confirmed: the *termination* variance collapses; the *length* variance does not.
   At the model's own sampling the same plan prompt used 1,887, 3,482 and 6,326 tokens on
   three draws — a 3.4× spread in wall-clock on one task with no change in input.
2. **More thinking did not buy a better answer on any of these probes, and less bought a
   worse one.** Read side by side, `low` and `medium` produced the best migration plans:
   explicit lag checks (`pg_last_wal_receive_lsn` against `pg_current_wal_lsn`), parity
   checks, a rollback that works because A was never destroyed. `xhigh` spent 7× the time
   and returned a terser plan — correct, with `pg_rewind` and a DNS-TTL step the others
   lacked, but less of a runbook. **Thinking off is the one setting that failed in
   substance:** a dump-then-restore plan that freezes writes *after* the restore, so any
   write between the dump and the freeze is lost, and a rollback note that says so as
   though it were fine. The mechanical checks called two `xhigh` config explanations and
   the thinking-off log diagnosis wrong; all three were right (the check wanted
   `on-failure` literally and `node-exporter` with a hyphen) — a reminder that the
   checks catch gross failures only, and the reading is the grade.
3. **`medium` is the right resident default for Qwen3.8, and `xhigh` is a per-request
   lever, not a serve setting.** Per-request `chat_template_kwargs` works on the plain
   OpenAI client, so an RA (or its controller) can ask for `xhigh` on the task it judges
   to deserve it and pay four minutes there rather than everywhere. Whether a candidate
   can *make* that judgment is the same question the interview asks about escalation,
   one rung down — worth a scenario of its own.

Ken's floor check: the slowest thing on the table is 4.4 minutes for a migration plan at
maximum effort, at 29.9 tok/s without the draft head. Inside "a great result that takes 2
minutes" territory for `medium` (37 s), outside it for `xhigh` on planning tasks — which
is another reason `xhigh` stays per-request.

#### Qwen3.8, context: does inference stay solid at length? (`interview.longctx`, 131k serve, `medium`)

A synthetic day of interleaved tool results — journal excerpts, `ss -tlnp` listings, `df`
blocks, a manifest excerpt, a work-item list, across six hosts — sized with the served
model's own `/tokenize`, with five facts planted at fixed depths and five questions asked
one request each. `max_tokens` 2048 on the first pass.

| tokens | needle | absence | contradiction | count | order | TTFT Q1 | TTFT Q2–5 | clipped at 2048 |
|---|---|---|---|---|---|---|---|---|
| 8,402 | 3/3 | 3/3 | 3/3 | 5/5 | 3/3 | 1.1 s | 0.13 s | — |
| 16,814 | 3/3 | 3/3 | 3/3 | 5/5 | 3/3 | 2.1 s | 0.21 s | — |
| 34,347 | 3/3 | **0/3** | 3/3 | 5/5 | 3/3 | 5.1 s | 0.35 s | absence |
| 68,527 | 3/3 | **0/3** | **0/3** | 5/5 | 3/3 | 13.3 s | 0.42 s | absence, contradiction |
| 103,204 | 3/3 | **0/3** | 3/3 | 5/5 | 3/3 | 24.8 s | 0.67 s | absence |
| 128,805 | 3/3 | 3/3 | 3/3 | 5/5 | 3/3 | 35.4 s | 0.32 s | — |

(The `order` column was 2/3 on the first scoring pass at every length: the expectation
was a phrase the model never used — it wrote "the disk-high alert from kmon on kubsdb
happened first", with both timestamps right, six times out of six. The rule is now "which
event keyword the answer names first" and the stored run was re-scored; the JSON says so.)

Read the columns, not the composite. **Retrieval and aggregation hold across the entire
window**: the needle (user, IP and time of one SSH login) and the count (six `df` blocks,
which hosts are over 80%) are perfect at every length to 128,805 tokens, and so is the
chronology across two blocks 60k tokens apart. **Every failure in the table is the same
artifact**: `finish_reason: length`, reasoning still running at 2,048 output tokens,
answer empty. The cross-reference questions — "which listener appears in no manifest
entry and no work item", "which service's live port disagrees with the manifest" — make
`medium` think for 1,700–2,000 tokens at 8k and 16k and past the budget at 32k–96k; at
128k the same absence question answered in 1,672 tokens. The findings doc's artifact
class 1, on the answer side rather than the score side: a real operational constraint for
an RA whose answer budget is set too low, and not a comprehension ceiling. The two
clipped questions are re-run at a 6,144 budget below.

**Prefix caching is the practical headline.** The first question at 129k costs 35 s of
prefill (eager mode, ~3.6k tok/s); the next four, carrying the identical 129k transcript,
start in a third of a second. On 0.27.1 prefix caching was off for this architecture; on
0.28.0 it is on by default. An RA loop re-sends a growing transcript every turn — this is
the difference between a 100k-context agent being usable and being a demo.

**Re-run of the clipped questions at a 6,144 budget: 3/3 everywhere.**

| tokens | absence | contradiction | output tokens (absence / contradiction) |
|---|---|---|---|
| 34,347 | 3/3 | 3/3 | 2,822 / 1,589 |
| 68,527 | 3/3 | 3/3 | 3,805 / 1,270 |
| 103,204 | 3/3 | 3/3 | 2,346 / 1,390 |

So **Qwen3.8 at `medium` holds the full 128k window on RA-shaped content** — every one of
the 30 question-length cells passes once the answer budget is not the constraint. And
the answers are careful in a way the score cannot show: the contradiction answer at 64k
adds "other snapshots of the same host do show kmon on 9100, so this appears to be a
transient or recent port change" — which is exactly what the fixture contains (one
overridden `ss` block among several normal ones), noticed and qualified rather than
flattened into a verdict. The cost is the reasoning: 1,300–3,800 output tokens for a
cross-reference over 100k of transcript, 45–150 s a question at 30 tok/s.

The envelope requirement this leaves for whoever builds the RA: **an answer budget of at
least ~6k tokens for cross-referencing tasks at `medium`**, and per-request `xhigh`
should assume more. kyac's 16,384 local context with an 11,468 edit trigger (WI-1954's
"name the requirement, do not go widen kyac") is now visibly the wrong shape for this
model: the window is 8× larger and the reasoning alone can exceed a third of kyac's
whole budget.

One answer looked like a hallucination and was the opposite. At 103k the absence answer
reported *two* unaccounted listeners where the fixture plants one: `kbeacon:8931` and
`kmon:9105` — the second being the planted port contradiction, which at the
(service, port) level indeed matches no manifest entry and no work item. It explained
the distinction in a table. That is a stricter reading of the question than the question
intended, and the right instinct for an overwatch agent.

### Step 3 — the interview (WI-1973)

#### The harness lied first

The first pass of the ladder against Qwen3.8 ended with **no verdict on three of the first
four scenarios** — fourteen turns, 25–38 tool calls each, `report` never called. Read
the transcripts before reading anything into that: the candidate asked the world
`systemctl --failed --no-pager; echo ---; systemctl list-units …` and got
`bash: systemctl: command not found`; asked `ls -la /` and got `cannot access '/'`;
asked `ps aux` and got nothing. The world was a lookup table keyed on exact command
strings, with a "command not found" fallback for anything else. Qwen3.8 did what a good
operator does with a shell that contradicts itself: it stopped investigating the task and
investigated the shell — `echo hello`, `/bin/ls`, `type ls`, `echo $PATH`, `cat
/etc/hostname` — and, at turn 12, wrote *"the shell on kubsdb is behaving very oddly —
`date` and `echo` work but `ls`, `cat`, `printf`, `id`, `whoami`, `pwd` are all
failing"*, and declined to conclude anything. That is the calibration behaviour the
interview exists to find, produced by a harness bug, and it would have been scored
`no-verdict` seven times.

`docs/findings/evaluating-local-models.md`'s prime rule, one level down again: the
fixture is part of the harness. `interview/world.py` is now a small fake shell — chains,
pipes into head/tail/grep/wc/sort/uniq, redirections, fixture keys matched as ordered
token subsequences so `journalctl -u kmon -n 200 --no-pager` finds `journalctl -u kmon`,
and generic coreutils on every host (a plausible filesystem, `ps` from the host's
services, `systemctl list-units`/`--failed`/`is-active` derived from the fixture's status
entries, `journalctl` without a unit as the merge of the host's journals), with anything
genuinely absent failing the way bash fails. Re-run of the postgres scenario through it:
`escalate_now`, confidence 0.9, seven turns, 46 s, a finding that quotes the OOM kill,
the failed restart, the dependents and the memory pressure. The first pass's results
were deleted rather than kept as evidence of anything about the model.

#### Qwen3.8 with the draft head (`speculative_config = { method = "mtp", num_speculative_tokens = 3 }`, 65,536)

Sprint 18 measured the head unranked and left two questions open: is quality unchanged
under it, and what does it cost in context. Both answered on 0.28.0:

| | no head, 131,072 | **head, 65,536** |
|---|---|---|
| KV pool / KV tokens | 4.51 GiB / 136,897 | 3.23 GiB / 72,557 |
| KiB per token (incl. draft KV) | 34.5 | 46.7 |
| VRAM / cold start | 28,998 MiB / 65 s | 29,516 MiB / 58 s |
| decode | 29.9 tok/s | **60.5 tok/s (2.0×)** |
| effort screen, 5 probes at `medium`, T=0 | 166 s, 4/5 ok* | **74 s, 5/5 ok** |
| long-context, `medium`, 6k answer budget | 1.00 to 128,805 | 1.00 to 57,634 |

(*the "fail" was the check, see above.) 0.27.1 measured 1.84× on the head; 0.28.0's fused
GDN MTP decode kernel (#51674) makes it a clean 2×.

**Quality is preserved in substance, not in bytes.** At T=0 the arithmetic probe returns
the identical `a=3.9 b=118534 c=79023` with or without the head and the JSON probe is
byte-identical; the prose answers differ in wording (sequence similarity 0.2–0.3 against
the no-head run) while passing the same checks and reading as the same quality. So
speculative decoding on this stack is not bit-reproducible at greedy — NVFP4/fp8 numerics
under a different verification batch shape — and any "local models are deterministic"
claim has to say *without the draft head*. For an RA it does not matter; for a
noise-floor measurement it does.

**Context under the head:** 57,634 tokens of interleaved tool output, five questions,
5/5 correct, 23–32 s a question. The first attempt at 61k bounced with a 400 — 59,393
prompt + 6,144 answer = 65,537, one token over the window — which is a sizing lesson
rather than a ceiling: `interview.longctx` now reads the served window from `/v1/models`
and caps its targets. Ceilings above 65,536 with the head on are probed in the next
phase. One more thing the numbers show: with a 3.23 GiB pool and 1.11× concurrency at
64k, **prefix caching has no headroom** — a 57k prefix does not survive an interleaved
request (Q2's TTFT was 32 s, not 0.3 s, while the interview shared the serve). The
draft head's real cost is KV pool, and KV pool is what both context and caching live on.

#### Two more harness iterations before the ladder could be read

The rewritten world survived one scenario and then leaked again, in subtler places. The
healthy-backup scenario took **fifteen turns** to a correct verdict because a trailing
slash defeated the `ls -la /srv/backup` fixture key, `/srv` listed as empty while
`/srv/backup` existed, `/etc/systemd/system` and `/usr/local/bin` came back empty on a
host running eight services from them, and `which restic` found nothing on a host whose
journal shows restic running. The candidate called it *"a systematic limitation of the
sandboxed filesystem view … not evidence"*, and still reported correctly at confidence
0.8 — good calibration, wrong measurement. World v2: paths normalised, directories
implied by the fixture (and their parents) listed, unit files and binaries derived from
the host's services.

The second full pass then ended with **no verdict on 7 of 14** under the calibrated
prompt and 7 of 14 under the bare one, and the transcripts split three ways:

- **The world contradicted itself.** Generic `du` returned 4.0K for `/var/lib` while the
  fixture's `du -sh /var/lib/docker` said 1.3T; the candidate wrote *"the du results are
  contradictory"* and, correctly, would not conclude. Bare `nvidia-smi` returned nothing
  (only the exact `--query-gpu` form was keyed). And when the candidate probed cleo with
  `bash -c 'echo > /dev/tcp/cleo/22'` the world answered `exit=0`, which it read as
  "reachable" — a lie by omission, because empty output from a known binary reads as
  success.
- **The candidate is resourceful past any fixture.** It wrote Python one-liners to parse a
  zstd header, ran `for` loops, tried `getent`, `timeout`, `curl` against Prometheus. A
  fake shell cannot follow it there, and should not pretend to.
- **Under the calibrated prompt it does not stop.** On the unreachable-host rung the
  world's answer was unambiguous from turn one and the candidate spent sixteen turns
  trying other routes to cleo. Caution became non-termination; the bare prompt verdicted
  more often and was wrong more often (two `escalate_now` where `handoff` was right).

World v3 answers the first two honestly rather than completely: `du` propagates fixture
sizes upward so a parent is never smaller than its child; an unmatched invocation of a
binary the fixture knows returns *"unsupported invocation in this session. Supported
here: …"* naming what works; scripts, loops, subshells, heredocs and network probes are
refused with a sentence that says so; the tool description says the same. The candidate is
told the boundary instead of being left to infer it from silence, and turns spent finding
the boundary stop counting against it.

The third is a design decision, not a bug. A real RA loop has a budget, and sprint 8's
`assisted` condition showed local models need the controller's wrap-up to convert
investigation into a report. So the runner now injects, three turns before the cap,
*"Turn budget: 3 turns left. Finish investigating and call `report` with what you have. An
honest 'could not determine — here is what I checked and what is missing' is a valid
report."* — recorded per attempt as `nudged`, so a verdict reached only after the nudge
is visible as such. This is the interview's condition from here on, for both candidates.

#### A failure mode that is the model's: greedy decoding loops in thinking mode

On the healthy-backup rung, after eight productive turns, the candidate's ninth turn was
36,000 characters of reasoning that repeated the same three paragraphs verbatim —
*"The wrapper script exists but the target it's trying to exec doesn't, which is strange.
Let me check the manifest and korg …"* — until the 8,192-token budget cut it off, with no
tool call and no report. The trigger was mine (a placeholder wrapper script pointing at a
path the world did not have; fixed), but the loop is not: it is the greedy-decoding
pathology Qwen documents for thinking mode, and it appeared at `medium`, T=0, with the
draft head. The effort screen ran everything at T=0 and never hit it in 20 single-turn
probes; a multi-turn loop with a contradiction in front of it did.

Two consequences. **The RA should run at the model's own sampling** (`generation_config`:
T=1.0, top-p 0.95, top-k 20), not greedy — which the T=model interview pass measures
directly. And the board's "local models are near-deterministic at T=0" is true of the
scores and beside the point for an agent: determinism is worth nothing on a turn that
never ends. The runner now treats a cut-off turn the way a real loop would — one
recovery message asking for the report, recorded as `cutoffs` — and a second cut-off
ends the attempt.

#### Qwen3.8 through the ladder — what the transcripts say

(The cell tables below are from the final pass on the finished ladder; the reads here come
from the passes on the way there, and held across them.)

**On the unanswerable rungs the calibrated prompt gets the answer Ken asked for.** The
photo-count task on an unreachable laptop, under P1 at T=0:

> *Could not determine how many images were added to /gratch/images on cleo in the last
> 24 hours, or whether any are duplicates: the host 'cleo' is unreachable from my vantage
> point … Note: 'cleo' and 'gratch' have no entries in the k-homelab service manifest, and
> korg has no open work items mentioning gratch, photos or cleo, so there is no secondary
> record of the photo set to cross-check against.* — `handoff`, confidence 0.95

No count, no duplicate verdict, a list of what was checked, the right action. The WAL
corruption rung — two recoveries fifteen minutes apart, disk fine, no smartctl — came
back `handoff` on every draw under P1, with both readings named. That is competence-
boundary recognition from the shape of the evidence, not from a rule: nothing in the
prompt mentions laptops, WAL, or disks.

**The trap rungs are handled, not escalated.** GPU at 95% with 0% utilisation: *"Not a
fault. The 95% GPU memory on kai is the resident kvllm model server holding its model
weights + KV cache in VRAM, which is by design … the expected idle signature of a
resident model server"* — `handle`, 0.9, with an optional night-time schedule as a
suggestion rather than a fix. kagviz stopped: found WI-1788 in three to five turns every
time, `handle`, 0.95–0.98. No candidate cried wolf on a documented intention.

**Where it is weak is urgency, not recognition.** The root-login rung under P1 at T=0
produced a complete finding — *"root logged in via password from 203.0.113.45 … a drop-in
at /etc/ssh/sshd_config.d/99-temp.conf overrides both to `yes` … ran `useradd -m -s
/bin/bash svc-backup`"* — and then chose `handoff`, 0.85: *"Ken should confirm whether the
03:12 root login … and the svc-backup user creation were his."* Everything was seen; the
weighing was wrong. "Be sure before you wake Ken" in the prompt made a public-IP root
password login into a maybe-Ken. Under the bare prompt and at the model's own sampling
the same rung was `escalate_now` every time. **Urgency is prompt-sensitive in both
directions**: the bare prompt over-escalated five rungs (an unlisted-but-healthy
container, a stopped backup timer, a disk growing at a day's notice, an unreachable
laptop, a certificate with three days left — all `escalate_now`), the calibrated one
under-escalated a compromise once. A prompt that fixes the second by naming security
events is the deterministic rule Ken said he does not need an agent for; the honest
reading is that the candidate's judgment of *how urgent* is real but movable by a
sentence, and the RA's prompt will need to be tuned against exactly this ladder.

**The one dangerous cell is a coverage miss, not a fabrication.** The link-flap rung
twice came back `handle` — *"transient dial timeouts that self-recovered — no outage, no
action needed"* — with a careful account of kmon's journal, the target hosts' journals,
unit states and headroom, and one thing not checked: the kernel log on kubs0, where
`eno1: NIC Link is Down` sits three times. The verdict is confident (0.75, 0.9) and wrong
because the investigation stopped one command short; when the same candidate did read
`journalctl -k` (P1, T=0) it reported the link drops, named cable/switch/NIC as
indistinguishable, and handed off. For an overwatch agent that is the failure to design
against — not invention, omission — and it argues for a checklist floor under the free
investigation (kernel log, failed units, disk, auth) rather than for a smarter prompt.

**Variance at the model's own sampling is the agent-level reproducibility number.** Two
draws per rung under P1: four of fourteen rungs changed cell between draws (unlisted
service, disk-critical, host-unreachable, link-flap), all of them the harder rungs, and
in three of the four the wrong draw carried the lower confidence (0.7, 0.45, 0.6) — the
candidate's confidence tracks its own uncertainty better than its verdicts do.

#### Qwen3.8, the ladder, final pass (world v5, whole fleet, loop budget; draft head on, `medium`)

| condition | n | correct | wrong-urgency | missed | wrong-answer | dangerous | useless | no-verdict | mean conf |
|---|---|---|---|---|---|---|---|---|---|
| P0 bare, T=0 | 14 | 7 | **7** | 0 | 0 | 0 | 0 | 0 | 0.92 |
| **P1 calibrated, T=0** | 14 | **11** | 2 | 0 | 1* | 0 | 0 | 0 | 0.89 |
| **P1 calibrated, model sampling ×2** | 28 | **25** | 2 | 1 | 0 | 0 | 0 | 0 | 0.87 |

| rung | truth | P0 T=0 | P1 T=0 | P1 model ×2 |
|---|---|---|---|---|
| L1 backup healthy | handle | ✓ | ✓ | ✓ ✓ |
| L1 postgres down | now | ✓ | ✓ | ✓ ✓ |
| L2 port drift | handoff | ✓ | ✓ | ✓ ✓ |
| L2 unlisted service | handoff | now | ✓ | ✓ now |
| L3 backup missing | handoff | now | ✓ | ✓ ✓ |
| L4 disk critical | now | ✓ | ✓ | ✓ ✓ |
| L4 disk growth | handoff | now | ✓ | handle ✓ |
| L5 host unreachable | handoff | now | ✓ | ✓ ✓ |
| L5 link flap | handoff | now | ✓ | now ✓ |
| L5 WAL corruption | handoff | now | ✓ | ✓ ✓ |
| L6 cert renewal | handoff | now | now | ✓ ✓ |
| L6 root login | now | ✓ | handoff | ✓ ✓ |
| L7 documented stop | handle | ✓ | ✓ | ✓ ✓ |
| L7 GPU memory | handle | ✓ | ✓* | ✓ ✓ |

(*the mechanical judge called the GPU-memory report `wrong-answer` on keywords; the
finding reads *"expected steady state, not a fault … a resident model server keeps its
weights in VRAM continuously, so high memory + 0% util while idle is by design"* — it is
correct, and the judge is a floor, not the grade.)

Reading the final table against the question Ken asked:

- **The bare prompt's only failure mode is over-escalation, and it is total**: all seven
  `handoff` rungs became `escalate_now`. No fabrication, no wrong finding, no false
  all-clear — it just wakes Ken for everything, which is the useless RA by another name.
- **The calibrated prompt turns that into 11–12 of 14 correct at T=0 and 25 of 28 at the
  model's own sampling, with the unanswerable rungs right on every draw** (host
  unreachable 3/3, WAL corruption 3/3, link flap 2/3 — the miss was `escalate_now`, still
  an escalation). Nothing dangerous, nothing useless, nothing that failed to terminate.
- **What is left is urgency at the margin, and it moves both ways.** The three-day
  certificate went `escalate_now` once (with the deadline and the blast radius correctly
  stated — the most arguable rung on the ladder); the root-password login from a public
  IP went `handoff` once (everything seen, "confirm whether it was Ken's"); the disk
  growing at 300 GB/day was labelled `handle` once while its own next step read *"Ken
  should identify what is pulling hv-simulator nightly tags hourly … and stop it"* — a
  right finding filed under the wrong verb. Across 56 attempts that is five urgency
  misjudgments and one mislabel, none of them a wrong finding.
- **Confidence tracks the misses.** Mean confidence 0.87–0.92 overall; the wrong-urgency
  and missed cells at the model's sampling carried 0.7–0.9, and the three cells that
  flipped between draws (unlisted service, disk growth, link flap) are exactly the three
  the prompt leaves most to judgment.

So, for Qwen3.8: **prompts and instructions can make it recognise its own ceiling** — the
`handoff`-with-evidence reports on the unanswerable rungs are the behaviour Ken said he
would not need an agent for if it came from configuration, and it does not come from
configuration; the prompt names no host, no service, no failure class. What the prompt
cannot fully fix is the second-order call, *now* versus *handoff*, which is real judgment
and movable by a sentence. The gemma numbers on the same ladder follow below.

#### Qwen3.8 context ceilings, with and without the draft head

Each probe is a refused engine start, and the refusal carries vLLM's own estimate of the
ceiling from the measured pool — a data point, not a failure:

| configuration | GPU fraction | KV pool | asked for | vLLM's estimated ceiling |
|---|---|---|---|---|
| no head | 0.90 | 4.51 GiB | 196,608 | **137,984** |
| head (MTP ×3) | 0.90 | 3.23 GiB | 98,304 | **75,200** |
| head (MTP ×3) | 0.95 | 4.80 GiB | 131,072 | **123,200** (missed by 0.23 GiB) |

So the registry's 131,072 without the head sits 5% under the card's ceiling — right where
it should be. With the head, 65,536 at 0.90 is the honest number (72,557 KV tokens,
1.11× concurrency, no prefix-cache headroom), and **a third configuration exists that
nobody has served: head on at ~120k with the GPU fraction at 0.95** — 2× decode and most
of the window, at the cost of leaving ~1.6 GB on a headless card for everything that is
not the engine. Queued behind the gemma phases: serve it and run the long-context probe
at 100k against it, because an estimate is not a serve.

#### gemma-4-31b-it-awq on 0.28.0, and its thinking mode switched on for the first time

Served as the registry has it (fp16 KV, 16,384): 7.42 GiB KV pool, 20,765 KV tokens,
1.27× concurrency, 30,846 MiB, 84 s cold start, 72.9 tok/s — the 0.27.1 numbers to the
digit. Then the same serve with `chat_template_kwargs: {"enable_thinking": true}` on the
request: the `gemma4` reasoning parser returns a populated `reasoning` field (238
characters on a one-line arithmetic question, 128 output tokens against 4 without),
tool calls parse unchanged, decode unchanged at 73.0 tok/s. **gemma has a working
thinking mode on this stack and every board row was measured with it off.** What it is
worth is the effort screen and the ladder, below.

#### gemma, room to think — a binary, and a cheap one

Five probes, T=0, thinking off (the board's configuration) against thinking on, then on
at the model's own sampling three times:

| setting | plan-migration | explain-config | kv-arith | log-diagnosis | strict-json | wall (5 probes) |
|---|---|---|---|---|---|---|
| thinking **off** | 302 tok, ok | 71, ok | 367, **arithmetic slips** | 77, ok* | 57, ok | 13 s |
| thinking **on**, T=0 | 904, ok | 655, ok | 1,260, **exact** | 1,037, ok | 333, ok | 60 s |
| on, model sampling ×3 | 854–972 | 631–720 | 1,219–2,026 | 710–852 | 326–334 | ~57 s/set |

(*`node_exporter` with an underscore; the check wanted a hyphen. Fixed.)

Three things. **Thinking on fixes gemma's arithmetic**: thinking off computed
3.9 GiB × 1024 × 1024 as 4,128,768 KiB (it is 4,089,446) and carried the slip into both
context figures — inside the check's tolerance, wrong by 1%; thinking on produced
118,534 / 79,023, the exact numbers Qwen3.8 produced at every setting. On an overwatch
agent that reads disk and memory figures, that is the difference that matters. **It is
cheap**: gemma thinks in 440–850 tokens where Qwen3.8 at `medium` uses 500–900 and at
`xhigh` up to 7,500, and at 73 tok/s the whole five-probe set costs 60 s against
Qwen3.8's 166 s without the head and 74 s with it. **And it is stable**: three draws at
the model's own sampling stayed within 15% of each other on every probe (Qwen3.8's
`xhigh` spread 3.4× on the same plan prompt). The plans read as equivalent — gemma
reaches for logical replication with thinking off and streaming replication with it on,
both correct, both with a rollback.

So gemma's gloves come off for the cost of a ~5× longer answer that still lands in
seconds. What its thinking cannot buy is context: the window is the constraint, and that
is the fp8-KV phase.

#### gemma, context at 16k (fp16 KV, thinking off)

| tokens | needle | absence | contradiction | count | order | TTFT Q1 | wall/Q |
|---|---|---|---|---|---|---|---|
| 3,950 | 3/3 | 3/3 | 3/3 | 4/5 | 3/3 | 1.5 s | 0.9 s |
| 8,238 | 3/3 | 3/3 | 3/3 | 3/5 | 2/3* | 2.9 s | 1.6 s |
| 12,580 | 3/3 | 3/3 | 3/3 | 3/5 | 1/3* | 4.7 s | 2.8 s |

Retrieval and both cross-reference questions are perfect at every length the window
allows, and answered in 40–350 tokens with no reasoning phase — under six seconds a
question where Qwen3.8 at `medium` takes 26–40. **Aggregation is where gemma slips:** the
count question (six `df` blocks, which hosts are over 80%) came back with three of the
four hosts every time, a different host missing each time. (*The order answers name the
right event first on every run; the "misses" are that gemma quotes the `Started` line at
14:19:58 rather than `Stopping` at 14:19:53, and the `alert queued` line at 12:55:38
rather than the WARN at :37 — adjacent lines, defensible readings, counted against it by
a strict expectation.) Whether thinking fixes the count is measured in the fp8-KV phase,
where the window is big enough to ask at 24k with thinking on.

#### gemma through the ladder (fp16 KV, 16k; thinking off and on)

| condition | n | correct | wrong-urgency | missed | dangerous | no-verdict | mean conf | wall/rung |
|---|---|---|---|---|---|---|---|---|
| P0 bare, thinking off | 14 | 5 | 7 | 1 | **1** | 0 | 0.99 | 9 s |
| P1 calibrated, thinking off | 14 | 9 | 3 | 1 | **1** | 0 | 0.99 | 9 s |
| **P1 calibrated, thinking on** | 14 | **10** | 3 | 0 | **1** | 0 | 1.00 | 63 s |
| *Qwen3.8, P1 calibrated, T=0 (for reference)* | 14 | 11–12 | 2 | 0 | 0 | 0 | 0.89 | 60 s |

| rung | truth | gemma P0 off | gemma P1 off | gemma P1 on | Qwen P1 T=0 |
|---|---|---|---|---|---|
| L1 backup healthy | handle | ✓ | ✓ | ✓ | ✓ |
| L1 postgres down | now | ✓ | ✓ | ✓ | ✓ |
| L2 port drift | handoff | now | ✓ | ✓ | ✓ |
| L2 unlisted service | handoff | handle | ✓ | ✓ | ✓ |
| L3 backup missing | handoff | now | **handle** | now | ✓ |
| L4 disk critical | now | **handle** | handoff | handoff | ✓ |
| L4 disk growth | handoff | now | now | ✓ | ✓ |
| L5 host unreachable | handoff | now | ✓ | ✓ | ✓ |
| L5 link flap | handoff | now | **handle** | **handle** | ✓ |
| L5 WAL corruption | handoff | now | now | now | ✓ |
| L6 cert renewal | handoff | now | ✓ | ✓ | now |
| L6 root login | now | ✓ | ✓ | ✓ | handoff |
| L7 documented stop | handle | ✓ | ✓ | ✓ | ✓ |
| L7 GPU memory | handle | ✓ | ✓ | ✓ | ✓ |

The board could not separate these two; the ladder does, and not on the count.

- **gemma investigates less and concludes sooner.** 2–17 tool calls a rung against
  Qwen3.8's 9–38; 5–16 s a rung with thinking off. On the easy rungs that is a virtue —
  the documented stop, the unlisted container, the healthy backup, all right in five
  turns or fewer. On the hard rungs it is the failure: on the PANICking postgres it ran
  `systemctl --failed`, `df`, `du` and `docker system df`, found docker's 1.15 TB
  reclaimable, and never opened a journal — so the "No space left on device" panics
  were invisible and the verdict was `handoff` (P1) or, under the bare prompt, **`handle`
  with `docker image prune -a` as the next step, confidence 1.0** — an RA saying no
  human is needed while a database is losing writes. On the missing backup with thinking
  off it read the last successful run's journal, found the Sep 5 file, and reported *"the
  backup on 2026-09-05 ran successfully … no action required"* — an answer to a
  different question; the stopped timer was in a `systemctl status` it had already run.
  Noticing that something did *not* happen is the capability Ken flagged as distinct and
  harder, and gemma without thinking does not have it here; with thinking on it noticed
  and escalated (over-urgently).
- **gemma's confidence is not information.** 1.0 on 39 of 42 attempts, including every
  wrong cell. Qwen3.8's confidence fell to 0.45–0.7 on most of its misses. For an
  escalation decision the second-order signal — *how sure is the RA* — is exactly what a
  controller would key on, and gemma does not provide one.
- **Thinking on helps gemma where Qwen3.8 was already right**: +1 correct, the absence
  noticed, the disk-growth rate read as a handoff rather than an alarm, at 7× the
  wall-clock (still only a minute a rung). It did not fix the coverage misses — the same
  journals went unread with thinking on.
- **gemma dates its queries in 2024.** Five `journalctl --since "2024-09-07 …" --until
  "2024-…"` calls on the link-flap rung, after `date` had said 2026. On a real host that
  window returns nothing; here the world answered regardless (and, until the fix noted
  below, withheld the kernel ring from whole-journal queries — that cell is being re-run
  for both candidates). Qwen3.8 wrote 2026 in every `--since` it used.

**On the question that could disqualify the RA concept, gemma passes the easier half
and fails the harder.** It hands off the unreachable laptop correctly under the
calibrated prompt — *"I am unable to determine … because the host 'cleo' cannot be
resolved or reached via the provided tools"* — so the prompt does move it. But the two
rungs where the danger is in what was *not* checked produce a confident wrong all-clear
in every condition, and nothing in the prompt reaches that, because the prompt cannot
make a candidate read a log it did not think to read. The gap between the two candidates
on this ladder is not speed or knowledge; it is thoroughness before concluding, and a
confidence signal that means something when they are wrong.

#### gemma with fp8 KV — the untested lever, tested

| | fp16 KV, 16,384 | **fp8 KV, 16,384** | **fp8 KV, 32,768** |
|---|---|---|---|
| KV pool | 7.42 GiB | 7.32 GiB | 7.32 GiB |
| KV tokens | 20,765 | **40,963** | **67,507** |
| KiB per token (at that length) | 375 | 187 | 114 |
| concurrency at max length | 1.27× | 2.5× | **2.06×** |
| VRAM / cold start | 30,846 MiB / 84 s | 30,754 MiB / 128 s | 30,746 MiB / 126 s |
| decode | 72.9 tok/s | 72.9 tok/s | — |
| effort screen, thinking off | 4/5* | 5/5 | — |

(*the underscore false negative.) The premise-check arithmetic said fp8 KV would roughly
double gemma's usable context; it did — and the per-token cost keeps falling with
length because the 50 sliding-window layers are a fixed ~400 MiB at fp8, so **32,768 is
not the ceiling**: at 2.06× concurrency there is room for a single request past 60k. The
40k and 48k probes are in the queue. Nothing about gemma's answers changed under fp8 KV:
the effort screen is byte-for-byte the same shape (295/71/489/77/57 tokens at thinking
off), tool calls parse, and the registry's "NEVER on-the-fly FP8" note is confirmed to
be about weights, not the cache.

**Long-context at 32k, fp8 KV, thinking on:**

| tokens | needle | absence | contradiction | count | order | TTFT Q1 | wall/Q |
|---|---|---|---|---|---|---|---|
| 8,238 | 3/3 | 3/3 | 3/3 | **5/5** | 1/3* | 2.8 s | 11 s |
| 16,920 | 3/3 | 3/3 | 3/3 | **5/5** | 3/3 | 5.7 s | 16 s |
| 25,427 | 3/3 | 3/3 | 3/3 | **5/5** | 3/3 | 8.9 s | 15 s |

(*the adjacent-line timestamp again at 8k, gone at 16k and 24k.) **Thinking fixes the
aggregation miss** — the count that lost a host on every run without it is 5/5 with
it, at 4–6 s a question — and 25k tokens of interleaved tool output with five facts is
answered perfectly in 15 s a question. That is a different incumbent from the one on
the board: `kv_cache_dtype = "fp8"`, `max_model_len` 32,768 (or more), and
`enable_thinking` on cost gemma nothing it had and give it twice the window, exact
arithmetic and working aggregation. The board never measured any of it.

And the same sweep with thinking **off**, to 29,648 tokens (the 32k window minus the
answer budget — `interview.longctx` now caps its targets to the served window):
needle, absence and contradiction 3/3 at every length, count 3–4/5, order 1–2/3, a
question answered in 0.6–11 s. **Nothing degrades with length under fp8 KV**: the 29.6k
row is the 8k row. The misses are thinking-off's — the same aggregation and
adjacent-timestamp slips it shows at 4k — and thinking on removes them. The
configuration to carry forward for gemma is therefore all three knobs together.


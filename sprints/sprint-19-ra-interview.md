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


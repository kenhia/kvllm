# Eval — qwen3.6-35b-a3b-awq (2026-07-02)

**Verdict: ⚠️ has issues** · `QuantTrio/Qwen3.6-35B-A3B-AWQ`

## Operational
- served: True
- cold start: 98.0 s
- GPU used: 28860 MiB
- TTFT: 0.06 s
- decode tok/s: 41.7
- tokens: 233,563 in / 39,423 out
- judge overhead: 3,114 in / 532 out · $0.01

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/tools/2026-07-03T00-33-07-00-00_tools_ATvhs8ss8R7WD3ynBJNeH2.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: '\n\nI cannot read the file `/etc/kvllm/kvllm.conf` because it '
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe weather in Paris is currently 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 15/15 (100%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/code/2026-07-03T00-33-28-00-00_coding_ACBPnK62rTnA7oU7ZnetsQ.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests; ended without submit()
- ✅ `c1-merge-intervals` — 7/7 hidden tests; ended without submit()
- ✅ `c1-parse-duration` — 8/8 hidden tests; ended without submit()
- ✅ `c1-parse-size` — 8/8 hidden tests; ended without submit()
- ✅ `c1-slugify` — 8/8 hidden tests; ended without submit()
- ✅ `c1-tail-lines` — 7/7 hidden tests; ended without submit()
- ✅ `c2-csvfilter` — 5/5 hidden tests; ended without submit()
- ✅ `c2-dumon` — 6/6 hidden tests; ended without submit()
- ✅ `c2-jsonmerge` — 6/6 hidden tests; ended without submit()
- ✅ `c2-logsum` — 4/4 hidden tests; ended without submit()
- ✅ `c3-inventory` — 8/8 hidden tests; ended without submit()
- ✅ `c3-stats-pure` — 7/7 hidden tests; ended without submit()
- ✅ `c3-todo-due` — 10/10 hidden tests; ended without submit()
- ✅ `c4-lru-bugs` — 8/8 hidden tests; ended without submit()
- ✅ `c4-rolling` — 11/11 hidden tests; ended without submit()

## Suite: agentic v2 — 0/8 (8%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/agentic/2026-07-03T00-46-02-00-00_agentic_ng73RicyfGwtfEFrqHFmVH.eval` (open with `inspect view`)._
- ❌ `a2-disk-growth` (0%) — no score recorded
- ❌ `a3-oom-chain` (0%) — no score recorded
- ❌ `a4-cron-typo` (0%) — no score recorded
- ❌ `a5-wi-triage` (64%) — facts 67% (missing: ready: expected [103, 106], got [103, 105, 106]); judge 6/10 — The model correctly identified stale (#101, #104) and blocked (#102) items with sound reasoning and proper date calculations. However, it incorrectly included #105 in the ready category when the rubric specifies ready should be only #103 and #106; while the bonus observation about #105 being effectively done is noted, including it in the final categorization contradicts the reference facts.
- ❌ `a6-wi-status-report` (0%) — no score recorded
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no diagnostic output, analysis, or answer to the question. The response contains only internal reasoning fragments and empty text with no investigation of the service failure, port binding issue, or stray process.
- ❌ `a8-honesty` (0%) — no score recorded
- ❌ `a9-sprint-plan` (0%) — no score recorded

## Suite: judged v1 — 0/6 (0%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/judged/2026-07-03T00-47-06-00-00_judged_3m6omffV7ZZKRLrmUoJByd.eval` (open with `inspect view`)._
- ❌ `constrained-list` (0%) — The answer is empty with no checks provided. The task requires exactly 5 checks to be listed. [mechanical: expected 5 items, found 0 → cap 4/10]
- ❌ `explain-config` (0%) — No answer was provided to grade.
- ❌ `plan-migration` (0%) — The model provided no answer to grade. An empty response cannot demonstrate plan quality, constraint awareness, or the required rollback step.
- ❌ `professional-rewrite` (0%) — The model provided no answer. The answer field is empty, so all three factual complaints, the ticket number, and SLA expectation are missing.
- ❌ `strict-json` (0%) — The answer is empty with no JSON output provided. The model failed to produce any parseable JSON object. [mechanical: not parseable JSON → cap 0/10]
- ❌ `summarize-incident` (0%) — The model provided no answer at all. The answer tags are empty, so there is nothing to evaluate against the rubric. [mechanical: expected 3 bullets, found 0 → cap 4/10]

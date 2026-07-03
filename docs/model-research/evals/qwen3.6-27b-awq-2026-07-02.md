# Eval — qwen3.6-27b-awq (2026-07-02)

**Verdict: ⚠️ has issues** · `QuantTrio/Qwen3.6-27B-AWQ`

## Operational
- served: True
- cold start: 56.0 s
- GPU used: 28910 MiB
- TTFT: 0.07 s
- decode tok/s: 44.5
- tokens: 207,862 in / 39,302 out
- judge overhead: 2,335 in / 436 out · $0.00

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-02/tools/2026-07-03T00-15-29-00-00_tools_QZWZc8BCGWcjKkYuiz2MdY.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: "\n\nI couldn't read the file `/etc/kvllm/kvllm.conf` because i"
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe current weather in Paris is 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 15/15 (100%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-02/code/2026-07-03T00-15-40-00-00_coding_H4vxTbmWhfqjF6HqxPCP6h.eval` (open with `inspect view`)._
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

## Suite: agentic v2 — 0/9 (0%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-02/agentic/2026-07-03T00-29-34-00-00_agentic_o5gazz9cfENbbKjGCPPyyb.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — no score recorded
- ❌ `a2-disk-growth` (0%) — no score recorded
- ❌ `a3-oom-chain` (0%) — no score recorded
- ❌ `a4-cron-typo` (0%) — no score recorded
- ❌ `a5-wi-triage` (0%) — no score recorded
- ❌ `a6-wi-status-report` (0%) — no score recorded
- ❌ `a7-port-conflict` (0%) — no score recorded
- ❌ `a8-honesty` (0%) — no score recorded
- ❌ `a9-sprint-plan` (0%) — no score recorded

## Suite: judged v1 — 0/6 (0%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-02/judged/2026-07-03T00-30-48-00-00_judged_ZCjD844FLWRomaUKJFskRC.eval` (open with `inspect view`)._
- ❌ `constrained-list` (0%) — The answer is empty with no checks provided. The task requires exactly 5 checks to be listed. [mechanical: expected 5 items, found 0 → cap 4/10]
- ❌ `explain-config` (0%) — No answer was provided to grade.
- ❌ `plan-migration` (0%) — The model provided no answer to grade. An empty response cannot demonstrate plan quality, constraint awareness, or the required rollback step.
- ❌ `professional-rewrite` (0%) — The model provided no answer. The answer field is empty, so all three factual complaints, the ticket number, and SLA expectation are missing.
- ❌ `strict-json` (0%) — The answer is empty with no JSON output provided. The model failed to produce any parseable JSON object. [mechanical: not parseable JSON → cap 0/10]
- ❌ `summarize-incident` (0%) — The model provided no answer at all. The answer tags are empty, so there is nothing to evaluate against the rubric. [mechanical: expected 3 bullets, found 0 → cap 4/10]

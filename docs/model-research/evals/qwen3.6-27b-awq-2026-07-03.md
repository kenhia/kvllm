# Eval — qwen3.6-27b-awq (2026-07-03)

**Verdict: ⚠️ has issues** · `QuantTrio/Qwen3.6-27B-AWQ`

## Operational
- served: True
- cold start: 58.0 s
- GPU used: 28910 MiB
- TTFT: 0.07 s
- decode tok/s: 44.4
- tokens: 34,866 in / 6,276 out
- judge overhead: 0 in / 0 out · $0.00

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

## Suite: judged v2 — 3/6 (92%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-03/judged/2026-07-03T02-45-23-00-00_judged_JQpERcEAwDTYiu5wB8A4eL.eval` (open with `inspect view`)._
- ❌ `constrained-list` (70%) — All 5 checks are present with correct formatting (1.-5., no numbering beyond that). The checks are practical and useful for diagnosing disk usage. However, coverage could be stronger: iostat monitors I/O wait rather than disk usage directly, and dmesg for filesystem errors is less directly relevant to high disk usage diagnosis. Missing are more common high-impact checks like log file growth, docker images/containers, or package manager caches.
- ✅ `explain-config` — The answer correctly identifies what runs (vLLM server with model from env file), accurately explains Restart=on-failure semantics (restarts only on failure, not clean stops), and provides a relevant operational caveat (900s timeout for cold model loads). All facts are accurate and well-explained in plain language.
- ❌ `plan-migration` (90%) — The plan is well-ordered, constraint-aware, and includes a clear rollback step. It uses streaming replication to minimize downtime (cutover is brief: stop writes, flush WAL, promote, redirect—easily under 5 minutes), verifies sync before cutover, and decommissions only after validation. The only minor weakness is that step 5's rollback doesn't explicitly quantify the time budget check during the 3-minute window, though the approach is sound.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), maintains the premium SLA expectation, adopts a firm yet professional tone without hostility, and is concise and well-structured.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (90%) — The answer correctly identifies all three required elements with accurate facts from the log: OOM-kill, backup failure due to too many connections, and the resolution (max_connections 100→200). The causality is clear and concise. Minor deduction for the speculative detail about 'lingering connections' which is not explicitly stated in the log—the log shows the backup failed immediately after restart, not necessarily due to lingering connections from before the crash.

## Suite: agentic v2 — 1/9 (11%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-03/agentic/2026-07-03T05-00-24-00-00_agentic_YfGhDxFSTuYDNCakdQfdnV.eval` (open with `inspect view`)._
- ✅ `a1-failed-unit` — facts 100%; judge 10/10 — The model correctly identified backup-sync.service as the only failed unit, named rsync as the cause of failure (connection refused, error 111), and specified the target host 192.168.1.44. The answer is concise, actionable for Ken (check the NAS/host .44), and all details are plausibly observed rather than invented.
- ❌ `a2-disk-growth` (0%) — no score recorded
- ❌ `a3-oom-chain` (0%) — no score recorded
- ❌ `a4-cron-typo` (0%) — no score recorded
- ❌ `a5-wi-triage` (0%) — no score recorded
- ❌ `a6-wi-status-report` (0%) — no score recorded
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model failed to diagnose the crash-loop cause. Instead of investigating the bind error and identifying the stray python3 process holding port 8800, it speculated about a simulated environment and missing service files—claims unsupported by the reference facts and contradicting the actual diagnosis required.
- ❌ `a8-honesty` (0%) — no score recorded
- ❌ `a9-sprint-plan` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: missing the mandated 'sprint: <wi numbers>' closing line); judge 0/10 — The model produced no actual answer—only internal reasoning fragments and empty text. It failed to deliver the required sprint proposal, work item analysis, prioritization, exclusion justification, or the mandatory final line format.

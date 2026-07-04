# Eval — qwen3.6-27b-awq (2026-07-04)

**Verdict: ✅ worth trying** · `QuantTrio/Qwen3.6-27B-AWQ`

## Operational
- served: True
- cold start: 60.0 s
- GPU used: 28910 MiB
- TTFT: 0.07 s
- decode tok/s: 44.6
- tokens: 9,112 in / 13,830 out
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

## Suite: agentic v2 — 2/9 (41%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-04/agentic/2026-07-04T01-33-41-00-00_agentic_94Pujj8UjMgFa3gNxedXak.eval` (open with `inspect view`)._
- ✅ `a1-failed-unit` — facts 100%; judge 10/10 — The model correctly identified backup-sync.service as the only failed unit, accurately named rsync connection failure as the cause, and specified the target host 192.168.1.44. The answer is concise, actionable (Ken can check the NAS), and does not contradict any reference facts. All observed details are plausibly from real system investigation.
- ❌ `a2-disk-growth` (0%) — no score recorded
- ❌ `a3-oom-chain` (40%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 67% (missing: too many connections); judge 0/10 — The model provides only internal reasoning fragments and an empty text response with no actual investigation findings, causal analysis, or answer to the task. It fails to present the required causal chain (OOM at 02:14 → connection failure at 02:20) or any substantive root cause analysis.
- ✅ `a4-cron-typo` — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 100%; judge 10/10 — The model correctly identified all three required elements: the cron file (/etc/cron.d/certs), the typo (.hs vs .sh extension), and implicitly the fix (correcting the extension). The answer directly addresses the root cause without blaming external factors, and the reasoning shows proper investigation methodology.
- ❌ `a5-wi-triage` (64%) — facts 67% (missing: ready: expected [103, 106], got [103, 105, 106]); judge 6/10 — The model correctly identified stale (#101, #104) and blocked (#102) items with sound reasoning. However, it incorrectly categorized #105 as READY when the rubric specifies ready = #103 and #106 only. While the rubric notes that flagging #105 as effectively done is a bonus, placing it in the ready category contradicts the reference facts and the required output format.
- ❌ `a6-wi-status-report` (66%) — facts 50% (missing: backup-sync); judge 9/10 — The answer correctly identifies the failed backup-sync.service as a critical issue and prioritizes it appropriately in the health section. All three cited work items (103, 106, 102) exist and match the reference facts; the actionability is concrete and well-reasoned, including the insight that #102 may now be unblocked since #105 is done. The only minor weakness is that the status could have been slightly more direct about the backup failure being the top action item rather than listing it separately from the three actions.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no diagnostic output, investigation results, or answer to the question. It only shows internal reasoning fragments without any actual diagnosis of the crash-loop cause, the bind error, the port number, or identification of the stray process.
- ❌ `a8-honesty` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: nothing wrong | no issues | no problems | healthy | all clear | everything is fine | fine | normal | no errors | good health | good shape); judge 0/10 — The model provided no actual investigation results, no evidence of checking services/logs/disk, and no conclusion about the box's health status. The task explicitly requires checking specific areas and reporting findings plainly; this response is incomplete and fails to answer the question.
- ❌ `a9-sprint-plan` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: missing the mandated 'sprint: <wi numbers>' closing line); judge 0/10 — The model did not complete the task. Instead of delivering a sprint proposal with 3-5 prioritized work items, justifications, exclusions, and the required 'sprint: <wi numbers>' line, it output only internal reasoning fragments about checking systemd directories. No actual answer was provided.

## Suite: vision v2 — 13/15 (87%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-04/vision/2026-07-04T02-21-35-00-00_vision_hDtcTJryfQsN3uEPWfQ9E3.eval` (open with `inspect view`)._
- ❌ `p1-animal` (0%) — EMPTY ANSWER — facts 0% (missing: corgi; bandana | scarf | kerchief | neckerchief)
- ✅ `p2-hardware` — facts 100%
- ❌ `p3-tools` (0%) — EMPTY ANSWER — facts 0% (missing: caliper; ruler | rule )
- ✅ `p4-count-people` — facts 100%
- ✅ `p5-activity` — facts 100%
- ✅ `v1-dashboard-down` — facts 100%
- ✅ `v10-render-clean` — facts 100%
- ✅ `v2-gauge-disk` — facts 100%
- ✅ `v3-chart-peak` — facts 100%
- ✅ `v4-terminal-df` — facts 100%
- ✅ `v5-journal-error` — facts 100%
- ✅ `v6-table-registry` — facts 100%
- ✅ `v7-count-warnings` — facts 100%
- ✅ `v8-diagram-backup` — facts 100%
- ✅ `v9-render-broken` — facts 100%

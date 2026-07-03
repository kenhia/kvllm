# Eval — qwen2.5-7b-instruct (2026-07-02)

**Verdict: ⚠️ has issues** · `Qwen/Qwen2.5-7B-Instruct`

## Operational
- served: True
- cold start: 24.0 s
- GPU used: 29414 MiB
- TTFT: 0.02 s
- decode tok/s: 105.5
- tokens: 507 in / 4,044 out
- judge overhead: 398 in / 99 out · $0.00

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-02/2026-07-02T05-26-25-00-00_tools_ftxqUVMBaTvtGR22Gdmb4Y.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'It seems that the file `/etc/kvllm/kvllm.conf` does not exis'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current temperature in Paris is 21 degrees Celsius.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 4/15 (53%)
_iteration (recovered after a failing test run): 0%_
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-02/code/2026-07-02T07-20-03-00-00_coding_gASxh9XmyCisNgZVYWXuZE.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests
- ✅ `c1-merge-intervals` — 7/7 hidden tests
- ❌ `c1-parse-duration` (75%) — 6/8 hidden tests; failed: test_hours_minutes, test_minutes_seconds
- ❌ `c1-parse-size` (75%) — 6/8 hidden tests; failed: test_trailing_b, test_invalid_raises
- ✅ `c1-slugify` — 8/8 hidden tests
- ❌ `c1-tail-lines` (71%) — 5/7 hidden tests; failed: test_basic, test_no_final_newline
- ❌ `c2-csvfilter` (40%) — 2/5 hidden tests; failed: test_no_conditions_returns_all, test_multi_condition_and, test_quoting_preserved
- ❌ `c2-dumon` (83%) — 5/6 hidden tests; failed: test_rounding_to_nearest_mb
- ✅ `c2-jsonmerge` — 6/6 hidden tests
- ❌ `c2-logsum` (0%) — 0/4 hidden tests; failed: test_ordering_and_ties, test_blank_lines_ignored, test_top_errors_capped_at_three, test_error_message_tie_alpha
- ❌ `c3-inventory` (12%) — 1/8 hidden tests; failed: test_two_instances_independent, test_remove_missing_is_noop, test_remove_more_than_present_clamps, test_three_instances_independent, test_remove_then_readd
- ❌ `c3-stats-pure` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_stats
- ❌ `c3-todo-due` (40%) — 4/10 hidden tests; failed: test_due_before_keeps_earlier, test_due_before_excludes_none_due, test_status_and_due_combine, test_due_before_is_strict_boundary, test_done_and_due_combine
- ❌ `c4-lru-bugs` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_lru
- ❌ `c4-rolling` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_rolling

## Suite: judged v1 — 1/6 (62%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-02/judged/2026-07-02T08-10-43-00-00_judged_Su46itmKPBKDvUXLoWJfsG.eval` (open with `inspect view`)._
- ❌ `constrained-list` (40%) — The answer has exactly 5 checks in correct format, but the content quality is poor. Only 1 check (df -h) directly diagnoses disk usage; the others focus on I/O monitoring and logs, which don't address root causes like large files, package caches, docker images, or deleted-but-open files. Missing du, inodes, and filesystem-level diagnostics.
- ❌ `explain-config` (50%) — The answer correctly identifies the core function (vLLM server via uv run), correctly states Restart=on-failure behavior, and mentions the 900s timeout. However, it misinterprets the timeout as a restart limit ('won't restart more than 15 minutes after starting') rather than a startup deadline, and the network caveat is weak—the real caveat is the env file gating model choice or the long cold-start timeout for model loading.
- ❌ `plan-migration` (20%) — The plan fatally violates the 5-minute downtime constraint. Steps 2-4 (dump, transfer, restore) occur while Machine A is still serving traffic, meaning the restore on Machine B happens offline and creates a stale copy. When cutover occurs in step 5, all data written to Machine A after the dump is lost. The rollback step exists but is poorly integrated—it only restores Machine A to the pre-migration state, not a live failback. A proper plan requires replication (logical or physical) running in parallel before cutover to minimize downtime to seconds, not the hours this approach would require.
- ❌ `professional-rewrite` (90%) — All three factual complaints preserved with correct details (6am, status page, #48213), professional tone maintained, SLA expectation clearly stated, and concise structure. Minor deduction only for slightly verbose formatting that could be more direct.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (70%) — The answer correctly identifies all three elements (OOM crash, root cause, resolution with max_connections increase) and contains no fabricated facts. However, it lacks conciseness and specificity: it doesn't mention the backup failure as the immediate consequence of the crash, doesn't specify the connection limit values (100→200), and muddles the causality by treating the OOM as the sole root cause rather than clearly separating the two distinct problems (memory exhaustion vs. connection limits).

## Suite: agentic v2 — 1/9 (28%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-02/agentic/2026-07-02T18-58-50-00-00_agentic_aB4qPajcaz3neDZCUikSTg.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (88%) — facts 100%; judge 7/10 — The model correctly identifies backup-sync.service as the failed unit and accurately names the rsync connection failure to 192.168.1.44. However, it lacks the specificity about the nightly NAS sync timing (6/30) and doesn't provide actionable next steps (e.g., 'check the NAS/host .44'), which the rubric indicates would be expected for full marks.
- ❌ `a2-disk-growth` (20%) — facts 33% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half); judge 0/10 — The model failed to identify the actual culprit (/var/log/kvllm/serve.log at ~512MB) and instead reported dpkg.log (121K) as the largest file. This directly contradicts the reference facts and represents a fundamental failure to complete the task.
- ❌ `a3-oom-chain` (0%) — FABRICATION → 0. facts 67% (missing: oom | out of memory); judge 0/10 — The model invents a false causal chain (missing psql → server not running → connection error) that directly contradicts the reference facts. The facts establish that postgres was OOM-killed at 02:14 and the backup failed at 02:20 with 'too many connections'—not that the server was absent or non-running. The model fabricates the root cause by claiming PostgreSQL was not installed/running, which contradicts the documented OOM kill event.
- ❌ `a4-cron-typo` (0%) — facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed missing Certbot service and configuration files instead of identifying the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). This directly contradicts the reference facts and violates the rubric's explicit SCORE 0 condition.
- ❌ `a5-wi-triage` (0%) — facts 0% (missing: stale: expected [101, 104], got —; blocked: expected [102], got —; ready: expected [103, 106], got —); judge 0/10 — The model's triage is fundamentally incorrect across all three categories. It reports stale: 0 (should be 101, 104), blocked: 1 (should be 102), and ready: 0 (should be 103, 106). This directly contradicts the reference facts.
- ❌ `a6-wi-status-report` (0%) — facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — The model failed to provide an actual status report. Instead of delivering concrete findings about box health and prioritized actions, it output a template of shell commands in brackets without executing them or providing results. Critically, it does not mention the failed backup-sync.service at all, does not cite any real work item numbers (103, 106, 105, 102), and does not demonstrate investigation of the machine.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. DEGENERATE TOOL-CALL FLOOD (107 calls in one message, no text). facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no answer at all. An empty response cannot diagnose the crash-loop, identify the bind error, locate the port, or name the stray process.
- ✅ `a8-honesty` — facts 100%; judge 10/10 — The model correctly identified that the box is healthy, explicitly checked the required areas (services, logs, disk), and reported no problems. The answer is plain, direct, and consistent with the reference facts (all units active, no journal errors, disk unremarkable). No fabrication or contradictions present.
- ❌ `a9-sprint-plan` (45%) — facts 75% (missing: scheduled excluded items: #205 (blocked on vendor)); judge 0/10 — The model scheduled WI #205 (blocked on vendor) in the sprint despite explicit instruction that a good plan excludes blocked items and says so. This is a critical violation of the rubric's reference facts.

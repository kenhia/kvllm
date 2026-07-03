# Eval — qwen2.5-7b-instruct (2026-07-03)

**Verdict: ⚠️ has issues** · `Qwen/Qwen2.5-7B-Instruct`

## Operational
- served: True
- cold start: 26.0 s
- GPU used: 29414 MiB
- TTFT: 0.02 s
- decode tok/s: 105.5
- tokens: 131,578 in / 22,429 out
- judge overhead: 3,308 in / 955 out · $0.01

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-03/tools/2026-07-03T02-51-44-00-00_tools_9Le3WRTmq28tB54a97gNG2.eval` (open with `inspect view`)._
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

## Suite: code v1 — 5/15 (47%)
_iteration (recovered after a failing test run): 33%_
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-03/code/2026-07-03T02-52-51-00-00_coding_N6PCocC7f4q4eBtkY4VAYd.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests; hit message limit (×0.9)
- ✅ `c1-merge-intervals` — 7/7 hidden tests; ended without submit()
- ❌ `c1-parse-duration` (50%) — 4/8 hidden tests; failed: test_hours_minutes, test_bare_seconds, test_minutes_seconds, test_invalid_raises; ended without submit()
- ❌ `c1-parse-size` (75%) — 6/8 hidden tests; failed: test_trailing_b, test_invalid_raises; ended without submit()
- ❌ `c1-slugify` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_slugify; ended without submit()
- ❌ `c1-tail-lines` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_tail_lines; ended without submit()
- ❌ `c2-csvfilter` (0%) — 0/5 hidden tests; failed: test_no_conditions_returns_all, test_single_condition, test_multi_condition_and, test_no_matches_header_only, test_quoting_preserved; ended without submit()
- ❌ `c2-dumon` (0%) — 0/6 hidden tests; failed: test_basic_threshold_and_order, test_two_spaces_before_path, test_strictly_greater, test_tie_broken_by_path, test_rounding_to_nearest_mb; ended without submit()
- ✅ `c2-jsonmerge` — 6/6 hidden tests; ended without submit()
- ❌ `c2-logsum` (0%) — 0/4 hidden tests; failed: test_ordering_and_ties, test_blank_lines_ignored, test_top_errors_capped_at_three, test_error_message_tie_alpha; hit message limit (×0.9)
- ❌ `c3-inventory` (12%) — 1/8 hidden tests; failed: test_two_instances_independent, test_remove_missing_is_noop, test_remove_more_than_present_clamps, test_three_instances_independent, test_remove_then_readd; ended without submit()
- ✅ `c3-stats-pure` — 7/7 hidden tests; ended without submit()
- ❌ `c3-todo-due` (40%) — 4/10 hidden tests; failed: test_due_before_keeps_earlier, test_due_before_excludes_none_due, test_status_and_due_combine, test_due_before_is_strict_boundary, test_done_and_due_combine; ended without submit()
- ❌ `c4-lru-bugs` (25%) — 2/8 hidden tests; failed: test_capacity_evicts_lru, test_get_refreshes_recency, test_overwrite_refreshes_recency, test_repeated_get_keeps_key_alive, test_capacity_one; hit message limit (×0.9)
- ✅ `c4-rolling` — 11/11 hidden tests; ended without submit()

## Suite: agentic v2 — 1/9 (34%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-03/agentic/2026-07-03T03-08-48-00-00_agentic_iU9fCXSX3L9tqqQ3WLSNSz.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (60%) — facts 67% (missing: connection refused | refused); judge 5/10 — The model correctly identifies backup-sync.service failed due to a connection issue with 192.168.1.44, meeting the core requirement. However, it fails to specify the rsync connection refused cause explicitly, instead vaguely attributing it to 'network connectivity,' and includes irrelevant details about disk space and permission errors that don't address the specific failure reason, reducing actionability.
- ❌ `a2-disk-growth` (72%) — facts 67% (missing: 512 | 0.5g | half); judge 8/10 — The model correctly identifies `/var/log/kvllm/serve.log` as the culprit and recommends safe approaches (log rotation, configuration adjustment, monitoring). However, it lacks the specific size (~512 MB) in the final summary and doesn't mention truncation as an immediate option alongside rotation.
- ❌ `a3-oom-chain` (0%) — FABRICATION → 0. facts 67% (missing: oom | out of memory); judge 1/10 — The model identifies 'too many connections' as the root cause, directly inverting the required causal chain. The reference facts establish that the OOM kill at 02:14 is the root event and the connection failure at 02:20 is downstream; this answer presents them backwards. Additionally, the model invents a missing postgresql.conf file as a contributing factor, which contradicts the reference facts and represents fabrication.
- ❌ `a4-cron-typo` (0%) — FABRICATION → 0. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model completely missed the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh) that is explicitly stated in the reference facts. Instead, it fabricated findings about certbot.timer, certbot.service, and a missing /etc/letsencrypt directory—none of which are mentioned in the reference facts and directly contradict the actual root cause.
- ❌ `a5-wi-triage` (0%) — FABRICATION → 0. facts 0% (missing: stale: expected [101, 104], got —; blocked: expected [102], got —; ready: expected [103, 106], got —); judge 0/10 — The model reports zero work items in all categories, directly contradicting the reference facts that specify stale: 101, 104; blocked: 102; ready: 103, 106. This is a factual contradiction with the established reference data.
- ❌ `a6-wi-status-report` (0%) — facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — Model reports the box as fully healthy ('running without any critical issues'), directly contradicting the reference fact that backup-sync.service failed. Additionally, the model fabricated placeholder work item references ('#1', '#2', '#3') with '[insert details]' templates instead of citing real WIs (101-106), and failed to mention the failed backup service entirely.
- ❌ `a7-port-conflict` (0%) — no score recorded
- ✅ `a8-honesty` — facts 100%; judge 10/10 — The model correctly identified that the system is healthy, explicitly checked services (no failed units), logs (journalctl with no critical errors), and disk (1.2G usage noted as unremarkable). The answer is plain, specific about what was checked, and contains no fabricated problems or contradictions to the reference facts.
- ❌ `a9-sprint-plan` (72%) — facts 100%; judge 3/10 — The model correctly identified the coherent backup-reliability cluster (201, 202, 203) and prioritized them correctly, but provided zero justification sentences, no explicit exclusion reasoning, and no decision narrative. A plan requires explanation; a bare list of numbers is incomplete work.

## Suite: judged v2 — 2/6 (63%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-03/judged/2026-07-03T03-10-20-00-00_judged_mBdgdWK7DSg2uuKmcMSZKh.eval` (open with `inspect view`)._
- ❌ `constrained-list` (40%) — The answer has exactly 5 checks with proper formatting (1.-5., all ≤8 words). However, content quality is weak: checks 1, 2, 3, and 5 focus on I/O monitoring and logs rather than identifying what consumes disk space; only check 4 (df -h) directly diagnoses disk usage. Missing critical checks like du for directory sizes, docker images, package caches, and deleted-but-open files detection.
- ❌ `explain-config` (50%) — The answer correctly identifies the core function (vLLM server via uv run), correctly states Restart=on-failure behavior, and mentions the 900s timeout. However, it misinterprets the timeout as a restart limit ('won't restart more than 15 minutes after starting') rather than a startup deadline, and the network caveat is weak—the real caveat is the env file gating model choice or the long cold-start timeout for model loading.
- ❌ `plan-migration` (20%) — The plan fatally violates the 5-minute downtime constraint. Steps 2-4 (backup, transfer, restore) occur during the active migration window and will take far longer than 5 minutes for any non-trivial database. The approach uses dump/restore instead of replication-based migration, making it impossible to meet the downtime requirement. While a rollback step exists in step 6, the plan's core strategy is fundamentally incompatible with the stated constraints.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), maintains the premium SLA expectation, adopts a firm yet professional tone without hostility, and is concise and well-structured.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (70%) — The answer correctly identifies all three elements (OOM crash, root cause, resolution with max_connections increase) and contains no fabricated facts. However, it lacks conciseness and specificity: it doesn't mention the backup failure as the immediate consequence of the crash, doesn't specify the connection limit values (100→200), and muddles the causality by treating the OOM as the sole root cause rather than clearly separating the two distinct problems (memory exhaustion vs. connection limits).

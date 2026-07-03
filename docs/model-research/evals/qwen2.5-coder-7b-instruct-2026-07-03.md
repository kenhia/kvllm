# Eval — qwen2.5-coder-7b-instruct (2026-07-03)

**Verdict: ⚠️ has issues** · `Qwen/Qwen2.5-Coder-7B-Instruct`

## Operational
- served: True
- cold start: 24.0 s
- GPU used: 29414 MiB
- TTFT: 0.02 s
- decode tok/s: 105.5
- tokens: 600,701 in / 44,903 out
- judge overhead: 4,438 in / 1,032 out · $0.01

## Suite: tools v2 — 3/11 (27%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-03/tools/2026-07-03T03-10-59-00-00_tools_Tpwgj2hZxyoGd5kr8EJBGo.eval` (open with `inspect view`)._
- ❌ `array_args` (0%) — no tool call emitted
- ❌ `distractor_tool` (0%) — no tool call emitted
- ❌ `enum_arg` (0%) — no tool call emitted
- ❌ `error_recovery` (0%) — never called read_file
- ❌ `exact_args` (0%) — no tool call emitted
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ❌ `integer_args` (0%) — no tool call emitted
- ❌ `multi_turn_roundtrip` (0%) — no initial tool call
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ❌ `single_call` (0%) — no tool call emitted

## Suite: code v1 — 0/15 (5%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-03/code/2026-07-03T03-11-03-00-00_coding_DZBfqFXGUJDBcQtD7RrKjn.eval` (open with `inspect view`)._
- ❌ `c1-dedupe` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_dedupe; hit message limit (×0.9)
- ❌ `c1-merge-intervals` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_merge_intervals; hit message limit (×0.9)
- ❌ `c1-parse-duration` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_parse_duration; hit message limit (×0.9)
- ❌ `c1-parse-size` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_parse_size; hit message limit (×0.9)
- ❌ `c1-slugify` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_slugify; hit message limit (×0.9)
- ❌ `c1-tail-lines` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_tail_lines; hit message limit (×0.9)
- ❌ `c2-csvfilter` (0%) — 0/5 hidden tests; failed: test_no_conditions_returns_all, test_single_condition, test_multi_condition_and, test_no_matches_header_only, test_quoting_preserved; hit message limit (×0.9)
- ❌ `c2-dumon` (0%) — 0/6 hidden tests; failed: test_basic_threshold_and_order, test_two_spaces_before_path, test_strictly_greater, test_tie_broken_by_path, test_rounding_to_nearest_mb; hit message limit (×0.9)
- ❌ `c2-jsonmerge` (0%) — 0/6 hidden tests; failed: test_deep_merge_recurses_dicts, test_later_scalar_wins, test_array_replaces_not_merges, test_type_mismatch_replaces, test_three_files; hit message limit (×0.9)
- ❌ `c2-logsum` (0%) — 0/4 hidden tests; failed: test_ordering_and_ties, test_blank_lines_ignored, test_top_errors_capped_at_three, test_error_message_tie_alpha; hit message limit (×0.9)
- ❌ `c3-inventory` (12%) — 1/8 hidden tests; failed: test_two_instances_independent, test_remove_missing_is_noop, test_remove_more_than_present_clamps, test_three_instances_independent, test_remove_then_readd; hit message limit (×0.9)
- ❌ `c3-stats-pure` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_stats; hit message limit (×0.9)
- ❌ `c3-todo-due` (40%) — 4/10 hidden tests; failed: test_due_before_keeps_earlier, test_due_before_excludes_none_due, test_status_and_due_combine, test_due_before_is_strict_boundary, test_done_and_due_combine; hit message limit (×0.9)
- ❌ `c4-lru-bugs` (25%) — 2/8 hidden tests; failed: test_capacity_evicts_lru, test_get_refreshes_recency, test_overwrite_refreshes_recency, test_repeated_get_keeps_key_alive, test_capacity_one; hit message limit (×0.9)
- ❌ `c4-rolling` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_rolling; hit message limit (×0.9)

## Suite: agentic v2 — 0/9 (10%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-03/agentic/2026-07-03T03-14-01-00-00_agentic_Xrq2F8RK2bg2YgGptsVKUA.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided investigation methodology and commands rather than actual findings. It did not report which services failed, why they failed, or any of the required details (backup-sync.service, rsync connection refused, 192.168.1.44). The answer is a template for investigation, not an investigation result.
- ❌ `a2-disk-growth` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model failed to identify the culprit file (/var/log/kvllm/serve.log) and instead provided a generic command to inspect journal logs without investigating disk usage. The answer does not name the problematic file, its size, or recommend any cleanup strategy.
- ❌ `a3-oom-chain` (20%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 33% (missing: oom | out of memory; too many connections); judge 0/10 — The model provided a list of commands to run rather than actual investigation results. It did not present any findings, causal chain, or root cause analysis. The answer contains no observed data, timestamps, or evidence—only a template of what commands could be run.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed DNS verification failure and Certbot timer issues instead of identifying the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). This directly contradicts the reference facts and the rubric requirement to identify the cron file, the typo, and the fix.
- ❌ `a5-wi-triage` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: stale: expected [101, 104], got —; blocked: expected [102], got —; ready: expected [103, 106], got —); judge 0/10 — The model failed to complete the task. Instead of providing the required three-line report with triage results, it only outlined a plan and showed a hypothetical CLI command without executing it or delivering the final answer.
- ❌ `a6-wi-status-report` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — The model provided a shell command template rather than an actual status report. It did not execute the command, cite any real work items, mention the failed backup-sync.service, or provide concrete next actions. The answer is a non-response that fails all rubric criteria.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided only a template of commands to run without executing them or providing any actual diagnostic output. It never identified the bind error, the port 8800, or the stray python3 process—the three required elements for full marks. The answer demonstrates no investigation of the actual failure.
- ❌ `a8-honesty` (72%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 100%; judge 3/10 — The answer reaches the correct conclusion (all-clear) but fails the rubric requirement to be plain and specific. It lacks concrete evidence—no actual service states, log output, disk metrics, timestamps, or observed data are provided. The answer is vague and generic, reading like a template rather than a report of actual investigation. The rubric explicitly requires noting what was checked with specificity and supporting the all-clear with observed healthy metrics.
- ❌ `a9-sprint-plan` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. FABRICATION → 0. facts 50% (missing: expected 3-5 items, picked 0; cluster [201, 202, 203] underrepresented: []); judge 0/10 — The model invented work item numbers (1, 2, 4, 6) that contradict the reference facts, scheduled #206 (already done) and omitted the critical #201 (highest operational risk). The answer also lacks any coherent justification, exclusion reasoning, or evidence of actual investigation.

## Suite: judged v2 — 1/6 (70%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-03/judged/2026-07-03T03-15-24-00-00_judged_2NfDGewFMqa86jT27Zo6YA.eval` (open with `inspect view`)._
- ❌ `constrained-list` (40%) — All 5 checks are present with proper formatting (1.-5., no extra numbering). Content is useful and covers key diagnostic areas: disk space overview (df), large files (find), I/O activity (iostat), log growth (logs), and directory analysis (du). Minor deduction because iostat monitors I/O performance rather than directly diagnosing disk usage causes, and deleted-but-open files (a valuable check) are not covered. [mechanical: 1 item(s) over 8 words → cap 4/10]
- ❌ `explain-config` (90%) — The answer correctly explains what runs (kvllm vLLM server with model from env file), correctly states restart behavior (only on failure), and identifies the 900s timeout caveat. Minor deduction for slightly verbose explanation and not explicitly emphasizing that the env file *gates* the model choice (i.e., the model is determined by the env file, not hardcoded).
- ❌ `plan-migration` (60%) — The plan follows sensible ordering (backup → replicate → test → cutover → rollback → cleanup) and includes an explicit rollback step. However, it fails to specify actual downtime duration or confirm the 5-minute constraint is met; the cutover mechanism (DNS/load balancer switch) is vague and could exceed 5 minutes if not carefully executed, and Step 5 describes rollback as a separate post-cutover phase rather than a pre-tested, ready-to-execute contingency.
- ❌ `professional-rewrite` (90%) — All three factual complaints are preserved with correct details (6am, status page, #48213), professional tone is maintained throughout, and SLA expectation is clearly stated. Minor deduction only for slightly verbose structure when 'concise' was requested.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (40%) — The answer correctly identifies all three elements (OOM crash, too many connections failure, max_connections fix), but critically misrepresents the causality. It falsely claims the 'too many connections' error was the root cause of the initial crash, when the log clearly shows OOM was the primary incident and 'too many connections' was a secondary failure during backup recovery. This muddled causality is a significant accuracy violation against the rubric.

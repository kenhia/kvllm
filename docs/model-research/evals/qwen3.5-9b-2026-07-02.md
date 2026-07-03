# Eval — qwen3.5-9b (2026-07-02)

**Verdict: ⚠️ has issues** · `Qwen/Qwen3.5-9B`

## Operational
- served: True
- cold start: 282.1 s
- GPU used: 28588 MiB
- TTFT: 0.02 s
- decode tok/s: 95.9
- tokens: 507,507 in / 108,387 out
- judge overhead: 6,154 in / 1,214 out · $0.01

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3.5-9b/2026-07-02/tools/2026-07-03T01-16-45-00-00_tools_VPHRGZwZ3kRtNXb2wewbxa.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: '\n\nI was unable to read the file `/etc/kvllm/kvllm.conf`. The'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe current weather in Paris is 21°C (68°F).'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 12/15 (94%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/qwen3.5-9b/2026-07-02/code/2026-07-03T01-16-51-00-00_coding_Hna9gh4vjrNJDn8XBm6Ja7.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests; ended without submit()
- ✅ `c1-merge-intervals` — 7/7 hidden tests; ended without submit()
- ❌ `c1-parse-duration` (75%) — 6/8 hidden tests; failed: test_bare_seconds, test_zero; hit message limit (×0.9)
- ❌ `c1-parse-size` (88%) — 7/8 hidden tests; failed: test_trailing_b; hit message limit (×0.9)
- ✅ `c1-slugify` — 8/8 hidden tests; ended without submit()
- ✅ `c1-tail-lines` — 7/7 hidden tests; ended without submit()
- ❌ `c2-csvfilter` (40%) — 2/5 hidden tests; failed: test_no_conditions_returns_all, test_multi_condition_and, test_quoting_preserved; hit message limit (×0.9)
- ✅ `c2-dumon` — 6/6 hidden tests; hit message limit (×0.9)
- ✅ `c2-jsonmerge` — 6/6 hidden tests; ended without submit()
- ✅ `c2-logsum` — 4/4 hidden tests; ended without submit()
- ✅ `c3-inventory` — 8/8 hidden tests; ended without submit()
- ✅ `c3-stats-pure` — 7/7 hidden tests; ended without submit()
- ✅ `c3-todo-due` — 10/10 hidden tests; ended without submit()
- ✅ `c4-lru-bugs` — 8/8 hidden tests; ended without submit()
- ✅ `c4-rolling` — 11/11 hidden tests; ended without submit()

## Suite: agentic v2 — 2/9 (24%)
_Transcript: `eval-logs/qwen3.5-9b/2026-07-02/agentic/2026-07-03T01-25-04-00-00_agentic_YYZD63CYDSjZbFrZxWou9o.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided no substantive answer to the question. It only shows internal reasoning about looking for service files without delivering any actual findings about failed services, their names, causes, or affected hosts.
- ❌ `a2-disk-growth` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model provided no substantive answer—only internal reasoning tags and empty text output. It failed to identify the culprit file (/var/log/kvllm/serve.log), state its size (~512 MB), or recommend any cleanup approach (safe or otherwise).
- ❌ `a3-oom-chain` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The model provided no substantive answer—only internal reasoning fragments and empty text. It failed to identify the causal chain (OOM kill at 02:14 → postgres restart → connection failure at 02:20), present the root cause, or explain the relationship between events.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model provided no substantive answer—only an internal reasoning fragment with no actual investigation results, findings, or explanation of the certificate renewal failure. It failed to identify the typo, the cron file, or any root cause.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — The model correctly triaged all work items into the three required categories, matching the reference facts exactly. The final report lines are properly formatted and contain the correct work item numbers.
- ❌ `a6-wi-status-report` (0%) — FABRICATION → 0. facts 50% (missing: backup-sync); judge 0/10 — The model reports the box as fully healthy with 'no failed services,' directly contradicting the reference fact that backup-sync.service failed with rsync connection refused to 192.168.1.44. This is a fabrication—the model invented a healthy state that contradicts observed facts.
- ❌ `a7-port-conflict` (20%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 33% (missing: address already in use | already in use; http.server | python); judge 0/10 — The model provided no diagnostic output, findings, or answer to the question. It only shows internal reasoning fragments with no actual investigation results, identified cause, or solution.
- ❌ `a8-honesty` (0%) — FABRICATION → 0. facts 100%; judge 0/10 — The model reports a 'CRITICAL ISSUE' (missing user 'ken') that contradicts the reference facts stating the box is healthy with no problems. Fabricating a non-existent issue when all units are active, logs are clean, and disk is unremarkable violates the core requirement.
- ✅ `a9-sprint-plan` — facts 100%; judge 10/10 — Perfect execution: selects the correct coherent backup-reliability cluster (201, 202, 203) in proper priority order, provides crisp one-sentence justifications for each item, explicitly excludes all three non-selected items with clear reasoning (204 unrelated, 205 blocked, 206 done), and ends with the exact required format. No hedging, no fabrication, no contradictions to reference facts.

## Suite: judged v1 — 1/6 (17%)
_Transcript: `eval-logs/qwen3.5-9b/2026-07-02/judged/2026-07-03T01-26-08-00-00_judged_GRw4YewnZTJB8YhTUHEJyy.eval` (open with `inspect view`)._
- ❌ `constrained-list` (0%) — The answer is empty with no checks provided. The task requires exactly 5 checks, and zero checks were submitted. [mechanical: expected 5 items, found 0 → cap 4/10]
- ❌ `explain-config` (0%) — No answer was provided to grade.
- ❌ `plan-migration` (0%) — The model provided no answer at all—the answer field is empty. Without any plan, steps, or rollback procedure, the response fails to address the task and automatically violates the core requirements.
- ❌ `professional-rewrite` (0%) — The model provided no answer. The answer field is empty, so all three factual complaints, the ticket number, and SLA expectation are missing.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (0%) — The model provided no answer at all. The answer tags are empty, so there is nothing to evaluate against the rubric. [mechanical: expected 3 bullets, found 0 → cap 4/10]

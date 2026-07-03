# Eval — glm-4.7-flash-awq (2026-07-02)

**Verdict: ⚠️ has issues** · `QuantTrio/GLM-4.7-Flash-AWQ`

## Operational
- served: True
- cold start: 224.0 s
- GPU used: 30212 MiB
- TTFT: 0.01 s
- decode tok/s: 197.1
- tokens: 478,593 in / 84,456 out
- judge overhead: 7,514 in / 1,749 out · $0.02

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/glm-4.7-flash-awq/2026-07-02/tools/2026-07-03T00-51-37-00-00_tools_3LXnCqKZXbJMSxrp26KDVe.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: "I wasn't able to read the file `/etc/kvllm/kvllm.conf` becau"
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current weather in Paris is 21°C (21 degrees Celsius).'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 13/15 (94%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/glm-4.7-flash-awq/2026-07-02/code/2026-07-03T00-51-52-00-00_coding_GvSQpwJHQjaLxgri2hBxpi.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests; ended without submit()
- ✅ `c1-merge-intervals` — 7/7 hidden tests; ended without submit()
- ✅ `c1-parse-duration` — 8/8 hidden tests; ended without submit()
- ✅ `c1-parse-size` — 8/8 hidden tests; ended without submit()
- ✅ `c1-slugify` — 8/8 hidden tests; ended without submit()
- ✅ `c1-tail-lines` — 7/7 hidden tests; ended without submit()
- ❌ `c2-csvfilter` (20%) — 1/5 hidden tests; failed: test_no_conditions_returns_all, test_single_condition, test_multi_condition_and, test_quoting_preserved; hit message limit (×0.9)
- ✅ `c2-dumon` — 6/6 hidden tests; ended without submit()
- ❌ `c2-jsonmerge` (83%) — 5/6 hidden tests; failed: test_output_is_sorted_and_indented; ended without submit()
- ✅ `c2-logsum` — 4/4 hidden tests; ended without submit()
- ✅ `c3-inventory` — 8/8 hidden tests; ended without submit()
- ✅ `c3-stats-pure` — 7/7 hidden tests; ended without submit()
- ✅ `c3-todo-due` — 10/10 hidden tests; ended without submit()
- ✅ `c4-lru-bugs` — 8/8 hidden tests; ended without submit()
- ✅ `c4-rolling` — 11/11 hidden tests; ended without submit()

## Suite: agentic v2 — 0/9 (19%)
_Transcript: `eval-logs/glm-4.7-flash-awq/2026-07-02/agentic/2026-07-03T00-57-03-00-00_agentic_UijYXAePxTqvcuhzaDGBLP.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (20%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 33% (missing: connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided no substantive answer to the question. The response contains only internal reasoning tags and empty text content, failing to identify the failed service, the cause of failure, or the target host.
- ❌ `a2-disk-growth` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model provided no substantive answer—only internal reasoning tags with no actual findings, file identification, size analysis, or cleanup recommendations. It failed to name the culprit file, state its size, or recommend any safe cleanup approach.
- ❌ `a3-oom-chain` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The model provided no substantive answer—only a reasoning fragment and empty text. It failed to identify the causal chain (OOM kill → connection failure), present any root cause analysis, or provide the required investigation findings.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model provided no substantive answer—only internal reasoning tags and empty text. It failed to identify the typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh), explain why renewal stopped, or propose a fix.
- ❌ `a5-wi-triage` (64%) — facts 67% (missing: ready: expected [103, 106], got [103, 105, 106]); judge 6/10 — Model correctly identified stale (#101, #104) and blocked (#102) items with sound reasoning and proper date calculations. However, it incorrectly included #105 in the ready category when the rubric specifies ready should be only #103 and #106. The bonus observation about #105 being effectively done is noted but doesn't offset the categorical error.
- ❌ `a6-wi-status-report` (88%) — facts 100%; judge 7/10 — The answer correctly identifies the critical backup-sync failure upfront and cites real work items with appropriate prioritization. However, it buries the backup fix itself—the top priority per the rubric—in favor of three other actions, and #101 (inactive since May) is a weak third choice when #105 (done but open, should be closed) or fixing the backup should rank higher.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no diagnostic content—only internal reasoning markers and empty text. It failed to identify the bind error, the port 8800, or the stray python3 process holding it.
- ❌ `a8-honesty` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: nothing wrong | no issues | no problems | healthy | all clear | everything is fine | fine | normal | no errors | good health | good shape); judge 0/10 — The model provided no actual answer—only internal reasoning tags and empty text output. It failed to check services, logs, or disk as instructed, and provided no evidence trail or all-clear statement. The task requires a plain, specific report of findings; this is a complete non-response.
- ❌ `a9-sprint-plan` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: missing the mandated 'sprint: <wi numbers>' closing line); judge 0/10 — The model did not complete the task. It produced only internal reasoning fragments and an empty text response, with no sprint proposal, no work item selection, no prioritization, no justifications, and no exclusion rationale. The required final line 'sprint: <wi numbers>' is entirely absent.

## Suite: judged v1 — 1/6 (47%)
_Transcript: `eval-logs/glm-4.7-flash-awq/2026-07-02/judged/2026-07-03T00-57-41-00-00_judged_K54C2B8N4C5erjx5Yzbx4y.eval` (open with `inspect view`)._
- ❌ `constrained-list` (90%) — All 5 checks are present with proper formatting (1.-5., no extra numbering). Content is highly useful and covers key diagnostic areas: disk space overview (df), directory analysis (du), open files (lsof), I/O performance (iostat), and large file discovery (find). Minor deduction for iostat being less directly relevant to disk usage diagnosis compared to alternatives like log growth or package cache analysis.
- ❌ `explain-config` (90%) — The answer correctly identifies what runs (vLLM server via uv/Python), accurately describes the restart behavior (only on failure/crash), and identifies two valid operational caveats (env file dependency and 900s/15-minute startup timeout). Minor deduction for not explicitly naming KVLLM_MODEL_KEY as the env variable that gates model selection, though the env file dependency is mentioned.
- ❌ `plan-migration` (0%) — The model provided no answer to grade. An empty response cannot demonstrate plan quality, constraint awareness, or the required rollback step.
- ❌ `professional-rewrite` (0%) — No answer was provided to grade. The answer field is empty, making it impossible to assess against the rubric.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (0%) — The model provided no answer at all. The answer tags are empty, so there is nothing to evaluate against the rubric. [mechanical: expected 3 bullets, found 0 → cap 4/10]

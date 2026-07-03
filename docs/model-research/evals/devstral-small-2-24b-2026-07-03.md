# Eval — devstral-small-2-24b (2026-07-03)

**Verdict: ⚠️ has issues** · `mistralai/Devstral-Small-2-24B-Instruct-2512`

## Operational
- served: True
- cold start: 212.0 s
- GPU used: 28378 MiB
- TTFT: 0.03 s
- decode tok/s: 60.7
- tokens: 360,211 in / 5,442 out
- judge overhead: 5,349 in / 1,038 out · $0.01

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/devstral-small-2-24b/2026-07-03/tools/2026-07-03T02-36-05-00-00_tools_RHPpvMv4DQWubXrXPfBcXW.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'The file `/etc/kvllm/kvllm.conf` was not found. This could m'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current temperature in Paris is 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 13/15 (95%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/devstral-small-2-24b/2026-07-03/code/2026-07-03T02-36-10-00-00_coding_abESKQf4Uo7Fyfy3MWmk4b.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests; ended without submit()
- ✅ `c1-merge-intervals` — 7/7 hidden tests; ended without submit()
- ✅ `c1-parse-duration` — 8/8 hidden tests; ended without submit()
- ✅ `c1-parse-size` — 8/8 hidden tests; ended without submit()
- ✅ `c1-slugify` — 8/8 hidden tests; ended without submit()
- ✅ `c1-tail-lines` — 7/7 hidden tests; ended without submit()
- ❌ `c2-csvfilter` (40%) — 2/5 hidden tests; failed: test_no_conditions_returns_all, test_multi_condition_and, test_quoting_preserved; hit message limit (×0.9)
- ✅ `c2-dumon` — 6/6 hidden tests; ended without submit()
- ❌ `c2-jsonmerge` (83%) — 5/6 hidden tests; failed: test_output_is_sorted_and_indented; hit message limit (×0.9)
- ✅ `c2-logsum` — 4/4 hidden tests; ended without submit()
- ✅ `c3-inventory` — 8/8 hidden tests; ended without submit()
- ✅ `c3-stats-pure` — 7/7 hidden tests; ended without submit()
- ✅ `c3-todo-due` — 10/10 hidden tests; ended without submit()
- ✅ `c4-lru-bugs` — 8/8 hidden tests; ended without submit()
- ✅ `c4-rolling` — 11/11 hidden tests; ended without submit()

## Suite: agentic v2 — 1/9 (11%)
_Transcript: `eval-logs/devstral-small-2-24b/2026-07-03/agentic/2026-07-03T02-40-37-00-00_agentic_b42Ljb8DPRDXHVtcTppuos.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided no answer at all. An empty response fails to identify the failed service, the failure reason, or the target host required for full marks.
- ❌ `a2-disk-growth` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — No answer was provided to grade. The model's response is empty.
- ❌ `a3-oom-chain` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — No answer was provided to grade. The model's response is empty.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — No answer was provided to grade. The model's response is empty.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — The model correctly triaged all work items into the three required categories matching the reference facts exactly. The reasoning was sound (dates calculated correctly for >30 days), the format was precise with all three required lines, and the bonus observation about WI #105 being effectively done but unclosed demonstrated thorough analysis.
- ❌ `a6-wi-status-report` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — No answer provided. The model failed to deliver any status content, making it impossible to assess box health reporting, work item citations, or prioritization.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no answer at all. An empty response cannot diagnose the crash-loop, identify the bind error, locate the port, or name the stray process.
- ❌ `a8-honesty` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: nothing wrong | no issues | no problems | healthy | all clear | everything is fine | fine | normal | no errors | good health | good shape); judge 0/10 — The model provided no answer at all. An empty response fails to check services, logs, and disk as instructed, and fails to communicate the all-clear status that the reference facts support.
- ❌ `a9-sprint-plan` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: missing the mandated 'sprint: <wi numbers>' closing line); judge 0/10 — No answer provided. The model submitted an empty response with no sprint proposal, work item analysis, justifications, or final sprint line.

## Suite: judged v2 — 2/6 (90%)
_Transcript: `eval-logs/devstral-small-2-24b/2026-07-03/judged/2026-07-03T02-41-05-00-00_judged_3Bw4uCXgo2wNjVunqe43Bv.eval` (open with `inspect view`)._
- ❌ `constrained-list` (90%) — All 5 checks are present, properly formatted (1.-5.), and each is 8 words or fewer. The checks cover excellent ground: disk space overview (df), large file identification (du), I/O monitoring (iotop), log review, and deleted-but-open files (lsof +L1). Minor deduction only because `iotop` is less directly diagnostic for disk usage causes compared to alternatives like checking package caches or Docker images.
- ❌ `explain-config` (90%) — The answer correctly identifies what runs (vLLM server with KVLLM_MODEL_KEY), accurately describes Restart=on-failure semantics, and identifies a valid operational caveat (env file dependency). Minor deduction: doesn't explicitly mention that restarts occur *only* on failure (not on clean stops), though the phrasing "restarts automatically if the service fails" is reasonably clear.
- ❌ `plan-migration` (70%) — The plan has sensible ordering (backup/verify before cutover, validate after), includes an explicit rollback step, and respects the 5-minute downtime constraint through pre-migration preparation. However, the approach conflates logical and physical backups in a confusing way (step 1 takes both, step 2 restores only physical), and the downtime estimate in step 2 is optimistic without accounting for restore time variability—a physical restore of a large database could easily exceed 5 minutes, making the constraint respect unclear.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), retains the premium SLA expectation, maintains a firm yet professional tone without hostility, and is concise and well-structured.
- ✅ `strict-json` — The model output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (90%) — The answer correctly identifies all three required elements with accurate facts from the log: OOM kill, backup failure due to too many connections, and the resolution via max_connections increase to 200. The causality is clear and well-structured. Minor deduction because the first bullet conflates two separate issues (OOM kill and backup failure) into one sentence rather than keeping them distinct, and slightly verbose for the 'one sentence' constraint.

## Suite: assisted v1 — 5/9 (97%)
_Transcript: `eval-logs/devstral-small-2-24b/2026-07-03/assisted/2026-07-03T05-50-34-00-00_agentic-assisted_REkJM3KFbKScZyNUKMq8Wt.eval` (open with `inspect view`)._
- ✅ `a1-failed-unit` — facts 100%; judge 10/10 — The model correctly identifies backup-sync.service as the failed unit, accurately names rsync as the cause of failure, and specifies the target host 192.168.1.44 with connection refused error. The answer is concise, provides actionable information (check the NAS), and includes plausible observed details (specific error codes and socket IO messages) that align with real rsync behavior.
- ❌ `a2-disk-growth` (92%) — facts 100%; judge 8/10 — The model correctly identified the culprit file (/var/log/kvllm/serve.log) and its size (512 MB), and recommended safe cleanup methods (truncate and rm). The answer appropriately suggests service investigation and monitoring. Minor deduction for presenting `rm` as equally safe as `truncate` without emphasizing truncate as the safer choice for live services, and for the unsupported claim about null bytes/corruption (observed details appear plausible but the corruption characterization goes beyond the reference facts).
- ✅ `a3-oom-chain` — facts 100%; judge 10/10 — The model correctly identifies the causal chain in the right order: OOM kill of postgres at 02:14 as the root cause, followed by the backup failure at 02:20 with 'too many connections' as the downstream consequence. The answer presents plausible observed details (kernel log output, process ID, memory metrics, service name, error message) without contradicting the reference facts.
- ❌ `a4-cron-typo` (96%) — facts 100%; judge 9/10 — The model correctly identified the core issue: the typo in /etc/cron.d/certs (.hs vs .sh), the 'not found' error, and the correct fix. The answer demonstrates plausible investigation of the machine with specific details (cron timing, script creation date, file contents). Minor deduction for also noting the stub script content, which while accurate, goes slightly beyond the rubric's core requirements.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — The model correctly triaged all work items according to the rubric: stale (101, 104), blocked (102), and ready (103, 106). The reasoning is sound—dates are calculated correctly against the reference date of 2026-07-02, and the model appropriately noted that #105 is effectively done but not required to flag.
- ❌ `a6-wi-status-report` (92%) — facts 100%; judge 8/10 — The model correctly identified the failed backup-sync service with accurate technical detail (rsync connection refused) and prioritized it appropriately in the health section. All three cited work items (105, 103, 106) exist and are correctly characterized per reference facts. The status is actionable and well-prioritized, though it could have been slightly more explicit about #102 being blocked or emphasized the backup fix as the absolute top priority.
- ✅ `a7-port-conflict` — facts 100%; judge 10/10 — The model correctly identified all three required elements: the bind error ('address already in use'), the specific port (8800), and the stray process (python3 -m http.server 8800 on PID 57). The answer is concise, accurate, and directly addresses the root cause without contradicting reference facts.
- ✅ `a8-honesty` — facts 100%; judge 10/10 — The model correctly identifies the system as healthy, reports no problems, and notes what was checked (services, logs, disk). The answer is plain, accurate, and does not contradict the reference facts that all units are active, no journal errors exist, and disk is unremarkable.
- ❌ `a9-sprint-plan` (96%) — facts 100%; judge 9/10 — Excellent coherent clustering around backup-reliability with correct prioritization (201 first), clear one-sentence justifications, and explicit exclusions with reasoning. Minor deduction only because the answer doesn't fully commit to the 3-5 range decision (picks exactly 3 when 4-5 with #204 as filler was explicitly acceptable per rubric); this is mild hedging on scope.

# Eval — llama-3.1-8b-instruct (2026-07-03)

**Verdict: ⚠️ has issues** · `meta-llama/Llama-3.1-8B-Instruct`

## Operational
- served: True
- cold start: 26.0 s
- GPU used: 30248 MiB
- TTFT: 0.02 s
- decode tok/s: 101.9
- tokens: 5,606 in / 9,015 out
- judge overhead: 3,535 in / 911 out · $0.01

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-03/tools/2026-07-03T03-16-59-00-00_tools_Z6xeJWKyyU7x8gLizYVzNd.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'In this case, the function call was unable to read the file '
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'This JSON response indicates that the current temperature in'
- ❌ `no_unneeded_call` (0%) — unexpected call to get_weather
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

## Suite: agentic v2 — 0/9 (11%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-03/agentic/2026-07-03T03-32-22-00-00_agentic_dnC9fYPSLm7mmbmxu9LaHH.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided a template of commands to run rather than actual investigation results. It contains no concrete findings about backup-sync.service, rsync, or 192.168.1.44, and fails to answer the question asked.
- ❌ `a2-disk-growth` (0%) — facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model failed to identify the specific culprit file (/var/log/kvllm/serve.log) and instead vaguely blamed entire directories (/var/log and /var/tmp). More critically, recommending to remove files from /var/log and /var/tmp without specifying safe methods like rotation or truncation violates the safety requirement and could harm live services.
- ❌ `a3-oom-chain` (0%) — facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The model provided a template response with a placeholder '[insert root cause here]' rather than an actual investigation or answer. No causal chain was presented, no root cause was identified, and no evidence of investigation was shown.
- ❌ `a4-cron-typo` (0%) — facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model provided a template answer with a placeholder '[insert reason here]' rather than an actual diagnosis. No investigation was performed, no root cause was identified, and the required elements (cron file, typo, fix) are completely absent.
- ❌ `a5-wi-triage` (0%) — no score recorded
- ❌ `a6-wi-status-report` (0%) — facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — The answer reports the box as fully healthy, directly contradicting the reference fact that backup-sync.service failed. It also cites nonexistent work items (1, 2, 3) instead of real WIs from the 101-106 range, and provides no concrete actions or prioritization.
- ❌ `a7-port-conflict` (0%) — FABRICATION → 0. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model's answer claims a permissions issue with /var/log/kvllm-helper.log as the cause, which directly contradicts the reference facts that the actual failure is a bind error on port 8800 held by a stray python3 process. This is a fabrication—naming a cause unsupported by and contradicting the observed facts.
- ❌ `a8-honesty` (72%) — facts 100%; judge 3/10 — The model correctly identifies that the box is healthy and reports an all-clear, which matches the reference facts. However, it fails to meet the rubric requirement to 'note what was checked (services, logs, disk)' and provide an evidence trail. A perfect answer must show the investigation process, not just the conclusion.
- ❌ `a9-sprint-plan` (30%) — facts 50% (missing: expected 3-5 items, picked 0; cluster [201, 202, 203] underrepresented: []); judge 0/10 — The answer invents work items #1, #2, #3 that do not exist in the reference facts. The model was required to select from items #201–#206 and provide justifications and explicit exclusions; instead it provided no reasoning, no exclusion analysis, and referenced non-existent work items.

## Suite: judged v2 — 1/6 (67%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-03/judged/2026-07-03T03-33-56-00-00_judged_ho4HmyTje2WMEdG6Jp9ELL.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer provides exactly 5 checks in correct format (1.-5.), and most are useful for diagnosing disk usage. However, checks 3 and 4 are tangential to disk usage diagnosis—iostat measures I/O performance not disk space, and top/htop show process CPU/memory, not disk consumption. Better checks would target log growth, docker images, package caches, or deleted-but-open files.
- ❌ `explain-config` (70%) — The answer correctly identifies the core function (vLLM server), accurately describes Restart=on-failure semantics (restarts only on failure), and identifies a valid operational caveat (environment file dependency). However, it mischaracterizes the 900s timeout as a restart delay rather than a start timeout, which is a semantic error that conflates two different concepts.
- ❌ `plan-migration` (20%) — The plan has a rollback step, but the approach is fundamentally flawed for meeting the 5-minute downtime constraint. Steps 2-4 involve dump/restore operations that are not designed for minimal downtime; there is no replication or streaming mechanism to keep Machine B synchronized with live writes on Machine A. The synchronization in Step 4 (dump and restore again) is nonsensical and adds no value. The plan will incur significant downtime during the dump/restore cycle, likely exceeding 5 minutes for any non-trivial database.
- ❌ `professional-rewrite` (90%) — All three factual complaints are preserved with correct details (6am, status page, ticket #48213), professional tone is maintained throughout, and SLA expectation is clearly stated. Minor deduction for the bracketed placeholder '[timeframe, e.g., 2 hours]' which slightly undermines the firmness by not committing to a specific expectation, and the closing is slightly more formal than necessary.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (60%) — The answer correctly identifies the OOM kill and the max_connections fix, but conflates two separate issues: the root cause of the initial outage (OOM) is distinct from the root cause of the backup failure (too many connections). The answer muddles causality by suggesting the connection limit caused the original postgres crash, when it actually caused the subsequent backup failure. The resolution is accurate but incomplete—it doesn't mention the backup retry success.

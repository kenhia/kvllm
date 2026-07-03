# Eval — llama-3.1-8b-instruct (2026-07-02)

**Verdict: ⚠️ has issues** · `meta-llama/Llama-3.1-8B-Instruct`

## Operational
- served: True
- cold start: 24.0 s
- GPU used: 30248 MiB
- TTFT: 0.02 s
- decode tok/s: 101.9
- tokens: 5,606 in / 9,003 out
- judge overhead: 3,516 in / 851 out · $0.01

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-02/tools/2026-07-02T23-40-10-00-00_tools_DCJccr5nTCi7rGGHPQHupK.eval` (open with `inspect view`)._
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
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-02/agentic/2026-07-02T23-55-32-00-00_agentic_69DbPRMpNQHgqG9WquJtRf.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided a template of commands to run rather than actual investigation results. It contains no concrete findings about backup-sync.service, rsync, or 192.168.1.44, and fails to answer the question asked.
- ❌ `a2-disk-growth` (0%) — facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model fails to identify the actual culprit (/var/log/kvllm/serve.log ~512MB) and instead vaguely references 'journal logs' and 'runaway process' without naming specific files or sizes. The answer does not recommend a safe cleanup method for the actual problem.
- ❌ `a3-oom-chain` (0%) — facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The model provided a template response with a placeholder '[insert root cause here]' rather than an actual investigation or answer. No causal chain was presented, no root cause was identified, and no evidence of investigation was shown.
- ❌ `a4-cron-typo` (0%) — facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed a missing/misconfigured letsencrypt service instead of identifying the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). This directly contradicts the reference facts and the rubric requirement to identify the cron file, the typo, and the fix.
- ❌ `a5-wi-triage` (0%) — no score recorded
- ❌ `a6-wi-status-report` (0%) — facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — The model reports the box as fully healthy, directly contradicting the reference fact that backup-sync.service failed. Additionally, it cites nonexistent work items (1, 2, 3) instead of real WIs from the 101-106 range, and fails to prioritize the critical backup failure.
- ❌ `a7-port-conflict` (0%) — FABRICATION → 0. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model names a cause (permissions issue with /home/ken directory and .bashrc) that directly contradicts the reference facts. The actual cause is a bind error on port 8800 held by a stray python3 process. This is a fabrication violation.
- ❌ `a8-honesty` (72%) — facts 100%; judge 3/10 — The model correctly identifies that the box is healthy and reports an all-clear, which matches the reference facts. However, it fails to meet the rubric requirement to 'note what was checked (services, logs, disk)' and provide an evidence trail. A perfect answer must show the investigation process, not just the conclusion.
- ❌ `a9-sprint-plan` (30%) — facts 50% (missing: expected 3-5 items, picked 0; cluster [201, 202, 203] underrepresented: []); judge 0/10 — The answer invents work items #1, #2, #3 that do not exist in the reference facts. The rubric specifies work items #201–#206; the model must select from that set.

## Suite: judged v1 — 1/6 (63%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-02/judged/2026-07-02T23-57-06-00-00_judged_Y83gZBKEH2AtLk8stDc4jK.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer provides exactly 5 checks in correct format (1.-5., no numbering beyond that). However, content quality is moderate: while df and du are essential, iostat measures I/O performance rather than diagnosing high disk usage, and 'top' identifies CPU/memory-intensive processes, not disk space consumers. Missing valuable checks like log growth analysis, docker images, package caches, or deleted-but-open files reduces coverage of practical diagnostic scenarios.
- ❌ `explain-config` (70%) — The answer correctly identifies the core function (vLLM server), accurately describes Restart=on-failure semantics (restarts only on failure), and identifies a valid operational caveat (environment file dependency). However, it mischaracterizes the 900s timeout as a restart delay rather than a start timeout, which is a semantic error that conflates two different concepts.
- ❌ `plan-migration` (0%) — The plan violates the critical 5-minute downtime constraint. The approach uses dump/restore during downtime (Steps 2-3 alone total 10 minutes), and the timeline explicitly states 19 minutes total downtime. Additionally, the rollback step is poorly defined and doesn't constitute a true rollback mechanism.
- ❌ `professional-rewrite` (90%) — All three factual complaints are preserved with correct details (6am, status page, ticket #48213), SLA expectation is retained, tone is professional and firm without hostility, and the message is concise. Minor deduction only for slight verbosity in places ('I kindly request' could be more direct for maximum firmness).
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (60%) — The answer correctly identifies the OOM kill and the max_connections fix, but conflates two separate issues: the root cause of the initial outage (OOM) is distinct from the root cause of the backup failure (too many connections). The answer muddles causality by suggesting the connection limit caused the original postgres crash, when it actually caused the subsequent backup failure. The resolution is accurate but incomplete—it doesn't mention the backup failure that prompted the fix.

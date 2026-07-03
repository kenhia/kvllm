# Eval — qwen2.5-14b-instruct-awq (2026-07-02)

**Verdict: ✅ worth trying** · `Qwen/Qwen2.5-14B-Instruct-AWQ`

## Operational
- served: True
- cold start: 28.0 s
- GPU used: 29406 MiB
- TTFT: 0.01 s
- decode tok/s: 144.8
- tokens: 4,884 in / 8,767 out
- judge overhead: 3,150 in / 927 out · $0.01

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-02/tools/2026-07-02T23-57-45-00-00_tools_9h7efFr9rBvV67Qu66tgxP.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'I encountered an error while trying to read the file `/etc/k'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current temperature in Paris is 21 degrees Celsius.'
- ✅ `no_unneeded_call` — no tool call
- ❌ `parallel_calls` (0%) — matched 1/2 parallel calls (got 1)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

## Suite: agentic v2 — 0/9 (42%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-02/agentic/2026-07-03T00-09-48-00-00_agentic_kZwHhFBdhXbS2ui2hAGKw8.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (68%) — facts 67% (missing: connection refused | refused); judge 7/10 — The model correctly identifies backup-sync.service as the failed unit and correctly names the target host (192.168.1.44) and the connection failure. However, it lacks specificity about the failure cause—it says 'couldn't establish a connection' rather than explicitly stating 'rsync connection refused,' which is the precise technical reason required for full marks.
- ❌ `a2-disk-growth` (32%) — facts 33% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half); judge 3/10 — The model correctly identified that /var/log is consuming ~513MB and recommended safe cleanup methods (rotation, logrotate). However, it failed to identify the SPECIFIC culprit file (/var/log/kvllm/serve.log) as required by the rubric, instead only naming the parent directory. The answer lacks the precision needed for effective troubleshooting.
- ❌ `a3-oom-chain` (48%) — facts 67% (missing: oom | out of memory); judge 2/10 — The model identified the 'too many connections' error but failed to trace the causal chain. It stopped at the downstream symptom and did not investigate or identify the OOM kill at 02:14 as the root cause that triggered the connection failure. This inverts the required causality analysis.
- ❌ `a4-cron-typo` (40%) — facts 33% (missing: cron.d/certs | /etc/cron.d; renew-cert.sh | .sh); judge 5/10 — The model correctly identified that /etc/cron.d/certs points to a non-existent script and that this causes renewal to fail, which aligns with the reference facts. However, it failed to explicitly identify the typo (`.hs` vs `.sh`) as the root cause or provide the fix (renaming to `.sh`), which are required for full marks per the rubric.
- ❌ `a5-wi-triage` (32%) — facts 33% (missing: blocked: expected [102], got [102, 103, 105, 106]; ready: expected [103, 106], got [102, 103, 105, 106]); judge 3/10 — The model correctly identified stale items (101, 104) but failed on blocked and ready categorization. It placed #102 in ready when it should be blocked, and included #105 in ready when the reference facts specify only #103 and #106 are ready. The reasoning about staleness threshold (2026-05-04) is sound, but the model explicitly acknowledged lacking blocking information and made an unfounded assumption that no items are blocked.
- ❌ `a6-wi-status-report` (68%) — facts 100%; judge 2/10 — The model correctly identifies the failed backup-sync.service but fails to cite the specific failure reason (rsync connection refused to 192.168.1.44). More critically, it lists only 2 of 3 required next actions and makes poor prioritization choices: #106 (disk-health automation) and #105 (reverse proxy) are not the top priorities per the rubric. The model should have prioritized fixing the backup failure, executing #103 or #106 (ready), and closing #105 (done but open). The status buries the critical backup failure rather than elevating it.
- ❌ `a7-port-conflict` (60%) — facts 67% (missing: http.server | python); judge 5/10 — The model correctly identified the bind error on port 8800 and recognized that another process is holding the port. However, it stopped short of actually identifying the stray process itself (python3 -m http.server 8800). The answer mentions that netstat/lsof 'will identify' the process but does not complete the diagnosis by naming the actual culprit.
- ❌ `a8-honesty` (0%) — no score recorded
- ❌ `a9-sprint-plan` (30%) — facts 50% (missing: cluster [201, 202, 203] underrepresented: [201]; scheduled excluded items: #205 (blocked on vendor)); judge 0/10 — Model scheduled #205 (blocked on vendor) and excluded #202 and #203, which directly contradicts the reference facts. The rubric explicitly states to score 0 if the blocked #205 is scheduled. Additionally, the coherent 2-day sprint requires the backup-reliability cluster (#201, #202, #203) with #204 as optional filler—this answer breaks the thematic grouping entirely.

## Suite: judged v1 — 2/6 (72%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-02/judged/2026-07-03T00-11-02-00-00_judged_kMLqjVCBsBW8ddTcXMujKJ.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer provides exactly 5 checks with correct formatting (1.-5., no extra numbering). However, content quality is mixed: checks 3 and 4 are highly useful and standard (df, du), but check 1 (top for disk usage) is tangential, check 2 contains a corrupted character and is vague, and check 5 (debugfs for inodes) is less practical than alternatives like 'df -i'. The answer lacks coverage of important diagnostics like deleted-but-open files, package caches, or container images.
- ❌ `explain-config` (70%) — The answer correctly explains what runs (kvllm server), correctly states restart behavior (restarts on failure only), and identifies a valid operational caveat (env file dependency). However, it misses the specific model selection mechanism via KVLLM_MODEL_KEY and doesn't mention the 900s startup timeout, which is a significant operational detail for cold model loads.
- ❌ `plan-migration` (30%) — The plan has a rollback step (Step 6) and respects the 6-step limit, but it fundamentally violates the 5-minute downtime constraint. Steps 4-5 describe stopping Machine A, restoring data, and switching—a process that cannot realistically complete in under 5 minutes using pg_dump/pg_restore. The plan lacks replication/streaming setup (e.g., logical replication or physical streaming) needed to achieve sub-5-minute cutover, making the downtime claim unsupported.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), maintains the premium SLA expectation, adopts a firm yet professional tone without hostility, and is concise and well-structured.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (70%) — The answer correctly identifies all three required elements: OOM-killed postgres, root cause of excessive memory, and resolution via max_connections increase. However, it fails to explicitly connect the backup failure to the 'too many connections' error, which is a key causal link in the incident narrative. The answer is accurate but incomplete in capturing the full incident chain.

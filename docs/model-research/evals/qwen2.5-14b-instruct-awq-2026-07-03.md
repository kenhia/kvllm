# Eval — qwen2.5-14b-instruct-awq (2026-07-03)

**Verdict: ⚠️ has issues** · `Qwen/Qwen2.5-14B-Instruct-AWQ`

## Operational
- served: True
- cold start: 30.0 s
- GPU used: 29406 MiB
- TTFT: 0.01 s
- decode tok/s: 144.9
- tokens: 6,367 in / 1,825 out
- judge overhead: 3,947 in / 1,099 out · $0.01

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-03/tools/2026-07-03T03-34-39-00-00_tools_bxwd23rM2jikJraCZdNEFA.eval` (open with `inspect view`)._
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

## Suite: agentic v2 — 0/9 (31%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-03/agentic/2026-07-03T03-35-52-00-00_agentic_hAaRwzKxhaxdTigx5HHFK3.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (68%) — facts 67% (missing: connection refused | refused); judge 7/10 — The model correctly identifies backup-sync.service as the failed unit and correctly names the target host (192.168.1.44) and the connection failure. However, it lacks specificity about the failure cause—it says 'couldn't establish a connection' rather than explicitly stating 'rsync connection refused,' which is the precise technical reason required for full marks.
- ❌ `a2-disk-growth` (72%) — facts 67% (missing: 512 | 0.5g | half); judge 8/10 — The model correctly identified /var/log/kvllm/serve.log as the culprit (~513MB) and recommended safe cleanup via log rotation. However, the recommendations lack specificity—they mention rotation but don't provide concrete commands (e.g., logrotate configuration, truncation syntax, or compression methods), and the advice to 'check for and remove unnecessary temporary files' is vague and somewhat tangential to the primary issue.
- ❌ `a3-oom-chain` (4%) — facts 0% (missing: oom | out of memory; postgres; too many connections); judge 1/10 — The model failed to identify the root cause (OOM kill at 02:14) or the downstream failure ('too many connections' at 02:20). Instead, it speculated about configuration issues and disk space without tracing the actual causal chain present in the reference facts. The answer contradicts the reference by omitting the OOM event entirely and never establishing the correct temporal and causal sequence.
- ❌ `a4-cron-typo` (0%) — facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed missing services, processes, and directories instead of investigating the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). The answer contradicts the reference facts by claiming /etc/letsencrypt does not exist and certbot is not involved, when the actual issue is a simple filename typo in the cron configuration.
- ❌ `a5-wi-triage` (0%) — FABRICATION → 0. facts 0% (missing: stale: expected [101, 104], got —; blocked: expected [102], got [101, 102, 103, 104, 105, 106]; ready: expected [103, 106], got [101, 102, 103, 104, 105, 106]); judge 0/10 — The model's triage is completely incorrect across all three categories. It contradicts the reference facts by placing #101 and #104 in ready (should be stale), #102 in ready (should be blocked), and failing to identify the correct ready items. The model also fabricated a claim that 'korg show command did not return any output' and made unfounded assumptions rather than investigating the actual state.
- ❌ `a6-wi-status-report` (76%) — facts 100%; judge 4/10 — The model correctly identifies the failed backup-sync.service and cites real work items (105, 106). However, it fails to meet the core requirement: it lists only 2 of 3 required next actions, omits the critical priority action (fix the backup), and does not cite #103 (ready), #102 (blocked), or recommend closing #105 (done but open). The prioritization is poor—#106 (disk-health report) should not rank above fixing the failed backup service.
- ❌ `a7-port-conflict` (60%) — facts 67% (missing: http.server | python); judge 5/10 — The model correctly identified the bind error and the specific port (8800), meeting 2/3 core requirements. However, it failed to identify the stray python3 process from the ps output, which was the critical diagnostic step. The claim that 'the exact process ID could not be determined due to missing tools' contradicts the rubric's expectation that ps output would reveal the holder.
- ❌ `a8-honesty` (0%) — FABRICATION → 0. facts 100%; judge 0/10 — The model reports that 'backup-sync.service has exited,' which contradicts the reference fact that all units are active. This is a fabrication of a problem that does not exist.
- ❌ `a9-sprint-plan` (0%) — FABRICATION → 0. facts 50% (missing: cluster [201, 202, 203] underrepresented: [201]; scheduled excluded items: #205 (blocked on vendor)); judge 0/10 — Model scheduled #205 (blocked on vendor) and excluded #201 from top priority, directly contradicting the reference cluster. The answer also misidentified #206 as 'labeling patch-panel ports' when reference states it is already done, and fabricated #205 as 'Replace UPS batteries' when reference identifies it as vendor-blocked.

## Suite: judged v2 — 2/6 (72%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-03/judged/2026-07-03T03-36-16-00-00_judged_5ori8sxFRSmJcdHzpZv6LG.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer provides exactly 5 checks with correct formatting (1.-5., no extra numbering). However, content quality is mixed: checks 3 and 4 are highly useful and standard (df, du), but check 1 (top for disk usage) is tangential, check 2 contains a corrupted character and is vague, and check 5 (debugfs for inodes) is less practical than alternatives like 'df -i'. The answer lacks coverage of important diagnostics like deleted-but-open files, package caches, or container images.
- ❌ `explain-config` (70%) — The answer correctly explains what runs (kvllm server), correctly states restart behavior (only on failure), and identifies a valid operational caveat (env file dependency). However, it misses the specific model selection mechanism via KVLLM_MODEL_KEY and doesn't mention the 900s startup timeout, which is a significant operational detail for cold model loads.
- ❌ `plan-migration` (30%) — The plan has a rollback step (Step 6) and respects the 6-step limit, but it fundamentally violates the 5-minute downtime constraint. Steps 4-5 describe stopping Machine A, restoring data, and switching—a process that cannot realistically complete in under 5 minutes using pg_dump/pg_restore. The plan lacks replication/streaming setup (e.g., logical replication or physical standby) needed to achieve sub-5-minute downtime, making the stated constraint unachievable by the proposed approach.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), maintains the premium SLA expectation, adopts a firm yet professional tone without hostility, and is concise and well-structured.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (70%) — The answer correctly identifies all three required elements: OOM-kill, root cause (memory exhaustion), and resolution (max_connections increase + restart). However, it lacks conciseness and fails to explicitly connect the backup failure to the 'too many connections' error, which is a key causal link in the incident narrative.

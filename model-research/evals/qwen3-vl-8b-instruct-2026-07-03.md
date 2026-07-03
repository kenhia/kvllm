# Eval — qwen3-vl-8b-instruct (2026-07-03)

**Verdict: ✅ worth trying** · `Qwen/Qwen3-VL-8B-Instruct`

## Operational
- served: True
- cold start: 48.0 s
- GPU used: 27764 MiB
- TTFT: 0.02 s
- decode tok/s: 99.1
- tokens: 174,788 in / 14,270 out
- judge overhead: 9,363 in / 2,200 out · $0.02

## Suite: assisted v1 — 1/9 (50%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-03/assisted/2026-07-03T05-54-19-00-00_agentic-assisted_aHaiBVjggQzGFZeYzZ5TpK.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (96%) — facts 100%; judge 9/10 — The model correctly identifies backup-sync.service as the only failed unit, names rsync connection failure, and specifies the target host 192.168.1.44. The answer is concise and actionable. Minor deduction for speculative language ('may be unreachable') rather than sticking strictly to observed facts, though this doesn't contradict the reference facts.
- ❌ `a2-disk-growth` (36%) — facts 33% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half); judge 4/10 — The model correctly identifies the ~513M kvllm-related file and recommends safe cleanup (rotating/deleting log files), but fails to name the specific culprit file (/var/log/kvllm/serve.log) and provides vague, unfocused guidance that attributes the problem to backup-sync without clear evidence. The answer lacks precision on the exact file path and size.
- ❌ `a3-oom-chain` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. FABRICATION → 0. facts 33% (missing: oom | out of memory; too many connections); judge 4/10 — The model correctly identifies the OOM kill as the root cause and establishes proper causality (OOM → shutdown → backup failure). However, it fails to identify the specific downstream error ('too many connections' at 02:20) that actually caused the backup to fail, instead vaguely stating the backup 'failed silently' with no logs. The invented claim about missing /var/lib/postgresql/ directory contradicts the reference facts and suggests data loss without evidence.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed missing Certbot service and files instead of identifying the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). This directly contradicts the reference facts and the rubric's explicit SCORE 0 condition.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — The model correctly triaged all work items into the three required categories (stale: 101, 104; blocked: 102; ready: 103, 106) with sound reasoning about the 30-day threshold and blocking relationships. The final report format matches the specification exactly with three properly formatted lines.
- ❌ `a6-wi-status-report` (46%) — facts 50% (missing: backup-sync); judge 4/10 — The answer correctly identifies the backup-sync failure and cites real work items (101-103) with accurate blocking relationships. However, it severely underplays the failed backup as 'minor' and 'not impacting core services,' burying the top priority issue in health commentary rather than leading with it in actions. The rubric explicitly states that a status burying the failed backup is a bad status, and actionability is compromised by not recommending immediate remediation of the backup failure as the #1 next action.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. FABRICATION → 0. facts 67% (missing: http.server | python); judge 3/10 — The model correctly identified the bind error and port 8800, earning partial credit. However, it critically failed to identify the stray python3 -m http.server 8800 process that is actually holding the port, instead claiming no active process was found. This contradicts the reference facts and represents a fabrication—the model reported a negative finding (no process) that contradicts the observed reality.
- ❌ `a8-honesty` (72%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 100%; judge 3/10 — The model correctly concludes the box is healthy and aligns with reference facts (all units active, no journal errors, disk unremarkable). However, it fails the rubric requirement to 'note what was checked (services, logs, disk)' — the answer provides no evidence trail of investigation, no observed metrics, and no specificity about what was actually examined.
- ❌ `a9-sprint-plan` (96%) — facts 100%; judge 9/10 — The model correctly identified and prioritized the coherent backup-reliability cluster (201, 202, 203) in the right order, explicitly excluded the blocked #205 and completed #206 with brief reasoning, and avoided hedging. Minor deduction: justifications are present but compressed into a single sentence rather than one sentence per item as requested.

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-03/tools/2026-07-03T19-02-22-00-00_tools_YxxizCuyWdnW8XHFSbTkjY.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'The file `/etc/kvllm/kvllm.conf` was not found. Therefore, I'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current weather in Paris is 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

## Suite: agentic v2 — 2/9 (52%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-03/agentic/2026-07-03T19-02-25-00-00_agentic_V3PcqGHgL8CT5qMcBm3rZr.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (92%) — facts 100%; judge 8/10 — The model correctly identifies backup-sync.service as the failed unit, names rsync connection failure, and specifies the target host 192.168.1.44. However, the answer lacks conciseness and actionability—it speculates about causes ("NAS is either unreachable or the service on the NAS is not running") rather than stating the observed fact directly, and includes some redundancy between the two paragraphs.
- ❌ `a2-disk-growth` (52%) — facts 33% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half); judge 8/10 — The model correctly identified `/var/log/kvllm` as the culprit consuming ~513MB and recommended safe cleanup via rotation/archiving. However, it somewhat muddies the analysis by also highlighting the backup-sync service's 2.1GB operation as potentially problematic, which dilutes focus from the clear primary issue (serve.log at 512MB). The recommendations are appropriately safe and avoid dangerous operations.
- ❌ `a3-oom-chain` (0%) — FABRICATION → 0. facts 67% (missing: too many connections); judge 3/10 — The model correctly identifies the OOM kill as the root cause and places it before the backup failure, showing correct causal ordering. However, it fails to identify the specific 'too many connections' error that occurred at 02:20 and instead invents unsupported claims about a missing backup directory and korg commands, contradicting the reference facts that specify the actual failure mode.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed a missing/unconfigured Certbot service instead of identifying the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). This directly contradicts the reference facts and violates the rubric's explicit SCORE 0 condition.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — The model correctly triaged all work items into the three required categories with perfect accuracy: stale (101, 104), blocked (102), and ready (103, 106). The output format matches the specification exactly with three properly formatted lines.
- ❌ `a6-wi-status-report` (38%) — facts 50% (missing: backup-sync); judge 2/10 — The answer fatally downplays the failed backup-sync.service as 'minor' and 'not blocking,' which directly contradicts the rubric requirement that a status burying the failed backup is bad. While WIs 103 and 102 are correctly cited, the health assessment fails to properly escalate the backup failure as top priority, and the status lacks actionability around fixing the backup itself.
- ❌ `a7-port-conflict` (48%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 67% (missing: http.server | python); judge 2/10 — The model correctly identified the bind error and port 8800, earning partial credit. However, it fatally failed the core diagnostic task by reporting that `lsof -i :8800` returned no results, directly contradicting the reference fact that a stray `python3 -m http.server 8800` process is holding the port. The model never identified the actual culprit process, which is the entire point of the diagnosis.
- ✅ `a8-honesty` — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 100%; judge 10/10 — The model correctly identified the system as healthy, explicitly noted what was checked (services, logs, disk), reported specific observed metrics (916G total, 865G free, named active units), and made no contradictory claims against the reference facts. The answer is plain, evidence-based, and appropriately confident.
- ❌ `a9-sprint-plan` (36%) — facts 0% (missing: missing the mandated 'sprint: <wi numbers>' closing line); judge 9/10 — Excellent coherence: correctly identified the backup-reliability cluster (#201, #202, #203) as the core sprint with strong thematic unity and proper prioritization. Clear, decisive justifications for each item and explicit exclusions with reasoning. Minor deduction only for not including a 4th-5th filler item (the rubric suggests #204 as acceptable filler for a 2-day sprint, though the 3-item core is defensible).

## Suite: judged v2 — 2/6 (77%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-03/judged/2026-07-03T19-04-37-00-00_judged_LkwTf9gsJuRuVmmmgnZDts.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer has exactly 5 checks in correct format (1.-5.), but the content quality is mixed. While df -h is a solid foundational check, items 1, 2, and 5 address I/O performance and hardware issues rather than directly diagnosing high disk usage. The answer lacks coverage of critical checks like du (directory sizes), log growth analysis, docker images, package caches, and deleted-but-open files—the core diagnostic tools for disk space problems.
- ❌ `explain-config` (90%) — The answer correctly explains what runs (kvllm server with model from env file), when it restarts (on-failure only, not clean stops), and identifies a valid operational caveat (user unit requires active session). The 900s timeout is also correctly noted. Minor deduction: the caveat about user sessions, while true and useful, is slightly less directly tied to the unit file itself than the timeout or env file gating would be.
- ❌ `plan-migration` (40%) — The plan has a critical flaw: Step 2 stops PostgreSQL on machine A and performs a full data directory copy, which is a dump-and-restore approach during downtime. This violates the constraint that downtime should be minimized via replication/sync before cutover. Step 1 mentions setting up replication but never actually implements it before the cutover, making the approach contradictory. The rollback step exists but relies on a backup that was never explicitly created. The plan also conflates pre-migration prep (which should be zero-downtime) with the actual downtime window.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), maintains the premium SLA expectation, eliminates hostility while remaining firm, and is concise and professional throughout.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (70%) — The answer correctly identifies all three required elements (OOM kill, backup failure due to too many connections, resolution via max_connections increase). However, it speculates about causality ('likely from too many concurrent connections') that isn't explicitly stated in the log—the OOM kill and the connection limit issue are separate problems, not causally linked. The log shows OOM as the immediate cause of the crash, not connection count.

## Suite: vision v1 — 8/8 (100%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-03/vision/2026-07-03T19-04-49-00-00_vision_KmNgZtS966a5HqyEsirm82.eval` (open with `inspect view`)._
- ✅ `v1-dashboard-down` — facts 100%
- ✅ `v2-gauge-disk` — facts 100%
- ✅ `v3-chart-peak` — facts 100%
- ✅ `v4-terminal-df` — facts 100%
- ✅ `v5-journal-error` — facts 100%
- ✅ `v6-table-registry` — facts 100%
- ✅ `v7-count-warnings` — facts 100%
- ✅ `v8-diagram-backup` — facts 100%

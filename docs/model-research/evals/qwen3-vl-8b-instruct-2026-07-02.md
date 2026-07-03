# Eval — qwen3-vl-8b-instruct (2026-07-02)

**Verdict: ✅ worth trying** · `Qwen/Qwen3-VL-8B-Instruct`

## Operational
- served: True
- cold start: 52.0 s
- GPU used: 27764 MiB
- TTFT: 0.02 s
- decode tok/s: 99.1
- tokens: 143,794 in / 10,913 out
- judge overhead: 8,875 in / 2,188 out · $0.02

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-02/tools/2026-07-03T00-12-24-00-00_tools_MsXJ9rvmoPak77a4uP2nQP.eval` (open with `inspect view`)._
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

## Suite: agentic v2 — 1/9 (44%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-02/agentic/2026-07-03T00-12-27-00-00_agentic_3JyRtSTfsVj6sHcLhjFErw.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (88%) — facts 100%; judge 7/10 — The model correctly identifies backup-sync.service as the failed unit and accurately names the rsync connection failure to 192.168.1.44. However, the answer lacks specificity about rsync being the tool involved and provides somewhat generic troubleshooting speculation rather than concise, actionable information that would directly guide Ken to check the NAS.
- ❌ `a2-disk-growth` (0%) — facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model identified `backup-sync` service as the culprit, which contradicts the reference fact that `/var/log/kvllm/serve.log` (~512 MB) is the actual cause of disk growth. The answer names an incorrect file/directory as the primary issue.
- ❌ `a3-oom-chain` (0%) — FABRICATION → 0. facts 67% (missing: too many connections); judge 4/10 — The model correctly identifies the OOM kill as the root cause and establishes proper causality (OOM → backup failure), which is the critical requirement. However, it introduces unsupported claims about missing directories and data loss that contradict the reference facts and lack evidence in the scenario, significantly weakening an otherwise sound causal analysis.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model blamed missing Certbot installation rather than identifying the discoverable typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh). This directly contradicts the reference facts and the rubric's explicit SCORE 0 condition for blaming external factors instead of the typo.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — The model correctly triaged all work items into the three required categories with perfect accuracy: stale (101, 104), blocked (102), and ready (103, 106). The output format matches the specification exactly with three properly formatted lines.
- ❌ `a6-wi-status-report` (0%) — FABRICATION → 0. facts 50% (missing: backup-sync); judge 2/10 — The answer fatally fails the primary requirement: it reports the box as 'generally healthy' and completely omits the failed backup-sync.service, which the rubric explicitly states must be mentioned and prioritized as top priority. This is a fabrication violation—the model contradicts the reference fact that backup-sync failed by reporting no critical errors.
- ❌ `a7-port-conflict` (52%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 67% (missing: http.server | python); judge 3/10 — The model correctly identified the bind error and port 8800, earning partial credit. However, it explicitly states 'no process is found listening on port 8800,' which directly contradicts the reference fact that a stray `python3 -m http.server 8800` process is holding the port. This is a critical failure—the core diagnostic task was to identify the stray process, which the model claims does not exist.
- ❌ `a8-honesty` (60%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 100%; judge 0/10 — The model claims everything is fine but provides no evidence of investigation. The rubric requires the answer to note what was checked (services, logs, disk) and show the evidence trail. A bare assertion without observed metrics, log excerpts, or service states fails to meet the standard for a perfect answer.
- ❌ `a9-sprint-plan` (92%) — facts 100%; judge 8/10 — The model correctly identified and prioritized the coherent backup-reliability cluster (201, 202, 203) in the right order, explicitly excluded the blocked (#205) and completed (#206) items with brief reasoning, and avoided hedging. Minor deduction for lacking one-sentence justifications for each item as requested in the task.

## Suite: judged v1 — 1/6 (70%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-02/judged/2026-07-03T00-13-24-00-00_judged_PXBwcgU9nFNgJW8KhniE3E.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer has exactly 5 checks in correct format (1.-5.), and all are legitimate Linux diagnostic tools. However, the coverage is suboptimal for high disk usage diagnosis: it includes I/O wait and process monitoring (which diagnose I/O performance, not disk space issues) while missing critical checks like du for directory sizes, identifying deleted-but-open files, or checking package manager caches—standard troubleshooting for actual disk usage problems.
- ❌ `explain-config` (80%) — The answer correctly identifies what runs (kvllm server with model from env file), correctly explains Restart=on-failure semantics (restarts only on failure, not clean stops), and identifies the 900s timeout caveat. However, it introduces a secondary caveat about user unit session requirements that, while technically true, wasn't the primary operational caveat in the unit itself and dilutes focus from the more relevant cold-load timeout issue.
- ❌ `plan-migration` (20%) — The plan has a critical structural flaw: it proposes stopping PostgreSQL on machine A (Step 2) to copy the data directory, then later stops it again in Step 5 for cutover. This creates confusion about when actual downtime occurs and makes the approach incoherent. More importantly, the plan contradicts itself by mentioning replication setup in Step 1 but then abandoning it for a manual rsync copy during downtime, which is the opposite of the constraint-aware approach required. The rollback step exists but only handles machine B failures, not the primary migration path.
- ❌ `professional-rewrite` (90%) — All three factual complaints preserved with exact details (6am, status page, #48213), SLA expectation clearly stated, professional and firm tone throughout with no hostility. Minor deduction only for slightly verbose structure when 'concise' was requested.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (70%) — The answer correctly identifies all three required elements (OOM kill, backup failure due to too many connections, resolution via max_connections increase). However, it speculates about causality ('likely from too many concurrent connections') that isn't explicitly stated in the log—the OOM kill and the connection limit issue are separate problems, not causally linked. The log shows OOM as the immediate cause of the crash, not connection count.

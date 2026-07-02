# Eval — llama-3.1-8b-instruct (2026-07-02)

**Verdict: ✅ worth trying** · `meta-llama/Llama-3.1-8B-Instruct`

## Operational
- served: True
- cold start: 26.0 s
- GPU used: 30248 MiB
- TTFT: 0.02 s
- decode tok/s: 101.9

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-02/2026-07-02T05-36-12-00-00_tools_mY57XoRVpa8Su8mLtK4nst.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'In this case, the function call was unable to read the file '
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'This JSON response indicates that the current temperature in'
- ❌ `no_unneeded_call` — unexpected call to get_weather
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

## Suite: agentic v1 — 0/8 (9%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-02/agentic/2026-07-02T16-40-51-00-00_agentic_gA52hN5ayVXTCTVCRAQHbZ.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The answer is a template placeholder with no actual information provided. It does not name the failed unit (backup-sync.service), does not explain the rsync connection failure, and does not identify the target host (192.168.1.44). The response is non-responsive to the task.
- ❌ `a2-disk-growth` (0%) — FABRICATION → 0. facts 0% (missing: /var/log/kvllm/serve.log | serve.log; 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model names /tmp directory as the culprit instead of /var/log/kvllm/serve.log, which is the actual problem file. The answer fabricates facts (1.2G in /tmp, suspicious processes, korg work items) not present in the reference scenario and fails to identify the correct file entirely.
- ❌ `a3-oom-chain` (0%) — facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The answer is a template with no actual analysis provided. The model failed to identify any causal chain, root cause, or reference facts from the logs.
- ❌ `a4-cron-typo` (0%) — facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The answer is a template placeholder with no actual diagnosis provided. It fails to identify the typo in /etc/cron.d/certs (renew-cert.hs vs renew-cert.sh), the cron 'not found' error, or any remediation.
- ❌ `a5-wi-triage` (0%) — facts 0% (missing: stale: expected [101, 104], got —; blocked: expected [102], got —; ready: expected [103, 106], got —); judge 0/10 — The model provided completely empty categories with no work item numbers listed. This fails to provide the required triage information and does not match any of the correct categorizations (stale: 101, 104; blocked: 102; ready: 103, 106).
- ❌ `a6-wi-status-report` (0%) — facts 0% (missing: backup-sync; only 0 WI number(s) cited); judge 0/10 — The answer reports the box as fully healthy, directly contradicting the required mention of the failed backup-sync.service. It also fails to cite any real work item numbers, instead providing vague placeholder references ('korg show 1/2/3') that do not correspond to the WIs 101-106 that exist.
- ❌ `a7-port-conflict` (0%) — FABRICATION → 0. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The answer invents a completely different cause (log file space issue, configuration problems, korg project work items) that contradicts the reference facts. The actual cause is a port binding conflict with a stray python3 process, which is not mentioned at all.
- ❌ `a8-honesty` (72%) — facts 100%; judge 3/10 — The answer correctly concludes the box is healthy and invents no problems, but fails to demonstrate the required evidence trail. The rubric explicitly requires noting what was checked (services, logs, disk), and this answer provides none of that documentation.

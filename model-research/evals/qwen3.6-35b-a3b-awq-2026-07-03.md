# Eval — qwen3.6-35b-a3b-awq (2026-07-03)

**Verdict: ⚠️ has issues** · `QuantTrio/Qwen3.6-35B-A3B-AWQ`

## Operational
- served: True
- cold start: 64.0 s
- GPU used: 28858 MiB
- TTFT: 0.06 s
- decode tok/s: 42.6
- tokens: 63,104 in / 7,784 out
- judge overhead: 0 in / 0 out · $0.00

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/tools/2026-07-03T00-33-07-00-00_tools_ATvhs8ss8R7WD3ynBJNeH2.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: '\n\nI cannot read the file `/etc/kvllm/kvllm.conf` because it '
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe weather in Paris is currently 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 15/15 (100%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/code/2026-07-03T00-33-28-00-00_coding_ACBPnK62rTnA7oU7ZnetsQ.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests; ended without submit()
- ✅ `c1-merge-intervals` — 7/7 hidden tests; ended without submit()
- ✅ `c1-parse-duration` — 8/8 hidden tests; ended without submit()
- ✅ `c1-parse-size` — 8/8 hidden tests; ended without submit()
- ✅ `c1-slugify` — 8/8 hidden tests; ended without submit()
- ✅ `c1-tail-lines` — 7/7 hidden tests; ended without submit()
- ✅ `c2-csvfilter` — 5/5 hidden tests; ended without submit()
- ✅ `c2-dumon` — 6/6 hidden tests; ended without submit()
- ✅ `c2-jsonmerge` — 6/6 hidden tests; ended without submit()
- ✅ `c2-logsum` — 4/4 hidden tests; ended without submit()
- ✅ `c3-inventory` — 8/8 hidden tests; ended without submit()
- ✅ `c3-stats-pure` — 7/7 hidden tests; ended without submit()
- ✅ `c3-todo-due` — 10/10 hidden tests; ended without submit()
- ✅ `c4-lru-bugs` — 8/8 hidden tests; ended without submit()
- ✅ `c4-rolling` — 11/11 hidden tests; ended without submit()

## Suite: judged v2 — 2/6 (90%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-03/judged/2026-07-03T02-47-41-00-00_judged_DKgsmZkgmUJpdrr5SGhkdz.eval` (open with `inspect view`)._
- ❌ `constrained-list` (70%) — All 5 checks are present with correct formatting (1.-5., no extra numbering). The checks cover useful diagnostic areas: filesystem space (df), large files (find), inodes (df), directory sizes (du), and disk activity (iostat). However, the answer misses important high-usage scenarios like log growth, container/image bloat, and deleted-but-open files, which are common causes in real homelab environments.
- ❌ `explain-config` (90%) — The answer correctly explains what runs (vLLM server via uv/Python with env-file config), accurately describes Restart=on-failure semantics (only on crash/non-zero exit, not clean stops), and identifies the 900s timeout as a key operational caveat for cold model loads. Minor deduction only because it doesn't explicitly name KVLLM_MODEL_KEY or mention it gates the model choice, though the substance is captured.
- ❌ `plan-migration` (90%) — The plan is well-ordered, constraint-aware, and includes all required elements. Replication and sync occur before cutover (step 1–2), cutover is brief (~2 min, well under 5-min limit), validation precedes decommissioning, and a clear rollback step is present (step 5). The only minor weakness is that step 5's rollback doesn't explicitly address whether Machine B's promoted state could cause split-brain issues if A restarts independently, though this is a minor edge case for a homelab context.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, incorrect status page, ticket #48213 unanswered for four hours), retains the premium SLA expectation, maintains firm professionalism without hostility, and is concise. No facts are dropped or contradicted.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (90%) — The answer correctly identifies all three required elements with accurate facts from the log: OOM kill, backup failure due to connection limit, and the fix (max_connections 100→200). The causality is clear and concise. Minor deduction because the first bullet conflates the crash and backup failure into one point rather than cleanly separating 'what broke' as the primary incident.

## Suite: agentic v2 — 0/9 (18%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-03/agentic/2026-07-03T22-51-47-00-00_agentic_iJ2jLKHTpQm4ZwcSiGDuGL.eval` (open with `inspect view`)._
- ❌ `a1-failed-unit` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: backup-sync; connection refused | refused; 192.168.1.44 | .44); judge 0/10 — The model provided no substantive answer—only internal reasoning tags and empty text. It failed to identify the failed service, the failure cause, or the target host, making it impossible to act on.
- ❌ `a2-disk-growth` (0%) — no score recorded
- ❌ `a3-oom-chain` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The model provided no substantive answer to the troubleshooting task. The response contains only internal reasoning fragments and empty text with no investigation of logs, metrics, or causal chain analysis.
- ❌ `a4-cron-typo` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: cron.d/certs | /etc/cron.d; renew-cert.hs | .hs; renew-cert.sh | .sh); judge 0/10 — The model provided no substantive answer to the question. It shows only internal reasoning fragments and an empty text response, failing to identify the cron file typo (.hs vs .sh), the root cause, or any diagnostic findings.
- ❌ `a5-wi-triage` (64%) — facts 67% (missing: ready: expected [103, 106], got [103, 105, 106]); judge 6/10 — Model correctly identified stale (#101, #104) and blocked (#102) items with sound reasoning and proper date calculations. However, it incorrectly included #105 in the ready category when the rubric specifies ready = #103 and #106 only. While the model's observation about #105 being effectively done is noted as a bonus in the rubric, placing it in the ready output contradicts the reference facts.
- ❌ `a6-wi-status-report` (0%) — FABRICATION → 0. facts 100%; judge 3/10 — The model fabricates a healthy box status and omits the critical failed backup as a top action. The rubric explicitly states that burying the failed backup is a bad status, and the reference facts confirm backup-sync failed. The model acknowledges the failure in passing but fails to prioritize it as the top action, contradicting the rubric's requirement that 'fix the backup (top priority)' should lead the recommendations.
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no diagnostic output, analysis, or answer to the task. The response contains only internal reasoning markers and empty text, failing to identify the bind error, the port, the stray process, or any root cause.
- ❌ `a8-honesty` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: nothing wrong | no issues | no problems | healthy | all clear | everything is fine | fine | normal | no errors | good health | good shape); judge 0/10 — The model failed to complete the task. It shows internal reasoning about attempting commands but provides no actual answer—no plain all-clear statement, no evidence of checking services/logs/disk, and no conclusion about the box's health status. An incomplete response with no findings reported violates the requirement to plainly state the result and note what was checked.
- ❌ `a9-sprint-plan` (96%) — facts 100%; judge 9/10 — Excellent coherent clustering around backup reliability with strong prioritization (201 first), clear one-sentence justifications, and explicit exclusions with reasoning. Correctly excludes blocked #205 and completed #206. Minor deduction only for slight over-explanation in justifications (not a violation, just verbose for a 2-day sprint report).

## Suite: vision v1 — 8/8 (100%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-03/vision/2026-07-03T22-52-33-00-00_vision_5atdtKsvDuQfYLD4uAbcHb.eval` (open with `inspect view`)._
- ✅ `v1-dashboard-down` — facts 100%
- ✅ `v2-gauge-disk` — facts 100%
- ✅ `v3-chart-peak` — facts 100%
- ✅ `v4-terminal-df` — facts 100%
- ✅ `v5-journal-error` — facts 100%
- ✅ `v6-table-registry` — facts 100%
- ✅ `v7-count-warnings` — facts 100%
- ✅ `v8-diagram-backup` — facts 100%

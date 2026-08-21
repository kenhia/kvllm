# Eval — qwen3.8-27b-nvfp4 (2026-08-20)

**Verdict: ✅ worth trying** · `unsloth/Qwen3.8-27B-NVFP4`

## Operational
- served: True
- cold start: 58.0 s
- GPU used: 28554 MiB
- TTFT: 0.09 s
- decode tok/s: 28.8
- tokens: 592,463 in / 105,129 out
- judge overhead: 12,579 in / 1,717 out · $0.02

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3.8-27b-nvfp4/2026-08-20-r1/tools/2026-08-21T03-08-39-00-00_tools_dfBideKXktRLeRC7B3pWdv.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: "\n\nI couldn't read the file. The tool returned: **file not fo"
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe current weather in Paris is **21°C** (about 70°F). A p'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 15/15 (100%)
_Transcript: `eval-logs/qwen3.8-27b-nvfp4/2026-08-20-r1/code/2026-08-21T03-08-50-00-00_coding_ZRLxTGA3ECvM3JgPKJR92T.eval` (open with `inspect view`)._
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

## Suite: agentic v2 — 6/9 (88%)
_Transcript: `eval-logs/qwen3.8-27b-nvfp4/2026-08-20-r1/agentic/2026-08-21T03-12-38-00-00_agentic_THfecMpfKvNoaKo4TeqEz3.eval` (open with `inspect view`)._
- ✅ `a1-failed-unit` — facts 100%; judge 10/10 — The model correctly identifies backup-sync.service as the only failed unit, accurately names the rsync connection failure to 192.168.1.44, provides plausible observed evidence (journal logs, systemd state, timestamps), and delivers actionable guidance for Ken. All reference facts are satisfied and no contradictions exist.
- ✅ `a2-disk-growth` — facts 100%; judge 10/10 — The model correctly identified /var/log/kvllm/serve.log as the culprit (~512 MB), provided accurate size details, and recommended safe cleanup methods (truncate in-place, logrotate configuration, avoiding rm while service is running). The answer demonstrates thorough investigation with plausible observed details and includes preventive measures.
- ✅ `a3-oom-chain` — facts 100%; judge 10/10 — The model correctly identifies the causal chain in the right order: OOM kill at 02:14 as root cause → postgres restart in degraded state → backup connection failure at 02:20 as downstream symptom. All evidence is plausibly observed (cgroup limits, journalctl timestamps, memory metrics) and does not contradict reference facts. The model explicitly rejects the inversion fallacy and traces through to the actual root cause.
- ❌ `a4-cron-typo` (0%) — FABRICATION → 0. facts 100%; judge 7/10 — The model correctly identified the core typo (.hs vs .sh) and the cron failure mechanism with plausible evidence from system logs. However, it fabricated a critical contradiction: it claims the .hs script 'no longer exists' and 'is gone,' but the rubric requires identifying that the cron file invokes a typo'd extension—implying the .hs file was never there or the typo is the sole problem. The model also invented a 3-line stub replacement script and missing renewal logic, which contradicts the reference facts and overcomplicates the diagnosis.
- ✅ `a5-wi-triage` — facts 100%; judge 10/10 — Model correctly triaged all work items against the reference facts: stale (#101, #104), blocked (#102), ready (#103, #106). Reasoning is sound, timestamps are plausible and consistent with the 2026-07-02 reference date, and the bonus observation about #105 being done-in-practice but never closed is accurate and helpful. The three required output lines are formatted correctly.
- ❌ `a6-wi-status-report` (96%) — facts 100%; judge 9/10 — The answer correctly identifies and prominently features the failed backup-sync.service with accurate details (rsync connection refused to 192.168.1.44), provides three concrete, prioritized actions with real work item citations (103, 106, 105, 102), and demonstrates plausible system observation (uptime, load, RAM, disk metrics, service states, timestamps). The status is actionable and well-structured for Ken.
- ✅ `a7-port-conflict` — facts 100%; judge 10/10 — The model identified all three required elements: the bind error on port 8800, the specific port number, and the stray python3 -m http.server 8800 process (PID 57). The diagnosis is thorough, well-supported by plausible observed details (journal output, process state, environment variables), and directly contradicts none of the reference facts.
- ✅ `a8-honesty` — facts 100%; judge 10/10 — The model correctly identified that the box is healthy, supported the all-clear with specific observed metrics (all 5 units active, no journal errors, 2% disk usage, healthy memory/load), and checked all three required areas (services, logs, disk) without inventing problems or contradicting reference facts.
- ❌ `a9-sprint-plan` (96%) — facts 100%; judge 9/10 — Excellent coherent sprint design with strong thematic grouping (backup-reliability cluster), correct prioritization (201 first), crisp one-sentence justifications, and explicit exclusions with clear reasoning. Correctly excludes #205 (blocked) and #206 (done). Observed system details (load, RAM, disk, service state, NAS unreachability, timestamps) are plausible and consistent with the reference facts. Minor deduction only for including #204 in the exclusion rationale when the rubric suggests it as acceptable filler—the model chose not to use it, which is defensible but slightly conservative.

## Suite: judged v2 — 2/6 (62%)
_Transcript: `eval-logs/qwen3.8-27b-nvfp4/2026-08-20-r1/judged/2026-08-21T03-26-19-00-00_judged_2ayWC5BXbESVfmtk3Rp99L.eval` (open with `inspect view`)._
- ❌ `constrained-list` (80%) — All 5 checks are present with proper formatting (1.-5., no extra numbering). Each line is 8 words or fewer. The checks cover good diagnostic ground: filesystem usage (df), directory analysis (du), file discovery (find), inode exhaustion (df -i), and mount/quota review. Minor deduction because the answer omits some valuable checks like log growth, deleted-but-open files, or package caches that would provide more comprehensive coverage.
- ❌ `explain-config` (0%) — No answer was provided to grade.
- ❌ `plan-migration` (0%) — The model provided no answer to grade. An empty response cannot demonstrate plan quality, constraint awareness, or the required rollback step.
- ❌ `professional-rewrite` (90%) — All three factual complaints preserved (dashboard down since 6am, status page showing incorrect status, ticket #48213 unanswered for four hours), premium SLA expectation clearly stated, professional tone throughout, and concise. Minor deduction only for slightly softer language ('we expect' vs. explicit SLA breach language) compared to the original's firm demand.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ✅ `summarize-incident` — All three bullet points are accurate, concise, and directly supported by the log. The answer correctly identifies the OOM kill and restart, the backup failure due to too many connections, and the resolution (max_connections 100→200). No fabricated facts or contradictions present.

## Suite: vision v2 — 13/15 (90%)
_Transcript: `eval-logs/qwen3.8-27b-nvfp4/2026-08-20-r1/vision/2026-08-21T03-28-52-00-00_vision_gdN5Kfh6cKpfVTZmUTwJPX.eval` (open with `inspect view`)._
- ❌ `p1-animal` (50%) — facts 50% (missing: corgi)
- ✅ `p2-hardware` — facts 100%
- ✅ `p3-tools` — facts 100%
- ✅ `p4-count-people` — facts 100%
- ✅ `p5-activity` — facts 100%
- ✅ `v1-dashboard-down` — facts 100%
- ❌ `v10-render-clean` (0%) — EMPTY ANSWER — facts 0% (missing: correct | no defect | no issue | fine | properly | looks good | renders well)
- ✅ `v2-gauge-disk` — facts 100%
- ✅ `v3-chart-peak` — facts 100%
- ✅ `v4-terminal-df` — facts 100%
- ✅ `v5-journal-error` — facts 100%
- ✅ `v6-table-registry` — facts 100%
- ✅ `v7-count-warnings` — facts 100%
- ✅ `v8-diagram-backup` — facts 100%
- ✅ `v9-render-broken` — facts 100%

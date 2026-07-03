# Eval — claude-haiku-4-5 (2026-07-02)

**Verdict: 🌐 baseline** · `None`

## Operational
- served: True
- cold start: None s
- GPU used: None MiB
- TTFT: None s
- decode tok/s: None
- tokens: 421,523 in / 42,740 out · est cost $0.68
- judge overhead: 10,280 in / 1,864 out · $0.02

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/claude-haiku-4-5/2026-07-02/tools/2026-07-02T18-13-59-00-00_tools_kouSGwjkFjcLRfncU5BSL5.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'The file `/etc/kvllm/kvllm.conf` could not be read because i'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The weather in Paris is currently **21°C (about 70°F)** and '
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

## Suite: code v1 — 15/15 (100%)
_iteration (recovered after a failing test run): 100%_
_Transcript: `eval-logs/claude-haiku-4-5/2026-07-02/code/2026-07-02T18-14-03-00-00_coding_nKvHe8WDTPqnBzfCWmXifF.eval` (open with `inspect view`)._
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

## Suite: agentic v2 — 3/9 (68%)
_Transcript: `eval-logs/claude-haiku-4-5/2026-07-02/agentic/2026-07-02T18-24-09-00-00_agentic_mPBS5owwPdXQsxHCGSYa2p.eval` (open with `inspect view`)._
- ✅ `a1-failed-unit` — facts 100%; judge 10/10 — The model correctly identifies backup-sync.service as the only failed unit, accurately names rsync connection failure as the cause, and specifies the target host 192.168.1.44. The answer is concise, actionable for Ken (check the NAS), and all observed details (timestamps, error codes, service status) are plausibly from real system investigation without contradicting reference facts.
- ❌ `a2-disk-growth` (20%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 33% (missing: 512 | 0.5g | half; rotat | truncat | logrotate | archiv | compress); judge 0/10 — The model fails to name the culprit file clearly, provide its size, or recommend a safe cleanup method. The answer is incomplete and does not address the task requirements.
- ❌ `a3-oom-chain` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: oom | out of memory; postgres; too many connections); judge 0/10 — The model provided no substantive answer—only a meta-statement ('Let me try a different approach') without any actual investigation, causal analysis, or findings. This fails to address the task entirely.
- ❌ `a4-cron-typo` (96%) — facts 100%; judge 9/10 — The model correctly identified the root cause (typo in cron file: .hs vs .sh), provided accurate evidence from logs and file system, and offered appropriate fixes. Minor deduction because the recommended fix suggests renaming the script to .hs, which is backwards—the standard fix is to correct the cron file to reference .sh (the existing, correct script).
- ❌ `a5-wi-triage` (0%) — FABRICATION → 0. facts 67% (missing: ready: expected [103, 106], got [103, 105, 106]); judge 2/10 — The model fabricated detailed work item data (timestamps, update dates, descriptions like 'key list finalized', 'script skeleton committed', 'merged and deployed 7/1') that contradict the reference facts. Most critically, it placed #105 in the 'ready' category when the rubric explicitly states ready = #103 and #106 only, and #105 should not be in any category (bonus only for flagging it). The final answer line lists #105 in ready, which is incorrect.
- ❌ `a6-wi-status-report` (96%) — facts 100%; judge 9/10 — The answer correctly identifies the failed backup-sync.service as a critical issue and prominently features it in box health. The three actions are concrete, properly cited (#105, #102, #103), and well-prioritized with clear reasoning (close #105 to unblock #102, then execute #103). All work items exist per reference facts. The only minor gap is that #106 (also ready) is not mentioned as an alternative or parallel action, though the three chosen actions are defensible and actionable.
- ✅ `a7-port-conflict` — facts 100%; judge 10/10 — The model identified all three required elements: the bind error on port 8800, the specific port number, and the stray python3 -m http.server 8800 process (PID 57). The diagnosis is complete, accurate, and directly addresses the root cause without contradicting reference facts.
- ✅ `a8-honesty` — facts 100%; judge 10/10 — The model correctly identified that the system is healthy, explicitly checked services (all active), logs (no errors), and disk (41% utilization, unremarkable), and reported the all-clear plainly without inventing problems. All observed metrics are plausible and consistent with reference facts.
- ❌ `a9-sprint-plan` (96%) — facts 100%; judge 9/10 — Excellent sprint plan with strong coherence, correct prioritization (201 first), clear one-sentence justifications, and explicit exclusions with reasoning. The model correctly identified the backup-reliability cluster, excluded blocked #205 and completed #206, and made a deliberate decision to defer #204. Minor deduction only for slight over-explanation (not a violation, but slightly verbose for a strict grading standard).

## Suite: judged v1 — 2/6 (87%)
_Transcript: `eval-logs/claude-haiku-4-5/2026-07-02/judged/2026-07-02T18-15-36-00-00_judged_RXdKbLxwecka9W9gaoR7Vc.eval` (open with `inspect view`)._
- ❌ `constrained-list` (60%) — The answer provides exactly 5 checks with correct formatting (1.-5., no numbering beyond that). All checks are 8 words or fewer and mechanically valid. However, coverage is somewhat limited: checks 1-3 are overlapping (all df/du variants), check 4 (inodes) is useful but less common for typical disk usage diagnosis, and check 5 (iostat) monitors I/O performance rather than disk usage itself. Missing are important checks like log file growth, Docker images/containers, package manager caches, or deleted-but-open files—which are common culprits in real-world scenarios.
- ❌ `explain-config` (90%) — The answer correctly explains what runs (vLLM server with model from env file), accurately describes Restart=on-failure semantics, and identifies a valid operational caveat (env file dependency). The 15-minute timeout is correctly noted. Minor deduction for not explicitly mentioning that the model choice is gated by KVLLM_MODEL_KEY variable, though this is implied.
- ❌ `plan-migration` (80%) — The plan demonstrates strong understanding of replication-based migration with sensible ordering (setup → replicate → read-only → promote → verify), respects the 5-minute downtime constraint (~4 minutes claimed), includes an explicit rollback step, and stays within 6 steps. Minor deduction for using logical replication (pg_basebackup) terminology inconsistently and not explicitly stating that the read-only window is the actual downtime period, which could cause confusion about when applications experience unavailability.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, status page incorrectly showing 'all systems operational', ticket #48213 unanswered for four hours), maintains the premium SLA expectation, uses firm but professional tone without hostility, and is concise. All reference facts are accurate and intact.
- ✅ `strict-json` — The model output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (90%) — The answer correctly identifies all three required elements with accurate facts from the log: OOM kill, backup failure due to too many connections, and the resolution of raising max_connections from 100 to 200. The causality is clear and concise. Minor deduction because the root cause bullet conflates two separate issues (OOM and connection limits) into one statement, when the log shows OOM was the initial problem and connection limits only became relevant after restart.

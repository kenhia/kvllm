# Eval — qwen3.6-35b-a3b-awq (2026-07-03)

**Verdict: ⚠️ has issues** · `QuantTrio/Qwen3.6-35B-A3B-AWQ`

## Operational
- served: True
- cold start: 64.0 s
- GPU used: 28858 MiB
- TTFT: 0.06 s
- decode tok/s: 42.1
- tokens: 982 in / 10,294 out
- judge overhead: 3,015 in / 700 out · $0.01

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

## Suite: agentic v2 — 0/8 (8%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-02/agentic/2026-07-03T00-46-02-00-00_agentic_ng73RicyfGwtfEFrqHFmVH.eval` (open with `inspect view`)._
- ❌ `a2-disk-growth` (0%) — no score recorded
- ❌ `a3-oom-chain` (0%) — no score recorded
- ❌ `a4-cron-typo` (0%) — no score recorded
- ❌ `a5-wi-triage` (64%) — facts 67% (missing: ready: expected [103, 106], got [103, 105, 106]); judge 6/10 — The model correctly identified stale (#101, #104) and blocked (#102) items with sound reasoning and proper date calculations. However, it incorrectly included #105 in the ready category when the rubric specifies ready should be only #103 and #106; while the bonus observation about #105 being effectively done is noted, including it in the final categorization contradicts the reference facts.
- ❌ `a6-wi-status-report` (0%) — no score recorded
- ❌ `a7-port-conflict` (0%) — CUT OFF BY MESSAGE LIMIT mid-investigation. facts 0% (missing: 8800; address already in use | already in use; http.server | python); judge 0/10 — The model provided no diagnostic output, analysis, or answer to the question. The response contains only internal reasoning fragments and empty text with no investigation of the service failure, port binding issue, or stray process.
- ❌ `a8-honesty` (0%) — no score recorded
- ❌ `a9-sprint-plan` (0%) — no score recorded

## Suite: judged v2 — 2/6 (90%)
_Transcript: `eval-logs/qwen3.6-35b-a3b-awq/2026-07-03/judged/2026-07-03T02-47-41-00-00_judged_DKgsmZkgmUJpdrr5SGhkdz.eval` (open with `inspect view`)._
- ❌ `constrained-list` (70%) — All 5 checks are present with correct formatting (1.-5., no extra numbering). The checks cover useful diagnostic areas: filesystem space (df), large files (find), inodes (df), directory sizes (du), and disk activity (iostat). However, the answer misses important high-usage scenarios like log growth, container/image bloat, and deleted-but-open files, which are common causes in real homelab environments.
- ❌ `explain-config` (90%) — The answer correctly explains what runs (vLLM server via uv/Python with env-file config), accurately describes Restart=on-failure semantics (only on crash/non-zero exit, not clean stops), and identifies the 900s timeout as a key operational caveat for cold model loads. Minor deduction only because it doesn't explicitly name KVLLM_MODEL_KEY or mention it gates the model choice, though the substance is captured.
- ❌ `plan-migration` (90%) — The plan is well-ordered, constraint-aware, and includes all required elements. Replication and sync occur before cutover (step 1–2), cutover is brief (~2 min, well under 5-min limit), validation precedes decommissioning, and a clear rollback step is present (step 5). The only minor weakness is that step 5's rollback doesn't explicitly address whether Machine B's promoted state could cause split-brain issues if A restarts independently, though this is a minor edge case for a homelab context.
- ✅ `professional-rewrite` — The rewrite preserves all three factual complaints (dashboard down since 6am, incorrect status page, ticket #48213 unanswered for four hours), retains the premium SLA expectation, maintains firm professionalism without hostility, and is concise. No facts are dropped or contradicted.
- ✅ `strict-json` — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- ❌ `summarize-incident` (90%) — The answer correctly identifies all three required elements with accurate facts from the log: OOM kill, backup failure due to connection limit, and the fix (max_connections 100→200). The causality is clear and concise. Minor deduction because the first bullet conflates the crash and backup failure into one point rather than cleanly separating 'what broke' as the primary incident.

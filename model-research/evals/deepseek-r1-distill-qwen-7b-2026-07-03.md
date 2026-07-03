# Eval — deepseek-r1-distill-qwen-7b (2026-07-03)

**Verdict: ✅ worth trying** · `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`

## Operational
- served: True
- cold start: 30.0 s
- GPU used: 29432 MiB
- TTFT: 0.01 s
- decode tok/s: 104.8
- tokens: 941 in / 4,075 out
- judge overhead: 3,515 in / 1,025 out · $0.01

## Suite: judged v2 — 0/6 (58%)
_Transcript: `eval-logs/deepseek-r1-distill-qwen-7b/2026-07-03/judged/2026-07-03T03-16-08-00-00_judged_ZP7zpU5ouAGLQTiqdMxEH2.eval` (open with `inspect view`)._
- ❌ `constrained-list` (40%) — The answer has exactly 5 checks with proper formatting (1.-5.), meeting structural requirements. However, content quality is poor: checks 3, 4, and 5 contain incorrect or nonsensical commands that don't actually diagnose disk usage (e.g., `ls / | wc -l` doesn't count open files, `cat /proc/sys/vm/dm SwpSize` is invalid syntax). Check 2 measures I/O latency rather than disk usage. Only check 1 is genuinely useful. The answer lacks coverage of critical diagnostics like `du`, log growth, container images, or package caches. [mechanical: 5 item(s) over 8 words → cap 4/10]
- ❌ `explain-config` (60%) — The answer correctly identifies the service (vLLM server), correctly states Restart=on-failure semantics, and accurately converts the 900s timeout to 15 minutes. However, it misses the critical caveat about the environment file gating the model choice (KVLLM_MODEL_KEY), and the network dependency caveat is weak since After=network-online.target is standard practice, not a meaningful operational caveat.
- ❌ `plan-migration` (10%) — This plan fundamentally violates the 5-minute downtime constraint by using dump/restore during the cutover window, which is unsuitable for any non-trivial database. The 'rollback plan' mentioned is vague and not an explicit step; step 6 shuts down machine A without any concrete rollback procedure, making recovery impossible if issues arise post-migration.
- ❌ `professional-rewrite` (90%) — All three factual complaints are preserved (dashboard down since 6am, status page showing incorrect 'All Systems Operational', ticket #48213 unanswered for four hours), the premium SLA expectation is retained, and the tone is professional and firm without hostility. The rewrite is concise and well-structured.
- ❌ `strict-json` (90%) — All four required keys present with correct values and parseable JSON. Minor deduction for status value capitalization: 'Degraded' instead of 'degraded' as specified in the rubric.
- ❌ `summarize-incident` (60%) — The answer correctly identifies all three elements (OOM kill, too many connections failure, max_connections increase), but conflates the root causes. The OOM kill and the 'too many connections' error are two separate incidents with different causes—the answer muddies this causality by suggesting the KILL signal caused the connection limit issue, when in fact the backup failed independently due to connection exhaustion after postgres restarted.

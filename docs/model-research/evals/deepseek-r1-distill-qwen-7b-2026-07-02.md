# Eval — deepseek-r1-distill-qwen-7b (2026-07-02)

**Verdict: ✅ worth trying** · `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`

## Operational
- served: True
- cold start: 24.0 s
- GPU used: 29432 MiB
- TTFT: 0.01 s
- decode tok/s: 104.8
- tokens: 941 in / 3,470 out
- judge overhead: 2,900 in / 897 out · $0.01

## Suite: judged v1 — 0/6 (57%)
_Transcript: `eval-logs/deepseek-r1-distill-qwen-7b/2026-07-02/judged/2026-07-02T23-39-29-00-00_judged_PwkcZYWg7U6vBaRUd998mZ.eval` (open with `inspect view`)._
- ❌ `constrained-list` (40%) — The answer has exactly 5 checks with proper formatting (1.-5.), meeting structural requirements. However, content quality is poor: checks 3, 4, and 5 contain incorrect or nonsensical commands that don't actually diagnose disk usage (ls / | wc -l doesn't count open files; /proc/sys/vm/dm_SwpSize doesn't exist; dmesg | grep latency won't find disk usage issues). Only checks 1-2 are genuinely useful for disk usage diagnosis. The answer lacks coverage of critical areas like du for directory sizes, log growth, docker images, package caches, and deleted-but-open files. [mechanical: 5 item(s) over 8 words → cap 4/10]
- ❌ `explain-config` (60%) — The answer correctly identifies the service (vLLM server), correctly states Restart=on-failure semantics, and accurately converts the 900s timeout to 15 minutes. However, it misses the critical caveat about the environment file gating the model choice (KVLLM_MODEL_KEY), and the network dependency caveat is weak since network-online.target is standard practice rather than a notable operational concern.
- ❌ `plan-migration` (0%) — The model provided no answer to grade. An empty response cannot demonstrate plan quality, constraint awareness, or the required rollback step.
- ❌ `professional-rewrite` (90%) — All three factual complaints are preserved (dashboard down since 6am, status page showing incorrect 'All Systems Operational', ticket #48213 unanswered for four hours), the premium SLA expectation is retained, and the tone is professional and firm without hostility. The rewrite is concise and well-structured.
- ❌ `strict-json` (90%) — All four required keys present with correct values and parseable JSON. Minor deduction for status value capitalization: 'Degraded' instead of 'degraded' as specified in the rubric.
- ❌ `summarize-incident` (60%) — The answer correctly identifies all three elements (OOM kill, too many connections failure, max_connections increase), but conflates the root causes. The OOM kill and the 'too many connections' error are two separate incidents with different causes—the answer muddies this causality by suggesting the KILL signal caused the connection limit issue, when in fact the backup failed independently due to connection exhaustion after postgres restarted.

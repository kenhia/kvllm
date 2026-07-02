# Eval — qwen2.5-coder-7b-instruct (2026-07-02)

**Verdict: ⚠️ has issues** · `Qwen/Qwen2.5-Coder-7B-Instruct`

## Operational
- served: True
- cold start: 22.0 s
- GPU used: 29414 MiB
- TTFT: 0.02 s
- decode tok/s: 105.5

## Suite: tools v2 — 3/11 (27%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-02/2026-07-02T03-28-45-00-00_tools_8dPZt4HeRU4BUzybTnLTm3.eval` (open with `inspect view`)._
- ❌ `array_args` — no tool call emitted
- ❌ `distractor_tool` — no tool call emitted
- ❌ `enum_arg` — no tool call emitted
- ❌ `error_recovery` — never called read_file
- ❌ `exact_args` — no tool call emitted
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ❌ `integer_args` — no tool call emitted
- ❌ `multi_turn_roundtrip` — no initial tool call
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ❌ `single_call` — no tool call emitted

## Suite: code v1 — 0/8 (0%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-02/code/2026-07-02T07-07-55-00-00_coding_6mpWZZRfe52t2kRteXU2jB.eval` (open with `inspect view`)._
- ❌ `c1-dedupe` (0%) — no score recorded
- ❌ `c1-merge-intervals` (0%) — no score recorded
- ❌ `c1-parse-size` (0%) — no score recorded
- ❌ `c2-logsum` (0%) — no score recorded
- ❌ `c3-inventory` (0%) — no score recorded
- ❌ `c3-stats-pure` (0%) — no score recorded
- ❌ `c3-todo-due` (0%) — no score recorded
- ❌ `c4-lru-bugs` (0%) — no score recorded

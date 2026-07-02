# Eval — qwen2.5-coder-7b-instruct (2026-06-30)

**Verdict: ⚠️ has issues** · `Qwen/Qwen2.5-Coder-7B-Instruct`

## Operational
- served: True
- cold start: 24.0 s
- GPU used: 29414 MiB
- tokens/sec: 90.3

## Suite: tools — 3/7 (43%)
- ❌ `single_call` — no tool call emitted
- ❌ `enum_arg` — no tool call emitted
- ❌ `integer_args` — no tool call emitted
- ✅ `no_unneeded_call` — no tool call
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ❌ `multi_turn_roundtrip` — no initial tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)

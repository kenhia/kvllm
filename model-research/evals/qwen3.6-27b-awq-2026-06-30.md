# Eval — qwen3.6-27b-awq (2026-06-30)

**Verdict: ⚠️ has issues** · `QuantTrio/Qwen3.6-27B-AWQ`

## Operational
- served: True
- cold start: 88.0 s
- GPU used: 28912 MiB
- tokens/sec: 2.5

## Suite: tools — 7/7 (100%)
- ✅ `single_call` — get_weather({'city': 'Paris'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `no_unneeded_call` — no tool call
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe current weather in Paris is 21°C.'
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)

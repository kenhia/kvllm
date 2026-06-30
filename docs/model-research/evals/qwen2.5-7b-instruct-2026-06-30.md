# Eval — qwen2.5-7b-instruct (2026-06-30)

**Verdict: ✅ worth trying** · `Qwen/Qwen2.5-7B-Instruct`

## Operational
- served: True
- cold start: 22.0 s
- GPU used: 29414 MiB
- tokens/sec: 90.5

## Suite: tools — 7/7 (100%)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `no_unneeded_call` — no tool call
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current temperature in Paris is 21 degrees Celsius.'
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)

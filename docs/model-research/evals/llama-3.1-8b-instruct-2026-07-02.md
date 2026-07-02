# Eval — llama-3.1-8b-instruct (2026-07-02)

**Verdict: ✅ worth trying** · `meta-llama/Llama-3.1-8B-Instruct`

## Operational
- served: True
- cold start: 158.0 s
- GPU used: 29480 MiB
- TTFT: 0.02 s
- decode tok/s: 102.0

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/llama-3.1-8b-instruct/2026-07-02/2026-07-02T05-36-12-00-00_tools_mY57XoRVpa8Su8mLtK4nst.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'In this case, the function call was unable to read the file '
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'This JSON response indicates that the current temperature in'
- ❌ `no_unneeded_call` — unexpected call to get_weather
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

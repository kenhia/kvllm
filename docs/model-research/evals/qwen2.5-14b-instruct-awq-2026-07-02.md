# Eval — qwen2.5-14b-instruct-awq (2026-07-02)

**Verdict: ✅ worth trying** · `Qwen/Qwen2.5-14B-Instruct-AWQ`

## Operational
- served: True
- cold start: 160.0 s
- GPU used: 28564 MiB
- TTFT: 0.01 s
- decode tok/s: 144.4

## Suite: tools v2 — 10/11 (91%)
_Transcript: `eval-logs/qwen2.5-14b-instruct-awq/2026-07-02/2026-07-02T05-39-15-00-00_tools_3LBSWQeVAxULkvETcE9FDB.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'I encountered an error while trying to read the file `/etc/k'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current temperature in Paris is 21 degrees Celsius.'
- ✅ `no_unneeded_call` — no tool call
- ❌ `parallel_calls` — matched 1/2 parallel calls (got 1)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

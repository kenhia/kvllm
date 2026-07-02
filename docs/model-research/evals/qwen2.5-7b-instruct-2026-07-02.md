# Eval — qwen2.5-7b-instruct (2026-07-02)

**Verdict: ✅ worth trying** · `Qwen/Qwen2.5-7B-Instruct`

## Operational
- served: True
- cold start: 24.0 s
- GPU used: 29414 MiB
- TTFT: 0.02 s
- decode tok/s: 105.5

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-02/2026-07-02T05-26-25-00-00_tools_ftxqUVMBaTvtGR22Gdmb4Y.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'It seems that the file `/etc/kvllm/kvllm.conf` does not exis'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current temperature in Paris is 21 degrees Celsius.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

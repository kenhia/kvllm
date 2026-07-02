# Eval — qwen3-vl-8b-instruct (2026-07-02)

**Verdict: ✅ worth trying** · `Qwen/Qwen3-VL-8B-Instruct`

## Operational
- served: True
- cold start: 206.0 s
- GPU used: 27764 MiB
- TTFT: 0.01 s
- decode tok/s: 98.4

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3-vl-8b-instruct/2026-07-02/2026-07-02T05-44-33-00-00_tools_hcJkf9yXRq2aMPjLPbyB8L.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: 'The file `/etc/kvllm/kvllm.conf` was not found. Therefore, I'
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin', 'unit': 'celsius'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: 'The current weather in Paris is 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris', 'unit': 'celsius'})

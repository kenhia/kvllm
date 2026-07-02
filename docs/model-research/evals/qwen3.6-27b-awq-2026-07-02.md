# Eval — qwen3.6-27b-awq (2026-07-02)

**Verdict: ✅ worth trying** · `QuantTrio/Qwen3.6-27B-AWQ`

## Operational
- served: True
- cold start: 56.0 s
- GPU used: 28910 MiB
- TTFT: 0.07 s
- decode tok/s: 45.5

## Suite: tools v2 — 11/11 (100%)
_Transcript: `eval-logs/qwen3.6-27b-awq/2026-07-02/2026-07-02T06-14-43-00-00_tools_Zm5ueDUUEky2uBjSRD4S8N.eval` (open with `inspect view`)._
- ✅ `array_args` — run_command({'host': 'kubsdb', 'argv': ['df', '-h']})
- ✅ `distractor_tool` — restart_service({'name': 'nginx'})
- ✅ `enum_arg` — get_weather({'city': 'Tokyo', 'unit': 'fahrenheit'})
- ✅ `error_recovery` — reported failure: "\n\nI couldn't read the file `/etc/kvllm/kvllm.conf` because i"
- ✅ `exact_args` — set_fan_speed({'device_id': 'gpu0', 'percent': 70})
- ✅ `forced_choice` — get_weather({'city': 'Berlin'})
- ✅ `integer_args` — add({'a': 17, 'b': 25})
- ✅ `multi_turn_roundtrip` — round-trip ok: '\n\nThe current weather in Paris is 21°C.'
- ✅ `no_unneeded_call` — no tool call
- ✅ `parallel_calls` — matched 2/2 parallel calls (got 2)
- ✅ `single_call` — get_weather({'city': 'Paris'})

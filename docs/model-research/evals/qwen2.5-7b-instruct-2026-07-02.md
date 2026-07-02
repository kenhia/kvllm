# Eval — qwen2.5-7b-instruct (2026-07-02)

**Verdict: ✅ worth trying** · `Qwen/Qwen2.5-7B-Instruct`

## Operational
- served: True
- cold start: 22.0 s
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

## Suite: code v1 — 4/15 (53%)
_iteration (recovered after a failing test run): 0%_
_Transcript: `eval-logs/qwen2.5-7b-instruct/2026-07-02/code/2026-07-02T07-20-03-00-00_coding_gASxh9XmyCisNgZVYWXuZE.eval` (open with `inspect view`)._
- ✅ `c1-dedupe` — 7/7 hidden tests
- ✅ `c1-merge-intervals` — 7/7 hidden tests
- ❌ `c1-parse-duration` (75%) — 6/8 hidden tests; failed: test_hours_minutes, test_minutes_seconds
- ❌ `c1-parse-size` (75%) — 6/8 hidden tests; failed: test_trailing_b, test_invalid_raises
- ✅ `c1-slugify` — 8/8 hidden tests
- ❌ `c1-tail-lines` (71%) — 5/7 hidden tests; failed: test_basic, test_no_final_newline
- ❌ `c2-csvfilter` (40%) — 2/5 hidden tests; failed: test_no_conditions_returns_all, test_multi_condition_and, test_quoting_preserved
- ❌ `c2-dumon` (83%) — 5/6 hidden tests; failed: test_rounding_to_nearest_mb
- ✅ `c2-jsonmerge` — 6/6 hidden tests
- ❌ `c2-logsum` (0%) — 0/4 hidden tests; failed: test_ordering_and_ties, test_blank_lines_ignored, test_top_errors_capped_at_three, test_error_message_tie_alpha
- ❌ `c3-inventory` (12%) — 1/8 hidden tests; failed: test_two_instances_independent, test_remove_missing_is_noop, test_remove_more_than_present_clamps, test_three_instances_independent, test_remove_then_readd
- ❌ `c3-stats-pure` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_stats
- ❌ `c3-todo-due` (40%) — 4/10 hidden tests; failed: test_due_before_keeps_earlier, test_due_before_excludes_none_due, test_status_and_due_combine, test_due_before_is_strict_boundary, test_done_and_due_combine
- ❌ `c4-lru-bugs` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_lru
- ❌ `c4-rolling` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_rolling

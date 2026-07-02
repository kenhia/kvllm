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

## Suite: code v1 — 0/15 (5%)
_Transcript: `eval-logs/qwen2.5-coder-7b-instruct/2026-07-02/code/2026-07-02T07-12-34-00-00_coding_G5pHPqTxjy6rWGMzs6Q78L.eval` (open with `inspect view`)._
- ❌ `c1-dedupe` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_dedupe
- ❌ `c1-merge-intervals` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_merge_intervals
- ❌ `c1-parse-duration` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_parse_duration
- ❌ `c1-parse-size` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_parse_size
- ❌ `c1-slugify` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_slugify
- ❌ `c1-tail-lines` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_tail_lines
- ❌ `c2-csvfilter` (0%) — 0/5 hidden tests; failed: test_no_conditions_returns_all, test_single_condition, test_multi_condition_and, test_no_matches_header_only, test_quoting_preserved
- ❌ `c2-dumon` (0%) — 0/6 hidden tests; failed: test_basic_threshold_and_order, test_two_spaces_before_path, test_strictly_greater, test_tie_broken_by_path, test_rounding_to_nearest_mb
- ❌ `c2-jsonmerge` (0%) — 0/6 hidden tests; failed: test_deep_merge_recurses_dicts, test_later_scalar_wins, test_array_replaces_not_merges, test_type_mismatch_replaces, test_three_files
- ❌ `c2-logsum` (0%) — 0/4 hidden tests; failed: test_ordering_and_ties, test_blank_lines_ignored, test_top_errors_capped_at_three, test_error_message_tie_alpha
- ❌ `c3-inventory` (12%) — 1/8 hidden tests; failed: test_two_instances_independent, test_remove_missing_is_noop, test_remove_more_than_present_clamps, test_three_instances_independent, test_remove_then_readd
- ❌ `c3-stats-pure` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_stats
- ❌ `c3-todo-due` (40%) — 4/10 hidden tests; failed: test_due_before_keeps_earlier, test_due_before_excludes_none_due, test_status_and_due_combine, test_due_before_is_strict_boundary, test_done_and_due_combine
- ❌ `c4-lru-bugs` (25%) — 2/8 hidden tests; failed: test_capacity_evicts_lru, test_get_refreshes_recency, test_overwrite_refreshes_recency, test_repeated_get_keeps_key_alive, test_capacity_one
- ❌ `c4-rolling` (0%) — 0/1 hidden tests; failed: .hidden_tests.test_rolling

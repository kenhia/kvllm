"""interview.serve — override and log-parsing logic (pure; no GPU)."""

from __future__ import annotations

from interview.serve import apply_overrides, parse_kv_stats


def _qwen():
    return {
        "hf_repo": "org/qwen",
        "max_model_len": 131072,
        "kv_cache_dtype": "fp8",
        "chat_template_kwargs": {"reasoning_effort": "medium"},
        "speculative_config": {"method": "mtp", "num_speculative_tokens": 3},
    }


def test_overrides_leave_entry_untouched():
    e = _qwen()
    apply_overrides(e, max_model_len=65536, no_spec=True)
    assert e["max_model_len"] == 131072 and "speculative_config" in e


def test_kv_auto_clears_and_no_spec_drops():
    e = apply_overrides(_qwen(), kv_cache_dtype="auto", no_spec=True)
    assert "kv_cache_dtype" not in e and "speculative_config" not in e


def test_chat_kwargs_merge_over_defaults():
    e = apply_overrides(_qwen(), chat_kwargs={"enable_thinking": True})
    assert e["chat_template_kwargs"] == {
        "reasoning_effort": "medium",
        "enable_thinking": True,
    }
    e = apply_overrides(_qwen(), chat_kwargs={"reasoning_effort": "xhigh"})
    assert e["chat_template_kwargs"] == {"reasoning_effort": "xhigh"}


def test_parse_kv_stats_reads_last_report():
    log = (
        "INFO [x] model weights take 21.34GiB; non_torch_memory takes 0.11GiB; "
        "PyTorch activation peak memory takes 3.55GiB; the rest of the memory "
        "reserved for KV Cache is 4.27GiB.\n"
        "INFO [x] Available KV cache memory: 4.27 GiB\n"
        "INFO [x] GPU KV cache size: 129,615 tokens\n"
        "INFO [x] Maximum concurrency for 131,072 tokens per request: 1.98x\n"
    )
    s = parse_kv_stats(log)
    assert s["kv_tokens"] == 129615
    assert s["concurrency_x"] == 1.98
    assert s["kv_pool_gib"] == 4.27
    assert s["weights_gib"] == 21.34
    assert s["kib_per_token"] == 34.5


def test_parse_kv_stats_empty_on_failed_start():
    assert parse_kv_stats("ValueError: no KV for you") == {}


def test_gpu_util_override_lands_on_the_entry():
    # The registry reads the fraction from the entry first, so an envelope override
    # has to be written there — passing it to build_serve_argv would be shadowed by
    # an entry that carries its own (qwen3.8 at 0.95 since sprint 20).
    e = apply_overrides(_qwen(), gpu_util="0.90")
    assert e["gpu_memory_utilization"] == 0.90
    assert "gpu_memory_utilization" not in _qwen()
    assert "gpu_memory_utilization" not in apply_overrides(_qwen())

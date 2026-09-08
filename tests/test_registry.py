"""kvllm.registry unit tests — serve-argv construction (pure config logic)."""

from __future__ import annotations

from kvllm.registry import build_serve_argv


def _entry(**kw):
    return {"hf_repo": "org/model", **kw}


def test_extra_args_appended_verbatim():
    argv = build_serve_argv(
        "m",
        _entry(extra_args=["--tokenizer-mode", "mistral", "--load-format", "mistral"]),
    )
    assert argv[-4:] == ["--tokenizer-mode", "mistral", "--load-format", "mistral"]


def test_no_extra_args_field_is_fine():
    argv = build_serve_argv("m", _entry())
    assert argv[:3] == ["vllm", "serve", "org/model"]


def test_tool_parser_enables_auto_tool_choice():
    argv = build_serve_argv("m", _entry(tool_parser="glm47"))
    assert "--enable-auto-tool-choice" in argv
    assert argv[argv.index("--tool-call-parser") + 1] == "glm47"


def test_kv_cache_dtype_emitted():
    argv = build_serve_argv("m", _entry(kv_cache_dtype="fp8"))
    assert argv[argv.index("--kv-cache-dtype") + 1] == "fp8"


def test_kv_cache_dtype_absent_by_default():
    assert "--kv-cache-dtype" not in build_serve_argv("m", _entry())


def test_kv_cache_dtype_precedes_extra_args():
    # extra_args stays the last-word escape hatch: a model can still override
    # a dedicated field by repeating the flag after it.
    argv = build_serve_argv(
        "m", _entry(kv_cache_dtype="fp8", extra_args=["--kv-cache-dtype", "auto"])
    )
    assert argv[-2:] == ["--kv-cache-dtype", "auto"]


def test_max_num_batched_tokens_absent_by_default():
    # Deliberately NOT pinned globally: vLLM derives this per model, and gemma-4's
    # derived value is 2496. A global pin at a plausible-looking 8192 inflates
    # activation memory enough to fail engine startup on this card.
    assert "--max-num-batched-tokens" not in build_serve_argv("m", _entry())


def test_max_num_batched_tokens_emitted_when_set():
    argv = build_serve_argv("m", _entry(max_num_batched_tokens=16384))
    assert argv[argv.index("--max-num-batched-tokens") + 1] == "16384"
    assert argv.count("--max-num-batched-tokens") == 1


def test_max_num_batched_tokens_precedes_extra_args():
    argv = build_serve_argv(
        "m",
        _entry(
            max_num_batched_tokens=16384,
            extra_args=["--max-num-batched-tokens", "4096"],
        ),
    )
    assert argv[-2:] == ["--max-num-batched-tokens", "4096"]


def test_speculative_config_absent_by_default():
    assert "--speculative-config" not in build_serve_argv("m", _entry())


def test_speculative_config_emitted_as_compact_json():
    argv = build_serve_argv(
        "m", _entry(speculative_config={"method": "mtp", "num_speculative_tokens": 3})
    )
    i = argv.index("--speculative-config")
    assert argv[i + 1] == '{"method":"mtp","num_speculative_tokens":3}'


def test_chat_template_kwargs_absent_by_default():
    assert "--default-chat-template-kwargs" not in build_serve_argv("m", _entry())


def test_chat_template_kwargs_emitted_as_compact_json():
    argv = build_serve_argv(
        "m", _entry(chat_template_kwargs={"reasoning_effort": "medium"})
    )
    i = argv.index("--default-chat-template-kwargs")
    assert argv[i + 1] == '{"reasoning_effort":"medium"}'


def test_chat_template_kwargs_precede_extra_args():
    # extra_args keeps the last word, as for every other first-class field.
    argv = build_serve_argv(
        "m",
        _entry(
            chat_template_kwargs={"enable_thinking": True},
            extra_args=["--default-chat-template-kwargs", "{}"],
        ),
    )
    assert argv[-2:] == ["--default-chat-template-kwargs", "{}"]

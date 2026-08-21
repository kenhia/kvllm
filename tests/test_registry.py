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

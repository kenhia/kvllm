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

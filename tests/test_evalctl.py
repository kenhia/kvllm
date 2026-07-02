"""Unit tests for kvllm.evalctl.serve_error — root-cause extraction from serve logs."""

from __future__ import annotations

from kvllm.evalctl import serve_error


def _write(tmp_path, text):
    p = tmp_path / "serve.log"
    p.write_text(text)
    return p


def test_serve_error_prefers_root_cause_over_wrappers(tmp_path):
    # the qwen3-8b-fp8 shape: EngineCore root cause, then APIServer re-raise machinery
    log = _write(
        tmp_path,
        "(EngineCore pid=1) ERROR 07-02 [core.py:1231] RuntimeError: Assertion error "
        "(layout.hpp:59): Unknown SF transformation\n"
        "(APIServer pid=2)     raise RuntimeError(\n"
        "(APIServer pid=2) RuntimeError: Engine core initialization failed. "
        "See root cause above. Failed core proc(s): {}\n",
    )
    msg = serve_error(log)
    assert "Unknown SF transformation" in msg
    assert "See root cause" not in msg


def test_serve_error_oom_beats_runtime_wrapper(tmp_path):
    log = _write(
        tmp_path,
        "(EngineCore pid=1) torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 1 GiB\n"
        "(APIServer pid=2) RuntimeError: Engine core initialization failed. See root cause above.\n",
    )
    assert "CUDA out of memory" in serve_error(log)


def test_serve_error_empty_log(tmp_path):
    assert serve_error(_write(tmp_path, "all fine here\n")) == ""


def test_serve_error_missing_file(tmp_path):
    assert serve_error(tmp_path / "nope.log") == ""

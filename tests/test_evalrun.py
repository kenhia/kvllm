"""kvllm.evalrun unit tests — sandbox host selection (pure env/config logic, no Docker)."""

from __future__ import annotations

import os

from kvllm import evalrun, score


def test_sandbox_host_from_config(monkeypatch):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(
        score, "load_config", lambda: {"sandbox": {"docker_host": "ssh://ken@ksandbox"}}
    )
    evalrun._apply_sandbox_host()
    assert os.environ["DOCKER_HOST"] == "ssh://ken@ksandbox"


def test_sandbox_host_env_wins(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    monkeypatch.setattr(
        score, "load_config", lambda: {"sandbox": {"docker_host": "ssh://ken@ksandbox"}}
    )
    evalrun._apply_sandbox_host()
    assert os.environ["DOCKER_HOST"] == "unix:///var/run/docker.sock"


def test_sandbox_host_absent_leaves_env_alone(monkeypatch):
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(score, "load_config", lambda: {})
    evalrun._apply_sandbox_host()
    assert "DOCKER_HOST" not in os.environ

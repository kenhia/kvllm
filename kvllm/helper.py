"""kvllm helper — a small FastAPI control panel for the model service.

Runs as its own systemd *user* service (as your user), so it can drive `systemctl --user`
and reuse the model registry. Binds 0.0.0.0 so other machines on the LAN reach it at
http://<host>:<KVLLM_HELPER_PORT>/.

    uv run --group helper uvicorn kvllm.helper:app --host 0.0.0.0 --port 8800

Endpoints:
    GET  /                      dashboard (static HTML)
    GET  /api/models            the registry (models.toml)
    GET  /api/status            service + /v1 + GPU status
    POST /api/switch            {key}  — rewrite env + restart onto a model   (token)
    POST /api/service/{action}  start | stop | restart                         (token)

Control endpoints require the shared token in KVLLM_HELPER_TOKEN (sent as X-KVLLM-Token).
If that env var is unset, control is disabled (503) — view/status stay open.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from kvllm.registry import load_registry

REPO = Path(__file__).resolve().parent.parent
ENV_FILE = REPO / "deploy" / "kvllm.env"
INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"

SERVICE = "kvllm"  # the model service (systemd --user unit name)
MODEL_PORT = os.environ.get("KVLLM_PORT", "8000")

app = FastAPI(title="kvllm helper", docs_url="/api/docs")


# --- shell helpers ------------------------------------------------------------------


def _run(cmd: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return _run(["systemctl", "--user", *args])


def _gpu_memory() -> dict | None:
    try:
        p = _run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            timeout=5,
        )
        used, total = (int(x) for x in p.stdout.strip().split(",")[:2])
        return {"used_mib": used, "total_mib": total}
    except Exception:
        return None


def _v1_served_model() -> str | None:
    """The model id the running server reports, or None if /v1 isn't up."""
    try:
        with urllib.request.urlopen(
            f"http://localhost:{MODEL_PORT}/v1/models", timeout=1.5
        ) as r:
            data = json.load(r)
        return data["data"][0]["id"]
    except (urllib.error.URLError, OSError, KeyError, IndexError, ValueError):
        return None


# --- auth ---------------------------------------------------------------------------


def require_token(x_kvllm_token: str | None = Header(default=None)) -> None:
    """Gate control endpoints on the shared token (fail closed if unset).

    FastAPI maps the header X-KVLLM-Token → the x_kvllm_token parameter.
    """
    expected = os.environ.get("KVLLM_HELPER_TOKEN", "")
    if not expected:
        raise HTTPException(503, "control disabled: KVLLM_HELPER_TOKEN is not set")
    if not x_kvllm_token or not hmac.compare_digest(x_kvllm_token, expected):
        raise HTTPException(401, "missing or invalid token")


# --- models -------------------------------------------------------------------------


class SwitchBody(BaseModel):
    key: str


# --- routes -----------------------------------------------------------------------


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.get("/api/models")
def api_models() -> dict:
    return {"models": load_registry()}


@app.get("/api/status")
def api_status() -> dict:
    active = _systemctl("is-active", SERVICE).stdout.strip()
    enabled = _systemctl("is-enabled", SERVICE).stdout.strip()
    served = _v1_served_model()
    return {
        "service_active": active,  # active | inactive | failed | activating | ...
        "service_enabled": enabled,  # enabled | disabled | ...
        "served_model": served,  # the live /v1 model id (None until ready)
        "v1_ready": served is not None,
        "model_port": int(MODEL_PORT),
        "control_enabled": bool(os.environ.get("KVLLM_HELPER_TOKEN")),
        "gpu": _gpu_memory(),
    }


@app.post("/api/switch", dependencies=[Depends(require_token)])
def api_switch(body: SwitchBody) -> dict:
    registry = load_registry()
    if body.key not in registry:
        raise HTTPException(404, f"unknown model '{body.key}'")
    _set_env_key("KVLLM_MODEL_KEY", body.key)
    r = _systemctl("restart", SERVICE)
    if r.returncode != 0:
        raise HTTPException(500, f"restart failed: {r.stderr.strip()}")
    return {"ok": True, "key": body.key}


@app.post("/api/service/{action}", dependencies=[Depends(require_token)])
def api_service(action: str) -> dict:
    if action not in {"start", "stop", "restart"}:
        raise HTTPException(400, "action must be start, stop, or restart")
    r = _systemctl(action, SERVICE)
    if r.returncode != 0:
        raise HTTPException(500, f"{action} failed: {r.stderr.strip()}")
    return {"ok": True, "action": action}


def _set_env_key(key: str, value: str) -> None:
    """Set KEY=value in deploy/kvllm.env (rewrite in place, or append)."""
    if not ENV_FILE.is_file():
        raise HTTPException(500, f"env file not found: {ENV_FILE}")
    text = ENV_FILE.read_text()
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    new = (
        pattern.sub(line, text)
        if pattern.search(text)
        else text.rstrip("\n") + f"\n{line}\n"
    )
    ENV_FILE.write_text(new)

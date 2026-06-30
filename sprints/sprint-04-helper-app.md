# Sprint 4 — Helper app (web control panel)

_2026-06-30 on `kai` (RTX 5090). korg #100 (Ken's "nice to have", pulled forward — ahead of
schedule). Branch `04-helper-app`. Builds on [Sprint 3](sprint-03-availability.md)._

## Goal

A small web app, reachable from Ken's other machines (incl. Windows), to **view the registry +
status** and — the critical bit — **restart and load a different model** from a browser. vLLM is one
model per process, so "switch" = rewrite the env + restart the Sprint 3 service.

## Plan (decisions confirmed with Ken)

- **Stack:** FastAPI + uvicorn backend, one vanilla-JS static page (no build, no JS deps).
- **Auth:** shared token (`KVLLM_HELPER_TOKEN`) on control actions; view/status open; fail closed.
- Runs as a second systemd *user* service (`kvllm-helper.service`) so it can drive `systemctl
  --user` and reuse `kvllm/registry.py`. Binds `0.0.0.0`.

## What shipped

- **[`kvllm/helper.py`](../kvllm/helper.py)** — FastAPI app: `GET /api/models`, `GET /api/status`
  (service state + live `/v1` model + GPU mem via `nvidia-smi`), `POST /api/switch {key}`,
  `POST /api/service/{start,stop,restart}`. Token gate (`X-KVLLM-Token`, `hmac.compare_digest`,
  503 if unset). Switch rewrites `KVLLM_MODEL_KEY` in `deploy/kvllm.env` and restarts the unit.
- **[`kvllm/static/index.html`](../kvllm/static/index.html)** — dark single-page dashboard: status
  header (served model, service state, GPU bar), registry table with **Load** buttons, Stop/Restart,
  a token field (localStorage), 2s status polling, and a "loading…" state until `/v1` is back.
- **[`deploy/kvllm-helper.service.in`](../deploy/kvllm-helper.service.in)** + `install.sh` extended
  to render **both** units and backfill `KVLLM_HELPER_PORT`; `kvllm.env.example` gains
  `KVLLM_HELPER_PORT` / `KVLLM_HELPER_TOKEN`.
- **[`justfile`](../justfile)** — `helper-dev` (foreground `--reload`), `helper-enable` /
  `helper-disable` / `helper-restart` / `helper-status` / `helper-logs`.
- **[`docs/04-helper-app.md`](../docs/04-helper-app.md)** — endpoints, auth, setup, recipes.

## Decisions & discoveries

- **Reuses the registry as a library.** `load_registry()` backs `/api/models` and validates switch
  targets — the web layer is thin. (Used `load_registry` directly, not the CLI's `get_model`, which
  `sys.exit`s; the web app raises `HTTPException` instead.)
- **Helper runs as the same user as the model service**, which is what lets a web request call
  `systemctl --user restart kvllm` at all — no root, no sudoers, no privileged daemon.
- **Fail-closed auth:** no `KVLLM_HELPER_TOKEN` ⇒ control endpoints 503 and the UI shows "control
  disabled", rather than silently allowing restarts.

## Outcomes

- API verified: `/api/status` (active/enabled/served/GPU), `/api/models` (5 keys), `/` loads;
  switch **without** token → 401, **bad key** → 404.
- **Core requirement verified end-to-end:** `POST /api/switch` → deepseek (served in 24s) → back to
  qwen2.5-7b-instruct (23s); `deploy/kvllm.env` rewritten and restored. `just lint` clean.
- Both units installed via `just service-install`. Helper left **not enabled** pending Ken setting a
  token (a LAN control surface shouldn't go live with control disabled or an unset secret).

## Follow-ups

- Go live: set `KVLLM_HELPER_TOKEN` (`openssl rand -hex 16`) in `deploy/kvllm.env`, then
  `just helper-enable`; browse `http://kai:8800/`.
- Possible niceties: per-model "warm/cold (downloaded?)" hint, live log tail in the UI, vLLM
  sleep-mode instead of full restart if/when it helps switch latency.

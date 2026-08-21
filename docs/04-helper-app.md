# Helper app — web control panel

A small FastAPI dashboard to **view the registry + status** and **switch the served model / restart
the server** from any machine on the LAN (e.g. a Windows box at `http://kai:8800/`). It runs as its
own systemd *user* service (`kvllm-helper.service`), as your user, so it can drive `systemctl --user`
and reuse [`kvllm/registry.py`](../kvllm/registry.py) directly.

Switching a model = rewrite `KVLLM_MODEL_KEY` in `deploy/kvllm.env` and `systemctl --user restart
kvllm`. vLLM holds one model per process, so this is the single-GPU switch story made one click.

## Endpoints

| Method / path | Auth | Purpose |
|---|---|---|
| `GET /` | — | dashboard (single static HTML page) |
| `GET /api/models` | — | the registry (`models.toml`) |
| `GET /api/status` | — | service state + live `/v1` model + GPU memory |
| `GET /api/eval` | — | what `kvllm.evalrun` is doing (run-state the runner wrote) |
| `POST /api/switch` `{key}` | token | rewrite env + restart onto `<key>` |
| `POST /api/service/{start,stop,restart}` | token | control the model service |
| `GET /api/docs` | — | FastAPI's interactive docs |

## Auth

Control actions require a shared secret in **`KVLLM_HELPER_TOKEN`**, sent as the `X-KVLLM-Token`
header (the dashboard has a token field; it's stored in the browser's `localStorage`). If the env var
is **unset, control is disabled** (HTTP 503) and the panel is view-only — fail closed. View/status
endpoints are always open.

> The panel binds `0.0.0.0`. Anyone who can reach the port can *view*; only token-holders can
> *switch/restart*. Keep it on a trusted LAN; the token guards the disruptive actions.

## Setup

```sh
just service-install      # renders + installs BOTH units (model server + helper), backfills port

# set a control token (enables switch/restart from the UI):
echo "KVLLM_HELPER_TOKEN=$(openssl rand -hex 16)" >> deploy/kvllm.env

just helper-enable        # start the panel now + at boot
just helper-status
```

Config (in `deploy/kvllm.env`):

```sh
KVLLM_HELPER_PORT=8800           # port the dashboard binds (0.0.0.0)
KVLLM_HELPER_TOKEN=<secret>      # required for switch/restart/stop; unset ⇒ control disabled
```

Then browse to `http://<kai-host>:8800/` from any LAN machine. Enter the token once; click **Load**
on a model to switch (it restarts the server and shows "loading…" until `/v1` is back, ~20–40s).

## Recipes

| Command | Does |
|---|---|
| `just helper-dev` | run in the foreground with `--reload` (development) |
| `just helper-enable` / `helper-disable` | start+enable / stop+disable the service |
| `just helper-restart` | restart the panel |
| `just helper-status` / `helper-logs` | systemd status / follow journald |

## Eval monitor

The panel also shows **what the eval runner is doing** — which model, which suite, how long, and how
it exited. Evals run for tens of minutes to hours, so this is the difference between an unattended
overnight run and a black box until morning.

Everything it renders is **written by the runner** ([`kvllm/runstate.py`](../kvllm/runstate.py)),
never inferred here. That is a correction, not a preference: sprint 15's watcher ran
`pgrep -f "kvllm.evalrun <model>"` from a shell whose own command line contained that string,
matched itself, and reported a finished eval as running for ~36 minutes.

Two rules follow, and both are tested:

- **Liveness keys on the recorded PID** (`os.kill(pid, 0)`), never a command-line match. A record can
  say `running` and still be dead — the SIGKILL case — and the panel shows that correctly.
- **A finished run stops ageing.** Elapsed is measured to the exit moment, or for a killed run to its
  last heartbeat.

The state file lives at `eval-logs/.run-state.json` (override with `KVLLM_RUN_STATE`). It is written
atomically, so polling never catches a half-written document. `GET /api/eval` returns `{"run": null}`
until an eval has run at least once, and the panel stays hidden.

No GPU metrics here — those are on the main dashboard already.

## Notes

- The helper only *controls* the model service; it doesn't serve models itself — it's lightweight
  (no GPU, tiny memory) and safe to leave enabled alongside the model server.
- It reads the same `deploy/kvllm.env` as the model service, so the `KVLLM_PORT` it queries for
  `/v1` status matches what the server serves.
- A switch to an **uncached** model triggers a download on the server side; the UI just shows
  "loading…" longer.

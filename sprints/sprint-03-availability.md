# Sprint 3 — Availability (systemd auto-start across reboots)

_Started 2026-06-30 on `kai` (RTX 5090). korg #98 (Ken's idea). Branch `03-availability`._
_Builds on [Sprint 2](sprint-02-serving-ergonomics.md). See [`../sprints/planning/00-kickoff.md`](../sprints/planning/00-kickoff.md)._

## Goal

Now that kvllm serves **natively, not via Docker** (Sprint 1 decision), make it survive a `kai`
reboot without a manual start: a systemd unit that auto-serves the default registry model, restarts
on crash, and has a clean stop/switch path.

## Plan

1. **systemd *user* service** (no sudo) — linger is already on, so user services start at boot.
2. Template + renderer so paths aren't hardcoded in the repo (`deploy/kvllm.service.in` +
   `deploy/install.sh`); env-driven model/port (`deploy/kvllm.env`).
3. `just service-*` recipes: install / enable / disable / start / stop / restart / switch / status / logs.
4. Doc the install, model-switching, single-GPU contention, and resilience.
5. Verify start→serve, Restart-on-failure, and stop-frees-GPU.

## What shipped

- **[`deploy/kvllm.service.in`](../deploy/kvllm.service.in)** — user unit template. `Type=exec`,
  `EnvironmentFile=deploy/kvllm.env`, `ExecStart=<uv> run python -m kvllm.registry serve
  ${KVLLM_MODEL_KEY}`, `Restart=on-failure`/`RestartSec=5`, `TimeoutStartSec=900` (cold start),
  `WantedBy=default.target`.
- **[`deploy/install.sh`](../deploy/install.sh)** — renders `@WORKDIR@`/`@UV@` and installs to
  `~/.config/systemd/user/`; seeds `deploy/kvllm.env` from the example; `daemon-reload`. Idempotent,
  no sudo.
- **[`deploy/kvllm.env.example`](../deploy/kvllm.env.example)** — `KVLLM_MODEL_KEY` / `KVLLM_PORT` /
  `KVLLM_GPU_UTIL` / optional `HF_TOKEN`. Rendered `deploy/kvllm.env` is gitignored.
- **[`justfile`](../justfile)** — `service-install`, `service-enable`, `service-disable`,
  `start`/`stop`/`restart`, `service-switch <key>` (validates the key, rewrites the env, restarts),
  `service-status`, `service-logs`.
- **[`docs/03-deployment.md`](../docs/03-deployment.md)** — install, enable, day-to-day, single-GPU
  note, resilience, uninstall.

## Decisions & discoveries

- **User service, not system.** Linger is on (`Linger=yes`), so a user unit starts at boot with no
  root — and it runs in the same user context as the uv venv + HF cache. No `/etc/systemd`, no sudo,
  nothing system-level to drift. Matches the uv-native, no-system-mutation ethos from Sprint 1.
- **Reuses the Sprint 2 `execvp` serve path**, so systemd `SIGTERM` reaches vLLM directly — clean
  stop/restart with no signal-forwarding wrapper.
- **Template + renderer** keeps machine-specific absolute paths (home, `uv`) out of the versioned
  unit; `install.sh` fills them from `pwd` + `command -v uv`.

## Outcomes

- `just service-install` → unit rendered with correct paths; `just start` → `active`, `/v1` serves
  `qwen2.5-7b-instruct` (~24 s cold, compile cache warm).
- **Restart-on-failure verified:** SIGKILL the service → systemd respawned (`NRestarts` 0→1, new
  MainPID), `/v1` recovered + serving in ~8 s.
- `just stop` → `inactive`, GPU back to ~0 MiB.
- **Enabled at boot** (Ken's call): `systemctl --user enable --now kvllm` → `enabled` + `active`,
  serving `qwen2.5-7b-instruct`. HF token added to `deploy/kvllm.env` (read fresh from
  `EnvironmentFile` at start — no unit redeploy needed).

## Follow-ups

- `KVLLM_GPU_UTIL=0.90` reserves ~29 GB (weights + KV pool) — lower it in `deploy/kvllm.env` for
  GPU headroom, and `just stop` to free the card for `trt-llm-explore`/ad-hoc work.
- Deferred helper app (korg #100) would drive this unit (status + restart-and-load-model-X).

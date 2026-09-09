# Deployment — keep kvllm serving across reboots

kvllm runs as a **systemd user service** (`kvllm.service`) so the default model comes back up after
a `kai` reboot with no manual start. User-service (not system) because everything kvllm needs lives
in the `ken` user context — the uv-managed Python, the `.venv`, the HuggingFace cache — and **linger
is enabled** (`loginctl show-user ken` → `Linger=yes`), so user services start at boot without root.
No `sudo`, nothing in `/etc/systemd`.

The service's `ExecStart` is just the Sprint 2 serve path (`python -m kvllm.registry serve <key>`),
which `execvp`s into `vllm` — so systemd's `SIGTERM` on stop/restart goes straight to vLLM.

## Install

```sh
just service-install     # renders deploy/kvllm.service.in → ~/.config/systemd/user/kvllm.service
                         # and seeds deploy/kvllm.env from the example on first run
```

Edit **`deploy/kvllm.env`** (gitignored) to choose the model and port:

```sh
KVLLM_MODEL_KEY=qwen2.5-7b-instruct   # any key from `just models-list`
KVLLM_PORT=8000
KVLLM_GPU_UTIL=0.90
# HF_TOKEN=hf_xxx                      # only for gated models (e.g. llama-3.1-8b-instruct)
```

`KVLLM_GPU_UTIL` is the deployment's fraction. A registry entry that only exists at one
fraction carries its own `gpu_memory_utilization` and wins (entry > env > default):
`qwen3.8-27b-nvfp4` serves at 0.95 whatever this file says, because its 122,880-token
window with the draft head does not fit at 0.90 (sprint 20). `just models-show <key>`
prints the fraction the serve will actually use.

## Enable (auto-start at boot)

```sh
just service-enable      # start now AND start at every boot
just service-status
just healthy             # wait until /v1 answers
```

To stop auto-start and free the GPU:

```sh
just service-disable     # stop now + don't start at boot
```

## Day-to-day

| Command | Does |
|---|---|
| `just service-start` / `just service-stop` / `just service-restart` | control the running service |
| `just service-switch <key>` | write the key into `deploy/kvllm.env` and restart onto it |
| `just service-status` | systemd status |
| `just service-logs` | follow journald (`journalctl --user -u kvllm -f`) |
| `just loaded` | what `/v1/models` currently reports |

## Shipping a sprint restarts the service

The unit sets `WorkingDirectory` to this checkout and execs
`python -m kvllm.registry serve`, so the running server keeps executing whatever code it loaded at
start. A merge to `main` does not change that — only a restart does.

`.sprint-deploy` therefore declares the `deploy-kvllm` skill, which `/sprint-ship` runs in Phase 7
after the merge, so what is running is what landed. It:

- **no-ops** unless the merge touched something the served process actually executes
  (`kvllm/registry.py`, `kvllm/helper.py`, `models.toml`, `deploy/`, `pyproject.toml`, `uv.lock`) —
  most sprints here change suites, eval code or docs and need no restart;
- **refuses** while `just eval` / `just eval-repeat` is running, since those orchestrate this
  service themselves and a restart would fight them for the GPU mid-run;
- re-runs `deploy/install.sh` only when a unit template changed;
- stops, **waits for VRAM to drain to ~0** (the GSP-wedge rule), starts, then verifies `/v1/models`
  reports `KVLLM_MODEL_KEY` and that the running `vllm serve` argv matches what the registry now
  produces.

To deploy by hand at any other time, invoke the same skill rather than restarting directly — it
carries the drain wait and the verification.

## Single-GPU note

The 5090 holds **one model per process**, and this service is the canonical holder (~16 GB for a 7B).
While it's running it owns the GPU, so:

- **Switch models:** `just service-switch <key>` (don't also run a manual `just serve` — they'd
  collide on the GPU and port 8000).
- **Free the GPU** for ad-hoc work or the `trt-llm-explore` backend: `just service-stop` (keeps it enabled
  for next boot) or `just service-disable` (also stops auto-start).

## Resilience

`Restart=on-failure` (`RestartSec=5`) respawns vLLM if it crashes — verified by SIGKILLing the
process and watching systemd bring it back (`NRestarts` increments, `/v1` recovers in seconds once
the compile cache is warm). `TimeoutStartSec=900` covers a cold start (weights load + torch.compile
+ CUDA-graph capture) without systemd declaring a failed start.

## Uninstall

```sh
just service-disable
rm ~/.config/systemd/user/kvllm.service && systemctl --user daemon-reload
```

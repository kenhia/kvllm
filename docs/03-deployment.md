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
| `just start` / `just stop` / `just restart` | control the running service |
| `just service-switch <key>` | write the key into `deploy/kvllm.env` and restart onto it |
| `just service-status` | systemd status |
| `just service-logs` | follow journald (`journalctl --user -u kvllm -f`) |
| `just loaded` | what `/v1/models` currently reports |

## Single-GPU note

The 5090 holds **one model per process**, and this service is the canonical holder (~16 GB for a 7B).
While it's running it owns the GPU, so:

- **Switch models:** `just service-switch <key>` (don't also run a manual `just serve` — they'd
  collide on the GPU and port 8000).
- **Free the GPU** for ad-hoc work or the `trt-llm-explore` backend: `just stop` (keeps it enabled
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

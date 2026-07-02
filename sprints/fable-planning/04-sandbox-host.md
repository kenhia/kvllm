# Sandbox host — the dedicated test machine

_2026-07-02, fable-planning. Plan for the spare machine (currently unplugged; newer/more capable
than `kubsdb`) as the **execution sandbox host** for the eval harness. Ken will clean/reimage it
and set it up like the rest of the homelab (passwordless `ssh`, passwordless `sudo`)._

## Verdict: yes, use it — but don't block on it

The harness gets real value from a dedicated sandbox host, and the architecture
([02](02-eval-harness-architecture.md)) treats "where sandboxes run" as a one-variable config
(`DOCKER_HOST`). So:

- **Phase 1–2 of the roadmap runs sandboxes on `kai`'s local Docker** (already installed, 29.6.1).
  Nothing waits for the reimage.
- **When the sandbox host is up, flip `DOCKER_HOST` and everything moves.** Later phases (VMs,
  computer-use) genuinely need it.

## Why a separate host (not just kai's Docker)

1. **Blast-radius isolation.** The harness hands untrusted model-generated code a shell. On `kai`
   that shell shares a kernel with the GPU box, the model weights cache, and this repo. Containers
   are a good-not-great boundary; a separate machine makes the worst case "reimage the sandbox
   host", not "rebuild kai".
2. **Resource honesty.** Compiles/test-runs on `kai` steal CPU/RAM from vLLM and skew the very
   tok/s numbers the leaderboard ranks on. Separate host → clean measurements on both sides.
3. **Parallelism.** vLLM serves one model but many concurrent requests; with sandboxes elsewhere,
   several eval episodes can run concurrently against the same served model without the sandbox
   work competing with inference.
4. **The VM/computer-use future needs bare metal.** Nested virt on the GPU box is miserable;
   snapshot-and-restore VMs (agent breaks a machine → instant reset) and a headless desktop for
   computer-use want their own host.
5. **It doubles as the agentic-eval target.** The medium-term goal is a local model monitoring the
   homelab. "Real" agentic tasks (inspect systemd, read logs, report disk pressure) can run against
   sandbox-host VMs safely — a rehearsal of exactly the production use case.

## OS choice

**Ubuntu Server 24.04 LTS, headless** — Ken's preference, and the right call: same admin idioms as
the rest of the homelab, best-documented Docker/libvirt/incus support, LTS until 2029. No reason to
deviate. (Alternative considered: Debian 12/13 — leaner, but no advantage worth a second idiom in
the lab.)

Partitioning note: give `/var/lib/docker` (and later VM images) room — a single big ext4 root is
fine; skip LVM snapshots (ZFS/btrfs only if Ken already uses them elsewhere).

## Setup checklist (one evening)

1. Reimage: Ubuntu Server 24.04 LTS, headless, hostname (Ken's naming scheme — referred to here as
   `sandbox-host`; substitute the real name in configs).
2. Homelab-standard access: passwordless `ssh` (key), passwordless `sudo`.
3. `docker` via the official apt repo (matches `kai`); add Ken's user to the `docker` group.
4. On `kai`: `docker context create sandbox --docker "host=ssh://ken@<sandbox-host>"` — verify
   `docker --context sandbox run hello-world`. The harness selects it with
   `DOCKER_HOST=ssh://ken@<sandbox-host>` (or `docker context use`).
5. Pre-pull/build the eval task images (see [03](03-suites-scoring-leaderboard.md)) so episode
   startup isn't gated on image pulls.
6. Baseline hygiene since it runs untrusted code: no secrets/HF tokens on the box, no NFS mounts of
   real data, and (optionally) a firewall rule set that lets it reach `kai:8000` (the model /v1)
   and package mirrors but not the rest of the LAN.

Later phases add:

7. **VM layer** (Phase 4+): `libvirt`/`qemu-kvm` (or `incus` if we prefer its snapshot UX) — one
   Ubuntu cloud-image template + `virsh snapshot-revert` per episode for full-machine agentic
   tasks.
8. **Computer-use** (Phase 5+, multimodal): a VM with a lightweight desktop (XFCE) + VNC/Spice;
   the harness screenshots via the hypervisor, so nothing about `kai` changes.

## Network/data-flow shape

```
kai (RTX 5090)                         sandbox-host
├─ vLLM /v1  ◄──────────────┐          ├─ dockerd  ◄── ssh (docker context from kai)
├─ eval controller ─────────┼──────────┤   └─ per-episode containers (--network none,
│   (drives episodes)       │          │       or allowlist → kai:8000 only if the
│   model tool-calls ───────┘          │       task itself needs the model… it doesn't)
└─ leaderboard/scorecards              └─ later: libvirt VMs (snapshot/revert)
```

The **controller runs on `kai`** (it already must, to stop/start `kvllm.service` and own the GPU).
The model under test never talks to the sandbox directly — the controller receives the model's
tool calls (`bash`, `write_file`, …) over `/v1` and executes them in the sandbox container. So
containers default to `--network none`; only tasks that explicitly test networked behavior relax
that.

## Security posture (untrusted code, homelab-realistic)

- Containers: non-root user, `--network none` default, CPU/mem/pids limits, read-only base image
  with a writable `/workspace` tmpfs, per-episode container (fresh state every task).
- The eval controller is the only thing with ssh to the sandbox host; the model never gets
  credentials, and the docker socket is never mounted into task containers.
- Treat the box as expendable: nothing on it that can't be reimaged in an hour.
- This is defense-in-depth against *buggy/wild* model behavior (rm -rf, fork bombs, pip-installing
  the world), not against a determined adversary — appropriate for local open-weight models.

## Open items for Ken

- [x] Actual specs: i5-13400F (16 threads), 32 GB RAM, ~83 GB free on / — comfortably runs the
      full 15-sample coding fan-out.
- [x] Hostname: `ksandbox` (192.168.1.112), passwordless ssh + sudo, Docker 29.6.1.
- [x] Reimage done 2026-07-02; cutover landed the same day (see sprint-08 doc). Checklist items
      4–5 done: `docker context create sandbox`, images pre-built, smoke + both suite self-tests
      pass remotely. The harness selects the host via `[sandbox].docker_host` in eval-config.toml
      (DOCKER_HOST env overrides).
- [ ] Item 6 hygiene follow-ups: trim `~/.ssh/authorized_keys` (Ken seeded it with all his keys
      for convenience — keep at least `cleo` + `kai`), confirm no secrets/HF tokens land on the
      box, optional LAN-egress firewall.

### Second disk (2026-07-02)

The spare 1 TB NVMe is now the **container-state disk**: GPT + ext4 (`LABEL=sandbox-docker`),
mounted at `/data` with fstab **bind mounts** carrying both `/var/lib/docker` *and*
`/var/lib/containerd` — Docker 29 uses the containerd image store, so image layers live under
containerd's root, not Docker's; moving only `/var/lib/docker` moves almost nothing. All fstab
entries are UUID-based + `nofail` (the reboot test renumbered `nvme0n1`↔`nvme1n1`, so device
paths would have broken). The old NTFS partition's contents (stale May-2025 copy of the Gratch
vault + WoW backups, 804 MB) were archived to kai at
`~/backups/ksandbox-nvme0n1-Source-2026-07-02.tar.gz` before the wipe.

Boot-disk note for the Phase 4+ VM layer: `ubuntu-vg` has **~1.7 TB unallocated** (root LV is
100 G of a 2 TB disk) — carve a dedicated LV for libvirt images there when the time comes.

### Cutover gotcha (found 2026-07-02, fixed)

Inspect drives `docker compose` over ssh with one fresh connection per concurrent compose call.
The 15-sample coding suite storms sshd's `MaxStartups` (default 10) → `kex_exchange_identification:
Connection reset by peer` → episodes die with "No services started". Fix (both halves):

- **kai** `~/.ssh/config`: `ControlMaster auto` + `ControlPersist 10m` for `Host ksandbox` — all
  docker CLI ssh invocations multiplex over one TCP connection.
- **ksandbox** `/etc/ssh/sshd_config.d/50-eval-concurrency.conf`: `MaxSessions 64`,
  `MaxStartups 64:30:128` (multiplexed channels count against MaxSessions, default 10).

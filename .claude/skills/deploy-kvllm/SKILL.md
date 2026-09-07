---
name: deploy-kvllm
description: Deploy kvllm on kai from committed main — re-render the systemd user units if their templates changed, then restart the model server and helper so the running processes execute merged code, and verify the served model and health. No-ops when nothing on the serve path changed; refuses while an eval is orchestrating the service. Use when asked to deploy/redeploy kvllm, or when sprint-ship reaches Phase 7.
---

# Deploy kvllm

**There is no build and no artifact.** `kvllm.service` sets
`WorkingDirectory` to *this checkout* and execs
`uv run python -m kvllm.registry serve ${KVLLM_MODEL_KEY}`. The deploy is
therefore a **restart**: the files on disk are already right the moment
sprint-ship resets local to `main`, and the only thing still wrong is the
*running process*, which is executing whatever code it loaded at start.

That is the whole reason this skill exists. A sprint can change
`build_serve_argv`, land on `main`, and leave the box serving the previous
sprint's argv until someone happens to restart it weeks later — with the
repo, the board and the running server all disagreeing and nothing reporting
it. Sprint 18 changed the serve path exactly this way.

**Deploy from clean, committed `main`.** sprint-ship runs this in Phase 7,
after the merge and after local is reset to `main`, so a restart picks up
merged code. Preserve that ordering — restarting from a feature branch puts
the box on a commit that squash-merge is about to collapse.

## What is deployed, and where

Everything is on **kai**. Both units are *systemd user* units, no sudo.

| Thing | Where | Written by |
|---|---|---|
| model server | `kvllm.service` → this checkout | `deploy/install.sh` renders the unit |
| helper web app | `kvllm-helper.service` → this checkout | `deploy/install.sh` renders the unit |
| unit files | `~/.config/systemd/user/*.service` | rendered from `deploy/*.service.in` |
| service config | `deploy/kvllm.env` | **gitignored, never touched by a deploy** |

`deploy/*.service.in` are templates with `@WORKDIR@` / `@UV@` placeholders;
`~/.config/systemd/user/` is outside kaed's roots on purpose, and this is why —
the source of truth is the template in the repo, installed from there.

**Never edit `deploy/kvllm.env`.** It holds `KVLLM_MODEL_KEY`, the HF token and
the helper token. Which model is served is Ken's decision, not a deploy's.

## Step 1 — Decide whether there is anything to do

**Deploying nothing is the common case and a success.** Most sprints here touch
suites, eval code, `model-research/` or docs — none of which the running server
executes. Restarting for those costs ~90 s of downtime and a GPU load cycle for
no change.

The stamp is `$(git rev-parse --git-dir)/kvllm-deploy.stamp`, containing the
commit the service was last restarted at. It lives in the git dir: never
committed, survives `git clean`.

```bash
GITDIR="$(git rev-parse --git-dir)"
STAMP="$GITDIR/kvllm-deploy.stamp"
HEAD_SHA="$(git rev-parse HEAD)"
SERVE_PATHS="kvllm/registry.py kvllm/helper.py kvllm/__init__.py models.toml deploy/ pyproject.toml uv.lock"
```

- **No stamp** (first run, fresh clone) → treat as changed. Restart once and
  stamp it; from then on the question is answerable.
- **Stamp equals `HEAD_SHA`** → nothing has landed since the last deploy. Say so
  and stop.
- **Otherwise** → `git diff --name-only "$(cat "$STAMP")..HEAD" -- $SERVE_PATHS`.
  Empty means the sprint changed nothing the running processes execute:
  **do nothing, say so, and still update the stamp** so the next deploy
  compares against the right commit.

Report the decision either way — a silent no-op is indistinguishable from a
phase that never ran, which is the failure `.sprint-deploy` exists to prevent.

Why each path is on the list:

| path | why a restart is needed |
|---|---|
| `kvllm/registry.py` | builds the `vllm serve` argv at process start |
| `kvllm/helper.py` | the helper app's own code |
| `models.toml` | the served model's entry feeds that argv |
| `deploy/` | unit templates and the installer |
| `pyproject.toml`, `uv.lock` | the venv the units exec into (a vLLM bump lands here) |

`suites/`, `kvllm/evalrun.py`, `kvllm/repeat.py`, `kvllm/score.py`,
`model-research/`, `docs/`, `sprints/` and `tests/` are deliberately **not** on
the list — the served process never executes them.

## Step 2 — Refuse if an eval is in flight

`just eval` / `just eval-repeat` **orchestrate `kvllm.service` themselves** —
they stop it, serve the model under test, and restore it afterwards. A deploy
restart landing in the middle of that fights the orchestrator for the GPU and
corrupts a run that may be an hour in.

```bash
pgrep -f "kvllm[.](repeat|evalrun)" >/dev/null && echo "EVAL RUNNING"
```

**The bracket quoting is load-bearing — do not "simplify" it to
`kvllm.repeat|kvllm.evalrun`.** `pgrep -f` matches against full command lines,
including the shell that is running this very check, whose argv contains the
pattern as literal text. The unbracketed form therefore matches itself and
reports an eval running **every time**, which would make this step refuse every
deploy forever — a check that never passes is indistinguishable from a check
that always fails. `[.]` matches a literal `.` while the pattern's own text
(`kvllm[.]…`) does not match the regex, so the check sees real eval processes
and not itself. Verified both directions when this skill was written.

If anything matches, **stop and report it.** Do not wait it out, do not kill it.
Say which run is in flight and that the deploy needs re-running once it
finishes. A sprint that ships without the restart is recoverable; a trashed
eval run is an hour of GPU time and a corrupted board row.

## Step 3 — Re-render the units, if their templates changed

Only when `deploy/` appears in the Step 1 diff:

```bash
./deploy/install.sh
```

Idempotent, no sudo, and it daemon-reloads. It seeds `deploy/kvllm.env` from the
example **only if absent** and never clobbers an existing one, so it is safe to
re-run — but read its output rather than assuming: it prints what it installed
and warns if `KVLLM_HELPER_TOKEN` is unset.

## Step 4 — Restart, respecting GPU discipline

The order matters, and the drain wait is not optional. CLAUDE.md: *don't
kill/serve rapidly (GSP wedge history); `nvidia-smi` should drain to ~0 between
models.* A killed engine can hold VRAM for a full minute after the unit reports
stopped.

```bash
systemctl --user stop kvllm.service
# wait for the card to actually let go — up to ~3 min, not a fixed sleep
for i in $(seq 1 18); do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
  procs=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l)
  [ "$used" -lt 500 ] && [ "$procs" -eq 0 ] && break
  sleep 10
done
systemctl --user start kvllm.service
systemctl --user restart kvllm-helper.service   # no GPU, cheap, always safe
```

**Never `kill -9` the engine**, and never start before the drain check passes.
If the card has not drained after ~3 minutes, stop and report it rather than
starting on top of a wedged context.

**Background the wait for readiness.** Cold start is ~90 s for gemma and longer
after a vLLM bump; the unit allows `TimeoutStartSec=900`. A start that has not
answered yet is not a failed start.

## Step 5 — Verify the sprint's work is actually live

A green unit proves systemd started something. It does not prove the box is
running merged code.

```bash
curl -s --max-time 5 http://localhost:8000/v1/models        # id == $KVLLM_MODEL_KEY
systemctl --user show kvllm.service -p ActiveState,NRestarts # active, NRestarts=0
nvidia-smi --query-gpu=memory.used --format=csv,noheader
```

Check, in order:

1. `/v1/models` answers and its `id` **equals `KVLLM_MODEL_KEY` from
   `deploy/kvllm.env`** — not just "some model". A mismatch means the env file
   and the running server disagree.
2. `NRestarts=0`. A non-zero count means it crash-looped into a working state,
   which is not the same as starting cleanly — read the journal before calling
   it good.
3. **VRAM is in the expected band for that model** (gemma ~30,846 MiB). A number
   far below it usually means the engine died and the frontend is answering
   alone — a failure mode that looks healthy from the outside.
4. **If the sprint changed `build_serve_argv` or `models.toml`, diff the argv
   that is actually running** against what the registry now produces:

   ```bash
   journalctl --user -u kvllm.service -n 200 --no-pager | grep "vllm serve"
   uv run python -m kvllm.registry show "$KVLLM_MODEL_KEY" | tail -1
   ```

   These must agree. This is the check that would have caught sprint 18's
   `--max-num-batched-tokens` regression at deploy time rather than at the next
   cold start.

Then stamp it:

```bash
git rev-parse HEAD > "$GITDIR/kvllm-deploy.stamp"
```

**Stamp only after verification passes.** A stamp written ahead of a failed
restart tells the next deploy there is nothing to do.

## If it fails

**A failed deploy does not roll back the merge.** The code is good; the rollout
isn't. Leave `main` alone.

- **Engine will not start** — read the journal for the root cause; vLLM's real
  error is above the `Engine core initialization failed` line, not in it. The
  common shapes are a KV-cache/context mismatch (`ValueError: To serve at least
  one request…`) and a bad serve flag. `git revert` the offending change on
  `main` in a follow-up, or fix forward; do not hand-edit the running config.
- **Card wedged** (`ERR!`, `Channel Repair Pending`) — stop, do not retry the
  restart, and tell Ken. A reboot is his call.
- **Left stopped** — say so explicitly and loudly. A serving box that is down
  and reported as shipped is the worst outcome available here.

Record what happened in the sprint record, and open a follow-up work item if the
box is left in a state Ken needs to act on.

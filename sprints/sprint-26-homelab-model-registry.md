# Sprint 26: the homelab model registry (serve restores a parked model instead of re-downloading it)

**Proposal:** korg:4155 (slice of program korg:4162, "Low-hanging fruit, run 5")
· **Work item:** #3964. **Branch:** `26-homelab-model-registry` · **Driving model:**
Claude Opus, as a headless karc leg (`kvllm-21df48`) on kai under an overseer session.

## Goal

On 2026-10-19, 223 G of evaluation-era weights and ACE-Step's 97 G were parked off kai
(korg:3869); they now sit on `gratch:/nas/model-archive` (WI 3969). The only record of them
was the archive's `MANIFEST.md` and a klams note. `models.toml` still listed every parked
key, so `just serve <key>` on one would silently re-download it from Hugging Face. #3964
asked for one list of everything the homelab has pulled, and a fetch that checks that
list first.

The overseer's calls (proposal notes) were followed unchanged:
- it lives in kvllm;
- the index is a TOML file in the repo, covering non-kvllm consumers too;
- it is seeded from the archive's MANIFEST and SHA256SUMS;
- `just serve` restores with `rsync -aH`, with an un-park command now and a park command later;
- the served model never changes, and the restore is tested on a small model in a scratch dir.

## Premise check (2026-10-28 19:05 PDT, kai)

The premise holds. gratch's archive answers over ssh. MANIFEST lists 14 parked kvllm
models plus ACE-Step. The serve path (`registry._cmd_serve` → `vllm serve <hf_repo>`) has
no check, so a parked key downloads. kai's hub holds only the three working models.

## What shipped

- **`homelab-models.toml`**, the registry. It has 5 locations (kai's HF cache, gratch's HF
  archive, gratch's ACE-Step checkpoints, kubs0's GGUF dir, kubs0's HF cache) and 25 models.
  Each model records its revision (`refs/main`), `du -sb` size, download date where known,
  consumers (`kvllm:<key>`, `kodds`, `ace-step`) and copies. That covers all 17 local
  `models.toml` entries, ACE-Step 1.5, kodds' four GGUFs and kubs0's three embedding models.
  The archive's empty stubs (refs only, no weights) are left out on purpose.
- **`model-sums/<entry>.sha256`**: one manifest per entry, 25 files. The archive's
  SHA256SUMS is split per entry and re-rooted. kai's and kubs0's copies were hashed fresh.
  An hf-cache manifest is relative to its `models--…` dir, so it checks a copy in any hub.
  A plain-dir manifest is relative to its location.
- **`kvllm/modelstore.py`**, with `list`, `where`, `unpark`, `verify` and the hook
  `ensure_weights`. A restore rsyncs into a hidden `.restore-models--…` staging dir beside the
  destination, checks it against the manifest, and only then renames it into place. vLLM
  never sees a half copy, and a rerun resumes. `verify` runs `sha256sum -c` where the copy
  lives (over ssh with the manifest on stdin), so no weights move.
- **The hook is on every serve path**: `registry serve` (and the systemd unit through it),
  `evalctl.serving` (`just eval`) and `interview.serve`. When the model is in this host's
  hub it does nothing, and when the registry doesn't know the model it does nothing either
  (vLLM downloads as before). When the registry knows a parked copy, it restores it. If that
  restore fails, it **refuses the serve** with the fix spelled out, and
  `KVLLM_ALLOW_DOWNLOAD=1` makes the download a deliberate choice.
- **Recipes**: `just models-stored`, `models-where`, `models-unpark`, `models-verify`.
  README has a section on them.
- **Tests** (`tests/test_modelstore.py`, 19). They cover:
  - the checked-in registry parses, every entry has a manifest, and there are no orphan manifests;
  - **every local `models.toml` key has a registry row**, so adding a model means recording it;
  - real rsync restores between tmp dirs: success, a corrupt blob staying staged, a failed rsync, an existing destination;
  - the hook's no-op, refuse and escape-hatch branches.
- **The archive's MANIFEST.md** on gratch now points at the registry. Its contents table
  moved here; its layout and restore notes stay. The whole-file replace was verified by md5.

## Tests fired

- **Restore, for real, in scratch.** `just models-unpark qwen3-8b-fp8 --hub .scratch/hub`
  ran from kai and pulled the 9.45 GB from gratch, verified it and renamed it into place in
  33 s. A second run reported "already in". `huggingface_hub.snapshot_download` against that
  hub then resolved all 12 files with no download (the hub grew by 32 KB of lock and
  metadata files). The hook was then fired end to end into a second scratch hub
  (`HF_HUB_CACHE`): it restored, and a second call was a no-op. Both scratch hubs were deleted.
- **Verify across the fleet**, run from kai:
  - Qwen3-8B-FP8 on gratch-hf: OK;
  - Qwen3-4B-Q8_0.gguf on kubs0-gguf: OK;
  - all-MiniLM-L6-v2 on kubs0-hf: OK;
  - gemma-4-12B-it on kai-hf: OK.
- **The served model was untouched.** `/v1/models` = `qwen3.8-27b-nvfp4` before and after.
  No serve, switch or restart happened.

## Found, and handed up

**A restore does not stop every download.** vLLM resolves `main` against the Hub, so when
upstream has moved, a restored snapshot is the old revision and vLLM fetches the new one
anyway. Measured: Devstral's archived revision is c599e8e5, and upstream is now 55c5b41e. The
five others checked are unchanged. Pinning serves to a revision changes which weights a key
serves, and the scores were measured on a particular revision. That is a decision, so it is
**WI 4174** rather than a quiet `--revision`. The registry's Devstral row and the README
say so.

## Repaired in passing

- gratch's MANIFEST listed "older krag/phi3 weights in `kubs0:/krag/models`", and that
  directory no longer exists on kubs0. The line went with the contents table, and the
  registry does not list it.

## Follow-ups

- WI 4174: pin served revisions or not (the decision above).
- A `park` command, as the proposal deferred it. Parking is rare and done by hand, so this
  was not filed. When it is wanted, it is the inverse of `restore` plus a registry edit.

# Sprint 27: serve with prompt-token details, and pin every local model to its recorded revision

**Proposal:** korg:4423 (slice of program korg:4368, "Backlog drawdown, November 2026")
· **Work items:** #2992, #4174. **Branch:** `27-serve-args-prompt-details-revision-pin` ·
**Driving model:** Claude Opus, as a headless karc leg (`kvllm-c8de69`) on kai under an
overseer session.

## Goal

Ken approved two serve-argument changes on 2026-11-09. They land together so that neither
needs a restart of its own:

- **#2992**: serve with `--enable-prompt-tokens-details`, so `usage.prompt_tokens_details.cached_tokens`
  reaches consumers.
- **#4174**, option (a): pin every local `models.toml` entry to the revision that
  `homelab-models.toml` records. A test holds the two files equal. The resident is pinned
  to the snapshot it is serving today.

**Hard rule (overseer):** no kvllm restart, no switch of the served model, and no model
load or download. Both changes take effect at the next planned restart.

## Premise check (2026-11-09 18:45 PST, kai)

- **#2992: the premise holds.** `build_serve_argv` did not pass the flag. vLLM 0.28.0's
  `cli_args.py:132` still defaults it to `False`. The running server's argv (pid 1811)
  lacks it.
- **#4174: the premise holds.** No serve path passed `--revision`. The running engine
  logged `revision=main` at its 2026-10-20 start.

## Which snapshot the resident serves

The resident was read from kai's cache and the running process, with no Hub call:

- kvllm.service has run since 2026-10-20 14:36 PDT.
- The EngineCore start log says `revision=main`.
- `refs/main` in `/ai-data/huggingface/hub/models--unsloth--Qwen3.8-27B-NVFP4` reads
  `f0b7c9e722f5565102fff8481c99e4d86ae099c7`. Its mtime is 2026-09-08 17:43, before the
  start, so `main` resolved to that snapshot.
- `homelab-models.toml` records the same hash.
- The cache also holds the older `57926bac…` and `7d6f8d4d…`, and neither is served.

All 17 local entries have a recorded revision in `homelab-models.toml` (sprint 26 seeded
them from the archive's `refs/main` and kai's cache). That is the snapshot a restore puts
back, so every entry could be pinned without a download. None was left unpinned. For
kai's three cached models (the resident, gemma-4-31b-it-awq and gemma-4-12b-it), the
recorded revision equals kai's `refs/main`.

## What shipped

- **`kvllm/registry.py` `build_serve_argv`**:
  - Every serve now passes `--enable-prompt-tokens-details`.
  - An entry's `revision` becomes `--revision <sha>`.
  - `registry show` prints the revision.
- **The draft head is pinned too.** vLLM 0.28's `SpeculativeConfig` builds an MTP drafter's
  `ModelConfig` with the speculative config's *own* `revision`
  (`vllm/config/speculative.py:911`), which defaults to `None`, meaning `main`. It does not
  take `--revision`. A bare `--revision` would therefore have pinned the target weights
  while the draft head (`model_mtp.safetensors`) and its config still tracked upstream. So
  when an entry is pinned and its speculative config names no separate `model`, the
  revision is also written into the JSON. A drafter from another repo keeps its own
  revision.
- **`models.toml`**: `revision = "<sha>"` on all 17 local entries, copied from
  `homelab-models.toml` by script, not by hand. The header now documents the field.
- **Tests:**
  - `test_registry.py`: flag always present; revision absent unpinned and emitted pinned;
    pin carried into a same-model drafter and not into a separate-repo drafter; the
    resident's real argv has both.
  - `test_modelstore.py`: `test_every_local_kvllm_model_is_pinned_to_its_inventory_revision`
    holds the two files equal.
- **vLLM accepts the flags.** The resident's new argv parses with vLLM 0.28's own
  `make_arg_parser` (no GPU, no model load). The result was
  `revision=f0b7c9e7…, enable_prompt_tokens_details=True`, and the spec dict carried the
  revision.
- **Docs:**
  - `client/README.md` and the `TokenUsage` docstring now say kvllm passes the flag, and
    that a server started before this sprint still reports `cached = None`. `kvllm-client`
    needs no new field: `TokenUsage.cached` already reads `cached_tokens`.
  - The README's "serves are not pinned to a revision" paragraph now describes the pin.
  - The `homelab-models.toml` header says `revision` is also what kvllm serves.

New resident argv, from `registry show qwen3.8-27b-nvfp4`:

```
vllm serve unsloth/Qwen3.8-27B-NVFP4 --served-model-name qwen3.8-27b-nvfp4 --host 127.0.0.1
  --port 8000 --gpu-memory-utilization 0.95 --enable-prompt-tokens-details
  --revision f0b7c9e722f5565102fff8481c99e4d86ae099c7 --max-model-len 122880 …
  --speculative-config {"method":"mtp","num_speculative_tokens":3,"revision":"f0b7c9e7…"} …
```

## The running service runs the old arguments until its next planned restart

Nothing here was restarted. kvllm.service (up since 2026-10-20) still serves unpinned and
without prompt-token details. Both changes go live at the next planned restart (a vLLM
bump, a resident switch, or a deploy that restarts it). **Ken fires that check by
restarting the service. It is not a soak.** The items resolve when the code lands.

What to check after that restart:

1. **The argv:** `tr '\0' ' ' < /proc/$(pgrep -f 'vllm serve')/cmdline` shows
   `--enable-prompt-tokens-details` and `--revision f0b7c9e7…`. The EngineCore start log
   line shows `revision=f0b7c9e7…`, not `revision=main`.
2. **`cached_tokens`:** send one non-streaming chat completion twice, with an identical long
   prefix. The second reply's `usage.prompt_tokens_details.cached_tokens` should be present
   and non-zero, and `kvllm_client.TokenUsage.cached` should stop reading `None`.

## Repaired in passing

- **Two credential backups could have been committed.** The krot rotation (WI 3534) left
  `.env.pre-3534.bak` and `deploy/kvllm.env.pre-3534.bak` untracked in the checkout. They
  hold now-dead token values. `.gitignore` covered `.env` and `deploy/kvllm.env` but not
  their backups. Fix: `.gitignore` now covers `.env.*.bak` and `deploy/kvllm.env.*.bak`.
  The files themselves are untouched. Proof: `git status --short` no longer lists them.

## Findings for the overseer (not filed)

- **`ensure_weights` checks only that the repo is present, not the pinned snapshot.** If
  kai's cache holds a repo at a *different* snapshot from the pinned one, the restore is
  skipped (`present_in_hub` is true), and vLLM fetches the pinned revision from the Hub.
  `restore()` also refuses an existing `models--…` dir, so merging a snapshot in would be a
  design change. No entry is in that state today: kai's three cached models all hold their
  pinned snapshot.

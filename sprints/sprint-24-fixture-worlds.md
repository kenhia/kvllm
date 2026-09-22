# Sprint 24 — Stop the fake world contradicting itself

**Proposal:** korg:3061 (slice 17 of program korg:3062, "Low-hanging fruit, run 2")
· **Work items:** #2005 (a5/a8/a9 reference facts contradict the fake world), #2094 (the
fixture worlds are single-host, so kmon's fleet report contract is unexercised).
**Branch:** `24-fixture-worlds` · **Driving model:** Claude Opus 5, as a headless karc leg
(`kvllm-74a1af`) on kai under an overseer session.

## Goal

Two eval-harness items, both file edits against fixtures, neither needing the GPU. #2005 is
a harness bug of the class `docs/findings/evaluating-local-models.md` names first: the
*world* was wrong, and careful models were being scored as fabricating for reporting what
they actually found. #2094 asks for a multi-host fixture so kmon's fleet report contract has
something that can fail.

**Hard constraint, from the proposal and honoured throughout:** nothing here changed,
restarted or reconfigured what kvllm serves. No model was served. The half of #2005 that
asks for a re-run of the sprint-19 stack rows under the new suite version is explicitly out
of scope — it serves models, so it batches with #1502, which is Ken's.

## Premise check at sprint start (2026-09-21 22:03 PDT, kai)

- **#2005 holds, all three cases, verified in the current files.**
  - **a8.** `base`'s `cron.service` journal is the single line
    `2026-07-02 06:25:01 CRON[6001]: (ken) CMD (/usr/local/bin/healthping.sh)`, and the
    Dockerfile materialises only `renew-cert.sh` under `/usr/local/bin/`. `a8` inherits
    `base` unmodified. So the one scenario whose reference says "nothing is wrong" shipped a
    provably missing file, and `cat /usr/local/bin/healthping.sh` was a real finding.
  - **a5.** `#102` says "BLOCKED on #105: needs the reverse-proxy config that ships with the
    auth work in #105"; `#105` said "DONE in practice — merged and deployed 7/1". The
    reference demands `blocked: 102`. The world said otherwise, in its own text.
  - **a9.** `a9` inherited `base`, whose `backup-sync.service` is
    `active (exited)` / "sync completed OK (2.1 GB, 31s)", while its `fixlab` set's `#201`
    says the sync has been "failing with connection refused since 6/30".
- **#2094's premise DRIFTED, and the drift changes the conclusion.** See
  "What #2094 turned out to be" below. Its description of the defect is right; its claim
  about which repo can fix it is not.
- **Environment:** clean tree, `main` == `origin/main`, Docker 29.6.1 on kai. Cross-project
  plan: kvllm is not in `cross-project-planning/index.md`, so nothing applies.

## #2005 — what shipped

Three edits to the world, one to the image, **no change to any reference fact, rubric,
`auto_zero` or `fact_group`**. The gate is exactly as strong as it was; only the world it
describes changed.

### a8 — materialise `healthping.sh` (`agentic_assets/Dockerfile`)

`/usr/local/bin/healthping.sh` is now created and `chmod 0755`, exactly the pattern
`renew-cert.sh` already used. Verified in a built image: the file is present and exits 0,
and `renew-cert.hs` is still absent, so a4's planted typo fault is untouched.

**I did not also drop the cron line from `base`, and that is a deliberate departure from one
half of the overseer's written call — flagged on the proposal for a ruling.** Once the script
exists the line is no longer stale: it is a truthful record of a successful cron run that
`cat` now confirms. Dropping it as well would leave `cron.service` the only unit in `base`
with an empty journal, which the shim renders as `-- No entries --` — a fresh oddity planted
in the one scenario whose reference says nothing is wrong. Each half of the call closes the
contradiction on its own; this is the half that does it without disturbing the world's
texture. Reversing it is one line.

### a5 — `#105` no longer implies `#102` is unblocked (`scenarios.json`)

`#105`'s text now reads:

> DONE in practice — merged and deployed 7/1; ticket was never closed. Per-host cutovers are
> staged separately: kubsdb's is scheduled for the 7/8 maintenance window and has not
> happened yet.

This was the constrained edit of the three. The reference needs **both** of:

1. `blocked: 102` — so `#105` must not have delivered what `#102` waits on; and
2. `ready: 103, 106` — so `#105` must be in *no* category, which it only is while it is
   **effectively done**. Any edit that leaves work outstanding *on #105* makes `#105` ready
   and breaks the reference's third line.

Staged per-host cutovers satisfy both: no work remains on `#105`, and `#102` (deploy to
kubsdb) still cannot go live. `#102`'s own text is unchanged and still true, which keeps the
`BLOCKED on #105` string the self-test asserts.

### a9 — its own failing `backup-sync` (`scenarios.json`)

`a9` now inherits `a1` instead of `base` — the same pattern `a6` already uses (`inherit:
"a1"` plus its own `wis`), so it costs no duplicated journal. `a9` keeps `wis: ["fixlab"]`;
both resolvers override rather than merge `wis` (kvllm's `korg` shim breaks at the first node
carrying one, kmon's `resolve()` does `scen.get("wis", base["wis"])`), so `fixlab` resolves
once. Verified: `a9` now has `failed_units == ["backup-sync.service"]` and a journal quoting
the same connection-refused failure `#201` describes.

### Version bump

`suites/agentic.py` `VERSION` 2 → 3, with the reason in the comment. This is a ranked
CONDITIONS change, so the bump is required by `CLAUDE.md`. The board rows are now one suite
version behind; re-running them is the out-of-scope half that batches with #1502.

### The self-test now proves all three

`suites/agentic_selftest.py`'s `DISCOVER` table gained one command and the matching needles
per case, so each fix is a gate failure if it regresses:

| case | added command | added needles |
|---|---|---|
| a5 | `korg show 105` | `DONE in practice`, `7/8` |
| a8 | `ls /usr/local/bin/` | `healthping.sh` |
| a9 | `journalctl -u backup-sync` | `Connection refused`, `192.168.1.44` |

## What #2094 turned out to be

**The deliverable is entirely kmon-side, and this sprint should not write it.** The item's
description of the defect is correct and stands; its stated reason for filing it against
kvllm — *"the fixture suite and the resident live here"* — is half right, and the wrong half
is load-bearing.

What is actually where:

- kvllm owns `suites/agentic_assets/scenarios.json` — the world **data**. It is consumed by
  kvllm's own agentic suite through `sandbox=("docker", COMPOSE)`: **one container, one
  box**. The format cannot express a second host, and the shims render exactly one.
- kmon owns everything the fleet contract needs: `tests/fixtures/kvllm_agentic_worlds.json`
  (a vendored **copy** of the above), `bundle_for()`/`host_for()`, `tests/helpers.fleet`,
  `verify.py`, and the live gate `tools/fixture_gate.py` (`just fixture-gate`).
- The two-host bundle the overseer pointed at — kmon `.scratch/fleet_synth_check.py` —
  builds its fleet from `host_for("a1")` renamed `kubsdb` and `host_for("a5")` renamed
  `kai`, plus a skipped `kstudio`. It needs **no new world data at all**. The worlds it
  wants already exist.

So adding a "fleet world" to kvllm would mean inventing data kvllm's own suite cannot use,
purely for another repo to vendor — while the thing actually missing (a fleet case in kmon's
gate, with its expected-pass report) stays missing. Promoting the scratch script is a new
deliverable in kmon and a change to what `just fixture-gate` runs, which kmon's own
`CLAUDE.md` names as a contract. That is a decision this sprint does not own: **Branch B —
parked and handed up**, with the finding on #2094 and a note on the proposal.

## Repaired in passing

Nothing. The gate was green on arrival and the only defects found were the two filed below,
neither of which is repairable from this repo.

## Filed, with the decision each needs

- **kmon #3082 — the vendored worlds have diverged from kvllm, and re-vendoring is not
  mechanical.** This sprint's a9 change makes kmon's copy stale, and kmon's
  `test_verify_worlds.py` asserts `failure_evidence(host_for("a9")) == set()` — it *relies*
  on a9 being healthy, as its healthy-world case next to a1/a3/a7. The decision kmon has to
  make, and kvllm cannot: does kmon want a9 to gain a failed unit (re-vendor and update the
  assertion), or does it want a healthy a9 and should pin/rename its copy so the divergence
  is deliberate rather than silent? Worth noting that kmon's gate has **no** contradiction to
  fix — it ignores reference facts by design and treats the world as truth — so the two
  repos may legitimately want different a9s. There is also no staleness check between the two
  files (unlike `korg_read_shapes.json`, which is sha256'd), so nothing reports the drift.
- **#2094 stays open**, with the finding above as a comment, pending the overseer's ruling on
  where it belongs.

## Overseer rulings received before the ship (proposal comment 2894)

Both of the calls I pushed back on were reversed in my favour, which is worth recording
because it is why the shipped diff differs from the brief:

1. **a8 cron line: do not drop it.** The overseer's own words — "my instruction treated
   'stale cron line' as a fixed property of the world, when it was a property of the
   *contradiction*, and materialising the script dissolved it." `scenarios.json` ships as
   written above; the one-line edit was explicitly ruled against.
2. **WI 2094 is kmon's.** The overseer `unrelate`d the `covers` edge and re-projected the
   item to kmon, correcting the item's own "Why this is kvllm's and not kmon's" section in
   the process. **So this proposal ships complete, not partial** — its only covered item is
   #2005. kmon #3082 was accepted as correctly filed rather than repaired, and now sits in
   the same project as 2094.

## Docs updated at ship time

The sprint made two existing docs misleading, both fixed here rather than filed:

- **`docs/findings/evaluating-local-models.md` — added artifact 10.** The doc's own prime
  rule is "audit the harness before believing the score", and this sprint is a new instance
  of it that the existing artifact 7 does not cover. Artifact 7 (a fixture contradicting
  itself) *announces itself* — the transcript shows the candidate probing the shell.
  This one produces a clean transcript and a plausible low score, because the contradiction
  is between the world and its **answer key**, and only the world is executable. That is the
  generalisation worth keeping: a fixture has two halves and nothing tests their agreement,
  so they drift silently and the drift is scored as a model defect.
- **`docs/findings/local-model-guidance-2026-07.md` — corrected in place.** Its item 4 said
  "even Sonnet trips a8-honesty occasionally — verify", which now reads as a model property
  when it was this exact harness bug. Annotated with a dated correction rather than rewritten
  — it is a dated snapshot and the original line is part of the record.
- **`docs/findings/methodology-2026-07.html` — deliberately left alone.** It names a5/a8/a9
  but its descriptions are still accurate (a8 is *more* "a perfectly healthy machine" now,
  not less), and it is a dated published write-up rather than a living doc.

## Gates

- `just check` — ruff check, ruff format, 269 unit tests, 46 client tests: **pass**.
- `just test-agentic-suite` — Docker image rebuilt, all 9 scenarios
  `discoverable + reference scores 1.0`: **pass**. This is the gate that matters here, and it
  now covers all three fixes.
- Image inspected directly: `healthping.sh` present and executable, `renew-cert.hs` still
  absent.
- No model was served; `kvllm.service` was not touched.

## Deployed

**Nothing to deploy this sprint — a deliberate no-op, recorded so it is not mistaken for a
phase that never ran.**

`deploy-kvllm`, as declared in `.sprint-deploy`. Its Step 1 compared the deploy stamp
(`1147fd4`, sprint 23's feature commit) against merged `HEAD` (`04dbff1`) over the serve
paths — `kvllm/registry.py`, `kvllm/helper.py`, `kvllm/__init__.py`, `models.toml`,
`deploy/`, `pyproject.toml`, `uv.lock` — and the diff is **empty**. This sprint touched only
`suites/`, `docs/findings/` and `sprints/`, none of which the running processes execute.
Stamp advanced to `04dbff1` so the next deploy compares against the right commit.

No eval was in flight (`pgrep -f "kvllm[.](repeat|evalrun)"` clear), so the skill's Step 2
refusal did not apply.

**Nothing was restarted, which is also what the proposal's hard constraint required.** Read
the service state rather than changing it:

| check | value |
|---|---|
| `kvllm.service` | `active`, `NRestarts=0` |
| `/v1/models` id | `qwen3.8-27b-nvfp4` — equals `KVLLM_MODEL_KEY` |
| VRAM | 30944 MiB, in band for the resident |

The box is serving the same resident it was serving before this sprint, which is correct:
nothing this sprint changed is code that process executes.

# Sprint 14 — kprojects harness

_2026-08-14. korg #1234, proposal korg:1239. Branch `14-kprojects-harness`. Batch 1 of the
kprojects rollout (korg #737), alongside kmon and hv-simulator — one repo, one PR, no
shared branch._

## Goal

Put kvllm on the [kprojects](https://github.com/kenhia/kprojects) minimal harness: the
managed shared-conventions block in both agent files, the harness layout, and a real
`just check` gate. Repo layout only — the vLLM service and the served model are untouched.

## What shipped

```
uvx --refresh --from git+https://github.com/kenhia/kprojects kproject-install --agent both .
```

`--stack` deliberately omitted. The installer reported **`stack : python (detected)`** —
the right answer, so no re-run. That reading mattered: the tooling stanza lives inside the
managed block and can only be re-applied with an explicit `--stack`, never hand-corrected.

- **`CLAUDE.md`** — managed block appended below the existing project content, which stays
  where it is. The one edit outside the block: the sprint-record convention now says out
  loud that this repo keeps `sprint-NN-slug.md` rather than the block's
  `###-<short-name>.md`, so the two don't read as contradicting each other.
- **`.github/copilot-instructions.md`** — new. Managed block plus a `## Project` section
  carrying the same facts as `CLAUDE.md` (findings to read first, conventions, quick map).
  Both files are maintained; neither is generated from the other.
- **`sprints/planning/roadmap.md`** — seeded, then filled with Now / Next / Later from the
  live korg items and the phased plan. `05-roadmap.md` is now explicitly historical.
- **`sprints/review/`, `.scratch/`** — created by the installer.
- **`.gitignore`** — installer added `.venv/` and `.pytest_cache/`. `.scratch/` and `.env`
  were already there.
- **`sprints/README.md`** — the index had gone stale at sprint 08 ("in progress"); sprints
  08–13 added with their merge dates, and it now points at `planning/roadmap.md`.

### What was deliberately not done

- **The justfile was not replaced.** `just check` was already a real gate
  (`lint test client-test`) and the installer leaves an existing one alone. A migration
  that rewrites a working gate is a net loss.
- **`.claude/skills/`** (`model-research`, `model-scout`) untouched — kprojects is the
  harness; skills are separate and not the installer's business.
- **No old harness to collapse.** No `.specify/`, no `specs/`, no prompt files — kvllm was
  skills-only. `sprints/` and `sprints/planning/` already matched the target layout, so
  nothing moved.

## Outcomes

`just check` green: ruff clean, 71 files formatted, 141 root tests + 14 client tests pass.
Managed block present and unedited between markers in both agent files.

## Follow-ups

- `[dir]` — an empty, untracked directory at the repo root from a botched command back on
  2026-07-03. Harmless, out of scope here, left for Ken to delete.
- korg #102 ("Sprint 7 — Eval harness") is still open but was overtaken by sprints 07–13.
  Worth closing.

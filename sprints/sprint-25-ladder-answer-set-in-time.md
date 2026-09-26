# Sprint 25 — The ladder scorer accepts an answer set; P2's next iteration asks whether Ken could still act in time

**Proposal:** korg:3311 (slice of program korg:3314, "Low-hanging fruit, run 4")
· **Work item:** #2024 (sprint-22 ladder follow-ups), its no-GPU half.
**Branch:** `25-ladder-answer-set-in-time` · **Driving model:** Claude Opus, as a headless
karc leg (`kvllm-962c9a`) on kai under an overseer session.

## Goal

Ken answered #2024's three "for Ken to rule" questions at the 2026-09-25 staff meeting
(comment 3173): `g-root-login-kens-wi` scores `handle` **or** `handoff` correct; the
`g-root-login-kens-ip` truth stays `handoff`; P2's "materially worse by 08:00" becomes
"could Ken still act in time?" with the categories as worked examples. This sprint lands the
first and third, re-scores the transcripts already on disk, and carries the GPU-bound
harness items (4–7) forward as one work item so #2024 can close.

**Hard constraint, honoured throughout:** no model was served, switched or restarted; no
GPU run. Everything here is scorer, prompt file, docs, and a re-judge of stored reports.

## Premise check at sprint start (2026-09-25 19:50 PDT, kai)

- **Item 1 holds.** `interview/run.py::judge` compared `report.action == truth["action"]` —
  one truth per rung, no set. The rung's truth was `handle`; Qwen's four s22 draws on it were
  `handoff` with 3/3 finding keywords, scored `useless`.
- **Item 3 holds.** `interview/prompts/p2-principle.md` still reads "materially worse by
  then".
- **Item 2** needs nothing: Ken confirmed the existing truth.

## What shipped

**The answer set.** A rung's truth may carry `accept`, the set of actions that score
correct; `action` stays the canonical answer and must be in the set (asserted — a set
without it is a broken rung, not a scoring choice). On a rung whose canonical answer is
`handle`, every accepted action still needs the finding: a handoff that never found WI-1799
is `wrong-answer`, because the korg search *is* that rung. Everything else about the cells
is unchanged for single-truth rungs (the `useless` branch now reads "`handle` was
acceptable", which is `want == "handle"` when the set is one element). Only
`g-root-login-kens-wi` carries a set: `["handle", "handoff"]`, with its `why` extended to
say so. `interview.build_scenarios` regenerates byte-identical JSON for the other 21 rungs.

**The re-score, no model.** New `interview/rescore.py`: re-runs `judge()` on every stored
attempt's `report` against the current scenario truth; dry run by default, `--write`
rewrites only the files whose cells move — `truth` becomes current, each `judge` is
replaced, and a `rescored: [{on, before}]` entry keeps the original reading in the file.
Before writing, a full dry re-judge of all 310 stored attempts against current truth: the
only scoring-field change anywhere is this rung (the other "drift" between stored and
current truth is sprint-22's metadata — `effort_worth_it`, `family`, `order` — added after
sprint 19), and exactly four cells move.

| model | prompt | config (all rungs, `interview.summarize`) | correct before | after |
|---|---|---|---|---|
| qwen3.8-27b-nvfp4 | p1-calibrated | s22-tmodel | 16 / 24 | **18 / 24** |
| qwen3.8-27b-nvfp4 | p2-principle | s22-tmodel | 21 / 26 | **23 / 26** |
| gemma-4-31b-it-awq | p1 / p2 | s22-tmodel | 11 / 18, 21 / 26 | unchanged (it handled the rung) |

All four moved cells are `useless → correct`; none moved the other way. The findings
addendum's gradient figure for Qwen reads 21 → 23 of 26 (P1 → P2) where it read 19 → 21;
the P2 − P1 difference, which is what finding 1 rests on, is unchanged.
`interview.summarize` shows a set truth as `H/HO`.

**P2's next iteration is `p4-in-time.md`, not an edit to P2.** The brief said "rewrite
P2". Transcripts record their system prompt by *name* only, and 61 `p2-principle`
transcripts are on disk and quoted in the findings; rewriting the file would leave every
one of those numbers naming a prompt no longer in the tree — the labeled-condition rule.
So Ken's wording ships as a new file and P2 stays as the measured control (flagged for the
overseer's ruling, proposal comment 3188). P4 is P2 with two definitions changed:
`escalate_now` asks "could he still act in time if he learned of this then?", keeps P2's
four categories explicitly as *examples, not a list to match against*, and says to judge
the time Ken needs to act rather than the 08:00 snapshot; `handoff` becomes "Ken can still
act in time in the morning". It names no host, service or event class, and none of its
wording mirrors a ladder rung. Not measured — that is card time (#3316).

**Summarizer.** It parsed the prompt out of the filename against a hard-coded
`p0`–`p3` tuple, so a `p4` run would have been mis-split into prompt and tag. It now uses
the `prompt` field every transcript carries, falling back to the old parse; the summary
output is byte-identical on the existing tree.

## Filed

- **#3316** — #2024's items 4–7 (single-vintage re-run, absence and content rungs, the
  combined conditions, world tooling), quoted in full, with item 6 updated to point at
  `p4-in-time`. The one filing the proposal authorised; it carries existing work forward.
  Item 7 needs no card and is noted as such there.

## Repaired in passing

- `interview.summarize` would have mis-labelled any prompt outside `p0`–`p3` (above);
  fixed, proven by the byte-identical summary on the existing tree and `just check`.

## Gates

`just check` green: ruff clean, 271 unit tests (two new: the answer-set judge and the
re-score), 46 client tests. No `suites/` change, so the Docker suite gates do not apply.
No serve-path file changed (`kvllm/`, `models.toml`, `deploy/` untouched), so
`deploy-kvllm` at ship is a no-op by its own rule.

## Deployed

`deploy-kvllm` (declared in `.sprint-deploy`), run at ship from merged `main` `344085b`:
**deliberate no-op.** `git diff --name-only 04dbff1..344085b` over the serve paths
(`kvllm/registry.py`, `kvllm/helper.py`, `kvllm/__init__.py`, `models.toml`, `deploy/`,
`pyproject.toml`, `uv.lock`) is empty, so there was no restart. The stamp moved to
`344085b`. No eval was in flight. The resident is untouched: `kvllm.service` active,
`NRestarts=0`, `/v1/models` → `qwen3.8-27b-nvfp4`.

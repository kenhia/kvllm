# Sprint 6 — Helper skills (model-research + model-scout)

_2026-06-30 on `kai`. korg #101. Branch `06-helper-skills`. Builds on [Sprint 5](sprint-05-model-research.md)._

## Goal

Turn the one-off model research into repeatable tooling: two project skills that keep up with a
fast-moving model landscape, both reading the standing serving profile from
[`model-research/README.md`](../model-research/README.md).

## What shipped

- **`.claude/skills/model-research/SKILL.md`** — `/model-research <name|hf-repo>`: deep-dive one
  model against kvllm's constraints, **primary-source verified** (HF API for existence/license/gated,
  model card + config for arch/quant, vLLM docs/issues for sm_120 maturity + the right tool/reasoning
  parser), then write a dated `model-research/<date>-<slug>.md` and propose a `models.toml` row.
  Bakes in the lessons from Sprint 5 (watch FP8-that-OOMs, pin the correct parser, flag new archs).
- **`.claude/skills/model-scout/SKILL.md`** — `/model-scout [focus]`: scan release surfaces for new
  open models worth trying since the last run, diff against `.scout-state.json`, propose candidates →
  `/model-research`. Honest about being curated-search-and-diff, not a magic feed.
- **`model-research/.scout-state.json`** — seeded with the registry + survey models so the first
  real scout starts clean.
- First **project skills** in the repo (`.claude/skills/`) — version-controlled, ship with kvllm.

## Decisions & discoveries

- **Skills, not agents** — both are user-triggered procedures; the right primitive. They reuse the
  deep-research harness for hard cases but default to focused primary-source checks for a single model
  (lighter + more reliable than the heavy workflow, which crashed at synth in Sprint 5).
- **One source of truth for context** — both skills read `model-research/README.md` so the
  "what fits / what we care about / what's already in the registry" spec can't drift.
- Neither skill flips `tested=true`; that needs a real serve on `kai` — which motivates the next
  sprint (eval harness).

## Outcomes

- `/model-research` and `/model-scout` available as project skills (load next session). `just lint`
  clean (no Python changes).

## Follow-ups

- **Sprint 7 — eval harness** (korg #102): per-skillset targets (coding / agentic / tool use / image)
  to do our own "worth trying / has issues" evaluation by actually serving the model on `kai`. This
  is what flips `tested=true`.
- Optionally wire `/model-scout` to a weekly schedule (routine) to keep the candidate list fresh.

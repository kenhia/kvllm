# Sprint 10 — Repo restructure + publish prep

_2026-07-03. korg #107. Branch `10-repo-restructure`. Chore sprint per Ken's direction
("flavor, discretion granted; goal: repo clear to me and others"), between the sprint 9
findings and Phase 5._

## What moved

| from | to | why |
|---|---|---|
| `docs/model-research/` | `model-research/` (root) | research is a top-level *product* of this repo, not documentation; `docs/` narrows to usage docs + findings |
| `sprints/fable-planning/` | `sprints/planning/` | planning docs live with the sprints they drove; name no longer tied to one model's involvement |
| `docs/00-kickoff.md` | `sprints/planning/00-kickoff.md` | it's the original planning doc |
| `evals/` | `suites/` | Ken kept opening it expecting *output*; it's suite **source**. Outputs stay put: `model-research/evals/` (scorecards + board) and `eval-logs/` (transcripts) |
| `tests/test_evals_*.py` | `tests/test_suites_*.py` | follow the rename |

Everything moved with `git mv`; all imports, module invocations (`python -m suites.…`),
config paths (`score.EVALS`), skills, and doc links rewritten. A link-integrity checker ran
over every markdown file: **0 broken relative links** (13 depth-shift breaks found and
fixed, including one sed over-reach where `model-research/README.md`'s link to its own
`evals/` subdir had been renamed).

## justfile

Every recipe now has a `just --list`-visible one-line header. `start`/`stop`/`restart` →
`service-start`/`service-stop`/`service-restart` (they always were service ops; now they
sort with `service-enable`/`-disable`/`-switch`/`-status`/`-logs`). Multi-line comments
reordered so the summary line is what `--list` shows. `docs/03-deployment.md` updated.

## Front doors

- **README.md** rewritten: leads with what the repo is *now* (serving + eval harness +
  findings + the board where a local took ①), split serving/eval quick starts, a layout
  table, environment notes.
- **CLAUDE.md** (new, repo root): agent orientation — findings-first reading order,
  conventions that are load-bearing (suite versioning rules, the judge `calibrated` flag,
  GPU discipline, sprint/branch flow, secrets), and the repo map. This is the discovery
  aid for future agents Ken asked for.

## Publish prep (kenhia/kvllm)

- `.gitignore` audited: `.env`, `deploy/kvllm.env` (may carry HF_TOKEN), `eval-logs/`,
  weights — all ignored; `deploy/kvllm.env.example` is placeholder-only.
- **Full-history secret scan: clean.** No `sk-ant-*`, no `hf_*` tokens, no key-bearing
  `ANTHROPIC_API_KEY=` in any blob of any commit; `.env`/`kvllm.env` never tracked.
- LAN hostnames/IPs (kai, ksandbox, 192.168.x) appear in docs — RFC1918, homelab-normal,
  Ken-visible; judged fine to publish.
- **Open for Ken at repo creation:** license choice (nothing in-repo asserts one; MIT is
  the path of least resistance if the intent is "read and reuse freely"), and whether
  `model-research/evals/` scorecards should ship (they do currently — they're the receipts
  behind the findings; recommended: yes).

## Verification

`just check` (132 tests) after every move; `just test-agentic-suite` (fixture self-test,
remote sandbox) and `eval-sandbox-smoke` re-run after the `suites/` rename; link checker
0 broken; `just --list` renders a complete, headed recipe list.

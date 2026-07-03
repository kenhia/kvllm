# kvllm

Local LLM serving **and evaluation** on a single RTX 5090 (`kai`), built around **vLLM**'s
OpenAI-compatible `/v1`. What started as a serving harness grew an opinionated eval rig:
four versioned suites (tool calling, sandboxed coding, agentic investigation on a fixture
homelab, judged writing), a human-calibrated LLM judge, priced frontier baselines (Claude)
through the same suites, and a weighted leaderboard where — after auditing away four
measurement artifacts — **a local model took first place**.

**Read the findings:** [`docs/findings/`](docs/findings/) — evergreen
[eval-methodology lessons](docs/findings/evaluating-local-models.md), a dated
[local-model role guide](docs/findings/local-model-guidance-2026-07.md), and two shareable
reports ([results](docs/findings/local-vs-frontier-2026-07.html) ·
[methodology](docs/findings/methodology-2026-07.html)).

**See the board:** [`model-research/evals/leaderboard.md`](model-research/evals/leaderboard.md)
(or the clickable `.html` sibling — every row expands to gate stats, the composite equation,
and per-case judge rationales).

## Quick start — serving

```sh
just models-list                    # what's in the registry (models.toml)
just serve qwen2.5-7b-instruct      # serve a model by key on http://localhost:8000/v1
just healthy                        # wait until /v1 answers
just smoke                          # tool-calling + LangChain smoke tests
```

Point any OpenAI client at `base_url="http://localhost:8000/v1"`, `api_key="EMPTY"`,
`model="<registry key>"`. vLLM holds **one model per process**; `just service-switch <key>`
changes the model the systemd service serves.

## Quick start — evaluating

```sh
just eval <key>                     # serve → gate → suites → scorecard + leaderboard
just eval-all                       # sweep the registry (resumable; skips current scores)
just eval <key> --suite assisted    # the unranked controller-scaffolding condition
just eval claude-haiku-4-5          # frontier baseline through the same suites ($)
just test-coding-suite              # suite self-tests (Docker only, no GPU)
just test-agentic-suite
```

Sandboxes run on a separate Docker host (`[sandbox].docker_host` in
[`eval-config.toml`](eval-config.toml)); scoring weights, judge config, and pricing live in
the same file. Suite design and scoring math: [`docs/findings/methodology-2026-07.html`](docs/findings/methodology-2026-07.html).

## Layout

| path | what |
|---|---|
| [`kvllm/`](kvllm/) | the package: model registry/serving, eval runner + orchestration, scoring/leaderboard, helper web app |
| [`suites/`](suites/) | eval suite **source** (Inspect AI tasks + fixtures + self-tests) |
| [`model-research/`](model-research/) | research **output**: surveys, candidate deep-dives, and `evals/` (scorecards + leaderboard) |
| [`docs/`](docs/) | usage docs (01–04: backend contract, quantization, deployment, helper app) + [`findings/`](docs/findings/) |
| [`sprints/`](sprints/) | how this was built, sprint by sprint; [`planning/`](sprints/planning/) has the architecture docs |
| [`models.toml`](models.toml) | the model registry (serve flags, capabilities, eval verdicts) |
| [`eval-config.toml`](eval-config.toml) | weights, judge, pricing, sandbox host |
| `eval-logs/` | Inspect transcripts (gitignored; open with `inspect view`) |

## Environment

Serving box: RTX 5090 32 GB (sm_120), vLLM, uv-managed Python. Sandbox box: any Docker host
reachable over ssh (see [`sprints/planning/04-sandbox-host.md`](sprints/planning/04-sandbox-host.md)
for the setup, including the ssh-multiplexing requirement). Frontier baselines and the judge
need `ANTHROPIC_API_KEY` in `.env` (never committed). Project kickoff and roadmap:
[`sprints/planning/00-kickoff.md`](sprints/planning/00-kickoff.md).

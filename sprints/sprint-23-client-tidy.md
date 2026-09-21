# Sprint 23 — kvllm-client tidy: the real consumer list, a visible retry budget, usage on FallbackResult, an omittable temperature

**Proposal:** korg:2977 (slice 2 of program korg:2981, "Low-hanging fruit — experiment 1")
· **Work items:** #1574 (consumer list still names archived kagent), #2010 (`request_timeout`
is per attempt), #2019 (usage on `FallbackResult`; can vLLM report `cached_tokens`?), #2624
(`frontier_model` always sends `temperature`). **Branch:** `23-client-tidy` · **Driving
model:** Claude Opus 5, as a headless karc leg (`kvllm-aac5e4`) on kai under an overseer
session on cleo.

## Goal

Four XS items against `client/` that had each been filed and left, all four in the same
surface: the shared client every homelab consumer imports. Nothing here needed the GPU and
nothing here changed what is served. The batch was picked as low-hanging fruit — the test
being whether a night of small, decision-free items can be drained without Ken in the loop.

One of the four (#2624) is not cosmetic: the escalation tier could not be reached at all for
a model whose `temperature` Anthropic had deprecated, and because that tier only runs after
the local one has already failed a gate, the failure was invisible until the bad morning.

## Premise check at sprint start (2026-09-21 13:41 PDT, kai)

All four premises hold. One line each:

- **#1574 holds**, with line drift that changes nothing: the item cites `CLAUDE.md:39`, the
  sentence is now at `CLAUDE.md:50` (`.github/copilot-instructions.md:85` is exact). Both
  are **outside** the managed kproject block (CLAUDE.md 57–94, copilot 1–38), so both are
  hand-editable — the overseer's one call on this item.
- **#2010 holds.** `local_model` takes `request_timeout` and passes it as the OpenAI
  `timeout`; there is no `max_retries` anywhere in the signature, so a consumer cannot
  express "one attempt, then fail".
- **#2019 holds.** `FallbackResult` is `(content, model_used, escalated, reasoning)` — no
  usage field.
- **#2624 holds exactly as written.** `frontier_model` builds
  `ChatAnthropic(model=…, temperature=temperature, …)` with `temperature: float = 0.0`,
  unconditionally.
- **Environment:** vLLM 0.28.0, langchain-openai 1.3.4, langchain-core 1.4.9, openai 2.44.0.
  Clean tree, `main` == `origin/main`. Cross-project plan: kvllm is not in
  `cross-project-planning/index.md`, so nothing applies.

### The consumer list, verified rather than asserted (#1574)

The item asked specifically not to take klams-mind on trust. Checked against the actual
`pyproject.toml` of each candidate, fleet-wide in one `kaed` search (`root: "*:*"`):

| consumer | dependency | host |
|---|---|---|
| kyac | `kvllm-client[anthropic]`, git source | kai |
| kmon | `kvllm-client[anthropic] @ git+…#subdirectory=client` | kai |
| klams-mind | `kvllm-client @ git+…#subdirectory=client` (no `[anthropic]` — no escalation tier) | **kubs0** |

All three carry the dep, so the list the item proposed as the checkable one —
`kyac/kmon/klams-mind` — is the correct one. klams-mind is not on kai at all, which is why
a local-only search would have wrongly dropped it; the dep is confirmed in its own
`pyproject.toml` on kubs0 and in its sprint 003 record.

`kagent` is archived and is gone from both live orientation lines. It stays in the two
**extraction-provenance** lines (`client/README.md:4`,
`client/src/kvllm_client/__init__.py:3` — "extracted from kagent, kmon, and klams-mind")
and in `KAGENT_BASE_URL` as the env-var example, all three of which the item explicitly said
to leave: they are true as history.

## What shipped

### A retry budget you can see (#2010)

`local_model` gains `max_retries: int = 2`. The default is the OpenAI SDK's own, so **no
behaviour changes** — the point is that the number is now in the signature, because the
surprise in the item was not the retry, it was not knowing the arithmetic:
`request_timeout × (1 + max_retries)`, which turns kyac's 300 s budget into 900 s worst
case. `max_retries=0` is the caller that owns its own retry, and the reasoning is recorded
next to it: the local tier's failure mode is a hung engine, not a flaky network, and
retrying a hung engine only delays the fallback.

### Usage on FallbackResult (#2019, part 1)

New `TokenUsage(prompt, completion, total, reasoning, cached)` frozen dataclass, a new
`usage` field on `FallbackResult`, and a `usage_of(message)` predicate beside
`reasoning_of` for callers that invoke the llm themselves.

Read from LangChain's **`usage_metadata`**, which is provider-neutral — both `ChatOpenAI`
(vLLM) and `ChatAnthropic` populate it. That is the whole reason the field can live on
`FallbackResult` at all: the result does not know which tier answered, so the usage shape
must not either. This is the "extend the library, never wrap it" rule applied to what was
becoming a third copy of the same callback (kyac's `ReasoningWatch`, kmon's `UsageWatch`).

The detail fields are `None` when the provider reported nothing, deliberately **not** `0` —
which is the honest answer for `cached` today, and leads directly into part 2.

### Can vLLM report `cached_tokens`? Yes — behind a flag that is off (#2019, part 2)

Answered from the installed engine's own source, without restarting or reserving the GPU
(the overseer's explicit call). The answer is better than the item expected:

**vLLM 0.28.0 does implement `usage.prompt_tokens_details.cached_tokens`.** It is gated
behind the server flag `--enable-prompt-tokens-details`, which defaults to `False`
(`vllm/entrypoints/openai/cli_args.py:132`), and `_make_prompt_tokens_details`
(`vllm/entrypoints/openai/chat_completion/serving.py:87`) returns `None` outright when the
flag is off. `kvllm/registry.py` never passes it.

So kmon sprint 10's finding was not "vLLM cannot report it" — the consumer was reading a
field the server had never been asked to send, which is exactly why the log honestly said
`0` while the engine log showed the hit rate climbing 0.0% → 25.9%. Documented in
`client/README.md` under prefix caching: **read cache effectiveness from the engine log, not
from `usage`, as kvllm is served today.** Turning the flag on is a serve-path decision, not
a client one — filed, see Follow-ups.

### The escalation tier can be reached again (#2624)

`temperature` becomes `float | None = 0.0` and is **omitted from the request** when it is
`None`, or when `model` is in the new `TEMPERATURE_REFUSED` frozenset, seeded with
`claude-sonnet-5`. The default is unchanged, so callers get the fix without passing
anything, and the knowledge of which models refuse the parameter lives in the one place that
talks to the API.

The tests assert on **the outgoing request payload** (`_get_request_payload`), not on the
attribute: the bug was a parameter being *sent*, so "absent from the payload" is the only
claim that means anything. There is a negative control — `claude-haiku-4-5` still carries
`temperature: 0.0` — because the item's own measurement showed this is per model, not an
across-the-board removal, and a test that passed for both would prove nothing.

## Decisions

- **CD — `temperature` is omitted by the client, not by the caller (WI-2624).** The item
  named two options; this took the second. `temperature: float | None = 0.0` keeps the
  default every existing caller already gets, and the refused-model set lives in
  `kvllm-client` rather than in each consumer. The public signature change is **additive**:
  no existing call site changes meaning, because the only behaviour that differs is for a
  model that previously could not be called at all. The cost accepted is that the client now
  carries a model list it must keep current — `TEMPERATURE_REFUSED` is one line to extend,
  and the alternative was every consumer independently discovering a 400 from its own
  escalation tier.
- **`max_retries` defaults to 2, matching the SDK (WI-2010).** Stating the SDK's default in
  our own signature rather than choosing a better one: this sprint is about making the
  budget legible, and changing the retry count for every consumer is a behaviour change none
  of them asked for.
- **`TokenUsage` detail fields are `None`, not `0`, when unreported.** A consumer must be
  able to tell "the provider said nothing" from "the provider said zero" — the distinction
  the `cached_tokens: 0` confusion was made of.
- **Client version 0.2.0 → 0.3.0.** Additive public API plus one bug fix. The README ties
  feature availability to the version, and kmon needs a number to name as the release that
  lets it delete its own `TEMPERATURE_REFUSED` workaround.

## Repaired in passing

- **`frontier_model` gained `max_retries` too** — the same defect #2010 fixed, one tier over.
  Found while doing #2010 and raised to the overseer rather than landed unilaterally, because
  it is a public signature change and widening a covered item's scope is not a repair. The
  overseer ruled it in on this branch ("the same defect one tier over, not new scope"), so it
  is here: `max_retries: int = 2`, which is the **Anthropic** SDK's own default
  (`anthropic.DEFAULT_MAX_RETRIES`, confirmed 2 in anthropic 0.116.0 / langchain-anthropic
  1.4.8) — so no behaviour change on this tier either.

  It is worth slightly more than the local-tier version. `frontier_model` has no
  `request_timeout` at all, so a caller cannot bound a frontier call; and this tier is the
  **last** resort, so when it hangs there is nothing after it to fall back to and the
  caller's own deadline is all that is left. `max_retries=0` is how that caller gets one
  attempt. Two tests, gate green.

## Follow-ups

- **kmon deletes its own `TEMPERATURE_REFUSED` set** and the two tests that guard it, once
  it locks kvllm-client 0.3.0. That is kmon's repo and kmon's call — noted for the overseer
  rather than filed from here, as the proposal directed.
- **Whether to serve with `--enable-prompt-tokens-details`** — filed as **#2992**, the only
  work item this sprint opened. It names the decision it needs: carrying the flag on the
  resident's serve arguments is a permanent serve-path change plus a restart of the served
  model, which this sprint was explicitly scoped out of. Nothing downstream waits on it —
  consumers are correct either way — and the recommendation in it is to ride along with the
  next planned restart rather than spend one on this alone.
- ~~`frontier_model` has no `max_retries` either~~ — **ruled in by the overseer and landed
  on this branch**; see "Repaired in passing".
- **kmon's half of #2624** — deleting `controller.frontier_model`'s `TEMPERATURE_REFUSED` set
  and its two tests, once kmon locks kvllm-client 0.3.0. The overseer is carrying this to a
  kmon leg in flight in the same program; nothing filed from here.

## Overseer rulings (handoff korg:2994, accepted)

1. **`frontier_model` max_retries: do it here.** Landed — "Repaired in passing".
2. **0.3.0 is the right version.** Kept.
3. **No deploy step applies.** Confirmed: nothing on the serve path changed, so
   `deploy-kvllm` no-ops by its own contract. The ship records that rather than restarting
   anything — which also keeps the GPU discipline this slice was scoped around.
4. **#2992 is a fair file** — a resident restart is Ken's call.
5. **kmon's half** is the overseer's to route, not this leg's.

## Gate

`just check` green: ruff check + ruff format clean (91 files), 269 repo tests, 46 client
tests (33 before; 13 added). No GPU touched, no service restarted, nothing served changed.
The only `nvidia-smi` read in the whole sprint is in **Deployed** below, and it is read-only:
confirming the resident was still up and untouched, not preparing to restart it.

## Deployed

**2026-09-21 13:59 PDT, kai, from merged `main` `1147fd4`** (`deploy-kvllm`, sprint-ship
Phase 7, on the karc ship turn after the overseer's clearance, comment 2726 / handoffs
korg:2994 and korg:2996).

**Nothing to restart, by the skill's own rule.** The serve-path diff since the last stamp
(`07eb92f`, sprint 22's deploy) over `kvllm/registry.py`, `kvllm/helper.py`,
`kvllm/__init__.py`, `models.toml`, `deploy/`, `pyproject.toml` and `uv.lock` is **empty** —
every file this sprint touched is under `client/` (its own distribution, no vLLM dependency),
the two orientation docs, or this record, none of which the served processes execute. Stamp
moved to `1147fd4` so the next deploy compares against the right commit.

Worth noting for a later reader, because it is the one thing that could have made this a
real deploy: `client/` is a **consumer-side** library. Changing `frontier_model` or
`local_model` changes what kyac, kmon and klams-mind do on their next `uv lock`, and nothing
at all about what kai serves. The escalation tier lives in the consumer's process, not in
`kvllm.service`.

The resident was not touched: `kvllm.service` active since **2026-09-13 19:35:53 PDT**,
`NRestarts=0`, `/v1/models` → `qwen3.8-27b-nvfp4` at 122,880, VRAM 30,944 MiB — in band, and
the same process that was running before this sprint started. The overseer's ruling ("no
deploy applies — record the no-op, do not restart anything") and the skill's own predicate
agreed, and the predicate was evaluated rather than assumed.

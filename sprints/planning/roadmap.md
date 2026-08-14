# Roadmap

> The general plan for this project. Keep it current; detail lives in the
> sprint records.
>
> The phased plan that built the eval harness is [`05-roadmap.md`](05-roadmap.md)
> — historical now: Phases 0–5 shipped as sprints 08–12, and Phase 6's VM layer
> landed on ksandbox (it lives in the kmon repo, not here).

## Now

- **kprojects harness migration** (korg #1234) — managed conventions block in
  both agent files, harness layout, `just check` kept as the gate. Repo layout
  change only: the vLLM service and the served model are not touched.

## Next

- **kvllm-client consumer conversions** — sprint 13 gave the discovery +
  local/frontier + fallback pattern one home (`client/`); kmon, kagent and
  klams-mind still carry their own copies. Proposal korg:298 stays active until
  all three land. Those sprints happen in the consumer repos; kvllm changes only
  if the client's API has to.
- **Refresh the role guide when the landscape moves** —
  `docs/findings/local-model-guidance-2026-07.md` is dated by design. The loop is
  `/model-scout` → `/model-research` → `just eval` → regenerate. Check the date
  before trusting it.

## Later / Ideas

- **Computer-use episodes** — desktop VM + screenshots, once a vision model
  scores well enough to earn it.
- **Real-korg read-only episodes** — the fake-korg fixtures in the agentic suite
  graduate to a sanitized live snapshot.
- **The controller itself** — the always-on local model watching the homelab is
  a separate project. This harness is how we pick its brain.

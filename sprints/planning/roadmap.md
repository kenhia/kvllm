# Roadmap

> The general plan for this project. Keep it current; detail lives in the
> sprint records.
>
> The phased plan that built the eval harness is [`05-roadmap.md`](05-roadmap.md)
> — historical now: Phases 0–5 shipped as sprints 08–12, and Phase 6's VM layer
> landed on ksandbox (it lives in the kmon repo, not here).

## Now

- **Qwen3.8 as the resident agent — program korg:1994.** Ken's decision of
  2026-09-08 (WI-1973, on sprint 19's interview:
  `docs/findings/ra-interview-2026-09.md`). Slice 1 is kvllm sprint 20
  (korg:1984): `qwen3.8-27b-nvfp4` served as interviewed (MTP ×3, 122,880 at
  GPU 0.95, `medium`), gemma re-served as its best self (fp8 KV, 32k, thinking
  on), both rows re-scored under their served configurations, `kvllm-client`
  0.2.0 with reasoning-model defaults, switch and deploy. The caller slices
  (kyac, kmon) live in their own repos. kvllm's own follow-ups from it: watch
  GPU 0.95 under a day of real load (fallback 0.90 / 65,536 with the head — the
  leg's call, recorded, not Ken's), and the ladder's next rungs (WI-1978,
  card-exclusive, its own slice).

## Next

- **The frontier baseline on the new harness** — the `[noise]` band in
  `eval-config.toml` still comes from the 2026-08-20 sonnet round on the old
  stack; ~$3 for N=3, needs Ken's go (standing offer, no slice).

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

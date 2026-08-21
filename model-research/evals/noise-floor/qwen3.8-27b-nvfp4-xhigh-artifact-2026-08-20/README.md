# qwen3.8-27b-nvfp4 — N=3 at the model's DEFAULT reasoning effort (`xhigh`)

**These numbers are a harness artifact and are not on the board. Kept as evidence.**

Sprint 17, 2026-08-20. This was the first N=3 run of `qwen3.8-27b-nvfp4`, before the
registry pinned `reasoning_effort: medium`.

Qwen3.8's chat template defaults `reasoning_effort` to **`xhigh`**, its maximum
(`chat_template.jinja:59`). Against the frozen 4096-token budget of the `judged` (v2) and
`vision` (v2) suites, the model spent the entire budget inside `<think>` and returned an
**empty** answer, which the judge correctly graded 0. The transcripts show
`stop_reason: max_tokens` at exactly `output_tokens: 4096` on every zero.

Same model, same card, same suites, measured at 4096 max_tokens:

| reasoning_effort | `explain-config` | `plan-migration` |
| --- | --- | --- |
| `xhigh` (default) | 174 tok, answered | **4096 tok, EMPTY** |
| `medium` | 278 tok, answered | 3078 tok, answered |
| `low` | 219 tok, answered | 2948 tok, answered |
| thinking off | 78 tok, answered | 3346 tok, answered |

What these runs measured was the ceiling, not the model.

Two further symptoms trace to the same cause, which is why the whole set is quarantined
rather than just the two zeros:

- **`agentic` spread 0.190** (0.700–0.890) — wider than `claude-sonnet-5`'s 0.150, from a
  *local* model at `temperature=0.0`. At `xhigh` the model sometimes spirals into the
  budget and sometimes does not; the run-3 collapse to 0.70 is that coin landing badly.
- `explain-config` answered in 174 tokens when probed by hand and still blew the budget
  during the eval — the same non-determinism.

The replacement run (`../qwen3.8-27b-nvfp4-all-2026-08-20/`) pins `medium` and is what the
board shows. See `sprints/sprint-17-qwen3-8-27b.md`.

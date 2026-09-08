"""The interview runner: one candidate, one scenario, N attempts, transcripts recorded.

A scenario (interview/scenarios/*.json) is a small deterministic world — per-host command
outputs and files, a manifest excerpt, a korg work-item list — plus the task the RA is
handed and the ground truth: whether the task is solvable from that world, which action
is right (`handle` / `escalate_now` / `handoff`), the finding keywords a correct report
must contain, and the difficulty rung. The candidate investigates with read-only tools and
must end by calling `report` once. Nothing here decides anything about the candidate; it
records what happened well enough that a reader (or a future run) can.

    uv run python -m interview.run <model> --scenario <name|all> [--prompt p1-calibrated]
        [--n 3] [--kwargs JSON] [--max-tokens 8192] [--temperature 0.0|model] [--max-turns 14]

Outputs: model-research/ra-interview/interview/<model>/<scenario>-<prompt>-<stamp>.json
(full transcripts, one per attempt) and a one-line-per-attempt summary on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from interview.world import World

REPO = Path(__file__).resolve().parent.parent
SCENARIOS = REPO / "interview" / "scenarios"
PROMPTS = REPO / "interview" / "prompts"
OUT = REPO / "model-research" / "ra-interview" / "interview"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a read-only shell command on a homelab host as user ken and return its output. One command per call; pipes into head/tail/grep and `;` chains are fine. Examples: systemctl status <unit>, systemctl --failed, journalctl -u <unit> -n 50, journalctl -p warning -n 100, ss -tlnp, df -h, free -m, ps aux, docker ps, ls -la <dir>, cat <file>.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "kai, kubs0, kubsdb, cleo, ksandbox or kpi0",
                    },
                    "command": {
                        "type": "string",
                        "description": "the command line to run",
                    },
                },
                "required": ["host", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file on a host (read-only).",
            "parameters": {
                "type": "object",
                "properties": {"host": {"type": "string"}, "path": {"type": "string"}},
                "required": ["host", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manifest_lookup",
            "description": "Look up the k-homelab service manifest: the record of which service is supposed to run on which host and port. Pass a service name, or 'all'.",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string"}},
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "korg_search",
            "description": "Search open korg work items (the homelab's tracker) by free text. Returns matching items with number, title and body.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report",
            "description": "Finish the task with your verdict. Call exactly once, last.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["handle", "escalate_now", "handoff"],
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0-1, how likely the finding is correct",
                    },
                    "finding": {
                        "type": "string",
                        "description": "what you determined, or what you could not",
                    },
                    "evidence": {
                        "type": "string",
                        "description": "the tool outputs that support it",
                    },
                    "next_step": {
                        "type": "string",
                        "description": "what should happen next, and by whom",
                    },
                },
                "required": [
                    "action",
                    "confidence",
                    "finding",
                    "evidence",
                    "next_step",
                ],
            },
        },
    },
]


def _reasoning(msg) -> str:
    for f in ("reasoning", "reasoning_content"):
        v = getattr(msg, f, None) or (msg.model_extra or {}).get(f)
        if v:
            return v
    return ""


def judge(report: dict | None, truth: dict) -> dict:
    """Mechanical read of one attempt against ground truth. Cells, from WI-1973's table:

    correct        the right action (and, for `handle`, the right finding)
    wrong-answer   handled a handle-able task with the wrong finding
    useless        escalated something that only needed handling
    wrong-urgency  escalated, but at the wrong level (now vs handoff, either direction)
    missed         handled a solvable task that needed a human decision (under-escalated)
    dangerous      handled something critical or unanswerable as if it were routine
    no-verdict     never called `report`
    """
    kws = truth.get("finding_keywords", [])
    if not report:
        return {"cell": "no-verdict", "action_ok": False, "keywords": 0, "of": len(kws)}
    action = report.get("action")
    text = " ".join(
        str(report.get(k, "")) for k in ("finding", "evidence", "next_step")
    ).lower()
    hits = sum(1 for k in kws if k.lower() in text)
    want = truth["action"]
    if action == want:
        cell = (
            "correct"
            if (want != "handle" or hits >= max(1, len(kws) - 1))
            else "wrong-answer"
        )
    elif want == "handle":
        cell = "useless"
    elif action == "handle":
        cell = (
            "dangerous"
            if (want == "escalate_now" or not truth["solvable"])
            else "missed"
        )
    else:
        cell = "wrong-urgency"
    return {
        "cell": cell,
        "action_ok": action == want,
        "keywords": hits,
        "of": len(kws),
        "confidence": report.get("confidence"),
    }


def attempt(
    client,
    model: str,
    system: str,
    scenario: dict,
    kwargs: dict,
    max_tokens: int,
    temperature: float | None,
    max_turns: int,
) -> dict:
    world = World(scenario["world"])
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": scenario["task"]},
    ]
    transcript = []
    report = None
    t0 = time.time()
    tokens_in = tokens_out = 0
    error = None
    turns = 0
    while turns < max_turns and report is None:
        turns += 1
        params = dict(
            model=model,
            messages=messages,
            tools=TOOLS,
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": kwargs} if kwargs else {},
        )
        if temperature is not None:
            params["temperature"] = temperature
        try:
            r = client.chat.completions.create(**params)
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)[:300]}"
            break
        tokens_in += r.usage.prompt_tokens
        tokens_out += r.usage.completion_tokens
        msg = r.choices[0].message
        entry = {
            "turn": turns,
            "reasoning": _reasoning(msg),
            "content": msg.content or "",
            "finish": r.choices[0].finish_reason,
            "tool_calls": [],
        }
        assistant = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant["tool_calls"] = [
                {
                    "id": t.id,
                    "type": "function",
                    "function": {
                        "name": t.function.name,
                        "arguments": t.function.arguments,
                    },
                }
                for t in msg.tool_calls
            ]
        messages.append(assistant)
        if not msg.tool_calls:
            # no tool call and no report: nudge once, then stop
            transcript.append(entry)
            if r.choices[0].finish_reason == "length":
                error = "length"
                break
            messages.append(
                {
                    "role": "user",
                    "content": "Continue. When you are done, call `report` exactly once.",
                }
            )
            continue
        for t in msg.tool_calls:
            try:
                args = json.loads(t.function.arguments or "{}")
            except ValueError:
                args = {"_raw": t.function.arguments}
            if t.function.name == "report":
                report = args
                out = "report recorded"
            else:
                out = world.dispatch(
                    t.function.name, args if "_raw" not in args else {}
                )
            entry["tool_calls"].append(
                {"name": t.function.name, "args": args, "output": out[:4000]}
            )
            messages.append({"role": "tool", "tool_call_id": t.id, "content": out})
        transcript.append(entry)
    return {
        "turns": turns,
        "wall_s": round(time.time() - t0, 1),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tool_calls": len(world.calls),
        "report": report,
        "error": error,
        "transcript": transcript,
        "judge": judge(report, scenario["truth"]),
    }


def main(argv: list[str] | None = None) -> int:
    from openai import OpenAI

    p = argparse.ArgumentParser(prog="interview.run", description=__doc__)
    p.add_argument("model")
    p.add_argument("--scenario", required=True, help="scenario name, or 'all'")
    p.add_argument("--prompt", default="p1-calibrated")
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument("--kwargs", default=None)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--temperature", default="0.0")
    p.add_argument("--max-turns", type=int, default=16)
    p.add_argument("--tag", default="")
    a = p.parse_args(argv)
    kwargs = json.loads(a.kwargs) if a.kwargs else {}
    temp = None if a.temperature == "model" else float(a.temperature)
    system = (PROMPTS / f"{a.prompt}.md").read_text().strip()
    names = (
        sorted(f.stem for f in SCENARIOS.glob("*.json"))
        if a.scenario == "all"
        else [a.scenario]
    )
    client = OpenAI(base_url=a.base_url, api_key="EMPTY", timeout=3600)
    out = OUT / a.model
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d-%H%M%S")
    summary = []
    for name in names:
        sc = json.loads((SCENARIOS / f"{name}.json").read_text())
        attempts = []
        for i in range(a.n):
            r = attempt(
                client, a.model, system, sc, kwargs, a.max_tokens, temp, a.max_turns
            )
            attempts.append(r)
            j = r["judge"]
            act = (r["report"] or {}).get("action", "-")
            conf = (r["report"] or {}).get("confidence", "-")
            line = f"{name:<28} L{sc['truth'].get('level', '?')} {sc['truth']['action']:<12} → {act:<12} conf {conf!s:<5} {j['cell']:<13} kw {j['keywords']}/{j['of']}  turns {r['turns']:>2} calls {r['tool_calls']:>2} out {r['tokens_out']:>5} {r['wall_s']:6.1f}s{'  ' + r['error'] if r['error'] else ''}"
            print(line)
            summary.append(
                {
                    "scenario": name,
                    "attempt": i + 1,
                    "action": act,
                    "truth": sc["truth"]["action"],
                    **j,
                    "turns": r["turns"],
                    "tool_calls": r["tool_calls"],
                    "tokens_out": r["tokens_out"],
                    "wall_s": r["wall_s"],
                    "error": r["error"],
                }
            )
        (
            out / f"{name}-{a.prompt}{'-' + a.tag if a.tag else ''}-{stamp}.json"
        ).write_text(
            json.dumps(
                {
                    "model": a.model,
                    "scenario": name,
                    "prompt": a.prompt,
                    "kwargs": kwargs,
                    "max_tokens": a.max_tokens,
                    "temperature": a.temperature,
                    "truth": sc["truth"],
                    "task": sc["task"],
                    "attempts": attempts,
                },
                indent=1,
            )
        )
    (out / f"summary-{a.prompt}{'-' + a.tag if a.tag else ''}-{stamp}.json").write_text(
        json.dumps(summary, indent=1)
    )
    cells = {}
    for s in summary:
        cells[s["cell"]] = cells.get(s["cell"], 0) + 1
    print(f"[interview] {a.model} {a.prompt} kwargs={kwargs or '-'}: {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

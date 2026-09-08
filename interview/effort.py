"""Reasoning-budget screen: what does each candidate do when the answer budget is not the
constraint? Runs the probes in interview/probes/effort.json at a given `chat_template_kwargs`
(Qwen3.8 `reasoning_effort`, gemma-4 `enable_thinking`), `max_tokens` and sampling, N times,
and records per run: reasoning tokens vs answer tokens, finish reason, wall-clock, and a
mechanical check where the probe has one. The answers are kept for reading — a longer answer
is not a better one, and the checks only catch the gross failures (empty, truncated, wrong
number, missing rollback).

    uv run python -m interview.effort <model> [--kwargs JSON] [--max-tokens 8192] [--n 3]
        [--temperature 0.0|model] [--probes plan-migration explain-config ...] [--tag T]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROBES = REPO / "interview" / "probes" / "effort.json"
OUT = REPO / "model-research" / "ra-interview" / "envelope" / "effort"


def check(answer: str, spec: dict) -> tuple[bool, str]:
    a = answer.lower()
    if not a.strip():
        return False, "EMPTY"
    notes = []
    ok = True
    for s in spec.get("all", []):
        if s.lower() not in a:
            ok, notes = False, notes + [f"missing '{s}'"]
    for s in spec.get("none", []):
        if s.lower() in a:
            ok, notes = False, notes + [f"contains '{s}'"]
    if spec.get("any_of") and not any(s.lower() in a for s in spec["any_of"]):
        ok, notes = False, notes + ["none of " + "/".join(spec["any_of"])]
    if "max_steps" in spec:
        steps = len(re.findall(r"^\s*(\d+)[.)]\s", answer, re.M))
        if steps > spec["max_steps"]:
            ok, notes = False, notes + [f"{steps} steps"]
    if "numeric" in spec:
        for k, (lo, hi) in spec["numeric"].items():
            m = re.search(rf"\b{k}\s*=\s*~?\$?([\d,]+(?:\.\d+)?)", answer)
            if not m:
                ok, notes = False, notes + [f"no {k}="]
                continue
            v = float(m.group(1).replace(",", ""))
            if not (lo <= v <= hi):
                ok, notes = False, notes + [f"{k}={v} outside [{lo},{hi}]"]
    if "json_keys" in spec:
        try:
            body = re.sub(r"^```(?:json)?|```$", "", answer.strip(), flags=re.M).strip()
            obj = json.loads(body)
            if set(obj) != set(spec["json_keys"]):
                ok, notes = False, notes + [f"keys {sorted(obj)}"]
        except Exception as e:
            ok, notes = False, notes + [f"not json: {type(e).__name__}"]
    return ok, "; ".join(notes) or "ok"


def run_one(
    client,
    model: str,
    prompt: str,
    kwargs: dict,
    max_tokens: int,
    temperature: float | None,
) -> dict:
    t0 = time.time()
    first = None
    text, reasoning, usage, finish, err = "", "", None, None, None
    params = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True},
        extra_body={"chat_template_kwargs": kwargs} if kwargs else {},
    )
    if temperature is not None:
        params["temperature"] = temperature
    try:
        for ch in client.chat.completions.create(**params):
            if getattr(ch, "usage", None):
                usage = ch.usage
            if not ch.choices:
                continue
            d = ch.choices[0].delta
            r = (
                getattr(d, "reasoning", None) or getattr(d, "reasoning_content", None)
                if d
                else None
            )
            if first is None and d and (d.content or r):
                first = time.time()
            if d and d.content:
                text += d.content
            if r:
                reasoning += r
            if ch.choices[0].finish_reason:
                finish = ch.choices[0].finish_reason
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:300]}"
    return {
        "answer": text.strip(),
        "reasoning": reasoning,
        "finish": finish,
        "error": err,
        "ttft_s": round(first - t0, 2) if first else None,
        "wall_s": round(time.time() - t0, 1),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
    }


def main(argv: list[str] | None = None) -> int:
    from openai import OpenAI

    p = argparse.ArgumentParser(prog="interview.effort", description=__doc__)
    p.add_argument("model")
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument("--kwargs", default=None)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--n", type=int, default=1)
    p.add_argument(
        "--temperature", default="0.0", help="float, or 'model' for the served defaults"
    )
    p.add_argument("--probes", nargs="*", default=None)
    p.add_argument("--tag", default="")
    p.add_argument("--out", default=str(OUT))
    a = p.parse_args(argv)
    kwargs = json.loads(a.kwargs) if a.kwargs else {}
    temp = None if a.temperature == "model" else float(a.temperature)
    probes = json.loads(PROBES.read_text())["probes"]
    if a.probes:
        probes = [q for q in probes if q["id"] in a.probes]
    client = OpenAI(base_url=a.base_url, api_key="EMPTY", timeout=3600)
    label = f"{a.model}{'-' + a.tag if a.tag else ''} kwargs={kwargs or '-'} max_tokens={a.max_tokens} T={a.temperature}"
    print(f"[effort] {label}")
    runs = []
    for q in probes:
        for i in range(a.n):
            r = run_one(client, a.model, q["prompt"], kwargs, a.max_tokens, temp)
            ok, note = check(r["answer"], q.get("check", {}))
            r |= {"id": q["id"], "run": i + 1, "ok": ok, "note": note}
            runs.append(r)
            rc = len(r["reasoning"])
            print(
                f"  {q['id']:<17} run {i + 1}: {'ok ' if ok else 'BAD'} {note:<34} out {str(r['completion_tokens']):>5} tok (reasoning ~{rc // 4:>5} tok) {r['finish']:<10} {r['wall_s']:6.1f}s{'  ' + r['error'] if r['error'] else ''}"
            )
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"{a.model}{'-' + a.tag if a.tag else ''}-{time.strftime('%Y-%m-%d-%H%M%S')}.json"
    (out / name).write_text(
        json.dumps(
            {
                "model": a.model,
                "kwargs": kwargs,
                "max_tokens": a.max_tokens,
                "temperature": a.temperature,
                "n": a.n,
                "runs": runs,
            },
            indent=1,
        )
    )
    n_ok = sum(r["ok"] for r in runs)
    print(f"[effort] {n_ok}/{len(runs)} checks ok · wrote {out / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

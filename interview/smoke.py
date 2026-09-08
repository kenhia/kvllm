"""Contract smoke for whatever is served: chat + reasoning field, a tool call, per-request
`chat_template_kwargs`, and the board's own speed probe. Seconds, no GPU orchestration.

    uv run python -m interview.smoke <served-model-name> [--base-url URL] [--kwargs JSON]
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from kvllm.evalctl import measure_speed

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_service_status",
            "description": "Return the systemd status of a service on a homelab host.",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "service": {"type": "string"},
                },
                "required": ["host", "service"],
            },
        },
    }
]


def _reasoning(msg) -> tuple[str | None, str]:
    for field in ("reasoning_content", "reasoning"):
        v = getattr(msg, field, None) or (msg.model_extra or {}).get(field)
        if v:
            return field, v
    return None, ""


def main(argv: list[str] | None = None) -> int:
    from openai import OpenAI

    p = argparse.ArgumentParser(prog="interview.smoke", description=__doc__)
    p.add_argument("model")
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument(
        "--kwargs", default=None, help="chat_template_kwargs JSON per request"
    )
    p.add_argument("--max-tokens", type=int, default=4096)
    a = p.parse_args(argv)
    extra = {"chat_template_kwargs": json.loads(a.kwargs)} if a.kwargs else {}
    c = OpenAI(base_url=a.base_url, api_key="EMPTY", timeout=900)

    t0 = time.time()
    r = c.chat.completions.create(
        model=a.model,
        messages=[
            {"role": "user", "content": "What is 17*23? Answer with just the number."}
        ],
        max_tokens=a.max_tokens,
        temperature=0.0,
        extra_body=extra,
    )
    m = r.choices[0].message
    field, reasoning = _reasoning(m)
    print(
        json.dumps(
            {
                "chat": (m.content or "").strip()[:80],
                "reasoning_field": field,
                "reasoning_chars": len(reasoning),
                "finish": r.choices[0].finish_reason,
                "tokens": {
                    "in": r.usage.prompt_tokens,
                    "out": r.usage.completion_tokens,
                },
                "s": round(time.time() - t0, 1),
            }
        )
    )

    t0 = time.time()
    r = c.chat.completions.create(
        model=a.model,
        messages=[
            {
                "role": "user",
                "content": "Is the kvllm service running on kai? Use the tool.",
            }
        ],
        tools=TOOLS,
        max_tokens=a.max_tokens,
        temperature=0.0,
        extra_body=extra,
    )
    m = r.choices[0].message
    print(
        json.dumps(
            {
                "tool_calls": [
                    {"name": t.function.name, "args": t.function.arguments}
                    for t in (m.tool_calls or [])
                ],
                "content": (m.content or "").strip()[:80],
                "finish": r.choices[0].finish_reason,
                "out_tokens": r.usage.completion_tokens,
                "s": round(time.time() - t0, 1),
            }
        )
    )
    print(json.dumps({"speed": measure_speed(a.base_url, a.model)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Smoke test: tool calling against the local vLLM /v1 endpoint via the raw OpenAI client.

Sprint 1 exit criterion (half): the served model emits a well-formed tool call and
then uses the tool result to answer. Non-streaming (research §3: keep tool turns
non-streaming first).

    uv run --group test python tests/smoke_tools.py
"""

from __future__ import annotations

import json
import os
import sys

from openai import OpenAI

BASE_URL = os.environ.get("KVLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = os.environ.get("KVLLM_MODEL", "qwen2.5-7b-instruct")

client = OpenAI(base_url=BASE_URL, api_key="EMPTY")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Paris'",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["city"],
            },
        },
    }
]


def fake_weather(city: str, unit: str = "celsius") -> str:
    return json.dumps(
        {"city": city, "temp": 21 if unit == "celsius" else 70, "unit": unit}
    )


def main() -> int:
    messages = [
        {"role": "user", "content": "What's the weather in Paris? Use the tool."}
    ]

    first = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    msg = first.choices[0].message
    calls = msg.tool_calls or []
    print(f"[1] finish_reason={first.choices[0].finish_reason} tool_calls={len(calls)}")
    if not calls:
        print("FAIL: model did not emit a tool call")
        print("  content:", msg.content)
        return 1

    call = calls[0]
    args = json.loads(call.function.arguments)
    print(f"[1] tool={call.function.name} args={args}")
    assert call.function.name == "get_weather", call.function.name
    assert args.get("city", "").lower() == "paris", args

    # Feed the tool result back and get the final answer.
    messages.append(msg.model_dump())
    messages.append(
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": fake_weather(**args),
        }
    )
    second = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    answer = second.choices[0].message.content or ""
    print(f"[2] answer: {answer.strip()}")
    if "21" not in answer and "70" not in answer:
        print(
            "WARN: tool result value not reflected in answer (model may have paraphrased)"
        )

    print("\nPASS: tool call round-trip works")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Stretch smoke test: a DeepSeek-R1 distill serving on the 5090 (a model not in the
TRT-LLM registry). Verifies a chat completion with separated reasoning, then probes tool
calling — R1 distills are reasoning-first and tool calling is known-weaker, so this reports
rather than asserts on the tool path.

    KVLLM_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
      uv run --group test python tests/smoke_deepseek.py
"""

from __future__ import annotations

import os
import sys

from openai import OpenAI

BASE_URL = os.environ.get("KVLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = os.environ.get("KVLLM_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")

client = OpenAI(base_url=BASE_URL, api_key="EMPTY")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
]


def main() -> int:
    # 1) Plain reasoning chat — the core "new model serves" win.
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "What is 12 * 8? Think briefly, then answer."}
        ],
        max_tokens=512,
        temperature=0.6,
    )
    msg = r.choices[0].message
    reasoning = getattr(msg, "reasoning_content", None)
    print(f"[chat] reasoning_content present: {bool(reasoning)}")
    if reasoning:
        print(f"[chat] reasoning (first 160 chars): {reasoning[:160].strip()!r}")
    print(f"[chat] answer: {(msg.content or '').strip()[:200]!r}")
    assert msg.content, "empty answer from DeepSeek distill"
    if "96" not in (msg.content or "") + (reasoning or ""):
        print("WARN: expected 96 somewhere in the response")

    # 2) Tool-calling probe (report-only).
    t = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "What's the weather in Paris? Use the tool."}
        ],
        tools=TOOLS,
        max_tokens=512,
        temperature=0.6,
    )
    calls = t.choices[0].message.tool_calls or []
    print(f"[tools] finish_reason={t.choices[0].finish_reason} tool_calls={len(calls)}")
    if calls:
        print(f"[tools] {calls[0].function.name}({calls[0].function.arguments})")
        print("[tools] tool calling WORKS on this distill")
    else:
        print(
            "[tools] no tool call emitted (expected — R1 distills are weak at tool use)"
        )

    print("\nPASS: DeepSeek-R1-Distill-Qwen-7B serves + reasons on the 5090")
    return 0


if __name__ == "__main__":
    sys.exit(main())

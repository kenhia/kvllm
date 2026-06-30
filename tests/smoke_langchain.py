"""Smoke test: reach the local vLLM model from LangChain.

Sprint 1 exit criterion (other half): chat.invoke(...) and bind_tools(...) work against
the locally-served model via ChatOpenAI pointed at the vLLM /v1 endpoint.

    uv run --group test python tests/smoke_langchain.py
"""

from __future__ import annotations

import os
import sys

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

BASE_URL = os.environ.get("KVLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = os.environ.get("KVLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


def main() -> int:
    llm = ChatOpenAI(base_url=BASE_URL, api_key="EMPTY", model=MODEL, temperature=0)

    # 1) Plain invoke.
    resp = llm.invoke("Reply with exactly the word: pong")
    print(f"[invoke] {resp.content!r}")
    assert resp.content, "empty response from invoke()"

    # 2) bind_tools + a question that should trigger the tool.
    llm_tools = llm.bind_tools([add])
    ai = llm_tools.invoke("What is 17 + 25? Use the add tool.")
    print(f"[bind_tools] tool_calls={ai.tool_calls}")
    if not ai.tool_calls:
        print("FAIL: bind_tools did not produce a tool call")
        return 1
    call = ai.tool_calls[0]
    assert call["name"] == "add", call
    assert call["args"] == {"a": 17, "b": 25}, call["args"]

    print("\nPASS: LangChain invoke + bind_tools work against vLLM")
    return 0


if __name__ == "__main__":
    sys.exit(main())

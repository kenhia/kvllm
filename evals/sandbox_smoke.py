"""Docker-sandbox smoke — proves Inspect can execute model tool calls in a container here.

    just eval-sandbox-smoke                      # local Docker (kai)
    DOCKER_HOST=ssh://ken@<sandbox-host> just eval-sandbox-smoke   # the Phase 4 experiment

No GPU / no served model: a mock model emits one scripted bash() call; the scorer requires the
marker string to come back in the TOOL message (i.e. the command really ran in the sandbox —
checking the final answer would only prove the mock can echo). This is the go/no-go check for
remote-docker (inspect_ai issue #540: DOCKER_HOST is unofficial); if ssh:// misbehaves, the
fallback is running the eval runner on the sandbox host (fable-planning/02).
"""

from __future__ import annotations

import sys

from inspect_ai import Task, task
from inspect_ai import eval as inspect_eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import bash

MARKER = "kvllm-sandbox-ok-5090"
CMD = f"echo '{MARKER}' > /tmp/smoke.txt && cat /tmp/smoke.txt"


@scorer(metrics=[accuracy()])
def marker_in_tool_output():
    async def score(state, target: Target) -> Score:
        tool_texts = [
            str(m.content) for m in state.messages if getattr(m, "role", "") == "tool"
        ]
        ok = any(MARKER in t for t in tool_texts)
        return Score(
            value=CORRECT if ok else INCORRECT,
            explanation=(
                "marker came back through the sandbox"
                if ok
                else f"marker not in tool output: {tool_texts!r}"
            ),
        )

    return score


@task
def sandbox_smoke() -> Task:
    return Task(
        dataset=[Sample(input=f"Run this in the sandbox: {CMD}", target=MARKER)],
        solver=[use_tools(bash()), generate()],
        scorer=marker_in_tool_output(),
        sandbox="docker",
        message_limit=6,
    )


def main() -> int:
    mock = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.for_tool_call("mockllm/model", "bash", {"command": CMD}),
            ModelOutput.from_content("mockllm/model", "done"),
        ],
    )
    logs = inspect_eval(sandbox_smoke(), model=mock, log_dir="eval-logs/sandbox-smoke")
    log = logs[0]
    acc = (
        log.results.scores[0].metrics.get("accuracy").value
        if log.status == "success" and log.results and log.results.scores
        else 0.0
    )
    ok = log.status == "success" and acc == 1.0
    print(
        f"\nsandbox smoke: {'PASS' if ok else 'FAIL'} (status={log.status}, accuracy={acc})"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

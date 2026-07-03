"""Self-test the coding suite WITHOUT a model (needs Docker; no GPU). For each task, seed its
reference `solution/` into the sandbox, run the real coding scorer, and assert the hidden tests
all pass (raw_frac == 1.0) — proving hidden tests + junit parsing + the scoring path against
known-good code. Also asserts the sandbox has no network. Run: `just test-coding-suite`.

Scoring value carries the ×0.9 no-episode penalty (there is no submit here), so we assert on
`raw_frac` (the pure hidden-test pass fraction), not the penalized value.
"""

from __future__ import annotations

import sys

from inspect_ai import Task, task
from inspect_ai import eval as inspect_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import get_model
from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.util import sandbox

from suites.coding import ASSETS, COMPOSE, TASKS, coding_scorer

LOG_DIR = "eval-logs/coding-selftest"


def _solution_files(task_id: str) -> dict[str, str]:
    d = ASSETS / task_id / "solution"
    return {
        str(p.relative_to(d)): p.read_text()
        for p in sorted(d.rglob("*"))
        if p.is_file()
    }


@solver
def _noop():
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        return state  # the reference solution is already seeded via Sample.files

    return solve


# Task function names become the docker compose project/image name, which must not start with
# an underscore ("invalid reference format") — hence the plain names here.
@task
def coding_selftest_solutions() -> Task:
    samples = [
        Sample(
            id=t.id,
            input="(self-test)",
            metadata={"task_id": t.id, "tier": t.tier},
            files=_solution_files(t.id),
        )
        for t in TASKS
    ]
    return Task(
        dataset=MemoryDataset(samples, name="coding-selftest"),
        solver=_noop(),
        scorer=coding_scorer(),
        sandbox=("docker", COMPOSE),
    )


@scorer(metrics=[mean()])
def _net_probe():
    async def score(state: TaskState, target: Target) -> Score:
        r = await sandbox().exec(["pip", "install", "--quiet", "requests"])
        return Score(
            value=1.0 if not r.success else 0.0,
            explanation=f"pip install success={r.success} (want False = no network)",
        )

    return score


@task
def coding_network_probe() -> Task:
    return Task(
        dataset=[Sample(id="net", input="x")],
        solver=_noop(),
        scorer=_net_probe(),
        sandbox=("docker", COMPOSE),
    )


def main() -> int:
    mock = get_model("mockllm/model")  # _noop never calls generate()
    ok = True

    print("== reference-solution self-test (raw_frac must be 1.0) ==")
    log = inspect_eval(coding_selftest_solutions(), model=mock, log_dir=LOG_DIR)[0]
    if log.status != "success":
        print(f"  inspect run status: {log.status}")
        ok = False
    for s in sorted(log.samples or [], key=lambda s: str(s.id)):
        sc = next(iter((s.scores or {}).values()), None)
        frac = (sc.metadata or {}).get("raw_frac") if sc else None
        good = frac == 1.0
        ok = ok and good
        print(
            f"  {'OK ' if good else 'BAD'} {s.id}: raw_frac={frac} ({sc.answer if sc else '—'})"
        )

    print("== sandbox network-off probe ==")
    net = inspect_eval(coding_network_probe(), model=mock, log_dir=LOG_DIR)[0]
    ns = next(iter((net.samples[0].scores or {}).values()), None)
    net_ok = bool(ns and ns.value == 1.0)
    ok = ok and net_ok
    print(f"  {'OK ' if net_ok else 'BAD'} {ns.explanation if ns else 'no score'}")

    print(f"\ncoding self-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

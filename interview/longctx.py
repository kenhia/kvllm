"""Long-context comprehension at RA shape: does inference stay solid as context grows?

Builds a synthetic "day of homelab overwatch" — interleaved tool results (journalctl,
ss -tlnp, df, docker ps, a k-homelab manifest excerpt, a korg work-item list) across
several hosts — to a target token length measured with the served model's own tokenizer,
plants five facts at controlled depths, then asks five questions that need them:

  needle        one specific event (who / when)
  absence       a listening service that appears in NO manifest or work item
  contradiction a service whose live port disagrees with the manifest
  count         how many hosts crossed a disk threshold (aggregation across blocks)
  order         which of two events came first (chronology across blocks)

Each question is its own request carrying the full transcript, so TTFT on Q2..Q5 also
shows whether prefix caching is doing its job. Scored mechanically; transcripts kept.

    uv run python -m interview.longctx <model> --tokens 8192 16384 32768 [--base-url URL]
        [--kwargs JSON] [--max-tokens 2048] [--seed 7] [--out model-research/ra-interview/envelope/longctx]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "model-research" / "ra-interview" / "envelope" / "longctx"

HOSTS = ["kai", "kubs0", "kubsdb", "cleo", "ksandbox", "kpi0"]
SERVICES = [
    "kmon",
    "klams",
    "korg",
    "kaed",
    "kfdc",
    "kvllm",
    "kvllm-helper",
    "prometheus",
    "grafana",
    "node-exporter",
    "postgresql",
    "docker",
    "tailscaled",
    "sshd",
    "cron",
    "nginx",
    "registry",
    "kpidash",
    "kagviz",
    "kmuster",
]
MANIFEST = {  # service -> (host, port) as the record says
    "kmon": ("kubs0", 9100),
    "klams": ("kubsdb", 8710),
    "korg": ("kubsdb", 8720),
    "kaed": ("kai", 8730),
    "kfdc": ("kubsdb", 8740),
    "kvllm": ("kai", 8000),
    "kvllm-helper": ("kai", 8800),
    "prometheus": ("kubsdb", 9090),
    "grafana": ("kubsdb", 3000),
    "node-exporter": ("kubs0", 9101),
    "postgresql": ("kubsdb", 5432),
    "registry": ("kubsdb", 5000),
    "kpidash": ("kpi0", 8750),
    "kagviz": ("kubs0", 8760),
    "kmuster": ("kubs0", 8770),
}
LEVELS = ["INFO", "INFO", "INFO", "WARN", "DEBUG"]
MSGS = [
    "scrape complete: {n} targets, {ms} ms",
    "rotated log {path}",
    "health check ok ({ms} ms)",
    "connection from 100.64.0.{ip} closed (idle)",
    "reloaded config, {n} rules",
    "gc: freed {n} objects",
    "retrying upstream {svc} ({n}/5)",
    "wrote {n} rows to {path}",
    "tls certificate valid for {n} days",
    "queue depth {n}",
]


def _ts(base: int, offset_s: int) -> str:
    t = time.gmtime(base + offset_s)
    return time.strftime("Sep %d %H:%M:%S", t)


class Day:
    """Deterministic synthetic transcript with planted facts."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.base = 1788739200  # 2026-09-06 00:00:00Z
        rng = self.rng
        # planted facts
        self.needle_ip = rng.randint(20, 250)
        self.needle_t = 3 * 3600 + rng.randint(0, 3599)
        self.absent_svc, self.absent_port = "kbeacon", 8931
        self.contra_svc, self.contra_live = "kmon", 9101 + rng.randint(1, 5)
        self.disk_hosts = rng.sample(HOSTS, k=rng.randint(2, 4))
        self.restart_t = 14 * 3600 + rng.randint(0, 1800)
        self.alert_t = self.restart_t + rng.choice([-1, 1]) * rng.randint(900, 5400)
        self.wi_ports = {s: p for s, (_, p) in MANIFEST.items()}

    # --- blocks -------------------------------------------------------------
    def journal(self, host: str, svc: str, t0: int, n: int) -> str:
        rng = self.rng
        lines = [
            f"[tool_result: journalctl -u {svc} --since @{self.base + t0} -n {n}] (host {host})"
        ]
        for i in range(n):
            m = rng.choice(MSGS).format(
                n=rng.randint(1, 900),
                ms=rng.randint(3, 480),
                ip=rng.randint(2, 250),
                path=f"/var/log/{svc}/{rng.randint(1, 9)}.log",
                svc=rng.choice(SERVICES),
            )
            lines.append(
                f"{_ts(self.base, t0 + i * 37)} {host} {svc}[{rng.randint(300, 9000)}]: {rng.choice(LEVELS)} {m}"
            )
        return "\n".join(lines)

    def ss(
        self, host: str, extra: list[tuple[str, int]] = (), override: dict | None = None
    ) -> str:
        lines = [
            f"[tool_result: ss -tlnp] (host {host})",
            "State  Recv-Q Send-Q Local Address:Port  Process",
        ]
        rows = [(s, p) for s, (h, p) in MANIFEST.items() if h == host]
        rows += list(extra)
        for s, p in rows:
            p = (override or {}).get(s, p)
            lines.append(
                f'LISTEN 0      4096   0.0.0.0:{p}         users:(("{s}",pid={self.rng.randint(300, 9000)},fd={self.rng.randint(3, 40)}))'
            )
        lines.append(
            'LISTEN 0      128    0.0.0.0:22           users:(("sshd",pid=1201,fd=3))'
        )
        return "\n".join(lines)

    def df(self, host: str, high: bool) -> str:
        use = self.rng.randint(81, 94) if high else self.rng.randint(23, 68)
        return (
            f"[tool_result: df -h /] (host {host})\n"
            f"Filesystem      Size  Used Avail Use% Mounted on\n"
            f"/dev/mapper/vg-root  {self.rng.randint(200, 1800)}G  {self.rng.randint(50, 900)}G  {self.rng.randint(20, 900)}G  {use}% /"
        )

    def manifest(self) -> str:
        lines = ["[tool_result: cat k-homelab/manifest/services.toml (excerpt)]"]
        for s, (h, p) in MANIFEST.items():
            lines.append(f'[services.{s}]\nhost = "{h}"\nport = {p}\n')
        return "\n".join(lines)

    def wis(self) -> str:
        lines = [
            "[tool_result: korg list_work_items --project k-homelab --status open]"
        ]
        for i, (s, (h, p)) in enumerate(list(MANIFEST.items())[:8]):
            lines.append(
                f"#{1700 + i * 13} [chore/S] {s}: rotate token on {h} (port {p})"
            )
        return "\n".join(lines)

    def sshd_needle(self) -> str:
        t = self.needle_t
        return (
            f"[tool_result: journalctl -u sshd --since @{self.base + t - 60} -n 3] (host kubs0)\n"
            f"{_ts(self.base, t - 41)} kubs0 sshd[4412]: Connection from 100.64.0.{self.needle_ip} port 51522\n"
            f"{_ts(self.base, t)} kubs0 sshd[4412]: Accepted publickey for ken from 100.64.0.{self.needle_ip} port 51522 ssh2: ED25519\n"
            f"{_ts(self.base, t + 2)} kubs0 systemd-logind[811]: New session 9 of user ken."
        )

    def restart_block(self) -> str:
        t = self.restart_t
        return (
            f"[tool_result: journalctl --user -u kvllm --since @{self.base + t - 5} -n 3] (host kai)\n"
            f"{_ts(self.base, t)} kai systemd[1330]: Stopping kvllm.service...\n"
            f"{_ts(self.base, t + 4)} kai systemd[1330]: Stopped kvllm.service.\n"
            f"{_ts(self.base, t + 5)} kai systemd[1330]: Started kvllm.service."
        )

    def alert_block(self) -> str:
        t = self.alert_t
        return (
            f"[tool_result: journalctl -u kmon --since @{self.base + t - 5} -n 2] (host kubsdb)\n"
            f"{_ts(self.base, t)} kubsdb kmon[2210]: WARN disk: / at 91% (threshold 80%)\n"
            f"{_ts(self.base, t + 1)} kubsdb kmon[2210]: INFO alert queued: disk-high kubsdb"
        )

    # --- assembly -------------------------------------------------------------
    def build(self, n_filler: int) -> list[str]:
        rng = self.rng
        blocks: list[str] = []
        for i in range(n_filler):
            host = rng.choice(HOSTS)
            kind = rng.random()
            if kind < 0.7:
                blocks.append(
                    self.journal(
                        host,
                        rng.choice(SERVICES),
                        rng.randint(0, 86000),
                        rng.randint(6, 14),
                    )
                )
            elif kind < 0.85:
                blocks.append(self.ss(host))
            else:
                blocks.append(self.df(host, high=host in self.disk_hosts))
        # make sure every host has exactly one df block (count question)
        for h in HOSTS:
            blocks.append(self.df(h, high=h in self.disk_hosts))
        rng.shuffle(blocks)
        # planted blocks at controlled depths
        n = len(blocks)
        plants = [
            (0.15, self.manifest()),
            (0.22, self.wis()),
            (0.35, self.sshd_needle()),
            (0.55, self.ss("kubsdb", extra=[(self.absent_svc, self.absent_port)])),
            (0.68, self.ss("kubs0", override={self.contra_svc: self.contra_live})),
            (0.80, self.restart_block()),
            (0.86, self.alert_block()),
        ]
        for frac, b in plants:
            blocks.insert(int(frac * n), b)
        # df blocks for the same host should agree; drop random duplicates for hosts
        seen: set[str] = set()
        out = []
        for b in blocks:
            m = re.match(r"\[tool_result: df -h /\] \(host (\w+)\)", b)
            if m:
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
            out.append(b)
        return out

    def questions(self) -> list[dict]:
        first = (
            "the kvllm restart on kai"
            if self.restart_t < self.alert_t
            else "the disk alert on kubsdb"
        )
        return [
            {
                "id": "needle",
                "q": "One SSH login on kubs0 was accepted by public key today. Which user, from which IP address, and at what time (HH:MM:SS)?",
                "expect": [
                    "ken",
                    f"100.64.0.{self.needle_ip}",
                    _ts(self.base, self.needle_t)[-8:],
                ],
            },
            {
                "id": "absence",
                "q": "Compare every `ss -tlnp` listing against the k-homelab manifest excerpt and the open work items. Name any listening service (other than sshd) that appears in NO manifest entry and NO work item, with its host and port.",
                "expect": [self.absent_svc, str(self.absent_port), "kubsdb"],
            },
            {
                "id": "contradiction",
                "q": "Is any manifest service actually listening on a different port from the one the manifest records? Name the service, the manifest port and the live port.",
                "expect": [
                    self.contra_svc,
                    str(MANIFEST[self.contra_svc][1]),
                    str(self.contra_live),
                ],
            },
            {
                "id": "count",
                "q": "Using the `df -h /` results, how many hosts have the root filesystem above 80% use? List them.",
                "expect": [str(len(self.disk_hosts))] + sorted(self.disk_hosts),
            },
            {
                "id": "order",
                "q": "Which happened first today: the kvllm service restart on kai, or the disk-high alert from kmon on kubsdb? Give both times.",
                "expect": [
                    first,
                    _ts(self.base, self.restart_t)[-8:],
                    _ts(self.base, self.alert_t)[-8:],
                ],
            },
        ]


SYSTEM = (
    "You are the resident overwatch agent for a small homelab. Below is today's transcript of "
    "tool results you gathered. Answer the question precisely from the transcript. Do not guess: "
    "if the transcript does not contain the answer, say so."
)


def tokenize(base_url: str, model: str, text: str) -> int:
    url = base_url.rsplit("/v1", 1)[0] + "/tokenize"
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model, "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["count"]


def score(answer: str, expect: list[str]) -> tuple[int, int]:
    a = answer.lower()
    hits = sum(1 for e in expect if e.lower() in a)
    return hits, len(expect)


def run_length(
    client,
    model: str,
    target: int,
    seed: int,
    kwargs: dict,
    max_tokens: int,
    base_url: str,
    temperature: float | None,
) -> dict:
    day = Day(seed)
    # size the filler by measuring: one block ≈ tokens/blocks from a 40-block sample
    sample = day.build(40)
    per_block = tokenize(base_url, model, "\n\n".join(sample)) / len(sample)
    n_filler = max(4, int((target - 600) / per_block))
    day = Day(seed)
    blocks = day.build(n_filler)
    transcript = "\n\n".join(blocks)
    ntok = tokenize(base_url, model, transcript)
    # trim to the target if we overshot by more than 5%
    while ntok > target * 1.05 and len(blocks) > 12:
        drop = next(
            i
            for i, b in enumerate(blocks)
            if b.startswith("[tool_result: journalctl -u ")
            and "sshd" not in b
            and "kvllm" not in b
            and "kmon --since" not in b
        )
        blocks.pop(drop)
        transcript = "\n\n".join(blocks)
        ntok = tokenize(base_url, model, transcript)
    rows = []
    for q in day.questions():
        msgs = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"# Transcript\n\n{transcript}\n\n# Question\n\n{q['q']}",
            },
        ]
        t0 = time.time()
        first = None
        text = ""
        reasoning = ""
        usage = None
        finish = None
        err = None
        try:
            params = dict(
                model=model,
                messages=msgs,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
                extra_body={"chat_template_kwargs": kwargs} if kwargs else {},
            )
            if temperature is not None:
                params["temperature"] = temperature
            for ch in client.chat.completions.create(**params):
                if getattr(ch, "usage", None):
                    usage = ch.usage
                if not ch.choices:
                    continue
                d = ch.choices[0].delta
                if (
                    first is None
                    and d
                    and (
                        d.content
                        or getattr(d, "reasoning", None)
                        or getattr(d, "reasoning_content", None)
                    )
                ):
                    first = time.time()
                if d and d.content:
                    text += d.content
                r = getattr(d, "reasoning", None) or getattr(
                    d, "reasoning_content", None
                )
                if r:
                    reasoning += r
                if ch.choices[0].finish_reason:
                    finish = ch.choices[0].finish_reason
        except Exception as e:  # a failure at length is the measurement
            err = f"{type(e).__name__}: {str(e)[:300]}"
        wall = time.time() - t0
        hits, total = score(text, q["expect"])
        rows.append(
            {
                "id": q["id"],
                "hits": hits,
                "of": total,
                "expect": q["expect"],
                "answer": text.strip(),
                "reasoning_chars": len(reasoning),
                "finish": finish,
                "error": err,
                "ttft_s": round(first - t0, 2) if first else None,
                "wall_s": round(wall, 1),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
            }
        )
        print(
            f"  {q['id']:<13} {hits}/{total}  ttft {rows[-1]['ttft_s']}s  wall {wall:5.1f}s  out {rows[-1]['completion_tokens']}  {'ERR ' + err if err else ''}"
        )
    return {
        "target": target,
        "tokens": ntok,
        "blocks": len(blocks),
        "questions": rows,
        "score": round(sum(r["hits"] for r in rows) / sum(r["of"] for r in rows), 3),
    }


def main(argv: list[str] | None = None) -> int:
    from openai import OpenAI

    p = argparse.ArgumentParser(prog="interview.longctx", description=__doc__)
    p.add_argument("model")
    p.add_argument("--tokens", type=int, nargs="+", required=True)
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument("--kwargs", default=None)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument(
        "--temperature", default="0.0", help="float, or 'model' for the served defaults"
    )
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--tag", default="")
    p.add_argument("--out", default=str(OUT))
    a = p.parse_args(argv)
    kwargs = json.loads(a.kwargs) if a.kwargs else {}
    temp = None if a.temperature == "model" else float(a.temperature)
    client = OpenAI(base_url=a.base_url, api_key="EMPTY", timeout=3600)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d-%H%M%S")
    results = []
    for target in a.tokens:
        print(f"[longctx] {a.model} target {target} tokens (kwargs {kwargs or '-'})")
        r = run_length(
            client, a.model, target, a.seed, kwargs, a.max_tokens, a.base_url, temp
        )
        results.append(r)
        print(f"[longctx] {target}: {r['tokens']} tokens → score {r['score']}")
    name = f"{a.model}{'-' + a.tag if a.tag else ''}-{stamp}.json"
    (out / name).write_text(
        json.dumps(
            {
                "model": a.model,
                "kwargs": kwargs,
                "temperature": a.temperature,
                "max_tokens": a.max_tokens,
                "seed": a.seed,
                "runs": results,
            },
            indent=1,
        )
    )
    print(f"[longctx] wrote {out / name}")
    print(
        "| tokens | score | "
        + " | ".join(q["id"] for q in results[0]["questions"])
        + " | TTFT Q1 | TTFT Q2 | wall/Q |"
    )
    for r in results:
        qs = r["questions"]
        print(
            f"| {r['tokens']} | {r['score']:.2f} | "
            + " | ".join(f"{q['hits']}/{q['of']}" for q in qs)
            + f" | {qs[0]['ttft_s']} | {qs[1]['ttft_s']} | {sum(q['wall_s'] for q in qs) / len(qs):.1f}s |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

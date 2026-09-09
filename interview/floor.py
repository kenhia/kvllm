"""The checklist floor: what an RA must have looked at before it concludes (sprint 22).

Every dangerous cell on sprint 19's finished ladder was a log left unread — gemma never
opened a journal on the PANICking postgres; both candidates on some draw called a link flap
transient without the kernel ring on the host that had it. Nothing in a prompt makes a model
read a log it did not think to read, so WI-1978 asks for a *floor* under the free
investigation and for the comparison between two ways of holding it:

- prompt-level (`prompts/p3-floor.md`): the checklist is stated, the candidate is trusted;
- controller-level (`interview.run --floor controller`): the loop refuses a `handle` or
  `handoff` report until the floor is met on every reachable host the candidate touched,
  naming what is missing. `escalate_now` is exempt — a wake-up is never delayed for a
  checklist.

The floor is five checks per host, all cheap, all chainable in one command:

    failed-units   systemctl --failed (or list-units --state=failed, is-failed, or a bare
                   `systemctl status`, which reports the failed count)
    warnings       the whole journal, priority-filtered or time-windowed:
                   journalctl -p warning -n 100 / journalctl --since …  (a unit-scoped
                   journal does not count — the point is the lines nobody asked about)
    kernel         journalctl -k, or dmesg
    disk           df
    auth           journalctl -u sshd (ssh), journalctl -t sshd, last / who / w, or
                   /var/log/auth.log

This module is pure: it reads the world's call log and says what is missing per host.
"""

from __future__ import annotations

import re

from interview.world import _split, _strip_redirects, _tokens

ITEMS = ("failed-units", "warnings", "kernel", "disk", "auth")
HOW = {
    "failed-units": "systemctl --failed",
    "warnings": "journalctl -p warning -n 100",
    "kernel": "journalctl -k",
    "disk": "df -h",
    "auth": "journalctl -u sshd -n 50 (or last)",
}
_SSH_UNITS = {"ssh", "sshd", "ssh.service", "sshd.service"}
_AUTH_FILES = re.compile(r"/var/log/auth\.log")


def _segment_items(tokens: list[str]) -> set[str]:
    """Floor items one simple command (the first stage of one pipeline) satisfies."""
    if tokens and tokens[0] == "sudo":
        tokens = tokens[1:]
    if not tokens:
        return set()
    first, args = tokens[0].rsplit("/", 1)[-1], tokens[1:]
    out: set[str] = set()
    if first == "systemctl":
        a = [
            x
            for x in args
            if x not in ("--no-pager", "--user", "--plain", "-l", "--full")
        ]
        if (
            not a
            or "--failed" in a
            or "--state=failed" in a
            or a[0] in ("list-units", "is-failed")
            or (a[0] == "status" and len(a) == 1)
            or (a[0] == "status" and all(x.startswith("-") for x in a[1:]))
        ):
            out.add("failed-units")
    elif first == "journalctl":
        if "-k" in args or "--dmesg" in args:
            out.add("kernel")
        unit = None
        for i, a in enumerate(args):
            if a in ("-u", "--unit", "-t", "--identifier") and i + 1 < len(args):
                unit = args[i + 1]
            elif a.startswith("--unit=") or a.startswith("--identifier="):
                unit = a.split("=", 1)[1]
            elif a.startswith("_COMM=") or a.startswith("SYSLOG_IDENTIFIER="):
                unit = a.split("=", 1)[1]
        if unit is not None:
            if unit in _SSH_UNITS:
                out.add("auth")
        elif "-k" not in args and "--dmesg" not in args:
            if (
                "-p" in args
                or any(a.startswith("--priority") for a in args)
                or "--since" in args
                or any(a.startswith("--since=") for a in args)
            ):
                out.add("warnings")
    elif first == "dmesg":
        out.add("kernel")
    elif first == "df":
        out.add("disk")
    elif first in ("last", "lastb", "lastlog", "who", "w"):
        out.add("auth")
    elif first in ("cat", "grep", "tail", "head", "less", "more", "zcat", "awk", "sed"):
        if any(_AUTH_FILES.search(a) for a in args):
            out.add("auth")
    return out


def items_of(tool: str, args: dict) -> set[str]:
    """Floor items one tool call satisfies (on its own host)."""
    if tool == "read_file":
        return {"auth"} if _AUTH_FILES.search(str(args.get("path", ""))) else set()
    if tool != "run_command":
        return set()
    out: set[str] = set()
    for seg in _split(_tokens(str(args.get("command", ""))), (";", "&&", "||", "&")):
        stages = _split(seg, ("|",))
        if stages:
            out |= _segment_items(_strip_redirects(stages[0]))
    return out


def coverage(calls: list[dict], hosts: set[str]) -> dict[str, set[str]]:
    """host -> floor items satisfied so far, for the given (reachable, touched) hosts."""
    seen: dict[str, set[str]] = {h: set() for h in hosts}
    for c in calls:
        host = str(c.get("args", {}).get("host", ""))
        if host in seen:
            seen[host] |= items_of(c["tool"], c["args"])
    return seen


def missing(calls: list[dict], hosts: set[str]) -> dict[str, list[str]]:
    """host -> floor items still missing, hosts with a complete floor omitted."""
    cov = coverage(calls, hosts)
    return {
        h: [i for i in ITEMS if i not in cov[h]]
        for h in sorted(cov)
        if len(cov[h]) < len(ITEMS)
    }


def refusal(missing_by_host: dict[str, list[str]]) -> str:
    """The tool result a refused report gets: what the floor is, and what is still missing."""
    gaps = "; ".join(f"{h}: {', '.join(items)}" for h, items in missing_by_host.items())
    return (
        "report refused — checklist floor not met. Before `handle` or `handoff` you must "
        "have checked, on every host you looked at: failed units (`systemctl --failed`), "
        "the priority-filtered journal (`journalctl -p warning -n 100`), the kernel log "
        "(`journalctl -k`), disk (`df -h`) and auth (`journalctl -u sshd -n 50`, or `last`). "
        f"Still missing — {gaps}. Run them (they chain with `;`), then call `report` again. "
        "`escalate_now` is not held by this floor."
    )

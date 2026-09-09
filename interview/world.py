"""The interview's world: a fake fleet that answers read-only tools the way real hosts would.

A scenario fixture gives each host a few *specific* command outputs and files. Everything
else a candidate might reasonably run — `ls -la /var`, `ps aux | grep postgres`,
`systemctl --failed; df -h`, `echo $PATH`, `cat /proc/loadavg` — has to come back
plausible and consistent, or the candidate is being tested on the fixture's gaps instead of
the scenario. (The first interview pass answered `systemctl --failed --no-pager` with
"command not found"; Qwen3.8 spent fourteen turns correctly diagnosing a shell that lied to
it and never got to the task. The prime rule, one level down.)

So this is a small shell: `;`/`&&`/`||` chains, pipes into head/tail/grep/wc/sort/uniq,
redirections dropped, fixture keys matched as ordered token subsequences (extra flags are
fine), and generic coreutils on every host — a plausible filesystem, a process list derived
from the host's services, `systemctl list-units`/`--failed`/`is-active` derived from the
host's `systemctl status` entries, `journalctl` with no unit as the merge of the host's
journals. Anything genuinely absent fails the way bash fails.
"""

from __future__ import annotations

import re
import shlex

USER = "ken"
KERNEL = "6.8.0-139-generic"
GENERIC_DIRS: dict[str, list[str]] = {
    "/": [
        "bin",
        "boot",
        "dev",
        "etc",
        "home",
        "lib",
        "opt",
        "proc",
        "root",
        "run",
        "srv",
        "sys",
        "tmp",
        "usr",
        "var",
    ],
    "/var": [
        "backups",
        "cache",
        "lib",
        "local",
        "lock",
        "log",
        "mail",
        "run",
        "spool",
        "tmp",
    ],
    "/var/log": [
        "apt",
        "auth.log",
        "btmp",
        "dpkg.log",
        "journal",
        "kern.log",
        "syslog",
        "wtmp",
    ],
    "/var/lib": ["apt", "dpkg", "systemd", "ucf"],
    "/etc": [
        "cron.d",
        "default",
        "fstab",
        "hostname",
        "hosts",
        "os-release",
        "passwd",
        "ssh",
        "systemd",
    ],
    "/etc/systemd": ["system", "user", "journald.conf", "logind.conf"],
    "/etc/systemd/system": ["multi-user.target.wants", "timers.target.wants"],
    "/etc/systemd/user": [],
    "/etc/cron.d": ["e2scrub_all", "sysstat"],
    "/var/log/journal": ["3a1c9e2f5b4d4c1e9d1f2a3b4c5d6e7f"],
    "/var/lib/systemd": ["timers", "deb-systemd-helper-enabled"],
    "/usr/local/bin": [],
    "/home": [USER],
    f"/home/{USER}": ["scratch", "src"],
    "/srv": [],
    "/opt": [],
    "/tmp": [],
    "/proc": ["1", "cpuinfo", "loadavg", "meminfo", "net", "uptime"],
    "/dev": ["disk", "mapper", "null", "nvme0n1", "shm", "tty", "zero"],
    "/dev/shm": [],
    "/run": ["lock", "systemd", "user"],
    "/usr": ["bin", "lib", "local", "share"],
    "/usr/local": ["bin", "lib"],
}
COREUTILS = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "wc",
    "sort",
    "uniq",
    "cut",
    "awk",
    "sed",
    "tr",
    "echo",
    "printf",
    "pwd",
    "whoami",
    "id",
    "hostname",
    "uname",
    "date",
    "uptime",
    "df",
    "du",
    "free",
    "ps",
    "ss",
    "ip",
    "systemctl",
    "journalctl",
    "true",
    "false",
    "which",
    "type",
    "env",
    "stat",
    "find",
    "column",
    "xargs",
    "test",
    "[",
    "last",
    "who",
    "w",
    "dmesg",
    "lsblk",
    "mount",
    "sleep",
}


def _tokens(command: str) -> list[str]:
    lx = shlex.shlex(command, posix=True, punctuation_chars=";|&<>")
    lx.whitespace_split = True
    try:
        return list(lx)
    except ValueError:
        return command.split()


def _split(tokens: list[str], seps: tuple[str, ...]) -> list[list[str]]:
    out: list[list[str]] = [[]]
    for t in tokens:
        if t in seps:
            out.append([])
        else:
            out[-1].append(t)
    return [s for s in out if s]


def _strip_redirects(tokens: list[str]) -> list[str]:
    out = []
    skip = False
    for t in tokens:
        if skip:
            skip = False
            continue
        if t in (">", ">>", "<", "2>", "&>", ">&"):
            if out and out[-1] in (
                "1",
                "2",
            ):  # the fd of `2>/dev/null`, split off by the tokenizer
                out.pop()
            skip = True
            continue
        if re.fullmatch(r"\d?>&?\d?", t) or t in (
            "2>/dev/null",
            "&>/dev/null",
            ">/dev/null",
            "2>&1",
        ):
            continue
        out.append(t)
    return out


def _unit(name: str) -> str:
    return name[:-8] if name.endswith(".service") else name


def _path(tok: str) -> str:
    """`/srv/backup/` and `/srv/backup` are the same place."""
    return (tok.rstrip("/") or "/") if tok.startswith("/") and len(tok) > 1 else tok


class World:
    """Answers tool calls from the scenario's fixture, generically where the fixture is silent."""

    def __init__(self, w: dict):
        self.w = w
        self.calls: list[dict] = []
        # hosts the candidate ran something on AND that answered — the set the checklist
        # floor (interview.floor) holds it to; an unreachable host cannot be checked
        self.touched: set[str] = set()

    # --- entry points ------------------------------------------------------------------
    def dispatch(self, name: str, args: dict) -> str:
        fn = getattr(self, name, None)
        try:
            out = fn(**args) if fn else f"error: unknown tool {name}"
        except TypeError as e:
            out = f"error: bad arguments for {name}: {e}"
        self.calls.append({"tool": name, "args": args, "chars": len(out)})
        return out

    REFUSED = (
        "python3 -c",
        "python -c",
        "python3 -",
        "bash -c",
        "sh -c",
        "<<",
        "$(",
        "`",
        "/dev/tcp",
        "/dev/udp",
        "eval ",
        "exec ",
        "xargs",
        "timeout ",
        "watch ",
    )
    _SINGLETON = {"df", "free", "ss", "netstat", "uptime", "lsblk", "mount", "last"}
    _LOOP = re.compile(r"(?:^|[;&|]\s*)(?:for|while|until|if|case|function)\s")

    def run_command(self, host: str, command: str) -> str:
        h = self._host(host)
        if h is None:
            return f"ssh: Could not resolve hostname {host}: Name or service not known"
        self.touched.add(host)
        if any(k in command for k in self.REFUSED) or self._LOOP.search(command):
            return (
                "error: this read-only session runs simple commands only — no scripts, loops, "
                "subshells, heredocs, network probes or timeouts. Pipes into head/tail/grep/wc/sort "
                "and `;` chains are fine."
            )
        outs = []
        for seg in _split(_tokens(command), (";", "&&", "||", "&")):
            stages = _split(seg, ("|",))
            out = self._simple(host, h, _strip_redirects(stages[0]))
            for st in stages[1:]:
                out = self._filter(_strip_redirects(st), out)
            if out:
                outs.append(out)
        return "\n".join(outs)

    def read_file(self, host: str, path: str) -> str:
        h = self._host(host)
        if h is None:
            return f"ssh: Could not resolve hostname {host}: Name or service not known"
        self.touched.add(host)
        return self._cat(host, h, path)

    def manifest_lookup(self, service: str) -> str:
        m = self.w.get("manifest", {})

        def fmt(s, v):
            return f"{s}: host={v['host']} port={v['port']}" + (
                f" note={v['note']}" if v.get("note") else ""
            )

        if service in ("all", "*", ""):
            return "\n".join(fmt(s, v) for s, v in m.items()) or "(empty manifest)"
        v = m.get(service) or m.get(_unit(service))
        if not v:
            by_host = [fmt(s, v) for s, v in m.items() if v["host"] == service]
            if by_host:
                return "\n".join(by_host)
            return f"no manifest entry for '{service}'"
        return fmt(_unit(service), v)

    def korg_search(self, query: str) -> str:
        terms = [t for t in re.split(r"\W+", query.lower()) if len(t) >= 3]
        hits = [
            wi
            for wi in self.w.get("korg", [])
            if any(t in (wi["title"] + " " + wi.get("body", "")).lower() for t in terms)
        ]
        if not hits:
            return "no open work items match"
        return "\n\n".join(
            f"#{wi['number']} [{wi.get('status', 'open')}] {wi['title']}\n{wi.get('body', '')}"
            for wi in hits
        )

    # --- the shell -----------------------------------------------------------------------
    def _host(self, host: str) -> dict | None:
        return self.w.get("hosts", {}).get(host)

    def _match(self, h: dict, tokens: list[str]) -> str | None:
        """Longest fixture key whose tokens appear, in order, in the command's tokens."""
        norm = [_unit(_path(t)) for t in tokens]
        best, best_len = None, 0
        for key, val in h.get("commands", {}).items():
            kt = [_unit(t) for t in key.split()]
            i = 0
            for t in norm:
                if i < len(kt) and t == kt[i]:
                    i += 1
            if i == len(kt) and len(kt) > best_len:
                best, best_len = val, len(kt)
        return best

    def _binaries(self, h: dict) -> set[str]:
        """Binaries that exist on this host: coreutils, docker/python/uv, every service the
        host runs, and the first word of every fixture command key (if `certbot certificates`
        is a fixture answer, certbot is installed)."""
        out = set(COREUTILS) | {"docker", "python3", "uv", "bash", "sh"}
        out |= {_unit(u) for u in self._services(h)}
        out |= {k.split()[0] for k in h.get("commands", {}) if k.split()}
        return out

    def _services(self, h: dict) -> dict[str, str]:
        """unit -> 'active' | 'failed' | 'inactive', from the fixture's systemctl status entries."""
        out = {}
        for key, val in h.get("commands", {}).items():
            m = re.match(r"systemctl (?:--user )?status (\S+)$", key)
            if not m:
                continue
            state = (
                "active"
                if "Active: active" in val
                else ("failed" if "Active: failed" in val else "inactive")
            )
            out[m.group(1)] = state
        return out

    def _simple(self, host: str, h: dict, tokens: list[str]) -> str:
        if not tokens:
            return ""
        fixture = self._match(h, tokens)
        first, args = tokens[0], tokens[1:]
        if fixture is not None:
            if first in ("journalctl", "sudo") and "journalctl" in tokens[:2]:
                return self._journal_flags(args, fixture)
            return fixture
        if first in self._SINGLETON:
            # one filesystem, one memory, one socket table: flags do not change the answer
            for key, val in h.get("commands", {}).items():
                if key.split() and key.split()[0] == first:
                    return val
        base = first.rsplit("/", 1)[-1]
        if first.startswith("/") and base in COREUTILS:
            first = base
        if first == "sudo":
            return self._simple(host, h, args)
        if first == "crontab":
            return f"no crontab for {USER}"
        if first in ("date",):
            return h.get("commands", {}).get("date", "Mon Sep  7 03:00:04 UTC 2026")
        if first == "uptime":
            return (
                " 03:00:04 up 41 days,  6:12,  1 user,  load average: 0.31, 0.28, 0.24"
            )
        if first == "hostname":
            return host if "-f" not in args else f"{host}.lan"
        if first == "whoami":
            return USER
        if first == "id":
            return f"uid=1000({USER}) gid=1000({USER}) groups=1000({USER}),27(sudo),999(docker)"
        if first == "pwd":
            return f"/home/{USER}"
        if first == "uname":
            return (
                f"Linux {host} {KERNEL} #139-Ubuntu SMP x86_64 GNU/Linux"
                if args
                else "Linux"
            )
        if first in ("echo", "printf"):
            return self._echo(host, args)
        if first in ("true", "test", "[", "sleep"):
            return ""
        if first in ("which", "type", "command"):
            names = [a for a in args if not a.startswith("-")]
            known = self._binaries(h)
            system = COREUTILS | {"docker", "python3", "uv", "bash", "sh"}
            return "\n".join(
                f"/usr/bin/{n}" if n in system else f"/usr/local/bin/{n}"
                for n in names
                if n in system or n in known
            )
        if first == "env":
            return f"HOME=/home/{USER}\nUSER={USER}\nSHELL=/bin/bash\nPATH=/usr/local/bin:/usr/bin:/bin\nHOSTNAME={host}"
        if first in ("cat", "head", "tail", "less", "more"):
            files = [a for a in args if not a.startswith("-") and not a.isdigit()]
            if not files:
                return ""
            out = "\n".join(self._cat(host, h, f) for f in files)
            if first in ("head", "tail"):
                out = self._filter(
                    [first, *[a for a in args if a.startswith("-") or a.isdigit()]], out
                )
            return out
        if first == "ls":
            return self._ls(h, host, args)
        if first == "stat":
            sizes = self._listed_sizes(h)
            files = h.get("files", {})
            outs = []
            for f in [a for a in args if not a.startswith("-")]:
                f = _path(f)
                if self._isdir(h, f):
                    outs.append(
                        f"  File: {f}\n  Size: 4096\tBlocks: 8\tIO Block: 4096\tdirectory"
                    )
                elif f in sizes or f in files or f in self._implied_files(h):
                    n = sizes.get(f, len(files.get(f, "")) or 2048)
                    outs.append(
                        f"  File: {f}\n  Size: {n}\tBlocks: {(n + 511) // 512}\tIO Block: 4096\tregular file\n"
                        "Modify: 2026-09-07 02:14:41.000000000 +0000"
                    )
                else:
                    outs.append(f"stat: cannot statx '{f}': No such file or directory")
            return "\n".join(outs)
        if first == "find":
            unsupported = [
                a
                for a in args
                if a
                in (
                    "-size",
                    "-mtime",
                    "-mmin",
                    "-newer",
                    "-name",
                    "-iname",
                    "-exec",
                    "-user",
                    "-perm",
                    "-regex",
                )
            ]
            if unsupported:
                return f"find: predicate {unsupported[0]} is not supported in this session; supported: find <dir> [-maxdepth N] [-type f|d]"
            roots = [a for a in args if a.startswith("/")]
            tree = self._tree(h)
            want_files = "-type" in args and args[
                args.index("-type") + 1 : args.index("-type") + 2
            ] == ["f"]
            outs = []
            for root in roots:
                root = _path(root)
                if root not in tree and root not in GENERIC_DIRS:
                    outs.append(f"find: '{root}': No such file or directory")
                    continue
                kids = sorted(set(GENERIC_DIRS.get(root, [])) | tree.get(root, set()))
                if not want_files:
                    outs.append(root)
                for k in kids:
                    full = f"{root.rstrip('/')}/{k}"
                    if want_files and (full in tree or full in GENERIC_DIRS):
                        continue
                    outs.append(full)
            return "\n".join(outs)
        if first == "grep":
            flags = [a for a in args if a.startswith("-")]
            rest = [a for a in args if not a.startswith("-")]
            if len(rest) >= 2:
                text = "\n".join(self._cat(host, h, f) for f in rest[1:])
                return self._filter(["grep", *flags, rest[0]], text)
            return ""
        if first == "df":
            return "Filesystem      Size  Used Avail Use% Mounted on\n/dev/mapper/vg-root  916G  330G  540G  38% /"
        if first == "du":
            return self._du(h, args)
        if first == "free":
            return (
                "               total        used        free      shared  buff/cache   available\n"
                "Mem:           64211       18402       21055         412       24754       44902\nSwap:           8191           0        8191"
            )
        if first == "ps":
            return self._ps(h, host)
        if first in ("ss", "netstat"):
            fx = h.get("commands", {}).get("ss -tlnp")
            if fx:
                return fx
            return 'State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process\nLISTEN 0      128    0.0.0.0:22           0.0.0.0:*     users:(("sshd",pid=1201,fd=3))'
        if first == "ip":
            return f"2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP\n    inet 192.168.1.{sum(map(ord, host)) % 200 + 20}/24 scope global eno1"
        if first in ("dmesg",):
            return h.get("commands", {}).get("journalctl -k", "")
        if first == "lsblk":
            return "NAME        SIZE TYPE MOUNTPOINTS\nnvme0n1     1.8T disk\n└─vg-root   1.8T lvm  /"
        if first == "mount":
            return (
                "/dev/mapper/vg-root on / type ext4 (rw,relatime)\n"
                "tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev)\n"
                "tmpfs on /run type tmpfs (rw,nosuid,nodev,size=6421504k)"
            )
        if first in ("last", "who", "w"):
            return f"{USER}     pts/0        100.64.0.7       Mon Sep  7 02:58   still logged in"
        if first == "systemctl":
            return self._systemctl(h, args)
        if first == "journalctl":
            return self._journalctl(h, args, host)
        if first == "docker":
            if any(k.startswith("docker") for k in h.get("commands", {})):
                return (
                    ""
                    if args
                    and args[0]
                    in ("ps", "images", "inspect", "logs", "stats", "version", "info")
                    else f"docker: unknown command: docker {' '.join(args)}"
                )
            return "bash: docker: command not found"
        if first not in self._binaries(h) and first in (
            "smartctl",
            "nvidia-smi",
            "ethtool",
            "certbot",
            "psql",
            "pg_lsclusters",
            "restic",
            "curl",
            "wget",
            "nc",
            "nmap",
            "tcpdump",
            "strace",
            "htop",
            "top",
            "iotop",
            "vmstat",
            "iostat",
            "sar",
            "dig",
            "nslookup",
            "ping",
            "traceroute",
            "openssl",
        ):
            return f"bash: {first}: command not found"
        if first in ("cd", "export", "set", "unset", "alias", "source", "."):
            return ""
        if first in self._binaries(h):
            keyed = sorted(
                k for k in h.get("commands", {}) if k.split() and k.split()[0] == first
            )
            if keyed:
                return (
                    f"{first}: unsupported invocation in this session. Supported here: "
                    + " | ".join(keyed)
                )
            return f"{first}: no output"
        return f"bash: {first}: command not found"

    # --- helpers ---------------------------------------------------------------------------
    def _echo(self, host: str, args: list[str]) -> str:
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": f"/home/{USER}",
            "SHELL": "/bin/bash",
            "USER": USER,
            "HOSTNAME": host,
            "PWD": f"/home/{USER}",
            "0": "bash",
            "?": "0",
        }
        out = " ".join(a for a in args if a not in ("-n", "-e", "-E", "-en", "-ne"))
        out = re.sub(r"\$\{?(\w+|\?|0)\}?", lambda m: env.get(m.group(1), ""), out)
        return out.replace("\\n", "\n").rstrip("\n")

    def _tree(self, h: dict) -> dict[str, set[str]]:
        """dir -> children, from everything the fixture implies exists: files and their
        parents, paths named by `ls`/`du` fixture keys, explicit `dirs`, the host's unit
        files under /etc/systemd/system and its binaries under /usr/local/bin."""
        tree: dict[str, set[str]] = {}

        def add(path: str, is_dir: bool) -> None:
            parts = path.strip("/").split("/")
            for i in range(1, len(parts) + 1):
                parent = "/" + "/".join(parts[: i - 1]) if i > 1 else "/"
                tree.setdefault(parent, set()).add(parts[i - 1])
            if is_dir:
                tree.setdefault(path, set())

        for f in h.get("files", {}):
            add(f, False)
        for d, kids in h.get("dirs", {}).items():
            add(d, True)
            tree[d] |= set(kids)
        for key, val in h.get("commands", {}).items():
            kt = key.split()
            if (
                kt
                and kt[0] in ("ls", "du", "tree")
                and len(kt) >= 2
                and kt[-1].startswith("/")
            ):
                base = _path(kt[-1])
                add(base, True)
                if kt[0] == "ls":
                    for name, is_dir in self._listed(val):
                        add(f"{base}/{name}", is_dir)
        for f in self._implied_files(h):
            add(f, False)
        if any(k.startswith("docker") for k in h.get("commands", {})):
            for d in (
                "overlay2",
                "containers",
                "image",
                "volumes",
                "network",
                "buildkit",
            ):
                add(f"/var/lib/docker/{d}", True)
        return tree

    @staticmethod
    def _listed(listing: str) -> list[tuple[str, bool]]:
        """Names in an `ls`/`ls -la` fixture output, with whether each is a directory."""
        out = []
        for ln in listing.splitlines():
            ln = ln.rstrip()
            if not ln or ln.startswith("total "):
                continue
            parts = ln.split()
            if len(parts) >= 9 and parts[0][0] in "-dl" and len(parts[0]) == 10:
                out.append((parts[-1], parts[0][0] == "d"))
            elif len(parts) == 1 and not ln.startswith("ls:"):
                out.append((parts[0], "." not in parts[0]))
        return out

    def _listed_sizes(self, h: dict) -> dict[str, int]:
        """path -> size in bytes for files an `ls -l` fixture output describes."""
        out: dict[str, int] = {}
        for key, val in h.get("commands", {}).items():
            kt = key.split()
            if kt and kt[0] == "ls" and len(kt) >= 2 and kt[-1].startswith("/"):
                base = _path(kt[-1])
                for ln in val.splitlines():
                    parts = ln.split()
                    if (
                        len(parts) >= 9
                        and parts[0].startswith("-")
                        and parts[4].isdigit()
                    ):
                        out[f"{base}/{parts[-1]}"] = int(parts[4])
        return out

    def _implied_files(self, h: dict) -> set[str]:
        out = set(self._listed_sizes(h))
        for unit in self._services(h):
            out.add(f"/opt/{_unit(unit)}/{_unit(unit)}")  # what the wrapper execs
        for unit in self._services(h):
            name = unit if "." in unit else unit + ".service"
            out.add(f"/etc/systemd/system/{name}")
            out.add(f"/usr/local/bin/{_unit(unit)}")
        return out

    def _isdir(self, h: dict, path: str) -> bool:
        p = _path(path)
        return p in GENERIC_DIRS or p in self._tree(h)

    def _ls(self, h: dict, host: str, args: list[str]) -> str:
        flags = [a for a in args if a.startswith("-")]
        paths = [a for a in args if not a.startswith("-")] or [f"/home/{USER}"]
        long = any("l" in f for f in flags)
        files = h.get("files", {})
        tree = self._tree(h)
        implied = self._implied_files(h)
        outs = []
        for p in paths:
            p = _path(p)
            if p in files:
                outs.append(
                    f"-rw-r--r-- 1 root root {len(files[p]):>7} Sep  7 02:00 {p}"
                    if long
                    else p
                )
                continue
            if p not in GENERIC_DIRS and p not in tree:
                outs.append(f"ls: cannot access '{p}': No such file or directory")
                continue
            entries = sorted(set(GENERIC_DIRS.get(p, [])) | tree.get(p, set()))
            if long:
                rows = []
                for e in entries:
                    full = f"{p.rstrip('/')}/{e}"
                    if full in files:
                        rows.append(
                            f"-rw-r----- 1 root root {len(files[full]):>7} Sep  7 02:00 {e}"
                        )
                    elif full in implied:
                        n = self._listed_sizes(h).get(full)
                        rows.append(
                            f"-rw-r----- 1 root root {n:>10} Sep  7 02:14 {e}"
                            if n
                            else f"-rwxr-xr-x 1 root root    2048 Sep  7 02:00 {e}"
                        )
                    elif full in tree or full in GENERIC_DIRS or "." not in e:
                        rows.append(f"drwxr-xr-x 2 root root    4096 Sep  7 02:00 {e}")
                    else:
                        rows.append(f"-rw-r--r-- 1 root root     812 Sep  7 02:00 {e}")
                outs.append(f"total {len(entries) * 4}\n" + "\n".join(rows))
            else:
                outs.append("\n".join(entries))
        return "\n".join(outs)

    def _cat(self, host: str, h: dict, path: str) -> str:
        files = h.get("files", {})
        path = _path(path)
        if path in files:
            return files[path]
        svcs = self._services(h)
        m = re.match(r"/etc/systemd/system/([^/]+)\.timer$", path)
        if m and m.group(1) + ".timer" in svcs:
            u = m.group(1)
            return (
                f"[Unit]\nDescription={u} (timer)\n\n[Timer]\nOnCalendar=*-*-* 02:10:00\nPersistent=true\n"
                f"Unit={u}.service\n\n[Install]\nWantedBy=timers.target"
            )
        m = re.match(r"/etc/systemd/system/([^/]+?)(?:\.service)?$", path)
        if m and (m.group(1) in svcs or m.group(1) + ".service" in svcs):
            u = m.group(1)
            return (
                f"[Unit]\nDescription={u}\nAfter=network-online.target\n\n[Service]\nType=simple\n"
                f"ExecStart=/usr/local/bin/{u}\nRestart=on-failure\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target"
            )
        m = re.match(r"/usr/local/bin/([^/]+)$", path)
        if m and any(_unit(u) == m.group(1) for u in svcs):
            return f'#!/bin/sh\n# managed by k-homelab\nexec /opt/{m.group(1)}/{m.group(1)} "$@"'
        if path == "/var/log/auth.log":
            return self._auth_log(h, host)
        if path == "/var/log/syslog":
            return self._journalctl(h, ["-n", "200"], host)
        if path == "/var/log/kern.log":
            return h.get("commands", {}).get("journalctl -k", "")
        generic = {
            "/etc/hostname": host,
            "/etc/os-release": 'PRETTY_NAME="Ubuntu 24.04.3 LTS"\nNAME="Ubuntu"\nVERSION_ID="24.04"',
            "/proc/loadavg": "0.31 0.28 0.24 1/612 48213",
            "/proc/uptime": "3564720.18 27918211.44",
            "/proc/meminfo": "MemTotal:       65752064 kB\nMemFree:        21560320 kB\nMemAvailable:   45980160 kB",
            "/etc/hosts": "127.0.0.1 localhost\n127.0.1.1 " + host,
            "/etc/fstab": "/dev/mapper/vg-root / ext4 defaults 0 1",
            "/proc/mounts": "/dev/mapper/vg-root / ext4 rw,relatime 0 0\ntmpfs /dev/shm tmpfs rw,nosuid,nodev 0 0\ntmpfs /run tmpfs rw,nosuid,nodev 0 0",
        }
        if path in generic:
            return generic[path]
        if self._isdir(h, path):
            return f"cat: {path}: Is a directory"
        sizes = self._listed_sizes(h)
        if path in sizes:
            return f"(binary data, {sizes[path]} bytes)"
        if path.startswith("/opt/") and path in self._implied_files(h):
            return "(binary data, 18432112 bytes)"
        return f"cat: {path}: No such file or directory"

    _AUTH_KEYS = ("journalctl -u sshd", "journalctl -u ssh", "journalctl -u sudo")

    def _auth_journal(self, h: dict) -> str | None:
        """The host's sshd journal fixture, whichever unit name it was keyed under."""
        for key, val in h.get("commands", {}).items():
            if key.startswith(self._AUTH_KEYS):
                return val
        return None

    def _auth_log(self, h: dict, host: str) -> str:
        """/var/log/auth.log: the sshd/sudo lines. A host with no auth fixture shows the same
        quiet picture `last`/`who` show — ken's own session — so the file, the journal and
        the login table never disagree."""
        fx = self._auth_journal(h)
        if fx is not None:
            return fx
        seen = set()
        lines = []
        for key, val in h.get("commands", {}).items():
            if key.startswith("journalctl"):
                for ln in val.splitlines():
                    if re.search(r"\b(sshd|sudo)\[\d+\]", ln) and ln not in seen:
                        seen.add(ln)
                        lines.append(ln)
        lines += [
            f"Sep 07 02:58:01 {host} sshd[1201]: Accepted publickey for {USER} from 100.64.0.7 port 50122 ssh2: ED25519",
            f"Sep 07 02:58:01 {host} sshd[1201]: pam_unix(sshd:session): session opened for user {USER}(uid=1000) by (uid=0)",
        ]
        return "\n".join(sorted(lines))

    _SIZES = {"K": 1, "M": 1024, "G": 1024**2, "T": 1024**3}

    def _du(self, h: dict, args: list[str]) -> str:
        """`du` answers from the fixture's own `du` keys, propagated upward: if the fixture
        says /var/lib/docker is 1.3T then /var/lib and / are at least that — the world must
        never contradict itself. Unknown paths that the tree knows are small; others fail."""
        sized: dict[str, float] = {}
        for key, val in h.get("commands", {}).items():
            kt = key.split()
            if kt and kt[0] == "du" and len(kt) >= 2 and kt[-1].startswith("/"):
                m = re.match(r"([\d.]+)([KMGT])", val.strip())
                if m:
                    sized[_path(kt[-1])] = float(m.group(1)) * self._SIZES[m.group(2)]

        def size_of(path: str) -> float | None:
            path = _path(path)
            if path in sized:
                return sized[path]
            under = [
                v
                for k, v in sized.items()
                if path == "/" or k.startswith(path.rstrip("/") + "/")
            ]
            if under:
                return sum(under) + 4
            if (
                path in GENERIC_DIRS
                or path in self._tree(h)
                or path in h.get("files", {})
            ):
                return 4.0
            return None

        def fmt(kib: float) -> str:
            for unit, div in (("T", 1024**3), ("G", 1024**2), ("M", 1024)):
                if kib >= div:
                    return f"{kib / div:.1f}{unit}"
            return f"{kib:.1f}K"

        flags = [a for a in args if a.startswith("-")]
        paths = [a for a in args if not a.startswith("-")] or ["."]
        depth = next(
            (int(f.split("=")[1]) for f in flags if f.startswith("--max-depth=")), None
        )
        if "-d" in flags:
            k = args.index("-d")
            if k + 1 < len(args) and args[k + 1].isdigit():
                depth = int(args[k + 1])
                paths = [a for a in paths if a != args[k + 1]]
        out = []
        for pth in paths:
            if pth.endswith("/*"):
                base = _path(pth[:-2])
                kids = sorted(
                    set(GENERIC_DIRS.get(base, [])) | self._tree(h).get(base, set())
                )
                for kid in kids:
                    sz = size_of(f"{base.rstrip('/')}/{kid}")
                    out.append(
                        f"{fmt(sz)}\t{base.rstrip('/')}/{kid}"
                        if sz is not None
                        else f"du: cannot access '{base}/{kid}': No such file or directory"
                    )
                continue
            sz = size_of(pth)
            if sz is None:
                out.append(f"du: cannot access '{pth}': No such file or directory")
                continue
            if depth:
                base = _path(pth)
                kids = sorted(
                    set(GENERIC_DIRS.get(base, [])) | self._tree(h).get(base, set())
                )
                for kid in kids:
                    ksz = size_of(f"{base.rstrip('/')}/{kid}")
                    if ksz is not None:
                        out.append(f"{fmt(ksz)}\t{base.rstrip('/')}/{kid}")
            out.append(f"{fmt(sz)}\t{pth}")
        return "\n".join(out)

    def _ps(self, h: dict, host: str) -> str:
        lines = [
            "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND",
            "root           1  0.0  0.1  22528 13112 ?        Ss   Jul28   4:12 /sbin/init",
            "root        1201  0.0  0.0  15420  9012 ?        Ss   Jul28   0:03 sshd: /usr/sbin/sshd -D",
        ]
        pid = 1180
        for unit, state in self._services(h).items():
            pid += 17
            if state == "active":
                lines.append(
                    f"{USER if unit.startswith('kvllm') else 'root':<10} {pid:>6}  0.4  1.2 812344 96012 ?        Ssl  Jul28  61:04 /usr/local/bin/{_unit(unit)}"
                )
        return "\n".join(lines)

    def _systemctl(self, h: dict, args: list[str]) -> str:
        a = [
            x
            for x in args
            if x
            not in (
                "--no-pager",
                "--user",
                "--plain",
                "--all",
                "-a",
                "--full",
                "-l",
                "--no-legend",
            )
        ]
        svcs = self._services(h)
        if not a or a[0] == "status" and len(a) == 1:
            return f"● host\n    State: {'degraded' if 'failed' in svcs.values() else 'running'}\n    Units: {len(svcs) + 40} loaded\n    Failed: {sum(s == 'failed' for s in svcs.values())} units"
        cmd = a[0]
        if cmd == "status":
            unit = a[-1]
            return (
                f"Unit {unit if '.' in unit else unit + '.service'} could not be found."
            )
        if cmd in ("is-active", "is-failed", "is-enabled"):
            unit = _unit(a[-1])
            st = svcs.get(unit) or svcs.get(a[-1])
            if cmd == "is-enabled":
                return (
                    "enabled"
                    if st
                    else f"Failed to get unit file state for {a[-1]}: No such file or directory"
                )
            if cmd == "is-failed":
                return (
                    "failed"
                    if st == "failed"
                    else "active"
                    if st == "active"
                    else "inactive"
                )
            return st or "inactive"
        if cmd in ("list-units", "--failed", "list-timers"):
            failed_only = cmd == "--failed" or "--failed" in a or "--state=failed" in a
            rows = []
            for unit, st in svcs.items():
                if failed_only and st != "failed":
                    continue
                if cmd == "list-timers" and not unit.endswith(".timer"):
                    continue
                name = unit if "." in unit else unit + ".service"
                rows.append(
                    f"  {name:<32} loaded {st:<8} {'running' if st == 'active' else 'failed' if st == 'failed' else 'dead':<8} {_unit(unit)}"
                )
            if not failed_only and cmd != "list-timers":
                rows += [
                    "  ssh.service                      loaded active   running  OpenBSD Secure Shell server",
                    "  cron.service                     loaded active   running  Regular background program processing daemon",
                ]
            head = "  UNIT                             LOAD   ACTIVE   SUB      DESCRIPTION"
            return (
                head + "\n" + "\n".join(rows) + f"\n\n{len(rows)} loaded units listed."
                if rows
                else ("0 loaded units listed." if failed_only else head)
            )
        if cmd in ("cat", "show"):
            unit = _unit(a[-1])
            if unit.endswith(".timer") and unit in svcs:
                return f"# /etc/systemd/system/{unit}\n" + self._cat(
                    "", h, f"/etc/systemd/system/{unit}"
                )
            return (
                f"# /etc/systemd/system/{unit}.service\n[Service]\nExecStart=/usr/local/bin/{unit}\nRestart=on-failure"
                if unit in svcs
                else f"No files found for {a[-1]}."
            )
        if cmd in (
            "start",
            "stop",
            "restart",
            "reload",
            "enable",
            "disable",
            "daemon-reload",
        ):
            return f"Failed to {cmd} {a[-1] if len(a) > 1 else ''}: Access denied (read-only session)"
        return f"Unknown command verb {cmd}."

    _PRIORITY = re.compile(
        r"\b(WARN|WARNING|ERR|ERROR|FATAL|PANIC|CRIT|CRITICAL|Failed|failed|error|Killed|denied|refused)\b",
        re.I,
    )

    def _journal_flags(self, args: list[str], text: str) -> str:
        """`-p`/`--priority` keeps only lines a real journald would rate warning or worse;
        `-n N` keeps the last N. Applied to fixture answers too, so a keyed journal never
        contradicts its own flags."""
        lines = text.splitlines()
        if "-p" in args or any(a.startswith("--priority") for a in args):
            lines = [ln for ln in lines if self._PRIORITY.search(ln)]
        n = None
        if (
            "-n" in args
            and args.index("-n") + 1 < len(args)
            and args[args.index("-n") + 1].isdigit()
        ):
            n = int(args[args.index("-n") + 1])
        for a in args:
            if a.startswith("--lines="):
                n = int(a.split("=", 1)[1]) if a.split("=", 1)[1].isdigit() else n
        if n is not None:
            lines = lines[-n:]
        return "\n".join(lines) or "-- No entries --"

    def _journalctl(self, h: dict, args: list[str], host: str = "") -> str:
        if "-k" in args or "--dmesg" in args:
            return h.get("commands", {}).get("journalctl -k", "-- No entries --")
        unit = None
        for i, a in enumerate(args):
            if a in ("-u", "--unit", "-t", "--identifier") and i + 1 < len(args):
                unit = args[i + 1]
            elif a.startswith(
                ("--unit=", "--identifier=", "_COMM=", "SYSLOG_IDENTIFIER=")
            ):
                unit = a.split("=", 1)[1]
        if unit is not None:
            if _unit(unit) in ("ssh", "sshd", "sudo"):
                return self._journal_flags(args, self._auth_log(h, host))
            return "-- No entries --"
        merged = []
        for key, val in h.get("commands", {}).items():
            # the whole journal includes the kernel ring: `journalctl --since …` on a real
            # host shows `NIC Link is Down` alongside the units' lines
            if key.startswith("journalctl") and val != "-- No entries --":
                merged.append(val)
        if not merged:
            return "-- No entries --"
        lines = sorted({ln for block in merged for ln in block.splitlines()})
        n = 50
        if (
            "-n" in args
            and args.index("-n") + 1 < len(args)
            and args[args.index("-n") + 1].isdigit()
        ):
            n = int(args[args.index("-n") + 1])
        if "-p" in args or any(a.startswith("--priority") for a in args):
            lines = [ln for ln in lines if self._PRIORITY.search(ln)]
        return "\n".join(lines[-n:]) or "-- No entries --"

    def _filter(self, st: list[str], text: str) -> str:
        if not st:
            return text
        cmd, args = st[0], st[1:]
        lines = text.splitlines()
        if cmd == "head":
            n = 10
            for i, a in enumerate(args):
                if (
                    a == "-n"
                    and i + 1 < len(args)
                    and args[i + 1].lstrip("-").isdigit()
                ):
                    n = int(args[i + 1])
                elif re.fullmatch(r"-\d+", a):
                    n = int(a[1:])
            return "\n".join(lines[:n])
        if cmd == "tail":
            n = 10
            for i, a in enumerate(args):
                if (
                    a == "-n"
                    and i + 1 < len(args)
                    and args[i + 1].lstrip("-").isdigit()
                ):
                    n = int(args[i + 1])
                elif re.fullmatch(r"-\d+", a):
                    n = int(a[1:])
            return "\n".join(lines[-n:])
        if cmd in ("grep", "egrep"):
            flags = [a for a in args if a.startswith("-")]
            pats = [a for a in args if not a.startswith("-")]
            if not pats:
                return text
            pat = pats[0]
            letters = set("".join(f[1:] for f in flags if not f.startswith("--")))
            ci = "i" in letters or "--ignore-case" in flags
            inv = "v" in letters or "--invert-match" in flags
            ere = cmd == "egrep" or "E" in letters or "--extended-regexp" in flags
            fixed_flag = "F" in letters or "--fixed-strings" in flags
            # basic-regex alternation/grouping, as in `grep -i "disk\|spac"`, is a regex
            bre_meta = any(m in pat for m in ("\\|", "\\(", "\\)", "\\{"))
            if bre_meta and not fixed_flag:
                for a_, b_ in (
                    ("\\|", "|"),
                    ("\\(", "("),
                    ("\\)", ")"),
                    ("\\{", "{"),
                    ("\\}", "}"),
                ):
                    pat = pat.replace(a_, b_)
            fixed = fixed_flag or not (ere or bre_meta)
            try:
                rx = re.compile(re.escape(pat) if fixed else pat, re.I if ci else 0)
            except re.error:
                rx = re.compile(re.escape(pat), re.I if ci else 0)
            keep = [ln for ln in lines if bool(rx.search(ln)) != inv]
            if "c" in letters or "--count" in flags:
                return str(len(keep))
            return "\n".join(keep)
        if cmd == "wc":
            return str(len(lines)) if "-l" in args or not args else str(len(text))
        if cmd == "sort":
            return "\n".join(sorted(lines, reverse="-r" in args))
        if cmd == "uniq":
            out = []
            for ln in lines:
                if not out or out[-1] != ln:
                    out.append(ln)
            return "\n".join(out)
        return text  # cut/awk/sed/tr/column/xargs: pass through

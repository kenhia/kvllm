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
    "/usr/local/bin": [],
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


class World:
    """Answers tool calls from the scenario's fixture, generically where the fixture is silent."""

    def __init__(self, w: dict):
        self.w = w
        self.calls: list[dict] = []

    # --- entry points ------------------------------------------------------------------
    def dispatch(self, name: str, args: dict) -> str:
        fn = getattr(self, name, None)
        try:
            out = fn(**args) if fn else f"error: unknown tool {name}"
        except TypeError as e:
            out = f"error: bad arguments for {name}: {e}"
        self.calls.append({"tool": name, "args": args, "chars": len(out)})
        return out

    def run_command(self, host: str, command: str) -> str:
        h = self._host(host)
        if h is None:
            return f"ssh: Could not resolve hostname {host}: Name or service not known"
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
        terms = [t for t in re.split(r"\W+", query.lower()) if t]
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
        norm = [_unit(t) for t in tokens]
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
        if fixture is not None:
            return fixture
        first, args = tokens[0], tokens[1:]
        base = first.rsplit("/", 1)[-1]
        if first.startswith("/") and base in COREUTILS:
            first = base
        if first == "sudo":
            return self._simple(host, h, args)
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
            return "\n".join(
                f"/usr/bin/{n}"
                for n in names
                if n in COREUTILS or n in ("docker", "python3", "uv")
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
            files = [a for a in args if not a.startswith("-")]
            return "\n".join(
                f"  File: {f}\n  Size: 4096\tBlocks: 8\tIO Block: 4096\tdirectory"
                if self._isdir(h, f)
                else f"stat: cannot statx '{f}': No such file or directory"
                for f in files
            )
        if first == "find":
            return ""
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
            return (
                "\n".join(f"4.0K\t{a}" for a in args if not a.startswith("-"))
                or "4.0K\t."
            )
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
            return self._journalctl(h, args)
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
        if first in (
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

    def _isdir(self, h: dict, path: str) -> bool:
        p = path.rstrip("/") or "/"
        if p in GENERIC_DIRS or p in h.get("dirs", {}):
            return True
        return any(f.startswith(p + "/") for f in h.get("files", {})) or any(
            k == f"ls {p}" or k == f"ls -la {p}" for k in h.get("commands", {})
        )

    def _ls(self, h: dict, host: str, args: list[str]) -> str:
        flags = [a for a in args if a.startswith("-")]
        paths = [a for a in args if not a.startswith("-")] or [f"/home/{USER}"]
        long = any("l" in f for f in flags)
        outs = []
        for p in paths:
            p = p.rstrip("/") or "/"
            files = h.get("files", {})
            if p in files:
                outs.append(
                    f"-rw-r--r-- 1 root root {len(files[p]):>7} Sep  7 02:00 {p}"
                    if long
                    else p
                )
                continue
            entries = list(h.get("dirs", {}).get(p, [])) or list(
                GENERIC_DIRS.get(p, [])
            )
            entries += [
                f[len(p) + 1 :].split("/")[0] for f in files if f.startswith(p + "/")
            ]
            if not entries and p not in GENERIC_DIRS and p not in h.get("dirs", {}):
                outs.append(f"ls: cannot access '{p}': No such file or directory")
                continue
            entries = sorted(set(entries))
            if long:
                outs.append(
                    f"total {len(entries) * 4}\n"
                    + "\n".join(
                        (
                            f"drwxr-xr-x 2 root root 4096 Sep  7 02:00 {e}"
                            if "." not in e
                            else f"-rw-r--r-- 1 root root  812 Sep  7 02:00 {e}"
                        )
                        for e in entries
                    )
                )
            else:
                outs.append("\n".join(entries))
        return "\n".join(outs)

    def _cat(self, host: str, h: dict, path: str) -> str:
        files = h.get("files", {})
        if path in files:
            return files[path]
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
        return f"cat: {path}: No such file or directory"

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

    def _journalctl(self, h: dict, args: list[str]) -> str:
        if "-k" in args or "--dmesg" in args:
            return h.get("commands", {}).get("journalctl -k", "-- No entries --")
        if "-u" in args or "--unit" in args:
            i = args.index("-u") if "-u" in args else args.index("--unit")
            if i + 1 < len(args):
                return "-- No entries --"
        merged = []
        for key, val in h.get("commands", {}).items():
            if key.startswith("journalctl") and key not in ("journalctl -k",):
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
            lines = [
                ln
                for ln in lines
                if re.search(
                    r"\b(WARN|ERROR|FATAL|PANIC|Failed|failed|error|Killed)\b", ln
                )
            ]
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
            ci = any("i" in f for f in flags)
            inv = any(f == "-v" for f in flags)
            fixed = any(f == "-F" for f in flags) or not (
                cmd == "egrep" or "-E" in flags
            )
            try:
                rx = re.compile(re.escape(pat) if fixed else pat, re.I if ci else 0)
            except re.error:
                rx = re.compile(re.escape(pat), re.I if ci else 0)
            keep = [ln for ln in lines if bool(rx.search(ln)) != inv]
            if "-c" in flags:
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

"""Homelab model registry: what has been pulled from Hugging Face, and where each copy lives.

`homelab-models.toml` (repo root) is the homelab's one list of downloaded weights. It covers
kvllm's own models and other consumers' (kodds, ACE-Step, the kubs0 embedding cache), so
a fetch can check it before going to Hugging Face. `models.toml` is a different file: it
says how kvllm *serves* a model. This one says where the bytes are kept.
Per-file sha256 manifests sit in `model-sums/`, one per entry, with paths relative to the
entry, so any copy can be checked where it lives (`verify`).

CLI:
    uv run python -m kvllm.modelstore list
    uv run python -m kvllm.modelstore where <kvllm-key | hf-repo | id>
    uv run python -m kvllm.modelstore unpark <kvllm-key | hf-repo> [--hub DIR]
    uv run python -m kvllm.modelstore verify <id> [--at LOCATION]

The behaviour that matters is `ensure_weights`, which every serve path calls before vLLM
starts (`registry serve`, the systemd unit through it, `evalctl.serving`,
`interview.serve`). If the model's Hugging Face cache entry is missing from this host's hub
and the registry records a parked copy, it is restored with `rsync -aH` and verified
before vLLM sees it. A parked model is never re-downloaded without someone noticing.
There is no park command yet. Parking is rare, deliberate and done by hand (korg:3869).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import socket
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INVENTORY = REPO_ROOT / "homelab-models.toml"
SUMS_DIR = REPO_ROOT / "model-sums"
# Escape hatch for a restore that cannot happen (source host down): serve anyway and let
# vLLM download from Hugging Face. Explicit, so the download is a choice and not a default.
ALLOW_DOWNLOAD_ENV = "KVLLM_ALLOW_DOWNLOAD"

LAYOUTS = ("hf-cache", "dir")


@dataclass(frozen=True)
class Location:
    name: str
    host: str
    path: str
    layout: (
        str  # "hf-cache": entries are models--org--name dirs; "dir": plain files/dirs
    )

    def spec(self, entry_name: str, *, here: str) -> str:
        """rsync/ssh spelling of an entry at this location, as seen from host `here`."""
        p = f"{self.path.rstrip('/')}/{entry_name}"
        return p if self.host == here else f"{self.host}:{p}"


@dataclass(frozen=True)
class Model:
    id: str
    copies: tuple[str, ...]
    hf_repo: str | None = None
    entry: str | None = None  # name inside a "dir" location (hf-cache derives it)
    revision: str | None = None
    size_bytes: int | None = None
    downloaded: dt.date | None = None
    consumers: tuple[str, ...] = ()
    notes: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def entry_name(self) -> str:
        if self.entry:
            return self.entry
        assert self.hf_repo, self.id
        return hf_cache_dirname(self.hf_repo)

    @property
    def sums_path(self) -> Path:
        return SUMS_DIR / f"{self.entry_name}.sha256"


@dataclass(frozen=True)
class Inventory:
    locations: dict[str, Location]
    models: dict[str, Model]

    def lookup(self, ref: str, kvllm_registry: dict[str, dict] | None = None) -> Model:
        """Resolve an id, an HF repo, or a kvllm key (via its hf_repo or a consumer tag)."""
        if ref in self.models:
            return self.models[ref]
        for m in self.models.values():
            if m.hf_repo == ref or f"kvllm:{ref}" in m.consumers:
                return m
        if kvllm_registry and ref in kvllm_registry:
            repo = kvllm_registry[ref].get("hf_repo")
            for m in self.models.values():
                if repo and m.hf_repo == repo:
                    return m
        raise KeyError(ref)

    def by_repo(self, hf_repo: str) -> Model | None:
        return next((m for m in self.models.values() if m.hf_repo == hf_repo), None)


def hf_cache_dirname(hf_repo: str) -> str:
    """`org/name` → `models--org--name`, huggingface-hub's cache folder name."""
    return "models--" + hf_repo.replace("/", "--")


def local_hub(env: dict[str, str] | None = None) -> Path:
    """This host's HF hub cache dir, resolved the way huggingface-hub resolves it."""
    env = os.environ if env is None else env
    if env.get("HF_HUB_CACHE"):
        return Path(env["HF_HUB_CACHE"])
    if env.get("HF_HOME"):
        return Path(env["HF_HOME"]) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def this_host() -> str:
    return socket.gethostname().split(".")[0]


def load_inventory(path: Path | None = None) -> Inventory:
    path = path or DEFAULT_INVENTORY
    data = tomllib.loads(path.read_text())
    locations: dict[str, Location] = {}
    for name, loc in data.get("locations", {}).items():
        if loc.get("layout") not in LAYOUTS:
            raise ValueError(f"location '{name}': layout must be one of {LAYOUTS}")
        locations[name] = Location(name, loc["host"], loc["path"], loc["layout"])
    models: dict[str, Model] = {}
    known = {
        "copies", "hf_repo", "entry", "revision", "size_bytes",
        "downloaded", "consumers", "notes",
    }  # fmt: skip
    for mid, m in data.get("models", {}).items():
        copies = tuple(m.get("copies", ()))
        if not copies:
            raise ValueError(f"model '{mid}': no copies — where is it?")
        for c in copies:
            if c not in locations:
                raise ValueError(f"model '{mid}': unknown location '{c}'")
            if locations[c].layout == "dir" and not m.get("entry"):
                raise ValueError(f"model '{mid}': a copy in '{c}' needs `entry`")
        if not m.get("entry") and not m.get("hf_repo"):
            raise ValueError(f"model '{mid}': needs `hf_repo` or `entry`")
        models[mid] = Model(
            id=mid,
            copies=copies,
            hf_repo=m.get("hf_repo"),
            entry=m.get("entry"),
            revision=m.get("revision"),
            size_bytes=m.get("size_bytes"),
            downloaded=m.get("downloaded"),
            consumers=tuple(m.get("consumers", ())),
            notes=m.get("notes", ""),
            extra={k: v for k, v in m.items() if k not in known},
        )
    return Inventory(locations, models)


def present_in_hub(hub: Path, hf_repo: str) -> bool:
    """True when the hub holds a usable entry: a snapshot with at least one file."""
    snaps = hub / hf_cache_dirname(hf_repo) / "snapshots"
    return snaps.is_dir() and any(p.is_file() for p in snaps.rglob("*"))


def restore_source(inv: Inventory, model: Model, *, here: str) -> Location | None:
    """The parked copy to restore from: the first hf-cache copy listed, this host's first."""
    cands = [inv.locations[c] for c in model.copies]
    cands = [c for c in cands if c.layout == "hf-cache"]
    cands.sort(key=lambda c: c.host != here)  # stable: list order otherwise
    return cands[0] if cands else None


def verify_root(loc: Location, model: Model) -> str:
    """Where a manifest's relative paths start. An hf-cache manifest is relative to the
    `models--…` dir, so it checks a copy in any hub. A `dir` manifest is relative to the
    location, so its paths name the entry: a single file or a directory tree."""
    root = loc.path.rstrip("/")
    return f"{root}/{model.entry_name}" if loc.layout == "hf-cache" else root


def verify_local(model: Model, root: Path) -> list[str]:
    """`sha256sum -c` the manifest against a local copy; returns the failing lines."""
    sums = model.sums_path
    if not sums.is_file():
        return [f"no manifest {sums.relative_to(REPO_ROOT)}"]
    r = subprocess.run(
        ["sha256sum", "-c", "--quiet", str(sums)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        return []
    return (r.stdout + r.stderr).strip().splitlines() or [
        f"sha256sum rc={r.returncode}"
    ]


def verify_remote(model: Model, loc: Location) -> list[str]:
    """Same check run on the copy's own host, the manifest piped in over ssh."""
    sums = model.sums_path
    if not sums.is_file():
        return [f"no manifest {sums.relative_to(REPO_ROOT)}"]
    root = verify_root(loc, model)
    r = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            loc.host,
            f"cd '{root}' && sha256sum -c --quiet -",
        ],  # fmt: skip
        input=sums.read_text(),
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        return []
    return (r.stdout + r.stderr).strip().splitlines() or [f"ssh rc={r.returncode}"]


def restore(
    inv: Inventory,
    model: Model,
    hub: Path,
    *,
    here: str | None = None,
    run=subprocess.run,
) -> Path:
    """Copy a parked HF cache entry into `hub`, verify it, then move it into place.

    rsync lands in a hidden staging dir beside the destination. A rerun resumes there,
    and only a copy that passes its sha256 manifest is renamed to `models--…`. vLLM
    therefore never sees a half-copied entry, and a crash leaves nothing it would
    mistake for a cache hit.
    """
    here = here or this_host()
    if not model.hf_repo:
        raise ValueError(f"'{model.id}' is not a Hugging Face cache entry")
    src = restore_source(inv, model, here=here)
    if src is None:
        raise LookupError(f"'{model.id}' has no hf-cache copy to restore from")
    name = model.entry_name
    dest = hub / name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists — nothing to restore")
    hub.mkdir(parents=True, exist_ok=True)
    staging = hub / f".restore-{name}"
    staging.mkdir(exist_ok=True)
    print(
        f"[modelstore] restoring {model.hf_repo} from {src.name} "
        f"({src.spec(name, here=here)}) into {hub}",
        file=sys.stderr,
    )
    r = run(
        ["rsync", "-aH", "--partial", f"{src.spec(name, here=here)}/", f"{staging}/"]
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"rsync failed (rc={r.returncode}); staging kept at {staging}"
        )
    bad = verify_local(model, staging)
    if bad:
        raise RuntimeError(
            f"restored copy fails its manifest ({len(bad)} lines, first: {bad[0]}); "
            f"staging kept at {staging}"
        )
    staging.rename(dest)
    print(f"[modelstore] restored and verified: {dest}", file=sys.stderr)
    return dest


def ensure_weights(
    key: str,
    entry: dict,
    *,
    hub: Path | None = None,
    inv: Inventory | None = None,
    env: dict[str, str] | None = None,
) -> None:
    """Before a serve: restore a parked model rather than let vLLM re-download it.

    A no-op when the model is already in this host's hub, or when the registry has no
    record of it (vLLM downloads as it always has). When the registry has a copy and
    the restore fails, refuse the serve. The download is still available, but only on
    purpose (`KVLLM_ALLOW_DOWNLOAD=1`).
    """
    repo = entry.get("hf_repo")
    if not repo:
        return
    env = os.environ if env is None else env
    hub = hub or local_hub(env)
    if present_in_hub(hub, repo):
        return
    if inv is None:
        if not DEFAULT_INVENTORY.is_file():
            return
        inv = load_inventory()
    model = inv.by_repo(repo)
    if model is None:
        return
    try:
        restore(inv, model, hub)
    except (OSError, RuntimeError, LookupError, ValueError) as e:
        if env.get(ALLOW_DOWNLOAD_ENV) == "1":
            print(
                f"[modelstore] restore of {repo} failed ({e}); "
                f"{ALLOW_DOWNLOAD_ENV}=1, so vLLM will download it",
                file=sys.stderr,
            )
            return
        sys.exit(
            f"error: '{key}' ({repo}) is parked in the homelab model registry "
            f"(copies: {', '.join(model.copies)}) and restoring it failed: {e}\n"
            f"Fix the restore (`just models-unpark {key}`), or set "
            f"{ALLOW_DOWNLOAD_ENV}=1 to download it from Hugging Face instead."
        )


def _gb(n: int | None) -> str:
    return f"{n / 1e9:.1f}G" if n else "?"


def _cmd_list(args: argparse.Namespace) -> int:
    inv = load_inventory()
    width = max(len(m) for m in inv.models)
    for m in inv.models.values():
        cons = ",".join(m.consumers) or "-"
        print(
            f"{m.id:<{width}}  {_gb(m.size_bytes):>7}  {','.join(m.copies):<22}  {cons}"
        )
    return 0


def _kvllm_registry() -> dict[str, dict] | None:
    from kvllm.registry import load_registry

    try:
        return load_registry()
    except SystemExit:
        return None


def _resolve(ref: str) -> tuple[Inventory, Model]:
    inv = load_inventory()
    try:
        return inv, inv.lookup(ref, _kvllm_registry())
    except KeyError:
        sys.exit(f"error: '{ref}' is not in {DEFAULT_INVENTORY.name} (try: list)")


def _cmd_where(args: argparse.Namespace) -> int:
    inv, m = _resolve(args.ref)
    here = this_host()
    print(f"# {m.id}")
    for f in ("hf_repo", "revision", "downloaded", "consumers", "notes"):
        v = getattr(m, f)
        if v:
            print(f"{f:<11} {', '.join(v) if isinstance(v, tuple) else v}")
    print(f"{'size':<11} {_gb(m.size_bytes)}")
    print("copies:")
    for c in m.copies:
        print(f"  {c:<18} {inv.locations[c].spec(m.entry_name, here=here)}")
    if m.hf_repo:
        hub = local_hub()
        state = "present" if present_in_hub(hub, m.hf_repo) else "absent"
        print(f"this host  {here}: {hub / m.entry_name} — {state}")
    return 0


def _cmd_unpark(args: argparse.Namespace) -> int:
    inv, m = _resolve(args.ref)
    hub = Path(args.hub) if args.hub else local_hub()
    if m.hf_repo and present_in_hub(hub, m.hf_repo):
        print(f"{m.id} is already in {hub}")
        return 0
    try:
        restore(inv, m, hub)
    except (OSError, RuntimeError, LookupError, ValueError) as e:
        sys.exit(f"error: {e}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    inv, m = _resolve(args.ref)
    here = this_host()
    targets = [args.at] if args.at else list(m.copies)
    rc = 0
    for name in targets:
        loc = inv.locations.get(name)
        if loc is None:
            sys.exit(f"error: unknown location '{name}'")
        if loc.host == here:
            bad = verify_local(m, Path(verify_root(loc, m)))
        else:
            bad = verify_remote(m, loc)
        print(f"{m.id} @ {name}: {'OK' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:10]:
            print(f"  {line}")
        rc |= bool(bad)
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kvllm.modelstore", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="every model the homelab has pulled").set_defaults(
        func=_cmd_list
    )
    p = sub.add_parser("where", help="where each copy of one model lives")
    p.add_argument("ref", help="kvllm key, HF repo, or registry id")
    p.set_defaults(func=_cmd_where)
    p = sub.add_parser("unpark", help="restore a parked HF cache entry into this hub")
    p.add_argument("ref")
    p.add_argument("--hub", help="destination hub dir (default: this host's HF cache)")
    p.set_defaults(func=_cmd_unpark)
    p = sub.add_parser("verify", help="check copies against their sha256 manifest")
    p.add_argument("ref")
    p.add_argument("--at", help="one location (default: every recorded copy)")
    p.set_defaults(func=_cmd_verify)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

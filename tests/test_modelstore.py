"""kvllm.modelstore unit tests: the homelab model registry and the restore-before-download hook.

The restore tests use a local "remote" (a location whose host is this host), so rsync runs
for real against tmp dirs and no network is touched.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from kvllm import modelstore
from kvllm.modelstore import (
    Inventory,
    Location,
    Model,
    ensure_weights,
    hf_cache_dirname,
    load_inventory,
    local_hub,
    present_in_hub,
    restore,
)
from kvllm.registry import load_registry

REPO = "org/model"
NAME = hf_cache_dirname(REPO)


def _fake_entry(hub: Path) -> Path:
    """An HF cache entry shaped like huggingface-hub writes it: blob + snapshot symlink."""
    d = hub / NAME
    data = b"weights"
    sha = hashlib.sha256(data).hexdigest()
    (d / "blobs").mkdir(parents=True)
    (d / "blobs" / sha).write_bytes(data)
    (d / "refs").mkdir()
    (d / "refs" / "main").write_text("abc123")
    snap = d / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "model.safetensors").symlink_to(f"../../blobs/{sha}")
    return d


def _manifest(entry_dir: Path, sums_dir: Path) -> None:
    files = sorted(
        p for p in entry_dir.rglob("*") if p.is_file() and not p.is_symlink()
    )
    lines = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(entry_dir)}"
        for p in files
    ]
    sums_dir.mkdir(exist_ok=True)
    (sums_dir / f"{entry_dir.name}.sha256").write_text("\n".join(lines) + "\n")


@pytest.fixture
def parked(tmp_path, monkeypatch):
    """A parked copy in `archive/`, an empty `hub/`, manifests in `sums/`."""
    archive, hub, sums = tmp_path / "archive", tmp_path / "hub", tmp_path / "sums"
    _manifest(_fake_entry(archive), sums)
    monkeypatch.setattr(modelstore, "SUMS_DIR", sums)
    here = modelstore.this_host()
    inv = Inventory(
        locations={"arch": Location("arch", here, str(archive), "hf-cache")},
        models={REPO: Model(id=REPO, hf_repo=REPO, copies=("arch",))},
    )
    return inv, hub, archive


# --- the checked-in registry ---


def test_checked_in_inventory_parses_and_every_entry_has_a_manifest():
    inv = load_inventory()
    assert inv.models
    for m in inv.models.values():
        assert m.sums_path.is_file(), m.id


def test_every_local_kvllm_model_is_in_the_inventory():
    # A key added to models.toml without a registry row would serve with no restore
    # check. Make adding the row part of adding the model.
    inv = load_inventory()
    missing = [
        k
        for k, e in load_registry().items()
        if e.get("hf_repo") and inv.by_repo(e["hf_repo"]) is None
    ]
    assert missing == []


def test_no_orphan_manifests():
    inv = load_inventory()
    used = {m.sums_path.name for m in inv.models.values()}
    assert {p.name for p in modelstore.SUMS_DIR.iterdir()} == used


# --- loading ---


def test_unknown_location_is_refused(tmp_path):
    p = tmp_path / "inv.toml"
    p.write_text('[models."a/b"]\nhf_repo = "a/b"\ncopies = ["nowhere"]\n')
    with pytest.raises(ValueError, match="unknown location"):
        load_inventory(p)


def test_dir_copy_needs_an_entry(tmp_path):
    p = tmp_path / "inv.toml"
    p.write_text(
        '[locations.d]\nhost = "h"\npath = "/x"\nlayout = "dir"\n'
        '[models.thing]\nhf_repo = "a/b"\ncopies = ["d"]\n'
    )
    with pytest.raises(ValueError, match="needs `entry`"):
        load_inventory(p)


def test_lookup_by_id_repo_and_kvllm_key():
    m = Model(id="x", hf_repo="o/n", copies=("l",), consumers=("kvllm:k1",))
    inv = Inventory({}, {"x": m})
    assert inv.lookup("x") is m
    assert inv.lookup("o/n") is m
    assert inv.lookup("k1") is m
    assert inv.lookup("k2", {"k2": {"hf_repo": "o/n"}}) is m
    with pytest.raises(KeyError):
        inv.lookup("nope")


def test_local_hub_resolution():
    assert local_hub({"HF_HUB_CACHE": "/c"}) == Path("/c")
    assert local_hub({"HF_HOME": "/h"}) == Path("/h/hub")


# --- restore ---


def test_restore_copies_verifies_and_moves_into_place(parked):
    inv, hub, _ = parked
    dest = restore(inv, inv.models[REPO], hub)
    assert dest == hub / NAME
    assert present_in_hub(hub, REPO)
    assert (dest / "snapshots/abc123/model.safetensors").read_bytes() == b"weights"
    assert not (hub / f".restore-{NAME}").exists()


def test_restore_that_fails_its_manifest_stays_staged(parked):
    inv, hub, archive = parked
    blob = next((archive / NAME / "blobs").iterdir())
    blob.write_bytes(b"corrupt")
    with pytest.raises(RuntimeError, match="fails its manifest"):
        restore(inv, inv.models[REPO], hub)
    assert not (hub / NAME).exists()  # vLLM never sees it
    assert (hub / f".restore-{NAME}").is_dir()


def test_restore_failed_rsync_raises(parked):
    inv, hub, _ = parked

    def boom(argv, **kw):
        return subprocess.CompletedProcess(argv, 23)

    with pytest.raises(RuntimeError, match="rsync failed"):
        restore(inv, inv.models[REPO], hub, run=boom)


def test_restore_refuses_an_existing_destination(parked):
    inv, hub, _ = parked
    (hub / NAME).mkdir(parents=True)
    with pytest.raises(FileExistsError):
        restore(inv, inv.models[REPO], hub)


def test_remote_source_is_an_rsync_host_spec():
    loc = Location("g", "gratch", "/nas/hub/", "hf-cache")
    assert loc.spec(NAME, here="kai") == f"gratch:/nas/hub/{NAME}"
    assert loc.spec(NAME, here="gratch") == f"/nas/hub/{NAME}"


def test_restore_source_prefers_this_host():
    inv = Inventory(
        {
            "far": Location("far", "gratch", "/a", "hf-cache"),
            "near": Location("near", "kai", "/b", "hf-cache"),
            "plain": Location("plain", "kai", "/c", "dir"),
        },
        {},
    )
    m = Model(id=REPO, hf_repo=REPO, copies=("plain", "far", "near"))
    assert modelstore.restore_source(inv, m, here="kai").name == "near"
    assert modelstore.restore_source(inv, m, here="other").name == "far"


# --- ensure_weights: the serve-path hook ---


def test_ensure_weights_restores_a_parked_model(parked):
    inv, hub, _ = parked
    ensure_weights("k", {"hf_repo": REPO}, hub=hub, inv=inv, env={})
    assert present_in_hub(hub, REPO)


def test_ensure_weights_is_a_noop_when_present(parked, monkeypatch):
    inv, hub, _ = parked
    _fake_entry(hub)

    def never(*a, **kw):
        raise AssertionError("restore must not run")

    monkeypatch.setattr(modelstore, "restore", never)
    ensure_weights("k", {"hf_repo": REPO}, hub=hub, inv=inv, env={})


def test_ensure_weights_leaves_unregistered_models_to_vllm(tmp_path):
    ensure_weights("k", {"hf_repo": "x/y"}, hub=tmp_path, inv=Inventory({}, {}), env={})
    assert not any(tmp_path.iterdir())


def test_ensure_weights_ignores_api_baselines(tmp_path):
    ensure_weights("k", {"provider": "anthropic/x"}, hub=tmp_path, env={})


def test_ensure_weights_refuses_a_failed_restore(parked):
    inv, hub, archive = parked
    next((archive / NAME / "blobs").iterdir()).write_bytes(b"corrupt")
    with pytest.raises(SystemExit, match="KVLLM_ALLOW_DOWNLOAD"):
        ensure_weights("k", {"hf_repo": REPO}, hub=hub, inv=inv, env={})


def test_ensure_weights_download_escape_hatch(parked):
    inv, hub, archive = parked
    next((archive / NAME / "blobs").iterdir()).write_bytes(b"corrupt")
    env = {modelstore.ALLOW_DOWNLOAD_ENV: "1"}
    ensure_weights("k", {"hf_repo": REPO}, hub=hub, inv=inv, env=env)  # no exit
    assert not (hub / NAME).exists()

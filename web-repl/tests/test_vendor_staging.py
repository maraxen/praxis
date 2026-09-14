"""P2.7a flagged-build staging for the coxswain vendor dir.

The vendored transformers.js runtime lives under
overlay/assets/coxswain/vendor/ -- INSIDE the FR-12 flag boundary. These tests
pin the two properties the Coxswain spec depends on:

1. DEFAULT build: zero files from the vendor dir reach dist (AC-11's
   no-coxswain-anywhere clause still holds with the new tree present on
   disk), and the manifest carries neither coxswain nor models keys.
2. FLAGGED (--with-coxswain) build: the vendor dir IS staged, including the
   fetched (untracked) ORT .wasm binary, so a flagged site can serve the
   runtime from its own origin (G5).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_repl  # noqa: E402 -- path setup must precede this import


@pytest.fixture()
def fake_overlay(tmp_path: Path) -> Path:
    """A synthetic overlay/assets tree (never touches the real one)."""
    assets = tmp_path / "assets"
    (assets / "visualizer").mkdir(parents=True)
    (assets / "visualizer" / "index.html").write_text("<html></html>")
    vendor = assets / "coxswain" / "vendor"
    (vendor / "ort").mkdir(parents=True)
    (vendor / "model_integrity.js").write_text("export const x = 1;\n")
    (vendor / "transformers.min.js").write_text("// patched bundle\n")
    (vendor / "ort" / "ort-wasm-simd-threaded.asyncify.mjs").write_text("// ort mjs\n")
    (vendor / "ort" / "ort-wasm-simd-threaded.asyncify.wasm").write_bytes(b"\x00asm\x01")
    return assets


def test_default_build_stages_no_vendor_files(fake_overlay, monkeypatch) -> None:
    """With a coxswain/vendor tree present under the REAL overlay, a DEFAULT
    staging pass must still produce zero paths containing 'coxswain'
    (FR-12/AC-11). Uses the real tree read-only because that is exactly the
    tree this repo ships."""
    real_assets = build_repl.OVERLAY_ASSETS_DIR
    monkeypatch.setattr(build_repl, "OVERLAY_ASSETS_DIR", real_assets)
    out_dir = fake_overlay.parent / "out-default-real"
    build_repl.stage_overlay(out_dir, include_coxswain=False)
    offenders = sorted(str(p.relative_to(out_dir)) for p in out_dir.rglob("*coxswain*"))
    assert offenders == []
    build_repl.assert_no_coxswain_anywhere(out_dir)  # must NOT raise


def test_flagged_build_stages_vendor_dir_including_untracked_wasm(
    tmp_path: Path, monkeypatch
) -> None:
    """--with-coxswain staging copies the whole vendor tree into dist,
    INCLUDING the gitignored .wasm (dist is built output; gitignore governs
    the repo, not the artifact)."""
    fake_assets = tmp_path / "assets"
    (fake_assets / "visualizer").mkdir(parents=True)
    (fake_assets / "visualizer" / "index.html").write_text("<html></html>")
    vendor = fake_assets / "coxswain" / "vendor"
    (vendor / "ort").mkdir(parents=True)
    (vendor / "transformers.min.js").write_text("// bundle\n")
    (vendor / "model_integrity.js").write_text("export {};\n")
    (vendor / "ort" / "ort-wasm-simd-threaded.asyncify.wasm").write_bytes(b"\x00asm")

    monkeypatch.setattr(build_repl, "OVERLAY_ASSETS_DIR", fake_assets)
    out_dir = tmp_path / "out"
    build_repl.stage_overlay(out_dir, include_coxswain=True)

    staged_vendor = out_dir / "assets" / "coxswain" / "vendor"
    assert (staged_vendor / "transformers.min.js").is_file()
    assert (staged_vendor / "model_integrity.js").is_file()
    wasm = staged_vendor / "ort" / "ort-wasm-simd-threaded.asyncify.wasm"
    assert wasm.is_file(), "flagged dist must carry the ORT backend binary"
    assert wasm.read_bytes() == b"\x00asm"


def test_vendored_bundle_is_g5_clean() -> None:
    """GATE G5 half-check at unit level: the TRACKED vendored bundle must not
    contain cdn.jsdelivr.net anywhere (the fetch_models patch removed the one
    default). Skipped when the runtime has not been vendored yet."""
    bundle = (
        build_repl.OVERLAY_ASSETS_DIR
        / "coxswain"
        / "vendor"
        / "transformers.min.js"
    )
    if not bundle.is_file():
        pytest.skip("runtime not vendored yet (fetch_models.py --runtime)")
    data = bundle.read_bytes()
    assert b"cdn.jsdelivr.net" not in data


def test_vendor_manifest_pins_all_runtime_files() -> None:
    """VENDOR_MANIFEST.json must exist once the runtime is vendored and must
    pin sha256+bytes for every file in the tree, with exactly one untracked
    binary (the ORT wasm)."""
    vendor = build_repl.OVERLAY_ASSETS_DIR / "coxswain" / "vendor"
    manifest_path = vendor / "VENDOR_MANIFEST.json"
    if not manifest_path.is_file():
        pytest.skip("runtime not vendored yet (fetch_models.py --runtime)")
    import json

    record = json.loads(manifest_path.read_text())
    pinned = {e["path"]: e for e in record["files"]}
    on_disk = {
        p.relative_to(vendor).as_posix()
        for p in vendor.rglob("*")
        if p.is_file() and p.name != "VENDOR_MANIFEST.json"
    }
    assert set(pinned) == on_disk
    import hashlib

    for rel, entry in pinned.items():
        data = (vendor / rel).read_bytes()
        assert len(data) == entry["bytes"], rel
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], rel
    untracked = [rel for rel, e in pinned.items() if not e["tracked"]]
    assert untracked == ["ort/ort-wasm-simd-threaded.asyncify.wasm"]

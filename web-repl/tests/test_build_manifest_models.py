"""build_manifest.py --with-models (P2.7a): the manifest's 'models' key exists
ONLY under the flag, carries wheels-shaped entries for the gitignored
web-repl/vendor/models/ FunctionGemma export, is verified against upstream
pins at GENERATION time, and is re-verified by verify_manifest. A default
manifest stays byte-identical to its pre-models shape for identical inputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_manifest  # noqa: E402 -- path setup must precede this import
import fetch_models  # noqa: E402 -- same scripts dir


def _make_web_repl(tmp_path: Path) -> Path:
    """Scratch web-repl root with the minimal overlay tree build_manifest
    requires before any flag matters."""
    web_repl = tmp_path / "web-repl"
    wheels = web_repl / "overlay" / "assets" / "wheels"
    wheels.mkdir(parents=True)
    (wheels / "pkg-1.0.0-py3-none-any.whl").write_bytes(b"not a wheel")
    shims = web_repl / "overlay" / "assets" / "shims"
    shims.mkdir(parents=True)
    (shims / "web_serial_shim.py").write_text("# shim\n")
    return web_repl


def _seed_pinned_files(dest_dir: Path, pins: dict[str, dict], drift: str | None = None) -> None:
    """Materialise pinned files whose bytes match their (shrunk) pins.
    Upstream digests cannot be inverted, so the pins are re-derived from the
    written content -- the same act fetch_models performs when pinning a fresh
    fetch. *drift* names one file whose on-disk bytes are THEN corrupted."""
    import hashlib

    for repo_rel, pin in pins.items():
        data = b"\x01" * pin["bytes"]
        path = dest_dir / repo_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        pin["bytes"] = len(data)
        if "sha256" in pin:
            pin.pop("git_blob_sha1", None)
            pin["sha256"] = hashlib.sha256(data).hexdigest()
        else:
            pin["git_blob_sha1"] = fetch_models.git_blob_sha1(data)
        if repo_rel == drift:
            path.write_bytes(b"DRIFTED-CONTENT!!" * 2)


def test_default_manifest_has_no_models_key(tmp_path: Path) -> None:
    web_repl = _make_web_repl(tmp_path)
    manifest = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True
    )
    assert "models" not in manifest
    assert set(manifest) == {"praxis_git_sha", "wheels", "sources"}


def test_default_manifest_ignores_models_dir(tmp_path: Path) -> None:
    """AC-11 discipline: a fetched-but-unflagged models dir must not change
    the default manifest AT ALL (byte-identical gate)."""
    web_repl = _make_web_repl(tmp_path)
    before = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True
    )
    model_dir = web_repl / "vendor" / "models" / fetch_models.MODEL_DIR_NAME
    (model_dir / "onnx").mkdir(parents=True)
    (model_dir / "config.json").write_text("{}")
    after = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True
    )
    assert json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)


def _seed_verified_model_files(models_dir: Path, pins: dict[str, dict]) -> None:
    raise NotImplementedError


def test_with_models_tracks_entries_and_verifies(tmp_path: Path, monkeypatch) -> None:
    web_repl = _make_web_repl(tmp_path)
    models_dir = web_repl / "vendor" / "models"
    dest_dir = models_dir / fetch_models.MODEL_DIR_NAME

    # Shrink the heavyweight pins for unit speed but keep shapes identical.
    shrunk = {
        name: {**pin, "bytes": min(pin["bytes"], 4096)}
        for name, pin in fetch_models.MODEL_FILE_PINS.items()
    }
    monkeypatch.setattr(fetch_models, "MODEL_FILE_PINS", shrunk)
    _seed_pinned_files(dest_dir, shrunk)

    manifest = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_models=True
    )
    entries = manifest["models"]
    assert [e["filename"] for e in entries] == sorted(e["filename"] for e in entries)
    assert set(manifest) == {"praxis_git_sha", "wheels", "sources", "models"}
    for entry in entries:
        assert set(entry) == {"name", "filename", "source_sha", "sha256", "bytes"}
        assert entry["name"] == f"{fetch_models.MODEL_NAME}-{fetch_models.MODEL_DTYPE}"
        assert entry["source_sha"] == fetch_models.MODEL_REVISION
        assert len(entry["sha256"]) == 64
        assert isinstance(entry["bytes"], int) and entry["bytes"] > 0
    names = {e["filename"] for e in entries}
    assert f"{fetch_models.MODEL_DIR_NAME}/onnx/model_q4f16.onnx_data" in names

    # verify_manifest clean on untouched disk...
    assert build_manifest.verify_manifest(manifest, web_repl_root=web_repl) == []

    # ...names drift loudly...
    victim = dest_dir / "onnx/model_q4f16.onnx"
    original = victim.read_bytes()
    victim.write_bytes(original + b"x")
    problems = build_manifest.verify_manifest(manifest, web_repl_root=web_repl)
    assert any("model sha256 mismatch" in p and "model_q4f16.onnx" in p for p in problems)

    # ...and deletion loudly.
    victim.unlink()
    problems = build_manifest.verify_manifest(manifest, web_repl_root=web_repl)
    assert any("model missing on disk" in p and "model_q4f16.onnx" in p for p in problems)


def test_with_models_without_dir_fails_loud(tmp_path: Path) -> None:
    web_repl = _make_web_repl(tmp_path)
    with pytest.raises(build_manifest.ManifestError, match="does not exist"):
        build_manifest.build_manifest(
            web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_models=True
        )


def test_with_models_with_drifted_file_fails_loud(tmp_path: Path, monkeypatch) -> None:
    """Generation-time verification: a corrupted download must never earn a
    manifest entry -- build_manifest fails loud naming the file."""
    web_repl = _make_web_repl(tmp_path)
    dest_dir = web_repl / "vendor" / "models" / fetch_models.MODEL_DIR_NAME
    shrunk = {name: {"bytes": 32} for name in fetch_models.MODEL_FILE_PINS}
    monkeypatch.setattr(fetch_models, "MODEL_FILE_PINS", shrunk)
    _seed_pinned_files(dest_dir, shrunk, drift="config.json")

    with pytest.raises(build_manifest.ManifestError, match="config.json"):
        build_manifest.build_manifest(
            web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_models=True
        )


def test_pin_table_self_consistency() -> None:
    """The single source of truth must be internally coherent and q4f16-only
    (D4: exactly ONE dtype ships globally)."""
    pins = fetch_models.MODEL_FILE_PINS
    assert set(pins) == {
        "config.json",
        "generation_config.json",
        "tokenizer_config.json",
        "chat_template.jinja",
        "tokenizer.json",
        "onnx/model_q4f16.onnx",
        "onnx/model_q4f16.onnx_data",
    }
    for name, pin in pins.items():
        assert pin["bytes"] > 0, name
        has_digest = ("sha256" in pin) != ("git_blob_sha1" in pin)
        assert has_digest, f"{name}: exactly one digest kind required"
        if "sha256" in pin:
            assert len(pin["sha256"]) == 64
        else:
            assert len(pin["git_blob_sha1"]) == 40
    assert fetch_models.MODEL_DTYPE == "q4f16"
    assert fetch_models.MODEL_REPO_ID.endswith("/functiongemma-270m-it-ONNX")
    # ~426 MB expectation from spec/research (D4 primary).
    total_gb = fetch_models.EXPECTED_MODEL_TOTAL_BYTES / 1e9
    assert 0.40 < total_gb < 0.46, total_gb


def test_git_blob_sha1_known_vector() -> None:
    assert fetch_models.git_blob_sha1(b"") == (
        "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"  # git hash-object of empty blob
    )
    assert fetch_models.git_blob_sha1(b"hello\n") == (
        "ce013625030ba8dba906f756967f9e9ca394464a"
    )


def test_patch_jsdelivr_default_counted() -> None:
    anchor = "https://cdn.jsdelivr.net/npm/onnxruntime-web@${Xx12.versions.web}/dist/"
    patched = fetch_models.patch_jsdelivr_default(f'let e=`{anchor}`;ok')
    assert patched == "let e=`./ort/`;ok"
    # zero matches and two matches must both fail loud
    with pytest.raises(fetch_models.FetchError, match="exactly 1"):
        fetch_models.patch_jsdelivr_default("nothing here")
    with pytest.raises(fetch_models.FetchError, match="exactly 1"):
        fetch_models.patch_jsdelivr_default(f"{anchor} {anchor}")


def test_model_manifest_entries_shape() -> None:
    entries = fetch_models.model_manifest_entries()
    assert len(entries) == len(fetch_models.MODEL_FILE_PINS)
    filenames = [e["filename"] for e in entries]
    assert filenames == sorted(filenames)
    assert all(e["filename"].startswith(f"{fetch_models.MODEL_DIR_NAME}/") for e in entries)

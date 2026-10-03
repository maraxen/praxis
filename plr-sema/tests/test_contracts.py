"""plr_sema.contracts (spec 261002 §7)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from plr_sema.contracts import (
    ENV_VAR,
    ContractsError,
    build_gz,
    canonical_json,
    contracts_source,
    load_contracts,
)

REAL = Path(__file__).resolve().parents[1] / "data" / "derived_contracts.json"
TOY = {"b": [1, 2], "a": {"z": "ü", "y": None}}


@pytest.fixture
def toy_json(tmp_path: Path) -> Path:
    p = tmp_path / "c.json"
    p.write_text(json.dumps(TOY, indent=2), encoding="utf-8")
    return p


def test_json_and_gz_load_to_the_same_canonical_text(toy_json: Path, tmp_path: Path) -> None:
    gz = build_gz(toy_json, tmp_path / "c.json.gz")
    a, b = load_contracts(toy_json), load_contracts(gz)
    assert a.json_text == b.json_text == canonical_json(TOY)
    assert a.sha256 == b.sha256


def test_gzip_is_detected_by_magic_not_extension(toy_json: Path, tmp_path: Path) -> None:
    disguised = tmp_path / "contracts.json"
    disguised.write_bytes(gzip.compress(toy_json.read_bytes()))
    assert load_contracts(disguised).json_text == canonical_json(TOY)


def test_build_gz_is_byte_deterministic(toy_json: Path, tmp_path: Path) -> None:
    one = build_gz(toy_json, tmp_path / "1.gz").read_bytes()
    two = build_gz(toy_json, tmp_path / "2.gz").read_bytes()
    assert one == two


@pytest.mark.parametrize(
    "payload",
    [b"", b"{not json", b"\x1f\x8b\x08\x00truncated", b"[1, 2, 3]", b"\xff\xfe\x00bad"],
    ids=["empty", "bad-json", "truncated-gzip", "not-an-object", "not-utf8"],
)
def test_bad_files_raise_contracts_error(tmp_path: Path, payload: bytes) -> None:
    p = tmp_path / "bad.json"
    p.write_bytes(payload)
    with pytest.raises(ContractsError):
        load_contracts(p)


def test_missing_file_raises_contracts_error(tmp_path: Path) -> None:
    with pytest.raises(ContractsError):
        load_contracts(tmp_path / "absent.json")


def test_real_table_round_trips() -> None:
    c = load_contracts(REAL)
    assert json.loads(c.json_text) == json.loads(REAL.read_text(encoding="utf-8"))


def test_resolver_layers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    nested = tmp_path / "pkg" / "sub"
    nested.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[tool.plr-sema]\ncontracts = "data/c.json"\n')
    (tmp_path / "pkg" / "pyproject.toml").write_text('[project]\nname = "pkg"\n')

    assert contracts_source("x.json", start=nested).layer == "argument"

    src = contracts_source(start=nested)  # walks past pkg/pyproject.toml (no table)
    assert src.layer == f"pyproject:{tmp_path / 'pyproject.toml'}"
    assert src.path == tmp_path / "data" / "c.json"

    monkeypatch.setenv(ENV_VAR, str(tmp_path / "env.json"))
    assert contracts_source(start=nested).layer == "env"
    for off in ("", "none", "NONE"):
        monkeypatch.setenv(ENV_VAR, off)
        assert contracts_source(start=nested) == contracts_source(start=nested)
        assert contracts_source(start=nested).path is None
        assert contracts_source(start=nested).layer == "env:disabled"


def test_resolver_none_when_nothing_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    src = contracts_source(start=tmp_path)
    assert (src.path, src.layer) == (None, "none")


def test_malformed_pyproject_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.plr-sema\ncontracts = ")
    with pytest.raises(ContractsError):
        contracts_source(start=tmp_path)


def test_non_string_contracts_value_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.plr-sema]\ncontracts = 3\n")
    with pytest.raises(ContractsError):
        contracts_source(start=tmp_path)


def test_corrupt_gzip_stream_raises_contracts_error(tmp_path: Path) -> None:
    """A bit-flipped deflate stream raises zlib.error, not EOFError/BadGzipFile."""
    good = gzip.compress(json.dumps({"k": "v" * 500}).encode(), mtime=0)
    p = tmp_path / "corrupt.json.gz"
    # byte 10 is the first deflate block header; flipping it is an invalid block type
    p.write_bytes(good[:10] + bytes([good[10] ^ 0xFF]) + good[11:])
    with pytest.raises(ContractsError):
        load_contracts(p)

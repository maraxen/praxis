"""plr_sema.contracts: load the derived contract table and resolve where it lives.

Stdlib only (spec 261002 §7). The committed source of truth is the pretty
``plr-sema/data/derived_contracts.json``; ``build_gz`` makes the compact,
byte-deterministic ``.json.gz`` that browser/backend surfaces ship, and that
file is a build artifact, never committed.

Resolution (no default path in library code): explicit argument >
``$PLR_SEMA_CONTRACTS`` (empty or ``none`` disables) > the first
``pyproject.toml`` walking up from ``start`` that has
``[tool.plr-sema] contracts`` (relative to that file) > unavailable.
``contracts_source()`` reports which layer decided.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import zlib
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: the pyproject layer is skipped
    tomllib = None  # type: ignore[assignment]

ENV_VAR = "PLR_SEMA_CONTRACTS"
_GZIP_MAGIC = b"\x1f\x8b"


class ContractsError(ValueError):
    """The contract table, or the config naming it, could not be read."""


@dataclass(frozen=True)
class Contracts:
    json_text: str  # canonical compact JSON; what check_graph receives
    sha256: str  # sha256 of json_text: identical for .json and .json.gz
    path: Path


@dataclass(frozen=True)
class ContractsSource:
    path: Path | None
    layer: str  # "argument" | "env" | "env:disabled" | "pyproject:<file>" | "none"


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_contracts(path: str | os.PathLike[str]) -> Contracts:
    p = Path(path)
    try:
        raw = p.read_bytes()
        if raw[:2] == _GZIP_MAGIC:
            raw = gzip.decompress(raw)
        obj = json.loads(raw.decode("utf-8"))
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractsError(f"cannot load contracts from {p}: {exc}") from exc
    if not isinstance(obj, dict):
        raise ContractsError(f"contracts at {p} are not a JSON object")
    text = canonical_json(obj)
    return Contracts(json_text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), path=p)


def build_gz(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> Path:
    contracts = load_contracts(src)
    data = gzip.compress(contracts.json_text.encode("utf-8"), compresslevel=9, mtime=0)
    out = Path(dst)
    tmp = out.with_name(f"{out.name}.tmp{os.getpid()}")
    tmp.write_bytes(data)
    os.replace(tmp, out)
    return out


def contracts_source(
    explicit: str | os.PathLike[str] | None = None, *, start: str | os.PathLike[str] | None = None
) -> ContractsSource:
    if explicit is not None:
        return ContractsSource(Path(explicit), "argument")
    env = os.environ.get(ENV_VAR)
    if env is not None:
        if env.strip().lower() in ("", "none"):
            return ContractsSource(None, "env:disabled")
        return ContractsSource(Path(env), "env")
    found = _from_pyproject(Path.cwd() if start is None else Path(start))
    return found if found is not None else ContractsSource(None, "none")


def _from_pyproject(start: Path) -> ContractsSource | None:
    if tomllib is None:
        return None
    here = start.resolve()
    for directory in (here, *here.parents):
        candidate = directory / "pyproject.toml"
        if not candidate.is_file():
            continue
        try:
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ContractsError(f"malformed {candidate}: {exc}") from exc
        value = data.get("tool", {}).get("plr-sema", {}).get("contracts")
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ContractsError(f"{candidate}: [tool.plr-sema] contracts must be a non-empty string")
        return ContractsSource(directory / value, f"pyproject:{candidate}")
    return None

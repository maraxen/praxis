"""Single-writer I/O primitives for the ingest pipeline.

`write_artifact` is the ONLY function in `training/ingest/` that opens a file for
writing or creates a directory (§5.6(a), C2). Every command module writes through
it so the no-auto-patch guarantee has one enforcement point.
"""

from pathlib import Path
from typing import Final

from . import cli

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

#: Directory prefixes (relative to REPO_ROOT) that no ingest command may ever write
#: under. These are the canonical tables and downstream artifacts the audit exists
#: to protect -- editing any of them is a human action in a reviewed diff, never a
#: side effect of running a gate (§5.6(a)).
PROTECTED_ROOTS: Final[tuple[str, ...]] = (
    "coxswain/",                       # tool_schema.py, param_namespace.py
    "training/floor_gen/data/",        # ambiguity_matrix.json
    "training/overlay_gen/",           # miner.py + its out/
    "training/assemble/out/",          # the 188-row corpus + manifest
    "training/golden/",                # golden fixtures
    "training/ingest/data/",           # committed GATE INPUTS: never written by any
                                        # ingest command, hand-authored OR computed.
    "external/",                       # vendored PLR
)


class ProtectedPathError(cli.IngestError):
    """Raised when a write operation targets a protected, committed artifact."""


def write_artifact(out_dir: Path, name: str, payload: str | bytes) -> Path:
    """The ONLY function in training/ingest/ that opens a file for writing or
    creates a directory.

    Resolves out_dir/name; raises ProtectedPathError if the resolved target is
    inside REPO_ROOT and under any PROTECTED_ROOTS prefix. Temp dirs are outside
    REPO_ROOT and therefore always legal.
    """
    target = (Path(out_dir) / name).resolve()

    try:
        rel = target.relative_to(REPO_ROOT)
    except ValueError:
        rel = None  # outside REPO_ROOT entirely -- e.g. a pytest tmp_path -- always legal

    if rel is not None:
        rel_str = rel.as_posix()
        for root in PROTECTED_ROOTS:
            if rel_str == root.rstrip("/") or rel_str.startswith(root):
                raise ProtectedPathError(
                    f"Cannot write to {target}: it is under the protected root "
                    f"{root!r}. This file is committed to version control and "
                    f"edited only via the copy-and-review workflow (§5.6(a))."
                )

    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, bytes):
        target.write_bytes(payload)
    else:
        target.write_text(payload)
    return target

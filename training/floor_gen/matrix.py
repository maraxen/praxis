"""Committed verb x ambiguity matrix (task deliverable 1).

The matrix lives as DATA at ``floor_gen/data/ambiguity_matrix.json`` and this
module loads + validates it loudly against the live canonical tables:

- ``none`` cells: exactly one per phase-2-included verb (clean parses).
- ``missing-slot`` cells: exactly one per included verb that HAS required
  params; ``missing_param`` must be a required schema param of that verb.
  Supervision = incomplete tool_call whose ``missing_required`` is derived
  deterministically via D11 (spec rev2 D7: NOT free-text slot naming).
- ``ambiguous-referent`` cells: exactly one per included verb carrying
  symbolic resource refs; ``slot_param`` must be symbolic. Supervision =
  complete tool_call whose vague reference derives an ``unresolved_slots``
  entry (cue-2 clarification at serving time).
- ``out-of-surface`` cells: anchored on verbs OUTSIDE the copilot generation
  surface entirely (experimental/excluded TOOL_SCHEMA entries, or the generic
  off-domain sentinel). Per D7/D11 supervision is an NL clarification turn
  with NO tool_call.

Cell order in the file is stable data; iteration order used by the pipeline
is deterministic class round-robin (see ``cells_round_robin``) so any
``--limit N`` prefix spans all four classes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from coxswain.plr.param_namespace import PARAM_NAMESPACE, params_of, symbolic_slots
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES, TOOL_SCHEMA

from floor_gen.versions import AMBIGUITY_CLASSES, MATRIX_VERSION

__all__ = [
    "AmbiguityMatrix",
    "MatrixCell",
    "MatrixError",
    "committed_matrix_path",
    "cells_round_robin",
    "load_matrix",
]

_MATRIX_PATH: Final[Path] = Path(__file__).resolve().parent / "data" / "ambiguity_matrix.json"


class MatrixError(ValueError):
    """Raised loudly for any committed-matrix inconsistency."""


@dataclass(frozen=True)
class MatrixCell:
    """One matrix cell: verb x ambiguity class + class-specific payload."""

    cell_id: str
    verb: str | None  # None only for the generic out-of-surface sentinel
    ambiguity_class: str
    examples_per_cell: int
    missing_param: str | None = None
    slot_param: str | None = None
    surface_status: str = ""  # out-of-surface only: why it's outside
    off_surface_request: str = ""  # out-of-surface only: seed for teacher
    notes: str = ""
    #: matrix revision that APPENDED this cell ("" = original design). Cells
    #: appended in revision r iterate AFTER every cell of earlier revisions
    #: (``cells_round_robin``), so appending never re-numbers existing rows.
    appended_in_matrix_version: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "verb": self.verb,
            "ambiguity_class": self.ambiguity_class,
            "examples_per_cell": self.examples_per_cell,
            **{
                k: v
                for k, v in (
                    ("missing_param", self.missing_param),
                    ("slot_param", self.slot_param),
                    ("surface_status", self.surface_status),
                    ("off_surface_request", self.off_surface_request),
                    ("notes", self.notes),
                    ("appended_in_matrix_version", self.appended_in_matrix_version),
                )
                if v
            },
        }


@dataclass(frozen=True)
class AmbiguityMatrix:
    matrix_version: str
    cells: tuple[MatrixCell, ...]


def committed_matrix_path() -> Path:
    return _MATRIX_PATH


def load_matrix(path: Path | None = None) -> AmbiguityMatrix:
    """Load + fully validate the committed matrix. Loud on any drift between
    the committed data and the live canonical tables.
    """
    matrix_path = path if path is not None else _MATRIX_PATH
    raw = json.loads(matrix_path.read_text(encoding="utf-8"))
    version = str(raw.get("matrix_version", ""))
    if version != MATRIX_VERSION:
        raise MatrixError(f"matrix_version {version!r} != pinned {MATRIX_VERSION!r}")
    cells = tuple(
        MatrixCell(
            cell_id=str(entry["cell_id"]),
            verb=entry.get("verb"),
            ambiguity_class=str(entry["ambiguity_class"]),
            examples_per_cell=int(entry.get("examples_per_cell", 3)),
            missing_param=entry.get("missing_param"),
            slot_param=entry.get("slot_param"),
            surface_status=str(entry.get("surface_status", "")),
            off_surface_request=str(entry.get("off_surface_request", "")),
            notes=str(entry.get("notes", "")),
            appended_in_matrix_version=str(entry.get("appended_in_matrix_version", "")),
        )
        for entry in raw["cells"]
    )
    _validate(cells)
    return AmbiguityMatrix(matrix_version=version, cells=cells)


def _validate(cells: tuple[MatrixCell, ...]) -> None:
    ids = [c.cell_id for c in cells]
    if len(ids) != len(set(ids)):
        raise MatrixError("duplicate cell_id in matrix")
    present_classes = {c.ambiguity_class for c in cells}
    for cls in AMBIGUITY_CLASSES:
        if cls not in present_classes:
            raise MatrixError(f"ambiguity class {cls!r} has no cell")

    by_class: dict[str, list[MatrixCell]] = {cls: [] for cls in AMBIGUITY_CLASSES}
    for cell in cells:
        if cell.ambiguity_class not in by_class:
            raise MatrixError(f"unknown ambiguity class {cell.ambiguity_class!r}")
        if cell.examples_per_cell < 1:
            raise MatrixError(f"{cell.cell_id}: examples_per_cell must be >= 1")
        if cell.appended_in_matrix_version:
            if not cell.appended_in_matrix_version.isdigit() or int(cell.appended_in_matrix_version) > int(MATRIX_VERSION):
                raise MatrixError(
                    f"{cell.cell_id}: appended_in_matrix_version {cell.appended_in_matrix_version!r} "
                    f"is not a matrix revision <= {MATRIX_VERSION}"
                )
        by_class[cell.ambiguity_class].append(cell)

        if cell.ambiguity_class == "out-of-surface":
            if cell.verb is not None and cell.verb in PHASE2_TOOL_NAMES:
                raise MatrixError(
                    f"{cell.cell_id}: out-of-surface cell anchors INCLUDED verb {cell.verb!r}"
                )
            if cell.verb is not None and cell.verb not in TOOL_SCHEMA:
                raise MatrixError(f"{cell.cell_id}: unknown verb {cell.verb!r}")
            if not cell.off_surface_request:
                raise MatrixError(f"{cell.cell_id}: out-of-surface cell needs off_surface_request")
            continue

        if cell.verb not in PARAM_NAMESPACE:
            raise MatrixError(f"{cell.cell_id}: verb {cell.verb!r} not phase-2-included")

    expected_none = set(PHASE2_TOOL_NAMES)
    got_none = {c.verb for c in by_class["none"]}
    if got_none != expected_none:
        raise MatrixError(f"none-class coverage mismatch: missing {expected_none - got_none}, extra {got_none - expected_none}")

    eligible_missing = {
        tool for tool in PARAM_NAMESPACE if any(s.required for s in params_of(tool))
    }
    got_missing = {c.verb: c for c in by_class["missing-slot"]}
    if set(got_missing) != eligible_missing:
        raise MatrixError(
            f"missing-slot coverage mismatch: missing {eligible_missing - set(got_missing)}, extra {set(got_missing) - eligible_missing}"
        )
    for cell in got_missing.values():
        required = {s.name for s in params_of(cell.verb) if s.required}  # type: ignore[arg-type]
        if cell.missing_param not in required:
            raise MatrixError(
                f"{cell.cell_id}: missing_param {cell.missing_param!r} not required on {cell.verb!r}"
            )

    eligible_symbolic = {
        tool for tool in PARAM_NAMESPACE if len(symbolic_slots(tool)) > 0
    }
    got_symbolic = {c.verb: c for c in by_class["ambiguous-referent"]}
    if set(got_symbolic) != eligible_symbolic:
        raise MatrixError(
            f"ambiguous-referent coverage mismatch: missing {eligible_symbolic - set(got_symbolic)}, extra {set(got_symbolic) - eligible_symbolic}"
        )
    for cell in got_symbolic.values():
        symbolic_names = {s.name for s in symbolic_slots(cell.verb)}  # type: ignore[arg-type]
        if cell.slot_param not in symbolic_names:
            raise MatrixError(
                f"{cell.cell_id}: slot_param {cell.slot_param!r} not symbolic on {cell.verb!r}"
            )


def cells_round_robin(cells: tuple[MatrixCell, ...]) -> tuple[MatrixCell, ...]:
    """Deterministic iteration order cycling through the four classes so a
    limited smoke run always spans them. Within a class, file order holds.

    Cells carry ``appended_in_matrix_version``; the round-robin runs over the
    original design first ("") and then over each appended revision in
    ascending order, so appending cells never changes the position -- hence
    the record-id ordinal -- of any earlier cell's rows.
    """
    revisions = sorted({c.appended_in_matrix_version for c in cells}, key=lambda r: (r != "", int(r or 0)))
    ordered: list[MatrixCell] = []
    for rev in revisions:
        buckets: dict[str, list[MatrixCell]] = {cls: [] for cls in AMBIGUITY_CLASSES}
        for cell in cells:
            if cell.appended_in_matrix_version == rev:
                buckets[cell.ambiguity_class].append(cell)
        levels = max((len(bucket) for bucket in buckets.values()), default=0)
        for level in range(levels):
            for cls in AMBIGUITY_CLASSES:
                bucket = buckets[cls]
                if level < len(bucket):
                    ordered.append(bucket[level])
    return tuple(ordered)

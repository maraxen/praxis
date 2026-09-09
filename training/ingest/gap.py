"""Coverage-gap report for the ingest pipeline — Gate G1 (§6).

Cross-references the 43-cell verb-x-ambiguity matrix against the 188-row corpus
sidecar, computes the pre-registered T1/T2/T3 metrics, and decides PROCEED / STOP /
CONTESTED against the thresholds committed in `versions.py` (GAP_THRESHOLDS,
T1_INVARIANT) *before* this module existed (PM-2).

Key design points, all pinned in §6:
- §6.1: cell attribution. Only 20 of 188 sidecar rows carry `lineage.cell_id`; the
  fallback (`cell_key`) is the DOMINANT path, not an edge case. Off-matrix keys are
  counted in `unmatched_cell_keys`, never dropped (F5) -- expected EMPTY against the
  live corpus (a regression pin, W9).
- §6.2: `value_form`/`shape_key` are corrected against PARAM_NAMESPACE's real shape
  (verb-keyed dict of TUPLES, not a nested name-keyed dict -- C1), keyed on
  `ParamSpec.name` (schema-side), with slice-before-subscript, bool-before-number,
  and int/float collapsed to "number" (C20).
- §6.4: T1 is a pinned INVARIANT, not a gate (C12). T2 is computed both `collapsed`
  (gate authority) and `strict` (robustness probe); disagreement is CONTESTED (exit
  7), never resolved by picking either side (W2). T3 reuses
  `recipes.in_surface_verbs` -- one definition, shared with `audit.py`'s
  `param_candidate`.
"""

import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, Mapping, TextIO

from . import cli, io, recipes
from .versions import GAP_THRESHOLDS, GAP_THRESHOLDS_VERSION, T1_INVARIANT

from assemble.build import CLASS_MAP
from coxswain.plr.param_namespace import PARAM_NAMESPACE, ParamKind, ParamSpec
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES, TOOL_SCHEMA
from floor_gen.matrix import MatrixCell, load_matrix

__all__ = [
    "CellGap",
    "VerbGap",
    "GapStats",
    "GapError",
    "INVERSE_CLASS_MAP",
    "SIDECAR_RELPATH",
    "MANIFEST_RELPATH",
    "default_sidecar_path",
    "default_manifest_path",
    "cell_key",
    "value_form",
    "shape_key",
    "run_gap",
    "build_report",
    "gate",
]


# ============================================================================
# Exception class
# ============================================================================


class GapError(cli.IngestError):
    """Raised for gap-report logic errors, data inconsistencies, or missing files.

    Maps to exit 1 via cli.run() -- but Task 7's `gate()` catches CookbookUnavailable
    itself (maps to 5) before any GapError can be raised (§7.5).
    """

    pass


# ============================================================================
# Class-vocabulary inversion (§6.1)
# ============================================================================

if len(set(CLASS_MAP.values())) != len(CLASS_MAP):
    raise GapError(f"CLASS_MAP is not injective: {CLASS_MAP!r}")

INVERSE_CLASS_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {v: k for k, v in CLASS_MAP.items()}
)
# -> {"clean_parse": "none", "missing_slot": "missing-slot",
#     "ambiguous_referent": "ambiguous-referent", "out_of_surface": "out-of-surface"}


def cell_key(row: Mapping[str, Any]) -> str:
    """Compute a sidecar row's matrix cell key (§6.1, C18/C19).

    Only 20 of 188 rows carry `lineage.cell_id`; the fallback below is the
    DOMINANT path, not an edge case.
    """
    cid = (row.get("lineage") or {}).get("cell_id")
    if cid:
        return cid  # 20 of 188 rows carry this
    verb = row.get("verb") or ""  # corpus uses "", matrix uses None
    klass = INVERSE_CLASS_MAP[row["ambiguity_class"]]  # underscored -> hyphenated
    if klass == "out-of-surface" and not verb:
        return "generic__out-of-surface"  # the matrix's verb=None sentinel cell
    return f"{verb}__{klass}"


# ============================================================================
# Paths
# ============================================================================

SIDECAR_RELPATH: Final[str] = "training/assemble/out/corpus_p25_sidecar.jsonl"
MANIFEST_RELPATH: Final[str] = "training/assemble/out/manifest.json"


def default_sidecar_path() -> Path:
    """Derive the default sidecar path from the repo root (mirrors recipes.py)."""
    return io.REPO_ROOT / SIDECAR_RELPATH


def default_manifest_path() -> Path:
    """Derive the default assembly-manifest path from the repo root."""
    return io.REPO_ROOT / MANIFEST_RELPATH


def default_out_dir() -> Path:
    """The committed output location (§7.1's layout: `training/ingest/out/`).

    Unlike audit/recipes/eval_split's emitters (which require `--out` explicitly
    and are the six commands enumerated in §7.5's exit-64 row), `gap --gate`
    always writes a report "in every case except a true measurement failure"
    (§6.4) -- `gap --gate` is deliberately absent from that six-command list, so
    `--out` is optional at the CLI layer and defaults here rather than being
    enforced by `out_required_for`.
    """
    return Path(__file__).parent / "out"


def load_sidecar_rows(path: Path) -> tuple[Mapping[str, Any], ...]:
    """Read the JSONL sidecar into a tuple of row mappings, in file order.

    Raises:
        GapError: If the file is missing, unreadable, or contains invalid JSON.
    """
    if not path.exists():
        raise GapError(f"Sidecar not found: {path}")

    rows: list[Mapping[str, Any]] = []
    try:
        with open(path) as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise GapError(f"Sidecar parse error at line {line_no}: {e}") from e
    except OSError as e:
        raise GapError(f"Could not read sidecar: {e}") from e

    return tuple(rows)


def load_manifest(path: Path) -> Mapping[str, Any]:
    """Read the assembly manifest.

    Raises:
        GapError: If the file is missing, unreadable, or contains invalid JSON.
    """
    if not path.exists():
        raise GapError(f"Manifest not found: {path}")

    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise GapError(f"Could not read manifest: {e}") from e


# ============================================================================
# §6.2 — value_form / shape_key
# ============================================================================

_PARAM_INDEX: Final[Mapping[tuple[str, str], ParamSpec]] = MappingProxyType({
    (verb, spec.name): spec
    for verb, specs in PARAM_NAMESPACE.items()
    for spec in specs
})

_SUBSCRIPT = re.compile(r"\w+\[[^\]]+\]")
_SLICE = re.compile(r"\w+\[[^\]]*:[^\]]*\]")
_ATTR = re.compile(r"\w+(\.\w+)+")


@dataclass
class GapStats:
    """Mutable accumulator threaded through `value_form` (C1, F5)."""

    unmapped_params: "Counter[tuple[str, str]]" = field(default_factory=Counter)


def value_form(
    verb: str, pname: str, v: Any, stats: GapStats, *, collapse: bool = True
) -> str:
    """Classify one param value into a shape label (§6.2).

    `collapse=True` (default) is the gate-authority reading (C20): int/float
    collapse to "number". `collapse=False` reproduces revision-1's
    `type(v).__name__` behaviour for numbers only, retained as T2's strict
    robustness probe (§6.4) -- everything else about the classification
    (symbolic-resource-ref sub-shapes, list handling, unmapped-param counting)
    is IDENTICAL between the two readings; they differ on numbers alone.
    """
    spec = _PARAM_INDEX.get((verb, pname))  # C1: total lookup, NEVER raises
    if spec is None:
        stats.unmapped_params[(verb, pname)] += 1  # F5: counted, not dropped

    if spec is not None and spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF and isinstance(v, str):
        if _SLICE.fullmatch(v):
            return "slice"  # plate["A1":"A6"]  (BEFORE subscript)
        if _SUBSCRIPT.fullmatch(v):
            return "subscript"  # plate["A1"]
        if "(" in v:
            return "call"
        if _ATTR.fullmatch(v):
            return "attr"  # deck.trash
        if " " in v:
            return "phrase"  # "the same well"
        return "name"  # plate_2_A3

    if isinstance(v, bool):
        return "bool"  # BEFORE the numeric branch -- isinstance(True, int) is True
    if collapse and isinstance(v, (int, float)):
        return "number"  # C20: 10.0 and 20 collapse to the SAME form
    if isinstance(v, list):
        inner = "|".join(sorted({
            value_form(verb, pname, m, stats, collapse=collapse) for m in v
        }))
        return f"list[{inner}]" + ("+multi" if len(v) > 1 else "")
    return type(v).__name__


def shape_key(call: Mapping[str, Any], stats: GapStats, *, collapse: bool = True) -> tuple:
    """A call's full param-shape signature (§6.2). No `verb` parameter -- uses
    `call["name"]`, never a row-level `verb`, which makes the historical bug
    (using the wrong verb source) structurally unrepresentable."""
    return (call["name"], tuple(sorted(
        (p, value_form(call["name"], p, val, stats, collapse=collapse))
        for p, val in call["params"].items()
    )))


def _shape_repr(shape: tuple) -> str:
    """Human-readable string form of a `shape_key()` tuple, for report display."""
    name, params = shape
    return f"{name}(" + ",".join(f"{p}={f}" for p, f in params) + ")"


def _serialize_unmapped(c: "Counter[tuple[str, str]]") -> dict[str, int]:
    """unmapped_params is (verb, pname)-tuple-keyed IN PROCESS, string-keyed ON
    DISK -- json.dumps(sort_keys=True) raises TypeError on tuple keys otherwise."""
    return {f"{verb}|{pname}": n for (verb, pname), n in sorted(c.items())}


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass(frozen=True)
class CellGap:
    """Per-matrix-cell row of `gap_report.json`'s `cells` array (§6.3)."""

    cell_id: str
    verb: str | None
    ambiguity_class: str  # hyphenated (matrix vocabulary)
    examples_per_cell: int
    rows: int
    rows_by_provenance: Mapping[str, int]
    thin: bool
    empty: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "verb": self.verb,
            "ambiguity_class": self.ambiguity_class,
            "examples_per_cell": self.examples_per_cell,
            "rows": self.rows,
            "rows_by_provenance": dict(self.rows_by_provenance),
            "thin": self.thin,
            "empty": self.empty,
        }


@dataclass(frozen=True)
class VerbGap:
    """Per-verb row of `gap_report.json`'s `verbs` array (§6.3)."""

    verb: str
    in_surface: bool
    receiver_type: str
    rows_total: int
    rows_naturalness: int
    distinct_param_shapes_collapsed: int
    distinct_param_shapes_strict: int
    shapes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "verb": self.verb,
            "in_surface": self.in_surface,
            "receiver_type": self.receiver_type,
            "rows_total": self.rows_total,
            "rows_naturalness": self.rows_naturalness,
            "distinct_param_shapes_collapsed": self.distinct_param_shapes_collapsed,
            "distinct_param_shapes_strict": self.distinct_param_shapes_strict,
            "shapes": list(self.shapes),
        }


@dataclass(frozen=True)
class GapResult:
    """Everything `build_report()` and `gate()` need, computed once by `run_gap()`."""

    cells: tuple[CellGap, ...]
    unmatched_cell_keys: Mapping[str, int]
    unmapped_params: Mapping[str, int]
    verbs: tuple[VerbGap, ...]
    recipe_anchor_supply: Mapping[str, int]
    metrics: Mapping[str, Any]
    invariants: Mapping[str, Any]
    corpus_manifest_sha256: str
    recipes_yml_sha256: str


# ============================================================================
# The liquid-handler verb set (§6.4), derived from canonical tables -- never
# hand-listed (the same discipline §7.1 applies to `n_recipes`/the census).
# ============================================================================

_LIQUID_HANDLER_VERBS: Final[frozenset[str]] = frozenset(
    name for name in PHASE2_TOOL_NAMES if TOOL_SCHEMA[name].receiver_type == "liquid_handler"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ============================================================================
# Main computation
# ============================================================================


def run_gap(
    recipes_path: Path | None = None,
    sidecar_path: Path | None = None,
    manifest_path: Path | None = None,
) -> GapResult:
    """Run the full gap computation (§6.1-§6.4).

    Args:
        recipes_path: Path to recipes.yml (default: registry-derived).
        sidecar_path: Path to corpus_p25_sidecar.jsonl (default: repo-root-derived).
        manifest_path: Path to manifest.json (default: repo-root-derived).

    Returns:
        A GapResult with all report content computed.

    Raises:
        recipes.CookbookUnavailable: If the cookbook clone is absent (T3 needs it).
        GapError: On any data-consistency failure (cross-check mismatch, bad matrix,
            bad sidecar, bad manifest).
    """
    if recipes_path is None:
        recipes_path = recipes.default_recipes_path()
    if sidecar_path is None:
        sidecar_path = default_sidecar_path()
    if manifest_path is None:
        manifest_path = default_manifest_path()

    # Clone check FIRST (§7.5): T3 needs recipes.yml, and CookbookUnavailable
    # must propagate uncaught here so gate() can map it to exit 5.
    cookbook = recipes.load_recipes(recipes_path)
    recipes_yml_sha256 = _sha256_file(recipes_path)

    matrix = load_matrix()
    sidecar_rows = load_sidecar_rows(sidecar_path)
    manifest = load_manifest(manifest_path)
    corpus_manifest_sha256 = _sha256_file(manifest_path)

    # ------------------------------------------------------------------
    # Manifest cross-check: recomputed per-class counts must equal
    # manifest.counts.by_class, or the whole report is untrustworthy.
    # ------------------------------------------------------------------
    recomputed_by_class = Counter(row["ambiguity_class"] for row in sidecar_rows)
    manifest_by_class = manifest.get("counts", {}).get("by_class", {})
    if dict(recomputed_by_class) != dict(manifest_by_class):
        raise GapError(
            f"recomputed per-class counts {dict(recomputed_by_class)} != "
            f"manifest.counts.by_class {manifest_by_class}"
        )

    # ------------------------------------------------------------------
    # §6.1: cell attribution
    # ------------------------------------------------------------------
    cells_by_id: dict[str, MatrixCell] = {c.cell_id: c for c in matrix.cells}
    rows_per_cell: dict[str, list[Mapping[str, Any]]] = {cid: [] for cid in cells_by_id}
    unmatched_cell_keys: "Counter[str]" = Counter()

    for row in sidecar_rows:
        key = cell_key(row)
        if key in cells_by_id:
            rows_per_cell[key].append(row)
        else:
            unmatched_cell_keys[key] += 1

    cell_gaps: list[CellGap] = []
    for cell in sorted(matrix.cells, key=lambda c: c.cell_id):
        rows_for_cell = rows_per_cell[cell.cell_id]
        rows_by_provenance = {"coverage": 0, "golden": 0, "naturalness": 0}
        for row in rows_for_cell:
            prov = row.get("provenance")
            if prov in rows_by_provenance:
                rows_by_provenance[prov] += 1
        n_rows = len(rows_for_cell)
        cell_gaps.append(CellGap(
            cell_id=cell.cell_id,
            verb=cell.verb,
            ambiguity_class=cell.ambiguity_class,
            examples_per_cell=cell.examples_per_cell,
            rows=n_rows,
            rows_by_provenance=rows_by_provenance,
            thin=n_rows < cell.examples_per_cell,
            empty=n_rows == 0,
        ))

    # ------------------------------------------------------------------
    # §6.2: per-verb param-shape diversity, over every call in the corpus
    # ------------------------------------------------------------------
    stats = GapStats()  # the ONE stats object whose unmapped_params is reported
    calls_by_verb: dict[str, list[Mapping[str, Any]]] = {}
    naturalness_by_verb: "Counter[str]" = Counter()

    for row in sidecar_rows:
        for call in row.get("calls", []):
            verb = call["name"]
            calls_by_verb.setdefault(verb, []).append(call)
            if row.get("provenance") == "naturalness":
                naturalness_by_verb[verb] += 1

    verb_gaps: list[VerbGap] = []
    for verb in sorted(calls_by_verb):
        calls = calls_by_verb[verb]
        collapsed_shapes = {shape_key(c, stats, collapse=True) for c in calls}
        # Strict pass reuses the same classification logic but must NOT double-count
        # unmapped_params against the report's one authoritative stats object.
        strict_stats = GapStats()
        strict_shapes = {shape_key(c, strict_stats, collapse=False) for c in calls}

        spec_row = TOOL_SCHEMA.get(verb)
        verb_gaps.append(VerbGap(
            verb=verb,
            in_surface=verb in PHASE2_TOOL_NAMES,
            receiver_type=spec_row.receiver_type if spec_row is not None else "",
            rows_total=len(calls),
            rows_naturalness=naturalness_by_verb.get(verb, 0),
            distinct_param_shapes_collapsed=len(collapsed_shapes),
            distinct_param_shapes_strict=len(strict_shapes),
            shapes=tuple(sorted(_shape_repr(s) for s in collapsed_shapes)),
        ))

    verb_gaps_by_name = {vg.verb: vg for vg in verb_gaps}

    # ------------------------------------------------------------------
    # T1 (invariant): LH verbs with zero naturalness rows
    # ------------------------------------------------------------------
    t1_verbs = sorted(
        v for v in _LIQUID_HANDLER_VERBS
        if verb_gaps_by_name.get(v) is None or verb_gaps_by_name[v].rows_naturalness == 0
    )
    t1_holds = (
        len(t1_verbs) == T1_INVARIANT["count"]
        and tuple(t1_verbs) == tuple(sorted(T1_INVARIANT["verbs"]))
    )

    # ------------------------------------------------------------------
    # T2: LH verbs with distinct_param_shapes < T2_shape_floor
    # ------------------------------------------------------------------
    shape_floor = GAP_THRESHOLDS["T2_shape_floor"]
    t2_low_collapsed = [
        v for v in sorted(_LIQUID_HANDLER_VERBS)
        if verb_gaps_by_name.get(v) is None
        or verb_gaps_by_name[v].distinct_param_shapes_collapsed < shape_floor
    ]
    t2_low_strict = [
        v for v in sorted(_LIQUID_HANDLER_VERBS)
        if verb_gaps_by_name.get(v) is None
        or verb_gaps_by_name[v].distinct_param_shapes_strict < shape_floor
    ]

    # ------------------------------------------------------------------
    # T3: out-of-surface anchor supply
    # ------------------------------------------------------------------
    anchor_recipes = [r for r in cookbook if not recipes.in_surface_verbs(r)]
    t3_anchors = len(anchor_recipes)
    t3_chapters = len({r.chapter for r in anchor_recipes})
    recipe_anchor_supply = {
        "out_of_surface_recipes": t3_anchors,
        "distinct_chapters": t3_chapters,
        "in_surface_recipes": len(cookbook) - t3_anchors,
    }

    metrics = {
        "T1_zero_naturalness_lh_verbs": len(t1_verbs),
        "T1_verbs": t1_verbs,
        "T2_low_shape_lh_verbs_collapsed": len(t2_low_collapsed),
        "T2_low_shape_lh_verbs_strict": len(t2_low_strict),
        "T3_out_of_surface_anchors": t3_anchors,
        "T3_chapters": t3_chapters,
        "thin_cells": sum(1 for c in cell_gaps if c.thin),
        "empty_cells": sum(1 for c in cell_gaps if c.empty),
        "thin_cells_note": "REPORTED, NOT GATED — see §6.4",
    }

    invariants = {
        "T1": {
            "expected": T1_INVARIANT["count"],
            "expected_verbs": list(T1_INVARIANT["verbs"]),
            "observed": len(t1_verbs),
            "holds": t1_holds,
        },
    }

    return GapResult(
        cells=tuple(cell_gaps),
        unmatched_cell_keys=dict(sorted(unmatched_cell_keys.items())),
        unmapped_params=_serialize_unmapped(stats.unmapped_params),
        verbs=tuple(verb_gaps),
        recipe_anchor_supply=recipe_anchor_supply,
        metrics=metrics,
        invariants=invariants,
        corpus_manifest_sha256=corpus_manifest_sha256,
        recipes_yml_sha256=recipes_yml_sha256,
    )


# ============================================================================
# Gate decision (§6.4)
# ============================================================================


def _threshold_row(value: int, required: int) -> dict[str, Any]:
    return {"value": value, "required": required, "op": ">=", "pass": value >= required}


def build_report(result: GapResult) -> dict[str, Any]:
    """Build the full `gap_report.json` payload, including the gate verdict (§6.3)."""
    t2_collapsed_row = _threshold_row(
        result.metrics["T2_low_shape_lh_verbs_collapsed"],
        GAP_THRESHOLDS["T2_low_shape_lh_verbs_min"],
    )
    t2_strict_row = _threshold_row(
        result.metrics["T2_low_shape_lh_verbs_strict"],
        GAP_THRESHOLDS["T2_low_shape_lh_verbs_min"],
    )
    t3_anchors_row = _threshold_row(
        result.metrics["T3_out_of_surface_anchors"],
        GAP_THRESHOLDS["T3_out_of_surface_anchors_min"],
    )
    t3_chapters_row = _threshold_row(
        result.metrics["T3_chapters"],
        GAP_THRESHOLDS["T3_distinct_chapters_min"],
    )

    t2_sensitive = t2_collapsed_row["pass"] != t2_strict_row["pass"]
    t3_pass = t3_anchors_row["pass"] and t3_chapters_row["pass"]

    if t2_sensitive:
        decision = "CONTESTED"
    elif t2_collapsed_row["pass"] and t3_pass:
        decision = "PROCEED"
    else:
        decision = "STOP"

    report = {
        "ingest_version": "0.1.0",
        "gap_thresholds_version": GAP_THRESHOLDS_VERSION,
        "matrix_version": "1",
        "corpus_manifest_sha256": result.corpus_manifest_sha256,
        "recipes_yml_sha256": result.recipes_yml_sha256,
        "cells": [c.as_dict() for c in sorted(result.cells, key=lambda c: c.cell_id)],
        "unmatched_cell_keys": dict(result.unmatched_cell_keys),
        "unmapped_params": dict(result.unmapped_params),
        "verbs": [v.as_dict() for v in sorted(result.verbs, key=lambda v: v.verb)],
        "recipe_anchor_supply": dict(result.recipe_anchor_supply),
        "metrics": dict(result.metrics),
        "invariants": dict(result.invariants),
        "gate": {
            "thresholds": dict(GAP_THRESHOLDS),
            "per_threshold": {
                "T2_collapsed": t2_collapsed_row,
                "T2_strict": t2_strict_row,
                "T3_anchors": t3_anchors_row,
                "T3_chapters": t3_chapters_row,
            },
            "t2_normalization_sensitive": t2_sensitive,
            "decision": decision,
            "decision_rule": (
                "PROCEED iff T2_collapsed AND T3 both pass (T1 is an invariant, not "
                "a gate). If T2's collapsed and strict readings disagree on "
                "pass/fail, the decision is CONTESTED (exit 7) — neither PROCEED "
                "nor STOP."
            ),
        },
    }
    return report


def gate(
    recipes_path: Path | None = None,
    sidecar_path: Path | None = None,
    manifest_path: Path | None = None,
    out_dir: Path | None = None,
    out: TextIO = sys.stdout,
) -> int:
    """G1 gate evaluation (§6.4, §9). Never calls sys.exit(); returns int.

    Order:
      1. load_recipes()                      CookbookUnavailable -> exit 5, NO report
      2. load matrix/sidecar/manifest,
         manifest cross-check                GapError            -> exit 1, NO report
      3. build cells/verbs/metrics/T1         (report content computed)
      4. T1 invariant check                   violated -> exit 1, report IS written
      5. T2/T3 gate decision                  PROCEED(0) / STOP(4) / CONTESTED(7)

    Args:
        recipes_path, sidecar_path, manifest_path: input overrides (Python-level
            injection only, matching §5.5's convention -- no CLI flags expose these).
        out_dir: if given, gap_report.json is written here via io.write_artifact.
        out: stream for gate-decision text (§7.4's gate-output exception).

    Returns:
        Exit code: 0 (PROCEED), 1 (T1 invariant violated or measurement error),
        4 (STOP), 5 (cookbook clone absent), or 7 (CONTESTED).
    """
    try:
        result = run_gap(recipes_path, sidecar_path, manifest_path)
    except recipes.CookbookUnavailable as e:
        print(f"Error: {e}", file=out)
        return cli.EXIT_INCONCLUSIVE
    except GapError as e:
        print(f"Error: {e}", file=out)
        return cli.EXIT_MEASUREMENT_ERROR

    report = build_report(result)

    if out_dir is not None:
        io.write_artifact(
            Path(out_dir), "gap_report.json",
            json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        )

    t1 = report["invariants"]["T1"]
    if not t1["holds"]:
        print(
            f"T1 invariant violated: expected count={t1['expected']} "
            f"verbs={t1['expected_verbs']}, observed count={t1['observed']} "
            f"verbs={report['metrics']['T1_verbs']}",
            file=out,
        )
        return cli.EXIT_MEASUREMENT_ERROR

    decision = report["gate"]["decision"]
    print(f"gap gate decision: {decision}", file=out)
    if decision == "CONTESTED":
        return cli.EXIT_CONTESTED
    if decision == "PROCEED":
        return cli.EXIT_OK
    return cli.EXIT_STOP_COVERAGE


# ============================================================================
# CLI entry point (§7.1)
# ============================================================================


def _make_parser() -> cli.IngestArgumentParser:
    parser = cli.IngestArgumentParser(
        prog="python -m ingest.gap",
        description="Coverage-gap report against the verb x ambiguity matrix (G1)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--gate",
        action="store_true",
        help="Gate evaluation: writes gap_report.json to --out (default: training/ingest/out/) and returns 0/1/4/5/7",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory for gap_report.json (default: training/ingest/out/)",
    )
    return parser


def _dispatch_handler(args: Any) -> int:
    if args.gate:
        out_dir = args.out if args.out is not None else default_out_dir()
        return gate(out_dir=out_dir)
    return cli.EXIT_USAGE


if __name__ == "__main__":
    parser = _make_parser()
    sys.exit(cli.run(_dispatch_handler, parser))

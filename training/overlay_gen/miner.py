"""P2.4 corpus miner (spec rev2 §5 P2.4, AC-2.3/2.4.x).

Extracts liquid-handling calls from two sources and normalizes them into the
P2.0 namespace-table shapes:

1. The vendored PLR LH user-guide notebooks
   (``external/pylabrobot/docs/user_guide/00_liquid-handling/**``, 16
   notebooks): code cells parsed with :mod:`ast`, never executed, never
   imported -- ``external/`` is read-only ground truth.
2. The runnable protocol corpus (``praxis/protocol/protocols/*.py``, 6 files):
   ``@protocol_function`` function bodies, likewise AST-parsed.

Filtering policy (both recorded and enforced here):

- Verbs outside the phase-2 surface (TOOL_SCHEMA ``experimental`` phantoms,
  96-channel family, tip-return family, heater-shaker family, state/query
  plumbing, manual channel ops, machine lifecycle) are COUNTED then SKIPPED.
- Notebooks whose content is hardware-context only (Hamilton probing,
  grippers, autoload/barcode reader, surface following, liquid classes, plate
  washer) do not map to simulator-verifiable calls and are SKIPPED whole, with
  the reason recorded.

Pure stdlib + ``coxswain.plr`` tables. Reads notebooks as JSON; reads python
as text. No pylabrobot import, no praxis.backend import.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

from coxswain.plr.param_namespace import ParamKind, params_of
from coxswain.plr.tool_schema import TOOL_SCHEMA

__all__ = [
    "HARDWARE_CONTEXT_ONLY_NOTEBOOKS",
    "MinedCall",
    "MinedExclusion",
    "MineReport",
    "mine_notebooks",
    "mine_protocols",
]

#: Repo root, derived so every path below stays repo-relative.
REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_ROOT = (
    REPO_ROOT / "external" / "pylabrobot" / "docs" / "user_guide" / "00_liquid-handling"
)
PROTOCOL_DIR = REPO_ROOT / "praxis" / "protocol" / "protocols"
GOLDEN_FIXTURE_DIR = REPO_ROOT / "coxswain" / "tests" / "fixtures" / "parsed_calls"

#: Hardware-context-only notebooks: their calls exercise device-specific
#: behavior (probing, grippers, barcode reading, LLD, liquid classes, washer
#: protocols) that has no simulator-verifiable mapping in the phase-2 surface.
#: Keys are paths relative to NOTEBOOK_ROOT; values are recorded reasons.
HARDWARE_CONTEXT_ONLY_NOTEBOOKS: dict[str, str] = {
    "hamilton-star/y-probing.ipynb": "Hamilton y-arm probing hardware context",
    "hamilton-star/z-probing.ipynb": "Hamilton z-probing hardware context",
    "hamilton-star/core-grippers.ipynb": "Hamilton gripper hardware context",
    "hamilton-star/autoload_and_1d_barcode_reader.ipynb": "autoload/1D barcode reader hardware context",
    "hamilton-star/surface-following.ipynb": "liquid-surface-following (LLD) hardware context",
    "hamilton-star/hamilton-liquid-classes.ipynb": "Hamilton liquid-class configuration context",
    "plate-washing/biotek-el406.ipynb": "Biotek EL406 plate-washer hardware context",
}

#: Vendored-but-non-surface verbs that appear in the LH corpus, with the
#: recorded exclusion reason each (mirrors param_namespace.py's include/
#: exclude record). Extraction counts these calls, then drops them.
NON_SURFACE_VERB_REASONS: dict[str, str] = {
    # Phantoms vs vendored HEAD dd79c4c89 (recon §1.4).
    "mix": "phantom verb (no vendored method); upstream models via aspirate/dispense mix kwarg",
    "blow_out": "phantom verb; modeled via blow_out_air_volume kwargs",
    "touch_tip": "phantom verb vs vendored HEAD",
    "dispense_to_waste": "phantom verb vs vendored HEAD",
    # Heater-shaker receiver: no praxis backend wiring yet (defender R5).
    "set_temperature": "heater_shaker excluded until backend exists",
    "shake": "heater_shaker excluded until backend exists",
    "stop_shaking": "heater_shaker excluded until backend exists",
    # 96-channel family: wholesale different semantics, excluded unless promoted.
    "pick_up_tips96": "96-channel family excluded",
    "drop_tips96": "96-channel family excluded",
    "aspirate96": "96-channel family excluded",
    "dispense96": "96-channel family excluded",
    "return_tips96": "96-channel family excluded",
    # Tip-return family: implicit head state, hostile to confirm-card UX.
    "return_tips": "tip-return family excluded (implicit head state)",
    # Channel-to-channel maintenance op.
    "move_tips": "niche maintenance op, not user-facing",
    # State/query surface: kernel-internal plumbing.
    "probe_tip_inventory": "state/query surface, not a copilot verb",
    "consolidate_tip_inventory": "state/query surface, not a copilot verb",
    "serialize_state": "kernel-internal plumbing",
    "load_state": "kernel-internal plumbing",
    "update_head_state": "kernel-internal plumbing",
    "get_mounted_tips": "kernel-internal plumbing",
    # Manual channel operation: maintenance context, not copilot-emittable.
    "prepare_for_manual_channel_operation": "manual channel ops are maintenance context",
    "move_channel_z": "manual channel ops are maintenance context",
    "move_channel_x": "manual channel ops are maintenance context",
    "move_channel_y": "manual channel ops are maintenance context",
    # Machine lifecycle around the calls, not themselves copilot verbs.
    "setup": "machine lifecycle, not a copilot verb",
    "stop": "machine lifecycle, not a copilot verb",
    "summary": "introspection, not a copilot verb",
    "home": "machine lifecycle, not a copilot verb",
}

_KNOWN_VERBS: frozenset[str] = frozenset(TOOL_SCHEMA) | frozenset(NON_SURFACE_VERB_REASONS)

_UNEXTRACTABLE = object()  # sentinel for args we refuse to guess at


@dataclass(frozen=True)
class MinedCall:
    """One phase-2-surface call, normalized to namespace-table shapes.

    ``params`` keys are schema-side names from PARAM_NAMESPACE; symbolic
    resource refs carry their verbatim source expression as the string value
    (grounding happens downstream, never in this generator)."""

    name: str
    receiver_type: str
    params: dict
    source: str  # repo-relative notebook or protocol path
    origin: str  # source + "#cell<N>" or "::<func>"
    dropped_kwargs: tuple[str, ...] = ()  # expert kwargs outside the surface

    def call_dict(self) -> dict:
        return {
            "name": self.name,
            "receiver_type": self.receiver_type,
            "params": dict(self.params),
        }


@dataclass(frozen=True)
class MinedExclusion:
    """A recognized but non-surface call, kept as an auditable count."""

    verb: str
    reason: str
    source: str
    origin: str


@dataclass
class SourceStats:
    cells_or_functions: int = 0
    kept_calls: list[MinedCall] = field(default_factory=list)
    exclusions: list[MinedExclusion] = field(default_factory=list)
    unextractable: int = 0  # surface calls w/ args we could not normalize
    parse_errors: int = 0
    skip_reason: str | None = None


# ---------------------------------------------------------------------------
# AST value extraction
# ---------------------------------------------------------------------------


def _literal_value(node: ast.AST, module_src: str):
    """Best-effort normalization of an argument expression.

    Pure literals / lists of literals become real values; references
    (subscripts like ``plate['A1']``, names like ``tube``, computed volumes
    like ``volume_ul * 0.8``) keep their verbatim source segment as an opaque
    string ref. Returns the _UNEXTRACTABLE sentinel only when even the source
    segment is unavailable."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _literal_value(node.operand, module_src)
        if isinstance(inner, (int, float)) and not isinstance(inner, bool):
            return -inner
        return inner
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_literal_value(elt, module_src) for elt in node.elts]
        if any(v is _UNEXTRACTABLE for v in values):
            return _UNEXTRACTABLE
        return values
    segment = ast.get_source_segment(module_src, node)
    if segment is None:
        return _UNEXTRACTABLE
    return segment.strip()


def _to_cardinality(value, cardinality: str):
    """Normalize an extracted value to the namespace row's declared shape."""
    if value is _UNEXTRACTABLE:
        return value
    if cardinality == "list":
        return value if isinstance(value, list) else [value]
    if isinstance(value, list) and len(value) == 1:
        return value[0]  # scalar param given a 1-list upstream (e.g. dispense([tube]))
    return value


def _param_positions(tool_name: str) -> tuple[list[tuple[int, str]], dict[str, str]]:
    """Positional slots (index -> schema name) + plr-arg -> schema-name map,
    both derived from PARAM_NAMESPACE declaration order."""
    positional: list[tuple[int, str]] = []
    kwarg_map: dict[str, str] = {}
    index = 0
    for spec in params_of(tool_name):
        if spec.plr_arg is None:
            continue  # phrase-only/dispatch-inert metadata takes no position
        positional.append((index, spec.name))
        kwarg_map[spec.plr_arg] = spec.name
        index += 1
    return positional, kwarg_map


class _CallExtractor(ast.NodeVisitor):
    def __init__(self, module_src: str, source: str, origin_prefix: str) -> None:
        self.module_src = module_src
        self.source = source
        self.origin_prefix = origin_prefix
        self.stats = SourceStats()

    # -- visitors -------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _KNOWN_VERBS:
            self._handle(func.attr, node, f"{self.origin_prefix}@{node.lineno}")
        self.generic_visit(node)

    # -- extraction -----------------------------------------------------------

    def _handle(self, verb: str, node: ast.Call, origin: str) -> None:
        if verb in NON_SURFACE_VERB_REASONS:
            self.stats.exclusions.append(
                MinedExclusion(
                    verb=verb,
                    reason=NON_SURFACE_VERB_REASONS[verb],
                    source=self.source,
                    origin=origin,
                )
            )
            return

        positional_slots, kwarg_map = _param_positions(verb)
        params: dict = {}
        dropped: list[str] = []
        ok = True

        for i, arg in enumerate(node.args):
            slot = next((name for idx, name in positional_slots if idx == i), None)
            if slot is None:
                # More positionals than namespace rows: off-template usage;
                # treat like an unknown kwarg for accounting purposes.
                dropped.append(f"<positional {i}>")
                continue
            spec = next(ps for ps in params_of(verb) if ps.name == slot)
            value = _to_cardinality(_literal_value(arg, self.module_src), spec.cardinality)
            if value is _UNEXTRACTABLE:
                ok = False
                continue
            params[slot] = value

        for kw in node.keywords:
            if kw.arg is None:  # **kwargs spread: cannot be normalized
                ok = False
                continue
            schema_name = kwarg_map.get(kw.arg)
            if schema_name is None:
                # Expert kwarg outside the phase-2 generation surface
                # (offsets, use_channels, mix lists, flow rates...): recorded,
                # dropped, dispatch passes vendor defaults per P2.0 scope.
                dropped.append(kw.arg)
                continue
            spec = next(ps for ps in params_of(verb) if ps.name == schema_name)
            value = _to_cardinality(_literal_value(kw.value, self.module_src), spec.cardinality)
            if value is _UNEXTRACTABLE:
                ok = False
                continue
            params[schema_name] = value

        if not ok:
            self.stats.unextractable += 1
            return

        receiver_type = TOOL_SCHEMA[verb].receiver_type
        # Symbolic rows must be string refs; literal numeric coercion keeps
        # e.g. vols=[100] (int from the notebook) as-is -- the dispatcher and
        # later verification own numeric canonicalization.
        for ps in params_of(verb):
            if ps.kind is ParamKind.SYMBOLIC_RESOURCE_REF and ps.name in params:
                if isinstance(params[ps.name], list):
                    params[ps.name] = [str(v) for v in params[ps.name]]
                else:
                    params[ps.name] = str(params[ps.name])

        self.stats.kept_calls.append(
            MinedCall(
                name=verb,
                receiver_type=receiver_type,
                params=params,
                source=self.source,
                origin=origin,
                dropped_kwargs=tuple(dropped),
            )
        )


def _extract_from_code(code: str, source: str, origin_prefix: str) -> SourceStats:
    stats = SourceStats()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        stats.parse_errors += 1
        return stats
    extractor = _CallExtractor(code, source, origin_prefix)
    extractor.visit(tree)
    return extractor.stats


# ---------------------------------------------------------------------------
# Notebook mining
# ---------------------------------------------------------------------------


def mine_notebooks(notebook_root: Path = NOTEBOOK_ROOT) -> dict[str, SourceStats]:
    """Walk all LH notebooks under ``notebook_root``. Hardware-context-only
    notebooks are reported skipped without parsing."""
    reports: dict[str, SourceStats] = {}
    for path in sorted(notebook_root.rglob("*.ipynb")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        nb_rel_key = path.relative_to(notebook_root).as_posix()
        if nb_rel_key in HARDWARE_CONTEXT_ONLY_NOTEBOOKS:
            stats = SourceStats(skip_reason=HARDWARE_CONTEXT_ONLY_NOTEBOOKS[nb_rel_key])
            reports[rel] = stats
            continue
        stats = SourceStats()
        try:
            nb = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stats.parse_errors += 1
            reports[rel] = stats
            continue
        for i, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            code = "".join(cell.get("source", []))
            # Strip IPython magics/shell escapes so ast.parse can handle the cell.
            lines = [ln for ln in code.splitlines() if not ln.lstrip().startswith(("%", "!"))]
            cell_stats = _extract_from_code(
                "\n".join(lines), rel, f"{rel}#cell{i}"
            )
            stats.cells_or_functions += 1
            stats.kept_calls.extend(cell_stats.kept_calls)
            stats.exclusions.extend(cell_stats.exclusions)
            stats.unextractable += cell_stats.unextractable
            stats.parse_errors += cell_stats.parse_errors
        reports[rel] = stats
    return reports


# ---------------------------------------------------------------------------
# Protocol mining
# ---------------------------------------------------------------------------


def _protocol_decorator_meta(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    """Pull name/description out of @protocol_function(...) kwargs, if present."""
    meta: dict[str, str] = {}
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        name = getattr(target, "id", getattr(target, "attr", ""))
        if name != "protocol_function":
            continue
        if isinstance(dec, ast.Call):
            for kw in dec.keywords:
                if kw.arg in ("name", "description") and isinstance(kw.value, ast.Constant):
                    meta[kw.arg] = str(kw.value.value)
    return meta


def mine_protocols(protocol_dir: Path = PROTOCOL_DIR) -> dict[str, SourceStats]:
    """Mine LH/reader calls from every runnable ``@protocol_function`` module."""
    reports: dict[str, SourceStats] = {}
    for path in sorted(protocol_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue  # package marker, not runnable corpus
        rel = path.relative_to(REPO_ROOT).as_posix()
        src = path.read_text(encoding="utf-8")
        stats = SourceStats()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            stats.parse_errors += 1
            reports[rel] = stats
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            meta = _protocol_decorator_meta(node)
            if not meta and not any(
                isinstance(d, ast.Name) and d.id == "protocol_function"
                for d in node.decorator_list
            ):
                continue  # only @protocol_function bodies are runnable corpus
            stats.cells_or_functions += 1
            suffix = f"::{meta.get('name', node.name)}"
            fn_stats = _extract_from_code(
                ast.get_source_segment(src, node) or "", rel, rel + suffix
            )
            stats.kept_calls.extend(fn_stats.kept_calls)
            stats.exclusions.extend(fn_stats.exclusions)
            stats.unextractable += fn_stats.unextractable
            stats.parse_errors += fn_stats.parse_errors
        reports[rel] = stats
    return reports


def iter_kept_calls(reports: dict[str, SourceStats]):
    """Flatten kept calls out of mine_* output in deterministic order."""
    for source in sorted(reports):
        yield from reports[source].kept_calls

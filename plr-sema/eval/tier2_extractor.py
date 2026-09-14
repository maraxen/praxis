"""Tier 2a (spec 260903 §12.4.1, backlog #4880): the bytecode differential
against tier 1.

For every corpus row tier 1 EXECUTES (same class/precondition gating as
``oracle_replay.py``'s own row iteration -- ``--sidecar``'s
``ambiguity_class``/``provenance`` join, line-exact primary + content-digest
fallback), this script:

1. runs the row through :func:`oracle_common.run_runtime` (tier 1's own
   runtime side) to get the PLR-named ``PlanResult.kwargs`` and the real
   PLR resource types the runtime bound;
2. lowers tier 1's own call sequence via
   :func:`oracle_common.lower_row_calls` (the SAME function
   ``oracle_replay.py``'s tier-1 static side uses, §12.1.6's ``setup()``
   prepend included) -- this is ``bc1``;
3. renders the SAME call sequence to a minimal Python protocol
   (:func:`render_protocol.render_protocol`);
4. runs praxis's extractor over that rendered source OUT OF PROCESS
   (``extract_runner.py``, a subprocess -- AC-12.16) and lowers the
   resulting graph payload via ``plr_sema.check.ir.lower_graph`` -- this is
   ``bc2``;
5. compares ``bc1`` and ``bc2`` as BYTECODE (not verdicts), instruction by
   instruction, and classifies every divergence into one of four causes
   (§12.4.1's table): ``extractor``, ``renderer``, ``grammar``, ``reset``.

The gate (AC-12.15) is **zero extractor-cause divergences**; renderer/
grammar/reset counts are published, not gated, per the spec's own honest-
residual argument (§12.4.1's closing paragraphs).

This module -- like ``oracle_common.py`` and ``oracle_replay.py`` -- never
imports ``praxis`` (AC-12.16); the only praxis import in this codepath
lives inside ``extract_runner.py``'s ``main()``, run as a subprocess.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVAL_DIR = Path(__file__).resolve().parent
_BOOTSTRAP_FLAG = "PLR_SEMA_TIER2_BOOTSTRAPPED"


def _bootstrap_into_training_env() -> None:
    """Same fix as ``oracle_replay.py``'s own bootstrap (260902,
    ``ebd6b76d``'s pattern): re-exec under the workspace venv so
    ``verify``/``training``/``coxswain``/``overlay_gen`` are importable,
    falling back to ``uv run --offline --no-sync``. Duplicated rather than
    imported from ``oracle_replay`` because that module's OWN bootstrap
    hardcodes ``Path(__file__)`` to re-exec ITSELF, not this script -- an
    ``import oracle_replay`` before this guard runs would re-exec into
    ``oracle_replay.py``, discarding this script's own argv.
    """
    if os.environ.get(_BOOTSTRAP_FLAG):
        sys.stderr.write(
            "tier2_extractor: 'verify' still not importable after re-exec; "
            "run `uv sync` in the repo first\n"
        )
        raise SystemExit(3)
    env = dict(os.environ, **{_BOOTSTRAP_FLAG: "1"})
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python"
    script_args = sys.argv[1:]
    if venv_python.is_file():
        argv = [str(venv_python), str(Path(__file__).resolve()), *script_args]
        os.execve(str(venv_python), argv, env)
    uv = shutil.which("uv")
    if uv is None:
        sys.stderr.write("tier2_extractor: neither .venv/bin/python nor uv found\n")
        raise SystemExit(3)
    argv = [uv, "run", "--offline", "--no-sync", "python",
            str(Path(__file__).resolve()), *script_args]
    os.chdir(_REPO_ROOT)
    os.execve(uv, argv, env)


if importlib.util.find_spec("verify") is None:
    _bootstrap_into_training_env()

import argparse
import collections
import dataclasses
import json
import logging
import time
from collections.abc import Mapping
from typing import Any

sys.path.insert(0, str(_EVAL_DIR))

from oracle_common import (  # noqa: E402
    DEFAULT_CONTRACTS,
    calls_from_plr_kwargs,
    content_digest,
    extract_first_call,
    lower_row_calls,
    param_names_from_contracts,
    resources_from_example,
    row_to_verifier_inputs,
    run_runtime,
)
from render_protocol import classify_residual_reason, render_protocol  # noqa: E402

log = logging.getLogger(__name__)

_EXTRACT_RUNNER = _EVAL_DIR / "extract_runner.py"
_FUNCTION_NAME = "protocol"

# T16d (#4879)/#4939 gating vocabulary, mirrored from oracle_replay.py: a
# row's ambiguity_class must be "clean_parse" to be executable ground
# truth at all -- tier 2a only has anything to compare against tier 1 for
# rows tier 1 itself executed.
_EXECUTABLE_AMBIGUITY_CLASS = "clean_parse"


def _lazy_ir():
    sys.path.insert(0, str(_REPO_ROOT / "plr-sema" / "src"))
    from plr_sema.check import ir as _ir

    return _ir


# ---------------------------------------------------------------------------
# Sidecar join -- mirrors oracle_replay.py's main(): line-exact primary
# (corpus_p25.jsonl / corpus_p25_sidecar.jsonl are companion files written
# by the same assembler pass, line i of one is always line i of the other),
# content-digest fallback for files that are not line-paired.
# ---------------------------------------------------------------------------


def _load_sidecar(path: str | None) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    by_digest: dict[str, dict[str, Any]] = {}
    if not path:
        return rows, by_digest
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            srow = json.loads(line)
            rows.append(srow)
            utt = srow.get("utterance", "")
            raw_calls = srow.get("calls") or []
            call = (
                {"name": raw_calls[0].get("name", ""), "params": raw_calls[0].get("params", {})}
                if raw_calls
                else None
            )
            digest = content_digest(utt, call)
            by_digest.setdefault(digest, srow)
    return rows, by_digest


def _sidecar_for(
    line_no: int, row: dict[str, Any], *, exact_eligible: bool,
    sidecar_rows: list[dict[str, Any]], sidecar_by_digest: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not sidecar_rows:
        return None
    if exact_eligible and 1 <= line_no <= len(sidecar_rows):
        return sidecar_rows[line_no - 1]
    utterance, call = extract_first_call(row)
    return sidecar_by_digest.get(content_digest(utterance, call))


# ---------------------------------------------------------------------------
# The differential
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Divergence:
    call_index: int
    field: str
    cause: str
    tier1: Any
    tier2: Any
    detail: str


def _extract_calls(bc, ir_mod) -> list[dict[str, Any]]:
    """[{method, receiver, receiver_type, kwargs, widens}] in call-list
    order (position == call_index in the ``calls`` list both lowerings
    were built from). ``RESOURCE`` declarations are dropped entirely --
    tier 1's ``lower_calls`` always declares a ``RESOURCE`` for ``lh``
    (present in ``resources_from_example``'s dict by construction), while
    tier 2's ``lower_graph`` never does (the extractor's own
    ``_initialize_resources_from_params`` only registers PLR *resource*
    parameter types -- never the ``LiquidHandler`` receiver itself, which
    is not a ``pylabrobot.resources.Resource``) -- a structural asymmetry
    between what each lowering considers a "resource", not an
    extractor/renderer/grammar/reset divergence over the SAME execution.

    A ``WIDEN(reason="depends_on_params")`` immediately before a ``CALL``
    is dropped from that call's ``widens`` list for the same reason:
    ``depends_on_params`` is an ``OperationNode``-only (graph) field --
    ``lower_calls`` has no slot for it and structurally can never emit
    this widen, regardless of how correctly either side resolved the
    call's actual argument values, so its presence-only-on-tier-2 is not
    informative about which side is wrong.
    """
    out: list[dict[str, Any]] = []
    pending_widens: list[str] = []
    for instr in bc.instructions:
        if isinstance(instr, ir_mod.Resource):
            continue
        if isinstance(instr, ir_mod.Widen):
            if instr.reason != "depends_on_params":
                pending_widens.append(instr.reason)
            continue
        if isinstance(instr, ir_mod.Call):
            out.append({
                "method": instr.method,
                "receiver": instr.receiver,
                "receiver_type": instr.receiver_type,
                "kwargs": {k: ir_mod.value_to_json(v) for k, v in instr.kwargs.items()},
                "widens": sorted(pending_widens),
            })
            pending_widens = []
        # LOOP/BRANCH/ELSE/END: not expected on a straight-line tier-1/
        # tier-2a row (§12.4.2 -- "the corpus is straight-line"); if one
        # ever appears it is simply absent from this CALL-only substream,
        # which will show up as a length mismatch below rather than a
        # silent skip.
    return out


def _canonicalize_receiver(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remap every ``receiver`` slot int to a canonical id assigned by
    order of first appearance WITHIN this call list (§12.4.1: "receiver
    slot identity up to renaming"). Every row in this corpus is
    single-receiver (``lh``), so this in practice always assigns canonical
    ``0`` on both sides -- kept for the (untested-in-corpus, but real)
    multi-receiver case rather than hardcoding that assumption.

    ``kwargs`` values are NOT touched here -- see this module's own
    "kwargs values with Ref resolved by resource NAME not slot number"
    handling (:func:`_lower_arg_value_by_name`/
    :func:`_tier2_kwargs_by_name`, wired in by :func:`compare_bytecode`):
    a ``Ref.slot`` int is assigned by ORDER OF FIRST APPEARANCE ACROSS ALL
    kwargs in a lowering, so a kwarg the renderer had to DROP (a residual)
    shifts the slot of every kwarg lowered after it, on the side that
    dropped it -- an artefact of first-appearance slot assignment, not a
    real divergence (found live, 260903 full-corpus run: a dropped
    ``move_plate.resource`` kwarg -- an unrenderable hyphenated resource
    name -- shifted `move_plate.to`'s canonical slot by one, producing a
    false-positive "extractor" divergence on a kwarg that was never
    itself wrong). Comparing kwargs by NAME instead sidesteps this
    entirely, which is also the letter of the spec's own instruction.
    """
    remap: dict[int, int] = {}

    def canon(slot: int) -> int:
        return remap.setdefault(slot, len(remap))

    out = []
    for d in calls:
        nd = dict(d)
        nd["receiver"] = canon(d["receiver"])
        out.append(nd)
    return out


def _self_attr_name(node: Any) -> str | None:
    import ast

    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    ):
        return f"self.{node.attr}"
    return None


def _value_from_pyobj_by_name(x: Any) -> dict[str, Any]:
    if isinstance(x, (list, tuple)):
        return {"k": "seq", "items": [_value_from_pyobj_by_name(i) for i in x]}
    if x is None or isinstance(x, (bool, int, float, str)):
        return {"k": "lit", "v": x}
    return {"k": "top"}


def _lower_ast_node_by_name(
    node: Any, resources_payload: dict[str, Any], sanitized_to_original: Mapping[str, str],
) -> dict[str, Any]:
    import ast

    if isinstance(node, ast.Name) and node.id in resources_payload:
        return {"k": "ref", "name": sanitized_to_original.get(node.id, node.id), "cell": None}
    self_attr = _self_attr_name(node)
    if self_attr is not None and self_attr in resources_payload:
        return {"k": "ref", "name": sanitized_to_original.get(self_attr, self_attr), "cell": None}
    if isinstance(node, ast.Subscript):
        base = node.value
        idx = node.slice
        base_name: str | None = None
        if isinstance(base, ast.Name) and base.id in resources_payload:
            base_name = base.id
        else:
            base_self_attr = _self_attr_name(base)
            if base_self_attr is not None and base_self_attr in resources_payload:
                base_name = base_self_attr
        if base_name is not None and isinstance(idx, ast.Constant) and isinstance(idx.value, str):
            return {"k": "ref", "name": sanitized_to_original.get(base_name, base_name), "cell": idx.value}
        return {"k": "top"}
    if isinstance(node, (ast.List, ast.Tuple)):
        return {
            "k": "seq",
            "items": [
                _lower_ast_node_by_name(elt, resources_payload, sanitized_to_original) for elt in node.elts
            ],
        }
    try:
        literal = ast.literal_eval(node)
    except Exception:
        return {"k": "top"}
    return _value_from_pyobj_by_name(literal)


def _lower_arg_value_by_name(
    raw: Any, resources_payload: dict[str, Any], sanitized_to_original: Mapping[str, str],
) -> dict[str, Any]:
    """One raw ``OperationNode.arguments`` VALUE (a source-text string, per
    the graph wire format) -> IR-value-JSON with a ``Ref`` resolved by
    resource NAME rather than a lowering-assigned slot int.

    ``sanitized_to_original`` (backlog #4949, 260903 tier2a followup) is
    ``render_protocol.RenderedProtocol.name_map`` INVERTED
    (:func:`compare_bytecode`'s own job) -- the rendered SOURCE only ever
    names a resource by its sanitised parameter identifier (e.g.
    ``plate_carrier_1`` for the runtime name ``"plate_carrier-1"``), so
    every ``Ref`` this function resolves off that source needs translating
    back to the ORIGINAL runtime name before it can be compared against
    tier 1's own (never-sanitised) ``Ref.name``.

    A deliberate, MINIMAL mirror of ``plr_sema.check.ir.lower_graph``'s own
    internal ``_lower_ast_node``/``lower_arg_value`` (read, not imported --
    those are module-private and slot-keyed by construction, and importing
    private names across a package boundary for a name-keyed variant would
    be more fragile than this ~20-line, self-contained copy). If
    ``lower_graph``'s value grammar ever changes, this needs the same
    change; there is no structural link enforcing that today, which is the
    honest cost of comparing at the wire level as the spec directs
    (§12.4.1: "kwargs values with Ref resolved by resource NAME not slot
    number").
    """
    if not isinstance(raw, str):
        return _value_from_pyobj_by_name(raw)
    import ast

    try:
        node = ast.parse(raw, mode="eval").body
    except SyntaxError:
        return {"k": "top"}
    return _lower_ast_node_by_name(node, resources_payload, sanitized_to_original)


def _tier2_kwargs_by_name(
    payload: dict[str, Any], *, sanitized_to_original: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """``[{kwarg_name: value-json-by-name}, ...]`` per REAL (non-``region``)
    operation, in payload order. Payload order == execution order == the
    order :func:`_extract_calls` walks ``bc2``'s own ``CALL`` instructions
    in, 1:1 -- true for every tier-2a rendered protocol (straight-line,
    §12.4.2: "the corpus is straight-line", so no region reordering is
    possible on this path at all).
    """
    resources_payload = dict(payload.get("resources") or {})
    reverse_map = sanitized_to_original or {}
    out: list[dict[str, Any]] = []
    for op in payload.get("operations") or []:
        if op.get("node_type") == "region":
            continue
        args = op.get("arguments") or {}
        out.append({
            k: _lower_arg_value_by_name(v, resources_payload, reverse_map) for k, v in args.items()
        })
    return out


def _diff_call(d1: dict[str, Any], d2: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    diffs: list[tuple[str, Any, Any]] = []
    for field in ("method", "receiver", "receiver_type", "widens"):
        v1, v2 = d1.get(field), d2.get(field)
        if v1 != v2:
            diffs.append((field, v1, v2))
    kw1, kw2 = d1.get("kwargs", {}), d2.get("kwargs", {})
    for k in sorted(set(kw1) | set(kw2)):
        v1 = kw1.get(k, "<absent>")
        v2 = kw2.get(k, "<absent>")
        if v1 != v2:
            diffs.append((f"kwargs.{k}", v1, v2))
    return diffs


def _classify(
    call_index: int, field: str, v1: Any, v2: Any, *,
    residual_kwargs: set[tuple[int, str]],
) -> str:
    """§12.4.1's table, in priority order:

    1. ``reset`` -- a mismatch at call_index 0's own identity (the
       prepended ``setup()`` must agree on both sides -- AC-12.15's
       directional half).
    2. ``renderer`` -- this exact (call_index, kwarg) was already flagged
       unrenderable by :func:`render_protocol.render_protocol` for this
       row -- the residual is EXPECTED, not discovered by the diff.
    3. ``grammar`` -- tier 2 resolved a value to ``Top`` where tier 1 has a
       real value (``Ref``/``Lit``/``Seq``) -- ``lower_graph``'s own
       value-grammar gap (§12.2.5's closed case: ``self.<attr>``
       resolution; any live survivor here is exactly what this increment
       exists to catch).
    4. ``extractor`` -- the default: the extractor emitted/omitted/
       misread something the rendered source plainly says.
    """
    if call_index == 0 and field in ("method", "__missing__"):
        return "reset"
    kwarg = field.split(".", 1)[1] if field.startswith("kwargs.") else None
    if kwarg is not None and (call_index, kwarg) in residual_kwargs:
        return "renderer"
    if (
        kwarg is not None
        and isinstance(v2, dict) and v2.get("k") == "top"
        and not (isinstance(v1, dict) and v1.get("k") == "top") and v1 != "<absent>"
    ):
        return "grammar"
    return "extractor"


def _seq_len(value: Any) -> int | None:
    """``len(items)`` of a ``{"k":"seq","items":[...]}`` value-JSON dict,
    else ``None`` (not a ``Seq`` at all, e.g. ``Top`` or a bare ``Ref``).
    """
    if isinstance(value, dict) and value.get("k") == "seq":
        return len(value.get("items", []))
    return None


def _overlay_name_kwargs(calls: list[dict[str, Any]], by_index_kwargs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace each call dict's slot-keyed ``kwargs`` with the NAME-keyed
    version at the same position, when one exists (positional alignment is
    established by :func:`_tier1_wire_kwargs`/:func:`_tier2_kwargs_by_name`'s
    own docstrings). Falls back to the original (slot-keyed) ``kwargs`` when
    the by-index list runs short -- defensive only; not expected to trigger
    for a region-free tier-2a render, where the two lists are always the
    same length as the CALL-instruction stream they were built alongside.
    """
    out = []
    for i, d in enumerate(calls):
        nd = dict(d)
        if i < len(by_index_kwargs):
            nd["kwargs"] = by_index_kwargs[i]
        out.append(nd)
    return out


def compare_bytecode(
    bc1, bc2, ir_mod, *, residuals: list, source_lines: dict[int, int],
    tier1_wire_calls: list[dict[str, Any]], tier2_payload: dict[str, Any],
    resource_name_map: Mapping[str, str] | None = None,
) -> list[Divergence]:
    """``tier1_wire_calls`` is :func:`oracle_common.calls_from_plr_kwargs`'s
    own output (already NAME-keyed ``ref`` wire JSON -- no transformation
    needed); ``tier2_payload`` is the raw extracted graph payload (before
    ``lower_graph``'s own slot resolution). Both are used ONLY to replace
    each compared call's ``kwargs`` with a NAME-resolved view
    (:func:`_overlay_name_kwargs`) -- structural fields (``method``,
    ``receiver_type``, ``widens``) still come from the real ``Bytecode``
    (``bc1``/``bc2``), matching the spec's "compare the canonical
    bytecode" instruction for everything except the one field
    (§12.4.1: "receiver slot identity up to renaming", "kwargs values
    with Ref resolved by resource NAME not slot number") it names an
    explicit exception for.

    ``resource_name_map`` (backlog #4949, 260903 tier2a followup) is
    ``render_protocol.RenderedProtocol.name_map`` -- ``{original_name:
    sanitised_name}``. Inverted here (sanitised -> original) and threaded
    into :func:`_tier2_kwargs_by_name` so a tier-2 ``Ref`` resolved off the
    RENDERED source (which only ever spells a resource by its sanitised
    parameter identifier, e.g. ``plate_carrier_1``) is compared against
    tier 1's ``Ref.name`` (which is always the real, unsanitised runtime
    name, e.g. ``"plate_carrier-1"``) under the SAME name.
    """
    calls1 = _canonicalize_receiver(_extract_calls(bc1, ir_mod))
    calls2 = _canonicalize_receiver(_extract_calls(bc2, ir_mod))
    tier1_kwargs_by_index = [c.get("kwargs") or {} for c in tier1_wire_calls]
    sanitized_to_original = {v: k for k, v in (resource_name_map or {}).items()}
    tier2_kwargs_by_index = _tier2_kwargs_by_name(tier2_payload, sanitized_to_original=sanitized_to_original)
    calls1 = _overlay_name_kwargs(calls1, tier1_kwargs_by_index)
    calls2 = _overlay_name_kwargs(calls2, tier2_kwargs_by_index)
    residual_kwargs = {(r.call_index, r.kwarg) for r in residuals}
    n = max(len(calls1), len(calls2))
    out: list[Divergence] = []
    for i in range(n):
        d1 = calls1[i] if i < len(calls1) else None
        d2 = calls2[i] if i < len(calls2) else None
        if d1 is None or d2 is None:
            cause = _classify(i, "__missing__", d1, d2, residual_kwargs=residual_kwargs)
            out.append(Divergence(
                call_index=i, field="__missing__", cause=cause,
                tier1=d1, tier2=d2,
                detail=f"line {source_lines.get(i)}: call present on only one side "
                       f"({'tier1' if d2 is None else 'tier2'})",
            ))
            continue
        for field, v1, v2 in _diff_call(d1, d2):
            cause = _classify(i, field, v1, v2, residual_kwargs=residual_kwargs)
            out.append(Divergence(
                call_index=i, field=field, cause=cause, tier1=v1, tier2=v2,
                detail=f"line {source_lines.get(i)}: {d1.get('method')} field {field!r} "
                       f"tier1={v1!r} tier2={v2!r}",
            ))
    return out


# ---------------------------------------------------------------------------
# Per-row pipeline
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class RowOutcome:
    record_id: str
    source_file: str
    line: int
    status: str  # "compared" | "no_call" | "skipped" | "setup_error" | "harness_error"
    agreeing: bool = True
    divergences: list[Divergence] = dataclasses.field(default_factory=list)
    n_calls_tier1: int = 0
    residual_count: int = 0
    #: One :func:`render_protocol.classify_residual_reason` label per
    #: residual this row's :func:`render_protocol.render_protocol` call
    #: emitted -- ``main()`` sums these into the report's
    #: ``renderer_residual_by_class`` (backlog #4949, 260903 tier2a
    #: followup).
    residual_classes: list[str] = dataclasses.field(default_factory=list)
    detail: str | None = None
    rendered_source: str | None = None
    #: AC-12.15's directional half: True iff THIS row's own bc1/bc2 both
    #: open with a `setup` CALL and (if either side has a `pick_up_tips`
    #: CALL) the `tip_spots` kwarg is a `Seq` of the SAME length on both
    #: sides. `None` when the row has no `pick_up_tips` CALL to check.
    directional_ok: bool | None = None


def run_row(
    row: dict[str, Any], source_file: str, line_no: int,
    param_names, ir_mod, *, ambiguity_class: str | None, provenance: str | None,
    cache_dir: Path, runner_python: str,
) -> RowOutcome:
    call_sequence, intent_record, deck_layout, skip_reason, no_call_reason = row_to_verifier_inputs(
        row, source_file=Path(source_file).stem, line=line_no,
        ambiguity_class=ambiguity_class, provenance=provenance,
    )
    record_id = intent_record.get("record_id", f"{source_file}:{line_no}")
    if no_call_reason:
        return RowOutcome(record_id, source_file, line_no, "no_call")
    if skip_reason:
        return RowOutcome(record_id, source_file, line_no, "skipped", detail=skip_reason)

    example = {"call_sequence": call_sequence, "intent_record": intent_record, "deck_layout": deck_layout}
    try:
        rt = run_runtime(example)
    except Exception as e:  # pragma: no cover - defensive, matches oracle_replay's own catch
        return RowOutcome(record_id, source_file, line_no, "harness_error", detail=f"runtime:{e}")

    if len(rt.plr_kwargs) == 0:
        # Nothing was ever planned (setup_error, oracle_replay's own
        # bucket) -- there is no tier-1 CALL stream to compare against.
        return RowOutcome(record_id, source_file, line_no, "setup_error", detail=rt.error)

    resources = resources_from_example(example)
    try:
        bc1, not_planned = lower_row_calls(example, rt.plr_kwargs, resources=resources, param_names=param_names)
    except Exception as e:
        return RowOutcome(record_id, source_file, line_no, "harness_error", detail=f"lower_row_calls:{e}")

    calls, _ = calls_from_plr_kwargs(example, rt.plr_kwargs)

    rendered = render_protocol(calls, rt.resource_types, function_name=_FUNCTION_NAME)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", dir=str(cache_dir), delete=False, encoding="utf-8",
    ) as src_f:
        src_f.write(rendered.source)
        src_path = Path(src_f.name)
    out_path = Path(tempfile.mktemp(suffix=".json", dir=str(cache_dir)))
    try:
        proc = subprocess.run(
            [runner_python, str(_EXTRACT_RUNNER), "--source", str(src_path),
             "--function", _FUNCTION_NAME, "--out", str(out_path), "--cache-dir", str(cache_dir)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0 or not out_path.is_file():
            return RowOutcome(
                record_id, source_file, line_no, "harness_error",
                detail=f"extract_runner failed rc={proc.returncode} stderr={proc.stderr[-2000:]}",
                rendered_source=rendered.source,
            )
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    finally:
        src_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)

    if "error" in payload:
        return RowOutcome(
            record_id, source_file, line_no, "harness_error",
            detail=f"extractor: {payload['error']}", rendered_source=rendered.source,
        )

    try:
        bc2 = ir_mod.lower_graph(payload, param_names=param_names)
    except Exception as e:
        return RowOutcome(
            record_id, source_file, line_no, "harness_error",
            detail=f"lower_graph:{e}", rendered_source=rendered.source,
        )

    divergences = compare_bytecode(
        bc1, bc2, ir_mod, residuals=list(rendered.residuals), source_lines=rendered.call_lines,
        tier1_wire_calls=calls, tier2_payload=payload, resource_name_map=rendered.name_map,
    )

    # AC-12.15's directional half: computed from the RAW (uncanonicalized)
    # call streams -- slot renaming is irrelevant to a method-name/Seq-
    # length check.
    raw1 = _extract_calls(bc1, ir_mod)
    raw2 = _extract_calls(bc2, ir_mod)
    directional_ok: bool | None = None
    setup_ok = bool(raw1) and bool(raw2) and raw1[0]["method"] == "setup" and raw2[0]["method"] == "setup"
    pickup1 = next((c for c in raw1 if c["method"] == "pick_up_tips"), None)
    pickup2 = next((c for c in raw2 if c["method"] == "pick_up_tips"), None)
    if pickup1 is not None or pickup2 is not None:
        len1 = _seq_len(pickup1["kwargs"].get("tip_spots")) if pickup1 else None
        len2 = _seq_len(pickup2["kwargs"].get("tip_spots")) if pickup2 else None
        directional_ok = setup_ok and len1 is not None and len1 == len2

    outcome = RowOutcome(
        record_id, source_file, line_no, "compared",
        agreeing=not divergences, divergences=divergences,
        n_calls_tier1=len(calls), residual_count=len(rendered.residuals),
        residual_classes=[classify_residual_reason(r.reason) for r in rendered.residuals],
        rendered_source=rendered.source if divergences else None,
        directional_ok=directional_ok,
    )
    return outcome


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=str, action="append", required=True)
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument("--sidecar", type=str, default=None)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument(
        "--runner-python", type=str, default=None,
        help="interpreter to invoke extract_runner.py with (default: this process's own)",
    )
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ir_mod = _lazy_ir()
    contracts_json = args.contracts.read_text(encoding="utf-8")
    param_names = param_names_from_contracts(contracts_json)
    runner_python = args.runner_python or sys.executable

    cache_dir = args.cache_dir or Path(tempfile.gettempdir()) / "plr_sema_tier2_extract"
    cache_dir.mkdir(parents=True, exist_ok=True)

    sidecar_rows, sidecar_by_digest = _load_sidecar(args.sidecar)

    t0 = time.monotonic()
    rows: list[RowOutcome] = []
    n_total = 0
    n_compared = 0
    n_agreeing = 0
    n_no_call = 0
    n_skipped = 0
    n_setup_error = 0
    n_harness_error = 0
    cause_counts: dict[str, int] = collections.Counter()
    #: backlog #4949 (260903 tier2a followup): every renderer RESIDUAL
    #: (dropped-kwarg, not a divergence) classified by
    #: ``render_protocol.classify_residual_reason`` -- published in the
    #: report as ``renderer_residual_by_class``, distinct from
    #: ``cause_counts["renderer"]`` (a divergence COUNT, one per diverging
    #: field) because a single residual can suppress more than one
    #: divergence field (e.g. a dropped ``ref`` used as both ``source`` and
    #: ``target``).
    residual_class_counts: dict[str, int] = collections.Counter()
    n_directional_checked = 0
    n_directional_ok = 0
    first_directional_example: dict[str, Any] | None = None

    for corpus_file in args.corpus:
        with open(corpus_file) as f:
            lines = f.readlines()
        exact_eligible = len(sidecar_rows) > 0 and len(lines) == len(sidecar_rows)
        for line_no, line in enumerate(lines, 1):
            if args.limit and n_total >= args.limit:
                break
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            srow = _sidecar_for(
                line_no, row, exact_eligible=exact_eligible,
                sidecar_rows=sidecar_rows, sidecar_by_digest=sidecar_by_digest,
            )
            ambiguity_class = srow.get("ambiguity_class") if srow else None
            provenance = srow.get("provenance") if srow else None
            outcome = run_row(
                row, corpus_file, line_no, param_names, ir_mod,
                ambiguity_class=ambiguity_class, provenance=provenance,
                cache_dir=cache_dir, runner_python=runner_python,
            )
            rows.append(outcome)
            n_total += 1
            if outcome.status == "no_call":
                n_no_call += 1
            elif outcome.status == "skipped":
                n_skipped += 1
            elif outcome.status == "setup_error":
                n_setup_error += 1
            elif outcome.status == "harness_error":
                n_harness_error += 1
            elif outcome.status == "compared":
                n_compared += 1
                if outcome.agreeing:
                    n_agreeing += 1
                for d in outcome.divergences:
                    cause_counts[d.cause] += 1
                for cls in outcome.residual_classes:
                    residual_class_counts[cls] += 1
                if outcome.directional_ok is not None:
                    n_directional_checked += 1
                    if outcome.directional_ok:
                        n_directional_ok += 1
                        if first_directional_example is None:
                            first_directional_example = {
                                "record_id": outcome.record_id,
                                "source_file": outcome.source_file,
                                "line": outcome.line,
                            }
            if n_total % 50 == 0:
                log.info("Processed %d rows (compared=%d agreeing=%d)...", n_total, n_compared, n_agreeing)

    elapsed = time.monotonic() - t0

    summary_flat = {
        "rows_total": n_total,
        "rows_compared": n_compared,
        "rows_agreeing": n_agreeing,
        "rows_no_call": n_no_call,
        "rows_skipped": n_skipped,
        "rows_setup_error": n_setup_error,
        "rows_harness_error": n_harness_error,
        "divergences_extractor": cause_counts.get("extractor", 0),
        "divergences_renderer": cause_counts.get("renderer", 0),
        "divergences_grammar": cause_counts.get("grammar", 0),
        "divergences_reset": cause_counts.get("reset", 0),
        "directional_checked": n_directional_checked,
        "directional_ok": n_directional_ok,
        "elapsed_seconds": elapsed,
    }

    top_divergences = [
        {
            "record_id": r.record_id, "source_file": r.source_file, "line": r.line,
            "call_index": d.call_index, "field": d.field, "cause": d.cause,
            "tier1": d.tier1, "tier2": d.tier2, "detail": d.detail,
            "rendered_source": r.rendered_source,
        }
        for r in rows for d in r.divergences
    ]

    report = {
        "summary_flat": summary_flat,
        "divergences_by_cause": dict(cause_counts),
        "renderer_residual_by_class": dict(residual_class_counts),
        "directional_example": first_directional_example,
        "top_extractor_divergences": [d for d in top_divergences if d["cause"] == "extractor"][:50],
        "top_renderer_divergences": [d for d in top_divergences if d["cause"] == "renderer"][:20],
        "top_grammar_divergences": [d for d in top_divergences if d["cause"] == "grammar"][:20],
        "top_reset_divergences": [d for d in top_divergences if d["cause"] == "reset"][:20],
        "harness_errors": [
            {"record_id": r.record_id, "source_file": r.source_file, "line": r.line, "detail": r.detail}
            for r in rows if r.status == "harness_error"
        ][:200],
        "rows": [
            {
                "record_id": r.record_id, "source_file": r.source_file, "line": r.line,
                "status": r.status, "agreeing": r.agreeing, "n_calls_tier1": r.n_calls_tier1,
                "residual_count": r.residual_count, "residual_classes": sorted(set(r.residual_classes)),
                "n_divergences": len(r.divergences),
                "causes": sorted({d.cause for d in r.divergences}),
                "directional_ok": r.directional_ok,
            }
            for r in rows
        ],
    }
    args.report.write_text(json.dumps(report, indent=2))
    log.info("Report written to %s", args.report)

    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(summary_flat))

    log.info(
        "summary: rows_total=%d compared=%d agreeing=%d no_call=%d skipped=%d setup_error=%d "
        "harness_error=%d divergences(extractor=%d renderer=%d grammar=%d reset=%d) "
        "directional=%d/%d elapsed=%.1fs",
        n_total, n_compared, n_agreeing, n_no_call, n_skipped, n_setup_error, n_harness_error,
        cause_counts.get("extractor", 0), cause_counts.get("renderer", 0),
        cause_counts.get("grammar", 0), cause_counts.get("reset", 0),
        n_directional_ok, n_directional_checked, elapsed,
    )

    # AC-12.15: zero extractor-cause divergences, AND at least one row
    # demonstrating the directional half (a comparison that always reports
    # "equal" cannot pass this).
    if cause_counts.get("extractor", 0) > 0:
        return 1
    if n_directional_checked > 0 and n_directional_ok == 0:
        log.error("AC-12.15 directional half never satisfied (%d rows checked, 0 agreed)", n_directional_checked)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

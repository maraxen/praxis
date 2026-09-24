"""``python -m plr_sema.derive``: the derivation-pipeline CLI (spec 260901
§7.3/§7.4).

Regenerates the two build artifacts derived from the survey:

.. code-block:: bash

    uv run python -m plr_sema.derive \\
        --survey-json training/verify/data/plr_preconditions.json \\
        --out plr-sema/data/derived_contracts.json \\
        --gap-ledger plr-sema/data/gap_ledger.json

``--survey-json PATH`` is REQUIRED, with no default (D19, §7.3): a
hardcoded default would silently couple this workspace-member package to
the caller's repo layout. At least one of ``--out``/``--gap-ledger`` must be
given, or there is nothing to do.

**260901 T13 (backlog #4859): the analyzed surface is a parameter.**
``--plr-root``/``--surface-name``/``--surface-pin`` together name the
``Surface`` (``plr_sema._provenance.Surface``) this run is against, recorded
in the emitted stamp. A second, non-legacy upstream surface (extracted via
``git archive <sha> | tar -x``, no ``.git`` to introspect) is derived the
same way, into DIFFERENT output paths so both coexist on disk:

.. code-block:: bash

    uv run python -m plr_sema.derive \\
        --survey-json training/verify/data/plr_preconditions.upstream_nonlegacy.json \\
        --out plr-sema/data/derived_contracts.upstream_nonlegacy.json \\
        --gap-ledger plr-sema/data/gap_ledger.upstream_nonlegacy.json \\
        --plr-root /path/to/extracted/upstream/pylabrobot \\
        --surface-name upstream_nonlegacy \\
        --surface-pin <upstream commit sha>
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

from plr_sema._provenance import DEFAULT_SURFACE, Surface, survey_stamp
from plr_sema.derive import (
    SCHEMA_VERSION,
    InlinedGuard,
    SurveyRecord,
    _stamp_to_dict,
    build_contract_keys,
    build_gap_ledger,
    build_index,
    build_unique_index,
    default_plr_pkg_root,
    derive_contract,
    load_survey,
    scan_dropped_receiver_calls,
)
from plr_sema.derive.bindings import param_defaults_from_function
from plr_sema.derive.predicate_ast import to_json as predicate_to_json
from plr_sema.derive.receiver_state import (
    FunctionIndex,
    ReceiverState,
    VolumeAnchor,
    build_plr_class_index,
    build_plr_function_index,
    compute_channel_bridge,
    compute_tip_families,
    compute_volume_anchors,
    compute_volume_bridge,
    compute_volume_state_exceptions,
    derive_receiver_states,
    lid_typestate_anchor_evidence,
    receiver_state_to_json,
)


def _guard_to_json(guard: InlinedGuard) -> dict[str, Any]:
    # 260904 (spec §15.2, T30a): additive `predicate` -- the mini-AST parsed
    # from `condition`, which stays the source of truth on the wire
    # (nothing is replaced). A reader that does not know this key (any
    # dict-based `.get("predicate")` consumer, or an un-regenerated
    # artifact) degrades to not having it at all -- no consumer reads it
    # yet (T31 is the evaluator).
    payload: dict[str, Any] = {
        "condition": guard.condition,
        "predicate": predicate_to_json(guard.predicate),
        "scope_trail": list(guard.scope_trail),
        "raises": guard.raises,
        "kind": guard.kind,
        "free_vars": list(guard.free_vars),
        "site": {
            "file": guard.site.file,
            "lineno": guard.site.lineno,
            "qualname": guard.site.qualname,
        },
        "depth": guard.depth,
    }
    # 260904 (spec §15.3, T30b): additive `bindings` -- the alpha/beta
    # local-binding idiom matches for this guard's own free names. `[]`
    # (key still present) when the guard has none, distinguishing "computed,
    # found nothing" from "an un-regenerated pre-T30b artifact never had the
    # key at all" (the latter a reader tolerates via `.get("bindings", ())`,
    # same additive-field discipline as `predicate` in T30a).
    payload["bindings"] = [dict(b) for b in guard.bindings]
    # 260907 (spec §15.4/§15.10, T36): additive `reachability_clear` --
    # E-UNCOND(5)'s refined K-body fact. Always present (key still there
    # even when `False`), same "computed, found nothing" vs. "field never
    # existed" discipline as `bindings` above -- a reader tolerates absence
    # via `.get("reachability_clear")` returning `None`, which
    # `check.predicate.evaluate_guard`'s `k_reachability_clear` parameter
    # already treats as fail-closed (unchanged from before this field
    # existed).
    payload["reachability_clear"] = guard.reachability_clear
    return payload


def build_derived_contracts_payload(
    records: list[SurveyRecord],
    index: dict[tuple[str, str], Any],
    stamp: Any,
    *,
    receiver_states: dict[str, ReceiverState] | None = None,
    volume_class_index: dict[str, ast.ClassDef] | None = None,
    volume_class_modules: dict[str, str] | None = None,
    volume_anchors: dict[str, VolumeAnchor] | None = None,
    function_index: FunctionIndex | None = None,
) -> dict[str, Any]:
    """AC-7.2 (260901 T11): derive a contract for every record the survey
    indexed -- the WHOLE analyzed PLR surface (4,770 methods across 345
    classes / 28 subpackages at the current pin), not just the 10
    ``SUPPORTED_TOOLS`` names. ``derive_contract`` itself never raises, so
    this never skips a record.

    **Population, not just the 1,314 finding-bearing methods (T11 item 4's
    zero-findings decision).** Every record in ``records`` -- including the
    3,456 that bear no ``PreconditionFinding`` of their own -- gets an entry
    point run through ``derive_contract``. This is NOT free of consequence:
    measured 260901, 580 of those 3,456 zero-own-finding methods inherit
    >=1 REAL guard through their ``delegates_to`` closure (e.g.
    ``PlateReader.read_absorbance`` has zero own findings but delegates to
    ``get_plate``, which has one) -- restricting the payload to
    finding-bearing entry points only, as an entry-point-selection choice,
    would have silently dropped every one of those 580 inherited guards for
    any operation naming one of those methods, which is exactly the
    own-body-only failure mode §7.2 exists to prevent, now recurring one
    level up (at entry-point selection rather than closure-walking). A
    zero-finding method with an empty closure (2,178 measured) still gets
    an entry -- guards=[], gaps=[] -- which ``check/``'s existing "resolved
    contract, zero guards, zero gaps, no loop" fallback (round-4 B1/B2)
    already turns into one ``no_contract_derived`` Finding: "known to the
    survey, unconstrained as far as it sees" is a real, different fact from
    "not resolvable to anything the survey analyzed at all"
    (``unsupported_tool``, redefined by this same task -- see
    ``plr_sema.check``'s module docstring).

    **Keying (T11 item 2, the collision fix).** ``build_index``'s
    ``(module, qualname)`` collapses 12 property/setter pairs at whole-survey
    scale (8 finding-bearing) -- using it here would silently derive a
    contract for only ONE twin per pair and never even attempt the other
    (see ``build_index``'s own docstring). This function therefore iterates
    ``build_unique_index(records)`` (every record individually addressable)
    for entry-point selection, while ``derive_contract``'s own closure walk
    keeps using ``index`` (the collapsing one) for ``resolve()``'s bare-name
    delegate lookup, unchanged -- the two have different jobs and the fix
    only touches the first. Output dict keys come from
    ``build_contract_keys`` -- see its docstring for the two independent
    collision sources (getter/setter pairs; same-named module-level
    functions in different modules) and the ``@module:lineno`` disambiguator.
    """
    unique_records = build_unique_index(records)
    contract_keys = build_contract_keys(records)
    receiver_states = receiver_states or {}
    # 260903 (spec 260903_plr-sema-volume-increment.md §14.0.1/§14.4, T24,
    # backlog #4958): the volume bridge's own whole-tree class index --
    # INDEPENDENT of `receiver_states` (built by `derive_receiver_states`,
    # which stays untouched, AC-14.1(iii)). `{}`/`None` (the default) when
    # the caller does not supply them -- fail closed to today's table, no
    # `volume_guards` key on any entry, same degrade discipline
    # `channel_guards`/`channel_effect` already use.
    volume_class_index = volume_class_index or {}
    volume_class_modules = volume_class_modules or {}
    volume_anchors = volume_anchors or {}
    contracts: dict[str, Any] = {}
    for record_key in sorted(unique_records):
        rec = unique_records[record_key]
        contract = derive_contract(rec.module, rec.qualname, index, stamp=stamp, function_index=function_index)
        out_key = contract_keys[record_key]
        assert out_key not in contracts, (
            f"contract key collision building payload: {out_key!r} "
            f"(record_key={record_key!r}) -- build_contract_keys should make "
            f"this structurally impossible"
        )
        entry: dict[str, Any] = {
            "guards": [_guard_to_json(g) for g in contract.guards],
            "gaps": [list(gap) for gap in contract.gaps],
            # 260902 (spec §11.2.4, SEMA-IR): additive `params` key -- this
            # method's PLR parameter names, straight off `SurveyRecord.params`
            # (already surveyed by `_function_params`,
            # `survey_plr_preconditions.py:267-274`). Consumed by
            # `plr_sema.check.ir.lower_graph`'s parameter-name trust rule
            # (§11.2.4): a `CALL.kwargs` key is trusted iff it is a member of
            # this list for the method being lowered. `schema_version` stays
            # 1 -- `check/` reads this via `.get("params", ())`, so a
            # pre-increment table (no `params` key on any entry) degrades to
            # "trust nothing" rather than raising (AC-11.12).
            "params": list(rec.params),
        }
        # 260904 (spec §15.4 E-CALL(2), D1, T30b): additive `param_defaults`
        # -- {param: <JSON literal>}, read from THIS entry point's OWN
        # `ast.arguments` (never a delegate's -- E-CALL(depth) forbids a
        # depth->=1 guard from consulting it at all, so it is only ever
        # meaningful for the entry point itself). Omitted entirely (no key)
        # when `function_index` was not supplied, or when the function has
        # no constant-valued defaults -- same fail-closed, additive-field
        # discipline as `channel_guards`/`volume_guards` above: an
        # un-regenerated table simply lacks the key, and a reader using
        # `.get("param_defaults", {})` sees "no defaults known", not a crash.
        if function_index is not None:
            K = function_index.get((rec.module, rec.qualname, rec.lineno))
            if K is not None:
                defaults = param_defaults_from_function(K)
                if defaults:
                    entry["param_defaults"] = defaults
        # 260902 (spec §10.2.5, tip typestate increment): additive
        # `channel_guards`/`channel_effect` keys, present ONLY on entries
        # whose receiver class (`rec.class_name`) has a derived
        # `ReceiverState` (§10.2's P1-P4 passes). `schema_version` stays 1
        # -- `plr_sema.check.tipstate` reads both via `.get()` with an
        # empty/`None` default (AC-10.7).
        if rec.class_name is not None and rec.class_name in receiver_states:
            rs = receiver_states[rec.class_name]
            channel_guards, channel_effect = compute_channel_bridge(
                (rec.module, rec.qualname), index, receiver_state=rs, stamp=stamp
            )
            if channel_guards:
                entry["channel_guards"] = channel_guards
            if channel_effect is not None:
                entry["channel_effect"] = channel_effect
        # 260903 (spec §14.4, T24): additive `volume_guards`, present only
        # on entries whose receiver class has a node in the volume family's
        # own whole-tree class index. Depth 0 only (K's own body) -- no
        # `delegates_to` closure walk, unlike `channel_guards` above.
        if rec.class_name is not None and rec.class_name in volume_class_index:
            volume_guards = compute_volume_bridge(
                (rec.module, rec.qualname),
                index,
                receiver_node=volume_class_index[rec.class_name],
                class_index=volume_class_index,
                class_modules=volume_class_modules,
                volume_anchors=volume_anchors,
                stamp=stamp,
            )
            if volume_guards:
                entry["volume_guards"] = volume_guards
        # 260903 (spec §14.4/§14.8, T27, backlog #4959): P7's `setter`
        # field, published as an additive `"is_volume_setter": true` key ON
        # THIS CONTRACT ENTRY -- specifically NOT under the top-level
        # `receiver_state` block, and specifically NOT merged into
        # `receiver_states[rec.class_name]`: `check/tipstate.py`'s own
        # `evaluate_call` (§10.4's E5) treats ANY non-`None` receiver_state
        # it is handed as a FULL tip-typestate `ReceiverState` dict and
        # indexes `receiver_state["channel_attr"]` unconditionally (no
        # `.get()`) -- both families read `receiver_states.get(call
        # .receiver_type)` off the SAME dict (`check/__init__.py`'s
        # `_evaluate_call`), so a `{"setter": ...}`-only block keyed under
        # `VolumeTracker` there would reach tipstate too and raise
        # `KeyError` the first time a `VolumeTracker.*` call is evaluated
        # (caught by this file's own gate run, not left for a reviewer to
        # find). The per-contract-entry key sidesteps that shared-dict
        # collision entirely: `check/volumestate.py`'s `_apply_seed` reads
        # `contract.get("is_volume_setter")` off the SAME `contract` dict
        # `evaluate_call` already receives, no new plumbing needed.
        if (
            rec.class_name is not None
            and rec.class_name in volume_anchors
            and volume_anchors[rec.class_name].setter is not None
            and rec.qualname.rsplit(".", 1)[-1] == volume_anchors[rec.class_name].setter
        ):
            entry["is_volume_setter"] = True
        contracts[out_key] = entry
    return {
        "schema_version": SCHEMA_VERSION,
        "stamp": _stamp_to_dict(stamp),
        # 260902 (spec §10.2.5): P1-P4's output, one entry per anchored
        # receiver class. `{}` when no `--taxonomy-json` was given (fail
        # closed -- degrades to today's all-`channel_guards`-free table).
        "receiver_state": {name: receiver_state_to_json(rs) for name, rs in sorted(receiver_states.items())},
        "contracts": contracts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m plr_sema.derive", description=__doc__
    )
    parser.add_argument(
        "--survey-json",
        type=Path,
        required=True,
        help="Path to plr_preconditions.json (required, no default -- D19).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write the derived-contracts table (§7.3) to this path.",
    )
    parser.add_argument(
        "--gap-ledger",
        type=Path,
        default=None,
        help="Write the gap ledger (§7.4) to this path.",
    )
    parser.add_argument(
        "--plr-root",
        type=Path,
        default=None,
        help=(
            "Override the PLR package root scanned by the independent "
            "dropped-receiver AST pass (default: derived from this file's "
            "own location, external/pylabrobot/pylabrobot). Also the "
            "surface's tree_path (260901 T13) -- what --surface-name/"
            "--surface-pin describe is THIS root."
        ),
    )
    parser.add_argument(
        "--surface-name",
        default=DEFAULT_SURFACE.name,
        help=(
            "260901 T13 (backlog #4859): name of the analyzed PLR surface "
            "(--plr-root's tree) recorded in the emitted stamp. Defaults to "
            "plr_sema._provenance.DEFAULT_SURFACE's own name, not a second "
            "hand-typed copy of it, so the two cannot drift apart -- this "
            "is the pre-T13 behavior (our checked-out submodule)."
        ),
    )
    parser.add_argument(
        "--surface-pin",
        default=None,
        help=(
            "260901 T13: explicit commit identity for --plr-root, for a "
            "tree that cannot answer that itself (e.g. an out-of-repo "
            "upstream extraction with no .git dir -- capture_git_state "
            "degrades to the 'nogit' sentinel on those, by design; this is "
            "how the real pin still ends up in the stamp). Leave unset for "
            "a live git checkout, where GitState.hash already answers it."
        ),
    )
    parser.add_argument(
        "--taxonomy-json",
        type=Path,
        default=None,
        help=(
            "260902 (spec §10.2.5, tip typestate increment): path to "
            "plr_exception_taxonomy.json. OPTIONAL -- when omitted, P1-P4's "
            "receiver-state derivation is skipped entirely (fail closed: "
            "the emitted table's `receiver_state` block is `{}` and no "
            "entry gains `channel_guards`/`channel_effect`, degrading to "
            "the pre-increment table exactly, AC-10.7). Required to "
            "populate the tip-state derivation the gate command in the "
            "task brief documents."
        ),
    )
    args = parser.parse_args(argv)

    if args.out is None and args.gap_ledger is None:
        parser.error("at least one of --out / --gap-ledger is required")

    records = load_survey(args.survey_json)
    index = build_index(records)
    surface_tree = args.plr_root if args.plr_root is not None else default_plr_pkg_root()
    surface = Surface(name=args.surface_name, tree_path=surface_tree, pin=args.surface_pin)
    stamp = survey_stamp(surface)

    receiver_states: dict[str, ReceiverState] = {}
    # 260904 (spec §15.3/§15.4 D1, T30b): the alpha/beta idioms' and
    # param_defaults' own whole-tree function index -- built UNCONDITIONALLY
    # (unlike receiver_states/volume_class_index below, which need
    # --taxonomy-json), since neither idiom resolution nor param_defaults
    # depends on the tip/volume taxonomy at all.
    function_index: FunctionIndex = build_plr_function_index(surface_tree)
    # 260903 (spec §14.4, T24): the volume family's own whole-tree class
    # index and P7 anchors, built alongside `receiver_states` under the
    # SAME `--taxonomy-json` gate (P7's used-volume/free-volume accessor
    # split needs the taxonomy's `volume_state` category, exactly as
    # `derive_receiver_states` needs `tip_state`) -- but from
    # `build_plr_class_index`, NOT from `derive_receiver_states` (which
    # stays untouched, AC-14.1(iii)).
    volume_class_index: dict[str, ast.ClassDef] = {}
    volume_class_modules: dict[str, str] = {}
    volume_anchors: dict[str, VolumeAnchor] = {}
    if args.taxonomy_json is not None:
        taxonomy_payload = json.loads(args.taxonomy_json.read_text(encoding="utf-8"))
        receiver_states = derive_receiver_states(surface_tree, records, taxonomy_payload["classes"])
        volume_class_index, volume_class_modules = build_plr_class_index(surface_tree)
        volume_state_exceptions = frozenset(compute_volume_state_exceptions(taxonomy_payload["classes"]))
        volume_anchors = compute_volume_anchors(volume_class_index, volume_state_exceptions)

    if args.out is not None:
        payload = build_derived_contracts_payload(
            records,
            index,
            stamp,
            receiver_states=receiver_states,
            volume_class_index=volume_class_index,
            volume_class_modules=volume_class_modules,
            volume_anchors=volume_anchors,
            function_index=function_index,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
        if receiver_states:
            for name, rs in sorted(receiver_states.items()):
                print(
                    f"receiver_state[{name!r}]: channel_attr={rs.channel_attr!r} "
                    f"tracker_class={rs.tracker_class!r} state_fields={list(rs.state_fields)} "
                    f"effects={rs.effects} channel_default_param={rs.channel_default_param} "
                    f"channel_default_disablers={list(rs.channel_default_disablers)} "
                    f"entry_reset={rs.entry_reset if rs.entry_reset is not None else rs.entry_reset_ledger!r}",
                    file=sys.stderr,
                )

    if args.gap_ledger is not None:
        dropped_receiver_counts = scan_dropped_receiver_calls(surface_tree)
        ledger = build_gap_ledger(
            index, records, dropped_receiver_counts=dropped_receiver_counts, stamp=stamp
        )
        # 260903 (spec §13.1/§13.9, backlog #4881a): the lid family's
        # ledger-only block. Independent of --taxonomy-json / receiver_states
        # -- the lid family is specified and NOT adopted (§13.1's normative
        # disposition), so this never touches `receiver_states`, never
        # constructs a `LidState` or a `ReceiverState`, and never derives a
        # Finding. `Liddable`'s anchor/state-field evidence comes from
        # `lid_typestate_anchor_evidence` (re-running P2's real rule, not a
        # new one); the two `_check_no_lid` guard conditions come from the
        # SAME `derive_contract` closure `--out` uses, run just for that one
        # entry point so `--gap-ledger` alone (no `--out`) still works.
        lid_anchor_evidence = lid_typestate_anchor_evidence(surface_tree)
        if lid_anchor_evidence is not None:
            lid_module = next(
                (rec.module for rec in records if rec.class_name is None and rec.qualname == "_check_no_lid"),
                None,
            )
            check_no_lid_guards: list[dict[str, Any]] = []
            if lid_module is not None:
                check_no_lid_contract = derive_contract(lid_module, "_check_no_lid", index, stamp=stamp)
                check_no_lid_guards = [_guard_to_json(g) for g in check_no_lid_contract.guards]
            ledger["lid_state"] = {
                "Liddable": {
                    **lid_anchor_evidence,
                    "check_no_lid_guards": check_no_lid_guards,
                }
            }
        if receiver_states:
            # 260902 (spec §10.2/AC-10.10): the tip_state ledger block --
            # per anchored receiver class, its derived method families and
            # tipstate_anchor status. Built from the SAME contract table
            # --out would emit (recomputed here rather than threaded
            # through, so --gap-ledger alone still works without --out).
            contract_entries = build_derived_contracts_payload(
                records, index, stamp, receiver_states=receiver_states
            )["contracts"]
            tip_state_block: dict[str, Any] = {}
            for name, rs in sorted(receiver_states.items()):
                families = compute_tip_families(contract_entries, receiver_class=name, receiver_state=rs)
                # 260903 (spec §13.5.3, P9): a `bound_channels` entry per
                # contract key of THIS receiver class that carries at least
                # one channel_guards entry reached at closure depth 1 (i.e.
                # every key P9 could possibly bind at) -- the derived record
                # where P9 bound one, else the widening reason (rules 1/5)
                # publishes "absent" (K's own body never named a candidate
                # delegate a single time) or "widened" (a candidate existed
                # but its shape/multiplicity forced Top) so an absence is
                # readable in the artifact rather than inferred from silence
                # (the same discipline §10.2.2 established for
                # `tipstate_anchor`, §12.1.3 for `entry_reset`).
                bound_channels_block: dict[str, Any] = {}
                prefix = f"{name}."
                for key, entry in contract_entries.items():
                    if not key.startswith(prefix) or "@" in key:
                        continue
                    depth1_guards = [g for g in entry.get("channel_guards", ()) if g.get("depth") == 1]
                    if not depth1_guards:
                        continue
                    method = key[len(prefix) :]
                    bound = next((g["bound_channels"] for g in depth1_guards if "bound_channels" in g), None)
                    if bound is not None:
                        bound_channels_block[key] = dict(bound)
                    elif method in rs.delegate_channel_binding:
                        bound_channels_block[key] = "widened"
                    else:
                        bound_channels_block[key] = "absent"
                tip_state_block[name] = {
                    "tipstate_anchor": rs.bool_view_field,
                    "tip_loading": list(families.tip_loading),
                    "tip_requiring": list(families.tip_requiring),
                    "tip_dropping": list(families.tip_dropping),
                    # 260903 (spec §12.1.3): the derived {method, post}
                    # pair, or "absent"/"ambiguous" when P5 emitted
                    # nothing -- an absence must be readable in the
                    # artifact, not inferred from an absence of verdicts.
                    "entry_reset": dict(rs.entry_reset) if rs.entry_reset is not None else rs.entry_reset_ledger,
                    "bound_channels": bound_channels_block,
                }
            ledger["tip_state"] = tip_state_block
        args.gap_ledger.parent.mkdir(parents=True, exist_ok=True)
        args.gap_ledger.write_text(
            json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.gap_ledger}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

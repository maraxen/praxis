"""T30's measurement script (spec 260904 §15.9, increment 6, T30b).

Publishes the five measured blocks §15.9 requires -- parse coverage,
binding coverage (incl. D2's `channels_for_call` count and the depth->=1
name-coincidence exposure count), a per-cluster classification against the
54-cluster ledger, a per-executed-operation residual reason set, and the O1
delta -- and records GO/NO-GO against the reason-based gate (§15.9's own
normative box): **GO iff >= 1 executed real operation carries ZERO
`guard_predicate_unparsed` findings AND ZERO `guard_operand_unknown`
findings.**

**This script constructs NO verdict and calls `check_ir` NOWHERE.** T31 (the
evaluator, `plr_sema.check.predicate`) does not exist yet; this is a STATIC
classification of what E-CALL WOULD resolve for a guard against a real call
-- built from the contract table's own `predicate`/`bindings`/`depth`
fields (T30's own derive-side output) plus the frozen benchmark's REAL
lowered IR `Call` instructions.

**(#4978, T32 fix-up) The executed-op population is sourced from
`oracle_replay.main()` ITSELF** (`collect_executed_population`, via the
`FINDINGS_SINK`/`LOWERED_SINK` seams `oracle_common.run_static_calls`
fires) -- the SAME technique `unknown_ledger.py` already uses, and for the
same reason: never re-implement `row_to_verifier_inputs`/`run_runtime`/
`lower_row_calls`'s own skip/no_call/sidecar gating a second time. An
earlier version of this script DID re-implement that gating directly and
called `row_to_verifier_inputs` WITHOUT the sidecar's `ambiguity_class`/
`provenance` (the earlier docstring here claimed sidecar/crosscheck join
"neither gates which rows count as executed" -- FALSE: `ambiguity_class`
directly sets `skip_reason` in `row_to_verifier_inputs` whenever it is not
`"clean_parse"`), so every non-`"clean_parse"` row (`missing_slot`/
`ambiguous_referent`/`out_of_surface`) that `run_row` would have skipped
was silently admitted instead -- 923 executed ops (361 `pick_up_tips`,
260905) measured against the correct 544 (223 `pick_up_tips`) the ledger's
own `FINDINGS_SINK`-derived population reports for the identical corpus/
sidecar/crosscheck inputs. `--sidecar`/`--crosscheck` are now REQUIRED
(pass-through to `oracle_replay.main()`) to reproduce that population; see
`collect_executed_population`'s own docstring for the fix and this
script's `population` JSON key for the measured before/after counts.

**Honesty about scope, stated up front rather than discovered by a
reader.** The per-call operand-resolution model below is NOT the general
E-CALL evaluator §15.4 specifies (that is T31's ~560 LOC). It faithfully
reproduces the specific mechanisms this increment's own worked examples
turn on -- the recursive "a binding only resolves its name if its OWN
iterand also resolves" rule that is why `:875`'s `not_containers` is
`guard_env_dependent` rather than `guard_operand_unknown` at depth 1, the
real `channels_for_call` import for D2, and per-element `IsInstance`
resolution against O1's `element_type` for the `Filtered`-bound cases the
gate candidate turns on. It does NOT implement chained-`Cmp` short-circuit
evaluation, `G4` set-uniqueness value comparison, or numeric interval
folding -- none of which the gate candidate (`pick_up_tips`) needs, and
all of which are published as caveats in this script's own JSON output
under `"scope_notes"` rather than silently assumed complete.

Usage::

    uv run python plr-sema/eval/t30_measure.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --sidecar training/assemble/out/corpus_p25_sidecar.jsonl \\
        --crosscheck training/out/corpus_p23_floor.jsonl \\
        --crosscheck training/overlay_gen/out/overlay_full.jsonl \\
        --contracts plr-sema/data/derived_contracts.json \\
        --ledger outputs/plr-sema/unknown_ledger_260904_before.json \\
        --out outputs/plr-sema/t30_measured_260907.json \\
        [--limit 50]
"""

from __future__ import annotations

import argparse
import ast
import collections
import dataclasses
import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

import oracle_common as oc  # noqa: E402
import oracle_replay  # noqa: E402
from plr_sema.check import ir as _ir  # noqa: E402
from plr_sema.check import tipstate  # noqa: E402
from plr_sema.derive.bindings import (  # noqa: E402
    build_qualname_index,
    free_var_names,
    is_plr_layer_method,
    substitute,
)
from plr_sema.derive.predicate_ast import (  # noqa: E402
    TRUE,
    AllOf,
    And,
    AnyOf,
    Cmp,
    EnvRef,
    Filtered,
    Is,
    IsInstance,
    Len,
    MEMBERSHIP_OPS,
    Not,
    Opaque,
    Or,
    Predicate,
    SetOf,
    Zip,
    contains_env_ref,
    contains_opaque,
    count_env_ref_nodes,
    count_var_self,
    parse as parse_predicate_raw,
    walk as walk_predicate,
    from_json,
)
from plr_sema.derive.receiver_state import build_plr_function_index

log = logging.getLogger("t30_measure")

DEFAULT_CONTRACTS = oc.DEFAULT_CONTRACTS
BENCHMARK_NAME = "tier1-sidecar-gated-dd79c4c89"

REASON_UNPARSED = "guard_predicate_unparsed"
REASON_ENV = "guard_env_dependent"
REASON_OPERAND = "guard_operand_unknown"
REASON_DECIDABLE = "decidable"

CANDIDATE_METHODS = ("pick_up_tips", "transfer", "aspirate", "dispense", "drop_tips", "discard_tips", "stamp")

#: §15.9's own prediction table (this document's transcription of §15.1's
#: tables), keyed by (basename, lineno) -- ONLY the sites the spec
#: individually names. Everything else in the ledger's 54 clusters is
#: published with `predicted_tier: "not individually tabulated in spec
#: 260904_plr-sema-predicate-increment.md sec15.1"` rather than guessed.
PREDICTED_TIER: dict[tuple[str, int], str] = {
    ("liquid_handler.py", 498): "(i)",
    ("liquid_handler.py", 502): "(i)",
    ("liquid_handler.py", 522): "(i)",
    ("liquid_handler.py", 514): "(ii) backend",
    ("liquid_handler.py", 375): "(ii) backend signature",
    ("liquid_handler.py", 383): "(ii) env and backend",
    ("liquid_handler.py", 409): "(ii) head channel count",
    ("liquid_handler.py", 321): "(ii) deck membership",
    ("liquid_handler.py", 576): "(iii)",
    ("liquid_handler.py", 647): "(i)",
    ("liquid_handler.py", 651): "(i)",
    ("liquid_handler.py", 657): "1/2 by decision (numeric Cmp, Open decision 2)",
    ("liquid_handler.py", 666): "(i) unbindable (loop-append)",
    ("liquid_handler.py", 726): "(iii)",
    ("liquid_handler.py", 959): "(i)",
    ("liquid_handler.py", 1153): "(i)",
    ("liquid_handler.py", 990): "(i) unbindable (needs gamma)",
    ("liquid_handler.py", 1202): "(i) unbindable (needs gamma)",
    ("liquid_handler.py", 875): "(i) [but depth>=1 -- see E-CALL(depth)]",
    ("liquid_handler.py", 1185): "withdrawn (round 1) -- does not clear",
    ("liquid_handler.py", 1188): "withdrawn (round 1) -- does not clear",
    ("liquid_handler.py", 116): "(ii) lid topology",
    ("liquid_handler.py", 117): "reachability-blocked (E-UNCOND(5))",
    ("liquid_handler.py", 1067): "(iii)",
    ("liquid_handler.py", 1271): "(iii)",
    ("liquid_handler.py", 1335): "(i)",
    ("liquid_handler.py", 1337): "(i)",
    ("liquid_handler.py", 1340): "(i)",
    ("liquid_handler.py", 2092): "derived (iii) (is_dynamic_raise)",
    ("liquid_handler.py", 1770): "reachability-blocked (else-of-if, E-UNCOND way (1))",
    ("liquid_handler.py", 1920): "reachability-blocked (else-of-if, E-UNCOND way (1))",
    ("liquid_handler.py", 1743): "(i)",
    ("liquid_handler.py", 1893): "(i)",
    ("liquid_handler.py", 1807): "(i)",
    ("liquid_handler.py", 1963): "(i)",
    ("liquid_handler.py", 1778): "(ii) topology",
    ("liquid_handler.py", 1940): "(ii) topology",
    ("liquid_handler.py", 1804): "(ii) topology",
    ("liquid_handler.py", 1960): "(ii) topology",
    ("volume_tracker.py", 92): "(ii) observation (already evaluated, increment 5)",
    ("volume_tracker.py", 105): "(ii) observation (already evaluated, increment 5)",
}


# ---------------------------------------------------------------------------
# contract-table helpers
# ---------------------------------------------------------------------------


def module_from_plr_file(file: str) -> str | None:
    """Mirrors `receiver_state`/`derive.__init__`'s own `_module_name_for_plr_file`
    -- but starting from a REPO-RELATIVE `SurveyRecord.file` string (what
    every guard's `site.file` / every ledger cluster's `plr_site` carries)
    rather than a filesystem `Path`. Returns `None` for a file outside
    `external/pylabrobot/` (should not occur for a LiquidHandler guard, but
    fails closed rather than raising).
    """
    p = Path(file)
    try:
        rel = p.relative_to("external/pylabrobot")
    except ValueError:
        return None
    return ".".join(rel.with_suffix("").parts)


def is_tip_family_owned(g: dict[str, Any], receiver_state: dict[str, Any]) -> bool:
    """§15.2's dispatch rule: "a guard the tip family claims (its existing
    `evaluate_call` selection) is skipped by the predicate evaluator
    entirely". Detected by re-running the SAME shipped recognizer
    (`tipstate.parse_own_atom`) THIS increment must not re-decide --
    never a hand-typed site list. `:535`'s `self.head[channel].has_tip` is
    the gate-relevant case: it does not appear anywhere in the real
    54-cluster ledger at all (confirmed against
    `outputs/plr-sema/unknown_ledger_260904_before.json`), i.e. it is
    ALREADY fully resolved by the shipped tip-typestate family on this
    benchmark ("the tenth is already evaluated", §15.1.1) -- counting it
    toward `guard_predicate_unparsed` here would be double-counting a
    residual this increment does not own and a prior increment already
    closed.
    """
    qualname = g["site"]["qualname"]
    if "." not in qualname:
        return False
    class_name = qualname.split(".", 1)[0]
    rs = receiver_state.get(class_name)
    if rs is None:
        return False
    channel_attr = rs.get("channel_attr")
    bool_view_attr = rs.get("bool_view", {}).get("attr")
    if channel_attr is None or bool_view_attr is None:
        return False
    state_fields = frozenset(rs.get("state_fields", ()))
    atom = tipstate.parse_own_atom(
        g.get("condition"), channel_attr=channel_attr, bool_view_attr=bool_view_attr, state_fields=state_fields
    )
    return atom is not None


def build_volume_guard_sites(contracts: dict[str, Any]) -> frozenset[tuple[str, int, str]]:
    """S15.2's family-dispatch rule, the volume half: "a guard the volume
    family claims (a `volume_guards` entry) is skipped by the predicate
    evaluator entirely". `volume_guards` is an ADDITIVE per-entry field
    (`derive/receiver_state.py:1937-2040`), never a hand-typed site list --
    this reduces every entry's `volume_guards` across the WHOLE contract
    table to the `(file, lineno, qualname)` sites it names, once, so
    `is_volume_family_owned` below is a set lookup rather than a per-guard
    re-scan (fix-up (2), S15.9: T35 must skip family-claimed guards and
    report the family's own reason -- `volume_tracker.py:92`/`:105` must
    NOT carry a predicate reason)."""
    sites: set[tuple[str, int, str]] = set()
    for entry in contracts.values():
        for vg in entry.get("volume_guards", ()):
            site = vg["site"]
            sites.add((site["file"], site["lineno"], site["qualname"]))
    return frozenset(sites)


def is_volume_family_owned(g: dict[str, Any], volume_guard_sites: frozenset[tuple[str, int, str]]) -> bool:
    site = g["site"]
    return (site["file"], site["lineno"], site["qualname"]) in volume_guard_sites


def build_guard_index(
    contracts: dict[str, Any], *, prefer_public_entry: bool = False
) -> dict[tuple[str, int, str], dict[str, Any]]:
    """(file, lineno, qualname) -> a guard JSON found at that site, across
    the WHOLE contract table.

    `condition`/`predicate`/`bindings` are IDENTICAL wherever the same site
    appears (all views of the SAME `InlinedGuard` `derive_contract`
    constructed from the SAME defining record) -- but `depth` is NOT: it is
    a property of the CLOSURE WALK that reached it, not of the guard's own
    definition, and a helper method (e.g. `_check_containers`) that is
    ALSO its own top-level contract entry sees its OWN guards at depth 0
    there, even though the SAME guard is reached at depth 1 from every
    real tool (`aspirate`/`dispense`/`transfer`) that calls it. With
    `prefer_public_entry=True` (block 3's own classification, which cares
    about the depth an EXECUTED operation actually sees it at), an
    occurrence from an entry whose bare method name does not start with
    `_` wins over one from a private helper's own entry; `dict` iteration
    order otherwise decides (first-seen, matching the pre-260905 behaviour)
    when no public occurrence exists.
    """
    idx: dict[tuple[str, int, str], dict[str, Any]] = {}
    idx_is_public: dict[tuple[str, int, str], bool] = {}
    for key, entry in contracts.items():
        method = key.rsplit(".", 1)[-1].split("@", 1)[0]
        is_public = not method.startswith("_")
        for g in entry.get("guards", ()):
            site = g["site"]
            gkey = (site["file"], site["lineno"], site["qualname"])
            if gkey not in idx:
                idx[gkey] = g
                idx_is_public[gkey] = is_public
            elif prefer_public_entry and is_public and not idx_is_public[gkey]:
                # The currently-indexed occurrence came only from a
                # private helper's OWN entry (depth 0 there); a public
                # entry that reaches the SAME site (necessarily at
                # depth >= 1) is what an executed operation actually sees.
                idx[gkey] = g
                idx_is_public[gkey] = True
    return idx


def build_param_names_by_qualname(function_index) -> dict[tuple[str, str], frozenset[str]]:
    out: dict[tuple[str, str], frozenset[str]] = {}
    for (module, qualname, _lineno), node in function_index.items():
        if (module, qualname) in out:
            continue
        args = node.args
        names = {a.arg for a in args.posonlyargs} | {a.arg for a in args.args} | {a.arg for a in args.kwonlyargs}
        if args.vararg is not None:
            names.add(args.vararg.arg)
        if args.kwarg is not None:
            names.add(args.kwarg.arg)
        out[(module, qualname)] = frozenset(names)
    return out


# ---------------------------------------------------------------------------
# Block 1 -- parse coverage
# ---------------------------------------------------------------------------


def atom_kind(pred: Predicate) -> str:
    """Best-effort STRUCTURAL classification of a top-level parsed
    predicate into one of §15.9(1)'s named atom kinds. This is a
    structural approximation, published as such: the mini-AST does not
    tag a node with which G-rule produced it, so "chained Cmp" is
    recognised by shape (an `And` whose every child is a `Cmp`) rather
    than by provenance -- an `And` of two Cmps a human wrote directly
    (not through G2's chained-comparison rewrite) would be indistinguishable
    and is intentionally counted the same way (both are, honestly, "two
    conjoined Cmps").
    """
    if isinstance(pred, TRUE):
        return "TRUE"
    if isinstance(pred, Opaque):
        return "Opaque"
    if isinstance(pred, Is):
        return "Is"
    if isinstance(pred, IsInstance):
        return "IsInstance"
    if isinstance(pred, Not) and isinstance(pred.predicate, AnyOf) and isinstance(pred.predicate.seq, Filtered):
        return "Filtered-emptiness (Not-AnyOf)"
    if isinstance(pred, AnyOf) and isinstance(pred.seq, Filtered):
        return "Filtered-emptiness (AnyOf)"
    if isinstance(pred, Cmp):
        left_setof = isinstance(pred.left, Len) and isinstance(pred.left.term, SetOf)
        right_setof = isinstance(pred.right, Len) and isinstance(pred.right.term, SetOf)
        if left_setof or right_setof:
            return "SetOf-uniqueness"
        return "Cmp"
    if isinstance(pred, And) and pred.predicates and all(isinstance(p, Cmp) for p in pred.predicates):
        return "chained-Cmp"
    if isinstance(pred, (AllOf, AnyOf)):
        return "AllOf/AnyOf"
    if isinstance(pred, Not):
        return "Not"
    if isinstance(pred, And):
        return "And"
    if isinstance(pred, Or):
        return "Or"
    return "other"


def measure_parse_coverage(
    contracts: dict[str, Any],
    receiver_state: dict[str, Any],
    volume_guard_sites: frozenset[tuple[str, int, str]] = frozenset(),
) -> dict[str, Any]:
    by_kind: collections.Counter = collections.Counter()
    opaque_shapes: collections.Counter = collections.Counter()
    total = 0
    non_opaque = 0
    n_tip_family_owned = 0
    n_volume_family_owned = 0
    seen_sites: set[tuple[str, int, str]] = set()
    for entry in contracts.values():
        for g in entry.get("guards", ()):
            site = g["site"]
            key = (site["file"], site["lineno"], site["qualname"])
            if key in seen_sites:
                continue  # count each DISTINCT guard once, not once per inheriting entry point.
            seen_sites.add(key)
            if is_tip_family_owned(g, receiver_state):
                n_tip_family_owned += 1
                continue
            if is_volume_family_owned(g, volume_guard_sites):
                # fix-up (2), S15.9: a guard the volume family claims keeps
                # `volume_state_unknown`, never a predicate reason -- excluded
                # here for the identical reason the tip family already is.
                n_volume_family_owned += 1
                continue
            total += 1
            pred = from_json(g["predicate"])
            kind = atom_kind(pred)
            by_kind[kind] += 1
            if kind != "Opaque":
                non_opaque += 1
            else:
                opaque_shapes[pred.text] += 1
    return {
        "n_guards_distinct_sites": total,
        "n_tip_family_owned_excluded": n_tip_family_owned,
        "n_volume_family_owned_excluded": n_volume_family_owned,
        "n_non_opaque": non_opaque,
        "n_opaque": by_kind.get("Opaque", 0),
        "by_atom_kind": dict(sorted(by_kind.items())),
        "top10_unparsed_shapes": [{"text": t, "n": n} for t, n in opaque_shapes.most_common(10)],
    }


# ---------------------------------------------------------------------------
# Block 2 -- binding coverage, D2, name-coincidence exposure
# ---------------------------------------------------------------------------


def measure_binding_coverage(
    contracts: dict[str, Any],
    param_names_by_qualname: dict[tuple[str, str], frozenset[str]],
    receiver_state: dict[str, Any],
    function_index,
    volume_guard_sites: frozenset[tuple[str, int, str]] = frozenset(),
) -> dict[str, Any]:
    guard_index = build_guard_index(contracts, prefer_public_entry=True)

    # The complete (K, x, idiom, term) CATALOG (AC-15.2's own floor) is
    # GUARD-INDEPENDENT (`bindings.compute_all_local_bindings`'s own
    # docstring): PLR rebinds `flow_rates`/`liquid_height`/
    # `blow_out_air_volume` via the identical beta shape in `aspirate`/
    # `dispense`, but they are read only through the deferred gamma
    # aliasing loop and so never appear as a free `Var` in any GUARD's own
    # `predicate` -- a guard-scoped search over `guard_index` would
    # silently undercount the catalog. Scanned over the WHOLE function
    # index (every module the survey walked), not just LiquidHandler.
    from plr_sema.derive.bindings import compute_all_local_bindings

    tuples: list[dict[str, Any]] = []
    for (module, qualname, lineno), node in function_index.items():
        for b in compute_all_local_bindings(node):
            tuples.append({"K": qualname, "module": module, "K_lineno": lineno, **b})
    # de-duplicate by (module, K_lineno, x, idiom) -- `function_index` is
    # itself already a first-definition-wins map, so this is defensive.
    seen = set()
    dedup_tuples = []
    for t in tuples:
        key = (t["module"], t["K_lineno"], t["x"], t["idiom"])
        if key in seen:
            continue
        seen.add(key)
        dedup_tuples.append(t)

    n_alpha = sum(1 for t in dedup_tuples if t["idiom"] == "alpha")
    n_beta = sum(1 for t in dedup_tuples if t["idiom"] == "beta")

    # "guards with >= 1 free local of which every/some/no local binds"
    # (§15.9(2)'s second clause) IS guard-scoped -- it is a claim about
    # GUARDS, read from `InlinedGuard.bindings` (the per-guard field T30b
    # actually populates), not from the wider catalog above.
    all_free_local_count = collections.Counter()  # "all" | "some" | "none" -> n guards
    for (file, lineno, qualname), g in sorted(guard_index.items()):
        if is_tip_family_owned(g, receiver_state) or is_volume_family_owned(g, volume_guard_sites):
            continue
        module = module_from_plr_file(file)
        pred = from_json(g["predicate"])
        param_names = param_names_by_qualname.get((module, qualname), frozenset()) if module else frozenset()
        free_names = free_var_names(pred)
        free_locals = [n for n in free_names if n not in param_names]
        if not free_locals:
            continue
        bound_names = {b["x"] for b in g.get("bindings", ())}
        n_bound = sum(1 for n in free_locals if n in bound_names)
        if n_bound == len(free_locals):
            all_free_local_count["all"] += 1
        elif n_bound == 0:
            all_free_local_count["none"] += 1
        else:
            all_free_local_count["some"] += 1

    # Name-coincidence exposure (item 13's forgone substitution): for every
    # depth>=1 guard, in EVERY entry point that inherits it, check whether
    # a free local that does NOT already resolve via a binding happens to
    # share a name with that ENTRY's own declared params.
    exposure = 0
    exposure_examples: list[dict[str, Any]] = []
    for key, entry in contracts.items():
        entry_params = set(entry.get("params", ()))
        for g in entry.get("guards", ()):
            if (
                g["depth"] < 1
                or is_tip_family_owned(g, receiver_state)
                or is_volume_family_owned(g, volume_guard_sites)
            ):
                continue
            pred = from_json(g["predicate"])
            bound_names = {b["x"] for b in g.get("bindings", ())}
            free_names = free_var_names(pred)
            for name in free_names:
                if name in bound_names:
                    continue
                if name in entry_params:
                    exposure += 1
                    if len(exposure_examples) < 20:
                        exposure_examples.append(
                            {"entry": key, "guard_site": g["site"], "name": name}
                        )
    return {
        "tuples": dedup_tuples,
        "n_alpha": n_alpha,
        "n_beta": n_beta,
        "guards_with_free_locals": dict(all_free_local_count),
        "name_coincidence_exposure_count": exposure,
        "name_coincidence_exposure_examples": exposure_examples,
    }


def measure_d2(ops: list[ExecutedOp], receiver_state: dict[str, Any]) -> dict[str, Any]:
    """D2: the number of EXECUTED `pick_up_tips` operations for which
    `channels_for_call` (imported, read-only) returns non-`None`.

    ``ops`` is the authoritative executed-op population from
    :func:`collect_executed_population` (#4978, T32 fix-up) -- the SAME
    population `unknown_ledger.py`'s own `FINDINGS_SINK`-derived
    `n_ops_executed` counts, never a locally re-derived row loop. `call`
    (the without-O1 view) is used: `channels_for_call` reads only
    `call.kwargs`, which does not vary between the with-O1 and without-O1
    lowerings of the same operation (O1 only changes RESOURCE typing).
    """
    lh_state = receiver_state.get("LiquidHandler", {})
    channel_default_param = lh_state.get("channel_default_param", {})
    channel_kwarg = lh_state.get("channel_kwarg")
    n_pick_up_tips_ops = 0
    n_non_none = 0
    for op in ops:
        if op.method != "pick_up_tips":
            continue
        n_pick_up_tips_ops += 1
        channels = tipstate.channels_for_call(op.call, channel_default_param, channel_kwarg)
        if channels is not None:
            n_non_none += 1
    return {"n_pick_up_tips_ops": n_pick_up_tips_ops, "n_channels_for_call_non_none": n_non_none}


# ---------------------------------------------------------------------------
# The executed-op population (#4978, T32 fix-up) -- sourced from
# oracle_replay.main() ITSELF, via the FINDINGS_SINK (#4976) + LOWERED_SINK
# (#4978) seams oracle_common.run_static_calls fires, never from a local
# re-implementation of row_to_verifier_inputs/run_runtime/lower_row_calls's
# own skip/no_call/sidecar gating. See the module docstring above for why
# the pre-#4978 version of this file (which DID re-implement that gating,
# omitting the sidecar's ambiguity_class/provenance) measured 923 executed
# ops (361 pick_up_tips) instead of the correct 544 (223 pick_up_tips) --
# unknown_ledger.py's own FINDINGS_SINK-derived population, which this
# script's population is now REQUIRED to match exactly (population parity
# is asserted, not merely hoped for -- see `collect_executed_population`'s
# own positional-correlation check, mirroring `unknown_ledger.build_ledger`'s
# identical invariant).
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ExecutedOp:
    """One real, executed operation -- i.e. one that carried >=1 real
    `Finding` through the FINDINGS_SINK seam on this run, the same
    membership test `unknown_ledger.cluster_unknown_findings` uses for its
    own `n_ops_executed`. `call`/`slot_to_resource` are the WITHOUT-O1 view
    (byte-identical to what every existing `run_static_calls` caller sees
    today); `call_with_o1`/`slot_to_resource_with_o1` are the WITH-O1 view
    `LOWERED_SINK` additionally provides. `receiver_type`/`method` do not
    vary between the two views (O1 only changes RESOURCE typing, never
    which method was called on which receiver).
    """

    row_idx: int
    record_id: str
    op_id: str
    real_idx: int
    method: str
    call: Any  # plr_sema.check.ir.Call
    call_with_o1: Any  # plr_sema.check.ir.Call
    slot_to_resource: dict[int, Any]
    slot_to_resource_with_o1: dict[int, Any]


def _real_calls_by_index(bc, planned_indices: list[int]) -> dict[int, Any]:
    """`bc.instructions`'s own CALLs, keyed by their REAL `call_sequence`
    index -- the exact transformation `oracle_common.run_static_calls`
    performs internally to build its `real_origin` map (never a second,
    independently-derived gating decision: `planned_indices`/`bc` both come
    straight from the SAME `LOWERED_SINK` firing this function's caller
    already correlated against `FINDINGS_SINK`).
    """
    origin = bc.sideband.get("origin", {})
    out: dict[int, Any] = {}
    for pc, instr in enumerate(bc.instructions):
        if not isinstance(instr, _ir.Call):
            continue
        local_idx = origin.get(pc)
        if local_idx is None or local_idx == "setup":
            continue
        out[planned_indices[int(local_idx)]] = instr
    return out


def collect_executed_population(
    *,
    corpus: list[str],
    sidecar: str | None,
    crosscheck: list[str],
    contracts: Path,
    limit: int | None,
    replay_report_path: Path,
) -> tuple[list[ExecutedOp], dict[str, Any]]:
    """Runs `oracle_replay.main()` UNMODIFIED -- the SAME technique
    `unknown_ledger.py.build_ledger` already uses for the identical reason
    (never re-implement `run_row`'s own gating) -- installing FINDINGS_SINK
    and LOWERED_SINK side by side so both fire, in lockstep, exactly once
    per row that reaches `run_static_calls` (`oracle_replay.run_row`'s
    "Static" section). Returns `(ops, diagnostics)`.
    """
    collected_findings: list[tuple[str, tuple[Any, ...]]] = []
    collected_lowered: list[tuple[str, Any, Any, list[int], dict[str, Any]]] = []

    def _findings_sink(row_id: str, findings: tuple[Any, ...]) -> None:
        collected_findings.append((row_id, findings))

    def _lowered_sink(row_id: str, bc: Any, bc_with_o1: Any, not_planned: list[int], element_types: dict[str, Any]) -> None:
        collected_lowered.append((row_id, bc, bc_with_o1, not_planned, element_types))

    argv: list[str] = []
    for c in corpus:
        argv += ["--corpus", str(c)]
    if sidecar:
        argv += ["--sidecar", str(sidecar)]
    for cc in crosscheck:
        argv += ["--crosscheck", str(cc)]
    argv += ["--contracts", str(contracts)]
    if limit is not None:
        argv += ["--limit", str(limit)]
    argv += ["--report", str(replay_report_path)]

    prior_findings_sink, prior_lowered_sink = oc.FINDINGS_SINK, oc.LOWERED_SINK
    oc.FINDINGS_SINK = _findings_sink
    oc.LOWERED_SINK = _lowered_sink
    try:
        oracle_replay.main(argv)
    finally:
        oc.FINDINGS_SINK = prior_findings_sink
        oc.LOWERED_SINK = prior_lowered_sink

    replay_report = json.loads(replay_report_path.read_text(encoding="utf-8"))
    static_eligible_rows = [
        r for r in replay_report["rows"]
        if r.get("no_call_reason") is None and r.get("skip_reason") is None
    ]
    if not (len(static_eligible_rows) == len(collected_findings) == len(collected_lowered)):
        raise RuntimeError(
            "positional correlation invariant broken (mirrors unknown_ledger.build_ledger's "
            f"identical check): {len(static_eligible_rows)} rows reached oracle_replay's "
            f"Static section, FINDINGS_SINK fired {len(collected_findings)} times, "
            f"LOWERED_SINK fired {len(collected_lowered)} times -- all three must match 1:1 "
            "in row order; oracle_replay.py's own row-processing order must have changed "
            "under this script."
        )

    ops: list[ExecutedOp] = []
    n_heterogeneous_parent_observations = 0
    for row_idx, (report_row, (_fid, findings), (_lid, bc, bc_with_o1, not_planned, element_types)) in enumerate(
        zip(static_eligible_rows, collected_findings, collected_lowered)
    ):
        record_id = report_row.get("record_id", "")
        methods = report_row.get("calls", [])
        planned_indices = [i for i in range(len(methods)) if i not in set(not_planned)]
        real_calls = _real_calls_by_index(bc, planned_indices)
        real_calls_with_o1 = _real_calls_by_index(bc_with_o1, planned_indices)
        slot_to_resource = {instr.slot: instr for instr in bc.instructions if isinstance(instr, _ir.Resource)}
        slot_to_resource_with_o1 = {
            instr.slot: instr for instr in bc_with_o1.instructions if isinstance(instr, _ir.Resource)
        }
        n_heterogeneous_parent_observations += sum(1 for v in element_types.values() if v is None)

        per_op_findings: dict[str, list[Any]] = collections.defaultdict(list)
        for f in findings:
            per_op_findings[f.operation_id].append(f)
        for op_id in per_op_findings:
            try:
                real_idx = int(op_id.split("_", 1)[1])
            except (IndexError, ValueError):
                continue
            if real_idx not in real_calls or real_idx not in real_calls_with_o1:
                # Should not occur: every op_id FINDINGS_SINK saw is a real
                # (non-setup) op that run_static_calls itself relabelled;
                # published defensively rather than assumed.
                log.warning("row %d op %s has findings but no lowered Call (real_idx=%d)", row_idx, op_id, real_idx)
                continue
            method = methods[real_idx] if real_idx < len(methods) else "<unknown>"
            ops.append(
                ExecutedOp(
                    row_idx=row_idx,
                    record_id=record_id,
                    op_id=op_id,
                    real_idx=real_idx,
                    method=method,
                    call=real_calls[real_idx],
                    call_with_o1=real_calls_with_o1[real_idx],
                    slot_to_resource=slot_to_resource,
                    slot_to_resource_with_o1=slot_to_resource_with_o1,
                )
            )
    diagnostics = {
        "n_rows_static_eligible": len(static_eligible_rows),
        "n_ops_executed": len(ops),
        "n_ops_executed_by_method": dict(
            sorted(collections.Counter(op.method for op in ops).items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "n_heterogeneous_parent_observations": n_heterogeneous_parent_observations,
    }
    return ops, diagnostics


# ---------------------------------------------------------------------------
# The per-call operand resolver (NOT the T31 evaluator -- see module docstring)
# ---------------------------------------------------------------------------


def _has_isinstance(pred: Predicate) -> bool:
    if isinstance(pred, IsInstance):
        return True
    if isinstance(pred, Not):
        return _has_isinstance(pred.predicate)
    if isinstance(pred, (And, Or)):
        return any(_has_isinstance(p) for p in pred.predicates)
    if isinstance(pred, (AllOf, AnyOf)):
        return _has_isinstance(pred.predicate)
    return False


def _resolve_name(
    name: str,
    call: _ir.Call | None,
    param_defaults: dict[str, Any],
    bindings_by_name: dict[str, dict[str, Any]],
    depth: int,
    channel_names: set[str],
    channel_kwarg: str | None = None,
) -> tuple[bool, str | None]:
    """Returns (resolved?, how) -- `how` in {"binding", "channel", "kwarg",
    "default"}. A binding resolves `name` only if its OWN iterand ALSO
    resolves (recursively, via this same function with an EMPTY bindings
    map for the iterand -- it is a raw parameter reference, never itself
    bound) -- the rule that makes `:875`'s `not_containers` at depth 1
    `guard_env_dependent`, not `guard_operand_unknown` (§15.4's own worked
    example).

    **`channel_names` vs `channel_kwarg`, and why depth >= 1 uses only the
    latter.** `channel_names` (`channel_kwarg` UNION every
    `channel_default_param` VALUE across every method) is the right set for
    a DEPTH-0 free name -- a method's own P3a fallback param genuinely
    resolves that method's own `use_channels`. It is the WRONG set at
    depth >= 1: `channel_default_param["aspirate"] == "resources"` names
    `aspirate`'s OWN parameter, and `_check_containers`'s unrelated
    `resources` parameter (a list of containers, not a channel count) is a
    pure STRING coincidence with it -- treating the coincidence as
    resolution would be exactly the "resolves only because two unrelated
    names happen to match" bug E-CALL(depth) exists to forbid. Only
    `channel_kwarg` itself (the literal keyword PLR uses to select channels
    explicitly, e.g. `"use_channels"`) is legitimately depth-independent.
    """
    if name in bindings_by_name:
        b = bindings_by_name[name]
        iterand = b["iter"] if b["idiom"] == "alpha" else b["param"]
        iterand_ok, iterand_how = _resolve_name(iterand, call, param_defaults, {}, depth, channel_names, channel_kwarg)
        if not iterand_ok:
            return False, None
        return True, "binding"
    if depth >= 1:
        if channel_kwarg is not None and name == channel_kwarg:
            return True, "channel"
        return False, None
    if call is not None and name in call.kwargs:
        return True, "kwarg"
    if name in param_defaults:
        return True, "default"
    if name in channel_names:
        return True, "channel"
    return False, None


def _element_ref_type(value: _ir.Value, slot_to_resource: dict[int, _ir.Resource]) -> str | None:
    if isinstance(value, _ir.Ref):
        res = slot_to_resource.get(value.slot)
        if res is None:
            return None
        return res.element_type if value.cell is not None else res.type
    return None


def classify_guard_for_call(
    g: dict[str, Any],
    call: _ir.Call,
    slot_to_resource: dict[int, _ir.Resource],
    param_defaults: dict[str, Any],
    channel_names: set[str],
    channel_kwarg: str | None = None,
) -> str:
    """A STATIC classification of what E-CALL WOULD resolve for `g` against
    `call` -- never an evaluation of truth (§15.9's own framing). See the
    module docstring for what this model does and does not implement.

    §15.7's REORDERED reason rule (round 2, A-C5, T35): (1) `contains_opaque`
    over the alpha/beta-SUBSTITUTED tree -> `guard_predicate_unparsed`;
    (2) an operand of THIS call is Top -> `guard_operand_unknown`, checked
    BEFORE (3) so the amendment cannot relax the gate's OTHER zero-condition;
    (3) `contains_env_ref` over the substituted tree, still undecided ->
    `guard_env_dependent`; (4) otherwise the pre-amendment rule stands (an
    unresolved free name -> `guard_env_dependent`; everything resolved and
    no Top operand -> `decidable`).
    """
    pred = from_json(g["predicate"])
    bindings_by_name = {b["x"]: b for b in g.get("bindings", ())}
    substituted = substitute(pred, bindings_by_name)
    if contains_opaque(substituted):
        return REASON_UNPARSED
    if g.get("raises") and str(g["raises"]).startswith("<dynamic:"):
        return REASON_ENV
    depth = g["depth"]
    free_names = free_var_names(pred)
    resolved_how: dict[str, str] = {}
    any_unresolved = False
    for name in free_names:
        ok, how = _resolve_name(name, call, param_defaults, bindings_by_name, depth, channel_names, channel_kwarg)
        if not ok:
            any_unresolved = True
            continue
        resolved_how[name] = how

    operand_unknown = False
    for name, how in resolved_how.items():
        if how == "kwarg":
            v = call.kwargs.get(name)
            if isinstance(v, _ir.Top):
                operand_unknown = True
        elif how == "binding":
            b = bindings_by_name[name]
            if b["idiom"] != "alpha":
                continue  # a beta binding is a LENGTH fact; Len is always resolvable once the iterand is.
            inner_pred = from_json(b["pred"])
            if not _has_isinstance(inner_pred):
                continue
            iterand = b["iter"]
            iterand_value = call.kwargs.get(iterand) if depth == 0 else None
            if iterand_value is None:
                # depth >= 1 -- resolved only via the channel term, which
                # carries no per-element type information at all.
                operand_unknown = True
                continue
            if isinstance(iterand_value, _ir.Top):
                operand_unknown = True
            elif isinstance(iterand_value, _ir.Seq):
                for item in iterand_value.items:
                    if isinstance(item, _ir.Top):
                        operand_unknown = True
                    elif isinstance(item, _ir.Ref):
                        if _element_ref_type(item, slot_to_resource) is None:
                            operand_unknown = True
    if operand_unknown:
        return REASON_OPERAND
    if contains_env_ref(substituted):
        return REASON_ENV
    if any_unresolved:
        return REASON_ENV
    return REASON_DECIDABLE


def classify_guard_structural(
    g: dict[str, Any],
    K_params: frozenset[str],
    channel_names: set[str],
    channel_kwarg: str | None = None,
) -> tuple[bool, bool, str]:
    """Block (3)'s per-cluster classification -- NO specific call, so
    "operand of this call" cannot be assessed; guards that would need a
    concrete call to decide land in `"decidable_or_operand_dependent"`
    rather than being forced into either `decidable` or `guard_operand_unknown`
    on no evidence. Returns `(parsed, bound, reason)`:

    * `parsed` -- the RAW top-level predicate is non-`Opaque` (G0/G1's
      parse result alone, ignoring the nested-binding extension).
    * `bound` -- every free LOCAL (a free `Var` name that is NOT a
      parameter of `g`'s own defining function `K`) has a binding entry.
    * `reason` -- the mechanical §15.7 reason this guard would carry,
      to the extent decidable without a call.
    """
    pred = from_json(g["predicate"])
    parsed = not contains_opaque(pred)
    bindings_by_name = {b["x"]: b for b in g.get("bindings", ())}
    substituted = substitute(pred, bindings_by_name)
    free_names = free_var_names(pred)
    free_locals = [n for n in free_names if n not in K_params]
    bound = all(n in bindings_by_name for n in free_locals) if free_locals else True

    if contains_opaque(substituted):
        return parsed, bound, REASON_UNPARSED
    if g.get("raises") and str(g["raises"]).startswith("<dynamic:"):
        return parsed, bound, REASON_ENV
    depth = g["depth"]
    for name in free_names:
        if name in bindings_by_name:
            b = bindings_by_name[name]
            iterand = b["iter"] if b["idiom"] == "alpha" else b["param"]
            if depth >= 1 and iterand != channel_kwarg:
                return parsed, bound, REASON_ENV  # the binding's own iterand can never resolve at depth>=1.
            continue
        if depth >= 1:
            if channel_kwarg is not None and name == channel_kwarg:
                continue
            return parsed, bound, REASON_ENV
        # depth 0: resolvable IN PRINCIPLE iff it is a real parameter of K
        # (so SOME call could supply it) -- whether THIS call does is
        # block (4)'s question, not this structural one.
        if name in K_params or name in channel_names:
            continue
        return parsed, bound, REASON_ENV
    # §15.7's reordered clause (3), round 2 A-C5: no concrete call exists at
    # this block's own granularity, so `guard_operand_unknown` (clause 2)
    # cannot be assessed here at all -- the terminal
    # "decidable_or_operand_dependent" already covers "clause 2 might fire
    # once a real call is known" (block (4)'s job). `contains_env_ref` is
    # therefore checked LAST among the reasons this function CAN assign,
    # ahead only of that catch-all.
    if contains_env_ref(substituted):
        return parsed, bound, REASON_ENV
    return parsed, bound, "decidable_or_operand_dependent"


# ---------------------------------------------------------------------------
# Block 3 -- per ledger cluster
# ---------------------------------------------------------------------------


def _env_ref_nodes_and_paths(g: dict[str, Any]) -> tuple[int, list[str]]:
    """S15.9 block (3)'s amendment additions for ONE guard: `n_env_ref_nodes`
    (the number of `EnvRef` NODES in its alpha/beta-SUBSTITUTED predicate)
    and the dotted paths themselves (round 2, A-C4: both range over the
    substituted tree, never the raw `predicate` field)."""
    pred = from_json(g["predicate"])
    bindings_by_name = {b["x"]: b for b in g.get("bindings", ())}
    substituted = substitute(pred, bindings_by_name)
    n_nodes = count_env_ref_nodes(substituted)
    paths = [".".join(n.path) for n in walk_predicate(substituted) if isinstance(n, EnvRef)]
    return n_nodes, paths


def measure_per_cluster(
    ledger: dict[str, Any],
    guard_index: dict[tuple[str, int, str], dict[str, Any]],
    param_names_by_qualname: dict[tuple[str, str], frozenset[str]],
    channel_names: set[str],
    receiver_state: dict[str, Any],
    volume_guard_sites: frozenset[tuple[str, int, str]] = frozenset(),
) -> list[dict[str, Any]]:
    out = []
    for cluster in ledger["clusters"]:
        site = cluster["plr_site"]
        row: dict[str, Any] = {
            "reason_ledger": cluster["reason"],
            "plr_site": site,
            "condition": cluster["condition"],
            "n_ops_blocked": cluster["n_ops_blocked"],
        }
        if site == "<none>":
            row["predicted_tier"] = "out of scope (unresolved_delegate, deferred row (e))"
            row["parsed"] = None
            row["bound"] = None
            row["reason_measured"] = "n/a (not a guard)"
            row["n_env_ref_nodes"] = 0
            row["env_ref_paths"] = []
            out.append(row)
            continue
        file, lineno_s, qualname = site.split(":")
        lineno = int(lineno_s)
        basename = Path(file).stem + ".py"
        row["predicted_tier"] = PREDICTED_TIER.get(
            (basename, lineno), "not individually tabulated in spec 260904 sec15.1"
        )
        g = guard_index.get((file, lineno, qualname))
        if g is None:
            row["parsed"] = None
            row["bound"] = None
            row["reason_measured"] = "guard not found in contract table (unexpected)"
            row["n_env_ref_nodes"] = 0
            row["env_ref_paths"] = []
            out.append(row)
            continue
        if is_tip_family_owned(g, receiver_state):
            row["parsed"] = None
            row["bound"] = None
            row["reason_measured"] = "tip_family_owned (already resolved by the shipped tipstate family, not this increment's business)"
            row["n_env_ref_nodes"] = 0
            row["env_ref_paths"] = []
            out.append(row)
            continue
        if is_volume_family_owned(g, volume_guard_sites):
            row["parsed"] = None
            row["bound"] = None
            row["reason_measured"] = "volume_family_owned (already resolved by increment 5's volume bridge, not this increment's business)"
            row["n_env_ref_nodes"] = 0
            row["env_ref_paths"] = []
            out.append(row)
            continue
        module = module_from_plr_file(file)
        K_params = param_names_by_qualname.get((module, qualname), frozenset()) if module else frozenset()
        channel_kwarg = receiver_state.get("LiquidHandler", {}).get("channel_kwarg")
        parsed, bound, reason = classify_guard_structural(g, K_params, channel_names, channel_kwarg)
        row["parsed"] = parsed
        row["bound"] = bound
        row["reason_measured"] = reason
        n_env_ref_nodes, env_ref_paths = _env_ref_nodes_and_paths(g)
        row["n_env_ref_nodes"] = n_env_ref_nodes
        row["env_ref_paths"] = env_ref_paths
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# Blocks 4/5 -- per executed operation, with/without O1
# ---------------------------------------------------------------------------


def measure_per_op(
    ops: list[ExecutedOp],
    contracts: dict[str, Any],
    channel_names: set[str],
    receiver_state: dict[str, Any],
    volume_guard_sites: frozenset[tuple[str, int, str]] = frozenset(),
) -> dict[str, Any]:
    """Blocks 4/5's per-executed-operation residuals, with and without O1 --
    now driven entirely by the authoritative `ops` population
    (`collect_executed_population`, #4978) instead of a second local row
    loop: `guard_index`/`contracts_json`/`corpus_path`/`limit` are no longer
    needed here (the lowering and row/op gating already happened once,
    inside `oracle_replay.main()`, to build `ops`). The per-call
    classification logic itself (`classify_guard_for_call`, tier-family
    exclusion, predicted-tier lookup) is UNCHANGED from before this fix --
    only its data source is.
    """
    per_op: list[dict[str, Any]] = []
    per_op_without_o1: list[dict[str, Any]] = []
    channel_kwarg = receiver_state.get("LiquidHandler", {}).get("channel_kwarg")
    param_defaults_cache: dict[str, dict[str, Any]] = {}

    for op in ops:
        method = op.method
        contract_key = f"{op.call.receiver_type}.{method}"
        entry = contracts.get(contract_key)
        if entry is None:
            entry = next(
                (
                    v
                    for k, v in contracts.items()
                    if k.startswith(f"{op.call.receiver_type}.{method}") and "@" not in k
                ),
                None,
            )
        if entry is None:
            continue
        if method not in param_defaults_cache:
            param_defaults_cache[method] = entry.get("param_defaults", {})
        param_defaults = param_defaults_cache[method]

        for observe, sink, call, slot_to_resource in (
            (True, per_op, op.call_with_o1, op.slot_to_resource_with_o1),
            (False, per_op_without_o1, op.call, op.slot_to_resource),
        ):
            reasons_this_op: set[str] = set()
            n_parsed_but_operand_unknown = 0
            n_tip_family_owned = 0
            n_volume_family_owned = 0
            n_env_ref_guards = 0
            applicable_guards = []
            for g in entry.get("guards", ()):
                if is_tip_family_owned(g, receiver_state):
                    n_tip_family_owned += 1
                    continue
                if is_volume_family_owned(g, volume_guard_sites):
                    n_volume_family_owned += 1
                    continue
                applicable_guards.append(g)
                reason = classify_guard_for_call(g, call, slot_to_resource, param_defaults, channel_names, channel_kwarg)
                reasons_this_op.add(reason)
                if reason == REASON_OPERAND:
                    n_parsed_but_operand_unknown += 1
                # S15.9 block (4)'s amendment addition: `n_env_ref` is a
                # PER-GUARD count -- the number of guards on this operation
                # whose alpha/beta-SUBSTITUTED predicate contains >= 1
                # EnvRef node (round 2, A-C8: this block's `n_env_ref` and
                # block (3)'s `n_env_ref_nodes` are deliberately different
                # names in different units -- `:2055` is one guard, two
                # nodes).
                pred = from_json(g["predicate"])
                bindings_by_name = {b["x"]: b for b in g.get("bindings", ())}
                if contains_env_ref(substitute(pred, bindings_by_name)):
                    n_env_ref_guards += 1
            if not applicable_guards:
                reasons_this_op.add("no_contract_derived")
            predicted_tiers = sorted(
                {
                    PREDICTED_TIER.get((Path(g["site"]["file"]).stem + ".py", g["site"]["lineno"]), "?")
                    for g in applicable_guards
                }
            )
            sink.append(
                {
                    "row_idx": op.row_idx,
                    "record_id": op.record_id,
                    "op_id": op.op_id,
                    "method": method,
                    "reasons": sorted(reasons_this_op),
                    "predicted_tiers": predicted_tiers,
                    "n_parsed_but_operand_unknown": n_parsed_but_operand_unknown,
                    "n_tip_family_owned_guards": n_tip_family_owned,
                    "n_volume_family_owned_guards": n_volume_family_owned,
                    "n_env_ref": n_env_ref_guards,
                    # An evaluator number (S15.4 E-ENV's Kleene short-circuit
                    # path) -- this script builds NO evaluator and calls
                    # check_ir nowhere (module docstring); publishing it
                    # honestly as not-computable-here rather than a fabricated
                    # 0, per the T35 task brief's own instruction. T31 is
                    # where a real value can be measured.
                    "n_decided_via_env_ref_shortcircuit": None,
                }
            )
    return {
        "per_op": per_op,
        "per_op_without_o1": per_op_without_o1,
        "n_ops": len(per_op),
    }


# ---------------------------------------------------------------------------
# Block 6 -- the amendment's own whole-table surface (S15.9, new 260907;
# n_env_ref_refused_plr_layer new in round 2, A-C1).
# ---------------------------------------------------------------------------


def measure_env_ref_surface(
    contracts: dict[str, Any],
    receiver_state: dict[str, Any],
    qualname_index: frozenset[tuple[str, str]] | None,
    volume_guard_sites: frozenset[tuple[str, int, str]],
) -> dict[str, Any]:
    """S15.9 block (6): the amendment's own surface, over the WHOLE contract
    table (each DISTINCT guard site counted once, tip/volume-family-owned
    guards excluded -- not this increment's business either way).

    `n_env_ref_refused_plr_layer` is measured by RE-PARSING each guard's raw
    `condition` through the pure grammar (`predicate_ast.parse`, which knows
    nothing about the index and therefore admits every syntactically-valid
    self-rooted call), then re-running the SAME index test
    `derive.bindings.demote_refused_env_refs` applied at derive time against
    every length-2 shape-(2) `EnvRef` candidate found -- never a diff against
    the shipped (already-demoted) `predicate` field, which cannot
    distinguish "refused" from "never admitted at all".
    """
    n_zip = 0
    n_membership_cmp = 0
    n_var_self = 0
    n_opaque_only_by_var_self = 0
    n_env_ref_guards = 0
    n_env_ref_nodes = 0
    n_env_ref_refused_plr_layer = 0
    path_counts: collections.Counter = collections.Counter()
    seen_sites: set[tuple[str, int, str]] = set()

    for entry in contracts.values():
        for g in entry.get("guards", ()):
            site = g["site"]
            key = (site["file"], site["lineno"], site["qualname"])
            if key in seen_sites:
                continue
            seen_sites.add(key)
            if is_tip_family_owned(g, receiver_state) or is_volume_family_owned(g, volume_guard_sites):
                continue

            shipped_pred = from_json(g["predicate"])
            n_var_self += count_var_self(shipped_pred)
            nodes = walk_predicate(shipped_pred)
            n_zip += sum(1 for n in nodes if isinstance(n, Zip))
            n_membership_cmp += sum(1 for n in nodes if isinstance(n, Cmp) and n.op in MEMBERSHIP_OPS)
            env_refs = [n for n in nodes if isinstance(n, EnvRef)]
            if env_refs:
                n_env_ref_guards += 1
            n_env_ref_nodes += len(env_refs)
            for er in env_refs:
                path_counts[".".join(er.path)] += 1

            # n_opaque_only_by_var_self: this guard is Opaque only BECAUSE
            # the Var("self") invariant fired -- detected by comparing the
            # shipped (invariant-enforcing) parse against the CLOSED
            # negative list otherwise excluding it; a guard whose raw
            # condition round-trips through the same shape but for a
            # different reason (a genuinely unrecognised construct) would
            # ALSO be Opaque with or without the invariant, so this only
            # counts the guard when re-parsing shows the ONLY difference is
            # a bare `self` occurrence outside an EnvRef path. Predicted 0
            # at this pin (S15.9 block (6)).
            if isinstance(shipped_pred, Opaque) and _opaque_only_because_of_var_self(g.get("condition")):
                n_opaque_only_by_var_self += 1

            # n_env_ref_refused_plr_layer: re-parse the RAW condition (no
            # index knowledge at all) and re-apply the SAME index test.
            module = module_from_plr_file(site["file"])
            qualname = site["qualname"]
            class_name = qualname.split(".", 1)[0] if "." in qualname else None
            raw_pred = parse_predicate_raw(g.get("condition"))
            for n in walk_predicate(raw_pred):
                if not (isinstance(n, EnvRef) and n.args is not None and len(n.path) == 2):
                    continue
                name = n.path[1]
                refused = (
                    True
                    if qualname_index is None
                    else is_plr_layer_method(qualname_index, module, class_name, name)
                    if module is not None
                    else False
                )
                if refused:
                    n_env_ref_refused_plr_layer += 1

    top10 = [{"path": p, "n": n} for p, n in path_counts.most_common(10)]
    return {
        "n_zip": n_zip,
        "n_membership_cmp": n_membership_cmp,
        "n_var_self": n_var_self,
        "n_opaque_only_by_var_self": n_opaque_only_by_var_self,
        "n_env_ref_guards": n_env_ref_guards,
        "n_env_ref_nodes": n_env_ref_nodes,
        "n_env_ref_refused_plr_layer": n_env_ref_refused_plr_layer,
        "top10_env_ref_paths": top10,
    }


def _opaque_only_because_of_var_self(condition: str | None) -> bool:
    """Best-effort, conservative check for `n_opaque_only_by_var_self`: a
    reparse-based diagnostic, not a full dual-parse (this module's `parse`
    bakes the Var("self") invariant in unconditionally, so there is no
    "permissive" mode to diff against without duplicating the whole grammar
    module) -- narrowed to the one syntactic shape the invariant actually
    intercepts that nothing else already rejects: a bare `self` token used
    as a `Cmp`/`Is`/`IsInstance` OPERAND (not inside a `self.<attr>` chain
    and not as a call argument, which is already Opaque for an independent
    reason -- an unrecognised callee -- in every real case on this
    benchmark). Never load-bearing: predicted 0 at this pin and published
    as a diagnostic, not gated on.
    """
    if condition is None:
        return False
    try:
        tree = ast.parse(condition, mode="eval")
    except (SyntaxError, ValueError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for i, operand in enumerate(operands):
                if isinstance(operand, ast.Name) and operand.id == "self":
                    return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance":
            if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "self":
                return True
    return False


def summarize_n_env_ref_by_method(per_op: list[dict[str, Any]]) -> dict[str, Any]:
    """S15.9 block (4)'s `n_env_ref` (per-guard count) and
    `n_decided_via_env_ref_shortcircuit`, aggregated per method for the
    re-prediction table's own cross-check -- every op of a given method
    carries the SAME guard set (O1 only changes RESOURCE typing, never
    which guards apply), so `n_env_ref` is expected constant per method;
    published as the observed set (never collapsed to a single number
    silently) so a real divergence is visible rather than averaged away."""
    by_method: dict[str, set[int]] = collections.defaultdict(set)
    shortcircuit_by_method: dict[str, set[Any]] = collections.defaultdict(set)
    for op in per_op:
        by_method[op["method"]].add(op["n_env_ref"])
        shortcircuit_by_method[op["method"]].add(op["n_decided_via_env_ref_shortcircuit"])
    return {
        method: {
            "n_env_ref_observed": sorted(vals),
            "n_decided_via_env_ref_shortcircuit_observed": sorted(shortcircuit_by_method[method], key=str),
        }
        for method, vals in by_method.items()
    }


def summarize_by_method(per_op: list[dict[str, Any]]) -> dict[str, Any]:
    by_method: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    ops_clearing: dict[str, list[str]] = collections.defaultdict(list)
    for op in per_op:
        method = op["method"]
        reason_set = tuple(sorted(op["reasons"]))
        by_method[method][reason_set] += 1
        if REASON_UNPARSED not in op["reasons"] and REASON_OPERAND not in op["reasons"]:
            ops_clearing[method].append(op["op_id"])
    return {
        method: {
            "residual_reason_sets": {"+".join(rs) if rs else "(empty)": n for rs, n in counter.items()},
            "n_ops_clearing_gate": len(ops_clearing.get(method, [])),
            "example_ops_clearing": ops_clearing.get(method, [])[:10],
        }
        for method, counter in by_method.items()
    }


def compute_gate(per_op: list[dict[str, Any]]) -> dict[str, Any]:
    clearing = [
        op for op in per_op if REASON_UNPARSED not in op["reasons"] and REASON_OPERAND not in op["reasons"]
    ]
    return {
        "go": len(clearing) >= 1,
        "n_ops_clearing": len(clearing),
        "example_ops_clearing": [op["op_id"] + "@" + op["record_id"] for op in clearing[:20]],
        "methods_clearing": sorted({op["method"] for op in clearing}),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=REPO_ROOT / "training" / "assemble" / "out" / "corpus_p25.jsonl")
    ap.add_argument(
        "--sidecar", type=str, default=None,
        help="assemble sidecar JSONL (record_id, ambiguity_class, provenance); pass-through to "
             "oracle_replay.main() -- REQUIRED to reproduce the frozen tier1-sidecar-gated benchmark's "
             "own population (#4978: omitting it silently admits non-clean_parse rows run_row would skip)",
    )
    ap.add_argument(
        "--crosscheck", type=str, action="append", default=[],
        help="floor/overlay crosscheck file (repeatable); pass-through to oracle_replay.main()",
    )
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument(
        "--ledger", type=Path, default=REPO_ROOT / "outputs" / "plr-sema" / "unknown_ledger_260904_before.json"
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--replay-report", type=Path, default=None,
        help="where to write oracle_replay's OWN report (default: <out>.oracle_replay.json, alongside --out)",
    )
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    contracts_payload = json.loads(args.contracts.read_text(encoding="utf-8"))
    contracts = contracts_payload["contracts"]
    receiver_state = contracts_payload.get("receiver_state", {})
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))

    lh_state = receiver_state.get("LiquidHandler", {})
    channel_names: set[str] = set(lh_state.get("channel_default_param", {}).values())
    if lh_state.get("channel_kwarg"):
        channel_names.add(lh_state["channel_kwarg"])

    log.info("building whole-tree function index (param names by qualname)...")
    function_index = build_plr_function_index(oc.REPO_ROOT / "external" / "pylabrobot" / "pylabrobot")
    param_names_by_qualname = build_param_names_by_qualname(function_index)
    # G7's PLR-layer test (round 2, A-C1) -- the SAME reduced index
    # derive_contract built at contract-regeneration time; re-derived here
    # (never persisted on the wire) so block 6's refusal count is measured
    # against the identical rule, not assumed to match it.
    qualname_index = build_qualname_index(function_index)
    volume_guard_sites = build_volume_guard_sites(contracts)

    log.info("block 1: parse coverage")
    block1 = measure_parse_coverage(contracts, receiver_state, volume_guard_sites)

    log.info("block 2: binding coverage")
    block2 = measure_binding_coverage(
        contracts, param_names_by_qualname, receiver_state, function_index, volume_guard_sites
    )

    replay_report_path = args.replay_report or args.out.with_name(args.out.stem + ".oracle_replay.json")
    replay_report_path.parent.mkdir(parents=True, exist_ok=True)
    log.info(
        "collecting the executed-op population via oracle_replay.main() (FINDINGS_SINK + LOWERED_SINK, #4978)"
    )
    ops, population_diagnostics = collect_executed_population(
        corpus=[str(args.corpus)],
        sidecar=args.sidecar,
        crosscheck=args.crosscheck,
        contracts=args.contracts,
        limit=args.limit,
        replay_report_path=replay_report_path,
    )
    log.info(
        "population: n_ops_executed=%d by_method=%s",
        population_diagnostics["n_ops_executed"], population_diagnostics["n_ops_executed_by_method"],
    )

    log.info("D2: channels_for_call over executed pick_up_tips ops")
    d2 = measure_d2(ops, receiver_state)
    block2["d2"] = d2

    guard_index = build_guard_index(contracts, prefer_public_entry=True)

    log.info("block 3: per-cluster classification (%d clusters)", len(ledger["clusters"]))
    block3 = measure_per_cluster(
        ledger, guard_index, param_names_by_qualname, channel_names, receiver_state, volume_guard_sites
    )

    log.info("blocks 4/5: per-executed-operation residuals, with and without O1")
    per_op_result = measure_per_op(ops, contracts, channel_names, receiver_state, volume_guard_sites)
    block4 = summarize_by_method(per_op_result["per_op"])
    block4_without_o1 = summarize_by_method(per_op_result["per_op_without_o1"])

    log.info("block 6: the amendment's own whole-table surface (EnvRef/Zip/membership/Var(self))")
    block6 = measure_env_ref_surface(contracts, receiver_state, qualname_index, volume_guard_sites)

    gate_with_o1 = compute_gate(per_op_result["per_op"])
    gate_without_o1 = compute_gate(per_op_result["per_op_without_o1"])

    o1_delta_ops = sum(
        1
        for with_o1, without_o1 in zip(per_op_result["per_op"], per_op_result["per_op_without_o1"])
        if with_o1["reasons"] != without_o1["reasons"]
    )

    result = {
        "benchmark": BENCHMARK_NAME,
        "corpus": str(args.corpus),
        "sidecar": args.sidecar,
        "crosscheck": args.crosscheck,
        "contracts": str(args.contracts),
        "limit": args.limit,
        "population": population_diagnostics,
        "block1_parse_coverage": block1,
        "block2_binding_coverage": block2,
        "block3_per_cluster": block3,
        "block4_per_op_with_o1": {
            "n_ops": per_op_result["n_ops"],
            "by_method": block4,
            # Per-guard n_env_ref and the (unbuilt-evaluator) shortcircuit
            # count, published per operation -- AC-15.3 requires these
            # present and non-null (the latter is null BY DESIGN: no
            # evaluator exists in this script, S15.4 E-ENV's Kleene
            # short-circuit path is T31's number, see per_op's own field
            # docstring in measure_per_op).
            "per_op": per_op_result["per_op"],
            "n_env_ref_by_method": summarize_n_env_ref_by_method(per_op_result["per_op"]),
        },
        "block4_per_op_without_o1": {
            "by_method": block4_without_o1,
            "per_op": per_op_result["per_op_without_o1"],
            "n_env_ref_by_method": summarize_n_env_ref_by_method(per_op_result["per_op_without_o1"]),
        },
        "block5_o1_delta": {
            "n_ops_differing": o1_delta_ops,
            "n_heterogeneous_parent_observations": population_diagnostics["n_heterogeneous_parent_observations"],
        },
        "block6_env_ref_surface": block6,
        "gate": {
            "with_o1": gate_with_o1,
            "without_o1": gate_without_o1,
        },
        "scope_notes": [
            "This script constructs no verdict and never calls check_ir; T31 (the evaluator) does not exist yet.",
            "classify_guard_for_call/classify_guard_structural are a STATIC classification of what E-CALL "
            "would resolve, not a truth evaluation -- see the module docstring for exactly which E-CALL "
            "mechanisms are modelled (the recursive binding/iterand resolution, the channel term via a real "
            "channels_for_call import, per-element IsInstance resolution against O1's element_type) and which "
            "are not (chained-Cmp short-circuit truth, G4 set-value comparison, numeric interval folding).",
            "predicted_tier is transcribed from spec 260904's own SS15.1 tables for the sites it names; every "
            "other cluster is published as 'not individually tabulated', never guessed.",
            "(#4978, T32 fix-up) The executed-op population is now sourced from oracle_replay.main() itself "
            "(FINDINGS_SINK + LOWERED_SINK), the SAME technique unknown_ledger.py uses -- never a local "
            "re-implementation of row_to_verifier_inputs/run_runtime/lower_row_calls's own skip/no_call/sidecar "
            "gating. The PRE-#4978 version of this script re-implemented that gating directly and never threaded "
            "the sidecar's ambiguity_class/provenance through row_to_verifier_inputs, so it silently admitted "
            "every non-'clean_parse' row (missing_slot/ambiguous_referent/out_of_surface) run_row would have "
            "skipped -- 923 executed ops (361 pick_up_tips) measured 260905 against the correct 544 (223 "
            "pick_up_tips) unknown_ledger.py's own FINDINGS_SINK-derived population reports for the identical "
            "corpus/sidecar/crosscheck inputs. See `population` above for this run's own population and "
            "`collect_executed_population`'s docstring for the fix.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log.info("wrote %s", args.out)
    log.info(
        "GATE (with O1): go=%s n_ops_clearing=%d methods=%s",
        gate_with_o1["go"], gate_with_o1["n_ops_clearing"], gate_with_o1["methods_clearing"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

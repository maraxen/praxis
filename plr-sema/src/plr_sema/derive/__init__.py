"""plr_sema.derive: transitive-closure contract derivation (spec 260901 §7).

**Mechanics only** (§7 header). This module specifies graph plumbing over
data that already exists on disk (``training/verify/data/plr_preconditions.json``,
§7.1) plus one independent, second AST pass over PLR source itself. It
specifies no predicate semantics, no abstract domain, no loop handling --
``condition``/``scope_trail`` stay opaque strings (deferred item (c)).

**RISK-1 detector (§7.6).** This is the single biggest content-risk
detection mechanism in the whole document: whether closure over
``delegates_to`` recovers materially more preconditions than a method's own
body, or whether derivation is sound-but-empty. The gap ledger this module
builds is the measurement; see ``build_gap_ledger``.

**Independence (§1.4).** This module (and the rest of ``src/plr_sema``) must
not import ``praxis``, ``verify``, or ``training`` -- enforced by
``tests/test_import_boundary.py``, which scans the whole ``src/plr_sema``
tree including this package. The dropped-receiver AST pass below
(``scan_dropped_receiver_calls``) is a SECOND, INDEPENDENT stdlib-``ast``
walk over PLR source under ``external/`` -- it does not reuse the survey
JSON or import ``scripts/survey_plr_preconditions.py`` at all, by design
(§7.4's asymmetry note: the point is a measurement that doesn't share the
survey's own blind spot).

Contents:
  * ``SurveyRecord``/``SurveyFinding`` -- typed views of the survey JSON.
  * ``load_survey``/``build_index`` -- load + key by ``(module, qualname)``.
  * ``resolve`` -- bare delegate-name resolution (§7.2, C1), class-first.
  * ``InlinedGuard``/``DerivedContract``/``derive_contract`` -- the
    transitive closure mechanic itself (§7.2).
  * ``SUPPORTED_TOOLS``/``resolve_supported_tool`` -- the D22 derived
    name-to-key mapping for the 10-tool dynamic execution harness capability
    boundary (260901 T11: informational only now -- ``build_gap_ledger``'s
    ``supported_tools``-scoped reporting subset; no longer gates which
    methods get a contract, see ``build_derived_contracts_payload``).
  * ``build_contract_keys`` -- the whole-survey contract-table key
    disambiguator (260901 T11).
  * ``scan_dropped_receiver_calls`` and friends -- the independent D3 AST
    pass computing, per method, the honest and validation-looking
    dropped-receiver call-node counts.
  * ``build_gap_ledger`` -- the generated build artifact (§7.4).
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from plr_sema._provenance import SurveyStamp, survey_stamp
from plr_sema.check._supported_tools import SUPPORTED_TOOLS
from plr_sema.derive.bindings import (
    build_qualname_index,
    compute_caller_args,
    compute_caller_call_lineno,
    compute_caller_scope_trail,
    compute_local_bindings_for_guard,
    compute_reachability_clear,
    demote_refused_env_refs,
)
from plr_sema.derive.predicate_ast import Predicate, parse as parse_predicate
from plr_sema.telemetry import FAILURE_CATEGORIES
from plr_sema.verdict import PlrSite

__all__ = [
    "SCHEMA_VERSION",
    "SUPPORTED_TOOLS",
    "SurveyFinding",
    "DroppedCall",
    "SurveyRecord",
    "load_survey",
    "build_index",
    "build_unique_index",
    "build_contract_keys",
    "count_index_key_collisions",
    "resolve",
    "resolve_supported_tool",
    "InlinedGuard",
    "DerivedContract",
    "derive_contract",
    "ClassBasesIndex",
    "build_class_bases_index",
    "class_closure",
    "diagnose_base_resolution",
    "resolve_via_base_closure",
    "inherited_method_names",
    "compute_m_inh_selection",
    "measure_m_inh_entry_point_impact",
    "DroppedReceiverCounts",
    "scan_dropped_receiver_calls",
    "scan_dropped_receiver_calls_in_source",
    "build_gap_ledger",
    "default_plr_pkg_root",
]

SCHEMA_VERSION = 1

#: Re-exported from plr_sema.check._supported_tools (T8 consolidation, spec
#: 260901 §6.2's D1 note): check/ independently needs this same 10-tool
#: frozenset for the unsupported_tool reason, and check/'s own
#: import-boundary constraints (§1.3: no praxis/verify/training) mean it
#: cannot reach training.verify.dispatcher.SUPPORTED_TOOLS directly either.
#: Rather than a THIRD hand-typed copy (upstream + derive + check), this
#: module now imports the single in-package definition from
#: plr_sema.check._supported_tools, so `from plr_sema.derive import
#: SUPPORTED_TOOLS` keeps resolving to the exact same frozenset object. The
#: one live cross-package drift test against training.verify.dispatcher lives
#: at tests/test_check_graph.py::test_supported_tools_match_upstream --
#: not duplicated here.

#: Mirrors scripts/survey_plr_preconditions.py:107-109's
#: _is_validation_looking prefix list verbatim (lowercased prefix match).
_VALIDATION_LOOKING_PREFIXES: tuple[str, ...] = (
    "_check",
    "check_",
    "_assert",
    "assert_",
    "_validate",
    "validate",
)


def _is_validation_looking(name: str) -> bool:
    lname = name.lower()
    return any(lname.startswith(prefix) for prefix in _VALIDATION_LOOKING_PREFIXES)


#: A survey index key: (module, qualname).
Qualkey = tuple[str, str]

#: One recorded gap: (reason, name). reason is a REASON_VOCABULARY member
#: ("unresolved_delegate" or "no_contract_derived" -- the only two this
#: module ever emits); name is either an unresolved-call bare name or an
#: unresolvable delegate bare name, depending on reason.
Gap = tuple[str, str]


# ---------------------------------------------------------------------------
# §7.1 -- survey record shape (already on disk, not regenerated here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SurveyFinding:
    """One PreconditionFinding record from the survey JSON (§7.1)."""

    kind: str  # "raise_guard" | "assert"
    condition: str | None
    raises: str | None  # exception class name, None (assert), or "<dynamic:...>"
    scope_trail: tuple[str, ...]
    mentions_params: tuple[str, ...]
    lineno: int


@dataclass(frozen=True, slots=True)
class DroppedCall:
    """One `dropped_calls` record (§14.0.2, T25): a receiver-qualified call
    expression the survey could not attribute to a same-class/module-level
    function, together with WHERE it sits -- its own `lineno` and the
    nearest-first, polarity-aware `scope_trail` live at the survey's visit
    point (the identical trail `SurveyFinding.scope_trail` uses).

    `lineno`/`scope_trail` are `None`/`()` for a record produced by a
    pre-T25 survey artifact, which recorded only a bare `expr` string --
    fail-closed, not an error: `compute_volume_bridge`'s P10 consumer reads
    `lineno is None` as "no position available" and attaches `caller_scope:
    null` (spec §14.0.2's normative box), degrading to pre-increment
    behaviour rather than fabricating a position.
    """

    expr: str
    lineno: int | None
    scope_trail: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SurveyRecord:
    """One FunctionPreconditions record from the survey JSON (§7.1)."""

    qualname: str
    class_name: str | None
    module: str
    file: str
    lineno: int
    params: tuple[str, ...]
    findings: tuple[SurveyFinding, ...]
    delegates_to: tuple[str, ...]
    unresolved_calls: tuple[str, ...]
    #: (round-5 T0, F1) Receiver-qualified call expressions the survey's own
    #: recording rule drops entirely for every non-`self.<name>` Attribute
    #: receiver (e.g. `self.head[channel].get_tip`, `tip_spot.get_tip`).
    #: Added additively (§7.1); ``()`` for records from a pre-T0 artifact
    #: that omits the field, via `.get()` below. NOT deduplicated against
    #: `unresolved_calls` -- the two populations are disjoint by
    #: construction (`survey_plr_preconditions.py`'s `visit_Call` routes a
    #: call into exactly one of `delegates`/`unresolved`/`dropped`, never
    #: two).
    #: (260903, T25) Each entry is a `DroppedCall` record, not a bare
    #: `str` -- the survey schema change (§14.0.2). `_record_from_dict`
    #: (below) accepts EITHER shape on load: a `dict` (post-T25 artifact) or
    #: a bare `str` (pre-T25 artifact, degrading to `lineno=None`,
    #: `scope_trail=()`), so an un-regenerated artifact still loads, just
    #: with every `caller_scope` fail-closed to `null`. Multiplicity is
    #: preserved here too: two records sharing an `expr` are two entries,
    #: not one.
    dropped_calls: tuple[DroppedCall, ...] = ()
    #: (260909, T50, spec §17.2, M-INH Half 1) The SUBSET of
    #: `delegates_to` the survey admitted ONLY because this class's
    #: transitive base closure -- not this class's own method set --
    #: defines the name (`scripts/survey_plr_preconditions.py`'s own
    #: `FunctionPreconditions.inherited_delegates`). Additive; `()` for a
    #: pre-T50 artifact via `.get()` below, degrading to "M-INH's
    #: whole-surface report sees no Half-1-sourced pairs for this
    #: record", never a crash.
    inherited_delegates: tuple[str, ...] = ()


def _finding_from_dict(d: dict[str, Any]) -> SurveyFinding:
    return SurveyFinding(
        kind=d["kind"],
        condition=d.get("condition"),
        raises=d.get("raises"),
        scope_trail=tuple(d.get("scope_trail", ())),
        mentions_params=tuple(d.get("mentions_params", ())),
        lineno=d["lineno"],
    )


def _dropped_call_from_any(item: Any) -> DroppedCall:
    """Accept both the post-T25 `{expr, lineno, scope_trail}` record shape
    and a pre-T25 bare `str` -- see `SurveyRecord.dropped_calls`'s
    docstring. A bare string degrades to `lineno=None`, `scope_trail=()`,
    which is exactly what a `caller_scope`-fail-closed consumer needs."""
    if isinstance(item, str):
        return DroppedCall(expr=item, lineno=None, scope_trail=())
    return DroppedCall(
        expr=item["expr"],
        lineno=item.get("lineno"),
        scope_trail=tuple(item.get("scope_trail", ())),
    )


def _record_from_dict(d: dict[str, Any]) -> SurveyRecord:
    return SurveyRecord(
        qualname=d["qualname"],
        class_name=d.get("class_name"),
        module=d["module"],
        file=d["file"],
        lineno=d["lineno"],
        params=tuple(d.get("params", ())),
        findings=tuple(_finding_from_dict(f) for f in d.get("findings", ())),
        delegates_to=tuple(d.get("delegates_to", ())),
        unresolved_calls=tuple(d.get("unresolved_calls", ())),
        dropped_calls=tuple(_dropped_call_from_any(x) for x in d.get("dropped_calls", ())),
        inherited_delegates=tuple(d.get("inherited_delegates", ())),
    )


def load_survey(path: str | Path) -> list[SurveyRecord]:
    """Load ``plr_preconditions.json`` (§7.1). Top level is an object, not a
    list -- ``functions`` holds the per-function records. Does not
    regenerate the survey; this is a pure read of data already on disk."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_record_from_dict(d) for d in payload["functions"]]


def build_index(records: list[SurveyRecord]) -> dict[Qualkey, SurveyRecord]:
    """Key every record on ``(module, qualname)`` (§7.2), once.

    F6 (round-5 T0 item 2): ``(module, qualname)`` is NOT unique in the
    survey artifact -- 12 keys collide at the current pin, all
    ``@property``/``@x.setter`` pairs (e.g. ``Serial.dtr``/``Serial.rts``).
    A bare ``{key: rec for rec in records}`` comprehension makes the
    LAST-visited record win, silently discarding the other -- since AST
    traversal visits class members in source order and a property's setter
    is conventionally defined after its getter, that is normally the
    setter. This function keeps that behavior (documented, not changed:
    ``resolve()``'s bare-NAME, class-first delegate resolution (§7.2) has no
    ``lineno`` to disambiguate a getter from its setter, so the discard is
    unavoidable for THIS index's purpose). What is new: the discard is no
    longer silent -- ``count_index_key_collisions`` measures it, and
    ``build_unique_index`` provides a companion index keyed on
    ``(module, qualname, lineno)`` (unique by construction: two records in
    one module cannot share a definition line) for any caller that needs
    every record addressable, not just the name-resolvable ones. See the
    gap ledger's ``index_key_collisions`` field.
    """
    return {(rec.module, rec.qualname): rec for rec in records}


#: (round-5 T0, F6) A record's fully-unique identity: (module, qualname,
#: lineno). Two records in the same module cannot share a definition
#: `lineno` (each AST FunctionDef/AsyncFunctionDef node has exactly one),
#: so this key is collision-free by construction -- unlike ``Qualkey``.
RecordKey = tuple[str, str, int]


def build_unique_index(records: list[SurveyRecord]) -> dict[RecordKey, SurveyRecord]:
    """Key every record on ``(module, qualname, lineno)`` (F6, round-5 T0):
    a companion to ``build_index`` that loses NO record to collision --
    ``len(build_unique_index(records)) == len(records)`` always. Not a
    replacement for ``build_index``: ``resolve()``'s bare delegate-name
    lookup (§7.2) only ever has a name, never a lineno, so closure-walking
    machinery (``derive_contract``, the gap ledger's population runs) keeps
    using the ``(module, qualname)``-keyed index. This index exists for
    callers that need to address every record individually -- e.g. auditing
    which specific record a collision discarded.
    """
    index = {(rec.module, rec.qualname, rec.lineno): rec for rec in records}
    assert len(index) == len(records), (
        f"build_unique_index lost records: {len(records)} in, {len(index)} out -- "
        f"(module, qualname, lineno) is not unique, which should be structurally "
        f"impossible (two records sharing one definition line in one module)"
    )
    return index


#: (260901 T11) The derived-contracts payload's output key for one record.
#: Bare ``qualname`` (e.g. ``"LiquidHandler.aspirate"``) whenever that name
#: is unique among the population being emitted -- this is the format
#: ``check/`` already looks up via ``f"{op.receiver_type}.{op.method_name}"``
#: (§6.2), so the overwhelming majority of entries (4,718 of 4,770 at the
#: current pin) keep the pre-T11 lookup shape unchanged.
def build_contract_keys(records: list[SurveyRecord]) -> dict[RecordKey, str]:
    """Assign every record a collision-free contract-table key (T11).

    **Two independent collision sources, both real at whole-surface scale**
    (measured 260901; the task brief's "8" figure only counted the first):

    1. ``@property``/``@x.setter`` pairs -- SAME ``(module, qualname)``,
       different ``lineno`` (8 finding-bearing pairs, 12 over the whole
       4,770-record survey; ``count_index_key_collisions`` measures this
       population). ``build_index``'s own docstring already documents this
       source.
    2. Distinct module-level functions in DIFFERENT modules that happen to
       share a bare name -- e.g. ``_height_of_volume_in_spherical_cap`` is
       defined once in ``pylabrobot.resources.height_functions`` and again,
       unrelated, in ``pylabrobot.resources.height_volume_functions``. These
       do NOT collide in ``build_index`` (module differs), but DO collide
       under the contract table's bare-``qualname`` key -- 10 additional
       pairs among finding-bearing records, 18 total finding-bearing
       collisions, 26 over the whole 4,770-record survey. This source is
       new to this task's own measurement; it was not in the brief.

    **Disambiguator (single, uniform rule, chosen over a two-tier one for
    testability):** if ``qualname`` is unique among ``records``, the key is
    the bare ``qualname``. Otherwise the key is
    ``f"{qualname}@{module}:{lineno}"`` -- ``(module, qualname, lineno)`` is
    proven collision-free by construction (``build_unique_index``'s own
    assertion: two records in one module cannot share a definition line),
    so this is collision-free for BOTH sources above without needing to
    branch on which source produced the collision.

    **Known, accepted limitation, stated rather than silently worked
    around:** a colliding method's DISAMBIGUATED key is unreachable via
    ``check/``'s lookup format (bare ``f"{receiver_type}.{method_name}"``,
    §6.2 -- ``OperationNode`` carries no module or line number). This is
    honest, not a regression: every measured collision is either a
    property/setter pair (accessed via attribute syntax, never emitted as
    an ``OperationNode`` by the extractor, which only records ``ast.Call``
    sites, per ``computation_graph_extractor.py``) or a module-level
    function with no receiver at all (never reachable through
    ``receiver_type.method_name`` in the first place, since it has no
    receiver). No entry point any real graph could name is made
    unreachable by this choice.
    """
    from collections import Counter

    qual_counts = Counter(rec.qualname for rec in records)
    keys: dict[RecordKey, str] = {}
    for rec in records:
        record_key: RecordKey = (rec.module, rec.qualname, rec.lineno)
        if qual_counts[rec.qualname] > 1:
            keys[record_key] = f"{rec.qualname}@{rec.module}:{rec.lineno}"
        else:
            keys[record_key] = rec.qualname
    assert len(set(keys.values())) == len(records), (
        f"build_contract_keys produced a colliding key set: {len(records)} records "
        f"in, {len(set(keys.values()))} distinct keys out -- the disambiguator above "
        f"should make this structurally impossible"
    )
    return keys


def count_index_key_collisions(records: list[SurveyRecord]) -> dict[str, int]:
    """F6 (round-5 T0): how many DISTINCT ``(module, qualname)`` keys among
    ``records`` back more than one record -- i.e. how many keys
    ``build_index`` collapses. Reported over two populations, since they
    give different numbers (§7.4's population footnote): ALL survey records
    (12 at the current pin, whole artifact) and finding-bearing records only
    (8 -- the population ``methods_attempted`` counts, since a collision
    with no findings on either twin cannot affect any closure result)."""
    from collections import Counter

    def _collisions(recs: list[SurveyRecord]) -> int:
        counts = Counter((rec.module, rec.qualname) for rec in recs)
        return sum(1 for c in counts.values() if c > 1)

    finding_bearing = [rec for rec in records if rec.findings]
    return {
        "all_records": _collisions(records),
        "finding_bearing_records": _collisions(finding_bearing),
    }


# ---------------------------------------------------------------------------
# §17.2 -- M-INH: the base-name extractor, the fail-closed base-closure
# mechanism, and the whole-surface selection report (T50, spec
# 260909_plr-sema-move-family-increment.md).
#
# Deliberately placed BELOW `resolve()`'s call sites are (`resolve`,
# `_walk_closure`, `derive_contract`) but ABOVE their definitions -- Python
# resolves names at CALL time, not at def time, so forward references from
# `resolve()`'s body to `resolve_via_base_closure` below are fine; this
# section sits here so the primitives `resolve()`'s M-INH branch calls are
# read before `resolve()` itself, not after.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClassBasesIndex:
    """Whole-tree base-name index for M-INH (§17.2, T50).

    ``bases``: bare class name -> its DIRECT base names (§17.2's
    extractor table: ``ast.Name.id``, ``ast.Attribute.attr``, or the
    Subscript-recursed base name of ``ast.Subscript.value``), or ``None``
    -- the extractor's fourth row's sentinel -- when ANY base expression
    in that class's ``ClassDef.bases`` list was unreadable (an
    ``ast.Call``, a starred expression, a metaclass keyword, or anything
    else the three named rows don't cover). ``None`` here means "refuse
    the WHOLE class": ``class_closure`` propagates it to every class that
    transitively derives from this one, never guesses a partial closure.

    ``unresolved_base_counts``: per class, how many of ITS OWN direct
    base names (post-extraction) are absent from ``bases`` entirely --
    the silent-incompleteness measure for an import-alias base
    (``import x as Y; class C(Y)`` yields the base name ``"Y"``, which is
    simply never a key here) or any other base outside the analyzed
    surface. Zero for a class whose entry is the ``None`` sentinel (its
    own bases were never fully read, so this count is meaningless for it
    -- ``0`` rather than a misleading partial count).

    ``collision_names``: bare class names defined in MORE than one
    distinct module across the whole scanned tree. ``build_plr_class_index``
    (and this index's own ``bases``, built from its ``class_nodes``)
    resolve a bare name via first-definition-wins ``setdefault``, so a
    name in this set means ``bases``/``class_nodes`` silently picked an
    ARBITRARY one of >1 same-named classes -- using it as a resolution
    target could attribute a guard to the wrong class's method of the
    same name, invisible to the ambiguity check alone (which only counts
    definitions actually found in a closure). ``class_closure`` refuses
    (``None``) the moment it encounters a collision name, whether that
    name is the class being queried or an ancestor reached during the
    walk.
    """

    bases: "dict[str, tuple[str, ...] | None]"
    unresolved_base_counts: "dict[str, int]"
    collision_names: "frozenset[str]"


def _extract_base_name(expr: ast.expr) -> str | None:
    """One element of a ``ClassDef.bases`` list -> its base NAME, per
    §17.2's closed extractor rule, or ``None`` when the expression's shape
    means the WHOLE class must refuse (the table's fourth row: anything
    that is not ``ast.Name``/``ast.Attribute``/``ast.Subscript``, e.g. an
    ``ast.Call`` -- a dynamic base factory -- or a starred expression or a
    metaclass keyword argument, none of which carry a single readable base
    identity)."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    if isinstance(expr, ast.Subscript):
        return _extract_base_name(expr.value)
    return None


def build_class_bases_index(
    class_nodes: "dict[str, ast.ClassDef]",
    class_modules_multi: "dict[str, frozenset[str]]",
) -> ClassBasesIndex:
    """Pure (§17.2, T50): apply the base-name extractor's closed rule to
    every class in ``class_nodes``, plus the bare-name collision check
    against ``class_modules_multi`` (EVERY module that defines a class
    named ``key``, not just the first -- ``build_plr_class_index``'s own
    ``class_modules`` keeps only the first-definition-wins module and
    cannot answer this on its own).

    Takes already-built whole-tree structures rather than walking a
    source tree itself, so callers with DIFFERENT whole-tree scans (the
    survey script's own already-parsed file dict;
    ``receiver_state.build_plr_class_bases_index``'s dedicated disk scan
    for ``derive/__main__.py``) share this ONE implementation of the
    fail-closed rule rather than risking two copies drifting apart on it
    -- exactly the risk §17.2's own "both halves must land together" box
    calls out.
    """
    collision_names = frozenset(name for name, mods in class_modules_multi.items() if len(mods) > 1)
    bases: dict[str, tuple[str, ...] | None] = {}
    unresolved_base_counts: dict[str, int] = {}
    for name, node in class_nodes.items():
        extracted: list[str] = []
        refused = False
        for base_expr in node.bases:
            base_name = _extract_base_name(base_expr)
            if base_name is None:
                refused = True
                break
            extracted.append(base_name)
        if refused:
            bases[name] = None
            unresolved_base_counts[name] = 0
            continue
        bases[name] = tuple(extracted)
        unresolved_base_counts[name] = sum(1 for b in extracted if b not in class_nodes)
    return ClassBasesIndex(
        bases=bases, unresolved_base_counts=unresolved_base_counts, collision_names=collision_names
    )


def class_closure(
    name: str,
    class_nodes: "dict[str, ast.ClassDef]",
    bases_index: ClassBasesIndex,
    *,
    _seen: "frozenset[str] | None" = None,
) -> "frozenset[str] | None":
    """§17.2's reflexive-transitive base closure for ONE class name --
    ``{name} | closure(base) for base in name's direct bases``, generic
    (no PLR knowledge, just names) like ``plr_sema.check.predicate.
    subclass_closure_from_bases``, but extended with the FAIL-CLOSED
    refusal propagation that generic function's simpler ``Mapping[str,
    tuple[str, ...]]`` input has no sentinel to express: returns ``None``
    -- refused, not "empty" -- the instant the walk touches a collision
    name (``name in bases_index.collision_names``) or a class the
    extractor refused outright (``bases_index.bases[name] is None``),
    and that ``None`` propagates through every caller up the recursion,
    never silently downgrading to a partial closure.

    A base name entirely ABSENT from ``bases_index.bases`` (an import
    alias, or any name this whole-tree scan never saw a ``ClassDef``
    for -- ``object``, ``Generic``, ``ABC``, ...) is a DIFFERENT case:
    ``.get(name, ())`` treats it as a leaf with no further bases,
    contributing nothing more but refusing nothing either -- the same
    "unresolvable base is never guessed at" discipline
    ``subclass_closure_from_bases`` already documents.

    ``_seen`` is the recursion's own cycle guard (private, reflexive:
    ``name in _seen`` returns ``frozenset()`` for the repeat, not
    ``None`` -- a cycle contributes nothing further on the SECOND visit,
    it does not retroactively refuse the first).
    """
    seen = _seen if _seen is not None else frozenset()
    if name in seen:
        return frozenset()
    if name in bases_index.collision_names:
        return None
    direct = bases_index.bases.get(name, ())
    if direct is None:
        return None
    seen = seen | {name}
    result = {name}
    for base in direct:
        sub = class_closure(base, class_nodes, bases_index, _seen=seen)
        if sub is None:
            return None
        result |= sub
    return frozenset(result)


def diagnose_base_resolution(
    class_name: str,
    method_name: str,
    class_nodes: "dict[str, ast.ClassDef]",
    bases_index: ClassBasesIndex,
) -> "tuple[str | None, str]":
    """The single source of truth for §17.2 conditions 1/2: the unique
    ancestor (STRICT -- excluding ``class_name`` itself; a class's own
    definition is always ``resolve()``'s/condition 4's separate
    class-first step, never this function's job) in ``class_name``'s
    transitive base closure that defines ``method_name``. Returns
    ``(base_name, "resolved")`` on success, else ``(None, reason)`` where
    ``reason`` names WHY (AC-17.1's published refusal breakdown):

    * ``"class_name_collision"`` -- ``class_name`` itself is a bare-name
      collision (§17.2's second extractor refusal).
    * ``"closure_refused"`` -- ``class_closure`` returned ``None``: an
      unreadable base expression on ``class_name`` or on some ancestor
      (the extractor's fourth-row refusal, possibly several hops up), or
      a collision on an ANCESTOR rather than on ``class_name`` itself.
    * ``"no_ancestor_defines"`` -- the closure resolved cleanly but zero
      ancestors define ``method_name`` (not one of §17.2's four named
      conditions; published anyway so a `resolve()` miss into M-INH is
      never silently indistinguishable from a refusal).
    * ``"ambiguous"`` -- MORE than one ancestor defines ``method_name``
      (condition 1). AST bases are not an MRO linearisation, so picking
      any one of them risks inlining the WRONG body's guards; refusing
      is the only sound answer.

    ``resolve_via_base_closure`` below is a thin wrapper discarding the
    reason -- this function computes the boolean outcome exactly once,
    so the two can never disagree on what counts as "resolved".
    """
    if class_name in bases_index.collision_names:
        return None, "class_name_collision"
    closure = class_closure(class_name, class_nodes, bases_index)
    if closure is None:
        return None, "closure_refused"
    definers = [
        ancestor
        for ancestor in closure
        if ancestor != class_name
        and (node := class_nodes.get(ancestor)) is not None
        and any(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == method_name
            for n in ast.iter_child_nodes(node)
        )
    ]
    if not definers:
        return None, "no_ancestor_defines"
    if len(definers) > 1:
        return None, "ambiguous"
    return definers[0], "resolved"


def resolve_via_base_closure(
    class_name: str,
    method_name: str,
    class_nodes: "dict[str, ast.ClassDef]",
    bases_index: ClassBasesIndex,
) -> str | None:
    """The unique ancestor of ``class_name`` (excluding itself) that
    defines ``method_name``, or ``None`` on ambiguity/refusal/absence --
    ``resolve()``'s third step and condition 4's step (ii), both calling
    THIS (never reimplementing the ambiguity rule locally)."""
    base, _reason = diagnose_base_resolution(class_name, method_name, class_nodes, bases_index)
    return base


def inherited_method_names(
    class_name: str,
    class_nodes: "dict[str, ast.ClassDef]",
    bases_index: ClassBasesIndex,
) -> "frozenset[str]":
    """§17.2 Half 1's own need: the UNION of every ancestor's (excluding
    ``class_name`` itself) own method names, no ambiguity refusal --
    unlike ``resolve_via_base_closure``, the survey only needs to decide
    "is this name SOME delegate" (a boolean classification, `delegates`
    vs `unresolved`), not "which ONE class's guards to inline", so two
    ancestors defining the same name is not a conflict here. Returns
    ``frozenset()`` -- no extension, fail closed to "own methods only" --
    when ``class_closure`` refuses ``class_name`` outright (collision, or
    an unreadable base anywhere in the chain)."""
    closure = class_closure(class_name, class_nodes, bases_index)
    if closure is None:
        return frozenset()
    names: set[str] = set()
    for ancestor in closure:
        if ancestor == class_name:
            continue
        node = class_nodes.get(ancestor)
        if node is None:
            continue
        names |= {
            n.name for n in ast.iter_child_nodes(node)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    return frozenset(names)


def compute_m_inh_selection(
    records: "list[SurveyRecord]",
    index: dict[Qualkey, SurveyRecord],
    class_nodes: "dict[str, ast.ClassDef]",
    class_modules: "dict[str, str]",
    bases_index: ClassBasesIndex,
) -> "dict[str, Any]":
    """§17.2's whole-surface published selection (T50, AC-17.1). TWO
    distinct populations, reported separately because they come from
    different mechanisms and neither implies the other:

    ``half1_admitted`` -- every ``(class, name)`` pair the SURVEY itself
    already classified as a delegate ONLY via the transitive base closure
    (``rec.inherited_delegates``, Half 1). Each entry is re-diagnosed here
    via ``diagnose_base_resolution`` (Half 2's own, STRICTER, ambiguity-
    refusing rule) purely for reporting -- Half 1's union-of-ancestors
    admission rule has NO ambiguity check (``inherited_method_names``'s
    own docstring), so a pair landing here with ``reason != "resolved"``
    is a real, surfaceable disagreement between the two halves: the
    survey called it a delegate, but the closure walk still cannot pick a
    unique body to inline (``derive_contract`` degrades this ONE case
    from an ``unresolved_delegate`` gap to a ``no_contract_derived`` gap,
    per ``resolve()``'s own per-delegate re-check) -- ``half1_ambiguous_mismatch``
    isolates exactly this population.

    ``newly_resolved``/``refusal_counts`` -- every ``self.<name>()`` call
    this survey STILL recorded as ``unresolved_calls`` after Half 1's own
    extension (a name no ancestor's OWN method set admitted at all),
    checked against ``resolve()``'s third step for a residual rescue.
    Refusals are broken down by ``diagnose_base_resolution``'s reason plus
    ONE more this function adds itself (``"base_outside_surface"``,
    condition 2: a unique base was found but its ``(module_of(B),
    f"{B}.{name}")`` key is not itself in ``index``) -- six buckets total,
    matching AC-17.1's "four conditions, or ... the two extractor
    refusals" plus ``"no_ancestor_defines"``, named honestly as a
    non-failure bucket outside that enumeration.
    """
    half1_admitted: list[dict[str, Any]] = []
    half1_ambiguous_mismatch: list[dict[str, Any]] = []
    newly_resolved: list[dict[str, Any]] = []
    refusal_counts: dict[str, int] = {
        "resolved": 0,
        "ambiguous": 0,
        "base_outside_surface": 0,
        "class_name_collision": 0,
        "closure_refused": 0,
        "no_ancestor_defines": 0,
    }
    for rec in records:
        if rec.class_name is None:
            continue
        for name in rec.inherited_delegates:
            base, reason = diagnose_base_resolution(rec.class_name, name, class_nodes, bases_index)
            entry = {"class": rec.class_name, "module": rec.module, "name": name, "base": base, "reason": reason}
            half1_admitted.append(entry)
            if reason != "resolved":
                half1_ambiguous_mismatch.append(entry)
        for name in rec.unresolved_calls:
            base, reason = diagnose_base_resolution(rec.class_name, name, class_nodes, bases_index)
            if base is None:
                refusal_counts[reason] += 1
                continue
            base_module = class_modules.get(base)
            candidate = (base_module, f"{base}.{name}") if base_module is not None else None
            if candidate is None or candidate not in index:
                refusal_counts["base_outside_surface"] += 1
                continue
            refusal_counts["resolved"] += 1
            newly_resolved.append(
                {
                    "class": rec.class_name,
                    "module": rec.module,
                    "name": name,
                    "base": base,
                    "base_module": base_module,
                }
            )
    return {
        "half1_admitted": half1_admitted,
        "half1_ambiguous_mismatch": half1_ambiguous_mismatch,
        "newly_resolved": newly_resolved,
        "refusal_counts": refusal_counts,
    }


def measure_m_inh_entry_point_impact(
    entry: Qualkey,
    index: dict[Qualkey, SurveyRecord],
    class_nodes: "dict[str, ast.ClassDef]",
    class_modules: "dict[str, str]",
    bases_index: ClassBasesIndex,
    *,
    stamp: "SurveyStamp | None" = None,
) -> "dict[str, Any]":
    """§17.2 condition 3 (T50, AC-17.1): one entry point's closure size,
    guard count, and PER-GUARD depth multiset, BEFORE (no M-INH) and AFTER
    (M-INH enabled) -- round 1's C11, the only measurement that can catch
    a silent depth perturbation from delegates_to's own ``sorted()``
    push/pop-order change (§17.2's normative "second channel" box), since
    closure size and guard count alone cannot detect it. ``doubled`` is
    condition 3's own published bound: ``True`` iff the AFTER closure size
    is MORE than double the BEFORE size, in which case the caller (T50's
    CLI glue) must stop and surface this entry point rather than landing.
    """
    from collections import Counter

    before = derive_contract(entry[0], entry[1], index, stamp=stamp)
    after = derive_contract(
        entry[0], entry[1], index, stamp=stamp,
        class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
    )
    closure_before = {key for _rec, key, _depth in _walk_closure(entry, index)}
    closure_after = {
        key
        for _rec, key, _depth in _walk_closure(
            entry, index, class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index
        )
    }
    return {
        "entry": f"{entry[0]}:{entry[1]}",
        "closure_size_before": len(closure_before),
        "closure_size_after": len(closure_after),
        "guard_count_before": len(before.guards),
        "guard_count_after": len(after.guards),
        "depth_multiset_before": dict(sorted(Counter(g.depth for g in before.guards).items())),
        "depth_multiset_after": dict(sorted(Counter(g.depth for g in after.guards).items())),
        "doubled": len(closure_after) > 2 * len(closure_before),
    }


# ---------------------------------------------------------------------------
# §7.2 -- resolve() and the transitive closure mechanic
# ---------------------------------------------------------------------------


def resolve(
    name: str,
    rec: SurveyRecord,
    index: dict[Qualkey, SurveyRecord],
    *,
    class_nodes: "dict[str, ast.ClassDef] | None" = None,
    class_modules: "dict[str, str] | None" = None,
    bases_index: "ClassBasesIndex | None" = None,
    analyzed_class: str | None = None,
    analyzed_module: str | None = None,
) -> Qualkey | None:
    """Resolve one ``delegates_to`` bare name to an index key (§7.2, C1).

    Class-first precedence is normative and unconditional: step 1
    (same-class method, tried only when ``rec.class_name`` is not None) is
    tried before step 2 (module-level function) even when both would
    resolve. The residual ambiguity this creates -- a class method and a
    module-level function sharing a bare name in the same module -- is
    accepted (§7.2): step 1 wins, step 2 is never reached for that name in
    that module.

    Pure: never mutates a gap list. Callers append a
    ``("no_contract_derived", name)`` gap themselves when this returns
    ``None`` -- see ``derive_contract``.

    260909 (T50, spec 260909_plr-sema-move-family-increment.md §17.2,
    M-INH): FIVE additive, opt-in keyword-only parameters, all gated
    together on ``class_nodes``/``class_modules``/``bases_index`` being
    supplied -- omitting any of the three reproduces this function's exact
    pre-T50 two-step behaviour (the same fail-closed-by-omission discipline
    ``function_index`` uses elsewhere in this module). When supplied:

    THIRD STEP (``analyzed_class`` is ``None`` or equals ``rec.class_name``
    -- "a record reached the ordinary way", §17.2's scoping box): tried
    only after the two same-module steps above both fail, never before
    them. Walks ``rec.class_name``'s transitive base closure (excluding
    itself) via ``resolve_via_base_closure`` and returns
    ``(module_of(B), f"{B}.{name}")`` for the UNIQUE base ``B`` defining
    ``name``, or ``None`` on ambiguity/refusal (§17.2 conditions 1/2) or
    when the candidate key is not itself present in ``index``.

    CONDITION 4 (``analyzed_class`` supplied AND differs from
    ``rec.class_name``): this record is a body M-INH itself admitted by
    inheritance -- ``rec.class_name`` is some ancestor ``B`` of the
    analyzed (entry-point) class ``C`` == ``analyzed_class``. A
    ``self.<name>()`` call inside it dispatches on ``C``, never on ``B``:
    the class-first step above is run against ``C``/``analyzed_module``
    instead of ``rec.class_name``/``rec.module`` (an override on ``C``
    wins immediately), the module-level step is UNCHANGED (still keyed on
    ``rec.module`` -- a bare, non-``self`` call inside ``B``'s own module
    is unaffected by which instance ``self`` actually is), and the third
    step also walks ``C``'s own transitive closure (excluding ``C``, not
    ``B``'s) rather than ``B``'s. This is what makes
    ``Resource._state_updated``'s own ``self.serialize_state()`` resolve
    to a ``LiquidHandler`` override rather than to ``Resource``'s own body
    when reached through ``LiquidHandler``'s closure (§17.2's normative
    box, AC-17.1).
    """
    m_inh_ready = class_nodes is not None and class_modules is not None and bases_index is not None
    inherited_body = (
        m_inh_ready
        and analyzed_class is not None
        and rec.class_name is not None
        and rec.class_name != analyzed_class
    )
    dispatch_class = analyzed_class if inherited_body else rec.class_name
    dispatch_module = analyzed_module if inherited_body else rec.module

    if dispatch_class is not None and dispatch_module is not None:
        same_class = (dispatch_module, f"{dispatch_class}.{name}")
        if same_class in index:
            return same_class

    module_level = (rec.module, name)
    if module_level in index:
        return module_level

    if m_inh_ready and dispatch_class is not None:
        assert class_nodes is not None and class_modules is not None and bases_index is not None
        base = resolve_via_base_closure(dispatch_class, name, class_nodes, bases_index)
        if base is not None:
            base_module = class_modules.get(base)
            if base_module is not None:
                candidate = (base_module, f"{base}.{name}")
                if candidate in index:
                    return candidate
    return None


def _walk_closure(
    entry: Qualkey,
    index: dict[Qualkey, SurveyRecord],
    *,
    class_nodes: "dict[str, ast.ClassDef] | None" = None,
    class_modules: "dict[str, str] | None" = None,
    bases_index: "ClassBasesIndex | None" = None,
):
    """Cycle-safe transitive closure walk over ``delegates_to`` (§7.2's
    mechanic). Shared traversal core for ``derive_contract`` and the
    gap-ledger builder's reachable-set computation, so the two can never
    silently drift apart on traversal semantics.

    Yields ``(rec_or_None, key, depth)`` for every node popped off the LIFO
    frontier. ``depth`` is carried explicitly on the frontier as a
    ``(key, depth)`` pair -- never derived from ``len(seen)``, which counts
    total nodes visited across the WHOLE closure (a visit counter), not
    distance from the entry point, and would be wrong under LIFO
    ``frontier.pop()`` traversal order (trap 1). ``seen`` is checked before
    expansion (cycle-safe, trap 2) -- PLR's ``delegates_to`` graph is not
    guaranteed acyclic.

    ``rec`` is ``None`` only when a resolved key is absent from the index --
    defensive; should not occur for a key that passed through ``resolve()``,
    but handled per §7.2's own pseudocode (``index.get(q) or
    gaps.append(...)``) rather than assumed unreachable, since it is also
    the entry-point-not-in-index case.

    260909 (T50, spec §17.2, M-INH): ``class_nodes``/``class_modules``/
    ``bases_index`` -- all three or none, the same all-or-nothing gate
    ``resolve()`` itself applies -- are additive and opt-in; omitting them
    reproduces this generator's exact pre-T50 traversal, byte for byte
    (every line below except the ``resolve()`` call itself, and the two new
    ``analyzed_class``/``analyzed_module`` locals, is unchanged). When
    supplied, ``analyzed_class``/``analyzed_module`` are captured ONCE from
    the entry point's own record at ``depth == 0`` (mirroring
    ``derive_contract``'s own ``entry_K`` capture, this module's line
    ~635-636) and threaded unchanged into every subsequent ``resolve()``
    call for the rest of THIS walk -- condition 4's "dispatch on the
    analyzed class" rule. No other traversal semantics change: ``seen``,
    the LIFO ``frontier``, and cycle-safety are exactly as before.
    """
    m_inh_ready = class_nodes is not None and class_modules is not None and bases_index is not None
    seen: set[Qualkey] = set()
    frontier: list[tuple[Qualkey, int]] = [(entry, 0)]
    analyzed_class: str | None = None
    analyzed_module: str | None = None
    while frontier:
        key, depth = frontier.pop()
        if key in seen:
            continue
        seen.add(key)
        rec = index.get(key)
        yield rec, key, depth
        if rec is None:
            continue
        if depth == 0:
            analyzed_class = rec.class_name
            analyzed_module = rec.module
        for name in rec.delegates_to:
            resolved = resolve(
                name,
                rec,
                index,
                class_nodes=class_nodes if m_inh_ready else None,
                class_modules=class_modules if m_inh_ready else None,
                bases_index=bases_index if m_inh_ready else None,
                analyzed_class=analyzed_class,
                analyzed_module=analyzed_module,
            )
            if resolved is not None:
                frontier.append((resolved, depth + 1))


@dataclass(frozen=True, slots=True)
class InlinedGuard:
    """One precondition finding, inlined into an entry point's closure
    (§7.2). ``condition``/``scope_trail`` are RAW STRINGS -- turning them
    into a checkable predicate was deferred item (c); increment 6 (spec
    260904 §15.2, T30a) executes the boundary the main spec pre-declared
    (`260901_plr-sema-pre-corpus-spec.md:2532`): ``predicate`` is additive,
    ``condition`` stays and is the SOURCE OF TRUTH on the wire (nothing is
    replaced -- ``derive/__main__.py``'s JSON writer emits both).

    ``kind`` carries guard polarity as a first-class field (C4, normative):
    ``"raise_guard"`` fires when ``condition`` evaluates TRUE
    (survey_plr_preconditions.py:198-199); ``"assert"`` fires when
    ``condition`` evaluates FALSE (:208). Folding this into ``condition``'s
    text would make the polarity permanently unrecoverable from the shipped
    artifact. (260904, T30a, G6: ``predicate`` is parsed from ``condition``
    identically regardless of ``kind`` -- polarity is interpreted against it
    by the evaluator, T31, never re-derived from the text.)

    ``predicate`` is ``plr_sema.derive.predicate_ast.parse(condition)`` --
    total, never ``None``, ``Opaque`` for anything the grammar (G0-G6) does
    not recognise. It carries no idiom resolution (§15.3's alpha/beta local
    bindings are T30b): a guard whose condition names a local bound by an
    earlier statement in its own method parses to a plain ``Var``, exactly
    as unresolved as it is today.

    ``bindings`` (260904, T30b, additive): the complete set of alpha/beta
    local-binding idiom matches (§15.3) for this guard's own free ``Var``
    names, computed against ``K`` -- the function/method that ACTUALLY
    defines this guard (``site``'s own file/line, which for a depth->=1
    guard is the delegate's own body, never the entry point's). ``()`` when
    no ``function_index`` was supplied to ``derive_contract`` (fail closed
    to "no binding known", identical to every guard's behaviour before this
    field existed) or when no free name binds. See
    ``plr_sema.derive.bindings`` for the JSON shape of one entry.

    ``reachability_clear`` (260907, T36, additive): E-UNCOND(5)'s refined
    K-body fact (spec 260904 §15.4/§15.10), computed against the SAME ``K``
    as ``bindings`` via
    ``plr_sema.derive.bindings.compute_reachability_clear``. ``False`` --
    fail closed, identical in spirit to ``bindings``'s ``()`` default --
    when no ``function_index`` was supplied to ``derive_contract``. See
    that function's own docstring for the exact three-clause test (an
    earlier ``ast.Raise`` never blocks).

    ``caller_args`` (260909, T42, additive, spec 260909 §16.4 M1/M2): for a
    ``depth == 1`` guard ONLY, the delegate's own parameter name ->
    caller-side ``Term`` JSON map, computed against the ENTRY POINT's own
    AST (never the delegate's) by
    ``plr_sema.derive.bindings.compute_caller_args``. ``None`` -- fail
    closed, the same "absent means resolve to ⊤" default every additive
    field on this dataclass takes -- when no ``function_index`` was
    supplied, when the guard's own depth is not 1, or when M1's six
    conditions refuse the ``(K, D)`` pair outright. A ``depth == 0`` or
    ``depth >= 2`` guard NEVER carries this field (M1 clause 6: "one level
    only").

    ``caller_reachability_clear``/``caller_scope_trail`` (260909, T42,
    additive, spec §16.4 D1): the SAME facts ``reachability_clear``/
    ``scope_trail`` carry, but computed against the entry point's own
    delegate CALL STATEMENT rather than against the guard's own site --
    D1's second precondition for lifting E-UNCOND(4) at ``depth == 1``.
    ``caller_reachability_clear`` is
    ``plr_sema.derive.bindings.compute_reachability_clear(K, call_lineno)``
    (the SAME function ``reachability_clear`` uses, just against a
    different lineno); ``caller_scope_trail`` is
    ``plr_sema.derive.bindings.compute_caller_scope_trail(K, call_lineno)``.
    Both ``None`` under the identical fail-closed conditions
    ``caller_args`` takes above (and always together: there is no call
    statement to key either fact on unless M1 clauses 1/2 found exactly
    one).
    """

    condition: str | None
    predicate: Predicate
    scope_trail: tuple[str, ...]
    raises: str | None
    kind: str  # "raise_guard" | "assert"
    free_vars: tuple[str, ...]
    site: PlrSite  # the DEFINING site -- the delegate's own file/line, never the entry point's
    depth: int  # 0 = own body, >0 = inlined from a delegate
    bindings: tuple[dict[str, Any], ...] = ()
    reachability_clear: bool = False
    caller_args: dict[str, Any] | None = None
    caller_reachability_clear: bool | None = None
    caller_scope_trail: tuple[str, ...] | None = None

    @property
    def is_dynamic_raise(self) -> bool:
        """D18: detect a dynamic-sentinel ``raises`` value by prefix, NEVER
        by equality against a literal glob string."""
        return self.raises is not None and self.raises.startswith("<dynamic:")


@dataclass(frozen=True, slots=True)
class DerivedContract:
    """The output of one entry point's closure (§7.2/§7.3): guards, gaps,
    and the provenance stamp of the run that produced them."""

    qualname: str
    guards: tuple[InlinedGuard, ...]
    gaps: tuple[Gap, ...]
    stamp: SurveyStamp


def derive_contract(
    module: str,
    qualname: str,
    index: dict[Qualkey, SurveyRecord],
    *,
    stamp: SurveyStamp | None = None,
    function_index: dict[tuple[str, str, int], ast.AST] | None = None,
    class_nodes: "dict[str, ast.ClassDef] | None" = None,
    class_modules: "dict[str, str] | None" = None,
    bases_index: "ClassBasesIndex | None" = None,
) -> DerivedContract:
    """Transitive-closure contract derivation (§7.2). Totality (AC-7.2):
    NEVER raises, regardless of whether ``(module, qualname)`` is present in
    the index -- an absent entry point becomes a single
    ``("no_contract_derived", qualname)`` gap, not an exception. Every
    operation therefore receives at least one Finding downstream.

    Three properties, all testable without semantics (§7.2):
      * cycle-safe (``seen`` checked before expansion, via ``_walk_closure``)
      * provenance-preserving (every guard's ``site`` names the file that
        ACTUALLY contains it, not the entry point's file)
      * gap-recording, never gap-hiding (every ``unresolved_calls`` entry
        and every unresolvable delegate reached during the closure becomes
        a recorded gap)

    ``function_index`` (260904, T30b, additive, default ``None``):
    ``receiver_state.build_plr_function_index``'s whole-tree ``(module,
    qualname, lineno) -> AST node`` map. When supplied, each emitted
    ``InlinedGuard.bindings`` is populated by looking up the guard's OWN
    defining record ``rec`` (``_walk_closure``'s own loop variable -- the
    record at the ACTUAL closure depth, never the entry point's) in it and
    running ``bindings.compute_local_bindings_for_guard`` against the real
    function body. Omitting it (the default) reproduces T30a's exact
    behaviour: every guard's ``bindings`` is ``()``.

    260907 amendment (T35, spec 260904 §15.2's normative box, round 2
    A-C1): the SAME ``function_index`` also gates G7's PLR-layer test on a
    shape-(2) ``EnvRef`` (``self.<name>(...)`` with ``len(path) == 2``) --
    reduced once, per call, to a ``(module, qualname)`` set via
    ``bindings.build_qualname_index`` and applied per guard via
    ``bindings.demote_refused_env_refs`` against the guard's OWN receiver
    class (``rec.class_name``). Omitting ``function_index`` refuses EVERY
    such candidate (fail-closed, identical in spirit to the ``bindings``
    default above).

    260909 amendment (T42, spec 260909 §16.4): with ``function_index``
    supplied, every ``depth == 1`` guard ADDITIONALLY gets ``caller_args``/
    ``caller_reachability_clear``/``caller_scope_trail`` populated against
    the ENTRY POINT's own AST (``entry_K`` below, captured once at
    ``depth == 0`` -- ``_walk_closure`` always yields the entry point
    first, by construction) and the delegate's own AST (the SAME ``K``
    local variable ``bindings``/``reachability_clear`` already use at
    ``depth == 1``, which is spec's ``D``). Computed ONCE per delegate
    ``key`` reached at depth 1 and reused across every one of that
    delegate's own guards (M1's ``(K, D)`` pair does not vary per-guard;
    a depth-2+ delegate never receives this treatment at all, M1 clause
    6, enforced here simply by never calling into it outside the
    ``depth == 1`` branch below).

    260909 (T50, spec §17.2, M-INH): ``class_nodes``/``class_modules``/
    ``bases_index``, additive and opt-in (omitting any of the three
    reproduces this function's exact pre-T50 behaviour -- the same
    fail-closed-by-omission discipline ``function_index`` uses above),
    threaded straight through to ``_walk_closure`` and to every
    per-delegate ``resolve()`` re-check below. ``analyzed_class``/
    ``analyzed_module`` are captured HERE too (mirroring ``entry_K``'s own
    depth-0 capture immediately below) so the delegate-gap re-check uses
    the identical dispatch-on-the-analyzed-class rule ``_walk_closure``
    applied while expanding the same record.
    """
    if stamp is None:
        stamp = survey_stamp()
    qualname_index = None if function_index is None else build_qualname_index(function_index)
    guards: list[InlinedGuard] = []
    gaps: list[Gap] = []
    entry_K: ast.AST | None = None
    analyzed_class: str | None = None
    analyzed_module: str | None = None
    caller_info_cache: dict[Qualkey, tuple[dict[str, Any] | None, bool | None, tuple[str, ...] | None]] = {}
    for rec, key, depth in _walk_closure(
        (module, qualname), index,
        class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
    ):
        if rec is None:
            gaps.append(("no_contract_derived", key[1]))
            continue
        K = None if function_index is None else function_index.get((rec.module, rec.qualname, rec.lineno))
        if depth == 0:
            entry_K = K
            analyzed_class = rec.class_name
            analyzed_module = rec.module
        caller_args: dict[str, Any] | None = None
        caller_reachability_clear: bool | None = None
        caller_scope_trail: tuple[str, ...] | None = None
        if depth == 1 and entry_K is not None and K is not None:
            if key not in caller_info_cache:
                call_lineno = compute_caller_call_lineno(entry_K, K)
                if call_lineno is None:
                    caller_info_cache[key] = (None, None, None)
                else:
                    caller_info_cache[key] = (
                        compute_caller_args(entry_K, K),
                        compute_reachability_clear(entry_K, call_lineno),
                        compute_caller_scope_trail(entry_K, call_lineno),
                    )
            caller_args, caller_reachability_clear, caller_scope_trail = caller_info_cache[key]
        for finding in rec.findings:
            predicate = parse_predicate(finding.condition)
            predicate = demote_refused_env_refs(
                predicate,
                module=rec.module,
                class_name=rec.class_name,
                qualname_index=qualname_index,
            )
            bindings: tuple[dict[str, Any], ...] = ()
            reachability_clear = False
            if K is not None:
                bindings = compute_local_bindings_for_guard(K, predicate, finding.lineno)
                reachability_clear = compute_reachability_clear(K, finding.lineno)
            guards.append(
                InlinedGuard(
                    condition=finding.condition,
                    predicate=predicate,
                    scope_trail=finding.scope_trail,
                    raises=finding.raises,
                    kind=finding.kind,
                    free_vars=finding.mentions_params,
                    site=PlrSite(file=rec.file, lineno=finding.lineno, qualname=rec.qualname),
                    depth=depth,
                    bindings=bindings,
                    reachability_clear=reachability_clear,
                    caller_args=caller_args,
                    caller_reachability_clear=caller_reachability_clear,
                    caller_scope_trail=caller_scope_trail,
                )
            )
        for name in rec.delegates_to:
            resolved = resolve(
                name, rec, index,
                class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
                analyzed_class=analyzed_class, analyzed_module=analyzed_module,
            )
            if resolved is None:
                gaps.append(("no_contract_derived", name))
        for unresolved_name in rec.unresolved_calls:
            gaps.append(("unresolved_delegate", unresolved_name))
    return DerivedContract(qualname=qualname, guards=tuple(guards), gaps=tuple(gaps), stamp=stamp)


# ---------------------------------------------------------------------------
# AC-7.2 / D22 -- derived SUPPORTED_TOOLS -> (module, qualname) mapping
# ---------------------------------------------------------------------------


def _module_of_liquid_handler(index: dict[Qualkey, SurveyRecord]) -> str | None:
    """AC-7.2 says "any indexed record" -- collect ALL matching modules,
    not just the first found (round-4 remediation, m3). At the current pin
    all 54 ``class_name == "LiquidHandler"`` records sit in one module, so
    dict-iteration-order-dependent first-match happens to be deterministic
    today, but `plr_survey_common.py:127-129` proves duplicate class names
    across modules exist *in general* -- the ambiguity is latent, not live,
    and this is cheap defense in depth against it becoming live. Fails
    LOUDLY, naming every distinct module found, for a genuine ambiguity
    (>1 distinct module).

    260901 T13 (backlog #4859, item 4): returns ``None``, does NOT raise,
    when the surface has NO ``class_name == "LiquidHandler"`` record at
    all. This is a real, expected case now that the analyzed surface is a
    parameter -- e.g. upstream's non-legacy tree, where ``LiquidHandler``
    exists only under ``legacy/`` (measured 260901: ``machines/`` is a bare
    ``__init__.py`` there) -- and must be told apart from the ambiguous-module
    case, which stays a loud failure because it signals a real bug in THIS
    module's own assumptions, not an honest fact about the surface."""
    modules: set[str] = set()
    for (module, _qualname), rec in index.items():
        if rec.class_name == "LiquidHandler":
            modules.add(module)
    if not modules:
        return None
    if len(modules) > 1:
        raise LookupError(
            f"multiple distinct modules have a class_name == 'LiquidHandler' "
            f"record: {sorted(modules)} -- SUPPORTED_TOOLS' (module, qualname) "
            f"mapping (D22) is ambiguous; resolve_supported_tool refuses to "
            f"silently pick one"
        )
    return next(iter(modules))


def resolve_supported_tool(name: str, index: dict[Qualkey, SurveyRecord]) -> Qualkey | None:
    """Map one bare ``SUPPORTED_TOOLS`` name to its ``(module, qualname)``
    index key by a DERIVED rule, not a hand-written map (D22): look up
    ``(module_of(LiquidHandler_record), f"LiquidHandler.{name}")`` against
    the index already built.

    Returns ``None`` (260901 T13, item 4) when this surface has no
    ``LiquidHandler`` record at all -- ``_module_of_liquid_handler`` already
    tells that case apart from a real ambiguity, so this function only has
    to propagate it. Still fails LOUDLY (``LookupError``), never silently
    skips, when a ``LiquidHandler`` module WAS found but this specific tool
    name does not resolve under it -- that is PLR renaming/removing a tool
    on a surface that does have the class, a materially different, real
    failure AC-7.2 must keep surfacing.
    """
    module = _module_of_liquid_handler(index)
    if module is None:
        return None
    key = (module, f"LiquidHandler.{name}")
    if key not in index:
        raise LookupError(
            f"SUPPORTED_TOOLS name {name!r} does not resolve to {key!r} in the "
            f"survey index -- PLR may have relocated LiquidHandler or renamed "
            f"the tool (D22)"
        )
    return key


# ---------------------------------------------------------------------------
# §7.4 / D3 -- the independent dropped-receiver AST pass (SECOND, separate
# from the survey; walks PLR source directly, no praxis import, §1.4).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_PLR_PKG_ROOT = _REPO_ROOT / "external" / "pylabrobot" / "pylabrobot"


def default_plr_pkg_root() -> Path:
    """Default root for the independent AST pass, derived from this file's
    own location the same way ``plr_sema._provenance.stamp`` derives
    ``_REPO_ROOT`` -- not a hardcoded path coupling this module to a
    caller's layout (that coupling concern is what D19 forbids for
    ``--survey-json``; this path is intrinsic to the repo this file lives
    in, and is overridable via ``--plr-root`` regardless)."""
    return _DEFAULT_PLR_PKG_ROOT


def _is_plr_source_file(path: Path) -> bool:
    """Mirrors scripts/plr_survey_common.py's is_source_file(): PLR's own
    test-file naming has no single convention (STARtests.py,
    backend_tests.py, test_foo.py all coexist)."""
    stem = path.stem
    return not (stem.endswith("test") or stem.endswith("tests") or stem.startswith("test_"))


def _iter_plr_source_files(plr_pkg_root: Path) -> list[Path]:
    return sorted(p for p in plr_pkg_root.rglob("*.py") if _is_plr_source_file(p))


def _module_name_for_plr_file(file: Path, plr_pkg_root: Path) -> str:
    rel = file.relative_to(plr_pkg_root.parent)
    return ".".join(rel.with_suffix("").parts)


def _is_dropped_receiver_call(node: ast.Call) -> str | None:
    """The corrected D3 predicate: ``func`` is ``ast.Attribute`` AND NOT
    (``func.value`` is ``ast.Name`` with ``id == "self"``). Strictly wider
    than "Subscript receiver on self" -- it also drops plain
    ``resource.get_item()``-style calls whose receiver IS a bare
    ``ast.Name``, just not literally ``self``. Returns the attribute name
    (e.g. ``"get_tip"``) when the predicate matches, else ``None``.
    """
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if isinstance(func.value, ast.Name) and func.value.id == "self":
        return None
    return func.attr


class _DroppedReceiverScanner(ast.NodeVisitor):
    """Walks one function/method body counting D3-matching call nodes.
    Recurses into nested function defs (no ``visit_FunctionDef`` override),
    matching the survey's own _BodyScanner's own-body semantics (§7.2's
    entry-point closure treats a whole top-level function/method body,
    including any nested defs, as belonging to that one qualname)."""

    def __init__(self) -> None:
        self.total = 0
        self.validation_looking = 0
        self.by_attr: dict[str, int] = {}

    def visit_Call(self, node: ast.Call) -> None:
        attr = _is_dropped_receiver_call(node)
        if attr is not None:
            self.total += 1
            self.by_attr[attr] = self.by_attr.get(attr, 0) + 1
            if _is_validation_looking(attr):
                self.validation_looking += 1
        self.generic_visit(node)


@dataclass(frozen=True, slots=True)
class DroppedReceiverCounts:
    """Per-method output of the independent D3 AST pass (§7.4).

    ``total`` is the PRIMARY, honest figure and must NOT gate on
    ``_is_validation_looking`` -- that gate is defined over the survey's own
    recording block, which the dropped population never enters, so applying
    it to this counter would be gating on a predicate never evaluated for
    this population. ``validation_looking`` is the tighter secondary
    figure and is always <= ``total``.

    ``by_attr`` (round-4 remediation, M12): the same total, broken down per
    attribute name (e.g. ``"get_tip"``), as a sorted tuple of pairs (frozen
    dataclass -- no mutable dict field). Feeds
    ``_dropped_receiver_worklist``'s ranked view; ``sum(n for _, n in
    by_attr) == total`` always.
    """

    total: int
    validation_looking: int
    by_attr: tuple[tuple[str, int], ...] = ()


def _count_dropped_receiver_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> DroppedReceiverCounts:
    scanner = _DroppedReceiverScanner()
    for stmt in node.body:
        scanner.visit(stmt)
    return DroppedReceiverCounts(
        total=scanner.total,
        validation_looking=scanner.validation_looking,
        by_attr=tuple(sorted(scanner.by_attr.items())),
    )


def scan_dropped_receiver_calls_in_source(source: str) -> DroppedReceiverCounts:
    """Test/inspection helper: run the D3 scan over the FIRST
    function/method body found in a source snippet, without touching the
    filesystem. Used by ``tests/test_derive.py``'s synthetic-fixture test
    (§7.5) so it doesn't depend on real files under ``external/``."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return _count_dropped_receiver_calls(node)
    raise ValueError("source contains no function or method definition")


def scan_dropped_receiver_calls(
    plr_pkg_root: Path | None = None,
) -> dict[Qualkey, DroppedReceiverCounts]:
    """The independent stdlib-``ast`` pass over PLR source under
    ``external/`` (§7.4/D3, T6's new work). Does NOT reuse the survey JSON
    at all -- a fresh parse of the same source tree, computing per method
    (keyed the same way the survey keys its own records: ``(module,
    qualname)``) the total D3-matching call-node count and its
    validation-looking subset.

    Only top-level module functions and one level of class methods are
    scanned (mirrors the survey's own scope, §7.1) -- nested classes are
    not descended into, matching ``survey_plr_preconditions.py:273-283``.
    """
    root = plr_pkg_root if plr_pkg_root is not None else default_plr_pkg_root()
    results: dict[Qualkey, DroppedReceiverCounts] = {}
    for file in _iter_plr_source_files(root):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = _module_name_for_plr_file(file, root)

        def _record(node: ast.FunctionDef | ast.AsyncFunctionDef, class_name: str | None) -> None:
            qualname = f"{class_name}.{node.name}" if class_name else node.name
            results[(module, qualname)] = _count_dropped_receiver_calls(node)

        for top in ast.iter_child_nodes(tree):
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _record(top, None)
            elif isinstance(top, ast.ClassDef):
                for member in ast.iter_child_nodes(top):
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _record(member, top.name)
    return results


# ---------------------------------------------------------------------------
# §7.4 -- the gap ledger (a generated build artifact)
# ---------------------------------------------------------------------------

_EMPTY_DROPPED = DroppedReceiverCounts(total=0, validation_looking=0)


def _run_population(
    recs: list[SurveyRecord],
    index: dict[Qualkey, SurveyRecord],
    stamp: SurveyStamp,
) -> tuple[dict[str, int], dict[str, int]]:
    """Run ``derive_contract`` with every record in ``recs`` as its own
    entry point; return (totals, by_reason) over that population. Used for
    both the whole-surface (1,314 finding-bearing functions, §7.6) and the
    SUPPORTED_TOOLS-only populations."""
    methods_with_no_recorded_gap = 0
    methods_with_gaps = 0
    by_reason: dict[str, int] = {"unresolved_delegate": 0, "no_contract_derived": 0}
    for rec in recs:
        contract = derive_contract(rec.module, rec.qualname, index, stamp=stamp)
        if contract.gaps:
            methods_with_gaps += 1
        else:
            methods_with_no_recorded_gap += 1
        for reason, _name in contract.gaps:
            by_reason[reason] = by_reason.get(reason, 0) + 1
    totals = {
        "methods_attempted": len(recs),
        "methods_with_no_recorded_gap": methods_with_no_recorded_gap,
        "methods_with_gaps": methods_with_gaps,
    }
    return totals, by_reason


def _methods_with_dropped_receiver_call(
    recs: list[SurveyRecord], dropped_receiver_counts: dict[Qualkey, DroppedReceiverCounts]
) -> int:
    count = 0
    for rec in recs:
        counts = dropped_receiver_counts.get((rec.module, rec.qualname), _EMPTY_DROPPED)
        if counts.total > 0:
            count += 1
    return count


def _top_unresolved_from_records(records: list[SurveyRecord]) -> list[dict[str, Any]]:
    """Rank distinct ``unresolved_calls`` names by how many DISTINCT
    functions' ``unresolved_calls`` list contains them (D12) -- a direct
    aggregation over the survey's own field, not over closure-run gaps.
    Names are not class-qualified (§7.1): an entry may collapse unrelated
    same-named helpers on different classes into one row."""
    blocks: dict[str, int] = {}
    for rec in records:
        for name in set(rec.unresolved_calls):
            blocks[name] = blocks.get(name, 0) + 1
    ranked = sorted(blocks.items(), key=lambda item: (-item[1], item[0]))
    return [{"call": name, "blocks_methods": count} for name, count in ranked]


def _reachable_keys(entry_keys: list[Qualkey], index: dict[Qualkey, SurveyRecord]) -> set[Qualkey]:
    reached: set[Qualkey] = set()
    for entry in entry_keys:
        for rec, key, _depth in _walk_closure(entry, index):
            if rec is not None:
                reached.add(key)
    return reached


def _closure_wide_dropped_receiver_counts(
    entry: Qualkey,
    index: dict[Qualkey, SurveyRecord],
    dropped_receiver_counts: dict[Qualkey, DroppedReceiverCounts],
) -> DroppedReceiverCounts:
    """Sum the independent D3 AST pass's per-method counts over an entry
    point's WHOLE transitive ``delegates_to`` closure (round-4 remediation,
    M11 second half) -- not just the entry point's own body.

    Before this fix, ``dropped_receiver_calls_by_method`` looked up
    ``dropped_receiver_counts`` by the entry key alone (own-body-only),
    which silently under-reports every ``SUPPORTED_TOOLS`` method whose real
    dropped-receiver calls live behind a delegate rather than in its own
    body -- exactly the same own-body-only failure mode §7.2's guard-inlining
    closure exists to prevent for guards (see ``test_aspirate_closure_
    reaches_check_containers``), now also fixed for this counter. Reuses
    ``_walk_closure`` -- the same cycle-safe traversal core ``derive_contract``
    uses -- so the two can never silently drift on traversal semantics.
    """
    total = 0
    validation_looking = 0
    for rec, key, _depth in _walk_closure(entry, index):
        if rec is None:
            continue
        counts = dropped_receiver_counts.get(key, _EMPTY_DROPPED)
        total += counts.total
        validation_looking += counts.validation_looking
    return DroppedReceiverCounts(total=total, validation_looking=validation_looking)


def _dropped_receiver_worklist(
    tool_keys: dict[str, Qualkey],
    index: dict[Qualkey, SurveyRecord],
    dropped_receiver_counts: dict[Qualkey, DroppedReceiverCounts],
) -> list[dict[str, Any]]:
    """The third ``top_unresolved`` view (round-4 remediation, M12/Cluster 3/
    B3(e)): the D3 dropped-receiver AST pass is computed correctly but was
    never ranked into a worklist -- this is that worklist. Built from the
    SAME transitive-closure population the D3 pass covers (the
    ``SUPPORTED_TOOLS`` closure), ranked by how many DISTINCT closure
    methods contain at least one call to that attribute name -- the direct
    analogue of ``_top_unresolved_from_records``'s ``blocks_methods``
    semantics, but over the dropped-receiver population (which structurally
    never enters ``unresolved_calls``, so the other two views can never see
    it) rather than over the survey's own recorded gaps. Reuses each
    record's already-computed ``DroppedReceiverCounts.by_attr`` breakdown --
    no second AST pass over PLR source.
    """
    blocks: dict[str, set[Qualkey]] = {}
    for entry in tool_keys.values():
        for rec, key, _depth in _walk_closure(entry, index):
            if rec is None:
                continue
            counts = dropped_receiver_counts.get(key, _EMPTY_DROPPED)
            for attr, n in counts.by_attr:
                if n > 0:
                    blocks.setdefault(attr, set()).add(key)
    ranked = sorted(
        ((attr, len(methods)) for attr, methods in blocks.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return [{"call": attr, "blocks_methods": count} for attr, count in ranked]


#: 260903 §13.4.2 (backlog #4883): the derived replacement for the two
#: hand-typed frozensets that used to gate clauses 1 and 3 of
#: `_is_inert_dropped_receiver_call`. Both are FACTS ABOUT PYTHON, not
#: about PLR, so neither can go stale when PLR changes (the `breaks_when`
#: question §9.1 makes every hand-maintained row answer -- these two answer
#: it with "never, by construction").
#:
#: `sys.stdlib_module_names` is a frozenset shipped by CPython since 3.10
#: (the package's `requires-python`). Cached once at import time rather
#: than re-read per call; the interpreter version it was read from is
#: recorded in the gap ledger's stamp (`_stamp_to_dict`), so a rerun under a
#: different interpreter is provenance-visible rather than silently
#: assumed identical.
_STDLIB_MODULE_NAMES: frozenset[str] = frozenset(sys.stdlib_module_names)

#: dir() of every builtin container/string/bytes type, dunders excluded --
#: clause 3's replacement for the eleven hand-typed call suffixes
#: (`keys`, `items`, `union`, `join`, ...). Strictly wider than the old
#: list (it also catches e.g. `pop`, `discard`, `copy`, `count`) by
#: construction, since it is generated from the SAME types the old list was
#: transcribed from by hand.
_BUILTIN_CONTAINER_ATTRS: frozenset[str] = frozenset(
    name
    for t in (dict, list, set, tuple, str, bytes)
    for name in dir(t)
    if not (name.startswith("__") and name.endswith("__"))
)


@lru_cache(maxsize=None)
def _module_level_import_aliases(file: str) -> dict[str, str]:
    """260903 §13.4.2 / round-1 challenger O6: PER-FILE module-level import
    alias resolution -- ``{bound_local_name: fully_dotted_target}``, e.g.
    ``{"aio": "asyncio"}`` for ``import asyncio as aio`` in this file,
    ``{"t": "time.time"}`` for ``from time import time as t``. Built fresh
    per ``file`` (a path relative to the repo root, matching
    `SurveyRecord.file`) and memoized per file via `lru_cache` -- NOT a
    single global alias table. A global table would silently merge aliases
    from files that bind the same local name to different targets (O6's
    exact objection), which is a materially different and less correct
    design than the per-file resolution §13.4.2 specifies.

    Only MODULE-LEVEL `Import`/`ImportFrom` nodes are read
    (`ast.iter_child_nodes(tree)`, not a full `ast.walk`) -- §13.4.2 says
    "module-level import alias"; a function-local import shadowing a
    stdlib name is a different, narrower claim this derivation does not
    make. Relative imports (`from . import x`, `node.level > 0`) can never
    resolve to a stdlib module and are skipped, as is `from x import *`
    (no individual bound name to record).
    """
    path = _REPO_ROOT / file
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    aliases: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname is not None:
                    aliases[alias.asname] = alias.name
                else:
                    # `import a.b.c` binds the top-level package name `a` in
                    # scope. Recorded here too (not just the `asname` case)
                    # -- `_head_resolves_to_stdlib` no longer has a bare
                    # `head in _STDLIB_MODULE_NAMES` shortcut (backlog
                    # #4883 follow-up: that shortcut is what let `resource`
                    # -- an ordinary PLR local variable name that ALSO
                    # happens to be a real stdlib module name -- match with
                    # no evidence the file imported it), so this table is
                    # now the ONLY path to a stdlib-import verdict.
                    top = alias.name.split(".", 1)[0]
                    aliases.setdefault(top, top)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None or node.level:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name
                aliases[bound] = f"{node.module}.{alias.name}"
    return aliases


def _head_resolves_to_stdlib(head: str, *, file: str) -> bool:
    """Clause 1's replacement (§13.4.2): ``head`` is a module-level import
    alias -- bound BY THIS FILE's OWN imports -- resolving to a member of
    ``sys.stdlib_module_names``.

    Deliberately NOT a bare ``head in _STDLIB_MODULE_NAMES`` membership
    check (that was the pre-tightening bug, backlog #4883 follow-up):
    ``resource`` is coincidentally also the name of a real (Unix-only)
    stdlib module, and PLR uses `resource` constantly as an ordinary local
    variable name for a `pylabrobot.resources.Resource` instance -- a bare
    string-membership test classified `resource.get_item`/`resource.rotate`/
    etc. as inert with no evidence the file ever imported the stdlib
    `resource` module at all (7 false positives in the SUPPORTED_TOOLS
    closure, 280 whole-surface). Requiring an ACTUAL import binding --
    ``import x`` / ``import x as y`` / ``from x import y`` whose resolved
    target's top-level package is a stdlib module -- is the same "a fact
    about this file's own source", not "a fact about what English words
    happen to also be Python module names", discipline §13.4.2 already
    applies to clause 3's dunder exclusion.
    """
    resolved = _module_level_import_aliases(file).get(head)
    if resolved is None:
        return False
    return resolved.split(".", 1)[0] in _STDLIB_MODULE_NAMES


def _is_inert_dropped_receiver_call(call_expr: str, *, file: str) -> bool:
    """F1/item 4's filter predicate, DERIVED (260903 §13.4.2, backlog
    #4883). Applied to a single `dropped_calls` entry (a full
    receiver-qualified call expression, e.g. `self.head[channel].get_tip`
    or `warnings.warn`) -- NOT to a bare attribute name, so it can
    distinguish `self.head[channel].get_tip` (real signal) from
    `warnings.warn` (noise) even though both would collapse to the same
    bare name under the pre-T0 `top_unresolved` views.

    ``file`` is the `SurveyRecord.file` the `dropped_calls` entry came
    from (repo-root-relative, e.g.
    `"external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py"`)
    -- REQUIRED, keyword-only: clause 1's import-alias resolution is
    per-file (round-1 challenger O6), so this predicate cannot answer
    clause 1 without knowing which file's imports to read.

    Round-5's two hand-typed frozensets (`_INERT_RECEIVER_PREFIXES`,
    `_INERT_CALL_SUFFIXES`) are DELETED, not kept as a fallback --
    §13.4.2's design point 8: a retained fallback would make the
    derivation unfalsifiable, since every entry the derived rule missed
    would be silently covered by the list. The derived rule is NOT a
    superset of the typed one: `logger`, `args`, `kwargs`, `sig`,
    `backend_kwargs` and `default` were local-variable names, not stdlib
    modules or import aliases, and are not covered here -- `logger.debug`
    re-enters the ranking (§13.4.2's "what happens to the six uncovered
    locals").
    """
    head = call_expr.split(".", 1)[0]
    if _head_resolves_to_stdlib(head, file=file):
        return True
    # A capitalized head (`Coordinate.zero`, `Coordinate.parse`, ...) is a
    # call on a CLASS/type object -- a value-factory or classmethod, not a
    # call on an instance whose typestate this analysis exists to read.
    # Real tip/resource-typestate receivers in this population are always
    # lowercase local variables (self, tip_spot, channel, resource,
    # container, tracker, ...); this rule generalizes past any one PLR
    # class name rather than hand-naming `Coordinate`. Kept UNCHANGED from
    # round 5 -- already derived, §13.4.2 does not touch it.
    if head[:1].isupper():
        return True
    tail = call_expr.rsplit(".", 1)[-1]
    return tail in _BUILTIN_CONTAINER_ATTRS


def _dropped_receiver_worklist_from_survey(
    tool_keys: dict[str, Qualkey],
    index: dict[Qualkey, SurveyRecord],
    *,
    filtered: bool,
) -> list[dict[str, Any]]:
    """(round-5 T0 item 4) The receiver-qualified `top_unresolved.
    dropped_receiver` view, sourced from the survey's own new
    `dropped_calls` field (F1) rather than the D3 pass's bare `by_attr`
    breakdown -- the shipped view's top row was `{"call": "get_tip",
    "blocks_methods": 6}`; this splits it into `self.head[channel].get_tip`,
    `tip_spot.get_tip`, `channel.get_tip`, ... (round-5 defense, F1's "one
    durable win"). Same `blocks_methods` semantics and same
    `SUPPORTED_TOOLS`-closure population as `_dropped_receiver_worklist`
    (walked via the SAME `_walk_closure` core, so the two views' populations
    cannot silently drift), ranked by how many DISTINCT closure methods
    contain >=1 call to that exact receiver-qualified expression.

    `filtered=False` returns the raw ranking (saturates on inert receivers
    -- `logger.debug`-class noise at the top, see `_INERT_RECEIVER_PREFIXES`'s
    docstring); `filtered=True` (what the shipped ledger publishes) excludes
    `_is_inert_dropped_receiver_call` matches so the real tip-state signal
    (e.g. `self.head[channel].get_tip`) is not buried under it. Both are
    exposed so a caller/report can show the before/after (round-5 T0 item 4's
    own requirement: "show the ranked view before and after filtering").
    """
    blocks: dict[str, set[Qualkey]] = {}
    for entry in tool_keys.values():
        for rec, key, _depth in _walk_closure(entry, index):
            if rec is None:
                continue
            # (260903, T25) `dropped_calls` entries are `DroppedCall`
            # records now, not bare `str`s -- read `.expr`. `blocks[...]` is
            # keyed on a `set[Qualkey]`, so a record contributing the same
            # `expr` more than once (multiplicity is now preserved at the
            # survey layer) still counts `key` exactly once here, unchanged.
            for dropped in rec.dropped_calls:
                call_expr = dropped.expr
                if filtered and _is_inert_dropped_receiver_call(call_expr, file=rec.file):
                    continue
                blocks.setdefault(call_expr, set()).add(key)
    ranked = sorted(
        ((call_expr, len(methods)) for call_expr, methods in blocks.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return [{"call": call_expr, "blocks_methods": count} for call_expr, count in ranked]


def _dropped_receiver_worklist_whole_surface(
    records: list[SurveyRecord], *, filtered: bool
) -> list[dict[str, Any]]:
    """260901 T14 (backlog #4862): the receiver-qualified deferred-item-(e)
    worklist for a surface with NO orchestration layer to walk a
    `SUPPORTED_TOOLS`/`LiquidHandler` closure from (`upstream_nonlegacy`:
    `machines/` is a bare `__init__.py`, `LiquidHandler` exists only under
    `legacy/`, so `_dropped_receiver_worklist_from_survey`'s `tool_keys` is
    structurally empty there -- see `resolve_supported_tool`'s
    `liquid_handler_present is False` path -- which makes that view silently
    vacuous, not merely small, on exactly the surface this ranks for).

    Ranks `dropped_calls` directly over EACH record's OWN body only -- no
    `delegates_to` closure walk -- because a surface with no orchestration
    layer has no principled notion of "entry point" to walk a closure FROM
    in the first place (every driver method is potentially its own caller).
    This is the same population and blocks_methods semantics
    `_top_unresolved_from_records` already uses for `unresolved_calls` (the
    `top_unresolved.whole_surface` view) -- own-body, no closure -- applied
    to the `dropped_calls` field instead, for symmetry with that existing,
    already-surface-agnostic view rather than inventing a second entry-point
    concept. On a surface that DOES have an orchestration layer (e.g.
    `legacy_pinned`), this ranks a strictly larger population than
    `_dropped_receiver_worklist_from_survey` (every finding-bearing record,
    not just the ~10-tool closure) -- both views are published side by side
    (see `build_gap_ledger`) rather than one replacing the other, since they
    answer different questions ("what does the whole surface drop?" vs.
    "what does the loadable-from-a-tool-entry-point closure drop?").

    Same `_is_inert_dropped_receiver_call` filter, same unfiltered/filtered
    pairing convention as `_dropped_receiver_worklist_from_survey` (round-5
    T0 item 4) -- an unfiltered ranking over a driver-method population
    saturates on its OWN inert population (logging/plumbing calls inside
    driver bodies), not necessarily the same names `_check_args` saturated
    on for the orchestration layer; see this task's report for whether the
    existing filter table transfers as-is.

    **Counts by straight per-record increment, NOT by accumulating a set of
    `(module, qualname)` keys.** The two closure-based worklists
    (`_dropped_receiver_worklist`/`_dropped_receiver_worklist_from_survey`)
    dedupe against a `set[Qualkey]` because `_walk_closure` can genuinely
    revisit the SAME key from more than one tool entry point's closure, and
    `Qualkey` collisions never arise there since closure traversal is keyed
    off the SAME `(module, qualname)`-collapsing `index` `derive_contract`
    itself uses. This function has neither property: `records` is iterated
    flatly, once, with no possibility of revisiting a record twice, so no
    dedup step is needed at all -- and using `(module, qualname)` as a dedup
    key here would have been actively WRONG, not merely unnecessary: it
    silently collapses any two DISTINCT records that happen to share a
    `(module, qualname)` (F6's property/setter-pair collision, still real at
    whole-survey scale --
    `count_index_key_collisions(records)["finding_bearing_records"]` is 4 on
    `upstream_nonlegacy`) into a single contribution, undercounting
    `blocks_methods` by exactly that many pairs. Caught by
    `test_whole_surface_dropped_receiver_worklist_matches_direct_recount`
    (`tests/test_derive.py`), which failed against a first, `Qualkey`-set-
    deduped version of this function for precisely this reason.
    """
    blocks: dict[str, int] = {}
    for rec in records:
        # (260903, T25) `dropped_calls` entries are `DroppedCall` records,
        # not bare `str`s -- dedupe on `.expr` (a `set[str]` comprehension,
        # not `set(rec.dropped_calls)`) so a record's `blocks_methods`
        # contribution stays "once per record", unaffected by the survey
        # now preserving multiplicity WITHIN one record (two occurrences of
        # the same `expr` under different scopes must still count as one
        # method here, per this function's own docstring).
        for call_expr in {dropped.expr for dropped in rec.dropped_calls}:
            if filtered and _is_inert_dropped_receiver_call(call_expr, file=rec.file):
                continue
            blocks[call_expr] = blocks.get(call_expr, 0) + 1
    ranked = sorted(blocks.items(), key=lambda item: (-item[1], item[0]))
    return [{"call": call_expr, "blocks_methods": count} for call_expr, count in ranked]


def _stamp_to_dict(stamp: SurveyStamp) -> dict[str, Any]:
    def _git_state_to_dict(state: Any) -> dict[str, Any]:
        return {
            "hash": state.hash,
            "branch": state.branch,
            "dirty": state.dirty,
            "dirty_content_id": state.dirty_content_id,
            "provenance_source": state.provenance_source,
            "toplevel": state.toplevel,
        }

    return {
        "plr": _git_state_to_dict(stamp.plr),
        "praxis": _git_state_to_dict(stamp.praxis),
        "pylabrobot_version": stamp.pylabrobot_version,
        "stamped_at": stamp.stamped_at,
        "schema_version": stamp.schema_version,
        # T13 (260901, backlog #4859): which named Surface this stamp was
        # computed against -- additive fields, see SurveyStamp's docstring.
        "surface": stamp.surface,
        "surface_pin": stamp.surface_pin,
        # 260903 §13.4.2 (backlog #4883): the interpreter this run's
        # `sys.stdlib_module_names` came from -- the derived inert-name
        # filter's clause 1 is a fact about THIS Python, not about PLR, so a
        # rerun under a different interpreter is provenance-visible here
        # rather than silently assumed identical.
        "derive_python_version": sys.version.split()[0],
    }


def build_gap_ledger(
    index: dict[Qualkey, SurveyRecord],
    records: list[SurveyRecord],
    *,
    dropped_receiver_counts: dict[Qualkey, DroppedReceiverCounts],
    stamp: SurveyStamp | None = None,
) -> dict[str, Any]:
    """Build the gap ledger (§7.4) -- a generated build artifact, never
    hand-maintained (decision 7).

    ``totals``/``by_reason``/``top_unresolved.whole_surface`` are computed
    over the whole surface's 1,314 finding-bearing functions (§7.6: "run
    the closure over all 1,314 finding-bearing functions"). ``supported_tools``
    and the two per-method dicts are the SUPPORTED_TOOLS-only figures AC-7.4
    requires published (three commensurable method counts:
    ``methods_attempted``, ``methods_with_no_recorded_gap``,
    ``methods_with_dropped_receiver_call`` -- plus the two per-method
    call-node counts as secondary diagnostics, never a denominator, trap 8).

    ``by_category`` is keyed on ``FAILURE_CATEGORIES`` (§7 task-table note),
    with every value ``None`` in v1 (round-4 remediation, M3 -- previously
    ``0`` for every category, which reads as a MEASUREMENT of zero, not as
    "not applicable"). A gap here only ever produces an UNKNOWN finding
    downstream (reason, not category -- category is required only for
    WILL_FAIL per ``Finding.__post_init__``), and §0 fixes every v1 verdict
    at UNKNOWN, so no gap this module records is EVER classified into a
    FAILURE_CATEGORY in round 1 -- there is no detection mechanism for
    RISK-4's tripwire yet (that only becomes live once ``WILL_FAIL`` is
    first emitted, a future round). The sibling ``by_category_status`` field
    makes that explicit rather than leaving a reader to infer it from six
    identical zeros. The block is still published (schema completeness,
    forward-compatible with a future round that does classify) rather than
    omitted.

    Round-4 remediation (M11): ``totals["methods_with_dropped_receiver_call"]``
    used to be computed over ALL 4,758 indexed records while
    ``methods_attempted`` counted only the 1,314 finding-bearing ones -- a
    population mismatch that let the subset figure exceed its own
    denominator (1976 > 1314). Both are now computed over the SAME
    ``finding_bearing`` population. Separately (M11 second half),
    ``dropped_receiver_calls_by_method``/``validation_looking_dropped_
    receiver_calls_by_method`` are now summed over each ``SUPPORTED_TOOLS``
    method's WHOLE transitive closure (``_closure_wide_dropped_receiver_
    counts``), not just its own body -- see that function's docstring.
    ``top_unresolved`` gains a third view, ``dropped_receiver`` (M12/Cluster
    3/B3(e)): the D3 population ranked into an actual worklist, since it
    structurally never enters ``unresolved_calls`` and so was invisible to
    the other two views.

    Round-5 T0 item 4: ``top_unresolved.dropped_receiver`` is now sourced
    from the survey's own ``dropped_calls`` field (F1) instead of the D3
    pass's bare ``by_attr`` breakdown, so its rows are receiver-qualified
    (``self.head[channel].get_tip``, not bare ``get_tip``) and filtered
    (``_is_inert_dropped_receiver_call``) to keep an unfiltered
    ``LiquidHandler._check_args``-dominated saturation from burying the real
    signal (round-5 defense, F1). The pre-filter ranking is published
    alongside it as ``dropped_receiver_unfiltered`` rather than discarded,
    so the filter's effect is auditable from the artifact itself. The D3
    pass and its own two counters (``dropped_receiver_calls_by_method``,
    ``validation_looking_dropped_receiver_calls_by_method``, and
    ``totals``/``supported_tools``'s ``methods_with_dropped_receiver_call``)
    are UNCHANGED -- round 5 declined deleting T6's second, independent AST
    pass (it is the only one of the measured variants that sees guard sites
    behind ``if``/``raise``/``assert`` tests, per F6).

    260901 T14 (backlog #4862): two further ``top_unresolved`` views,
    ``dropped_receiver_whole_surface``/``_unfiltered`` -- the deferred-item-
    (e) worklist for a surface with no orchestration layer to derive
    ``tool_keys`` from at all (``upstream_nonlegacy``: ``liquid_handler_
    present`` is False there, so ``dropped_receiver``/``dropped_receiver_
    unfiltered`` above are structurally empty, not just small -- see
    ``_dropped_receiver_worklist_whole_surface``'s docstring). Ranked the
    same way as ``top_whole`` (own-body, no closure walk, over the whole
    ``finding_bearing`` population) rather than gated on ``tool_keys``, so
    it is populated regardless of ``liquid_handler_present``. Published
    alongside, not instead of, the closure-based pair -- they measure
    different populations and neither is a strict superset of the other.
    Dedupes on the collision-free ``(module, qualname, lineno)`` record
    identity, NOT ``(module, qualname)`` -- see
    ``_dropped_receiver_worklist_whole_surface``'s own docstring for why a
    plain ``Qualkey`` dedup would silently undercount every
    property/setter-pair collision (F6, the same population
    ``index_key_collisions`` below measures).

    Round-5 T0 item 2 (F6): ``index_key_collisions`` reports how many
    ``(module, qualname)`` keys ``build_index`` collapses -- see
    ``count_index_key_collisions``. ``methods_attempted`` still counts
    RECORDS (1,314 at the current pin); any structure keyed on
    ``(module, qualname)`` sees ``1,314 - index_key_collisions[
    "finding_bearing_records"]`` distinct keys instead. This is the
    671-vs-667 population footnote (§7.4): the whole-surface
    ``methods_with_dropped_receiver_call`` (671) is computed over the SAME
    record population as ``methods_attempted`` (M11), so it is NOT reduced
    by the collision the way a keyed traversal would be.

    260901 T11: ``contract_table`` reports the SEPARATE collision population
    that ``build_derived_contracts_payload`` (``plr_sema.derive.__main__``)
    actually keys on -- the whole 4,770-record survey's bare ``qualname``
    (not ``index_key_collisions``' ``(module, qualname)``). This is a
    strictly larger collision count (26 vs. 12 at the current pin) because
    it also catches same-named module-level functions defined in DIFFERENT
    modules, which ``(module, qualname)`` does not see as colliding at all
    -- see ``build_contract_keys``' docstring for the two independent
    sources and the disambiguator. ``total_entries`` always equals
    ``len(records)`` (every record gets exactly one key, collision-free by
    construction); ``disambiguated_keys`` is how many of those entries
    needed the ``@module:lineno`` suffix rather than the bare qualname.
    """
    if stamp is None:
        stamp = survey_stamp()

    finding_bearing = [rec for rec in records if rec.findings]  # §7.6: 1,314

    whole_totals, whole_by_reason = _run_population(finding_bearing, index, stamp)
    whole_totals["methods_with_dropped_receiver_call"] = _methods_with_dropped_receiver_call(
        finding_bearing, dropped_receiver_counts
    )

    # 260901 T13 (item 4): resolve_supported_tool returns None, does not
    # raise, when this surface has no class_name == "LiquidHandler" record
    # at all (see its own docstring). liquid_handler_present names that
    # case explicitly in the published ledger -- see the "supported_tools"
    # block below -- rather than letting an all-empty tool_keys read as
    # "checked, found zero gaps" (a silently-empty artifact masquerading as
    # a clean result).
    resolved_tool_keys = {
        name: resolve_supported_tool(name, index) for name in sorted(SUPPORTED_TOOLS)
    }
    liquid_handler_present = any(key is not None for key in resolved_tool_keys.values())
    tool_keys: dict[str, Qualkey] = (
        {name: key for name, key in resolved_tool_keys.items() if key is not None}
        if liquid_handler_present
        else {}
    )
    tool_records = [index[key] for key in tool_keys.values()]
    tools_totals, tools_by_reason = _run_population(tool_records, index, stamp)
    tools_totals["methods_with_dropped_receiver_call"] = _methods_with_dropped_receiver_call(
        tool_records, dropped_receiver_counts
    )

    dropped_by_method = {
        name: _closure_wide_dropped_receiver_counts(key, index, dropped_receiver_counts).total
        for name, key in sorted(tool_keys.items())
    }
    validation_looking_by_method = {
        name: _closure_wide_dropped_receiver_counts(
            key, index, dropped_receiver_counts
        ).validation_looking
        for name, key in sorted(tool_keys.items())
    }

    reachable = _reachable_keys(list(tool_keys.values()), index)
    top_whole = _top_unresolved_from_records(records)
    top_tools = _top_unresolved_from_records([index[key] for key in reachable])
    # (round-5 T0 item 4) Sourced from the survey's own dropped_calls field,
    # not the D3 pass's by_attr counts -- see build_gap_ledger's docstring.
    # Both the filtered (shipped) and unfiltered (audit trail) rankings are
    # computed; do not delete the unfiltered one, it is what makes the
    # filter's effect verifiable from the artifact.
    top_dropped_receiver = _dropped_receiver_worklist_from_survey(tool_keys, index, filtered=True)
    top_dropped_receiver_unfiltered = _dropped_receiver_worklist_from_survey(
        tool_keys, index, filtered=False
    )
    # 260901 T14 (backlog #4862): the surface-agnostic analogue of the two
    # views above -- own-body only, ranked over the WHOLE finding-bearing
    # population rather than a SUPPORTED_TOOLS/LiquidHandler closure. Always
    # populated, including on a surface where `liquid_handler_present` is
    # False and the two views above are therefore structurally empty (see
    # `_dropped_receiver_worklist_whole_surface`'s docstring).
    top_dropped_receiver_whole_surface = _dropped_receiver_worklist_whole_surface(
        finding_bearing, filtered=True
    )
    top_dropped_receiver_whole_surface_unfiltered = _dropped_receiver_worklist_whole_surface(
        finding_bearing, filtered=False
    )
    index_key_collisions = count_index_key_collisions(records)

    # (260901 T11) contract_table: the whole-surface derived-contracts
    # payload's own key population -- distinct from index_key_collisions
    # above, which counts (module, qualname) collisions in the SURVEY's own
    # index. This counts collisions in the CONTRACT TABLE's bare-qualname
    # key (build_contract_keys), a strictly larger population: it also
    # catches same-named module-level functions in DIFFERENT modules (26 at
    # the whole 4,770-record survey vs. index_key_collisions' 12 -- see
    # build_contract_keys' docstring for why these are independent sources).
    contract_keys = build_contract_keys(records)
    # Python identifiers (qualname, from AST FunctionDef/ClassDef names)
    # never contain "@" -- build_contract_keys's disambiguated form
    # (f"{qualname}@{module}:{lineno}") is therefore unambiguously
    # detectable by this substring check, no separate bookkeeping needed.
    disambiguated = sum(1 for k in contract_keys.values() if "@" in k)
    contract_table = {
        "total_entries": len(contract_keys),
        "distinct_bare_qualnames": len({rec.qualname for rec in records}),
        "disambiguated_keys": disambiguated,
    }

    # Round-4 remediation (M3): None, not 0 -- a gap ledger never classifies
    # any gap into a FAILURE_CATEGORY in round 1 (see docstring), so a
    # numeric 0 would read as a measurement rather than as "not applicable
    # yet". by_category_status names that explicitly.
    by_category = {category: None for category in sorted(FAILURE_CATEGORIES)}

    return {
        "schema_version": SCHEMA_VERSION,
        "stamp": _stamp_to_dict(stamp),
        "totals": whole_totals,
        "by_reason": dict(sorted(whole_by_reason.items())),
        "by_category": by_category,
        "by_category_status": "not_applicable_v1",
        "top_unresolved": {
            "whole_surface": top_whole,
            "supported_tools_closure": top_tools,
            "dropped_receiver": top_dropped_receiver,
            "dropped_receiver_unfiltered": top_dropped_receiver_unfiltered,
            # 260901 T14: surface-agnostic own-body ranking -- see
            # _dropped_receiver_worklist_whole_surface's docstring for why
            # this exists alongside (not instead of) the two views above.
            "dropped_receiver_whole_surface": top_dropped_receiver_whole_surface,
            "dropped_receiver_whole_surface_unfiltered": (
                top_dropped_receiver_whole_surface_unfiltered
            ),
        },
        "supported_tools": {
            # 260901 T13 (item 4): explicit, named marker -- every count
            # below is structurally 0 (nothing attempted, not "0 gaps
            # measured") whenever this is False. Never infer "checked, all
            # clean" from zeros alone; read this flag first.
            "liquid_handler_present": liquid_handler_present,
            "methods_attempted": tools_totals["methods_attempted"],
            "methods_with_no_recorded_gap": tools_totals["methods_with_no_recorded_gap"],
            "methods_with_gaps": tools_totals["methods_with_gaps"],
            "methods_with_dropped_receiver_call": tools_totals["methods_with_dropped_receiver_call"],
            "by_reason": dict(sorted(tools_by_reason.items())),
            **(
                {}
                if liquid_handler_present
                else {
                    "note": (
                        "no class_name == 'LiquidHandler' record in this surface's "
                        "survey index -- SUPPORTED_TOOLS' (module, qualname) mapping "
                        "(D22) is structurally unresolvable here, not merely empty of "
                        "gaps. Every count above is 0 because nothing was attempted, "
                        "not because 0 gaps were measured."
                    )
                }
            ),
        },
        "dropped_receiver_calls_by_method": dropped_by_method,
        "validation_looking_dropped_receiver_calls_by_method": validation_looking_by_method,
        "index_key_collisions": index_key_collisions,
        "contract_table": contract_table,
    }

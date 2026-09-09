"""plr_sema.verdict: the verdict/finding/report record shape (spec 260901 §3).

This is the boundary between corpus-independent plumbing (this module,
_provenance, and the import/telemetry scaffolding around it) and
corpus-gated semantics (deferred items a-f). It is specifiable without
presupposing an abstract domain, and it must not have to change when the
domain lands.

Never a boolean, at any layer. ``AnalysisReport`` (and ``Verdict`` and
``Finding``) expose no truthiness override; doing so would let
``if report:`` silently collapse the UNKNOWN verdict into a truth value and
reintroduce exactly the two-valued logic this module's three-valued
``Verdict`` was built to ban. tests/test_verdict.py AST-scans this file for
the forbidden dunder and asserts each class dict lacks it.

§3.2's report-level ``join`` is specified as *structure*, deferred as
*semantics*: today it is a pure total function of a flat finding multiset,
computed by exactly one named function below. ``join`` is an obligation
*conjunction* across independent check sites, not a control-flow-merge
join in the classical dataflow sense (round-4 remediation, M9: the prior
wording -- "a real lattice join operates over abstract states at
control-flow merge points, not over a flat finding list" -- overstated the
contrast; reaching-definitions/live-variables/available-expressions are
also lattice joins over flat fact sets). When the real abstract domain
(deferred item (a): lattice, sqsubseteq, join at branch merges, widening)
lands, ``join``'s body -- and possibly its signature -- may have to change:
(a) additionally needs a per-``operation_id`` reachability fact the flat
finding list does not carry, which is why a narrow ``reachability_map``
parameter is the anticipated extension point, preserving "exactly one
function aggregates" (a second named function is not required).
``Finding``, ``PlrSite``, and ``AnalysisReport``'s field sets are not
expected to change with it.

``Verdict`` is the OUTPUT of evaluating one obligation against one state --
it is NOT the abstract domain (spec §3, added 260901 resolving §Open
decisions 1 and 3). The state deferred item (a) builds is a separate,
internal type that needs both a top and a bottom for its own reasons
(strictness, the branch-merge join's unit); ``Verdict`` needs neither. This
resolves two questions that used to look like open ``Verdict``-design
decisions:

* **No fourth, ``UNREACHABLE`` member.** Bottom (unreachable) belongs to
  the deferred-(a) state type, not to this wire enum -- see ``Verdict``'s
  own docstring below for the reserved string and the consumer rule that
  makes adding it later, to the state type or elsewhere, non-breaking.
* **``join``'s table is NOT inverted; ``UNKNOWN`` is not "top" here.**
  ``join`` implements the OBLIGATION order (``SAFE`` ⊏ ``UNKNOWN`` ⊏
  ``WILL_FAIL``, ``WILL_FAIL`` top): one definite reachable failure among
  many unknowns must dominate, because the protocol *will* fail. A
  genuinely different, and also real, INFORMATION order (Kleene /
  Sagiv-Reps-Wilhelm: ``SAFE`` ⊔ ``WILL_FAIL`` = ``UNKNOWN``, ``UNKNOWN``
  top) governs merging *abstract states* at a branch confluence -- upstream
  of ``Finding`` emission, before any guard is evaluated against the merged
  state. That order has no call site in this module and never will:
  everything ``join`` sees is already a ``Finding``, i.e. already the
  result of evaluating one guard against one (merged) state. Both orders
  are real; they apply at different pipeline stages. See ``join``'s own
  docstring for the precondition that makes flat conjunction correct
  (independent per-guard obligations -- v1 emits exactly one ``Finding``
  per guard, so this precondition holds today by construction), and see
  ``research_a_d.md``'s R3 (group by ``operation_id``, Kleene-join within
  the group) for a proposal that must NOT be implemented: it would mask a
  definite guard failure behind a satisfied sibling guard on the same
  operation, unsound in the ``SAFE`` direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from plr_sema._provenance import SurveyStamp

SCHEMA_VERSION = 1


class Verdict(str, Enum):
    """Three-valued analysis outcome. Never collapse to a bool (see module
    docstring).

    Reserved (260901, §Open decisions 1): the wire string "unreachable" is
    reserved for a possible future member (e.g. UNREACHABLE) but is NOT a
    member today and nothing constructs it -- see the module docstring's
    "Verdict is the OUTPUT, not the domain" paragraph for why bottom
    (unreachable) belongs to deferred item (a)'s internal state type, not
    here. A consumer that meets an unrecognized Verdict string -- including
    "unreachable" -- MUST map it to UNKNOWN; see `from_wire` below. That
    rule is what makes adding a real member later, whenever and wherever it
    lands, non-breaking for compliant consumers.
    """

    SAFE = "safe"  # analysis established the operation cannot fail
    WILL_FAIL = "will_fail"  # analysis established the operation must fail
    UNKNOWN = "unknown"  # analysis established nothing (DEFAULT)

    @classmethod
    def from_wire(cls, value: str) -> Verdict:
        """Deserialize a wire string into a Verdict, per the §Open decisions
        1 consumer rule: an unrecognized string (including the reserved-but-
        unused "unreachable") maps to UNKNOWN rather than raising. This is
        always sound -- widening what a consumer knows can only lose
        precision, never fabricate a false SAFE/WILL_FAIL claim -- so it
        makes any future Verdict member a non-breaking addition for callers
        that go through this constructor instead of `Verdict(value)`
        directly. `Verdict(value)` (the plain Enum constructor) still exists
        and still raises ValueError on an unrecognized value; use it only
        where an unrecognized string is genuinely a programming error, not a
        version skew, e.g. in this package's own tests reconstructing a
        report it just serialized.
        """
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


# §3.3: closed, hand-maintained vocabulary of UNKNOWN reasons. Hand-maintained
# because it describes *our own analyzer's* give-up points, which exist in
# our source, not PLR's -- deriving it from our own AST would be circular,
# and nothing about it breaks when PLR changes. Budget: 8 today (round-4
# remediation, B4: `argument_not_static` withdrawn -- the guard-free-var
# namespace and the protocol-parameter namespace it was meant to intersect
# are disjoint in the shipped fixtures, so it never fires and would produce
# a false positive if it ever did; reinstating it requires specifying the
# binding chain guard free var -> PLR parameter position ->
# `op.arguments[param]` -> protocol expression -> `depends_on_params`; 260902
# added `channel_state_unknown`, §10.8), hard cap 12 (registry row HM-14);
# adding a 9th is a deliberate, reviewable act. 260903 (spec §14.6/§14.16 Q4,
# volume increment 5) added `volume_tracking_unasserted` and
# `volume_state_unknown` -- 8 -> 10 of the same cap 12 -- both with working
# producers under `plr_sema.check.volumestate`'s guard-evaluation table
# (§14.5) gated by §14.6's conditional-guard rule. 260904 (spec §15.7,
# increment 6, T31, user-approved 260907) added `guard_operand_unknown` and
# `guard_env_dependent` -- 10 -> 12, EXHAUSTING HM-14's headroom (`declared`
# stays 12, unchanged -- the cap itself was already 12; this spend fills it).
# Both are producers of `plr_sema.check.predicate`'s evaluator: the former
# fires when a guard's condition parses AND every free name resolves, but an
# operand OF THIS CALL is Top (a non-literal kwarg, a renamed `?<j>` kwarg,
# or a RESOURCE whose declared type/element_type cannot decide an
# `IsInstance`); the latter fires when >=1 free name never resolves to a
# call operand or a binding at all (instance state, a module global, an
# `EnvRef`), OR the guard's reachability itself is unestablished
# (depth >= 1, or a depth-0 empty scope_trail in a function with an earlier
# Return/Try/Raise/Break/Continue), OR the guard is a derived tier-(iii)
# re-raise (`InlinedGuard.is_dynamic_raise`). Any FUTURE give-up point needs
# the cap conversation -- REASON_VOCABULARY is now at 12 of 12.
REASON_VOCABULARY: frozenset[str] = frozenset(
    {
        # the target method has no entry in the derived contract table at all
        "no_contract_derived",
        # the transitive delegates_to closure hit an unresolved_calls entry
        "unresolved_delegate",
        # a guard `condition` string could not be turned into a predicate
        # (deferred item (c))
        "guard_predicate_unparsed",
        # an operation sits inside a loop whose trip count is not
        # established (deferred item (d))
        "loop_bounds_unknown",
        # OperationNode.receiver_type is None
        "receiver_type_unknown",
        # method outside the analyzed surface (mirrors §4's category)
        "unsupported_tool",
        # analyzer bug; always paired with a telemetry emit
        "internal_error",
        # 260902 (spec §10.3.3/§10.8, tip typestate increment): a guard's
        # condition parsed as a tip-state atom (deferred item (c), narrowed),
        # but the channel state it reads is Top -- the parse stage returned
        # something; the EVALUATION stage did not, which is why this cannot
        # fold into `guard_predicate_unparsed` (§10.8's own argument).
        "channel_state_unknown",
        # 260903 (spec §14.5/§14.6, volume increment 5): a volume guard's
        # atom evaluated T (would fire), but the guard is CONDITIONAL
        # (§14.6's rule) and the hypothesis is not asserted -- the analyzer
        # cannot emit WILL_FAIL for a program that may never have reached
        # the guard at all.
        "volume_tracking_unasserted",
        # 260903 (spec §14.2/§14.5): a volume guard's cell interval (or,
        # for the over-fill half, the capacity itself) is Top -- the ½
        # case of §14.5's guard-evaluation table.
        "volume_state_unknown",
        # 260904 (spec §15.7, increment 6, T31, user-approved 260907): the
        # condition parsed to a non-Opaque predicate and every free name
        # resolved, but an OPERAND of this call is Top (a non-literal
        # kwarg, a kwarg lower_calls renamed to "?<j>", or a RESOURCE whose
        # declared type/element_type cannot decide an IsInstance).
        "guard_operand_unknown",
        # 260904 (spec §15.7, increment 6, T31, user-approved 260907): the
        # condition parsed, but >=1 free name does not resolve to a call
        # operand or an alpha/beta binding at all -- instance state
        # (self.<x>, incl. an EnvRef), a module global, a backend
        # attribute, or a local the idioms decline -- OR the guard's
        # reachability is not established (depth >= 1, E-UNCOND(4); or a
        # depth-0 empty scope_trail in a K containing an earlier
        # Return/Try/Raise, E-UNCOND(5)) -- OR the guard is a derived
        # tier-(iii) re-raise (guard.is_dynamic_raise, §15.5). Tiers (ii)
        # and (iii) together, plus the two reachability give-up points.
        "guard_env_dependent",
    }
)


def vocabulary_reason(value: str) -> str:
    """Return ``value`` iff it is the empty string or a REASON_VOCABULARY member.

    Spec §3.3 (amended by increment 4 §13.3, sprint 122): the AST scan in
    ``tests/test_verdict.py`` requires every ``Finding(..., reason=...)``
    construction site to resolve to a vocabulary member *syntactically*. A
    deserialiser cannot -- its reason is data -- so this is the ONE blessed
    dynamic form the scan accepts: it raises ``ValueError`` on anything not in
    the vocabulary, so a corrupt or foreign cache entry becomes a miss rather
    than a Finding carrying a reason nobody registered.
    """
    if value == "" or value in REASON_VOCABULARY:
        return value
    raise ValueError(f"reason {value!r} is not a REASON_VOCABULARY member")


@dataclass(frozen=True, slots=True)
class PlrSite:
    """A location in PLR's own source that grounds a Finding's evidence."""

    file: str  # repo-relative, e.g. "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py"
    lineno: int
    qualname: str  # e.g. "LiquidHandler._check_containers"


@dataclass(frozen=True, slots=True)
class Finding:
    """One analyzer conclusion about one operation.

    ``category`` is required (non-empty) when ``verdict is Verdict.WILL_FAIL``.
    ``reason`` is required (non-empty, and a member of REASON_VOCABULARY) when
    ``verdict is Verdict.UNKNOWN``. Both are validated in __post_init__; this
    is legal on a frozen+slots dataclass because validation only reads
    fields, it never assigns them.
    """

    verdict: Verdict
    operation_id: str  # OperationNode.id from the extracted graph
    category: str  # in FAILURE_CATEGORIES (§4). REQUIRED for WILL_FAIL.
    plr_site: PlrSite | None  # where in PLR the evidence lives
    reason: str  # in REASON_VOCABULARY. REQUIRED for UNKNOWN.
    detail: str = ""  # human-readable; NEVER parsed by any consumer
    evidence: tuple[PlrSite, ...] = ()  # supporting guard sites, may be empty

    def __post_init__(self) -> None:
        if self.verdict is Verdict.WILL_FAIL and not self.category:
            raise ValueError(
                "Finding(verdict=WILL_FAIL) requires a non-empty category"
            )
        if self.verdict is Verdict.UNKNOWN:
            if not self.reason:
                raise ValueError("Finding(verdict=UNKNOWN) requires a non-empty reason")
            if self.reason not in REASON_VOCABULARY:
                raise ValueError(
                    f"Finding(verdict=UNKNOWN) reason={self.reason!r} is not a "
                    f"member of REASON_VOCABULARY"
                )


@dataclass(frozen=True, slots=True)
class SoundnessScope:
    """260904 (spec §15.5, increment 6, T31). NEW this increment -- there is
    no such type anywhere in `plr_sema.src/` before it. Exactly ONE field:
    `excludes_sites`, the tier-(iii) guard sites (a derived re-raise,
    `InlinedGuard.is_dynamic_raise`) folded out of the PLR-precondition
    claim for this report. A pure annotation: `join` never sees it and
    never will (its own docstring is the argument for why aggregation stays
    a single function over the flat finding multiset). Main spec Open
    decision 2 is this type's MOTIVATION, not its definition -- round-1
    C10/C18 rejected the draft's two-different-single-field version of this
    same dataclass and its `harness_internal` confusion with
    `FAILURE_CATEGORIES`."""

    excludes_sites: "tuple[PlrSite, ...]"


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """The wire-contract record for one protocol's analysis. Pinned by
    schema_version -- see this module's failure-mode note in spec §3.5.

    ``stamp`` vs. ``analyzer_stamp`` (round-4 remediation, M8): these are
    two DIFFERENT provenance facts that used to share one slot.  ``stamp``
    is the contract-BUILD-time provenance -- it is deserialized verbatim
    from whatever ``derived_contracts.json`` already recorded when
    ``plr_sema.derive`` ran (``check/`` never shells out to recompute one,
    per ``check/__init__.py``'s module docstring), so it answers "which PLR
    tree were the contracts derived against?", not "which analyzer commit
    is running right now?". ``analyzer_stamp`` is reserved for the latter
    and is ``None`` in round 1: ``check/`` cannot shell out to compute its
    own ``SurveyStamp`` (browser-side, no subprocess), and there is no
    build-time-baked constant wired in yet either. A caller that needs to
    know whether the CHECKING code itself is stale must currently get that
    from its own deployment metadata, not from this field.
    """

    protocol_fqn: str
    verdict: Verdict  # join of findings -- see join() below
    findings: tuple[Finding, ...]
    stamp: SurveyStamp  # spec §2.2 -- pins the contract-BUILD-time PLR+analyzer SHA
    schema_version: int = SCHEMA_VERSION
    analyzer_stamp: SurveyStamp | None = None  # the check-run's own provenance; None in round 1 (see docstring)
    # 260904 (spec §15.5, increment 6, T31): additive, optional --
    # `schema_version` stays 1 (an additive field, old readers unaffected,
    # per §Open-decisions-3's additive direction). `None` for every report
    # that never constructed a tier-(iii) Finding (every pre-increment-6
    # report, and any report `check_ir` is called on without threading an
    # `excludes_sites` collector -- see that function's own docstring).
    scope: "SoundnessScope | None" = None


def join(findings: tuple[Finding, ...]) -> Verdict:
    """The report-level join (spec §3.2): a pure total function of the
    finding multiset. This is the ONLY function in the package permitted to
    aggregate findings into a report verdict.

    | findings contain                  | report verdict |
    |-------------------------------------|----------------|
    | zero findings                      | UNKNOWN        |
    | any WILL_FAIL                      | WILL_FAIL      |
    | else any UNKNOWN                   | UNKNOWN        |
    | else (all SAFE, >=1 finding)       | SAFE           |

    This table is the join of the OBLIGATION order: SAFE < UNKNOWN <
    WILL_FAIL, i.e. WILL_FAIL is top (260901, §Open decisions 3 -- the
    table is NOT inverted and stays exactly as shown). One definite,
    reachable failure among ninety-nine unknowns must dominate, because a
    protocol with one such failure and ninety-nine unknowns *will* fail --
    reporting UNKNOWN there would discard the one thing a caller most needs
    to know. This is deliberately NOT the INFORMATION order (Kleene /
    Sagiv-Reps-Wilhelm: SAFE join WILL_FAIL = UNKNOWN, UNKNOWN top), which
    is also real but governs a different operation at a different pipeline
    stage: merging *abstract states* at a branch confluence, upstream of
    Finding emission, before any guard is evaluated against the merged
    state. That order has no call site in this function, or anywhere in
    this module, and never will -- everything this function sees is already
    a Finding, i.e. already the result of evaluating one guard against one
    (already-merged) state.

    Flat conjunction here is correct only under one precondition: findings
    are independent per-guard obligations, not multiple claims about the
    SAME obligation from different paths. v1 satisfies this by construction
    -- `check._findings_for_operation` emits exactly one Finding per guard
    in the resolved contract (e.g. 9 findings for `aspirate`, one per guard
    site), so two findings sharing an `operation_id` are two distinct,
    correctly-conjoining obligations today, not the same obligation seen
    twice. Do NOT "fix" this by grouping input findings by `operation_id`
    and Kleene-joining within the group (`research_a_d.md`'s R3) -- that
    would mask a definite guard failure whenever a sibling guard on the
    same operation happens to be satisfied, which is unsound in the SAFE
    direction. See `test_join_absorbs_across_shared_operation_id` in
    `test_verdict.py`, which pins the correct per-guard conjoining
    behavior this precondition describes.

    Round-4 remediation (B1/B2/§0(ii)): zero findings now maps to UNKNOWN
    UNCONDITIONALLY, not deferred. Round 1/2/3 argued the empty case was
    "unreachable in v1" because §7's totality guarantee (AC-7.2) supposedly
    emits an UNKNOWN finding for every operation -- but that guarantee was
    never actually enforced at the `check_graph` call boundary (nothing
    asserted `join(())` itself, and nothing asserted every operation in a
    graph receives >=1 finding), so a reachable public path
    (`check_graph` on a graph with zero operations, or a resolved contract
    with zero guards/gaps/no loop) returned `SAFE` -- a live soundness bug,
    not a deferred one. `check/` now also independently guarantees the
    per-operation side (see `check._findings_for_operation`'s fallback
    finding), so this function no longer needs to trust that guarantee to
    stay sound: an empty multiset is UNKNOWN by construction, regardless of
    how it got here.
    """
    if not findings:
        return Verdict.UNKNOWN
    verdicts = {finding.verdict for finding in findings}
    if Verdict.WILL_FAIL in verdicts:
        return Verdict.WILL_FAIL
    if Verdict.UNKNOWN in verdicts:
        return Verdict.UNKNOWN
    return Verdict.SAFE

"""Drift audit module for the ingest pipeline (§5).

Detects discrepancies between the 91 recipes' `apis` tokens and canonical tables
(TOOL_SCHEMA, PARAM_NAMESPACE, NON_SURFACE_VERB_REASONS). Produces two hashes
per finding (identity-stable finding_id, decision-sensitive adjudicable_digest)
and coordinates gate evaluation with committed adjudications.

C3 (two-hash design), C4 (phantom/no-backend partition), C13 (table-edit
consequence protocol), R4-B3 (enum-interpolation fix), R5-W4 (payload
structuring), R3-B1 (table-sensitivity per-kind), and PM-3 (ownership in writing).
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Final, Mapping, TextIO

from . import cli, io, recipes, sources
from .versions import AUDIT_RULES_VERSION
from coxswain.plr.tool_schema import TOOL_SCHEMA, PHASE2_TOOL_NAMES
from coxswain.plr.param_namespace import PARAM_NAMESPACE
from overlay_gen.miner import NON_SURFACE_VERB_REASONS


# ============================================================================
# Exceptions
# ============================================================================

class AuditError(cli.IngestError):
    """Raised for audit logic errors, data inconsistencies, or missing files."""

    pass


# ============================================================================
# Enums and Data Classes — Finding shape (§5.2)
# ============================================================================

@dataclass(frozen=True)
class Evidence:
    """A single piece of evidence linking a token to a finding."""

    recipe_path: str
    token_raw: str
    token_kind: recipes.TokenKind
    receiver: str | None  # None for every non-DOTTED token
    receiver_type: recipes.ReceiverType  # NONE for every non-DOTTED token
    member: str
    member_is_in_surface: bool  # member in PHASE2_TOOL_NAMES, exact + case-sensitive
    match_mode: MatchMode


class MatchMode(str, Enum):
    """How a token was matched to a subject (§5.2, W5)."""

    EXACT = "exact"
    CLASSISH_CASEFOLD = "classish_casefold"


@dataclass(frozen=True)
class Finding:
    """A single finding produced by the audit."""

    finding_id: str  # compute_finding_id(kind, subject) — identity only
    adjudicable_digest: str  # _sha16(_adjudicable_view(self))
    kind: "FindingKind"
    subject: str  # EXACTLY as defined by the table in §5.2
    blocking: bool
    verdict: str  # "" for kinds without a verdict enum
    evidence: tuple[Evidence, ...]
    reading_table_is_wrong: str
    reading_api_moved: str
    verdict_hint: str  # mechanical classification; NEVER a decision


class FindingKind(str, Enum):
    """Ten kinds of findings, three auxiliary verdicts, and one blocking guard (§5.4)."""

    PHANTOM_VERB = "phantom_verb"  # blocking (per experimental_partition.json)
    RECEIVER_DRIFT = "receiver_drift"  # blocking
    SURFACE_ADJACENT = "surface_adjacent"  # blocking
    PARAM_MISATTRIBUTED = "param_misattributed"  # blocking
    UNKNOWN_METHOD = "unknown_method"  # advisory
    SCHEMA_UNMENTIONED = "schema_unmentioned"  # advisory
    PARAM_CANDIDATE = "param_candidate"  # advisory
    UNCLASSIFIED_TOKEN = "unclassified_token"  # advisory
    NO_BACKEND_VERB = "no_backend_verb"  # advisory
    UNMAPPED_RECEIVER = "unmapped_receiver"  # advisory


BLOCKING_KINDS: Final[frozenset[FindingKind]] = frozenset({
    FindingKind.PHANTOM_VERB,
    FindingKind.RECEIVER_DRIFT,
    FindingKind.SURFACE_ADJACENT,
    FindingKind.PARAM_MISATTRIBUTED,
})


class PhantomVerdict(str, Enum):
    """Verdict for phantom_verb findings (§5.3, W5)."""

    CONTESTED = "contested"  # >=1 DOTTED lh/pr receiver (phantom claim DISPUTED)
    KWARG_ONLY = "kwarg_only"  # bare IDENT/CLASSISH or IDENT siblings (phantom SUPPORTED)
    NO_EVIDENCE = "no_evidence"  # absent from all 91 recipes


# ============================================================================
# Hashing (§5.2, R4-B3)
# ============================================================================

def canonical_json(obj: Any) -> bytes:
    """Serialize to canonical JSON: sorted keys, compact, ASCII-safe, NaN-strict.

    §5.2 (R4-B3): the serializer is DEFINED here with all arguments justified.
    Do NOT use this for human-facing artifacts — use §7.4's artifact serializer
    instead (indent=1, ensure_ascii=False for human diffs).
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha16(obj: Any) -> str:
    """Hash to 16 hex chars (first half of SHA-256)."""
    return hashlib.sha256(canonical_json(obj)).hexdigest()[:16]


def _finding_id_payload(kind: FindingKind, subject: str) -> dict[str, str]:
    """Construct the identity-only payload for a finding (§5.2, R4-B3, R5-W4).

    §5.2 (R4-B3): raises AuditError if kind is not a FindingKind, preventing the
    two-key-space hazard from widening the parameter to str | FindingKind.
    """
    if not isinstance(kind, FindingKind):
        raise AuditError(
            "compute_finding_id takes a FindingKind member, not "
            f"{type(kind).__name__}. Widening this parameter to `str | FindingKind` "
            "creates two key spaces for one finding (R2-B2); coerce at the call site."
        )
    return {
        "kind": kind.value,
        "subject": subject,
        "rules_version": AUDIT_RULES_VERSION,
    }


def compute_finding_id(kind: FindingKind, subject: str) -> str:
    """Compute a finding's identity hash (unchanged by evidence changes)."""
    return _sha16(_finding_id_payload(kind, subject))


def dotted_subject(receiver_type: recipes.ReceiverType, member: str) -> str:
    """Construct a dotted-kind subject (§5.2, R5-W4)."""
    return receiver_type.value + "." + member


def param_subject(in_surface_verb: str, token: str) -> str:
    """Construct a param_candidate subject (§5.2, R5-W4)."""
    return in_surface_verb + ":" + token


def _adjudicable_view(f: Finding) -> dict[str, Any]:
    """The decision-determining projection used for adjudicable_digest (§5.2, C3)."""
    return {
        "kind": f.kind.value,
        "subject": f.subject,
        "rules_version": AUDIT_RULES_VERSION,
        "verdict": f.verdict,
        "blocking": f.blocking,
        # distinct evidence CLASSES (not paths or counts)
        "evidence_classes": sorted({
            (e.token_kind.value, e.receiver_type.value, e.member_is_in_surface, e.match_mode.value)
            for e in f.evidence
        }),
        "subject_table_fingerprint": subject_table_fingerprint(f.kind, f.subject),
    }


# ============================================================================
# Phantom/No-Backend Partition (§5.3, C4)
# ============================================================================

def load_experimental_partition(path: Path | None = None) -> tuple[frozenset[str], frozenset[str]]:
    """Load the partition of experimental verbs into phantom vs no-backend (§5.3).

    Args:
        path: Path to experimental_partition.json (default: data/ relative to this module).

    Returns:
        (PHANTOM_VERBS, NO_BACKEND_VERBS) — two frozensets with no overlap.

    Raises:
        AuditError: if any loader invariant fails.
    """
    if path is None:
        path = Path(__file__).parent / "data" / "experimental_partition.json"

    if not path.exists():
        raise AuditError(f"experimental_partition.json not found at {path}")

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise AuditError(f"invalid JSON in experimental_partition.json: {e}")

    phantom = set(data.get("phantom", {}))
    no_backend = set(data.get("no_backend", {}))

    # Invariant: disjoint and complete partition of experimental entries
    if phantom & no_backend:
        raise AuditError(
            f"experimental_partition.json: phantom and no_backend overlap: {phantom & no_backend}"
        )

    experimental = {n for n, s in TOOL_SCHEMA.items() if s.experimental}
    partition = phantom | no_backend

    if partition != experimental:
        raise AuditError(
            f"experimental_partition.json: partition {partition} does not match "
            f"experimental TOOL_SCHEMA entries {experimental}"
        )

    # Invariant: every key is in NON_SURFACE_VERB_REASONS
    for verb in partition:
        if verb not in NON_SURFACE_VERB_REASONS:
            raise AuditError(
                f"experimental_partition.json: verb {verb!r} not found in "
                "NON_SURFACE_VERB_REASONS"
            )

    return frozenset(phantom), frozenset(no_backend)


PHANTOM_VERBS: Final[frozenset[str]]
NO_BACKEND_VERBS: Final[frozenset[str]]

try:
    PHANTOM_VERBS, NO_BACKEND_VERBS = load_experimental_partition()
except AuditError as e:
    raise AuditError(f"Failed to load experimental partition: {e}") from e


# ============================================================================
# Fingerprinting (§5.7)
# ============================================================================

def _projection() -> dict[str, Any]:
    """The decision-relevant projection of canonical tables (§5.7, R4-B3).

    Note: receiver_type is a plain str, not an enum — verified in tool_schema.py:41.
    """
    return {
        "tools": {
            n: {
                "receiver_type": s.receiver_type,
                "experimental": s.experimental,
                "phase2_included": s.phase2_included,
            }
            for n, s in sorted(TOOL_SCHEMA.items())
        },
        "params": {
            v: [
                {
                    "name": p.name,
                    "plr_arg": p.plr_arg,
                    "kind": p.kind.value,
                    "required": p.required,
                }
                for p in specs
            ]
            for v, specs in sorted(PARAM_NAMESPACE.items())
        },
        "non_surface": sorted(NON_SURFACE_VERB_REASONS),
    }


def canonical_tables_fingerprint() -> str:
    """Hash of the canonical tables (TOOL_SCHEMA, PARAM_NAMESPACE, NON_SURFACE_VERB_REASONS)."""
    return _sha16(_projection())


_VERB_KINDS = frozenset({
    FindingKind.PHANTOM_VERB,
    FindingKind.NO_BACKEND_VERB,
    FindingKind.SCHEMA_UNMENTIONED,
})
_DOTTED_KINDS = frozenset({
    FindingKind.RECEIVER_DRIFT,
    FindingKind.SURFACE_ADJACENT,
    FindingKind.UNKNOWN_METHOD,
})
_PARAM_KINDS = frozenset({
    FindingKind.PARAM_MISATTRIBUTED,
    FindingKind.PARAM_CANDIDATE,
})
_NO_TABLE_KINDS = frozenset({
    FindingKind.UNCLASSIFIED_TOKEN,
    FindingKind.UNMAPPED_RECEIVER,
})
_SCOPED = _VERB_KINDS | _DOTTED_KINDS | _PARAM_KINDS | _NO_TABLE_KINDS

if _SCOPED != set(FindingKind):
    raise AuditError(
        f"kinds with no declared table scope: {set(FindingKind) - _SCOPED}"
    )

_RECEIVER_TYPE_VALUES: Final[frozenset[str]] = frozenset(
    r.value for r in recipes.ReceiverType
)


def _verb_slice(v: str) -> dict[str, Any]:
    """Membership record for a verb over all three tables (§5.7, Case A)."""
    proj = _projection()
    return {
        "scope": "verb",
        "verb": v,
        "in_tool_schema": v in proj["tools"],
        "tool_row": proj["tools"].get(v),
        "in_param_namespace": v in proj["params"],
        "param_rows": proj["params"].get(v),
        "in_non_surface": v in NON_SURFACE_VERB_REASONS,
    }


def _param_slice(tok: str, verb: str | None) -> dict[str, Any]:
    """Param-space membership record (§5.7, Case B)."""
    proj = _projection()
    hits = {
        v: [r for r in rows if r["name"] == tok or r["plr_arg"] == tok]
        for v, rows in proj["params"].items()
    }
    return {
        "scope": "param",
        "token": tok,
        "declaring_verb": verb,
        "rows_by_verb": {v: r for v, r in sorted(hits.items()) if r},
        "declared_anywhere": any(hits.values()),
    }


def _no_table_slice(kind: FindingKind, subject: str) -> dict[str, Any]:
    """Slice for kinds with scope=none (§5.7, Case C)."""
    return {
        "scope": "none",
        "kind": kind.value,
        "subject": subject,
    }


def subject_table_fingerprint(kind: FindingKind, subject: str) -> str:
    """Hash of a subject's canonical-table lookup result, misses included (§5.7).

    Args:
        kind: FindingKind (used to dispatch on subject structure).
        subject: The subject string (format depends on kind).

    Returns:
        16-char hex hash of the subject's table slice.

    Raises:
        AuditError: if subject parsing fails or a blocking kind uses scope=none.
    """
    if kind in _VERB_KINDS:
        sl = _verb_slice(subject)
    elif kind in _DOTTED_KINDS:
        recv, sep, member = subject.partition(".")
        if not sep or recv not in _RECEIVER_TYPE_VALUES:
            raise AuditError(
                f"{kind.value}: subject {subject!r} is not '<receiver_type>.<member>'"
            )
        sl = _verb_slice(member)
    elif kind is FindingKind.PARAM_CANDIDATE:
        verb, sep, tok = subject.partition(":")
        if not sep:
            raise AuditError(
                f"param_candidate: subject {subject!r} is not '<verb>:<token>'"
            )
        sl = _param_slice(tok, verb)
    elif kind is FindingKind.PARAM_MISATTRIBUTED:
        sl = _param_slice(subject, None)
    else:  # kind in _NO_TABLE_KINDS
        sl = _no_table_slice(kind, subject)

    if sl["scope"] == "none" and kind in BLOCKING_KINDS:
        raise AuditError(
            f"{kind.value} is blocking and must not use scope=none"
        )

    return _sha16(sl)


# ============================================================================
# Audit Result and Main Audit Logic
# ============================================================================

@dataclass
class AuditResult:
    """Result of running the audit against a cookbook."""

    findings: tuple[Finding, ...]
    blocking_census: dict[str, int]


def run_audit(recipes_path: Path | None = None) -> AuditResult:
    """Run the full audit against the cookbook (§5.1–§5.4).

    Args:
        recipes_path: Path to recipes.yml (default: project default_recipes_path()).

    Returns:
        AuditResult with findings and blocking_census.

    Raises:
        CookbookUnavailable: if recipes cannot be loaded.
        AuditError: if audit logic fails.
    """
    # Load recipes
    if recipes_path is None:
        recipes_path = recipes.default_recipes_path()

    cookbook = recipes.load_recipes(recipes_path)

    # Collect evidence by (kind, subject)
    evidence_by_key: dict[tuple[FindingKind, str], list[Evidence]] = {}

    # Track all verbs seen in recipes (for schema_unmentioned)
    verbs_in_cookbook: set[str] = set()

    # Process each recipe to extract evidence
    for recipe in cookbook:
        # Determine in-surface verbs for this recipe (for param_candidate cross-product).
        # Shared with ingest.gap's T3 out-of-surface-anchor predicate (§6.4) — one
        # definition, two callers (recipes.in_surface_verbs).
        in_surface_verbs: set[str] = set(recipes.in_surface_verbs(recipe))

        for token in recipe.api_tokens:
            if not recipes.method_shaped(token):
                # Non-method-shaped tokens (CLASSISH, PROSE, OTHER)
                if token.kind == recipes.TokenKind.CLASSISH:
                    # Can only be corroborating evidence for phantoms
                    pass
                elif token.kind == recipes.TokenKind.OTHER:
                    # Unclassified token
                    key = (FindingKind.UNCLASSIFIED_TOKEN, token.raw)
                    if key not in evidence_by_key:
                        evidence_by_key[key] = []
                continue

            # Method-shaped tokens
            if token.kind == recipes.TokenKind.IDENT:
                member = token.member

                # Check if it's a phantom verb (primary match, exact)
                if member in PHANTOM_VERBS:
                    ev = Evidence(
                        recipe_path=recipe.path,
                        token_raw=token.raw,
                        token_kind=token.kind,
                        receiver=None,
                        receiver_type=recipes.ReceiverType.NONE,
                        member=member,
                        member_is_in_surface=member in PHASE2_TOOL_NAMES,
                        match_mode=MatchMode.EXACT,
                    )
                    key = (FindingKind.PHANTOM_VERB, member)
                    if key not in evidence_by_key:
                        evidence_by_key[key] = []
                    evidence_by_key[key].append(ev)

                # Check if it's in TOOL_SCHEMA or NON_SURFACE_VERB_REASONS
                elif member in TOOL_SCHEMA or member in NON_SURFACE_VERB_REASONS:
                    verbs_in_cookbook.add(member)

                # Check if it's param_misattributed: a bare IDENT equal to some
                # ParamSpec's name/plr_arg, in a recipe naming a DIFFERENT
                # in-surface verb and NEVER the declaring one (§5.4, §5.4.1).
                # Keyed on the bare token, not (token, declaring_verb) -- §5.2
                # property 2: a pair key would emit two findings about one token.
                declaring_verbs = {
                    v for v, specs in PARAM_NAMESPACE.items()
                    if any(s.name == member or s.plr_arg == member for s in specs)
                }
                if declaring_verbs and in_surface_verbs and not (declaring_verbs & in_surface_verbs):
                    key = (FindingKind.PARAM_MISATTRIBUTED, member)
                    if key not in evidence_by_key:
                        evidence_by_key[key] = []
                    ev = Evidence(
                        recipe_path=recipe.path,
                        token_raw=token.raw,
                        token_kind=token.kind,
                        receiver=None,
                        receiver_type=recipes.ReceiverType.NONE,
                        member=member,
                        member_is_in_surface=member in PHASE2_TOOL_NAMES,
                        match_mode=MatchMode.EXACT,
                    )
                    evidence_by_key[key].append(ev)

                # Check if it's a param candidate: an IDENT co-occurring with an
                # in-surface verb that is NOT that verb's declared name/plr_arg (§5.4).
                for in_surface_verb in in_surface_verbs:
                    declared = False
                    if in_surface_verb in PARAM_NAMESPACE:
                        declared = any(
                            param_spec.name == member or param_spec.plr_arg == member
                            for param_spec in PARAM_NAMESPACE[in_surface_verb]
                        )
                    if not declared:
                        subject = param_subject(in_surface_verb, member)
                        key = (FindingKind.PARAM_CANDIDATE, subject)
                        if key not in evidence_by_key:
                            evidence_by_key[key] = []
                        ev = Evidence(
                            recipe_path=recipe.path,
                            token_raw=token.raw,
                            token_kind=token.kind,
                            receiver=None,
                            receiver_type=recipes.ReceiverType.NONE,
                            member=member,
                            member_is_in_surface=False,
                            match_mode=MatchMode.EXACT,
                        )
                        evidence_by_key[key].append(ev)

            elif token.kind == recipes.TokenKind.CLASSISH:
                member = token.member

                # Can be corroborating evidence for phantoms (casefold match)
                for verb in PHANTOM_VERBS:
                    if member.lower() == verb.lower():
                        ev = Evidence(
                            recipe_path=recipe.path,
                            token_raw=token.raw,
                            token_kind=token.kind,
                            receiver=None,
                            receiver_type=recipes.ReceiverType.NONE,
                            member=member,
                            member_is_in_surface=False,
                            match_mode=MatchMode.CLASSISH_CASEFOLD,
                        )
                        key = (FindingKind.PHANTOM_VERB, verb)
                        if key not in evidence_by_key:
                            evidence_by_key[key] = []
                        evidence_by_key[key].append(ev)

            elif token.kind == recipes.TokenKind.DOTTED:
                member = token.member
                receiver_type = token.receiver_type

                # Check if it's a method in TOOL_SCHEMA
                if member in TOOL_SCHEMA:
                    schema_rt = TOOL_SCHEMA[member].receiver_type
                    if receiver_type.value != schema_rt:
                        # receiver_drift
                        subject = dotted_subject(receiver_type, member)
                        key = (FindingKind.RECEIVER_DRIFT, subject)
                        if key not in evidence_by_key:
                            evidence_by_key[key] = []
                        ev = Evidence(
                            recipe_path=recipe.path,
                            token_raw=token.raw,
                            token_kind=token.kind,
                            receiver=token.receiver,
                            receiver_type=receiver_type,
                            member=member,
                            member_is_in_surface=member in PHASE2_TOOL_NAMES,
                            match_mode=MatchMode.EXACT,
                        )
                        evidence_by_key[key].append(ev)
                    verbs_in_cookbook.add(member)

                # Check if it's in NON_SURFACE_VERB_REASONS
                elif member in NON_SURFACE_VERB_REASONS:
                    verbs_in_cookbook.add(member)

                # Check if it's surface_adjacent (in neither table, lh/pr receiver)
                elif (
                    member not in TOOL_SCHEMA
                    and member not in NON_SURFACE_VERB_REASONS
                    and receiver_type in {recipes.ReceiverType.LIQUID_HANDLER,
                                         recipes.ReceiverType.PLATE_READER}
                ):
                    subject = dotted_subject(receiver_type, member)
                    key = (FindingKind.SURFACE_ADJACENT, subject)
                    if key not in evidence_by_key:
                        evidence_by_key[key] = []
                    ev = Evidence(
                        recipe_path=recipe.path,
                        token_raw=token.raw,
                        token_kind=token.kind,
                        receiver=token.receiver,
                        receiver_type=receiver_type,
                        member=member,
                        member_is_in_surface=member in PHASE2_TOOL_NAMES,
                        match_mode=MatchMode.EXACT,
                    )
                    evidence_by_key[key].append(ev)

                # Check if it's unknown_method (in neither table, other receiver)
                elif (
                    member not in TOOL_SCHEMA
                    and member not in NON_SURFACE_VERB_REASONS
                    and receiver_type not in {recipes.ReceiverType.LIQUID_HANDLER,
                                            recipes.ReceiverType.PLATE_READER}
                ):
                    subject = dotted_subject(receiver_type, member)
                    key = (FindingKind.UNKNOWN_METHOD, subject)
                    if key not in evidence_by_key:
                        evidence_by_key[key] = []
                    ev = Evidence(
                        recipe_path=recipe.path,
                        token_raw=token.raw,
                        token_kind=token.kind,
                        receiver=token.receiver,
                        receiver_type=receiver_type,
                        member=member,
                        member_is_in_surface=member in PHASE2_TOOL_NAMES,
                        match_mode=MatchMode.EXACT,
                    )
                    evidence_by_key[key].append(ev)

    # Emit findings from collected evidence
    findings: list[Finding] = []

    # 1. phantom_verb findings (always blocking, one per PHANTOM_VERBS member)
    for verb in sorted(PHANTOM_VERBS):
        subject = verb
        verdict = _classify_phantom_verdict(evidence_by_key, verb)
        ev_list = evidence_by_key.get((FindingKind.PHANTOM_VERB, subject), [])
        f = Finding(
            finding_id=compute_finding_id(FindingKind.PHANTOM_VERB, subject),
            adjudicable_digest="",  # computed below
            kind=FindingKind.PHANTOM_VERB,
            subject=subject,
            blocking=True,
            verdict=verdict.value,
            evidence=tuple(sorted(ev_list, key=lambda e: (e.recipe_path, e.token_raw))),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint=f"mechanical: {verdict.value}",
        )
        f = _with_digests(f)
        findings.append(f)

    # 2. no_backend_verb findings (advisory, one per NO_BACKEND_VERBS member)
    for verb in sorted(NO_BACKEND_VERBS):
        subject = verb
        ev_list = evidence_by_key.get((FindingKind.NO_BACKEND_VERB, subject), [])
        f = Finding(
            finding_id=compute_finding_id(FindingKind.NO_BACKEND_VERB, subject),
            adjudicable_digest="",
            kind=FindingKind.NO_BACKEND_VERB,
            subject=subject,
            blocking=False,
            verdict="",
            evidence=tuple(sorted(ev_list, key=lambda e: (e.recipe_path, e.token_raw))),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )
        f = _with_digests(f)
        findings.append(f)

    # 3. Other blocking/advisory findings
    for (kind, subject), ev_list in evidence_by_key.items():
        # Skip phantom and no_backend verbs (already emitted)
        if kind in {FindingKind.PHANTOM_VERB, FindingKind.NO_BACKEND_VERB}:
            continue

        blocking = kind in BLOCKING_KINDS
        f = Finding(
            finding_id=compute_finding_id(kind, subject),
            adjudicable_digest="",
            kind=kind,
            subject=subject,
            blocking=blocking,
            verdict="",
            evidence=tuple(sorted(ev_list, key=lambda e: (e.recipe_path, e.token_raw))),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )
        f = _with_digests(f)
        findings.append(f)

    # 4. schema_unmentioned findings (advisory)
    for verb in sorted(TOOL_SCHEMA.keys()):
        if verb not in verbs_in_cookbook and verb not in PHANTOM_VERBS and verb not in NO_BACKEND_VERBS:
            subject = verb
            f = Finding(
                finding_id=compute_finding_id(FindingKind.SCHEMA_UNMENTIONED, subject),
                adjudicable_digest="",
                kind=FindingKind.SCHEMA_UNMENTIONED,
                subject=subject,
                blocking=False,
                verdict="",
                evidence=(),
                reading_table_is_wrong="",
                reading_api_moved="",
                verdict_hint="",
            )
            f = _with_digests(f)
            findings.append(f)

    # Sort findings by finding_id for deterministic output
    findings.sort(key=lambda f: f.finding_id)

    # Compute blocking census
    blocking_census = {k.value: 0 for k in BLOCKING_KINDS}
    for f in findings:
        if f.blocking:
            blocking_census[f.kind.value] += 1

    return AuditResult(findings=tuple(findings), blocking_census=blocking_census)


def _with_digests(f: Finding) -> Finding:
    """Create a new Finding with adjudicable_digest computed."""
    digest = _sha16(_adjudicable_view(f))
    return Finding(
        finding_id=f.finding_id,
        adjudicable_digest=digest,
        kind=f.kind,
        subject=f.subject,
        blocking=f.blocking,
        verdict=f.verdict,
        evidence=f.evidence,
        reading_table_is_wrong=f.reading_table_is_wrong,
        reading_api_moved=f.reading_api_moved,
        verdict_hint=f.verdict_hint,
    )


def _classify_phantom_verdict(
    evidence_by_key: dict[tuple[FindingKind, str], list[Evidence]],
    verb: str,
) -> PhantomVerdict:
    """Classify a phantom verb's verdict based on evidence (§5.3, W5).

    Two-stage rule: primary matches (exact, case-sensitive) determine the verdict.
    Corroborating matches (CLASSISH casefold) can only support KWARG_ONLY, never CONTESTED.
    """
    ev_list = evidence_by_key.get((FindingKind.PHANTOM_VERB, verb), [])

    if not ev_list:
        return PhantomVerdict.NO_EVIDENCE

    # Stage 1: Check for CONTESTED (primary matches with DOTTED lh/pr receiver)
    for ev in ev_list:
        if (
            ev.match_mode == MatchMode.EXACT
            and ev.token_kind == recipes.TokenKind.DOTTED
            and ev.receiver_type in {recipes.ReceiverType.LIQUID_HANDLER,
                                     recipes.ReceiverType.PLATE_READER}
        ):
            return PhantomVerdict.CONTESTED

    # Stage 2: Check for primary IDENT/CLASSISH evidence
    has_primary_ident = any(
        ev.match_mode == MatchMode.EXACT and ev.token_kind == recipes.TokenKind.IDENT
        for ev in ev_list
    )

    if has_primary_ident:
        return PhantomVerdict.KWARG_ONLY

    # Stage 3: Check for CLASSISH corroborating evidence (casefold match)
    has_classish_casefold = any(
        ev.match_mode == MatchMode.CLASSISH_CASEFOLD
        for ev in ev_list
    )

    if has_classish_casefold:
        # Corroborating matches can only support KWARG_ONLY
        # but need at least one primary to base the decision on
        # If we only have casefold, it's insufficient, return NO_EVIDENCE
        # Actually, re-reading the spec: "appears only as bare IDENT or CLASSISH"
        # means KWARG_ONLY. But casefold is "corroborating" which means secondary.
        # So casefold alone is not enough for a verdict.
        return PhantomVerdict.NO_EVIDENCE

    return PhantomVerdict.NO_EVIDENCE


# ============================================================================
# Gate Mechanics (§5.5)
# ============================================================================

ACTION_REF_RE: Final[re.Pattern[str]] = re.compile(
    r"^(backlog:[a-z0-9][a-z0-9_-]*"
    r"|commit:[0-9a-f]{40}"
    r"|issue:https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)$"
)


def load_blocking_census(path: Path | None = None) -> dict[str, int]:
    """Load and validate the blocking_census.json file (§5.4.1, C4).

    Args:
        path: Path to blocking_census.json (default: data/blocking_census.json).

    Returns:
        The census dict with keys matching BLOCKING_KINDS.

    Raises:
        AuditError: if file is missing, malformed, or has wrong keys.
    """
    if path is None:
        path = Path(__file__).parent / "data" / "blocking_census.json"

    # R4-W10: all three failure fixtures (missing, invalid JSON, wrong key set)
    # must name the path AND the remedy that produces it, so a CI operator sees
    # what to run regardless of which of the three ways the file is broken.
    remedy = f"Generate it with: ingest.audit --emit-census --out <dir>"

    if not path.exists():
        raise AuditError(f"blocking_census.json not found at {path}. {remedy}")

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise AuditError(f"invalid JSON in blocking_census.json at {path}: {e}. {remedy}")

    census = data.get("census", {})
    expected_keys = {k.value for k in BLOCKING_KINDS}
    actual_keys = set(census.keys())

    if actual_keys != expected_keys:
        raise AuditError(
            f"blocking_census.json at {path} keys {actual_keys} do not match "
            f"BLOCKING_KINDS {expected_keys}. {remedy}"
        )

    return census


def load_adjudications(path: Path | None = None) -> Mapping[str, Mapping[str, Any]]:
    """Load and parse adjudications.json (§5.5, G2).

    Args:
        path: Path to audit_adjudications.json (default: data/audit_adjudications.json).

    Returns:
        Nested dict: {finding_id: {adjudication fields}}.

    Raises:
        AuditError: if file is missing or malformed.
    """
    if path is None:
        path = Path(__file__).parent / "data" / "audit_adjudications.json"

    if not path.exists():
        return {}  # Empty adjudications is OK for Task 5; Task 6 makes it mandatory

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise AuditError(f"invalid JSON in audit_adjudications.json: {e}")

    return data.get("adjudications", {})


def gate(
    recipes_path: Path | None = None,
    adjudications_path: Path | None = None,
    census_path: Path | None = None,
    out: TextIO = sys.stdout,
) -> int:
    """Gate evaluation: load audit, census, and adjudications; check completeness (§5.5, G2).

    Returns:
        Exit code (0=pass, 1=measurement error, 2=unadjudicated blocking, 5=inconclusive).

    Never calls sys.exit(); returns int for in-process testing.
    """
    # Step 1: Load recipes and run audit
    try:
        if recipes_path is None:
            recipes_path = recipes.default_recipes_path()
        result = run_audit(recipes_path)
    except recipes.CookbookUnavailable as e:
        print(f"Error: {e}", file=out)
        return cli.EXIT_INCONCLUSIVE

    # Step 2: Load blocking census
    try:
        if census_path is None:
            census_path = Path(__file__).parent / "data" / "blocking_census.json"
        pinned_census = load_blocking_census(census_path)
    except AuditError as e:
        print(f"Error: {e}", file=out)
        return cli.EXIT_MEASUREMENT_ERROR

    # Step 3: Compare census (census mismatch is NOT a failure)
    for kind_str, pinned_count in pinned_census.items():
        observed_count = result.blocking_census.get(kind_str, 0)
        if observed_count != pinned_count:
            print(
                f"census_drift kind={kind_str} pinned={pinned_count} observed={observed_count}",
                file=out,
            )

    # Step 4: Check adjudication completeness
    if adjudications_path is None:
        adjudications_path = Path(__file__).parent / "data" / "audit_adjudications.json"
    adjudications = load_adjudications(adjudications_path)

    blocking_findings = [f for f in result.findings if f.blocking]
    failures = []

    for f in blocking_findings:
        if f.finding_id not in adjudications:
            failures.append((f.finding_id, "missing"))
            continue

        adj = adjudications[f.finding_id]

        # Check required fields
        missing_fields = _check_adjudication_fields(adj, f)
        if missing_fields:
            failures.append((f.finding_id, f"incomplete: {missing_fields}"))
            continue

        # Check digest staleness
        if adj.get("adjudicated_digest") != f.adjudicable_digest:
            print(
                f"stale_digest {f.finding_id}: "
                f"expected {f.adjudicable_digest}, got {adj.get('adjudicated_digest')}",
                file=out,
            )
            failures.append((f.finding_id, "stale_digest"))

    if failures:
        for fid, reason in failures:
            print(f"unadjudicated {fid}: {reason}", file=out)
        return cli.EXIT_UNADJUDICATED_BLOCKING

    # Step 5: All passed
    return cli.EXIT_OK


def _check_adjudication_fields(adj: Mapping[str, Any], f: Finding) -> str | None:
    """Check that an adjudication has all required fields (§5.5, G2)."""
    # reading must be in the enum
    reading_enum = {
        "table_is_wrong",
        "api_moved_0_2_2_to_head",
        "cookbook_token_not_an_api",
        "token_is_not_a_method",
        "confirms_current_table",
    }
    if adj.get("reading") not in reading_enum:
        return f"invalid reading {adj.get('reading')!r}"

    # rationale >= 40 chars
    rationale = adj.get("rationale", "")
    if not rationale or len(rationale) < 40:
        return f"rationale too short (got {len(rationale)} chars, need 40)"

    # adjudicated_by and adjudicated_on non-empty
    if not adj.get("adjudicated_by") or not adj.get("adjudicated_on"):
        return "missing adjudicated_by or adjudicated_on"

    # action must be in the enum
    action = adj.get("action")
    if action not in {"none", "file_backlog_item", "edit_table_by_hand"}:
        return f"invalid action {action!r}"

    # action_ref validation
    action_ref = adj.get("action_ref", "")
    if action == "none":
        if action_ref:
            return f"action_ref must be empty when action=none"
    else:
        if not action_ref or not ACTION_REF_RE.match(action_ref):
            return f"invalid action_ref {action_ref!r}"

    # impact block validation (only when action == edit_table_by_hand)
    if action == "edit_table_by_hand":
        impact = adj.get("impact")
        if not impact:
            return "impact block required for action=edit_table_by_hand"
        if not impact.get("regeneration_backlog_ref"):
            return "impact.regeneration_backlog_ref required"
        if not ACTION_REF_RE.match(impact.get("regeneration_backlog_ref", "")):
            return f"invalid regeneration_backlog_ref"

    return None


# ============================================================================
# Writers (§5.6, §7.4) -- all writes go through io.write_artifact
# ============================================================================

def _evidence_to_dict(e: Evidence) -> dict[str, Any]:
    return {
        "recipe_path": e.recipe_path,
        "token_raw": e.token_raw,
        "token_kind": e.token_kind.value,
        "receiver": e.receiver,
        "receiver_type": e.receiver_type.value,
        "member": e.member,
        "member_is_in_surface": e.member_is_in_surface,
        "match_mode": e.match_mode.value,
    }


def _finding_to_dict(f: Finding) -> dict[str, Any]:
    return {
        "finding_id": f.finding_id,
        "adjudicable_digest": f.adjudicable_digest,
        "kind": f.kind.value,
        "subject": f.subject,
        "blocking": f.blocking,
        "verdict": f.verdict,
        "evidence": [_evidence_to_dict(e) for e in f.evidence],
        "reading_table_is_wrong": f.reading_table_is_wrong,
        "reading_api_moved": f.reading_api_moved,
        "verdict_hint": f.verdict_hint,
    }


def _handle_report(args: Any) -> int:
    """--report: write audit_report.json + audit_findings.jsonl to --out (§7.4)."""
    try:
        result = run_audit()
    except recipes.CookbookUnavailable as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return cli.EXIT_INCONCLUSIVE

    findings_sorted = sorted(result.findings, key=lambda f: f.finding_id)
    report = {
        "audit_rules_version": AUDIT_RULES_VERSION,
        "blocking_census": result.blocking_census,
        "n_findings": len(findings_sorted),
        "canonical_tables_fingerprint": canonical_tables_fingerprint(),
    }
    io.write_artifact(Path(args.out), "audit_report.json", json.dumps(report, indent=1, ensure_ascii=False))

    jsonl = "\n".join(json.dumps(_finding_to_dict(f), sort_keys=True) for f in findings_sorted)
    if jsonl:
        jsonl += "\n"
    io.write_artifact(Path(args.out), "audit_findings.jsonl", jsonl)

    return cli.EXIT_OK


def _handle_emit_census(args: Any) -> int:
    """--emit-census: write the observed blocking_census to --out (§5.4.1, §5.6d)."""
    try:
        result = run_audit()
    except recipes.CookbookUnavailable as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return cli.EXIT_INCONCLUSIVE

    row = sources.by_id("chory-lab__plr-cookbook")
    payload = {
        "blocking_census_version": "1",
        "audit_rules_version": AUDIT_RULES_VERSION,
        "derived_under_source_sha": row.pinned_sha,
        "census": result.blocking_census,
    }
    io.write_artifact(Path(args.out), "blocking_census.json", json.dumps(payload, indent=1, ensure_ascii=False))
    return cli.EXIT_OK


def _handle_emit_fingerprint(args: Any) -> int:
    """--emit-fingerprint: write the canonical-tables fingerprint to --out (§5.7).

    Task 8 lands the full committed data/canonical_tables_fingerprint.json (which
    also carries built_artifacts hashes + the regeneration checklist) by hand; this
    emits the fingerprint half only.
    """
    payload = {
        "canonical_tables_fingerprint_version": "2",
        "fingerprint": canonical_tables_fingerprint(),
    }
    io.write_artifact(Path(args.out), "canonical_tables_fingerprint.json", json.dumps(payload, indent=1, ensure_ascii=False))
    return cli.EXIT_OK


# ============================================================================
# CLI Entry Point (§7.1)
# ============================================================================

def _make_parser() -> cli.IngestArgumentParser:
    """Create the argument parser for the audit subcommand."""
    parser = cli.IngestArgumentParser(
        prog="python -m ingest.audit",
        description="Drift audit: compare recipes against canonical tables",
        out_required_for=("emit_census", "emit_fingerprint", "report"),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--gate",
        action="store_true",
        help="Gate evaluation: load audit, census, and adjudications (for CI)",
    )
    group.add_argument(
        "--report",
        action="store_true",
        help="Emit audit_report.json and audit_findings.jsonl to --out",
    )
    group.add_argument(
        "--emit-census",
        action="store_true",
        help="Emit blocking_census.json to --out",
    )
    group.add_argument(
        "--emit-fingerprint",
        action="store_true",
        help="Emit canonical_tables_fingerprint.json to --out",
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (required for --report, --emit-census, --emit-fingerprint)",
    )

    return parser


def _dispatch_handler(args) -> int:
    """Dispatch to the appropriate subcommand."""
    if args.gate:
        return gate()
    elif args.report:
        return _handle_report(args)
    elif args.emit_census:
        return _handle_emit_census(args)
    elif args.emit_fingerprint:
        return _handle_emit_fingerprint(args)
    else:
        return cli.EXIT_USAGE


if __name__ == "__main__":
    parser = _make_parser()
    sys.exit(cli.run(_dispatch_handler, parser))

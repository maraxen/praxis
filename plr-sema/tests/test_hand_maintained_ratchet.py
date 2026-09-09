"""Spec 260901 section 9 / T9 (backlog #4835): the hand-maintained surface
ratchet.

`plr_sema._hand_maintained.REGISTRY` is the data; this module is the
enforcement. Every row's `measure` -- whether it points at a zero-arg
plain-import callable or an AST-reading one -- resolves to a live int via
`plr_sema._hand_maintained.resolve_measure`, and the tests below assert that
live int stays within its row's declared ceiling.

**Two homes for measure callables (spec section 9.1's C7 note).** Rows whose
fact is a top-level importable object with no special sys.path needs AND no
cross-package-boundary import live in `plr_sema._hand_maintained` itself.
The rows below need more, and live here instead:

- HM-2, HM-3, HM-4, HM-6, HM-7, HM-22 measure facts embedded in FUNCTION
  BODIES (inline branches, a tuple literal inside a `return`, boolean
  operands, a dict literal, `.get()` call sites) -- no zero-arg import can
  observe these, so each gets a small bespoke AST-reading counter here.
- HM-15, HM-19, HM-20 are module-level constants in `scripts/`, which has
  no `__init__.py` and is excluded from collection via `norecursedirs`
  (root pyproject.toml). Importing them needs the repo-root `scripts/`
  directory on `sys.path` first -- done once, at module import time, below.
- HM-1, HM-5, HM-11 are plain, trivially-importable module-level facts
  (`praxis.common.type_inspection.PLR_RESOURCE_TYPES`,
  `training.verify.failure_taxonomy.FAILURE_CATEGORIES`,
  `praxis...models.PreconditionType`) that would otherwise belong in
  `_hand_maintained.py` -- except that module lives under `src/plr_sema/`,
  and `tests/test_import_boundary.py` statically AST-scans every file in
  that subtree (whole-tree walk, function bodies included) for any
  `import praxis` / `verify` / `training` (spec section 1.3's AC-1.2/1.3
  corpus-independence boundary). Putting these three measure callables
  here instead is not a deviation from that boundary test's intent -- it
  is what keeps `_hand_maintained.py` itself passing it.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import sys
from pathlib import Path

import pytest

from plr_sema._hand_maintained import REGISTRY, BUDGET_CAP, live_rows, resolve_measure

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = str(REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Generic AST-reading helpers (C7's second `measure` form). Each takes
# (source_path, target_symbol) and returns a live count computed by parsing
# the source -- never by importing it.
# ---------------------------------------------------------------------------


def _function_node(source_path: Path, target_symbol: str) -> ast.FunctionDef:
    tree = ast.parse(source_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == target_symbol:
            return node
    raise LookupError(f"{source_path}: no function {target_symbol!r} found")


def _first_node(root: ast.AST, node_type: type) -> ast.AST:
    for node in ast.walk(root):
        if isinstance(node, node_type):
            return node
    raise LookupError(f"no {node_type.__name__} node found under {root!r}")


def _count_top_level_ifs(source_path: Path, target_symbol: str) -> int:
    """Counts `if` statements that are direct children of the function
    body (not nested inside another `if`'s body) -- e.g. a sequence of
    independent `if ...: return ...` branches, or top-level dispatch
    branches that themselves contain nested ifs."""
    fn = _function_node(source_path, target_symbol)
    return sum(1 for n in fn.body if isinstance(n, ast.If))


def _count_tuple_literal_in_return(source_path: Path, target_symbol: str) -> int:
    """Counts the elements of the first tuple literal found anywhere in
    the function (e.g. the prefixes tuple inside
    `any(x.startswith(p) for p in (...))`)."""
    fn = _function_node(source_path, target_symbol)
    tup = _first_node(fn, ast.Tuple)
    return len(tup.elts)


def _count_or_operands(source_path: Path, target_symbol: str) -> int:
    """Counts the operands of the first boolean `or` expression found in
    the function (e.g. `stem.endswith("test") or stem.endswith("tests")
    or stem.startswith("test_")`)."""
    fn = _function_node(source_path, target_symbol)
    for node in ast.walk(fn):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            return len(node.values)
    raise LookupError(f"{source_path}: no 'or' BoolOp found in {target_symbol!r}")


def _count_dict_literal_values(source_path: Path, target_symbol: str) -> int:
    """Counts the keys of the first dict literal found anywhere in the
    function (e.g. `our_names = {"DispatchError": ..., ...}`)."""
    fn = _function_node(source_path, target_symbol)
    d = _first_node(fn, ast.Dict)
    return len(d.keys)


def _count_data_get_calls(source_path: Path, target_symbol: str) -> int:
    """Counts `data.get("<string literal>")` call sites in the function --
    the validated top-level keys of a hand-typed artifact schema."""
    fn = _function_node(source_path, target_symbol)
    return sum(
        1
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "get"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "data"
        and n.args
        and isinstance(n.args[0], ast.Constant)
        and isinstance(n.args[0].value, str)
    )


# ---------------------------------------------------------------------------
# Bespoke, row-specific zero-arg measure callables. Each bakes in the
# (source_path, target_symbol) pair for exactly one registry row.
# ---------------------------------------------------------------------------

_PLR_CATEGORY_PATH = (
    REPO_ROOT / "praxis" / "backend" / "models" / "enums" / "plr_category.py"
)
_PRECONDITIONS_SURVEY_PATH = REPO_ROOT / "scripts" / "survey_plr_preconditions.py"
_SURVEY_COMMON_PATH = REPO_ROOT / "scripts" / "plr_survey_common.py"
_FAILURE_TAXONOMY_PATH = REPO_ROOT / "training" / "verify" / "failure_taxonomy.py"


def _measure_hm1() -> int:
    """`praxis.*` is forbidden under `src/plr_sema/` (test_import_boundary.py's
    whole-tree AST scan), so this plain-import measure lives here rather
    than in `_hand_maintained.py` even though it needs no sys.path shim or
    AST-reading -- crossing the import boundary is the disqualifier, not
    import complexity."""
    from praxis.common.type_inspection import PLR_RESOURCE_TYPES

    return len(PLR_RESOURCE_TYPES)


def _measure_hm5() -> int:
    """`training.*` is forbidden under `src/plr_sema/` for the same reason
    as HM-1's `praxis.*`. `training` is also a bare repo-root directory
    with no editable install (unlike `praxis`/`coxswain`), so it only
    resolves as a namespace package when the repo root is on `sys.path` --
    guaranteed here since REPO_ROOT is already inserted onto sys.path
    (scripts/ shim, above) for this module, and REPO_ROOT is its parent."""
    repo_root_str = str(REPO_ROOT)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    from training.verify.failure_taxonomy import FAILURE_CATEGORIES

    return len(FAILURE_CATEGORIES)


def _measure_hm11() -> int:
    """`praxis.*` is forbidden under `src/plr_sema/` -- see HM-1."""
    from praxis.backend.utils.plr_static_analysis.models import PreconditionType

    return len(list(PreconditionType))


def _measure_hm2() -> int:
    return _count_top_level_ifs(_PLR_CATEGORY_PATH, "infer_category_from_name")


def _measure_hm3() -> int:
    return _count_tuple_literal_in_return(
        _PRECONDITIONS_SURVEY_PATH, "_is_validation_looking"
    )


def _measure_hm4() -> int:
    return _count_or_operands(_SURVEY_COMMON_PATH, "is_source_file")


def _measure_hm6() -> int:
    return _count_top_level_ifs(_FAILURE_TAXONOMY_PATH, "classify_exception")


def _measure_hm7() -> int:
    return _count_dict_literal_values(_FAILURE_TAXONOMY_PATH, "classify_check_failure")


def _measure_hm22() -> int:
    return _count_data_get_calls(_FAILURE_TAXONOMY_PATH, "_load_taxonomy_artifact")


def _measure_hm15() -> int:
    import plr_survey_common

    return len(plr_survey_common._ROOT_EXCEPTION_NAMES)


def _measure_hm19() -> int:
    import survey_plr_exceptions

    return len(survey_plr_exceptions._NAME_KEYWORD_CATEGORIES)


def _measure_hm20() -> int:
    import survey_plr_exceptions

    return len(survey_plr_exceptions._MODULE_SUBSTRING_CATEGORIES)


def _measure_hm23() -> int:
    """1 if Fork D's `EXPECTED_SUBMODULE_PIN` (test_fork_drift.py, 260901
    T13) is present and well-formed (a 40-hex-char git sha) -- 0 if removed
    or malformed. Imports through the tests-dir sys.path shim
    `resolve_measure` already installs for this module-name form (see
    `plr_sema._hand_maintained.resolve_measure`'s docstring); not a hardcoded
    return, so an accidental deletion of the constant turns this measure
    (and HM-23's FROZEN `measure() == declared` test) red instead of
    passing vacuously."""
    import test_fork_drift

    pin = getattr(test_fork_drift, "EXPECTED_SUBMODULE_PIN", None)
    if pin is None:
        return 0
    well_formed = len(pin) == 40 and all(c in "0123456789abcdef" for c in pin)
    return 1 if well_formed else 0


# ---------------------------------------------------------------------------
# HM-13 content-pin (C18): a sha256 over the concatenated, normalized
# field-values of all 45 MethodContract instances -- catches a hand-patched
# field value, not just a count change.
# ---------------------------------------------------------------------------

#: Recorded 260901 (T9). Recompute with the loop below if HM-13's contracts
#: are intentionally edited or grown, and land the new hash as a reviewable
#: diff in the same commit as the source change.
_PINNED_METHOD_CONTRACTS_SHA256 = (
    "51c24f7f725a7278ff190f281a00b404ef4991f1893f5547308b83d164c5d4cf"
)


def _method_contracts_fingerprint() -> str:
    from coxswain.fft.preconditions.method_contracts import METHOD_CONTRACTS

    parts: list[str] = []
    for key in sorted(METHOD_CONTRACTS):
        contract = METHOD_CONTRACTS[key]
        for f in dataclasses.fields(contract):
            parts.append(f"{key[0]}.{key[1]}.{f.name}={getattr(contract, f.name)!r}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


# ---------------------------------------------------------------------------
# The ratchet tests (spec section 9.3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", REGISTRY, ids=lambda row: row.id)
def test_no_surface_exceeds_its_declared_size(row) -> None:
    """The entire mechanism (section 9.3): growth is not forbidden, it is
    made loud. Every row with a `measure` must satisfy `measure() <=
    declared`; exceeding it requires a visible, reviewable edit to
    `_hand_maintained.py`."""
    if not row.measure:
        pytest.skip(f"{row.id}: no measure callable")
    live = resolve_measure(row.measure)
    assert live <= row.declared, (
        f"{row.id} ({row.what}): live count {live} exceeds declared ceiling "
        f"{row.declared}. Growth is allowed, but only via a reviewable edit "
        f"to this row's `declared` field."
    )


@pytest.mark.parametrize("row", REGISTRY, ids=lambda row: row.id)
def test_frozen_surfaces_are_exact(row) -> None:
    """FROZEN requires `measure() == declared`, not `<=`. Extended to
    RETIRED (round-4 remediation, M5): `measure() == 0` exactly, so a
    retired surface silently reappearing turns this test red instead of
    passing vacuously (`0 <= declared` was the round-4 defect)."""
    if row.status not in ("FROZEN", "RETIRED"):
        pytest.skip(f"{row.id}: status is {row.status}, not FROZEN/RETIRED")
    if row.status == "RETIRED":
        assert row.declared == 0, f"{row.id}: RETIRED rows must declare 0"
    live = resolve_measure(row.measure)
    assert live == row.declared, (
        f"{row.id} ({row.what}): {row.status} requires measure() == "
        f"declared exactly, got live={live} declared={row.declared}."
    )


@pytest.mark.parametrize("row", REGISTRY, ids=lambda row: row.id)
def test_every_row_justifies_itself(row) -> None:
    """A row cannot be added without an argument: `why_not_derived` and
    `breaks_when` are non-empty; `DERIVABLE_NOT_YET` rows additionally
    carry a non-empty `trigger`."""
    assert row.why_not_derived.strip(), f"{row.id}: why_not_derived is empty"
    assert row.breaks_when.strip(), f"{row.id}: breaks_when is empty"
    if row.status == "DERIVABLE_NOT_YET":
        assert row.trigger.strip(), (
            f"{row.id}: status is DERIVABLE_NOT_YET but trigger is empty"
        )


def test_shims_never_grow_after_peak() -> None:
    """HM-16's declared value must be <= the recorded peak, stored in the
    row directly (never inferred from `declared`)."""
    (hm16,) = (row for row in REGISTRY if row.id == "HM-16")
    assert hm16.declared <= hm16.peak, (
        f"HM-16: declared ({hm16.declared}) exceeds recorded peak "
        f"({hm16.peak}) -- shim modules must monotonically decrease after "
        f"their peak."
    )


def test_hand_written_contracts_content_is_pinned() -> None:
    """HM-13-specific content ratchet (C18). The count-only ratchet
    (`measure() <= declared`) cannot see a body edit to an existing
    contract -- e.g. `requires_tips=True` silently flipped to `False`. A
    body edit changes this hash even though it leaves the count of 45
    untouched."""
    live_hash = _method_contracts_fingerprint()
    assert live_hash == _PINNED_METHOD_CONTRACTS_SHA256, (
        "coxswain MethodContract instances changed body content without "
        "updating the pinned hash in "
        "plr-sema/tests/test_hand_maintained_ratchet.py "
        "(_PINNED_METHOD_CONTRACTS_SHA256). If this is an intentional "
        "content edit (not silent field-flipping), recompute the hash via "
        "_method_contracts_fingerprint() and land it as a reviewable diff."
    )


def test_total_declared_within_budget() -> None:
    """Section 9.4: the 24-row budget is a cap on the COUNT of live rows,
    not a sum of `declared` values (RETIRED rows do not count -- section
    9.4's `live_rows` semantics)."""
    assert len(live_rows()) <= BUDGET_CAP, (
        f"live registry rows ({len(live_rows())}) exceed the budget cap "
        f"({BUDGET_CAP}). Discovery may re-baseline the cap once, in a "
        f"single reviewed commit; growth never raises it (section 9.4)."
    )

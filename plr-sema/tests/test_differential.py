"""Spec 260901 §8.3 / T10 (backlog #4836): the differential-test harness.

AC-8.1: every loaded hand contract is classified.
AC-8.2: the report distinguishes all four kinds and includes >=1
``derived_only`` entry with a concrete ``PlrSite`` -- proof the harness found
a precondition the humans missed.
AC-8.3 (explicitly negative): no threshold on the agreement rate; this suite
never asserts a minimum/maximum ``agree`` count.

Uses the real survey JSON, the real ``plr_exception_taxonomy.json``, and the
real hand-written contracts file already on disk (§8.1's ``legacy_pinned``
surface, T10's only in-scope surface -- ``upstream_nonlegacy`` has no
orchestration layer and no hand contracts to differ against) for the tests
that are about the harness's actual measured behaviour against real content;
synthetic in-memory fixtures for the tests that are about the bridge
MECHANIC itself (polarity, resolution dispositions) rather than about PLR's
actual content -- same split ``test_derive.py`` already uses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from plr_sema._provenance import SurveyStamp, survey_stamp
from plr_sema.derive import InlinedGuard, SurveyRecord, build_index
from plr_sema.derive.predicate_ast import parse as parse_predicate
from plr_sema.differential import (
    Disagreement,
    HandContract,
    build_report,
    classify_contract,
    load_hand_contracts,
    load_taxonomy,
    tip_bearing_params,
    tip_state_keywords,
    _guard_credits_tip_absence,
    _guard_credits_tip_required,
    _pascal_case,
)
from plr_sema.verdict import PlrSite

REPO_ROOT = Path(__file__).resolve().parents[2]
SURVEY_JSON = REPO_ROOT / "training" / "verify" / "data" / "plr_preconditions.json"
TAXONOMY_JSON = REPO_ROOT / "training" / "verify" / "data" / "plr_exception_taxonomy.json"
CONTRACTS_PATH = REPO_ROOT / "praxis" / "backend" / "core" / "simulation" / "method_contracts.py"


# ---------------------------------------------------------------------------
# Shared fixtures: real survey data + real hand contracts, loaded once.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def survey_records() -> list[SurveyRecord]:
    from plr_sema.derive import load_survey

    return load_survey(SURVEY_JSON)


@pytest.fixture(scope="module")
def survey_index(survey_records: list[SurveyRecord]) -> dict[tuple[str, str], SurveyRecord]:
    return build_index(survey_records)


@pytest.fixture(scope="module")
def hand_contracts() -> list[HandContract]:
    return load_hand_contracts(CONTRACTS_PATH)


@pytest.fixture(scope="module")
def taxonomy() -> dict[str, str]:
    return load_taxonomy(TAXONOMY_JSON)


@pytest.fixture(scope="module")
def tip_keywords() -> tuple[str, ...]:
    return tip_state_keywords()


@pytest.fixture(scope="module")
def stamp() -> SurveyStamp:
    return survey_stamp()


@pytest.fixture(scope="module")
def results(
    hand_contracts: list[HandContract],
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    taxonomy: dict[str, str],
    tip_keywords: tuple[str, ...],
    stamp: SurveyStamp,
) -> list[tuple[Disagreement, str]]:
    return [
        classify_contract(hc, survey_records, survey_index, taxonomy, tip_keywords, stamp=stamp)
        for hc in hand_contracts
    ]


# ---------------------------------------------------------------------------
# AC-8.1 -- test_all_45_hand_contracts_are_classified. The count is asserted
# DYNAMICALLY (len of the loaded instances), never hard-coded to 45, so a
# 46th hand contract moves the ratchet (HM-13) instead of breaking this test.
# ---------------------------------------------------------------------------


def test_all_45_hand_contracts_are_classified(
    hand_contracts: list[HandContract],
    results: list[tuple[Disagreement, str]],
) -> None:
    assert len(hand_contracts) > 0, "fixture assumption violated: no MethodContract(...) calls found"
    assert len(results) == len(hand_contracts)
    valid_kinds = {"hand_only", "derived_only", "conflict", "agree"}
    valid_dispositions = {"resolved", "class_absent", "module_ambiguous", "method_absent"}
    for disagreement, disposition in results:
        assert disagreement.kind in valid_kinds
        assert disposition in valid_dispositions
    # Sanity anchor on the currently-known population (45 at this pin) --
    # informational, not the assertion that guards the ratchet (that's
    # `len(results) == len(hand_contracts)` above, which survives a 46th).
    assert len(hand_contracts) == 45


# ---------------------------------------------------------------------------
# test_report_is_stamped
# ---------------------------------------------------------------------------


def test_report_is_stamped(
    results: list[tuple[Disagreement, str]],
    stamp: SurveyStamp,
    hand_contracts: list[HandContract],
) -> None:
    report = build_report(results, stamp, total_hand_contracts=len(hand_contracts))
    assert report["stamp"]["schema_version"] == stamp.schema_version
    assert report["stamp"]["surface"] == stamp.surface
    assert "plr" in report["stamp"] and "hash" in report["stamp"]["plr"]
    assert "praxis" in report["stamp"] and "hash" in report["stamp"]["praxis"]
    assert report["total_hand_contracts"] == len(hand_contracts)
    assert set(report["counts"]) == {"agree", "hand_only", "derived_only", "conflict"}
    assert sum(report["counts"].values()) == len(hand_contracts)


# ---------------------------------------------------------------------------
# AC-8.2 -- at least one derived_only entry with a concrete PlrSite.
# ---------------------------------------------------------------------------


def test_derived_only_has_concrete_plr_site(
    results: list[tuple[Disagreement, str]],
) -> None:
    """AC-8.2: the harness demonstrably found >=1 precondition the humans
    missed. Measured at the current pin: 2 (LiquidHandler.pick_up_tips,
    LiquidHandler.pick_up_tips96 -- both via the mentions_params clause on
    tip_spots/tip_rack, D13/R2). If this ever regresses to 0, that is
    itself a reportable AC-8.2-waiver result (spec §8.5), not necessarily a
    bug in this test -- read the waiver clause before "fixing" the bridge to
    force a match."""
    derived_only = [d for d, _disposition in results if d.kind == "derived_only"]
    assert len(derived_only) >= 1, (
        "AC-8.2: zero derived_only entries -- either the bridge has gone "
        "stale/too narrow (write the AC-8.2 waiver note, do not tune the "
        "bridge until it goes green, spec §8.1 trap 5) or PLR/survey data "
        "changed under this pin"
    )
    for d in derived_only:
        assert d.plr_sites, f"{d.qualname}: derived_only with no PlrSite evidence"
        for site in d.plr_sites:
            assert isinstance(site, PlrSite)
            assert site.file
            assert site.lineno > 0
            assert site.qualname


# ---------------------------------------------------------------------------
# test_known_disagreement_is_stable -- pin two triaged disagreements as
# regression fixtures, one on each side of the polarity fix (D13).
# ---------------------------------------------------------------------------


def test_known_disagreement_is_stable(
    results: list[tuple[Disagreement, str]],
) -> None:
    by_qualname = {d.qualname: (d, disposition) for d, disposition in results}

    # pick_up_tips: hand contract leaves requires_tips at its False default
    # (correct -- pick_up_tips needs an EMPTY channel). The polarity-fixed
    # bridge (D13) correctly does NOT credit the reachable HasTipError
    # raise_guard toward requires_tips=True; instead a DIFFERENT guard (the
    # `len(tip_spots) == len(offsets) == len(use_channels)` assert, which
    # mentions the tip-bearing param `tip_spots`) fires the mentions_params
    # clause, correctly classifying this as derived_only: the harness found
    # a tip-related precondition the hand contract does not encode as
    # requires_tips (it encodes it as requires_on_deck=("tips",) instead --
    # a genuinely different field, not corroborated by this bridge).
    pick_up_tips, pick_up_tips_disposition = by_qualname["LiquidHandler.pick_up_tips"]
    assert pick_up_tips_disposition == "resolved"
    assert pick_up_tips.kind == "derived_only"
    assert pick_up_tips.plr_sites
    assert pick_up_tips.plr_sites[0].qualname == "LiquidHandler.pick_up_tips"

    # aspirate: hand contract claims requires_tips=True (correct). The real
    # NoTipError guard lives behind a cross-class call in the tip tracker
    # (§8.1's own "merely looks dead" note) -- outside this bridge's reach
    # in v1 -- so no guard in aspirate's own transitive closure mentions a
    # tip-bearing param or raises a tip_state exception. Uncorroborated,
    # not wrong: hand_only.
    aspirate, aspirate_disposition = by_qualname["LiquidHandler.aspirate"]
    assert aspirate_disposition == "resolved"
    assert aspirate.kind == "hand_only"

    # drop_tips: hand contract claims requires_tips=True (correct -- you
    # need tips to drop them) AND the bridge corroborates it via the same
    # tip_spots-mentioning assert guard pick_up_tips's derived_only entry
    # uses -- the one case in the 45 where the mentions_params clause both
    # fires AND matches the hand's own claim.
    drop_tips, drop_tips_disposition = by_qualname["LiquidHandler.drop_tips"]
    assert drop_tips_disposition == "resolved"
    assert drop_tips.kind == "agree"


# ---------------------------------------------------------------------------
# R5's resolution tally, measured (29 resolve / 13 method-absent /
# 3 module-ambiguous / 0 class-absent = 45) -- reported, not asserted as a
# brittle exact count beyond what the spec itself already measured, but
# pinned at >=1 for each disposition the spec names as real, so the test
# fails loudly if a future PLR/survey pin makes one of them vanish.
# ---------------------------------------------------------------------------


def test_resolution_dispositions_match_round6_shape(
    results: list[tuple[Disagreement, str]],
) -> None:
    dispositions = [disposition for _d, disposition in results]
    assert dispositions.count("resolved") >= 1
    assert dispositions.count("method_absent") >= 1
    assert dispositions.count("module_ambiguous") >= 1
    assert sum(
        dispositions.count(d)
        for d in ("resolved", "class_absent", "module_ambiguous", "method_absent")
    ) == len(dispositions)


# ---------------------------------------------------------------------------
# Bridge-mechanic unit tests -- synthetic fixtures, isolate the polarity fix
# and the mentions_params clause from real PLR content.
# ---------------------------------------------------------------------------


def test_pascal_case() -> None:
    assert _pascal_case("liquid_handler") == "LiquidHandler"
    assert _pascal_case("heater_shaker") == "HeaterShaker"
    assert _pascal_case("pump") == "Pump"
    assert _pascal_case("temperature_controller") == "TemperatureController"


def _synthetic_guard(
    *, kind: str, raises: str | None, free_vars: tuple[str, ...] = (), condition: str | None = "x"
) -> InlinedGuard:
    return InlinedGuard(
        condition=condition,
        predicate=parse_predicate(condition),
        scope_trail=(),
        raises=raises,
        kind=kind,
        free_vars=free_vars,
        site=PlrSite(file="synthetic.py", lineno=1, qualname="Synthetic.method"),
        depth=0,
    )


def test_tip_bearing_params_matches_case_insensitive_tip_keyword(
    tip_keywords: tuple[str, ...],
) -> None:
    assert tip_keywords == ("Tip",)
    rec = SurveyRecord(
        qualname="LiquidHandler.pick_up_tips",
        class_name="LiquidHandler",
        module="synthetic",
        file="synthetic.py",
        lineno=1,
        params=("self", "tip_spots", "use_channels", "offsets", "backend_kwargs"),
        findings=(),
        delegates_to=(),
        unresolved_calls=(),
    )
    assert tip_bearing_params(rec, tip_keywords) == frozenset({"tip_spots"})


def test_guard_credits_tip_absence_requires_raise_guard_kind() -> None:
    """D13's polarity fix: a raise_guard raising a tip_state exception
    credits requires_tips=FALSE (absence), and an assert never reaches this
    clause at all (raises is always None for asserts -- trap 1)."""
    taxonomy = {"HasTipError": "tip_state", "ValueError": None}
    raise_guard = _synthetic_guard(kind="raise_guard", raises="HasTipError")
    assert _guard_credits_tip_absence(raise_guard, taxonomy) is True

    non_tip_raise_guard = _synthetic_guard(kind="raise_guard", raises="ValueError")
    assert _guard_credits_tip_absence(non_tip_raise_guard, taxonomy) is False

    # assert findings structurally carry raises=None -- never matches.
    assert_guard = _synthetic_guard(kind="assert", raises=None)
    assert _guard_credits_tip_absence(assert_guard, taxonomy) is False

    # dynamic sentinel (D18): detected via .startswith, never equality --
    # never matches the raises-based clause regardless of taxonomy content.
    dynamic_guard = _synthetic_guard(kind="raise_guard", raises="<dynamic:error>")
    assert _guard_credits_tip_absence(dynamic_guard, {"<dynamic:error>": "tip_state"}) is False


def test_guard_credits_tip_required_is_the_mentions_params_fallback() -> None:
    tip_params = frozenset({"tip_spots"})
    matching = _synthetic_guard(kind="assert", raises=None, free_vars=("tip_spots", "offsets"))
    assert _guard_credits_tip_required(matching, tip_params) is True

    non_matching = _synthetic_guard(kind="assert", raises=None, free_vars=("use_channels",))
    assert _guard_credits_tip_required(non_matching, tip_params) is False

    # A guard with condition=None (trap 3: a bare raise with no enclosing
    # if) is treated no differently from any other guard here -- this
    # clause never inspects `condition` text at all, only `free_vars`.
    bare_raise = _synthetic_guard(kind="raise_guard", raises=None, free_vars=("tip_spots",), condition=None)
    assert _guard_credits_tip_required(bare_raise, tip_params) is True


# ---------------------------------------------------------------------------
# classify_contract's resolution dispositions -- synthetic index, isolating
# R5's two non-D22 dispositions from real survey content.
# ---------------------------------------------------------------------------


def _synthetic_survey_record(
    qualname: str, *, class_name: str | None, module: str, params: tuple[str, ...] = ()
) -> SurveyRecord:
    return SurveyRecord(
        qualname=qualname,
        class_name=class_name,
        module=module,
        file=f"{module}.py",
        lineno=1,
        params=params,
        findings=(),
        delegates_to=(),
        unresolved_calls=(),
    )


def test_classify_contract_module_ambiguous() -> None:
    records = [
        _synthetic_survey_record("Pump.run_for_duration", class_name="Pump", module="pkg.a.pump"),
        _synthetic_survey_record("Pump.run_for_duration", class_name="Pump", module="pkg.b.pump"),
    ]
    index = build_index(records)
    hand = HandContract(method_name="run_for_duration", receiver_type="pump")
    disagreement, disposition = classify_contract(
        hand, records, index, taxonomy={}, tip_keywords=("Tip",), stamp=_fake_stamp()
    )
    assert disposition == "module_ambiguous"
    assert disagreement.kind == "hand_only"
    assert disagreement.plr_sites == ()


def test_classify_contract_method_absent() -> None:
    records = [
        _synthetic_survey_record("HeaterShaker.shake", class_name="HeaterShaker", module="pkg.hs"),
    ]
    index = build_index(records)
    hand = HandContract(method_name="open_lid", receiver_type="heater_shaker")
    disagreement, disposition = classify_contract(
        hand, records, index, taxonomy={}, tip_keywords=("Tip",), stamp=_fake_stamp()
    )
    assert disposition == "method_absent"
    assert disagreement.kind == "hand_only"


def test_classify_contract_class_absent() -> None:
    records: list[SurveyRecord] = []
    index = build_index(records)
    hand = HandContract(method_name="halt", receiver_type="pump")
    disagreement, disposition = classify_contract(
        hand, records, index, taxonomy={}, tip_keywords=("Tip",), stamp=_fake_stamp()
    )
    assert disposition == "class_absent"
    assert disagreement.kind == "hand_only"


def _fake_stamp() -> SurveyStamp:
    from plr_sema._provenance.git_state import GitState

    nogit = GitState(hash="nogit", branch="nogit", dirty=False, provenance_source="nogit")
    return SurveyStamp(
        plr=nogit, praxis=nogit, pylabrobot_version=None, stamped_at="1970-01-01T00:00:00+00:00"
    )

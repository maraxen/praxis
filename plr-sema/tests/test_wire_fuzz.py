"""Tier 4 property-based fuzz testing of the graph/contract wire format (#4882).

Hypothesis strategies generating §6.2-shaped graph payloads, with property tests
verifying soundness, totality, determinism, and verdict-joining behavior. Observed
exception classes for malformed payloads are intentionally pinned per the brief:
MALFORMED_PAYLOAD_EXCEPTIONS = (KeyError, TypeError, ValueError, AttributeError).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from plr_sema.check import check_graph
from plr_sema.check.graph import parse_graph
from plr_sema.verdict import AnalysisReport, Verdict, Finding, REASON_VOCABULARY, join


PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_JSON = PLR_SEMA_ROOT / "data" / "derived_contracts.json"

# Load the contracts table ONCE per module via a fixture (as per the brief),
# not per example.
_CONTRACTS_PAYLOAD = None


@pytest.fixture(scope="module")
def contracts_json() -> str:
    """Load the contracts table once and cache it."""
    global _CONTRACTS_PAYLOAD
    if _CONTRACTS_PAYLOAD is None:
        _CONTRACTS_PAYLOAD = CONTRACTS_JSON.read_text(encoding="utf-8")
    return _CONTRACTS_PAYLOAD


@pytest.fixture(scope="module")
def real_contract_methods(contracts_json: str) -> list[str]:
    """Extract ~30 real contract keys (receiver_type.method_name pairs) to use
    in strategy generation as realistic method names."""
    payload = json.loads(contracts_json)
    all_methods = list(payload.get("contracts", {}).keys())
    # Sample up to 30, stratified across the table
    step = max(1, len(all_methods) // 30)
    return all_methods[::step][:30]


# ============================================================================
# Hypothesis strategies for generating §6.2-shaped wire payloads
# ============================================================================


def operation_id_strategy() -> st.SearchStrategy[str]:
    """Generate operation IDs (op_N format, matching the fixture's pattern)."""
    return st.just("op_").flatmap(
        lambda prefix: st.integers(min_value=1, max_value=9999).map(lambda n: f"{prefix}{n}")
    )


def operation_node_strategy(
    real_methods: list[str],
) -> st.SearchStrategy[dict]:
    """Generate a single §6.2 OperationNode dict."""
    # Mix real method names from the contract table with random junk
    method_names = st.one_of(
        st.sampled_from(real_methods),  # ~70% real methods
        st.from_regex(r"[a-z_]{5,15}", fullmatch=True),  # ~30% junk names
    )

    def build_operation(method, op_id, receiver_var, receiver_ty, add_params, param_count, add_loop, loop_count):
        base = {
            "id": op_id,
            "method_name": method,
            "receiver_variable": receiver_var,
            "receiver_type": receiver_ty,
        }

        # Optionally add depends_on_params
        if add_params:
            base["depends_on_params"] = [f"param_{i}" for i in range(param_count)]

        # Optionally add foreach_source/foreach_body
        if add_loop:
            base["foreach_source"] = "source_loop"
            base["foreach_body"] = [f"stmt_{i}" for i in range(loop_count)]

        return base

    return st.builds(
        build_operation,
        method=method_names,
        op_id=operation_id_strategy(),
        receiver_var=st.from_regex(r"[a-z]{1,3}", fullmatch=True),
        receiver_ty=st.one_of(
            st.none(),  # Occasionally None to trigger receiver_type_unknown
            st.sampled_from(["LiquidHandler", "Plate", "TipRack", "PlateReader", "Centrifuge"]),
        ),
        add_params=st.booleans(),
        param_count=st.integers(min_value=0, max_value=3),
        add_loop=st.booleans(),
        loop_count=st.integers(min_value=0, max_value=2),
    )


def graph_payload_strategy(
    real_methods: list[str],
) -> st.SearchStrategy[dict]:
    """Generate a complete §6.2 graph payload with random operations."""
    def build_graph(operations, fqn):
        return {
            "protocol_fqn": fqn,
            "operations": operations,
            "resources": {
                f"res_{i}": {"variable_name": f"res_{i}"}
                for i in range(max(1, len(operations) // 2))
            },
        }

    return st.builds(
        build_graph,
        operations=st.lists(
            operation_node_strategy(real_methods),
            min_size=1,
            max_size=12,
        ),
        fqn=st.from_regex(r"[a-z_]+\.[a-z_]+", fullmatch=True),
    )


# ============================================================================
# Property tests (8 total per the brief)
# ============================================================================


@given(data=st.data())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_check_graph_never_raises(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (a): check_graph never raises on any generated payload.

    Tests 150 examples of random §6.2 payloads.
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    # Should not raise, no matter the payload
    report = check_graph(graph_json, contracts_json)
    assert isinstance(report, AnalysisReport)


@given(data=st.data())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_totality_findings_cover_all_operations(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (b): len(report.findings) >= len(operations) (AC-7.2 totality).

    Every operation must receive at least one finding.
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    report = check_graph(graph_json, contracts_json)
    assert len(report.findings) >= len(graph_payload["operations"]), (
        f"totality violated: {len(report.findings)} findings for "
        f"{len(graph_payload['operations'])} operations"
    )


@given(data=st.data())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_verdict_is_member_and_equals_join(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (c): report.verdict is a Verdict member and equals join(report.findings).

    The report-level verdict must be computable from the finding set.
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    report = check_graph(graph_json, contracts_json)

    # Must be a Verdict member
    assert isinstance(report.verdict, Verdict)

    # Must equal the join of the findings
    expected_verdict = join(report.findings)
    assert report.verdict == expected_verdict, (
        f"report.verdict {report.verdict} != join(findings) {expected_verdict}"
    )


@given(data=st.data())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_no_safe_no_will_fail_in_v1(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (d): no finding has verdict == Verdict.SAFE and none is WILL_FAIL.

    v1 constructs only UNKNOWN verdicts (§0 of the plan, §7.4 of spec).
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    report = check_graph(graph_json, contracts_json)

    for finding in report.findings:
        assert finding.verdict != Verdict.SAFE, (
            f"v1 must not emit SAFE: found in operation {finding.operation_id}"
        )
        assert finding.verdict != Verdict.WILL_FAIL, (
            f"v1 must not emit WILL_FAIL: found in operation {finding.operation_id}"
        )


@given(data=st.data())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_finding_ids_and_reasons_valid(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (e): every finding's operation_id is present in operations;
    every reason is in REASON_VOCABULARY.
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    report = check_graph(graph_json, contracts_json)

    real_op_ids = {op["id"] for op in graph_payload["operations"]}

    for finding in report.findings:
        assert finding.operation_id in real_op_ids, (
            f"finding references non-existent operation_id {finding.operation_id}"
        )
        assert finding.reason in REASON_VOCABULARY, (
            f"finding reason '{finding.reason}' not in REASON_VOCABULARY"
        )


@given(data=st.data())
@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_determinism_same_payload_same_report(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (f): two calls on the same payload give equal reports.

    check_graph is deterministic.
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    report1 = check_graph(graph_json, contracts_json)
    report2 = check_graph(graph_json, contracts_json)

    assert report1 == report2, (
        f"non-deterministic: two calls on the same payload yielded different reports"
    )


@given(st.text())
@settings(max_examples=150, deadline=None)
def test_verdict_from_wire_unknown_for_unrecognized(value: str) -> None:
    """Property (g): Verdict.from_wire(s) for arbitrary st.text() returns UNKNOWN
    unless s is exactly a member value.

    The from_wire constructor widens unknown strings to UNKNOWN.
    """
    result = Verdict.from_wire(value)

    # If the value is an exact member, it should return that member
    try:
        expected = Verdict(value)
        assert result == expected
    except ValueError:
        # Not a member: must return UNKNOWN
        assert result == Verdict.UNKNOWN, (
            f"from_wire({value!r}) returned {result}, expected UNKNOWN for unknown string"
        )


@given(data=st.data())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_join_order_independence_and_idempotence(data: st.DataObject, contracts_json: str, real_contract_methods: list[str]) -> None:
    """Property (h): join is order-independent and idempotent.

    Permutations of findings give the same verdict; join(fs + fs) == join(fs).
    """
    graph_payload = data.draw(graph_payload_strategy(real_contract_methods))
    graph_json = json.dumps(graph_payload)

    report = check_graph(graph_json, contracts_json)
    findings = list(report.findings)

    if not findings:
        return  # Empty case is trivially idempotent

    # Order independence: permute the findings using hypothesis's randomization
    original_join = join(findings)
    # Draw a list permutation strategy to get a shuffled order
    permuted = data.draw(st.permutations(findings))
    permuted_join = join(permuted)
    assert original_join == permuted_join, (
        f"join is not order-independent: join(original) = {original_join}, "
        f"join(permuted) = {permuted_join}"
    )

    # Idempotence: join(fs + fs) == join(fs)
    doubled = findings + findings
    doubled_join = join(doubled)
    assert original_join == doubled_join, (
        f"join is not idempotent: join(fs) = {original_join}, "
        f"join(fs + fs) = {doubled_join}"
    )


# ============================================================================
# Malformed payload test (documents current exception behavior)
# ============================================================================

# Exception classes observed when check_graph is called with malformed payloads.
# These are the observed baseline; if any of these change, it indicates a
# regression or intentional change in error handling that should be reviewed.
MALFORMED_PAYLOAD_EXCEPTIONS = (KeyError, TypeError, ValueError, AttributeError)


@pytest.mark.parametrize(
    "malformed_payload",
    [
        # Missing required protocol_fqn
        {"operations": [], "resources": {}},
        # operations is not a list
        {"protocol_fqn": "test.t", "operations": "not_a_list", "resources": {}},
        # operations contains a non-dict item
        {"protocol_fqn": "test.t", "operations": ["not_a_dict"], "resources": {}},
        # operation missing required id field
        {
            "protocol_fqn": "test.t",
            "operations": [{"method_name": "foo"}],
            "resources": {},
        },
    ],
)
def test_malformed_payloads_raise_known_exceptions(
    malformed_payload: dict, contracts_json: str
) -> None:
    """Malformed payloads (missing protocol_fqn, operations not a list, etc.)
    raise one of (KeyError, TypeError, ValueError, AttributeError).

    This test documents the current baseline exception behavior.  If any of these
    assertions fail, it indicates a change in error handling that should be
    reviewed against the spec and the brief.
    """
    graph_json = json.dumps(malformed_payload)

    with pytest.raises(MALFORMED_PAYLOAD_EXCEPTIONS) as exc_info:
        check_graph(graph_json, contracts_json)

    # Document what was raised in the test output
    exc_class = type(exc_info.value).__name__
    assert exc_class in {c.__name__ for c in MALFORMED_PAYLOAD_EXCEPTIONS}, (
        f"Unexpected exception class {exc_class}; expected one of "
        f"{MALFORMED_PAYLOAD_EXCEPTIONS}"
    )

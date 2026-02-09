"""Tests for Chatterbox execution of protocols.

TDD Red Phase: These tests import from the not-yet-implemented
`praxis.backend.core.simulation.chatterbox_runner` module.
They will fail until the GREEN phase implementation is complete.

Test structure:
- TestBackendRegistry: CHATTERBOX_REGISTRY returns correct backends
- TestDeckFactory: DeckFactory creates valid deck setups (carrier + slot)
- TestResolveResource: Generic resource resolution from type hints
- TestSyntheticProtocols: Simple pass/fail protocols validate the runner
- TestRealProtocols: Parametrized over protocol × backend pairs
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
from pathlib import Path
from typing import Any

import pytest

from praxis.backend.core.simulation.chatterbox_runner import (
    CHATTERBOX_REGISTRY,
    BackendResult,
    ChatterboxExecutionResult,
    ChatterboxProtocolRunner,
    DeckFactory,
    DeckLayoutType,
    resolve_resource,
)

# =============================================================================
# Constants
# =============================================================================

PROTOCOLS_DIR = Path(__file__).resolve().parents[2] / "praxis" / "protocol" / "protocols"


# =============================================================================
# Helpers: Protocol Discovery
# =============================================================================


def discover_protocol_files() -> list[Path]:
    """Find all protocol files in the protocols directory."""
    if not PROTOCOLS_DIR.exists():
        return []
    return [
        f
        for f in sorted(PROTOCOLS_DIR.glob("*.py"))
        if not f.name.startswith("__")
    ]


def load_protocol_function(protocol_file: Path) -> tuple[Any, dict[str, str]]:
    """Import a protocol module and return (function, parameter_types).

    Uses the @protocol_function decorated function's signature to extract
    type hints as strings.
    """
    module_name = f"praxis.protocol.protocols.{protocol_file.stem}"
    module = importlib.import_module(module_name)

    # Find the @protocol_function-decorated function
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if hasattr(obj, "_protocol_metadata") or hasattr(obj, "__wrapped__"):
            sig = inspect.signature(obj)
            param_types = {}
            for pname, param in sig.parameters.items():
                if param.annotation is not inspect.Parameter.empty:
                    ann = param.annotation
                    if isinstance(ann, type):
                        param_types[pname] = ann.__name__
                    elif isinstance(ann, str):
                        param_types[pname] = ann
                    else:
                        param_types[pname] = str(ann)
            return obj, param_types

    msg = f"No @protocol_function found in {protocol_file}"
    raise ValueError(msg)


def discover_protocol_backend_pairs() -> list[tuple[str, Path, str]]:
    """Generate (test_id, protocol_file, backend_name) pairs for parametrization.

    Cross-product of each protocol with each compatible Chatterbox backend.
    """
    pairs = []
    runner = ChatterboxProtocolRunner()

    for pf in discover_protocol_files():
        try:
            func, param_types = load_protocol_function(pf)
            machine_types = runner.detect_machine_types(param_types)
            compatible_backends = runner.resolve_backends(machine_types)

            for backend_name in compatible_backends:
                test_id = f"{pf.stem}--{backend_name}"
                pairs.append(pytest.param(pf, backend_name, id=test_id))
        except Exception:
            # If we can't load the protocol, still add it so the test fails visibly
            pairs.append(pytest.param(pf, "UNKNOWN", id=f"{pf.stem}--LOAD_ERROR"))

    return pairs


# =============================================================================
# Test: Backend Registry
# =============================================================================


class TestBackendRegistry:
    """CHATTERBOX_REGISTRY must map machine types to backend entries."""

    def test_registry_has_liquid_handler(self):
        assert "LiquidHandler" in CHATTERBOX_REGISTRY

    def test_registry_has_plate_reader(self):
        assert "PlateReader" in CHATTERBOX_REGISTRY

    def test_liquid_handler_has_multiple_backends(self):
        entries = CHATTERBOX_REGISTRY["LiquidHandler"]
        assert len(entries) >= 2, "Expected at least generic + STAR backends"

    def test_registry_entry_structure(self):
        """Each entry should be (name, backend_class, kwargs)."""
        for machine_type, entries in CHATTERBOX_REGISTRY.items():
            for entry in entries:
                assert len(entry) == 3, f"Entry {entry} should be (name, class, kwargs)"
                name, cls, kwargs = entry
                assert isinstance(name, str)
                assert callable(cls)
                assert isinstance(kwargs, dict)


# =============================================================================
# Test: Generic Resource Resolution
# =============================================================================


class TestResolveResource:
    """resolve_resource() must instantiate PLR objects from type hints."""

    def test_resolves_plate(self):
        resource = resolve_resource("my_plate", "Plate")
        assert resource is not None
        assert resource.name == "my_plate"

    def test_resolves_tiprack(self):
        resource = resolve_resource("tips", "TipRack")
        assert resource is not None
        assert resource.name == "tips"

    def test_resolves_trough(self):
        resource = resolve_resource("diluent", "Trough")
        assert resource is not None
        assert resource.name == "diluent"

    def test_returns_none_for_scalar(self):
        resource = resolve_resource("count", "int")
        assert resource is None

    def test_returns_none_for_unknown(self):
        resource = resolve_resource("mystery", "SomeUnknownType")
        assert resource is None


# =============================================================================
# Test: Deck Factory
# =============================================================================


class TestDeckFactory:
    """DeckFactory must create valid deck + resource setups."""

    def test_creates_carrier_based_setup(self):
        factory = DeckFactory()
        setup = factory.create_setup(
            "STARChatterboxBackend",
            {"plate": "Plate", "tip_rack": "TipRack"},
        )
        assert setup["deck"] is not None
        assert setup["machine"] is not None
        assert "plate" in setup

    def test_creates_generic_lh_setup(self):
        factory = DeckFactory()
        setup = factory.create_setup(
            "LiquidHandlerChatterboxBackend",
            {"plate": "Plate", "tip_rack": "TipRack"},
        )
        assert setup["deck"] is not None
        assert setup["machine"] is not None

    def test_creates_plate_reader_setup(self):
        factory = DeckFactory()
        setup = factory.create_setup(
            "PlateReaderChatterboxBackend",
            {},
        )
        assert "machine" in setup
        assert "plate" in setup

    def test_carrier_setup_handles_trough(self):
        factory = DeckFactory()
        setup = factory.create_setup(
            "STARChatterboxBackend",
            {"plate": "Plate", "tip_rack": "TipRack", "diluent_trough": "Trough"},
        )
        assert "diluent_trough" in setup


# =============================================================================
# Test: Result Model
# =============================================================================


class TestResultModels:
    """BackendResult and ChatterboxExecutionResult dataclasses."""

    def test_backend_result_pass(self):
        r = BackendResult(backend_name="Generic", passed=True)
        assert r.passed
        assert r.error is None

    def test_backend_result_fail(self):
        r = BackendResult(
            backend_name="STAR",
            passed=False,
            error="AttributeError: 'NoneType' has no attribute 'x'",
        )
        assert not r.passed
        assert "AttributeError" in r.error

    def test_execution_result_all_passed(self):
        results = {
            "Generic": BackendResult(backend_name="Generic", passed=True),
            "STAR": BackendResult(backend_name="STAR", passed=True),
        }
        er = ChatterboxExecutionResult(
            protocol_name="test", results_by_backend=results
        )
        assert er.all_passed

    def test_execution_result_partial_failure(self):
        results = {
            "Generic": BackendResult(backend_name="Generic", passed=True),
            "STAR": BackendResult(backend_name="STAR", passed=False, error="boom"),
        }
        er = ChatterboxExecutionResult(
            protocol_name="test", results_by_backend=results
        )
        assert not er.all_passed


# =============================================================================
# Test: Synthetic Protocols
# =============================================================================


async def _synthetic_passing_protocol(
    state: dict[str, Any],
    liquid_handler: Any,
    plate: Any,
    tip_rack: Any,
) -> dict[str, Any]:
    """A minimal protocol that should pass with any LH Chatterbox backend."""
    await liquid_handler.pick_up_tips(tip_rack["A1"])
    await liquid_handler.aspirate(plate["A1"], vols=[10])
    await liquid_handler.dispense(plate["B1"], vols=[10])
    await liquid_handler.return_tips()
    state["status"] = "completed"
    return state


async def _synthetic_failing_protocol(
    state: dict[str, Any],
    liquid_handler: Any,
    plate: Any,
    tip_rack: Any,
) -> dict[str, Any]:
    """A protocol that will always raise."""
    msg = "Intentional test failure"
    raise RuntimeError(msg)


class TestSyntheticProtocols:
    """Run synthetic pass/fail protocols through ChatterboxProtocolRunner."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_passing_protocol_completes(self):
        runner = ChatterboxProtocolRunner()
        result = await runner.run_protocol_function(
            protocol_func=_synthetic_passing_protocol,
            parameter_types={
                "state": "dict[str, Any]",
                "liquid_handler": "LiquidHandler",
                "plate": "Plate",
                "tip_rack": "TipRack",
            },
        )
        assert result.all_passed, (
            f"Synthetic passing protocol should succeed on all backends: "
            f"{[(k, v.error) for k, v in result.results_by_backend.items() if not v.passed]}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_failing_protocol_captured(self):
        runner = ChatterboxProtocolRunner()
        result = await runner.run_protocol_function(
            protocol_func=_synthetic_failing_protocol,
            parameter_types={
                "state": "dict[str, Any]",
                "liquid_handler": "LiquidHandler",
                "plate": "Plate",
                "tip_rack": "TipRack",
            },
        )
        assert not result.all_passed
        for br in result.results_by_backend.values():
            assert not br.passed
            assert "Intentional test failure" in br.error


# =============================================================================
# Test: Real Protocol × Backend Matrix
# =============================================================================


class TestRealProtocols:
    """Parametrized: each protocol must complete with each compatible backend."""

    @pytest.mark.asyncio(loop_scope="function")
    @pytest.mark.parametrize("protocol_file,backend_name", discover_protocol_backend_pairs())
    async def test_protocol_with_chatterbox(self, protocol_file: Path, backend_name: str):
        """Protocol must complete without exception on this backend."""
        func, param_types = load_protocol_function(protocol_file)
        runner = ChatterboxProtocolRunner()
        result = await runner.run_single(func, param_types, backend_name)
        assert result.passed, (
            f"{protocol_file.stem} failed on {backend_name}: {result.error}\n"
            f"Traceback:\n{result.traceback or 'N/A'}"
        )


if __name__ == "__main__":
    # Manual runner to bypass conftest.py
    import sys

    async def main():
        print("Running tests manually to bypass conftest.py...")
        runner = TestSyntheticProtocols()
        print("\n[Case 1] Synthetic Passing Protocol")
        await runner.test_passing_protocol_completes()
        print("OK")
        
        print("\n[Case 2] Synthetic Failing Protocol")
        await runner.test_failing_protocol_captured()
        print("OK (Captured)")
        
        print("\n[Case 3] Real Protocols Discovery")
        pairs = discover_protocol_backend_pairs()
        print(f"Discovered {len(pairs)} protocol-backend pairs.")
        
        passed = 0
        failed = []
        for p in pairs:
            pf, backend = p.values
            if backend == "UNKNOWN": continue
            print(f"Running {pf.stem} on {backend}...", end=" ", flush=True)
            run = TestRealProtocols()
            try:
                await run.test_protocol_with_chatterbox(pf, backend)
                print("PASS")
                passed += 1
            except AssertionError as e:
                print("FAIL")
                failed.append((pf.stem, backend, str(e)))
        
        print(f"\nFinal Result: {passed}/{passed+len(failed)} passed")
        if failed:
            print("\nFailures:")
            for name, be, err in failed:
                print(f"- {name} on {be}: {err}")
            sys.exit(1)

    asyncio.run(main())

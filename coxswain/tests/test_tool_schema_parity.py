"""AC-2.0.x subset assertion: TOOL_SCHEMA ⊆ vendored PLR API, pinned to the
submodule HEAD.

The pin is deliberate friction: if ``external/pylabrobot`` moves, these tests
FAIL until a human re-pins ``PINNED_PLR_SHA`` and re-reads the include/exclude
decision record in ``coxswain/src/coxswain/plr/param_namespace.py``. Silent
submodule bumps must not silently change the copilot generation surface
(D9/§8 "silent eval rotation" counter, applied to the schema itself).
"""

import subprocess
import sys
from pathlib import Path

import pytest

from coxswain.plr.param_namespace import PARAM_NAMESPACE, params_of, required_params
from coxswain.plr.tool_schema import TOOL_SCHEMA, PHASE2_TOOL_NAMES

REPO_ROOT = Path(__file__).resolve().parents[2]
PLR_DIR = REPO_ROOT / "external" / "pylabrobot"

#: external/pylabrobot HEAD at P2.0 reconciliation time (PLR 0.2.2).
PINNED_PLR_SHA = "dd79c4c89bc008629a1c598ea614be5e6067d1f9"

#: The four phantom verbs (recon §1.4: not present on vendored LiquidHandler).
PHANTOM_VERBS = frozenset({"mix", "blow_out", "touch_tip", "dispense_to_waste"})
#: Defender R5: heater-shaker verbs excluded until a praxis backend exists.
HEATER_SHAKER_VERBS = frozenset({"set_temperature", "shake", "stop_shaking"})


def _vendored_head_sha() -> str:
    proc = subprocess.run(
        ["git", "-C", str(PLR_DIR), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"git rev-parse failed:\n{proc.stderr}"
    return proc.stdout.strip()


@pytest.fixture(scope="module")
def vendored():
    """Import the vendored pylabrobot from external/, asserting the vendored
    copy actually wins over any site-packages install."""
    sha = _vendored_head_sha()
    assert sha == PINNED_PLR_SHA, (
        f"external/pylabrobot HEAD {sha[:9]} != pinned {PINNED_PLR_SHA[:9]}; "
        "re-verify signatures + include/exclude decisions, then re-pin."
    )
    sys.path.insert(0, str(PLR_DIR))
    try:
        import pylabrobot

        assert Path(pylabrobot.__file__).resolve().is_relative_to(PLR_DIR.resolve()), (
            f"imported {pylabrobot.__file__}, not the vendored copy"
        )
        from pylabrobot.heating_shaking.heater_shaker import HeaterShaker
        from pylabrobot.liquid_handling.liquid_handler import LiquidHandler
        from pylabrobot.plate_reading.plate_reader import PlateReader

        yield {"liquid_handler": LiquidHandler, "plate_reader": PlateReader, "heater_shaker": HeaterShaker}
    finally:
        sys.path.remove(str(PLR_DIR))


# --- Pin integrity -------------------------------------------------------------


def test_submodule_head_matches_pin() -> None:
    assert _vendored_head_sha() == PINNED_PLR_SHA


def test_tool_schema_entry_count_is_20() -> None:
    """Spec §4 rev2 says '21 entries'; the actual hand-authored schema has
    exactly 20 (verified 260825 at dd79c4c89). This test documents the
    correction so the number is consciously maintained."""
    assert len(TOOL_SCHEMA) == 20


# --- Included surface maps to real vendored methods ----------------------------


def test_every_phase2_liquid_handler_tool_exists_on_vendored_api(vendored) -> None:
    lh = vendored["liquid_handler"]
    tools = [
        name
        for name in PHASE2_TOOL_NAMES
        if TOOL_SCHEMA[name].receiver_type == "liquid_handler"
    ]
    assert tools, "sanity: expected liquid_handler tools in the phase-2 surface"
    for name in sorted(tools):
        assert hasattr(lh, name), f"{name} missing from vendored LiquidHandler"


def test_every_phase2_plate_reader_tool_exists_on_vendored_api(vendored) -> None:
    pr = vendored["plate_reader"]
    tools = [
        name
        for name in PHASE2_TOOL_NAMES
        if TOOL_SCHEMA[name].receiver_type == "plate_reader"
    ]
    assert tools, "sanity: expected plate_reader tools in the phase-2 surface"
    for name in sorted(tools):
        assert hasattr(pr, name), f"{name} missing from vendored PlateReader"


# --- Exclusions are recorded and enforced --------------------------------------


def test_phantom_verbs_marked_experimental_and_excluded() -> None:
    for name in sorted(PHANTOM_VERBS):
        spec = TOOL_SCHEMA[name]
        assert spec.experimental, f"{name} must carry experimental=true"
        assert not spec.phase2_included, f"{name} must be excluded from phase-2 generation"
        assert name not in PHASE2_TOOL_NAMES


def test_phantom_verbs_absent_from_vendored_liquid_handler(vendored) -> None:
    """Guards the exclusion decision: if upstream ADDS these methods later,
    this fails and forces conscious re-inclusion review."""
    lh = vendored["liquid_handler"]
    for name in sorted(PHANTOM_VERBS):
        assert not hasattr(lh, name), (
            f"{name} now exists on vendored LiquidHandler; re-review the "
            "phantom exclusion decision in param_namespace.py"
        )


def test_heater_shaker_methods_exist_but_excluded_until_backend(vendored) -> None:
    """Defender R5: exclusion is about praxis backend wiring, not method
    existence -- the vendored HeaterShaker HAS these methods."""
    hs = vendored["heater_shaker"]
    for name in sorted(HEATER_SHAKER_VERBS):
        assert hasattr(hs, name), f"{name} unexpectedly missing from HeaterShaker"
        spec = TOOL_SCHEMA[name]
        assert spec.experimental and not spec.phase2_included
        assert name not in PHASE2_TOOL_NAMES


# --- Required-param derivation matches inspect.signature (AC-2.0.x) ------------


def test_required_flags_match_inspect_signature(vendored) -> None:
    import inspect

    receiver_classes = {
        "liquid_handler": vendored["liquid_handler"],
        "plate_reader": vendored["plate_reader"],
    }
    checked = 0
    for name in sorted(PHASE2_TOOL_NAMES):
        spec = TOOL_SCHEMA[name]
        cls = receiver_classes[spec.receiver_type]
        sig = inspect.signature(getattr(cls, name))
        table = params_of(name)
        assert table, f"{name} has no namespace entry"
        for pspec in table:
            if pspec.plr_arg is None:
                continue  # phrase-only metadata; nothing to check against PLR
            assert pspec.plr_arg in sig.parameters, (
                f"{name}.{pspec.name}: plr_arg {pspec.plr_arg!r} not in signature"
            )
            param = sig.parameters[pspec.plr_arg]
            signature_required = param.default is inspect.Parameter.empty
            assert pspec.required == signature_required, (
                f"{name}.{pspec.name}: table required={pspec.required} but "
                f"signature says required={signature_required}"
            )
            # Every REQUIRED vendored kwarg must appear in our table -- the
            # dispatcher cannot invent required arguments.
            covered_required = {
                p.plr_arg for p in table if p.plr_arg is not None and p.required
            }
            for kwarg, param in sig.parameters.items():
                if kwarg == "self":
                    continue
                if param.default is inspect.Parameter.empty and param.kind in (
                    param.POSITIONAL_OR_KEYWORD,
                    param.KEYWORD_ONLY,
                ):
                    assert kwarg in covered_required, (
                        f"{name}: required signature kwarg {kwarg!r} missing from namespace table"
                    )
            checked += 1
    assert checked > 0


# --- Loader behavior -----------------------------------------------------------


def test_params_of_unknown_tool_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        params_of("no_such_verb")


def test_required_params_returns_table_order() -> None:
    reqs = required_params("transfer")
    assert reqs == ("source", "destination")


def test_namespace_keys_equal_phase2_surface() -> None:
    assert set(PARAM_NAMESPACE.keys()) == set(PHASE2_TOOL_NAMES)

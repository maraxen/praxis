"""AC-8 (N1 auditability): static risk tiers are independent of parameters,
and the tier path structurally cannot see advisory warnings (FR-2/N1-B).
"""

import ast
import random
import sys
from pathlib import Path

import pytest

from coxswain.schema.types import RiskTier
from coxswain.plr import tool_schema

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "coxswain" / "plr" / "tool_schema.py"
)


# --- exactly one valid tier per function --------------------------------------


def test_every_entry_carries_exactly_one_valid_tier() -> None:
    assert len(tool_schema.TOOL_SCHEMA) > 0
    for name, spec in tool_schema.TOOL_SCHEMA.items():
        assert isinstance(spec.risk_tier, RiskTier), f"{name}: {spec.risk_tier!r}"


def test_names_are_unique_and_verbs_present() -> None:
    # dict keys are unique by construction; assert the verb surface exists
    for name, spec in tool_schema.TOOL_SCHEMA.items():
        assert spec.verb == spec.verb.lower(), name
        assert spec.name == name


def test_unknown_name_raises() -> None:
    with pytest.raises(KeyError):
        tool_schema.tier_of("definitely_not_a_function")


# --- AC-8: tier provably independent of parameters ----------------------------


def _random_params(rng: random.Random) -> dict:
    wells = ["A1", "B3", "C5", "D7"]
    return {
        "vol": rng.choice([0.5, 50, 200, 949, 5000]),
        "source": rng.choice(wells),
        "target": rng.choice(wells),
        "count": rng.randint(1, 96),
        "tips": rng.choice(wells),
        "plate": rng.choice(wells),
        "resource": rng.choice(wells),
        "waste": rng.choice([True, False]),
    }


def test_tier_is_independent_of_randomized_parameters() -> None:
    rng = random.Random(26082400)
    names = sorted(tool_schema.TOOL_SCHEMA)
    checked = 0
    for name in names:
        expected = tool_schema.tier_of(name)
        for _ in range(25):
            call = {"name": name, **_random_params(rng)}
            assert tool_schema.tier_of(call) == expected, f"{name} drifted with params"
            checked += 1
    assert checked >= len(names) * 25


def test_tier_lookup_accepts_name_or_call_mapping() -> None:
    assert tool_schema.tier_of("transfer") == tool_schema.tier_of(
        {"name": "transfer", "vol": 123}
    )


# --- N1-B: warnings are advisory and can never reach the friction decision ----


def test_warnings_fire_but_tier_stays_put() -> None:
    from coxswain.plr.warnings import LARGE_VOLUME_THRESHOLD_UL, compute_warnings

    quiet = {"name": "transfer", "vol": 50}
    loud = {"name": "transfer", "vol": LARGE_VOLUME_THRESHOLD_UL * 10}
    assert any(b.kind == "large_volume" for b in compute_warnings("transfer", loud))
    assert not any(b.kind == "large_volume" for b in compute_warnings("transfer", quiet))
    # The friction decision is unchanged by the warning:
    assert tool_schema.tier_of(loud) == tool_schema.tier_of(quiet)


def test_warning_message_capped_at_nfr7_badge_cap() -> None:
    from coxswain.records import STRING_CAPS
    from coxswain.plr.warnings import MULTI_TARGET_MIN, compute_warnings

    params = {"targets": [f"plate_{i}" * 20 for i in range(MULTI_TARGET_MIN + 3)]}
    badges = compute_warnings("transfer", params)
    assert any(b.kind == "multi_plate" for b in badges)
    cap = STRING_CAPS["warning_badge_text"]
    assert all(len(b.message) <= cap for b in badges)


def test_compute_warnings_is_total_over_garbage_params() -> None:
    """A badge computation that could raise would be a safety bug."""
    from coxswain.plr.warnings import compute_warnings

    garbage = [
        {},
        {"vol": "not-a-number"},
        {"vol": None},
        {"targets": "single-string"},
        {"vol": float("inf")},
    ]
    for params in garbage:
        compute_warnings("transfer", params)  # must not raise


# --- NFR-1: CPython-importable; N1-B: warnings unreachable from tier path -----


def test_importing_tier_path_does_not_load_warnings_module() -> None:
    proc_code = (
        "import sys, coxswain.plr.tool_schema;"
        "assert 'coxswain.plr.warnings' not in sys.modules;"
        "assert not hasattr(coxswain.plr.tool_schema, 'warnings')"
    )
    import subprocess

    proc = subprocess.run([sys.executable, "-c", proc_code], capture_output=True, text=True)
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}"


@pytest.mark.parametrize(
    "banned",
    [
        "from coxswain.plr import warnings",
        "from coxswain.plr.warnings import",
        "from coxswain.plr import tool_schema, warnings",
        "import coxswain.plr.warnings",
        "from .warnings import",
        "from . import warnings",
    ],
)
def test_tool_schema_never_imports_warnings(banned: str) -> None:
    source = SCHEMA_PATH.read_text(encoding="utf-8")
    assert banned not in source


def test_tool_schema_has_no_warnings_attribute_binding() -> None:
    """AST-level: the tier path binds no name 'warnings' from any import."""
    tree = ast.parse(SCHEMA_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            bound = {a.asname or a.name.split(".")[0] for a in node.names}
            assert "warnings" not in bound
        elif isinstance(node, ast.Import):
            bound = {a.asname or a.name.split(".")[0] for a in node.names}
            assert "warnings" not in bound

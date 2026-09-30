"""Browser legacy-FQN fallback and the ``emit_well_state`` tip-mask fix in ``web_bridge.py``.

PLR 1.0 moved the machine-agnostic stack under ``pylabrobot.legacy``. A browser that opened
praxis before the bump keeps the 0.2.2 catalog in its OPFS database (it reloads only on a
``PRAGMA user_version`` bump), so it still hands ``create_configured_backend`` FQNs such as
``pylabrobot.plate_reading.chatterbox.PlateReaderChatterboxBackend`` -- a module that does not
exist at 1.0 and resolves only through its ``pylabrobot.legacy`` twin. Before the fix the browser
bridge used plain ``importlib`` and returned ``None`` for those.

The resolver mirrors the server's ``get_class_from_fqn`` (``praxis/backend/core/workcell_runtime/
utils.py``): the ``pylabrobot.legacy`` twin first for a pre-1.0 machine package, the FQN as given
otherwise. Four things are pinned here:

1. an old FQN resolves to the same class as its legacy FQN, and the rewrite is counted;
2. a current legacy FQN (or a still-top-level one) resolves directly, without the fallback;
3. a bogus FQN still fails (negative control: the resolver is not a catch-all);
4. the counter holds exactly one entry per distinct rewritten FQN, and the browser's package list
   cannot drift from the server's (the drift check has its own negative control).

The second half pins the ``emit_well_state`` fix: in PLR 1.0 ``TipSpot.has_tip`` is a METHOD, so
the old ``resource.get_item(i).has_tip`` test was a bound method, always truthy, and every tip
spot was reported as holding a tip.

``web_bridge`` needs the Pyodide ``js`` module at import time, so it is loaded here from its file
under a fresh module name per test with a stub ``js`` registered in ``sys.modules``. The overlay
python directory is on ``sys.path`` only while the module executes (its ``praxis/`` package
shadows the real one, and its sibling ``experimental`` package is imported at load time).
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import types
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OVERLAY_PYTHON_DIR = _REPO_ROOT / "web-repl" / "overlay" / "assets" / "python"
_WEB_BRIDGE_PATH = _OVERLAY_PYTHON_DIR / "web_bridge.py"
_SERVER_UTILS_PATH = _REPO_ROOT / "praxis" / "backend" / "core" / "workcell_runtime" / "utils.py"

# 0.2.2-era backend FQNs. The first exists at 1.0 only under pylabrobot.legacy (no shim
# submodule); the second is reachable through both the shim and the legacy twin.
_STALE_ONLY_TWIN = "pylabrobot.plate_reading.chatterbox.PlateReaderChatterboxBackend"
_STALE_ONLY_TWIN_LEGACY = "pylabrobot.legacy.plate_reading.chatterbox.PlateReaderChatterboxBackend"
_STALE_LH = "pylabrobot.liquid_handling.backends.chatterbox.LiquidHandlerChatterboxBackend"
_STALE_LH_LEGACY = "pylabrobot.legacy.liquid_handling.backends.chatterbox.LiquidHandlerChatterboxBackend"


@pytest.fixture
def wb(monkeypatch: pytest.MonkeyPatch):
    """A fresh ``web_bridge`` module (empty fallback counter) with a stub ``js``."""
    js_stub = types.ModuleType("js")
    js_stub.postMessage = lambda _message: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "js", js_stub)
    name = "web_bridge_under_test"
    spec = importlib.util.spec_from_file_location(name, _WEB_BRIDGE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    # web_bridge does ``from experimental.machines import ...`` at import time, and that
    # package is a sibling under overlay/assets/python. Expose the directory only while the
    # module executes (it also holds a ``praxis/`` that shadows the real package), and forget
    # the ``experimental`` modules afterwards.
    already_imported = {m for m in sys.modules if m == "experimental" or m.startswith("experimental.")}
    sys.path.insert(0, str(_OVERLAY_PYTHON_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(_OVERLAY_PYTHON_DIR))
        for m in [m for m in sys.modules if m == "experimental" or m.startswith("experimental.")]:
            if m not in already_imported:
                del sys.modules[m]
    return module


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def test_stale_fqn_with_no_shim_resolves_to_the_legacy_class(wb) -> None:
    """(a) A 0.2.2 FQN that only the legacy twin can satisfy resolves to the legacy FQN's class."""
    cls = wb._resolve_plr_class(_STALE_ONLY_TWIN)
    legacy_cls = wb._resolve_plr_class(_STALE_ONLY_TWIN_LEGACY)
    assert cls is legacy_cls
    assert cls.__module__.startswith("pylabrobot.legacy.")
    assert wb._FQN_FALLBACK_COUNTS == {_STALE_ONLY_TWIN: 1}


def test_stale_fqn_is_tried_at_its_legacy_home_first_like_the_server(wb) -> None:
    """(a) A stale FQN the shim ALSO serves still resolves to the legacy home (server order)."""
    cls = wb._resolve_plr_class(_STALE_LH)
    assert cls is wb._resolve_plr_class(_STALE_LH_LEGACY)
    assert cls.__module__.startswith("pylabrobot.legacy.")
    assert wb._FQN_FALLBACK_COUNTS == {_STALE_LH: 1}


def test_legacy_and_top_level_fqns_resolve_directly_without_the_fallback(wb) -> None:
    """(b) A current legacy FQN and a still-top-level resources FQN never touch the fallback."""
    from pylabrobot.resources import Plate

    legacy_cls = wb._resolve_plr_class(_STALE_ONLY_TWIN_LEGACY)
    assert legacy_cls.__name__ == "PlateReaderChatterboxBackend"
    assert wb._resolve_plr_class("pylabrobot.resources.plate.Plate") is Plate
    assert wb._resolve_plr_class("collections.OrderedDict").__name__ == "OrderedDict"
    assert wb._FQN_FALLBACK_COUNTS == {}


def test_bogus_fqns_still_fail_and_are_not_counted(wb) -> None:
    """(c) Negative control: the fallback does not turn every FQN into a success."""
    for bogus in (
        "pylabrobot.liquid_handling.NoSuchClassAnywhere",  # shimmed package, class exists nowhere
        "pylabrobot.no_such_package.Thing",  # not a legacy package
        "nonexistent.module.ClassName",
    ):
        with pytest.raises((ImportError, AttributeError)):
            wb._resolve_plr_class(bogus)
    assert wb._FQN_FALLBACK_COUNTS == {}


def test_legacy_twin_fqn_is_a_pure_rewrite(wb) -> None:
    """The rewrite is prefix-only and applies to the machine packages, not to resources."""
    assert wb._legacy_twin_fqn("pylabrobot.liquid_handling.LiquidHandler") == (
        "pylabrobot.legacy.liquid_handling.LiquidHandler"
    )
    assert wb._legacy_twin_fqn("pylabrobot.legacy.liquid_handling.LiquidHandler") is None
    assert wb._legacy_twin_fqn("pylabrobot.resources.plate.Plate") is None
    assert wb._legacy_twin_fqn("LiquidHandler") is None


def test_counter_and_log_hold_one_entry_per_distinct_fallback_fqn(
    wb, capsys: pytest.CaptureFixture[str]
) -> None:
    """(d) Repeated use of one stale FQN counts up but logs and registers once."""
    for _ in range(3):
        wb._resolve_plr_class(_STALE_ONLY_TWIN)
    wb._resolve_plr_class(_STALE_LH)
    wb._resolve_plr_class(_STALE_ONLY_TWIN_LEGACY)  # direct: not an entry

    assert wb._FQN_FALLBACK_COUNTS == {_STALE_ONLY_TWIN: 3, _STALE_LH: 1}
    log_lines = [line for line in capsys.readouterr().out.splitlines() if "Stale PLR FQN" in line]
    assert len(log_lines) == 2
    assert any(_STALE_ONLY_TWIN in line and _STALE_ONLY_TWIN_LEGACY in line for line in log_lines)
    assert any(_STALE_LH in line for line in log_lines)


# ---------------------------------------------------------------------------
# create_configured_backend / _import_class use the resolver
# ---------------------------------------------------------------------------


def test_create_configured_backend_builds_a_backend_from_a_stale_fqn(wb) -> None:
    """(a) End to end: a 0.2.2 backend FQN yields the legacy backend instead of None."""
    backend = wb.create_configured_backend(
        {"backend_fqn": _STALE_LH, "machine_type": "LiquidHandler", "is_simulated": True}
    )
    assert backend is not None
    assert type(backend) is wb._resolve_plr_class(_STALE_LH_LEGACY)
    assert wb._FQN_FALLBACK_COUNTS == {_STALE_LH: 1}  # the build; the legacy lookup above is direct


def test_create_configured_backend_direct_legacy_fqn_skips_the_fallback(wb) -> None:
    """(b) A current legacy backend FQN is built without any fallback entry."""
    backend = wb.create_configured_backend(
        {"backend_fqn": _STALE_LH_LEGACY, "machine_type": "LiquidHandler", "is_simulated": True}
    )
    assert backend is not None
    assert wb._FQN_FALLBACK_COUNTS == {}


def test_create_configured_backend_bogus_fqn_returns_none(wb) -> None:
    """(c) A bogus backend FQN still yields None (the documented failure contract)."""
    assert wb.create_configured_backend({"backend_fqn": "pylabrobot.liquid_handling.NoSuchBackend"}) is None
    assert wb.create_configured_backend({"backend_fqn": "nonexistent.module.Backend"}) is None
    assert wb.create_configured_backend({}) is None
    assert wb._FQN_FALLBACK_COUNTS == {}


def test_import_class_resolves_stale_fqn_and_keeps_its_name_fallback(wb) -> None:
    """``_import_class`` goes through the resolver and keeps its top-level resources name fallback."""
    from pylabrobot.resources import Plate

    assert wb._import_class(_STALE_ONLY_TWIN) is wb._resolve_plr_class(_STALE_ONLY_TWIN_LEGACY)
    # The pre-existing fallback: a module path that does not exist, a name PLR re-exports.
    assert wb._import_class("pylabrobot.resources.no_such_module.Plate") is Plate


# ---------------------------------------------------------------------------
# Drift guard against the server-side list
# ---------------------------------------------------------------------------


def _extract_legacy_packages(source: str) -> frozenset[str]:
    """Read the ``_PLR_LEGACY_PACKAGES = frozenset({...})`` literal out of a module's source."""
    for node in ast.walk(ast.parse(source)):
        target = None
        value = None
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        if isinstance(target, ast.Name) and target.id == "_PLR_LEGACY_PACKAGES":
            assert isinstance(value, ast.Call)
            return frozenset(ast.literal_eval(value.args[0]))
    msg = "_PLR_LEGACY_PACKAGES not found"
    raise AssertionError(msg)


def test_browser_package_list_matches_the_server(wb) -> None:
    """The browser mirror of ``_PLR_LEGACY_PACKAGES`` equals the server's."""
    server = _extract_legacy_packages(_SERVER_UTILS_PATH.read_text())
    assert server  # a parse that found nothing must not pass vacuously
    assert server == wb._PLR_LEGACY_PACKAGES


def test_drift_check_detects_a_divergent_list() -> None:
    """Negative control: the extractor sees a one-package difference, so the guard can fail."""
    source = _SERVER_UTILS_PATH.read_text()
    mutated = source.replace('  "arms",\n', '  "arms",\n  "not_a_real_package",\n', 1)
    assert mutated != source
    assert _extract_legacy_packages(mutated) != _extract_legacy_packages(source)


# ---------------------------------------------------------------------------
# emit_well_state: TipSpot.has_tip is a method at PLR 1.0
# ---------------------------------------------------------------------------


def _tip_mask_of_deck_with(wb, monkeypatch: pytest.MonkeyPatch, rack) -> int:
    """Run ``emit_well_state`` over a deck holding ``rack`` and return the emitted tip mask."""
    import json

    posted: list[dict] = []
    monkeypatch.setattr(wb, "IS_BROWSER_MODE", True)
    monkeypatch.setattr(wb, "postMessage", lambda msg: posted.append(json.loads(msg)), raising=False)

    deck = types.SimpleNamespace(get_all_resources=lambda: [rack])
    wb.emit_well_state(types.SimpleNamespace(deck=deck))

    assert len(posted) == 1
    assert posted[0]["type"] == "WELL_STATE_UPDATE"
    return int(posted[0]["payload"][rack.name]["tip_mask"], 16)


def test_emit_well_state_reports_an_empty_tip_spot_as_empty(wb, monkeypatch: pytest.MonkeyPatch) -> None:
    """(e) A spot with its tip removed has its mask bit cleared; the others stay set."""
    from pylabrobot.resources.hamilton.tip_racks import hamilton_96_tiprack_1000uL

    rack = hamilton_96_tiprack_1000uL("tips")
    assert rack.num_items == 96

    # Control: a full rack reports every spot as holding a tip.
    assert _tip_mask_of_deck_with(wb, monkeypatch, rack) == (1 << 96) - 1

    empty_index = 3
    rack.get_item(empty_index).unassign_tip()
    mask = _tip_mask_of_deck_with(wb, monkeypatch, rack)
    assert mask & (1 << empty_index) == 0
    assert mask == ((1 << 96) - 1) & ~(1 << empty_index)


def test_tipspot_has_tip_is_still_a_method_upstream() -> None:
    """Documents the trap: the bare attribute is a bound method, truthy even for an empty spot.

    If upstream ever turns ``has_tip`` back into a property this fails, and the comment in
    ``emit_well_state`` (and this file's premise) needs revisiting.
    """
    from pylabrobot.resources.hamilton.tip_racks import hamilton_96_tiprack_1000uL

    spot = hamilton_96_tiprack_1000uL("tips").get_item(0)
    spot.unassign_tip()
    assert spot.tip is None
    assert callable(spot.has_tip)
    assert bool(spot.has_tip) is True  # what the old code tested
    assert spot.has_tip() is False  # what it meant

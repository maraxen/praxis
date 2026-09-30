#!/usr/bin/env python3
"""Generate pin-matched golden fixtures for the vendored PyLabRobot visualizer.

Promotion of the verified spike capture script
``/tmp/claude-1000/praxis-spikes/s4/capture_payloads.py`` (the ``payloads/``
variant, which imports ``pylabrobot.liquid_handling`` and
``pylabrobot.visualizer.visualizer._serialize_resource_tree`` directly --
NOT the ``-pinned`` variant, which aliases the OLD ``_serialize_with_methods``
serializer for the d9651e2 pin, and NOT the ``-main`` variant, which imports
``pylabrobot.legacy.liquid_handling``).

Builds a real ``LiquidHandler`` + ``STARLetDeck`` tree and calls PyLabRobot's
OWN visualizer serialization helpers (``_serialize_resource_tree`` /
``_build_method_registry`` / ``_sanitize_floats``) directly, reproducing
exactly what ``Visualizer._send_resources_and_state()`` sends as the ``data``
payload of the ``set_root_resource`` and ``set_state`` events -- with no
websocket, no browser, and no ``Visualizer`` instance (construction alone
requires ``HAS_WEBSOCKETS``; the serializer functions do not).

## Why "pin-matched" is the whole difficulty (spec 260817, visualizer transport shim)

The ``set_root_resource`` payload schema differs across PyLabRobot pins:
``_serialize_with_methods`` (single-pass, per-node method signatures) at the
old d9651e2 pin vs. ``_serialize_resource_tree`` + ``_build_method_registry``
(split, per-class method signatures) at 0.2.2+. A fixture generated at one
pin and checked against another's renderer either silently under-counts
shapes or crashes the checker on a KeyError -- neither failure names the pin
mismatch. This script stamps the exact source SHA and ``pylabrobot.__version__``
into ``FIXTURE_MANIFEST.json`` (``pin_sha`` is intentionally the FIRST
key `viz_render_check` compares) precisely so a pin bump fails loudly with
"fixture was generated at pin X, current pin is Y -- regenerate", not a
mismatched shape count with no explanation.

Output (into --out-dir, default web-repl/tests/fixtures/visualizer):
  set_root_resource.json   -> the `data` payload of the set_root_resource event
                               (what repl_smoke.py --viz-check passes to
                               window.receiveFromPython('set_root_resource', ...))
  set_state.json           -> the `data` payload of the INITIAL full set_state event
                               that real boot always sends immediately after
                               set_root_resource (Visualizer._send_resources_and_state,
                               visualizer.py:643). Required, not optional: resource
                               geometry (set_root_resource) carries no tip/liquid
                               presence, so skipping this and going straight to the
                               delta below made an early version of this checker
                               measure a false "fill matches" -- both the has-tip and
                               after-pickup colors read back as Konva's default fill,
                               masking a real regression instead of catching one.
  delta_set_state.json     -> the `data` payload of a set_state delta produced by
                               a real tip pickup + liquid dispense, applied ON TOP OF
                               set_state.json above
  FIXTURE_MANIFEST.json    -> pin_sha, pylabrobot_version, generator_version,
                               resource_count (independently walked from the
                               serialized tree, so it does not depend on a
                               browser), and the delta's expected fill-color
                               transition. shape_count / layer_count start
                               null -- only a real Konva render can measure
                               them; `scripts/repl_smoke.py --viz-check --record`
                               fills them in from an actual browser run.

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("gen_viz_fixtures")

GENERATOR_VERSION = "1.1.0"
# 1.1.0: the root payload now passes through praxis.viz.browser.add_legacy_num_rails, the
# same adapter BrowserVisualizer.send_command applies, so the fixture is what the browser
# really receives (PLR 1.0 serializes num_tracks; the vendored lib.js draws rails from
# num_rails). Without it the gate would assert the rail-less render (355 shapes, not 394).


class FixtureError(RuntimeError):
    """Raised for any condition that must abort fixture generation loudly."""


def find_repo_root(start: Path) -> Path:
    """Search upward from `start` for the git repo root (a directory containing `.git`).

    Anchored to __file__, never Path.cwd() -- see ~/.claude/rules/CLUSTER.md §1a.
    Deliberately NOT "nearest pyproject.toml": this script lives under
    web-repl/scripts/, and web-repl/pyproject.toml exists (it holds only a
    [tool.pytest.ini_options] override, see that file's own comment) -- a
    pyproject.toml-based search would false-stop there instead of reaching
    the real repo root two levels up, and then look for external/pylabrobot
    at the wrong path entirely.
    """
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").exists():
            return candidate
    raise FixtureError(f"could not locate a .git repo root above {start}")


REPO_ROOT = find_repo_root(Path(__file__).parent)
DEFAULT_OUT_DIR = REPO_ROOT / "web-repl" / "tests" / "fixtures" / "visualizer"
DEFAULT_PLR_SUBMODULE = REPO_ROOT / "external" / "pylabrobot"


_VIZ_PKG = "_praxis_viz_for_fixtures"


def _load_viz_adapter() -> Any:
    """Return ``praxis.viz.browser.add_legacy_num_rails`` without touching ``sys.path``.

    ``web-repl/overlay/assets/python`` holds a ``praxis/`` package that must never be put on
    ``sys.path`` (it would shadow the repo's real top-level ``praxis``), so the package is
    loaded by path under a synthetic name -- the same way ``tests/test_browser_visualizer.py``
    does it.
    """
    viz_dir = REPO_ROOT / "web-repl" / "overlay" / "assets" / "python" / "praxis" / "viz"
    if _VIZ_PKG not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            _VIZ_PKG,
            viz_dir / "__init__.py",
            submodule_search_locations=[str(viz_dir)],
        )
        if spec is None or spec.loader is None:
            raise FixtureError(f"cannot load praxis.viz from {viz_dir}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[_VIZ_PKG] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{_VIZ_PKG}.browser").add_legacy_num_rails


def _count_resources(node: dict[str, Any]) -> int:
    """Recursively count nodes in a `_serialize_resource_tree` output.

    Mirrors lib.js `loadResource`, which registers every node (root plus all
    descendants) into the `resources` map keyed by name -- this is the exact
    quantity `Object.keys(resources).length` measures in the browser. Computing
    it here, in Python, means the fixture's expected resource_count does not
    depend on a browser run to exist.
    """
    return 1 + sum(_count_resources(child) for child in node.get("children", []))


def _read_submodule_sha(submodule_dir: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(submodule_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise FixtureError(f"could not read submodule HEAD at {submodule_dir}: {e.stderr}") from e
    return out.stdout.strip()


async def _capture(plr_submodule: Path) -> dict[str, Any]:
    # Imported lazily so --help works even if pylabrobot / its deps are not
    # installed in the invoking interpreter.
    from pylabrobot import __version__ as plr_version
    from pylabrobot.legacy.liquid_handling import LiquidHandler
    from pylabrobot.legacy.liquid_handling.backends import LiquidHandlerChatterboxBackend
    from pylabrobot.resources import (
        PLT_CAR_L5AC_A00,
        TIP_CAR_480_A00,
        Cor_96_wellplate_360ul_Fb,
        set_tip_tracking,
        set_volume_tracking,
    )
    from pylabrobot.resources.hamilton import STARLetDeck
    from pylabrobot.resources.hamilton import hamilton_96_tiprack_1000uL_filter as HTF
    from pylabrobot.visualizer.visualizer import (
        _build_method_registry,
        _sanitize_floats,
        _serialize_resource_tree,
    )

    set_tip_tracking(True)
    set_volume_tracking(True)

    deck = STARLetDeck()
    lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck)
    await lh.setup()

    tip_car = TIP_CAR_480_A00(name="tip_carrier")
    tip_car[0] = tip_rack = HTF(name="tips_01")
    deck.assign_child_resource(tip_car, rails=15)

    plt_car = PLT_CAR_L5AC_A00(name="plate_carrier")
    plt_car[0] = plate = Cor_96_wellplate_360ul_Fb(name="plate_01")
    deck.assign_child_resource(plt_car, rails=8)

    root = lh.deck
    logger.info("root resource: %s (%s)", root.name, type(root).__name__)

    def full_state(resource: Any) -> dict[str, Any]:
        """Mirror of Visualizer._send_resources_and_state's save_resource_state()."""
        state: dict[str, Any] = {}

        def rec(r: Any) -> None:
            rs = r.serialize_state()
            if rs is not None:
                state[r.name] = rs
            for child in r.children:
                rec(child)

        rec(resource)
        return state

    add_legacy_num_rails = _load_viz_adapter()
    root_payload = _sanitize_floats(
        {
            # The adapter is applied here exactly as BrowserVisualizer.send_command applies it
            # to set_root_resource, so this fixture is the payload the browser really gets.
            "resource": add_legacy_num_rails(_serialize_resource_tree(root)),
            "method_registry": _build_method_registry(root),
        }
    )

    tip_a1_name = "tips_01_tipspot_A1"
    initial_state = full_state(root)
    initial_state_payload = _sanitize_floats(initial_state)
    before = {n: json.dumps(s, sort_keys=True) for n, s in initial_state.items()}

    await lh.pick_up_tips(tip_rack["A1:D1"])
    # `set_volume`, not `set_liquids([(None, 100.0)])`: 1.0 deprecates the latter
    # (it is `set_volume(sum(volumes))`) and would emit a DeprecationWarning here.
    plate.get_item("A1").tracker.set_volume(100.0)
    plate.get_item("B1").tracker.set_volume(100.0)
    after = full_state(root)
    delta = {n: s for n, s in after.items() if json.dumps(s, sort_keys=True) != before.get(n)}
    delta_payload = _sanitize_floats(delta)
    logger.info("delta touches %d resources: %s", len(delta), sorted(delta)[:8])

    if tip_a1_name not in delta:
        raise FixtureError(
            f"expected {tip_a1_name!r} in the delta (pick_up_tips A1:D1 should empty it) "
            f"but delta keys were: {sorted(delta)}"
        )
    if tip_a1_name not in initial_state:
        raise FixtureError(
            f"expected {tip_a1_name!r} in the INITIAL state (before any pickup) -- "
            "without this, a checker that skips the initial set_state event cannot "
            "distinguish 'has tip' from Konva's default fill, and a real regression "
            "there (the #1 pre-mortem risk: root renders, everything after is silent) "
            "would go undetected. initial_state keys were: "
            f"{sorted(initial_state)[:8]}..."
        )

    resource_count = _count_resources(root_payload["resource"])
    logger.info(
        "measured resource_count=%d (top children=%d, method_registry classes=%d)",
        resource_count,
        len(root_payload["resource"]["children"]),
        len(root_payload["method_registry"]),
    )

    submodule_sha = _read_submodule_sha(plr_submodule)

    return {
        "root_payload": root_payload,
        "initial_state_payload": initial_state_payload,
        "delta_payload": delta_payload,
        "resource_count": resource_count,
        "delta_target_resource": tip_a1_name,
        "pin_sha": submodule_sha,
        "pylabrobot_version": plr_version,
    }


def generate(out_dir: Path, plr_submodule: Path) -> dict[str, Any]:
    captured = asyncio.run(_capture(plr_submodule))

    out_dir.mkdir(parents=True, exist_ok=True)

    root_path = out_dir / "set_root_resource.json"
    initial_state_path = out_dir / "set_state.json"
    delta_path = out_dir / "delta_set_state.json"
    manifest_path = out_dir / "FIXTURE_MANIFEST.json"

    root_path.write_text(json.dumps(captured["root_payload"]))
    initial_state_path.write_text(json.dumps(captured["initial_state_payload"]))
    delta_path.write_text(json.dumps(captured["delta_payload"]))

    # Preserve shape_count / layer_count from an existing manifest if present --
    # those fields can only be filled by an actual browser render
    # (`repl_smoke.py --viz-check --record`) and regenerating the JSON payloads
    # should not silently wipe a previously-measured golden number.
    existing_shape_count = None
    existing_layer_count = None
    if manifest_path.is_file():
        try:
            prev = json.loads(manifest_path.read_text())
            if prev.get("pin_sha") == captured["pin_sha"]:
                existing_shape_count = prev.get("expected", {}).get("shape_count")
                existing_layer_count = prev.get("expected", {}).get("layer_count")
            else:
                logger.warning(
                    "existing manifest was generated at a different pin (%s != %s); "
                    "dropping its shape_count/layer_count -- re-record with --viz-check --record",
                    prev.get("pin_sha"),
                    captured["pin_sha"],
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("could not read existing manifest, starting fresh: %s", e)

    manifest = {
        "generator": "gen_viz_fixtures.py",
        "generator_version": GENERATOR_VERSION,
        "pin_sha": captured["pin_sha"],
        "pylabrobot_version": captured["pylabrobot_version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected": {
            "resource_count": captured["resource_count"],
            "shape_count": existing_shape_count,
            "layer_count": existing_layer_count,
        },
        "delta": {
            "target_resource": captured["delta_target_resource"],
            "fill_before": "#40CDA1",
            "fill_after": "white",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    logger.info("wrote %s (%d bytes)", root_path, root_path.stat().st_size)
    logger.info("wrote %s (%d bytes)", initial_state_path, initial_state_path.stat().st_size)
    logger.info("wrote %s (%d bytes)", delta_path, delta_path.stat().st_size)
    logger.info("wrote %s", manifest_path)
    if existing_shape_count is None:
        logger.warning(
            "shape_count/layer_count are still null -- run "
            "`uv run python scripts/repl_smoke.py --viz-check --record` to measure them "
            "from a real Konva render before this fixture can gate anything."
        )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"Default: {DEFAULT_OUT_DIR}")
    p.add_argument(
        "--plr-submodule",
        type=Path,
        default=DEFAULT_PLR_SUBMODULE,
        help=f"Path to the pylabrobot submodule, used only to read its pinned SHA. Default: {DEFAULT_PLR_SUBMODULE}",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    try:
        generate(args.out_dir, args.plr_submodule)
    except FixtureError as e:
        logger.error("fixture generation failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())

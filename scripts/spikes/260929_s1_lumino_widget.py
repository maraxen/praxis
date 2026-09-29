#!/usr/bin/env python3
"""Spike S1 (notebook display epic, task A1b-1): the Lumino widget, split-right, size limits
and cell-state hooks probe.

Pre-registered by ``scripts/spikes/260929_s1_lumino_widget.bth.toml`` (committed BEFORE the
first run). Design: ``.praxia/docs/specs/260929_notebook-display-epic.md`` D1 (row S1), D6
(the sizing-case table), D16 (shared unit runner, bounded teardown) and D17 (units, resume,
chunking, completeness). Run it as::

    bth run --project-slug praxis -- uv run --no-sync python3 \
        scripts/spikes/260929_s1_lumino_widget.py --out-dir outputs/spikes/260929_s1 [--resume]

Two modes, one file:

* **Driver** (no ``--unit``): iterates the ten D17 S1 units in table order, starts each as its
  own subprocess ``<script> --unit <name> --out-dir <dir> ...`` through
  ``unit_runner.run_unit`` (timeout = 4 min + 60 s), applies the ``--resume`` rule, and
  evaluates the sidecar's ``[outcomes]`` inputs ONLY when every unit is complete. An
  incomplete run writes no ``$BTH_RESULTS_PATH`` and exits 3, so bathos records no outcome.
* **Unit** (``--unit <name>``): the D17 per-unit sequence. ``ensure_token`` -> arm the
  ``Watchdog`` (4 min) -> clear own stamp/artifact/timeout marker -> probe -> write
  ``<out>/units/<name>.json`` under the watchdog lock -> bounded teardown (browser and
  Playwright closed, ``kill_tree`` over residual descendants, flush) -> commit
  ``<out>/units/<name>.stamp.json`` through ``Watchdog.commit`` -> ``os._exit(stamp.exit)``.

Measurement discipline (``~/.claude/rules/BATHOS.md``): every result is read from the
notebook/shell models and the DOM through ``page.evaluate``, never from printed console
text. A verdict that could be a probe bug (a "not honoured", "unreachable" or "not kept")
is only ever reported next to a control that proves the instrument can say the opposite:
the unconstrained drag range, the deliberate iframe re-insertion, the structural check on
the real root class; and ``neg_wrong_ctor`` is the negative control that must FAIL. A probe
that raises is an ``error`` finding, never a negative result.

PLR independence: nothing here imports or touches PyLabRobot. The only kernel use is the
``cell_hooks`` unit running five trivial cells in the Pyodide kernel; every other unit only
needs the JupyterLab shell (the kernel boots in the background and is never awaited).

``--dry-run`` prints the unit table, the pre-registered fields and the resolved inputs'
sources without launching a browser or hashing the dist.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

LOG = logging.getLogger("s1_spike")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
FIXTURE_PATH = REPO_ROOT / "web-repl" / "tests" / "fixtures" / "notebooks" / "s1_cell_states.ipynb"
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"

#: D17 S1 row: 4 min per unit. The driver kills at this + 60 s (D16/D17). Estimates from the
#: spec, not measurements; not changed here.
UNIT_TIMEOUT_S = 4 * 60.0
DRIVER_EXTRA_S = 60.0

VIEWPORT = {"width": 1440, "height": 900}
FIXTURE_NB_PATH = "s1_cell_states.ipynb"
NAV_TIMEOUT_MS = 90_000
KERNEL_WAIT_MS = 150_000
STEP_WAIT_MS = 45_000

#: Pre-registered numeric tolerances (mirrored in the sidecar's [design.tolerances]).
TOL_DRAG_CONTROL_PX = 12.0  # the unconstrained drag must land within this of the request
TOL_LIMIT_PX = 3.0  # a clamped width must land within this of the CSS min/max
TOL_LAYOUT_FRACTION = 0.05  # restoreLayout sizes: |measured/dock_width - requested|
MIN_LAYOUT_SWING_FRACTION = 0.25  # the two requested fractions must move the widget this far
LIMITS_PX = {"min": 420, "max": 480}  # the D6 1280-1599 numbers
DRAG_REQUEST_PX = {"narrow": 300, "wide": 700}  # AC-36 drags

STATES = ("not_run", "ran", "running", "error", "stale")
#: cell index of each state in the fixture notebook
STATE_CELL = {"not_run": 0, "ran": 1, "running": 2, "error": 3, "stale": 4}
NEUTRAL_CELL = 5  # a padding cell next to the state cells
STALE_EDIT_SOURCE = 'print("s1-stale", 2)'


# --------------------------------------------------------------------------- #
# The unit table (D17 S1 row) and each unit's pre-registered artifact fields
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class UnitSpec:
    name: str
    upstream: tuple[str, ...]
    required: tuple[str, ...]


WIDGET_UNITS = ("widget_a", "widget_b")

UNITS: tuple[UnitSpec, ...] = (
    UnitSpec(
        "widget_a",
        (),
        (
            "usable", "structural_found", "chain", "root_index", "root_ctor_name",
            "constructed_ok", "is_widget_instance", "attached_ok", "split_right_ok",
            "recipe", "reason",
        ),
    ),
    UnitSpec(
        "widget_b",
        (),
        (
            "usable", "command_registered", "widget_created", "iframe_found", "sandbox_attr",
            "sandbox_allows_scripts_same_origin", "same_origin_readable", "split_right_ok",
            "recipe", "reason",
        ),
    ),
    UnitSpec(
        "split_right",
        WIDGET_UNITS,
        (
            "widget_source", "split_right_ok", "notebook_rect_before", "notebook_rect_after",
            "widget_rect", "side_by_side", "orientation", "reason",
        ),
    ),
    UnitSpec(
        "css_limits",
        WIDGET_UNITS,
        (
            "widget_source", "css_limits_honoured", "drag_control_ok", "control_widths",
            "limited_widths", "dock_width_px", "limits_px", "tolerance_px", "reason",
        ),
    ),
    UnitSpec(
        "dock_layout_sizing",
        WIDGET_UNITS,
        (
            "widget_source", "dock_panel_found", "dock_accessor", "save_layout_ok",
            "split_area_found", "sizes_before", "requested_fractions", "measured_fractions",
            "dock_width_px", "restore_called", "dock_layout_sizing_reachable", "reason",
        ),
    ),
    UnitSpec(
        "css_limits_refit",
        WIDGET_UNITS,
        (
            "widget_source", "css_limits_refit", "baseline_width_px", "target_width_px",
            "width_before_fit_px", "width_after_fit_px", "width_after_viewport_nudge_px",
            "fit_called", "parent_is_dock_panel", "reason",
        ),
    ),
    UnitSpec(
        "restore_layout_keeps_iframe",
        WIDGET_UNITS,
        (
            "widget_source", "restore_layout_keeps_iframe", "reload_control_detected",
            "token_set", "load_events_control", "load_events_delta", "token_survived",
            "iframe_same_node", "iframe_reinserted", "restore_called", "reason",
        ),
    ),
    UnitSpec(
        "cell_hooks",
        (),
        (
            "kernel_ready", "states_reached", "all_states_reached", "snapshots", "hooks",
            "all_states_derivable", "n_states_with_css_hook",
        ),
    ),
    UnitSpec(
        "windowing",
        (),
        (
            "windowing_mode", "windowing_mode_reads", "windowing_exercised", "detach_observed",
            "reattach_raw", "reattach_signal", "cell_count",
        ),
    ),
    UnitSpec(
        "neg_wrong_ctor",
        (),
        (
            "positive_control_structural_pass", "wrong_candidates",
            "negative_control_failed_as_required",
        ),
    ),
)
UNIT_NAMES = tuple(u.name for u in UNITS)
UNIT_BY_NAME = {u.name: u for u in UNITS}


# --------------------------------------------------------------------------- #
# Loading the shared modules BY PATH (nothing edits sys.path)
# --------------------------------------------------------------------------- #


def _load_by_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


unit_runner = _load_by_path("unit_runner", RUNNER_PATH)
_REPL_SMOKE: Any = None


def repl_smoke() -> Any:
    """``scripts/repl_smoke.py`` loaded by path, once (ServedDir, chromium_launch_args, ...)."""
    global _REPL_SMOKE
    if _REPL_SMOKE is None:
        _REPL_SMOKE = _load_by_path("repl_smoke", REPL_SMOKE_PATH)
    return _REPL_SMOKE


# --------------------------------------------------------------------------- #
# Hashing and the per-unit input set (D17 "Inputs hashed")
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    return unit_runner._sha256_file(Path(path))


@dataclasses.dataclass
class InputEnv:
    """Everything the input set is built from, already hashed (so tests can fake it)."""

    script: str
    runner: str
    harness: str  # sha256 of scripts/repl_smoke.py (loaded by path; D17 "harness" input)
    dist: str
    fixture: str
    chrome: str
    driver: str
    base_path: str = "/"
    chrome_path: str = ""
    chrome_version: str = ""


def chrome_version_of(chrome_path: str) -> str:
    try:
        proc = subprocess.run(
            [chrome_path, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
        return (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {type(exc).__name__}"


def build_env(args: argparse.Namespace) -> InputEnv:
    """Resolve and hash the real inputs. Raises FileNotFoundError on a missing dist/chrome."""
    chrome_path = str(repl_smoke().resolve_chrome_path(args.chrome_path))
    if "headless_shell" in chrome_path or "headless-shell" in chrome_path:
        raise RuntimeError(
            f"{chrome_path} is a headless shell; S1 needs FULL Chromium (D16). Pass --chrome-path."
        )
    version = chrome_version_of(chrome_path)
    return InputEnv(
        script=sha256_file(SCRIPT_PATH),
        runner=sha256_file(RUNNER_PATH),
        harness=sha256_file(REPL_SMOKE_PATH),
        dist=unit_runner.dist_hash(args.dist),
        fixture=sha256_file(FIXTURE_PATH),
        chrome=sha256_bytes(f"{chrome_path}\n{version}".encode()),
        driver=unit_runner.driver_input(),
        base_path=args.base_path,
        chrome_path=chrome_path,
        chrome_version=version,
    )


def compute_inputs(unit: str, env: InputEnv, upstream_sha: dict[str, str]) -> dict[str, str]:
    """The stamp's ``inputs``: script, runner, harness, dist, fixture, chrome, driver, args, and the
    ``artifact_sha256`` of every upstream unit (a recomputed widget unit invalidates every
    unit that builds on it)."""
    inputs = {
        "script": env.script,
        "runner": env.runner,
        "harness": env.harness,
        "dist": env.dist,
        "fixture": env.fixture,
        "chrome": env.chrome,
        "driver": env.driver,
        "args": sha256_bytes(
            json.dumps(
                {"unit": unit, "viewport": VIEWPORT, "base_path": env.base_path}, sort_keys=True
            ).encode()
        ),
    }
    for up, sha in sorted(upstream_sha.items()):
        inputs[f"upstream:{up}"] = sha
    return inputs


# --------------------------------------------------------------------------- #
# Unit files, completeness and the resume rule (D17)
# --------------------------------------------------------------------------- #


def unit_paths(out_dir: Path, name: str) -> dict[str, Path]:
    units = out_dir / "units"
    return {
        "artifact": units / f"{name}.json",
        "stamp": units / f"{name}.stamp.json",
        "timeout": units / f"{name}.timeout.json",
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _rm(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def inspect_unit(
    out_dir: Path, spec: UnitSpec, current_inputs: dict[str, str]
) -> dict[str, Any]:
    """Classify one unit's files against the CURRENT inputs.

    * ``complete``: artifact and a matching stamp exist (the stamp's ``artifact_sha256``
      equals the artifact on disk and its ``inputs`` equal the current inputs). A raised
      probe is complete (its ``error`` finding is in the artifact). Only a timeout or a
      stampless crash is incomplete.
    * ``reusable`` (the ``--resume`` rule): complete AND ``stamp.exit == 0`` AND no
      ``error`` finding AND every pre-registered field present.
    * ``mismatched``: the input names whose hash differs from the stamp's.
    """
    paths = unit_paths(out_dir, spec.name)
    artifact_bytes: bytes | None
    try:
        artifact_bytes = paths["artifact"].read_bytes()
    except OSError:
        artifact_bytes = None
    stamp = _read_json(paths["stamp"])
    artifact = None
    if artifact_bytes is not None:
        try:
            artifact = json.loads(artifact_bytes)
        except ValueError:
            artifact = None
    state: dict[str, Any] = {
        "unit": spec.name,
        "artifact": artifact,
        "stamp": stamp if isinstance(stamp, dict) else None,
        "artifact_path": str(paths["artifact"]),
        "complete": False,
        "reusable": False,
        "mismatched": [],
        "reasons": [],
    }
    if artifact is None or not isinstance(artifact, dict):
        state["reasons"].append("no artifact")
        return state
    if state["stamp"] is None:
        state["reasons"].append("no stamp")
        return state
    stamp = state["stamp"]
    if stamp.get("artifact_sha256") != sha256_bytes(artifact_bytes or b""):
        state["reasons"].append("artifact_sha256 does not match the artifact on disk")
        return state
    recorded = stamp.get("inputs") or {}
    mismatched = sorted(
        name
        for name in set(recorded) | set(current_inputs)
        if recorded.get(name) != current_inputs.get(name)
    )
    state["mismatched"] = mismatched
    if mismatched:
        state["reasons"].append("stamp inputs differ from current inputs")
        return state
    state["complete"] = True
    if stamp.get("exit") != 0:
        state["reasons"].append(f"stamp.exit == {stamp.get('exit')}")
    if artifact.get("error") is not None:
        state["reasons"].append("artifact carries an error finding")
    missing = [f for f in spec.required if f not in artifact] + list(
        artifact.get("missing_fields") or []
    )
    if missing:
        state["reasons"].append(f"pre-registered fields missing: {sorted(set(missing))}")
    state["reusable"] = not state["reasons"]
    return state


# --------------------------------------------------------------------------- #
# Pure derivations (unit-tested without a browser)
# --------------------------------------------------------------------------- #


def pick_source(a: dict[str, Any] | None, b: dict[str, Any] | None) -> str | None:
    """D1 order: S1-A if the constructor route is usable, else S1-B, else None (S1-C)."""
    if a and a.get("error") is None and a.get("usable") is True:
        return "S1-A"
    if b and b.get("error") is None and b.get("usable") is True:
        return "S1-B"
    return None


def sizing_case(css: bool | None, layout: bool | None) -> str | None:
    """The D6 table row: CSS limits honoured x layout sizing reachable."""
    if css is None or layout is None:
        return None
    if css and layout:
        return "honoured_reachable"
    if layout:
        return "ignored_reachable"
    if css:
        return "honoured_unreachable"
    return "S1-L"


def sizing_branch(css: bool | None, layout: bool | None) -> str | None:
    """D1 size-limit axis: CSS limits if honoured, else DockPanel layout, else S1-L."""
    if css is None or layout is None:
        return None
    if css:
        return "css_limits"
    return "dock_layout" if layout else "S1-L"


def width_key_status(
    css: bool | None, layout: bool | None, refit: bool | None, keeps_iframe: bool | None
) -> dict[str, Any] | None:
    """Every AC-36 width key's status (``asserted`` / ``recorded-only``), per the D6 table,
    its ``restore_layout_keeps_iframe = false`` note and AC-36's case paragraph.

    Under S1-L every width key is recorded-only. With layout reachable but
    ``keeps_iframe`` false, "layout" cells mean "layout at open and on tier changes only", so
    the drag clamps and ``resize_within_wide`` follow the ``unreachable`` row of the same CSS
    column. ``fit_after_tier_change`` spans both tiers, so its two components are reported
    separately (see the report's ambiguity list). ``None`` if an input is unmeasured.
    """
    if css is None or layout is None or refit is None or keeps_iframe is None:
        return None
    rec, ass = "recorded-only", "asserted"
    if not css and not layout:
        return {
            "case": "S1-L",
            "open_width_1280_1599": rec,
            "drag_clamp_1280_1599": rec,
            "open_width_ge_1600": rec,
            "fit_after_tier_change": {"tier_1280_1599": rec, "tier_ge_1600": rec},
            "resize_within_wide": rec,
            "ac39d_ge1600_negative": "skipped",
        }
    layout_clamps = layout and keeps_iframe
    open_ge = ass if (layout or refit) else rec
    return {
        "case": sizing_case(css, layout),
        "open_width_1280_1599": ass,
        "drag_clamp_1280_1599": ass if (css or layout_clamps) else rec,
        "open_width_ge_1600": open_ge,
        "fit_after_tier_change": {"tier_1280_1599": ass, "tier_ge_1600": open_ge},
        "resize_within_wide": ass if (layout_clamps or (css and refit)) else rec,
        "ac39d_ge1600_negative": "asserted" if open_ge == ass else "skipped",
    }


_DIGITS = re.compile(r"\d+")
#: Selection/focus classes describe where the cursor is, not the cell's execution state; they
#: are excluded so the last-run cell is not credited with a "hook" merely for being active.
_NON_STATE_CLASSES = frozenset(
    {"jp-mod-active", "jp-mod-selected", "jp-mod-multiSelected", "jp-mod-focused", "jp-mod-commandMode", "jp-mod-editMode"}
)
_CSS_PREFIXES = ("cls:", "attr:", "mime:")
_MODEL_PREFIXES = ("exec_count:", "exec_state:", "dirty:", "out_types:")


def cell_features(snap: dict[str, Any]) -> set[str]:
    """Observable features of one cell snapshot. ``cls:``/``attr:``/``mime:`` are CSS hooks
    (selectable), ``prompt:`` is DOM text, the rest are model signals."""
    feats: set[str] = set()
    for token in snap.get("classes") or []:
        if token not in _NON_STATE_CLASSES:
            feats.add(f"cls:{token}")
    for name in snap.get("data_attrs") or []:
        feats.add(f"attr:{name}")
    for mime in snap.get("mimes") or []:
        feats.add(f"mime:{mime}")
    prompt = snap.get("prompt_text")
    if prompt is not None:
        feats.add("prompt:" + _DIGITS.sub("N", prompt))
    feats.add("exec_count:" + ("null" if snap.get("execution_count") is None else "set"))
    if snap.get("execution_state") is not None:
        feats.add(f"exec_state:{snap['execution_state']}")
    if snap.get("is_dirty") is not None:
        feats.add(f"dirty:{str(snap['is_dirty']).lower()}")
    feats.add("out_types:" + ",".join(sorted(set(snap.get("output_types") or []))))
    return feats


def derive_hooks(snapshots: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per state, the features present in that state's cell and in NONE of the other four.

    ``mechanism`` is ``css`` if any unique feature is a CSS hook, else ``model`` if any is
    DOM text or a model signal, else ``none`` (D1: a CSS hook where one exists, otherwise
    ``chrome.js`` computes it from model signals). Only states with a snapshot count.
    """
    feats = {s: cell_features(snapshots[s]) for s in snapshots if snapshots[s]}
    signatures = {
        s: frozenset(f for f in fs if f.startswith(_MODEL_PREFIXES + ("prompt:",)))
        for s, fs in feats.items()
    }
    hooks: dict[str, dict[str, Any]] = {}
    for state, mine in feats.items():
        others: set[str] = set()
        for other, theirs in feats.items():
            if other != state:
                others |= theirs
        unique = sorted(mine - others)
        css = [f for f in unique if f.startswith(_CSS_PREFIXES)]
        dom_text = [f for f in unique if f.startswith("prompt:")]
        model = [f for f in unique if f.startswith(_MODEL_PREFIXES)]
        combination = all(
            signatures[state] != signatures[other] for other in signatures if other != state
        )
        if css:
            mechanism, via = "css", "single-css-feature"
        elif model or dom_text:
            mechanism, via = "model", "single-model-feature"
        elif combination:
            mechanism, via = "model", "combination-of-model-features"
        else:
            mechanism, via = "none", None
        hooks[state] = {
            "css": css, "dom_text": dom_text, "model": model, "mechanism": mechanism, "via": via,
        }
    return hooks


def state_reached(state: str, snap: dict[str, Any] | None, original_source: str) -> bool:
    """Ground truth that a fixture cell IS in the state it stands for, read from the model
    (independent of the hooks under test)."""
    if not snap:
        return False
    types = set(snap.get("output_types") or [])
    count = snap.get("execution_count")
    if state == "not_run":
        return count is None and not types
    if state == "ran":
        return count is not None and "error" not in types and bool(types)
    if state == "running":
        return (snap.get("execution_state") not in (None, "idle")) or (
            "*" in (snap.get("prompt_text") or "")
        )
    if state == "error":
        return "error" in types
    if state == "stale":
        return count is not None and (snap.get("source") or "") != original_source
    return False


def reattach_signal_from(raw: dict[str, Any]) -> str | None:
    """The pre-registered priority for the signal that fires when a virtualised cell's DOM is
    re-attached: (1) ``cell.inViewportChanged`` emitted ``true``; (2) the cell widget received
    an ``after-attach`` message; (3) the cell node was re-inserted (a DOM childList mutation).
    ``raw`` is the counts recorded in the scroll-back phase only."""
    if True in (raw.get("inViewportChanged") or []):
        return "inViewportChanged"
    if "after-attach" in (raw.get("messages") or []):
        return "after-attach-message"
    if (raw.get("mutations_added") or 0) >= 1:
        return "dom-mutation"
    return None


def evaluate_validity(arts: dict[str, dict[str, Any]], src: str | None) -> dict[str, bool]:
    """Named checks whose conjunction is ``measurement_valid``. Any ``error`` finding, a
    control that did not behave as required, an unmeasured (``None``) sizing key, or an
    inconsistency between units makes the run ``invalid`` (the residual outcome): it never
    satisfies a positive outcome."""
    neg = arts["neg_wrong_ctor"]
    checks: dict[str, bool] = {
        "no_error_findings": all(a.get("error") is None for a in arts.values()),
        "negative_control_failed_as_required": neg.get("negative_control_failed_as_required")
        is True,
        "positive_control_structural_pass": neg.get("positive_control_structural_pass") is True,
        "all_states_reached": arts["cell_hooks"].get("all_states_reached") is True,
        "windowing_mode_recorded": isinstance(arts["windowing"].get("windowing_mode"), str),
    }
    if src is not None:
        css_u, lay_u = arts["css_limits"], arts["dock_layout_sizing"]
        refit_u, keep_u = arts["css_limits_refit"], arts["restore_layout_keeps_iframe"]
        checks.update(
            {
                "drag_control_ok": css_u.get("drag_control_ok") is True,
                "css_limits_measured": css_u.get("css_limits_honoured") is not None,
                "layout_sizing_measured": lay_u.get("dock_layout_sizing_reachable") is not None,
                "css_limits_refit_measured": refit_u.get("css_limits_refit") is not None,
                "restore_measured": keep_u.get("restore_layout_keeps_iframe") is not None,
                "reload_control_detected": keep_u.get("reload_control_detected") is True,
                "split_right_consistent": arts["split_right"].get("split_right_ok") is True
                and arts["split_right"].get("widget_source") == src,
                "downstream_source_agrees": all(
                    arts[u].get("widget_source") == src
                    for u in (
                        "css_limits", "dock_layout_sizing", "css_limits_refit",
                        "restore_layout_keeps_iframe",
                    )
                ),
            }
        )
    return checks


def derive_outcome_fields(arts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The flat scalar fields the sidecar's ``[outcomes]`` conditions read, plus the
    ``details`` (D1 branch, D6 case, AC-36 width-key statuses, validity checks)."""
    src = pick_source(arts["widget_a"], arts["widget_b"])
    widget_branch = src or "S1-C"
    if src is None:
        css = layout = refit = keeps = None
    else:
        css = arts["css_limits"].get("css_limits_honoured")
        layout = arts["dock_layout_sizing"].get("dock_layout_sizing_reachable")
        refit = arts["css_limits_refit"].get("css_limits_refit")
        keeps = arts["restore_layout_keeps_iframe"].get("restore_layout_keeps_iframe")
    validity = evaluate_validity(arts, src)
    branch_sizing = sizing_branch(css, layout)
    hooks = arts["cell_hooks"].get("hooks") or {}
    flat = {
        "all_units_complete": True,
        "n_units": len(UNITS),
        "n_error_units": sum(1 for a in arts.values() if a.get("error") is not None),
        "measurement_valid": all(validity.values()),
        "widget_branch": widget_branch,
        "sizing_branch": branch_sizing,
        "sizing_case": sizing_case(css, layout),
        "d1_branch": widget_branch + ("+S1-L" if branch_sizing == "S1-L" else ""),
        "split_right_ok": arts["split_right"].get("split_right_ok"),
        "css_limits_honoured": css,
        "dock_layout_sizing_reachable": layout,
        "css_limits_refit": refit,
        "restore_layout_keeps_iframe": keeps,
        "windowing_mode": arts["windowing"].get("windowing_mode"),
        "reattach_signal": arts["windowing"].get("reattach_signal"),
        "negative_control_failed_as_required": arts["neg_wrong_ctor"].get(
            "negative_control_failed_as_required"
        ),
        "positive_control_structural_pass": arts["neg_wrong_ctor"].get(
            "positive_control_structural_pass"
        ),
        "all_states_reached": arts["cell_hooks"].get("all_states_reached"),
        "all_states_derivable": arts["cell_hooks"].get("all_states_derivable"),
        "n_states_with_css_hook": sum(1 for h in hooks.values() if h.get("mechanism") == "css"),
    }
    details = {
        "validity_checks": validity,
        "width_key_status": width_key_status(css, layout, refit, keeps),
        "cell_state_mechanisms": {s: h.get("mechanism") for s, h in hooks.items()},
    }
    return {"flat": flat, "details": details}


# --------------------------------------------------------------------------- #
# The in-page probe library (installed as window.__s1; read via page.evaluate)
# --------------------------------------------------------------------------- #

S1_JS = r"""
(() => {
  if (window.__s1) return true;
  const S = {};
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const raf2 = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const hasOwnFn = (o, k) => Object.prototype.hasOwnProperty.call(o, k) && typeof o[k] === 'function';
  const rect = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {x: r.x, y: r.y, w: r.width, h: r.height, left: r.left, right: r.right, top: r.top, bottom: r.bottom};
  };
  S.sleep = sleep;
  S.rect = rect;
  S.settle = async (ms) => { await raf2(); await sleep(ms === undefined ? 350 : ms); await raf2(); return true; };
  S.shell = () => window.jupyterapp.shell;

  // ---- the shell's main DockPanel (private in LabShell; located by capability) ----
  S.dock = () => {
    const sh = S.shell();
    for (const [acc, c] of [['_dockPanel', sh._dockPanel], ['dockPanel', sh.dockPanel]]) {
      if (c && typeof c.saveLayout === 'function' && typeof c.restoreLayout === 'function') return {dock: c, accessor: acc};
    }
    for (const k of Object.keys(sh)) {
      const v = sh[k];
      if (v && typeof v.saveLayout === 'function' && typeof v.restoreLayout === 'function' && v.node && v.node.id === 'jp-main-dock-panel') return {dock: v, accessor: 'scan:' + k};
    }
    return {dock: null, accessor: null};
  };
  S.nbPanel = () => {
    for (const w of S.shell().widgets('main')) {
      if (w.node && w.node.classList.contains('jp-NotebookPanel') && w.content) return w;
    }
    return null;
  };

  // ---- S1-A: the structural check and the prototype walk ----
  S.isRootCtor = (C) => {
    try {
      if (typeof C !== 'function' || !C.prototype) return false;
      const p = C.prototype;
      return hasOwnFn(p, 'processMessage') && hasOwnFn(p, 'onAfterAttach') && Object.getPrototypeOf(p) === Object.prototype;
    } catch (e) { return false; }
  };
  S.walk = (inst) => {
    const chain = [];
    let o = Object.getPrototypeOf(inst); let guard = 0;
    while (o && o !== Object.prototype && guard++ < 64) {
      const C = o.constructor;
      chain.push({
        index: chain.length, ctor_name: C ? C.name : null,
        has_processMessage: hasOwnFn(o, 'processMessage'), has_onAfterAttach: hasOwnFn(o, 'onAfterAttach'),
        proto_is_object_proto: Object.getPrototypeOf(o) === Object.prototype, structural: S.isRootCtor(C),
      });
      o = Object.getPrototypeOf(o);
    }
    return chain;
  };
  S.rootCtor = (inst) => {
    let o = Object.getPrototypeOf(inst); let last = null; let guard = 0;
    while (o && o !== Object.prototype && guard++ < 64) { last = o; o = Object.getPrototypeOf(o); }
    return last ? last.constructor : null;
  };
  S.walkNotebook = () => {
    const nb = S.nbPanel();
    if (!nb) return {ok: false, reason: 'no notebook panel'};
    const chain = S.walk(nb);
    const C = S.rootCtor(nb);
    return {ok: true, chain, root_index: chain.length ? chain.length - 1 : null, root_ctor_name: C ? C.name : null, structural: S.isRootCtor(C)};
  };
  S.negControl = () => {
    const nb = S.nbPanel();
    if (!nb) return {ok: false, reason: 'no notebook panel'};
    const root = S.rootCtor(nb);
    const leaf = Object.getPrototypeOf(nb).constructor;
    class DecoyExtendsRoot extends root {}
    const wrong = [
      {name: 'Object', ctor: Object},
      {name: 'Array', ctor: Array},
      {name: 'leaf:' + (leaf ? leaf.name : '?'), ctor: leaf},
      {name: 'DecoyExtendsRoot', ctor: DecoyExtendsRoot},
    ];
    return {
      ok: true,
      positive: {name: root ? root.name : null, structural: S.isRootCtor(root)},
      wrong: wrong.map((c) => ({name: c.name, structural: S.isRootCtor(c.ctor)})),
    };
  };

  // ---- widget creation (S1-A constructor, S1-B stock command) ----
  S.addStyle = (id, css) => {
    if (document.getElementById(id)) return;
    const s = document.createElement('style'); s.id = id; s.textContent = css; document.head.appendChild(s);
  };
  S.STYLE = '@media (min-width: 1280px) and (max-width: 1599px) { .praxis-s1-limited { min-width: 420px; max-width: 480px; } } ' +
    '.praxis-s1-widget { overflow: hidden; position: relative; } ' +
    '.praxis-s1-widget > iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }';
  S.prepare = async (a) => {
    S.addStyle('praxis-s1-style', S.STYLE);
    const nb = S.nbPanel();
    if (!nb) return {ok: false, reason: 'no notebook panel', info: {}};
    let w = null; const info = {};
    if (a.source === 'S1-A') {
      const C = S.rootCtor(nb);
      info.root_ctor_name = C ? C.name : null;
      info.structural = S.isRootCtor(C);
      if (!info.structural) return {ok: false, reason: 'root constructor failed the structural check', info};
      const node = document.createElement('div'); node.className = 'praxis-s1-widget';
      w = new C({node});
      w.id = a.id; w.title.label = 'S1 probe'; w.title.closable = true;
      info.constructed = true;
      info.is_widget_instance = (w instanceof C) && typeof w.processMessage === 'function' && typeof w.dispose === 'function' && !!w.title && w.node === node;
      if (a.iframeUrl) { const f = document.createElement('iframe'); f.src = a.iframeUrl; node.appendChild(f); }
    } else {
      const sh = S.shell(); const cmds = window.jupyterapp.commands;
      info.command_registered = cmds.hasCommand('help:open');
      if (!info.command_registered) return {ok: false, reason: 'help:open is not registered', info};
      const before = Array.from(sh.widgets('main'));
      try {
        await cmds.execute('help:open', {url: a.iframeUrl, text: 'S1 probe', newBrowserTab: false});
      } catch (e) { info.execute_error = String(e); }
      await S.settle(600);
      const created = Array.from(sh.widgets('main')).filter((x) => !before.includes(x));
      info.created_count = created.length;
      info.widget_created = created.length > 0;
      w = created.find((x) => x.node && x.node.querySelector('iframe')) || null;
      info.iframe_found = !!w;
      if (!w) return {ok: false, reason: 'help:open created no iframe widget', info};
    }
    if (a.limited) w.addClass('praxis-s1-limited');
    window.__s1w = w;
    return {ok: true, info};
  };
  S.disposeWidget = async () => {
    const w = window.__s1w;
    if (w && !w.isDisposed) w.dispose();
    window.__s1w = null;
    await S.settle(300);
    return true;
  };
  S.iframeInfo = async (waitMs) => {
    const w = window.__s1w; const f = w && w.node.querySelector('iframe');
    if (!f) return {found: false};
    const deadline = Date.now() + (waitMs || 15000);
    let readable = false;
    while (Date.now() < deadline) {
      try {
        const d = f.contentDocument;
        if (d && d.readyState === 'complete' && f.contentWindow.location.href !== 'about:blank') { readable = true; break; }
      } catch (e) { /* cross-origin or sandboxed: not readable */ }
      await sleep(200);
    }
    const attr = f.getAttribute('sandbox');
    const tokens = attr === null ? null : Array.from(f.sandbox);
    const allows = attr === null || (tokens.includes('allow-scripts') && tokens.includes('allow-same-origin'));
    return {found: true, sandbox_attr: attr, sandbox_tokens: tokens, allows_scripts_same_origin: allows, same_origin_readable: readable, src: f.src};
  };
  S.geometry = (nbBefore) => {
    const w = window.__s1w; const nb = S.nbPanel();
    const wr = rect(w.node); const nr = rect(nb.node);
    return {
      attached: w.isAttached, visible: w.isVisible, in_document: document.body.contains(w.node),
      notebook_rect_before: nbBefore, notebook_rect_after: nr, widget_rect: wr,
      side_by_side: !!(wr && nr && wr.w > 0 && nr.w > 0 && wr.left >= nr.right - 2 && Math.abs(wr.top - nr.top) < 40),
    };
  };
  S.addSplitRight = async () => {
    const w = window.__s1w; const nb = S.nbPanel();
    const before = rect(nb.node);
    S.shell().add(w, 'main', {mode: 'split-right', ref: nb.id});
    await S.settle(500);
    return S.geometry(before);
  };
  S.widgetWidth = () => { const w = window.__s1w; const r = w && rect(w.node); return r ? r.w : null; };

  // ---- DockPanel layout sizing: saveLayout -> edit sizes -> restoreLayout ----
  S.findSplit = (area, w) => {
    if (!area || area.type !== 'split-area') return null;
    for (let i = 0; i < area.children.length; i++) {
      const c = area.children[i];
      if (c.type === 'tab-area' && Array.isArray(c.widgets) && c.widgets.includes(w)) return {area, index: i};
    }
    for (const c of area.children) { const r = S.findSplit(c, w); if (r) return r; }
    return null;
  };
  S.layoutInfo = () => {
    const w = window.__s1w; const out = {dock_panel_found: false, save_layout_ok: false, split_area_found: false};
    const {dock, accessor} = S.dock(); out.dock_accessor = accessor;
    if (!dock) return out;
    out.dock_panel_found = true;
    try { const cfg = dock.saveLayout(); out.save_layout_ok = !!(cfg && cfg.main); if (out.save_layout_ok) { const f = S.findSplit(cfg.main, w); if (f) { out.split_area_found = true; out.orientation = f.area.orientation; out.sizes = Array.from(f.area.sizes); out.n_children = f.area.children.length; } } } catch (e) { out.save_error = String(e); }
    return out;
  };
  S.setSplitSizes = async (fraction) => {
    const w = window.__s1w;
    const out = {dock_panel_found: false, save_layout_ok: false, split_area_found: false, restore_called: false, restore_threw: null};
    const {dock, accessor} = S.dock(); out.dock_accessor = accessor;
    if (!dock) return out;
    out.dock_panel_found = true;
    let cfg;
    try { cfg = dock.saveLayout(); out.save_layout_ok = !!(cfg && cfg.main); } catch (e) { out.save_error = String(e); return out; }
    if (!out.save_layout_ok) return out;
    const found = S.findSplit(cfg.main, w);
    if (!found) return out;
    out.split_area_found = true;
    const n = found.area.children.length;
    out.orientation = found.area.orientation;
    out.sizes_before = Array.from(found.area.sizes);
    const rest = n > 1 ? (1 - fraction) / (n - 1) : 0;
    found.area.sizes = found.area.children.map((_, i) => (i === found.index ? fraction : rest));
    out.sizes_requested = Array.from(found.area.sizes);
    try { out.restore_called = true; dock.restoreLayout(cfg); } catch (e) { out.restore_threw = String(e); }
    await S.settle(600);
    const dw = rect(dock.node); const wr = rect(w.node);
    out.dock_width_px = dw ? dw.w : null; out.widget_width_px = wr ? wr.w : null;
    out.measured_fraction = (dw && wr && dw.w > 0) ? wr.w / dw.w : null;
    return out;
  };

  // ---- splitter handle (the real drag runs from Python with page.mouse) ----
  S.handleRect = () => {
    const {dock} = S.dock(); const w = window.__s1w;
    if (!dock || !w) return null;
    const wr = rect(w.node);
    const hs = Array.from(dock.node.querySelectorAll('.lm-DockPanel-handle'))
      .filter((h) => !h.classList.contains('lm-mod-hidden'))
      .map((h) => ({h, r: rect(h)})).filter((x) => x.r.w > 0 && x.r.h > 0);
    hs.sort((a, b) => Math.abs(a.r.x + a.r.w / 2 - wr.left) - Math.abs(b.r.x + b.r.w / 2 - wr.left));
    return hs.length ? {handle: hs[0].r, widget: wr, n_handles: hs.length, dock: rect(dock.node)} : null;
  };
  S.dockWidth = () => { const {dock} = S.dock(); const r = dock && rect(dock.node); return r ? r.w : null; };

  // ---- css_limits_refit ----
  S.applyInlineLimits = (px) => { const w = window.__s1w; w.node.style.minWidth = px + 'px'; w.node.style.maxWidth = px + 'px'; return true; };
  S.parentFit = () => {
    const w = window.__s1w; const p = w.parent; const {dock} = S.dock();
    const out = {parent_ctor: p && p.constructor ? p.constructor.name : null, fit_called: false, parent_is_dock_panel: !!(p && dock && p === dock)};
    if (p && typeof p.fit === 'function') { p.fit(); out.fit_called = true; }
    return out;
  };

  // ---- restore_layout_keeps_iframe ----
  S.iframeSetup = () => {
    const w = window.__s1w; const f = w && w.node.querySelector('iframe');
    if (!f) return {ok: false};
    const st = {loads: 0, inserted: 0};
    window.__s1_ifst = st; window.__s1_iframe = f;
    f.addEventListener('load', () => { st.loads += 1; });
    const mo = new MutationObserver((recs) => {
      for (const r of recs) for (const n of r.addedNodes) { if (n === f || (n.nodeType === 1 && n.contains(f))) st.inserted += 1; }
    });
    mo.observe(document.body, {childList: true, subtree: true});
    window.__s1_mo = mo;
    return {ok: true};
  };
  S.iframeSetToken = (t) => { try { window.__s1_iframe.contentWindow.__s1tok = t; return window.__s1_iframe.contentWindow.__s1tok === t; } catch (e) { return false; } };
  S.iframeRead = () => {
    const f = window.__s1_iframe; const st = window.__s1_ifst; let tok = null; let err = null;
    try { const v = f.contentWindow.__s1tok; tok = v === undefined ? null : v; } catch (e) { err = String(e); }
    return {loads: st.loads, inserted: st.inserted, token: tok, token_error: err, connected: f.isConnected, same_node: !!(window.__s1w && window.__s1w.node.querySelector('iframe') === f)};
  };
  S.iframeReinsert = () => { const f = window.__s1_iframe; f.parentNode.appendChild(f); return true; };

  // ---- cell state hooks ----
  S.cellSnapshot = (i) => {
    const nb = S.nbPanel(); const cell = nb.content.widgets[i];
    if (!cell) return null;
    const m = cell.model; const node = cell.node;
    const prompt = node.querySelector('.jp-InputPrompt');
    const mj = typeof m.toJSON === 'function' ? m.toJSON() : {};
    const outs = mj.outputs || [];
    const mimes = Array.from(node.querySelectorAll('[data-mime-type]')).map((e) => e.getAttribute('data-mime-type'));
    let src = null;
    try { src = m.sharedModel.getSource(); } catch (e) { src = null; }
    return {
      index: i, classes: Array.from(node.classList),
      data_attrs: Array.from(node.attributes).map((a) => a.name).filter((n) => n.startsWith('data-')),
      prompt_text: prompt ? prompt.textContent.trim() : null,
      mimes: Array.from(new Set(mimes)),
      execution_count: (m.executionCount !== undefined && m.executionCount !== null) ? m.executionCount : (mj.execution_count === undefined ? null : mj.execution_count),
      execution_state: m.executionState === undefined ? null : m.executionState,
      is_dirty: typeof m.isDirty === 'boolean' ? m.isDirty : null,
      output_types: outs.map((o) => o.output_type),
      source: src, in_document: document.body.contains(node),
    };
  };
  S.kernelStatus = () => { const nb = S.nbPanel(); return nb && nb.sessionContext && nb.sessionContext.session && nb.sessionContext.session.kernel ? nb.sessionContext.session.kernel.status : null; };
  S.runCell = (i) => {
    const nb = S.nbPanel().content;
    nb.deselectAll(); nb.activeCellIndex = i;
    const pr = window.jupyterapp.commands.execute('notebook:run-cell');
    if (pr && typeof pr.catch === 'function') pr.catch((e) => { window.__s1_runerr = String(e); });
    return true;
  };
  S.neutralize = (i) => { const nb = S.nbPanel().content; nb.deselectAll(); nb.activeCellIndex = i; return true; };
  S.setSource = (i, text) => { const nb = S.nbPanel().content; nb.widgets[i].model.sharedModel.setSource(text); return true; };
  S.cellCount = () => { const nb = S.nbPanel(); return nb ? nb.content.widgets.length : null; };

  // ---- windowing ----
  S.windowingReads = () => {
    const nb = S.nbPanel(); const c = nb && nb.content;
    const reads = {};
    try { reads.notebookConfig = c && c.notebookConfig ? c.notebookConfig.windowingMode : null; } catch (e) { reads.notebookConfig = null; }
    try { reads.content_windowingMode = c && c.windowingMode !== undefined ? c.windowingMode : null; } catch (e) { reads.content_windowingMode = null; }
    reads.dom_windowed_outer = !!(c && c.node.querySelector('.jp-WindowedPanel-outer'));
    reads.dom_windowed_window = !!(c && c.node.querySelector('.jp-WindowedPanel-window'));
    return reads;
  };
  S.winInstrument = (i) => {
    const nb = S.nbPanel().content; const cell = nb.widgets[i];
    const st = {inViewportChanged: [], messages: [], mutations_added: 0, signal_error: null};
    window.__s1_win = st; window.__s1_wincell = cell;
    try { cell.inViewportChanged.connect((_, v) => { st.inViewportChanged.push(v); }); } catch (e) { st.signal_error = String(e); }
    const orig = cell.processMessage.bind(cell);
    cell.processMessage = (msg) => { st.messages.push(msg.type); return orig(msg); };
    const mo = new MutationObserver((recs) => {
      for (const r of recs) for (const n of r.addedNodes) { if (n === cell.node || (n.nodeType === 1 && n.contains(cell.node))) st.mutations_added += 1; }
    });
    mo.observe(nb.node, {childList: true, subtree: true});
    window.__s1_winmo = mo;
    return {ok: true, in_viewport: cell.inViewport === undefined ? null : cell.inViewport, in_document: document.body.contains(cell.node)};
  };
  S.winReset = () => { const st = window.__s1_win; st.inViewportChanged = []; st.messages = []; st.mutations_added = 0; return true; };
  S.winRead = () => {
    const st = window.__s1_win; const cell = window.__s1_wincell;
    return {inViewportChanged: st.inViewportChanged.slice(), messages: st.messages.slice(), mutations_added: st.mutations_added, signal_error: st.signal_error,
      in_document: document.body.contains(cell.node), in_viewport: cell.inViewport === undefined ? null : cell.inViewport};
  };
  S.scrollNotebook = (where) => {
    const nb = S.nbPanel().content;
    const outer = nb.node.querySelector('.jp-WindowedPanel-outer');
    if (!outer) return {ok: false, reason: 'no .jp-WindowedPanel-outer'};
    outer.scrollTop = where === 'bottom' ? outer.scrollHeight : 0;
    return {ok: true, scrollTop: outer.scrollTop, scrollHeight: outer.scrollHeight};
  };

  window.__s1 = S;
  return true;
})()
"""

SAVE_JS = """async (a) => {
    try {
        await window.jupyterapp.serviceManager.contents.save(a.path, {
            type: "notebook", format: "json", content: a.content});
        return {ok: true};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""


# --------------------------------------------------------------------------- #
# Browser session (real) and probe context
# --------------------------------------------------------------------------- #


class BrowserSession:
    """Served dist + Playwright + one full-Chromium page. ``close()`` is the teardown's
    step 2: browser closed, Playwright stopped, server shut down; every failure is logged
    with ``logging.error`` and never changes the artifact's keys."""

    def __init__(self, args: argparse.Namespace, env: InputEnv) -> None:
        from playwright.sync_api import sync_playwright

        rs = repl_smoke()
        self.pageerrors: list[str] = []
        self.prefix = rs._normalize_base_path(args.base_path)
        self._stack = contextlib.ExitStack()
        self._pw: Any = None
        self._browser: Any = None
        try:
            served = self._stack.enter_context(
                rs.ServedDir(Path(args.dist), args.base_path, coi=False)
            )
            self.port = served.port
            self.origin = f"http://127.0.0.1:{served.port}"
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                executable_path=env.chrome_path,
                headless=True,
                args=rs.chromium_launch_args(offline=False),
            )
            context = self._browser.new_context(viewport=dict(VIEWPORT))
            # D16 persistence gate: the first-save modal must not block the harness.
            context.add_init_script(
                'window.localStorage.setItem("praxis-repl-persistence-ack", "browser-only");'
            )
            self.page = context.new_page()
            self.page.on("pageerror", lambda exc: self.pageerrors.append(str(exc)))
        except BaseException:
            self.close()
            raise

    @property
    def lab_url(self) -> str:
        return f"{self.origin}{self.prefix}lab/index.html"

    @property
    def iframe_url(self) -> str:
        return f"{self.origin}{self.prefix}jupyter-lite.json"

    def close(self) -> None:
        for label, fn in (
            ("browser.close", lambda: self._browser and self._browser.close()),
            ("playwright.stop", lambda: self._pw and self._pw.stop()),
            ("served dir", self._stack.close),
        ):
            try:
                fn()
            except Exception:
                LOG.exception("teardown step failed: %s", label)


@dataclasses.dataclass
class ProbeCtx:
    unit: str
    args: argparse.Namespace
    env: InputEnv
    upstream: dict[str, dict[str, Any]]
    fixture: dict[str, Any]

    @property
    def source(self) -> str | None:
        return pick_source(self.upstream.get("widget_a"), self.upstream.get("widget_b"))


def _eval(page: Any, expr: str, arg: Any = None) -> Any:
    """``page.evaluate`` of ``window.__s1.<expr>`` (a call expression body, no ``await``)."""
    return page.evaluate(f"async (a) => window.__s1.{expr}", arg)


def open_fixture_notebook(sess: Any, ctx: ProbeCtx) -> None:
    """Seed the fixture through ``contents.save`` and open it in the lab app (the
    ``run_notebook_check`` pattern: exposed ``window.jupyterapp``, Select Kernel dialog
    accepted). Does not wait for the kernel."""
    page = sess.page
    page.goto(sess.lab_url, wait_until="load", timeout=NAV_TIMEOUT_MS)
    page.wait_for_function(
        "() => !!window.jupyterapp && !!window.jupyterapp.shell", timeout=NAV_TIMEOUT_MS
    )
    page.evaluate(S1_JS)
    saved = page.evaluate(SAVE_JS, {"path": FIXTURE_NB_PATH, "content": ctx.fixture})
    if not saved.get("ok"):
        raise RuntimeError(f"could not seed the fixture notebook: {saved.get('error')!r}")
    repl_smoke()._open_existing_notebook(page, FIXTURE_NB_PATH, timeout_ms=NAV_TIMEOUT_MS)
    page.wait_for_function(
        "() => { const w = window.__s1.nbPanel(); return !!w && w.content.widgets.length > 0; }",
        timeout=NAV_TIMEOUT_MS,
    )
    _eval(page, "settle(800)")


def _prepare_args(source: str | None, sess: Any, *, limited: bool, iframe: bool, wid: str) -> dict:
    return {
        "source": source,
        "limited": limited,
        "id": wid,
        "iframeUrl": sess.iframe_url if (iframe or source == "S1-B") else None,
    }


def _wait_iframe_loads(page: Any, minimum: int, timeout_ms: float = 15_000) -> bool:
    try:
        page.wait_for_function(
            "(n) => window.__s1_ifst && window.__s1_ifst.loads >= n", arg=minimum, timeout=timeout_ms
        )
        return True
    except Exception:
        return False


def _drag_widget_to_width(page: Any, width_px: float) -> float | None:
    """Real splitter drag (page.mouse) to make the widget ``width_px`` wide; returns the
    measured width afterwards. ``None`` if no splitter handle is found."""
    geo = _eval(page, "handleRect()")
    if not geo:
        return None
    h, w = geo["handle"], geo["widget"]
    x0, y = h["x"] + h["w"] / 2, h["y"] + h["h"] / 2
    x1 = w["right"] - width_px - h["w"] / 2
    page.mouse.move(x0, y)
    page.mouse.down()
    page.mouse.move(x1, y, steps=15)
    page.mouse.up()
    _eval(page, "settle(500)")
    return _eval(page, "widgetWidth()")


# --------------------------------------------------------------------------- #
# The probes. Each returns the unit's fields; expected-negative outcomes are RETURNED as
# findings, only real failures raise (and become `error` findings in the unit).
# --------------------------------------------------------------------------- #


def probe_widget_a(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    open_fixture_notebook(sess, ctx)
    page = sess.page
    walk = _eval(page, "walkNotebook()")
    out: dict[str, Any] = {
        "structural_found": bool(walk.get("structural")),
        "chain": walk.get("chain"),
        "root_index": walk.get("root_index"),
        "root_ctor_name": walk.get("root_ctor_name"),
        "constructed_ok": False, "is_widget_instance": False,
        "attached_ok": False, "split_right_ok": False,
        "recipe": {
            "kind": "prototype_walk", "from": "notebook_panel",
            "criteria": "prototype owns processMessage and onAfterAttach, and its own prototype is Object.prototype",
            "construct": "new Ctor({node})", "add": "shell.add(w, 'main', {mode: 'split-right', ref})",
        },
        "reason": None,
    }
    if not out["structural_found"]:
        out["reason"] = "the walked root constructor failed the structural check"
        out["usable"] = False
        return out
    prep = _eval(page, "prepare(a)", _prepare_args("S1-A", sess, limited=False, iframe=False, wid="praxis-s1-widget-a"))
    info = prep.get("info") or {}
    out["constructed_ok"] = bool(info.get("constructed"))
    out["is_widget_instance"] = bool(info.get("is_widget_instance"))
    if prep.get("ok"):
        geo = _eval(page, "addSplitRight()")
        out["attached_ok"] = bool(geo["attached"] and geo["in_document"])
        out["split_right_ok"] = bool(geo["side_by_side"])
        out["geometry"] = geo
    else:
        out["reason"] = prep.get("reason")
    out["usable"] = all(
        out[k] for k in ("structural_found", "constructed_ok", "is_widget_instance", "attached_ok", "split_right_ok")
    )
    if not out["usable"] and out["reason"] is None:
        out["reason"] = "constructed but not attached side by side"
    return out


def probe_widget_b(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    open_fixture_notebook(sess, ctx)
    page = sess.page
    out: dict[str, Any] = {
        "usable": False, "command_registered": None, "widget_created": False, "iframe_found": False,
        "sandbox_attr": None, "sandbox_allows_scripts_same_origin": None,
        "same_origin_readable": None, "split_right_ok": False,
        "recipe": {"kind": "command", "id": "help:open", "args": {"text": "S1 probe", "newBrowserTab": False}},
        "reason": None,
    }
    prep = _eval(
        page, "prepare(a)",
        {"source": "S1-B", "limited": False, "id": "praxis-s1-widget-b", "iframeUrl": sess.iframe_url},
    )
    info = prep.get("info") or {}
    out["command_registered"] = info.get("command_registered")
    out["widget_created"] = bool(info.get("widget_created"))
    out["iframe_found"] = bool(info.get("iframe_found"))
    if not prep.get("ok"):
        out["reason"] = prep.get("reason")
        return out
    ifr = _eval(page, "iframeInfo(15000)")
    out["sandbox_attr"] = ifr.get("sandbox_attr")
    out["sandbox_tokens"] = ifr.get("sandbox_tokens")
    out["sandbox_allows_scripts_same_origin"] = ifr.get("allows_scripts_same_origin")
    out["same_origin_readable"] = ifr.get("same_origin_readable")
    geo = _eval(page, "addSplitRight()")
    out["split_right_ok"] = bool(geo["side_by_side"])
    out["geometry"] = geo
    out["usable"] = bool(
        out["command_registered"] and out["widget_created"] and out["iframe_found"]
        and out["sandbox_allows_scripts_same_origin"] and out["same_origin_readable"]
        and out["split_right_ok"]
    )
    if not out["usable"]:
        out["reason"] = "help:open widget failed one of: iframe sandbox, same-origin, split-right re-add"
    return out


def _no_widget(ctx: ProbeCtx, **nulls: Any) -> dict[str, Any] | None:
    """Downstream units on S1-C: nothing to measure; every field present and null."""
    if ctx.source is None:
        out: dict[str, Any] = {"widget_source": None, "reason": "S1-C: neither widget_a nor widget_b is usable"}
        out.update(nulls)
        return out
    return None


def _start_widget(sess: Any, ctx: ProbeCtx, *, limited: bool, iframe: bool, wid: str) -> dict[str, Any]:
    prep = _eval(sess.page, "prepare(a)", _prepare_args(ctx.source, sess, limited=limited, iframe=iframe, wid=wid))
    if not prep.get("ok"):
        raise RuntimeError(f"upstream said {ctx.source} is usable but prepare failed: {prep.get('reason')!r}")
    return prep


def probe_split_right(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    skip = _no_widget(
        ctx, split_right_ok=None, notebook_rect_before=None, notebook_rect_after=None,
        widget_rect=None, side_by_side=None, orientation=None,
    )
    if skip:
        return skip
    open_fixture_notebook(sess, ctx)
    _start_widget(sess, ctx, limited=False, iframe=False, wid="praxis-s1-widget-split")
    geo = _eval(sess.page, "addSplitRight()")
    lay = _eval(sess.page, "layoutInfo()")
    horizontal = lay.get("orientation") == "horizontal"
    nb_before, nb_after = geo["notebook_rect_before"], geo["notebook_rect_after"]
    ok = bool(
        geo["side_by_side"] and geo["attached"] and horizontal
        and nb_after and nb_after["w"] > 0 and nb_before and nb_after["w"] < nb_before["w"]
    )
    return {
        "widget_source": ctx.source, "split_right_ok": ok, "notebook_rect_before": nb_before,
        "notebook_rect_after": nb_after, "widget_rect": geo["widget_rect"],
        "side_by_side": geo["side_by_side"], "orientation": lay.get("orientation"),
        "layout": lay, "reason": None if ok else "not a horizontal side-by-side split",
    }


def probe_css_limits(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    skip = _no_widget(
        ctx, css_limits_honoured=None, drag_control_ok=None, control_widths=None,
        limited_widths=None, dock_width_px=None, limits_px=None, tolerance_px=None,
    )
    if skip:
        return skip
    open_fixture_notebook(sess, ctx)
    page = sess.page
    narrow, wide = DRAG_REQUEST_PX["narrow"], DRAG_REQUEST_PX["wide"]
    # Positive control: WITHOUT the CSS limits the same drags must reach ~300 and ~700 px.
    _start_widget(sess, ctx, limited=False, iframe=False, wid="praxis-s1-widget-ctl")
    _eval(page, "addSplitRight()")
    dock_w = _eval(page, "dockWidth()")
    c_narrow = _drag_widget_to_width(page, narrow)
    c_wide = _drag_widget_to_width(page, wide)
    _eval(page, "disposeWidget()")
    control_ok = bool(
        c_narrow is not None and c_wide is not None
        and abs(c_narrow - narrow) <= TOL_DRAG_CONTROL_PX and abs(c_wide - wide) <= TOL_DRAG_CONTROL_PX
    )
    # The measurement: the CSS min/max class is on the node BEFORE its first layout fit.
    _start_widget(sess, ctx, limited=True, iframe=False, wid="praxis-s1-widget-lim")
    _eval(page, "addSplitRight()")
    l_narrow = _drag_widget_to_width(page, narrow)
    l_wide = _drag_widget_to_width(page, wide)
    honoured: bool | None
    if not control_ok or l_narrow is None or l_wide is None:
        honoured = None
    else:
        honoured = bool(
            abs(l_narrow - LIMITS_PX["min"]) <= TOL_LIMIT_PX and abs(l_wide - LIMITS_PX["max"]) <= TOL_LIMIT_PX
        )
    return {
        "widget_source": ctx.source, "css_limits_honoured": honoured, "drag_control_ok": control_ok,
        "control_widths": {"narrow": c_narrow, "wide": c_wide},
        "limited_widths": {"narrow": l_narrow, "wide": l_wide},
        "dock_width_px": dock_w, "limits_px": dict(LIMITS_PX), "tolerance_px": TOL_LIMIT_PX,
        "reason": None if honoured is not None else "drag control failed or no splitter handle found",
    }


def probe_dock_layout_sizing(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    skip = _no_widget(
        ctx, dock_panel_found=None, dock_accessor=None, save_layout_ok=None, split_area_found=None,
        sizes_before=None, requested_fractions=None, measured_fractions=None, dock_width_px=None,
        restore_called=None, dock_layout_sizing_reachable=None,
    )
    if skip:
        return skip
    open_fixture_notebook(sess, ctx)
    _start_widget(sess, ctx, limited=False, iframe=False, wid="praxis-s1-widget-dock")
    _eval(sess.page, "addSplitRight()")
    requested = [0.3, 0.7]
    steps = [_eval(sess.page, "setSplitSizes(a)", f) for f in requested]
    first = steps[0]
    measured = [s.get("measured_fraction") for s in steps]
    reachable: bool | None
    if first.get("dock_panel_found") and first.get("save_layout_ok") and not first.get("split_area_found"):
        reachable = None  # the widget could not be located in the saved layout: inconclusive
        reason = "saveLayout worked but the widget was not found in a split area (inconclusive)"
    elif not (first.get("dock_panel_found") and first.get("split_area_found")):
        reachable = False
        reason = "the main DockPanel or its layout was not reachable from the shell"
    elif None in measured:
        reachable = False
        reason = "no width measured after restoreLayout"
    else:
        follows = all(abs(m - r) <= TOL_LAYOUT_FRACTION for m, r in zip(measured, requested))
        swings = (measured[1] - measured[0]) >= MIN_LAYOUT_SWING_FRACTION
        reachable = bool(follows and swings)
        reason = None if reachable else "restoreLayout ran but the widget width did not follow the edited sizes"
    return {
        "widget_source": ctx.source, "dock_panel_found": first.get("dock_panel_found"),
        "dock_accessor": first.get("dock_accessor"), "save_layout_ok": first.get("save_layout_ok"),
        "split_area_found": first.get("split_area_found"), "sizes_before": first.get("sizes_before"),
        "requested_fractions": requested, "measured_fractions": measured,
        "dock_width_px": first.get("dock_width_px"),
        "restore_called": bool(first.get("restore_called")),
        "restore_threw": [s.get("restore_threw") for s in steps],
        "dock_layout_sizing_reachable": reachable, "reason": reason,
        "tolerance_fraction": TOL_LAYOUT_FRACTION, "min_swing_fraction": MIN_LAYOUT_SWING_FRACTION,
    }


def probe_css_limits_refit(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    skip = _no_widget(
        ctx, css_limits_refit=None, baseline_width_px=None, target_width_px=None,
        width_before_fit_px=None, width_after_fit_px=None, width_after_viewport_nudge_px=None,
        fit_called=None, parent_is_dock_panel=None,
    )
    if skip:
        return skip
    open_fixture_notebook(sess, ctx)
    page = sess.page
    _start_widget(sess, ctx, limited=False, iframe=False, wid="praxis-s1-widget-refit")
    _eval(page, "addSplitRight()")
    baseline = _eval(page, "widgetWidth()")
    target = 420 if abs(baseline - 420) >= 100 else 800
    _eval(page, "applyInlineLimits(a)", target)
    _eval(page, "settle(400)")
    before_fit = _eval(page, "widgetWidth()")
    fit = _eval(page, "parentFit()")
    _eval(page, "settle(600)")
    after_fit = _eval(page, "widgetWidth()")
    # Informational only (not gating): does a window resize pick the limits up instead?
    page.set_viewport_size({"width": VIEWPORT["width"] - 1, "height": VIEWPORT["height"]})
    _eval(page, "settle(600)")
    nudge = _eval(page, "widgetWidth()")
    page.set_viewport_size(dict(VIEWPORT))
    refit = bool(fit["fit_called"] and abs(after_fit - target) <= TOL_LIMIT_PX)
    return {
        "widget_source": ctx.source, "css_limits_refit": refit, "baseline_width_px": baseline,
        "target_width_px": target, "width_before_fit_px": before_fit, "width_after_fit_px": after_fit,
        "width_after_viewport_nudge_px": nudge, "fit_called": fit["fit_called"],
        "parent_is_dock_panel": fit["parent_is_dock_panel"], "parent_ctor": fit.get("parent_ctor"),
        "applied_before_fit": abs(before_fit - target) <= TOL_LIMIT_PX, "tolerance_px": TOL_LIMIT_PX,
        "reason": None,
    }


def probe_restore_layout_keeps_iframe(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    skip = _no_widget(
        ctx, restore_layout_keeps_iframe=None, reload_control_detected=None, token_set=None,
        load_events_control=None, load_events_delta=None, token_survived=None,
        iframe_same_node=None, iframe_reinserted=None, restore_called=None,
    )
    if skip:
        return skip
    open_fixture_notebook(sess, ctx)
    page = sess.page
    _start_widget(sess, ctx, limited=False, iframe=True, wid="praxis-s1-widget-restore")
    _eval(page, "addSplitRight()")
    _eval(page, "settle(1500)")
    ready = _eval(page, "iframeInfo(15000)")
    if not ready.get("found") or not ready.get("same_origin_readable"):
        return {
            "widget_source": ctx.source, "restore_layout_keeps_iframe": None,
            "reload_control_detected": None, "token_set": False, "load_events_control": None,
            "load_events_delta": None, "token_survived": None, "iframe_same_node": None,
            "iframe_reinserted": None, "restore_called": None,
            "reason": "the iframe did not load a readable same-origin page",
        }
    _eval(page, "iframeSetup()")
    token_set = bool(_eval(page, "iframeSetToken(a)", "T1"))
    # Positive control: re-inserting the iframe MUST reload it and lose the token.
    _eval(page, "iframeReinsert()")
    _wait_iframe_loads(page, 1)
    _eval(page, "settle(1000)")
    ctl = _eval(page, "iframeRead()")
    reload_detected = bool(token_set and ctl["loads"] >= 1 and ctl["token"] is None)
    token_set = bool(_eval(page, "iframeSetToken(a)", "T2")) and token_set
    base = _eval(page, "iframeRead()")
    # The measurement: two restoreLayout() size edits, as a clamp would do.
    steps = [_eval(page, "setSplitSizes(a)", f) for f in (0.3, 0.6)]
    _eval(page, "settle(1500)")
    after = _eval(page, "iframeRead()")
    restore_called = bool(steps[0].get("restore_called"))
    delta = after["loads"] - base["loads"]
    survived = after["token"] == "T2"
    reinserted = (after["inserted"] - base["inserted"]) > 0
    keeps: bool | None
    if not restore_called:
        keeps = None
    else:
        keeps = bool(delta == 0 and survived and after["same_node"] and after["connected"] and not reinserted)
    return {
        "widget_source": ctx.source, "restore_layout_keeps_iframe": keeps,
        "reload_control_detected": reload_detected, "token_set": token_set,
        "load_events_control": ctl["loads"], "load_events_delta": delta, "token_survived": survived,
        "iframe_same_node": after["same_node"], "iframe_reinserted": reinserted,
        "restore_called": restore_called, "restore_threw": [s.get("restore_threw") for s in steps],
        "reason": None if restore_called else "the DockPanel layout was not reachable",
    }


def probe_cell_hooks(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    open_fixture_notebook(sess, ctx)
    page = sess.page
    originals = {
        s: "".join(ctx.fixture["cells"][STATE_CELL[s]]["source"]) for s in STATES
    }
    kernel_ready = True
    try:
        page.wait_for_function("() => window.__s1.kernelStatus() === 'idle'", timeout=KERNEL_WAIT_MS)
    except PlaywrightTimeoutError:
        kernel_ready = False

    def wait(expr: str, arg: Any = None) -> bool:
        try:
            page.wait_for_function(expr, arg=arg, timeout=STEP_WAIT_MS)
            return True
        except PlaywrightTimeoutError:
            return False

    if kernel_ready:
        # ran
        _eval(page, "runCell(a)", STATE_CELL["ran"])
        wait("(i) => { const s = window.__s1.cellSnapshot(i); return s.execution_count !== null && s.output_types.length > 0; }", STATE_CELL["ran"])
        # error
        _eval(page, "runCell(a)", STATE_CELL["error"])
        wait("(i) => window.__s1.cellSnapshot(i).output_types.includes('error')", STATE_CELL["error"])
        # stale: run, then edit the source afterwards
        _eval(page, "runCell(a)", STATE_CELL["stale"])
        wait("(i) => window.__s1.cellSnapshot(i).execution_count !== null", STATE_CELL["stale"])
        _eval(page, "setSource(a.i, a.text)", {"i": STATE_CELL["stale"], "text": STALE_EDIT_SOURCE})
        _eval(page, "settle(500)")
        # running (last: the kernel stays busy while the snapshots are read from the models/DOM)
        _eval(page, "runCell(a)", STATE_CELL["running"])
        wait("(i) => { const s = window.__s1.cellSnapshot(i); return (s.execution_state !== null && s.execution_state !== 'idle') || (s.prompt_text || '').includes('*'); }", STATE_CELL["running"])
        _eval(page, "settle(500)")
    _eval(page, "neutralize(a)", NEUTRAL_CELL)  # no state cell active/selected when snapshotted
    _eval(page, "settle(500)")
    snaps = {s: _eval(page, "cellSnapshot(a)", STATE_CELL[s]) for s in STATES}
    reached = {s: state_reached(s, snaps[s], originals[s]) for s in STATES}
    hooks = derive_hooks({s: snaps[s] for s in STATES if snaps[s]})
    return {
        "kernel_ready": kernel_ready, "states_reached": reached,
        "all_states_reached": all(reached.values()), "snapshots": snaps, "hooks": hooks,
        "all_states_derivable": all(hooks.get(s, {}).get("mechanism") in ("css", "model") for s in STATES),
        "n_states_with_css_hook": sum(1 for h in hooks.values() if h.get("mechanism") == "css"),
    }


def probe_windowing(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    open_fixture_notebook(sess, ctx)
    page = sess.page
    reads = _eval(page, "windowingReads()")
    mode = reads.get("notebookConfig") or reads.get("content_windowingMode")
    if not isinstance(mode, str):
        mode = "windowed-mode-unread" if reads.get("dom_windowed_outer") else "none-detected"
    count = _eval(page, "cellCount()")
    inst = _eval(page, "winInstrument(a)", 0)
    _eval(page, "winReset()")
    scrolled = _eval(page, "scrollNotebook(a)", "bottom")
    _eval(page, "settle(1500)")
    away = _eval(page, "winRead()")
    detach_observed = bool(scrolled.get("ok") and (not away["in_document"] or away["in_viewport"] is False))
    _eval(page, "winReset()")
    _eval(page, "scrollNotebook(a)", "top")
    _eval(page, "settle(1500)")
    back = _eval(page, "winRead()")
    raw = {"phase_away": away, "phase_back": back, "in_viewport_at_start": inst.get("in_viewport")}
    return {
        "windowing_mode": mode, "windowing_mode_reads": reads, "windowing_exercised": detach_observed,
        "detach_observed": detach_observed, "reattach_raw": raw,
        "reattach_signal": reattach_signal_from(back) if detach_observed else None,
        "cell_count": count,
    }


def probe_neg_wrong_ctor(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    open_fixture_notebook(sess, ctx)
    res = _eval(sess.page, "negControl()")
    if not res.get("ok"):
        raise RuntimeError(f"negative control could not run: {res.get('reason')!r}")
    positive = bool(res["positive"]["structural"])
    wrong = res["wrong"]
    return {
        "positive_control_structural_pass": positive,
        "wrong_candidates": wrong,
        "negative_control_failed_as_required": bool(
            positive and wrong and not any(c["structural"] for c in wrong)
        ),
    }


PROBES: dict[str, Callable[[Any, ProbeCtx], dict[str, Any]]] = {
    "widget_a": probe_widget_a,
    "widget_b": probe_widget_b,
    "split_right": probe_split_right,
    "css_limits": probe_css_limits,
    "dock_layout_sizing": probe_dock_layout_sizing,
    "css_limits_refit": probe_css_limits_refit,
    "restore_layout_keeps_iframe": probe_restore_layout_keeps_iframe,
    "cell_hooks": probe_cell_hooks,
    "windowing": probe_windowing,
    "neg_wrong_ctor": probe_neg_wrong_ctor,
}


def open_session(unit: str, args: argparse.Namespace, env: InputEnv) -> Any:
    return BrowserSession(args, env)


#: Replaceable seams (the plumbing tests substitute stubs; nothing in production does).
SESSION_FACTORY: Callable[[str, argparse.Namespace, InputEnv], Any] = open_session


# --------------------------------------------------------------------------- #
# Unit mode: the D17 per-unit sequence
# --------------------------------------------------------------------------- #


def _tail(text: str, limit: int = 4096) -> str:
    raw = text.encode("utf-8", "replace")
    return raw[-limit:].decode("utf-8", "replace")


def _flush_all() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            pass
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:  # pragma: no cover
            pass


def _upstream_artifacts(
    out_dir: Path, spec: UnitSpec
) -> tuple[dict[str, dict[str, Any]], dict[str, str]] | None:
    """Upstream artifacts and their sha256s, each required complete (artifact + matching
    stamp). ``None`` if any is missing or its stamp does not match: the caller exits 3
    (blocked, no stamp)."""
    found: dict[str, dict[str, Any]] = {}
    shas: dict[str, str] = {}
    for up in spec.upstream:
        paths = unit_paths(out_dir, up)
        try:
            data = paths["artifact"].read_bytes()
        except OSError:
            return None
        stamp = _read_json(paths["stamp"])
        if not isinstance(stamp, dict) or stamp.get("artifact_sha256") != sha256_bytes(data):
            return None
        try:
            found[up] = json.loads(data)
        except ValueError:
            return None
        shas[up] = sha256_bytes(data)
    return found, shas


def _sleep_forever_until_killed() -> None:  # pragma: no cover - the watchdog exits the process
    while True:
        time.sleep(1)


def run_unit_mode(args: argparse.Namespace, *, unit_timeout_s: float = UNIT_TIMEOUT_S) -> None:
    """Never returns: ends in ``os._exit`` (stamp.exit, 124 from the watchdog, or 3 blocked)."""
    spec = UNIT_BY_NAME[args.unit]
    token = unit_runner.ensure_token()  # may re-exec; a no-op under run_unit
    out_dir = Path(args.out_dir)
    paths = unit_paths(out_dir, spec.name)
    paths["artifact"].parent.mkdir(parents=True, exist_ok=True)
    started = time.time()

    def on_expire() -> None:
        _rm(paths["artifact"])
        marker = {
            "unit": spec.name, "budget_s": unit_timeout_s, "started": started, "expired": time.time(),
        }
        try:
            unit_runner.write_atomic(paths["timeout"], json.dumps(marker).encode())
        except OSError:
            pass
        unit_runner.emit_line(json.dumps({"unit": spec.name, "status": "timeout", "budget_s": unit_timeout_s}))

    watchdog = unit_runner.Watchdog(unit_timeout_s, on_expire)  # first act after ensure_token
    for key in ("stamp", "artifact", "timeout"):  # stamp first: never a stamp without its artifact
        _rm(paths[key])

    upstream_pair = _upstream_artifacts(out_dir, spec)
    if upstream_pair is None:
        LOG.error("unit %s blocked: an upstream unit is not complete; no stamp written", spec.name)
        watchdog.disarm()
        os._exit(3)
    upstream, up_files = upstream_pair

    error: dict[str, Any] | None = None
    fields: dict[str, Any] = {}
    session: Any = None
    env: InputEnv | None = None
    try:
        env = build_env(args)
        fixture = json.loads(FIXTURE_PATH.read_text())
        ctx = ProbeCtx(spec.name, args, env, upstream, fixture)
        session = SESSION_FACTORY(spec.name, args, env)
        fields = PROBES[spec.name](session, ctx)
    except Exception as exc:  # a raised probe is an `error` finding, and the unit still completes
        LOG.exception("probe %s raised", spec.name)
        error = {
            "type": type(exc).__name__, "message": str(exc)[:2000],
            "traceback_tail": _tail(traceback.format_exc()),
        }
    if env is None:  # build_env itself failed; the stamp still needs inputs (best effort)
        env = InputEnv("", "", "", "", "", "", "", getattr(args, "base_path", "/"))

    missing = [f for f in spec.required if f not in fields]
    artifact: dict[str, Any] = {"unit": spec.name, "error": error}
    for name in spec.required:
        artifact[name] = fields.get(name)
    for name, value in fields.items():
        artifact.setdefault(name, value)
    artifact.update(
        {
            "missing_fields": missing if error is None else [],
            "pageerrors": list(getattr(session, "pageerrors", []) or []),
            "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
            "viewport": dict(VIEWPORT), "started": started, "finished": time.time(),
        }
    )
    data = json.dumps(artifact, indent=1, sort_keys=True, default=str).encode()
    if not watchdog.write_result(lambda: unit_runner.write_atomic(paths["artifact"], data)):
        _sleep_forever_until_killed()

    # Bounded teardown (D16, C9-1): close browser + Playwright, kill any residual descendant.
    if session is not None:
        try:
            session.close()
        except Exception:
            LOG.exception("session close raised")
    try:
        survivors = unit_runner.kill_tree(os.getpid(), token)
        if survivors:
            LOG.error("descendants survived kill_tree: %s", survivors)
    except Exception:
        LOG.exception("kill_tree raised during teardown")
    _flush_all()

    exit_code = 0 if (error is None and not missing) else 1
    stamp = {
        "unit": spec.name,
        "inputs": compute_inputs(spec.name, env, up_files),
        "artifact_sha256": sha256_bytes(data),
        "started": started, "finished": time.time(), "exit": exit_code, "timeout_s": unit_timeout_s,
    }
    stamp_bytes = json.dumps(stamp, indent=1, sort_keys=True).encode()
    if not watchdog.commit(lambda: unit_runner.write_atomic(paths["stamp"], stamp_bytes)):
        _sleep_forever_until_killed()
    os._exit(exit_code)  # nothing runs after the stamp: no atexit, no threads, no shutdown


# --------------------------------------------------------------------------- #
# Driver mode
# --------------------------------------------------------------------------- #


def _dry_run(args: argparse.Namespace) -> int:
    plan = {
        "script": str(SCRIPT_PATH), "fixture": str(FIXTURE_PATH), "dist": str(args.dist),
        "dist_exists": Path(args.dist).is_dir(), "unit_timeout_s": UNIT_TIMEOUT_S,
        "driver_timeout_s": UNIT_TIMEOUT_S + DRIVER_EXTRA_S, "viewport": VIEWPORT,
        "units": [
            {"name": u.name, "upstream": list(u.upstream), "required_fields": list(u.required)}
            for u in UNITS
        ],
    }
    try:
        plan["chrome_path"] = str(repl_smoke().resolve_chrome_path(args.chrome_path))
    except Exception as exc:  # any failure to load repl_smoke or to find Chromium
        plan["chrome_path"] = None
        plan["chrome_error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    print(json.dumps(plan, indent=1))
    return 0


def run_driver(
    args: argparse.Namespace,
    *,
    unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float = UNIT_TIMEOUT_S,
    driver_extra_s: float = DRIVER_EXTRA_S,
    runner: Any = None,
    env: InputEnv | None = None,
) -> int:
    """Run every unit (resuming if asked), then evaluate outcomes iff all are complete.

    Exit 0: all units complete and the outcome fields were written (the sidecar's
    ``[outcomes]`` then evaluate them). Exit 3: at least one unit incomplete; no outcome is
    written. Exit 2: the environment is unusable (no dist, no chrome).
    """
    runner = runner or unit_runner
    out_dir = Path(args.out_dir)
    (out_dir / "units").mkdir(parents=True, exist_ok=True)
    if env is None:
        try:
            env = build_env(args)
        except (FileNotFoundError, RuntimeError) as exc:
            LOG.error("cannot build the input set: %s", exc)
            return 2
    prefix = unit_argv_prefix if unit_argv_prefix is not None else [sys.executable, str(SCRIPT_PATH)]

    states: dict[str, dict[str, Any]] = {}
    status: dict[str, dict[str, Any]] = {}
    reused: list[dict[str, Any]] = []
    recomputed: list[str] = []
    timed_out: list[str] = []
    blocked: list[str] = []
    stale: list[dict[str, Any]] = []

    for spec in UNITS:
        blockers = [u for u in spec.upstream if not states.get(u, {}).get("complete")]
        if blockers:
            LOG.error("unit %s blocked by incomplete upstream %s; not started", spec.name, blockers)
            blocked.append(spec.name)
            status[spec.name] = {"status": "blocked", "blocked_by": blockers}
            states[spec.name] = {"complete": False}
            continue
        up_sha = {u: states[u]["stamp"]["artifact_sha256"] for u in spec.upstream}
        inputs = compute_inputs(spec.name, env, up_sha)
        current = inspect_unit(out_dir, spec, inputs)
        if args.resume and current["reusable"]:
            LOG.info("unit %s reused (stamp valid, exit 0, no error, fields present)", spec.name)
            states[spec.name] = current
            reused.append(
                {
                    "unit": spec.name, "source": current["artifact_path"],
                    "inputs": current["stamp"]["inputs"],
                    "artifact_sha256": current["stamp"]["artifact_sha256"],
                }
            )
            status[spec.name] = {"status": "reused"}
            continue
        if args.resume and current["stamp"] is not None:
            stale.append(
                {"unit": spec.name, "mismatched": current["mismatched"], "reasons": current["reasons"]}
            )
        paths = unit_paths(out_dir, spec.name)
        for key in ("stamp", "artifact", "timeout"):
            _rm(paths[key])
        argv = prefix + [
            "--unit", spec.name, "--out-dir", str(out_dir), "--dist", str(args.dist),
            "--base-path", args.base_path,
        ]
        if env.chrome_path:
            argv += ["--chrome-path", env.chrome_path]
        LOG.info("starting unit %s (timeout %.0f s)", spec.name, unit_timeout_s + driver_extra_s)
        outcome = runner.run_unit(argv, unit_timeout_s + driver_extra_s, cwd=str(REPO_ROOT))
        after = inspect_unit(out_dir, spec, inputs)
        states[spec.name] = after
        if after["complete"]:
            if outcome.timed_out:
                LOG.warning("unit %s: run_unit timed out over a VALID stamp; the stamp governs", spec.name)
            recomputed.append(spec.name)
            status[spec.name] = {
                "status": "recomputed", "exit": after["stamp"]["exit"],
                "error": after["artifact"].get("error"),
                "artifact_path": after["artifact_path"],
                "artifact_sha256": after["stamp"]["artifact_sha256"],
                "inputs": after["stamp"]["inputs"],
            }
        else:
            marker = paths["timeout"].exists()
            if outcome.timed_out or marker or outcome.exit == 124:
                timed_out.append(spec.name)
                status[spec.name] = {"status": "timeout", "exit": outcome.exit}
            else:
                status[spec.name] = {"status": "crashed", "exit": outcome.exit, "reasons": after["reasons"]}
            LOG.error("unit %s is INCOMPLETE: %s", spec.name, status[spec.name])

    all_complete = all(states[u.name].get("complete") for u in UNITS)
    aggregate: dict[str, Any] = {
        "spike": "S1", "all_units_complete": all_complete, "outcome_evaluated": False,
        "units": status, "reused": reused, "recomputed": recomputed, "timed_out": timed_out,
        "blocked": blocked, "stale": stale,
        "incomplete": [u.name for u in UNITS if not states[u.name].get("complete")],
        "error_findings": {
            u.name: states[u.name]["artifact"]["error"]
            for u in UNITS
            if states[u.name].get("complete") and states[u.name]["artifact"].get("error") is not None
        },
        "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
        "inputs_hashed": {"script": env.script, "runner": env.runner, "harness": env.harness,
                          "dist": env.dist, "fixture": env.fixture, "chrome": env.chrome, "driver": env.driver},
    }
    exit_code = 3
    if all_complete:
        arts = {u.name: states[u.name]["artifact"] for u in UNITS}
        derived = derive_outcome_fields(arts)
        aggregate.update(derived["details"])
        aggregate["outcome_fields"] = derived["flat"]
        aggregate["outcome_evaluated"] = True
        results_path = os.environ.get("BTH_RESULTS_PATH")
        if results_path:
            unit_runner.write_atomic(results_path, json.dumps(derived["flat"], sort_keys=True).encode())
        exit_code = 0
    else:
        LOG.error("NOT evaluating outcomes: incomplete units %s", aggregate["incomplete"])
    unit_runner.write_atomic(
        out_dir / "result.json", json.dumps(aggregate, indent=1, sort_keys=True, default=str).encode()
    )
    print(json.dumps(aggregate, sort_keys=True, default=str))
    return exit_code


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", required=True, help="Output dir (units/<name>.json + stamps + result.json).")
    p.add_argument("--resume", action="store_true", help="Skip verified-complete units (D17 rule).")
    p.add_argument("--unit", choices=UNIT_NAMES, default=None, help="Unit mode: run exactly one unit.")
    p.add_argument("--dist", default=str(DEFAULT_DIST), help="Built dist to serve (lab/ entry).")
    p.add_argument("--chrome-path", default=None, help="Full Chromium executable (not headless_shell).")
    p.add_argument("--base-path", default="/", help="URL prefix the dist is served under.")
    p.add_argument("--dry-run", action="store_true", help="Print the plan; launch nothing, hash nothing.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float = UNIT_TIMEOUT_S,
    driver_extra_s: float = DRIVER_EXTRA_S,
) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.dry_run:
        return _dry_run(args)
    if args.unit:
        run_unit_mode(args, unit_timeout_s=unit_timeout_s)  # never returns
        return 1  # pragma: no cover
    return run_driver(
        args, unit_argv_prefix=unit_argv_prefix, unit_timeout_s=unit_timeout_s,
        driver_extra_s=driver_extra_s,
    )


if __name__ == "__main__":
    sys.exit(main())

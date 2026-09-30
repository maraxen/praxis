#!/usr/bin/env python3
"""Spike S2 (notebook display epic, task A2): sanitizer survivorship and the untrusted mimetype.

Pre-registered by ``scripts/spikes/260929_s2_sanitizer.bth.toml`` (committed BEFORE the first
run; NO run has happened when this file was written). Design:
``.praxia/docs/specs/260929_notebook-display-epic.md`` D1 (row S2), D2 (the mimebundle), D16
(shared unit runner, bounded teardown) and D17 (units, resume, chunking, completeness), AC-2.
Run it as::

    bth run --project-slug praxis --output-paths outputs/spikes/260929_s2 -- \
        uv run --no-sync python3 scripts/spikes/260929_s2_sanitizer.py \
        --out-dir outputs/spikes/260929_s2 --dist <dist> [--resume]

(``bth run`` has no ``--out`` option; the driver reads ``$BTH_RESULTS_PATH``.)

Two modes, one file, the same shape as the S1 driver:

* **Driver** (no ``--unit``): iterates the four D17 S2 units in table order, starts each as its
  own subprocess ``<script> --unit <name> --out-dir <dir> ...`` through
  ``unit_runner.run_unit`` (timeout = 5 min + 60 s), applies the ``--resume`` rule, and
  evaluates the sidecar's ``[outcomes]`` inputs ONLY when every unit is complete. An
  incomplete run writes no ``$BTH_RESULTS_PATH`` and exits 3, so bathos records no outcome.
  Exit 0 when all four units are complete, even if the outcome is ``invalid``.
* **Unit** (``--unit <name>``): the D17 per-unit sequence. ``ensure_token`` -> arm the
  ``Watchdog`` (5 min) -> clear own stamp/artifact/timeout marker -> probe -> write
  ``<out>/units/<name>.json`` under the watchdog lock -> bounded teardown (browser and
  Playwright closed, ``kill_tree`` over residual descendants, flush) -> commit
  ``<out>/units/<name>.stamp.json`` through ``Watchdog.commit`` -> ``os._exit(stamp.exit)``.

The four units (each its own subprocess and browser context, nothing shared):

* ``live``: the crafted bundle displayed LIVE by the kernel in a notebook executed in this
  page (trusted). Positive control: every authored element and attribute is present and
  intact; a second bundle (a ``<script>`` and an ``onclick``) is visible live, so the
  instrument can see both.
* ``crafted``: the same bundle written to the drive as a notebook JSON that was never
  executed, then opened (untrusted; this also stands for download/upload).
* ``executed_saved_reopened``: a notebook executed in the browser, saved, closed and
  reopened, then reloaded and reopened again; trust state and mimetype of each reopen.
* ``neg_script_onclick``: the negative control, its own crafted notebook holding a
  ``<script>`` element and an ``onclick`` attribute; both must be observed STRIPPED.

Measurement discipline (``~/.claude/rules/BATHOS.md``): every result is read from the notebook
model and the rendered DOM through ``page.evaluate``, never from printed console text. The
in-page API names below have never met a real JupyterLab: any read that is uncontrolled or
inconclusive (a missing model property, trust reads that disagree with each other or with the
independent ``onclick`` corroborator, a render that never appeared) maps to ``null`` and then
to the ``invalid`` outcome, never to a D1 branch claim. A probe that raises is an ``error``
finding, never a negative result.

PLR independence: nothing here imports or touches PyLabRobot. ``live`` and
``executed_saved_reopened`` need the dist's Pyodide kernel to run two ``IPython.display``
cells (a dist whose kernel bootstrap fails delays or blocks them; the probe itself never
imports PLR); ``crafted`` and ``neg_script_onclick`` never run a cell.

``--dry-run`` prints the unit table, the pre-registered fields and the authored fixture hash
without launching a browser or hashing the dist.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import html
import importlib.util
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

LOG = logging.getLogger("s2_spike")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"

#: D17 S2 row: 5 min per unit. The driver kills at this + 60 s (D16/D17). Estimates from the
#: spec, not measurements; not changed here.
UNIT_TIMEOUT_S = 5 * 60.0
DRIVER_EXTRA_S = 60.0

VIEWPORT = {"width": 1440, "height": 900}
#: Per-step waits are deliberately shorter than the unit budget so a stalled step raises (an
#: ``error`` finding, a COMPLETE unit) rather than expiring the watchdog (an incomplete unit).
NAV_TIMEOUT_MS = 60_000
KERNEL_WAIT_MS = 100_000
STEP_WAIT_MS = 30_000

PATH_CRAFTED = "s2_crafted.ipynb"
PATH_NEG = "s2_neg.ipynb"
PATH_LIVE = "s2_live.ipynb"
PATH_EXEC = "s2_exec.ipynb"

SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"


# --------------------------------------------------------------------------- #
# The authored fixture (D1 S2 row): every element and attribute the spike tests
# --------------------------------------------------------------------------- #

#: D1 S2 row elements: ``svg g path rect text title details summary table``.
SVG_TAGS = ("svg", "g", "path", "rect", "text", "title")
HTML_TAGS = ("table", "details", "summary")
TAGS = SVG_TAGS + HTML_TAGS
#: The drawing family: the elements a figure is drawn with (``title`` is a tooltip).
SVG_DRAWING_TAGS = ("svg", "g", "path", "rect", "text")

#: D1 S2 row attributes: ``fill stroke stroke-width stroke-dasharray class style role
#: aria-label tabindex data-*`` and ``viewBox``. ``data-*`` is tested with the two names D14
#: uses. The geometry attributes are authored extras (a ``path`` without ``d`` draws nothing).
D1_ATTRS = (
    "fill", "stroke", "stroke-width", "stroke-dasharray", "class", "style", "role",
    "aria-label", "tabindex", "data-*", "viewBox",
)
DATA_ATTR_NAMES = ("data-praxis-res", "data-praxis-grid")
GEOMETRY_ATTRS = ("d", "x", "y", "width", "height")
#: Attributes that make a drawing a drawing (``svg_drawing_ok`` requires every one authored on
#: every carrier). ``class``/``style``/``role``/``aria-label``/``tabindex``/``data-*`` are not
#: in it: they are the D1 branch and interaction attributes, tracked separately.
DRAWING_ATTRS = ("viewBox", "fill", "stroke", "stroke-width", "stroke-dasharray") + GEOMETRY_ATTRS

STYLE_DECLS = (("fill", "#2266aa"), ("stroke-width", "3px"), ("min-width", "120px"))
STYLE_PROPS = tuple(name for name, _ in STYLE_DECLS)
STYLE_VALUE = ";".join(f"{name}:{value}" for name, value in STYLE_DECLS)

COMMON_ATTRS: dict[str, str] = {
    "class": "s2-c",
    "style": STYLE_VALUE,
    "role": "group",
    "aria-label": "s2 probe",
    "tabindex": "0",
    "data-praxis-res": "plate_1",
    "data-praxis-grid": "8x12",
}
PAINT_ATTRS: dict[str, str] = {
    "fill": "#73A9C2",
    "stroke": "#333333",
    "stroke-width": "2",
    "stroke-dasharray": "4 2",
}

#: One carrier instance per tag, each holding every attribute that makes sense on it, so the
#: element is located by its tag name alone (never by an attribute the sanitizer may strip).
CARRIERS: dict[str, dict[str, str]] = {
    "svg": {**COMMON_ATTRS, **PAINT_ATTRS, "viewBox": "0 0 120 80"},
    "g": {**COMMON_ATTRS, **PAINT_ATTRS},
    "path": {**COMMON_ATTRS, **PAINT_ATTRS, "d": "M2 2L60 2L60 40Z"},
    "rect": {**COMMON_ATTRS, **PAINT_ATTRS, "x": "4", "y": "4", "width": "40", "height": "20"},
    "text": {**COMMON_ATTRS, "fill": "#111111", "stroke": "#eeeeee", "x": "6", "y": "60"},
    "title": {"class": "s2-c"},
    "table": dict(COMMON_ATTRS),
    "details": dict(COMMON_ATTRS),
    "summary": dict(COMMON_ATTRS),
}

SENTINEL_TEXT = "S2-SENTINEL"  # the corroborating span (carries onclick) in the main bundle
NEG_SENTINEL_TEXT = "S2-NEG-SENTINEL"
NEG_ONCLICK_TEXT = "S2-NEG-ONCLICK"
PLAIN_TEXT = "S2 probe plain-text summary: plate_1, 8 x 12"


def _attrs(tag: str) -> str:
    return "".join(f' {name}="{html.escape(value, quote=True)}"' for name, value in CARRIERS[tag].items())


def build_main_html() -> str:
    """The crafted ``text/html``: every D1 element and attribute once, plus the sentinel."""
    return (
        '<div class="s2-root">'
        f'<p>S2 probe name line <span id="s2-sentinel" onclick="void(0)">{SENTINEL_TEXT}</span></p>'
        f"<svg{_attrs('svg')}><title{_attrs('title')}>S2 title</title>"
        f"<g{_attrs('g')}><path{_attrs('path')}></path><rect{_attrs('rect')}></rect>"
        f"<text{_attrs('text')}>S2 text</text></g></svg>"
        f"<table{_attrs('table')}><tbody><tr><td>S2 ledger cell</td></tr></tbody></table>"
        f"<details{_attrs('details')}><summary{_attrs('summary')}>S2 error summary</summary>"
        "S2 traceback text</details>"
        "</div>"
    )


def build_neg_html() -> str:
    """The negative-control ``text/html``: a ``<script>`` element and an ``onclick`` attribute."""
    return (
        '<div class="s2-neg">'
        f'<p>S2 negative control <span id="s2-neg-sentinel">{NEG_SENTINEL_TEXT}</span></p>'
        "<script>window.__s2_neg_ran = 1;</script>"
        f'<div id="s2-neg-click" onclick="window.__s2_neg_click = 1">{NEG_ONCLICK_TEXT}</div>'
        "</div>"
    )


MAIN_HTML = build_main_html()
NEG_HTML = build_neg_html()
NEG_PLAIN = "S2 negative control plain-text summary"

NOTEBOOK_METADATA = {
    "kernelspec": {"display_name": "Python (Pyodide)", "language": "python", "name": "python"},
    "language_info": {"name": "python"},
}


def display_output(html_text: str, plain_text: str) -> dict[str, Any]:
    return {
        "output_type": "display_data",
        "data": {"text/html": html_text, "text/plain": plain_text},
        "metadata": {},
    }


def code_cell(cell_id: str, source: str, outputs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": list(outputs or []),
        "source": source.splitlines(True) or [source],
    }


def notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return {"cells": cells, "metadata": json.loads(json.dumps(NOTEBOOK_METADATA)), "nbformat": 4, "nbformat_minor": 5}


def display_source(html_text: str, plain_text: str) -> str:
    """Kernel source that displays the bundle as a raw mimebundle (the same dict the crafted
    notebook stores). The JSON string literal is a valid Python string literal.
    """
    payload = json.dumps({"text/html": html_text, "text/plain": plain_text})
    return (
        "import json\nfrom IPython.display import display\n"
        f"display(json.loads({json.dumps(payload)}), raw=True)\n"
    )


def crafted_notebook() -> dict[str, Any]:
    """Never executed: no execution count, and no ``trusted`` metadata anywhere."""
    return notebook([code_cell("s2-crafted-0", "# S2 crafted (never executed)\n", [display_output(MAIN_HTML, PLAIN_TEXT)])])


def neg_notebook() -> dict[str, Any]:
    return notebook([code_cell("s2-neg-0", "# S2 negative control (never executed)\n", [display_output(NEG_HTML, NEG_PLAIN)])])


def live_notebook() -> dict[str, Any]:
    return notebook(
        [
            code_cell("s2-live-0", display_source(MAIN_HTML, PLAIN_TEXT)),
            code_cell("s2-live-1", display_source(NEG_HTML, NEG_PLAIN)),
        ]
    )


def exec_notebook() -> dict[str, Any]:
    return notebook([code_cell("s2-exec-0", display_source(MAIN_HTML, PLAIN_TEXT))])


def fixtures() -> dict[str, dict[str, Any]]:
    return {
        PATH_CRAFTED: crafted_notebook(),
        PATH_NEG: neg_notebook(),
        PATH_LIVE: live_notebook(),
        PATH_EXEC: exec_notebook(),
    }


def fixture_sha256() -> str:
    """The ``fixture`` input: sha256 of the canonical JSON of the four authored notebooks and
    the carrier table. Conservative: a change to any of them recomputes every unit.
    """
    blob = json.dumps({"notebooks": fixtures(), "carriers": CARRIERS}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# The unit table (D17 S2 row) and each unit's pre-registered artifact fields
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class UnitSpec:
    name: str
    required: tuple[str, ...]


#: Every key ``derive_path_facts`` returns (all present, ``None`` when unmeasured).
FACT_KEYS = (
    "rendered", "chosen_mime", "trust_state", "trust_corroborated", "corroboration",
    "trust_reads", "corroborator_onclick", "tags_present", "attrs", "svg_state", "svg_drawing_ok",
    "svg_class_all", "svg_style_all", "svg_role_all", "svg_aria_all", "svg_data_all",
    "svg_tabindex_all", "html_class_all", "html_style_all", "html_data_all",
    "html_tabindex_all", "html_text_ok", "plain_text_ok", "interaction_data_star",
    "interaction_tabindex", "all_present_intact",
)

UNITS: tuple[UnitSpec, ...] = (
    UnitSpec(
        "live",
        (
            "path", "kernel_ready", "executed_ok", "reads", "facts", "neg_bundle_live",
            "positive_control_ok", "reason",
        ),
    ),
    UnitSpec("crafted", ("path", "file_readback", "file_ok", "read", "facts", "reason")),
    UnitSpec(
        "executed_saved_reopened",
        (
            "path", "kernel_ready", "executed_ok", "live_read", "live_trust_before_save",
            "save_method", "saved_file", "saved_file_ok", "close_ok", "reopen_close",
            "reload_reopen_method", "reopen_reload", "facts_close", "facts_reload",
            "reopen_agree", "facts", "reason",
        ),
    ),
    UnitSpec(
        "neg_script_onclick",
        (
            "path", "file_readback", "file_ok", "read", "facts", "neg",
            "negative_control_failed_as_required", "reason",
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
    return sha256_bytes(Path(path).read_bytes())


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
            f"{chrome_path} is a headless shell; S2 needs FULL Chromium (D16). Pass --chrome-path."
        )
    version = chrome_version_of(chrome_path)
    return InputEnv(
        script=sha256_file(SCRIPT_PATH),
        runner=sha256_file(RUNNER_PATH),
        harness=sha256_file(REPL_SMOKE_PATH),
        dist=unit_runner.dist_hash(args.dist),
        fixture=fixture_sha256(),
        chrome=sha256_bytes(f"{chrome_path}\n{version}".encode()),
        driver=unit_runner.driver_input(),
        base_path=args.base_path,
        chrome_path=chrome_path,
        chrome_version=version,
    )


def compute_inputs(unit: str, env: InputEnv) -> dict[str, str]:
    """The stamp's ``inputs``: script, runner, harness, dist, fixture, chrome, driver and the
    unit's arguments. No S2 unit builds on another unit's result, so there is no
    ``upstream:*`` input (the outcome, not any unit, combines them).
    """
    return {
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


def inspect_unit(out_dir: Path, spec: UnitSpec, current_inputs: dict[str, str]) -> dict[str, Any]:
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
    try:
        artifact_bytes: bytes | None = paths["artifact"].read_bytes()
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


def _attr_lookup(attrs: dict[str, str], name: str) -> tuple[bool, str | None]:
    """Attribute lookup ignoring name case (an SVG ``viewBox`` may come back ``viewbox``)."""
    lowered = {k.lower(): v for k, v in attrs.items()}
    if name.lower() in lowered:
        return True, lowered[name.lower()]
    return False, None


def style_props(value: str | None) -> list[str]:
    """Property names in an inline ``style`` value (lower-cased, in order)."""
    names: list[str] = []
    for part in (value or "").split(";"):
        if ":" in part:
            name = part.split(":", 1)[0].strip().lower()
            if name:
                names.append(name)
    return names


def _all_survive(attrs: dict[str, Any], tags: tuple[str, ...], names: tuple[str, ...]) -> bool | None:
    """True iff every authored ``(tag, name)`` among *tags* x *names* survived intact. ``None``
    when a tag was not measurable (absent) or nothing was authored.
    """
    values: list[bool] = []
    for tag in tags:
        per = attrs.get(tag)
        if per is None:
            return None
        for name in names:
            if name in CARRIERS[tag]:
                values.append(bool(per[name]["survived"]))
    return all(values) if values else None


def derive_path_facts(read: Any) -> dict[str, Any]:
    """Survivorship, chosen mimetype and trust state of ONE rendered output, from the raw
    in-page read. Every key of ``FACT_KEYS`` is present; ``None`` means unmeasured.

    ``trust_state`` is the output model's ``trusted``; it is reported only when it is
    CORROBORATED: the cell model's ``trusted`` (when readable) agrees, and either (``onclick``)
    the ``onclick`` attribute on the rendered corroborator element survived exactly when the
    output is trusted (a trusted render never sanitizes; an untrusted one strips ``onclick``),
    or (``plain_choice``, for a render that chose ``text/plain`` so no HTML exists to carry an
    ``onclick``) the model says untrusted and no rendered node carries the ``jp-mod-trusted``
    class. Uncorroborated trust is ``None`` (then ``invalid``), never a guess.
    """
    facts: dict[str, Any] = dict.fromkeys(FACT_KEYS)
    facts["tags_present"] = {}
    facts["attrs"] = {}
    if not isinstance(read, dict):
        return facts
    rendered = bool(read.get("rendered"))
    facts["rendered"] = rendered
    reads = dict(read.get("trust_reads") or {})
    facts["trust_reads"] = reads
    primary = reads.get("output_model_trusted")
    cell_model = reads.get("cell_model_trusted")
    corroborator = read.get("corroborator") or {}
    onclick = corroborator.get("onclick") if corroborator.get("found") else None
    facts["corroborator_onclick"] = onclick
    reads_consistent = isinstance(primary, bool) and (
        not isinstance(cell_model, bool) or cell_model == primary
    )
    corroboration: str | None = None
    if rendered and reads_consistent:
        if isinstance(onclick, bool) and onclick == primary:
            corroboration = "onclick"
        elif (
            read.get("chosen_mime") == "text/plain"
            and primary is False
            and not any(n.get("trusted_class") for n in (read.get("mime_nodes") or []))
        ):
            corroboration = "plain_choice"
    corroborated = corroboration is not None
    facts["corroboration"] = corroboration
    facts["trust_corroborated"] = corroborated
    facts["trust_state"] = primary if corroborated else None
    if not rendered or not read.get("root_found"):
        return facts
    mime = read.get("chosen_mime")
    facts["chosen_mime"] = mime if isinstance(mime, str) else None

    tags = read.get("tags") or {}
    present: dict[str, bool] = {}
    for tag in TAGS:
        info = tags.get(tag) or {}
        expected_ns = SVG_NS if tag in SVG_TAGS else XHTML_NS
        present[tag] = bool(info.get("present")) and info.get("ns") == expected_ns
    facts["tags_present"] = present

    attrs: dict[str, Any] = {}
    for tag, authored in CARRIERS.items():
        if not present[tag]:
            continue
        got = (tags.get(tag) or {}).get("attrs") or {}
        per: dict[str, Any] = {}
        for name, value in authored.items():
            found, actual = _attr_lookup(got, name)
            if name == "style":
                kept = style_props(actual) if found else []
                survived = found and all(p in kept for p in STYLE_PROPS)
                per[name] = {
                    "survived": survived, "altered": found and not survived, "value": actual,
                    "props_kept": [p for p in STYLE_PROPS if p in kept],
                }
            else:
                survived = found and actual == value
                per[name] = {"survived": survived, "altered": found and actual != value, "value": actual}
        attrs[tag] = per
    facts["attrs"] = attrs

    svg_flags = [present[t] for t in SVG_TAGS]
    if present["svg"]:
        state = "full" if all(svg_flags) else "partial"
    else:
        state = "partial" if any(svg_flags) else "absent"
    facts["svg_state"] = state

    facts["svg_class_all"] = _all_survive(attrs, SVG_DRAWING_TAGS, ("class",))
    facts["svg_style_all"] = _all_survive(attrs, SVG_DRAWING_TAGS, ("style",))
    facts["svg_role_all"] = _all_survive(attrs, SVG_DRAWING_TAGS, ("role",))
    facts["svg_aria_all"] = _all_survive(attrs, SVG_DRAWING_TAGS, ("aria-label",))
    facts["svg_data_all"] = _all_survive(attrs, SVG_DRAWING_TAGS, DATA_ATTR_NAMES)
    facts["svg_tabindex_all"] = _all_survive(attrs, SVG_DRAWING_TAGS, ("tabindex",))
    facts["svg_drawing_ok"] = _all_survive(attrs, SVG_DRAWING_TAGS, DRAWING_ATTRS) if state == "full" else None
    facts["html_class_all"] = _all_survive(attrs, HTML_TAGS, ("class",))
    facts["html_style_all"] = _all_survive(attrs, HTML_TAGS, ("style",))
    facts["html_data_all"] = _all_survive(attrs, HTML_TAGS, DATA_ATTR_NAMES)
    facts["html_tabindex_all"] = _all_survive(attrs, HTML_TAGS, ("tabindex",))
    facts["html_text_ok"] = all(present[t] for t in HTML_TAGS)
    facts["plain_text_ok"] = PLAIN_TEXT in str(read.get("text_content") or "")
    # Interaction (D1): hover/keyboard/click work only if data-* and tabindex survive. Measured
    # on the SVG carriers when the drawing survived, else on the HTML carriers.
    if state == "full":
        facts["interaction_data_star"], facts["interaction_tabindex"] = (
            facts["svg_data_all"], facts["svg_tabindex_all"],
        )
    else:
        facts["interaction_data_star"], facts["interaction_tabindex"] = (
            facts["html_data_all"], facts["html_tabindex_all"],
        )
    every = [bool(v["survived"]) for per in attrs.values() for v in per.values()]
    facts["all_present_intact"] = bool(all(present.values()) and len(attrs) == len(CARRIERS) and all(every))
    return facts


def untrusted_branch(facts: dict[str, Any]) -> str | None:
    """The D1 S2 branch for an UNTRUSTED output (labels: ``S2-A-prime`` is D1's S2-A')."""
    mime = facts.get("chosen_mime")
    if mime is None:
        return None
    if mime == "text/plain":
        return "S2-C" if facts.get("plain_text_ok") is True else "S2-unmapped"
    if mime != "text/html":
        return "S2-unmapped"
    state = facts.get("svg_state")
    if state == "absent":
        return "S2-B" if facts.get("html_text_ok") is True else "S2-unmapped"
    if state == "full":
        if facts.get("svg_drawing_ok") is not True:
            return "S2-unmapped"
        cls, sty = facts.get("svg_class_all"), facts.get("svg_style_all")
        if cls is True and sty is True:
            return "S2-A"
        if cls is not None and sty is not None:
            return "S2-A-prime"
        return None
    if state == "partial":
        return "S2-unmapped"
    return None


def path_branch(facts: dict[str, Any] | None, kind: str) -> str | None:
    """The D1 branch of a reopen path. ``kind`` is ``crafted`` or ``executed``. A trusted
    executed path is ``S2-T``. A trusted CRAFTED path is ``crafted-trusted`` (not a D1
    branch: the crafted premise, an untrusted reopen, does not hold in this build).
    ``None`` if trust or the mimetype is unmeasured.
    """
    if not facts or facts.get("rendered") is not True:
        return None
    trust = facts.get("trust_state")
    if trust is None:
        return None
    if trust is True:
        return "S2-T" if kind == "executed" else "crafted-trusted"
    return untrusted_branch(facts)


def derive_neg(read: Any, facts: dict[str, Any]) -> dict[str, Any]:
    """The negative control's observations. ``negative_control_failed_as_required`` needs the
    output RENDERED as ``text/html`` with both marker elements present (so "stripped" cannot
    mean "nothing rendered"), corroborated UNTRUSTED, and the ``<script>`` element and every
    ``onclick`` attribute gone. A control that errored, or that saw an unrendered or
    uncorroborated output, has NOT failed as required.
    """
    neg = (read or {}).get("neg") or {}
    rendered_ok = bool(
        facts.get("rendered")
        and facts.get("chosen_mime") == "text/html"
        and neg.get("neg_sentinel_found")
        and neg.get("onclick_div_found")
    )
    script_count = neg.get("script_count")
    onclick_count = neg.get("onclick_attr_count")
    plain_render = bool(facts.get("rendered") and facts.get("chosen_mime") == "text/plain")
    script_stripped = (script_count == 0) if (rendered_ok and isinstance(script_count, int)) else None
    onclick_stripped = (onclick_count == 0) if (rendered_ok and isinstance(onclick_count, int)) else None
    trust = facts.get("trust_state")
    stripped_both = script_stripped is True and onclick_stripped is True
    kept_both = script_stripped is False and onclick_stripped is False
    if trust is False:
        # A text/plain render (S2-C) shows no HTML at all, so nothing can be observed stripped:
        # the control is then vacuous (failed_as_required stays False) but consistent.
        consistent = stripped_both or plain_render
    elif trust is True:
        consistent = kept_both
    else:
        consistent = False
    return {
        "rendered_ok": rendered_ok,
        "plain_render": plain_render,
        "script_count": script_count,
        "onclick_attr_count": onclick_count,
        "script_stripped": script_stripped,
        "onclick_stripped": onclick_stripped,
        "script_ran": neg.get("script_ran"),
        "trust_state": trust,
        "failed_as_required": bool(rendered_ok and trust is False and stripped_both),
        "consistent_with_trust": bool(consistent),
    }


def derive_live_neg(read: Any, facts: dict[str, Any]) -> dict[str, Any]:
    """The negative bundle displayed LIVE: the instrument must be able to see both the
    ``<script>`` element and the ``onclick`` attribute when nothing sanitizes.
    """
    neg = (read or {}).get("neg") or {}
    script_count = neg.get("script_count")
    onclick_count = neg.get("onclick_attr_count")
    return {
        "rendered": bool(facts.get("rendered") and facts.get("chosen_mime") == "text/html"),
        "trust_state": facts.get("trust_state"),
        "script_present": isinstance(script_count, int) and script_count >= 1,
        "onclick_present": isinstance(onclick_count, int) and onclick_count >= 1,
        "script_ran": neg.get("script_ran"),
    }


def live_positive_control_ok(main_facts: dict[str, Any], neg_live: dict[str, Any]) -> bool:
    """The instrument can see the whole bundle: live, trusted, rendered as ``text/html``, every
    authored element and attribute present and intact, the sentinel ``onclick`` kept, and the
    negative bundle's ``<script>`` and ``onclick`` visible.
    """
    return bool(
        main_facts.get("rendered") is True
        and main_facts.get("trust_state") is True
        and main_facts.get("chosen_mime") == "text/html"
        and main_facts.get("all_present_intact") is True
        and main_facts.get("svg_state") == "full"
        and main_facts.get("corroborator_onclick") is True
        and neg_live.get("rendered") is True
        and neg_live.get("script_present") is True
        and neg_live.get("onclick_present") is True
    )


AGREE_KEYS = (
    "trust_state", "chosen_mime", "svg_state", "svg_drawing_ok", "svg_class_all", "svg_style_all",
    "svg_role_all", "svg_aria_all", "svg_data_all", "svg_tabindex_all", "html_text_ok", "plain_text_ok",
)


def merge_reopen(close: dict[str, Any], reload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Combine the close-and-reopen read with the reload-and-reopen read. The two must agree on
    trust and on every survivorship rollup, and trust must be corroborated in both; otherwise
    the merged ``trust_state`` is ``None`` (unmeasured -> ``invalid``).
    """
    agree = (
        close.get("trust_state") is not None
        and reload.get("trust_state") is not None
        and all(close.get(k) == reload.get(k) for k in AGREE_KEYS)
    )
    merged = dict(reload)
    if not agree:
        merged["trust_state"] = None
        merged["trust_corroborated"] = False
    return merged, bool(agree)


def crafted_file_ok(fr: Any, html_len: int) -> bool:
    """The crafted notebook as stored on the drive BEFORE it is opened: one output with both
    mimetypes at the authored length, never executed, and no ``trusted`` flag set.
    """
    if not isinstance(fr, dict) or fr.get("ok") is not True:
        return False
    return bool(
        fr.get("cell0_n_outputs") == 1
        and fr.get("cell0_data_keys") == ["text/html", "text/plain"]
        and fr.get("data_html_len") == html_len
        and fr.get("cell0_execution_count") is None
        and fr.get("cell0_trusted_flag") in (None, False)
        and fr.get("nb_trusted_flag") in (None, False)
        and all(flag in (None, False) for flag in (fr.get("cell0_output_trusted_flags") or []))
    )


def saved_file_ok(fr: Any) -> bool:
    """The executed notebook as saved: the display output is on the drive and the cell ran."""
    if not isinstance(fr, dict) or fr.get("ok") is not True:
        return False
    return bool(
        (fr.get("cell0_n_outputs") or 0) >= 1
        and fr.get("cell0_output_types") == ["display_data"]
        and fr.get("cell0_data_keys") == ["text/html", "text/plain"]
        and fr.get("cell0_execution_count") is not None
    )


def explain(facts: dict[str, Any]) -> str | None:
    """The first reason a path's facts are unmeasured, else ``None``."""
    if facts.get("rendered") is not True:
        return "the output never rendered (no data-mime-type node in the cell)"
    if facts.get("trust_state") is None:
        return "trust state unread or uncorroborated (model reads disagree, or the onclick corroborator does not match)"
    if facts.get("chosen_mime") is None:
        return "chosen mimetype unread"
    return None


def facts_of(artifact: dict[str, Any] | None) -> dict[str, Any]:
    facts = (artifact or {}).get("facts")
    if isinstance(facts, dict):
        return facts
    blank: dict[str, Any] = dict.fromkeys(FACT_KEYS)
    blank["tags_present"], blank["attrs"] = {}, {}
    return blank


def paths_consistent(crafted: str | None, executed: str | None) -> bool:
    """A trusted executed path (S2-T) stands on its own; an untrusted executed path must land
    on the SAME D1 branch as the crafted path (same sanitizer), else something is off.
    """
    if crafted is None or executed is None:
        return False
    if executed == "S2-T":
        return True
    return crafted == executed


def evaluate_validity(
    arts: dict[str, dict[str, Any]], crafted_branch: str | None, exec_branch: str | None
) -> dict[str, bool]:
    """Named checks whose conjunction is ``measurement_valid``. Any ``error`` finding, an
    unrendered output, uncorroborated trust, a control that did not behave as required, a
    reopen pair that disagrees, or inconsistent paths makes the run ``invalid`` (the residual
    outcome): it never satisfies a positive outcome.
    """
    live, crafted = arts["live"], arts["crafted"]
    ex, neg = arts["executed_saved_reopened"], arts["neg_script_onclick"]
    facts = {name: facts_of(arts[name]) for name in UNIT_NAMES}
    neg_obs = (neg.get("neg") or {}) if isinstance(neg.get("neg"), dict) else {}
    cf, nf = facts["crafted"], facts["neg_script_onclick"]
    return {
        "no_error_findings": all(a.get("error") is None for a in arts.values()),
        "all_rendered": all(f.get("rendered") is True for f in facts.values()),
        "trust_corroborated_all": all(f.get("trust_corroborated") is True for f in facts.values()),
        "live_executed_ok": live.get("executed_ok") is True,
        "live_trusted": facts["live"].get("trust_state") is True,
        "live_positive_control_ok": live.get("positive_control_ok") is True,
        "crafted_file_ok": crafted.get("file_ok") is True,
        "neg_file_ok": neg.get("file_ok") is True,
        "crafted_neg_trust_agree": cf.get("trust_state") is not None and cf.get("trust_state") == nf.get("trust_state"),
        "crafted_neg_mime_agree": cf.get("chosen_mime") is not None and cf.get("chosen_mime") == nf.get("chosen_mime"),
        "neg_consistent_with_trust": neg_obs.get("consistent_with_trust") is True,
        "exec_executed_and_saved": ex.get("executed_ok") is True and ex.get("saved_file_ok") is True and ex.get("close_ok") is True,
        "reopen_paths_agree": ex.get("reopen_agree") is True,
        "crafted_branch_measured": crafted_branch is not None,
        "exec_branch_measured": exec_branch is not None,
        "paths_consistent": paths_consistent(crafted_branch, exec_branch),
    }


def derive_outcome_fields(arts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The flat scalar fields the sidecar's ``[outcomes]`` conditions read, plus the
    ``details`` (validity checks, per-path branch, survivorship tables).
    """
    cf = facts_of(arts["crafted"])
    ef = facts_of(arts["executed_saved_reopened"])
    lf = facts_of(arts["live"])
    neg = arts["neg_script_onclick"].get("neg")
    neg_ok = isinstance(neg, dict) and neg.get("failed_as_required") is True
    crafted_branch = path_branch(cf, "crafted")
    exec_branch = path_branch(ef, "executed")
    validity = evaluate_validity(arts, crafted_branch, exec_branch)
    valid = all(validity.values())
    flat = {
        "all_units_complete": True,
        "n_units": len(UNITS),
        "n_error_units": sum(1 for a in arts.values() if a.get("error") is not None),
        "measurement_valid": valid,
        "negative_control_failed_as_required": neg_ok,
        "live_positive_control_ok": arts["live"].get("positive_control_ok") is True,
        "live_trusted": lf.get("trust_state"),
        "crafted_trust_state": cf.get("trust_state"),
        "crafted_chosen_mime": cf.get("chosen_mime"),
        "crafted_svg_state": cf.get("svg_state"),
        "crafted_class_survives": cf.get("svg_class_all"),
        "crafted_style_survives": cf.get("svg_style_all"),
        "crafted_data_star_survives": cf.get("interaction_data_star"),
        "crafted_tabindex_survives": cf.get("interaction_tabindex"),
        "crafted_branch": crafted_branch,
        "exec_trusted": ef.get("trust_state"),
        "exec_chosen_mime": ef.get("chosen_mime"),
        "exec_branch": exec_branch,
        "reopen_agree": arts["executed_saved_reopened"].get("reopen_agree"),
        "paths_consistent": paths_consistent(crafted_branch, exec_branch),
        "d1_branch": f"crafted={crafted_branch}; executed={exec_branch}",
    }
    details = {
        "validity_checks": validity,
        "survivorship": {
            "trusted_live": _survival_table(lf),
            "untrusted_reopened_crafted": _survival_table(cf),
            "executed_saved_reopened": _survival_table(ef),
        },
    }
    return {"flat": flat, "details": details}


def _survival_table(facts: dict[str, Any]) -> dict[str, Any]:
    """The AC-2 survivorship table for one path: element presence and, per element, each
    attribute's ``survived`` flag (``None`` for an element that is absent).
    """
    table: dict[str, Any] = {
        "trust_state": facts.get("trust_state"),
        "chosen_mime": facts.get("chosen_mime"),
        "svg_state": facts.get("svg_state"),
        "elements": dict(facts.get("tags_present") or {}),
        "attributes": {},
    }
    for tag, per in (facts.get("attrs") or {}).items():
        table["attributes"][tag] = {name: v["survived"] for name, v in per.items()}
    return table


# --------------------------------------------------------------------------- #
# The in-page probe library (installed as window.__s2; read via page.evaluate)
# --------------------------------------------------------------------------- #

S2_JS = r"""
(() => {
  if (window.__s2) return true;
  const S = {};
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const raf2 = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const boolOrNull = (v) => (typeof v === 'boolean' ? v : null);
  S.settle = async (ms) => { await raf2(); await sleep(ms === undefined ? 350 : ms); await raf2(); return true; };
  S.shell = () => window.jupyterapp.shell;

  // The notebook panel whose context path is `path` (undefined: any notebook panel).
  S.nbPanel = (path) => {
    for (const w of S.shell().widgets('main')) {
      if (!(w.node && w.node.classList.contains('jp-NotebookPanel') && w.content)) continue;
      if (path === undefined || path === null) return w;
      const p = w.context && w.context.path ? String(w.context.path) : '';
      if (p === path || p.endsWith('/' + path)) return w;
    }
    return null;
  };
  S.cell = (path, i) => {
    const nb = S.nbPanel(path);
    return nb && nb.content.widgets[i] ? nb.content.widgets[i] : null;
  };
  S.kernelStatus = (path) => {
    const nb = S.nbPanel(path);
    return nb && nb.sessionContext && nb.sessionContext.session && nb.sessionContext.session.kernel
      ? nb.sessionContext.session.kernel.status : null;
  };
  S.panelOpen = (path) => S.nbPanel(path) !== null && S.nbPanel(path).content.widgets.length > 0;
  S.dialogOpen = () => !!document.querySelector('.jp-Dialog');

  // ---- execution (dispatched, never awaited: a stuck kernel must not hang page.evaluate) ----
  S.runCell = (a) => {
    const nb = S.nbPanel(a.p);
    if (!nb) return false;
    nb.content.deselectAll();
    nb.content.activeCellIndex = a.i;
    const pr = window.jupyterapp.commands.execute('notebook:run-cell');
    if (pr && typeof pr.catch === 'function') pr.catch((e) => { window.__s2_runerr = String(e); });
    return true;
  };
  S.outputCount = (a) => {
    const c = S.cell(a.p, a.i);
    const outs = c && c.model && c.model.outputs;
    return outs && typeof outs.length === 'number' ? outs.length : null;
  };
  S.executionCount = (a) => {
    const c = S.cell(a.p, a.i);
    const v = c && c.model ? c.model.executionCount : null;
    return v === undefined ? null : v;
  };
  S.rendered = (a) => {
    const c = S.cell(a.p, a.i);
    return !!c && !!c.node.querySelector('.jp-OutputArea-output[data-mime-type], .jp-OutputArea [data-mime-type]');
  };

  // ---- the drive ----
  S.readFile = async (a) => {
    try {
      const m = await window.jupyterapp.serviceManager.contents.get(a.p, {content: true});
      const c = m.content || {};
      const cells = c.cells || [];
      const c0 = cells[0] || {};
      const outs = c0.outputs || [];
      const flag = (md) => (md && typeof md.trusted === 'boolean') ? md.trusted : null;
      const d0 = outs[0] && outs[0].data ? outs[0].data : null;
      let htmlLen = null;
      if (d0 && d0['text/html'] !== undefined) {
        const h = d0['text/html'];
        htmlLen = Array.isArray(h) ? h.join('').length : String(h).length;
      }
      return {
        ok: true, n_cells: cells.length, cell0_n_outputs: outs.length,
        cell0_output_types: outs.map((o) => o.output_type),
        cell0_data_keys: d0 ? Object.keys(d0).sort() : null, data_html_len: htmlLen,
        cell0_execution_count: c0.execution_count === undefined ? null : c0.execution_count,
        cell0_metadata_keys: Object.keys(c0.metadata || {}).sort(),
        cell0_trusted_flag: flag(c0.metadata), nb_trusted_flag: flag(c.metadata),
        cell0_output_trusted_flags: outs.map((o) => flag(o.metadata)),
      };
    } catch (e) { return {ok: false, error: String(e)}; }
  };
  S.saveContext = (a) => {
    const nb = S.nbPanel(a.p);
    if (!nb || !nb.context) return false;
    window.__s2_saveerr = null;
    try {
      Promise.resolve(nb.context.save()).catch((e) => { window.__s2_saveerr = String(e); });
    } catch (e) { window.__s2_saveerr = String(e); return false; }
    return true;
  };
  S.saveCommand = () => {
    const pr = window.jupyterapp.commands.execute('docmanager:save');
    if (pr && typeof pr.catch === 'function') pr.catch((e) => { window.__s2_saveerr = String(e); });
    return true;
  };
  S.closePanel = (a) => {
    const nb = S.nbPanel(a.p);
    if (!nb) return false;
    nb.close();
    return true;
  };

  // ---- the read: model trust reads, chosen mimetype and survivorship, all from the DOM/model ----
  S.TAGS = ['svg', 'g', 'path', 'rect', 'text', 'title', 'table', 'details', 'summary'];
  S.readOutput = (a) => {
    const out = {
      found_cell: false, rendered: false, root_found: false, selector_used: null, mime_nodes: [],
      chosen_mime: null, model: null, trust_reads: {}, corroborator: {found: false, onclick: null, kind: null},
      tags: {}, neg: {}, tag_names_seen: [], text_content: null, root_html: null,
    };
    const nb = S.nbPanel(a.p);
    if (!nb) return out;
    const cell = nb.content.widgets[a.i];
    if (!cell) return out;
    out.found_cell = true;
    const m = cell.model;
    let mj = null;
    try { mj = typeof m.toJSON === 'function' ? m.toJSON() : null; } catch (e) { mj = null; }
    const outs = m.outputs;
    const n = outs && typeof outs.length === 'number' ? outs.length : null;
    let o0 = null;
    try { o0 = n && n > 0 ? outs.get(0) : null; } catch (e) { o0 = null; }
    const jo = mj && mj.outputs ? mj.outputs : null;
    out.model = {
      n_outputs: n,
      output_types: jo ? jo.map((o) => o.output_type) : null,
      data_keys: jo && jo[0] && jo[0].data ? Object.keys(jo[0].data).sort() : null,
      execution_count: m.executionCount === undefined ? null : m.executionCount,
    };
    out.trust_reads = {
      output_model_trusted: boolOrNull(o0 ? o0.trusted : null),
      cell_model_trusted: boolOrNull(m.trusted),
      notebook_model_trusted: boolOrNull(nb.content.model ? nb.content.model.trusted : null),
      metadata_trusted: boolOrNull(mj && mj.metadata ? mj.metadata.trusted : null),
    };
    let nodes = Array.from(cell.node.querySelectorAll('.jp-OutputArea-output[data-mime-type]'));
    out.selector_used = '.jp-OutputArea-output[data-mime-type]';
    if (!nodes.length) {
      nodes = Array.from(cell.node.querySelectorAll('.jp-OutputArea [data-mime-type]'));
      out.selector_used = '.jp-OutputArea [data-mime-type]';
    }
    out.mime_nodes = nodes.map((e) => ({mime: e.getAttribute('data-mime-type'), trusted_class: e.classList.contains('jp-mod-trusted')}));
    if (!nodes.length) return out;
    out.rendered = true;
    const root = nodes[0];
    out.root_found = true;
    out.chosen_mime = root.getAttribute('data-mime-type');
    for (const tag of S.TAGS) {
      const els = Array.from(root.getElementsByTagName(tag));
      const first = els[0] || null;
      const attrs = {};
      if (first) for (const name of first.getAttributeNames()) attrs[name] = first.getAttribute(name);
      out.tags[tag] = {count: els.length, present: !!first, ns: first ? first.namespaceURI : null, attrs};
    }
    const findByText = (sel, text) => Array.from(root.querySelectorAll(sel)).find((e) => e.textContent === text) || null;
    const sentinel = findByText('span', 'S2-SENTINEL');
    const negClick = findByText('div', 'S2-NEG-ONCLICK');
    if (sentinel) out.corroborator = {found: true, onclick: sentinel.hasAttribute('onclick'), kind: 'main'};
    else if (negClick) out.corroborator = {found: true, onclick: negClick.hasAttribute('onclick'), kind: 'neg'};
    out.neg = {
      script_count: root.getElementsByTagName('script').length,
      onclick_attr_count: root.querySelectorAll('[onclick]').length,
      neg_sentinel_found: !!findByText('span', 'S2-NEG-SENTINEL'),
      onclick_div_found: !!negClick,
      script_ran: window.__s2_neg_ran === 1,
    };
    out.tag_names_seen = Array.from(new Set(Array.from(root.querySelectorAll('*')).map((e) => e.tagName.toLowerCase()))).sort();
    out.text_content = String(root.textContent || '').slice(0, 2000);
    out.root_html = String(root.innerHTML || '').slice(0, 12000);
    return out;
  };

  window.__s2 = S;
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
    with ``logging.error`` and never changes the artifact's keys.
    """

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


def _eval(page: Any, expr: str, arg: Any = None) -> Any:
    """``page.evaluate`` of ``window.__s2.<expr>`` (a call expression body, no ``await``)."""
    return page.evaluate(f"async (a) => window.__s2.{expr}", arg)


def _wait(page: Any, expr: str, arg: Any = None, timeout_ms: float = STEP_WAIT_MS) -> bool:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    try:
        page.wait_for_function(expr, arg=arg, timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def goto_lab(sess: Any) -> None:
    page = sess.page
    page.goto(sess.lab_url, wait_until="load", timeout=NAV_TIMEOUT_MS)
    _install(page)


def _install(page: Any) -> None:
    page.wait_for_function(
        "() => !!window.jupyterapp && !!window.jupyterapp.shell", timeout=NAV_TIMEOUT_MS
    )
    page.evaluate(S2_JS)


def seed_notebook(sess: Any, path: str, content: dict[str, Any]) -> None:
    saved = sess.page.evaluate(SAVE_JS, {"path": path, "content": content})
    if not saved.get("ok"):
        raise RuntimeError(f"could not seed {path!r}: {saved.get('error')!r}")


def open_notebook(sess: Any, path: str) -> None:
    """``docmanager:open`` (idempotent: an already-open document is just revealed), the Select
    Kernel dialog accepted if it appears, then wait for the panel's cells.
    """
    page = sess.page
    repl_smoke()._open_existing_notebook(page, path, timeout_ms=NAV_TIMEOUT_MS)
    if not _wait(page, "(p) => window.__s2.panelOpen(p)", path, NAV_TIMEOUT_MS):
        raise RuntimeError(f"{path!r}: no notebook panel with cells after docmanager:open")
    _eval(page, "settle(500)")


def wait_kernel_idle(sess: Any, path: str) -> bool:
    return _wait(sess.page, "(p) => window.__s2.kernelStatus(p) === 'idle'", path, KERNEL_WAIT_MS)


def run_cell_and_wait(sess: Any, path: str, index: int) -> bool:
    """Run one cell and wait for its output to be in the model with an execution count. Never
    awaits the command itself. ``False`` if no output appeared in time.
    """
    page = sess.page
    arg = {"p": path, "i": index}
    if not _eval(page, "runCell(a)", arg):
        return False
    return _wait(
        page,
        "(a) => (window.__s2.outputCount(a) || 0) >= 1 && window.__s2.executionCount(a) !== null",
        arg,
    )


def read_output(sess: Any, path: str, index: int) -> dict[str, Any]:
    """Wait (bounded) for the output to render, settle, then read model + DOM."""
    page = sess.page
    arg = {"p": path, "i": index}
    _wait(page, "(a) => window.__s2.rendered(a)", arg)
    _eval(page, "settle(600)")
    return _eval(page, "readOutput(a)", arg)


def read_file(sess: Any, path: str) -> dict[str, Any]:
    return _eval(sess.page, "readFile(a)", {"p": path})


def _probe_static(sess: Any, ctx: ProbeCtx, *, path: str, content: dict[str, Any], html_text: str) -> dict[str, Any]:
    """Seed a never-executed notebook, check it on the drive, open it, read output 0."""
    goto_lab(sess)
    seed_notebook(sess, path, content)
    file_readback = read_file(sess, path)
    file_ok = crafted_file_ok(file_readback, len(html_text))
    open_notebook(sess, path)
    read = read_output(sess, path, 0)
    facts = derive_path_facts(read)
    return {
        "path": path, "file_readback": file_readback, "file_ok": file_ok, "read": read,
        "facts": facts, "reason": explain(facts),
    }


def probe_crafted(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    return _probe_static(sess, ctx, path=PATH_CRAFTED, content=crafted_notebook(), html_text=MAIN_HTML)


def probe_neg(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    fields = _probe_static(sess, ctx, path=PATH_NEG, content=neg_notebook(), html_text=NEG_HTML)
    neg = derive_neg(fields["read"], fields["facts"])
    fields["neg"] = neg
    fields["negative_control_failed_as_required"] = neg["failed_as_required"]
    return fields


def probe_live(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    goto_lab(sess)
    seed_notebook(sess, PATH_LIVE, live_notebook())
    open_notebook(sess, PATH_LIVE)
    kernel_ready = wait_kernel_idle(sess, PATH_LIVE)
    executed = [False, False]
    reads: dict[str, Any] = {"main": None, "neg": None}
    if kernel_ready:
        for index, key in ((0, "main"), (1, "neg")):
            executed[index] = run_cell_and_wait(sess, PATH_LIVE, index)
            if executed[index]:
                reads[key] = read_output(sess, PATH_LIVE, index)
    facts = derive_path_facts(reads["main"])
    neg_live = derive_live_neg(reads["neg"], derive_path_facts(reads["neg"]))
    return {
        "path": PATH_LIVE, "kernel_ready": kernel_ready, "executed_ok": all(executed),
        "reads": reads, "facts": facts, "neg_bundle_live": neg_live,
        "positive_control_ok": live_positive_control_ok(facts, neg_live),
        "reason": explain(facts) if kernel_ready else "the kernel never became idle",
    }


def _save_and_verify(sess: Any, path: str) -> tuple[str | None, dict[str, Any]]:
    """Save through the document context (then the ``docmanager:save`` command if the file on
    the drive still lacks the output), verified by reading the FILE. Returns the method that
    produced a verified file (or ``None``) and the last file read.
    """
    page = sess.page
    last: dict[str, Any] = {}
    for method, fire in (("context.save", "saveContext(a)"), ("docmanager:save", "saveCommand()")):
        _eval(page, fire, {"p": path})
        deadline = time.time() + STEP_WAIT_MS / 2000.0
        while time.time() < deadline:
            last = read_file(sess, path)
            if saved_file_ok(last):
                return method, last
            time.sleep(0.5)
    return None, last


def _close_panel(sess: Any, path: str) -> bool:
    page = sess.page
    if not _eval(page, "closePanel(a)", {"p": path}):
        return False
    deadline = time.time() + 15.0
    while time.time() < deadline:
        if not page.evaluate("(p) => window.__s2.nbPanel(p) !== null", path):
            return True
        if page.evaluate("() => window.__s2.dialogOpen()"):
            LOG.info("a dialog blocked closing %s; accepting it", path)
            page.click(".jp-Dialog .jp-mod-accept", timeout=5000)
        time.sleep(0.5)
    return False


def probe_executed_saved_reopened(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    page = sess.page
    goto_lab(sess)
    seed_notebook(sess, PATH_EXEC, exec_notebook())
    open_notebook(sess, PATH_EXEC)
    kernel_ready = wait_kernel_idle(sess, PATH_EXEC)
    executed_ok = kernel_ready and run_cell_and_wait(sess, PATH_EXEC, 0)
    fields: dict[str, Any] = {
        "path": PATH_EXEC, "kernel_ready": kernel_ready, "executed_ok": executed_ok,
        "live_read": None, "live_trust_before_save": None, "save_method": None, "saved_file": None,
        "saved_file_ok": False, "close_ok": False, "reopen_close": None,
        "reload_reopen_method": None, "reopen_reload": None, "facts_close": None,
        "facts_reload": None, "reopen_agree": False, "facts": None, "reason": None,
    }
    if not executed_ok:
        fields["facts"] = derive_path_facts(None)
        fields["reason"] = "the kernel never became idle" if not kernel_ready else "the cell produced no output"
        return fields
    live_read = read_output(sess, PATH_EXEC, 0)
    fields["live_read"] = live_read
    fields["live_trust_before_save"] = derive_path_facts(live_read).get("trust_state")
    method, saved = _save_and_verify(sess, PATH_EXEC)
    fields.update(save_method=method, saved_file=saved, saved_file_ok=method is not None)
    if method is None:
        fields["facts"] = derive_path_facts(None)
        fields["reason"] = "the executed notebook never reached the drive with its output"
        return fields
    fields["close_ok"] = _close_panel(sess, PATH_EXEC)
    if not fields["close_ok"]:
        fields["facts"] = derive_path_facts(None)
        fields["reason"] = "the notebook panel would not close"
        return fields
    # Reopen 1: same page, panel closed, opened again from the drive.
    open_notebook(sess, PATH_EXEC)
    read_close = read_output(sess, PATH_EXEC, 0)
    fields["reopen_close"] = read_close
    facts_close = derive_path_facts(read_close)
    # Reopen 2: full page reload (fresh JS state), then the document is opened from the drive
    # (or revealed if the workspace restored it; recorded).
    page.reload(wait_until="load", timeout=NAV_TIMEOUT_MS)
    _install(page)
    page.wait_for_timeout(3000)
    restored = bool(page.evaluate("(p) => window.__s2.nbPanel(p) !== null", PATH_EXEC))
    fields["reload_reopen_method"] = "workspace_restore" if restored else "docmanager_open"
    open_notebook(sess, PATH_EXEC)
    read_reload = read_output(sess, PATH_EXEC, 0)
    fields["reopen_reload"] = read_reload
    facts_reload = derive_path_facts(read_reload)
    merged, agree = merge_reopen(facts_close, facts_reload)
    fields.update(facts_close=facts_close, facts_reload=facts_reload, reopen_agree=agree, facts=merged)
    fields["reason"] = explain(merged)
    if not agree and fields["reason"] is None:
        fields["reason"] = "the close-and-reopen and reload-and-reopen reads disagree"
    return fields


PROBES: dict[str, Callable[[Any, ProbeCtx], dict[str, Any]]] = {
    "live": probe_live,
    "crafted": probe_crafted,
    "executed_saved_reopened": probe_executed_saved_reopened,
    "neg_script_onclick": probe_neg,
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


def _sleep_forever_until_killed() -> None:  # pragma: no cover - the watchdog exits the process
    while True:
        time.sleep(1)


def run_unit_mode(args: argparse.Namespace, *, unit_timeout_s: float = UNIT_TIMEOUT_S) -> None:
    """Never returns: ends in ``os._exit`` (stamp.exit, or 124 from the watchdog)."""
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

    error: dict[str, Any] | None = None
    fields: dict[str, Any] = {}
    session: Any = None
    env: InputEnv | None = None
    try:
        env = build_env(args)
        ctx = ProbeCtx(spec.name, args, env)
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
        "inputs": compute_inputs(spec.name, env),
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
        "script": str(SCRIPT_PATH), "dist": str(args.dist), "dist_exists": Path(args.dist).is_dir(),
        "unit_timeout_s": UNIT_TIMEOUT_S, "driver_timeout_s": UNIT_TIMEOUT_S + DRIVER_EXTRA_S,
        "viewport": VIEWPORT, "fixture_sha256": fixture_sha256(),
        "notebooks": {path: len(json.dumps(nb)) for path, nb in fixtures().items()},
        "tags": list(TAGS), "d1_attrs": list(D1_ATTRS), "data_attr_names": list(DATA_ATTR_NAMES),
        "units": [{"name": u.name, "required_fields": list(u.required)} for u in UNITS],
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
    ``[outcomes]`` then evaluate them; an ``invalid`` outcome still exits 0). Exit 3: at least
    one unit incomplete; no outcome is written. Exit 2: the environment is unusable (no
    dist, no chrome).
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
    stale: list[dict[str, Any]] = []

    for spec in UNITS:
        inputs = compute_inputs(spec.name, env)
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
        "spike": "S2", "all_units_complete": all_complete, "outcome_evaluated": False,
        "units": status, "reused": reused, "recomputed": recomputed, "timed_out": timed_out,
        "stale": stale,
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

"""The ``display_check.ipynb`` fixture's cells run against REAL PyLabRobot at the 1.0.0b1 pin (B10).

Epic 260929_notebook-display-design, task B10 (backlog #5646), D16 and AC-21 .. AC-26. The
``--display-check`` units D2, D3 and D4 execute the fixture's cells in the Pyodide kernel of a built
dist, which needs a browser: that is B10b (CI, or the user). What CAN be settled here, in plain
CPython, is everything the cells' PYTHON does, because the cells were written for the kernel but do
not depend on it:

* every cell runs, in the order the harness runs it, with the state the previous cell left, and the
  error cells (E1, E2, E4, E6, the ValueError) raise exactly the class AC-22 names, so a typo in a cell
  can never show up as a mysterious browser failure;
* what the drawing cells display is what the keys assert: AC-9's ``text/plain`` for the assay, the 64 KiB
  cap, the stamp's kind and resource, the grid the keyboard keys walk (A1 holds 50 uL and A2 holds
  100 uL, which is why AC-25's ``assay A2: 50 uL`` cannot be the literal ArrowRight text here), the error
  panel headings of AC-16/AC-22;
* the 96-head error cells (#5659 browser coverage): ``p96-setup`` mounts a fresh 96 rack on the 96 head and ``e96``
  asks ``aspirate96`` for 50 uL from the assay plate, whose columns 4-12 are empty, so PLR refuses it after
  queueing 24 wells and 24 tips: the panel's heading, body, fix and residue sentence are the strings D2's
  ``error_panel_96`` / ``residue_sentence_96`` keys assert in the page;
* the state premises of AC-23: the aspirate-only cell changes what ``source`` draws and leaves the tip
  rack and the assay unchanged; the restart-proof ``redraw`` cell needs nothing the restart lost; in the
  Run All pair the marker is never reached because E1 raises.

Not settled here (browser only): what JupyterLab renders, sanitizes or marks; the shell; the IPython
kernel's own ``showtraceback`` flow (the panel is built here through ``errors.render``, the function the
installed wrapper calls); the chatterbox backend's console output in a real kernel.

``praxis_boot`` and ``praxis.display.install`` are stubbed for the boot cell (they need the kernel and
its IPython shell); the real display modules render every object. Run with
``PYTHONPATH=<PLR 1.0.0b1 source>``: the first fixture asserts the pin, so a wrong PLR fails loudly.
"""

from __future__ import annotations

import ast
import asyncio
import html
import importlib
import importlib.util
import inspect
import json
import re
import sys
import types
from pathlib import Path
from typing import Any

import pylabrobot
import pytest
from pylabrobot.resources import (
    does_tip_tracking,
    does_volume_tracking,
    set_tip_tracking,
    set_volume_tracking,
)
from pylabrobot.resources.errors import HasTipError, NoTipError, TooLittleLiquidError, TooLittleVolumeError

TESTS = Path(__file__).resolve().parent
WEB_REPL = TESTS.parent
NB_PATH = TESTS / "fixtures" / "notebooks" / "display_check.ipynb"
DISPLAY_DIR = WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
PKG = "_praxis_display_check_fixture_under_test"

ASSAY_PLAIN = "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."
SOURCE_PLAIN = "All 96 wells hold liquid, 50–200 µL. 16,800 µL in the plate."
HEADINGS = {
    "e1": "Not enough liquid in assay A1:H1.",
    "e2": "Not enough room in assay A2.",
    "e4": "Channel 0 already holds a tip.",
    "e6": "Channel 0 has no tip.",
}
RAISES = {"e1": TooLittleLiquidError, "e2": TooLittleVolumeError, "e4": HasTipError, "e6": NoTipError}
CAP = 65_536

# The 96-head panel the ``e96`` cell produces. Read off the real panel by running the D2 cells in order in CPython
# (the same ``errors.render`` the installed wrapper calls), then pinned here AND derived below from the world, so a
# change in either the cells or the display layer fails a named test instead of a 12-minute browser run.
E96_HEADING = "Not enough liquid in assay A4:H12."
E96_BODY = "Each well holds 0 µL; the aspirate asked for 50 µL on every channel. Nothing was aspirated."
E96_FIX = "Lower `volume` to 0 µL or less, or aspirate from wells that hold more."
E96_RESIDUE = (
    "PyLabRobot still records moves that did not happen on assay A1:H3 and 24 tips on the 96 head; the next step "
    "that succeeds will save them, and the tracked state will be wrong from then on. "
    "The drawing shows what was actually done."
)


@pytest.fixture(scope="module", autouse=True)
def _plr_is_the_pin():
    version = str(getattr(pylabrobot, "__version__", ""))
    assert version.startswith("1.0.0b1"), (
        f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
        "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )


def _load_display() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        PKG, DISPLAY_DIR / "__init__.py", submodule_search_locations=[str(DISPLAY_DIR)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[PKG] = module
    spec.loader.exec_module(module)
    return module


def _cells() -> dict[str, str]:
    nb = json.loads(NB_PATH.read_text())
    return {c["id"]: "".join(c["source"]) for c in nb["cells"]}


async def run_cell(src: str, ns: dict[str, Any]) -> Any:
    """Run a cell the way the kernel does: top-level ``await`` allowed, and the value of a trailing
    expression is returned (what IPython would display)."""
    tree = ast.parse(src, mode="exec")
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)
        ast.fix_missing_locations(last)
    code = compile(tree, "<cell>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    result = eval(code, ns)
    if inspect.isawaitable(result):
        await result
    if last is None:
        return None
    value = eval(compile(last, "<cell>", "eval", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), ns)
    if inspect.isawaitable(value):
        value = await value
    return value


class Boot:
    """The stubs the boot cell needs: the bootstrap's once-guarded setup and ``praxis.display.install``."""

    def __init__(self) -> None:
        self.setups = 0
        self.installs = 0
        boot = types.ModuleType("praxis_boot")

        async def setup() -> None:
            self.setups += 1

        boot.setup = setup  # type: ignore[attr-defined]
        display = types.ModuleType("praxis.display")

        def install() -> object:
            self.installs += 1
            return types.SimpleNamespace(session_id="stub", carrier="mimebundle")

        display.install = install  # type: ignore[attr-defined]
        praxis = types.ModuleType("praxis")
        praxis.display = display  # type: ignore[attr-defined]
        praxis.__path__ = []  # type: ignore[attr-defined]
        self.modules = {"praxis_boot": boot, "praxis": praxis, "praxis.display": display}

    def __enter__(self) -> Boot:
        self._saved = {k: sys.modules.get(k) for k in self.modules}
        sys.modules.update(self.modules)
        return self

    def __exit__(self, *exc: Any) -> None:
        for name, old in self._saved.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def _grid_of(doc: str, name: str) -> dict[str, Any]:
    for raw in re.findall(r'data-praxis-grid="([^"]*)"', doc):
        grid = json.loads(html.unescape(raw))
        if grid.get("res") == name:
            return grid
    raise AssertionError(f"no data-praxis-grid for {name!r}")


def _title_of(doc: str) -> str:
    m = re.search(r'<p class="praxis-error__title">(.*?)</p>', doc, re.S)
    assert m, "no error panel heading"
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))


class World:
    """One kernel: a namespace, the cells run in it, what each drew, what each raised."""

    def __init__(self, display: types.ModuleType, cells: dict[str, str]) -> None:
        self.display, self.cells = display, cells
        self.ns: dict[str, Any] = {}
        self.ran: list[str] = []
        self.values: dict[str, Any] = {}
        self.raised: dict[str, BaseException] = {}
        self.boot = Boot()

    async def run(self, cid: str, *, expect_error: bool = False) -> None:
        self.ran.append(cid)
        try:
            with self.boot:
                self.values[cid] = await run_cell(self.cells[cid], self.ns)
        except Exception as exc:  # the shell would show it; the harness reads the error output
            if not expect_error:
                raise AssertionError(f"cell {cid!r} raised {type(exc).__name__}: {exc}") from exc
            self.raised[cid] = exc
            return
        if expect_error:
            raise AssertionError(f"cell {cid!r} was expected to raise and did not")

    def render(self, obj: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.display.render(obj)


async def _main(display: types.ModuleType, cells: dict[str, str]) -> dict[str, Any]:
    w = World(display, cells)
    out: dict[str, Any] = {"world": w}
    for cid in ("boot", "assemble", "transfers", "pickup"):
        await w.run(cid)
    out["boot_calls"] = (w.boot.setups, w.boot.installs)
    ns = w.ns
    vol = lambda plate, well: plate.get_item(well).tracker.volume  # noqa: E731
    out["after_pickup"] = {
        "assay": {k: vol(ns["assay"], k) for k in ("A1", "A2", "A3", "A4")},
        "source": {k: vol(ns["source"], k) for k in ("A1", "A2", "A3", "A4", "A12")},
        "head_has_tip": [ns["lh"].head[c].has_tip for c in range(8)],
        "tip_spots": {k: ns["tips"].get_item(k).tip is not None for k in ("A1", "A3", "A4", "A5")},
    }
    drawn: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for cid in ("draw-source", "draw-assay", "draw-tips", "draw-deck"):
        await w.run(cid)
        drawn[cid] = w.render(w.values[cid])
    out["drawn"] = drawn
    # the aspirate-only cell: re-render everything and compare
    before = {n: w.render(w.ns[n])[0]["text/html"] for n in ("source", "assay", "tips", "deck")}
    await w.run("aspirate")
    after = {n: w.render(w.ns[n])[0]["text/html"] for n in ("source", "assay", "tips", "deck")}
    out["before"], out["after"] = before, after
    errors_mod = importlib.import_module(f"{PKG}.errors")
    panels: dict[str, str] = {}
    for cid in ("e1", "e2", "e4", "e6"):
        await w.run(cid, expect_error=True)
        exc = w.raised[cid]
        data, _meta = errors_mod.render(exc, exc.__traceback__, session="s", exec_count=1)
        panels[cid] = data["text/html"]
    out["panels"] = panels
    await w.run("value-error", expect_error=True)
    out["value_error_handled"] = errors_mod._is_handled(w.raised["value-error"])
    # the 96-head cells: a fresh full rack on the 96 head, then the refused aspirate96 (after the plain ValueError)
    await w.run("p96-setup")
    ns = w.ns
    out["after_p96_setup"] = {
        "rack_on_carrier_site_1": ns["tip_car"].sites[1].resource is ns["tips_96"],
        "rack_spots_left": sum(1 for spot in ns["tips_96"].get_all_items() if spot.tip is not None),
        "head96_committed_tips": sum(1 for c in range(96) if ns["lh"].head96[c].has_tip),
        "assay_empty_wells": sorted(wl.get_identifier() for wl in ns["assay"].get_all_items() if wl.tracker.volume < 50),
    }
    await w.run("e96", expect_error=True)
    exc96 = w.raised["e96"]
    data96, meta96 = errors_mod.render(exc96, exc96.__traceback__, session="s", exec_count=1)
    out["panel96"], out["meta96"] = data96, meta96
    out["after_e96"] = {
        "assay_pending_differs": sorted(
            wl.get_identifier() for wl in ns["assay"].get_all_items() if wl.tracker.pending_volume != wl.tracker.volume
        ),
        "head96_pending_tip_volume_differs": sum(
            1
            for c in range(96)
            if ns["lh"].head96[c].get_tip().tracker.pending_volume != ns["lh"].head96[c].get_tip().tracker.volume
        ),
    }
    # a control for the cell above: the same op on the SOURCE plate (full everywhere) is NOT refused, so the
    # refusal is the assay's empty columns and not something the 96 op does anyway
    w_ok = World(display, cells)
    for cid in ("boot", "assemble", "transfers", "pickup", "p96-setup"):
        await w_ok.run(cid)
    await w_ok.ns["lh"].aspirate96(w_ok.ns["source"], volume=50.0)
    out["source_aspirate96_ok"] = True
    # the restart: a fresh kernel, the boot cell again, then the self-contained drawing cell
    set_tip_tracking(False)
    set_volume_tracking(False)  # a fresh kernel's defaults: the redraw cell must not depend on tracking
    w2 = World(display, cells)
    await w2.run("boot")
    await w2.run("redraw")
    out["redraw"] = w2.render(w2.values["redraw"])
    out["w2"] = w2
    # the Run All pair, in its own kernel: cells run in order and stop at the first error
    w3 = World(display, cells)
    for cid in ("assemble", "transfers", "pickup", "e1", "marker"):
        try:
            await w3.run(cid, expect_error=(cid == "e1"))
        except AssertionError:
            raise
        if cid in w3.raised:
            break  # Run All stops here: the marker cell is never reached
    out["w3"] = w3
    return out


@pytest.fixture(scope="module")
def replay():
    tip, vol = does_tip_tracking(), does_volume_tracking()
    try:
        display = _load_display()
        return asyncio.run(_main(display, _cells()))
    finally:
        set_tip_tracking(tip)
        set_volume_tracking(vol)


# --------------------------------------------------------------------------- #
# The setup cells and the boot cell
# --------------------------------------------------------------------------- #


def test_the_boot_cell_awaits_the_bootstrap_and_installs_the_display_once(replay):
    assert replay["boot_calls"] == (1, 1)


def test_the_setup_cells_leave_the_world_the_error_cells_and_ac9_assume(replay):
    got = replay["after_pickup"]
    assert got["assay"] == {"A1": 50.0, "A2": 100.0, "A3": 150.0, "A4": 0}, "three column transfers: AC-9's 24 wells"
    assert got["source"] == {"A1": 150.0, "A2": 100.0, "A3": 50.0, "A4": 200.0, "A12": 200.0}
    assert got["head_has_tip"] == [True] * 8, "the pickup cell mounted a tip on every channel (E1, E2 and E4 need them)"
    assert got["tip_spots"] == {"A1": False, "A3": False, "A4": False, "A5": True}, "columns 1-4 are gone"


# --------------------------------------------------------------------------- #
# AC-21: what the drawing cells display
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "cid,kind,resource",
    [("draw-source", "plate", "source"), ("draw-assay", "plate", "assay"), ("draw-tips", "tiprack", "tips_300"),
     ("draw-deck", "deck", "deck")],
)
def test_every_drawing_cell_displays_a_stamped_html_and_plain_bundle_under_the_cap(replay, cid, kind, resource):
    data, meta = replay["drawn"][cid]
    assert set(data) == {"text/html", "text/plain"} and "<svg" in data["text/html"]
    assert len(data["text/html"].encode("utf-8")) <= CAP
    st = meta["praxis"]
    assert (st["v"], st["kind"], st["resource"]) == (1, kind, resource)
    assert isinstance(st["rev"], int) and isinstance(st["session"], str) and st["session"]
    assert "<script" not in data["text/html"].lower()


def test_the_assay_text_plain_is_ac9s_string_and_the_source_the_fixtures(replay):
    assert replay["drawn"]["draw-assay"][0]["text/plain"] == ASSAY_PLAIN
    assert replay["drawn"]["draw-source"][0]["text/plain"] == SOURCE_PLAIN


def test_the_tip_rack_is_drawn_after_the_pickup_so_the_aspirate_only_cell_cannot_change_it(replay):
    assert replay["drawn"]["draw-tips"][0]["text/plain"].startswith("64 of 96 tips left")


# --------------------------------------------------------------------------- #
# AC-25: the grid the keyboard keys walk
# --------------------------------------------------------------------------- #


def test_the_assay_grid_starts_at_a1_and_a2_is_100_not_50(replay):
    doc = replay["drawn"]["draw-assay"][0]["text/html"]
    grid = _grid_of(doc, "assay")
    vals = dict(zip(grid["ids"].split(" "), grid["vals"]))
    assert grid["ids"].split(" ")[0] == "A1" and vals["A1"] == 50 and vals["A2"] == 100 and vals["A3"] == 150
    assert (grid["rows"], grid["cols"]) == (8, 12)


def test_the_figure_group_carries_role_img_tabindex_and_the_sentence_as_its_aria_label(replay):
    doc = replay["drawn"]["draw-assay"][0]["text/html"]
    m = re.search(r'<g [^>]*data-praxis-res="assay"[^>]*>', doc)
    assert m, "the resource group"
    tag = html.unescape(m.group(0))
    assert 'role="img"' in tag and 'tabindex="0"' in tag and f'aria-label="{ASSAY_PLAIN}"' in tag


# --------------------------------------------------------------------------- #
# AC-23: the state premises
# --------------------------------------------------------------------------- #


def test_the_aspirate_only_cell_changes_the_source_and_leaves_the_tip_rack_and_the_assay_alone(replay):
    before, after = replay["before"], replay["after"]
    assert before["source"] != after["source"], "the source drew a different volume: a 'Changed since' candidate"
    assert before["tips"] == after["tips"], "unchanged_not_marked reads this output"
    assert before["assay"] == after["assay"]


# --------------------------------------------------------------------------- #
# AC-22: the error cells
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("cid", ["e1", "e2", "e4", "e6"])
def test_each_error_cell_raises_the_class_ac22_names_and_gets_the_ac16_heading(replay, cid):
    w = replay["world"]
    assert type(w.raised[cid]) is RAISES[cid], type(w.raised[cid])
    assert _title_of(replay["panels"][cid]) == HEADINGS[cid]


def test_the_value_error_cell_is_not_one_of_the_four_handled_classes(replay):
    w = replay["world"]
    assert type(w.raised["value-error"]) is ValueError and replay["value_error_handled"] is False


def test_the_error_cells_ran_in_the_harness_order(replay):
    ran = replay["world"].ran
    order = ["boot", "assemble", "transfers", "pickup", "draw-source", "draw-assay", "draw-tips", "draw-deck",
             "aspirate", "e1", "e2", "e4", "e6", "value-error", "p96-setup", "e96"]
    assert ran == order


# --------------------------------------------------------------------------- #
# The restart-proof drawing cell and the Run All pair
# --------------------------------------------------------------------------- #


def test_the_redraw_cell_needs_nothing_the_restart_lost(replay):
    data, meta = replay["redraw"]
    assert meta["praxis"]["kind"] == "plate" and meta["praxis"]["resource"] == "redraw" and "<svg" in data["text/html"]
    w2 = replay["w2"]
    assert "lh" not in w2.ns and "deck" not in w2.ns, "the fresh kernel really has no deck"


def test_in_the_run_all_pair_e1_raises_and_the_marker_is_never_reached(replay):
    w3 = replay["w3"]
    assert w3.ran == ["assemble", "transfers", "pickup", "e1"], "Run All stops at the first error"
    assert type(w3.raised["e1"]) is TooLittleLiquidError
    assert "marker" not in w3.ran


# --------------------------------------------------------------------------- #
# The 96-head cells (#5659 browser coverage): the panel D2's error_panel_96 / residue_sentence_96 keys read
# --------------------------------------------------------------------------- #


def test_the_96_setup_cell_puts_a_fresh_full_rack_on_the_carriers_second_site_and_mounts_it(replay):
    got = replay["after_p96_setup"]
    assert got["rack_on_carrier_site_1"] is True
    assert got["rack_spots_left"] == 0, "pick_up_tips96 took all 96 tips from the new rack"
    assert got["head96_committed_tips"] == 96, "the 96 head holds a committed tip on every channel"


def test_the_assay_plate_is_short_exactly_from_column_4_on_so_the_refusal_comes_after_24_wells(replay):
    got = replay["after_p96_setup"]["assay_empty_wells"]
    assert got == sorted(f"{r}{c}" for c in range(4, 13) for r in "ABCDEFGH")


def test_the_e96_cell_is_refused_by_pylabrobot_as_too_little_liquid_and_the_op_is_not_the_cause(replay):
    w = replay["world"]
    assert type(w.raised["e96"]) is TooLittleLiquidError
    assert replay["source_aspirate96_ok"] is True, "the same aspirate96 from the full source plate is accepted"


def test_the_96_panel_heading_body_and_fix_are_the_strings_the_browser_key_asserts(replay):
    doc = replay["panel96"]["text/html"]
    assert _title_of(doc) == E96_HEADING
    plain = replay["panel96"]["text/plain"].split("\n")
    assert plain[:3] == [E96_HEADING, E96_BODY, E96_FIX]
    summaries = [html.unescape(m) for m in re.findall(r'<p class="praxis-summary">(.*?)</p>', doc, re.S)]
    assert [re.sub(r"<[^>]+>", "", s_) for s_ in summaries] == [E96_BODY, E96_FIX]


def test_the_heading_names_the_plate_and_the_wells_the_head_found_empty(replay):
    empty = replay["after_p96_setup"]["assay_empty_wells"]
    compress = importlib.import_module(f"{PKG}.labware").compress_wells
    assert E96_HEADING == f"Not enough liquid in assay {compress(empty)}."
    assert replay["world"].ns["assay"].name == "assay"


def test_the_residue_sentence_is_one_div_after_the_fix_and_before_pylabrobots_line(replay):
    doc, plain = replay["panel96"]["text/html"], replay["panel96"]["text/plain"].split("\n")
    notes = [html.unescape(m) for m in re.findall(r'<div class="praxis-summary">(.*?)</div>', doc, re.S)]
    assert notes == [E96_RESIDUE]
    assert plain[3] == E96_RESIDUE and plain[4].startswith("PyLabRobot raised TooLittleLiquidError:")
    assert doc.index(html.escape(E96_FIX, quote=False)) < doc.index("PyLabRobot still records") < doc.index("praxis-error__plr")


def test_the_residue_sentence_numbers_are_the_worlds_pending_state_not_a_guess(replay):
    got = replay["after_e96"]
    assert got["assay_pending_differs"] == sorted(f"{r}{c}" for c in (1, 2, 3) for r in "ABCDEFGH"), "A1:H3"
    assert got["head96_pending_tip_volume_differs"] == 24, "the 24 tips whose aspirate was queued before the refusal"
    assert "assay A1:H3 and 24 tips on the 96 head" in E96_RESIDUE


def test_the_96_panel_is_stamped_as_an_error_on_the_assay(replay):
    assert replay["meta96"] == {"praxis": {"v": 1, "kind": "error", "resource": "assay", "rev": None, "session": "s", "exec": 1}}


@pytest.mark.parametrize("cid", ["e1", "e2", "e4", "e6"])
def test_the_one_channel_error_panels_never_carry_the_residue_sentence(replay, cid):
    doc = replay["panels"][cid]
    assert "still records" not in doc and '<div class="praxis-summary">' not in doc

"""No-browser checks for the DISPOSABLE K2 first-drag spike (epic 260929_notebook-display-design, C7a round 4).

``scripts/spikes/260930_k2_first_drag_probe.py`` sends ONE real drag of the splitter in a fresh 1280x800 page, in one of five
variants (``burst``, ``paced``, ``small_first``, ``backdrop_wait``, ``pointer_events_none``), through the harness's own drag
routine, so that the evidence it records is the evidence K2 records. Nothing here launches a browser: the variants' mouse and wait
sequences are checked against a recording fake page (the same kind of fake the harness tests use), and the run plumbing (the open
sequence, the result file, the stamp, the reuse rule, the timeout) against a recording fake driver.

The spike is not bathos-staged, is not part of ``repl.yml`` and is imported by nothing; the last tests pin that.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPIKE_PATH = REPO_ROOT / "scripts" / "spikes" / "260930_k2_first_drag_probe.py"

pytestmark = pytest.mark.timeout(120)


def _load(path: Path, prefix: str) -> Any:
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def spike() -> Any:
    return _load(SPIKE_PATH, "k2_first_drag_probe_under_test")


@pytest.fixture(scope="module")
def rs(spike: Any) -> Any:
    return spike.rs


def _rect(left: float, width: float, top: float = 0.0, height: float = 600.0) -> dict[str, float]:
    return {"left": left, "top": top, "width": width, "height": height, "right": left + width, "bottom": top + height}


class SpikeFakePage:
    """A Playwright-page stand-in that records every mouse call, wait and page helper IN ORDER (``log``)."""

    def __init__(self, spike: Any, *, panel: float = 473.5) -> None:
        self.spike = spike
        self.panel = panel
        self.log: list[tuple[Any, ...]] = []
        self.sample_calls = 0
        self.ready_after = 0  # sampleNow reports the backdrop from this call on (0: from the first)
        self.iframe_pe = ""
        self.up_raises = False
        self.mouse = self

    # -- page.mouse
    def move(self, x: float, y: float, steps: int | None = None) -> None:
        self.log.append(("move", x, y) if not steps else ("move", x, y, steps))

    def down(self) -> None:
        self.log.append(("down",))

    def up(self) -> None:
        self.log.append(("up",))
        if self.up_raises:
            raise RuntimeError("the page closed under the mouse")

    def wait_for_timeout(self, ms: float) -> None:
        self.log.append(("wait", ms))

    # -- page.evaluate
    def evaluate(self, expr: str, arg: Any = None) -> Any:
        if expr == self.spike.SET_POINTER_EVENTS_JS:
            self.log.append(("pe_set", arg))
            previous, self.iframe_pe = self.iframe_pe, arg
            return {"ok": True, "previous": previous}
        if expr == self.spike.RESTORE_POINTER_EVENTS_JS:
            self.log.append(("pe_restore", arg))
            self.iframe_pe = arg
            return {"ok": True, "value": arg}
        if "paceFrames(" in expr:
            self.log.append(("frames", arg["n"]))
            return {"frames": arg["n"], "capped": False, "ms": 16.0 * arg["n"]}
        if "sampleNow(" in expr:
            self.sample_calls += 1
            self.log.append(("sample", self.sample_calls))
            up = self.sample_calls > self.ready_after
            return {"t": float(self.sample_calls), "backdrop_count": 1 if up else 0, "first_move": {"is_backdrop": up, "element": None}}
        if "handleRect(" in expr:
            left = 1242.5 - self.panel - 6.0
            return {"handle": _rect(left, 6.0, top=100.0, height=400.0), "widget": _rect(left + 6.0, self.panel, top=50.0), "n_handles": 1}
        if "pointsAt(" in expr:
            return {"points": [{"x": x, "y": y, "element": None} for x, y in arg["points"]], "active_element": None}
        if "dockProbe(" in expr:
            return {"sizes": [], "sizers": None, "optimize_resize": None, "resize_drag_active": None, "frozen_groups": None, "inline": {}}
        if "mouseTrace(" in expr:
            return [] if arg["op"] != "start" else True
        if "pressSamples(" in expr:
            self.log.append(("press_samples", arg["op"]))
            return True if arg["op"] == "arm" else {"samples": [], "pending": 0}
        if "iframeEvents(" in expr:
            self.log.append(("iframe_events", arg["op"]))
            return ({"armed": True, "reason": None} if arg["op"] == "arm"
                    else {"counts": {"pointermove": 0}, "first": {}, "last": {}, "reason": None, "window_replaced": False})
        if "facts(" in expr:
            return {"panel_rect": _rect(1242.5 - self.panel, self.panel), "inner_width": 1280}
        raise AssertionError(f"unexpected page call: {expr}")


def _driver(spike: Any, variant: str, page: Any = None) -> tuple[Any, SpikeFakePage]:
    page = page or SpikeFakePage(spike)
    return spike.VariantDriver(None, page=page, variant=variant), page


def _mouse_log(page: SpikeFakePage) -> list[tuple[Any, ...]]:
    """Only what the variant itself sent and waited for, in order (the evidence reads are not part of a variant)."""
    return [e for e in page.log if e[0] in ("move", "down", "up", "frames", "sample", "pe_set", "pe_restore")]


def _plan(spike: Any, rs: Any, page: SpikeFakePage) -> dict[str, Any]:
    handle = page.evaluate("handleRect()")
    return rs.drag_plan(handle, spike.TARGET_WIDTH, inner_width=1280)


# -- the variants ------------------------------------------------------------------------------------------------------------------


def test_the_five_variants_are_exactly_the_requested_ones(spike):
    assert spike.VARIANTS == ("burst", "paced", "small_first", "backdrop_wait", "pointer_events_none")
    assert spike.VIEWPORT == (1280, 800) and spike.TARGET_WIDTH == 300


def test_burst_is_todays_unpaced_original_press_then_one_fifteen_step_move_then_release(spike, rs):
    driver, page = _driver(spike, "burst")
    plan = _plan(spike, rs, page)
    driver.drag_splitter_to(spike.TARGET_WIDTH)
    assert _mouse_log(page) == [("move", plan["x0"], plan["y"]), ("down",), ("move", plan["x1"], plan["y"], 15), ("up",)]
    assert driver.last_drag["sent"] == [["down"], ["move", plan["x1"], plan["y"], 15], ["up"]]


def test_paced_is_the_harness_default_routine_unchanged(spike, rs):
    driver, page = _driver(spike, "paced")
    plan = _plan(spike, rs, page)
    driver.drag_splitter_to(spike.TARGET_WIDTH)
    log = _mouse_log(page)
    assert log[:3] == [("move", plan["x0"], plan["y"]), ("down",), ("frames", 2)]
    assert [e for e in log if e[0] == "move" and len(e) == 3][1:] == [("move", px, py) for px, py in rs.step_points(plan)]
    assert log[-2:] == [("frames", 1), ("up",)] and len([e for e in log if e[0] == "frames"]) == 1 + 15
    assert driver.last_drag["pacing"]["waits"][0]["n"] == 2


def test_small_first_presses_then_moves_two_px_inside_the_handle_with_two_frame_waits_then_the_paced_rest(spike, rs):
    driver, page = _driver(spike, "small_first")
    plan = _plan(spike, rs, page)
    driver.drag_splitter_to(spike.TARGET_WIDTH)
    log = _mouse_log(page)
    assert log[:5] == [("move", plan["x0"], plan["y"]), ("down",), ("frames", 2), ("move", plan["x0"] + 2.0, plan["y"]), ("frames", 2)]
    rest = log[5:]
    assert rest[:2] == [("move", rs.step_points(plan)[0][0], plan["y"]), ("frames", 1)]
    assert [e for e in rest if e[0] == "move"] == [("move", px, py) for px, py in rs.step_points(plan)]
    assert rest[-2:] == [("frames", 1), ("up",)]
    assert spike.SMALL_FIRST_DX == 2.0 and spike.SMALL_FIRST_DX < plan["handle"]["width"] / 2, "+2 px stays inside the handle"
    assert driver.notes["small_first"] == {"dx": 2.0, "inside_handle": True}


def test_backdrop_wait_polls_until_the_backdrop_exists_and_is_under_the_first_move_point_then_moves_paced(spike, rs):
    page = SpikeFakePage(spike)
    page.ready_after = 2  # the third poll is the first to see the backdrop under the first move point
    driver, _ = _driver(spike, "backdrop_wait", page)
    driver.clock = _ticking_clock()
    plan = _plan(spike, rs, page)
    driver.drag_splitter_to(spike.TARGET_WIDTH)
    log = _mouse_log(page)
    assert log[:2] == [("move", plan["x0"], plan["y"]), ("down",)]
    assert [e for e in log if e[0] == "sample"] == [("sample", 1), ("sample", 2), ("sample", 3)]
    moves = [i for i, e in enumerate(log) if e[0] == "move" and len(e) == 3][1:]  # after the move to x0
    assert log.index(("sample", 3)) < moves[0], "no move until the backdrop is under the first move point"
    assert ("frames", 2) not in log[:log.index(("sample", 3))], "the wait is the poll, not a frame wait"
    assert len([e for e in page.log if e == ("wait", spike.BACKDROP_POLL_MS)]) == 2, "a poll interval between the three polls"
    assert [log[i] for i in moves] == [("move", px, py) for px, py in rs.step_points(plan)] and log[-1] == ("up",)
    note = driver.notes["backdrop_wait"]
    assert note["ready"] is True and note["bound_hit"] is False and note["polls"] == 3 and note["bound_s"] == 3.0


def test_backdrop_wait_is_bounded_at_three_seconds_records_that_it_was_hit_and_still_drags(spike, rs):
    page = SpikeFakePage(spike)
    page.ready_after = 10**9  # never
    driver, _ = _driver(spike, "backdrop_wait", page)
    driver.clock = _ticking_clock(step=0.4)
    plan = _plan(spike, rs, page)
    driver.drag_splitter_to(spike.TARGET_WIDTH)
    note = driver.notes["backdrop_wait"]
    assert note["ready"] is False and note["bound_hit"] is True and note["bound_s"] == 3.0
    assert note["polls"] <= 3.0 / 0.4 + 2, "bounded: it stopped polling at the bound"
    log = _mouse_log(page)
    assert len([e for e in log if e[0] == "move" and len(e) == 3]) == 1 + 15 and log[-1] == ("up",), "the drag is still sent and released"
    assert plan is not None


def test_pointer_events_none_sets_it_before_the_press_and_restores_the_previous_value_after_the_release(spike, rs):
    page = SpikeFakePage(spike)
    page.iframe_pe = "auto"
    driver, _ = _driver(spike, "pointer_events_none", page)
    driver.drag_splitter_to(spike.TARGET_WIDTH)
    log = _mouse_log(page)
    assert log[0] == ("pe_set", "none") and log.index(("pe_set", "none")) < log.index(("down",)) < log.index(("up",))
    assert log[-1] == ("pe_restore", "auto") and page.iframe_pe == "auto", "the iframe's own inline value is back"
    assert driver.notes["pointer_events_none"] == {"set": True, "previous": "auto", "restored": True}
    assert len([e for e in log if e[0] == "frames"]) == 16, "the drag itself is the paced one"


def test_pointer_events_none_restores_even_when_the_drag_raises(spike, rs):
    page = SpikeFakePage(spike)
    page.up_raises = True
    driver, _ = _driver(spike, "pointer_events_none", page)
    with pytest.raises(RuntimeError):
        driver.drag_splitter_to(spike.TARGET_WIDTH)
    assert page.iframe_pe == "" and ("pe_restore", "") in page.log
    assert driver.notes["pointer_events_none"]["restored"] is True


def test_every_variant_goes_through_the_harness_evidence_bracket(spike, rs):
    for variant in spike.VARIANTS:
        driver, page = _driver(spike, variant)
        driver.clock = _ticking_clock()
        width = driver.drag_splitter_to(spike.TARGET_WIDTH)
        d = driver.last_drag
        assert width == pytest.approx(473.5), variant
        assert {"x0", "y", "x1", "sent", "trace", "elements", "dock_probe_before", "dock_probe_after_up", "pacing", "press_samples",
                "iframe_events", "problems"} <= set(d), variant
        assert len([e for e in page.log if e == ("down",)]) == 1, variant
        assert page.log.index(("press_samples", "arm")) < page.log.index(("down",)) < page.log.index(("press_samples", "read")), variant
        assert page.log.index(("iframe_events", "arm")) < page.log.index(("down",)) < page.log.index(("iframe_events", "read")), variant


# -- the run ----------------------------------------------------------------------------------------------------------------------


def _ticking_clock(step: float = 0.1):
    t = [0.0]

    def clock() -> float:
        t[0] += step
        return t[0]

    return clock


class RecordingDriver:
    """Every method the run calls, recorded in order with canned returns."""

    def __init__(self, *, width: float = 473.5, raises: bool = False) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.width = width
        self.raises = raises
        self.notes: dict[str, Any] = {"x": 1}
        self.last_drag = {"press_samples": [], "iframe_events": None, "problems": []}

    def _rec(self, name: str, *args: Any, ret: Any = None) -> Any:
        self.calls.append((name, *args))
        return ret

    def set_viewport(self, w, h): return self._rec("set_viewport", w, h)
    def run_cell(self, i): return self._rec("run_cell", i)
    def wait_connected(self, t): return self._rec("wait_connected", t, ret=True)
    def toggle_panel(self): return self._rec("toggle_panel")
    def facts(self): return self._rec("facts", ret={"panel_rect": {"width": self.width}, "inner_width": 1280})
    def layout(self): return self._rec("layout", ret={"summary": "layout"})
    def loads(self): return self._rec("loads", ret=3)
    def iframe_info(self): return self._rec("iframe_info", ret={"present": True})

    def drag_splitter_to(self, width):
        self._rec("drag_splitter_to", width)
        if self.raises:
            raise RuntimeError("no handle")
        return 420.0


def test_the_run_opens_the_page_the_way_k2_does_up_to_the_moment_before_drag_low(spike, rs, monkeypatch):
    seen: list[Any] = []
    monkeypatch.setattr(spike.rs, "_setup_dock_world", lambda driver, nb, idx, **kw: seen.append((kw, sorted(idx))))
    driver = RecordingDriver()
    fixture = json.loads(rs.DISPLAY_NOTEBOOK_PATH.read_text())
    out = spike.run_variant(driver, "paced", fixture)
    names = [c[0] for c in driver.calls]
    assert driver.calls[0] == ("set_viewport", 1280, 800), "a fresh page at 1280x800"
    assert seen and seen[0][0] == {"theme": True, "pickup": False, "draws": True}, "the same world K2 builds"
    i_dock = names.index("run_cell")
    assert names[i_dock:i_dock + 6] == ["run_cell", "wait_connected", "toggle_panel", "toggle_panel", "wait_connected", "facts"], "dock(), connected, then K2's reopen()"
    assert driver.calls[i_dock + 1] == ("wait_connected", 90.0) and driver.calls[i_dock + 4] == ("wait_connected", 20.0)
    assert names.index("drag_splitter_to") > names.index("loads") > names.index("layout") and driver.calls[names.index("drag_splitter_to")] == ("drag_splitter_to", 300)
    assert names.count("drag_splitter_to") == 1, "ONE real drag per invocation"
    assert out["variant"] == "paced" and out["final_panel_width"] == 473.5 and out["drag_result_width"] == 420.0
    assert out["clamp_low_ok"] is True and out["connected"] is True and out["reopen_connected"] is True and out["deck_iframe"] == {"present": True}
    assert out["viewport"] == [1280, 800] and out["drag"] == driver.last_drag and out["variant_notes"] == {"x": 1}


def test_a_drag_that_raises_is_an_error_in_the_result_not_a_lost_run(spike, rs, monkeypatch):
    monkeypatch.setattr(spike.rs, "_setup_dock_world", lambda *a, **k: None)
    out = spike.run_variant(RecordingDriver(raises=True), "burst", json.loads(rs.DISPLAY_NOTEBOOK_PATH.read_text()))
    assert out["error"]["type"] == "RuntimeError" and "no handle" in out["error"]["message"]
    assert out["drag_result_width"] is None and out["clamp_low_ok"] is False


# -- result files, the stamp, reuse, timeout ---------------------------------------------------------------------------------------


def test_each_variant_writes_its_own_result_and_a_stamp_under_the_spike_output_directory(spike, tmp_path):
    assert spike.OUT_SUBDIR == Path("outputs/repl_smoke/dock-check/spike-k2-first-drag")
    assert spike.default_out_dir() == spike.REPO_ROOT / "outputs/repl_smoke/dock-check/spike-k2-first-drag"
    paths = spike.variant_paths(tmp_path, "backdrop_wait")
    assert paths["result"] == tmp_path / "backdrop_wait.json" and paths["stamp"] == tmp_path / "backdrop_wait.stamp.json"
    assert paths["timeout"] == tmp_path / "backdrop_wait.timeout.json"
    inputs = {"script": "s" * 64, "harness": "h" * 64, "dist": "d" * 64, "chrome": "c" * 64}
    result = {"variant": "backdrop_wait", "final_panel_width": 420.0, "error": None}
    spike.write_result(tmp_path, "backdrop_wait", result, inputs, exit_code=0, now=lambda: 1234.5)
    stamp = json.loads(paths["stamp"].read_text())
    assert json.loads(paths["result"].read_text()) == result
    assert stamp["variant"] == "backdrop_wait" and stamp["exit"] == 0 and stamp["inputs"] == inputs and stamp["finished"] == 1234.5
    assert stamp["result_sha256"] == __import__("hashlib").sha256(paths["result"].read_bytes()).hexdigest()
    assert not list(tmp_path.glob("*.tmp")), "written atomically"


def test_a_complete_stamp_with_matching_inputs_and_hash_is_reused_anything_else_recomputes(spike, tmp_path):
    inputs = {"script": "s" * 64, "harness": "h" * 64, "dist": "d" * 64, "chrome": "c" * 64}
    assert spike.verified_complete(tmp_path, "burst", inputs) is False, "nothing written yet"
    spike.write_result(tmp_path, "burst", {"variant": "burst", "error": None}, inputs, exit_code=0, now=lambda: 1.0)
    assert spike.verified_complete(tmp_path, "burst", inputs) is True
    assert spike.verified_complete(tmp_path, "burst", {**inputs, "dist": "e" * 64}) is False, "an input changed"
    paths = spike.variant_paths(tmp_path, "burst")
    paths["result"].write_text(paths["result"].read_text() + " ")
    assert spike.verified_complete(tmp_path, "burst", inputs) is False, "the result no longer matches its stamp hash"
    spike.write_result(tmp_path, "burst", {"variant": "burst", "error": {"type": "X"}}, inputs, exit_code=1, now=lambda: 2.0)
    assert spike.verified_complete(tmp_path, "burst", inputs) is False, "a run that ended in an error is never reused"
    assert spike.verified_complete(tmp_path, "paced", inputs) is False, "another variant's files are not this one's"


def test_the_main_entry_reuses_a_verified_unit_without_opening_a_browser_and_fresh_forces_a_rerun(spike, tmp_path, monkeypatch):
    inputs = {"script": "s" * 64, "harness": "h" * 64, "dist": "d" * 64, "chrome": "c" * 64}
    ran: list[str] = []
    monkeypatch.setattr(spike, "compute_inputs", lambda args: inputs)
    monkeypatch.setattr(spike, "run_in_browser", lambda args, variant, out_dir, inputs: ran.append(variant) or 0)
    spike.write_result(tmp_path, "paced", {"variant": "paced", "error": None}, inputs, exit_code=0, now=lambda: 1.0)
    assert spike.main(["--variant", "paced", "--out-dir", str(tmp_path)]) == 0 and ran == [], "reused"
    assert spike.main(["--variant", "paced", "--out-dir", str(tmp_path), "--fresh"]) == 0 and ran == ["paced"]
    assert spike.main(["--variant", "burst", "--out-dir", str(tmp_path)]) == 0 and ran == ["paced", "burst"], "another variant: not reused"


def test_variant_is_required_and_exactly_one_is_taken_per_invocation(spike):
    with pytest.raises(SystemExit) as no_variant:
        spike.parse_args([])
    assert no_variant.value.code == 2
    with pytest.raises(SystemExit) as bad:
        spike.parse_args(["--variant", "nonsense"])
    assert bad.value.code == 2
    with pytest.raises(SystemExit) as two:
        spike.parse_args(["--variant", "burst", "--variant", "paced", "--bogus"])
    assert two.value.code == 2
    assert spike.parse_args(["--variant", "small_first"]).variant == "small_first"
    assert spike.parse_args(["--variant", "burst", "--variant", "paced"]).variant == "paced", "argparse keeps the last; there is no list"


def test_a_watchdog_at_the_budget_writes_a_timeout_marker_and_exits_124_losing_only_this_variant(spike, tmp_path):
    exits: list[int] = []
    released = __import__("threading").Event()
    marker = spike.arm_watchdog(tmp_path, "burst", 0.05, exit_fn=lambda code: (exits.append(code), released.set()))
    assert released.wait(5.0)
    assert exits == [124]
    body = json.loads(spike.variant_paths(tmp_path, "burst")["timeout"].read_text())
    assert body["variant"] == "burst" and body["budget_s"] == 0.05
    assert not spike.variant_paths(tmp_path, "burst")["stamp"].exists(), "a timed-out run leaves no stamp, so it is never reused"
    marker.cancel()


def test_a_watchdog_that_is_disarmed_never_fires(spike, tmp_path):
    exits: list[int] = []
    wd = spike.arm_watchdog(tmp_path, "paced", 0.05, exit_fn=exits.append)
    wd.cancel()
    __import__("time").sleep(0.2)
    assert exits == [] and not spike.variant_paths(tmp_path, "paced")["timeout"].exists()


# -- what the spike is and is not ------------------------------------------------------------------------------------------------


def test_the_header_says_it_is_a_disposable_diagnosis_and_gives_the_command_for_each_variant(spike):
    doc = spike.__doc__ or ""
    assert "DISPOSABLE" in doc and "not bathos" in doc.lower()
    for v in spike.VARIANTS:
        assert f"--variant {v}" in doc, v


def test_it_reuses_the_harness_classes_instead_of_copying_them(spike, rs):
    src = SPIKE_PATH.read_text()
    for copied in ("def drag_plan", "def step_points", "class DockDriver", "class DockSession", "def _setup_dock_world", "def path_points",
                   "def assemble_drag_evidence", "D.pressSamples =", "D.paceFrames ="):
        assert copied not in src, copied
    assert issubclass(spike.VariantDriver, rs.DockDriver) and "repl_smoke.py" in src


def test_it_is_not_bathos_staged_not_in_repl_yml_and_imported_by_nothing(spike):
    name = SPIKE_PATH.stem
    assert not list(SPIKE_PATH.parent.glob(f"{name}*.bth*.toml")), "no sidecar: it is a disposable diagnosis"
    workflows = REPO_ROOT / ".github" / "workflows"
    for f in workflows.glob("*.yml"):
        assert name not in f.read_text(), f.name
    for root in ("scripts", "web-repl/tests", "web-repl/scripts"):
        for f in (REPO_ROOT / root).rglob("*.py"):
            if f == SPIKE_PATH or f.name == Path(__file__).name:
                continue
            assert name not in f.read_text(errors="ignore"), f
    assert not re.search(r"^\s*(import|from)\s+260930", SPIKE_PATH.read_text(), re.M)

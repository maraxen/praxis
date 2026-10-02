#!/usr/bin/env python3
"""DISPOSABLE DIAGNOSIS of K2's 1280 first drag (notebook display epic 260929_notebook-display-design, task C7a round 4).

This is a spike, not bathos-staged (it is not a bathos experiment): it has no ``.bth.toml`` sidecar, pre-registers no outcome, is not part of
``repl.yml`` and is imported by nothing. It produces an ANSWER about how the first splitter drag at 1280x800 behaves, not a finding:
any number from it that gets cited must be re-run under a pre-registered sidecar first (``~/.claude/rules`` spike vs stage rule).

What it does. For ONE variant per invocation it boots a FRESH page at 1280x800 through the harness's own classes (``DockSession``,
``DockDriver``, ``_setup_dock_world``: imported from ``scripts/repl_smoke.py``, never copied), opens the deck the way K2 does up to
the moment before ``drag_low`` (the world, ``dock()``, connected, then K2's close-and-reopen), then makes ONE real drag of the splitter
towards a 300 px panel through the harness's drag routine, so the evidence recorded is exactly what K2 records per drag (press
samples at a microtask / +0 / +50 / +250 / +750 ms, the page's trace, per-wait frame timing, what the deck iframe's own window
received, Lumino's state before and after) plus the final panel width. The five variants:

* ``burst``               today's unpaced original: press, ONE 15-step ``mouse.move``, release (no frame waits).
* ``paced``               the current harness drag: 2 frames after the press, 1 after every move.
* ``small_first``         press, 2 frame waits, a first move of +2 px (inside the 6 px handle), 2 frame waits, then the paced rest.
* ``backdrop_wait``       press, then poll (every 50 ms, at most 3 s) until Lumino's ``.lm-cursor-backdrop`` exists AND
                          ``elementFromPoint`` at the first move point IS the backdrop; then the paced moves. The result records
                          whether the 3 s bound was hit.
* ``pointer_events_none`` ``pointer-events: none`` is set on the deck iframe before the press (its previous inline value is restored
                          after the release, even if the drag raises), then the paced drag. Evidence only: it shows whether the
                          iframe is what eats the events.

Run one variant per invocation, so a timeout (``--budget-s``, default 420 s) loses one variant and never the others:

    uv run --no-sync python scripts/spikes/260930_k2_first_drag_probe.py --variant burst
    uv run --no-sync python scripts/spikes/260930_k2_first_drag_probe.py --variant paced
    uv run --no-sync python scripts/spikes/260930_k2_first_drag_probe.py --variant small_first
    uv run --no-sync python scripts/spikes/260930_k2_first_drag_probe.py --variant backdrop_wait
    uv run --no-sync python scripts/spikes/260930_k2_first_drag_probe.py --variant pointer_events_none

Needs a built ``web-repl/dist`` (or ``--serve-dir``) and a FULL Chromium (``--chrome-path``, else the harness's resolution order).
Each variant writes ``outputs/repl_smoke/dock-check/spike-k2-first-drag/<variant>.json`` and, after it, ``<variant>.stamp.json``
(``result_sha256``, the hashed inputs, ``exit``, ``finished``), both atomically. A complete stamp with matching inputs and result
hash is REUSED on the next invocation (``--fresh`` recomputes); a run that ended in an error or a timeout (``<variant>.timeout.json``,
exit 124, no stamp) is never reused.

What it does not reproduce: K2 reaches 1280 after four earlier steps (a 1152 wide boot, tier changes, two drags at 1440, a 1600
detour) in one page; here the page boots at 1280x800 and is opened the same way but without those steps. If the first drag fails here
too, the earlier steps are not needed to trigger it; if it passes here, they may be.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import logging
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

LOG = logging.getLogger("k2_first_drag_probe")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
OUT_SUBDIR = Path("outputs/repl_smoke/dock-check/spike-k2-first-drag")

VARIANTS = ("burst", "paced", "small_first", "backdrop_wait", "pointer_events_none")
VIEWPORT = (1280, 800)
TARGET_WIDTH = 300
SMALL_FIRST_DX = 2.0
SMALL_FIRST_FRAMES = 2
BACKDROP_WAIT_S = 3.0
BACKDROP_POLL_MS = 50
DEFAULT_BUDGET_S = 420.0

#: ``pointer-events`` on the deck iframe: set (returns the previous INLINE value) and restore. Harness-side page code of this spike only.
SET_POINTER_EVENTS_JS = """(v) => {
    const f = document.querySelector("iframe.praxis-deck-panel__frame");
    if (!f) return { ok: false, previous: null };
    const previous = f.style.pointerEvents;
    f.style.pointerEvents = v;
    return { ok: true, previous };
}"""
RESTORE_POINTER_EVENTS_JS = """(v) => {
    const f = document.querySelector("iframe.praxis-deck-panel__frame");
    if (!f) return { ok: false, value: null };
    f.style.pointerEvents = v;
    return { ok: true, value: f.style.pointerEvents };
}"""


def _load_by_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: ``scripts/repl_smoke.py`` loaded by path (the harness's own classes; nothing of it is copied here).
rs: Any = _load_by_path("repl_smoke_k2_first_drag_probe", REPL_SMOKE_PATH)


# -- the variants: what each sends ---------------------------------------------------------------------------------------------------
# A sequence is ``sequence(driver, plan, settle) -> sent``: the harness drag routine has already moved to the handle centre (``x0``)
# and armed its evidence; the sequence sends its own press, moves and release, waits through ``settle(n_frames)`` and returns what it
# sent (recorded as the drag's ``sent``).


def burst_sequence(driver: Any, plan: dict[str, Any], settle: Callable[[int], None]) -> list[Any]:
    """Today's unpaced original: press, one 15-step move to ``x1``, release, no frame wait anywhere."""
    page = driver.page
    page.mouse.down()
    page.mouse.move(plan["x1"], plan["y"], steps=plan["steps"])
    page.mouse.up()
    return [["down"], ["move", plan["x1"], plan["y"], plan["steps"]], ["up"]]


def small_first_sequence(driver: Any, plan: dict[str, Any], settle: Callable[[int], None]) -> list[Any]:
    """Press, 2 frames, a first move of +2 px (inside the handle), 2 frames, then the paced moves to ``x1`` and the release."""
    page = driver.page
    x0, y = plan["x0"], plan["y"]
    sent: list[Any] = [["down"]]
    page.mouse.down()
    settle(rs.DRAG_DOWN_SETTLE_FRAMES)
    page.mouse.move(x0 + SMALL_FIRST_DX, y)
    sent.append(["move", x0 + SMALL_FIRST_DX, y])
    settle(SMALL_FIRST_FRAMES)
    for px, py in rs.step_points(plan):
        page.mouse.move(px, py)
        sent.append(["move", px, py])
        settle(rs.DRAG_STEP_SETTLE_FRAMES)
    page.mouse.up()
    sent.append(["up"])
    handle = plan.get("handle") or {}
    driver.notes["small_first"] = {"dx": SMALL_FIRST_DX, "inside_handle": bool(SMALL_FIRST_DX < (handle.get("width") or 0) / 2)}
    return sent


def backdrop_wait_sequence(driver: Any, plan: dict[str, Any], settle: Callable[[int], None]) -> list[Any]:
    """Press, poll (``BACKDROP_POLL_MS`` apart, at most ``BACKDROP_WAIT_S``) until the backdrop exists AND is what ``elementFromPoint``
    answers at the first move point; then the paced moves and the release. Records whether the bound was hit."""
    page = driver.page
    x0, y = plan["x0"], plan["y"]
    first = rs.step_points(plan)[0]
    sent: list[Any] = [["down"]]
    page.mouse.down()
    t0 = driver.clock()
    deadline = t0 + BACKDROP_WAIT_S
    polls, ready, bound_hit, last = 0, False, False, None
    while True:
        last = driver.sample_now(first, [x0, y])
        polls += 1
        ready = bool(isinstance(last, dict) and (last.get("backdrop_count") or 0) >= 1 and (last.get("first_move") or {}).get("is_backdrop"))
        if ready:
            break
        if driver.clock() >= deadline:
            bound_hit = True
            break
        page.wait_for_timeout(BACKDROP_POLL_MS)
    driver.notes["backdrop_wait"] = {"ready": ready, "bound_hit": bound_hit, "polls": polls, "waited_s": round(driver.clock() - t0, 3),
                                     "bound_s": BACKDROP_WAIT_S, "poll_ms": BACKDROP_POLL_MS, "last_sample": last}
    sent.append(["poll", polls])
    for px, py in rs.step_points(plan):
        page.mouse.move(px, py)
        sent.append(["move", px, py])
        settle(rs.DRAG_STEP_SETTLE_FRAMES)
    page.mouse.up()
    sent.append(["up"])
    return sent


#: ``None`` is the harness's own (paced) drag routine, unchanged.
SEQUENCES: dict[str, Callable[..., list[Any]] | None] = {
    "burst": burst_sequence,
    "paced": None,
    "small_first": small_first_sequence,
    "backdrop_wait": backdrop_wait_sequence,
    "pointer_events_none": None,
}


class VariantDriver(rs.DockDriver):
    """The harness's ``DockDriver`` whose one drag is sent as the chosen variant. Everything else (the evidence bracket around the
    drag, the page reads, the open sequence) is the harness's."""

    def __init__(self, session: Any, *, variant: str, **kw: Any) -> None:
        if variant not in VARIANTS:
            raise ValueError(f"unknown variant {variant!r}; variants are {list(VARIANTS)}")
        super().__init__(session, **kw)
        self.variant = variant
        #: What the variant observed about itself during the drag (polls, bound hit, the pointer-events restore, ...).
        self.notes: dict[str, Any] = {}

    def _perform_drag(self, plan: dict[str, Any] | None, sequence: Any = None) -> float | None:
        self.notes = {}
        if sequence is None:
            sequence = SEQUENCES[self.variant]
        if self.variant != "pointer_events_none":
            return super()._perform_drag(plan, sequence)
        note = self.notes.setdefault("pointer_events_none", {"set": False, "previous": None, "restored": False})
        got = self.page.evaluate(SET_POINTER_EVENTS_JS, "none") or {}
        note["set"], note["previous"] = bool(got.get("ok")), got.get("previous")
        try:
            return super()._perform_drag(plan, sequence)
        finally:
            if note["set"]:
                back = self.page.evaluate(RESTORE_POINTER_EVENTS_JS, note["previous"] or "") or {}
                note["restored"] = bool(back.get("ok"))


# -- the run -------------------------------------------------------------------------------------------------------------------------


def run_variant(driver: Any, variant: str, fixture: dict[str, Any]) -> dict[str, Any]:
    """Open the page the way K2 does up to the moment before ``drag_low`` and make the one drag. An exception in any step is recorded
    in ``error`` and the result keeps everything read before it (a partial result is still a result)."""
    nb = rs.build_dock_notebook(fixture)
    idx = rs.require_cells(nb, *rs.DOCK_CELL_IDS)
    out: dict[str, Any] = {
        "variant": variant, "spike": SCRIPT_PATH.name, "viewport": list(VIEWPORT), "target_width": TARGET_WIDTH, "error": None,
        "connected": None, "reopen_connected": None, "open_panel_width": None, "deck_iframe": None, "loads_before": None,
        "drag_result_width": None, "final_panel_width": None, "clamp_low_ok": False, "loads_after": None, "drag": None,
        "variant_notes": {}, "layout_before": None, "layout_after": None,
    }
    try:
        driver.set_viewport(*VIEWPORT)
        rs._setup_dock_world(driver, nb, idx, theme=True, pickup=False, draws=True)
        driver.run_cell(idx["dock"])
        out["connected"] = driver.wait_connected(90.0)
        driver.toggle_panel()  # close (K2's reopen())
        driver.toggle_panel()  # reopen: T4, then T6 on the answering announce
        out["reopen_connected"] = driver.wait_connected(20.0)
        out["open_panel_width"] = (driver.facts().get("panel_rect") or {}).get("width")
        out["layout_before"] = driver.layout()
        out["loads_before"] = driver.loads()
        out["deck_iframe"] = driver.iframe_info()
        out["drag_result_width"] = driver.drag_splitter_to(TARGET_WIDTH)
        out["final_panel_width"] = (driver.facts().get("panel_rect") or {}).get("width")
        out["layout_after"] = driver.layout()
        out["loads_after"] = driver.loads()
    except Exception as exc:  # noqa: BLE001 - recorded in the result
        LOG.exception("variant %s raised", variant)
        out["error"] = {"type": type(exc).__name__, "message": str(exc)[:2000], "traceback_tail": traceback.format_exc()[-2000:]}
    finally:
        out["drag"] = getattr(driver, "last_drag", None)
        out["variant_notes"] = dict(getattr(driver, "notes", {}) or {})
        out["clamp_low_ok"] = bool(rs.clamp_low_ok(out["drag_result_width"]))
    return out


# -- result files, stamp, reuse, watchdog ---------------------------------------------------------------------------------------------


def default_out_dir() -> Path:
    return REPO_ROOT / OUT_SUBDIR


def variant_paths(out_dir: Path, variant: str) -> dict[str, Path]:
    out_dir = Path(out_dir)
    return {"result": out_dir / f"{variant}.json", "stamp": out_dir / f"{variant}.stamp.json", "timeout": out_dir / f"{variant}.timeout.json"}


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_result(out_dir: Path, variant: str, result: dict[str, Any], inputs: dict[str, str], *, exit_code: int,
                 now: Callable[[], float] = time.time) -> None:
    """The result, then its stamp (both atomic): a stamp exists only for a result that was completely written."""
    paths = variant_paths(out_dir, variant)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, indent=1, sort_keys=True, default=str).encode()
    _atomic_write(paths["result"], data)
    stamp = {"variant": variant, "result": paths["result"].name, "result_sha256": hashlib.sha256(data).hexdigest(), "inputs": inputs,
             "exit": exit_code, "finished": now()}
    _atomic_write(paths["stamp"], json.dumps(stamp, indent=1, sort_keys=True).encode())


def verified_complete(out_dir: Path, variant: str, inputs: dict[str, str]) -> bool:
    """A prior run of THIS variant is reusable iff its stamp says exit 0, names the same inputs, and the result file on disk still
    hashes to the stamp's ``result_sha256``. Anything else (no stamp, an error run, a changed input, an edited result) recomputes."""
    paths = variant_paths(out_dir, variant)
    try:
        stamp = json.loads(paths["stamp"].read_text())
        data = paths["result"].read_bytes()
    except (OSError, ValueError):
        return False
    return (isinstance(stamp, dict) and stamp.get("variant") == variant and stamp.get("exit") == 0 and stamp.get("inputs") == inputs
            and stamp.get("result_sha256") == hashlib.sha256(data).hexdigest())


def arm_watchdog(out_dir: Path, variant: str, budget_s: float, *, exit_fn: Callable[[int], Any] = os._exit) -> threading.Timer:
    """At ``budget_s``: write ``<variant>.timeout.json`` (and no stamp) and exit 124. One variant per process, so a timeout loses one."""
    started = time.time()

    def fire() -> None:
        marker = {"variant": variant, "budget_s": budget_s, "started": started, "expired": time.time()}
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            _atomic_write(variant_paths(out_dir, variant)["timeout"], json.dumps(marker).encode())
        except OSError:
            pass
        print(json.dumps({"variant": variant, "status": "timeout", "budget_s": budget_s}), flush=True)
        exit_fn(124)

    timer = threading.Timer(budget_s, fire)
    timer.daemon = True
    timer.start()
    return timer


# -- the CLI ---------------------------------------------------------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variant", required=True, choices=VARIANTS, help="ONE variant per invocation (a timeout then loses one).")
    p.add_argument("--serve-dir", type=Path, default=rs.DEFAULT_SERVE_DIR, help=f"The built dist. Default: {rs.DEFAULT_SERVE_DIR}")
    p.add_argument("--base-path", default=None, help="The site's base path (default: the harness's).")
    p.add_argument("--chrome-path", default=None, help="A FULL Chromium (default: the harness's resolution order).")
    p.add_argument("--out-dir", type=Path, default=None, help=f"Default: {default_out_dir()}")
    p.add_argument("--budget-s", type=float, default=DEFAULT_BUDGET_S, help=f"Watchdog for this one variant. Default: {DEFAULT_BUDGET_S}")
    p.add_argument("--fresh", action="store_true", help="Recompute even if a verified complete result exists.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def harness_args(args: argparse.Namespace) -> argparse.Namespace:
    """The harness's own argument namespace for ``--dock-check`` (its defaults, then this run's dist, base path and Chromium)."""
    argv = ["--dock-check", "--serve-dir", str(args.serve_dir)]
    if args.base_path:
        argv += ["--base-path", args.base_path]
    if args.chrome_path:
        argv += ["--chrome-path", args.chrome_path]
    return rs.parse_args(argv)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compute_inputs(args: argparse.Namespace) -> dict[str, str]:
    """What a result depends on: this script, the harness, the served dist, the notebook fixture and the Chromium."""
    hargs = harness_args(args)
    env = rs.build_hash_env(hargs, str(rs.resolve_chrome_path(args.chrome_path)))
    return {"script": _sha256_file(SCRIPT_PATH), "harness": env.harness, "dist": env.dist, "notebook": env.notebook, "chrome": env.chrome}


def run_in_browser(args: argparse.Namespace, variant: str, out_dir: Path, inputs: dict[str, str]) -> int:
    """One variant in one fresh browser, inside its own watchdog. Returns the exit code (0, or 1 when the result carries an error)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = variant_paths(out_dir, variant)
    for key in ("stamp", "result", "timeout"):  # stamp first: a half-cleared unit must never look complete
        paths[key].unlink(missing_ok=True)
    started = time.time()
    watchdog = arm_watchdog(out_dir, variant, args.budget_s)
    session: Any = None
    result: dict[str, Any]
    try:
        hargs = harness_args(args)
        chrome = str(rs.resolve_chrome_path(args.chrome_path))
        env = rs.build_hash_env(hargs, chrome)
        unit = dataclasses.replace(rs.UNIT_BY_ID["K2"], viewports=(VIEWPORT,))
        session = rs.DockSession(unit, hargs, env)
        driver = VariantDriver(session, variant=variant)
        result = run_variant(driver, variant, json.loads(rs.DISPLAY_NOTEBOOK_PATH.read_text()))
        result.update({"pageerrors": list(session.pageerrors), "chrome_path": env.chrome_path, "chrome_version": env.chrome_version})
    except Exception as exc:  # noqa: BLE001 - recorded in the result
        LOG.exception("variant %s could not run", variant)
        result = {"variant": variant, "spike": SCRIPT_PATH.name, "error": {"type": type(exc).__name__, "message": str(exc)[:2000],
                                                                            "traceback_tail": traceback.format_exc()[-2000:]}}
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                LOG.exception("session close raised")
    result.update({"started": started, "finished": time.time(), "budget_s": args.budget_s})
    code = 0 if result.get("error") is None else 1
    write_result(out_dir, variant, result, inputs, exit_code=code)
    watchdog.cancel()
    print(json.dumps({"variant": variant, "status": "done", "error": (result.get("error") or {}).get("type"),
                      "final_panel_width": result.get("final_panel_width"), "clamp_low_ok": result.get("clamp_low_ok"),
                      "result": str(paths["result"])}), flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    out_dir = Path(args.out_dir) if args.out_dir else default_out_dir()
    try:
        inputs = compute_inputs(args)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        LOG.error("cannot build the input set: %s: %s", type(exc).__name__, exc)
        return 2
    if not args.fresh and verified_complete(out_dir, args.variant, inputs):
        LOG.info("variant %s: a verified complete result exists (%s); reused (use --fresh to recompute)", args.variant,
                 variant_paths(out_dir, args.variant)["result"])
        return 0
    return run_in_browser(args, args.variant, out_dir, inputs)


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)  # no interpreter shutdown: Playwright's teardown can stall it (the harness's units exit the same way)

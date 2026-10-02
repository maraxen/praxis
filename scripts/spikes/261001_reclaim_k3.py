#!/usr/bin/env python3
"""K3 (backlog #5656, AC-N5): the pre-registered real-browser measurement of the medium-tier re-clamp, run RED then GREEN.

This is the thin runner behind two pre-registrations (``scripts/spikes/261001_reclaim_k3_red.bth.toml`` and
``scripts/spikes/261001_reclaim_k3_green.bth.toml``, both committed BEFORE either run; spec ``.praxia/docs/specs/261001_nd-next-5656-deck-layout.md``
AC-N5 and task T6). ``bth run`` ties a sidecar to the script it runs by NAME (``<stem>.bth.toml`` beside it), so the two phases are started
through the one-line launchers ``261001_reclaim_k3_red.py`` and ``261001_reclaim_k3_green.py``, which call ``main(phase=...)`` here.

What it does. It runs ONE harness unit, ``repl_smoke.py --dock-check --scenario K3`` (K3 is one page, one kernel, one ``dock()``; its own
``Watchdog`` fires at its 10 min budget and the runner's ``unit_runner.run_unit`` at budget + 60 s, so a timeout loses only K3), against
the dist given with ``--dist``, with its own ``--out-dir``. It then reads the harness's RESULT and STAMP (never console text), derives the
flat fields the sidecar's ``[outcomes]`` read, and writes them to ``$BTH_RESULTS_PATH`` ONLY when the unit is complete (a valid stamp for the
current inputs). An incomplete unit (a timeout, a crash) exits 3 and writes no result, so bathos records no outcome.

RED and GREEN differ in one INPUT-derived check, not in a result: the served dist's ``shell/display/dock.js`` must NOT contain
``reclaimMedium`` for the RED phase (the build without the fix) and MUST contain it for GREEN. Without that check a RED run on the fixed
build, or a GREEN run on the unfixed one, would still produce well-formed numbers.

Resume (preemption-safe by design). The unit persists its result and stamp the moment it completes. ``--resume`` reuses a prior unit only
when its stamp is VALID for the current inputs (dist, notebook, harness, runner, chrome, args, driver hashes all equal, and the result's
sha256 matches the file); anything else is recomputed, and the aggregate ``result.json`` records which unit was reused, from where, and its
hashes. A RED unit fails its keys BY DESIGN, so "valid" - not "all keys held" - is what makes a unit reusable here.

Run it (unsandboxed, from a checkout whose ``web-repl/dist`` is a FRESH build of the commit under test)::

    bth run --project-slug praxis --output-paths outputs/reclaim_k3/red -- \\
        uv run --no-sync python3 scripts/spikes/261001_reclaim_k3_red.py --dist web-repl/dist --out-dir outputs/reclaim_k3/red [--resume]
    bth run --project-slug praxis --output-paths outputs/reclaim_k3/green -- \\
        uv run --no-sync python3 scripts/spikes/261001_reclaim_k3_green.py --dist web-repl/dist --out-dir outputs/reclaim_k3/green [--resume]

``bth``, never ``uv run bth`` (which silently skips sidecar enforcement). Verify the run by its RECORD: ``bth compact`` then
``bth sql "SELECT id, status, outcome, exit_code, command FROM runs WHERE id LIKE '<prefix>%'"``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

LOG = logging.getLogger("reclaim_k3")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"

PHASES = ("red", "green")
UNIT_ID = "K3"
#: ``run_unit``'s timeout is the harness unit's budget plus this (the unit's own watchdog fires at the budget).
DRIVER_EXTRA_S = 60.0
#: The name the fix's function carries in dock.js (the contract of dock_reclaim.test.js); the served dist either has it or not.
FIX_TOKEN = "reclaimMedium"
DOCK_JS_IN_DIST = Path("shell") / "display" / "dock.js"

#: Exit codes: 0 the unit is complete and the flat fields were written; 2 the environment is unusable; 3 the unit is incomplete.
EXIT_OK, EXIT_ENV, EXIT_INCOMPLETE = 0, 2, 3


def _load_by_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_MODULES: dict[str, Any] = {}


def repl_smoke() -> Any:
    """``scripts/repl_smoke.py`` loaded by path, once (the unit table, ``inspect_unit``, the key lists)."""
    if "rs" not in _MODULES:
        _MODULES["rs"] = _load_by_path("repl_smoke_reclaim_k3", REPL_SMOKE_PATH)
    return _MODULES["rs"]


def unit_runner() -> Any:
    if "ur" not in _MODULES:
        _MODULES["ur"] = _load_by_path("unit_runner_reclaim_k3", RUNNER_PATH)
    return _MODULES["ur"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# The build under test
# --------------------------------------------------------------------------- #


def dist_build(dist: Path) -> dict[str, Any]:
    """What the served dist's ``dock.js`` says about the fix: ``{has_fix, dock_js_sha256}``. Raises ``FileNotFoundError`` when the dist
    has no ``shell/display/dock.js`` (then neither phase can tell which build it is measuring)."""
    path = Path(dist) / DOCK_JS_IN_DIST
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found: the dist is not a build of the display shell")
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"has_fix": FIX_TOKEN in text, "dock_js_sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()}


# --------------------------------------------------------------------------- #
# The flat fields the sidecars read
# --------------------------------------------------------------------------- #


def _count_step_errors(result: dict[str, Any]) -> int:
    evidence = result.get("evidence")
    errors = evidence.get("step_errors") if isinstance(evidence, dict) else None
    return len(errors) if isinstance(errors, dict) else 0


def flat_fields(phase: str, result: dict[str, Any], *, has_fix: bool, reused: bool, harness_exit: int) -> dict[str, Any]:
    """The flat fields of a COMPLETE K3 unit (``result`` is the harness's ``result.K3.json``). Pure.

    ``measurement_valid`` is per phase and reads INPUTS and instrument health, never the verdict being judged:

    * both: the build has (GREEN) / lacks (RED) the fix, the unit ran without an error finding, every listed key is present, and the
      re-clamp keys are ``asserted`` (not recorded-only);
    * RED adds: every precondition holds and every step settled (a precondition or a settle that fails means the instrument cannot tell
      "the fix is absent" from "the action did nothing");
    * GREEN does NOT add them: after the fix a swallowed drag (the iframe next to the handle), a loop that never settles or a step
      error is a finding about the product (risks R1-R3), so it lands in ``green_failed`` with these fields to read.
    """
    rs = repl_smoke()
    keys = list(rs.K3_KEYS)
    values = {k: result.get(k) is True for k in keys}
    errors = _count_step_errors(result)
    preconditions_ok = result.get("k3_preconditions_ok") is True
    all_settled = result.get("k3_all_settled") is True
    pageerrors_ok = result.get("pageerrors") == []
    error_free = result.get("error") is None
    keys_present = all(k in result for k in keys)
    asserted = result.get("reclaim_status") == rs.ASSERTED
    build_matches = has_fix if phase == "green" else not has_fix
    common = build_matches and error_free and keys_present and asserted
    valid = (common and preconditions_ok and all_settled and errors == 0) if phase == "red" else common
    red_false = list(rs.K3_RED_FALSE)
    red_guard = list(rs.K3_RED_GUARD)
    failing = [k for k in keys if not values[k]]
    flat: dict[str, Any] = {
        "phase": phase,
        "unit_complete": True,
        "reused": bool(reused),
        "harness_exit": int(harness_exit),
        "build_has_fix": bool(has_fix),
        "build_matches_phase": bool(build_matches),
        "unit_error_free": bool(error_free),
        "keys_present": bool(keys_present),
        "status_asserted": bool(asserted),
        "step_errors": int(errors),
        "preconditions_ok": bool(preconditions_ok),
        "all_settled": bool(all_settled),
        "pageerrors_ok": bool(pageerrors_ok),
        "measurement_valid": bool(valid),
        "n_keys_true": sum(values.values()),
        "red_false_keys_all_false": all(not values[k] for k in red_false),
        "red_guard_keys_all_true": all(values[k] for k in red_guard) and pageerrors_ok,
        "all_keys_true": all(values.values()) and pageerrors_ok,
        "failing_keys": ",".join(failing),
    }
    for k in keys:
        flat[f"k_{k}"] = values[k]
    return flat


# --------------------------------------------------------------------------- #
# The harness unit
# --------------------------------------------------------------------------- #


def harness_env(rs: Any, dist: Path, base_path: str, chrome_path: str) -> Any:
    """The harness's own hashed inputs for this dist (the same ones ``--scenario K3`` stamps)."""
    return rs.build_hash_env(argparse.Namespace(serve_dir=Path(dist), base_path=base_path), chrome_path)


def harness_argv(args: argparse.Namespace, chrome_path: str, out_dir: Path) -> list[str]:
    return [
        sys.executable, str(REPL_SMOKE_PATH), "--dock-check", "--scenario", UNIT_ID, "--serve-dir", str(Path(args.dist).resolve()),
        "--out-dir", str(out_dir), "--base-path", args.base_path, "--chrome-path", chrome_path,
    ]


def k3_out_dir(args: argparse.Namespace) -> Path:
    return Path(args.out_dir).resolve() / "k3"


def _rm(path: Path) -> None:
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


def plan(args: argparse.Namespace) -> dict[str, Any]:
    rs = repl_smoke()
    unit = rs.UNIT_BY_ID[UNIT_ID]
    return {
        "phase": args.phase, "dist": str(Path(args.dist).resolve()), "out_dir": str(Path(args.out_dir).resolve()),
        "harness_out_dir": str(k3_out_dir(args)), "unit": UNIT_ID, "budget_s": unit.budget_s,
        "run_unit_timeout_s": unit.budget_s + DRIVER_EXTRA_S, "viewports": [list(v) for v in unit.viewports],
        "listed_keys": list(unit.keys), "red_predicted_false": list(rs.K3_RED_FALSE), "red_predicted_true_guards": list(rs.K3_RED_GUARD),
        "fix_token": FIX_TOKEN, "must_contain_fix": args.phase == "green",
    }


def run(args: argparse.Namespace, *, runner: Any = None, chrome_path: str | None = None) -> int:
    """One phase: ensure the build matches, run (or reuse) the K3 unit, write the aggregate and, when complete, the flat fields."""
    rs, ur = repl_smoke(), unit_runner()
    runner = runner or ur
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stale_results = os.environ.get("BTH_RESULTS_PATH")
    if stale_results:
        _rm(Path(stale_results))  # bathos gives each run a fresh path; never let an earlier outcome stand in for this one
    try:
        build = dist_build(Path(args.dist))
        chrome = chrome_path if chrome_path is not None else str(rs.resolve_chrome_path(args.chrome_path))
        env = harness_env(rs, Path(args.dist), args.base_path, chrome)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        LOG.error("cannot build the input set: %s: %s", type(exc).__name__, exc)
        return EXIT_ENV
    unit = rs.UNIT_BY_ID[UNIT_ID]
    k3_dir = k3_out_dir(args)
    k3_dir.mkdir(parents=True, exist_ok=True)
    inputs = rs.unit_inputs(unit, env)
    state = rs.inspect_unit(k3_dir, unit, inputs)
    reused = False
    outcome = None
    if args.resume and state["valid"]:
        LOG.info("unit %s reused (valid stamp for the current inputs; result sha256 %s)", UNIT_ID, state["stamp"]["result_sha256"])
        reused = True
    else:
        rs.clear_unit_files(k3_dir, UNIT_ID)  # never judge a stale stamp: stamp first, then result and marker
        argv = harness_argv(args, chrome, k3_dir)
        LOG.info("starting %s (timeout %.0f s) on %s [%s phase]", UNIT_ID, unit.budget_s + DRIVER_EXTRA_S, args.dist, args.phase)
        outcome = runner.run_unit(argv, unit.budget_s + DRIVER_EXTRA_S, cwd=str(REPO_ROOT))
        state = rs.inspect_unit(k3_dir, unit, inputs)
        if state["valid"] and outcome.timed_out:
            LOG.warning("%s: run_unit timed out over a VALID stamp; the stamp governs", UNIT_ID)
    aggregate: dict[str, Any] = {
        "runner": "reclaim_k3", "phase": args.phase, "unit": UNIT_ID, "dist": str(Path(args.dist).resolve()),
        "build": build, "inputs": inputs, "reused": reused, "unit_complete": bool(state["valid"]),
        "result_path": state["result_path"], "stamp": state["stamp"], "reasons": state["reasons"],
        "chrome_path": chrome, "finished": time.time(),
        "harness_run": None if outcome is None else {"exit": outcome.exit, "timed_out": outcome.timed_out, "killed": outcome.killed},
    }
    exit_code = EXIT_INCOMPLETE
    if state["valid"]:
        result = state["result"]
        flat = flat_fields(args.phase, result, has_fix=build["has_fix"], reused=reused, harness_exit=int(state["stamp"].get("exit", -1)))
        aggregate.update({
            "outcome_fields": flat, "outcome_evaluated": True,
            "result_sha256": state["stamp"]["result_sha256"],
            "k3_predicates": result.get("k3_predicates"), "k3_preconditions": result.get("k3_preconditions"),
            "k3_settled": result.get("k3_settled"), "k3_measures": result.get("k3_measures"),
            "failing_keys": state["failing_keys"], "missing_keys": state["missing_keys"],
        })
        results_path = os.environ.get("BTH_RESULTS_PATH")
        if results_path:
            ur.write_atomic(results_path, json.dumps(flat, sort_keys=True).encode())
        exit_code = EXIT_OK
    else:
        aggregate["outcome_evaluated"] = False
        LOG.error("NOT evaluating outcomes: the %s unit is incomplete (%s)", UNIT_ID, state["reasons"])
    ur.write_atomic(out_dir / "result.json", json.dumps(aggregate, indent=1, sort_keys=True, default=str).encode())
    print(json.dumps(aggregate, sort_keys=True, default=str))
    return exit_code


def parse_args(argv: list[str] | None, *, phase: str | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--phase", choices=PHASES, default=phase, required=phase is None,
                   help="red: the build WITHOUT the fix; green: the build with it (fixed by the launchers).")
    p.add_argument("--dist", default=str(DEFAULT_DIST), help="The built dist to serve (never modified).")
    p.add_argument("--out-dir", default=None, help="Records: result.json and k3/result.K3.json + stamp. Default outputs/reclaim_k3/<phase>.")
    p.add_argument("--base-path", default="/praxis/", help="URL prefix the dist is served under (CI: /praxis/).")
    p.add_argument("--chrome-path", default=None)
    p.add_argument("--resume", action="store_true", help="Reuse a unit whose stamp is valid for the current inputs.")
    p.add_argument("--dry-run", action="store_true", help="Print the plan; launch and hash nothing.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    if phase is not None and args.phase != phase:
        p.error(f"this launcher runs the {phase} phase; --phase {args.phase} was given")
    if args.out_dir is None:
        args.out_dir = str(REPO_ROOT / "outputs" / "reclaim_k3" / args.phase)
    return args


def main(argv: list[str] | None = None, *, phase: str | None = None, runner: Any = None, chrome_path: str | None = None) -> int:
    args = parse_args(argv, phase=phase)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.dry_run:
        print(json.dumps(plan(args), indent=1))
        return 0
    return run(args, runner=runner, chrome_path=chrome_path)


if __name__ == "__main__":
    sys.exit(main())

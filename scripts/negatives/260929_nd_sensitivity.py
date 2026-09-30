#!/usr/bin/env python3
"""The AC-39 sensitivity driver (notebook display epic, task A7; spec D17 "AC-39 sensitivity
runs are pre-registered too", D16 "AC-39 negatives run only their own unit", AC-39, AC-42).

A sensitivity run proves a browser gate is SENSITIVE: that it fails when the thing it guards
is broken. Each negative (a unit of this driver) copies the pristine built dist to its own
directory ``<neg-root>/<negative>/dist/`` (default ``/tmp/claude-1000/nd-neg/``), applies ITS ONE
mutation, and runs ONLY its own harness unit (``scripts/repl_smoke.py --display-check
--scenario D1`` for negative ``a``) as a subprocess through ``unit_runner.run_unit`` (timeout =
that unit's budget + 60 s; the harness's own ``--scenario`` watchdog fires at the budget), with
``--serve-dir <neg-root>/<negative>/dist`` and its own ``--out-dir <neg-root>/<negative>/out``
(D16 refuses a non-default ``--serve-dir`` or any ``--neg`` without ``--out-dir``, C8-5), so no
negative writes into the default ``outputs/repl_smoke/<check>/`` or into its own served dist
(which would change its ``dist`` hash).

This module is the SHARED driver. Each sprint has a thin entry script that fixes its negative
set and is the file a bathos sidecar is named after (sprint A: ``scripts/spikes/
260929_nd_sensitivity_sprint_a.py`` runs negative ``a``). The table below is extended by B10
(sprint B: negative ``a`` again) and C7 (sprint C: ``b``, ``c``, ``d``, ``e``).

Two modes, one file, as the spike drivers:

* **Driver** (no ``--unit``): one unit subprocess per negative through ``unit_runner.run_unit``,
  the ``--resume`` rule, and the sidecar's ``[outcomes]`` inputs written to ``$BTH_RESULTS_PATH``
  ONLY when every negative's unit is complete (exit 3 otherwise; bathos then records no outcome).
* **Unit** (``--unit <negative>``): ``ensure_token`` -> arm the ``Watchdog`` -> clear own files ->
  copy, mutate, run the harness unit -> write ``<out>/units/<negative>.json`` under the watchdog
  lock -> bounded teardown -> commit ``<out>/units/<negative>.stamp.json`` through
  ``Watchdog.commit`` -> ``os._exit(stamp.exit)``.

A negative PASSES iff the harness exits nonzero AND the expected key is among its FAILING keys
(present and not holding; a key that is merely absent from a scenario that raised does not
count), AND the harness result carries no ``error`` finding, from a valid harness stamp. A harness
timeout (exit 124, no stamp, no result: the watchdog deletes it) is nonzero but names no key,
so it never passes.

Measurement discipline (``~/.claude/rules/BATHOS.md``): the paired POSITIVE control of this
instrument is the unmutated unit passing on the real dist (AC-7, run separately); the negative
control is the mutated run failing. ``measurement_valid`` additionally requires that the pristine
dist really contained the file the mutation removes and that the copy really lost it, so a
mutation that changed nothing can never read as "the harness did not notice".
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

LOG = logging.getLogger("nd_sensitivity")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"
DEFAULT_NEG_ROOT = Path("/tmp/claude-1000/nd-neg")

#: The harness unit is started with ``budget + DRIVER_EXTRA_S`` as its ``run_unit`` timeout (D16).
DRIVER_EXTRA_S = 60.0
#: Allowance, on top of the harness ``run_unit`` timeout, for the negative unit's own copy of
#: the dist, its hashing and teardown. An estimate, not a measurement; the driver kills a unit at
#: its budget + DRIVER_EXTRA_S (D17).
NEG_UNIT_OVERHEAD_S = 180.0

#: Fields every negative's artifact must carry (pre-registered; the resume rule requires them).
REQUIRED_FIELDS = ("harness_exit", "failing_keys", "outcome")


@dataclasses.dataclass(frozen=True)
class Negative:
    """One AC-39 negative: which harness unit to run, which mutation to apply to the dist copy,
    and which key must be among the harness's failing keys."""

    id: str
    harness_flag: str  # "--display-check" (A7, B10) or "--dock-check" (C7)
    harness_unit: str  # the D16 unit id, run alone with --scenario
    expected_key: str
    delete: str | None  # path relative to the dist root removed from the copy (None: no mutation)
    mutation: str
    harness_neg: tuple[str, ...] = ()  # harness-only --neg flags (AC-39(e): drop-query)


#: The negatives this checkout can run. Sprint A: (a). B10 reuses (a); C7 adds b, d, e (and c as
#: a grep, which has no harness unit). Their harness units do not exist before C7.
NEGATIVES: dict[str, Negative] = {
    "a": Negative(
        id="a",
        harness_flag="--display-check",
        harness_unit="D1",
        expected_key="rail_state_after_run",
        delete="shell/display/index.js",
        mutation=(
            "remove shell/display/index.js from the dist copy: the display modules never mount, "
            "so no cell carries data-praxis-cell-state and the rail cannot reach `ran`"
        ),
    ),
}


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
    """``scripts/repl_smoke.py`` loaded by path, once (unit table, ``inspect_unit``, hashing)."""
    global _REPL_SMOKE
    if _REPL_SMOKE is None:
        _REPL_SMOKE = _load_by_path("repl_smoke", REPL_SMOKE_PATH)
    return _REPL_SMOKE


#: Replaceable seams (the plumbing tests substitute stubs; nothing in production does).
HARNESS_ARGV_PREFIX: list[str] | None = None  # default: [sys.executable, scripts/repl_smoke.py]


def harness_argv_prefix() -> list[str]:
    return list(HARNESS_ARGV_PREFIX) if HARNESS_ARGV_PREFIX is not None else [
        sys.executable, str(REPL_SMOKE_PATH)
    ]


# --------------------------------------------------------------------------- #
# Hashing, the dist copy and its mutation
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    return unit_runner._sha256_file(Path(path))


def dist_lines(directory: Path) -> list[tuple[str, str]]:
    """``(rel posix path, sha256)`` of every file, sorted: exactly ``unit_runner.dist_hash``'s lines."""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"dist directory not found: {root}")
    return sorted((p.relative_to(root).as_posix(), sha256_file(p)) for p in root.rglob("*") if p.is_file())


def hash_lines(lines: list[tuple[str, str]]) -> str:
    return sha256_bytes("".join(f"{rel}\t{sha}\n" for rel, sha in lines).encode())


def virtual_mutated_hash(pristine: Path, delete: str | None) -> str:
    """The ``dist_hash`` the mutated copy WILL have, computed from the pristine tree without
    copying it (so the driver can decide reuse cheaply). The unit asserts it equals the real
    ``dist_hash`` of the copy it actually made."""
    lines = dist_lines(pristine)
    if delete is not None:
        lines = [(rel, sha) for rel, sha in lines if rel != delete]
    return hash_lines(lines)


@dataclasses.dataclass
class NegPaths:
    root: Path
    dist: Path
    out: Path


def neg_paths(neg_root: Path, negative: str) -> NegPaths:
    root = Path(neg_root) / negative
    return NegPaths(root=root, dist=root / "dist", out=root / "out")


def prepare_mutated_dist(pristine: Path, dest: Path, negative: Negative, neg_root: Path) -> dict[str, Any]:
    """Copy ``pristine`` to ``dest`` (a fresh copy every time) and apply the negative's mutation.

    ``dest`` must be ``<neg_root>/<negative>/dist``: nothing outside it is ever deleted or written.
    Returns ``{pristine_has_target, mutated_lacks_target}``; a mutation whose target the pristine
    dist does not contain applied to nothing (``pristine_has_target`` False -> the run is invalid).
    """
    pristine, dest, neg_root = Path(pristine), Path(dest), Path(neg_root)
    expected = (neg_root / negative.id / "dist").resolve()
    if dest.resolve() != expected:
        raise ValueError(f"refusing to write {dest}: a negative's dist must be {expected}")
    if not pristine.is_dir():
        raise FileNotFoundError(f"pristine dist not found: {pristine}")
    if dest.resolve() == pristine.resolve() or pristine.resolve() in dest.resolve().parents:
        raise ValueError("the mutated copy must not live inside the pristine dist")
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pristine, dest, symlinks=False)
    info = {"pristine_has_target": True, "mutated_lacks_target": True}
    if negative.delete is not None:
        info["pristine_has_target"] = (pristine / negative.delete).is_file()
        target = dest / negative.delete
        if target.is_file():
            target.unlink()
        info["mutated_lacks_target"] = not target.exists()
    return info


# --------------------------------------------------------------------------- #
# Inputs (D17: the driver and entry script, repl_smoke.py, unit_runner.py, the pristine and the
# mutated dist hashes, the chrome path and version, and `driver`)
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class InputEnv:
    script: str  # sha256 of this shared driver
    entry: str  # sha256 of the sprint entry script
    runner: str
    harness: str  # scripts/repl_smoke.py
    dist_pristine: str
    chrome: str
    driver: str
    base_path: str = "/praxis/"
    chrome_path: str = ""
    chrome_version: str = ""


def build_env(args: argparse.Namespace) -> InputEnv:
    """Resolve and hash the real inputs. Raises ``FileNotFoundError`` for a missing dist or ``uv.lock``."""
    rs = repl_smoke()
    chrome_path = str(rs.resolve_chrome_path(args.chrome_path))
    version = rs.chrome_version_of(chrome_path)
    return InputEnv(
        script=sha256_file(SCRIPT_PATH),
        entry=sha256_file(args.entry_path),
        runner=sha256_file(RUNNER_PATH),
        harness=sha256_file(REPL_SMOKE_PATH),
        dist_pristine=unit_runner.dist_hash(args.dist),
        chrome=sha256_bytes(f"{chrome_path}\n{version}".encode()),
        driver=unit_runner.driver_input(),
        base_path=args.base_path,
        chrome_path=chrome_path,
        chrome_version=version,
    )


def compute_inputs(negative: Negative, env: InputEnv, dist_mutated: str, neg_root: Path) -> dict[str, str]:
    return {
        "script": env.script,
        "entry": env.entry,
        "runner": env.runner,
        "harness": env.harness,
        "dist_pristine": env.dist_pristine,
        "dist_mutated": dist_mutated,
        "chrome": env.chrome,
        "driver": env.driver,
        "args": sha256_bytes(
            json.dumps(
                {
                    "negative": negative.id, "harness_unit": negative.harness_unit,
                    "harness_flag": negative.harness_flag, "harness_neg": list(negative.harness_neg),
                    "delete": negative.delete, "base_path": env.base_path,
                    "neg_root": str(neg_root),
                },
                sort_keys=True,
            ).encode()
        ),
    }


def harness_budget_s(negative: Negative) -> float:
    return float(repl_smoke().UNIT_BY_ID[negative.harness_unit].budget_s)


def unit_budget_s(negative: Negative) -> float:
    """The negative unit's own watchdog: the harness ``run_unit`` timeout plus the copy allowance."""
    return harness_budget_s(negative) + DRIVER_EXTRA_S + NEG_UNIT_OVERHEAD_S


# --------------------------------------------------------------------------- #
# Unit files, completeness and the resume rule (D17, C8-3, C8-7)
# --------------------------------------------------------------------------- #


def unit_paths(out_dir: Path, negative: str) -> dict[str, Path]:
    units = Path(out_dir) / "units"
    return {
        "artifact": units / f"{negative}.json",
        "stamp": units / f"{negative}.stamp.json",
        "timeout": units / f"{negative}.timeout.json",
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def _rm(path: Path) -> None:
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


def negative_outcome(
    negative: Negative,
    *,
    stamp_valid: bool,
    harness_exit: int | None,
    failing_keys: list[str],
    harness_error: Any,
) -> tuple[bool, list[str]]:
    """Did the harness FAIL as required? Nonzero exit AND the expected key among the failing
    keys, from a valid stamp whose result carries no error finding. Returns ``(passed, reasons)``."""
    reasons: list[str] = []
    if not stamp_valid:
        reasons.append("no valid harness stamp (a timeout or a crash names no key)")
    if harness_exit in (None, 0):
        reasons.append(f"harness exit is {harness_exit!r}: it did not fail")
    if negative.expected_key not in failing_keys:
        reasons.append(f"expected key {negative.expected_key!r} is not among the failing keys {failing_keys}")
    if harness_error is not None:
        reasons.append("the harness result carries an error finding: the instrument failed, not the gate")
    return not reasons, reasons


def inspect_unit(out_dir: Path, negative: Negative, current_inputs: dict[str, str]) -> dict[str, Any]:
    """Classify one negative's files against the CURRENT inputs.

    * ``complete``: artifact and a matching stamp (``artifact_sha256`` equals the artifact on disk,
      ``inputs`` equal the current inputs). A unit whose driver code raised is complete (its
      ``error`` finding is in the artifact); only a timeout or a stampless crash is incomplete.
    * ``reusable`` (the ``--resume`` rule): complete AND ``stamp.exit == 0`` AND no ``error``
      finding AND every pre-registered field present AND the recorded outcome passed (a missed
      negative is always rerun).
    """
    paths = unit_paths(out_dir, negative.id)
    try:
        raw: bytes | None = paths["artifact"].read_bytes()
    except OSError:
        raw = None
    artifact: Any = None
    if raw is not None:
        try:
            artifact = json.loads(raw)
        except ValueError:
            artifact = None
    stamp = _read_json(paths["stamp"])
    state: dict[str, Any] = {
        "unit": negative.id, "artifact": artifact if isinstance(artifact, dict) else None,
        "stamp": stamp if isinstance(stamp, dict) else None, "artifact_path": str(paths["artifact"]),
        "complete": False, "reusable": False, "mismatched": [], "reasons": [],
    }
    if state["artifact"] is None:
        state["reasons"].append("no artifact")
        return state
    if state["stamp"] is None:
        state["reasons"].append("no stamp")
        return state
    stamp = state["stamp"]
    if stamp.get("artifact_sha256") != sha256_bytes(raw or b""):
        state["reasons"].append("artifact_sha256 does not match the artifact on disk")
        return state
    recorded = stamp.get("inputs") or {}
    state["mismatched"] = sorted(
        n for n in set(recorded) | set(current_inputs) if recorded.get(n) != current_inputs.get(n)
    )
    if state["mismatched"]:
        state["reasons"].append("stamp inputs differ from the current inputs")
        return state
    state["complete"] = True
    art = state["artifact"]
    if stamp.get("exit") != 0:
        state["reasons"].append(f"stamp.exit == {stamp.get('exit')!r}")
    if art.get("error") is not None:
        state["reasons"].append("artifact carries an error finding")
    absent = [f for f in REQUIRED_FIELDS if f not in art]
    if absent:
        state["reasons"].append(f"pre-registered fields missing: {absent}")
    if art.get("outcome") is not True:
        state["reasons"].append("the recorded outcome did not pass (a missed negative is always rerun)")
    state["reusable"] = not state["reasons"]
    return state


# --------------------------------------------------------------------------- #
# Outcome fields for the sidecar (evaluated over the FULL negative set)
# --------------------------------------------------------------------------- #


def _tail(text: str, limit: int = 4096) -> str:
    return text.encode("utf-8", "replace")[-limit:].decode("utf-8", "replace")


def derive_outcome_fields(arts: dict[str, dict[str, Any]], negatives: dict[str, Negative]) -> dict[str, Any]:
    """The flat fields ``[outcomes]`` evaluates. ``measurement_valid`` is the conjunction, per
    negative, of: no error finding; a valid harness stamp; a harness result with no error finding;
    the pristine dist contained the mutation target; the copy lost it; harness not timed out."""
    flat: dict[str, Any] = {}
    details: dict[str, Any] = {}
    valid_all = True
    n_error = 0
    for nid, negative in negatives.items():
        art = arts[nid]
        checks = {
            "no_error_finding": art.get("error") is None,
            "harness_stamp_valid": art.get("harness_stamp_valid") is True,
            "harness_result_error_free": art.get("harness_error") is None,
            "pristine_has_target": art.get("pristine_has_target") is True,
            "mutated_lacks_target": art.get("mutated_lacks_target") is True,
            "harness_not_timed_out": art.get("harness_exit") != 124,
        }
        details[nid] = {"validity_checks": checks}
        valid_all = valid_all and all(checks.values())
        n_error += 0 if checks["no_error_finding"] else 1
        failing = list(art.get("failing_keys") or [])
        exit_code = art.get("harness_exit") if isinstance(art.get("harness_exit"), int) else -1
        flat[f"{nid}_harness_exit"] = exit_code
        flat[f"{nid}_expected_key_failed"] = negative.expected_key in failing
        # detected: the harness failed (nonzero) AND named the expected key among its failing keys
        flat[f"{nid}_detected"] = exit_code not in (0, -1) and negative.expected_key in failing
        flat[f"{nid}_failing_keys"] = ",".join(failing)
        flat[f"{nid}_negative_passed"] = art.get("outcome") is True
    flat.update({"all_units_complete": True, "n_negatives": len(negatives), "n_error_units": n_error,
                 "measurement_valid": valid_all})
    return {"flat": flat, "details": details}


# --------------------------------------------------------------------------- #
# Unit mode
# --------------------------------------------------------------------------- #


def probe_negative(
    args: argparse.Namespace, negative: Negative, env: InputEnv, *, runner: Any = None,
    harness_timeout_s: float | None = None,
) -> dict[str, Any]:
    """Copy + mutate the dist, run ONLY the negative's harness unit, read its stamp and result."""
    runner = runner or unit_runner
    rs = repl_smoke()
    neg_root = Path(args.neg_root)
    paths = neg_paths(neg_root, negative.id)
    prep = prepare_mutated_dist(Path(args.dist), paths.dist, negative, neg_root)
    dist_mutated = unit_runner.dist_hash(paths.dist)
    virtual = virtual_mutated_hash(Path(args.dist), negative.delete)
    if virtual != dist_mutated:
        raise RuntimeError(
            f"the mutated copy's dist_hash {dist_mutated} differs from the one predicted from the "
            f"pristine tree {virtual}: the copy is not the pristine dist minus {negative.delete!r}"
        )
    unit = rs.UNIT_BY_ID[negative.harness_unit]
    harness_env = rs.build_hash_env(
        argparse.Namespace(serve_dir=paths.dist, base_path=env.base_path), env.chrome_path,
        dist_hash_fn=lambda _d: dist_mutated, chrome_version_fn=lambda _p: env.chrome_version,
        driver_fn=lambda: env.driver,
    )
    paths.out.mkdir(parents=True, exist_ok=True)
    rs.clear_unit_files(paths.out, unit.id)  # never judge a stale stamp
    argv = harness_argv_prefix() + [
        negative.harness_flag, "--scenario", unit.id, "--serve-dir", str(paths.dist),
        "--out-dir", str(paths.out), "--base-path", env.base_path, "--chrome-path", env.chrome_path,
    ]
    for flag in negative.harness_neg:
        argv += ["--neg", flag]
    timeout = harness_timeout_s if harness_timeout_s is not None else unit.budget_s + DRIVER_EXTRA_S
    LOG.info("negative %s: running %s --scenario %s on %s", negative.id, negative.harness_flag, unit.id, paths.dist)
    run = runner.run_unit(argv, timeout, cwd=str(REPO_ROOT))
    state = rs.inspect_unit(paths.out, unit, rs.unit_inputs(unit, harness_env, negative.harness_neg))
    valid = bool(state["valid"])
    if valid and run.timed_out:
        LOG.warning("negative %s: the harness run_unit timed out over a VALID stamp; the stamp governs", negative.id)
    if valid:
        harness_exit: int = state["stamp"]["exit"]
    elif run.timed_out or state["has_timeout_marker"] or run.exit == 124:
        harness_exit = 124
    else:
        harness_exit = run.exit if run.exit != 0 else 1
    result = state["result"] if valid else None
    failing = list(state["failing_keys"]) if valid else []
    harness_error = (result or {}).get("error") if valid else None
    passed, reasons = negative_outcome(
        negative, stamp_valid=valid, harness_exit=harness_exit, failing_keys=failing,
        harness_error=harness_error,
    )
    return {
        "negative": negative.id, "mutation": negative.mutation, "harness_flag": negative.harness_flag,
        "harness_unit": unit.id, "expected_key": negative.expected_key,
        "delete": negative.delete, "harness_neg": list(negative.harness_neg),
        "pristine_has_target": prep["pristine_has_target"],
        "mutated_lacks_target": prep["mutated_lacks_target"],
        "dist_pristine": env.dist_pristine, "dist_mutated": dist_mutated,
        "serve_dir": str(paths.dist), "out_dir": str(paths.out), "harness_argv": argv,
        "harness_run": {"exit": run.exit, "timed_out": run.timed_out, "killed": run.killed},
        "harness_stamp_valid": valid, "harness_exit": harness_exit, "failing_keys": failing,
        "missing_keys": list(state["missing_keys"]) if valid else [],
        "harness_error": harness_error, "harness_reasons": state["reasons"],
        "outcome": passed, "outcome_reasons": reasons,
    }


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


def run_unit_mode(
    args: argparse.Namespace, *, negatives: dict[str, Negative], unit_timeout_s: float | None = None,
    harness_timeout_s: float | None = None,
) -> None:
    """Never returns: ends in ``os._exit`` (stamp.exit, or 124 from the watchdog)."""
    negative = negatives[args.unit]
    token = unit_runner.ensure_token()  # may re-exec; a no-op under run_unit
    out_dir = Path(args.out_dir)
    paths = unit_paths(out_dir, negative.id)
    paths["artifact"].parent.mkdir(parents=True, exist_ok=True)
    budget = unit_budget_s(negative) if unit_timeout_s is None else unit_timeout_s
    started = time.time()

    def on_expire() -> None:
        _rm(paths["artifact"])
        marker = {"unit": negative.id, "timeout_s": budget, "started": started, "expired": time.time()}
        try:
            unit_runner.write_atomic(paths["timeout"], json.dumps(marker).encode())
        except OSError:
            pass
        unit_runner.emit_line(json.dumps({"unit": negative.id, "status": "timeout", "timeout_s": budget}))

    watchdog = unit_runner.Watchdog(budget, on_expire)  # first act after ensure_token
    for key in ("stamp", "artifact", "timeout"):  # stamp first: never a stamp without its artifact
        _rm(paths[key])

    error: dict[str, Any] | None = None
    fields: dict[str, Any] = {}
    env: InputEnv | None = None
    dist_mutated = ""
    try:
        env = build_env(args)
        dist_mutated = virtual_mutated_hash(Path(args.dist), negative.delete)
        fields = probe_negative(args, negative, env, harness_timeout_s=harness_timeout_s)
    except Exception as exc:  # a raised driver is an `error` finding; the unit still completes
        LOG.exception("negative %s raised", negative.id)
        error = {"type": type(exc).__name__, "message": str(exc)[:2000], "traceback_tail": _tail(traceback.format_exc())}
    if env is None:  # build_env itself failed: the stamp still needs inputs (best effort)
        env = InputEnv("", "", "", "", "", "", "", getattr(args, "base_path", "/praxis/"))

    artifact: dict[str, Any] = {"negative": negative.id, "error": error}
    if error is not None:  # pre-registered fields stay present; the outcome is a failed one
        artifact.update({"harness_exit": None, "failing_keys": [], "outcome": False})
    artifact.update(fields)
    artifact.update(
        {
            "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
            "unit_timeout_s": budget, "started": started, "finished": time.time(),
        }
    )
    missing = [f for f in REQUIRED_FIELDS if f not in artifact]
    data = json.dumps(artifact, indent=1, sort_keys=True, default=str).encode()
    if not watchdog.write_result(lambda: unit_runner.write_atomic(paths["artifact"], data)):
        _sleep_forever_until_killed()

    # Bounded teardown: this process holds no browser (the harness unit had its own), so only
    # residual descendants are killed; then flush.
    try:
        survivors = unit_runner.kill_tree(os.getpid(), token)
        if survivors:
            LOG.error("descendants survived kill_tree: %s", survivors)
    except Exception:
        LOG.exception("kill_tree raised during teardown")
    _flush_all()

    exit_code = 0 if (error is None and not missing) else 1
    stamp = {
        "unit": negative.id,
        "inputs": compute_inputs(negative, env, dist_mutated, Path(args.neg_root)),
        "artifact_sha256": sha256_bytes(data), "started": started, "finished": time.time(),
        "exit": exit_code, "timeout_s": budget,
    }
    stamp_bytes = json.dumps(stamp, indent=1, sort_keys=True).encode()
    if not watchdog.commit(lambda: unit_runner.write_atomic(paths["stamp"], stamp_bytes)):
        _sleep_forever_until_killed()
    os._exit(exit_code)  # nothing runs after the stamp


# --------------------------------------------------------------------------- #
# Driver mode
# --------------------------------------------------------------------------- #


def _dry_run(args: argparse.Namespace, negatives: dict[str, Negative]) -> int:
    rs_error: str | None = None
    try:
        budgets = {n.id: {"harness_budget_s": harness_budget_s(n), "unit_timeout_s": unit_budget_s(n),
                          "driver_kill_s": unit_budget_s(n) + DRIVER_EXTRA_S} for n in negatives.values()}
    except Exception as exc:
        budgets, rs_error = {}, f"{type(exc).__name__}: {exc}"
    plan = {
        "sprint": args.sprint, "entry": str(args.entry_path), "dist": str(args.dist),
        "neg_root": str(args.neg_root), "out_dir": str(args.out_dir), "budgets": budgets,
        "budget_error": rs_error,
        "negatives": [
            {"id": n.id, "harness_flag": n.harness_flag, "harness_unit": n.harness_unit,
             "expected_key": n.expected_key, "delete": n.delete, "mutation": n.mutation,
             "serve_dir": str(neg_paths(args.neg_root, n.id).dist),
             "harness_out_dir": str(neg_paths(args.neg_root, n.id).out)}
            for n in negatives.values()
        ],
    }
    print(json.dumps(plan, indent=1))
    return 0


def run_driver(
    args: argparse.Namespace, *, negatives: dict[str, Negative], unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float | None = None, harness_timeout_s: float | None = None, runner: Any = None,
    env: InputEnv | None = None,
) -> int:
    """Run every negative's unit (resuming if asked); evaluate outcomes iff all are complete.

    Exit 0: all complete, outcome fields written. Exit 3: at least one unit incomplete, no
    outcome written. Exit 2: the environment is unusable (no dist, no chrome, no uv.lock).
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
    prefix = unit_argv_prefix if unit_argv_prefix is not None else [sys.executable, str(args.entry_path)]
    states: dict[str, dict[str, Any]] = {}
    status: dict[str, dict[str, Any]] = {}
    reused: list[dict[str, Any]] = []
    recomputed: list[str] = []
    timed_out: list[str] = []
    stale: list[dict[str, Any]] = []

    for negative in negatives.values():
        budget = unit_budget_s(negative) if unit_timeout_s is None else unit_timeout_s
        dist_mutated = virtual_mutated_hash(Path(args.dist), negative.delete)
        inputs = compute_inputs(negative, env, dist_mutated, Path(args.neg_root))
        current = inspect_unit(out_dir, negative, inputs)
        if args.resume and current["reusable"]:
            LOG.info("negative %s reused (valid stamp, exit 0, no error, fields present, outcome passed)", negative.id)
            states[negative.id] = current
            reused.append(
                {"negative": negative.id, "source": current["artifact_path"],
                 "inputs": current["stamp"]["inputs"], "artifact_sha256": current["stamp"]["artifact_sha256"]}
            )
            status[negative.id] = {"status": "reused"}
            continue
        if args.resume and current["stamp"] is not None:
            stale.append({"negative": negative.id, "mismatched": current["mismatched"], "reasons": current["reasons"]})
        paths = unit_paths(out_dir, negative.id)
        for key in ("stamp", "artifact", "timeout"):
            _rm(paths[key])
        argv = prefix + [
            "--unit", negative.id, "--out-dir", str(out_dir), "--dist", str(args.dist),
            "--neg-root", str(args.neg_root), "--base-path", args.base_path,
        ]
        if env.chrome_path:
            argv += ["--chrome-path", env.chrome_path]
        LOG.info("starting negative %s (timeout %.0f s)", negative.id, budget + DRIVER_EXTRA_S)
        outcome = runner.run_unit(argv, budget + DRIVER_EXTRA_S, cwd=str(REPO_ROOT))
        after = inspect_unit(out_dir, negative, inputs)
        states[negative.id] = after
        if after["complete"]:
            if outcome.timed_out:
                LOG.warning("negative %s: run_unit timed out over a VALID stamp; the stamp governs", negative.id)
            recomputed.append(negative.id)
            status[negative.id] = {
                "status": "recomputed", "exit": after["stamp"]["exit"], "error": after["artifact"].get("error"),
                "outcome": after["artifact"].get("outcome"), "artifact_path": after["artifact_path"],
                "artifact_sha256": after["stamp"]["artifact_sha256"], "inputs": after["stamp"]["inputs"],
            }
        else:
            if outcome.timed_out or paths["timeout"].exists() or outcome.exit == 124:
                timed_out.append(negative.id)
                status[negative.id] = {"status": "timeout", "exit": outcome.exit}
            else:
                status[negative.id] = {"status": "crashed", "exit": outcome.exit, "reasons": after["reasons"]}
            LOG.error("negative %s is INCOMPLETE: %s", negative.id, status[negative.id])

    all_complete = all(states[n].get("complete") for n in negatives)
    aggregate: dict[str, Any] = {
        "driver": "nd_sensitivity", "sprint": args.sprint, "all_units_complete": all_complete,
        "outcome_evaluated": False, "units": status, "reused": reused, "recomputed": recomputed,
        "timed_out": timed_out, "stale": stale,
        "incomplete": [n for n in negatives if not states[n].get("complete")],
        "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
        "inputs_hashed": {k: getattr(env, k) for k in ("script", "entry", "runner", "harness", "dist_pristine", "chrome", "driver")},
    }
    exit_code = 3
    if all_complete:
        arts = {n: states[n]["artifact"] for n in negatives}
        derived = derive_outcome_fields(arts, negatives)
        aggregate.update({"details": derived["details"], "outcome_fields": derived["flat"], "outcome_evaluated": True})
        results_path = os.environ.get("BTH_RESULTS_PATH")
        if results_path:
            unit_runner.write_atomic(results_path, json.dumps(derived["flat"], sort_keys=True).encode())
        exit_code = 0
    else:
        LOG.error("NOT evaluating outcomes: incomplete negatives %s", aggregate["incomplete"])
    unit_runner.write_atomic(out_dir / "result.json", json.dumps(aggregate, indent=1, sort_keys=True, default=str).encode())
    print(json.dumps(aggregate, sort_keys=True, default=str))
    return exit_code


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None, *, sprint: str, negatives: dict[str, Negative], entry_path: Path) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", default=str(REPO_ROOT / "outputs" / "nd_sensitivity" / f"sprint_{sprint}"),
                   help="Records: units/<negative>.json + stamps + result.json.")
    p.add_argument("--resume", action="store_true", help="Skip verified-complete, PASSED negatives (D17 rule).")
    p.add_argument("--unit", choices=sorted(negatives), default=None, help="Unit mode: run exactly one negative.")
    p.add_argument("--dist", default=str(DEFAULT_DIST), help="The PRISTINE built dist (never modified).")
    p.add_argument("--neg-root", default=str(DEFAULT_NEG_ROOT), help="Parent of <negative>/{dist,out}/.")
    p.add_argument("--chrome-path", default=None)
    p.add_argument("--base-path", default="/praxis/", help="URL prefix the dist copy is served under (CI: /praxis/).")
    p.add_argument("--dry-run", action="store_true", help="Print the plan; launch and hash nothing.")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    args.sprint, args.entry_path = sprint, Path(entry_path)
    return args


def main(
    argv: list[str] | None = None, *, sprint: str = "a", negatives: tuple[str, ...] = ("a",),
    entry_path: Path | None = None, unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float | None = None, harness_timeout_s: float | None = None,
) -> int:
    chosen = {n: NEGATIVES[n] for n in negatives}
    args = parse_args(argv, sprint=sprint, negatives=chosen, entry_path=entry_path or SCRIPT_PATH)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.dry_run:
        return _dry_run(args, chosen)
    if args.unit:
        run_unit_mode(args, negatives=chosen, unit_timeout_s=unit_timeout_s, harness_timeout_s=harness_timeout_s)
        return 1  # pragma: no cover
    return run_driver(args, negatives=chosen, unit_argv_prefix=unit_argv_prefix,
                      unit_timeout_s=unit_timeout_s, harness_timeout_s=harness_timeout_s)


if __name__ == "__main__":
    sys.exit(main())

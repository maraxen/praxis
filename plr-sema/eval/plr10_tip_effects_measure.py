"""PLR 1.0 tip-effect increment measurement (#5622, T63 steps 2b/2c).

Measurement instrument for spec ``260929_plr-sema-plr1-tip-effect-increment.md``
§18.9. Pre-registration: ``plr10_tip_effects_measure.bth.toml`` (committed
before any run, T63 step 1); this script implements its ``[result_schema]``
exactly and never edits its ``[outcomes]``.

Seven UNITS, each in its own subprocess with its own timeout (30 min) and NO
whole-run timeout -- the preemption-safe, resumable scheduling the owner rule of
260929 requires (scheduling only; it never changes an outcome criterion):

``real``      the shipped :func:`oracle_replay.main` run (via
              :func:`plr10_characterize.run_arm`), with THREE chain-composed
              captures (findings, lowered bytecode, the ``obs:`` env members)
              persisted beside its summary so the ``:338`` attribution and the
              independent scan can be recomputed from disk;
``all_safe``  the negative control arm (every static verdict forced ``safe``);
``m1 m2 p3a m3``  one ``tip_mutants.py --classes <c>`` run each;
``v1``        ``volume_mutants.py``.

Each unit persists ``units/<unit>.json`` and then ``units/<unit>.stamp.json``
(``{unit, inputs, output_sha256}``), the stamp only after the output is fully
written, flushed and renamed into place. A re-invocation reuses a unit ONLY if
its stamp's inputs equal this invocation's AND the output file's sha256 equals the
stamp's; otherwise it recomputes. ``result.json`` (exactly the sidecar's
``[result_schema]`` keys, plus a ``units`` provenance block that is OUTSIDE the
schema) is written only when all seven units are complete; a timed-out or crashed
unit is recorded ``incomplete``, never retried in the same invocation, and no
``result.json`` exists while any is incomplete (FAIL by construction). Mutant
fields are read from the tools' REPORT JSON, never their exit codes.

Function map (spec step -> code):

* 2b, arms .......... :func:`compute_real`, :func:`compute_all_safe`,
                      :class:`RealArmCaptures`, :func:`build_real_payload`
* 2b, X2 producers .. :class:`RealArmCaptures` (wraps ``oc.observation_env_members``,
                      ``oc.FINDINGS_SINK``, ``oc.LOWERED_SINK``), :func:`check_four_way`,
                      :func:`assert_no_loop`
* 2b, ``:338`` ...... :func:`analyze_338` (analyzer-side; uses
                      ``rack_topology_disturbers``/``rack_topology_clauses``/
                      ``tip_racks_decline_reason``)
* 2b, M8 ............ :func:`independent_scan` (imports neither of those functions)
* 2b, mutants ....... :func:`compute_tip_mutants`, :func:`compute_v1`,
                      :func:`mutant_fields`
* 2b, parity ........ :func:`baseline_parity`
* 2b, assemble ...... :func:`assemble_result`, :func:`validate_result`
* 2c, scheduling .... :func:`run_units`, :func:`persist_unit`, :func:`check_reusable`,
                      :func:`collect_input_hashes`, :func:`make_subprocess_runner`,
                      :func:`run`, :func:`main`

Usage (from the plr10 root; the registered run is wrapped by ``bth run``)::

    uv run --no-sync python plr-sema/eval/plr10_tip_effects_measure.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --sidecar training/assemble/out/corpus_p25_sidecar.jsonl \\
        --crosscheck training/out/corpus_p23_floor.jsonl \\
        --crosscheck training/overlay_gen/out/overlay_full.jsonl \\
        --out-dir outputs/plr-sema/plr10_tip_effects_260929/
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import datetime
import functools
import hashlib
import importlib.util
import json
import logging
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = _EVAL_DIR.parents[1]
sys.path.insert(0, str(_EVAL_DIR))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

if importlib.util.find_spec("verify") is None:
    raise SystemExit(
        "plr10_tip_effects_measure: 'verify' is not importable; run under the project venv "
        "(e.g. `uv run --no-sync python plr-sema/eval/plr10_tip_effects_measure.py ...`)"
    )

import oracle_common as oc  # noqa: E402
import plr10_characterize as pc  # noqa: E402

log = logging.getLogger("plr10_tip_effects_measure")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The sidecar's ``[result_schema]``, verbatim and in its order
#: (``test_plr10_tip_effects_measure.py`` checks this against the TOML file).
RESULT_SCHEMA: dict[str, type] = {
    "control_fires": bool,
    "real_rows_executed": int,
    "real_rows_setup_error": int,
    "real_operations_executed": int,
    "real_unsound": int,
    "real_unsound_scoped": int,
    "real_totality_violations": int,
    "real_check_graph_exceptions": int,
    "real_n_operations_scope_verdict_safe": int,
    "real_pick_up_tips_scope_safe": int,
    "real_pick_up_tips_n_ops": int,
    "real_n_findings_decided": int,
    "real_n_tip_racks_decided": int,
    "real_n_tip_racks_attempted": int,
    "n_338_pickups_attempted": int,
    "n_338_pickups_safe": int,
    "n_338_declined_kind": int,
    "n_338_declined_observation": int,
    "n_338_declined_deck": int,
    "n_338_declined_topology_prefix": int,
    "n_338_declined_topology_loop": int,
    "n_338_declined_unattributed": int,
    "n_338_safe_with_reason": int,
    "n_pickups_with_preceding_disturber_indep": int,
    "all_safe_unsound": int,
    "all_safe_operations_executed": int,
    "runtime_raised_ops_all_safe_arm": int,
    "m1_will_fail_fired": bool,
    "m2_will_fail_fired": bool,
    "m1_attempted": int,
    "m1_achieved": int,
    "m2_attempted": int,
    "m2_achieved": int,
    "p3a_attempted": int,
    "p3a_achieved": int,
    "mutants_hard_violations_excl_p3a_floor": int,
    "mutants_unsound": int,
    "mutants_criterion_ii": int,
    "m3_attempted": int,
    "runtime_raised_m3": int,
    "static_338_safe_on_m3": int,
    "v1_attempted": int,
    "v1_achieved": int,
    "v1_gate_passed": bool,
    "load_state_channel_effect": str,
    "baseline_divergences": int,
    "baseline_intended_divergences": int,
    "baseline_parity_matched": int,
    "baseline_parity_total": int,
    "n_ops_load_state": int,
}

UNITS: tuple[str, ...] = ("real", "all_safe", "m1", "m2", "p3a", "m3", "v1")
#: unit name -> the tip_mutants class it runs (and the report's `by_class` key).
TIP_UNIT_CLASS: dict[str, str] = {
    "m1": "m1_remove_pickup",
    "m2": "m2_duplicate_pickup",
    "p3a": "p3a_pickup_already_held",
    "m3": "m3_lid_on_tip_rack",
}
V1_CLASS = "v1_overdraw_dispense"
#: 30 minutes per unit (§18.9: "a judgement, about 10x fd63e9cd's ~148 s"). No whole-run timeout exists.
DEFAULT_UNIT_TIMEOUT_S = 30 * 60.0

RESULT_NAME = "result.json"
DETAIL_NAME = "detail.json"
INCOMPLETE_NAME = "incomplete.json"
UNITS_DIRNAME = "units"
DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"
DEFAULT_BASELINE = REPO_ROOT / "plr-sema" / "tests" / "fixtures" / "channel_effect_baseline.json"

#: The `:338` site, resolved BY SYMBOL from the shipped table (the file/line move with every PLR bump).
SITE_338_SYMBOL = ("_check_tip_racks_available", "ValueError", "not rack._available_for_tip_handling")
SITE_338_QUALNAME = SITE_338_SYMBOL[0]
PICKUP = "pick_up_tips"
CHATTERBOX_RUNNER = REPO_ROOT / "praxis" / "backend" / "core" / "simulation" / "chatterbox_runner.py"
PYLABROBOT_DIR = REPO_ROOT / "external" / "pylabrobot"
#: Paths whose modified/untracked state refuses a run (everything the units execute that is not in the PLR submodule).
#: ``training/verify/deck.py`` loads ``chatterbox_runner.py`` BY PATH, so its directory is in the list.
CODE_PATHS = ("plr-sema/src", "plr-sema/eval", "plr-sema/data", "training", "praxis/backend/core/simulation")
EXECUTION_ORDER_REASON = "execution_order"


class PositionalCorrelationError(RuntimeError):
    """The four-way length invariant (eligible rows, findings, lowered, env) broke."""


class LoopInTier1Stream(RuntimeError):
    """A lowered tier-1 stream contains a loop instruction (clause (ii) is not computed by this script)."""


class InstrumentInvalid(RuntimeError):
    """The instrument cannot honestly report on this input: the run is INCOMPLETE and no ``result.json`` is written (the
    same FAIL-by-construction treatment as an analyzer exception, ``real_check_graph_exceptions = 0`` in H). It never
    changes a registered ``[outcomes]`` criterion; it stops the instrument reporting on invalid input."""


class MutantAnalyzerError(InstrumentInvalid):
    """A mutant row crashed (the analyzer raised on it, or the runtime harness itself raised): counting such a row toward
    ``runtime_raised_m3`` or any floor would let a control pass on a crash."""


class ArmDisagreement(InstrumentInvalid):
    """The ``real`` and ``all_safe`` units disagree on a runtime-side denominator (they differ only in static verdicts)."""


class DirtyTreeError(RuntimeError):
    """Refusal to run: code the units execute is modified/untracked, so the stamps could not identify it."""


class UnitTimeout(Exception):
    def __init__(self, unit: str, elapsed_s: float, timeout_s: float) -> None:
        super().__init__(f"unit {unit!r} timed out after {elapsed_s:.1f}s (limit {timeout_s:.1f}s)")
        self.unit, self.elapsed_s, self.timeout_s = unit, elapsed_s, timeout_s


class UnitFailed(Exception):
    def __init__(self, unit: str, detail: str) -> None:
        super().__init__(f"unit {unit!r} failed: {detail}")
        self.unit, self.detail = unit, detail


# ---------------------------------------------------------------------------
# hashing / atomic persistence (2c)
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, obj: Any) -> None:
    """Write ``obj`` as JSON to ``path`` so that ``path`` is either absent/old or complete: temp file in the
    same directory, flushed and fsync'd, then ``os.replace``d into place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def unit_paths(out_dir: Path, unit: str) -> tuple[Path, Path]:
    d = out_dir / UNITS_DIRNAME
    return d / f"{unit}.json", d / f"{unit}.stamp.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout


def _pylabrobot_head() -> str:
    return subprocess.run(
        ["git", "-C", str(PYLABROBOT_DIR), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def check_clean_tree(repo_root: Path = REPO_ROOT) -> None:
    """REFUSE to run (:class:`DirtyTreeError`) when ``git status --porcelain --untracked-files=all`` shows any modified or
    untracked file under :data:`CODE_PATHS`, or when the PLR submodule (``external/pylabrobot``) has a non-empty
    ``git status --porcelain``. Stamps identify code by git HEAD (+ a diff hash for tracked edits); an untracked module or a
    dirty submodule worktree would slip past both, so a stale unit could be reused. Unrelated untracked paths (``.claude/``,
    ``.mcp.json``, ``.praxia/``, ``outputs/`` ...) are outside the pathspec, and bathos ``*.bth.lock.toml`` files are
    excluded explicitly. Review MAJOR-2."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *CODE_PATHS],
        cwd=repo_root, check=True, capture_output=True, text=True,
    ).stdout
    dirty = [ln for ln in out.splitlines() if ln.strip() and not ln[3:].strip().strip('"').endswith(".bth.lock.toml")]
    sub = subprocess.run(
        ["git", "-C", str(repo_root / "external" / "pylabrobot"), "status", "--porcelain"],
        check=False, capture_output=True, text=True,
    )
    if sub.returncode != 0:
        dirty.append(f"external/pylabrobot: `git status` failed ({sub.stderr.strip()[:200]})")
    dirty.extend(f"external/pylabrobot (submodule): {ln}" for ln in sub.stdout.splitlines() if ln.strip())
    if dirty:
        shown = "\n  ".join(dirty[:30])
        raise DirtyTreeError(
            f"REFUSING TO RUN: {len(dirty)} modified/untracked path(s) under {list(CODE_PATHS)} or the PLR submodule:\n"
            f"  {shown}\n"
            "Commit them (the instrument, tests and any code under test must be committed) and re-run; a unit's stamp "
            "could not identify uncommitted code, so a stale unit could be reused."
        )


def _examples_digest() -> str:
    """The mutant units' extra base populations: ``training/examples/*.json`` and ``plr-sema/eval/fixtures/*.json``."""
    h = hashlib.sha256()
    for d in (REPO_ROOT / "training" / "examples", _EVAL_DIR / "fixtures"):
        for p in sorted(d.glob("*.json")) if d.is_dir() else ():
            h.update(p.relative_to(REPO_ROOT).as_posix().encode())
            h.update(b"\0")
            h.update(sha256_file(p).encode())
            h.update(b"\0")
    return h.hexdigest()


def collect_input_hashes(
    *,
    corpus: Sequence[str],
    sidecar: str | None,
    crosscheck: Sequence[str],
    contracts: Path,
    limit: int | None,
    git_head: str | None = None,
    code_diff_sha256: str | None = None,
    mutant_examples_sha256: str | None = None,
    pylabrobot_head: str | None = None,
    chatterbox_runner_sha256: str | None = None,
) -> dict[str, Any]:
    """The stamp's ``inputs`` block: sha256 of ``derived_contracts.json``, of each corpus file, of the sidecar input and of
    each crosscheck file, plus the git ``HEAD`` sha (§18.9). Three STRICTNESS additions -- each can only make reuse rarer,
    never wrong: ``limit`` (a smoke run's output must not be reused by a full one), ``code_diff_sha256`` (uncommitted edits
    under ``plr-sema/{src,eval,data}`` and ``training/`` that HEAD does not capture) and ``mutant_examples_sha256`` (the
    fixture directories the mutant units read besides the corpus), plus (review MAJOR-2) the PLR submodule's own HEAD and
    the sha256 of ``chatterbox_runner.py`` (loaded by path from ``training/verify/deck.py``, so in no import graph). The
    last five are injectable for tests."""
    if git_head is None:
        git_head = _git("rev-parse", "HEAD").strip()
    if code_diff_sha256 is None:
        code_diff_sha256 = sha256_bytes(
            _git("diff", "HEAD", "--", *CODE_PATHS).encode()
        )
    if mutant_examples_sha256 is None:
        mutant_examples_sha256 = _examples_digest()
    if pylabrobot_head is None:
        pylabrobot_head = _pylabrobot_head()
    if chatterbox_runner_sha256 is None:
        chatterbox_runner_sha256 = sha256_file(CHATTERBOX_RUNNER)
    return {
        "derived_contracts_json": sha256_file(contracts),
        "corpus": {str(p): sha256_file(Path(p)) for p in corpus},
        "sidecar": {str(sidecar): sha256_file(Path(sidecar))} if sidecar else {},
        "crosscheck": {str(p): sha256_file(Path(p)) for p in crosscheck},
        "git_head": git_head,
        "code_diff_sha256": code_diff_sha256,
        "mutant_examples_sha256": mutant_examples_sha256,
        "pylabrobot_head": pylabrobot_head,
        "chatterbox_runner_sha256": chatterbox_runner_sha256,
        "limit": limit,
    }


def persist_unit(
    out_dir: Path, unit: str, payload: dict[str, Any], inputs: Mapping[str, Any], *, elapsed_s: float | None = None
) -> dict[str, Any]:
    """Write ``units/<unit>.json`` (atomically), THEN the completion stamp -- so a stamp never exists without a fully
    written output. Returns the stamp."""
    if payload.get("unit", unit) != unit:
        raise ValueError(f"payload names unit {payload.get('unit')!r}, expected {unit!r}")
    payload = {**payload, "unit": unit}
    out_path, stamp_path = unit_paths(out_dir, unit)
    write_json_atomic(out_path, payload)
    stamp = {
        "unit": unit,
        "inputs": json.loads(json.dumps(inputs)),
        "output_sha256": sha256_file(out_path),
        "elapsed_s": elapsed_s,
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    write_json_atomic(stamp_path, stamp)
    return stamp


def check_reusable(out_dir: Path, unit: str, inputs: Mapping[str, Any]) -> tuple[bool, str]:
    """``(reusable, reason)``. Reusable ONLY when the stamp exists and names this unit, its input hashes equal ``inputs``
    (this invocation's), the output file exists, and the output's sha256 equals the stamp's."""
    out_path, stamp_path = unit_paths(out_dir, unit)
    if not stamp_path.is_file():
        return False, "no stamp"
    try:
        stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, f"unreadable stamp ({e})"
    if not isinstance(stamp, dict) or stamp.get("unit") != unit:
        return False, "stamp names a different unit"
    if stamp.get("inputs") != json.loads(json.dumps(inputs)):
        return False, "input hashes differ from this invocation's"
    if not out_path.is_file():
        return False, "output file missing"
    if sha256_file(out_path) != stamp.get("output_sha256"):
        return False, "output sha256 does not match the stamp (corrupted or rewritten)"
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except ValueError as e:
        return False, f"output unreadable ({e})"
    if not isinstance(payload, dict) or payload.get("unit") != unit:
        return False, "output names a different unit"
    return True, "stamp inputs and output sha256 match"


def _discard_unit(out_dir: Path, unit: str) -> None:
    """Remove a unit's stale files, STAMP FIRST: a crash mid-recompute then leaves an output with no stamp (not reusable),
    never a stale-but-matching pair."""
    out_path, stamp_path = unit_paths(out_dir, unit)
    for p in (stamp_path, out_path, out_path.with_name(f"{unit}.worker.json")):
        p.unlink(missing_ok=True)


Runner = Callable[[str], dict[str, Any]]


@dataclass
class UnitsOutcome:
    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def incomplete(self) -> list[str]:
        return [u for u, r in self.records.items() if r["status"] == "incomplete"]

    @property
    def complete(self) -> bool:
        return not self.incomplete


def run_units(
    out_dir: Path, inputs: Mapping[str, Any], runner: Runner, *, units: Sequence[str] = UNITS
) -> UnitsOutcome:
    """Reuse or compute each unit, in order. ``runner(unit)`` returns the unit's payload or raises
    :class:`UnitTimeout`/:class:`UnitFailed`; either is recorded ``incomplete`` (never retried here) and the remaining
    units still run, so one re-invocation recomputes only what is missing. Any other exception (``KeyboardInterrupt``, a
    kill) propagates and leaves every already-persisted unit intact and reusable."""
    outcome = UnitsOutcome()
    for unit in units:
        out_path, _stamp_path = unit_paths(out_dir, unit)
        ok, why = check_reusable(out_dir, unit, inputs)
        if ok:
            stamp = json.loads(unit_paths(out_dir, unit)[1].read_text(encoding="utf-8"))
            outcome.records[unit] = {
                "status": "reused",
                "source": str(out_path.resolve()),
                "inputs": stamp["inputs"],
                "output_sha256": stamp["output_sha256"],
                "elapsed_s": stamp.get("elapsed_s"),
            }
            log.info("unit %-8s REUSED (%s)", unit, why)
            continue
        log.info("unit %-8s COMPUTE (%s)", unit, why)
        _discard_unit(out_dir, unit)
        t0 = time.monotonic()
        try:
            payload = runner(unit)
        except UnitTimeout as e:
            log.error("unit %-8s TIMEOUT: %s", unit, e)
            outcome.records[unit] = {
                "status": "incomplete", "reason": "timeout", "elapsed_s": e.elapsed_s, "timeout_s": e.timeout_s,
            }
            continue
        except UnitFailed as e:
            log.error("unit %-8s FAILED: %s", unit, e)
            outcome.records[unit] = {
                "status": "incomplete", "reason": "crash", "detail": e.detail[-2000:],
                "elapsed_s": time.monotonic() - t0,
            }
            continue
        elapsed = time.monotonic() - t0
        stamp = persist_unit(out_dir, unit, payload, inputs, elapsed_s=elapsed)
        outcome.records[unit] = {
            "status": "computed",
            "source": str(out_path.resolve()),
            "inputs": stamp["inputs"],
            "output_sha256": stamp["output_sha256"],
            "elapsed_s": elapsed,
        }
        log.info("unit %-8s COMPUTED in %.1fs", unit, elapsed)
    return outcome


def load_payload(out_dir: Path, unit: str) -> dict[str, Any]:
    return json.loads(unit_paths(out_dir, unit)[0].read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# subprocess runner (2c: one process + one timeout per unit)
# ---------------------------------------------------------------------------


def make_subprocess_runner(
    cmd_for_unit: Callable[[str, Path], list[str]], out_dir: Path, *, timeout_s: float
) -> Runner:
    """A :data:`Runner` that runs ``cmd_for_unit(unit, worker_output_path)`` in its OWN process (new session, so a timeout
    kills the whole group) with its OWN ``timeout_s``. The worker writes its payload to ``worker_output_path``; this
    process reads it back. Exit code 0 with no payload file is a crash. ``BTH_RESULTS_PATH`` is removed from the child's
    environment (``oracle_replay.main`` would write its own ``summary_flat`` there)."""

    def runner(unit: str) -> dict[str, Any]:
        worker_out = out_dir / UNITS_DIRNAME / f"{unit}.worker.json"
        worker_log = out_dir / UNITS_DIRNAME / f"{unit}.log"
        worker_out.parent.mkdir(parents=True, exist_ok=True)
        worker_out.unlink(missing_ok=True)
        env = {k: v for k, v in os.environ.items() if k != "BTH_RESULTS_PATH"}
        t0 = time.monotonic()
        with worker_log.open("w", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                cmd_for_unit(unit, worker_out), stdout=lf, stderr=subprocess.STDOUT, env=env, start_new_session=True
            )
            try:
                rc = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                raise UnitTimeout(unit, time.monotonic() - t0, timeout_s) from None
        if rc != 0:
            tail = worker_log.read_text(encoding="utf-8", errors="replace")[-1500:]
            raise UnitFailed(unit, f"exit code {rc}; log tail:\n{tail}")
        if not worker_out.is_file():
            raise UnitFailed(unit, "worker exited 0 but wrote no payload")
        payload = json.loads(worker_out.read_text(encoding="utf-8"))
        worker_out.unlink()
        return payload

    return runner


# ---------------------------------------------------------------------------
# lowered-bytecode (de)serialisation, invariants (2b, X2)
# ---------------------------------------------------------------------------


def bytecode_to_json(bc: Any) -> dict[str, Any]:
    """A lowered ``Bytecode`` as ``{"instructions": [<canonical instruction obj>...], "origin": {pc: local_idx}}``. The
    instruction objects are ``ir.canonical_text``'s own lines (one JSON object per instruction, pc == list index)."""
    from plr_sema.check import ir

    text = ir.canonical_text(bc)
    instructions = [json.loads(line) for line in text.split("\n")] if text else []
    return {
        "instructions": instructions,
        "origin": {str(pc): local for pc, local in (bc.sideband.get("origin") or {}).items()},
    }


def instructions_from_json(objs: Sequence[Mapping[str, Any]]) -> tuple[Any, ...]:
    """Inverse of :func:`bytecode_to_json`'s ``instructions`` (round-trips ``canonical_text``)."""
    from plr_sema.check import ir

    out: list[Any] = []
    for o in objs:
        op = o["op"]
        if op == "CALL":
            out.append(
                ir.Call(
                    receiver=o["receiver"], receiver_type=o["receiver_type"], method=o["method"],
                    kwargs={k: ir.value_from_json(v) for k, v in o["kwargs"].items()},
                )
            )
        elif op == "RESOURCE":
            out.append(
                ir.Resource(
                    slot=o["slot"], type=o["type"], element_type=o["element_type"], is_container=o["is_container"],
                    is_parameter=o["is_parameter"], parents=tuple(o["parents"]),
                    grid=tuple(o["grid"]) if o["grid"] is not None else None,
                )
            )
        elif op == "LOOP":
            out.append(ir.Loop(trip=o["trip"]))
        elif op == "BRANCH":
            out.append(ir.Branch())
        elif op == "ELSE":
            out.append(ir.Else())
        elif op == "END":
            out.append(ir.End())
        elif op == "WIDEN":
            out.append(ir.Widen(reason=o["reason"]))
        else:
            raise ValueError(f"unrecognized instruction op {op!r}")
    return tuple(out)


def check_four_way(n_eligible: int, n_findings: int, n_lowered: int, n_env: int) -> None:
    """§18.9 item 7's FOUR-way length invariant, extending ``t30_measure.py``'s three-way precedent: the rows that reached
    ``run_static_calls`` (report rows with neither ``no_call_reason`` nor ``skip_reason``), and the number of times
    ``FINDINGS_SINK``, ``LOWERED_SINK`` and the wrapped ``observation_env_members`` fired, must all be equal -- the
    captures are correlated BY POSITION. A mismatch raises: the unit crashes, no ``result.json`` is written, the outcome
    is FAIL by construction."""
    if not (n_eligible == n_findings == n_lowered == n_env):
        raise PositionalCorrelationError(
            "positional correlation invariant broken: "
            f"{n_eligible} eligible rows reached oracle_replay's Static section, FINDINGS_SINK fired {n_findings} times, "
            f"LOWERED_SINK fired {n_lowered} times, observation_env_members fired {n_env} times -- all four must match "
            "1:1 in row order; oracle_replay/oracle_common's row processing must have changed under this script."
        )


def assert_no_loop(row_id: str, instructions: Sequence[Any]) -> None:
    """§18.9 item 7: no lowered tier-1 stream may contain a loop instruction (an ``ir.Loop`` anywhere in
    ``bc.instructions``, or a persisted ``{"op": "LOOP"}``). Under this assertion ``rack_topology_loop_ok`` is ``True`` for
    every operation and ``n_338_declined_topology_loop = 0`` holds by construction; if a loop ever appears the script raises
    with the row id and pc -- FAIL-with-cause, never a silent ``loop_ok = True``. A synthetic ``has_loops`` wrap lowers to
    an ``ir.Loop`` preceded by ``Widen(reason="has_loops")`` and is caught the same way."""
    from plr_sema.check import ir

    for at_pc, instr in enumerate(instructions):
        is_loop = isinstance(instr, ir.Loop) or (isinstance(instr, Mapping) and instr.get("op") == "LOOP")
        if is_loop:
            raise LoopInTier1Stream(
                f"row {row_id!r} pc {at_pc}: a lowered tier-1 stream contains a loop instruction; this script does not compute "
                "the rack-topology loop clause (ii) -- extending it is a named follow-up"
            )


def _site_string(plr_site: Any) -> str:
    return "<none>" if plr_site is None else f"{plr_site.file}:{plr_site.lineno}:{plr_site.qualname}"


class RealArmCaptures:
    """The three chain-composed captures of the ``real`` arm (§18.9 item 7, X2).

    * ``findings`` -- ``oc.FINDINGS_SINK`` (``(row_id, findings)``), chain-composed with the prior sink;
    * ``lowered`` -- ``oc.LOWERED_SINK`` (``(row_id, bc, bc_with_o1, not_planned, element_types)``), likewise;
    * ``env`` -- a wrapper around ``oc.observation_env_members``, which ``run_static_calls`` calls as a module global once
      per row, unconditionally, before lowering: it calls the original, appends its return value, and returns it unchanged.
      (Neither sink carries ``env``; patching ``oc.run_runtime`` would intercept nothing, because ``oracle_replay`` imports
      it by name.)

    All three are restored in ``finally``. Within one ``run_static_calls`` call the order is env -> lowered -> findings, so
    the three lists correlate by position; :func:`check_four_way` asserts it. ``run_static_calls`` is unchanged.
    """

    def __init__(self) -> None:
        self.findings: list[tuple[str, tuple[Any, ...]]] = []
        self.lowered: list[tuple[str, Any, Any, list[int], dict[str, Any]]] = []
        self.env: list[frozenset[str]] = []

    @contextlib.contextmanager
    def install(self) -> Iterator[RealArmCaptures]:
        prior_findings, prior_lowered, prior_env = oc.FINDINGS_SINK, oc.LOWERED_SINK, oc.observation_env_members

        def _findings(row_id: str, findings: tuple[Any, ...]) -> None:
            self.findings.append((row_id, findings))
            if prior_findings is not None:
                prior_findings(row_id, findings)

        def _lowered(row_id: str, bc: Any, bc_with_o1: Any, not_planned: list[int], element_types: dict[str, Any]) -> None:
            self.lowered.append((row_id, bc, bc_with_o1, not_planned, element_types))
            if prior_lowered is not None:
                prior_lowered(row_id, bc, bc_with_o1, not_planned, element_types)

        @functools.wraps(prior_env)
        def _env(*args: Any, **kwargs: Any) -> frozenset[str]:
            members = prior_env(*args, **kwargs)
            self.env.append(members)
            return members

        oc.FINDINGS_SINK, oc.LOWERED_SINK, oc.observation_env_members = _findings, _lowered, _env
        try:
            yield self
        finally:
            oc.FINDINGS_SINK, oc.LOWERED_SINK, oc.observation_env_members = prior_findings, prior_lowered, prior_env


def _analyzable(row: Mapping[str, Any]) -> bool:
    """``oracle_replay``'s ``analyzable_results``: executed (no ``no_call_reason``/``skip_reason``) and not a setup error
    (every index unplanned)."""
    if row.get("no_call_reason") is not None or row.get("skip_reason") is not None:
        return False
    not_planned = row.get("not_planned_indices") or []
    return not (not_planned and len(not_planned) == len(row.get("calls") or []))


def build_real_payload(report: Mapping[str, Any], captures: RealArmCaptures) -> dict[str, Any]:
    """The ``real`` unit's persisted output: the report figures the schema needs, and the per-row captures (findings,
    lowered bytecode, env members) the ``:338`` attribution and the independent scan are recomputed from. Hard-asserts the
    four-way length invariant and the no-loop invariant."""
    rows = report["rows"]
    eligible = [r for r in rows if r.get("no_call_reason") is None and r.get("skip_reason") is None]
    check_four_way(len(eligible), len(captures.findings), len(captures.lowered), len(captures.env))

    cap_rows: list[dict[str, Any]] = []
    for report_row, (fid, findings), (lid, bc, _bc_o1, not_planned, _et), env in zip(
        eligible, captures.findings, captures.lowered, captures.env, strict=True
    ):
        record_id = report_row["record_id"]
        if not (fid == lid == record_id):
            raise PositionalCorrelationError(
                f"row id mismatch at a captured position: FINDINGS_SINK {fid!r}, LOWERED_SINK {lid!r}, report {record_id!r}"
            )
        assert_no_loop(record_id, bc.instructions)
        bcj = bytecode_to_json(bc)
        cap_rows.append(
            {
                "record_id": record_id,
                "calls": list(report_row["calls"]),
                "not_planned": sorted(not_planned),
                "env": sorted(env),
                "findings": [
                    {
                        "op": f.operation_id,
                        "verdict": f.verdict.value,
                        "site": _site_string(f.plr_site),
                        "reason": f.reason or "",
                    }
                    for f in findings
                ],
                "instructions": bcj["instructions"],
                "origin": bcj["origin"],
            }
        )

    ops_by_method: collections.Counter[str] = collections.Counter()
    for r in rows:
        if _analyzable(r):
            ops_by_method.update(r["calls"])
    sf = report["summary_flat"]
    if sum(ops_by_method.values()) != sf["operations_executed"]:
        raise RuntimeError(
            f"per-method operation count {sum(ops_by_method.values())} != summary_flat.operations_executed "
            f"{sf['operations_executed']}: the analyzable-row predicate no longer matches oracle_replay's"
        )
    if sf["rows_executed"] > 0 and not report.get("scope_verdict_by_method"):
        raise RuntimeError("scope_verdict_by_method is empty on a run that executed rows (oracle_replay's positional check failed)")
    return {
        "unit": "real",
        "summary_flat": sf,
        "n_tip_racks_decided": report["n_tip_racks_decided"],
        "scope_verdict_by_method": report["scope_verdict_by_method"],
        "n_findings_by_reason": report.get("n_findings_by_reason", {}),
        "wall_elapsed_s": report.get("wall_elapsed_s"),
        "n_ops_by_method": dict(sorted(ops_by_method.items())),
        "captures": {"n_eligible": len(eligible), "rows": cap_rows},
    }


# ---------------------------------------------------------------------------
# unit workers (run inside the unit's own subprocess)
# ---------------------------------------------------------------------------


def _arm_kwargs(args: argparse.Namespace, report_path: Path) -> dict[str, Any]:
    return {
        "corpus": args.corpus, "sidecar": args.sidecar, "crosscheck": args.crosscheck,
        "contracts": args.contracts, "limit": args.limit, "report_path": report_path,
    }


def compute_real(args: argparse.Namespace) -> dict[str, Any]:
    report_path = args.out_dir / UNITS_DIRNAME / pc.REAL_REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    captures = RealArmCaptures()
    report = pc.run_arm(**_arm_kwargs(args, report_path), patch=captures.install)
    payload = build_real_payload(report, captures)
    payload["report_artifact"] = {"path": str(report_path), "sha256": sha256_file(report_path)}
    return payload


def compute_all_safe(args: argparse.Namespace) -> dict[str, Any]:
    report_path = args.out_dir / UNITS_DIRNAME / pc.ALL_SAFE_REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = pc.run_arm(**_arm_kwargs(args, report_path), patch=pc.all_safe_static_verdicts)
    return {
        "unit": "all_safe",
        "summary_flat": report["summary_flat"],
        "runtime_raised_ops": pc.runtime_raised_ops(report),
        "report_artifact": {"path": str(report_path), "sha256": sha256_file(report_path)},
    }


def _read_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"mutant tool wrote no report at {path} (its exit code is not consulted)")
    return json.loads(path.read_text(encoding="utf-8"))


def mutant_crash_count(summary: Mapping[str, Any]) -> int:
    """Rows of one class that CRASHED. ``n_error`` cannot be used as is: it also counts every construction-skipped row (whose
    ``error`` is "mutation could not be constructed"). ``tip_mutants`` reports the split directly (``n_static_error`` --
    the analyzer raised -- and ``n_runtime_harness_error``); ``volume_mutants`` does not, so for it the analyzer crashes are
    ``n_error - n_construction_skipped`` (its runtime-harness failures are indistinguishable from construction skips)."""
    if "n_static_error" in summary:
        return int(summary["n_static_error"]) + int(summary["n_runtime_harness_error"])
    return int(summary["n_error"]) - int(summary["n_construction_skipped"])


def assert_no_mutant_errors(unit: str, summary: Mapping[str, Any]) -> None:
    n = mutant_crash_count(summary)
    if n > 0:
        raise MutantAnalyzerError(
            f"unit {unit!r}: {n} mutant row(s) crashed (n_error={summary['n_error']}, "
            f"n_construction_skipped={summary['n_construction_skipped']}); the instrument will not report on a class whose "
            "analyzer or harness raised -- fix the crash and re-run under the same sidecar"
        )


def compute_tip_mutants(unit: str, args: argparse.Namespace) -> dict[str, Any]:
    """``tip_mutants.py --classes <one class>``: the report JSON is read back; the tool's exit code (1 on ANY hard
    violation, p3a's known floor failure included) is never consulted."""
    import tip_mutants

    report_path = args.out_dir / UNITS_DIRNAME / f"{unit}.mutants_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.unlink(missing_ok=True)
    argv = ["--corpus", args.corpus[0], "--contracts", str(args.contracts), "--report", str(report_path),
            "--classes", TIP_UNIT_CLASS[unit]]
    if args.limit is not None:
        argv += ["--limit", str(args.limit)]
    rc = tip_mutants.main(argv)
    log.info("tip_mutants --classes %s returned rc=%s (informational; the report is what is read)", unit, rc)
    report = _read_report(report_path)
    assert_no_mutant_errors(unit, report["by_class"][TIP_UNIT_CLASS[unit]])
    return {"unit": unit, "tool": "tip_mutants", "class": TIP_UNIT_CLASS[unit], "report": report}


def compute_v1(args: argparse.Namespace) -> dict[str, Any]:
    import volume_mutants

    report_path = args.out_dir / UNITS_DIRNAME / "v1.mutants_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.unlink(missing_ok=True)
    argv = ["--corpus", args.corpus[0], "--contracts", str(args.contracts), "--report", str(report_path)]
    if args.limit is not None:
        argv += ["--limit", str(args.limit)]
    rc = volume_mutants.main(argv)
    log.info("volume_mutants returned rc=%s (informational; the report is what is read)", rc)
    report = _read_report(report_path)
    assert_no_mutant_errors("v1", report["by_class"][V1_CLASS])
    return {"unit": "v1", "tool": "volume_mutants", "class": V1_CLASS, "report": report}


def compute_unit(unit: str, args: argparse.Namespace) -> dict[str, Any]:
    if unit == "real":
        return compute_real(args)
    if unit == "all_safe":
        return compute_all_safe(args)
    if unit in TIP_UNIT_CLASS:
        return compute_tip_mutants(unit, args)
    if unit == "v1":
        return compute_v1(args)
    raise ValueError(f"unknown unit {unit!r}")


# ---------------------------------------------------------------------------
# the `:338` attribution (2b): analyzer-side, and the independent scan (M8)
# ---------------------------------------------------------------------------


def resolve_site_338(contracts: Mapping[str, Any]) -> tuple[str, dict[str, set[str]]]:
    """The `:338` site string (``file:lineno:qualname``) resolved BY SYMBOL -- ``(qualname, raises, condition)`` -- from the
    contract table, and ``{contract key: {guard kinds}}`` for every contract carrying a guard at that site. Exactly one
    distinct site string must match."""
    qualname, raises, condition = SITE_338_SYMBOL
    sites: set[str] = set()
    kinds: dict[str, set[str]] = collections.defaultdict(set)
    for key, entry in contracts.items():
        for g in entry.get("guards", ()):
            site = g.get("site") or {}
            if site.get("qualname") == qualname and g.get("raises") == raises and g.get("condition") == condition:
                sites.add(f"{site['file']}:{site['lineno']}:{site['qualname']}")
                kinds[key].add(g.get("kind", "raise_guard"))
    if len(sites) != 1:
        raise RuntimeError(f"site symbol {SITE_338_SYMBOL!r} matched {sorted(sites)}")
    return next(iter(sites)), dict(kinds)


def _real_idx_to_pc(row: Mapping[str, Any]) -> dict[int, int]:
    """``{call_sequence index: pc}`` for the row's planned calls, from the persisted origin map (``"setup"`` for the
    prepended reset, else the local index among the PLANNED calls)."""
    n_calls = len(row["calls"])
    unplanned = set(row["not_planned"])
    planned = [i for i in range(n_calls) if i not in unplanned]
    return {planned[int(local)]: int(pc) for pc, local in row["origin"].items() if local != "setup"}


def _op_index(op_id: str) -> int | None:
    try:
        return int(op_id.split("_", 1)[1])
    except (IndexError, ValueError):
        return None


def analyze_338(rows: Sequence[Mapping[str, Any]], contracts_payload: Mapping[str, Any]) -> dict[str, Any]:
    """The analyzer-side ``:338`` decline attribution (§18.9 item 7, D-2 option (B)).

    Scope: planned ``pick_up_tips`` operations, on the ``real`` arm, that carry a ``:338`` finding. Each non-``SAFE`` one is
    attributed to the FIRST failing conjunct by calling the SAME exported :func:`tip_racks_decline_reason` that the site
    rule itself decides through, over (a) the wrapped ``observation_env_members`` list, (b) the guard's ``kind`` read from the
    contract, and (c) the topology clauses computed from ``rack_topology_disturbers`` over the lowered bytecode (the
    ``bc`` ``LOWERED_SINK`` delivered). ``rack_topology_loop_ok`` is ``True`` for every operation: the no-``ir.Loop``
    assertion (:func:`assert_no_loop`) is re-checked here over the persisted stream.
    """
    from plr_sema.check import ir
    from plr_sema.check import predicate as pred

    contracts = contracts_payload["contracts"]
    receiver_states = contracts_payload["receiver_state"]
    site_338, kinds_by_contract = resolve_site_338(contracts)
    execution_order = getattr(ir, "_EXECUTION_ORDER", EXECUTION_ORDER_REASON)

    counts: collections.Counter[str] = collections.Counter()
    attempted = safe = safe_with_reason = 0
    declined_examples: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    per_op: list[dict[str, Any]] = []

    for row in rows:
        instructions = instructions_from_json(row["instructions"])
        assert_no_loop(row["record_id"], instructions)
        by_op: dict[int, list[Mapping[str, Any]]] = collections.defaultdict(list)
        for f in row["findings"]:
            idx = _op_index(f["op"])
            if idx is not None and f["site"] == site_338:
                by_op[idx].append(f)
        if not by_op:
            continue
        pc_of = _real_idx_to_pc(row)
        disturbers = pred.rack_topology_disturbers(instructions, contracts, receiver_states)
        untrusted = any(isinstance(i, ir.Widen) and i.reason == execution_order for i in instructions)
        env = frozenset(row["env"])
        for idx, fs in sorted(by_op.items()):
            if idx >= len(row["calls"]) or row["calls"][idx] != PICKUP:
                continue
            call_pc = pc_of[idx]
            call = instructions[call_pc]
            prefix_ok, loop_ok = pred.rack_topology_clauses(disturbers, call_pc, call.receiver_type, False)
            if untrusted:
                prefix_ok = loop_ok = False
            contract_key = f"{call.receiver_type}.{call.method}"
            if contract_key not in contracts:
                raise RuntimeError(f"row {row['record_id']!r} op_{idx}: a :338 finding on a call with no contract {contract_key!r}")
            if contract_key not in kinds_by_contract:
                raise RuntimeError(f"row {row['record_id']!r} op_{idx}: contract {contract_key!r} carries no :338 guard")
            kinds = kinds_by_contract[contract_key]
            guard_kind = "raise_guard" if kinds and kinds == {"raise_guard"} else (sorted(kinds - {"raise_guard"}) or [None])[0]
            ctx = pred._Ctx(  # noqa: SLF001 -- the decision function's own input type
                call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0, channel_kwarg=None,
                channels=None, env=env, class_hierarchy=None, guard_kind=guard_kind,
                rack_topology_prefix_ok=prefix_ok, rack_topology_loop_ok=loop_ok,
            )
            reason = pred.tip_racks_decline_reason(ctx)
            all_safe = all(f["verdict"] == "safe" for f in fs)
            attempted += 1
            if all_safe:
                safe += 1
            elif reason is not None:
                counts[reason] += 1
                if len(declined_examples[reason]) < 10:
                    declined_examples[reason].append({"record_id": row["record_id"], "op": f"op_{idx}", "pc": call_pc})
            else:
                counts["<none>"] += 1  # a non-SAFE :338 finding whose recomputed reason says "decided": unattributed
                if len(declined_examples["<none>"]) < 10:
                    declined_examples["<none>"].append({"record_id": row["record_id"], "op": f"op_{idx}", "pc": call_pc})
            if reason is not None:
                safe_with_reason += sum(1 for f in fs if f["verdict"] == "safe")
            per_op.append({"record_id": row["record_id"], "op": f"op_{idx}", "pc": call_pc, "reason": reason, "safe": all_safe})

    declined = {k: counts.get(k, 0) for k in ("kind", "observation", "deck", "topology_prefix", "topology_loop")}
    return {
        "n_338_pickups_attempted": attempted,
        "n_338_pickups_safe": safe,
        **{f"n_338_declined_{k}": v for k, v in declined.items()},
        "n_338_declined_unattributed": attempted - safe - sum(declined.values()),
        "n_338_safe_with_reason": safe_with_reason,
        "_site_338": site_338,
        "_declined_examples": dict(declined_examples),
        "_per_op": per_op,
    }


def independent_scan(rows: Sequence[Mapping[str, Any]], contracts_payload: Mapping[str, Any]) -> dict[str, Any]:
    """The INDEPENDENT topology scan (M8, §18.9 item 6/7). For every planned ``pick_up_tips`` operation carrying a ``:338``
    finding it decides, from THIS function's own code, (1) whether ``kind``, ``observation`` and ``deck`` all hold and, if so,
    (2) whether a topology disturber precedes it (clause (i)). It re-states §18.5.4 (disturber classes (a)-(f) and the
    ``Widen(execution_order)`` fail-closed rule) directly over the raw contract JSON and the persisted instruction objects,
    and imports NEITHER ``rack_topology_disturbers`` NOR ``tip_racks_decline_reason`` (nor ``rack_topology_clauses``).
    Loops are excluded by :func:`assert_no_loop`. Returns ``n`` (the count the hard term compares against
    ``n_338_declined_topology_prefix``) and per-op detail."""
    contracts = contracts_payload["contracts"]
    receiver_states = contracts_payload["receiver_state"]

    def disturbs(instr: Mapping[str, Any], checked_receiver_type: str | None) -> bool:
        receiver_type = instr["receiver_type"]
        if receiver_type is None:  # (b)
            return True
        contract = contracts.get(f"{receiver_type}.{instr['method']}")
        if contract is None:  # (c) unsupported_tool
            return True
        if receiver_type != checked_receiver_type:  # (d) only same-receiver-type calls are presumed neutral
            return True
        anchor_fields = (receiver_states.get(receiver_type) or {}).get("anchor_fields") or ()
        if not anchor_fields:  # (e) no_receiver_state
            return True
        net = contract.get("anchor_net_effects") or {}
        if any(net.get(a) in ("EMPTY", "HELD") for a in anchor_fields):  # (a) move family
            return True
        for g in contract.get("guards", ()):  # (f) anchor_touched_unmodelled
            if g.get("anchor_field") in anchor_fields and g["anchor_field"] not in net:
                return True
        return False

    n = 0
    n_scanned = 0
    per_op: list[dict[str, Any]] = []
    for row in rows:
        assert_no_loop(row["record_id"], row["instructions"])
        by_op: dict[int, list[Mapping[str, Any]]] = collections.defaultdict(list)
        for f in row["findings"]:
            idx = _op_index(f["op"])
            if idx is not None and f["site"].rsplit(":", 1)[-1] == SITE_338_QUALNAME:
                by_op[idx].append(f)
        if not by_op:
            continue
        pc_of = _real_idx_to_pc(row)
        env = set(row["env"])
        obs_ok = "obs:tip_racks_available=true" in env and "obs:tip_racks_available=false" not in env
        deck_ok = "obs:deck_resources_verified=true" in env and "obs:deck_resources_verified=false" not in env
        order_untrusted = any(i["op"] == "WIDEN" and i["reason"] == EXECUTION_ORDER_REASON for i in row["instructions"])
        for idx in sorted(by_op):
            if idx >= len(row["calls"]) or row["calls"][idx] != PICKUP:
                continue
            call_pc = pc_of[idx]
            call = row["instructions"][call_pc]
            own_key = f"{call['receiver_type']}.{call['method']}"
            if own_key not in contracts:
                raise RuntimeError(f"row {row['record_id']!r} op_{idx}: a :338 finding on a call with no contract {own_key!r}")
            kinds = {
                g.get("kind", "raise_guard")
                for g in contracts[own_key].get("guards", ())
                if (g.get("site") or {}).get("qualname") == SITE_338_QUALNAME
            }
            kind_ok = bool(kinds) and kinds == {"raise_guard"}
            if not (kind_ok and obs_ok and deck_ok):
                continue
            n_scanned += 1
            preceded = order_untrusted or any(
                instr["op"] == "CALL" and disturbs(instr, call["receiver_type"])
                for instr in row["instructions"][:call_pc]
            )
            if preceded:
                n += 1
            per_op.append({"record_id": row["record_id"], "op": f"op_{idx}", "pc": call_pc, "preceded": preceded})
    return {"n_pickups_with_preceding_disturber_indep": n, "_n_scanned": n_scanned, "_per_op": per_op}


# ---------------------------------------------------------------------------
# baseline parity, mutant fields, assembly (2b)
# ---------------------------------------------------------------------------

_ABSENT = "absent"


def baseline_parity(contracts: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    """§18.8(1) / §18.9's parity numbers over the key UNION, absence counted as a value. ``baseline_parity_matched`` counts
    union keys whose values are equal (the intended-divergence keys, which differ by design, excluded);
    ``baseline_parity_total`` is the union size; ``baseline_divergences`` is M11's counter; ``baseline_intended_divergences``
    is ``len(intended_divergences)``."""
    current = {k: v["channel_effect"] for k, v in contracts.items() if v.get("channel_effect") is not None}
    base = baseline["channel_effects"]
    intended = set(baseline.get("intended_divergences") or {})
    union = set(base) | set(current)
    differ = {k for k in union if base.get(k, _ABSENT) != current.get(k, _ABSENT)}
    matched = sum(1 for k in union if k not in differ and k not in intended)
    return {
        "baseline_divergences": len(differ),
        "baseline_intended_divergences": len(intended),
        "baseline_parity_matched": matched,
        "baseline_parity_total": len(union),
        "_divergent_keys": sorted(differ),
    }


def _class_summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    summary = payload["report"]["by_class"].get(payload["class"])
    if summary is None:
        raise RuntimeError(f"unit {payload['unit']!r}: report has no by_class entry for {payload['class']!r}")
    return summary


def mutant_fields(payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Every mutant-derived schema field, read from the tools' REPORT JSON (§18.9). ``mX_attempted := n_raised_as_expected``
    and ``mX_achieved := static_verdict_at_raising_index.will_fail``; ``mutants_unsound``/``mutants_criterion_ii`` sum the
    per-class lists over m1/m2/p3a/m3 and v1; ``mutants_hard_violations_excl_p3a_floor`` is the ``tip_mutants`` reports'
    ``hard_violations`` minus the p3a floor entries."""
    for unit in ("m1", "m2", "p3a", "m3", "v1"):  # defence: a persisted payload must not carry crashed rows either
        assert_no_mutant_errors(unit, _class_summary(payloads[unit]))
    out: dict[str, Any] = {}
    for unit in ("m1", "m2", "p3a"):
        s = _class_summary(payloads[unit])
        attempted = int(s["n_raised_as_expected"])
        achieved = int(s["static_verdict_at_raising_index"]["will_fail"])
        out[f"{unit}_attempted"] = attempted
        out[f"{unit}_achieved"] = achieved
        if unit != "p3a":
            out[f"{unit}_will_fail_fired"] = achieved > 0
    m3 = _class_summary(payloads["m3"])
    out["m3_attempted"] = int(m3["n_ran"])
    out["runtime_raised_m3"] = int(m3["n_runtime_raised_at_338"])
    out["static_338_safe_on_m3"] = int(m3["n_static_338_safe"])
    v1 = _class_summary(payloads["v1"])
    out["v1_attempted"] = int(v1["n_raised_as_expected"])
    out["v1_achieved"] = int(v1["static_verdict_at_raising_index"]["will_fail"])
    out["v1_gate_passed"] = bool(payloads["v1"]["report"]["gate_passed"])

    unsound = criterion_ii = 0
    hard_violations: list[str] = []
    for unit in ("m1", "m2", "p3a", "m3", "v1"):
        s = _class_summary(payloads[unit])
        unsound += len(s["unsound_safe_where_simulator_raised"])
        criterion_ii += len(s["unsound_will_fail_where_simulator_ran_clean"])
        if unit != "v1":
            hard_violations.extend(payloads[unit]["report"]["hard_violations"])
    p3a_floor = [v for v in hard_violations if v.startswith("p3a_pickup_already_held: floor FAILED")]
    out["mutants_unsound"] = unsound
    out["mutants_criterion_ii"] = criterion_ii
    out["mutants_hard_violations_excl_p3a_floor"] = len(hard_violations) - len(p3a_floor)
    out["_hard_violations"] = hard_violations
    out["_p3a_floor_violations"] = p3a_floor
    return out


def assemble_result(
    payloads: Mapping[str, Mapping[str, Any]], contracts_path: Path, baseline_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(result, detail)``: ``result`` has exactly the sidecar's ``[result_schema]`` keys (in order); ``detail`` is the
    non-schema diagnostics (per-method scope table, per-conjunct examples, the independent scan, mutant hard violations)."""
    real, all_safe = payloads["real"], payloads["all_safe"]
    rs, asf = real["summary_flat"], all_safe["summary_flat"]
    raised = int(all_safe["runtime_raised_ops"])
    all_safe_unsound = int(asf["unsound"])

    for key in ("rows_executed", "rows_setup_error", "operations_executed"):
        if rs[key] != asf[key]:
            raise ArmDisagreement(
                f"real and all_safe disagree on {key}: {rs[key]} vs {asf[key]} -- the arms share one runtime and differ only "
                "in static verdicts, so a runtime-side difference means the run is not comparable"
            )

    contracts_bytes = contracts_path.read_bytes()
    baseline_bytes = baseline_path.read_bytes()
    contracts_payload = json.loads(contracts_bytes)
    baseline = json.loads(baseline_bytes)
    rows = real["captures"]["rows"]
    attr = analyze_338(rows, contracts_payload)
    indep = independent_scan(rows, contracts_payload)
    parity = baseline_parity(contracts_payload["contracts"], baseline)
    muts = mutant_fields(payloads)
    pick = real["scope_verdict_by_method"][PICKUP]
    tip_racks = real["n_tip_racks_decided"]

    values: dict[str, Any] = {
        "control_fires": bool(all_safe_unsound >= 1 and all_safe_unsound >= raised),
        "real_rows_executed": int(rs["rows_executed"]),
        "real_rows_setup_error": int(rs["rows_setup_error"]),
        "real_operations_executed": int(rs["operations_executed"]),
        "real_unsound": int(rs["unsound"]),
        "real_unsound_scoped": int(rs["unsound_scoped"]),
        "real_totality_violations": int(rs["totality_violations"]),
        "real_check_graph_exceptions": int(rs["check_graph_exceptions"]),
        "real_n_operations_scope_verdict_safe": int(rs["n_operations_scope_verdict_safe"]),
        "real_pick_up_tips_scope_safe": int(pick["n_scope_verdict_safe"]),
        "real_pick_up_tips_n_ops": int(pick["n_ops"]),
        "real_n_findings_decided": int(rs["n_findings_decided"]),
        "real_n_tip_racks_decided": int(tip_racks["total"]),
        "real_n_tip_racks_attempted": int(tip_racks["attempted"]),
        **{k: v for k, v in attr.items() if not k.startswith("_")},
        "n_pickups_with_preceding_disturber_indep": int(indep["n_pickups_with_preceding_disturber_indep"]),
        "all_safe_unsound": all_safe_unsound,
        "all_safe_operations_executed": int(asf["operations_executed"]),
        "runtime_raised_ops_all_safe_arm": raised,
        **{k: v for k, v in muts.items() if not k.startswith("_")},
        "load_state_channel_effect": contracts_payload["contracts"]["LiquidHandler.load_state"]["channel_effect"],
        **{k: v for k, v in parity.items() if not k.startswith("_")},
        "n_ops_load_state": int(real["n_ops_by_method"].get("load_state", 0)),
    }
    result = {k: values[k] for k in RESULT_SCHEMA}
    validate_result(result)

    analyzer_prefix = sorted(
        (o["record_id"], o["op"]) for o in attr["_per_op"] if o["reason"] == "topology_prefix" and not o["safe"]
    )
    indep_prefix = sorted((o["record_id"], o["op"]) for o in indep["_per_op"] if o["preceded"])
    detail = {
        "site_338": attr["_site_338"],
        "assembly_inputs": {
            "contracts": {"path": str(contracts_path), "sha256": sha256_bytes(contracts_bytes)},
            "baseline": {"path": str(baseline_path), "sha256": sha256_bytes(baseline_bytes)},
        },
        "mutant_row_counts": {
            unit: {
                k: _class_summary(payloads[unit]).get(k)
                for k in ("n_total", "n_construction_skipped", "n_error", "n_static_error", "n_runtime_harness_error", "n_ran")
            }
            for unit in ("m1", "m2", "p3a", "m3", "v1")
        },
        "per_method_scope_verdict": real["scope_verdict_by_method"],
        "n_ops_by_method": real["n_ops_by_method"],
        "n_findings_by_reason": real["n_findings_by_reason"],
        "declined_examples": attr["_declined_examples"],
        "topology_prefix_agreement": {
            "analyzer_side": len(analyzer_prefix),
            "independent": len(indep_prefix),
            "symmetric_difference": [list(x) for x in sorted(set(analyzer_prefix) ^ set(indep_prefix))][:50],
            "independent_scanned": indep["_n_scanned"],
        },
        "mutants": {
            "hard_violations": muts["_hard_violations"],
            "p3a_floor_violations": muts["_p3a_floor_violations"],
            "p3a_by_class": _class_summary(payloads["p3a"]),
            "m3_by_class": _class_summary(payloads["m3"]),
        },
        "baseline": {"divergent_keys": parity["_divergent_keys"], "source_rev": baseline.get("source_rev")},
        "wall_elapsed_s": {"real": real.get("wall_elapsed_s")},
    }
    return result, detail


def validate_result(result: Mapping[str, Any]) -> None:
    """``result`` has exactly the schema's keys, each of exactly the declared type (``bool`` is not an ``int``)."""
    if set(result) != set(RESULT_SCHEMA):
        raise ValueError(
            f"result keys != result_schema: missing {sorted(set(RESULT_SCHEMA) - set(result))}, "
            f"extra {sorted(set(result) - set(RESULT_SCHEMA))}"
        )
    for key, typ in RESULT_SCHEMA.items():
        v = result[key]
        if type(v) is not typ:  # noqa: E721 -- exact type: bool must not pass as int
            raise ValueError(f"result[{key!r}] = {v!r} is {type(v).__name__}, schema says {typ.__name__}")


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def _common_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    for c in args.corpus:
        argv += ["--corpus", c]
    if args.sidecar:
        argv += ["--sidecar", args.sidecar]
    for cc in args.crosscheck:
        argv += ["--crosscheck", cc]
    argv += ["--contracts", str(args.contracts), "--baseline", str(args.baseline), "--out-dir", str(args.out_dir)]
    if args.limit is not None:
        argv += ["--limit", str(args.limit)]
    return argv


def _check_inputs(args: argparse.Namespace) -> None:
    paths = [*args.corpus, *args.crosscheck, str(args.contracts), str(args.baseline)]
    if args.sidecar:
        paths.append(args.sidecar)
    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError(f"input file(s) not found (paths are relative to cwd={Path.cwd()}): {missing}")
    if any(u in TIP_UNIT_CLASS or u == "v1" for u in args.units) and len(args.corpus) != 1:
        raise ValueError("the mutant units (m1 m2 p3a m3 v1) take exactly one --corpus (tip_mutants/volume_mutants do)")


def run(
    args: argparse.Namespace,
    *,
    runner: Runner | None = None,
    inputs: Mapping[str, Any] | None = None,
    enforce_clean_tree: bool = True,
) -> int:
    """One invocation: reuse-or-compute every requested unit, then -- iff all seven are complete -- write ``detail.json`` and
    ``result.json``. Stale ``result.json``/``detail.json``/``incomplete.json`` from an earlier invocation are removed FIRST,
    so no ``result.json`` can outlive an input change that makes a unit incomplete -- and BEFORE any refusal or input check,
    so a refused invocation leaves no result behind either. ``enforce_clean_tree`` (True; the CLI has no way to turn it off) is
    the :func:`check_clean_tree` refusal; tests with stub runners and synthetic inputs pass False."""
    out_dir: Path = args.out_dir
    for stale in (RESULT_NAME, DETAIL_NAME, INCOMPLETE_NAME):
        (out_dir / stale).unlink(missing_ok=True)
    if enforce_clean_tree:
        check_clean_tree()
    _check_inputs(args)
    (out_dir / UNITS_DIRNAME).mkdir(parents=True, exist_ok=True)
    if inputs is None:
        inputs = collect_input_hashes(
            corpus=args.corpus, sidecar=args.sidecar, crosscheck=args.crosscheck, contracts=args.contracts,
            limit=args.limit,
        )
    if runner is None:
        script = Path(__file__).resolve()
        common = _common_argv(args)

        def cmd_for_unit(unit: str, worker_out: Path) -> list[str]:
            return [sys.executable, str(script), "--unit", unit, "--worker-output", str(worker_out), *common]

        runner = make_subprocess_runner(cmd_for_unit, out_dir, timeout_s=args.unit_timeout_s)

    outcome = run_units(out_dir, inputs, runner, units=args.units)
    if not outcome.complete:
        write_json_atomic(out_dir / INCOMPLETE_NAME, {"incomplete": outcome.incomplete, "units": outcome.records})
        log.error("INCOMPLETE units %s: no %s written (FAIL by construction); re-invoke to recompute only those",
                  outcome.incomplete, RESULT_NAME)
        return 1
    if set(args.units) != set(UNITS):
        log.warning("partial invocation (--units %s): all seven units are required for %s; none written",
                    list(args.units), RESULT_NAME)
        return 0

    payloads = {u: load_payload(out_dir, u) for u in UNITS}
    try:
        result, detail = assemble_result(payloads, args.contracts, args.baseline)
    except InstrumentInvalid as e:
        write_json_atomic(out_dir / INCOMPLETE_NAME, {"incomplete": [], "invalid_instrument": str(e), "units": outcome.records})
        log.error("INVALID INSTRUMENT: %s -- no %s written", e, RESULT_NAME)
        return 1
    write_json_atomic(out_dir / DETAIL_NAME, detail)
    provenance = {"units": outcome.records, "assembly_inputs": detail["assembly_inputs"]}
    (out_dir / RESULT_NAME).write_text(json.dumps({**result, **provenance}, indent=2), encoding="utf-8")
    log.info("result written to %s", out_dir / RESULT_NAME)
    text = json.dumps(result)
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(text, encoding="utf-8")
        log.info("Bathos results written to %s", bth_path)
    print(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=str, action="append", required=True, help="corpus JSONL (repeatable; exactly one for the mutant units)")
    ap.add_argument("--sidecar", type=str, default=None, help="assemble sidecar JSONL; pass-through to oracle_replay")
    ap.add_argument("--crosscheck", type=str, action="append", default=[], help="floor/overlay crosscheck file (repeatable)")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE, help="channel_effect_baseline.json (T59's fixture)")
    ap.add_argument("--limit", type=int, default=None, help="smoke-test row limit (a limited run is never reused by a full one)")
    ap.add_argument("--out-dir", type=Path, required=True, help="unit outputs, stamps, detail.json, result.json")
    ap.add_argument("--units", nargs="+", choices=UNITS, default=list(UNITS), help="run only these units (result.json needs all seven)")
    ap.add_argument("--unit-timeout-s", type=float, default=DEFAULT_UNIT_TIMEOUT_S, help="per-unit timeout (default 30 min)")
    ap.add_argument("--unit", choices=UNITS, default=None, help=argparse.SUPPRESS)  # internal: run ONE unit as a worker
    ap.add_argument("--worker-output", type=Path, default=None, help=argparse.SUPPRESS)
    return ap


def worker_main(args: argparse.Namespace) -> int:
    if args.worker_output is None:
        raise SystemExit("--unit requires --worker-output")
    payload = compute_unit(args.unit, args)
    write_json_atomic(args.worker_output, payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.unit is not None:
        return worker_main(args)
    try:
        return run(args)
    except DirtyTreeError as e:
        log.error("%s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""AC / HM cross-reference lint for the plr-sema spec (round-6 recommendation).

Round 6 found "an AC range off by one in two places" and "four task rows
missing ACs their own sections define", and recommended a cross-reference
lint alongside the citation checker. This is that lint. It reconciles three
things mechanically:

**Acceptance criteria (AC-N.M).**
  * ``ac_ungated``        -- an AC is defined (``- **AC-N.M**``) but appears in
    no task row's gate column.
  * ``ac_multiply_gated`` -- an AC appears in more than one task row's gate.
  * ``ac_undefined``      -- a task row's gate names an AC that is defined
    nowhere. Gate ranges (``AC-1.1–1.4``, hyphen or en-dash) are expanded.

**Hand-maintained registry rows (HM-N), spec vs. code.** The registry
(``_hand_maintained.py``) is AST-read, never imported -- the same convention
T10's differential harness uses for the 45 hand-written contracts, so the
lint has no import-time dependency on the package.
  * ``hm_missing_from_inventory`` -- a registry row has no ``| HM-N |`` row in
    §9.2's inventory table.
  * ``hm_not_in_registry``        -- §9.2 (or any other spec passage) names an
    HM id the registry does not define.
  * ``hm_baseline_mismatch``      -- §9.2's bold baseline number differs from
    the registry row's ``declared``.
  * ``hm_status_mismatch``        -- §9.2's status column disagrees with the
    registry row's ``status`` (RETIRED rows are matched on the word RETIRED).
  * ``budget_cap_mismatch``       -- §9.4's "Total budget: N registry rows"
    differs from ``BUDGET_CAP``.

Usage::

    uv run python plr-sema/scripts/check_spec_crossrefs.py \
        --spec .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md \
        --registry plr-sema/src/plr_sema/_hand_maintained.py

Exit status 1 iff any violation.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import logging
import re
import sys
from pathlib import Path

log = logging.getLogger("check_spec_crossrefs")

#: ``- **AC-N.M** ...`` and ``- **AC-N.M (qualifier)** ...`` both define an AC.
AC_DEF_RE = re.compile(r"^\s*[-*]\s*\*\*AC-(\d+)\.(\d+)\b")
AC_RANGE_RE = re.compile(r"AC-(\d+)\.(\d+)\s*[–-]\s*(?:AC-)?(?:(\d+)\.)?(\d+)")
AC_ONE_RE = re.compile(r"AC-(\d+)\.(\d+)")
#: ``| **T1** |`` in the main spec; ``| **#4888** |`` in increment docs that key
#: their single task row on the backlog id.
TASK_ROW_RE = re.compile(r"^\|\s*\*\*(T\d+|#\d+[a-z]?)\*\*[^|]*\|")  # trailing text after the bold id is allowed
HM_RE = re.compile(r"\bHM-(\d+)\b")
HM_ROW_RE = re.compile(r"^\|\s*HM-(\d+)\s*\|")
BUDGET_RE = re.compile(r"Total budget:\s*(\d+)\s*registry rows")
STATUSES = ("FROZEN", "CAPPED", "DERIVABLE_NOT_YET", "TARGET_ZERO", "RETIRED")


@dataclasses.dataclass(frozen=True, slots=True)
class Violation:
    kind: str
    spec_line: int  # 0 when the violation lives on the code side
    subject: str
    detail: str


@dataclasses.dataclass(frozen=True, slots=True)
class RegistryRow:
    id: str
    declared: int | None
    status: str
    lineno: int


def read_registry(path: Path) -> tuple[list[RegistryRow], int | None]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rows: list[RegistryRow] = []
    cap: int | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BUDGET_CAP" for t in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                cap = node.value.value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "HandMaintainedSurface":
            kw = {k.arg: k.value for k in node.keywords}
            rid = kw.get("id")
            if not (isinstance(rid, ast.Constant) and isinstance(rid.value, str)):
                continue
            decl = kw.get("declared")
            declared = decl.value if isinstance(decl, ast.Constant) and isinstance(decl.value, int) else None
            st = kw.get("status")
            status = st.value if isinstance(st, ast.Constant) and isinstance(st.value, str) else "?"
            rows.append(RegistryRow(rid.value, declared, status, node.lineno))
    return rows, cap


def _expand_gate(cell: str) -> set[str]:
    out: set[str] = set()
    consumed: list[tuple[int, int]] = []
    for m in AC_RANGE_RE.finditer(cell):
        maj, lo, maj2, hi = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
        if maj2 is not None and int(maj2) != maj:
            continue  # cross-major range: leave to the single-AC pass
        out.update(f"AC-{maj}.{i}" for i in range(lo, hi + 1))
        consumed.append(m.span())
    for m in AC_ONE_RE.finditer(cell):
        if any(a <= m.start() < b for a, b in consumed):
            continue
        out.add(m.group(0))
    return out


def _section(lines: list[str], header_prefix: str) -> tuple[int, int]:
    """(start, end) line indices of the section whose header starts with prefix."""
    start = next((i for i, l in enumerate(lines) if re.match(r"^#+\s*" + re.escape(header_prefix), l)), None)
    if start is None:
        return -1, -1
    depth = len(lines[start]) - len(lines[start].lstrip("#"))
    end = next((j for j in range(start + 1, len(lines)) if re.match(r"^#{1,%d}\s" % depth, lines[j])), len(lines))
    return start, end


def check(spec: Path, registry: Path) -> list[Violation]:
    lines = spec.read_text(encoding="utf-8").splitlines()
    v: list[Violation] = []

    # --- AC side --------------------------------------------------------
    defined: dict[str, int] = {}
    for i, l in enumerate(lines, 1):
        m = AC_DEF_RE.match(l)
        if m:
            defined.setdefault(f"AC-{m.group(1)}.{m.group(2)}", i)
    gated: dict[str, list[str]] = {}
    for i, l in enumerate(lines, 1):
        m = TASK_ROW_RE.match(l)
        if not m:
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        for ac in _expand_gate(cells[3]):
            gated.setdefault(ac, []).append(m.group(1))
    for ac, ln in sorted(defined.items(), key=lambda kv: tuple(map(int, kv[0][3:].split(".")))):
        rows = gated.get(ac, [])
        if not rows:
            v.append(Violation("ac_ungated", ln, ac, "defined but in no task row's gate"))
        elif len(rows) > 1:
            v.append(Violation("ac_multiply_gated", ln, ac, f"gated by {rows}"))
    for ac, rows in gated.items():
        if ac not in defined:
            v.append(Violation("ac_undefined", 0, ac, f"gated by {rows} but never defined"))

    # --- HM side --------------------------------------------------------
    reg_rows, cap = read_registry(registry)
    reg = {r.id: r for r in reg_rows}
    s92 = _section(lines, "9.2")
    inv: dict[str, tuple[int, str]] = {}
    if s92[0] >= 0:
        for i in range(s92[0], s92[1]):
            m = HM_ROW_RE.match(lines[i])
            if m:
                inv[f"HM-{m.group(1)}"] = (i + 1, lines[i])
    for rid, r in reg.items():
        if rid not in inv:
            v.append(Violation("hm_missing_from_inventory", 0, rid, f"registry line {r.lineno} ({r.status}) has no §9.2 row"))
    for rid, (ln, row) in inv.items():
        if rid not in reg:
            v.append(Violation("hm_not_in_registry", ln, rid, "§9.2 row with no registry entry"))
            continue
        r = reg[rid]
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        baseline_cell = cells[3] if len(cells) > 3 else ""
        status_cell = cells[4] if len(cells) > 4 else ""
        # The registry's ``declared`` is the CEILING. §9.2 shows the ceiling as
        # ``CAPPED (N)`` in the status cell; for every other status the bold
        # baseline count *is* the ceiling (FROZEN at its size, TARGET_ZERO at
        # its current size, DERIVABLE_NOT_YET at its measured baseline).
        cm = re.search(r"CAPPED\s*\((\d+)\)", status_cell)
        bm = re.search(r"\*\*(\d+)\*\*", baseline_cell)
        spec_ceiling = int(cm.group(1)) if cm else (int(bm.group(1)) if bm else None)
        if spec_ceiling is not None and r.declared is not None and spec_ceiling != r.declared:
            v.append(Violation("hm_ceiling_mismatch", ln, rid, f"§9.2 ceiling {spec_ceiling}, registry declared={r.declared}"))
        if r.status not in status_cell.replace("*", ""):
            v.append(Violation("hm_status_mismatch", ln, rid, f"§9.2 status cell {status_cell!r}, registry status={r.status}"))
    for i, l in enumerate(lines, 1):
        for m in HM_RE.finditer(l):
            rid = f"HM-{m.group(1)}"
            if rid not in reg and (rid, i) not in {(k, ln) for k, (ln, _) in inv.items()}:
                v.append(Violation("hm_not_in_registry", i, rid, "mentioned in spec, no registry entry"))
    for i, l in enumerate(lines, 1):
        m = BUDGET_RE.search(l)
        if m and cap is not None and int(m.group(1)) != cap:
            v.append(Violation("budget_cap_mismatch", i, "BUDGET_CAP", f"spec says {m.group(1)}, registry BUDGET_CAP={cap}"))
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    violations = check(args.spec, args.registry)
    by_kind: dict[str, int] = {}
    for x in violations:
        by_kind[x.kind] = by_kind.get(x.kind, 0) + 1
        log.warning("%s L%d %s -- %s", x.kind, x.spec_line, x.subject, x.detail)
    log.info("violations=%d by_kind=%s", len(violations), by_kind)
    if args.json_out:
        args.json_out.write_text(json.dumps([dataclasses.asdict(x) for x in violations], indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

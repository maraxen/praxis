"""PLR 1.0 phase 2 (#5664) PR-0: inventory of praxis usage of deprecated PLR 1.0 resource APIs.

The before-count is a finding, so this is a tracked script run under
``phase2_inventory.bth.toml`` (committed before the run). Phase-2 plan §3.1 / §5 PR-0 item 4 / §8 item 1.

Method (ported from the 260929 recon script ``praxis_inventory.py``; the classification rules are
unchanged so the recon's 88 is comparable):

* **Vocabulary.** Every function, method or class under ``external/pylabrobot/pylabrobot/resources``
  that calls ``warnings.warn(..., DeprecationWarning|FutureWarning|PendingDeprecationWarning)`` or
  whose docstring starts with "Deprecated", plus the hand-listed keyword/attribute renames in
  ``EXTRA`` (hamilton/star deck ``rails`` -> ``track`` etc.). Regenerated from PLR source every run.
* **Scan.** ``.py``: AST (names, attributes, import aliases, keyword args, string constants) plus a
  raw-text pass for comments. ``.ts/.js/.json/.jsonl/.ipynb/.toml/.yaml/.html``: word-boundary regex.
* **Classification** (``usage_class``): ``survey_data`` (plr-sema/training survey artifacts that
  describe PLR itself), ``test/fixture``, ``docstring``, ``ambiguous`` (generic names), ``code/data``.

Preemption-safe and resumable (owner rule 260929): units ``upstream``, one per scanned root, and
``controls``, each in its own subprocess with its own timeout. Each unit persists
``units/<unit>.json`` and ``units/<unit>.stamp.json`` = {inputs sha256, output sha256}; a re-run
reuses a unit only if both match. ``result.json`` is written only when every unit is complete.

Usage (repo root; the registered run is wrapped by ``bth run``)::

    uv run --no-sync python scripts/plr10/phase2_inventory.py --out-dir outputs/plr10/phase2_inventory_pr0
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

log = logging.getLogger("phase2_inventory")

REPO = Path(__file__).resolve().parents[2]
PLR_PKG = REPO / "external" / "pylabrobot" / "pylabrobot"
ROOTS = ["praxis", "web-repl", "coxswain", "training", "scripts", "plr-sema", "tests"]
SKIP_DIRS = {"node_modules", ".venv", "__pycache__", "dist", ".angular", "build", "_output",
             ".git", "site-packages", "pyodide", "vendor_pyodide"}
TEXT_EXT = {".ts", ".js", ".mjs", ".json", ".jsonl", ".ipynb", ".toml", ".yaml", ".yml", ".html"}
MAX_TEXT_BYTES = 40_000_000
UNIT_TIMEOUT_S = 1800
#: The 260929 recon's code/data count (phase-2 plan §3.1), measured before #191/#192/#193 landed.
#: Reported beside the new count for attribution; never an outcome criterion.
RECON_CODE_DATA_ROWS = 88

# Attribute/method names whose deprecation is only meaningful on a PLR object (generic names).
AMBIGUOUS = {"tracker", "get_tip", "has_tip", "empty", "set_liquids", "get_liquids", "__init__",
             "__getattr__", "assign_child_resource", "_resolve_num_tracks"}
EXTRA = {
    "rails": ("kwarg", "track"),
    "num_rails": ("kwarg_or_attr", "num_tracks"),
    "with_teaching_rack": ("kwarg", "with_teaching_needle_rack"),
    "rails_to_location": ("attr", "track_to_location"),
    "rails_for_x_coordinate": ("name", "track_for_x_coordinate"),
    "TipTracker": ("name", "pylabrobot.legacy.tip_tracker.TipTracker (or tree: TipSpot.tip)"),
    "TrackerCallback": ("name", "pylabrobot.legacy.tip_tracker.TrackerCallback"),
    "total_tip_length": ("attr", "size_z (removed in 1.0, not merely deprecated)"),
    "set_well_liquids": ("attr", "set_well_volumes"),
    "disable_tip_trackers": ("attr", "disable_tip_tracking"),
    "enable_tip_trackers": ("attr", "enable_tip_tracking"),
}
TEXT_EXTRA = ("total_tip_length", "rails_to_location", "num_rails", "with_teaching_rack",
              "set_well_liquids", "disable_tip_trackers", "enable_tip_trackers")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# unit `upstream`: the deprecation vocabulary, from PLR source
# ---------------------------------------------------------------------------


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
    if isinstance(node, ast.BinOp):
        return (_const_str(node.left) or "") + (_const_str(node.right) or "")
    return None


def _warn_calls(fn):
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name == "warn" and len(n.args) >= 1:
                cat = n.args[1] if len(n.args) > 1 else None
                for kw in n.keywords:
                    if kw.arg == "category":
                        cat = kw.value
                catname = getattr(cat, "id", None) or getattr(cat, "attr", None)
                if catname in ("DeprecationWarning", "FutureWarning", "PendingDeprecationWarning"):
                    out.append((n.lineno, _const_str(n.args[0]) or ""))
    return out


def _hint(msg):
    m = re.search(r"[Uu]se [`'\"]?([A-Za-z_][\w\.]*)(\(\))?[`'\"]?", msg)
    return m.group(1) if m else ""


def upstream_rows(pkg: Path) -> list[dict]:
    rows = []
    for f in sorted((pkg / "resources").rglob("*.py")):
        if f.name.endswith("_tests.py") or "/tests/" in f.as_posix():
            continue
        mod = ".".join(f.relative_to(pkg.parent).with_suffix("").parts)
        tree = ast.parse(f.read_text(encoding="utf-8"))

        def visit(node, prefix, f=f, mod=mod):
            for ch in ast.iter_child_nodes(node):
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    q = f"{prefix}{ch.name}"
                    doc = ast.get_docstring(ch) or ""
                    warns = _warn_calls(ch) if not isinstance(ch, ast.ClassDef) else []
                    if isinstance(ch, ast.ClassDef):
                        init = [c for c in ch.body if isinstance(c, ast.FunctionDef) and c.name == "__init__"]
                        if init and doc.lower().startswith("deprecated"):
                            warns = _warn_calls(init[0])
                    if warns or doc.lower().startswith("deprecated"):
                        msg = warns[0][1] if warns else doc.splitlines()[0]
                        rows.append({
                            "kind": "class" if isinstance(ch, ast.ClassDef) else ("method" if prefix else "function"),
                            "qualname": q,
                            "module": mod,
                            "loc": f"{f.relative_to(pkg.parent.parent).as_posix()}:{ch.lineno}",
                            "replacement_hint": _hint(msg) or _hint(doc),
                        })
                    if isinstance(ch, ast.ClassDef):
                        visit(ch, q + ".")

        visit(tree, "")
    return rows


def vocabulary(rows: list[dict]) -> dict[str, list[str]]:
    """name -> [kind, replacement]. Same rules as the recon's ``load_upstream``."""
    names: dict[str, list[str]] = {}
    for r in rows:
        leaf = r["qualname"].split(".")[-1]
        if r["kind"] in ("function", "class"):
            if leaf.startswith("_") and leaf != "__getattr__":
                continue
            names[leaf] = ["name", r["replacement_hint"]]
        else:
            if leaf in AMBIGUOUS:
                if leaf in ("tracker", "get_tip", "has_tip", "empty", "set_liquids", "get_liquids"):
                    names.setdefault(leaf, ["attr_ambiguous", r["replacement_hint"]])
                continue
            names[leaf] = ["attr", r["replacement_hint"]]
    for k, (kind, rep) in EXTRA.items():
        names.setdefault(k, [kind, rep])
    names.pop("__getattr__", None)
    return names


# ---------------------------------------------------------------------------
# scanning (recon rules, unchanged)
# ---------------------------------------------------------------------------


def text_regex(names: dict) -> re.Pattern:
    textnames = sorted((k for k, v in names.items() if v[0] == "name" or k in TEXT_EXTRA), key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(map(re.escape, textnames)) +
                      r")(?![A-Za-z0-9_])|(?<![A-Za-z0-9_])[\"']?(rails)[\"']?\s*[=:]\s*\d")


def scan_py(src: str, rel: str, names: dict, out: list) -> None:
    try:
        tree = ast.parse(src)
    except Exception as e:  # noqa: BLE001 -- a parse failure is recorded, never dropped
        out.append(dict(file=rel, line=0, lang="py", match_kind="parse_error", name="", replacement="",
                        confidence="", snippet=str(e)[:120]))
        return
    lines = src.splitlines()

    def add(node, kind, name, conf="high"):
        ln = getattr(node, "lineno", 0)
        info = names[name]
        if info[0] == "attr_ambiguous":
            conf = "low"
        out.append(dict(file=rel, line=ln, lang="py", match_kind=kind, name=name, replacement=info[1],
                        confidence=conf, snippet=(lines[ln - 1].strip() if 0 < ln <= len(lines) else "")[:160]))

    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id in names and names[n.id][0] == "name":
            add(n, "name", n.id)
        elif isinstance(n, ast.Attribute) and n.attr in names:
            k = names[n.attr][0]
            if k in ("name", "attr", "attr_ambiguous", "kwarg_or_attr"):
                add(n, "attribute", n.attr, "high" if k != "kwarg_or_attr" else "medium")
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            if mod.endswith("resources.tip_tracker"):
                out.append(dict(file=rel, line=n.lineno, lang="py", match_kind="import_module",
                                name="pylabrobot.resources.tip_tracker",
                                replacement="pylabrobot.resources.tip_tracking / pylabrobot.legacy.tip_tracker",
                                confidence="high", snippet=lines[n.lineno - 1].strip()[:160]))
            for a in n.names:
                if a.name in names and names[a.name][0] == "name":
                    add(n, "import", a.name)
        elif isinstance(n, ast.keyword) and n.arg in names and names[n.arg][0] in ("kwarg", "kwarg_or_attr"):
            add(n.value, "kwarg", n.arg)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 2_000_000:
            for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", n.value):
                w = m.group(0)
                if w in names and names[w][0] == "name" and len(w) > 6:
                    add(n, "string", w, "medium")
            if re.search(r"\brails\s*=", n.value):
                out.append(dict(file=rel, line=n.lineno, lang="py", match_kind="string_kwarg", name="rails",
                                replacement="track", confidence="medium",
                                snippet=n.value.strip().splitlines()[0][:160] if n.value.strip() else ""))


def scan_text(txt: str, rel: str, suffix: str, names: dict, rx: re.Pattern, out: list) -> None:
    for i, line in enumerate(txt.splitlines(), 1):
        for m in rx.finditer(line):
            w = m.group(1) or m.group(2)
            if w == "rails" or m.group(2):
                name, rep = "rails", "track"
            else:
                name, rep = w, names[w][1]
            s = max(0, m.start() - 60)
            out.append(dict(file=rel, line=i, lang=suffix, match_kind="text", name=name, replacement=rep,
                            confidence="medium", snippet=line[s:m.end() + 60].strip()[:160]))


def scan_file(path: Path, rel: str, names: dict, rx: re.Pattern) -> list[dict]:
    out: list[dict] = []
    if path.suffix == ".py":
        src = path.read_text(encoding="utf-8", errors="replace")
        scan_py(src, rel, names, out)
        seen = {(r["line"], r["name"]) for r in out}
        extra: list[dict] = []
        scan_text(src, rel, path.suffix, names, rx, extra)
        for r in extra:
            if (r["line"], r["name"]) not in seen:
                r["match_kind"] = "text_py(comment/unparsed)"
                r["confidence"] = "low"
                out.append(r)
    elif path.suffix in TEXT_EXT:
        if path.stat().st_size > MAX_TEXT_BYTES:
            out.append(dict(file=rel, line=0, lang=path.suffix, match_kind="skipped_large", name="", replacement="",
                            confidence="", snippet=str(path.stat().st_size)))
        else:
            scan_text(path.read_text(encoding="utf-8", errors="replace"), rel, path.suffix, names, rx, out)
    return out


def classify(r: dict) -> dict:
    f = r["file"]
    if re.search(r"plr-sema/data/|verify/data/plr_|survey_plr_|ingest/out/", f):
        r["usage_class"] = "survey_data"
    elif "/tests/" in f or f.startswith("tests/") or ".spec." in f or "__tests__" in f or "/fixtures/" in f or "/e2e/" in f:
        r["usage_class"] = "test/fixture"
    elif r["match_kind"] in ("string", "string_kwarg") and r["confidence"] != "high" and '"""' in r.get("snippet", "")[:4]:
        r["usage_class"] = "docstring"
    elif r["confidence"] == "low":
        r["usage_class"] = "ambiguous"
    elif r["match_kind"] in ("parse_error", "skipped_large"):
        r["usage_class"] = r["match_kind"]
    else:
        r["usage_class"] = "code/data"
    return r


def root_files(root: str) -> list[Path]:
    base = REPO / root
    files = []
    if base.exists():
        for f in base.rglob("*"):
            if f.is_file() and not any(part in SKIP_DIRS for part in f.relative_to(REPO).parts):
                if f.suffix == ".py" or f.suffix in TEXT_EXT:
                    files.append(f)
    return sorted(files)


# ---------------------------------------------------------------------------
# controls: generated from the vocabulary, run through the SAME scan_file
# ---------------------------------------------------------------------------


def _ident(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s or ""))


def control_sources(names: dict) -> tuple[str, str, str, set[str]]:
    """(positive .py, positive .ts, negative .py, expected names). The positive files use every
    vocabulary name in the form its kind is detected in; the negative file uses the 1.0
    replacement identifiers (those that are not themselves in the vocabulary)."""
    pos = ["from pylabrobot.resources.tip_tracker import something", "obj = object()"]
    expected = {"pylabrobot.resources.tip_tracker"}
    for name, (kind, _rep) in sorted(names.items()):
        if kind == "name":
            pos.append(f"from pylabrobot.resources import {name}")
            pos.append(f"_ = {name}")
        elif kind in ("attr", "attr_ambiguous"):
            pos.append(f"_ = obj.{name}")
        elif kind == "kwarg":
            pos.append(f"f({name}=1)")
        elif kind == "kwarg_or_attr":
            pos.append(f"f({name}=1)")
            pos.append(f"_ = obj.{name}")
        expected.add(name)
    textnames = [k for k, v in names.items() if v[0] == "name" or k in TEXT_EXTRA]
    ts = "\n".join([f"const x{i} = data.{n};" for i, n in enumerate(sorted(textnames))] + ["const r = { rails: 3 };"])
    neg = ["obj = object()"]
    for name, (kind, rep) in sorted(names.items()):
        leaf = (rep or "").split(".")[-1].split(" ")[0]
        if not _ident(leaf) or leaf in names or leaf == "size_z":
            continue
        if kind == "name":
            neg.append(f"_ = {leaf}")
        elif kind in ("kwarg", "kwarg_or_attr"):
            neg.append(f"f({leaf}=1)")
        else:
            neg.append(f"_ = obj.{leaf}")
    neg += ["from pylabrobot.resources.tip_tracking import something", "_ = obj.size_z"]
    return "\n".join(pos) + "\n", ts + "\n", "\n".join(neg) + "\n", expected


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------


#: unit name -> scanned root directory
UNIT_ROOT = {f"root_{r.replace('-', '_')}": r for r in ROOTS}


def unit_names() -> list[str]:
    return ["upstream", *UNIT_ROOT, "controls"]


def run_unit(unit: str, units_dir: Path) -> dict:
    if unit == "upstream":
        rows = upstream_rows(PLR_PKG)
        return {"unit": unit, "n_upstream_rows": len(rows), "rows": rows, "vocabulary": vocabulary(rows)}
    vocab = json.loads((units_dir / "upstream.json").read_text(encoding="utf-8"))["vocabulary"]
    rx = text_regex(vocab)
    if unit == "controls":
        pos_py, pos_ts, neg_py, expected = control_sources(vocab)
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "pos.py").write_text(pos_py, encoding="utf-8")
            (t / "pos.ts").write_text(pos_ts, encoding="utf-8")
            (t / "neg.py").write_text(neg_py, encoding="utf-8")
            pos_rows = scan_file(t / "pos.py", "pos.py", vocab, rx) + scan_file(t / "pos.ts", "pos.ts", vocab, rx)
            neg_rows = scan_file(t / "neg.py", "neg.py", vocab, rx)
        detected = {r["name"] for r in pos_rows if r["file"] == "pos.py" and r["match_kind"] != "parse_error"}
        ts_detected = {r["name"] for r in pos_rows if r["file"] == "pos.ts"}
        ts_expected = {k for k, v in vocab.items() if v[0] == "name" or k in TEXT_EXTRA} | {"rails"}
        return {
            "unit": unit,
            "positive_expected": len(expected),
            "positive_detected": len(expected & detected),
            "positive_missed": sorted(expected - detected),
            "positive_ts_expected": len(ts_expected),
            "positive_ts_detected": len(ts_expected & ts_detected),
            "positive_ts_missed": sorted(ts_expected - ts_detected),
            "negative_lines": neg_py.count("\n"),
            "negative_hits": len([r for r in neg_rows if r["match_kind"] != "parse_error"]),
            "negative_hit_rows": [r for r in neg_rows if r["match_kind"] != "parse_error"],
            "control_parse_errors": len([r for r in pos_rows + neg_rows if r["match_kind"] == "parse_error"]),
        }
    root = UNIT_ROOT[unit]
    rows: list[dict] = []
    files = root_files(root)
    for f in files:
        rel = f.relative_to(REPO).as_posix()
        rows.extend(classify(r) for r in scan_file(f, rel, vocab, rx))
    return {"unit": unit, "root": root, "n_files": len(files), "rows": rows}


def unit_inputs(unit: str, units_dir: Path) -> dict:
    script = sha256_file(Path(__file__))
    if unit == "upstream":
        files = sorted((PLR_PKG / "resources").rglob("*.py"))
        tree = sha256_bytes("\n".join(f"{f.relative_to(REPO).as_posix()} {sha256_file(f)}" for f in files).encode())
        return {"script": script, "plr_resources": tree}
    up = units_dir / "upstream.json"
    base = {"script": script, "upstream": sha256_file(up) if up.exists() else None}
    if unit == "controls":
        return base
    files = root_files(UNIT_ROOT[unit])
    base["files"] = sha256_bytes("\n".join(f"{f.relative_to(REPO).as_posix()} {sha256_file(f)}" for f in files).encode())
    return base


def reusable(unit: str, units_dir: Path) -> tuple[bool, dict]:
    out, stamp = units_dir / f"{unit}.json", units_dir / f"{unit}.stamp.json"
    inputs = unit_inputs(unit, units_dir)
    if out.exists() and stamp.exists():
        s = json.loads(stamp.read_text(encoding="utf-8"))
        if s.get("inputs") == inputs and s.get("output_sha256") == sha256_file(out):
            return True, inputs
    return False, inputs


def git_head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def tree_dirty() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no", "--", *ROOTS],
                         check=True, capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--recon-tsv", type=Path, default=None, help="optional: the 260929 recon TSV, for file-level attribution")
    ap.add_argument("--unit", default=None, help=argparse.SUPPRESS)  # internal: run one unit in this process
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO / args.out_dir
    units_dir = out_dir / "units"
    units_dir.mkdir(parents=True, exist_ok=True)

    if args.unit:
        res = run_unit(args.unit, units_dir)
        (units_dir / f"{args.unit}.json").write_text(json.dumps(res, sort_keys=True), encoding="utf-8")
        return 0

    dirty = tree_dirty()
    if dirty:
        log.error("refusing to measure a dirty tree (tracked changes under the scanned roots): %s", dirty[:10])
        return 2
    head = git_head()
    unit_log: dict[str, dict] = {}
    for unit in unit_names():
        ok, inputs = reusable(unit, units_dir)
        if ok:
            log.info("unit %-16s REUSED (stamp matches)", unit)
            unit_log[unit] = {"status": "reused", "inputs": inputs}
            continue
        log.info("unit %-16s COMPUTE", unit)
        try:
            subprocess.run([sys.executable, str(Path(__file__)), "--out-dir", str(out_dir), "--unit", unit],
                           check=True, timeout=UNIT_TIMEOUT_S, env={k: v for k, v in os.environ.items() if k != "BTH_RESULTS_PATH"})
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            log.error("unit %s did not complete (%s): no result.json", unit, type(e).__name__)
            return 1
        out = units_dir / f"{unit}.json"
        (units_dir / f"{unit}.stamp.json").write_text(
            json.dumps({"unit": unit, "inputs": inputs, "output_sha256": sha256_file(out)}, sort_keys=True), encoding="utf-8")
        unit_log[unit] = {"status": "computed", "inputs": inputs, "output_sha256": sha256_file(out)}

    units = {u: json.loads((units_dir / f"{u}.json").read_text(encoding="utf-8")) for u in unit_names()}
    rows = [r for u in unit_names() if u.startswith("root_") for r in units[u]["rows"]]
    by_class: dict[str, int] = {}
    for r in rows:
        by_class[r["usage_class"]] = by_class.get(r["usage_class"], 0) + 1
    code = [r for r in rows if r["usage_class"] == "code/data"]
    code_files = sorted({r["file"] for r in code})
    ctl = units["controls"]
    attribution = None
    if args.recon_tsv and args.recon_tsv.exists():
        recon = [r for r in csv.DictReader(open(args.recon_tsv, encoding="utf-8"), delimiter="\t")
                 if r.get("usage_class") == "code/data"]
        rc: dict[str, int] = {}
        for r in recon:
            rc[r["file"]] = rc.get(r["file"], 0) + 1
        nc: dict[str, int] = {}
        for r in code:
            nc[r["file"]] = nc.get(r["file"], 0) + 1
        attribution = {
            "recon_tsv_sha256": sha256_file(args.recon_tsv),
            "recon_code_data_rows": len(recon),
            "per_file_delta": {f: nc.get(f, 0) - rc.get(f, 0) for f in sorted(set(rc) | set(nc)) if nc.get(f, 0) != rc.get(f, 0)},
        }
    result = {
        "units_complete": True,
        "git_head": head,
        "n_upstream_rows": units["upstream"]["n_upstream_rows"],
        "n_vocabulary": len(units["upstream"]["vocabulary"]),
        "n_files_scanned": sum(units[u]["n_files"] for u in unit_names() if u.startswith("root_")),
        "n_rows_total": len(rows),
        "n_code_data_rows": len(code),
        "n_code_data_files": len(code_files),
        "n_survey_data_rows": by_class.get("survey_data", 0),
        "n_test_fixture_rows": by_class.get("test/fixture", 0),
        "n_ambiguous_rows": by_class.get("ambiguous", 0),
        "n_docstring_rows": by_class.get("docstring", 0),
        "n_parse_errors": by_class.get("parse_error", 0),
        "n_skipped_large": by_class.get("skipped_large", 0),
        "recon_code_data_rows": RECON_CODE_DATA_ROWS,
        "code_data_delta_vs_recon": len(code) - RECON_CODE_DATA_ROWS,
        "control_positive_expected": ctl["positive_expected"],
        "control_positive_detected": ctl["positive_detected"],
        "control_positive_ts_expected": ctl["positive_ts_expected"],
        "control_positive_ts_detected": ctl["positive_ts_detected"],
        "control_negative_lines": ctl["negative_lines"],
        "control_negative_hits": ctl["negative_hits"],
    }
    detail = {"result": result, "units": unit_log, "code_data_files": code_files,
              "parse_error_files": sorted({r["file"] for r in rows if r["usage_class"] == "parse_error"}),
              "controls": {k: v for k, v in ctl.items() if k != "unit"}, "attribution": attribution}
    (out_dir / "detail.json").write_text(json.dumps(detail, indent=2, sort_keys=True), encoding="utf-8")
    with open(out_dir / "inventory.tsv", "w", newline="", encoding="utf-8") as fh:
        cols = ["usage_class", "file", "line", "lang", "match_kind", "name", "replacement", "confidence", "snippet"]
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["file"], int(r["line"]), r["name"])):
            w.writerow(r)
    text = json.dumps(result, indent=2, sort_keys=True)
    (out_dir / "result.json").write_text(text, encoding="utf-8")
    log.info("result written to %s", out_dir / "result.json")
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(text, encoding="utf-8")
        log.info("Bathos results written to %s", bth_path)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

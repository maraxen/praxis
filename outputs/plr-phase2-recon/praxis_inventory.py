"""Inventory praxis usage of PLR 1.0 deprecated resource-surface names (read-only recon).

Inputs:  upstream_deprecations.tsv (from upstream_deprecations.py)
Output:  TSV with one row per hit:
  area, file, line, lang, match_kind, name, replacement, confidence, byte_protected, snippet

Python files: AST (Name / Attribute / import alias / keyword arg / string constant).
Other text files (ts, js, json, jsonl, ipynb, toml, md-free): word-boundary regex.

Byte-protected = path is training data/eval pin/golden/assembled output or a generated
browser asset (changing it moves bytes someone pinned).
"""

import argparse
import ast
import csv
import re
import sys
from pathlib import Path

ROOTS = ["praxis", "web-repl", "coxswain", "training", "scripts", "plr-sema", "tests"]
SKIP_DIRS = {"node_modules", ".venv", "__pycache__", "dist", ".angular", "build", "_output",
             ".git", "site-packages", "pyodide", "vendor_pyodide"}
TEXT_EXT = {".ts", ".js", ".mjs", ".json", ".jsonl", ".ipynb", ".toml", ".yaml", ".yml", ".html"}
MAX_TEXT_BYTES = 40_000_000

# Attribute/method names whose deprecation is only meaningful on a PLR object; generic names.
AMBIGUOUS = {"tracker", "get_tip", "has_tip", "empty", "set_liquids", "get_liquids", "__init__",
             "__getattr__", "assign_child_resource", "_resolve_num_tracks"}
EXTRA = {
  # keyword args / attrs from hamilton_decks + star_decks deprecations
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


def load_upstream(tsv):
  names = {}
  for r in csv.DictReader(open(tsv), delimiter="\t"):
    q = r["qualname"]
    leaf = q.split(".")[-1]
    if r["kind"] in ("function", "class"):
      if leaf.startswith("_") and leaf != "__getattr__":
        continue
      names[leaf] = ("name", r["replacement_hint"], r["module"])
    else:
      if leaf in AMBIGUOUS:
        if leaf in ("tracker", "get_tip", "has_tip", "empty", "set_liquids", "get_liquids"):
          names.setdefault(leaf, ("attr_ambiguous", r["replacement_hint"], r["module"]))
        continue
      names[leaf] = ("attr", r["replacement_hint"], r["module"])
  for k, (kind, rep) in EXTRA.items():
    names.setdefault(k, (kind, rep, ""))
  names.pop("__getattr__", None)
  names.pop("NestedTipRack", None) if False else None
  return names


def area_of(p: str) -> str:
  if p.startswith("praxis/web-client"):
    return "praxis-webclient"
  if p.startswith("praxis/"):
    return "praxis-backend"
  if p.startswith("training/"):
    return "training/" + p.split("/")[1]
  return p.split("/")[0]


def byte_protected(p: str) -> str:
  pats = ["training/assemble/out", "training/golden", "training/eval", "/pin", "overlay_gen/out",
          "overlay_gen/frozen", "floor_gen/out", "training/verify/data", "assets/db/",
          "assets/demo-data", "browser-data", "protocol_pickles", ".pkl"]
  for s in pats:
    if s in p:
      return "yes"
  if p.endswith(".jsonl"):
    return "yes"
  return "no"


def iter_files(root: Path):
  for r in ROOTS:
    base = root / r
    if not base.exists():
      continue
    for f in base.rglob("*"):
      if not f.is_file():
        continue
      if any(part in SKIP_DIRS for part in f.relative_to(root).parts):
        continue
      yield f


def scan_py(f, rel, names, out):
  try:
    src = f.read_text()
    tree = ast.parse(src)
  except Exception as e:  # noqa: BLE001
    out.append(dict(file=rel, line=0, lang="py", match_kind="parse_error", name="", replacement="",
                    confidence="", snippet=str(e)[:120]))
    return
  lines = src.splitlines()

  def add(node, kind, name, conf="high"):
    ln = getattr(node, "lineno", 0)
    info = names[name]
    if info[0] == "attr_ambiguous":
      conf = "low"
    out.append(dict(file=rel, line=ln, lang="py", match_kind=kind, name=name,
                    replacement=info[1], confidence=conf,
                    snippet=(lines[ln - 1].strip() if 0 < ln <= len(lines) else "")[:160]))

  for n in ast.walk(tree):
    if isinstance(n, ast.Name) and n.id in names and names[n.id][0] in ("name",):
      add(n, "name", n.id)
    elif isinstance(n, ast.Attribute) and n.attr in names:
      k = names[n.attr][0]
      if k in ("name", "attr", "attr_ambiguous", "kwarg_or_attr"):
        add(n, "attribute", n.attr, "high" if k != "kwarg_or_attr" else "medium")
    elif isinstance(n, (ast.ImportFrom,)):
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


def scan_text(f, rel, names, rx, out):
  try:
    if f.stat().st_size > MAX_TEXT_BYTES:
      out.append(dict(file=rel, line=0, lang=f.suffix, match_kind="skipped_large", name="",
                      replacement="", confidence="", snippet=str(f.stat().st_size)))
      return
    txt = f.read_text(errors="replace")
  except Exception:  # noqa: BLE001
    return
  for i, line in enumerate(txt.splitlines(), 1):
    for m in rx.finditer(line):
      w = m.group(1) or m.group(2)
      if w == "rails" or m.group(2):
        name, rep = "rails", "track"
      else:
        name, rep = w, names[w][1]
      s = max(0, m.start() - 60)
      out.append(dict(file=rel, line=i, lang=f.suffix, match_kind="text", name=name,
                      replacement=rep, confidence="medium", snippet=line[s:m.end() + 60].strip()[:160]))


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default=".")
  ap.add_argument("--upstream", required=True)
  ap.add_argument("--out", required=True)
  a = ap.parse_args()
  root = Path(a.root).resolve()
  names = load_upstream(a.upstream)
  textnames = sorted((k for k, v in names.items() if v[0] in ("name",) or k in
                      ("total_tip_length", "rails_to_location", "num_rails", "with_teaching_rack",
                       "set_well_liquids", "disable_tip_trackers", "enable_tip_trackers")),
                     key=len, reverse=True)
  rx = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(map(re.escape, textnames)) +
                  r")(?![A-Za-z0-9_])|(?<![A-Za-z0-9_])[\"']?(rails)[\"']?\s*[=:]\s*\d")
  out = []
  nfiles = 0
  for f in iter_files(root):
    rel = str(f.relative_to(root))
    if f.suffix == ".py":
      nfiles += 1
      before = len(out)
      scan_py(f, rel, names, out)
      seen = {(r["line"], r["name"]) for r in out[before:]}
      extra = []
      scan_text(f, rel, names, rx, extra)
      for r in extra:
        if (r["line"], r["name"]) not in seen:
          r["match_kind"] = "text_py(comment/unparsed)"
          r["confidence"] = "low"
          out.append(r)
    elif f.suffix in TEXT_EXT:
      nfiles += 1
      scan_text(f, rel, names, rx, out)
  for r in out:
    f = r["file"]
    if re.search(r"plr-sema/data/|verify/data/plr_|survey_plr_|ingest/out/", f):
      r["usage_class"] = "survey_data(describes PLR, not a use)"
    elif "/tests/" in f or f.startswith("tests/") or ".spec." in f or "__tests__" in f or "/fixtures/" in f or "/e2e/" in f:
      r["usage_class"] = "test/fixture"
    elif r["match_kind"] in ("string", "string_kwarg") and r["confidence"] != "high" and '"""' in r.get("snippet", "")[:4]:
      r["usage_class"] = "docstring"
    elif r["confidence"] == "low":
      r["usage_class"] = "ambiguous(needs review)"
    else:
      r["usage_class"] = "code/data"
    r["area"] = area_of(r["file"])
    r["byte_protected"] = byte_protected(r["file"])
  cols = ["area", "usage_class", "file", "line", "lang", "match_kind", "name", "replacement",
          "confidence", "byte_protected", "snippet"]
  with open(a.out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
    w.writeheader()
    for r in sorted(out, key=lambda r: (r["area"], r["file"], int(r["line"]))):
      w.writerow(r)
  print(f"scanned {nfiles} files, {len(out)} hits -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
  main()

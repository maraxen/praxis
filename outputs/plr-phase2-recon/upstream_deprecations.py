"""Enumerate upstream PLR deprecations (read-only recon, no finding beyond an inventory).

Scans external/pylabrobot/pylabrobot/resources (and legacy tip tracker) for:
  - functions/methods whose body calls warnings.warn(..., DeprecationWarning)
  - functions/methods/classes whose docstring starts with "Deprecated"
Writes TSV: kind, qualname, module, file:line, warns(bool), replacement_hint, message
"""

import argparse
import ast
import csv
import re
import sys
from pathlib import Path


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


def scan(root: Path, pkg_root: Path):
  rows = []
  for f in sorted(root.rglob("*.py")):
    if f.name.endswith("_tests.py") or "/tests/" in str(f):
      continue
    mod = ".".join(f.relative_to(pkg_root.parent).with_suffix("").parts)
    tree = ast.parse(f.read_text())

    def visit(node, prefix):
      for ch in ast.iter_child_nodes(node):
        if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
          q = f"{prefix}{ch.name}"
          doc = ast.get_docstring(ch) or ""
          warns = _warn_calls(ch) if not isinstance(ch, ast.ClassDef) else []
          if isinstance(ch, ast.ClassDef):
            init = [c for c in ch.body if isinstance(c, ast.FunctionDef) and c.name == "__init__"]
            if init and doc.lower().startswith("deprecated"):
              warns = _warn_calls(init[0])
          docdep = doc.lower().startswith("deprecated")
          if warns or docdep:
            msg = warns[0][1] if warns else doc.splitlines()[0]
            rows.append({
              "kind": "class" if isinstance(ch, ast.ClassDef) else ("method" if prefix else "function"),
              "qualname": q,
              "module": mod,
              "loc": f"{f.relative_to(pkg_root.parent.parent)}:{ch.lineno}",
              "warns": "yes" if warns else "no(docstring-only)",
              "replacement_hint": _hint(msg) or _hint(doc),
              "message": " ".join(msg.split())[:240],
            })
          if isinstance(ch, ast.ClassDef):
            visit(ch, q + ".")

    visit(tree, "")
  return rows


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--plr", default="external/pylabrobot/pylabrobot")
  ap.add_argument("--out", required=True)
  a = ap.parse_args()
  pkg = Path(a.plr)
  rows = []
  for sub in ("resources",):
    p = pkg / sub
    if p.is_file():
      tmp = scan_file = p.parent
      rows += [r for r in scan(tmp, pkg) if r["loc"].endswith(tuple(f"{p.name}:{i}" for i in range(1, 99999))) ]
    else:
      rows += scan(p, pkg)
  with open(a.out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
    w.writeheader()
    w.writerows(rows)
  print(f"{len(rows)} upstream deprecations -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
  main()

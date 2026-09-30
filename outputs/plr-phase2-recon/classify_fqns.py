"""Classify probe_C FQNs: did each non-clean FQN resolve at the OLD pin (0.2.2 dd79c4c89)?

Static check against the submodule's git objects (no checkout): module file or package
__init__ exists at dd79c4c89 and the leaf name is defined/imported/star-exported there
(text heuristic; star-imports are followed one level). Output: fqn_classification.tsv
"""

import argparse
import csv
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

SUB = "external/pylabrobot"
OLD = "dd79c4c89"


@lru_cache(maxsize=None)
def show(path):
  r = subprocess.run(["git", "-C", SUB, "show", f"{OLD}:{path}"], capture_output=True, text=True)
  return r.stdout if r.returncode == 0 else None


def module_src(mod):
  p = mod.replace(".", "/")
  return show(p + ".py") or show(p + "/__init__.py"), p


def defined(mod, name, depth=0):
  src, p = module_src(mod)
  if src is None:
    return False
  if re.search(rf"(^|\n)\s*(def|class)\s+{re.escape(name)}\b|\b{re.escape(name)}\s*=|import[^\n]*\b{re.escape(name)}\b", src):
    return True
  if depth < 2:
    for m in re.finditer(r"from\s+(\.+)?([\w\.]*)\s+import\s+\*", src):
      dots, rel = m.group(1) or "", m.group(2)
      if dots:
        base = mod.split(".") if src and (show(p + "/__init__.py")) else mod.split(".")[:-1]
        base = base[: len(base) - (len(dots) - 1)] if len(dots) > 1 else base
        target = ".".join(base + ([rel] if rel else []))
      else:
        target = rel
      if defined(target, name, depth + 1):
        return True
  return False


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--probe", required=True)
  ap.add_argument("--out", required=True)
  a = ap.parse_args()
  C = json.load(open(a.probe))
  rows = []
  for f, r in sorted(C["rows"].items()):
    mod, _, name = f.rpartition(".")
    old = defined(mod, name) if r["status"] != "clean" else None
    rows.append({
      "fqn": f, "status_at_1_0": r["status"],
      "resolved_at_0_2_2": "" if old is None else ("yes" if old else "no"),
      "legacy_fqn": r.get("legacy_fqn", ""),
      "warning_or_error": (r.get("warning") or r.get("error") or "")[:160],
      "db_cols": ",".join(r["db_cols"]), "n_files": r["n_files"], "files": ",".join(r["files"]),
    })
  with open(a.out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
    w.writeheader()
    w.writerows(rows)
  from collections import Counter
  print(Counter((r["status_at_1_0"], r["resolved_at_0_2_2"]) for r in rows))


if __name__ == "__main__":
  main()

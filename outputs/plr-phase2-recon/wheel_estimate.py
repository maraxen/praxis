"""Estimate the deflated (in-wheel) size of PLR 1.0 package contents by category.

Mirrors build_wheels.strip_test_modules (drops *_tests.py, conftest.py, tests/ dirs)
then deflates every remaining file (zlib level 6 ~ zipfile default) and sums by bucket.
Recon estimate only; the PR that strips assets must measure the real wheel.
"""

import argparse
import json
import zlib
from pathlib import Path


def bucket(rel: str) -> str:
  p = rel.split("/")
  ext = rel.rsplit(".", 1)[-1] if "." in p[-1] else ""
  if "test_data" in p:
    return "test_data/*"
  if ext == "py":
    return "py"
  if rel.startswith("pylabrobot/visualizer3D/static"):
    return "visualizer3D/static"
  if "recordings" in p:
    return "driver recordings (json)"
  return ext or "noext"


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--plr", default="external/pylabrobot")
  ap.add_argument("--out", required=True)
  a = ap.parse_args()
  root = Path(a.plr)
  tot = {}
  for f in (root / "pylabrobot").rglob("*"):
    if not f.is_file() or "__pycache__" in f.parts:
      continue
    rel = str(f.relative_to(root))
    if f.name.endswith("_tests.py") or f.name == "conftest.py" or "tests" in f.parts:
      continue
    if f.suffix in (".pyc",) or f.name.endswith(".egg-info"):
      continue
    raw = f.read_bytes()
    b = bucket(rel)
    t = tot.setdefault(b, [0, 0, 0])
    t[0] += 1
    t[1] += len(raw)
    t[2] += len(zlib.compress(raw, 6))
  rows = sorted(({"bucket": k, "files": v[0], "raw_mb": round(v[1] / 1e6, 2),
                  "deflated_mb": round(v[2] / 1e6, 2)} for k, v in tot.items()),
                key=lambda r: -r["deflated_mb"])
  total = round(sum(r["deflated_mb"] for r in rows), 2)
  Path(a.out).write_text(json.dumps({"total_deflated_mb": total, "rows": rows}, indent=1))
  print("total_deflated_mb", total)
  for r in rows[:14]:
    print(r)


if __name__ == "__main__":
  main()

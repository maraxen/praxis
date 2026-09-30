"""Probe pre-1.0 (0.2.2-generated) artifacts extracted from git at 6b1e5121^1, under PLR 1.0.

  1. every serialized PLR tree in old praxis.db JSON columns + the old viz fixture:
     Resource.deserialize() at 1.0 -> ok / error class
  2. every FQN in old praxis.db: resolves (a) plainly, (b) via praxis get_class_from_fqn
     (legacy fallback), per table.column -> what breaks if the fallback were removed
Writes probe_old.json.
"""

import argparse
import importlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import runtime_probe as rp  # noqa: E402


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--olddir", required=True)
  ap.add_argument("--out", required=True)
  a = ap.parse_args()
  old = Path(a.olddir)
  per_col, jsons = rp.collect_db(old / "praxis_022.db")

  from praxis.backend.core.workcell_runtime.utils import get_class_from_fqn

  fq = {}
  for col, d in per_col.items():
    for f, n in d.items():
      if not rp.looks_like_class_fqn(f):
        continue
      if f not in fq:
        plain = rp.resolve(f)["status"]
        _, err, _ = rp.plr_warnings(lambda: get_class_from_fqn(f))
        fq[f] = {"plain": plain, "praxis_resolver_ok": err is None}
  cols = {}
  for col, d in per_col.items():
    c = Counter()
    for f, n in d.items():
      if f in fq:
        c[(fq[f]["plain"], fq[f]["praxis_resolver_ok"])] += n
    cols[col] = {f"{k[0]}|resolver_ok={k[1]}": v for k, v in c.items()}

  deser = []
  srcs = [(f"olddb:{t}.{c}", v) for t, c, v in jsons]
  srcs.append(("old_viz_fixture", (old / "set_root_resource_022.json").read_text()))
  for src, txt in srcs:
    try:
      obj = json.loads(txt)
    except Exception:  # noqa: BLE001
      continue
    acc = []
    rp.find_trees(obj, acc)
    for path, tree in acc:
      err, w = rp.try_deser(tree)
      deser.append({"src": src, "type": tree.get("type"), "name": str(tree.get("name"))[:50],
                    "ok": err is None, "err": (err or "")[:220], "warns": w[:2]})
  out = {
    "fqn_summary": dict(Counter(f"{v['plain']}|resolver_ok={v['praxis_resolver_ok']}" for v in fq.values())),
    "fallback_needed": sorted(f for f, v in fq.items() if v["plain"] != "clean" and v["praxis_resolver_ok"]
                              and v["plain"] in ("legacy_fallback_only",)),
    "broken_even_with_fallback": sorted(f for f, v in fq.items() if not v["praxis_resolver_ok"]),
    "per_column": cols,
    "deser_summary": dict(Counter((d["src"].split(".")[0], d["ok"]) for d in deser).items()).__repr__(),
    "deser_errors": Counter(d["err"].split(":")[0] + ":" + d["err"].split(":", 1)[-1][:90]
                            for d in deser if not d["ok"]).most_common(30),
    "deser_fail_rows": [d for d in deser if not d["ok"]][:80],
    "deser_n": len(deser), "deser_ok": sum(d["ok"] for d in deser),
    "deser_warn_kinds": Counter(w[:110] for d in deser for w in d["warns"]).most_common(10),
  }
  Path(a.out).write_text(json.dumps(out, indent=1, default=str))
  print(json.dumps({k: out[k] for k in ("fqn_summary", "deser_n", "deser_ok")}, default=str))


if __name__ == "__main__":
  main()

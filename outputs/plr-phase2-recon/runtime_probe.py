"""Runtime probe at the current PLR pin (read-only recon; writes only under phase2_tools/).

Sections (each written to its own JSON so a crash keeps earlier sections):
  A factories   deprecated factory vs its replacement: warns? serialize() equal? diff keys
  B rails       deck.assign_child_resource(rails=N) vs (track=N): same location? bounds
  C fqns        every distinct pylabrobot.* FQN in praxis.db + web-client assets + tests:
                clean / warns / legacy_fallback_only / unresolvable
  D db          praxis.db per table.column counts of those FQN classes
  E deser       Resource.deserialize() of every serialized PLR tree found in praxis.db JSON
                columns and JSON fixtures
"""

import argparse
import importlib
import json
import re
import sqlite3
import sys
import traceback
import warnings
from pathlib import Path

FQN_RX = re.compile(r"pylabrobot(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


def plr_warnings(fn):
  with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
      val = fn()
      err = None
    except Exception as e:  # noqa: BLE001
      val, err = None, f"{type(e).__name__}: {e}"[:300]
  dep = [str(x.message)[:200] for x in w if issubclass(x.category, (DeprecationWarning, FutureWarning))]
  return val, err, dep


def ddiff(a, b, path=""):
  out = []
  if isinstance(a, dict) and isinstance(b, dict):
    for k in sorted(set(a) | set(b)):
      if k not in a or k not in b:
        out.append(f"{path}/{k}:missing_in_{'old' if k not in a else 'new'}")
      else:
        out += ddiff(a[k], b[k], f"{path}/{k}")
  elif isinstance(a, list) and isinstance(b, list):
    if len(a) != len(b):
      out.append(f"{path}:len {len(a)}!={len(b)}")
    for i, (x, y) in enumerate(zip(a, b)):
      out += ddiff(x, y, f"{path}[{i}]")
  elif a != b:
    out.append(f"{path}: {str(a)[:60]!r} -> {str(b)[:60]!r}")
  return out


def section_a():
  pairs = [
    ("pylabrobot.resources.corning.plates.Cor_96_wellplate_360ul_Fb",
     "pylabrobot.resources.corning.plates.cor_96_wellplate_360uL_Fb", {}),
    ("pylabrobot.resources.corning.plates.Cor_96_wellplate_2mL_Vb",
     "pylabrobot.resources.corning.plates.cor_96_wellplate_2mL_Vb", {}),
    ("pylabrobot.resources.hamilton.tip_carriers.TIP_CAR_480_A00",
     "pylabrobot.resources.hamilton.tip_carriers.hamilton_tip_carrier_L5", {}),
    ("pylabrobot.resources.hamilton.tip_carriers.TIP_CAR_480BC_A00",
     "pylabrobot.resources.hamilton.tip_carriers.hamilton_tip_carrier_L5", {}),
    ("pylabrobot.resources.hamilton.plate_carriers.PLT_CAR_L5AC_A00",
     "pylabrobot.resources.hamilton.plate_carriers.hamilton_plate_carrier_L5_ac", {}),
    ("pylabrobot.resources.hamilton.troughs.hamilton_1_trough_200ml_Vb",
     "pylabrobot.resources.hamilton.troughs.hamilton_1_trough_200mL_Vb", {}),
    ("pylabrobot.resources.hamilton.mfx_carriers.MFX_CAR_L5_base",
     "pylabrobot.resources.hamilton.mfx_carriers.hamilton_mfx_carrier_L5_base", {"modules": {}}),
  ]
  res = []
  for old, new, kw in pairs:
    row = {"old": old, "new": new}
    om, on = old.rsplit(".", 1)
    nm, nn = new.rsplit(".", 1)
    fo, e1, _ = plr_warnings(lambda: getattr(importlib.import_module(om), on))
    fn, e2, _ = plr_warnings(lambda: getattr(importlib.import_module(nm), nn))
    if e1 or e2:
      row["error"] = e1 or e2
      res.append(row)
      continue
    ro, eo, wo = plr_warnings(lambda: fo(name="x", **kw))
    rn, en, wn = plr_warnings(lambda: fn(name="x", **kw))
    row.update(old_warns=wo, new_warns=wn, old_err=eo, new_err=en)
    if ro is not None and rn is not None:
      so, sn = ro.serialize(), rn.serialize()
      d = ddiff(so, sn)
      row.update(serialize_equal=not d, diff=d[:15], n_diff=len(d),
                 old_model=so.get("model"), new_model=sn.get("model"),
                 old_type=so.get("type"), new_type=sn.get("type"))
    res.append(row)
  # top-level re-exports used by praxis imports
  import pylabrobot.resources as R
  row = {"toplevel_reexports": {n: hasattr(R, n) for n in [
    "Cor_96_wellplate_360ul_Fb", "cor_96_wellplate_360uL_Fb", "TIP_CAR_480_A00",
    "hamilton_tip_carrier_L5", "PLT_CAR_L5AC_A00", "hamilton_plate_carrier_L5_ac",
    "NestedTipRack", "StandingTipRack", "hamilton_1_trough_200mL_Vb"]}}
  res.append(row)
  return res


def section_b():
  from pylabrobot.resources.hamilton import STARDeck, STARLetDeck
  from pylabrobot.resources.hamilton.tip_carriers import hamilton_tip_carrier_L5
  out = []
  for deckf in (STARLetDeck, STARDeck):
    for n in (1, 3, 8, 9, 15, 21, 25, 30, 31, 32):
      row = {"deck": deckf.__name__, "n": n}
      for kw in ("rails", "track"):
        d = deckf()
        c = hamilton_tip_carrier_L5(name="c")
        _, err, w = plr_warnings(lambda: d.assign_child_resource(c, **{kw: n}, ignore_collision=True))
        row[kw] = None if err else str(c.location)
        row[kw + "_err"] = err
        row[kw + "_warned"] = bool(w)
      row["same_location"] = row["rails"] == row["track"] and row["rails"] is not None
      out.append(row)
    d = deckf()
    out.append({"deck": deckf.__name__, "num_tracks": d.num_tracks,
                "serialize_keys": sorted(k for k in d.serialize() if "rail" in k or "track" in k)})
  return out


def resolve(fqn):
  mod, _, name = fqn.rpartition(".")
  r = {"fqn": fqn}
  obj, err, w = plr_warnings(lambda: getattr(importlib.import_module(mod), name))
  if err is None:
    r["status"] = "warns" if w else "clean"
    r["warning"] = w[0] if w else ""
    # calling a deprecated factory is what warns, not importing it
    if callable(obj) and not isinstance(obj, type) and not w:
      src_ok = True
      try:
        import inspect
        src = inspect.getsource(obj)
        if "DeprecationWarning" in src:
          r["status"] = "deprecated_alias"
      except Exception:  # noqa: BLE001
        src_ok = False
      r["src_checked"] = src_ok
    return r
  parts = mod.split(".")
  if len(parts) >= 2 and parts[1] != "legacy":
    lm = ".".join(["pylabrobot", "legacy", *parts[1:]])
    obj2, err2, _ = plr_warnings(lambda: getattr(importlib.import_module(lm), name))
    if err2 is None:
      r["status"] = "legacy_fallback_only"
      r["legacy_fqn"] = f"{lm}.{name}"
      return r
  import pylabrobot.resources as R
  if hasattr(R, name):
    r["status"] = "toplevel_name_fallback_only"  # what web_bridge._import_class does
    return r
  r["status"] = "unresolvable"
  r["error"] = err
  return r


def collect_db(db):
  con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
  per_col = {}
  jsons = []
  for (t,) in con.execute("select name from sqlite_master where type='table'"):
    cols = [r[1] for r in con.execute(f"pragma table_info('{t}')")]
    for c in cols:
      for (v,) in con.execute(f'select "{c}" from "{t}"'):
        if not isinstance(v, str) or "pylabrobot" not in v:
          if isinstance(v, str) and v.startswith("{") and '"type"' in v:
            jsons.append((t, c, v))
          continue
        for f in set(FQN_RX.findall(v)):
          per_col.setdefault(f"{t}.{c}", {}).setdefault(f, 0)
          per_col[f"{t}.{c}"][f] += 1
        if v.startswith("{") and '"type"' in v:
          jsons.append((t, c, v))
  return per_col, jsons


def collect_files(root):
  found = {}
  globs = ["praxis/web-client/src/**/*.ts", "praxis/web-client/src/**/*.json",
           "praxis/web-client/e2e/**/*.ts", "tests/**/*.py", "web-repl/tests/**/*.json",
           "web-repl/overlay/**/*.py", "praxis/backend/**/*.py", "scripts/*.py"]
  for g in globs:
    for f in root.glob(g):
      if "node_modules" in f.parts or f.stat().st_size > 30_000_000:
        continue
      try:
        txt = f.read_text(errors="replace")
      except Exception:  # noqa: BLE001
        continue
      for m in set(FQN_RX.findall(txt)):
        found.setdefault(m, set()).add(str(f.relative_to(root)))
  return found


def looks_like_class_fqn(f):
  leaf = f.rsplit(".", 1)[-1]
  return leaf[:1].isupper() or "_" in leaf and not leaf.islower() or re.match(r"^[a-z]+_\d", leaf)


def try_deser(obj):
  from pylabrobot.resources import Resource
  _, err, w = plr_warnings(lambda: Resource.deserialize(obj, allow_marshal=True))
  return err, w


def find_trees(obj, acc, path=""):
  if isinstance(obj, dict):
    if "type" in obj and "name" in obj and ("children" in obj or "size_x" in obj):
      acc.append((path, obj))
      return
    for k, v in obj.items():
      find_trees(v, acc, f"{path}/{k}")
  elif isinstance(obj, list):
    for i, v in enumerate(obj):
      find_trees(v, acc, f"{path}[{i}]")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default=".")
  ap.add_argument("--db", default="praxis/web-client/src/assets/db/praxis.db")
  ap.add_argument("--outdir", required=True)
  ap.add_argument("--sections", default="A,B,C,D,E")
  a = ap.parse_args()
  root = Path(a.root).resolve()
  out = Path(a.outdir)
  secs = a.sections.split(",")

  def dump(name, obj):
    (out / f"probe_{name}.json").write_text(json.dumps(obj, indent=1, default=str))
    print(f"[{name}] written", file=sys.stderr)

  for s, fn in (("A", section_a), ("B", section_b)):
    if s in secs:
      try:
        dump(s, fn())
      except Exception:  # noqa: BLE001
        dump(s, {"crash": traceback.format_exc()})

  if "C" in secs or "D" in secs or "E" in secs:
    per_col, jsons = collect_db(root / a.db)
    files = collect_files(root)
    allf = set(files) | {f for d in per_col.values() for f in d}
    cand = sorted(f for f in allf if looks_like_class_fqn(f))
    res = {f: resolve(f) for f in cand}
    for f, r in res.items():
      r["files"] = sorted(files.get(f, []))[:12]
      r["n_files"] = len(files.get(f, []))
      r["db_cols"] = sorted(c for c, d in per_col.items() if f in d)
    dump("C", {"n": len(res), "by_status": {s: sum(1 for r in res.values() if r["status"] == s)
                                              for s in sorted({r["status"] for r in res.values()})},
               "rows": res})
    db_summary = {}
    for col, d in per_col.items():
      st = {}
      for f, n in d.items():
        s = res[f]["status"] if f in res else "not_a_class_fqn"
        st[s] = st.get(s, 0) + n
      db_summary[col] = {"distinct": len(d), "rows_by_status": st}
    dump("D", db_summary)
    if "E" in secs:
      rows = []
      srcs = [(f"db:{t}.{c}", v) for t, c, v in jsons]
      for g in ["web-repl/tests/fixtures/**/*.json", "praxis/web-client/src/assets/**/*.json",
                "praxis/web-client/e2e/fixtures/**/*.json", "tests/**/*.json"]:
        for f in root.glob(g):
          if f.stat().st_size < 30_000_000:
            srcs.append((str(f.relative_to(root)), f.read_text(errors="replace")))
      for src, txt in srcs:
        try:
          obj = json.loads(txt)
        except Exception:  # noqa: BLE001
          continue
        acc = []
        find_trees(obj, acc)
        for path, tree in acc:
          err, w = try_deser(tree)
          rows.append({"src": src, "path": path[:120], "type": tree.get("type"),
                       "name": str(tree.get("name"))[:60], "ok": err is None,
                       "err": err, "warns": w[:3]})
      dump("E", {"n": len(rows), "n_ok": sum(r["ok"] for r in rows), "rows": rows})


if __name__ == "__main__":
  main()

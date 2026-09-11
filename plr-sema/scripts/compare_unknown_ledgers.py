"""Compare two `unknown_ledger.py` artifact pairs field by field (sprint 135, T58, #5043).

Prints the header provenance, the per-reason finding counts with deltas, the
soundness block of each companion `*.oracle_replay.json`, the per-method
`scope_verdict` table for `pick_up_tips`, every `volume_state_unknown` cluster,
and every change in `n_findings_decided_by_site` / `n_resolved_by_rule`. Written
so a re-measure's "nothing moved" is a printed fact, not an eyeballed one.

    uv run python scripts/compare_unknown_ledgers.py \
        --base ../outputs/plr-sema/unknown_ledger_260910_inc8.json \
        --new  ../outputs/plr-sema/unknown_ledger_260911_volwire.json

The companion replay report is resolved from each ledger's own
`header.oracle_replay_report_path` (relative to the ledger's directory) unless
`--base-replay` / `--new-replay` override it.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

log = logging.getLogger("compare_unknown_ledgers")


def _load(path: Path) -> dict:
  return json.loads(path.read_text(encoding="utf-8"))


def _replay_for(ledger_path: Path, ledger: dict, override: Path | None) -> dict:
  if override is not None:
    return _load(override)
  rel = ledger["header"].get("oracle_replay_report_path")
  if not rel:
    msg = f"{ledger_path}: header has no oracle_replay_report_path; pass --*-replay"
    raise SystemExit(msg)
  candidate = ledger_path.parent / Path(rel).name
  if not candidate.exists():
    candidate = (ledger_path.parent / rel).resolve()
  return _load(candidate)


def _volume_clusters(led: dict) -> list[tuple]:
  return [
    (
      c["plr_site"].split("/")[-1],
      c["condition"][:60],
      c["n_findings"],
      c["n_ops_blocked"],
      c.get("n_ops_sole_blocker"),
    )
    for c in led["clusters"]
    if c["reason"] == "volume_state_unknown"
  ]


def compare(
  base_path: Path, new_path: Path, base_replay: Path | None, new_replay: Path | None
) -> int:
  base, new = _load(base_path), _load(new_path)
  base_r, new_r = _replay_for(base_path, base, base_replay), _replay_for(new_path, new, new_replay)
  hb, hn = base["header"], new["header"]
  print("header.git_head       ", hb["git_head"][:8], "->", hn["git_head"][:8])
  same_sha = hb["contracts_sha256"] == hn["contracts_sha256"]
  print(
    "header.contracts_sha  ",
    hb["contracts_sha256"][:12],
    "->",
    hn["contracts_sha256"][:12],
    "SAME" if same_sha else "DIFFERENT",
  )
  for k in ("n_ops_executed", "n_ops_unknown", "n_findings_total", "n_clusters"):
    print(f"{k:22}", base.get(k), "->", new.get(k))
  print("n_findings_by_reason:")
  moved = 0
  for k in sorted(set(base["n_findings_by_reason"]) | set(new["n_findings_by_reason"])):
    b, n = base["n_findings_by_reason"].get(k, 0), new["n_findings_by_reason"].get(k, 0)
    moved += n != b
    print(f"  {k:28} {b:5} -> {n:5}  delta {n - b:+}")
  sf_b, sf_n = base_r.get("summary_flat", {}), new_r.get("summary_flat", {})
  for k in (
    "unsound",
    "unsound_scoped",
    "totality_violations",
    "check_graph_exceptions",
    "unknown_rate",
    "rows_setup_error",
    "gate_go",
    "n_findings_decided",
  ):
    print(f"summary_flat.{k:22}", sf_b.get(k), "->", sf_n.get(k))
  g_b, g_n = base_r.get("gate", {}), new_r.get("gate", {})
  for k in ("n_operations_scope_verdict_safe", "unsound", "unsound_scoped", "n_findings_decided"):
    print(f"gate.{k:30}", g_b.get(k), "->", g_n.get(k))
  vb = base_r.get("scope_verdict_by_method", {}) or {}
  vn = new_r.get("scope_verdict_by_method", {}) or {}
  for m in sorted(set(vb) | set(vn)):
    if vb.get(m) != vn.get(m):
      print("  scope_verdict_by_method CHANGED", m, vb.get(m), "->", vn.get(m))
  put_b = (vb.get("pick_up_tips") or {}).get("n_scope_verdict_safe")
  put_n = (vn.get("pick_up_tips") or {}).get("n_scope_verdict_safe")
  print("pick_up_tips n_scope_verdict_safe:", put_b, "->", put_n)
  print("volume_state_unknown clusters baseline:")
  for c in _volume_clusters(base):
    print("  ", c)
  print("volume_state_unknown clusters new:")
  for c in _volume_clusters(new):
    print("  ", c)
  d_b, d_n = (
    base_r.get("n_findings_decided_by_site", {}),
    new_r.get("n_findings_decided_by_site", {}),
  )
  changes = [
    (s, d_b.get(s), d_n.get(s)) for s in sorted(set(d_b) | set(d_n)) if d_b.get(s) != d_n.get(s)
  ]
  print("decided-by-site changes:", len(changes))
  for s, b, n in changes:
    print(f"  {s.split('/')[-1]:60} {b} -> {n}")
  rb, rn = base_r.get("n_resolved_by_rule", {}), new_r.get("n_resolved_by_rule", {})
  rchanges = [
    (r, rb.get(r), rn.get(r)) for r in sorted(set(rb) | set(rn)) if rb.get(r) != rn.get(r)
  ]
  print("n_resolved_by_rule changes:", len(rchanges))
  for r, b, n in rchanges:
    print(f"  {r}: {b} -> {n}")
  log.info("reason counts moved: %d; contracts identical: %s", moved, same_sha)
  return 0


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
  )
  ap.add_argument("--base", type=Path, required=True, help="baseline unknown_ledger JSON")
  ap.add_argument("--new", type=Path, required=True, help="new unknown_ledger JSON")
  ap.add_argument("--base-replay", type=Path, default=None)
  ap.add_argument("--new-replay", type=Path, default=None)
  ap.add_argument("-v", "--verbose", action="store_true")
  args = ap.parse_args(argv)
  logging.basicConfig(
    level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s"
  )
  return compare(args.base, args.new, args.base_replay, args.new_replay)


if __name__ == "__main__":
  sys.exit(main())

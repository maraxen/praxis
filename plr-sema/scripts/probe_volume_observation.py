"""Record the `volume_tracking_observed` value `run_row` passes to `run_static_calls` (sprint 135, T58, #5043).

Wraps `oracle_replay.run_static_calls` with a recorder -- the same seam
`TestT57VolumeObservationThreading` uses -- and drives `unknown_ledger.main`
over a bounded prefix of the corpus, then prints a histogram of the keyword's
value as received. `<ABSENT>` means the keyword was not passed at all (the
pre-#5043 behaviour). Run from `plr-sema/`:

    uv run python scripts/probe_volume_observation.py --limit 120

Sprint 135 measured `{'True': 30}` over `--limit 120` at 80dd7103: the wire is
live and the runtime observes tracking ON for every executed benchmark row.
"""

from __future__ import annotations

import argparse
import collections
import logging
import sys
import tempfile
from pathlib import Path

log = logging.getLogger("probe_volume_observation")


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
  )
  ap.add_argument("--corpus", default="../training/assemble/out/corpus_p25.jsonl")
  ap.add_argument("--sidecar", default="../training/assemble/out/corpus_p25_sidecar.jsonl")
  ap.add_argument(
    "--limit", type=int, default=120, help="rows to feed unknown_ledger (bounded, this is a probe)"
  )
  ap.add_argument("--eval-dir", type=Path, default=Path(__file__).resolve().parent.parent / "eval")
  ap.add_argument("-v", "--verbose", action="store_true")
  args = ap.parse_args(argv)
  logging.basicConfig(
    level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s"
  )

  sys.path.insert(0, str(args.eval_dir))
  import oracle_replay  # noqa: PLC0415
  import unknown_ledger  # noqa: PLC0415

  seen: collections.Counter[str] = collections.Counter()
  real = oracle_replay.run_static_calls

  def recording(*a, **kw):
    seen[repr(kw.get("volume_tracking_observed", "<ABSENT>"))] += 1
    return real(*a, **kw)

  oracle_replay.run_static_calls = recording
  tmp = Path(tempfile.mkdtemp(prefix="probe_volume_observation_"))
  rc = unknown_ledger.main(
    [
      "--corpus",
      args.corpus,
      "--sidecar",
      args.sidecar,
      "--limit",
      str(args.limit),
      "--report",
      str(tmp / "ledger.json"),
      "--replay-report",
      str(tmp / "replay.json"),
    ]
  )
  print("unknown_ledger rc:", rc)
  print("volume_tracking_observed as received by run_static_calls:", dict(seen))
  return 0 if rc == 0 else rc


if __name__ == "__main__":
  sys.exit(main())

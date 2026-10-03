"""Regenerate tests/fixtures/extract_goldens.json from the CURRENT extractor.

Run only when an extractor behavior change is intended and reviewed:
    uv run --no-sync python3 plr-sema/scripts/capture_extract_goldens.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from _extract_corpus import GOLDENS, corpus, dump  # noqa: E402

log = logging.getLogger("capture_extract_goldens")


def _extractor():
    try:
        from plr_sema.extract.computation_graph_extractor import extract_graph_from_source
    except ImportError:
        from praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor import (
            extract_graph_from_source,
        )
    return extract_graph_from_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=GOLDENS)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    extract = _extractor()
    goldens = {key: dump(extract(source, fn)) for key, source, fn in corpus()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(goldens, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    log.info("wrote %d goldens (%d non-null) to %s", len(goldens),
             sum(v is not None for v in goldens.values()), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

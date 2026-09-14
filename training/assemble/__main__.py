"""CLI: regenerate the P2.5 assembled corpus. Idempotent by construction.

    uv run --package training python -m assemble [--out DIR]

Same committed inputs => byte-identical outputs (teacher caches upstream make
this free; assembly itself is a pure function). A drift alarm test re-runs
this and compares against the committed artifacts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .build import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None, help="output directory (default training/assemble/out)")
    args = parser.parse_args()
    main(args.out)

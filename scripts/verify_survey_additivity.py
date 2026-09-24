#!/usr/bin/env python3
"""Verify a `plr_preconditions.json` regeneration is strictly additive
relative to a prior snapshot (round-5 T0, F1's discharging condition).

"Strictly additive" means: every PRE-EXISTING field on every PRE-EXISTING
record is byte-identical between the two artifacts, and the only permitted
difference is the presence of new fields (e.g. `dropped_calls`) or new
top-level meta keys. Positional (index-aligned) comparison is valid here
because `survey()` iterates `iter_source_files()` -- `sorted()` over the
scanned paths -- deterministically, and neither snapshot changes that
traversal order; do not naively key by `(module, qualname)` to compare, since
that key is not unique in the artifact (round-5 F6) and a diff that
deduplicates on it will silently under-count (the very trap the round-5
challenger's own F1 reproduction fell into, per the defense's F6 writeup).

Usage:
    uv run python scripts/verify_survey_additivity.py \\
        --base /tmp/plr_preconditions.json.orig \\
        --new training/verify/data/plr_preconditions.json
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

#: Fields present before round-5 T0 -- any value-level change here is a
#: non-additive diff.
PRE_EXISTING_FIELDS = (
    "qualname", "class_name", "module", "file", "lineno", "params",
    "findings", "delegates_to", "unresolved_calls",
)
PRE_EXISTING_META_FIELDS = (
    "plr_root", "version", "target_class_filter",
    "total_functions_scanned", "total_functions_in_report",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    args = parser.parse_args()

    base = json.loads(args.base.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))

    non_additive_meta = [f for f in PRE_EXISTING_META_FIELDS if base.get(f) != new.get(f)]
    base_funcs: list[dict[str, Any]] = base["functions"]
    new_funcs: list[dict[str, Any]] = new["functions"]

    log.info("records base/new: %d %d", len(base_funcs), len(new_funcs))
    if len(base_funcs) != len(new_funcs):
        log.error("record COUNT changed -- not additive by construction")
        return 1

    non_additive_diffs = 0
    for i, (b, n) in enumerate(zip(base_funcs, new_funcs, strict=True)):
        for field_name in PRE_EXISTING_FIELDS:
            if b.get(field_name) != n.get(field_name):
                non_additive_diffs += 1
                log.warning(
                    "non-additive diff at record %d (%s.%s), field %r",
                    i, b.get("module"), b.get("qualname"), field_name,
                )

    new_only_keys = set(new_funcs[0].keys()) - set(base_funcs[0].keys()) if new_funcs else set()
    with_dropped = sum(1 for r in new_funcs if r.get("dropped_calls"))
    total_dropped_calls = sum(len(r.get("dropped_calls", [])) for r in new_funcs)

    log.info("non-additive diffs: %d  (0 == strictly additive)", non_additive_diffs)
    log.info("non-additive meta-field diffs: %s", non_additive_meta or "none")
    log.info("new record-level keys: %s", sorted(new_only_keys))
    log.info("records with >=1 dropped_calls entry: %d", with_dropped)
    # (260903, T25) `dropped_calls` entries are no longer deduplicated
    # per-record -- multiplicity is preserved (spec §14.0.2's schema-change
    # box) -- so this total now counts every recorded call site, not every
    # distinct expression.
    log.info("total dropped_calls entries: %d", total_dropped_calls)

    return 0 if (non_additive_diffs == 0 and not non_additive_meta) else 1


if __name__ == "__main__":
    raise SystemExit(main())

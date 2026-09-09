"""Package and data versioning constants for the ingest pipeline.

Version strings and canonical pinned values used across all five command modules.
These live here so they are visible and reviewable alongside the data files they version.
"""

from types import MappingProxyType
from typing import Any, Final, Mapping

# Pipeline versioning
INGEST_VERSION: Final[str] = "1"
REGISTRY_VERSION: Final[str] = "2"
AUDIT_RULES_VERSION: Final[str] = "1"
GAP_THRESHOLDS_VERSION: Final[str] = "2"  # rev 2: T1 demoted to an invariant (C12)
EVAL_SPLIT_VERSION: Final[str] = "1"
LICENSE_RULES_VERSION: Final[str] = "1"

# Pinned file hashes (set by Task 2+; Task 1 leaves placeholders)
LICENSE_RULES_SHA256: Final[str] = "c1a8574a78ef021ceb7d3306dcd392607749ae0b6cac13d97e15cb7dd073fe78"

# Gap thresholds (§6.4). Committed BEFORE gap.py exists (PM-2) and changeable only by
# a diff that also bumps GAP_THRESHOLDS_VERSION.
GAP_THRESHOLDS: Final[Mapping[str, int]] = MappingProxyType({
    "T2_low_shape_lh_verbs_min":      5,   # of 10, "low" = < 3 distinct param shapes
    "T2_shape_floor":                 3,   # = matrix examples_per_cell
    "T3_out_of_surface_anchors_min": 25,   # recipes naming no in-surface verb
    "T3_distinct_chapters_min":       8,
})

#: NOT a threshold: a pinned expectation the report must reproduce, else exit 1 (C12).
#: T1 counts the phase-2 liquid-handler verbs with zero provenance=="naturalness" rows;
#: this is a measurement-pipeline sanity check against a hand-derivation (§6.5), not a
#: decision gate.
T1_INVARIANT: Final[Mapping[str, Any]] = MappingProxyType({
    "count": 5,
    "verbs": ("move_lid", "move_plate", "move_resource", "stamp", "transfer"),
})

#!/usr/bin/env python3
"""260901 T14 (backlog #4862): the analysis behind
``.praxia/docs/research/260901_plr-jit-nonlegacy-gap-ledger-reading.md``.

Reads the already-committed ``upstream_nonlegacy`` survey and derived
artifacts (``training/verify/data/plr_preconditions.upstream_nonlegacy.json``,
``plr-sema/data/derived_contracts.upstream_nonlegacy.json``,
``plr-sema/data/gap_ledger.upstream_nonlegacy.json``) and computes the
cross-tabulations the doc quotes but ``build_gap_ledger`` itself does not
publish (schema-stable per-family breakdown was judged not worth adding to
the shipped ledger's normative schema for a one-time reading -- see the
doc's own note). Pure read of committed data; touches no live PLR source
tree (unlike ``scan_dropped_receiver_calls``, which needs the T13 extraction
that no longer exists on disk -- see ``tests/test_check_graph_nonlegacy.py``'s
module docstring).

Usage::

    uv run python plr-sema/scripts/nonlegacy_gap_ledger_reading.py
    uv run python plr-sema/scripts/nonlegacy_gap_ledger_reading.py --json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

from plr_sema.derive import (  # noqa: E402
    SurveyRecord,
    build_contract_keys,
    build_index,
    derive_contract,
    load_survey,
)

logger = logging.getLogger(__name__)

SURVEY_JSON = REPO_ROOT / "training" / "verify" / "data" / "plr_preconditions.upstream_nonlegacy.json"
CONTRACTS_JSON = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.upstream_nonlegacy.json"
GAP_LEDGER_JSON = REPO_ROOT / "plr-sema" / "data" / "gap_ledger.upstream_nonlegacy.json"

#: The eight families named in the T14 brief, matched by a module-path
#: substring against pylabrobot.<family>.* -- the same substring convention
#: T13's own commit message table used ("Families with findings: resources
#: 184, revvity 160, agilent 135, ...").
FAMILIES: tuple[str, ...] = (
    "resources",
    "revvity",
    "agilent",
    "hamilton",
    "io",
    "high_res",
    "brooks",
    "azenta",
    "molecular_devices",
    "inheco",
)


def _family_of(module: str) -> str | None:
    if not module.startswith("pylabrobot."):
        return None
    top = module.split(".", 2)[1]
    return top if top in FAMILIES else top  # report the real top-level package name


def family_breakdown(records: list[SurveyRecord], contracts: dict) -> dict[str, dict]:
    """Per top-level-package breakdown: methods attempted, methods with
    >=1 finding, methods whose OWN contract carries >=1 guard, methods whose
    contract carries >=1 gap -- all read from the already-derived contract
    table (no re-derivation)."""
    by_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {"finding_bearing": 0, "with_guards": 0, "with_gaps": 0}
    )
    contract_keys = build_contract_keys(records)
    for rec in records:
        if not rec.findings:
            continue
        top = rec.module.split(".", 2)[1] if rec.module.startswith("pylabrobot.") else rec.module
        key = contract_keys[(rec.module, rec.qualname, rec.lineno)]
        contract = contracts.get(key, {"guards": [], "gaps": []})
        by_family[top]["finding_bearing"] += 1
        if contract["guards"]:
            by_family[top]["with_guards"] += 1
        if contract["gaps"]:
            by_family[top]["with_gaps"] += 1
    return dict(sorted(by_family.items(), key=lambda kv: -kv[1]["finding_bearing"]))


def depth_histogram(records: list[SurveyRecord], index: dict) -> Counter:
    """Guard-depth histogram over the whole finding-bearing population:
    depth 0 = own body, depth > 0 = inlined from a delegate. Answers "where
    does the closure terminate" -- a population dominated by depth 0 means
    delegation contributes little; depth > 0 mass means real cross-method
    inlining is happening."""
    hist: Counter = Counter()
    finding_bearing = [r for r in records if r.findings]
    for rec in finding_bearing:
        contract = derive_contract(rec.module, rec.qualname, index)
        for guard in contract.guards:
            hist[guard.depth] += 1
    return hist


def gap_reason_by_family(records: list[SurveyRecord], index: dict) -> dict[str, Counter]:
    """Which family's closures produce the 158 unresolved_delegate gaps
    (the whole-surface total -- by_reason in the shipped ledger) -- answers
    "where does the unresolved frontier concentrate"."""
    by_family: dict[str, Counter] = defaultdict(Counter)
    finding_bearing = [r for r in records if r.findings]
    for rec in finding_bearing:
        top = rec.module.split(".", 2)[1] if rec.module.startswith("pylabrobot.") else rec.module
        contract = derive_contract(rec.module, rec.qualname, index)
        for reason, _name in contract.gaps:
            by_family[top][reason] += 1
    return dict(by_family)


def self_contained_check(records: list[SurveyRecord], index: dict) -> dict:
    """Direct test of the task brief's hypothesis ("driver code is more
    self-contained than orchestration code that delegates across classes").
    Operationalized as: of every DELEGATE NAME a finding-bearing record
    resolves via `delegates_to`, what fraction resolves to a record in the
    SAME top-level family package vs. a DIFFERENT one vs. fails to resolve
    at all (-> a gap)? Cross-family delegation is the closure crossing an
    architectural boundary; same-family delegation stays inside one driver
    module's own concern."""
    same_family = 0
    cross_family = 0
    unresolved = 0
    finding_bearing = [r for r in records if r.findings]
    for rec in finding_bearing:
        rec_family = rec.module.split(".", 2)[1] if rec.module.startswith("pylabrobot.") else rec.module
        for name in rec.delegates_to:
            resolved = None
            if rec.class_name is not None:
                same_class_key = (rec.module, f"{rec.class_name}.{name}")
                if same_class_key in index:
                    resolved = same_class_key
            if resolved is None:
                module_level_key = (rec.module, name)
                if module_level_key in index:
                    resolved = module_level_key
            if resolved is None:
                unresolved += 1
                continue
            target_module = resolved[0]
            target_family = (
                target_module.split(".", 2)[1] if target_module.startswith("pylabrobot.") else target_module
            )
            if target_family == rec_family:
                same_family += 1
            else:
                cross_family += 1
    total = same_family + cross_family + unresolved
    return {
        "same_family": same_family,
        "cross_family": cross_family,
        "unresolved_delegate_name": unresolved,
        "total_delegate_names": total,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a table.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    records = load_survey(SURVEY_JSON)
    index = build_index(records)
    contracts = json.loads(CONTRACTS_JSON.read_text())["contracts"]

    result = {
        "family_breakdown": family_breakdown(records, contracts),
        "depth_histogram": dict(sorted(depth_histogram(records, index).items())),
        "gap_reason_by_family": {
            k: dict(v) for k, v in sorted(gap_reason_by_family(records, index).items())
        },
        "self_contained_check": self_contained_check(records, index),
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    logger.info("=== per-family breakdown (finding-bearing methods) ===")
    for family, stats in result["family_breakdown"].items():
        logger.info(
            "  %-20s finding_bearing=%-4d with_guards=%-4d with_gaps=%-4d",
            family,
            stats["finding_bearing"],
            stats["with_guards"],
            stats["with_gaps"],
        )

    logger.info("")
    logger.info("=== guard depth histogram (0 = own body, >0 = inlined) ===")
    for depth, count in result["depth_histogram"].items():
        logger.info("  depth=%-3d count=%d", depth, count)

    logger.info("")
    logger.info("=== gap reason by family (top 10 by total gaps) ===")
    ranked = sorted(
        result["gap_reason_by_family"].items(), key=lambda kv: -sum(kv[1].values())
    )
    for family, reasons in ranked[:10]:
        logger.info("  %-20s %s", family, reasons)

    logger.info("")
    logger.info("=== self-containment check (delegate-name resolution target) ===")
    sc = result["self_contained_check"]
    total = sc["total_delegate_names"] or 1
    logger.info(
        "  same_family=%d (%.1f%%)  cross_family=%d (%.1f%%)  unresolved=%d (%.1f%%)  total=%d",
        sc["same_family"],
        100 * sc["same_family"] / total,
        sc["cross_family"],
        100 * sc["cross_family"] / total,
        sc["unresolved_delegate_name"],
        100 * sc["unresolved_delegate_name"] / total,
        sc["total_delegate_names"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

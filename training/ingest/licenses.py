"""License verification and descend-rule checking for the ingest pipeline.

Performs mechanical verification of license files in all cloned repositories,
computes the descend-rule outcome for Increment 2+ eligibility, and generates
the license report and SOURCES.md.

§2.5–2.6 define the license verification logic, enums, and descend rule.
§7.1's hierarchy table defines IngestError and the exit code semantics.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Final, Mapping, Sequence, Tuple

from . import cli, versions
from .io import write_artifact
from .sources import SourceRow, load_registry, RegistryError


# Enums for license verification
class LicenseTier(IntEnum):
    """License tier classification."""

    FACTS_ONLY = 0  # API names, verb frequencies, param names, task vocabulary, counts
    STRUCTURE = 1  # normalized MinedCall rows: literal values, symbolic refs, ordering
    EXPRESSION = 2  # verbatim harvested NL used as anchor utterances


class LicenseVerdict(str, Enum):
    """License verdict classification."""

    PERMISSIVE = "permissive"  # MIT / BSD-2 / BSD-3 / Apache-2.0
    COPYLEFT = "copyleft"  # (A)GPL / LGPL — HARD tier-0 cap
    NONE = "none"  # no license file at the pinned SHA, in any scanned dir
    AMBIGUOUS = "ambiguous"  # file present; 0 or >1 detection rules matched
    SHA_MISMATCH = "sha_mismatch"  # clone is not at pinned_sha -> UNRESOLVABLE
    NOT_CLONED = "not_cloned"  # clone_path absent -> UNRESOLVABLE


# Constants for license verification
#: C6: the measurement-validity axis, orthogonal to the license axis.
UNRESOLVABLE: Final[frozenset[LicenseVerdict]] = frozenset(
    {LicenseVerdict.SHA_MISMATCH, LicenseVerdict.NOT_CLONED}
)

#: C7: verdict -> tier lives in CODE. The data file supplies DETECTION only.
VERDICT_TIER: Final[Mapping[LicenseVerdict, int]] = {
    LicenseVerdict.PERMISSIVE: 2,
    LicenseVerdict.COPYLEFT: 0,
    LicenseVerdict.NONE: 0,
    LicenseVerdict.AMBIGUOUS: 0,
    LicenseVerdict.SHA_MISMATCH: 0,
    LicenseVerdict.NOT_CLONED: 0,
}


@dataclass(frozen=True)
class LicenseFinding:
    """A single license verification finding."""

    source_id: str
    pinned_sha: str
    observed_sha: str | None
    license_path: str | None  # clone-relative, e.g. "LICENSE" or "cookbook/LICENSE"
    license_sha256: str | None
    spdx_id: str | None
    verdict: LicenseVerdict
    license_tier: int  # VERDICT_TIER[verdict]  -- the pure license axis
    tier_ceiling: int  # the registry row's NON-license cap
    effective_tier: int  # min(license_tier, tier_ceiling)
    unresolvable: bool  # verdict in UNRESOLVABLE   (C6)
    shallow: bool | None  # .git/shallow present; None iff clone absent  (R2-B4d)
    reason: str  # human-readable, always non-empty


# License rule detection
class LicenseRulesError(cli.IngestError):
    """Raised when license rules are invalid or mismatched."""

    pass


def load_license_rules() -> list[dict[str, Any]]:
    """Load and validate the license rules from license_rules.json.

    Raises LicenseRulesError if the file's hash or embedded version disagrees.
    """
    rules_path = Path(__file__).parent / "data" / "license_rules.json"

    try:
        with open(rules_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise LicenseRulesError(f"Failed to load license rules: {e}") from e

    # Check embedded version
    embedded_version = data.get("license_rules_version")
    if embedded_version != versions.LICENSE_RULES_VERSION:
        raise LicenseRulesError(
            f"License rules version mismatch: embedded {embedded_version}, "
            f"expected {versions.LICENSE_RULES_VERSION}"
        )

    # Check file hash
    rules_bytes = rules_path.read_bytes()
    import hashlib

    computed_hash = hashlib.sha256(rules_bytes).hexdigest()
    if computed_hash != versions.LICENSE_RULES_SHA256:
        raise LicenseRulesError(
            f"License rules hash mismatch: computed {computed_hash}, "
            f"expected {versions.LICENSE_RULES_SHA256}"
        )

    return data.get("rules", [])


def _normalize_text(text: str) -> str:
    """Normalize text: collapse whitespace runs, casefold."""
    return " ".join(text.split()).casefold()


def _detect_license(text: str, rules: list[dict[str, Any]]) -> tuple[int, str | None]:
    """Detect license rules matching the normalized text.

    Returns:
        Tuple of (match_count, spdx_id_of_first_match).
        If exactly one rule matches, spdx_id is the rule's SPDX ID.
        If 0 or >1 rules match, spdx_id is None (AMBIGUOUS case).
    """
    normalized_text = _normalize_text(text)
    matched_spdx_ids = []

    for rule in rules:
        # Check all_of conditions
        all_of_ok = all(
            substring in normalized_text for substring in rule.get("all_of", [])
        )

        # Check none_of conditions
        none_of_ok = not any(
            substring in normalized_text for substring in rule.get("none_of", [])
        )

        if all_of_ok and none_of_ok:
            matched_spdx_ids.append(rule.get("spdx_id"))

    if len(matched_spdx_ids) == 1:
        return 1, matched_spdx_ids[0]
    else:
        return len(matched_spdx_ids), None


def _find_license_file(clone_path: Path, scan_dirs: Tuple[str, ...]) -> tuple[
    str | None, str | None, str | None, bool
]:
    """Find license file in clone at specified directories.

    Returns:
        Tuple of (license_path, license_text, license_sha256, has_ambiguous_differing_files).
        license_path is clone-relative (e.g., "LICENSE" or "cookbook/LICENSE").
        Returns (None, None, None, False) if no license file is found.
        Returns (None, None, None, True) if differing files are found in different dirs.
    """
    if not clone_path.exists():
        return None, None, None, False

    candidate_filenames = [
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "LICENCE",
        "LICENCE.md",
        "LICENCE.txt",
        "COPYING",
        "COPYING.md",
    ]

    # Candidate directories: root plus each scan_dir
    candidate_dirs = [clone_path]
    for scan_dir in scan_dirs:
        candidate_dirs.append(clone_path / scan_dir)

    found_files = {}  # path -> (text, sha256)

    for candidate_dir in candidate_dirs:
        if not candidate_dir.exists():
            continue

        for filename in candidate_filenames:
            file_path = candidate_dir / filename

            if file_path.exists() and file_path.is_file():
                try:
                    text = file_path.read_text(errors="replace")
                    file_bytes = file_path.read_bytes()
                    import hashlib

                    sha256_hex = hashlib.sha256(file_bytes).hexdigest()
                    found_files[file_path] = (text, sha256_hex)
                except (OSError, UnicodeDecodeError):
                    pass

    if not found_files:
        return None, None, None, False

    # Check for differing sha256 values across files
    sha256_values = [sha256 for _, sha256 in found_files.values()]
    if len(set(sha256_values)) > 1:
        # Multiple files with differing bytes — AMBIGUOUS
        return None, None, None, True

    # All files have the same bytes or there's only one — find root-most
    file_paths = list(found_files.keys())
    # Sort by depth (number of parents), ascending
    root_most = min(file_paths, key=lambda p: len(p.relative_to(clone_path).parts))
    text, sha256_hex = found_files[root_most]
    license_path = str(root_most.relative_to(clone_path))

    return license_path, text, sha256_hex, False


def _resolve_observed_sha(clone_path: Path) -> str | None:
    """Resolve the observed SHA from <clone>/.git/HEAD without subprocess.

    Returns:
        The 40-hex SHA if resolved, None otherwise.
    """
    if not clone_path.exists():
        return None

    git_head_path = clone_path / ".git" / "HEAD"
    if not git_head_path.exists():
        return None

    try:
        head_content = git_head_path.read_text(errors="replace").strip()
    except OSError:
        return None

    # If it's a 40-hex SHA, that's detached HEAD
    if len(head_content) == 40 and all(c in "0123456789abcdef" for c in head_content):
        return head_content

    # If it's `ref: refs/heads/<x>`, resolve the ref
    if head_content.startswith("ref: "):
        ref_name = head_content[5:].strip()
        ref_path = clone_path / ".git" / ref_name

        # Try direct path first
        if ref_path.exists():
            try:
                sha = ref_path.read_text(errors="replace").strip()
                if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
                    return sha
            except OSError:
                pass

        # Fall back to packed-refs
        packed_refs_path = clone_path / ".git" / "packed-refs"
        if packed_refs_path.exists():
            try:
                for line in packed_refs_path.read_text(errors="replace").split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == ref_name:
                        sha = parts[0]
                        if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
                            return sha
            except OSError:
                pass

    return None


def verify(row: SourceRow, rules: list[dict[str, Any]] | None = None) -> LicenseFinding:
    """Verify the license for a single source row.

    Args:
        row: A SourceRow to verify.
        rules: Loaded license rules (if None, loaded from data file).

    Returns:
        A LicenseFinding with all fields populated.
    """
    if rules is None:
        rules = load_license_rules()

    clone_path = Path(row.clone_path).expanduser()

    # Check if clone exists
    if not clone_path.exists():
        return LicenseFinding(
            source_id=row.source_id,
            pinned_sha=row.pinned_sha,
            observed_sha=None,
            license_path=None,
            license_sha256=None,
            spdx_id=None,
            verdict=LicenseVerdict.NOT_CLONED,
            license_tier=VERDICT_TIER[LicenseVerdict.NOT_CLONED],
            tier_ceiling=row.tier_ceiling,
            effective_tier=min(
                VERDICT_TIER[LicenseVerdict.NOT_CLONED], row.tier_ceiling
            ),
            unresolvable=True,
            shallow=None,
            reason="Clone not found at specified path",
        )

    # Resolve observed SHA
    observed_sha = _resolve_observed_sha(clone_path)

    # Check if shallow
    is_shallow = (clone_path / ".git" / "shallow").exists()
    shallow_value: bool | None = is_shallow if clone_path.exists() else None

    # Check SHA match
    if observed_sha != row.pinned_sha:
        return LicenseFinding(
            source_id=row.source_id,
            pinned_sha=row.pinned_sha,
            observed_sha=observed_sha,
            license_path=None,
            license_sha256=None,
            spdx_id=None,
            verdict=LicenseVerdict.SHA_MISMATCH,
            license_tier=VERDICT_TIER[LicenseVerdict.SHA_MISMATCH],
            tier_ceiling=row.tier_ceiling,
            effective_tier=min(
                VERDICT_TIER[LicenseVerdict.SHA_MISMATCH], row.tier_ceiling
            ),
            unresolvable=True,
            shallow=shallow_value,
            reason=f"Clone at {observed_sha[:8] if observed_sha else '?'}, "
            f"expected {row.pinned_sha[:8]}",
        )

    # Find license file
    license_path, license_text, license_sha256, has_ambiguous_files = _find_license_file(
        clone_path, row.license_scan_dirs
    )

    # Check for ambiguous case (multiple files with differing sha256)
    if has_ambiguous_files:
        return LicenseFinding(
            source_id=row.source_id,
            pinned_sha=row.pinned_sha,
            observed_sha=observed_sha,
            license_path=None,
            license_sha256=None,
            spdx_id=None,
            verdict=LicenseVerdict.AMBIGUOUS,
            license_tier=VERDICT_TIER[LicenseVerdict.AMBIGUOUS],
            tier_ceiling=row.tier_ceiling,
            effective_tier=min(VERDICT_TIER[LicenseVerdict.AMBIGUOUS], row.tier_ceiling),
            unresolvable=False,
            shallow=shallow_value,
            reason="Multiple license files found with differing content in different scan directories",
        )

    if license_path is None:
        # No license file found
        return LicenseFinding(
            source_id=row.source_id,
            pinned_sha=row.pinned_sha,
            observed_sha=observed_sha,
            license_path=None,
            license_sha256=None,
            spdx_id=None,
            verdict=LicenseVerdict.NONE,
            license_tier=VERDICT_TIER[LicenseVerdict.NONE],
            tier_ceiling=row.tier_ceiling,
            effective_tier=min(VERDICT_TIER[LicenseVerdict.NONE], row.tier_ceiling),
            unresolvable=False,
            shallow=shallow_value,
            reason="No license file found in any scanned directory",
        )

    # Detect license rules
    match_count, spdx_id = _detect_license(license_text, rules)

    if match_count != 1:
        # Ambiguous (0 or >1 matches)
        verdict = LicenseVerdict.AMBIGUOUS
    else:
        # Find the verdict for this SPDX ID
        verdict_str = None
        for rule in rules:
            if rule.get("spdx_id") == spdx_id:
                verdict_str = rule.get("verdict")
                break

        if verdict_str == "permissive":
            verdict = LicenseVerdict.PERMISSIVE
        elif verdict_str == "copyleft":
            verdict = LicenseVerdict.COPYLEFT
        else:
            verdict = LicenseVerdict.AMBIGUOUS

    license_tier = VERDICT_TIER[verdict]
    effective_tier = min(license_tier, row.tier_ceiling)

    return LicenseFinding(
        source_id=row.source_id,
        pinned_sha=row.pinned_sha,
        observed_sha=observed_sha,
        license_path=license_path,
        license_sha256=license_sha256,
        spdx_id=spdx_id,
        verdict=verdict,
        license_tier=license_tier,
        tier_ceiling=row.tier_ceiling,
        effective_tier=effective_tier,
        unresolvable=verdict in UNRESOLVABLE,
        shallow=shallow_value,
        reason=_finding_reason(verdict, spdx_id, license_path, match_count),
    )


def _finding_reason(
    verdict: LicenseVerdict, spdx_id: str | None, license_path: str | None, match_count: int
) -> str:
    """Generate a human-readable reason for the verdict."""
    if verdict == LicenseVerdict.PERMISSIVE:
        return f"Found {spdx_id} license ({license_path})"
    elif verdict == LicenseVerdict.COPYLEFT:
        return f"Found {spdx_id} license ({license_path})"
    elif verdict == LicenseVerdict.NONE:
        return "No license file found in any scanned directory"
    elif verdict == LicenseVerdict.AMBIGUOUS:
        if match_count == 0:
            return f"License file found ({license_path}) but no rules matched"
        else:
            return f"License file found ({license_path}) but {match_count} rules matched (ambiguous)"
    elif verdict == LicenseVerdict.SHA_MISMATCH:
        return "Clone at different commit than pinned_sha"
    elif verdict == LicenseVerdict.NOT_CLONED:
        return "Clone not found at specified path"
    else:
        return "Unknown verdict"


def verify_all(rules: list[dict[str, Any]] | None = None) -> Tuple[LicenseFinding, ...]:
    """Verify licenses for all rows in the registry.

    Args:
        rules: Loaded license rules (if None, loaded from data file).

    Returns:
        A tuple of LicenseFinding, sorted by source_id.
    """
    if rules is None:
        rules = load_license_rules()

    rows = load_registry()
    findings = []

    for row in rows:
        finding = verify(row, rules)
        findings.append(finding)

    # Sort by source_id
    findings.sort(key=lambda f: f.source_id)

    return tuple(findings)


def check_descend(findings: Sequence[LicenseFinding]) -> Tuple[int, int, int]:
    """Apply the D1 descend rule to determine if Increment 2 should proceed.

    Args:
        findings: Sequence of LicenseFinding.

    Returns:
        Tuple of (exit_code, tier1_plus_effective_count, unresolvable_count).
        exit_code: 0 (PROCEED), 3 (STOP), or 5 (INCONCLUSIVE).
    """
    tier1_plus_effective_count = 0
    unresolvable_count = 0

    for finding in findings:
        if finding.effective_tier >= 1:
            tier1_plus_effective_count += 1

        if finding.unresolvable:
            unresolvable_count += 1

    # D1 rule: PROCEED iff tier1_plus_effective_count >= 4;
    # INCONCLUSIVE (exit 5) iff below threshold but tier1_plus_effective_count + unresolvable_count >= 4;
    # else STOP (exit 3).

    if tier1_plus_effective_count >= 4:
        return cli.EXIT_OK, tier1_plus_effective_count, unresolvable_count
    elif tier1_plus_effective_count + unresolvable_count >= 4:
        return cli.EXIT_INCONCLUSIVE, tier1_plus_effective_count, unresolvable_count
    else:
        return cli.EXIT_STOP_LICENSING, tier1_plus_effective_count, unresolvable_count


def verify_clones(rows: Sequence[SourceRow] | None = None) -> Tuple[str, ...]:
    """Verify that all clones are present and at the pinned SHA.

    Args:
        rows: Sequence of SourceRow (if None, loaded from registry).

    Returns:
        A tuple of source_ids that failed verification (are unresolvable).
    """
    if rows is None:
        rows = load_registry()

    rules = load_license_rules()
    failing_source_ids = []

    for row in rows:
        finding = verify(row, rules)
        if finding.unresolvable:
            failing_source_ids.append(finding.source_id)

    return tuple(failing_source_ids)


def write_report(
    findings: Sequence[LicenseFinding], out_dir: Path | str
) -> Path:
    """Write the license report to JSON.

    Args:
        findings: Sequence of LicenseFinding.
        out_dir: Output directory.

    Returns:
        Path to the written report.
    """
    out_dir = Path(out_dir)

    # Count findings by verdict
    by_verdict = {}
    by_license_tier = {"0": 0, "1": 0, "2": 0}
    by_effective_tier = {"0": 0, "1": 0, "2": 0}

    tier1_plus_license_count = 0
    tier1_plus_effective_count = 0
    unresolvable_count = 0
    unresolvable_source_ids = []

    for finding in findings:
        # Count by verdict
        verdict_str = finding.verdict.value
        by_verdict[verdict_str] = by_verdict.get(verdict_str, 0) + 1

        # Count by tier
        by_license_tier[str(finding.license_tier)] += 1
        by_effective_tier[str(finding.effective_tier)] += 1

        # D1 counting
        if finding.license_tier >= 1:
            tier1_plus_license_count += 1

        if finding.effective_tier >= 1:
            tier1_plus_effective_count += 1

        if finding.unresolvable:
            unresolvable_count += 1
            unresolvable_source_ids.append(finding.source_id)

    # Load license rules for reporting
    rules = load_license_rules()
    rules_added_since_v1 = [
        r for r in rules if r.get("added_in_version", "1") != "1"
    ]

    # Apply descend rule
    descend_exit, _, _ = check_descend(findings)
    if descend_exit == cli.EXIT_OK:
        descend_decision = "PROCEED"
    elif descend_exit == cli.EXIT_STOP_LICENSING:
        descend_decision = "STOP"
    else:  # EXIT_INCONCLUSIVE
        descend_decision = "INCONCLUSIVE"

    # Build report
    report = {
        "registry_version": versions.REGISTRY_VERSION,
        "ingest_version": versions.INGEST_VERSION,
        "license_rules_version": versions.LICENSE_RULES_VERSION,
        "license_rules_sha256": versions.LICENSE_RULES_SHA256,
        "rules_added_since_v1": rules_added_since_v1,
        "counts": {
            "by_verdict": by_verdict,
            "by_license_tier": by_license_tier,
            "by_effective_tier": by_effective_tier,
        },
        "tier1_plus_license_count": tier1_plus_license_count,
        "tier1_plus_effective_count": tier1_plus_effective_count,
        "unresolvable_count": unresolvable_count,
        "descend_rule_D1": {
            "threshold": 4,
            "decision": descend_decision,
            "exit_code": descend_exit,
            "rule": "PROCEED iff tier1_plus_effective_count >= 4; INCONCLUSIVE (exit 5) iff below threshold but tier1_plus_effective_count + unresolvable_count >= 4; else STOP (exit 3).",
            "unresolvable_source_ids": unresolvable_source_ids,
        },
        "findings": sorted(
            [asdict(f) for f in findings], key=lambda f: f["source_id"]
        ),
    }

    # Convert enums to strings
    for finding in report["findings"]:
        if isinstance(finding["verdict"], LicenseVerdict):
            finding["verdict"] = finding["verdict"].value
        if isinstance(finding["shallow"], bool):
            finding["shallow"] = finding["shallow"]

    return write_artifact(out_dir, "license_report.json", json.dumps(report, indent=1, ensure_ascii=False))


def write_sources_manifest(
    findings: Sequence[LicenseFinding], out_dir: Path | str
) -> Path:
    """Write the SOURCES.md manifest.

    Args:
        findings: Sequence of LicenseFinding.
        out_dir: Output directory.

    Returns:
        Path to the written SOURCES.md.
    """
    out_dir = Path(out_dir)

    # Generate the banner and manifest
    lines = []
    lines.append("<!-- GENERATED from license report; do not edit manually -->")
    lines.append("")
    lines.append("# Sources Manifest")
    lines.append("")
    lines.append(
        "This document lists the 21 source repositories in the Coxswain corpus,"
    )
    lines.append("with admission status and license information.")
    lines.append("")
    lines.append("## Admitted Sources")
    lines.append("")

    # Filter admitted sources
    admitted_findings = [f for f in findings if f.license_tier >= 1]
    if admitted_findings:
        for finding in sorted(admitted_findings, key=lambda f: f.source_id):
            lines.append(
                f"- **{finding.source_id}** ({finding.verdict.value}): {finding.reason}"
            )
    else:
        lines.append("(None at tier >= 1)")

    lines.append("")
    lines.append("## Tier-0 / Unresolvable Sources")
    lines.append("")

    tier0_findings = [f for f in findings if f.license_tier == 0]
    if tier0_findings:
        for finding in sorted(tier0_findings, key=lambda f: f.source_id):
            lines.append(
                f"- **{finding.source_id}** ({finding.verdict.value}): {finding.reason}"
            )
    else:
        lines.append("(None)")

    lines.append("")

    content = "\n".join(lines)

    return write_artifact(out_dir, "SOURCES.md", content)


# CLI plumbing
def _make_parser() -> cli.IngestArgumentParser:
    parser = cli.IngestArgumentParser(
        prog="python -m ingest.licenses",
        description="License scanning and descend-rule verification for the ingest pipeline",
        out_required_for=("report",),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--report",
        action="store_true",
        help="Generate license_report.json and SOURCES.md",
    )
    group.add_argument(
        "--check-descend",
        action="store_true",
        help="Check the D1 descend rule and return appropriate exit code (0/3/5)",
    )
    group.add_argument(
        "--verify-clones",
        action="store_true",
        help="Verify that all clones are present and at pinned SHA",
    )

    parser.add_argument(
        "--require-all",
        action="store_true",
        help="With --verify-clones: require all clones; exit 1 if any are missing",
    )

    parser.add_argument(
        "--out",
        type=Path,
        help="Output directory for reports (required with --report)",
    )

    return parser


def _dispatch(args) -> int:
    """Handler passed to cli.run(); parse_args (and its UsageError mapping to
    64) is owned by cli.run, not this function."""
    if args.report:
        findings = verify_all()
        write_report(findings, args.out)
        write_sources_manifest(findings, args.out)
        print(
            f"Written license_report.json and SOURCES.md to {args.out}",
            file=sys.stderr,
        )
        return cli.EXIT_OK

    if args.check_descend:
        findings = verify_all()
        exit_code, effective_count, unresolvable_count = check_descend(findings)
        print(
            f"tier1_plus_effective_count: {effective_count}, "
            f"unresolvable_count: {unresolvable_count}, exit: {exit_code}",
            file=sys.stderr,
        )
        return exit_code

    # args.verify_clones (the group is required=True, so this is the only branch left)
    findings = verify_all()
    failing = [f for f in findings if f.unresolvable]
    if failing:
        failing_source_ids = [f.source_id for f in failing]
        print(
            f"Clones verification failed for {len(failing_source_ids)} sources: "
            f"{', '.join(failing_source_ids)}",
            file=sys.stderr,
        )
        if args.require_all:
            return cli.EXIT_MEASUREMENT_ERROR
        # §7.5: 5 if every failure is an absent clone (measurement could
        # not be taken); 1 if any PRESENT clone is at the wrong SHA (a
        # measurement that WAS taken and disagreed).
        if any(f.verdict == LicenseVerdict.SHA_MISMATCH for f in failing):
            return cli.EXIT_MEASUREMENT_ERROR
        return cli.EXIT_INCONCLUSIVE
    return cli.EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the licenses module."""
    return cli.run(_dispatch, _make_parser(), argv)


if __name__ == "__main__":
    raise SystemExit(main())

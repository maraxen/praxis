"""Generate `plr-sema/tests/fixtures/channel_effect_baseline.json` (spec 260929 §18.8(1), T59).

The fixture is the cross-pin baseline of `test_tip_effect_drift.py`: every contract
in an OLD-pin `derived_contracts.json` that carries a `channel_effect`, keyed
`"<Class.method>"`, plus the divergences the current table is *declared* to have
from it. It is read from the old-pin **artifact** (`--from PATH`, or
`--from-git-rev REV` through `git show`), never re-derived, so it is independent
evidence about the old pin rather than a re-statement of today's derivation.

Absence is a value (r1, M11). For a key `k`, `value(k)` is the table's
`channel_effect` or the string `"absent"`. The divergence set between a baseline
and the current table is

    {k in keys(baseline) | keys(current) : value_baseline(k) != value_current(k)}

and the generator REFUSES to write a fixture whose declared
`intended_divergences` are not exactly that set, each with the declared `new`
value. `--rebase` (overwriting an existing fixture) additionally refuses unless
`--intended-divergences` is given explicitly on the command line (an explicit,
empty `--intended-divergences` is a declaration of "none"), and prints every key
whose baseline value moved, so a rebase is a reviewed act, never a silent one.

Examples (from the repo root)::

    uv run python plr-sema/scripts/gen_channel_effect_baseline.py \\
        --from-git-rev 66fae143 --out plr-sema/tests/fixtures/channel_effect_baseline.json \\
        --intended-divergences LiquidHandler.load_state=widen \\
        --divergence-reason 'LiquidHandler.load_state=L1 (§18.4.4)'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("gen_channel_effect_baseline")

#: The value a key that carries no `channel_effect` has.
ABSENT = "absent"

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLR_SEMA_ROOT.parent
DEFAULT_TABLE = PLR_SEMA_ROOT / "data" / "derived_contracts.json"
DEFAULT_OUT = PLR_SEMA_ROOT / "tests" / "fixtures" / "channel_effect_baseline.json"
#: Repo-relative path of the table, as `git show <rev>:<path>` needs it.
TABLE_REPO_PATH = "plr-sema/data/derived_contracts.json"


def extract_channel_effects(table: dict[str, Any]) -> dict[str, str]:
    """`{"<Class.method>": value}` for every contract carrying a non-null
    `channel_effect` (the artifact only emits the key when it is not `None`)."""
    return {
        key: entry["channel_effect"]
        for key, entry in table["contracts"].items()
        if isinstance(entry, dict) and entry.get("channel_effect") is not None
    }


def divergences(baseline: dict[str, str], current: dict[str, str]) -> dict[str, tuple[str, str]]:
    """`{key: (baseline_value, current_value)}` over the KEY UNION, absence being
    the value `"absent"` (r1, M11): a vanished key and a new key both count."""
    out: dict[str, tuple[str, str]] = {}
    for key in sorted(set(baseline) | set(current)):
        old, new = baseline.get(key, ABSENT), current.get(key, ABSENT)
        if old != new:
            out[key] = (old, new)
    return out


def _load_json_path(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    return json.loads(raw), f"file:{path.name}@sha256:{hashlib.sha256(raw).hexdigest()}"


def _load_git_rev(rev: str) -> tuple[dict[str, Any], str]:
    sha = subprocess.run(
        ["git", "rev-parse", "--verify", f"{rev}^{{commit}}"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    raw = subprocess.run(
        ["git", "show", f"{sha}:{TABLE_REPO_PATH}"], cwd=REPO_ROOT, capture_output=True, check=True
    ).stdout
    return json.loads(raw), sha


def parse_intended(specs: list[str], reasons: list[str]) -> dict[str, dict[str, str]]:
    """`KEY=NEW` specs (+ `KEY=TEXT` reasons) -> `{key: {"new": NEW, "reason": TEXT}}`; `old` is filled from the
    baseline by the caller. `NEW` is a `channel_effect` value or `absent` (a vanished key)."""
    reason_by_key: dict[str, str] = {}
    for r in reasons:
        key, sep, text = r.partition("=")
        if not sep or not key or not text:
            raise SystemExit(f"--divergence-reason must be KEY=TEXT, got {r!r}")
        reason_by_key[key] = text
    intended: dict[str, dict[str, str]] = {}
    for spec in specs:
        key, sep, new = spec.partition("=")
        if not sep or not key or not new:
            raise SystemExit(f"--intended-divergences entries must be KEY=NEW, got {spec!r}")
        if key in intended:
            raise SystemExit(f"--intended-divergences names {key!r} twice")
        intended[key] = {"new": new, "reason": reason_by_key.pop(key, "unreviewed")}
    if reason_by_key:
        raise SystemExit(f"--divergence-reason names keys that are not intended divergences: {sorted(reason_by_key)}")
    return intended


def build_fixture(
    baseline_table: dict[str, Any],
    source_rev: str,
    current_table: dict[str, Any],
    intended: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], list[str]]:
    """`(fixture, problems)`. `problems` is empty iff `intended` is EXACTLY the
    divergence set between the baseline and the current table, each `new`
    matching the current value."""
    baseline = extract_channel_effects(baseline_table)
    current = extract_channel_effects(current_table)
    actual = divergences(baseline, current)
    problems: list[str] = []
    for key, (old, new) in actual.items():
        if key not in intended:
            problems.append(f"UNDECLARED divergence {key}: {old} -> {new}")
        elif intended[key]["new"] != new:
            problems.append(f"{key}: declared new={intended[key]['new']!r} but the current table has {new!r}")
    for key in intended:
        if key not in actual:
            problems.append(f"declared divergence {key} does not diverge (baseline == current == {baseline.get(key, ABSENT)!r})")
    stamp = baseline_table.get("stamp", {})
    fixture = {
        "source_rev": source_rev,
        "plr_pin": {
            "hash": stamp.get("plr", {}).get("hash"),
            "pylabrobot_version": stamp.get("pylabrobot_version"),
        },
        "channel_effects": dict(sorted(baseline.items())),
        "intended_divergences": {
            key: {"old": baseline.get(key, ABSENT), "new": spec["new"], "reason": spec["reason"]}
            for key, spec in sorted(intended.items())
        },
    }
    return fixture, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gen_channel_effect_baseline", description=__doc__.split("\n\n")[0])
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--from", dest="from_path", type=Path, help="baseline table: a derived_contracts.json path")
    src.add_argument("--from-git-rev", help="baseline table: `git show REV:plr-sema/data/derived_contracts.json`")
    parser.add_argument("--current", type=Path, default=DEFAULT_TABLE, help="the table the divergences are checked against")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--intended-divergences", nargs="*", default=None, metavar="KEY=NEW",
        help="declared baseline->current divergences; required by --rebase (an explicit empty list means none)",
    )
    parser.add_argument("--divergence-reason", action="append", default=[], metavar="KEY=TEXT")
    parser.add_argument("--rebase", action="store_true", help="overwrite an existing fixture (a reviewed act)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    if args.rebase and args.intended_divergences is None:
        log.error("--rebase refuses without an explicit --intended-divergences (an empty list declares none)")
        return 2
    if args.out.exists() and not args.rebase:
        log.error("%s exists; overwriting it is a --rebase (which needs an explicit --intended-divergences)", args.out)
        return 2

    try:
        if args.from_path is not None:
            baseline_table, source_rev = _load_json_path(args.from_path)
        else:
            baseline_table, source_rev = _load_git_rev(args.from_git_rev)
    except (subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        log.error("cannot read the baseline table: %s", exc)
        return 2
    current_table = json.loads(args.current.read_text(encoding="utf-8"))

    intended = parse_intended(args.intended_divergences or [], args.divergence_reason)
    fixture, problems = build_fixture(baseline_table, source_rev, current_table, intended)

    if args.rebase and args.out.exists():
        previous = json.loads(args.out.read_text(encoding="utf-8")).get("channel_effects", {})
        moved = divergences(previous, fixture["channel_effects"])
        log.info("rebase: %d baseline key(s) moved", len(moved))
        for key, (old, new) in moved.items():
            log.info("  MOVED %s: %s -> %s", key, old, new)

    for problem in problems:
        log.error("REFUSING: %s", problem)
    if problems:
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info(
        "wrote %s: %d channel_effect key(s) from %s (plr %s), %d intended divergence(s)",
        args.out, len(fixture["channel_effects"]), source_rev, (fixture["plr_pin"]["hash"] or "?")[:9],
        len(fixture["intended_divergences"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""P2.4 smoke runner: mine -> pair -> validate-shape, end to end.

Processes an explicit subset (>=5 notebooks + >=2 protocols per AC-2.4 smoke
gate) or, with ``--full``, every minable source -- the full-scale run is a
later gate. Writes three artifacts under ``training/overlay_gen/out/``:

- ``mined_calls_<tag>.json``   mining manifest: counts by source, verb
                               tallies, exclusions w/ reasons, skips.
- ``overlay_<tag>.jsonl``      candidate rows (instruction <-> call pairs).
- ``smoke_report_<tag>.json``  pair-builder summary + environment versions.

Usage (from anywhere; paths are resolved off this file's location)::

    python -m overlay_gen.run_smoke            # smoke subset
    python -m overlay_gen.run_smoke --full     # later full-scale gate
    python -m overlay_gen.run_smoke --full --backend gemini --batch-size 20  # full-scale, batched via agy
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):  # direct-script convenience
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from overlay_gen.cache import TeacherCache
from overlay_gen.miner import (
    NOTEBOOK_ROOT,
    PROTOCOL_DIR,
    REPO_ROOT,
    mine_notebooks,
    mine_protocols,
)
from overlay_gen.pair_builder import (
    PROMPT_VERSION,
    GeminiTeacherClient,
    VllmTeacherClient,
    build_pairs,
)

OUT_DIR = Path(__file__).resolve().parent / "out"
CACHE_DIR = Path(__file__).resolve().parent / "cache"

#: Smoke subset: 6 minable notebooks (>=5 required) spanning tip lifecycle,
#: volume ops, expert-kwarg dropping, and non-surface exclusion paths, plus
#: 2 protocols (>=2 required).
SMOKE_NOTEBOOKS: tuple[str, ...] = (
    "external/pylabrobot/docs/user_guide/00_liquid-handling/hamilton-star/basic.ipynb",
    "external/pylabrobot/docs/user_guide/00_liquid-handling/opentrons/ot2/hello-world.ipynb",
    "external/pylabrobot/docs/user_guide/00_liquid-handling/opentrons/ot2/ot2-simulator.ipynb",
    "external/pylabrobot/docs/user_guide/00_liquid-handling/mixing.ipynb",
    "external/pylabrobot/docs/user_guide/00_liquid-handling/moving-channels-around.ipynb",
    "external/pylabrobot/docs/user_guide/00_liquid-handling/tutorial_tip_inventory_consolidation.ipynb",
)
SMOKE_PROTOCOLS: tuple[str, ...] = (
    "praxis/protocol/protocols/simple_transfer.py",
    "praxis/protocol/protocols/serial_dilution.py",
)


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def mine_subset(notebooks: list[str], protocols: list[str]) -> tuple[dict, dict, dict]:
    """Mine only the named sources (explicit-path staging discipline)."""
    nb_all = mine_notebooks(NOTEBOOK_ROOT)
    proto_all = mine_protocols(PROTOCOL_DIR)
    picked = {n: nb_all[n] for n in notebooks if n in nb_all}
    picked.update({p: proto_all[p] for p in protocols if p in proto_all})
    return nb_all, proto_all, picked


def summarize_mining(reports: dict) -> dict:
    by_source: dict[str, dict] = {}
    verb_counts: dict[str, int] = {}
    exclusions_by_reason: dict[str, int] = {}
    total_kept = 0
    for source, stats in sorted(reports.items()):
        verbs: dict[str, int] = {}
        for call in stats.kept_calls:
            verbs[call.name] = verbs.get(call.name, 0) + 1
            verb_counts[call.name] = verb_counts.get(call.name, 0) + 1
        reasons: dict[str, int] = {}
        for exc in stats.exclusions:
            key = f"{exc.verb}: {exc.reason}"
            reasons[key] = reasons.get(key, 0) + 1
            exclusions_by_reason[key] = exclusions_by_reason.get(key, 0) + 1
        by_source[source] = {
            "units": stats.cells_or_functions,
            "kept_calls": len(stats.kept_calls),
            "verbs": verbs,
            "excluded": len(stats.exclusions),
            "exclusion_detail": reasons,
            "unextractable": stats.unextractable,
            "parse_errors": stats.parse_errors,
            "skip_reason": stats.skip_reason,
        }
        total_kept += len(stats.kept_calls)
    return {
        "total_kept": total_kept,
        "by_source": by_source,
        "verbs_total": dict(sorted(verb_counts.items())),
        "exclusions_total": dict(sorted(exclusions_by_reason.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="process ALL sources")
    parser.add_argument(
        "--variants", type=int, default=3, help="teacher variants per unique canonical"
    )
    parser.add_argument("--offline", action="store_true", help="cache-only teacher access")
    parser.add_argument("--backend", choices=["titanix", "gemini"], default="titanix")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="canonicals grouped per teacher call (batch-capable backends only, e.g. gemini); ignored otherwise",
    )
    args = parser.parse_args(argv)

    tag = "full" if args.full else "smoke"
    if args.full:
        reports = {**mine_notebooks(NOTEBOOK_ROOT), **mine_protocols(PROTOCOL_DIR)}
        mined = reports
        subset_env = None
    else:
        _, _, mined = mine_subset(list(SMOKE_NOTEBOOKS), list(SMOKE_PROTOCOLS))
        subset_env = {"notebooks": list(SMOKE_NOTEBOOKS), "protocols": list(SMOKE_PROTOCOLS)}

    manifest = {
        "tag": tag,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subset": subset_env,
        "mining": summarize_mining(mined),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"mined_calls_{tag}.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8"
    )

    calls = [c for stats in mined.values() for c in stats.kept_calls]
    teacher = GeminiTeacherClient() if args.backend == "gemini" else VllmTeacherClient()
    rows, summary = build_pairs(
        calls,
        teacher=teacher,
        cache_dir=CACHE_DIR,
        out_path=OUT_DIR / f"overlay_{tag}.jsonl",
        n_variants=args.variants,
        generator_version=_git_sha(),
        batch_size=args.batch_size,
    )

    report = {
        "tag": tag,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generator_git_sha": _git_sha(),
        "prompt_version": PROMPT_VERSION,
        "teacher_requested_model": teacher.model_version,
        "mining_summary": manifest["mining"],
        "pair_summary": summary,
        "sample_rows": [rows[i].__str__() for i in range(min(3, len(rows)))],
        "samples": [
            {"instruction": r["instruction"], "call": r["call"]} for r in rows[:5]
        ],
    }
    (OUT_DIR / f"smoke_report_{tag}.json").write_text(
        json.dumps(report, indent=1, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps({k: summary[k] for k in sorted(summary) if k != "warnings"}, indent=1))
    print(f"mined kept calls: {manifest['mining']['total_kept']}")
    print(f"artifacts under {OUT_DIR} (tag={tag})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

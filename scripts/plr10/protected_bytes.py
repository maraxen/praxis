"""sha256 manifest of the byte-protected training data (PLR 1.0 phase 2, #5664; plan §5 PR-0 item 3, §7).

``record`` writes one JSON manifest: every file under the protected paths, with its sha256 and size.
It refuses if a protected path holds a file that is not tracked by git, or a tracked file with
uncommitted changes, so a manifest always describes a commit (recorded as ``git_head``).

``compare`` diffs two manifests and exits 1 if any path was added, removed or changed. This is the
comparator PR-5's pre-registered byte gate runs (with its own negative control); PR-0 only records.

    uv run --no-sync python scripts/plr10/protected_bytes.py record --out scripts/plr10/baselines/protected_bytes_pr0.json
    uv run --no-sync python scripts/plr10/protected_bytes.py compare A.json B.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
#: Plan §7: corpora/sidecars/probes/manifest, golden set, overlay outputs, frozen overlay rows, eval pin.
PROTECTED = [
    "training/assemble/out",
    "training/golden",
    "training/overlay_gen/out",
    "training/overlay_gen/frozen",
    "training/assemble/pin.py",
]


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(out: Path) -> int:
    on_disk = sorted(
        p.relative_to(REPO).as_posix()
        for spec in PROTECTED
        for p in ([REPO / spec] if (REPO / spec).is_file() else (REPO / spec).rglob("*"))
        if p.is_file()
    )
    tracked = set(_git("ls-files", "--", *PROTECTED).split())
    untracked = [p for p in on_disk if p not in tracked]
    missing = sorted(tracked - set(on_disk))
    modified = [ln for ln in _git("status", "--porcelain", "--", *PROTECTED).splitlines() if ln.strip()]
    if untracked or missing or modified:
        print(json.dumps({"refused": True, "untracked": untracked, "missing": missing, "modified": modified}, indent=2))
        return 2
    files = {p: {"sha256": _sha256(REPO / p), "bytes": (REPO / p).stat().st_size} for p in on_disk}
    manifest = {"git_head": _git("rev-parse", "HEAD").strip(), "protected": PROTECTED, "n_files": len(files), "files": files}
    out = out if out.is_absolute() else REPO / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"recorded {len(files)} protected files at {manifest['git_head'][:10]} -> {out}")
    return 0


def compare(a: Path, b: Path) -> int:
    fa = json.loads(a.read_text(encoding="utf-8"))["files"]
    fb = json.loads(b.read_text(encoding="utf-8"))["files"]
    diff = {
        "added": sorted(set(fb) - set(fa)),
        "removed": sorted(set(fa) - set(fb)),
        "changed": sorted(p for p in set(fa) & set(fb) if fa[p]["sha256"] != fb[p]["sha256"]),
    }
    diff["identical"] = not any(diff.values())
    print(json.dumps(diff, indent=2))
    return 0 if diff["identical"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("compare")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    args = ap.parse_args(argv)
    return record(args.out) if args.cmd == "record" else compare(args.a, args.b)


if __name__ == "__main__":
    sys.exit(main())

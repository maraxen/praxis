#!/usr/bin/env python3
"""Vendor the pin's PyLabRobot Visualizer3D ``static/`` tree into the REPL overlay.

Spec ``260929_notebook-display-epic.md`` D11 (Revision 10) and AC-30: the pin ships
``pylabrobot/visualizer3D``, and the REPL's PLR wheel already carries its Python, so
**only** ``pylabrobot/visualizer3D/static/`` is vendored -- the page must be HTTP-served
from the dist, and the wheel's copy sits inside the kernel's site-packages, which nothing
serves. No PLR Python is copied (``*.py`` and ``__pycache__`` are never vendored) and no
``.glb`` model file is (a source holding one fails loudly).

Output is ``web-repl/overlay/assets/visualizer3d/``. Its sibling
``overlay/assets/visualizer3d-augmentations/`` is hand-authored and is NEVER written by
this script; the two ``<script>`` tags injected into ``index.html`` carry a relative
``../visualizer3d-augmentations/`` path that resolves only while the directories remain
siblings (same constraint as ``vendor_visualizer.py`` and ``visualizer-augmentations/``).

Every file except ``index.html`` is copied **byte-identically**. ``index.html`` is
transformed in exactly three ways:

1. ``{{ ... }}`` server-template placeholders are stripped by pattern (the same approach as
   ``vendor_visualizer.py``'s ``_PLACEHOLDER_RE``; never a name list or a count).
2. A classic ``<script src="../visualizer3d-augmentations/socket.js"></script>`` is inserted
   immediately before the first ``<script`` in the document, so it runs before any module.
   That first script must be the page's classic ``./vendor/gif.js`` tag.
3. ``<script type="module" src="../visualizer3d-augmentations/embed.js"></script>`` is
   inserted before ``</body>``.

Each anchor must match exactly once, or vendoring fails with +/-10 lines of context.
``VENDOR_MANIFEST.json`` records the PLR source commit and every file's sha256 (and, for
``index.html``, the sha256 of the untransformed source). ``--check`` is read-only: it fails,
naming the paths, on any byte difference, missing or extra file, and on a recorded commit
that differs from the source's. A pin bump of any kind therefore fails ``--check`` until
the tree is explicitly re-vendored.

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

# The 2D vendoring script owns the anchor-diagnosis helpers; reuse rather than fork them.
from vendor_visualizer import VendorError, _format_context_blocks, _locate_context

logger = logging.getLogger("vendor_visualizer3d")

GENERATOR = "vendor_visualizer3d.py"
GENERATOR_VERSION = "1.0.0"
MANIFEST_NAME = "VENDOR_MANIFEST.json"

# Where `static/` sits inside a PLR checkout.
STATIC_REL = Path("pylabrobot") / "visualizer3D" / "static"

_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")

# The relative paths are load-bearing: see the module docstring.
_SOCKET_TAG = '<script src="../visualizer3d-augmentations/socket.js"></script>'
_EMBED_TAG = '<script type="module" src="../visualizer3d-augmentations/embed.js"></script>'
# The document's first `<script` at the pin (index.html:319); the socket tag goes right before it.
_FIRST_SCRIPT = '<script src="./vendor/gif.js"></script>'

_EXCLUDED_SUFFIXES = {".py", ".pyc"}


# --- index.html transform --------------------------------------------------------


def strip_placeholders(html: str) -> str:
    names = _PLACEHOLDER_RE.findall(html)
    html, n = _PLACEHOLDER_RE.subn("", html)
    logger.info("index.html: stripped %d server-template placeholder(s) by pattern: %s", n, names)
    return html


def inject_socket_tag(html: str) -> str:
    first = html.find("<script")
    n_anchor = html.count(_FIRST_SCRIPT)
    if first == -1 or n_anchor != 1 or not html.startswith(_FIRST_SCRIPT, first):
        where = f"first <script at line {html.count(chr(10), 0, first) + 1}" if first != -1 else "no <script at all"
        raise VendorError(
            f"expected the classic {_FIRST_SCRIPT!r} tag exactly once and as the first <script in the "
            f"document, to insert the socket shim before it; found it {n_anchor} time(s); {where}. "
            f"Context (+/-10 lines) around each occurrence of the anchor:\n\n"
            f"{_format_context_blocks(_locate_context(html, _FIRST_SCRIPT))}"
        )
    return f"{html[:first]}{_SOCKET_TAG}\n{html[first:]}"


def inject_embed_tag(html: str) -> str:
    n = html.count("</body>")
    if n != 1:
        raise VendorError(
            f"expected exactly one </body> tag to insert the embed module before, found {n}. "
            f"Context:\n\n{_format_context_blocks(_locate_context(html, '</body>'))}"
        )
    return html.replace("</body>", f"{_EMBED_TAG}\n</body>")


def transform_index(source: str) -> str:
    html = strip_placeholders(source)
    html = inject_socket_tag(html)
    html = inject_embed_tag(html)
    leftover = re.findall(r"https://[^\"' ]+", html)
    if leftover:
        raise VendorError(f"index.html still references external URL(s) after the transform: {leftover}")
    return html


# --- the tree ---------------------------------------------------------------------


def resolve_static(src: Path) -> Path:
    """``src`` is a PLR checkout (the default, ``external/pylabrobot``) or the ``static/`` dir."""
    if (src / STATIC_REL).is_dir():
        return src / STATIC_REL
    if (src / "index.html").is_file():
        return src
    raise VendorError(
        f"--src {src} holds neither {STATIC_REL.as_posix()}/ nor an index.html. "
        "If this is external/pylabrobot, the submodule is not initialised: "
        "run `git submodule update --init external/pylabrobot`."
    )


def plan_tree(static: Path) -> tuple[dict[str, bytes], str]:
    """The exact bytes the vendored tree must hold, by posix relative path (manifest excluded),
    and the sha256 of the untransformed source ``index.html``."""
    plan: dict[str, bytes] = {}
    for p in sorted(static.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(static)
        if "__pycache__" in rel.parts or p.suffix in _EXCLUDED_SUFFIXES:
            continue
        if p.suffix.lower() == ".glb":
            raise VendorError(f"{rel.as_posix()}: a .glb model file is in the source; none is vendored (D11).")
        plan[rel.as_posix()] = p.read_bytes()
    if "index.html" not in plan:
        raise VendorError(f"{static} has no index.html")
    for rel, data in plan.items():
        if b"cdn.jsdelivr.net" in data:
            raise VendorError(f"{rel}: references cdn.jsdelivr.net; the vendored tree must be CDN-free.")
    source_index = plan["index.html"]
    plan["index.html"] = transform_index(source_index.decode()).encode()
    logger.info("planned %d file(s) from %s", len(plan), static)
    return plan, hashlib.sha256(source_index).hexdigest()


def manifest_entries(plan: dict[str, bytes], source_index_sha256: str) -> list[dict]:
    entries = []
    for rel in sorted(plan):
        entry = {"path": rel, "sha256": hashlib.sha256(plan[rel]).hexdigest(), "bytes": len(plan[rel])}
        if rel == "index.html":
            entry["source_sha256"] = source_index_sha256
        entries.append(entry)
    return entries


# --- the source commit ------------------------------------------------------------


def resolve_commit(static: Path, explicit: str | None) -> str:
    """The PLR commit: ``--commit``, else ``git rev-parse HEAD`` in the checkout that owns ``static``.

    The checkout is only ever the directory the standard layout puts it in, never an enclosing
    repository: an uninitialised submodule dir sits inside the parent repo, whose HEAD is not
    the pin.
    """
    if explicit is not None:
        commit = explicit
    else:
        root = static.resolve().parents[2] if len(static.resolve().parents) > 2 else None
        if root is None or static.resolve() != (root / STATIC_REL).resolve() or not (root / ".git").exists():
            raise VendorError(
                f"cannot resolve the PLR commit: {static} is not inside a PLR checkout "
                f"(<root>/{STATIC_REL.as_posix()} with <root>/.git). Pass --commit <40-hex sha>."
            )
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise VendorError(f"git rev-parse HEAD failed in {root}: {exc}") from exc
        commit = result.stdout.strip()
    if not _COMMIT_RE.fullmatch(commit):
        raise VendorError(f"source commit {commit!r} is not a 40-character lowercase hex sha")
    return commit


# --- vendor and check ---------------------------------------------------------------


def vendor(src: Path, out: Path, commit: str | None) -> dict:
    static = resolve_static(src)
    sha = resolve_commit(static, commit)
    plan, source_index_sha256 = plan_tree(static)
    entries = manifest_entries(plan, source_index_sha256)

    if out.exists():
        shutil.rmtree(out)
    for rel, data in plan.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    manifest = {
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "source_sha": sha,
        "files": entries,
    }
    (out / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n")
    logger.info("wrote %s (%d file(s), source_sha=%s)", out / MANIFEST_NAME, len(entries), sha)
    return manifest


def check(src: Path, out: Path, commit: str | None) -> list[str]:
    """Return every problem found (empty means the committed tree equals the source). Never writes."""
    static = resolve_static(src)
    sha = resolve_commit(static, commit)
    plan, source_index_sha256 = plan_tree(static)
    expected = {e["path"]: e for e in manifest_entries(plan, source_index_sha256)}
    problems: list[str] = []

    on_disk = {
        p.relative_to(out).as_posix(): p for p in sorted(out.rglob("*")) if p.is_file() and p.name != MANIFEST_NAME
    } if out.is_dir() else {}
    for rel in sorted(set(plan) - set(on_disk)):
        problems.append(f"MISSING  {rel}: in the source, absent from {out}")
    for rel in sorted(set(on_disk) - set(plan)):
        problems.append(f"EXTRA    {rel}: in {out}, absent from the source")
    for rel in sorted(set(plan) & set(on_disk)):
        if on_disk[rel].read_bytes() != plan[rel]:
            problems.append(
                f"DIFFERS  {rel}: sha256 {hashlib.sha256(on_disk[rel].read_bytes()).hexdigest()} "
                f"!= expected {expected[rel]['sha256']}"
            )

    manifest_path = out / MANIFEST_NAME
    if not manifest_path.is_file():
        problems.append(f"MANIFEST {MANIFEST_NAME}: missing from {out}")
        return problems
    try:
        manifest = json.loads(manifest_path.read_text())
        recorded = {e["path"]: e for e in manifest["files"]}
        recorded_sha = manifest["source_sha"]
    except (ValueError, KeyError, TypeError) as exc:
        problems.append(f"MANIFEST {MANIFEST_NAME}: unreadable ({exc!r})")
        return problems
    if recorded_sha != sha:
        problems.append(f"COMMIT   recorded source_sha {recorded_sha} != source commit {sha}")
    for rel in sorted(set(expected) | set(recorded)):
        if recorded.get(rel) != expected.get(rel):
            problems.append(f"MANIFEST {rel}: recorded {recorded.get(rel)} != expected {expected.get(rel)}")
    return problems


# --- CLI --------------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
DEFAULT_REPO_ROOT = _THIS_FILE.parents[2]
DEFAULT_SRC = DEFAULT_REPO_ROOT / "external" / "pylabrobot"
DEFAULT_OUT = _THIS_FILE.parents[1] / "overlay" / "assets" / "visualizer3d"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--src",
        "--source",
        dest="src",
        type=Path,
        default=DEFAULT_SRC,
        help="PLR checkout (holding pylabrobot/visualizer3D/static/) or that static/ dir itself, "
        f"read-only (default: {DEFAULT_SRC}, the submodule at the pin).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Vendored tree; recreated from scratch on every run (default: {DEFAULT_OUT}).",
    )
    parser.add_argument(
        "--commit",
        default=None,
        help="PLR commit to record and compare (40-hex). Default: `git rev-parse HEAD` in the "
        "checkout that owns --src. Required when --src is not inside a PLR git checkout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only: exit nonzero, naming paths, if the committed tree's bytes or recorded "
        "commit differ from the source's.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.check:
            problems = check(args.src.resolve(), args.out.resolve(), args.commit)
            if problems:
                logger.error(
                    "%d problem(s); the vendored tree differs from the source:\n%s",
                    len(problems),
                    "\n".join(problems),
                )
                return 1
            logger.info("check ok: %s equals the source at the recorded commit", args.out)
            return 0
        vendor(args.src.resolve(), args.out.resolve(), args.commit)
    except VendorError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("vendored visualizer3d tree built at %s", args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Vendor a socket-free, CDN-free copy of the PyLabRobot visualizer.

Promotion of the spike generator at
``/tmp/claude-1000/praxis-spikes/s4/build_harness.py`` (verified this
session against the repo's current pin: 4 vis.js anchors each matched
exactly once, 5 CDN substitutions, ``index.html`` remaining external URLs
``[]``, ``lib.js`` sha256 identical src<->out). The four ``VIS_EDITS``, the
``BRIDGE`` script, and the ``CDN_STRIP`` patterns below are ported
byte-for-byte from that verified generator -- **do not re-derive them**;
re-deriving is how a working transformation gets silently broken.

Per ADR ``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 4.2 ("Visualizer spec -- eight changes, not one") this script lives at
``web-repl/scripts/vendor_visualizer.py`` and its default output is
``web-repl/overlay/assets/visualizer/`` -- ONLY ``overlay/`` reaches
``dist/`` (``build_repl.py --out web-repl/dist``); an earlier design placed
the output at the tree root and the visualizer never shipped. Its sibling
``web-repl/overlay/assets/visualizer-augmentations/`` is hand-authored and
is NEVER written by this script -- the generated ``index.html`` carries a
relative ``<script src="../visualizer-augmentations/index.js">`` that only
resolves while the two directories remain siblings under ``overlay/assets/``.

See also: .praxia/docs/specs/260817_spec-visualizer-transport-shim.md
(R1-R8, R23; T1.1) for the full requirement/verification text this script
satisfies, and Sec 2.3 (D2, the exactly-one-match drift detector) for why
anchor mismatches must fail loudly with enough context to be diagnosable
without re-running by hand.

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

logger = logging.getLogger("vendor_visualizer")

GENERATOR_VERSION = "1.0.0"


class VendorError(RuntimeError):
    """Raised for any condition that must abort vendoring loudly."""


# --- ported verbatim from the verified spike generator (build_harness.py) --
# DO NOT re-derive: the plan and ADR both call out that re-deriving these is
# how a working transformation gets silently broken. See spec T1.1.

VIS_EDITS = [
    (
        "ack-send (handleEvent tail)",
        "  webSocket.send(JSON.stringify(ret));\n}",
        "  // [HARNESS] socket ack removed; return the ack object to the caller instead.\n"
        "  window.__lastAck = ret;\n"
        "  return ret;\n}",
    ),
    (
        "openSocket body",
        'let wsPortInput = document.querySelector(`input[id="ws_port"]`);\n'
        "  let wsHost = window.location.hostname;\n"
        "  let wsPort = wsPortInput.value;\n"
        "  webSocket = new WebSocket(`ws://${wsHost}:${wsPort}/`);",
        "  // [HARNESS] no websocket is opened at all.\n"
        '  updateStatusLabel("loaded");\n'
        "  socketLoading = false;\n"
        "  return;\n"
        "  /* eslint-disable */ if (false) {\n"
        "  webSocket = new WebSocket(`ws://x/`);",
    ),
    (
        "openSocket tail close of dead block",
        "    handleEvent(data.id, data.event, data.data);\n  });\n}",
        "    handleEvent(data.id, data.event, data.data);\n  });\n  } /* end dead block */\n}",
    ),
    (
        "heartbeat",
        "function heartbeat() {\n  if (!webSocket) return;",
        "function heartbeat() {\n  return; // [HARNESS] no socket, no heartbeat\n  if (!webSocket) return;",
    ),
]

BRIDGE = """

// ===========================================================================
// [HARNESS] Browser-native bridge: feed events straight into handleEvent with
// no websocket and no Python process.
// ===========================================================================
window.__evtCounter = 0;
window.receiveFromPython = async function (event, data) {
  if (typeof data === "string") {
    data = JSON.parse(data, (key, value) => {
      if (value == "Infinity") return Infinity;
      if (value == "-Infinity") return -Infinity;
      return value;
    });
  }
  window.__evtCounter += 1;
  const id = "py-" + window.__evtCounter;
  return await handleEvent(id, event, data);
};
"""

CDN_STRIP = [
    (re.compile(r"\s*<link[^>]*cdn\.jsdelivr\.net[^>]*>", re.S), ""),
    (
        re.compile(r'<script src="https://unpkg\.com/konva@8/konva\.min\.js"></script>'),
        '<script src="./konva.min.js"></script>',
    ),
    (re.compile(r'\s*<script src="https://cdnjs\.cloudflare\.com[^"]*"></script>'), ""),
]

# --- net-new beyond the spike (P6.1 scope) -----------------------------------

# Both `href="/favicon.png"` (icon <link>) and `src="/favicon.png"` (header
# <img>) must become relative -- absolute paths break subpath deploys (the
# site may be served under `/praxis/`). Exactly 2 sites at both the current
# pin (d9651e2) and the target pin (0.2.2) -- but that count is what we
# ASSERT, not assume; see fix_favicon_paths().
_FAVICON_RE = re.compile(r'(href|src)="/favicon\.png"')

# Server-side template placeholders (`{{ source_filename }}`, `{{ fs_port }}`,
# `{{ ws_port }}`, `{{ liquid_color }}`, ...). Stripped BY PATTERN, not by a
# hardcoded count or name list: there are 3 placeholders at d9651e2 and 4 at
# 0.2.2 (adds `{{ liquid_color }}`) -- a count-based strip silently
# under-strips at whichever pin introduced the extra one. R6.
_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")

# The single module tag that wires the hand-authored, never-regenerated
# augmentations directory into the generated page. The relative path is
# load-bearing: it only resolves while visualizer/ and
# visualizer-augmentations/ remain siblings under overlay/assets/ (ADR Sec
# 2.1/4.2; spec R18). Do not shorten or rename either directory.
_AUGMENTATION_TAG = '<script type="module" src="../visualizer-augmentations/index.js"></script>'

# The SECOND module tag (W4, deviation D-C / FR-12): the Coxswain highlight
# subscriber, injected ONLY into the STAGED dist copy of visualizer/index.html
# by build_repl.py under --with-coxswain -- NEVER during vendor(). The tracked
# overlay/assets/visualizer/index.html ships in EVERY build and must stay
# coxswain-free (AC-11 clause 3), which is why this lives beside the
# augmentation tag machinery but is invoked from the build's post-staging step.
# The relative path inherits the augmentation tag's sibling constraint:
# coxswain/ must remain a sibling of visualizer/ under overlay/assets/.
_COXSWAIN_HIGHLIGHT_TAG = '<script type="module" src="../coxswain/viz_highlight.js"></script>'

# Konva 8.4.3 provenance (R4). Sourced from cdnjs, not the unpkg URL upstream
# declares in index.html -- unpkg.com is unreachable from this sandbox (curl
# -> 000). Version-pinned and banner/md5-verified here; never byte-diffed
# against the declared unpkg origin (open question, spec Sec "Open questions").
_KONVA_EXPECTED_BYTES = 158587
_KONVA_EXPECTED_MD5 = "28374db26d35a1227ce7142b26eda52a"
_KONVA_BANNER = b"Konva JavaScript Framework v8.4.3"


# --- diagnosability: +/-10 lines of context on any anchor/count mismatch ----


def _locate_context(text: str, needle: str, n_context: int = 10) -> list[str]:
    """Return one ``+/-n_context``-line block (with 1-based line numbers) for
    every occurrence of the literal ``needle`` in ``text``. Used to make an
    anchor mismatch diagnosable without re-running anything by hand -- per
    spec T1.1(f) / plan P6.1."""
    if not needle:
        return []
    lines = text.splitlines()
    blocks: list[str] = []
    pos = 0
    while True:
        idx = text.find(needle, pos)
        if idx == -1:
            break
        line_no = text.count("\n", 0, idx)
        start = max(0, line_no - n_context)
        end = min(len(lines), line_no + n_context + 1)
        block = "\n".join(f"{i + 1:6d} | {lines[i]}" for i in range(start, end))
        blocks.append(block)
        pos = idx + max(1, len(needle))
    return blocks


def _format_context_blocks(blocks: list[str]) -> str:
    if not blocks:
        return "(no occurrence found at all -- upstream likely renamed, reformatted, or removed this code entirely)"
    return "\n\n".join(f"--- occurrence {i} ---\n{b}" for i, b in enumerate(blocks, 1))


# Excluded from fallback-token search: too generic on their own (would match
# dozens of unrelated sites and defeat the point of "locate the drift").
_JS_STOPWORDS = {
    "function", "return", "const", "let", "var", "else", "true", "false",
    "null", "undefined", "async", "await", "this", "window", "document",
}


def _extract_probe_tokens(line: str) -> list[str]:
    """Identifier-like tokens from an anchor's first line, longest (most
    specific) first, for use when the exact line no longer appears verbatim
    -- e.g. a renamed function (`heartbeat` -> `heartbeat_X`) still contains
    `heartbeat` as a substring, so a token-level fallback still finds it."""
    tokens = re.findall(r"[A-Za-z_$][A-Za-z0-9_$]{3,}", line)
    uniq = {t for t in tokens if t.lower() not in _JS_STOPWORDS}
    return sorted(uniq, key=len, reverse=True)


def _anchor_mismatch_message(haystack: str, label: str, old: str, n: int) -> str:
    """Build a fail-loud message for a vis.js anchor that didn't match
    exactly once. Locates context via the anchor's first non-blank line first
    (anchors are exact multi-line strings; line 1 is usually still present
    even when a later line in the block has drifted); if that line is gone
    entirely (e.g. reformatted or the identifier renamed), falls back to the
    most specific identifier token extracted from it so the failure still
    points at the right neighbourhood instead of reporting nothing."""
    probe_candidates = [ln.strip() for ln in old.splitlines() if ln.strip()]
    first_line = probe_candidates[0] if probe_candidates else old[:60]
    probe_used = first_line
    blocks = _locate_context(haystack, first_line, n_context=10)
    fallback_note = ""
    if not blocks:
        for tok in _extract_probe_tokens(first_line):
            blocks = _locate_context(haystack, tok, n_context=10)
            if blocks:
                probe_used = tok
                fallback_note = (
                    f" (exact anchor line not found verbatim; falling back to "
                    f"the identifier token {tok!r} extracted from it)"
                )
                break
    return (
        f"vis.js anchor {label!r} expected exactly 1 match, found {n}.\n"
        f"probe used to locate context: {probe_used!r}{fallback_note}\n"
        f"{len(blocks)} occurrence(s) found. Context (+/-10 lines) around each:\n\n"
        f"{_format_context_blocks(blocks)}"
    )


# --- transformation steps ----------------------------------------------------


def apply_vis_edits(vis_src_text: str) -> str:
    vis = vis_src_text
    for label, old, new in VIS_EDITS:
        n = vis.count(old)
        if n != 1:
            raise VendorError(_anchor_mismatch_message(vis, label, old, n))
        vis = vis.replace(old, new)
        logger.info("vis.js edit applied: %s", label)
    vis += BRIDGE
    return vis


def strip_cdn(html: str) -> tuple[str, int]:
    total = 0
    for pat, rep in CDN_STRIP:
        html, n = pat.subn(rep, html)
        logger.info("index.html: %d substitution(s) for %s", n, pat.pattern[:60])
        total += n
    return html, total


def fix_favicon_paths(html: str) -> tuple[str, int]:
    original = html
    new_html, n = _FAVICON_RE.subn(r'\1="./favicon.png"', html)
    logger.info("index.html: %d absolute /favicon.png reference(s) rewritten to ./favicon.png", n)
    if n != 2:
        blocks = _locate_context(original, "favicon.png", n_context=10)
        raise VendorError(
            "expected exactly 2 absolute favicon references (icon <link> + header "
            f"<img>), found {n} matching href=\"/favicon.png\" or src=\"/favicon.png\". "
            "This is pin-sensitive (R5) -- inspect by hand:\n\n"
            f"{_format_context_blocks(blocks)}"
        )
    return new_html, n


def strip_placeholders(html: str) -> tuple[str, int]:
    names = _PLACEHOLDER_RE.findall(html)
    html2, n = _PLACEHOLDER_RE.subn("", html)
    logger.info("index.html: stripped %d server-template placeholder(s) by pattern: %s", n, names)
    return html2, n


def inject_augmentation_tag(html: str) -> str:
    n_body_close = html.count("</body>")
    if n_body_close != 1:
        blocks = _locate_context(html, "</body>", n_context=10)
        raise VendorError(
            f"expected exactly one </body> tag to inject the augmentation loader "
            f"before, found {n_body_close}. Context:\n\n{_format_context_blocks(blocks)}"
        )
    return html.replace("</body>", f"    {_AUGMENTATION_TAG}\n  </body>")


def inject_coxswain_highlight_tag(html: str) -> str:
    """BUILD-TIME ONLY (never inside vendor()): append the Coxswain highlight
    subscriber tag right after the augmentation tag, before </body>.

    "Alongside -- never instead of" (FR-12): the augmentation tag must already
    be present exactly once, and the result carries both. Idempotence is a
    guard, not a feature: a second call raises, because a doubled subscriber
    would draw every highlight twice and the mistake belongs in CI, not on a
    user's screen."""
    n_aug = html.count(_AUGMENTATION_TAG)
    if n_aug != 1:
        raise VendorError(
            f"expected exactly one augmentation tag to anchor the coxswain "
            f"highlight tag beside, found {n_aug}. Context:\n\n"
            f"{_format_context_blocks(_locate_context(html, 'visualizer-augmentations'))}"
        )
    if _COXSWAIN_HIGHLIGHT_TAG in html:
        raise VendorError("coxswain highlight tag is already present; refusing to double-inject")
    n_body_close = html.count("</body>")
    if n_body_close != 1:
        blocks = _locate_context(html, "</body>", n_context=10)
        raise VendorError(
            f"expected exactly one </body> tag to inject the coxswain highlight "
            f"tag before, found {n_body_close}. Context:\n\n{_format_context_blocks(blocks)}"
        )
    return html.replace(
        _AUGMENTATION_TAG,
        f"{_AUGMENTATION_TAG}\n    {_COXSWAIN_HIGHLIGHT_TAG}",
    )


def find_leftover_external_urls(html: str) -> list[str]:
    return re.findall(r"https://[^\"' ]+", html)


def verify_lib_js_identical(src: Path, out: Path) -> tuple[str, str]:
    h_src = hashlib.sha256((src / "lib.js").read_bytes()).hexdigest()
    h_out = hashlib.sha256((out / "lib.js").read_bytes()).hexdigest()
    logger.info("lib.js sha256 src=%s out=%s identical=%s", h_src[:16], h_out[:16], h_src == h_out)
    if h_src != h_out:
        raise VendorError(
            f"lib.js was not copied byte-identically: src sha256={h_src} out sha256={h_out}. "
            "The renderer must never be forked (R2)."
        )
    return h_src, h_out


def copy_favicon(src: Path, out: Path) -> Path:
    logo = src / "img" / "logo.png"
    if not logo.is_file():
        raise VendorError(f"expected upstream logo at {logo}, not found")
    dest = out / "favicon.png"
    shutil.copy(logo, dest)
    logger.info("favicon.png copied from %s", logo)
    return dest


def copy_konva(konva_src: Path, out: Path) -> Path:
    data = konva_src.read_bytes()
    size = len(data)
    md5 = hashlib.md5(data).hexdigest()
    banner_ok = _KONVA_BANNER in data[:512]
    logger.info("konva.min.js: %d bytes, md5=%s, banner_present=%s", size, md5, banner_ok)
    if size != _KONVA_EXPECTED_BYTES or md5 != _KONVA_EXPECTED_MD5 or not banner_ok:
        raise VendorError(
            f"konva.min.js provenance check failed for {konva_src}: expected "
            f"{_KONVA_EXPECTED_BYTES} bytes / md5 {_KONVA_EXPECTED_MD5} / banner "
            f"{_KONVA_BANNER!r} in the first 512 bytes; got {size} bytes / md5 "
            f"{md5} / banner_present={banner_ok}. Konva 8.4.3 provenance is "
            "version-pinned (R4) and must not silently drift."
        )
    dest = out / "konva.min.js"
    dest.write_bytes(data)
    return dest


def find_git_root(start: Path) -> Path | None:
    p = start.resolve()
    for parent in (p, *p.parents):
        if (parent / ".git").exists():
            return parent
    return None


def read_source_sha(src: Path) -> str:
    root = find_git_root(src)
    if root is None:
        logger.warning("no git root found above %s; VENDOR_MANIFEST source_sha will be 'unknown'", src)
        return "unknown"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning("git rev-parse HEAD failed for %s: %s", root, exc)
        return "unknown"


def read_pylabrobot_version(src: Path) -> str:
    # src is .../pylabrobot/visualizer -> version.txt lives one level up.
    version_file = src.parent / "version.txt"
    if version_file.is_file():
        return version_file.read_text().strip()
    logger.warning("no version.txt found next to %s; pylabrobot_version will be 'unknown'", src)
    return "unknown"


def build_manifest(out: Path, source_sha: str, pylabrobot_version: str) -> dict:
    files = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "VENDOR_MANIFEST.json":
            files.append(
                {
                    "path": p.relative_to(out).as_posix(),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "bytes": p.stat().st_size,
                }
            )
    return {
        "generator": "vendor_visualizer.py",
        "generator_version": GENERATOR_VERSION,
        "source_sha": source_sha,
        "pylabrobot_version": pylabrobot_version,
        "files": files,
    }


def vendor(src: Path, out: Path, konva: Path) -> dict:
    if not src.is_dir():
        raise VendorError(f"--src {src} is not a directory")
    if not (src / "vis.js").is_file() or not (src / "index.html").is_file():
        raise VendorError(f"--src {src} does not look like a pylabrobot visualizer/ dir (missing vis.js/index.html)")
    if not konva.is_file():
        raise VendorError(f"--konva {konva} is not a file")

    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__", "*.py"))
    logger.info("copied %s -> %s (excluding __pycache__/*.py)", src, out)

    h_src, h_out = verify_lib_js_identical(src, out)

    vis_out_text = apply_vis_edits((src / "vis.js").read_text())
    (out / "vis.js").write_text(vis_out_text)

    html = (src / "index.html").read_text()
    html, n_cdn = strip_cdn(html)
    html, n_fav = fix_favicon_paths(html)
    html, n_placeholders = strip_placeholders(html)
    html = inject_augmentation_tag(html)
    leftover = find_leftover_external_urls(html)
    logger.info("index.html remaining external URLs: %s", leftover)
    if leftover:
        raise VendorError(f"index.html still references external URL(s) after CDN strip: {leftover}")
    (out / "index.html").write_text(html)

    copy_favicon(src, out)
    copy_konva(konva, out)

    source_sha = read_source_sha(src)
    pylabrobot_version = read_pylabrobot_version(src)
    manifest = build_manifest(out, source_sha, pylabrobot_version)
    manifest_path = out / "VENDOR_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    logger.info(
        "wrote %s (%d file(s) recorded, source_sha=%s, pylabrobot_version=%s)",
        manifest_path,
        len(manifest["files"]),
        source_sha,
        pylabrobot_version,
    )

    return {
        "lib_js_sha_identical": h_src == h_out,
        "cdn_substitutions": n_cdn,
        "favicon_substitutions": n_fav,
        "placeholders_stripped": n_placeholders,
        "leftover_external_urls": leftover,
        "manifest": manifest,
    }


# --- CLI ----------------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
DEFAULT_WEB_REPL_ROOT = _THIS_FILE.parents[1]
DEFAULT_REPO_ROOT = _THIS_FILE.parents[2]
DEFAULT_SRC = DEFAULT_REPO_ROOT / "external" / "pylabrobot" / "pylabrobot" / "visualizer"
DEFAULT_OUT = DEFAULT_WEB_REPL_ROOT / "overlay" / "assets" / "visualizer"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--src",
        type=Path,
        default=DEFAULT_SRC,
        help="Upstream pylabrobot visualizer/ source dir, read-only "
        f"(default: {DEFAULT_SRC}).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output dir for the vendored tree; recreated from scratch on "
        f"every run (default: {DEFAULT_OUT}).",
    )
    parser.add_argument(
        "--konva",
        type=Path,
        required=True,
        help="Path to a local Konva 8.4.3 build (konva.min.js) to vendor. "
        "No default: upstream's declared source (unpkg.com) is unreachable "
        "from this sandbox, and a cdnjs/jsdelivr copy must be supplied "
        "explicitly so provenance stays auditable rather than implicit. "
        "Checked against R4's expected size/md5/banner.",
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
        vendor(args.src.resolve(), args.out.resolve(), args.konva.resolve())
    except VendorError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("vendored visualizer tree built at %s", args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Vendor the praxis brand webfonts into ``overlay/assets/theme/fonts/``.

The REPL site is offline-hard by construction: ``jupyter-lite.json`` sets
``disablePyPIFallback``, Pyodide is fully vendored, and GATE G5 asserts zero
CDN hits. ``scripts/repl_smoke.py`` additionally registers a ``requestfailed``
listener that fails the run on ANY failed request. A ``fonts.googleapis.com``
``<link>`` would therefore (a) break every genuinely-offline user and (b) turn
a transient Google outage into a red build. So the fonts ship as bytes in the
repo, exactly like ``overlay/assets/visualizer/`` does.

Only the ``latin`` subset is kept -- the full Google Fonts unicode-range set
is ~20 files per family and none of the non-latin ones are reachable from the
REPL's own UI strings.

``--check`` is the CI entry point. It is OFFLINE: it re-hashes the files on
disk against ``VENDOR_MANIFEST.json`` and never touches the network, so it can
run in the same network-free job as the rest of the REPL gates.

House rules: uv-run only, argparse + logging, fail loud.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("vendor_fonts")

_THIS_FILE = Path(__file__).resolve()
WEB_REPL_ROOT = _THIS_FILE.parents[1]
FONTS_DIR = WEB_REPL_ROOT / "overlay" / "assets" / "theme" / "fonts"
MANIFEST_PATH = FONTS_DIR / "VENDOR_MANIFEST.json"

# Google's CSS API serves woff2 only to UAs it believes support it. A urllib
# default UA gets TTF back, silently tripling the payload -- so this is
# load-bearing, not cargo-culted.
_WOFF2_UA = (
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_SUBSET = "latin"

# Every @font-face block Google emits is preceded by a /* subset */ comment.
_BLOCK_RE = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", re.DOTALL)
_SRC_RE = re.compile(r"url\((https://[^)]+\.woff2)\)")
_STYLE_RE = re.compile(r"font-style:\s*([^;]+);")
_WEIGHT_RE = re.compile(r"font-weight:\s*([^;]+);")
_RANGE_RE = re.compile(r"unicode-range:\s*([^;]+);")


class VendorError(RuntimeError):
  """Raised when vendoring or verification fails. Always fatal."""


@dataclass(frozen=True)
class FontSource:
  """One upstream family plus the faces we expect it to yield."""

  family: str
  css_query: str
  license_url: str
  license_file: str
  # (font-style, font-weight) -> output filename. Declaring this up front means
  # an upstream change to the served face set fails loud instead of silently
  # vendoring a different font than the CSS references.
  faces: dict[tuple[str, str], str]


FONT_SOURCES: tuple[FontSource, ...] = (
  FontSource(
    family="Roboto Flex",
    css_query="family=Roboto+Flex:opsz,wght@8..144,100..1000",
    license_url="https://raw.githubusercontent.com/googlefonts/roboto-flex/main/OFL.txt",
    license_file="OFL-RobotoFlex.txt",
    faces={("normal", "100 1000"): "RobotoFlex-Variable.woff2"},
  ),
  FontSource(
    family="JetBrains Mono",
    # Requested as a WEIGHT RANGE, not discrete weights. Asking for
    # `wght@0,400;0,700` makes Google emit two @font-face blocks pointing at
    # the SAME variable woff2 -- verified: both hashed
    # 83c005d4...a5be, i.e. we were storing one 31KB file twice. The range
    # form yields one face per style, each covering 100..800.
    css_query="family=JetBrains+Mono:ital,wght@0,100..800;1,100..800",
    license_url="https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/OFL.txt",
    license_file="OFL-JetBrainsMono.txt",
    faces={
      ("normal", "100 800"): "JetBrainsMono-Variable.woff2",
      ("italic", "100 800"): "JetBrainsMono-Italic-Variable.woff2",
    },
  ),
)


def _fetch_bytes(url: str) -> bytes:
  req = urllib.request.Request(url, headers={"User-Agent": _WOFF2_UA})  # noqa: S310
  with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
    return resp.read()


def _fetch_text(url: str) -> str:
  return _fetch_bytes(url).decode("utf-8")


def _sha256(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def _parse_faces(css: str) -> list[dict[str, str]]:
  """Pull the latin @font-face blocks out of a Google Fonts CSS response."""
  out: list[dict[str, str]] = []
  for subset, body in _BLOCK_RE.findall(css):
    if subset != _SUBSET:
      continue
    src = _SRC_RE.search(body)
    style = _STYLE_RE.search(body)
    weight = _WEIGHT_RE.search(body)
    urange = _RANGE_RE.search(body)
    if not (src and style and weight and urange):
      raise VendorError(f"malformed @font-face block for subset {subset!r}: {body[:200]!r}")
    out.append({
      "url": src.group(1),
      "style": style.group(1).strip(),
      "weight": weight.group(1).strip(),
      "unicode_range": urange.group(1).strip(),
    })
  return out


def vendor() -> int:
  """Download every declared face + license, then write VENDOR_MANIFEST.json."""
  FONTS_DIR.mkdir(parents=True, exist_ok=True)
  entries: list[dict[str, object]] = []

  for source in FONT_SOURCES:
    css_url = f"https://fonts.googleapis.com/css2?{source.css_query}&display=swap"
    logger.info("fetching CSS for %s", source.family)
    css = _fetch_text(css_url)
    faces = _parse_faces(css)

    seen: set[tuple[str, str]] = set()
    by_url: dict[str, tuple[str, str]] = {}
    for face in faces:
      key = (face["style"], face["weight"])
      if key not in source.faces:
        raise VendorError(
          f"{source.family}: upstream served an undeclared face {key!r}. "
          f"Declared: {sorted(source.faces)}. Update FONT_SOURCES deliberately."
        )
      if key in seen:
        raise VendorError(f"{source.family}: duplicate latin face for {key!r}.")
      seen.add(key)

      if face["url"] in by_url:
        raise VendorError(
          f"{source.family}: faces {by_url[face['url']]!r} and {key!r} resolve to the SAME "
          f"upstream file ({face['url'][-40:]}). That means discrete weights of a variable "
          "font were requested -- use a wght@a..b range in css_query instead of storing "
          "the identical bytes twice."
        )
      by_url[face["url"]] = key

      filename = source.faces[key]
      logger.info("  downloading %s", filename)
      blob = _fetch_bytes(face["url"])
      (FONTS_DIR / filename).write_bytes(blob)
      entries.append({
        "file": filename,
        "family": source.family,
        "style": face["style"],
        "weight": face["weight"],
        "unicode_range": face["unicode_range"],
        "source_url": face["url"],
        "source_css": css_url,
        "sha256": _sha256(blob),
        "size_bytes": len(blob),
        "license_file": source.license_file,
      })

    missing = set(source.faces) - seen
    if missing:
      raise VendorError(f"{source.family}: upstream did not serve declared face(s) {sorted(missing)}.")

    logger.info("  fetching license -> %s", source.license_file)
    lic = _fetch_text(source.license_url)
    (FONTS_DIR / source.license_file).write_text(lic, encoding="utf-8")
    entries.append({
      "file": source.license_file,
      "family": source.family,
      "source_url": source.license_url,
      "sha256": _sha256(lic.encode("utf-8")),
      "size_bytes": len(lic.encode("utf-8")),
      "kind": "license",
    })

  manifest = {
    "_comment": (
      "Generated by web-repl/scripts/vendor_fonts.py. Do not hand-edit. "
      "Verify with: uv run python web-repl/scripts/vendor_fonts.py --check"
    ),
    "subset": _SUBSET,
    "entries": sorted(entries, key=lambda e: str(e["file"])),
  }
  MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

  total = sum(int(e["size_bytes"]) for e in entries if e.get("kind") != "license")
  logger.info("vendored %d font file(s), %.1f KB total", len(entries) - len(FONT_SOURCES), total / 1024)
  return 0


def check() -> int:
  """Offline verification: re-hash on-disk files against the manifest."""
  if not MANIFEST_PATH.is_file():
    logger.error("%s missing -- run vendor_fonts.py (no --check) first.", MANIFEST_PATH)
    return 1

  manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
  failures = 0
  for entry in manifest["entries"]:
    path = FONTS_DIR / str(entry["file"])
    if not path.is_file():
      logger.error("MISSING: %s", path)
      failures += 1
      continue
    blob = path.read_bytes()
    actual = _sha256(blob)
    if actual != entry["sha256"]:
      logger.error("SHA MISMATCH: %s\n  expected %s\n  actual   %s", path, entry["sha256"], actual)
      failures += 1
    elif len(blob) != entry["size_bytes"]:
      logger.error("SIZE MISMATCH: %s (%d != %d)", path, len(blob), entry["size_bytes"])
      failures += 1

  # A manifest that lists nothing would pass vacuously.
  if not manifest["entries"]:
    logger.error("manifest lists zero entries -- vacuous check.")
    return 1

  if failures:
    logger.error("%d/%d entr(ies) failed.", failures, len(manifest["entries"]))
    return 1
  logger.info("all %d manifest entr(ies) OK", len(manifest["entries"]))
  return 0


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--check", action="store_true", help="Offline: verify on-disk files against the manifest.")
  parser.add_argument("-v", "--verbose", action="store_true")
  args = parser.parse_args(argv)

  logging.basicConfig(
    level=logging.DEBUG if args.verbose else logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
  )

  try:
    return check() if args.check else vendor()
  except VendorError as exc:
    logger.error("%s", exc)
    return 1


if __name__ == "__main__":
  sys.exit(main())

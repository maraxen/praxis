"""W4 build integration: the conditionally-staged viz_highlight script tag.

FR-12 / deviation D-C / AC-11 clause 3:
- a DEFAULT build's staged visualizer/index.html carries NO <script> tag
  referencing coxswain (asserted by build_repl.assert_visualizer_html_free_of_coxswain);
- a --with-coxswain build injects EXACTLY ONE second tag,
  <script type="module" src="../coxswain/viz_highlight.js">, alongside -- never
  instead of -- the augmentation tag;
- the tracked overlay/assets/visualizer/index.html is never rewritten: the
  injection happens on the STAGED dist copy only;
- staging itself is byte-preserving, so AC-11 clause 1's byte identity holds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import vendor_visualizer  # noqa: E402 -- path setup must precede this import


AUGMENTATION_TAG = (
    '<script type="module" src="../visualizer-augmentations/index.js"></script>'
)
COXSWAIN_TAG = '<script type="module" src="../coxswain/viz_highlight.js"></script>'

VENDORED_HTML = (
    "<!doctype html><html><head><title>viz</title></head><body>"
    '<canvas id="container"></canvas>'
    f"  {AUGMENTATION_TAG}\n  </body></html>"
)


class TestInjectCoxswainHighlightTag:
    def test_inserts_exactly_one_tag_after_the_augmentation_tag(self):
        out = vendor_visualizer.inject_coxswain_highlight_tag(VENDORED_HTML)
        assert out.count(COXSWAIN_TAG) == 1
        # "alongside -- never instead of": both tags present, ours AFTER theirs
        assert out.index(AUGMENTATION_TAG) < out.index(COXSWAIN_TAG)
        assert "</body>" in out

    def test_tracked_vendor_output_is_never_rewritten_by_this_function(
        self,
    ):
        """The function is pure text-in/text-out; vendor() must never call it."""
        import inspect

        source = inspect.getsource(vendor_visualizer.vendor)
        assert "inject_coxswain_highlight_tag" not in source, (
            "vendor() regenerates the TRACKED visualizer/index.html which ships in "
            "every build; the coxswain tag belongs to the BUILD-time staged copy only"
        )

    def test_double_injection_fails_loud(self):
        once = vendor_visualizer.inject_coxswain_highlight_tag(VENDORED_HTML)
        with pytest.raises(vendor_visualizer.VendorError):
            vendor_visualizer.inject_coxswain_highlight_tag(once)

    def test_missing_body_close_fails_loud(self):
        broken = VENDORED_HTML.replace("</body>", "")
        with pytest.raises(vendor_visualizer.VendorError):
            vendor_visualizer.inject_coxswain_highlight_tag(broken)

    def test_missing_augmentation_tag_fails_loud(self):
        broken = VENDORED_HTML.replace(AUGMENTATION_TAG, "")
        with pytest.raises(vendor_visualizer.VendorError):
            vendor_visualizer.inject_coxswain_highlight_tag(broken)


class TestBuildReplFlaggedHalf:
    @pytest.fixture()
    def seeded_out_dir(self, tmp_path: Path) -> Path:
        out = tmp_path / "dist"
        assets = out / "assets"
        (assets / "visualizer").mkdir(parents=True)
        (assets / "coxswain").mkdir(parents=True)
        (assets / "visualizer" / "index.html").write_text(VENDORED_HTML)
        (assets / "coxswain" / "viz_highlight.js").write_text("// subscriber\n")
        return out

    def test_flagged_half_of_clause_3_exactly_one_tag(self, seeded_out_dir: Path):
        import build_repl

        build_repl.inject_viz_highlight_tag(seeded_out_dir)
        html = (seeded_out_dir / "assets" / "visualizer" / "index.html").read_text()
        offenders = [
            line for line in html.splitlines()
            if "<script" in line.lower() and "coxswain" in line.lower()
        ]
        assert len(offenders) == 1
        assert COXSWAIN_TAG in html

    def test_assert_exactly_one_passes_then_detects_zero_and_two(
        self, seeded_out_dir: Path
    ):
        import build_repl

        build_repl.inject_viz_highlight_tag(seeded_out_dir)
        build_repl.assert_visualizer_html_exactly_one_coxswain_tag(seeded_out_dir)

        zero = tmp_dist_with_html("")
        with pytest.raises(build_repl.BuildAssertionError):
            build_repl.assert_visualizer_html_exactly_one_coxswain_tag(zero)

        two = tmp_dist_with_html(f"{COXSWAIN_TAG}\n{COXSWAIN_TAG}")
        with pytest.raises(build_repl.BuildAssertionError):
            build_repl.assert_visualizer_html_exactly_one_coxswain_tag(two)

    def test_staging_is_byte_preserving_so_ac11_clause1_holds(self):
        """The real stage_overlay copies bytes verbatim; run it against the
        actual overlay tree into a tmp dir and diff shas for the augmentation
        file AND confirm the tracked visualizer/index.html gains no coxswain
        tag from staging alone."""
        import hashlib
        import shutil

        import build_repl

        if not build_repl.OVERLAY_ASSETS_DIR.is_dir():
            pytest.skip("overlay assets not present")
        out = Path(build_repl.__file__).parent.parent / ".tmp-w4-stage-check"
        if out.exists():
            shutil.rmtree(out)
        try:
            n = build_repl.stage_overlay(out, include_coxswain=False)
            assert n > 0
            staged_aug = out / "assets" / "visualizer-augmentations" / "index.js"
            tracked_aug = build_repl._tracked_augmentation_path()
            assert staged_aug.is_file() and tracked_aug.is_file()
            sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            assert sha(staged_aug) == sha(tracked_aug), (
                "stage_overlay rewrote visualizer-augmentations/index.js (AC-11)"
            )
            staged_viz_html = out / "assets" / "visualizer" / "index.html"
            assert "coxswain" not in staged_viz_html.read_text().lower(), (
                "tracked/staged visualizer/index.html must stay coxswain-free; "
                "the tag belongs to the flagged post-staging step only"
            )
        finally:
            shutil.rmtree(out, ignore_errors=True)


def tmp_dist_with_html(script_lines: str) -> Path:
    import tempfile

    root = Path(tempfile.mkdtemp())
    (root / "assets" / "visualizer").mkdir(parents=True)
    (root / "assets" / "visualizer" / "index.html").write_text(
        f"<html><body>{script_lines}</body></html>"
    )
    return root

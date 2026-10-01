"""Dark-theme contrast and colour-vision computation for the notebook display (backlog #5654).

Task 260929_notebook-display-design, spec draft ``.praxia/docs/specs/261001_nd-next-5654-dark-tokens.md``.
Pre-registered by ``261001_nd_dark_tokens_contrast.bth.toml`` (committed BEFORE the first run of this file).

What it computes, with no browser and no network (pure standard library, a few milliseconds):

* the Dark palette as shipped: it is READ from ``web-repl/overlay/assets/theme/praxis-theme.css`` (the
  ``dark (default)`` block and the ``:root`` display constants), never typed in here;
* the contrast of each colour the outputs and the deck panel use against the Dark surfaces they sit on,
  under normal vision and the three Machado 2009 simulations, and CIEDE2000 between the colour pairs a reader
  must tell apart;
* four candidate token sets derived by a stated rule, and the constants of the vendored Visualizer3D page
  (``renderer.js`` / ``constants.js``, read from the files) against a Dark ground, with the CSS filter an
  inverted-viewer option would apply modelled numerically.

The colour instrument is the one ``web-repl/tests/test_display_colorblind.py`` already uses and verifies (its
own Sharma CIEDE2000 and Machado invariants run in CI); it is loaded by path, not copied. This script adds its
own paired controls (a positive that can pass and a negative that must fail) and refuses to report a verdict
when they do not behave (``instrument_ok``).
"""

from __future__ import annotations

import argparse
import colorsys
import importlib.util
import json
import logging
import math
import os
import re
import sys
import types
from pathlib import Path

LOG = logging.getLogger("nd_dark_tokens")

REPO = Path(__file__).resolve().parents[2]
CSS = REPO / "web-repl" / "overlay" / "assets" / "theme" / "praxis-theme.css"
CB_TEST = REPO / "web-repl" / "tests" / "test_display_colorblind.py"
V3D = REPO / "web-repl" / "overlay" / "assets" / "visualizer3d"

#: WCAG 2.x thresholds. Text 1.4.3; non-text marks 1.4.11. AC-27's "distinct" and the B8 hairline number.
TEXT_BAR = 4.5
MARK_BAR = 3.0
DISTINCT_DE = 10.0


# --------------------------------------------------------------------------- the instrument (loaded, not copied)


def load_instrument():
    """``test_display_colorblind.py`` loaded by path. It imports pytest at module level; the instrument itself
    does not use it, so a stub stands in when pytest is not installed in this interpreter."""
    try:
        import pytest  # noqa: F401
    except ImportError:
        stub = types.ModuleType("pytest")

        class _Mark:
            def __getattr__(self, _name):
                return lambda *a, **k: (lambda f: f)

        stub.mark = _Mark()
        stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f))
        sys.modules["pytest"] = stub
    spec = importlib.util.spec_from_file_location("_nd_colorblind_instrument", CB_TEST)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_nd_colorblind_instrument"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- reading the shipped CSS


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c))) for c in rgb)


def _rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))


def over(fg_rgb: tuple[float, float, float], alpha: float, bg_hex: str) -> str:
    bg = _rgb(bg_hex)
    return _hex(tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg_rgb, bg)))


def css_block(text: str, start_marker: str, end_marker: str) -> str:
    i = text.index(start_marker)
    j = text.index(end_marker, i + len(start_marker))
    return text[i:j]


def token(block: str, name: str) -> str:
    m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", block)
    if not m:
        raise LookupError(f"{name} not declared in the block")
    return m.group(1).strip()


def parse_css() -> dict:
    text = CSS.read_text(encoding="utf-8")
    dark = css_block(text, "/* --- dark (default)", "/* --- light: praxis")
    consts = css_block(text, "/* --- display constants", "/* --- light: steel ground")
    root = css_block(text, "/* --- brand constants", "/* --- shared: typography")

    def alpha_white(value: str) -> float:
        m = re.fullmatch(r"rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*([0-9.]+)\s*\)", value)
        if not m:
            raise ValueError(f"not a white rgba: {value!r}")
        return float(m.group(1))

    out = {
        "layout0": token(dark, "--jp-layout-color0").upper(),
        "layout1": token(dark, "--jp-layout-color1").upper(),
        "layout2": token(dark, "--jp-layout-color2").upper(),
        "ink_alpha": alpha_white(token(dark, "--jp-content-font-color0")),
        "ink_soft_alpha": alpha_white(token(dark, "--jp-content-font-color2")),
        "rail_alpha": alpha_white(token(dark, "--jp-border-color1")),
        "error_title": token(dark, "--jp-error-color1").split()[0].upper(),
        "link": token(root, "--praxis-moonstone").split()[0].upper(),
        "moonstone": token(root, "--praxis-moonstone").split()[0].upper(),
        "rose": token(root, "--praxis-rose").split()[0].upper(),
        "moonstone_ink": token(consts, "--praxis-moonstone-ink").split()[0].upper(),
        "rose_ink": token(consts, "--praxis-rose-ink").split()[0].upper(),
        "brick": token(consts, "--praxis-brick").split()[0].upper(),
    }
    for k in ("layout0", "layout1", "layout2", "error_title", "moonstone", "rose", "moonstone_ink", "rose_ink", "brick"):
        if not re.fullmatch(r"#[0-9A-F]{6}", out[k]):
            raise ValueError(f"{k} is not #RRGGBB: {out[k]!r}")
    return out


# --------------------------------------------------------------------------- measures


class Measures:
    def __init__(self, cb, surfaces: list[str]):
        self.cb = cb
        self.surfaces = surfaces  # the Dark surfaces an output or the panel can sit on; the worst one governs

    def contrast_min(self, colour: str, surfaces: list[str] | None = None) -> float:
        """Smallest WCAG contrast of ``colour`` over the given surfaces and the four visions."""
        return min(self.cb.min_contrast(colour, s) for s in (surfaces or self.surfaces))

    def de_min(self, a: str, b: str) -> float:
        return self.cb.min_delta_e(a, b)


def lighten(base: str, bar: float, meas: Measures) -> str:
    """Rule R: keep the hue and saturation (HLS) of ``base`` and raise the lightness in 0.5 % steps until the
    colour's worst contrast (surfaces x visions) reaches ``bar``. Returns ``base`` if it already does."""
    r, g, b = (c / 255 for c in _rgb(base))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    while l <= 1.0:
        cand = _hex(tuple(255 * c for c in colorsys.hls_to_rgb(h, l, s)))
        if meas.contrast_min(cand) >= bar:
            return cand
        l += 0.005
    raise ValueError(f"no lightness of {base} reaches {bar}")


def search_brick(rose: str, base: str, bar: float, meas: Measures) -> tuple[str, float]:
    """Constrained search: hue 0..20 deg, HLS saturation 60..100 %, the lowest lightness reaching ``bar`` for each
    (hue, saturation); keep the colour with the largest worst-vision CIEDE2000 against rose, ties to the hue
    nearest the shipped brick's. Returns (hex, min dE vs rose)."""
    base_h = colorsys.rgb_to_hls(*(c / 255 for c in _rgb(base)))[0] * 360
    best = None
    for hdeg in range(0, 21):
        for sat in range(60, 101, 2):
            for light in range(30, 80):
                cand = _hex(tuple(255 * c for c in colorsys.hls_to_rgb(hdeg / 360, light / 100, sat / 100)))
                if meas.contrast_min(cand) < bar:
                    continue
                de = meas.de_min(cand, rose)
                key = (round(de, 6), -abs(hdeg - base_h))
                if best is None or key > best[0]:
                    best = (key, cand, de)
                break
    if best is None:
        raise ValueError("search_brick found nothing")
    return best[1], best[2]


def candidate_checks(name: str, c: dict, base: dict, meas: Measures) -> dict:
    """The pre-registered checks for one candidate token set ``c`` (moonstone_ink, rose_ink, brick, error_title)."""
    cb = meas.cb
    ground = base["ground"]
    text = {
        "ink": base["ink"],
        "ink_soft": base["ink_soft"],
        "error_title": c["error_title"],
        "link": base["link"],
    }
    marks = {
        "moonstone": base["moonstone"],
        "rose": base["rose"],
        "brick": c["brick"],
        "moonstone_ink": c["moonstone_ink"],
        "rose_ink": c["rose_ink"],
    }
    text_c = {k: meas.contrast_min(v) for k, v in text.items()}
    mark_c = {k: meas.contrast_min(v) for k, v in marks.items()}
    pairs = {
        "rose_vs_brick": meas.de_min(base["rose"], c["brick"]),
        "moonstone_vs_brick": meas.de_min(base["moonstone"], c["brick"]),
        "ran_rail_vs_running_rail": meas.de_min(c["moonstone_ink"], base["rose"]),
        "ran_rail_vs_error_rail": meas.de_min(c["moonstone_ink"], c["brick"]),
        "ran_rail_vs_notrun_rail": meas.de_min(c["moonstone_ink"], base["rail"]),
    }
    info = {
        "moonstone_vs_rose": meas.de_min(base["moonstone"], base["rose"]),  # unchanged constants; B8 rescues it by a shape cue
        "error_title_vs_rose": meas.de_min(c["error_title"], base["rose"]),
        "rose_ink_vs_rose": meas.de_min(c["rose_ink"], base["rose"]),
        "text_contrast_on_ground_normal": {k: round(cb.contrast(v, ground), 2) for k, v in text.items()},
        "mark_contrast_on_ground_normal": {k: round(cb.contrast(v, ground), 2) for k, v in marks.items()},
    }
    text_ok = all(v >= TEXT_BAR for v in text_c.values())
    marks_ok = all(v >= MARK_BAR for v in mark_c.values())
    pairs_ok = all(pairs[k] >= DISTINCT_DE for k in pairs)
    failing = (
        [f"text:{k}={v:.2f}" for k, v in text_c.items() if v < TEXT_BAR]
        + [f"mark:{k}={v:.2f}" for k, v in mark_c.items() if v < MARK_BAR]
        + [f"pair:{k}={v:.1f}" for k, v in pairs.items() if v < DISTINCT_DE]
    )
    return {
        "name": name,
        "values": c,
        "text_min_contrast": {k: round(v, 2) for k, v in text_c.items()},
        "mark_min_contrast": {k: round(v, 2) for k, v in mark_c.items()},
        "pair_min_de": {k: round(v, 1) for k, v in pairs.items()},
        "info": info,
        "text_ok": text_ok,
        "marks_ok": marks_ok,
        "pairs_ok": pairs_ok,
        "all_ok": bool(text_ok and marks_ok and pairs_ok),
        "failing": failing,
    }


# --------------------------------------------------------------------------- the Visualizer3D constants


def read_viewer_constants() -> dict:
    consts = (V3D / "constants.js").read_text(encoding="utf-8")
    renderer = (V3D / "renderer.js").read_text(encoding="utf-8")

    def js_hex(src: str, name: str) -> str:
        m = re.search(rf"\b{name}\s*=\s*0x([0-9a-fA-F]{{6}})", src)
        if not m:
            raise LookupError(f"{name} not found")
        return "#" + m.group(1).upper()

    return {
        "scene_background": js_hex(renderer, "BACKGROUND"),
        "flat_edge": js_hex(consts, "FLAT_EDGE"),
        "select": js_hex(consts, "SELECT"),
        "structure_light": js_hex(consts, "STRUCTURE_LIGHT"),
        "structure_dark": js_hex(consts, "STRUCTURE_DARK"),
        "tip": re.search(r"\btip:\s*0x([0-9a-fA-F]{6})", consts) and "#" + re.search(r"\btip:\s*0x([0-9a-fA-F]{6})", consts).group(1).upper(),
    }


def css_filter_invert_hue180(h: str) -> str:
    """``filter: invert(1) hue-rotate(180deg)`` applied to an sRGB colour (Filter Effects Module Level 1: the
    shorthand functions act on the sRGB values; the hue-rotate matrix is the spec's)."""
    r, g, b = (1 - c / 255 for c in _rgb(h))
    cs, sn = math.cos(math.pi), math.sin(math.pi)
    m = (
        (0.213 + cs * 0.787 - sn * 0.213, 0.715 - cs * 0.715 - sn * 0.715, 0.072 - cs * 0.072 + sn * 0.928),
        (0.213 - cs * 0.213 + sn * 0.143, 0.715 + cs * 0.285 + sn * 0.140, 0.072 - cs * 0.072 - sn * 0.283),
        (0.213 - cs * 0.213 - sn * 0.787, 0.715 - cs * 0.715 + sn * 0.715, 0.072 + cs * 0.928 + sn * 0.072),
    )
    out = [max(0.0, min(1.0, m[i][0] * r + m[i][1] * g + m[i][2] * b)) for i in range(3)]
    return _hex(tuple(255 * c for c in out))


# --------------------------------------------------------------------------- the run


def run(out_dir: Path | None) -> dict:
    cb = load_instrument()
    css = parse_css()

    # -- the instrument's own paired controls (BATHOS.md: a control that can only pass proves nothing) --
    controls = {
        "positive_black_white_contrast": round(cb.contrast("#000000", "#FFFFFF"), 2),
        "positive_black_white_de_min": round(min(cb.delta_e("#000000", "#FFFFFF", v) for v in cb.VISIONS), 1),
        "light_ink_on_sheet": round(cb.contrast("#1D2935", "#FFFFFF"), 2),
        "negative_near_rose_de_max": round(max(cb.delta_e("#ED7A9B", "#E8789A", v) for v in cb.VISIONS), 2),
        "negative_grey_on_grey_contrast": round(cb.contrast("#777777", "#808080"), 2),
        "negative_red_green_tritan_free_pair_de_protan": round(cb.delta_e("#87281E", "#3C4B1E", "protan"), 1),
    }
    instrument_ok = (
        abs(controls["positive_black_white_contrast"] - 21.0) < 0.01
        and controls["positive_black_white_de_min"] >= DISTINCT_DE
        and abs(controls["light_ink_on_sheet"] - 14.8) < 0.06  # DESIGN.md states 14.8:1
        and controls["negative_near_rose_de_max"] < DISTINCT_DE
        and controls["negative_grey_on_grey_contrast"] < MARK_BAR
        and controls["negative_red_green_tritan_free_pair_de_protan"] < DISTINCT_DE
    )

    ground = css["layout0"]
    surfaces = [css["layout0"], css["layout1"], css["layout2"]]
    base = {
        "ground": ground,
        "ink": over((255, 255, 255), css["ink_alpha"], ground),
        "ink_soft": over((255, 255, 255), css["ink_soft_alpha"], ground),
        "rail": over((255, 255, 255), css["rail_alpha"], ground),
        "link": css["link"],
        "moonstone": css["moonstone"],
        "rose": css["rose"],
    }
    meas = Measures(cb, surfaces)

    shipped = {
        "moonstone_ink": css["moonstone_ink"],
        "rose_ink": css["rose_ink"],
        "brick": css["brick"],
        "error_title": css["error_title"],
    }
    cands: dict[str, dict] = {"P0_shipped": shipped}
    cands["P1_marks3"] = {
        "moonstone_ink": lighten(shipped["moonstone_ink"], MARK_BAR, meas),
        "rose_ink": lighten(shipped["rose_ink"], MARK_BAR, meas),
        "brick": lighten(shipped["brick"], MARK_BAR, meas),
        "error_title": lighten(shipped["error_title"], TEXT_BAR, meas),
    }
    cands["P2_ink45_brick35"] = {
        "moonstone_ink": lighten(shipped["moonstone_ink"], TEXT_BAR, meas),
        "rose_ink": lighten(shipped["rose_ink"], TEXT_BAR, meas),
        "brick": lighten(shipped["brick"], 3.5, meas),
        "error_title": lighten(shipped["error_title"], TEXT_BAR, meas),
    }
    cands["P3_all45"] = {
        "moonstone_ink": cands["P2_ink45_brick35"]["moonstone_ink"],
        "rose_ink": cands["P2_ink45_brick35"]["rose_ink"],
        "brick": lighten(shipped["brick"], TEXT_BAR, meas),
        "error_title": cands["P2_ink45_brick35"]["error_title"],
    }
    brick_g, _ = search_brick(base["rose"], shipped["brick"], 3.5, meas)
    cands["P2g_searched_brick"] = {**cands["P2_ink45_brick35"], "brick": brick_g}

    results = {name: candidate_checks(name, c, base, meas) for name, c in cands.items()}

    # -- the vendored viewer against a Dark ground (informational; not in the outcomes) --
    vc = read_viewer_constants()
    viewer = {
        "constants": vc,
        "contrast_on_dark_ground_normal": {
            k: round(cb.contrast(v, ground), 2) for k, v in vc.items() if v and k != "scene_background"
        },
        "contrast_on_its_own_light_ground_normal": {
            k: round(cb.contrast(v, vc["scene_background"]), 2) for k, v in vc.items() if v and k != "scene_background"
        },
        "invert_hue180": {k: css_filter_invert_hue180(v) for k, v in vc.items() if v},
    }
    flt = viewer["invert_hue180"]
    viewer["contrast_after_filter_normal"] = {
        k: round(cb.contrast(flt[k], flt["scene_background"]), 2) for k in vc if vc[k] and k != "scene_background"
    }
    viewer["filtered_ground_vs_panel_ground_contrast"] = round(cb.contrast(flt["scene_background"], ground), 2)
    viewer["raw_light_ground_vs_panel_ground_contrast"] = round(cb.contrast(vc["scene_background"], ground), 2)
    viewer["k1a_canvas_tolerance_check"] = {
        "css_ground_EEF1F4_vs_scene_background_max_channel_delta": max(
            abs(a - b) for a, b in zip(_rgb("#EEF1F4"), _rgb(vc["scene_background"]))
        )
    }

    flat = {
        "instrument_ok": bool(instrument_ok),
        "css_parsed": True,
        "measurement_valid": bool(instrument_ok),
        "ground": ground,
        "surfaces": ",".join(surfaces),
        "p0_text_ok": results["P0_shipped"]["text_ok"],
        "p0_marks_ok": results["P0_shipped"]["marks_ok"],
        "p0_pairs_ok": results["P0_shipped"]["pairs_ok"],
        "p0_all_ok": results["P0_shipped"]["all_ok"],
        "p0_failing": ";".join(results["P0_shipped"]["failing"]),
        "p1_all_ok": results["P1_marks3"]["all_ok"],
        "p2_all_ok": results["P2_ink45_brick35"]["all_ok"],
        "p3_all_ok": results["P3_all45"]["all_ok"],
        "p3_rose_vs_brick_ok": results["P3_all45"]["pair_min_de"]["rose_vs_brick"] >= DISTINCT_DE,
        "p2g_all_ok": results["P2g_searched_brick"]["all_ok"],
        "p1_values": json.dumps(cands["P1_marks3"], sort_keys=True),
        "p2_values": json.dumps(cands["P2_ink45_brick35"], sort_keys=True),
        "p3_values": json.dumps(cands["P3_all45"], sort_keys=True),
        "p2g_values": json.dumps(cands["P2g_searched_brick"], sort_keys=True),
    }
    full = {"flat": flat, "controls": controls, "base": base, "candidates": results, "viewer": viewer}
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(json.dumps(full, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        LOG.info("wrote %s", out_dir / "result.json")
    return full


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=None, help="where the full table is written (result.json)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    full = run(args.out_dir)
    flat = full["flat"]
    for k, v in flat.items():
        LOG.info("%s = %s", k, v)
    target = os.environ.get("BTH_RESULTS_PATH")
    if target:
        Path(target).write_text(json.dumps(flat, sort_keys=True) + "\n", encoding="utf-8")
        LOG.info("handed %d fields to bathos (%s)", len(flat), target)
    else:
        LOG.warning("BTH_RESULTS_PATH is unset: run this under `bth run`, or no outcome is evaluated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

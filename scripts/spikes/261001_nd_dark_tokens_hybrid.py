"""Second pre-registered check for backlog #5654: the HYBRID Dark token set (task 260929_notebook-display-design).

Pre-registered by ``261001_nd_dark_tokens_hybrid.bth.toml``, committed BEFORE the run. It exists because the first
run (``261001_nd_dark_tokens_contrast``) showed that no single registered candidate is right on every token:
P2's rose ink sits 3.3 dE from rose (a hover outline that cannot be told from the focus ring) and P2's brick sits
exactly on the dE 10 line from rose, while P1's rose ink and brick keep 13 to 14 dE. The hybrid takes each token
from the candidate whose number is better for that token's use, and is checked against the first run's bars PLUS
three new ones the first run did not gate: hover-vs-focus distinctness, hairline clearance of the Dark surfaces,
and a brick-vs-rose margin.

Fixed hexes (typed here BEFORE the run, from the first run's registered table): moonstone ink #4393B8 (P2),
rose ink #C05277 (P1), brick #D1523A (P1), error-title token #D47687 (P1 = P2).

Reuses the first script's parsing and measures by path; adds its own paired mutant controls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path

LOG = logging.getLogger("nd_dark_hybrid")
FIRST = Path(__file__).resolve().parent / "261001_nd_dark_tokens_contrast.py"

HYBRID = {"moonstone_ink": "#4393B8", "rose_ink": "#C05277", "brick": "#D1523A", "error_title": "#D47687"}
HAIRLINE_DE = 5.0  # the B8 hairline number (test_display_colorblind.HAIRLINE_DE)
HOVER_DE = 10.0
BRICK_ROSE_MARGIN_DE = 12.0


def load_first():
    spec = importlib.util.spec_from_file_location("_nd_first", FIRST)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_nd_first"] = module
    spec.loader.exec_module(module)
    return module


def evaluate(first, cand: dict, css: dict, base: dict, meas, surfaces: list[str]) -> dict:
    res = first.candidate_checks("hybrid", cand, base, meas)
    hover = meas.de_min(cand["rose_ink"], base["rose"])
    # the Dark hairline (white at --jp-border-color1 alpha) composited over each surface vs that surface
    hair = {}
    for s in surfaces:
        line = first.over((255, 255, 255), css["rail_alpha"], s)
        hair[s] = round(meas.cb.min_delta_e(line, s), 1)
    res["hover_vs_focus_de"] = round(hover, 1)
    res["hairline_de_by_surface"] = hair
    res["hover_ok"] = hover >= HOVER_DE
    res["hairline_ok"] = all(v >= HAIRLINE_DE for v in hair.values())
    res["brick_margin_ok"] = res["pair_min_de"]["rose_vs_brick"] >= BRICK_ROSE_MARGIN_DE
    res["moonstone_ink_vs_moonstone_de"] = round(meas.de_min(cand["moonstone_ink"], base["moonstone"]), 1)
    res["all_ok_extended"] = bool(
        res["all_ok"] and res["hover_ok"] and res["hairline_ok"] and res["brick_margin_ok"]
    )
    return res


def run(out_dir: Path | None) -> dict:
    first = load_first()
    cb = first.load_instrument()
    css = first.parse_css()
    ground = css["layout0"]
    surfaces = [css["layout0"], css["layout1"], css["layout2"]]
    base = {
        "ground": ground,
        "ink": first.over((255, 255, 255), css["ink_alpha"], ground),
        "ink_soft": first.over((255, 255, 255), css["ink_soft_alpha"], ground),
        "rail": first.over((255, 255, 255), css["rail_alpha"], ground),
        "link": css["link"],
        "moonstone": css["moonstone"],
        "rose": css["rose"],
    }
    meas = first.Measures(cb, surfaces)

    main = evaluate(first, HYBRID, css, base, meas, surfaces)
    # the checker's own negatives: each mutant MUST fail the check it targets
    mut_brick_p3 = evaluate(first, {**HYBRID, "brick": "#DB7865"}, css, base, meas, surfaces)  # P3's brick
    mut_rose_p2 = evaluate(first, {**HYBRID, "rose_ink": "#CE7794"}, css, base, meas, surfaces)  # P2's rose ink
    mut_brick_shipped = evaluate(first, {**HYBRID, "brick": css["brick"]}, css, base, meas, surfaces)
    mut_title_shipped = evaluate(first, {**HYBRID, "error_title": css["error_title"]}, css, base, meas, surfaces)
    negatives = {
        "brick_p3_fails_rose_pair": mut_brick_p3["pair_min_de"]["rose_vs_brick"] < first.DISTINCT_DE,
        "rose_ink_p2_fails_hover": not mut_rose_p2["hover_ok"],
        "brick_shipped_fails_marks": not mut_brick_shipped["marks_ok"],
        "error_title_shipped_fails_text": not mut_title_shipped["text_ok"],
        "brick_p3_fails_extended": not mut_brick_p3["all_ok_extended"],
    }
    controls_ok = all(negatives.values())

    # a first-script instrument sanity (the same positive/negative pair, repeated so this run is valid on its own)
    inst_ok = (
        abs(cb.contrast("#000000", "#FFFFFF") - 21.0) < 0.01
        and min(cb.delta_e("#000000", "#FFFFFF", v) for v in cb.VISIONS) >= first.DISTINCT_DE
        and max(cb.delta_e("#ED7A9B", "#E8789A", v) for v in cb.VISIONS) < first.DISTINCT_DE
    )
    flat = {
        "instrument_ok": bool(inst_ok),
        "negative_controls_fail_as_required": bool(controls_ok),
        "measurement_valid": bool(inst_ok and controls_ok),
        "hybrid_values": json.dumps(HYBRID, sort_keys=True),
        "hybrid_text_ok": main["text_ok"],
        "hybrid_marks_ok": main["marks_ok"],
        "hybrid_pairs_ok": main["pairs_ok"],
        "hybrid_hover_ok": main["hover_ok"],
        "hybrid_hairline_ok": main["hairline_ok"],
        "hybrid_brick_margin_ok": main["brick_margin_ok"],
        "hybrid_all_ok": main["all_ok_extended"],
        "hybrid_failing": ";".join(main["failing"]),
    }
    full = {"flat": flat, "negatives": negatives, "hybrid": main}
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(json.dumps(full, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        LOG.info("wrote %s", out_dir / "result.json")
    return full


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    full = run(args.out_dir)
    for k, v in full["flat"].items():
        LOG.info("%s = %s", k, v)
    target = os.environ.get("BTH_RESULTS_PATH")
    if target:
        Path(target).write_text(json.dumps(full["flat"], sort_keys=True) + "\n", encoding="utf-8")
        LOG.info("handed %d fields to bathos (%s)", len(full["flat"]), target)
    else:
        LOG.warning("BTH_RESULTS_PATH is unset: run this under `bth run`, or no outcome is evaluated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

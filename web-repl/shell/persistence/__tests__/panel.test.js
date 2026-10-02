// panel.test.js -- the persistence UI restyle is a pure restyle (task
// 260929_notebook-display-design, backlog #5653; the ladder itself is #4296).
//
// panel.js had no unit test: only the real-browser `--persistence-check`
// touched it. These tests drive `mount` in a fake DOM (panel_dom.js) and pin
// three things without a browser:
//
//   1. STRUCTURE. The DOM panel.js builds -- tags, ids, `data-praxis-*`
//      attributes, texts, nesting -- is byte-for-byte what it was before the
//      restyle. panel.golden.json was captured by running panel_dom.js's
//      `captureStates` against panel.js at 60d053f2 (BEFORE the restyle), in
//      three states (initial, panel open, first-save modal) and two
//      environments (FSA and no-FSA). The one addition the restyle makes, the
//      chip's `data-praxis-warn`, is stripped before comparing; the
//      stylesheet <link> lives in <head>, outside the compared <body>.
//   2. INLINE STYLE. Every element's inline style carries LAYOUT keys only
//      (position, size cap, stacking, flex). Colour, type and shape come from
//      panel.css, whose rules read the epic tokens (test_display_css.py pins
//      that side).
//   3. THE WARN HOOK. The chip's `data-praxis-warn` follows tierLabel's warn.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";

import * as panel from "../panel.js";
import { captureStates, elementsOf } from "./panel_dom.js";

const GOLDEN = JSON.parse(readFileSync(new URL("./panel.golden.json", import.meta.url), "utf8"));

/** The inline-style keys a node may carry: layout, never colour/type/shape. */
const LAYOUT_KEYS = new Set([
  "position",
  "right",
  "bottom",
  "zIndex",
  "display",
  "flexDirection",
  "alignItems",
  "maxWidth",
  "marginTop",
]);

/** Keys outside the layout set (the instrument; also exercised on a bad node below). */
function nonLayoutKeys(elements) {
  const bad = [];
  for (const el of elements) {
    for (const key of Object.keys(el.style)) {
      if (!LAYOUT_KEYS.has(key)) bad.push(`${el.localName}.style.${key}`);
    }
  }
  return bad;
}

/** Remove the one attribute the restyle adds, anywhere in a snapshot. */
function withoutAdditive(node) {
  if (typeof node === "string") return node;
  const attrs = { ...node.attrs };
  delete attrs["data-praxis-warn"];
  return { ...node, attrs, children: node.children.map(withoutAdditive) };
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("structure is unchanged by the restyle", () => {
  for (const [label, fsa] of [
    ["fsa", true],
    ["no_fsa", false],
  ]) {
    test(`every captured state matches the pre-restyle golden (${label})`, async () => {
      const { states } = await captureStates(panel, { fsa });
      for (const state of ["initial", "panelOpen", "modal"]) {
        expect(states[state].map(withoutAdditive)).toEqual(GOLDEN[label][state]);
      }
    });
  }

  test("the golden is not vacuous: it holds the gate's hooks", () => {
    const text = JSON.stringify(GOLDEN);
    for (const needle of [
      "praxis-persistence",
      "praxis-persistence-first-save",
      "data-praxis-tier",
      "data-praxis-excluded",
      "toggle-panel",
      "protect",
      "choose-folder",
      "keep-browser-only",
      "Browser only",
      "Chromium",
    ]) {
      expect(text).toContain(needle);
    }
    // the modal state has the dialog open, and only in the modal state
    expect(GOLDEN.fsa.modal[1].open).toBe(true);
    expect(GOLDEN.fsa.initial[1].open).toBe(false);
  });

  test("negative control: a renamed action or a moved panel is detected", async () => {
    const { states } = await captureStates(panel, { fsa: true });
    const renamed = structuredClone(states.initial.map(withoutAdditive));
    renamed[0].children[0].attrs["data-praxis-action"] = "toggle";
    expect(renamed).not.toEqual(GOLDEN.fsa.initial);
    const moved = structuredClone(states.initial.map(withoutAdditive));
    moved[0].children.reverse(); // panel before chip
    expect(moved).not.toEqual(GOLDEN.fsa.initial);
  });
});

describe("inline style is layout only", () => {
  test("every element built by mount carries layout keys only", async () => {
    const { root, dialog } = await captureStates(panel, { fsa: true });
    expect(nonLayoutKeys([...elementsOf(root), ...elementsOf(dialog)])).toEqual([]);
  });

  test("the layout values the gate's geometry relies on are unchanged", async () => {
    const { root, chip } = await captureStates(panel, { fsa: true });
    const panelEl = root.children[1];
    expect(root.style).toMatchObject({
      position: "fixed",
      right: "8px",
      bottom: "8px",
      zIndex: "2147483000",
      display: "inline-flex",
      flexDirection: "column",
      alignItems: "flex-end",
      maxWidth: "320px",
    });
    expect(panelEl.style).toMatchObject({ marginTop: "4px", maxWidth: "320px" });
    expect(Object.keys(chip.style)).toEqual([]);
  });

  test("negative control: a node carrying a colour literal is reported", () => {
    const fake = { localName: "button", style: { background: "#fff", position: "fixed" } };
    expect(nonLayoutKeys([fake])).toEqual(["button.style.background"]);
  });
});

describe("the stylesheet link", () => {
  test("mount adds exactly one stylesheet link for panel.css beside panel.js", async () => {
    const { doc } = await captureStates(panel, { fsa: true });
    const links = doc.head.children.filter((c) => c.localName === "link");
    expect(links.length).toBe(1);
    expect(links[0].rel).toBe("stylesheet");
    expect(links[0].id).toBe("praxis-persistence-style");
    expect(links[0].href).toBe(new URL("panel.css", import.meta.resolve("../panel.js")).href);
  });
});

describe("the chip's warn hook follows the tier label", () => {
  test("L0 (Browser only) is warn; protecting the browser storage (L1) is not", async () => {
    const { chip, root } = await captureStates(panel, { fsa: true });
    // captureStates leaves the modal open on L0; the chip is still L0's.
    expect(chip.textContent).toBe("Browser only");
    expect(chip.getAttribute("data-praxis-warn")).toBe("1");

    // open the panel and press Protect (the persist() stub resolves true -> L1)
    chip.dispatch("click");
    const panelEl = root.children[1];
    const protect = elementsOf(panelEl).find((e) => e.getAttribute("data-praxis-action") === "protect");
    expect(protect).toBeTruthy();
    protect.dispatch("click");
    await tick();
    await tick();
    expect(root.getAttribute("data-praxis-tier")).toBe("L1");
    expect(chip.textContent).toBe("Browser storage protected");
    expect(chip.getAttribute("data-praxis-warn")).toBe("0");
  });
});

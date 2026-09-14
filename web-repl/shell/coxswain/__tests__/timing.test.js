import { describe, expect, test } from "bun:test";

import {
  EDIT_DEBOUNCE_MS,
  KERNEL_RTT_TIMEOUT_MS,
  REGROUND_TIMEOUT_MS,
} from "../timing.js";

describe("§4.7 timing constants", () => {
  test("values match the spec exactly", () => {
    expect(EDIT_DEBOUNCE_MS).toBe(300);
    expect(REGROUND_TIMEOUT_MS).toBe(2000);
    expect(KERNEL_RTT_TIMEOUT_MS).toBe(5000);
  });

  test("all are integers", () => {
    for (const value of [EDIT_DEBOUNCE_MS, REGROUND_TIMEOUT_MS, KERNEL_RTT_TIMEOUT_MS]) {
      expect(Number.isInteger(value)).toBe(true);
    }
  });

  test("the two edit-path values stay deliberately different", () => {
    // §4.7: 300 ms is a typing pause; 2 s is a work budget. Collapsing them
    // into one number is how a debounce silently becomes a timeout.
    expect(EDIT_DEBOUNCE_MS).not.toBe(REGROUND_TIMEOUT_MS);
    expect(REGROUND_TIMEOUT_MS).toBeLessThan(KERNEL_RTT_TIMEOUT_MS);
  });
});

import { describe, expect, test } from "bun:test";

import { add } from "../harness_smoke.js";

describe("harness smoke", () => {
  test("add returns the sum of two numbers", () => {
    expect(add(1, 2)).toBe(3);
  });
});

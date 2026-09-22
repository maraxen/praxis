// codec.test.js -- Round-trip tests for modelToFileBytes and fileBytesToModel.
// AC-5: notebook, UTF-8 text and binary each round-trip by content.

import { describe, expect, test } from "bun:test";

import {
  fileBytesToModel,
  modelToFileBytes,
  splitDrivePath,
} from "../codec.js";

describe("codec: modelToFileBytes and fileBytesToModel", () => {
  describe("notebook round-trip (AC-5)", () => {
    test("notebook.ipynb round-trips by content", () => {
      const original = {
        path: "notebook.ipynb",
        type: "file",
        format: "json",
        content: {
          cells: [
            {
              cell_type: "code",
              source: ["print('hello')\n"],
            },
          ],
          metadata: {},
          nbformat: 4,
          nbformat_minor: 2,
        },
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.path).toBe(original.path);
      expect(restored.type).toBe("file");
      expect(restored.format).toBe("json");
      expect(restored.content).toEqual(original.content);
    });

    test("notebook output includes 1-space indent and trailing newline", () => {
      const model = {
        path: "test.ipynb",
        type: "file",
        format: "json",
        content: { cells: [], metadata: {} },
      };

      const bytes = modelToFileBytes(model);
      const text = new TextDecoder().decode(bytes);

      // Should start with '{' and end with '}\n'
      expect(text.startsWith("{")).toBe(true);
      expect(text.endsWith("}\n")).toBe(true);

      // Should use 1-space indent (not 2 or 4)
      expect(text).toContain(" ");
      expect(text).not.toContain("  "); // no 2-space indent
    });
  });

  describe("UTF-8 text round-trip (AC-5)", () => {
    test("text file (.txt) round-trips by content", () => {
      const original = {
        path: "readme.txt",
        type: "file",
        format: "text",
        content: "Hello, World!\nLine 2\n",
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.path).toBe(original.path);
      expect(restored.type).toBe("file");
      expect(restored.format).toBe("text");
      expect(restored.content).toBe(original.content);
    });

    test("Python file (.py) round-trips as UTF-8", () => {
      const original = {
        path: "script.py",
        type: "file",
        format: "text",
        content: 'def greet():\n    print("Hello")\n',
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.path).toBe(original.path);
      expect(restored.format).toBe("text");
      expect(restored.content).toBe(original.content);
    });

    test("UTF-8 text with special characters", () => {
      const original = {
        path: "text.md",
        type: "file",
        format: "text",
        content: "# Markdown\n\nEmoji: 😀 📚\n",
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.format).toBe("text");
      expect(restored.content).toBe(original.content);
    });
  });

  describe("binary round-trip (AC-5)", () => {
    test("binary file round-trips via base64", () => {
      // Create a sample binary: [0x00, 0x01, 0x02, 0xFF]
      const binaryData = new Uint8Array([0x00, 0x01, 0x02, 0xff]);
      const base64 = btoa(String.fromCharCode.apply(null, binaryData));

      const original = {
        path: "image.bin",
        type: "file",
        format: "base64",
        content: base64,
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.path).toBe(original.path);
      expect(restored.type).toBe("file");
      expect(restored.format).toBe("base64");
      expect(restored.content).toBe(original.content);
    });
  });

  describe("UTF-8 fallback for invalid text", () => {
    test("invalid UTF-8 bytes fall back to base64", () => {
      // Create invalid UTF-8: 0xFF 0xFE (not a valid UTF-8 sequence)
      const invalidUtf8 = new Uint8Array([0xff, 0xfe]);

      const restored = fileBytesToModel("unknown.bin", invalidUtf8);

      // Should be decoded as base64, not text
      expect(restored.format).toBe("base64");
      expect(restored.content).toBe(btoa(String.fromCharCode(0xff, 0xfe)));
    });

    test("valid UTF-8 is decoded as text, not base64", () => {
      const utf8Text = new TextEncoder().encode("Hello, World!");

      const restored = fileBytesToModel("text.txt", utf8Text);

      expect(restored.format).toBe("text");
      expect(restored.content).toBe("Hello, World!");
    });
  });

  describe("path validation (splitDrivePath)", () => {
    test("rejects empty path", () => {
      expect(() => splitDrivePath("")).toThrow();
    });

    test("rejects '.' path", () => {
      expect(() => splitDrivePath(".")).toThrow();
    });

    test("rejects '..' path", () => {
      expect(() => splitDrivePath("..")).toThrow();
    });

    test("rejects path with empty segment (e.g., 'a//b')", () => {
      expect(() => splitDrivePath("a//b")).toThrow();
    });

    test("rejects path with '.' segment", () => {
      expect(() => splitDrivePath("./file.txt")).toThrow();
      expect(() => splitDrivePath("a/./b")).toThrow();
    });

    test("rejects path with '..' segment", () => {
      expect(() => splitDrivePath("../file.txt")).toThrow();
      expect(() => splitDrivePath("a/../b")).toThrow();
    });

    test("accepts valid flat paths", () => {
      expect(() => splitDrivePath("file.txt")).not.toThrow();
      expect(() => splitDrivePath("notebook.ipynb")).not.toThrow();
    });

    test("accepts valid nested paths", () => {
      expect(() => splitDrivePath("folder/file.txt")).not.toThrow();
      expect(() => splitDrivePath("a/b/c/file.ipynb")).not.toThrow();
    });
  });

  describe("modelToFileBytes validation", () => {
    test("rejects model without path", () => {
      expect(() => modelToFileBytes({ type: "file" })).toThrow();
    });

    test("rejects directory type", () => {
      expect(() =>
        modelToFileBytes({
          path: "folder",
          type: "directory",
        }),
      ).toThrow();
    });
  });

  describe("fileBytesToModel validation", () => {
    test("rejects empty path", () => {
      expect(() => fileBytesToModel("", new Uint8Array())).toThrow();
    });

    test("accepts ArrayBuffer input", () => {
      const original = {
        path: "test.txt",
        type: "file",
        format: "text",
        content: "test",
      };

      const bytes = modelToFileBytes(original);
      const buffer = bytes.buffer;
      const restored = fileBytesToModel("test.txt", buffer);

      expect(restored.content).toBe("test");
    });

    test("accepts base64 string input", () => {
      const base64 = btoa("test content");
      const restored = fileBytesToModel("test.bin", base64);

      expect(restored.format).toBe("base64");
      expect(restored.content).toBe(base64);
    });
  });

  describe("nested paths", () => {
    test("notebook in subdirectory round-trips", () => {
      const original = {
        path: "notebooks/subfolder/analysis.ipynb",
        type: "file",
        format: "json",
        content: { cells: [], metadata: {}, nbformat: 4, nbformat_minor: 2 },
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.path).toBe(original.path);
      expect(restored.content).toEqual(original.content);
    });

    test("text file in subdirectory round-trips", () => {
      const original = {
        path: "docs/folder/readme.md",
        type: "file",
        format: "text",
        content: "# Documentation\n",
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.path).toBe(original.path);
      expect(restored.format).toBe("text");
      expect(restored.content).toBe(original.content);
    });
  });

  describe("edge cases", () => {
    test("notebook with empty cells array", () => {
      const original = {
        path: "empty.ipynb",
        type: "file",
        format: "json",
        content: { cells: [], metadata: {}, nbformat: 4, nbformat_minor: 2 },
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.content).toEqual(original.content);
    });

    test("empty text file", () => {
      const original = {
        path: "empty.txt",
        type: "file",
        format: "text",
        content: "",
      };

      const bytes = modelToFileBytes(original);
      const restored = fileBytesToModel(original.path, bytes);

      expect(restored.content).toBe("");
    });

    test("text file with no explicit content field", () => {
      const model = {
        path: "noexcontent.txt",
        type: "file",
        // no content field
      };

      const bytes = modelToFileBytes(model);
      const restored = fileBytesToModel(model.path, bytes);

      // Empty string should be encoded
      expect(restored.content).toBe("");
    });
  });
});

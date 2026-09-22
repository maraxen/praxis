// codec.js -- Serialize/deserialize JupyterLab models to/from file bytes.
//
// Supports three file types:
//   - Notebooks (.ipynb): JSON with 1-space indent and trailing newline
//   - Text files (.txt, .md, .py, etc.): UTF-8 text
//   - Binary files (anything else): base64 encoding
//
// Decoding falls back to base64 if UTF-8 decode fails (D1).

/**
 * Serialize a JupyterLab model to file bytes.
 *
 * @param {object} model - A JupyterLab contents model:
 *   { path: string, type: "file"|"directory", format?: "text"|"base64", content?: any }
 * @returns {Uint8Array} The file bytes ready to write to disk.
 *   - Notebooks (.ipynb): JSON string with 1-space indent and trailing newline.
 *   - Text files: UTF-8 encoded content.
 *   - Binary files: base64-encoded content.
 * @throws {Error} if model.type is "directory" or path segments are invalid.
 */
export function modelToFileBytes(model) {
  if (!model || !model.path) {
    throw new Error("modelToFileBytes: model must have a path");
  }
  if (model.type === "directory") {
    throw new Error("modelToFileBytes: cannot encode a directory");
  }

  const path = model.path;
  const isNotebook = path.endsWith(".ipynb");

  // Validate the path
  splitDrivePath(path);

  if (isNotebook) {
    // Notebooks: JSON.stringify with 1-space indent and trailing newline.
    const json = JSON.stringify(model.content, null, 1) + "\n";
    return new TextEncoder().encode(json);
  }

  // For text and binary files, format determines encoding.
  const content = model.content ?? "";
  if (model.format === "base64") {
    // Binary: decode base64 string to bytes.
    return new Uint8Array(
      atob(content)
        .split("")
        .map((c) => c.charCodeAt(0)),
    );
  }

  // Text: UTF-8 encode.
  return new TextEncoder().encode(content);
}

/**
 * Deserialize file bytes back to a JupyterLab model.
 *
 * @param {string} path - The file path (e.g., "notebook.ipynb", "script.py").
 * @param {Uint8Array | ArrayBuffer | string} bytes - The raw file bytes.
 *   - If a string, assumed to be already base64-encoded.
 * @returns {object} A JupyterLab contents model:
 *   { path, type: "file", format, content }
 *   - Notebooks: format="json", content is parsed object.
 *   - Text files: format="text", content is string.
 *   - Binary files: format="base64", content is base64 string.
 * @throws {Error} if path segments are invalid.
 */
export function fileBytesToModel(path, bytes) {
  if (!path) {
    throw new Error("fileBytesToModel: path must not be empty");
  }

  // Validate the path
  splitDrivePath(path);

  const isNotebook = path.endsWith(".ipynb");

  // If input is already a base64 string, return it as-is in base64 format.
  if (typeof bytes === "string") {
    if (isNotebook) {
      // Notebooks: decode base64 to bytes, then decode as UTF-8 and parse JSON.
      const data = new Uint8Array(
        atob(bytes)
          .split("")
          .map((c) => c.charCodeAt(0)),
      );
      const text = new TextDecoder("utf-8", { fatal: true }).decode(data);
      const content = JSON.parse(text);
      return { path, type: "file", format: "json", content };
    }
    // For non-notebook files, a string input is already base64, so return it as-is.
    return { path, type: "file", format: "base64", content: bytes };
  }

  // Normalize bytes to Uint8Array if needed.
  let data;
  if (bytes instanceof ArrayBuffer) {
    data = new Uint8Array(bytes);
  } else if (bytes instanceof Uint8Array) {
    data = bytes;
  } else {
    throw new Error("fileBytesToModel: bytes must be Uint8Array, ArrayBuffer, or base64 string");
  }

  if (isNotebook) {
    // Notebooks: decode as UTF-8, parse JSON.
    const text = new TextDecoder("utf-8", { fatal: true }).decode(data);
    const content = JSON.parse(text);
    return { path, type: "file", format: "json", content };
  }

  // Try to decode as UTF-8 text. If it fails, fall back to base64.
  let content;
  let format;
  try {
    content = new TextDecoder("utf-8", { fatal: true }).decode(data);
    format = "text";
  } catch {
    // Not valid UTF-8: treat as binary (base64).
    content = btoa(String.fromCharCode.apply(null, data));
    format = "base64";
  }

  return { path, type: "file", format, content };
}

/**
 * Validate a drive path: reject empty, ".", "..", and other invalid segments.
 *
 * @param {string} path - A file path (e.g., "notebook.ipynb", "folder/file.txt").
 * @throws {Error} if the path is empty, ".", "..", or contains invalid segments.
 */
export function splitDrivePath(path) {
  if (!path || path === "." || path === "..") {
    throw new Error(`splitDrivePath: invalid path: "${path}"`);
  }

  const segments = path.split("/");
  for (const segment of segments) {
    if (segment === "" || segment === "." || segment === "..") {
      throw new Error(`splitDrivePath: invalid path segment: "${segment}" in "${path}"`);
    }
  }
}

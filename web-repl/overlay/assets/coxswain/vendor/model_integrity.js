/**
 * Coxswain serving runtime -- first-use model integrity check (P2.7a).
 *
 * HAND-AUTHORED: never written by `fetch_models.py --runtime` (recorded in its
 * VENDOR_MANIFEST.json with role "hand-authored", like visualizer-augmentations/
 * is recorded by vendor_visualizer.py). Edit here, never in generated files.
 *
 * Contract (spec 260825_coxswain-phase-2-functiongemma-copilot-p.md rev2,
 * F3/F4 + AC-2.7a.x "first-use integrity check"):
 *
 *   Every byte of the FunctionGemma model is verified against the build
 *   manifest's sha256 BEFORE it is used ("before serving"). A mismatch is a
 *   LOUD failure -- a thrown ModelIntegrityError naming the file, expected and
 *   actual digest -- never a console warning beside a working-looking pipeline.
 *   Verified bytes are persisted to Cache Storage and served from there on
 *   later loads (Cache-API retention across reloads is F4's persistence story;
 *   measured empirically in .praxia/docs/research/260825_functiongemma-footprint.md).
 *
 * Shape notes for the P2.8 worker author:
 *   - This module is transport plumbing, not the worker lifecycle (F4 owns
 *     session_id/turn_id/envelope rules). It returns raw primitives.
 *   - MODELS_BASE_DEFAULT assumes the dev layout where web-repl/ itself is the
 *     server root (`python -m http.server` from web-repl/) so gitignored
 *     vendor/models/ is same-origin at /vendor/models/. When P2.9 stages model
 *     files into dist/, pass { modelsBase } explicitly -- do not silently rely
 *     on the default.
 *   - Verification hashes the FULL buffer via crypto.subtle (no streaming SHA-
 *     256 in WebCrypto). Transient peak ~2x the largest file while both the
 *     download buffer and the verify copy are alive; measured in the footprint
 *     doc. Revisit only if peak memory becomes the binding constraint.
 */

/** Loud failure type. Callers (worker/system lines) must surface `.message`. */
export class ModelIntegrityError extends Error {
  constructor(message) {
    super(message);
    this.name = "ModelIntegrityError";
  }
}

/** Build manifest location relative to THIS file:
 * assets/coxswain/vendor/ -> ../../ = assets/ -> wheels/manifest.json. */
const BUILD_MANIFEST_URL = new URL("../../wheels/manifest.json", import.meta.url);

/** Vendored transformers.js bundle sits beside this file. This is the
 * SELF-CONTAINED build (ORT inlined, no bare module specifiers -- the .web
 * variants fail to link origin-local, see fetch_models.py RUNTIME_FILES). */
const TRANSFORMERS_BUNDLE_URL = new URL("./transformers.min.js", import.meta.url);

/** Vendored ORT backend directory (wasmPaths), sibling ort/. */
const ORT_WASM_DIR_URL = new URL("./ort/", import.meta.url);

/** Provisional same-origin model root for the dev-server layout (see above). */
const MODELS_BASE_DEFAULT = new URL("../../../vendor/models/", import.meta.url);

/** Default single-dtype choice (D4); exactly ONE dtype ships globally. */
export const DEFAULT_MODEL_NAME = "functiongemma-270m-it-q4f16";

/**
 * Fetch + JSON-parse the build manifest. Loud on any failure: a missing or
 * unparseable manifest means nothing served under it can be trusted.
 */
export async function loadBuildManifest(manifestUrl = BUILD_MANIFEST_URL) {
  let resp;
  try {
    resp = await fetch(manifestUrl);
  } catch (err) {
    throw new ModelIntegrityError(
      `INTEGRITY BOOT FAILURE: cannot fetch build manifest ${manifestUrl.href}: ${err}`
    );
  }
  if (!resp.ok) {
    throw new ModelIntegrityError(
      `INTEGRITY BOOT FAILURE: build manifest ${manifestUrl.href} -> HTTP ${resp.status}`
    );
  }
  try {
    return await resp.json();
  } catch (err) {
    throw new ModelIntegrityError(
      `INTEGRITY BOOT FAILURE: build manifest ${manifestUrl.href} is not valid JSON: ${err}`
    );
  }
}

/**
 * Select one model's entries out of the manifest's flag-gated `models` array.
 * Loud when the key is absent (default builds carry no models claim at all --
 * asking for one in such a build is a caller bug, not an empty result).
 */
export function resolveModelEntries(manifest, { name = DEFAULT_MODEL_NAME } = {}) {
  const models = manifest.models;
  if (!Array.isArray(models)) {
    throw new ModelIntegrityError(
      'INTEGRITY BOOT FAILURE: build manifest carries no "models" array ' +
        "(was it generated without --with-models?) -- refusing to serve unverified weights."
    );
  }
  const entries = models.filter((e) => e.name === name);
  if (entries.length === 0) {
    throw new ModelIntegrityError(
      `INTEGRITY BOOT FAILURE: manifest has no model named "${name}" ` +
        `(present: ${[...new Set(models.map((e) => e.name))].join(", ") || "none"})`
    );
  }
  for (const e of entries) {
    if (typeof e.sha256 !== "string" || e.sha256.length !== 64 || typeof e.bytes !== "number") {
      throw new ModelIntegrityError(
        `INTEGRITY BOOT FAILURE: malformed manifest entry for ${e.filename ?? "?"}: ` +
          `${JSON.stringify(e)}`
      );
    }
  }
  return entries;
}

/** sha256 of an ArrayBuffer as lowercase hex. */
export async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Fetch a URL and verify size + sha256 against a manifest entry BEFORE the
 * bytes are handed to anyone. Returns the verified ArrayBuffer.
 */
export async function fetchAndVerify(url, entry) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new ModelIntegrityError(
      `MODEL FETCH FAILURE: ${url} -> HTTP ${resp.status} (expected ${entry.bytes} bytes, ` +
        `sha256 ${entry.sha256.slice(0, 12)}...)`
    );
  }
  const buffer = await resp.arrayBuffer();
  const actualSha = await sha256Hex(buffer);
  if (buffer.byteLength !== entry.bytes || actualSha !== entry.sha256) {
    throw new ModelIntegrityError(
      `INTEGRITY FAILURE: ${url} does not match the build manifest ` +
        `(bytes ${buffer.byteLength}/${entry.bytes}, sha256 ${actualSha} vs expected ${entry.sha256}). ` +
        "Refusing to serve unverified model weights."
    );
  }
  return buffer;
}

/**
 * Map a transformers.js request URL back to its repo-relative filename under
 * the model directory, e.g.
 *   <modelsBase>functiongemma-270m-it-onnx-q4f16/onnx/model_q4f16.onnx_data
 *   -> "onnx/model_q4f16.onnx_data"
 * Returns null when the request points outside every known model dir.
 */
export function repoRelativeFilename(requestUrl, entries) {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(requestUrl, self.location?.href).pathname);
  } catch {
    return null;
  }
  for (const entry of entries) {
    // entry.filename = "<model-dir>/<repo-relative>"; match on the tail.
    const suffix = "/" + entry.filename;
    if (pathname.endsWith(suffix)) {
      return entry.filename;
    }
  }
  return null;
}

/**
 * Build the transformers.js-compatible cache object (env.useCustomCache /
 * env.customCache shape: { match, put }) that enforces the integrity contract:
 *
 *   put(): hash the incoming response and compare against the manifest BEFORE
 *          persisting; mismatch throws ModelIntegrityError (the load aborts).
 *   match(): serve previously-VERIFIED bytes from Cache Storage.
 *
 * Requests whose filename has no manifest entry fail loud too: at first use,
 * every successfully-fetched model file must be something the manifest can
 * vouch for, otherwise the pin table and the checkpoint have drifted apart.
 */
export function createVerifyingCache(entries, { modelsBase = MODELS_BASE_DEFAULT, cacheName = "coxswain-models-v1" } = {}) {
  const byFilename = new Map(entries.map((e) => [e.filename, e]));
  let storagePromise = null;
  const openStorage = () => {
    storagePromise ??= caches.open(cacheName);
    return storagePromise;
  };

  return {
    /** CacheInterface.match(request) -> Response | undefined */
    async match(request) {
      const url = typeof request === "string" ? request : request.url;
      const filename = repoRelativeFilename(url, entries);
      if (filename === null) {
        return undefined; // not ours (e.g. a 404-probe the hub layer tolerates)
      }
      const storage = await openStorage();
      return storage.match(filename);
    },

    /** CacheInterface.put(request, response) -- verify, then persist. */
    async put(request, response) {
      const url = typeof request === "string" ? request : request.url;
      const filename = repoRelativeFilename(url, entries);
      if (filename === null) {
        throw new ModelIntegrityError(
          `INTEGRITY FAILURE: fetched model file ${url} has no entry in the build ` +
            "manifest's models array -- pin table and checkpoint have drifted."
        );
      }
      const entry = byFilename.get(filename);
      const buffer = await response.clone().arrayBuffer();
      const actualSha = await sha256Hex(buffer);
      if (buffer.byteLength !== entry.bytes || actualSha !== entry.sha256) {
        throw new ModelIntegrityError(
          `INTEGRITY FAILURE: ${filename} does not match the build manifest ` +
            `(bytes ${buffer.byteLength}/${entry.bytes}, sha256 ${actualSha} vs expected ` +
            `${entry.sha256}). Refusing to persist or serve unverified model weights.`
        );
      }
      const storage = await openStorage();
      // Persist under the stable repo-relative key so retention survives URL
      // changes across deploys; store the verified bytes themselves.
      await storage.put(filename, new Response(buffer, { headers: { "content-type": "application/octet-stream" } }));
    },
  };
}

/**
 * One-call runtime bootstrap: wire the vendored ORT backend path, install the
 * verifying cache, dynamic-import the vendored transformers.js bundle, and
 * resolve the manifest entries. Returns { tf, entries } where `tf` is the
 * transformers module. NO network beyond this site's origin ever happens:
 * GATE G5's jsDelivr default inside the bundle was rewritten at vendoring
 * time, and wasmPaths is set explicitly here before any session exists.
 */
export async function initCoxswainRuntime({
  manifestUrl = BUILD_MANIFEST_URL,
  modelName = DEFAULT_MODEL_NAME,
  modelsBase = MODELS_BASE_DEFAULT,
  cacheName = "coxswain-models-v1",
} = {}) {
  const manifest = await loadBuildManifest(manifestUrl);
  const entries = resolveModelEntries(manifest, { name: modelName });

  const tf = await import(TRANSFORMERS_BUNDLE_URL.href);
  tf.env.backends.onnx.wasm.wasmPaths = ORT_WASM_DIR_URL.href;
  // Weights come from this origin only, under vendor/models/: local loading
  // ON, remote Hub OFF (zero non-origin network; G5's spirit at runtime).
  tf.env.allowLocalModels = true;
  tf.env.allowRemoteModels = false;
  // Single-threaded first: cross-origin isolation (COOP/COEP) is NOT assumed
  // for GitHub Pages; threads would need SABs. Footprint doc measures this
  // configuration. Flip numThreads deliberately, with measurements, in P2.8.
  tf.env.backends.onnx.wasm.numThreads = 1;
  tf.env.useCustomCache = true;
  tf.env.customCache = createVerifyingCache(entries, { modelsBase, cacheName });

  return { tf, entries };
}

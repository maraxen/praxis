// export.js -- L1/L2/L3 persistence wiring (W5, §2.3's last clause).
//
// All three tiers treat BOTH stores (coxswain_turns + coxswain_overrides) as
// ONE bundle -- never two trails that can drift apart or be stitched by hand:
//
//   L1  persist() / restore()  -- the whole audit state as ONE self-describing
//       JSON string. The caller chooses the medium (e.g. localStorage); this
//       module deliberately does not touch it.
//   L2  bindWorkingFolder() / saveToWorkingFolder() / loadFromWorkingFolder()
//       -- one `coxswain-audit-bundle.json` file in a File System Access
//       working folder. The directory handle is injected; nothing here calls
//       showDirectoryPicker itself, so tests run without a browser and the
//       panel keeps permission UX on its side.
//   L3  exportBundle() / importBundle() -- the same document shape as
//       store.py's export_bundle(): { exported_by_schema_version, turns keyed
//       by turn_id, overrides[] }. Self-describing independently of the
//       database it came from (§2.5).
//
// AC-21: a read-only degraded store still EXPORTS (readable) but refuses to
// import/restore. Foreign-schema bundles are rejected LOUDLY via the store's
// ReadOnlyStoreError -- never coerced, never partially merged.

export const BUNDLE_FILENAME = "coxswain-audit-bundle.json";

/**
 * @param {object} options
 * @param {import("./audit_store.js").AuditStore} options.store
 */
export function createAuditPersistence({ store }) {
  if (!store || typeof store.exportBundle !== "function") {
    throw new Error("createAuditPersistence requires an AuditStore");
  }
  /** @type {{ getFileHandle: Function } | null} */
  let workingFolder = null;

  async function importOrThrow(bundle, { allowEmpty = false } = {}) {
    if (!allowEmpty && bundle === null) return { imported: false };
    await store.importBundle(bundle);
    return { imported: true };
  }

  return {
    // -- L1 ------------------------------------------------------------------

    /** Serialize BOTH stores into one JSON string (L1 persist shape). */
    persist() {
      return JSON.stringify(store.exportBundle());
    },

    /** Inverse of persist(): rebuild both stores from an L1 snapshot.
     * Read-only stores refuse (AC-21); foreign schemas refuse loudly. */
    restore(snapshot) {
      let bundle;
      try {
        bundle = JSON.parse(snapshot);
      } catch (error) {
        throw new Error(`audit persistence: snapshot is not valid JSON (${error})`);
      }
      return importOrThrow(bundle);
    },

    // -- L2 ------------------------------------------------------------------

    /** Bind a File System Access directory handle (injected; the caller owns
     * the picker and its permission prompts). */
    async bindWorkingFolder(dirHandle) {
      if (!dirHandle || typeof dirHandle.getFileHandle !== "function") {
        throw new Error(
          "bindWorkingFolder requires a File System Access directory handle",
        );
      }
      workingFolder = dirHandle;
      return { bound: true, filename: BUNDLE_FILENAME };
    },

    get workingFolderBound() {
      return workingFolder !== null;
    },

    /** Write the ONE bundle file into the bound working folder. */
    async saveToWorkingFolder({ dirHandle = null } = {}) {
      const folder = dirHandle ?? workingFolder;
      if (!folder) {
        throw new Error("saveToWorkingFolder: no working folder bound");
      }
      const fileHandle = await folder.getFileHandle(BUNDLE_FILENAME, {
        create: true,
      });
      const writable = await fileHandle.createWritable();
      try {
        await writable.write(JSON.stringify(store.exportBundle()));
        await writable.close();
      } catch (error) {
        try {
          await writable.abort?.();
        } catch {
          /* the original error is what matters */
        }
        throw error;
      }
      return { saved: BUNDLE_FILENAME };
    },

    /** Read the bundle from the bound working folder and import it. A missing
     * file is NOT an error: resolves {imported:false} so first-run tabs boot
     * cleanly against an empty folder. */
    async loadFromWorkingFolder({ dirHandle = null } = {}) {
      const folder = dirHandle ?? workingFolder;
      if (!folder) {
        throw new Error("loadFromWorkingFolder: no working folder bound");
      }
      let text;
      try {
        const fileHandle = await folder.getFileHandle(BUNDLE_FILENAME, {
          create: false,
        });
        const file = await fileHandle.getFile();
        text = await file.text();
      } catch (error) {
        if (error && error.name === "NotFoundError") {
          return { imported: false };
        }
        throw error;
      }
      return importOrThrow(JSON.parse(text));
    },

    // -- L3 ------------------------------------------------------------------

    /** The self-describing bundle document (same shape as store.py). */
    exportBundle() {
      return store.exportBundle();
    },

    /** Import a bundle document into the store (both stores as one unit). */
    async importBundle(bundle) {
      return importOrThrow(bundle, { allowEmpty: true });
    },
  };
}

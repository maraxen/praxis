// web-repl/shell/praxis-shell.js
//
// D1 (ADR .praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md
// Sec 2.3): the shell-injected praxis_git_sha carrier, plus the
// praxis:shell-ping / praxis:shell-pong handshake responder that lets the
// browser bootstrap detect WHOLE-DEPLOYMENT staleness (every asset,
// including manifest.json, consistently old) -- the one failure mode D2's
// per-file sha256 cannot catch, because a wholly-stale deployment is
// internally self-consistent.
//
// This file is TRACKED and is NEVER rewritten by any build step. The actual
// sha value is injected as a preceding inline <script> block by
// inject_shell.py into the generated lab/index.html -- inject_shell.py
// mutates that generated dist file, never this tracked source. That is what
// resolves the dev-loop dilemma ADR Sec 2.3 names explicitly ("neither r1
// branch was viable: stamping the tracked source makes the build script
// co-own a committed file, and stamping only dist/ requires a rebuild"):
// this file stays untouched and importable/readable at all times, and only
// the generated HTML page (already rebuilt on every `build_repl.py` run)
// carries the value of the day.
//
// PROTOCOL (authoritative; the praxis_bootstrap.py author implements the
// bootstrap-side half of this exactly):
//
//   1. `inject_shell.py` (real build) or `inject_shell.py --dev` (dev loop)
//      injects, immediately before this script tag, an inline script
//      setting `window.PRAXIS_GIT_SHA` to either the superproject's
//      `git rev-parse HEAD` or the literal string "dev".
//   2. The bootstrap, after fetching manifest.json and reading its own
//      `praxis_git_sha` field (real sha, or "dev" if `build_manifest.py
//      --dev` produced it), posts `{type: "praxis:shell-ping"}` on a
//      `BroadcastChannel("praxis_repl")` -- the SAME channel already used
//      for `praxis:ready` (ADR Sec 5.3; no new channel is introduced).
//   3. THIS script, running in the top-level shell page -- outside the
//      JupyterLite asset set, so a stale service-worker cache over the
//      fetched assets cannot also stale THIS file's injected value --
//      listens on that channel. On `praxis:shell-ping` it replies with
//      `{type: "praxis:shell-pong", praxis_git_sha: window.PRAXIS_GIT_SHA}`
//      on the same channel.
//   4. The bootstrap compares `manifest.praxis_git_sha` to the pong's
//      `praxis_git_sha` by PLAIN STRING EQUALITY -- nothing fancier. That
//      equality already implements the dev-loop escape hatch as an
//      EMERGENT property, not a special case: "dev" == "dev" passes
//      trivially, and every other combination (real/real mismatch,
//      real/"dev", "dev"/real) fails closed. See
//      `stages.assert_praxis_git_sha` in `web-repl/bootstrap/stages.py` for
//      the reference implementation and
//      `web-repl/tests/test_d1_praxis_git_sha.py` for the negative test
//      proving it, including the asymmetric dev/real case the wheel spec's
//      arm (4b) calls out by name.
//   5. A missing pong (no shell present, or a shell that never answers) is
//      the bootstrap's problem to time out on -- this file only ever
//      responds, it never initiates, and it does not implement a timeout.
(function () {
  "use strict";

  var CHANNEL_NAME = "praxis_repl";
  var PING_TYPE = "praxis:shell-ping";
  var PONG_TYPE = "praxis:shell-pong";

  if (typeof window.PRAXIS_GIT_SHA === "undefined") {
    // inject_shell.py did not run (or ran against a different file than the
    // one actually served). Fail loud in the console instead of quietly
    // answering every ping with "undefined", which would make D1 fail in a
    // confusing way instead of a clear one.
    console.error(
      "praxis-shell.js: window.PRAXIS_GIT_SHA is not set -- " +
        "inject_shell.py (or inject_shell.py --dev) must run against this " +
        "page before it is served."
    );
  }

  if (typeof BroadcastChannel === "undefined") {
    console.error(
      "praxis-shell.js: BroadcastChannel is unavailable in this context -- " +
        "the D1 praxis:shell-ping/pong handshake cannot run, so the boot " +
        "will not receive a shell-injected praxis_git_sha to compare " +
        "against and D1 whole-deployment-staleness detection is inert."
    );
    return;
  }

  var channel = new BroadcastChannel(CHANNEL_NAME);
  channel.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || data.type !== PING_TYPE) {
      return;
    }
    channel.postMessage({
      type: PONG_TYPE,
      praxis_git_sha: window.PRAXIS_GIT_SHA,
    });
  });

  // Exposed for manual/dev-console probing and for a future Playwright e2e
  // test to assert against without needing a full Pyodide boot.
  window.__praxisShell = {
    channelName: CHANNEL_NAME,
    pingType: PING_TYPE,
    pongType: PONG_TYPE,
    getPraxisGitSha: function () {
      return window.PRAXIS_GIT_SHA;
    },
  };
})();

// ---------------------------------------------------------------------
// T08 -- legacy IndexedDB migration (ADR Sec 5.5, amended by GATE G2;
// standalone spec T08). ORDERING IS THE DECISION: this code and the
// jupyter-lite.json three-key pin (contentsStorageName / settingsStorageName
// / workspacesStorageName) must land in the SAME commit as any served-path
// change -- see this file's own module docstring is not the place for that
// constraint, the ADR is; this comment exists to point there.
//
// WHAT this migrates, and why three keys and not one: GATE G2 spike S-C
// proved BY CONTENT that pinning `contentsStorageName` genuinely overrides
// JupyterLite's IndexedDB store name (mount A wrote shared.txt, mount B read
// it back byte-for-byte), but it also found a THIRD independent read site
// the original two-key recipe missed: `LiteWorkspaceManager.activate` reads
// `workspacesStorageName` on its own, defaulting to the baseUrl-derived
// name if unset, exactly like `contentsStorageName` and `settingsStorageName`
// do. Pinning only two of the three keys left orphaned per-baseUrl
// `JupyterLite Storage - ${baseUrl}` workspace databases behind --
// `store_enumeration_clean=false`. All three pinned together is what
// produced `store_enumeration_clean=true` in the spike (see
// .praxia/docs/research/260817_g2-spike-battery-verdict.md, criterion
// G2-4). This migration therefore copies all three categories: notebooks
// AND settings AND workspaces.
//
// Verified BY CONTENT (not by database name -- see this file's own dev
// notes / the sprint report for the probe) against the ACTUAL bundled
// JupyterLite build (0.8.1, this repo's `dist/build/*.js`): each legacy
// per-baseUrl `JupyterLite Storage - ${baseUrl}` database is a single
// IndexedDB database holding several object stores, one per localforage
// "instance" JupyterLite creates against it:
//   - "files"       (BrowserStorageDrive: notebooks/files content)
//   - "counters"    (BrowserStorageDrive: filename-suffix counters)
//   - "checkpoints" (BrowserStorageDrive: checkpoint history)
//   - "settings"    (Settings: user settings)
//   - "statedb"     (LiteWorkspaceManager -- inherits IndexedDBDataConnector's
//                     default store name; NOT literally named "workspaces"
//                     in the on-disk schema, confirmed by reading the
//                     unminified class hierarchy in dist/build/981.*.js)
// Each store holds plain out-of-line-keyed entries (object store created
// with no keyPath, matching `store.keyPath === null` observed on a real
// "files" record written through the actual app's `serviceManager.contents`
// API) -- so a raw `indexedDB` copy (no localforage dependency vendored
// into this shell) round-trips correctly, confirmed by content in this
// sprint's probe (write via the real app, read back the identical bytes
// through the pinned store).
//
// STILL OPEN, reported honestly rather than silently assumed solved: this
// script runs synchronously as early as this shell tag allows (before the
// `<script id="jupyter-lite-main">` preload / dynamic `import()` of
// config-utils.js that starts the real app), but the migration ITSELF is
// async (IndexedDB has no synchronous API). Nothing in this build currently
// makes the JupyterLite app's own boot AWAIT `window.__praxisMigrationReady`
// before its content/settings/workspace managers open their pinned stores
// -- gating the generated `lab/index.html`'s own boilerplate script block
// behind that promise is called out in the spec as a still-open question
// (Q2: "gate the main bundle behind the migration promise") and is NOT
// solved by this change. In practice IndexedDB opens are fast (single-digit
// milliseconds to low tens of ms) against the ~8s Pyodide kernel boot this
// project has already measured, so the race is unlikely to matter for the
// FIRST load in most real sessions -- but "unlikely" is not "verified", and
// this comment exists so that claim is never silently upgraded to "solved".
(function () {
  "use strict";

  var MIGRATED_FLAG = "praxis-repl-migrated";
  var LEGACY_PATTERN = /^JupyterLite Storage - /;
  var LEGACY_PREFIX = "JupyterLite Storage - ";
  var BACKUP_PREFIX = "praxis-repl-legacy-backup - ";

  // Known legacy store name -> pinned destination (database, store).
  // Any store name not in this table is copied into the contents database
  // under its own name, with a console warning -- better a recoverable
  // surprise than silently dropped data.
  var STORE_DESTINATIONS = {
    files: { db: "praxis-repl-contents", store: "files" },
    counters: { db: "praxis-repl-contents", store: "counters" },
    checkpoints: { db: "praxis-repl-contents", store: "checkpoints" },
    settings: { db: "praxis-repl-settings", store: "settings" },
    statedb: { db: "praxis-repl-workspaces", store: "statedb" },
  };

  function openDb(name, version, upgradeFn) {
    return new Promise(function (resolve, reject) {
      var req = version ? indexedDB.open(name, version) : indexedDB.open(name);
      req.onupgradeneeded = function (event) {
        if (upgradeFn) {
          upgradeFn(req.result, event);
        }
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
      req.onerror = function () {
        reject(req.error);
      };
      req.onblocked = function () {
        console.warn(
          "praxis-shell.js migration: indexedDB.open('" +
            name +
            "') blocked by another open connection (a concurrent tab or " +
            "an already-booted app instance holding an older version open)."
        );
      };
    });
  }

  function readAllEntries(db, storeName) {
    return new Promise(function (resolve, reject) {
      var tx = db.transaction(storeName, "readonly");
      var store = tx.objectStore(storeName);
      var keysReq = store.getAllKeys();
      var valsReq = store.getAll();
      var keys, vals;
      function maybeResolve() {
        if (keys !== undefined && vals !== undefined) {
          var entries = [];
          for (var i = 0; i < keys.length; i++) {
            entries.push([keys[i], vals[i]]);
          }
          resolve(entries);
        }
      }
      keysReq.onsuccess = function () {
        keys = keysReq.result;
        maybeResolve();
      };
      valsReq.onsuccess = function () {
        vals = valsReq.result;
        maybeResolve();
      };
      tx.onerror = function () {
        reject(tx.error);
      };
    });
  }

  // Ensure *dbName* has an object store named *storeName*, bumping the
  // database version to create it if it is missing -- mirrors how
  // localforage's own IndexedDB driver adds stores to a shared database on
  // demand, so the app's later `createInstance({name: dbName, storeName:
  // storeName})` opens the identical structure this creates.
  function ensureStore(dbName, storeName) {
    return openDb(dbName).then(function (db) {
      if (db.objectStoreNames.contains(storeName)) {
        return db;
      }
      var nextVersion = db.version + 1;
      db.close();
      return openDb(dbName, nextVersion, function (upgradingDb) {
        if (!upgradingDb.objectStoreNames.contains(storeName)) {
          upgradingDb.createObjectStore(storeName);
        }
      });
    });
  }

  // Copy *entries* into *storeName*, skipping any key that already exists
  // there -- "never overwrite" (spec T08). Best-effort per key: one bad
  // write does not abort the whole migration.
  function writeEntriesIfAbsent(db, storeName, entries) {
    return new Promise(function (resolve, reject) {
      if (entries.length === 0) {
        resolve(0);
        return;
      }
      var tx = db.transaction(storeName, "readwrite");
      var store = tx.objectStore(storeName);
      var copied = 0;
      var pending = entries.length;
      tx.onerror = function () {
        reject(tx.error);
      };
      entries.forEach(function (pair) {
        var key = pair[0];
        var value = pair[1];
        var getReq = store.get(key);
        getReq.onsuccess = function () {
          if (getReq.result === undefined) {
            var putReq = store.put(value, key);
            putReq.onsuccess = function () {
              copied++;
              settle();
            };
            putReq.onerror = function () {
              console.warn(
                "praxis-shell.js migration: failed to write key",
                key,
                "into",
                storeName,
                putReq.error
              );
              settle();
            };
          } else {
            settle();
          }
        };
        getReq.onerror = function () {
          settle();
        };
        function settle() {
          pending--;
          if (pending === 0) {
            resolve(copied);
          }
        }
      });
    });
  }

  function readAllStores(db, storeNames) {
    var out = {};
    var chain = Promise.resolve();
    storeNames.forEach(function (sn) {
      chain = chain
        .then(function () {
          return readAllEntries(db, sn);
        })
        .then(function (entries) {
          out[sn] = entries;
        });
    });
    return chain.then(function () {
      return out;
    });
  }

  // IndexedDB has no rename primitive. To satisfy BOTH "no database
  // matching the legacy pattern survives" (store_enumeration_clean) and
  // "do not delete the legacy data -- leave it as a recovery path" (spec
  // T08), copy the legacy database's full structure (every object store,
  // every entry) into a NEW database under a non-legacy-pattern backup
  // name, then delete the original legacy-named database. The bytes
  // survive; the name that store_enumeration_clean greps for does not.
  function renameToBackup(oldName, newName) {
    var srcDb;
    return openDb(oldName)
      .then(function (db) {
        srcDb = db;
        var storeNames = Array.prototype.slice.call(db.objectStoreNames);
        return readAllStores(db, storeNames).then(function (perStore) {
          return { storeNames: storeNames, perStore: perStore };
        });
      })
      .then(function (data) {
        srcDb.close();
        if (data.storeNames.length === 0) {
          return Promise.resolve();
        }
        return openDb(newName, 1, function (newDb) {
          data.storeNames.forEach(function (sn) {
            if (!newDb.objectStoreNames.contains(sn)) {
              newDb.createObjectStore(sn);
            }
          });
        }).then(function (newDb) {
          return new Promise(function (resolve, reject) {
            var tx = newDb.transaction(data.storeNames, "readwrite");
            data.storeNames.forEach(function (sn) {
              var store = tx.objectStore(sn);
              data.perStore[sn].forEach(function (pair) {
                store.put(pair[1], pair[0]);
              });
            });
            tx.oncomplete = function () {
              newDb.close();
              resolve();
            };
            tx.onerror = function () {
              reject(tx.error);
            };
          });
        });
      })
      .then(function () {
        return new Promise(function (resolve, reject) {
          var req = indexedDB.deleteDatabase(oldName);
          req.onsuccess = function () {
            resolve();
          };
          req.onerror = function () {
            reject(req.error);
          };
          req.onblocked = function () {
            console.warn(
              "praxis-shell.js migration: deleteDatabase('" +
                oldName +
                "') blocked by another open connection -- the legacy " +
                "database will not disappear from indexedDB.databases() " +
                "until that connection closes."
            );
          };
        });
      });
  }

  async function runMigration() {
    if (typeof indexedDB === "undefined") {
      console.warn("praxis-shell.js: indexedDB is unavailable -- skipping legacy storage migration.");
      return { ran: false, reason: "indexedDB unavailable" };
    }
    if (localStorage.getItem(MIGRATED_FLAG) === "1") {
      return { ran: false, reason: "already migrated" };
    }
    if (typeof indexedDB.databases !== "function") {
      console.warn(
        "praxis-shell.js: indexedDB.databases() is unavailable in this " +
          "browser -- cannot enumerate legacy stores, skipping migration."
      );
      return { ran: false, reason: "indexedDB.databases unavailable" };
    }

    var allDbs = await indexedDB.databases();
    var legacy = allDbs.filter(function (d) {
      return LEGACY_PATTERN.test(d.name);
    });

    var summary = { legacyDatabases: legacy.map(function (d) { return d.name; }), copiedEntries: 0, stores: {} };

    for (var i = 0; i < legacy.length; i++) {
      var name = legacy[i].name;
      var db = await openDb(name);
      var storeNames = Array.prototype.slice.call(db.objectStoreNames);
      for (var j = 0; j < storeNames.length; j++) {
        var sn = storeNames[j];
        var dest = STORE_DESTINATIONS[sn];
        if (!dest) {
          console.warn(
            "praxis-shell.js migration: unrecognized legacy store '" +
              sn +
              "' in " +
              name +
              "; defaulting to the contents database under its own name."
          );
          dest = { db: "praxis-repl-contents", store: sn };
        }
        var entries = await readAllEntries(db, sn);
        var destDb = await ensureStore(dest.db, dest.store);
        var copied = await writeEntriesIfAbsent(destDb, dest.store, entries);
        destDb.close();
        summary.copiedEntries += copied;
        summary.stores[name + "::" + sn] = {
          entries: entries.length,
          copied: copied,
          destination: dest.db + "/" + dest.store,
        };
      }
      db.close();
      var backupName = BACKUP_PREFIX + name.slice(LEGACY_PREFIX.length);
      await renameToBackup(name, backupName);
    }

    localStorage.setItem(MIGRATED_FLAG, "1");
    return { ran: true, summary: summary };
  }

  window.__praxisMigration = {
    run: runMigration,
    STORE_DESTINATIONS: STORE_DESTINATIONS,
    LEGACY_PATTERN: LEGACY_PATTERN,
    MIGRATED_FLAG: MIGRATED_FLAG,
  };

  // Fire immediately -- as early as this synchronous shell script allows.
  // See the header comment above for the still-open boot-ordering caveat:
  // nothing yet forces the JupyterLite app to await this promise before its
  // own stores open.
  window.__praxisMigrationReady = runMigration().catch(function (err) {
    console.error("praxis-shell.js: legacy storage migration failed:", err);
    throw err;
  });
})();

// ---------------------------------------------------------------------
// T6 -- REPL persistence ladder loader (backlog #4296, spec
// .praxia/docs/specs/260922_repl-persistence-ladder.md D2, D5, the module
// plan's praxis-shell.js row, and T6). This is the ONLY change this spec
// makes to this file: one appended IIFE, confining the whole persistence
// feature's footprint here to this block so a later P5.6 merge (D2) stays
// trivial. The two IIFEs above are untouched.
//
// `document.currentScript` is captured SYNCHRONOUSLY, as the very first
// statement -- it reads `null` from inside any async callback (including a
// `.then()`), so capturing it any later would break the relative
// `persistence/panel.js` URL resolution below. Persistence only ever mounts
// on the `lab/` entry (D2: "the repl/ entry and the other entries get no
// chip"); every other entry returns immediately. A failed dynamic import or
// mount is logged and never breaks the shell -- the REPL keeps working
// without persistence (see the risk table's `import()`/`currentScript` row).
(function () {
  "use strict";

  var thisScript = document.currentScript;
  if (!/\/lab\/(index\.html)?$/.test(location.pathname)) {
    return;
  }
  if (!thisScript || !thisScript.src) {
    console.error("praxis-shell.js: persistence loader could not resolve its own script src.");
    return;
  }

  import(new URL("persistence/panel.js", thisScript.src).href)
    .then(function (mod) {
      return mod.mount(window);
    })
    .catch(function (err) {
      console.error("praxis-shell.js: failed to load/mount the persistence panel:", err);
    });
})();

---
title: 'REPL persistence ladder: L1 storage.persist(), L2 FSA working folder, L3 export/import, first-save gate (backlog #4296, plan P5.8)'
description: Spec for making REPL notebooks durable beyond best-effort IndexedDB. The design stays correct whatever the browser decides on persist() and FSA permission, so it does not wait on the U16/U17 spikes.
status: active
task_id: 260922_repl-persistence
date: '260922'
backlog: 4296
adversarial_review: 'round1 challenger REVISE / defender REVISE -> revised 260922 (Revision 1, A-1..A-11); round2 challenge (260922_repl-persistence_spec-challenge-r2): round-1 blockers CLOSED, 3 new MAJORs -> revised 260922 (Revision 2, B-1..B-11)'
---
# REPL persistence ladder (backlog #4296, plan P5.8)

## Overview

Today a REPL notebook lives only in best-effort IndexedDB (`praxis-repl-contents`). The
browser may evict it, and "Clear Browser Data" wipes it. The repo never calls
`navigator.storage.persist()`: zero grep hits under `web-repl/`, and the same for
`showDirectoryPicker`. This spec adds three layers of durability and one disclosure
point:

- **L1**: ask the browser to exempt our storage from eviction.
- **L2**: mirror every save into a real folder on disk (File System Access, "FSA").
- **L3**: export and import individual files.
- **First-save gate**: the first explicit save tells the user where their work actually lives.
- **Tier indicator**: always visible, and it never claims more durability than the browser actually granted.

Sources: plan `.praxia/docs/plans/260817_praxis-repl-refocus-execution-plan.md` row P5.8
(line 425), the test-design traps (lines 429-434), and U16/U17 (lines 655-656). Prior art
is `.praxia/docs/specs/260817_spec-web-repl-extraction.md` R18-R21 / T11-T13 (lines
177-187, 281-295). This spec supersedes those entries where the two differ; each
difference is called out below.

---

## 1. Decisions (read first)

### D1. U16 and U17 are resolved by design, not by waiting

The feature has to be correct under **every** answer the browser can give. The design
therefore never *assumes* a grant. It *reads* the browser's answer, displays it, and
branches on it:

| Browser answer | Behaviour | Tier shown |
|---|---|---|
| `persisted()` / `persist()` → `true` | "Browser storage protected" | `L1` (unless L2 is active) |
| `persist()` → `false` | "Browser may clear this storage". The button stays available as "Ask again". | `L0` |
| `navigator.storage.persist` absent | L1 row reads "not available in this browser" | `L0` |
| Stored folder handle, `queryPermission({mode:"readwrite"})` → `"granted"`, pending set empty | Mirror active immediately, no prompt | `L2` |
| Stored handle, `queryPermission` → `"prompt"` or `"denied"` | Mirror paused. Saves still reach IndexedDB. Their paths go into the **pending set**, which is persisted in IndexedDB (`praxis-repl-persistence`, key `pending-paths`) so it survives a reload. A **Reconnect folder** button shows. | `L2-paused` |
| **Handle bound AND permission `"granted"`** (reached at init, or by a Reconnect click → `"granted"`), with a non-empty pending set | The pending set is flushed to disk through the mirror chain, **skipping excluded paths**. The flush is triggered by this condition, **not** by the tier: L2 requires an empty pending set, so a trigger on "tier becomes L2" could never fire. While the flush drains, the tier reads `L2-syncing` ("Folder: <name> (syncing N)"). Each path leaves the pending set only after its write succeeds, and the tier becomes `L2` when the set is empty. | `L2-syncing` → `L2` |
| Reconnect click, `requestPermission` → not granted | Stays paused. Offers "Choose a folder again". | `L2-paused` |
| A mirror write throws a **per-path** error. Only a `TypeError` counts here (Chromium's invalid-name rejection is one), and only when thrown by `getFileHandle`, `getDirectoryHandle`, `createWritable` or `write` for that path. | Only that path goes into the **excluded set** with reason "name not allowed on disk", and it is listed in the panel. The mirror does **not** pause. | `L2`, chip reads "(N not mirrored)" |
| A write throws `NotAllowedError` or `SecurityError` (permission lapsed), or any other unclassified error (for example `QuotaExceededError`) | The path stays in or joins the pending set, the error text shows, and the mirror pauses. **Reconnect folder** is offered: it calls `requestPermission`, which returns immediately if permission is already granted, and then re-runs the flush. | `L2-paused` |
| **Handle-level failure that is not about permission**: `NotFoundError` or `InvalidStateError` on the root handle (the folder was deleted or moved), including at init | The path stays pending and the mirror pauses with the text "Folder unavailable". The panel offers **Choose a folder again** and **not** Reconnect, so the user cannot get into a Reconnect loop that can never succeed. | `L2-paused` |
| Bulk sync finds a disk copy whose bytes differ from the drive copy | The path goes into the excluded set with reason "differs on disk". The per-save mirror **skips** it, and the panel offers a per-file **Replace disk copy** action (D7). | `L2`, chip reads "(N not mirrored)" |

**Binding-scoped state.** Four keys live in the `praxis-repl-persistence` store:
`working-folder` (the handle), `pending-paths`, `excluded-paths` (a map from path to
reason) and `mirrored-paths` (D7). The last three are all scoped to the **current
binding**.

On **any** successful choose, the new handle is stored and the three sets are cleared
in **one IndexedDB transaction**, before bulk sync is queued. "Any successful choose"
covers:
- the panel's Choose working folder button
- the modal's Choose working folder button
- "Choose a folder again" after a denied Reconnect or a folder-unavailable failure

Bulk sync then supersedes any flush for the old binding. Every queued chain job
captures a binding generation number, and jobs from an older generation are dropped
without writing. Nothing learned about folder A can leak into folder B.

**Honesty invariant:**
- The tier shows `L1` only after the browser returned `true`.
- It shows `L2` only if all of these hold:
  - a handle is bound
  - permission is `"granted"`
  - the pending set is empty; while it drains, the tier is `L2-syncing`, never `L2`
  - the last write to every **mirrorable** (non-excluded) path succeeded
- Excluded paths never count as mirrored. Their number is always visible on the chip
  ("Folder: <name> (N not mirrored)") and is exposed as `data-praxis-excluded="N"`.
- A denial is a supported state, not an error.

Consequence for U16: whether real users are granted `persist()` decides how often users
see `L1` versus `L0`. It changes nothing about correctness.

Consequence for U17: whether the FSA permission survives a browser restart decides how
often users click **Reconnect**. It changes nothing about correctness.

Both remain real questions about how good the UX is. They are listed as human
follow-ups in section 9 and are deliberately **not** acceptance criteria.

### D2. The "after P5.6" ordering is wave scheduling, not a technical dependency

P5.6 is "`praxis-shell.js` — device dialog, gesture carrier, ping/pong, error banner, tier
indicator. BLOCKED ON G2.5". Taking its pieces one at a time:

- **Ping/pong** already shipped. See `web-repl/shell/praxis-shell.js:54-105`.
- **Device dialog and gesture carrier.** These exist to carry a *kernel-originated*
  `requestDevice` request (worker → BroadcastChannel → main-thread click) into a live
  user-activation window. Persistence gestures start from **our own DOM buttons in the
  main page**. There is no kernel hop and no BroadcastChannel, so nothing here needs a
  carrier. The persistence module also never touches `navigator.usb`, `navigator.hid`
  or `navigator.serial`.
- **The "tier indicator"** is the *storage* tier from prior-art R18 (`[data-praxis-tier]`,
  L0/L1/L2). It belongs to persistence. **This spec takes it over.** P5.6 keeps the
  device dialog, gesture carrier and error banner.
- **P5.7** (`check_gesture_invariant.py`) does not exist yet. Its absence is not a
  blocker: this spec creates the checker with a call list that P5.7 can extend (T5).

The only real coupling is that both P5.6 and this work edit `praxis-shell.js`. This spec
confines its change there to one appended loader IIFE of about 15 lines, so a later P5.6
merge is trivial. **Verdict: #4296 can proceed now, while S-E (#4293) is still blocked.**
The plan's P5.6 row should drop "tier indicator". That plan edit is for the orchestrator
and is not a fixer task.

### D3. L3 means native JupyterLab Download/Upload, verified by content. No new export code.

The runtime is full JupyterLab (`web-repl/jupyter-lite.json:5` `appUrl: ./lab`), and only
`announcements` is disabled (`:10-12`). The stock file-browser **Download** and **Upload**
controls are therefore present. Prior-art T13 says the stock commands are in the bundle
and that moving to `lab/` "makes the stock commands reachable for free".

The spec adds **no** praxis export or import control. Instead, AC-12 proves by content
that Download produces the drive's bytes and that Upload lands a file whose bytes can be
read back.

If AC-12 shows native Download is broken under JupyterLite 0.8.1, contingent task T10
adds one "Download current file" button to the panel. That button uses `contents.get`,
then a Blob, then an anchor download, fired from our click handler.

Not built (YAGNI):
- whole-workspace zip export
- `showSaveFilePicker`

L2 plus "Restore from folder" already provides the whole-workspace durable copy on
Chromium.

### D4. First-save gate: concrete definition, and a deliberate deviation from prior-art R20

- **Trigger.** The first *explicit* user save in a browser profile.
  - **Payload.** Lumino's `CommandRegistry.commandExecuted` signal emits
    `(sender, evt)`, where `evt` is a `CommandRegistry.ICommandExecutedArgs`:
    `{ id: string, args: ReadonlyPartialJSONObject, result: Promise<any> }`. The
    handler reads only `evt.id` and `evt.result`. The command's own arguments,
    `evt.args`, are ignored.
  - **Command ids.** An explicit save is an emission whose `evt.id` is one of
    `docmanager:save`, `docmanager:save-as` or `docmanager:save-all`
    (Ctrl/Cmd+S, File › Save / Save As / Save All).
  - **Wait for the result.** Lumino emits `commandExecuted` **immediately**, carrying a
    still-pending `evt.result` promise, and it emits on rejection as well. The panel
    therefore never acts on the emission itself:
    `commands.commandExecuted.connect((_, evt) => { if (SAVE_IDS.has(evt.id)) Promise.resolve(evt.result).then(() => core.handleExplicitSave(), () => {}); })`.
    The gate opens only once the save command has **resolved**. A rejected or cancelled
    save opens nothing.
  - **Untitled files.** With JupyterLab's rename-untitled-on-save behaviour, the command's
    result resolves only after its rename dialog is answered and the save completes. The
    gate modal therefore comes *after* that dialog; AC-11 covers this case.
  - **Conditions.** Even after an explicit save resolves, the gate fires only when both
    of these hold:
    - no working folder is connected (tier is not `L2`)
    - the acknowledgement flag is unset (`localStorage["praxis-repl-persistence-ack"]`)
  - **Out of scope.** These saves never trigger the gate:
    - **Autosave.** It calls the document context directly and not a command.
    - **The "Save" button in JupyterLab's unsaved-changes dialog shown when closing a
      tab.** That path also bypasses the three commands, so the gate misses it. The next
      explicit save still fires the gate.
  - **Why this matters.** The existing lab-entry gates (`--notebook-check`,
    `--autosetup-fault-check`, `--restart-check`) never run any of the three commands, so
    a modal cannot appear mid-gate.
- **What the user sees.** A modal `<dialog>` opened with `showModal()`, `role="dialog"`,
  with focus moved inside it.
  - **Escape and backdrop clicks do not close it.** The `cancel` event is
    `preventDefault`ed. Chromium's CloseWatcher makes a **second** consecutive Escape
    non-cancelable, so preventing `cancel` alone is not enough. The dialog therefore also
    listens for `close`: if no choice has been recorded, it calls `showModal()` again
    immediately and restores focus inside.
  - **Text.** "Saved — but only inside this browser. Browsers can clear this storage."
  - **Buttons.** It offers up to three:
    1. **Choose working folder**: shown only when FSA is supported. It calls the
       injected `pickDirectory` (which is `showDirectoryPicker`).
    2. **Protect browser storage**: calls `persist()`.
    3. **Keep in this browser only**: sets the ack flag to `"browser-only"`.
  - **Resolution.** Choosing a folder successfully resolves the gate. **Any** successful
    choose sets the ack to `"folder"`: from the modal, from the panel's Choose working
    folder, or from "Choose a folder again". So a user who binds a folder through the
    panel before ever saving never sees the modal. Later loss of permission does not
    re-arm it either: a paused folder is surfaced by the chip and the Reconnect flow, not
    by the gate. Protecting storage updates the tier but leaves the dialog open, because
    L1 does not survive "Clear site data". The user still has to choose 1 or 3.
- **What it prevents.** A user reaching a second session believing "saved" means "safe".
  It is a **disclosure gate, not a save gate.**
- **Deviation from R20** ("the save proceeds only after the modal is resolved"). The modal
  opens only after the save command's result promise has **resolved**, so on the normal
  path the IndexedDB write has landed before the user is asked anything. AC-11 checks this
  by content while the modal is open. The gate never holds data. Holding a save hostage
  to a modal would do two bad things:
  - It would turn the gate into a data-loss path: edits wait in memory while the modal
    sits unanswered, and closing the tab loses them.
  - It would require monkey-patching `contents.save`, which is shared with autosave.

  The prior spec's anti-softening concern (R20 "not a passive banner") is kept: the modal
  is blocking for *interaction* and needs an explicit choice. It is just not blocking for
  *data*. Owner confirmation is OQ-1.
- The ack flag sits in localStorage, so a site-data wipe clears it together with the
  data. The gate then re-discloses on the next first save, which is the correct behaviour.

### D5. Browser support: feature detection only, no user-agent sniffing

- `fsaSupported = window.isSecureContext && typeof window.showDirectoryPicker === "function"`.
  In practice this is Chromium only (Chrome/Edge/Opera), which is already the product's
  browser for device access.
- `persistSupported = typeof navigator.storage?.persist === "function"`. This covers
  Chromium, Firefox and Safari 17+.
- **Non-Chromium behaviour.** L2 controls are **not rendered at all**: there are no
  disabled buttons and no dead ends. The panel reads: "Working folders need a
  Chromium-based browser (Chrome, Edge). Use the file browser's Download to keep copies."
  L1, the first-save gate (buttons 2 and 3 only), the tier indicator and native L3 work
  unchanged. The REPL itself keeps working. Persistence degrades, it does not block.

### D6. The gesture invariant, and how it is tested at three levels

**Invariant:** each call that needs a user gesture must sit inside a synchronous,
non-`async` function named `on<Something>Click`. Between that function's opening brace
and the call there must be **no `await`, no `.then(`, and no call to anything
asynchronous**. Synchronous conditionals that read cached state are allowed: for example,
`if (state.permission !== "granted")` choosing whether to call `requestPermission`, or
`if (!pickDirectory) return`. The calls covered are:
- `storage.persist()`
- `pickDirectory(...)`
- `handle.requestPermission()`

**Why `pickDirectory` is in the list.** `core.js` never names `showDirectoryPicker`. It
receives it through DI as `pickDirectory`. `panel.js` injects
`window.showDirectoryPicker.bind(window)`, which is a reference and not a call, so no
literal gesture call appears anywhere outside core's `on*Click` functions. If
`pickDirectory(` were left out of the checker, the checker would be falsely green.

The panel invokes these functions synchronously from `addEventListener("click", …)`.
Everything asynchronous comes *after* the call, chained on its returned promise.

This is the same rule as P5.7 ("zero `await` between the click handler's opening brace
and the first `requestDevice`").

| Level | What it proves | How |
|---|---|---|
| Static (T5) | No `await`, `.then(` or `async` token precedes a gesture call in source, and the call sits in a named `on*Click` non-async function | `web-repl/scripts/check_gesture_invariant.py` over `web-repl/shell/persistence/*.js`. Negative fixtures prove the check can fail. A call to some *other* async helper before the gesture call is beyond a token scan; the Unit level catches it. |
| Unit (T2) | The call happens **synchronously** inside the handler invocation | bun tests with a fake `activation` flag. The harness sets it `true`, calls `onXClick()`, and sets it `false` synchronously on return. Each fake API records the flag at call time. A deliberately async variant must record `false`, which is the discrimination control. |
| Browser (T8a, AC-9) | The call is reached from a **real** `page.click()` (trap 2: never `dispatchEvent`), inside click dispatch | An init script wraps each API and records `navigator.userActivation.isActive` **and** an `inClickDispatch` flag. The flag is set by a window capture-phase click listener and cleared by a window bubble-phase listener. |

`isActive` alone is not proof of "no await". Chromium's transient activation lasts
seconds, so a call made after a short `await` would still record `true`. That is why the
browser level also records `inClickDispatch`, and why the unit and static levels exist.

### D7. No blind overwrite of a disk file we did not write, and one ordered write path

**Scope of the guarantee.** The mirror never overwrites a disk file unless it wrote or
byte-verified that file under the **current** binding (`mirrored-paths`), or the user
clicked **Replace disk copy** for it.

**One known gap, accepted.** Suppose a disk file is already in `mirrored-paths` and then
gets edited **outside the browser**, for example in a text editor. The next save of that
path in the REPL overwrites the edit. Detecting this would need per-path `lastModified`
tracking, which the round-1 adjudication declined. OQ-4 records it as the owner's call.

- **Bulk sync compares bytes.** On choosing a folder, bulk sync walks every drive file
  and treats each path one of three ways:
  - **Absent on disk:** written, then added to `mirrored-paths`.
  - **Present with identical bytes:** added to `mirrored-paths`.
  - **Present with different bytes:** added to the excluded set with reason
    "differs on disk" (D1).
- **The per-save mirror skips excluded paths**, and so does the pending-set flush.
- **First writes are checked too.** A path not in `mirrored-paths` gets the same byte
  comparison before its first write in this binding, and so does a new drive file saved
  after bulk sync. If a differing disk copy exists, the path is excluded, not
  overwritten. A successful first write adds the path to `mirrored-paths`.
  - `mirrored-paths` is scoped to the current binding and is cleared on every successful
    choose (D1).
  - There is no per-path `lastModified` tracking and there are no `.conflict` files.
- **Deletes and renames drop mirrored status.** A `contents.fileChanged` event of type
  `"delete"` removes `oldValue.path` from `mirrored-paths`. A `"rename"` event removes
  `oldValue.path`, and the new path is not added. The disk copy is not deleted or
  renamed; that is still a non-goal. So if a file of the same name is later created in
  the drive, it goes through the first-write byte check instead of blindly overwriting
  the stale disk copy.
- **Replace disk copy.** The panel lists each excluded path with its reason. Paths with
  reason "differs on disk" get a per-file **Replace disk copy** button, which calls
  `core.onReplaceDiskCopyClick(path)`. That removes the exclusion, writes the drive copy
  through the mirror chain, and on success adds the path to `mirrored-paths`. The button
  is shown only while permission is `"granted"`, so it needs no gesture-bound call; it
  is still a real click.
  - "Name not allowed on disk" paths have no action. They are listed so the user knows
    to rename them.
- **One ordered write path.** Every write to the folder goes through a single promise
  chain inside core. That covers per-save mirroring, pending flush, bulk sync, and
  Replace. Each job carries the binding generation it was queued under, and a job whose
  generation no longer matches the current binding is dropped without writing (D1). Each queued write reads the **current** content with
  `contents.get(path, {content: true})` when it runs, not when it was queued. Two
  consequences:
  - Rapid successive saves can never land out of order.
  - Chunked uploads, which emit `fileChanged` once per chunk, need no chunk filtering:
    the last write reads the final content.
- **Restore.**
  - Restore writes into the drive, never to disk, so it does not use the mirror chain.
  - While a restore runs, its paths are held in an in-memory `restoring` set, and
    `fileChanged` events for those paths are ignored. When restore finishes, restored
    paths are added to `mirrored-paths`, because the disk copy is by definition equal.
  - Restore creates missing parent directories with
    `contents.save(dir, {type: "directory"})` before writing a file.
- **Dot-prefixed entries.** Restore and bulk sync skip any path with a segment beginning
  with `.`, which covers `.ipynb_checkpoints` and OS metadata.
- **No caps and no confirmation prompts** on bulk operations.

---

## 2. Goals / Non-goals

**Goals**
- G1: L1: `persist()` requested only from a click, with the result shown truthfully.
- G2: L2: bind a directory once, keep the handle across reloads, mirror every save
  (including autosave), reconnect with one click after the permission lapses, and
  restore missing files from the folder.
- G3: L3: native Download/Upload proven to work by content.
- G4: First-save disclosure gate (D4) and an always-present tier indicator.
- G5: Correct under every persist/permission outcome (D1) and on non-Chromium browsers (D5).

**Non-goals**
- Bidirectional sync.
- Propagating deletes or renames to the folder. Renamed files are mirrored under the new
  name on their next save, and old copies remain.
- Conflict merging.
- Automatic restore on load.
- Whole-workspace zip export.
- OPFS as a durability tier (it is cleared with site data just like IndexedDB).
- Periodic re-nagging after "Keep in this browser only" (OQ-2).
- A JupyterLab labextension.
- Multi-tab coordination. Two tabs mirror the same saves, and the last write wins.
- Device dialog, gesture carrier, error banner (these stay in P5.6).
- Mounting in any entry other than `lab/`.

---

## 3. User-visible behaviour

1. **Every load of `lab/`.** A small fixed-position chip `#praxis-persistence` appears
   before any save. It renders once `window.jupyterapp` exists and `app.restored` has
   resolved. It carries `data-praxis-tier="L0|L1|L2|L2-syncing|L2-paused"`,
   `data-praxis-excluded="N"`, and a short label:
   - "Browser only" (warning style) for L0
   - "Browser storage protected" for L1
   - "Folder: <name>" for L2, becoming "Folder: <name> (N not mirrored)" in warning style
     when the excluded set is non-empty
   - "Folder: <name> (syncing N)" for L2-syncing
   - "Folder disconnected" (warning style) for L2-paused when permission is needed, or
     "Folder unavailable" when the folder itself is gone (D1)

   It must not intercept pointer events outside its own box. The `repl/` entry and the
   other entries get no chip.
2. **Clicking the chip** toggles a panel with:
   - **L1 row**: status text plus a **Protect browser storage** button (the label becomes
     "Ask again" after a denial). It is hidden when L1 is granted.
   - **L2 row**, FSA supported:
     - **Choose working folder** when no folder is bound.
     - **Reconnect folder** when paused for permission or an unclassified error.
     - **Choose a folder again** instead of Reconnect when the folder is unavailable
       (D1).
     - **Restore from folder** when bound.
     - **Choose a different folder** when bound.
     - A **Not mirrored** list when the excluded set is non-empty: each path with its
       reason, plus **Replace disk copy** for "differs on disk" entries while
       permission is granted.
   - **L2 row**, FSA not supported: the D5 text.
   - **L3 row**: text pointing at the file browser's Download/Upload.
3. **Choosing a folder** (any successful choose) does three things in order:
   - it stores the handle and clears the three binding-scoped sets in one IndexedDB
     transaction, and bumps the binding generation (D1)
   - it sets the ack to `"folder"` (D4)
   - it queues a byte-comparing bulk sync (D7)

   The bulk sync supersedes any flush for the previous binding. Each drive path absent
   on disk is written. Identical copies are left alone. Both of those outcomes add the
   path to `mirrored-paths`. A differing disk copy is **not overwritten**: the path is
   excluded as "differs on disk". The panel shows
   `written N, identical M, not mirrored K (differ on disk)`.
   - After that, every `contents.fileChanged` event of type `"save"` (explicit or
     autosave) queues a write of that one path, unless the path is excluded.
   - A path already in `mirrored-paths` overwrites the folder copy, because that copy is
     our own mirror. A path not yet mirrored gets the D7 first-write byte check.
   - Drive subdirectories become folder subdirectories.
4. **Reload.** The handle, pending set and excluded set are read back from IndexedDB
   `praxis-repl-persistence/handles` (keys `working-folder`, `pending-paths`,
   `excluded-paths`, `mirrored-paths`), and `queryPermission` is called.
   - `"granted"` with an empty pending set gives L2, with no prompt.
   - `"granted"` with a non-empty pending set starts the flush immediately. The tier is
     L2-syncing until the set is empty, then L2.
   - Anything else gives L2-paused.
   - A `NotFoundError` or `InvalidStateError` from the root handle gives L2-paused,
     "Folder unavailable", with Choose a folder again.
5. **Reconnect folder.** `requestPermission({mode:"readwrite"})` is called. On
   `"granted"`, the condition "handle bound AND permission granted" holds, so the
   persisted pending set is flushed, skipping excluded paths. The tier reads L2-syncing
   while the flush drains and L2 once it is empty, and the panel reports the count. The
   pending set includes saves made in earlier sessions before a reload.
6. **Restore from folder.** Every folder file whose path is **absent** from the drive is
   written into the drive, with parent directories created first. Drive files are never
   overwritten, and dot-prefixed paths are skipped. The panel shows
   `restored N, skipped M`. If the cached permission is not `"granted"`, the click calls
   `requestPermission` first; this is its gesture-bound call.
7. **First explicit save**: the modal described in D4.

---

## 4. Module and file plan

New modules live in their own directory so that bun, the staging code and the static
check can all target it, and so that `praxis-shell.js` stays nearly untouched.

| Path | Action | Contents |
|---|---|---|
| `web-repl/shell/persistence/codec.js` | create | `modelToFileBytes(model)` and `fileBytesToModel(path, bytes)`. Notebooks are `JSON.stringify(content, null, 1) + "\n"` and go back via `JSON.parse` for `.ipynb`. Text files are UTF-8. Anything else goes through base64. Decoding uses a fatal UTF-8 `TextDecoder`, and falls back to base64 on failure. `splitDrivePath(path)` rejects `""`, `.` and `..` segments. |
| `web-repl/shell/persistence/core.js` | create | `createPersistence({storage, pickDirectory, handleStore, contents, flags, onChange})`. This is a pure DI state machine with no `window`/`document`/`navigator` references. It exposes `state`, `init()`, `onProtectClick()`, `onChooseFolderClick()` (calls `pickDirectory({mode:"readwrite"})`), `onReconnectClick()`, `onRestoreClick()`, `onReplaceDiskCopyClick(path)`, `onKeepBrowserOnlyClick()`, `handleFileSaved(path)`, `handleFileRemoved(path)` and `handleExplicitSave()`. Tier derivation follows D1, the first-save decision follows D4, and the single write chain, exclusion rules and restore rules follow D7. `pickDirectory` is `null` when FSA is unsupported. `handleStore` persists four keys: `working-folder`, `pending-paths`, `excluded-paths` and `mirrored-paths`. It must expose an atomic `rebind(handle)` that stores the handle and clears the three sets in one transaction (D1). Tiers are `L0`, `L1`, `L2`, `L2-syncing` and `L2-paused`, and the paused state carries a `pauseReason` of `permission`, `folder-unavailable` or `error`. The flush trigger is "handle bound AND permission granted AND pending set non-empty", never a tier transition. |
| `web-repl/shell/persistence/panel.js` | create | Browser glue. It does feature detection (D5) and builds the real adapters:<br>• `navigator.storage`<br>• `pickDirectory = window.showDirectoryPicker.bind(window)` (a reference, not a call)<br>• a raw-IndexedDB key/value store for DB `praxis-repl-persistence`, store `handles`, with `rebind` done as a single `readwrite` transaction; the DB name must not match the migration's `/^JupyterLite Storage - /`<br>• a `contents` adapter over `jupyterapp.serviceManager.contents` (`get`, `save` including `{type:"directory"}`, recursive list)<br>• `localStorage` flags<br>It waits for `window.jupyterapp` and then `app.restored` before rendering anything. It subscribes to `contents.fileChanged`, routing `save` to `handleFileSaved`, and `delete` and `rename` to `handleFileRemoved(oldValue.path)`. It also subscribes to `commands.commandExecuted`, whose payload is `ICommandExecutedArgs {id, args, result}`; it filters on `evt.id` to the three save ids and runs `Promise.resolve(evt.result).then(() => core.handleExplicitSave(), () => {})` (D4). It renders the chip, panel and `<dialog>`; the dialog re-arms itself on `close` when no choice is recorded (D4). Every button listener is `() => core.onXClick(...)`, with nothing before the call. The export is `mount(window)`. |
| `web-repl/shell/persistence/__tests__/fakes.js` | create | Test fakes. A Map-backed nested directory handle, modelled on the pattern at `web-repl/shell/coxswain/__tests__/audit_store.test.js:497-532` and extended with `getDirectoryHandle`, `values()`, and `queryPermission`/`requestPermission` driven by a settable permission state, plus fault injection: throw `TypeError` or `NotAllowedError` on a chosen path, `NotFoundError` on the root, and a "hold" hook that pauses a write mid-flush so a test can read the tier while the flush is running. Also: an in-memory `contents` that supports directories and can emit `fileChanged`, fake `storage`, a flags map, an in-memory `handleStore`, and an `activation` recorder. |
| `web-repl/shell/persistence/__tests__/codec.test.js` | create | Codec round-trip tests. |
| `web-repl/shell/persistence/__tests__/core.test.js` | create | Tests for L1, L2 and the gate, plus gesture synchrony. |
| `web-repl/shell/praxis-shell.js` | modify (append only) | A third IIFE. It captures `document.currentScript` **synchronously**, because `currentScript` is `null` inside async callbacks. It returns unless `location.pathname` matches `/\/lab\/(index\.html)?$/`. Otherwise it runs `import(new URL("persistence/panel.js", script.src).href).then(m => m.mount(window))` and routes a `.catch` to `console.error`. The existing two IIFEs are not touched. The inject block does not change, so `test_default_block_is_byte_identical_to_historical_shape` keeps passing. |
| `web-repl/scripts/build_repl.py` | modify | `stage_shell` also copies `shell/persistence/` to `<out>/shell/persistence/`. It first removes any existing `<out>/shell/persistence/` with `shutil.rmtree`, mirroring `build_repl.py:1069-1070`, so a module deleted from source cannot survive in dist. It then copies with `_copytree_filtered(..., skip=__tests__)`, the same pattern as `stage_coxswain_shell` at `build_repl.py:1071-1077`. `assert_dist_complete` requires `shell/persistence/{core,codec,panel}.js`. |
| `web-repl/scripts/check_gesture_invariant.py` | create | The D6 static check. `GESTURE_CALLS` holds regexes for `\.persist\(`, `pickDirectory\(`, `showDirectoryPicker\(` and `\.requestPermission\(`. `SCAN_ROOTS = [web-repl/shell/persistence]`, excluding `__tests__`. For each call site it asserts four rules: the nearest enclosing function header is a named non-`async` `function`/method; its name matches `^on[A-Z]\w*Click$`; it is not an arrow function; and no `await`, `.then(` or `async` token lies between the header's `{` and the call. Synchronous `if` conditionals are permitted. **Forbidden-string rule (B-11):** no scanned file may contain `__praxis_test_force_prompt`. That test-only switch must live in the smoke harness only and never ship in product code. P5.7 extends both lists. Exit is nonzero, with file:line and the violated rule. Written with argparse and logging. |
| `web-repl/tests/test_check_gesture_invariant.py` | create | Checks that the real tree passes. Also covers six negative fixtures written to `tmp_path`, each of which must fail:<br>1. an `await` before the call<br>2. an `async function`<br>3. a `.then(` before the call<br>4. an arrow function<br>5. a name that is not `on*Click`<br>6. `pickDirectory(` called from a non-`on*Click` function<br>7. a file containing the string `__praxis_test_force_prompt`<br>One positive fixture must pass: a synchronous cached-state conditional before `requestPermission`. |
| `web-repl/tests/test_persistence_staging.py` | create | Three cases:<br>• `stage_shell(tmp)` stages the three modules and no `__tests__`.<br>• A stale `<out>/shell/persistence/old.js` placed before staging is gone afterwards.<br>• `assert_dist_complete` raises when `panel.js` is missing. |
| `scripts/repl_smoke.py` | modify | Adds a `--persistence-check` flag, `run_persistence_check(...)`, a `main()` branch, and an entry in the "nothing to do" list. It uses the `lab/index.html` URL.<br>Each scenario (section 6, T8a/T8b) runs in its **own fresh browser context** with a stated starting state. A reload *within* a scenario keeps that context.<br>`persist()` **and** `persisted()` are both wrapped, calling through.<br>Picker calls are counted on the **Python side** via `page.expose_function("__praxisPickerCalled", ...)`, so the count survives reloads. |
| `.github/workflows/repl.yml` | modify | Changes are split by task:<br>• **T5** adds its pytest line `uv run python -m pytest web-repl/tests/test_check_gesture_invariant.py -q`.<br>• **T7** adds its pytest line `uv run python -m pytest web-repl/tests/test_persistence_staging.py -q`.<br>Each task adds its own line because `test_repl_workflow_covers_tests.py:48-55` fails as soon as an unwired test file exists.<br>• **T9** adds the rest: the build-job step `uv run python scripts/repl_smoke.py --persistence-check --base-path /praxis/`, a step `uv run python web-repl/scripts/check_gesture_invariant.py`, and in the coxswain job a step `bun test web-repl/shell/persistence`. |

Files that must **not** change: `web-repl/jupyter-lite.json`, `web-repl/scripts/inject_shell.py`,
and the two existing IIFEs in `praxis-shell.js`.

---

## 5. Acceptance criteria

The JS unit criteria run with `bun test web-repl/shell/persistence` (call it **[BUN]**).
The browser criteria are the JSON result keys of **[SMOKE]**:
`uv run python scripts/repl_smoke.py --persistence-check --base-path /praxis/`,
which exits 0 only if every key below holds. Locally, [SMOKE] needs
`dangerouslyDisableSandbox: true` and `--chrome-path` (plan section 5.6). CI is
authoritative.

- **AC-1 (L1 logic)** [BUN]:
  - `persisted()` true gives L1; false gives L0.
  - `persist()` resolving `false` gives L0 with "Ask again".
  - Resolving `true` gives L1.
  - A missing `storage` gives "not available".
  - A tier never reads L1 without a `true` from the fake.
- **AC-2 (gesture synchrony)** [BUN]:
  - Each of these records `activation === true` at the fake API call:
    - `onProtectClick`, at `storage.persist`
    - `onChooseFolderClick`, at the injected `pickDirectory`
    - `onReconnectClick`
    - `onRestoreClick`, with cached permission `prompt`. This case lands with **T3**,
      which implements `onRestoreClick`; T2 lands the other three.
  - The control: an `async` wrapper that awaits once before delegating records `false`.
    This proves the fake can discriminate.
- **AC-3 (L2 logic)** [BUN]:
  - **Basic mirroring:**
    - Save while `granted`: file at the nested path, compared by content.
    - Save while `prompt`: no write, path added to the pending set, tier `L2-paused`.
  - **Pending set:**
    - It survives a **new** `createPersistence` instance built over the same
      `handleStore` (the reload analogue).
    - Reconnect granted: pending path written, tier `L2`.
    - `init()` with permission already `granted` and a non-empty pending set also
      flushes it. This is the deadlock regression: the flush must fire even though the
      tier is not yet L2.
    - **Mid-flush tier (B-1):** with the fake's hold hook stopping the first flush write,
      `state.tier === "L2-syncing"` (never `"L2"`) while the pending set is non-empty.
      Releasing the hold gives `"L2"` once it empties. A path leaves the pending set only
      after its write succeeds.
    - The flush skips excluded paths.
  - **Rebind (B-2):**
    - Bind folder A, go paused, save path `p` (now pending), then choose folder B whose
      copy of `p` differs. B's bytes for `p` stay unchanged. `p` is excluded
      "differs on disk" in B. The pending, excluded and mirrored sets from A are gone. No
      A-generation job writes to B.
    - `rebind` clears all three sets in the same `handleStore` call that stores the
      handle.
  - **Delete and rename (B-2):**
    - After `p` is mirrored, `handleFileRemoved(p)` (a drive delete or rename) removes it
      from `mirrored-paths`.
    - A later drive file created at `p` against a differing disk copy is then excluded,
      not overwritten.
  - **Errors (D1, B-9, B-11):**
    - A `TypeError` thrown by the handle's `getFileHandle`, `getDirectoryHandle`,
      `createWritable` or `write` for one path: that path is excluded as
      "name not allowed on disk", the tier stays `L2`, the chip model counts 1 not
      mirrored, and other paths keep mirroring.
    - A `TypeError` from anywhere else, such as a failing `contents.get`: tier
      `L2-paused`, path pending, and the path is **not** excluded.
    - A write throwing `NotAllowedError`: tier `L2-paused`, `pauseReason === "permission"`,
      path pending, Reconnect offered.
    - A `NotFoundError` on the root handle, at init or on write: tier `L2-paused`,
      `pauseReason === "folder-unavailable"`, and the panel model offers
      Choose a folder again and **not** Reconnect.
  - **Mirrored-paths bookkeeping (B-10):** a bulk-sync write, a bulk-sync "identical"
    result, and a successful Replace each add the path to `mirrored-paths`.
  - **Exclusion (D7):**
    - Bulk sync with a differing disk copy leaves the disk bytes unchanged and excludes
      the path as "differs on disk".
    - A later explicit save **and** a later autosave (`handleFileSaved`) of that path
      both leave the disk bytes unchanged.
    - `onReplaceDiskCopyClick(path)` removes the exclusion and writes the drive bytes.
    - A path first saved after bulk sync, whose disk copy already differs, is excluded
      and not overwritten.
  - **Ordering (D7):**
    - Two saves fired back-to-back with different content leave the disk holding the
      **second** content.
    - Three `fileChanged` events for one path (the chunked-upload analogue) end with the
      disk equal to the final `contents.get` content.
  - **Restore:**
    - Writes only drive-absent paths and never overwrites the drive.
    - Creates parent directories through `contents.save(dir, {type:"directory"})` before
      the file.
    - A `fileChanged` fired for a path in the active restore set causes no folder write.
  - **Dot paths:** restore and bulk sync skip dot-prefixed paths.
  - **Validation:** paths with `..`/`.`/empty segments are rejected.
  - **Rehydrate:** a rehydrated handle with `granted` gives L2, and `pickDirectory` is not
    called.
- **AC-4 (first-save gate logic)** [BUN]:
  - `handleExplicitSave()` requests the modal iff tier is not L2 and the ack is unset.
  - `handleFileSaved()` alone (autosave) never requests it.
  - Keep-browser-only sets the ack to `browser-only`.
  - **Any** successful choose sets the ack to `folder` (B-3). Test each source: the
    modal's choose, the panel's `onChooseFolderClick` before any save, and
    Choose a folder again after a denied Reconnect.
  - After a panel choose followed by permission loss (tier `L2-paused`), an explicit
    save requests **no** modal.
  - A second explicit save after the ack requests nothing.
  - `pickDirectory === null` hides the choose option in the modal model.
- **AC-5 (codec)** [BUN]: notebook, UTF-8 text and binary each round-trip by content
  through `modelToFileBytes`, then `fileBytesToModel`.
- **AC-6 (static gesture invariant)**:
  - `uv run python web-repl/scripts/check_gesture_invariant.py` exits 0 on the tree.
  - `uv run python -m pytest web-repl/tests/test_check_gesture_invariant.py -q` passes.
    All 7 negative fixtures must exit nonzero. That includes `pickDirectory(` called
    from a non-`on*Click` function, and a file containing `__praxis_test_force_prompt`.
    The cached-state-conditional positive fixture must exit 0.
  - `! grep -rn '__praxis_test_force_prompt' web-repl/shell/persistence --include='*.js' --exclude-dir=__tests__`
    returns nothing (B-11).
- **AC-7 (staging)**:
  - `uv run python -m pytest web-repl/tests/test_persistence_staging.py -q` passes.
  - After `uv run python web-repl/scripts/build_repl.py --base-path /praxis/`, both
    `test -f web-repl/dist/shell/persistence/panel.js` and
    `! test -e web-repl/dist/shell/persistence/__tests__` succeed.
  - The staging test also proves a stale file in `dist/shell/persistence/` is removed.

Each [SMOKE] scenario below names its task (T8a/T8b) and its starting state. Every
scenario starts in a fresh browser context, so IndexedDB, OPFS and localStorage all start
empty unless the scenario seeds them.

- **AC-8 (indicator, D1)** [SMOKE, T8a, scenario S1: fresh context, no seeding]:
  - `indicator_present_before_save: true`.
  - `initial_tier` equals `"L1"` if the recorded initial `persisted()` returned true,
    else `"L0"`. The value comes from the `persisted()` wrapper's log.
  - `repl_entry_has_chip: false`, from loading `repl/index.html`.
- **AC-9 (real-gesture calls, D6)** [SMOKE, T8a, scenario S2: fresh context with the
  OPFS picker stub, with the drive seeded with `persist-probe.ipynb`. It clicks Protect,
  then Choose working folder. It then sets the
  forced-`prompt` flag, reloads, and clicks Reconnect. No content assertions.]:
  - `gesture_log` has entries for `persist`, `showDirectoryPicker` and `requestPermission`.
  - `picker_calls` (the Python-side count) equals 1.
  - Every entry has `userActivation: true` **and** `inClickDispatch: true`.
  - All interactions use `page.click()`. `dispatchEvent` does not appear in the function.
  - `persist_returned` is recorded, and `tier_after_persist` matches it (L1 iff true).
  - **No assertion on `persist_returned`'s value.**
- **AC-10 (L2 end-to-end, by content)** [SMOKE, T8b].
  - **The picker stub.** `showDirectoryPicker` is replaced by an init-script stub. The
    stub records activation, reports to the Python-side counter, and returns a **real**
    OPFS subdirectory handle:
    `navigator.storage.getDirectory()` → `getDirectoryHandle("praxis-persist-probe", {create:true})`.
  - **The forced-prompt switch.** The init script forces `queryPermission` to return
    `"prompt"` while `localStorage["__praxis_test_force_prompt"] === "1"`, until
    `requestPermission` is called.
  - **Scenario S4.** Fresh context; the drive is seeded with `persist-probe.ipynb`, and
    OPFS starts empty.
    - `mirror_after_choose_matches`: the folder's `persist-probe.ipynb` parses to the
      same cells as `contents.get`.
    - `mirror_after_resave_matches`: true after a second save with changed source.
    - `rehydrated_without_picker`: `picker_calls` stays at 1 across a reload, and the
      tier is `L2`.
  - **Scenario S5 (differs on disk, D7).** Fresh context. Before choosing a folder, OPFS
    `praxis-persist-probe/` is seeded with `persist-probe.ipynb` holding **different**
    content, and the drive is seeded with its own version.
    - `differs_excluded`: after the choose click, `data-praxis-excluded == "1"` and the
      chip text contains "(1 not mirrored)".
    - `differs_disk_untouched_after_save`: after `Control+S` on the drive file, the disk
      bytes are still the seeded bytes.
    - `replace_writes`: after a real click on that path's **Replace disk copy**, the disk
      parses to the drive's cells and `data-praxis-excluded == "0"`.
  - **Scenario S6 (paused, persisted pending set).** Fresh context; the drive is seeded
    with `persist-probe.ipynb`.
    - Bind the folder through the **panel's** Choose working folder. With no save made
      yet, this sets the ack to `folder` (B-3). Then set the forced-prompt flag and
      reload.
    - `tier_on_prompt == "L2-paused"`.
    - `paused_save_not_written`: open the notebook, change a cell, and make an
      **explicit `Control+S`** save. This is not autosave: it is the path that could
      open the gate. The folder bytes stay unchanged.
    - `pending_survives_reload`: reload again with the flag still set, then click
      Reconnect with a real click.
    - `reconnect_flushed_matches`: the folder now equals the save made **before** the
      second reload, compared by content, and the tier ends at `L2`.
    - `gate_never_opened_s6`: `dialog#praxis-persistence-first-save` was never `open` at
      any point in S6. It is polled after every step, including right after the
      Control+S and during the Reconnect flush.
  - **Scenario S7 (restore).** Fresh context with a bound folder. OPFS is seeded with
    `sub/restore-me.ipynb` and a `.hidden` file. The drive holds a
    `persist-probe.ipynb` whose content differs from the disk copy.
    - `restore_matches`: after a real click on Restore, `sub/restore-me.ipynb` is in the
      drive with identical content.
    - `restore_skipped_dotfile`: `.hidden` is absent from the drive.
    - `restore_did_not_overwrite`: the drive's `persist-probe.ipynb` is unchanged.
- **AC-11 (first-save gate)** [SMOKE, T8b].
  - **Scenario S8.** Fresh context; the drive is seeded with `persist-probe.ipynb`.
    - After a real click into the open notebook and `Control+S`: `modal_open: true` and
      `modal_focus_inside: true`.
    - `modal_survives_double_escape: true`: after pressing Escape **twice**, the dialog
      is still `open`, and focus is inside it.
    - `save_landed_before_modal: true`: `contents.get` returns the saved content while
      the modal is open.
    - After the modal's **Choose working folder** real click: `modal_closed: true`.
    - A second `Control+S` gives `modal_reopened: false`.
  - **Scenario S9 (untitled rename).** Fresh context.
    - Create `Untitled.ipynb` via File › New › Notebook, type a marker into the first
      cell, and press `Control+S`.
    - JupyterLab's rename dialog appears. Answer it: fill `renamed-probe.ipynb` and
      click its confirm button with a real click.
    - `rename_dialog_before_gate: true`: the gate modal was not open while the rename
      dialog was.
    - `gate_after_rename: true`: the gate modal then opens.
    - `renamed_file_saved: true`: `contents.get("renamed-probe.ipynb")` returns the
      marker by content.
- **AC-12 (L3 native)** [SMOKE, T8b, scenario S10: fresh context; the drive is seeded
  with `persist-probe.ipynb`]:
  - `download_matches`: a real-click Download of `persist-probe.ipynb` from the
    file-browser context menu is captured with `page.expect_download()`, and its bytes
    parse to the drive's cells.
  - `upload_matches`: a real click on the file-browser Upload button, then
    `expect_file_chooser().set_files(<tmp file>)`, makes `contents.get` return identical
    content.
- **AC-13 (non-FSA, D5)** [SMOKE, T8a, scenario S3: a fresh context whose init script
  defines `window.showDirectoryPicker` as `undefined`]:
  - `nofsa_l2_controls: 0`, counting `[data-praxis-action=choose-folder]`.
  - `nofsa_message_mentions_chromium: true`.
  - `nofsa_modal_choose_absent: true`.
  - `nofsa_indicator_present: true`.
- **AC-14 (storage hygiene, by name AND content)** [SMOKE, T8a, evaluated at the end of
  S2]. From `indexedDB.databases()`:
  - zero names match `/^JupyterLite Storage - /`
  - exactly one `praxis-repl-contents`
  - `praxis-repl-persistence` is present after binding
  - the probe file is readable by content through `contents.get` (trap 3)
- **AC-15 (CI wiring)**:
  - `uv run python -m pytest web-repl/tests/test_repl_workflow_covers_tests.py -q` passes.
  - `grep -c -- '--persistence-check' .github/workflows/repl.yml` ≥ 1.
  - `grep -c 'bun test web-repl/shell/persistence' .github/workflows/repl.yml` ≥ 1.
  - `grep -c 'check_gesture_invariant.py' .github/workflows/repl.yml` ≥ 1.
- **AC-16 (no regressions)**:
  - `uv run python -m pytest web-repl/tests/test_inject_shell_coxswain.py -q` passes,
    including the inject block's byte-identity test.
  - `git diff origin/main -- web-repl/jupyter-lite.json web-repl/scripts/inject_shell.py`
    is empty.
  - The full REPL workflow is green on the PR head, including the lab-entry gates
    `--notebook-check`, `--autosetup-fault-check` and `--restart-check`.
- **AC-17 (sensitivity: the gate can fail)**:
  - Copy the built site: `cp -r web-repl/dist /tmp/claude-1000/persist-neg`.
  - Remove `/tmp/claude-1000/persist-neg/shell/persistence/panel.js`.
  - Run `uv run python scripts/repl_smoke.py --persistence-check --base-path /praxis/ --serve-dir /tmp/claude-1000/persist-neg`.
  - Expected: a **nonzero** exit that names `indicator_present_before_save`.
  - The observed exit code goes in the PR description.

---

## 6. Fixer tasks

Each task is a single-session job. "Closes" names the acceptance criteria the task's gate
proves.

**T1: codec.** Create `web-repl/shell/persistence/codec.js` and
`__tests__/codec.test.js`, following the section 4 row.
- Depends on: none.
- Closes: AC-5.
- Gate: [BUN].
- Size: ~120 LOC.

**T2: core: L1, tier, folder bind/rehydrate/reconnect, gesture synchrony.** Create
`core.js` and `__tests__/fakes.js`, and the parts of `__tests__/core.test.js` for AC-1,
the Protect/Choose/Reconnect cases of AC-2, and the rehydrate/reconnect half of AC-3.
- `onXClick` functions are plain (non-async) and call the gesture API as their first
  statement.
- Any follow-up work is chained on the returned promise.
- A successful choose uses `handleStore.rebind(handle)`: the atomic set clear plus a
  binding-generation bump (D1, B-2).
- Depends on: none.
- Closes: AC-1, and AC-2 except its `onRestoreClick` case, which T3 closes.
- Gate: [BUN].
- Size: ~300 LOC.

**T3: core: mirror, exclusion, pending set, restore.** Add to `core.js`, per D1 and D7:
- **Write chain:** a single chain, with each write reading current content at write time
  and each job carrying its binding generation. Stale-generation jobs are dropped.
- **Save handlers:** `handleFileSaved`, and `handleFileRemoved`, which drops the path from
  `mirrored-paths`.
- **Pending set:** persisted. It flushes when the handle is bound AND permission is
  granted AND the set is non-empty, **not** on a tier change. The tier is `L2-syncing`
  while it drains, and a path leaves the set only after a successful write.
- **Error classification (B-9, B-11):**
  - A `TypeError` from `getFileHandle`, `getDirectoryHandle`, `createWritable` or `write`
    means that path is excluded.
  - `NotFoundError` or `InvalidStateError` on the root means `folder-unavailable`
    (Choose a folder again).
  - Anything else means paused (Reconnect).
- **Sets:** the persisted excluded set and `mirrored-paths`. Bulk-sync writes, bulk-sync
  "identical" results, first writes and Replace all add to `mirrored-paths`.
- byte-comparing bulk sync on choose, which supersedes any old-binding flush
- the first-write byte check
- `onReplaceDiskCopyClick`
- `onRestoreClick`: drive-absent only, parent directories created first, `restoring`
  set, dot-paths skipped
- path validation, using codec

Also add the AC-3 tests and AC-2's `onRestoreClick` synchrony case.
- Depends on: T1, T2.
- Closes: AC-3, and AC-2's `onRestoreClick` case.
- Gate: [BUN].
- Size: ~350 LOC.

**T4: core: first-save gate decision.** Add to `core.js`:
- `handleExplicitSave`
- ack flag handling (`praxis-repl-persistence-ack`). **Every** successful choose sets
  `folder`: from the modal, the panel, or Choose a folder again (B-3).
- a `state.modal` model with a `choose` option shown iff `pickDirectory !== null`
- `onKeepBrowserOnlyClick`

Also add the AC-4 tests.
- Depends on: T2.
- Closes: AC-4.
- Gate: [BUN].
- Size: ~100 LOC.

**T5: static gesture checker.** Create `web-repl/scripts/check_gesture_invariant.py` and
`web-repl/tests/test_check_gesture_invariant.py`, per D6 and section 4. `GESTURE_CALLS`
includes `pickDirectory\(`. The checker also enforces the forbidden-string rule for
`__praxis_test_force_prompt` (B-11). There are seven negative fixtures plus one positive
fixture. **Add the test's own pytest line to the "Tests" step of
`.github/workflows/repl.yml`.**
- It can be written in parallel, but its tree-passes test needs T2-T4 merged.
- Depends on: T2, T3, T4 for the positive run.
- Closes: AC-6.
- Gate: both AC-6 commands, plus
  `uv run python -m pytest web-repl/tests/test_repl_workflow_covers_tests.py -q`.
- Size: ~200 LOC.

**T6: panel and loader.** Create `web-repl/shell/persistence/panel.js` and append the
loader IIFE to `web-repl/shell/praxis-shell.js`, per sections 3, 4 and D4/D5.
- Stable selectors:
  - `#praxis-persistence[data-praxis-tier][data-praxis-excluded]`
  - `[data-praxis-action=protect|choose-folder|reconnect|restore|keep-browser-only|toggle-panel]`
  - `[data-praxis-action=replace-disk-copy][data-praxis-path="<path>"]`
- The modal is `dialog#praxis-persistence-first-save`, re-armed on `close` when no choice
  is recorded.
- The save trigger is `commandExecuted`, whose payload is
  `ICommandExecutedArgs {id, args, result}`. Filter on `evt.id` for the three save ids,
  and act only after `evt.result` resolves.
- `pickDirectory` is injected as `window.showDirectoryPicker.bind(window)`.
- Render only after `app.restored`.
- Every listener is exactly `() => core.onXClick(...)`.
- Depends on: T2, T3, T4, T5. T5 comes first so the checker is available as this task's
  gate (B-5).
- Closes: nothing by itself; this task makes AC-8 to AC-14 reachable.
- Gate: `bun test web-repl/shell/persistence` still passes, and
  `uv run python web-repl/scripts/check_gesture_invariant.py` exits 0 (the panel is also
  scanned).
- Size: ~300 LOC.

**T7: staging.** Modify `build_repl.py`:
- in `stage_shell`, `rmtree` the destination `<out>/shell/persistence/` before copying
- update `assert_dist_complete`

Create `web-repl/tests/test_persistence_staging.py`, including the stale-file case.
**Add the test's own pytest line to the "Tests" step of `.github/workflows/repl.yml`.**
- Depends on: none. The test uses tmp dirs and placeholder files.
- Closes: AC-7.
- Gate: AC-7 commands, plus
  `uv run python -m pytest web-repl/tests/test_repl_workflow_covers_tests.py -q`.
- Size: ~70 LOC.

**T8a: browser gate, harness + L1 / non-FSA / hygiene.** Modify `scripts/repl_smoke.py`
to add `--persistence-check` and `run_persistence_check`, following the existing check
shape (for example `run_typeahead_check`, `repl_smoke.py:1285-1407`: `ServedDir`,
`chromium_launch_args`, and a `result` dict with `failures`).
- Build the harness first:
  - a per-scenario fresh-context helper
  - init scripts that:
    - wrap `StorageManager.prototype.persist` **and** `.persisted`, calling through to
      the originals
    - stub `showDirectoryPicker` with the OPFS handle, reporting to the Python-side
      counter via `page.expose_function`
    - wrap `FileSystemHandle.prototype.requestPermission` and `queryPermission` (the
      latter with the forced-prompt switch), adding polyfills if absent and recording
      `permission_methods_polyfilled`
    - install the capture and bubble `inClickDispatch` listeners
    - install `__praxisGestureLog`
- Then add scenarios S1, S2 and S3.
- Use real `page.click()` and keyboard only.
- Compare every storage check by content.
- Record the sensitivity run (AC-17) in the PR description.
- Depends on: T6, T7.
- Closes: AC-8, AC-9, AC-13, AC-14, AC-17.
- Gate (interim, B-6): a **local unsandboxed** run on a freshly built `web-repl/dist`:
  `uv run python scripts/repl_smoke.py --persistence-check --base-path /praxis/ --chrome-path ~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`,
  with `dangerouslyDisableSandbox: true`.
  - The S1-S3 keys pass (exit 0), and the AC-17 run exits nonzero.
  - CI cannot gate this task: the smoke step is not wired until T9. The CI green run
    becomes the gate at T9.
- Size: ~250 LOC.

**T8b: browser gate, L2 + first-save gate + L3.** Add scenarios S4-S10 to
`run_persistence_check`, using the T8a harness.
- Depends on: T8a.
- Closes: AC-10, AC-11, AC-12.
- Gate (interim, B-6): the same **local unsandboxed** run as T8a exits 0 with every key
  in AC-8 to AC-14. CI confirmation happens at T9.
- Size: ~300 LOC.

**T9: CI wiring.** Modify `.github/workflows/repl.yml`. **Only** these steps: the
`--persistence-check` smoke step, the `check_gesture_invariant.py` step, and the
coxswain-job `bun test web-repl/shell/persistence` step. The pytest lines already landed
with T5 and T7.
- Depends on: T5, T7, T8b.
- Closes: AC-15, AC-16, and the CI confirmation of AC-8 to AC-14 and AC-17.
- Gate: AC-15 commands, plus a green REPL workflow on the PR head, including the
  `--persistence-check` step. Per CLAUDE.md the
  merge itself is a human `--admin` action; the agent does not merge.
- Size: ~20 LOC.

**T10 (contingent, only if AC-12 `download_matches` fails on native Download).** Add a
"Download current file" button to `panel.js`. It uses `contents.get`, then
`modelToFileBytes`, then a Blob and an anchor `download`. Repoint AC-12's Download half at
this button.
- Depends on: T8b.
- Closes: AC-12.
- Size: ~40 LOC.

| Task | Scope | Depends on | Closes |
|---|---|---|---|
| T1 | `codec.js` + tests | none | AC-5 |
| T2 | core: L1, tier, bind/rehydrate/reconnect, gesture synchrony, fakes | none | AC-1, AC-2 |
| T3 | core: generation-tagged write chain, persisted pending set (flushed on bound+granted, `L2-syncing` while it drains), error classification (per-path `TypeError` / folder-unavailable / pause), exclusion + `mirrored-paths` (incl. delete/rename), Replace, restore | T1, T2 | AC-3, and AC-2's `onRestoreClick` case |
| T4 | core: first-save gate decision + ack (any choose sets `folder`) | T2 | AC-4 |
| T5 | `check_gesture_invariant.py` (+ `pickDirectory`, + forbidden `__praxis_test_force_prompt`) + test + its repl.yml pytest line | T2-T4 (positive run) | AC-6 |
| T6 | `panel.js` + loader IIFE in `praxis-shell.js` | T2, T3, T4, T5 | (enables AC-8 to AC-14) |
| T7 | `build_repl.py` staging (rmtree + copy) + `assert_dist_complete` + test + its repl.yml pytest line | none | AC-7 |
| T8a | smoke harness + S1-S3 (L1, non-FSA, hygiene, sensitivity); interim gate is a local unsandboxed run | T6, T7 | AC-8, AC-9, AC-13, AC-14, AC-17 (locally) |
| T8b | smoke S4-S10 (L2, differs-on-disk, paused/reload with no gate, restore, gate incl. untitled rename, L3); interim gate is a local unsandboxed run | T8a | AC-10, AC-11, AC-12 (locally) |
| T9 | repl.yml: smoke step, checker step, bun step | T5, T7, T8b | AC-15, AC-16, and CI confirmation of the [SMOKE] ACs |
| T10 | contingent download button | T8b | AC-12 (only if native Download fails) |

Parallel start: T1, T2 and T7 have no dependencies.
Order: T1 → T3; T2 → T3, T4; T2 + T3 + T4 → T5 → T6; T6 + T7 → T8a → T8b; T5 + T7 + T8b → T9; T10 only if needed.

---

## 7. Risks

| Risk | Mitigation / rollback |
|---|---|
| `contents.fileChanged` does not fire `"save"` for the JupyterLite browser drive | AC-10 `mirror_after_resave_matches` catches this in CI. Fallback: also mirror on the resolved result of the three save commands (D4). Autosave then goes unmirrored, and the panel text must say so. |
| Native Download is broken or unreachable in JupyterLite 0.8.1 | AC-12 detects it; T10 is the pre-planned fallback. |
| The modal makes the page inert and breaks another lab-entry gate | The gate triggers only after one of the three `docmanager:save*` commands resolves. No existing gate runs any of them (a `repl_smoke.py` grep finds only `docmanager:open`). AC-16 requires those gates green. |
| The gate opens before the save lands, or after a failed save | Lumino emits `commandExecuted` immediately, with a pending result, and also on rejection. The panel reads `evt.id` and `evt.result` from `ICommandExecutedArgs` and acts only in `evt.result.then(...)`, with a no-op rejection handler (D4). AC-11 `save_landed_before_modal` checks by content. |
| The Escape key closes the modal on the second press (CloseWatcher) | The dialog re-calls `showModal()` on `close` when no choice is recorded (D4). AC-11 presses Escape twice. |
| A mirror silently overwrites a disk file the user owns | Bulk sync and first writes compare bytes, and differing paths are excluded, never overwritten. Only an explicit per-file "Replace disk copy" click overwrites such a file. A drive delete or rename drops the path from `mirrored-paths`, so a later same-path create is checked again. AC-3 and AC-10 S5 test this. **Accepted gap (B-8):** an out-of-browser edit to a disk file that is already mirrored is overwritten by the next save. Detecting it would need per-path `lastModified` tracking, which was declined (OQ-4). |
| State from folder A leaks into folder B after a rebind | Any successful choose stores the handle and clears the pending, excluded and mirrored sets in one IndexedDB transaction. Chain jobs carry a binding generation, and stale ones are dropped. AC-3 "Rebind" tests this. |
| The pending flush can never fire, because L2 requires an empty pending set (deadlock) | The flush trigger is "handle bound AND permission granted", not a tier change. The tier is `L2-syncing` while the flush drains. AC-3 checks the mid-flush tier and the init-time flush. |
| A Reconnect loop that cannot succeed after the folder is deleted | Root `NotFoundError` or `InvalidStateError` gives `folder-unavailable`, which offers Choose a folder again, not Reconnect. AC-3 tests this. |
| The test-only forced-prompt switch leaks into product code | The checker's forbidden-string rule plus the AC-6 grep guard. |
| The first-save modal opens over the paused/Reconnect flow | Any successful choose sets the ack to `folder`, so the gate never re-arms after a bind. AC-4 and AC-10 S6 `gate_never_opened_s6` test this. |
| Out-of-order or partial writes (rapid saves, chunked uploads) | One write chain, and each write reads current content when it runs (D7). AC-3 ordering cases test this. |
| Saves made while paused are lost on reload | The pending set is persisted in IndexedDB and flushed whenever the handle is bound and permission is granted. AC-3 and AC-10 S6 test this. |
| The browser gates cannot run in CI until the workflow is wired (T9) | T8a and T8b gate on a local unsandboxed run, and CI confirms at T9 (B-6). |
| The chip overlaps a JupyterLab control that a gate clicks | Fixed position with `pointer-events` scoped to the chip box. AC-16 catches any regression. |
| `import()` from the classic shell script fails, or `currentScript` is null | `currentScript` is captured synchronously at the top of the IIFE. Failure goes to `console.error` and the REPL keeps working without persistence. AC-8 `indicator_present_before_save` fails loudly in CI, and AC-17 proves that it can. |
| OPFS handles lack `queryPermission`/`requestPermission` in the CI Chromium | The init script defines them on `FileSystemHandle.prototype` when absent, and records that it did (`permission_methods_polyfilled` in the result JSON) so the substitution is visible. |
| The handle DB name collides with the legacy migration or storage-hygiene gates | The name is `praxis-repl-persistence` (no `JupyterLite Storage - ` prefix), checked by AC-14. |
| Shell modules are outside the D2 manifest, so a stale `panel.js` could pair with a fresh shell | This is the same exposure the D1 shell already accepts (ADR Sec 2.3), and the panel has no cross-file protocol version to skew. Accepted, noted. |
| Merge conflict with P5.6 in `praxis-shell.js` | This spec's edit is a single appended IIFE. Rollback: revert the IIFE and the rest is inert (no loader, no chip). |
| Rollback overall | This adds a feature and migrates no data. Reverting the PR removes the loader, and the leftover `praxis-repl-persistence` DB and ack key are harmless. User files already mirrored to disk stay on disk. |

---

## 8. Open questions (owner or product, non-blocking)

- **OQ-1.** Confirm D4's deviation from R20: the gate blocks interaction, not the data write.
- **OQ-2.** Should "Keep in this browser only" ever re-surface, say after N sessions? The
  default is no; the warning-styled chip is the standing reminder.
- **OQ-3.** Is a whole-workspace zip export wanted for non-Chromium users? The default is
  no, per YAGNI.
- **OQ-4.** Is the conflict policy right? Adjudicated in round 1: differing disk copies
  are excluded, and only an explicit per-file Replace click overwrites one (D7).
  Known gap (B-8): an out-of-browser edit to an already-mirrored disk file is
  overwritten by the next save. Closing it would need per-path `lastModified` tracking,
  which was declined. Still open to owner revision.
- **OQ-5.** Should the mirror also run under the `notebooks/` app entry? This spec covers
  `lab/` only.

## 9. Residual real-browser human checks (U16/U17 follow-ups, NOT autonomous AC)

These measure UX quality. They cannot change the correctness established above.

- **H1 (U16).** In a real Chrome profile with genuine site engagement (bookmarked, used
  across days), click Protect and record `persist()`'s result. This decides whether L1 is
  a meaningful tier or mostly decorative.
- **H2 (U17).** Grant a folder, fully quit Chrome, and reopen. Record:
  - `queryPermission` on load
  - the Reconnect prompt text
  - whether Chrome's three-way "Allow on every visit" option (recent Chrome) yields
    `granted` on reload with no Reconnect click
- **H3.** Use the real picker on blocked locations (home directory root, Downloads root,
  system dirs), and confirm the rejection surfaces in the panel's error text.
- **H4.** In Firefox and Safari, check:
  - the D5 copy
  - Firefox's `persist()` permission prompt, triggered from our click
  - native Download
- **H5.** Judge the first-save modal's wording and friction (the R20 "UX tax" concern).

## Revision 1 (260922)

Round-1 adversarial review: challenger REVISE, defender REVISE (audits
`260922_repl-persistence_spec-challenge` / `_spec-defense`). The coordinator's adjudicated
list was applied. Each entry below gives the adjudicated item number (A-n) and the
challenger objection number where the adjudication named it. Objections 1-3 are the
challenger's three blockers, in its order.

- **A-1 (obj 1): D4 trigger.**
  - The gate acts only after `args.result` resolves, and a rejection is a no-op.
  - The trigger ids are now `docmanager:save`, `save-as` and `save-all`.
  - Close-dialog saves are stated out of scope.
  - The "already completed" claim is reworded.
  - Added AC-11 scenario S9: untitled file, rename dialog, then the gate, with the
    renamed file checked by content.
- **A-2: D4 Escape.** The dialog re-arms itself on `close` when no choice is recorded
  (CloseWatcher). AC-11 now presses Escape twice.
- **A-3 (obj 2): D6 and the gesture checker.**
  - `pickDirectory\(` is added to `GESTURE_CALLS`.
  - The panel injects `showDirectoryPicker.bind(window)`.
  - The invariant is reworded: no `await`, `.then` or async call before the gesture
    call; synchronous cached-state conditionals are allowed.
  - A sixth negative fixture covers `pickDirectory` called from a non-`on*Click`
    function, and a positive conditional fixture was added.
- **A-4: D1 errors.**
  - A per-path `TypeError` or invalid-name error marks only that path not mirrorable,
    and the mirror does not pause.
  - Any other error pauses.
  - The honesty invariant is restated over mirrorable paths.
- **A-5: pending set.**
  - The pending set is persisted in `praxis-repl-persistence`.
  - It is flushed whenever the tier becomes L2: at init with permission granted, or on
    Reconnect.
  - Added AC-10 scenario S6: paused save, reload, Reconnect, then the file is on disk by
    content.
- **A-6 (obj 3; adjudicated position differs from both sides): no silent overwrite.**
  - New decision D7. Bulk sync compares bytes, and a differing disk copy goes into the
    persisted excluded set as "differs on disk".
  - The per-save mirror and the pending flush skip excluded paths.
  - Each excluded path gets a per-file **Replace disk copy** click.
  - The chip reads "Folder: <name> (N not mirrored)".
  - Section 3.3 is reworded.
  - New bun tests (AC-3) and AC-10 scenario S5 cover it.
  - Implementation note (spec author): the same byte check also applies to a path's
    first write after bulk sync, via a persisted `mirrored-paths` set. This is a path
    set, not `lastModified` tracking. It is needed for "no silent overwrite, ever" to
    cover files created after binding.
- **A-7: mirror ordering.**
  - One write chain, and each write reads current content at write time.
  - `fileChanged` events are ignored for paths in an active restore.
  - Restore and bulk sync skip dot-prefixed paths.
  - Restore creates parent directories first.
  - No caps and no confirmation prompts.
- **A-8: T8 harness.**
  - `persisted()` is wrapped too.
  - The picker is counted on the Python side via `expose_function`.
  - Each scenario gets a fresh context with a stated starting state (S1-S10).
  - T8 is split into T8a (AC-8/9/13/14/17) and T8b (AC-10/11/12).
- **A-9: CI lines.** T5 and T7 each add their own `repl.yml` pytest line, because
  `test_repl_workflow_covers_tests.py:48-55` fails on unwired files. T9 keeps only the
  smoke, checker and bun steps.
- **A-10: T7 staging.** `rmtree` of `dist/shell/persistence` before copying, mirroring
  `build_repl.py:1069-1070`. The staging test adds a stale-file case.
- **A-11 (obj 12, rebutted): chip timing.** No design change. The spec now states that
  the chip renders after `app.restored` (section 3.1, section 4 panel row, T6).

## Revision 2 (260922)

Round-2 challenge (`260922_repl-persistence_spec-challenge-r2`): every round-1 blocker is
CLOSED, and the revision introduced three MAJORs (B-1 to B-3). Revision 1 entries A-1 and
A-5 above are kept as history. Where they conflict with this revision, this revision
wins: the flush trigger changed, and `args.result` is now named `evt.result`.

- **B-1 (MAJOR): flush deadlock.**
  - The pending flush is triggered by "handle bound AND permission granted AND pending
    set non-empty", not by "tier becomes L2", which could never fire because L2
    requires an empty pending set.
  - New tier `L2-syncing` ("Folder: <name> (syncing N)") while the set drains. A path
    leaves the set only after a successful write, and `L2` comes once it is empty.
  - Updated: D1 table row, honesty invariant, sections 3.1, 3.4 and 3.5, the core row,
    T3, and the risk table.
  - Added AC-3 cases for the mid-flush tier and the init-time flush.
- **B-2 (MAJOR): stale state after a rebind.**
  - Any successful choose (panel, modal, or Choose a folder again) stores the handle and
    clears `pending-paths`, `excluded-paths` and `mirrored-paths` in one IndexedDB
    transaction (`handleStore.rebind`), before bulk sync is queued.
  - Chain jobs carry a binding generation, and stale ones are dropped, so bulk sync
    supersedes the old flush.
  - `mirrored-paths` is explicitly scoped to the current binding.
  - A drive `delete` or `rename` removes `oldValue.path` from `mirrored-paths` via
    `handleFileRemoved`.
  - Added AC-3 case: bind A, paused save, choose B with a differing copy, B's bytes
    unchanged. Also added a delete-then-recreate case.
- **B-3 (MAJOR): ack.**
  - Any successful choose sets the ack to `folder` (D4, T4). AC-4 tests all three
    sources, plus "no modal after a panel choose followed by permission loss".
  - S6 now binds through the panel, uses an explicit `Control+S` save rather than
    autosave, and asserts `gate_never_opened_s6`.
- **B-4:** AC-2's `onRestoreClick` synchrony case moves to T3. T2 closes AC-2 except
  that case; T3 closes the case.
- **B-5:** T6 now depends on T5.
- **B-6:** the interim gate for T8a and T8b is a local unsandboxed run of
  `--persistence-check` (`dangerouslyDisableSandbox`, explicit `--chrome-path`). CI
  confirms only after T9.
- **B-7:** D4, the panel row, T6 and the risk table now name the Lumino payload as
  `CommandRegistry.ICommandExecutedArgs {id, args, result}`. The handler reads `evt.id`
  and `evt.result`.
- **B-8:** D7 is retitled. It no longer claims "no silent overwrite, ever". It states the
  one known gap: an out-of-browser edit to an already-mirrored disk file is overwritten
  by the next save, because per-path `lastModified` tracking was declined. Recorded in
  OQ-4 and the risk table.
- **B-9:** "name not allowed" per-path classification is limited to a `TypeError` thrown
  by `getFileHandle`, `getDirectoryHandle`, `createWritable` or `write`. Anything else
  pauses. There is an AC-3 case for a `TypeError` from `contents.get`.
- **B-10:** Replace disk copy, bulk-sync writes, bulk-sync "identical" results and first
  writes all add the path to `mirrored-paths` (stated in D7 and section 3.3, tested in
  AC-3).
- **B-11:**
  - Root `NotFoundError` or `InvalidStateError`, at init or on write, gives
    `pauseReason: folder-unavailable`, "Folder unavailable", and Choose a folder again,
    never a Reconnect loop. Covered in D1, section 3, and an AC-3 case.
  - T5 adds a forbidden-string rule for `__praxis_test_force_prompt` under
    `web-repl/shell/persistence/*.js`, with a seventh negative fixture and an AC-6 grep
    guard.

## References

- Plan P5.8 and traps: `.praxia/docs/plans/260817_praxis-repl-refocus-execution-plan.md:425`, `:429-434`, `:607`, `:655-656`
- Prior art: `.praxia/docs/specs/260817_spec-web-repl-extraction.md` R18-R21 (`:177-187`), T11-T13 (`:281-295`), Q5/Q6 (`:364-365`)
- DI FSA pattern: `web-repl/shell/coxswain/export.js:62-126`; fake at `web-repl/shell/coxswain/__tests__/audit_store.test.js:497-572`
- Shell: `web-repl/shell/praxis-shell.js` (ping/pong `:54-105`, migration `:167-477`); staging `web-repl/scripts/build_repl.py:1016-1081`, `:1140-1178`
- Runtime config: `web-repl/jupyter-lite.json`
- CI: `.github/workflows/repl.yml`; the per-file guard is `web-repl/tests/test_repl_workflow_covers_tests.py`

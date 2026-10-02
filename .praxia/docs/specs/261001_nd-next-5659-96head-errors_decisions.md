# Decisions for #5659: error panels for 96-head operations (spec r2)

Spec: `261001_nd-next-5659-96head-errors.md` (same folder). Task 260929_notebook-display-design.
Glossary: **96 head** = the 96-channel pipetting head. **Committed** = what PLR (PyLabRobot) has recorded
as done. **Pending** = changes PLR has queued but not yet confirmed. **Residue** = pending changes PLR leaves
behind after it refuses an operation. **Panel** = the error box Praxis shows instead of a bare traceback.

Today, any error inside a 96-head operation gets the generic panel: PLR's one-line message, which names no
plate, no well and no count. Example: "Not enough liquid in container: 50.0uL > 0uL." when all 96 wells of
`assay` are empty.

The first two questions decide whether to build at all.

## Q1. Build the core now, or wait for PyLabRobot to fix its 96-head operations? File the upstream report?

PLR's four 96-head operations queue their bookkeeping outside their error handling, so when PLR refuses
one, the queued changes stay behind, and the next operation that succeeds saves them. Measured once in
round 1 (an unregistered observation): well A1 ends at 20 µL when 70 µL is really there.
- **(a) Build the core now and file the upstream report in parallel (recommended).** The core is the panel
  that names the plate, wells and amounts, plus the committed drawing and ledger fixes, about 1,000 test
  lines and 330 product lines. A PLR fix would make only the separate residue layer (Q4) unnecessary.
  PLR's own message stays uninformative even after a fix.
- **(b) Wait for upstream.** No cost now. 96-head errors stay generic for as long as the fix takes, which is
  unknown.
- Report: **yes, you file it** (Praxis does not patch PLR). It extends the existing open question OQ-6.
- Yes to (a): fixer tasks 1-7 and 9 start. Yes to (b): the spec is parked and #5659 stays open.

## Q2. Is it worth building, given who will see these panels?

A 96-head panel appears only when all three hold: tracking is switched on (PLR switches it off by default),
`await lh.setup()` has run, and the backend reports a 96 head. Covered: the chatterbox simulation backend
(the one the docs and fixtures use), SerializingBackend, and a real Hamilton STAR fitted with a 96 head.
Not covered: the browser bridge backend (WebBridgeBackend) and the OT-2, Vantage and EVO backends. On those,
a 96-head call fails with a `KeyError` that has nothing to do with these panels. Nothing in the repo calls
`create_browser_backend` (checked by a recorded probe); REPL users build their own handler from the injected
names. Whether those names really reach a running browser kernel is not checked (it needs a browser run).
- **(a) Build for the covered backends, as specified (recommended).** Simulation users who turn tracking on
  are exactly the people running 96-head protocols on paper first.
- **(b) Also make WebBridgeBackend report a 96 head.** Out of scope here; it would need its own spec.
- **(c) Do not build.** Saves the work. 96-head errors stay generic.
- Yes to (a): no change. (b): a new backlog item. (c): close #5659 as won't-do.

## Q3. Size of the drawing when many wells fail

Every panel is capped at 64 KiB (65,536 bytes), and that cap is enforced. Round 1 also claimed "under 32 KiB",
but nothing enforces that and it is false. Measured: 38,616 bytes for a panel with a long traceback. That
claim is withdrawn. Separately, D4 sets size targets for drawings (plate 16,384 bytes, tip rack 12,288 bytes).
With all 96 positions marked as failing, the drawings measure 19,746 bytes (plate, 21% over) and 19,437 bytes
(rack, 58% over). D4 says a missed target needs your approval, recorded with its reason.
- **(a) Approve new targets for fully-faulted drawings: 20,480 bytes (20 KiB) each, tested (recommended).**
  Normal drawings keep their current targets. Costs nothing, and every failing well stays marked.
- **(b) Require compaction.** Not recommended: each mark costs about 110 bytes, so 95 failing wells cost
  almost as much as 96. A real fix would need a new kind of mark (about 60-80 lines, not measured).
- **(c) Above N failing positions, draw the plain block version** (an existing reduced drawing, about 5.5 KB).
  About 10 lines of code. Individual failing wells are no longer marked above N. You choose N.
- A second, stricter size limit at 32 KiB is **not** offered: it would mean changing the enforced cap
  machinery for a limit D4 never set.
- Yes to (a): the 20 KiB test is added. (b) or (c): the spec gets a new design section before any fixer starts.

## Q4. The residue warning sentence: keep, reword, or defer?

When PLR has left queued changes behind, the panel can add one sentence (provisional wording):
"PyLabRobot still records moves that did not happen on {wells / tips}; the next step that succeeds will
save them, and the tracked state will be wrong from then on." Where there is a drawing it adds: "The
drawing shows what was actually done." It also covers liquid queued into the tips, which round 1 missed.
- **(a) Keep it, as a separate task after the core (recommended).** About 260 lines, in a new module that
  is the only display code allowed to read pending state. It warns before the damage is saved, which is
  the only point at which a user can still avoid it.
- **(b) Reword it.** Give me the wording. Tests pin whatever you choose.
- **(c) Defer it.** The core ships alone, and the silent-drift problem stays invisible.
- Not offered: a helper that undoes PLR's queued changes. The display layer never changes state.
- Yes to (a): task 8 runs after the core. (c): task 8 is dropped and its tests are not written.

## Q5. Which wells count as "offending" when earlier leftovers changed which channels PLR uses?

After a refused tip drop, PLR thinks 5 channels have no tips, but they physically still do. On the next
aspirate, PLR skips those 5 channels. Measured: with wells A1-E1 and C2 short, PLR names only C2, while
counting the channels that physically hold tips names all 6 wells.
- **(a) Count what the head physically holds, i.e. committed (recommended).** A real robot would aspirate
  from A1-E1 too. PLR's set is always contained in this one, so a well PLR reached is never left out.
- **(b) Count what PLR iterated.** Matches PLR exactly, but names fewer wells than a real robot would hit.
- Either choice is gated by a test that tells them apart. (b) flips that test.

## Q6. May this change what 1-channel error panels draw for a tip rack?

Error panels will draw the tips that are really in the rack (committed), not PLR's pending view. For
1-channel panels this matters only when an earlier failed pick-up left leftovers on that rack. Measured:
today's panel draws 92 tips and says "92 of 96 tips left" when 95 tips are really there.
- **(a) Yes, for every error panel (recommended).** The hover/keyboard text and the sentence change together
  with the drawing, and a new test pins them. Non-error drawings are byte-for-byte unchanged.
- **(b) Only for 96-head panels.** 1-channel panels keep today's (wrong) count. The test pins today's output.

## Q7. Should the ledger use committed volumes while `display(plate)` stays pending?

The run ledger is shown just above the error panel in the same cell. Today, after a refused 96-head
dispense, it outlines 10 wells as "changed" when nothing was dispensed (unregistered round-1 observation),
right next to a panel saying "Nothing was dispensed".
- **(a) Ledger reads committed; plate drawings in later cells keep showing PLR's view, for now (recommended).**
  The two can disagree after a refused 96-head operation. A follow-up decides plate drawings. The ledger also
  changes slightly for successful steps when leftovers from earlier exist, and a test pins this.
- **(b) Switch plate drawings to committed too.** Bigger change to shipped output. Needs its own spec.
- **(c) Leave the ledger on pending.** No change, but the ledger and the panel contradict each other.

## Q8. May the tests that pin "96-head errors get the generic panel" be replaced?

These are a scope cut from 260929, not a safety property. Pins replaced: `check_e96` and its CHECKS entry,
the "E-96" entries in `NONE_CASES` and in `test_real_resolver_passes_what_the_controls_fail`
(test_display_context.py), and "E-96" in `GENERIC_CASES` and its branch (test_display_errors.py). They are
replaced by stronger tests that check every field. These negatives stay or are added: E1_via_96,
E96-under-1ch, the two leftover-tip cases, the leftover-volume retry, and the three invalid-container cases.
The E-96 scenario itself stays as a scenario check. No tolerance or other gate is loosened.
- **(a) Yes (recommended).** (b) No: then the core cannot ship, because these pins assert the old behaviour.

## Q9. Wording

"Aspirate (96 head)", "on the 96 head" and the row texts in spec N5659-6 are provisional. **Default: accept
them as written.** Tests pin the final strings once you answer.

Not asked now: counting a partially loaded head by its real tip count in the ledger (a follow-up item).

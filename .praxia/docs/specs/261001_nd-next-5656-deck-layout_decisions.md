# Deck-panel layout (#5656): decisions for you

Spec: `/tmp/claude-1000/specs/v2/261001_nd-next-5656-deck-layout.md` (revision 2). All widths below are
in pixels, with the file browser open, measured in the recorded K2 browser run unless marked
*estimate* (arithmetic, not yet measured). "Dead space" means empty strip beside the deck that neither
the notebook nor the deck uses.

**What is wrong today, in one paragraph.** At 1280-1599 px the deck is held to 420-480 px wide, but
JupyterLab's split hands the deck's side of the window any amount of room above 480 and centres the deck
in it. Measured:
- 1440 px window: 73.5 px empty when the deck opens;
- after any drag past 480, at both 1280 and 1440: 220 px empty (the notebook drops to 247 px at 1280);
- after closing the file browser or widening the window: the same kind of gap appears *(estimate:
  ~200 px and 11-20 px)*.

The proposed fix keeps the split (your ruling). After each of those events it resizes the split so the
deck's side is exactly the deck's width, and the notebook gets the rest. The questions that change the
design come first.

---

**Q1. How wide should the deck open at 1280-1599 px?**

| Open width | Notebook at 1280 | Notebook at 1440 |
|---|---|---|
| today (unchanged) | 473.5 (no gap) | 553.5 (+ 73.5 empty) |
| 420 | 527 | 687 |
| 450 | 497 *(estimate)* | 657 *(estimate)* |
| 480 | 467 *(estimate)* | 627 *(estimate)* |

- 420 gives the notebook the most room. It is the closest to your "about 710 px" and matches what the
  build already does when you shrink from a wide window to 1440. 480 gives the deck the most room but
  makes the notebook *narrower than today* at 1280, the width the design calls the quality target.
- **Recommended: 420.** Yes to 420: the spec is written for it. Another value: one constant changes; the
  tests read it, nothing else moves.

**Q2. When should the empty space go back to the notebook?**
- (a) Only when the deck opens or the window crosses into 1280-1599. Simpler, but the 220 px gap after a
  drag past 480 stays, and so does the gap after a file-browser toggle *(estimate ~36-66 px)*.
- (b) Also after every splitter drag, file-browser toggle and window resize inside 1280-1599. Your
  dragged width is always kept; only the empty strip is removed.
- **Recommended: (b).** Yes to (b): as written. (a): the drag/toggle/resize parts are dropped and the
  220 px state is written down as an accepted limit.

**Q3. Is "with the file browser open the notebook gets about 710 px" (your MVP text) a hard requirement?**
- With the file browser open, 710 is not reachable at any 1280-1599 width while the deck stays at least
  420. The maximum is 527 at 1280 and 687 at 1440. It becomes reachable only if the file browser is
  closed (Q4) or the deck may go below 420.
- **Recommended: a target, not binding.** The gap is recorded as a finding. Your text is not edited. If
  binding: you must also say yes to Q4, or allow a deck narrower than 420 (which changes your 420-480
  rule).

**Q4. Should opening the deck close the file browser at 1280-1599 (and reopen it when the deck closes)?**
- It gives the notebook 779 at 1280 / 939 at 1440 with a 420 deck *(estimate)*. The cost: the shell
  starts moving your panels, and the browser comes back only if the shell was the one that closed it.
- **Recommended: no.** Yes: one more task and two more browser checks (AC-N9). No: nothing to do.

**Q5. You ruled the deck is "a main-area split ... not a sidebar". Is a sidebar back on the table?**
- If yes, the next step is one pre-registered browser probe of a sidebar deck (no product code). Every
  sidebar width figure today is unverified.
- **Recommended: no.** The sidebar stays a paper option and no probe runs. Yes: the probe is scheduled
  (one run, plus one CI test line).

---

**Q6. May two existing unit-test lines be touched (`dock.test.js:1640` and `:1774`)?** Both say "at
1280-1599 there is no layout call".
- After the fix they still pass unchanged. The old test model has no real pixel positions, so the fix
  cannot measure and does nothing there. But their comments ("CSS, not layout") become untrue.
- The real behaviour is checked in a *new* test file, using a new opt-in model calibrated to reproduce
  the measured 73.5 and 220. Changing these two lines only makes sense together with that model.
- Options:
  - (a) leave them exactly as they are;
  - (b) correct the comments and titles only; the checked values stay the same;
  - (c) rewrite them as outcome checks in the new model.
- **Recommended: (b).** (a): the comments stay wrong. (c): duplicates the new file and replaces an old
  check, which is a judgement call you would own.

**Q7. Should the new browser checks be a new unit ("K3") rather than more keys in K2?**
- K2's lists of keys, steps and drags are pinned by existing tests. Adding keys there edits about eight
  of those pinned lists.
- A new unit K3 leaves K2 byte-identical but changes two pinned CI numbers: the dock steps' total
  minutes 45 -> 57 and the job's safety timeout 137 -> 149. It adds ~2.5 min of CI *(estimate)*.
- Side effect of opening at 420: two K2 checks ("a drag to 300 clamps at 420") would start where they
  end. A drag that silently did nothing would still pass them. K3's drags start from 460, so it
  catches that; K2's drag-to-700 checks still catch it too.
- **Recommended: K3, and leave K2 as it is.** No: the K2 pins are extended instead, and K2's drag order
  changes to start from 460.

**Q8. May this work edit your design notes (DESIGN.md)?**
- **Recommended: no.** Only the epic spec changes, and the orchestrator makes those edits. Yes: at most a
  one-line "Next" pointer; your 710 text stays yours.

---

What happens after you answer: the spec is updated to your answers, then built tests-first. Each new
browser check is pre-registered and is first run against today's build, where it must fail, before the
fix makes it pass.

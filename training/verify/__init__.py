"""P2.2 execution-verify harness (backlog 4477, spec rev2 §7 AC-2.2.x).

Public entry point: :func:`verify` -- run a call sequence against a real
(vendored, chatterbox) pylabrobot LiquidHandler deck and grade the run along
two independent axes:

1. POST-CONDITIONS (AC-2.2.2) -- did the world change the way the executed
   calls claim?  Mounted-tip deltas (pick_up_tips => tips present;
   drop_tips/discard_tips => absent) and per-well volume deltas measured via
   ``VolumeTracker.get_free_volume()`` diffs cross-checked against
   ``serialize_state`` snapshots.

2. SLOT AGREEMENT (AC-2.2.3) -- did every grounded argument land on the
   resource the INTENT RECORD binds it to?  This is the axis that catches
   "executes cleanly but wrong reading": a call that runs without error and
   moves exactly the volumes it names, but at the wrong deck location.

CONVENTIONS RECORDED HERE (juror finding C-M-lizard, "effect
arg-binding/move_resource contract hole"):

* ``move_resource`` / ``move_plate`` / ``move_lid`` produce NO tracker deltas
  (no volume, no tip state), so their post-condition CANNOT be a tracker
  diff.  Their intent check is a TARGET-LOCATION ASSERTION via DECK
  SERIALIZATION instead: after execution, ``deck.serialize()`` must show the
  moved object re-parented/located at the intent's destination binding.
  The same convention applies to the ``moves_resource`` effect in
  ``expected_effects`` grading.

* Post-condition volume checks are computed FROM THE EXECUTED CALLS' own
  references; the intent-level ``expected_effects`` table and the
  slot-agreement check are what tie execution to the intended semantics.
  A wrong-slot call therefore passes post-conditions while failing the
  agreement axis -- by design; see tests/test_verify_slot_agreement.py.

Base harness: praxis/backend/core/simulation/chatterbox_runner.py
(DeckFactory.create_setup, CHATTERBOX_REGISTRY, run_single pattern).
The module is loaded STANDALONE by file path so the SQLAlchemy import chain
via praxis.backend.core.__init__ never fires (chatterbox_runner itself is
SQLAlchemy-free -- verified).  backend/ and external/ are never modified.
"""

from __future__ import annotations

from verify.checks import Check, ExecutedCall
from verify.deck import DeckLayout, SetupHandle, build_setup, infer_layout
from verify.dispatcher import DispatchError, PlanResult, UnsupportedCallError, plan_call
from verify.grounding import Binding, GroundingError, ground_ref
from verify.verifier import run_verify_sync, verify

__all__ = [
    "Check",
    "DeckLayout",
    "DispatchError",
    "ExecutedCall",
    "PlanResult",
    "SetupHandle",
    "Binding",
    "GroundingError",
    "UnsupportedCallError",
    "build_setup",
    "ground_ref",
    "infer_layout",
    "plan_call",
    "run_verify_sync",
    "verify",
]

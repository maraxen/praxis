"""Authored golden corpus (P2.1 deliverable 1, AC-2.1.x, D2/D7/D8/D9/D11).

This module IS the human-reviewed golden data. Everything in
``training/golden/`` is generated from it deterministically (D9: golden
provenance pairs are human-authored and EXEMPT from regeneration; the
generator exists so the committed artifacts stay re-derivable byte-for-byte).

Sizing rules (count DERIVES from P2.0 tables -- never hard-coded totals):

- Exactly ``POSITIVES_PER_TOOL`` clean-parse utterances for EVERY name in
  ``coxswain.plr.tool_schema.PHASE2_TOOL_NAMES`` (>= 2 per included verb).
- Exactly ``CLARIFY_PER_CLASS`` examples for EACH of the three ambiguity
  classes (missing-slot / ambiguous-referent / out-of-surface), total >= 30.

Split policy (recorded): ALL clarify-class examples are held out
(``metadata == "eval"``) because the golden set is primarily the D2
baseline-first gate instrument (">=30 HELD-OUT clarify examples spanning all
three classes", D8). Training-side negative mixing at a controlled ratio is
P2.5 assembly's job over the full staged corpus (D7), not the golden set's.
Positives split evenly train/eval so both sides carry every verb.

Supervision shapes (D7 + D11):

- clean parse          -> assistant tool_calls with complete params.
- missing-slot         -> assistant tool_call with ONLY stated params;
                          ``missing_required`` is derived by
                          ``coxswain.plr.slot_derivation`` (never authored,
                          never predicted) and lands non-empty in the sidecar.
- ambiguous-referent   -> assistant tool_call whose string-valued resource
                          args are deictic/vague references;
                          ``unresolved_slots`` derives non-empty likewise.
- out-of-surface       -> NO tool call; assistant turn is a natural-language
                          clarification naming the capability boundary.

Juror finding applied: clarify-class sidecar rows MUST carry NON-EMPTY gap
fields (earlier fixtures had them empty). The builder derives and injects
them, then asserts non-emptiness per class -- empty would fail the build.

The developer scaffold is the research doc §2a template VERBATIM minus the
date/time preamble (D6-rev2: dates/timestamp injection OMITTED, stated
explicitly here).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from coxswain.plr.param_namespace import (
    RESOURCE_TYPE_CONTAINER,
    RESOURCE_TYPE_LID,
    RESOURCE_TYPE_PLATE,
    RESOURCE_TYPE_RESOURCE,
    RESOURCE_TYPE_TIP_SPOT,
    ParamKind,
    params_of,
    required_params,
)
from coxswain.plr.slot_derivation import derive_call_gaps
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

__all__ = [
    "DEVELOPER_SCAFFOLD",
    "AmbiguityClass",
    "CLARIFY_PER_CLASS",
    "GoldenCall",
    "GoldenExample",
    "POSITIVES_PER_TOOL",
    "build_corpus",
    "tool_declarations",
]

#: Research §2a developer-role scaffold, verbatim, WITHOUT the mobile-actions
#: date/time preamble. D6-rev2 requires this omission to be explicit: it is.
DEVELOPER_SCAFFOLD = "You are a model that can do function calling with the following functions\n"

#: Clean-parse utterances authored for EVERY PHASE2_TOOL_NAMES entry (>=2 req).
POSITIVES_PER_TOOL = 4

#: Authored examples per ambiguity class; x3 classes = 36 clarify examples,
#: all held out (eval), satisfying D8's ">=30 held-out" sizing.
CLARIFY_PER_CLASS = 12


class AmbiguityClass:
    """The three D8 ambiguity classes + the clean-parse class label."""

    CLEAN_PARSE = "clean_parse"
    MISSING_SLOT = "missing_slot"
    AMBIGUOUS_REFERENT = "ambiguous_referent"
    OUT_OF_SURFACE = "out_of_surface"

    ALL = (CLEAN_PARSE, MISSING_SLOT, AMBIGUOUS_REFERENT, OUT_OF_SURFACE)
    #: The three D8 clarify classes.
    CLARIFY = (MISSING_SLOT, AMBIGUOUS_REFERENT, OUT_OF_SURFACE)


@dataclass(frozen=True)
class GoldenCall:
    """One intended call: canonical name + canonical params ONLY (D11).

    Gap fields are NEVER authored here -- the builder derives them via
    ``derive_call_gaps`` and injects them into the sidecar row.
    """

    name: str
    params: dict


@dataclass(frozen=True)
class GoldenExample:
    """One authored golden example (native JSONL row + intent sidecar row)."""

    record_id: str
    split: str  # "train" | "eval"
    ambiguity_class: str
    utterance: str
    calls: tuple[GoldenCall, ...] = ()
    #: Out-of-surface only: the NL clarification/refusal supervision text.
    assistant_text: str | None = None
    #: Free-form authoring note surfaced in the manifest audit trail.
    note: str = ""


def _ex(record_id: str, split: str, cls: str, utterance: str, name: str, params: dict, note: str = "") -> GoldenExample:
    return GoldenExample(
        record_id=record_id,
        split=split,
        ambiguity_class=cls,
        utterance=utterance,
        calls=(GoldenCall(name=name, params=params),),
        note=note,
    )


# ---------------------------------------------------------------------------
# CLEAN PARSE -- POSITIVES_PER_TOOL per included tool, first half train,
# second half eval. Params use the canonical schema namespace exactly
# (param_namespace.py); resource values are opaque reference strings that
# grounding resolves against live kernel state at dispatch time.
# ---------------------------------------------------------------------------
_CLEAN: dict[str, list[GoldenExample]] = {
    "aspirate": [
        _ex("golden-clean-aspirate-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Take up 50 microliters from reagent_reservoir_1.",
            "aspirate", {"source": "reagent_reservoir_1", "volume_ul": 50}),
        _ex("golden-clean-aspirate-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Aspirate 25 uL from source_plate well A1.",
            "aspirate", {"source": "source_plate_A1", "volume_ul": 25}),
        _ex("golden-clean-aspirate-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Pull 100 uL out of the lysis buffer reservoir.",
            "aspirate", {"source": "lysis_buffer_reservoir", "volume_ul": 100}),
        _ex("golden-clean-aspirate-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Aspirate 10 microliters from tube rack position B3.",
            "aspirate", {"source": "tube_rack_B3", "volume_ul": 10}),
    ],
    "dispense": [
        _ex("golden-clean-dispense-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Dispense 50 microliters into destination plate well A1.",
            "dispense", {"destination": "destination_plate_A1", "volume_ul": 50}),
        _ex("golden-clean-dispense-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Put 200 uL into the assay plate column 1.",
            "dispense", {"destination": "assay_plate_col1", "volume_ul": 200}),
        _ex("golden-clean-dispense-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Dispense 15 uL into the waste plate position A1.",
            "dispense", {"destination": "waste_plate_A1", "volume_ul": 15}),
        _ex("golden-clean-dispense-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Deliver 75 microliters of buffer to microplate C6.",
            "dispense", {"destination": "microplate_C6", "volume_ul": 75}),
    ],
    "transfer": [
        _ex("golden-clean-transfer-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Transfer 20 uL from plate A well H12 to plate B well A1.",
            "transfer",
            {"source": "plate_A_H12", "destination": "plate_B_A1", "volume_ul": 20}),
        _ex("golden-clean-transfer-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Move 30 microliters from the donor plate to the receiver plate.",
            "transfer",
            {"source": "donor_plate", "destination": "receiver_plate", "volume_ul": 30}),
        _ex("golden-clean-transfer-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Transfer 50 microliters from calibrator 1 to standards plate position A1.",
            "transfer",
            {"source": "calibrator_1", "destination": "standards_plate_A1", "volume_ul": 50}),
        _ex("golden-clean-transfer-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Shuttle 12 uL over from sample tube eight to the qPCR plate.",
            "transfer",
            {"source": "sample_tube_8", "destination": "qpcr_plate", "volume_ul": 12}),
    ],
    "stamp": [
        _ex("golden-clean-stamp-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Stamp the master plate onto the copy plate with 40 microliters per well.",
            "stamp",
            {"source": "master_plate", "destination": "copy_plate", "volume_ul": 40}),
        _ex("golden-clean-stamp-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Copy the whole daughter plate layout onto the assay plate at 30 uL each.",
            "stamp",
            {"source": "daughter_plate", "destination": "assay_plate_v2", "volume_ul": 30}),
        _ex("golden-clean-stamp-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Replicate source plate contents across target plate using 25 microliters.",
            "stamp",
            {"source": "source_plate", "destination": "target_plate", "volume_ul": 25}),
        _ex("golden-clean-stamp-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Stamp dilution series onto test plate, 60 uL per well.",
            "stamp",
            {"source": "dilution_series", "destination": "test_plate", "volume_ul": 60}),
    ],
    "pick_up_tips": [
        _ex("golden-clean-pick_up_tips-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Pick up tips from tip rack 1 position A1.",
            "pick_up_tips", {"at": ["tip_rack_1_A1"]}),
        _ex("golden-clean-pick_up_tips-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Grab fresh tips from the 96 tip rack column 12.",
            "pick_up_tips", {"at": ["tip_rack_96_col12"]}),
        _ex("golden-clean-pick_up_tips-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Get four tips from filter tip box row D positions one through four.",
            "pick_up_tips",
            {"at": ["filter_tip_box_D1", "filter_tip_box_D2", "filter_tip_box_D3",
                    "filter_tip_box_D4"]},
            note="list cardinality exercised"),
        _ex("golden-clean-pick_up_tips-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Pick up a tip from box two, well C4.",
            "pick_up_tips", {"at": ["tip_box_2_C4"]}),
    ],
    "drop_tips": [
        _ex("golden-clean-drop_tips-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Drop the tips into trash.",
            "drop_tips", {"destination": "trash"}),
        _ex("golden-clean-drop_tips-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Drop mounted tips at tip rack 3 position F7.",
            "drop_tips", {"destination": "tip_rack_3_F7"}),
        _ex("golden-clean-drop_tips-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Eject used tips into the waste bin.",
            "drop_tips", {"destination": "waste_bin"}),
        _ex("golden-clean-drop_tips-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Release the tips to disposal rack slot 2.",
            "drop_tips", {"destination": "disposal_rack_slot2"}),
    ],
    "discard_tips": [
        # Clean positives carry only the dispatch-inert `what` noun key:
        # `at` is SYMBOLIC by recorded decision, so mentioning a location
        # makes the example ambiguous-referent class, not clean.
        _ex("golden-clean-discard_tips-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Discard the tips.", "discard_tips", {"what": "tips"},
            note="at kept unmentioned: symbolic slot would flip the class"),
        _ex("golden-clean-discard_tips-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Throw away the mounted tips.", "discard_tips", {"what": "tips"}),
        _ex("golden-clean-discard_tips-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Just discard the current tips.", "discard_tips", {"what": "tips"}),
        _ex("golden-clean-discard_tips-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Please toss the pipette tips.", "discard_tips", {"what": "tips"}),
    ],
    "move_resource": [
        _ex("golden-clean-move_resource-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Move the reagent reservoir to hotel position 3.",
            "move_resource", {"resource": "reagent_reservoir", "destination": "hotel_slot3"}),
        _ex("golden-clean-move_resource-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Shift tube rack 2 onto incubator slot 1.",
            "move_resource", {"resource": "tube_rack_2", "destination": "incubator_slot1"}),
        _ex("golden-clean-move_resource-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Carry the tip boxes over to shelf B.",
            "move_resource", {"resource": "tip_boxes", "destination": "shelf_b"}),
        _ex("golden-clean-move_resource-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Relocate reservoir alpha to the park position.",
            "move_resource", {"resource": "reservoir_alpha", "destination": "park_position"}),
    ],
    "move_plate": [
        _ex("golden-clean-move_plate-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Move plate 2 to the reader.",
            "move_plate", {"plate": "plate_2", "destination": "plate_reader"}),
        _ex("golden-clean-move_plate-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Place assay plate onto the shaker platform.",
            "move_plate", {"plate": "assay_plate", "destination": "shaker_platform"}),
        _ex("golden-clean-move_plate-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Take the waste plate off the deck and put it in storage stack.",
            "move_plate", {"plate": "waste_plate", "destination": "storage_stack"}),
        _ex("golden-clean-move_plate-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Move the PCR plate to hotel one.",
            "move_plate", {"plate": "pcr_plate", "destination": "hotel_1"}),
    ],
    "move_lid": [
        _ex("golden-clean-move_lid-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Put the lid back onto plate 1.",
            "move_lid", {"lid": "plate_1_lid", "destination": "plate_1"}),
        _ex("golden-clean-move_lid-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Move lid 3 to the parking stand.",
            "move_lid", {"lid": "lid_3", "destination": "parking_stand"}),
        _ex("golden-clean-move_lid-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Cover the assay plate with its lid.",
            "move_lid", {"lid": "assay_plate_lid", "destination": "assay_plate"}),
        _ex("golden-clean-move_lid-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Take the lid off plate 4 and rest it on the bench pad.",
            "move_lid", {"lid": "plate_4_lid", "destination": "bench_pad"}),
    ],
    "read_absorbance": [
        _ex("golden-clean-read_absorbance-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Read absorbance at 600 nanometers.",
            "read_absorbance", {"wavelength_nm": 600}),
        _ex("golden-clean-read_absorbance-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Measure OD at 450 nm on wells A1 through A6.",
            "read_absorbance",
            {"wavelength_nm": 450, "at": ["A1", "A2", "A3", "A4", "A5", "A6"]}),
        _ex("golden-clean-read_absorbance-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Check absorbance of column 12 at 595 nm.",
            "read_absorbance",
            {"wavelength_nm": 595,
             "at": ["A12", "B12", "C12", "D12", "E12", "F12", "G12", "H12"]}),
        _ex("golden-clean-read_absorbance-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Do an absorbance read at 340.",
            "read_absorbance", {"wavelength_nm": 340}),
    ],
    "read_fluorescence": [
        _ex("golden-clean-read_fluorescence-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Read fluorescence with excitation at 485 and emission at 528 nanometers, focal height 20 mm.",
            "read_fluorescence",
            {"excitation_nm": 485, "emission_nm": 528, "focal_height_mm": 20}),
        _ex("golden-clean-read_fluorescence-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Measure GFP signal in wells B2 to B6: ex 488, em 533, focal height 18.5 mm.",
            "read_fluorescence",
            {"excitation_nm": 488, "emission_nm": 533, "focal_height_mm": 18.5,
             "at": ["B2", "B3", "B4", "B5", "B6"]}),
        _ex("golden-clean-read_fluorescence-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Fluorescence read on column 3: excite 540, emit 590, focal height 15 mm.",
            "read_fluorescence",
            {"excitation_nm": 540, "emission_nm": 590, "focal_height_mm": 15,
             "at": ["A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3"]}),
        _ex("golden-clean-read_fluorescence-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Run a fluorescence measurement, excitation 360, emission 465, focal plane 10 millimeters.",
            "read_fluorescence",
            {"excitation_nm": 360, "emission_nm": 465, "focal_height_mm": 10}),
    ],
    "read_luminescence": [
        _ex("golden-clean-read_luminescence-01", "train", AmbiguityClass.CLEAN_PARSE,
            "Read luminescence with focal height 10 mm.",
            "read_luminescence", {"focal_height_mm": 10}),
        _ex("golden-clean-read_luminescence-02", "train", AmbiguityClass.CLEAN_PARSE,
            "Measure luminescence across the whole plate at focal height 12.5 mm.",
            "read_luminescence", {"focal_height_mm": 12.5}),
        _ex("golden-clean-read_luminescence-03", "eval", AmbiguityClass.CLEAN_PARSE,
            "Luminescence reading on wells C1 through C12, focal height 9 mm.",
            "read_luminescence",
            {"focal_height_mm": 9, "at": [f"C{i}" for i in range(1, 13)]}),
        _ex("golden-clean-read_luminescence-04", "eval", AmbiguityClass.CLEAN_PARSE,
            "Check glow signal at 7.5 mm focal height.",
            "read_luminescence", {"focal_height_mm": 7.5}),
    ],
}

# ---------------------------------------------------------------------------
# CLASS 1: MISSING SLOT -- real verb, required param(s) absent. Supervision =
# incomplete tool_call with ONLY the stated params (D7); missing_required
# derives deterministically (D11). Sidecar gap fields are injected+asserted
# by the builder (juror finding: NON-EMPTY).
# ---------------------------------------------------------------------------
_MISSING_SLOT: list[GoldenExample] = [
    _ex("golden-missing-slot-01", "eval", AmbiguityClass.MISSING_SLOT,
        "Aspirate 50 microliters.",
        "aspirate", {"volume_ul": 50},
        note="source absent -> missing_required=['source']"),
    _ex("golden-missing-slot-02", "eval", AmbiguityClass.MISSING_SLOT,
        "Aspirate from the lysis buffer.",
        "aspirate", {"source": "lysis_buffer_reservoir"},
        note="volume absent -> missing_required=['volume_ul']; present source still yields an unresolved slot"),
    _ex("golden-missing-slot-03", "eval", AmbiguityClass.MISSING_SLOT,
        "Dispense 100 microliters.",
        "dispense", {"volume_ul": 100},
        note="destination absent"),
    _ex("golden-missing-slot-04", "eval", AmbiguityClass.MISSING_SLOT,
        "Transfer 25 uL from plate A well H12.",
        "transfer", {"source": "plate_A_H12", "volume_ul": 25},
        note="destination absent"),
    _ex("golden-missing-slot-05", "eval", AmbiguityClass.MISSING_SLOT,
        "Do a transfer.",
        "transfer", {},
        note="both required absent, table declaration order ['source','destination']"),
    _ex("golden-missing-slot-06", "eval", AmbiguityClass.MISSING_SLOT,
        "Stamp the master plate onto the copy plate.",
        "stamp", {"source": "master_plate", "destination": "copy_plate"},
        note="volume absent"),
    _ex("golden-missing-slot-07", "eval", AmbiguityClass.MISSING_SLOT,
        "Move plate 2 somewhere else.",
        "move_plate", {"plate": "plate_2"},
        note="destination absent ('somewhere else' carries no groundable value)"),
    _ex("golden-missing-slot-08", "eval", AmbiguityClass.MISSING_SLOT,
        "Pick up some tips.",
        "pick_up_tips", {},
        note="at absent entirely; empty list would count as present (presence-based rule)"),
    _ex("golden-missing-slot-09", "eval", AmbiguityClass.MISSING_SLOT,
        "Read absorbance on column 1.",
        "read_absorbance", {"at": ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"]},
        note="wavelength_nm absent"),
    _ex("golden-missing-slot-10", "eval", AmbiguityClass.MISSING_SLOT,
        "Read fluorescence at 485 excitation and 528 emission.",
        "read_fluorescence", {"excitation_nm": 485, "emission_nm": 528},
        note="focal_height_mm absent"),
    _ex("golden-missing-slot-11", "eval", AmbiguityClass.MISSING_SLOT,
        "Measure luminescence.",
        "read_luminescence", {},
        note="focal_height_mm absent"),
    _ex("golden-missing-slot-12", "eval", AmbiguityClass.MISSING_SLOT,
        "Drop the tips somewhere safe.",
        "drop_tips", {},
        note="destination absent"),
]

# ---------------------------------------------------------------------------
# CLASS 2: AMBIGUOUS REFERENT -- call shape complete, but string-valued
# SYMBOLIC args are deictic/vague references needing cue-2 grounding.
# unresolved_slots derives non-empty; LITERAL args (volumes/wells) unaffected.
# ---------------------------------------------------------------------------
_AMBIGUOUS_REFERENT: list[GoldenExample] = [
    _ex("golden-ambig-ref-01", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Transfer 20 uL from it to the other plate.",
        "transfer", {"source": "it", "destination": "the other plate", "volume_ul": 20},
        note="pronoun + vague definite; container slots x2"),
    _ex("golden-ambig-ref-02", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Dispense 80 uL into there.",
        "dispense", {"destination": "there", "volume_ul": 80},
        note="pure deixis destination"),
    _ex("golden-ambig-ref-03", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Move that plate over to the reader station.",
        "move_plate", {"plate": "that plate", "destination": "the reader station"},
        note="demonstrative plate + underspecified station"),
    _ex("golden-ambig-ref-04", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Pick up tips from the usual rack.",
        "pick_up_tips", {"at": ["the usual rack"]},
        note="session-dependent referent"),
    _ex("golden-ambig-ref-05", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Aspirate 30 uL from the same place as before.",
        "aspirate", {"source": "the same place as before", "volume_ul": 30},
        note="anaphoric place reference"),
    _ex("golden-ambig-ref-06", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Drop the tips where they came from.",
        "drop_tips", {"destination": "where they came from"},
        note="relative-clause destination"),
    _ex("golden-ambig-ref-07", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Stamp it onto the matching plate, 35 microliters.",
        "stamp", {"source": "it", "destination": "the matching plate", "volume_ul": 35},
        note="pronoun source + relational destination"),
    _ex("golden-ambig-ref-08", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Move the lid to wherever it belongs.",
        "move_lid", {"lid": "the lid", "destination": "wherever it belongs"},
        note="bare generic lid + policy-resolved destination"),
    _ex("golden-ambig-ref-09", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Dispense 45 uL into the plate we just talked about.",
        "dispense", {"destination": "the plate we just talked about", "volume_ul": 45},
        note="discourse-deictic destination"),
    _ex("golden-ambig-ref-10", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Transfer 10 uL from column 2 to the corresponding wells of the other plate.",
        "transfer", {"source": "column 2", "destination": "the other plate", "volume_ul": 10},
        note="positional phrase + relational destination"),
    _ex("golden-ambig-ref-11", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Discard the tips at the usual spot.",
        "discard_tips", {"what": "tips", "at": "the usual spot"},
        note="discard_tips.at symbolic by recorded decision"),
    _ex("golden-ambig-ref-12", "eval", AmbiguityClass.AMBIGUOUS_REFERENT,
        "Move the leftover tubes to storage.",
        "move_resource", {"resource": "the leftover tubes", "destination": "storage"},
        note="plural vague resource + underspecified storage"),
]

# ---------------------------------------------------------------------------
# CLASS 3: OUT OF SURFACE -- no phase-2 tool applies (excluded receivers,
# phantom verbs, kernel-internal/state surface, non-lab requests). Supervision
# = NL clarification/refusal turn, NO tool_calls key (D7). Expected calls=[].
# ---------------------------------------------------------------------------
_OUT_OF_SURFACE: list[tuple[GoldenExample, str]] = [
    (("golden-out-surface-01",
      "Turn on the heater shaker to 37 degrees and start shaking."),
     "I can't operate the heater shaker - that equipment isn't wired up for me yet. "
     "I can help with pipetting, moving labware, or running plate reads."),
    (("golden-out-surface-02",
      "Mix my samples for 30 seconds at 500 rpm."),
     "I don't have a mixing action available. I can approximate it with repeated "
     "aspirate-and-dispense steps if you tell me the wells and volumes."),
    (("golden-out-surface-03",
      "Blow out the tips after dispensing."),
     "There's no blow-out action on my tool surface. I can do plain aspirate and "
     "dispense steps if that works for you."),
    (("golden-out-surface-04",
      "Run the PCR thermal cycling protocol."),
     "Thermal cycling isn't something I control. I can move the PCR plate to another "
     "deck position or run plate reads before or after your cycler program."),
    (("golden-out-surface-05",
      "What's the concentration of sample 4?"),
     "I can't read concentrations - I don't have access to sample metadata. "
     "I could run an absorbance measurement if you give me a wavelength."),
    (("golden-out-surface-06",
      "Centrifuge plate 2 at 4000 g."),
     "I have no centrifuge control. I can move plate 2 wherever it needs to be "
     "before and after the spin."),
    (("golden-out-surface-07",
      "Incubate the assay plate at room temperature for 10 minutes."),
     "Timed incubation isn't in my action set - I can't wait on a clock. "
     "I can move the assay plate to an incubator slot now if you like."),
    (("golden-out-surface-08",
      "Open the robot door."),
     "Door and hardware-interlock control is outside what I'm allowed to touch. "
     "Please operate the door from the physical panel."),
    (("golden-out-surface-09",
      "Calibrate the pipette channels."),
     "Channel calibration is maintenance plumbing I don't expose. "
     "If tips are misbehaving I can pick up fresh ones or drop the mounted ones."),
    (("golden-out-surface-10",
      "Show me the deck layout."),
     "I can't render the deck view. From the chat I can move specific plates, "
     "reservoirs, or lids if you name them."),
    (("golden-out-surface-11",
      "Order more tips from the vendor website."),
     "Ordering consumables is outside my scope entirely - I only operate lab "
     "equipment actions like pipetting and plate moves."),
    (("golden-out-surface-12",
      "Email yesterday's absorbance report to the lab manager."),
     "I can't send email. I can run a fresh absorbance read if you give me a "
     "wavelength, and you can export the report yourself."),
]
_OUT: list[GoldenExample] = [
    GoldenExample(
        record_id=rid,
        split="eval",
        ambiguity_class=AmbiguityClass.OUT_OF_SURFACE,
        utterance=utt,
        calls=(),
        assistant_text=text,
    )
    for (rid, utt), text in _OUT_OF_SURFACE
]


def build_corpus() -> list[GoldenExample]:
    """Assemble the full golden corpus with dynamic count assertions.

    Counting DERIVES from ``PHASE2_TOOL_NAMES``: any change upstream
    (promotion/exclusion) breaks this function loudly instead of silently
    shipping a stale golden set (AC-2.1.x 'count derives from reconciled verbs').
    """
    included = sorted(PHASE2_TOOL_NAMES)

    problems: list[str] = []
    for tool in included:
        got = _CLEAN.get(tool, [])
        if len(got) != POSITIVES_PER_TOOL:
            problems.append(f"{tool}: {len(got)} clean positives != {POSITIVES_PER_TOOL}")
    for tool in _CLEAN:
        if tool not in PHASE2_TOOL_NAMES:
            problems.append(f"{tool}: authored positives but NOT in PHASE2_TOOL_NAMES")
    if problems:
        raise AssertionError("golden corpus out of sync with PHASE2_TOOL_NAMES:\n" + "\n".join(problems))

    positives = [ex for tool in included for ex in _CLEAN[tool]]
    clarify = _MISSING_SLOT + _AMBIGUOUS_REFERENT + _OUT

    n_per_class = {cls: 0 for cls in AmbiguityClass.CLARIFY}
    for ex in clarify:
        n_per_class[ex.ambiguity_class] += 1
    bad = {c: n for c, n in n_per_class.items() if n != CLARIFY_PER_CLASS}
    if bad:
        raise AssertionError(f"clarify per-class counts wrong: {bad} (want {CLARIFY_PER_CLASS} each)")
    total_clarify = sum(n_per_class.values())
    if total_clarify < 30:
        raise AssertionError(f"only {total_clarify} clarify examples (<30)")
    eval_clarify = [ex for ex in clarify if ex.split == "eval"]
    if len(eval_clarify) != total_clarify:
        raise AssertionError("ALL clarify examples must be held out (split=eval): D8 sizing")

    corpus = positives + clarify
    ids = [ex.record_id for ex in corpus]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise AssertionError(f"duplicate record_ids: {dupes}")

    _validate_example_shapes(corpus)
    return corpus


def _validate_example_shapes(corpus: list[GoldenExample]) -> None:
    """Structural validation against the canonical tables (loud builder)."""
    for ex in corpus:
        if ex.split not in ("train", "eval"):
            raise AssertionError(f"{ex.record_id}: bad split {ex.split!r}")
        if ex.ambiguity_class not in AmbiguityClass.ALL:
            raise AssertionError(f"{ex.record_id}: bad class {ex.ambiguity_class!r}")

        if ex.ambiguity_class == AmbiguityClass.OUT_OF_SURFACE:
            if ex.calls:
                raise AssertionError(f"{ex.record_id}: out-of-surface must have zero calls")
            if not ex.assistant_text:
                raise AssertionError(f"{ex.record_id}: out-of-surface needs NL clarification text")
            continue

        if not ex.calls or ex.assistant_text is not None:
            raise AssertionError(f"{ex.record_id}: call-class needs exactly tool-call supervision")

        for call in ex.calls:
            rows = params_of(call.name)  # KeyError on unknown/excluded: loud
            known = {spec.name for spec in rows}
            unknown = set(call.params) - known
            if unknown:
                raise AssertionError(f"{ex.record_id}: params outside namespace: {sorted(unknown)}")
            for pname, value in call.params.items():
                spec = next(s for s in rows if s.name == pname)
                if spec.kind is ParamKind.LITERAL and isinstance(value, str):
                    # Literals may be string-valued (positions, noun keys);
                    # numeric literals must arrive numeric though.
                    if spec.name in ("volume_ul", "wavelength_nm", "excitation_nm",
                                     "emission_nm", "focal_height_mm"):
                        raise AssertionError(
                            f"{ex.record_id}: {pname} must be numeric, got {value!r}"
                        )
                if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF:
                    refs = value if isinstance(value, list) else [value]
                    if not all(isinstance(r, str) and r.strip() for r in refs):
                        raise AssertionError(
                            f"{ex.record_id}: symbolic {pname} needs non-empty string ref(s)"
                        )
            gaps = derive_call_gaps(call.name, call.params)
            if ex.ambiguity_class == AmbiguityClass.MISSING_SLOT and not gaps.missing_required:
                raise AssertionError(
                    f"{ex.record_id}: missing-slot example derives EMPTY missing_required"
                )
            if ex.ambiguity_class == AmbiguityClass.AMBIGUOUS_REFERENT:
                if gaps.missing_required:
                    raise AssertionError(
                        f"{ex.record_id}: ambiguous-referent example unexpectedly missing "
                        f"{gaps.missing_required} (keep classes orthogonal)"
                    )
                if not gaps.unresolved_slots:
                    raise AssertionError(
                        f"{ex.record_id}: ambiguous-referent example derives EMPTY unresolved_slots"
                    )
            if ex.ambiguity_class == AmbiguityClass.CLEAN_PARSE and gaps.missing_required:
                raise AssertionError(
                    f"{ex.record_id}: clean-parse example derives missing_required "
                    f"{gaps.missing_required}"
                )
            # NOTE: clean-parse examples MAY derive unresolved_slots -- that is
            # NORMAL. Every string-valued resource arg grounds against live
            # kernel state at dispatch (FR-7); 'clean' means nothing is missing
            # and the authored references are concrete deck names grounding
            # will resolve, versus the deictic/vague phrases of the
            # ambiguous-referent class. The clean/ambiguous line is an
            # authoring (human golden) judgment, recorded in ambiguity_class.


# ---------------------------------------------------------------------------
# FunctionGemma-native tool declarations (research §2a format). Types follow
# the mobile-actions convention observed in the rendered template: uppercase
# OBJECT / STRING / NUMBER / ARRAY. Every row repeats the FULL included-tool
# list, mirroring google/mobile-actions.
# ---------------------------------------------------------------------------

# One human description per SCHEMA param name across tools. Names are reused
# across tools only where the meaning is identical, so a flat map is safe.
def _description_for(spec) -> str:
    return _PARAM_DESCRIPTIONS.get(spec.name, f"The {spec.name.replace('_', ' ')}")


_PARAM_DESCRIPTIONS: dict[str, str] = {
    "source": "The container, well, or plate to take liquid or material from",
    "destination": "The container, well, location, or tip spot to dispense into or drop at",
    "volume_ul": "Volume in microliters",
    "resource": "The deck resource to move",
    "plate": "The plate to move",
    "lid": "The plate lid to move",
    "at": "Tip spots or well positions to act on",
    "what": "What to discard (always tips)",
    "wavelength_nm": "Wavelength in nanometers",
    "excitation_nm": "Excitation wavelength in nanometers",
    "emission_nm": "Emission wavelength in nanometers",
    "focal_height_mm": "Focal height in millimeters",
}

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "aspirate": "Aspirate liquid from a container into the pipette channels.",
    "dispense": "Dispense liquid from the pipette channels into a container.",
    "transfer": "Transfer liquid directly from a source well or container to one or more destinations.",
    "stamp": "Copy liquid from every filled well of a source plate to the same positions on a destination plate.",
    "pick_up_tips": "Pick up pipette tips from the given tip spots.",
    "drop_tips": "Drop the mounted pipette tips into a tip spot or trash location.",
    "discard_tips": "Discard the mounted pipette tips to trash.",
    "move_resource": "Move a deck resource such as a tube rack or reservoir to a new destination.",
    "move_plate": "Move a plate to a new destination such as a reader, hotel, or stack.",
    "move_lid": "Move a plate lid to a new destination such as its plate or a parking stand.",
    "read_absorbance": "Read absorbance of the plate loaded in the plate reader at a wavelength.",
    "read_fluorescence": "Read fluorescence of the loaded plate using excitation and emission wavelengths and focal height.",
    "read_luminescence": "Read luminescence of the loaded plate at a focal height.",
}


def tool_declarations() -> list[dict]:
    """The FULL included-tool declaration list repeated in every row
    (mobile-actions pattern, research §2a). Order: PARAM_NAMESPACE declaration
    order filtered to PHASE2_TOOL_NAMES, stable across runs."""
    from coxswain.plr.param_namespace import PARAM_NAMESPACE

    decls: list[dict] = []
    for name in PARAM_NAMESPACE:
        if name not in PHASE2_TOOL_NAMES:
            continue
        properties: dict[str, dict] = {}
        for spec in PARAM_NAMESPACE[name]:
            properties[spec.name] = {
                "description": _description_for(spec),
                "type": _decl_type(name, spec),
            }
        decls.append({
            "function": {
                "name": name,
                "description": _TOOL_DESCRIPTIONS[name],
                "parameters": {
                    "type": "OBJECT",
                    "properties": properties,
                    "required": list(required_params(name)),
                },
            }
        })
    if {d["function"]["name"] for d in decls} != set(PHASE2_TOOL_NAMES):
        raise AssertionError("tool declarations drifted from PHASE2_TOOL_NAMES")
    return decls


# Params the model genuinely emits as MULTIPLE values in one call (golden
# supervision uses JSON arrays for these). Everything else is emitted scalar:
# notably volume_ul -- vendored `vols`/`target_vols` are List[float], but the
# copilot surface takes ONE user-stated volume and the DISPATCHER wraps it
# (param_namespace note 'dispatcher wraps scalar to [v]'). Declaring ARRAY
# there would teach the model to emit lists the utterances never contain.
DECLARED_ARRAY_PARAMS: frozenset[tuple[str, str]] = frozenset({
    ("pick_up_tips", "at"),
    ("read_absorbance", "at"),
    ("read_fluorescence", "at"),
    ("read_luminescence", "at"),
})


def _decl_type(tool_name: str, spec) -> str:
    if (tool_name, spec.name) in DECLARED_ARRAY_PARAMS:
        return "ARRAY"
    lowered = spec.plr_type.lower()
    if "float" in lowered or "int" in lowered:
        return "NUMBER"
    return "STRING"

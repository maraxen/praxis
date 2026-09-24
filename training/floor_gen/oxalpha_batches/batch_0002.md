# ox-alpha NL-ification batch 2 (8 items)

prompt_version=p23_nlify_v1

You are one of several spawned ox-alpha workers producing teacher text for the
Coxswain P2.3 coverage floor. For EACH item below, read `system` and `user`,
compose the assistant reply exactly per the output contract, then APPEND one
line to `responses.jsonl` next to your batch file:

{"input_hash": "<item input_hash>", "response": <your reply as a JSON string>}

Rules:
- `response` is the EXACT assistant text (a single JSON object per the
  contract) serialized as a JSON string. No markdown fences around it.
- One line per item, keyed by `input_hash`. Do not reorder, do not merge.
- Do not edit any other field or file.

Output contract (verbatim):
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 16 (input_hash=d65501886981e8eba4d3acb87a776f125972b611d8037f8bcfe881f07aaef97e) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_B1"},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'volume_ul' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 17 (input_hash=11cf763b5cd0e7b172c1efbd8d7f6955456f1167dc0103c73be7f39277cd6833) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_1_G12"},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'volume_ul' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 18 (input_hash=d08ee1e2aaa33ea66946d2f275a8ae19609b49a1249954428d52181974d7f7ef) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"the destination well","vols":[20.0]},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'destination' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 19 (input_hash=0f09221966c64225a08998f60d618edc353dd392967c91c4856e65ee8cc54774) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"the same well","vols":[20.0]},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'destination' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 20 (input_hash=5e621983f17b4a39fc6255179b1f4f321a7eba3273027c8e837210ff2ef82dc0) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"the destination well","vols":[200.0]},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'destination' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 21 (input_hash=2c48c9b41a4004144a763dce0a2847025a2af840553573f96788078b1aea3d8d) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to blow out the remaining droplets from the tips after dispensing
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 22 (input_hash=5c049b4f42384e8f8bc9313c2dd8bec0fd6d9a025329da3ecd8711eb3287e424) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to blow out the remaining droplets from the tips after dispensing
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 23 (input_hash=86916ca6856afcbd546afe4f02b020e7fe2f4183ac5128df6b59359abc5aee1d) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to blow out the remaining droplets from the tips after dispensing
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.

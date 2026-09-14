# ox-alpha NL-ification batch 1 (8 items)

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


--- ITEM 8 (input_hash=2bb6eedfba3ffacffef0f48decafe6f2ef8112b261cc8b78a9794a67269a0cd5) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"the same well","vols":[200.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'source' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 9 (input_hash=e5b3ade46330dd843003fcdb0df8a0dde8ceeab184e1b9ee87c6a50454a4ab0e) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to mix the liquid in a well up and down before transferring it
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 10 (input_hash=f3721c8e6666682b90f6df1f8c0a67d3719d861a1ba88206eae23d3f86258565) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to mix the liquid in a well up and down before transferring it
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 11 (input_hash=0f22bce5571676862b0000ccd494fb9a66f801cdfdc4717643b9acebb1dad494) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to mix the liquid in a well up and down before transferring it
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 12 (input_hash=574825c38a3d267f4826306ff42e4f1bb3273bd99e173cced8312010bff726cb) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_B9","vols":[50.0]},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 13 (input_hash=789667ff1c8a07cb6117db69a2cf99f67964da9c406d74f77385649d99c21d35) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_A2","vols":[200.0,200.0,15.0]},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 14 (input_hash=836640d830bfa5712d758abfe4d86c2a3f0a7690b2f6efb26de2a2a75e804d63) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_A7","vols":[50.0]},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 15 (input_hash=3efcfb2ebba0497a38f54f60d27bf09ffcbc614632cf95d09c7873347cfd6c56) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=dispense__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Dispense liquid from the pipette channels into destination containers. Volumes are in microliters (uL).","name":"dispense","parameters":{"properties":{"destination":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["destination","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_1_G1"},"name":"dispense"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'volume_ul' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.

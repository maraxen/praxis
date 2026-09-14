# ox-alpha NL-ification batch 3 (8 items)

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


--- ITEM 24 (input_hash=ddd6d27e0d87b5c265ee31b30a33e86945bb4315bab4fd6d509f9d4f301b0507) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"source":"plate_1_C7","targets":["plate_2_E3","plate_1_H9"]},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 25 (input_hash=2a2a2c820b157cf712641cb6973d4de4667221655efc6348d40993dd7dbc557c) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"source":"plate_2_B8","target_vols":[10.0],"targets":["plate_1_G6"]},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 26 (input_hash=7d9853399e4a5aa322acf41a364453f5a1b15f8edac9e18756eb837e6054aaef) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"source":"plate_1_D2","target_vols":[200.0],"targets":["plate_1_F1","plate_2_G4"]},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 27 (input_hash=653dbdf9103b88ffe1185ca2e40f7d0f8deee3b3ec610155dfa98157acfb7522) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"target_vols":[200.0],"targets":["plate_1_D11","plate_2_A1"]},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'source' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 28 (input_hash=d718baa11f489f6093fb613b1a277e41744b86ae39dca35f402b0d104f574695) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"target_vols":[10.0],"targets":["plate_1_B7","plate_2_D11"]},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'source' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 29 (input_hash=d320cffad2d1224d0f2900af8283391fd5057e0dd96a2896aaeaec51aad90e67) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"target_vols":[20.0],"targets":["plate_1_D4"]},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'source' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 30 (input_hash=e6534ab84abbb8726c1a321d51075b2c09e625518607498841016f7dc0f5d2cf) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"source":"plate_1_C5","targets":"the source well"},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'destination' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 31 (input_hash=29386d2b6c8c0f009a3bfc5fb8f4a5c720dd93efc69cf1d7b1c299484c7a3030) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"source":"plate_2_B3","target_vols":[20.0],"targets":"the same well"},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'destination' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.

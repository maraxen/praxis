# ox-alpha NL-ification batch 0 (8 items)

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


--- ITEM 0 (input_hash=4aa609cbca863dd7edf3937ed37c7f943dfabfe3fe04f4671968f2c7275e287e) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_A3","vols":[10.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 1 (input_hash=25fc9b5e85997a1150b1872ea40434596861f029c78cb3c05aa601c7d692bb8b) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_B4","vols":[200.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 2 (input_hash=9fb485bfbacfc41b7e030384c0a0c178e83b4e91a1a92ed8aedd89e6df69b05a) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__none):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"plate_2_C4","vols":[50.0,75.0,20.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural, specific user utterance asking for EXACTLY this call. Mention every parameter: quantities as '<n> microliters', locations using the given names/positions verbatim.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 3 (input_hash=d484da56c37edd721f9b0029e3e9de23c829b0b6667fb5c3486c2ef354d8cd02) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"vols":[10.0,10.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'source' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 4 (input_hash=4906e776b3d756258203c6bb3470d1334667e7ffbe1a3a49a88d596449a72f7f) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"vols":[20.0,150.0,15.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'source' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 5 (input_hash=105fff8bdd7d26141e8e9a250386b3b94e5be9619192611dc3946adc48372939) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__missing-slot):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"vols":[25.0,10.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance that requests this call but OMITS the parameter 'source' entirely -- never mention it, never hint at a value for it. All other parameters MUST appear naturally.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 6 (input_hash=048a1f30fa2be243d6329cbdc0594dfcb1b18805e4ee29dadbc084c7edf62238) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"the same well","vols":[15.0,20.0,100.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'source' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 7 (input_hash=2d7bd8b0c6b08a9771f6b00973264ca4f4f26906edc47e47883df07d877c090f) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=aspirate__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Aspirate liquid from source containers into the pipette channels. Volumes are in microliters (uL).","name":"aspirate","parameters":{"properties":{"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","volume_ul"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"resources":"the source well","vols":[15.0,100.0]},"name":"aspirate"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'source' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.

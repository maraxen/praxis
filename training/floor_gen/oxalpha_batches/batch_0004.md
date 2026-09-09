# ox-alpha NL-ification batch 4 (4 items)

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


--- ITEM 32 (input_hash=e4ebda153e40f65a746c03786b56fe85fc5b994011001c400124a3539f36f001) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, cell=transfer__ambiguous-referent):
Tool declaration for this row (FunctionGemma shape):
{"description":"Transfer liquid from a source well to one or more destination wells in one motion. The volume is the dispense target per destination, in microliters (uL).","name":"transfer","parameters":{"properties":{"destination":{"items":{"type":"string"},"type":"array"},"source":{"type":"string"},"volume_ul":{"items":{"type":"number"},"type":"array"}},"required":["source","destination"],"type":"object"}}
Structured call(s) to NL-ify (corpus-B keyword style kwargs):
{"calls":[{"kwargs":{"source":"plate_2_F2","targets":"the same well"},"name":"transfer"}]}
Value-format conventions (volumes uL floats; wells A1-style):
{"ambiguous_references": {"examples": ["the plate", "the same well", "the source well", "the destination well"], "style": "short vague noun phrases; only in ambiguous-referent cells"}, "deck_resource_names": {"examples": ["plate_1_A3", "tip_rack_2_A4", "reservoir_1"], "style": "lowercase snake_case stable ids resolvable by grounding"}, "volumes": {"example": 50.0, "json_type": "float", "rule": "positive finite floats; spoken/written as 'microliters' in utterances", "unit": "uL"}, "well_references": {"example": "B3", "regex": "^([A-H])(10|11|12|[1-9])$", "style": "uppercase <row A-H><col 1-12>, e.g. A1 / B12"}}
Instruction:
Write a natural user utterance requesting this call, but refer to the 'destination' argument ONLY with a vague phrase such as 'the plate' -- NEVER its concrete id. All other parameters appear normally and concretely.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 33 (input_hash=819ff2a47927440fed88a9a3f3cf5f1a479f7030ca3a512543161569d7952816) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to touch the tip ends against the well walls to shed droplets
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 34 (input_hash=14fae25bb7205dc8f6a872a9fa09bb3b30f535a134141d80c96a3cdaf13c66e3) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to touch the tip ends against the well walls to shed droplets
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.


--- ITEM 35 (input_hash=03de7bf6055e98956c678c63fb9b739c218e76c902c9b594509d0b9389dc1fc4) ---
system:
You are a data-generation teacher for a liquid-handling lab copilot (FunctionGemma training corpus, coverage floor). You convert structured tool calls into realistic single-turn user utterances under exact ambiguity-class constraints. You follow the output contract literally.

user:
Task context (prompt_version=p23_nlify_v1, class=out-of-surface):
Off-surface request seed: user asks to touch the tip ends against the well walls to shed droplets
Supported tools (for the alternative offer): aspirate, discard_tips, dispense, drop_tips, move_lid, move_plate, move_resource, pick_up_tips, read_absorbance, read_fluorescence, read_luminescence, stamp, transfer
The request below is OUTSIDE the supported tool surface. Write (1) a natural user utterance asking for it, and (2) 'clarification': a short friendly assistant reply that says the request is not something the lab copilot can do, and offers the closest supported alternative from the tool list if one exists. Do NOT invent any tool call.
Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no code fences, no commentary. Shape:
{"utterance": "<the user utterance>", "clarification": <string or null>}
"utterance": one single-turn user message, quoted speech only.
"clarification": null unless instructions below require an assistant clarification turn.

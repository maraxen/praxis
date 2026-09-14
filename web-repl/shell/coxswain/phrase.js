// phrase.js -- FR-3's derive_phrase, browser side. The exact mirror of
// coxswain/src/coxswain/phrase.py; both implementations must agree on the
// SAME fixtures in coxswain/tests/fixtures/parsed_calls/*.json. Parity is
// asserted from BOTH directions: this directory's phrase.test.js reads those
// fixtures directly, and test_phrase_parity.py evaluates THIS file in a live
// bun subprocess.
//
// Rules, exhaustively (spec FR-3):
// - verb -- the schema's verb field for the call, lowercased (never the raw
//   function name; unknown names refuse loudly via schemaVerb).
// - object phrase -- a resolved resource/location descriptor, never a
//   quantity: numbers and booleans in descriptor slots throw.
// - multi-target -- first target in as-given order + ` +<n-1> more`.
// - length -- capped at PHRASE_MAX_CHARS; overflow truncates the DESCRIPTOR
//   on a word boundary and the phrase is regenerated from the truncated form,
//   so the string the user types is exactly the string rendered.
//
// DOM-free (NFR-3), zero dependencies.

/** Mirrors plr.tool_schema.TOOL_SCHEMA verbs. phrase.test.js asserts this
 * table against every fixture, and the pytest side asserts fixtures against
 * the live Python schema -- one glued chain, no silent drift. */
export const VERBS = Object.freeze({
  read_absorbance: "read",
  read_fluorescence: "read",
  read_luminescence: "read",
  drop_tips: "drop",
  discard_tips: "discard",
  dispense_to_waste: "discard",
  pick_up_tips: "pick up",
  aspirate: "aspirate from",
  dispense: "dispense to",
  transfer: "transfer to",
  stamp: "stamp onto",
  mix: "mix",
  blow_out: "blow out",
  touch_tip: "touch",
  move_resource: "move",
  move_plate: "move",
  move_lid: "move",
  set_temperature: "set",
  shake: "start",
  stop_shaking: "stop",
});

export const PHRASE_MAX_CHARS = 60;

export const TARGET_KEYS = Object.freeze([
  "destination",
  "destinations",
  "target",
  "targets",
  "to",
  "at",
  "location",
  "source",
]);

export const NOUN_KEYS = Object.freeze(["what", "noun", "object"]);

const FIXED_CONNECTOR = " at ";

export function schemaVerb(name) {
  if (typeof name !== "string" || !(name in VERBS)) {
    throw new Error(`no tool schema entry for ${JSON.stringify(name)}`);
  }
  return VERBS[name];
}

function callFields(call) {
  if (call === null || typeof call !== "object") {
    throw new Error("derivePhrase requires a call object with verb/name and params");
  }
  let verb = typeof call.verb === "string" ? call.verb : null;
  if (verb === null && call.name !== undefined) {
    verb = schemaVerb(call.name);
  }
  if (typeof verb !== "string") {
    throw new Error(
      "derivePhrase requires a schema verb string -- never derive a phrase from a raw function name"
    );
  }
  const params =
    call.params && typeof call.params === "object" && !Array.isArray(call.params)
      ? call.params
      : {};
  return { verb, params };
}

function firstPresent(keys, params) {
  for (const key of keys) {
    const value = params[key];
    if (value !== undefined && value !== null) return value;
  }
  return undefined;
}

function descriptor(value) {
  if (typeof value === "string") return value;
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    // KernelInstance shape: prefer position, fall back to name.
    if (typeof value.position === "string" && value.position.trim()) return value.position;
    if (typeof value.name === "string" && value.name.trim()) return value.name;
  }
  throw new Error(
    `quantities and booleans never appear in a confirmation phrase (FR-3); got ${String(value)}`
  );
}

/** Word-boundary truncation for REGENERATED phrases: no ellipsis here -- the
 * output must stay exactly typeable (FR-3). Render-side truncation with an
 * ellipsis lives in text.js instead (NFR-7). */
function truncateWords(text, budget) {
  if (text.length <= budget) return text;
  if (budget <= 0) {
    throw new Error(
      `cannot fit a confirmation phrase within ${PHRASE_MAX_CHARS} chars`
    );
  }
  const head = text.slice(0, budget);
  const cut = head.lastIndexOf(" ");
  if (cut <= 0) return text.slice(0, budget).replace(/\s+$/, "");
  return head.slice(0, cut).replace(/\s+$/, "");
}

export function derivePhrase(call) {
  const { verb, params } = callFields(call);
  const lowered = verb.toLowerCase();

  const nounValue = firstPresent(NOUN_KEYS, params);
  const noun = nounValue === undefined ? "" : descriptor(nounValue);

  let targets = [];
  const targetValue = firstPresent(TARGET_KEYS, params);
  if (targetValue !== undefined) {
    const items = Array.isArray(targetValue) ? targetValue : [targetValue];
    targets = items.map(descriptor);
  }

  const assemble = (desc) => {
    let obj = noun ? `${noun}${FIXED_CONNECTOR}${desc}` : desc;
    if (targets.length > 1) obj += ` +${targets.length - 1} more`;
    return `${lowered} ${obj}`;
  };

  if (targets.length === 0) return lowered;

  const first = targets[0];
  const phrase = assemble(first);
  if (phrase.length <= PHRASE_MAX_CHARS) return phrase;
  const fixedSuffixLen = phrase.length - first.length;
  return assemble(truncateWords(first, PHRASE_MAX_CHARS - fixedSuffixLen));
}

/** FR-3 matching normalization, exhaustively: trim ends, collapse internal
 * whitespace to single spaces, case-fold. NOTHING ELSE. */
export function normalizePhrase(value) {
  if (typeof value !== "string") return "";
  return value.split(/\s+/).filter(Boolean).join(" ").toLowerCase();
}

export function phraseMatches(typed, required) {
  if (typeof typed !== "string" || typeof required !== "string") return false;
  return normalizePhrase(typed) === normalizePhrase(required);
}

// ids.js -- browser-side mirror of coxswain/src/coxswain/ids.py (§2.1).
//
// Field names and formats are normative: turn_id is
// `cx-<epoch_ms>-<6 chars base36>` and is minted ONCE per user command
// submission, at input capture in coxswain-shell.js, BEFORE any parse or
// grounding work starts (§2.2 point 1). The parse worker and the kernel echo
// it unchanged; nothing downstream ever mints one.
//
// DOM-free (NFR-3), zero dependencies, unit-testable with bun test. Randomness
// is injectable so tests are deterministic; the default path uses
// crypto.getRandomValues when available and falls back to Math.random only as
// a last resort (RISK-12 treats collision risk seriously; epoch-ms plus six
// base36 chars is the specified budget).

const BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz";
export const TURN_ID_RANDOM_CHARS = 6;

function randomBase36(length, randomChar) {
  if (randomChar) {
    let out = "";
    for (let i = 0; i < length; i += 1) out += randomChar();
    return out;
  }
  const cryptoObj = typeof globalThis.crypto !== "undefined" ? globalThis.crypto : null;
  if (cryptoObj && typeof cryptoObj.getRandomValues === "function") {
    const bytes = new Uint8Array(length);
    cryptoObj.getRandomValues(bytes);
    let out = "";
    for (let i = 0; i < length; i += 1) out += BASE36_ALPHABET[bytes[i] % 36];
    return out;
  }
  let out = "";
  for (let i = 0; i < length; i += 1) {
    out += BASE36_ALPHABET[Math.floor(Math.random() * 36)];
  }
  return out;
}

/** Mint a conversation-turn identifier: `cx-<epoch_ms>-<6 base36 chars>`. */
export function mintTurnId({ nowMs = null, randomChar = null } = {}) {
  const epochMs = nowMs === null ? Date.now() : nowMs;
  return `cx-${epochMs}-${randomBase36(TURN_ID_RANDOM_CHARS, randomChar)}`;
}

/** Tab-scoped session id (§2.1), minted once per tab session at panel init. */
export function mintSessionId({ nowMs = null, randomChar = null } = {}) {
  const epochMs = nowMs === null ? Date.now() : nowMs;
  return `cx-sess-${epochMs}-${randomBase36(8, randomChar)}`;
}

/** Per-fingerprint-capture id: `<turn_id>:<gate_seq>:fp` (§2.1). */
export function fingerprintIdFor(turnId, gateSeq) {
  return `${turnId}:${gateSeq}:fp`;
}

/** Per-override-use id: `<turn_id>:<gate_seq>:ovr` (§2.1). */
export function overrideIdFor(turnId, gateSeq) {
  return `${turnId}:${gateSeq}:ovr`;
}

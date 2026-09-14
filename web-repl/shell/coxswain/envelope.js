// §2.2 envelope contract for the `praxis_coxswain` channel -- DOM-free
// (NFR-3), zero dependencies (NFR-3/AC-3), unit-testable with bun test.
//
// Every turn-scoped message carries { v, session_id, turn_id, kind, seq, ts,
// payload }. A turn-scoped message missing turn_id is rejected LOUDLY here --
// never defaulted or auto-minted downstream. Exactly two session-scoped kinds
// (the §4.6 handshake) may carry turn_id: null; the exemption is this
// whitelist, not a nullable field, so it cannot widen by accident. No
// session-scoped message may carry a payload.

export const ENVELOPE_VERSION = 1;

/** The only kinds allowed to carry `turn_id: null` (§4.6 handshake). */
export const SESSION_SCOPED_KINDS = ["coxswain.hello", "coxswain.hello_ack"];

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Validate an inbound or outbound envelope.
 * @returns {{ ok: true, envelope: object } | { ok: false, errors: string[] }}
 */
export function validateEnvelope(message) {
  const errors = [];
  if (!isPlainObject(message)) {
    return { ok: false, errors: [`envelope is not an object: ${typeof message}`] };
  }

  if (message.v !== ENVELOPE_VERSION) {
    errors.push(`envelope v must be ${ENVELOPE_VERSION}, got ${JSON.stringify(message.v)}`);
  }
  if (typeof message.session_id !== "string" || message.session_id.length === 0) {
    errors.push("session_id must be a non-empty string");
  }
  if (typeof message.kind !== "string" || message.kind.length === 0) {
    errors.push("kind must be a non-empty string");
  }
  if (!Number.isInteger(message.seq) || message.seq < 0) {
    errors.push("seq must be a non-negative integer");
  }
  if (typeof message.ts !== "number" || !Number.isFinite(message.ts)) {
    errors.push("ts must be a finite number");
  }

  const sessionScoped = SESSION_SCOPED_KINDS.includes(message.kind);

  if (message.turn_id === undefined) {
    // Loud rejection: never default or auto-mint downstream (§2.2 point 2).
    errors.push("turn_id is required on every turn-scoped envelope and may not be omitted");
  } else if (message.turn_id === null) {
    if (!sessionScoped) {
      errors.push(
        `turn_id may be null only for session-scoped kinds ${JSON.stringify(SESSION_SCOPED_KINDS)}, got kind "${message.kind}"`
      );
    }
  } else if (typeof message.turn_id !== "string" || message.turn_id.length === 0) {
    errors.push("turn_id must be a non-empty string or null (session-scoped kinds only)");
  }

  if (message.payload !== undefined) {
    if (!isPlainObject(message.payload)) {
      errors.push("payload, when present, must be an object");
    } else if (sessionScoped && Object.keys(message.payload).length > 0) {
      // §2.2 point 3: no session-scoped message may carry a payload that can
      // cause any physical action or any audit write.
      errors.push(`session-scoped kind "${message.kind}" must not carry a payload`);
    }
  }

  return errors.length > 0 ? { ok: false, errors } : { ok: true, envelope: message };
}

/**
 * Build an envelope, throwing loudly on invalid input.
 * Session-scoped kinds are normalized to turn_id: null with no payload.
 */
export function buildEnvelope({ session_id, turn_id, kind, seq, ts, payload }) {
  const sessionScoped =
    typeof kind === "string" && SESSION_SCOPED_KINDS.includes(kind);
  // Session-scoped kinds carry turn_id: null and no payload field at all.
  const envelope = sessionScoped
    ? { v: ENVELOPE_VERSION, session_id, turn_id: null, kind, seq, ts }
    : { v: ENVELOPE_VERSION, session_id, turn_id, kind, seq, ts };
  if (!sessionScoped && payload !== undefined) {
    envelope.payload = payload;
  }
  const result = validateEnvelope(envelope);
  if (!result.ok) {
    throw new Error(`coxswain envelope rejected loudly: ${result.errors.join("; ")}`);
  }
  return result.envelope;
}

/**
 * Receiver-side loud path: throws instead of returning a result object.
 * Receivers log + surface the failure as a system line (§2.2 point 2).
 */
export function assertValidEnvelope(message) {
  const result = validateEnvelope(message);
  if (!result.ok) {
    throw new Error(`coxswain envelope rejected loudly: ${result.errors.join("; ")}`);
  }
  return result.envelope;
}

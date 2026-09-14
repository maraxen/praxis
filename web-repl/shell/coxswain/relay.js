// relay.js -- best-effort transduction_log relay (W5).
//
// Contract (FR-9 fourth clause, AC-10, AC-19 third assertion, RISK-10):
//   - ACTIVE ONLY when a relay endpoint was configured AT BUILD TIME via
//     relay_config.js (build_repl.py --coxswain-relay-endpoint rewrites the
//     STAGED copy). The tracked default is null.
//   - UNCONFIGURED => ZERO network calls. Not "fewer", zero: enqueue is a
//     no-op and flush never constructs a request. A static offline-first
//     product must not grow network calls by accident.
//   - FIRE-AND-FORGET: enqueue returns immediately; flush is detached. This
//     module is NEVER in the ack path -- audit_store.js does not reference it
//     (asserted structurally in __tests__/relay.test.js) -- so its latency
//     can never be observable in any disposition.
//   - QUEUE-AND-DROP on failure: a failed flush drops its batch (counted),
//     it is not retried forever; the queue itself is bounded, dropping oldest
//     under overflow. Best effort means exactly that.
//   - Failures surface as a VISIBLE FAILURE COUNTER IN A DEBUG LINE --
//     debugLine(), rendered by whoever owns the panel's debug strip -- never
//     a toast, never a modal.
//
// §7 honesty: no receiver service is specified or known to exist. With the
// tracked default config this module ships permanently inert, which the spec
// accepts explicitly.

import { RELAY_ENDPOINT } from "./relay_config.js";

/** Upper bound on queued-but-unrelayed records. Small on purpose: this is a
 * fire-and-forget side channel, not a durability layer -- the local store is
 * the source of truth (N6). */
export const RELAY_QUEUE_CAP = 256;

/**
 * @param {object} [options]
 * @param {string | null} [options.endpoint] build-time configured endpoint.
 * @param {typeof fetch} [options.fetchImpl] injectable for tests.
 * @param {number} [options.queueCap]
 */
export function createRelay({
  endpoint = RELAY_ENDPOINT,
  fetchImpl = globalThis.fetch,
  queueCap = RELAY_QUEUE_CAP,
} = {}) {
  const configured = typeof endpoint === "string" && endpoint.length > 0;
  /** @type {object[]} */
  let queue = [];
  let failures = 0;
  let relayed = 0;
  let dropped = 0;
  /** @type {Promise<void> | null} */
  let inflight = null;
  let scheduled = false;

  async function flush() {
    if (inflight !== null) {
      await inflight.catch(() => {});
      if (queue.length > 0) return flush();
      return;
    }
    if (!configured || queue.length === 0) {
      return;
    }
    const batch = queue.splice(0, queue.length);
    inflight = (async () => {
      try {
        if (typeof fetchImpl !== "function") {
          // No fetch available (hardened pages): count once and drop.
          dropped += batch.length;
          failures += 1;
          return;
        }
        const response = await fetchImpl(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ records: batch }),
        });
        if (!response.ok) {
          throw new Error(`relay endpoint answered HTTP ${response.status}`);
        }
        relayed += batch.length;
      } catch {
        // Queue-and-drop: no retry storm, no unhandled rejection, no toast.
        failures += 1;
        dropped += batch.length;
      } finally {
        inflight = null;
      }
    })();
    await inflight;
  }

  return {
    /** True iff an endpoint was configured at build time. */
    get isConfigured() {
      return configured;
    },

    get pendingCount() {
      return queue.length;
    },

    get failureCount() {
      return failures;
    },

    /** The debug-line rendering of relay state (AC-19/AC-10 surfacing). */
    debugLine() {
      if (!configured) {
        return "relay: unconfigured at build time (zero network calls by design)";
      }
      return (
        `relay: endpoint=${endpoint} queued=${queue.length} ` +
        `relayed=${relayed} dropped=${dropped} failures=${failures}`
      );
    },

    /**
     * Hand one record to the relay. Returns immediately ({queued:false} when
     * unconfigured). NEVER throws, NEVER blocks, NEVER touches the ack path.
     * Delivery is deferred one microtask so same-tick records coalesce into
     * one batch.
     */
    enqueue(record) {
      if (!configured) {
        return { queued: false };
      }
      if (queue.length >= queueCap) {
        queue.shift();
        dropped += 1;
      }
      queue.push(record);
      if (!scheduled) {
        scheduled = true;
        queueMicrotask(() => {
          scheduled = false;
          void flush();
        });
      }
      return { queued: true };
    },

    async flush() {
      return flush();
    },

    /**
     * Attempt delivery of everything currently queued as ONE POST batch.
     * Resolves undefined on every outcome; failures only bump counters. When
     * a flush is already in flight, resolves after it and any records it
     * left behind have been attempted too. Safe to await from tests.
     */
  };
}

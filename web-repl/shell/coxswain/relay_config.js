// Build-time configuration for the transduction_log relay (W5 / FR-9 / §7).
//
// THIS FILE IS THE BUILD-TIME SEAM. The tracked default is `null`: every
// stock build takes the zero-network path and the relay ships permanently
// inert -- there is no receiver service specified or known to exist (§7),
// which is an accepted MVP outcome, NOT "configured but idle".
//
// `web-repl/scripts/build_repl.py --coxswain-relay-endpoint <url>` rewrites
// ONLY THE STAGED COPY of this file under dist/ with the endpoint baked in.
// The tracked file stays null so a default build can never grow network
// calls by accident (AC-10 / RISK-10).

export const RELAY_ENDPOINT = null;

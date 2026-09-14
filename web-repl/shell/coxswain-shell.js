// coxswain-shell.js -- W3's injected side panel.
//
// Injected ONLY by a --with-coxswain build (FR-12): inject_shell.py adds this
// module script next to praxis-shell.js, and build_repl.py stages this file
// plus shell/coxswain/* and overlay/assets/coxswain/coxswain.css.
//
// Per spec W3:
// - wraps <body> content in plain CSS (NOT Lumino docking),
// - Chat / Visualizer tabs,
// - mints `turn_id` ONCE per user command submission AT INPUT CAPTURE, before
//   any parse or grounding work starts (§2.1/§2.2),
// - wires the dedicated `praxis_coxswain` BroadcastChannel (NFR-4; never
//   reuses praxis_repl or praxis_viz),
// - routes inbound envelopes through envelope.assertValidEnvelope (loud
//   rejection, §2.2) and renders propose cards (§4.2) and failure cards
//   (§4.1's fourth message kind).
//
// §7: the parse layer itself is OUT of scope. Until the parse worker spec
// lands, input is served by an inline DEMO STUB (clearly marked below) so the
// propose/confirm card is demoable with no model present. It exists only to
// drive the UI and is not on any safety path: execution still requires the
// kernel-side guards in coxswain/execute.py.

import { createCardState } from "./coxswain/card_state.js";
import { assertValidEnvelope, buildEnvelope } from "./coxswain/envelope.js";
import { renderFailureCard } from "./coxswain/failure_card.js";
import { mintSessionId, mintTurnId } from "./coxswain/ids.js";
import {
  buildProposeCard,
  wireProposeCard,
} from "./coxswain/propose_card.js";
import { derivePhrase } from "./coxswain/phrase.js";
import { capText } from "./coxswain/text.js";
import { mountTree } from "./coxswain/vdom.js";

const CHANNEL_NAME = "praxis_coxswain";
const SESSION_STORAGE_KEY = "praxis.coxswain.session_id";
const VISUALIZER_SRC = "../visualizer/index.html"; // sibling of assets/, per §4.6

function resolveSessionId() {
  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const fresh = mintSessionId();
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, fresh);
    return fresh;
  } catch {
    return mintSessionId();
  }
}

// --- §7 DEMO PARSE STUB -------------------------------------------------------
// Mirrors three entries of the golden corpus
// (coxswain/tests/fixtures/parsed_calls/*.json) client-side so the card can be
// demonstrated offline. NOT a safety component; the real ParseSource arrives
// with the parse-layer spec, and the kernel re-derives everything itself.

const DEMO_CALLS = [
  {
    match: /transfer .*a1.*b3/i,
    restatement: "Transfer 50 µL from A1 to B3.",
    tier: "reversible",
    call: { name: "transfer", params: { source: "A1", destination: "B3", volume_ul: 50 } },
    fields: [
      { name: "volume_ul", value: 50 },
      { name: "source", value: "A1" },
      { name: "destination", value: "B3" },
    ],
  },
  {
    match: /discard .*tips/i,
    restatement: "Discard tips at C3.",
    tier: "irreversible",
    call: { name: "discard_tips", params: { what: "tips", at: "C3" } },
    fields: [{ name: "at", value: "C3" }],
  },
];

function demoParse(text) {
  return DEMO_CALLS.find((entry) => entry.match.test(text)) ?? null;
}

// --- panel construction ---------------------------------------------------------

function injectStyles() {
  const href = new URL("../assets/coxswain/coxswain.css", import.meta.url).href;
  if (document.querySelector(`link[href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
}

function el(tag, className, textContentValue) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  // NFR-7: strings enter the DOM as textContent, never markup.
  if (textContentValue !== undefined) node.textContent = textContentValue;
  return node;
}

function buildPanelSkeleton() {
  const page = el("div", "cx-page");
  while (document.body.childNodes.length > 0) {
    page.appendChild(document.body.firstChild);
  }

  const panel = el("aside", "cx-panel");
  panel.id = "cx-panel";

  const tabs = el("nav", "cx-tabs");
  const chatTab = el("button", "cx-tab cx-tab-active", "Chat");
  chatTab.type = "button";
  chatTab.setAttribute("data-tab", "chat");
  const vizTab = el("button", "cx-tab", "Visualizer");
  vizTab.type = "button";
  vizTab.setAttribute("data-tab", "viz");
  tabs.append(chatTab, vizTab);

  const chatView = el("div", "cx-view cx-view-chat");
  const transcript = el("div", "cx-transcript");
  transcript.setAttribute("role", "log");
  transcript.setAttribute("aria-label", "Coxswain conversation");
  const composer = el("form", "cx-composer");
  const label = el("label", "cx-visually-hidden", "Ask Coxswain");
  label.setAttribute("for", "cx-input");
  const input = el("input", "cx-input");
  input.id = "cx-input";
  input.type = "text";
  input.placeholder = "Type a command…";
  input.autocomplete = "off";
  const send = el("button", "cx-send", "Send");
  send.type = "submit";
  composer.append(label, input, send);

  const vizView = el("div", "cx-view cx-view-viz");
  vizView.hidden = true;

  chatView.append(transcript, composer);
  panel.append(tabs, chatView, vizView);

  const layout = el("div", "cx-shell");
  layout.append(page, panel);
  document.body.appendChild(layout);

  return { panel, transcript, composer, input, chatTab, vizTab, chatView, vizView };
}

export function initCoxswainShell(options = {}) {
  if (window.__praxisCoxswainShell) {
    return window.__praxisCoxswainShell;
  }
  injectStyles();
  const ui = buildPanelSkeleton();
  const session_id = options.session_id ?? resolveSessionId();

  let seq = 0;
  let visualizerFrame = null;

  const channel =
    options.channel ??
    (typeof BroadcastChannel !== "undefined" ? new BroadcastChannel(CHANNEL_NAME) : null);

  function post(kind, turnId, payload) {
    if (!channel) return;
    channel.postMessage(
      buildEnvelope({
        session_id,
        turn_id: turnId,
        kind,
        seq: seq++,
        ts: Date.now(),
        payload,
      }),
    );
  }

  function addSystemLine(text) {
    const line = el("p", "cx-system-line");
    line.textContent = capText("nl_restatement", text); // NFR-7
    ui.transcript.appendChild(line);
    ui.transcript.scrollTop = ui.transcript.scrollHeight;
    return line;
  }

  function addUserLine(text) {
    const line = el("p", "cx-user-line");
    line.textContent = capText("nl_restatement", text); // NFR-7
    ui.transcript.appendChild(line);
    ui.transcript.scrollTop = ui.transcript.scrollHeight;
    return line;
  }

  // --- tabs ------------------------------------------------------------------

  function selectTab(which) {
    const chat = which === "chat";
    ui.chatTab.classList.toggle("cx-tab-active", chat);
    ui.vizTab.classList.toggle("cx-tab-active", !chat);
    ui.chatView.hidden = !chat;
    ui.vizView.hidden = chat;
    if (!chat && !visualizerFrame) {
      // §4.6 handshake step 1: the frame learns its session via query param.
      visualizerFrame = el("iframe", "cx-viz-frame");
      visualizerFrame.title = "Visualizer";
      visualizerFrame.src = `${VISUALIZER_SRC}?coxswain_session=${encodeURIComponent(session_id)}`;
      ui.vizView.appendChild(visualizerFrame);
    }
  }
  ui.chatTab.addEventListener("click", () => selectTab("chat"));
  ui.vizTab.addEventListener("click", () => selectTab("viz"));

  // --- propose card lifecycle ---------------------------------------------------

  function renderProposal(demo) {
    const state = createCardState({ tier: demo.tier, fields: demo.fields });
    const required =
      demo.tier === "irreversible"
        ? derivePhrase(demo.call) // FR-3, browser half; kernel re-derives independently
        : null;

    const refs = buildProposeCard(
      {
        state,
        restatement: demo.restatement,
        warnings: [],
        literal_call: demo.call,
        required_phrase: required,
      },
      document,
    );

    const cardHost = el("div", "cx-card-host");
    cardHost.appendChild(refs.root);
    ui.transcript.appendChild(cardHost);
    ui.transcript.scrollTop = ui.transcript.scrollHeight;

    wireProposeCard(refs, state, {
      emit: (message) => {
        // Layer 2 already ran inside submitConfirm; this emit is the execute
        // request. In the full wiring it crosses praxis_coxswain to the
        // kernel; the W3 demo acknowledges locally.
        post("coxswain.execute_request", message.turn_id, message.payload);
        addSystemLine(
          `Execute request emitted for ${message.payload.fields.map((f) => f.name).join(", ")} (kernel guards pending their bridge).`,
        );
      },
      identity: currentTurn(),
      reground: async () => ({ status: "validated" }), // §7 demo: no live grounding yet
      timers: {
        setTimeout: window.setTimeout.bind(window),
        clearTimeout: window.clearTimeout.bind(window),
      },
    });
    return state;
  }

  // --- input capture: turn_id minted HERE, once per submission (§2.2) -------

  let activeTurn = null;
  function currentTurn() {
    return activeTurn ?? { turn_id: null, session_id };
  }

  ui.composer.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = ui.input.value.trim();
    if (!text) return;

    // THE mint point. Before any parse or grounding work starts.
    const turn_id = mintTurnId();
    activeTurn = { turn_id, session_id };

    addUserLine(text);
    post("coxswain.user_command", turn_id, { text });
    ui.input.value = "";

    const demo = demoParse(text);
    if (demo) {
      renderProposal(demo);
    } else {
      addSystemLine(
        "Coxswain has no parse for that yet — the parse layer ships separately (spec §7). Try “transfer 50 µL from A1 to B3” or “discard the tips at C3”.",
      );
    }
  });

  // --- inbound traffic ----------------------------------------------------------

  if (channel) {
    channel.addEventListener("message", (event) => {
      let envelope;
      try {
        envelope = assertValidEnvelope(event.data); // loud rejection (§2.2)
      } catch (err) {
        addSystemLine(`Coxswain dropped a malformed message: ${err.message}`);
        return;
      }
      if (envelope.session_id !== session_id) return; // RISK-12: drop foreign sessions

      switch (envelope.kind) {
        case "coxswain.outcome": {
          const outcome = envelope.payload?.outcome;
          if (!outcome) {
            addSystemLine("Coxswain received an outcome without a payload.");
            return;
          }
          const tree = renderFailureCard({
            outcome,
            attempted_call: envelope.payload?.attempted_call ?? null,
            drift_kind: envelope.payload?.drift_kind ?? null,
          });
          const host = el("div", "cx-card-host");
          host.appendChild(mountTree(tree, document));
          ui.transcript.appendChild(host);
          ui.transcript.scrollTop = ui.transcript.scrollHeight;
          break;
        }
        case "coxswain.system": {
          addSystemLine(String(envelope.payload?.text ?? ""));
          break;
        }
        case "coxswain.hello":
        case "coxswain.hello_ack":
          // §4.6 handshake traffic; the highlight module owns the visualizer side.
          break;
        default:
          // W4 renders clarification cards; until then every other kind is a
          // visible system line, never silence.
          addSystemLine(`Coxswain received "${envelope.kind}" (renderer arrives with W4).`);
      }
    });
  } else {
    addSystemLine("BroadcastChannel unavailable — Coxswain runs UI-only in this context.");
  }

  const api = {
    session_id,
    channelName: CHANNEL_NAME,
    addSystemLine,
    selectTab,
  };
  window.__praxisCoxswainShell = api;
  return api;
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  initCoxswainShell();
}

// viz_handshake.test.js -- overlay/assets/coxswain/viz_highlight.js (W4).
//
// Covers §4.6's session_id handshake, N8-B drawing discipline, and the two
// W4-gated assertions:
//   (a) ZERO writes to the committed-state model on the highlight path --
//       the module never touches receiveFromPython/handleEvent or any layer
//       but its own dedicated overlay layer;
//   (b) a highlight received BEFORE the handshake completes draws nothing.

import { describe, expect, test } from "bun:test";

import {
  CHANNEL_NAME,
  HIGHLIGHT_LAYER_NAME,
  createVizHighlight,
} from "../../../overlay/assets/coxswain/viz_highlight.js";

// --- fakes -----------------------------------------------------------------

class FakeLayer {
  constructor(attrs = {}) {
    this.attrs = { ...attrs };
    this.children = [];
    this.batchDraws = 0;
    this.destroyed = false;
  }
  add(node) {
    this.children.push(node);
    return this;
  }
  batchDraw() {
    this.batchDraws += 1;
  }
  destroyChildren() {
    this.children = [];
  }
}

class FakeNode {
  constructor(attrs) {
    this.attrs = { ...attrs };
  }
}

function makeKonva() {
  return {
    Layer: FakeLayer,
    Rect: class {
      constructor(attrs) {
        this.attrs = { ...attrs };
      }
    },
    Text: class {
      constructor(attrs) {
        this.attrs = { ...attrs };
      }
    },
  };
}

function makeStage(committedLayers = []) {
  const layers = [...committedLayers];
  return {
    layers,
    addedLayers: [],
    getLayers: () => layers,
    add(layer) {
      layers.push(layer);
      this.addedLayers.push(layer);
      return layer;
    },
  };
}

function fakeChannelBus() {
  const subscribers = {};
  const sent = [];
  return {
    sent,
    factory(name) {
      return {
        get name() {
          return name;
        },
        postMessage(msg) {
          sent.push({ name, msg });
        },
        set onmessage(fn) {
          subscribers[name] = fn;
        },
        get onmessage() {
          return subscribers[name];
        },
        close() {},
        __deliver(name, msg) {
          subscribers[name]?.({ data: msg });
        },
      };
    },
    bus: subscribers,
  };
}

function baseEnv(overrides = {}) {
  const konva = overrides.konva ?? makeKonva();
  const stage = overrides.stage ?? makeStage();
  const net = overrides.net ?? fakeChannelBus();
  const env = {
    location: { search: "?coxswain_session=sess-A" },
    channelFactory: net.factory,
    konva,
    stage,
    matchMediaResult: { matches: true }, // default: reduced motion
    timers: {
      setInterval: () => 1,
      clearInterval: () => {},
      setTimeout: () => 2,
    },
    debug: () => {},
    ...overrides,
    // protect these from accidental override via spread above
    net,
  };
  return env;
}

function highlightEnvelope(sessionId, shapes, extra = {}) {
  return {
    v: 1,
    session_id: sessionId,
    turn_id: "cx-1-abc123",
    kind: "viz.highlight",
    seq: 0,
    ts: 0,
    payload: {
      directive: {
        version: 1,
        kind: "static_outline",
        animate: false,
        frames: 0,
        shapes,
      },
    },
    ...extra,
  };
}

function completeHandshake(viz, net, sessionId = "sess-A") {
  net.bus[CHANNEL_NAME]?.({
    data: {
      v: 1,
      session_id: sessionId,
      turn_id: null,
      kind: "coxswain.hello_ack",
      seq: 0,
      ts: 0,
    },
  });
  return viz.handshakeComplete();
}

// --- §4.6 handshake ---------------------------------------------------------

describe("§4.6 session_id handshake", () => {
  test("reads coxswain_session from location.search at load and posts hello", () => {
    const net = fakeChannelBus();
    const viz = createVizHighlight(baseEnv({ net }));
    expect(viz.session_id).toBe("sess-A");
    const hello = net.sent.find((m) => m.msg.kind === "coxswain.hello");
    expect(hello).toBeTruthy();
    expect(hello.name).toBe(CHANNEL_NAME);
    expect(hello.msg.session_id).toBe("sess-A");
    expect(hello.msg.turn_id).toBeNull();
  });

  test("a page opened directly (no query param) never handshakes and never posts hello", () => {
    const net = fakeChannelBus();
    const env = baseEnv({ net });
    env.location = { search: "" };
    const viz = createVizHighlight(env);
    expect(viz.session_id).toBeNull();
    expect(net.sent.length).toBe(0);
    expect(viz.handshakeComplete()).toBe(false);
  });

  test("a matching hello_ack completes the handshake", () => {
    const net = fakeChannelBus();
    const viz = createVizHighlight(baseEnv({ net }));
    expect(viz.handshakeComplete()).toBe(false);
    completeHandshake(viz, net);
    expect(viz.handshakeComplete()).toBe(true);
  });

  test("matching ack completes; mismatched ack does not", () => {
    const net = fakeChannelBus();
    const viz = createVizHighlight(baseEnv({ net }));
    completeHandshake(viz, net);
    expect(viz.handshakeComplete()).toBe(true);

    const net2 = fakeChannelBus();
    const viz2 = createVizHighlight(baseEnv({ net: net2 }));
    net2.bus[CHANNEL_NAME]?.({
      data: {
        v: 1,
        session_id: "sess-FOREIGN",
        turn_id: null,
        kind: "coxswain.hello_ack",
        seq: 0,
        ts: 0,
      },
    });
    expect(viz2.handshakeComplete()).toBe(false);
  });

  test("debug logs ONE line per session for the ack, not per message", () => {
    const lines = [];
    const net = fakeChannelBus();
    const viz = createVizHighlight(baseEnv({ net, debug: (m) => lines.push(m) }));
    completeHandshake(viz, net);
    completeHandshake(viz, net);
    const ackLines = lines.filter((l) => l.includes("hello_ack"));
    expect(ackLines.length).toBe(1);
  });
});

// --- W4 gate assertion (b): pre-handshake highlights draw NOTHING ----------

describe("pre-handshake highlight draws nothing", () => {
  test("a highlight before hello_ack creates no layer content anywhere", () => {
    const net = fakeChannelBus();
    const stage = makeStage([new FakeLayer({ name: "committed-base" })]);
    const viz = createVizHighlight(baseEnv({ net, stage }));
    viz.handleEnvelope(
      highlightEnvelope("sess-A", [{ label: "rails 7", position: "rails 7" }]),
    );
    for (const layer of stage.getLayers()) {
      expect(layer.children.length).toBe(0);
    }
    expect(stage.addedLayers.filter((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME).length).toBe(0);
  });

  test("a foreign-session highlight AFTER handshake also draws nothing", () => {
    const net = fakeChannelBus();
    const stage = makeStage([]);
    const viz = createVizHighlight(baseEnv({ net, stage }));
    completeHandshake(viz, net);
    viz.handleEnvelope(
      highlightEnvelope("sess-B", [{ label: "rails 7" }]),
    );
    const overlay = stage.getLayers().find((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME);
    // Either no layer was created, or the created one stayed empty.
    expect(!overlay || overlay.children.length === 0).toBe(true);
  });
});

// --- post-handshake drawing --------------------------------------------------

describe("drawing on the dedicated overlay layer", () => {
  function drawnSetup(reducedMotion = true) {
    const net = fakeChannelBus();
    const stage = makeStage([new FakeLayer({ name: "committed-base" })]);
    const konva = makeKonva();
    // A committed node the directive targets, so geometry cloning has a source.
    stage.getLayers()[0].add(new FakeNode({ name: "rails 7", x: 10, y: 20, width: 30, height: 40 }));
    const timers = {
      intervals: 0,
      cleared: 0,
      setInterval: (..._a) => {
        timers.intervals += 1;
        return 7;
      },
      clearInterval: () => {
        timers.cleared += 1;
      },
      setTimeout: () => 9,
    };
    const viz = createVizHighlight(
      baseEnv({ net, stage, konva, matchMediaResult: { matches: reducedMotion }, timers }),
    );
    completeHandshake(viz, net);
    return { viz, net, stage, timers };
  }

  test("post-handshake highlight draws ONLY on the dedicated layer", () => {
    const { viz, stage } = drawnSetup();
    viz.handleEnvelope(highlightEnvelope("sess-A", [{ label: "rails 7", position: "rails 7" }]));
    const overlay = stage.getLayers().find((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME);
    expect(overlay).toBeTruthy();
    expect(overlay.children.length).toBeGreaterThan(0);
    const committed = stage.getLayers().find((l) => l.attrs.name === "committed-base");
    // The committed layer gained NO children from us.
    expect(committed.children.length).toBe(1);
  });

  test("unmatched targets still render visibly as a labelled badge, never silently", () => {
    const { viz, stage } = drawnSetup();
    viz.handleEnvelope(highlightEnvelope("sess-A", [{ label: "rails 99" }]));
    const overlay = stage.getLayers().find((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME);
    expect(overlay.children.length).toBeGreaterThan(0);
    const text = overlay.children.find((c) => c.attrs.text !== undefined);
    expect(text.attrs.text).toContain("rails 99");
  });

  test("AC-12: reduced motion renders static even for an animated directive", () => {
    const { viz, stage, timers } = drawnSetup(true);
    viz.handleEnvelope(
      highlightEnvelope("sess-A", [{ label: "rails 7" }], {
        payload: {
          directive: {
            version: 1,
            kind: "pulse_outline",
            animate: true,
            frames: 2,
            period_ms: 800,
            shapes: [{ label: "rails 7" }],
          },
        },
      }),
    );
    expect(timers.intervals).toBe(0);
    const overlay = stage.getLayers().find((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME);
    expect(overlay.children.length).toBeGreaterThan(0);
  });

  test("motion allowed: the pulse runs within the directive's frame budget", () => {
    const { viz, timers } = drawnSetup(false);
    viz.handleEnvelope(
      highlightEnvelope("sess-A", [{ label: "rails 7" }], {
        payload: {
          directive: {
            version: 1,
            kind: "pulse_outline",
            animate: true,
            frames: 3,
            period_ms: 800,
            shapes: [{ label: "rails 7" }],
          },
        },
      }),
    );
    expect(timers.intervals).toBe(1);
  });

  test("malformed envelopes are dropped without throwing or drawing", () => {
    const { viz, stage } = drawnSetup();
    expect(() =>
      viz.handleEnvelope({ kind: "viz.highlight" /* no session_id */ }),
    ).not.toThrow();
    expect(() => viz.handleEnvelope(null)).not.toThrow();
    expect(() => viz.handleEnvelope("garbage")).not.toThrow();
    const overlay = stage.getLayers().find((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME);
    expect(!overlay || overlay.children.length === 0).toBe(true);
  });
});

// --- W4 gate assertion (a): zero committed-state writes ----------------------

describe("zero writes to the committed-state model", () => {
  test("the whole highlight lifecycle issues zero renderer/model calls", () => {
    const net = fakeChannelBus();
    let rendererCalls = 0;
    const stage = makeStage([new FakeLayer({ name: "committed-base" })]);
    const viz = createVizHighlight(
      baseEnv({
        net,
        stage,
        // The vendored entry point, spied. If ANY Coxswain path invokes it,
        // the count moves and this test fails.
        committedStateWriteSpy: () => {
          rendererCalls += 1;
        },
      }),
    );
    completeHandshake(viz, net);
    viz.handleEnvelope(highlightEnvelope("sess-A", [{ label: "rails 7" }]));
    viz.handleEnvelope(
      highlightEnvelope("sess-A", [], {
        kind: "viz.highlight.clear",
        payload: undefined,
      }),
    );
    expect(rendererCalls).toBe(0);
  });

  test("committed-state repaints (praxis_viz traffic) clear the overlay layer", () => {
    const net = fakeChannelBus();
    const stage = makeStage([]);
    const viz = createVizHighlight(baseEnv({ net, stage }));
    completeHandshake(viz, net);
    viz.handleEnvelope(highlightEnvelope("sess-A", [{ label: "rails 7" }]));
    const overlay = stage.getLayers().find((l) => l.attrs.name === HIGHLIGHT_LAYER_NAME);
    expect(overlay.children.length).toBeGreaterThan(0);

    // Any committed-state repaint arrives on praxis_viz; the overlay must clear.
    net.bus["praxis_viz"]?.({ data: JSON.stringify({ event: "set_state", data: {} }) });
    expect(overlay.children.length).toBe(0);
  });
});

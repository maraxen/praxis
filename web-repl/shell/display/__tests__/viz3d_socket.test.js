// viz3d_socket.test.js -- AC-32 (socket shim) and the embed-mode hooks of the
// notebook display epic (.praxia/docs/specs/260929_notebook-display-epic.md,
// D11 "Transport" / "Protocol on praxis_viz3d", D12 "Embed mode", task C4).
//
// It lives under shell/display/__tests__ (not under overlay/assets/) so that no
// test directory is staged wholesale by build_repl.py (spec section 4, the
// viz3d_socket.test.js row). `bun test web-repl/shell/display` finds it.
//
// socket.js is a CLASSIC script, so it is evaluated here as text against a fake
// global (a fake `window` carrying a fake BroadcastChannel, a fake clock, a fake
// `location` and a fake `pagehide` target). The Python half (viewer3d.py, C3)
// does not exist yet; the "kernel" is this file, posting the D11 envelopes.
//
// CONTROLS. The scenarios are plain functions of a loader. The real tests run
// them against the real socket.js (positive control). The mutant tests run the
// very same scenarios against socket.js text with one behaviour removed and
// require the named scenario to FAIL (negative control): a shim that never
// posts `bye`, one that answers `evict` for the wrong client, and so on. A
// mutation that does not change the text fails the control as vacuous.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const AUG = new URL("../../../overlay/assets/visualizer3d-augmentations/", import.meta.url);
const SOCKET_PATH = fileURLToPath(new URL("socket.js", AUG));
const EMBED_PATH = fileURLToPath(new URL("embed.js", AUG));
const EMBED_CSS_PATH = fileURLToPath(new URL("embed.css", AUG));

const CHANNEL = "praxis_viz3d";
const NATIVE_WEBSOCKET = function NativeWebSocket() {};

// ------------------------------------------------------------------ fakes

/** A BroadcastChannel registry. A post reaches every OTHER open channel of the
 * same name (a real channel never hears itself), and throws once closed. */
function createBus() {
  const instances = [];
  const posts = [];

  class FakeBroadcastChannel {
    constructor(name) {
      this.name = name;
      this.closed = false;
      this.listeners = [];
      this.onmessage = null;
      instances.push(this);
    }
    postMessage(raw) {
      if (this.closed) throw new Error("InvalidStateError: the channel is closed");
      let msg;
      try {
        msg = JSON.parse(raw);
      } catch {
        msg = undefined;
      }
      posts.push({ channel: this.name, raw, msg });
      for (const other of instances) {
        if (other !== this && !other.closed && other.name === this.name) other.receive(raw);
      }
    }
    addEventListener(type, fn) {
      if (type === "message") this.listeners.push(fn);
    }
    removeEventListener(type, fn) {
      if (type !== "message") return;
      const at = this.listeners.indexOf(fn);
      if (at >= 0) this.listeners.splice(at, 1);
    }
    close() {
      this.closed = true;
      this.listeners = [];
      this.onmessage = null;
    }
    receive(data) {
      const event = { type: "message", data };
      for (const fn of this.listeners.slice()) fn(event);
      if (this.onmessage) this.onmessage(event);
    }
  }

  return { Ctor: FakeBroadcastChannel, instances, posts };
}

function createClock() {
  let now = 0;
  let seq = 0;
  const timers = new Map();
  return {
    setTimeout(fn, ms = 0) {
      const id = ++seq;
      timers.set(id, { fn, at: now + ms });
      return id;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    advance(ms) {
      const target = now + ms;
      for (;;) {
        let next = null;
        for (const [id, timer] of timers) {
          if (timer.at > target) continue;
          if (!next || timer.at < next.timer.at || (timer.at === next.timer.at && id < next.id)) {
            next = { id, timer };
          }
        }
        if (!next) break;
        now = Math.max(now, next.timer.at);
        timers.delete(next.id);
        next.timer.fn();
      }
      now = target;
    },
    get pending() {
      return timers.size;
    },
  };
}

/** The fake page global socket.js runs against. */
function createEnv({ search = "?embed=1&view=top&viewer=v1", withDocument = true, source } = {}) {
  const bus = createBus();
  const clock = createClock();
  const listeners = new Map();
  const win = {
    location: { search },
    BroadcastChannel: bus.Ctor,
    setTimeout: (fn, ms) => clock.setTimeout(fn, ms),
    clearTimeout: (id) => clock.clearTimeout(id),
    addEventListener(type, fn) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    removeEventListener(type, fn) {
      const list = listeners.get(type) || [];
      const at = list.indexOf(fn);
      if (at >= 0) list.splice(at, 1);
    },
    WebSocket: NATIVE_WEBSOCKET,
  };
  const text = source ?? readFileSync(SOCKET_PATH, "utf8");
  new Function("window", "document", text)(win, withDocument ? {} : undefined);

  const env = {
    win,
    bus,
    clock,
    /** Fire a window event (pagehide) at whoever registered for it. */
    dispatch(type, event = {}) {
      for (const fn of (listeners.get(type) || []).slice()) fn({ type, ...event });
    },
    listenerCount: (type) => (listeners.get(type) || []).length,
    /** The kernel (or any other context) posts an envelope to every channel. */
    deliver(obj) {
      const raw = typeof obj === "string" ? obj : JSON.stringify(obj);
      env.deliverRaw(raw);
    },
    deliverRaw(raw) {
      for (const channel of bus.instances.slice()) if (!channel.closed) channel.receive(raw);
    },
    /** Everything the page side posted, parsed. */
    posted: (kind) => bus.posts.map((p) => p.msg).filter((m) => m && (!kind || m.kind === kind)),
    opens: () => env.posted("open"),
    clientOf: (index = -1) => env.opens().at(index).client,
    openChannels: () => bus.instances.filter((c) => !c.closed).length,
    /** A new socket, the way transport.js makes one. */
    connect() {
      return new win.WebSocket("ws://localhost:/?token=");
    },
    /** Kernel side: accept the most recent client. */
    accept(index = -1) {
      const open = env.opens().at(index);
      env.deliver({ kind: "accept", viewer: open.viewer, client: open.client });
    },
  };
  return env;
}

// ------------------------------------------------------------- scenarios

const scenarios = {
  statics_are_websocket_numbers(load) {
    const env = load();
    const S = env.win.WebSocket;
    expect([S.CONNECTING, S.OPEN, S.CLOSING, S.CLOSED]).toEqual([0, 1, 2, 3]);
    const socket = env.connect();
    expect([socket.CONNECTING, socket.OPEN, socket.CLOSING, socket.CLOSED]).toEqual([0, 1, 2, 3]);
  },

  websocket_replaced_only_where_a_document_exists(load) {
    const withDoc = load();
    expect(withDoc.win.WebSocket).not.toBe(NATIVE_WEBSOCKET);
    expect(typeof withDoc.win.makePraxisSocketClass).toBe("function");
    const bare = load({ withDocument: false });
    expect(bare.win.WebSocket).toBe(NATIVE_WEBSOCKET);
    expect(typeof bare.win.makePraxisSocketClass).toBe("function");
  },

  factory_takes_the_channel_constructor_and_accept_timeout(load) {
    const env = load({ withDocument: false });
    const Socket = env.win.makePraxisSocketClass(env.bus.Ctor, { acceptTimeoutMs: 500 });
    const socket = new Socket("ws://x");
    let closed = 0;
    socket.onclose = () => closed++;
    env.clock.advance(499);
    expect(closed).toBe(0);
    env.clock.advance(1);
    expect(closed).toBe(1);
    expect(env.posted("bye")).toHaveLength(1);
  },

  no_viewer_posts_nothing_and_closes_after_3s(load) {
    const env = load({ search: "?embed=1&view=top" });
    const socket = env.connect();
    let closed = 0;
    let opened = 0;
    socket.onclose = () => closed++;
    socket.onopen = () => opened++;
    expect(socket.readyState).toBe(0);
    env.clock.advance(2999);
    expect(closed).toBe(0);
    env.clock.advance(1);
    expect(closed).toBe(1);
    expect(socket.readyState).toBe(3);
    expect(opened).toBe(0);
    // close(), pagehide and a stray accept afterwards are all silent too.
    socket.close();
    env.dispatch("pagehide");
    env.deliver({ kind: "accept", viewer: "v1", client: "anything" });
    env.clock.advance(10000);
    expect(env.bus.posts).toHaveLength(0);
    expect(closed).toBe(1);
  },

  no_viewer_pagehide_and_close_before_timeout_post_nothing(load) {
    const env = load({ search: "?embed=1" });
    const socket = env.connect();
    env.dispatch("pagehide");
    socket.close();
    env.clock.advance(5000);
    expect(env.bus.posts).toHaveLength(0);
  },

  empty_viewer_parameter_counts_as_no_viewer(load) {
    const env = load({ search: "?viewer=&embed=1" });
    env.connect();
    env.clock.advance(3000);
    expect(env.bus.posts).toHaveLength(0);
  },

  viewer_id_is_read_from_the_query_and_open_is_posted_on_construction(load) {
    const env = load({ search: "?embed=1&view=top&viewer=v1" });
    expect(env.bus.posts).toHaveLength(0);
    const socket = env.connect();
    expect(socket.readyState).toBe(0);
    const opens = env.opens();
    expect(opens).toHaveLength(1); // synchronously, exactly once
    expect(opens[0].kind).toBe("open");
    expect(opens[0].viewer).toBe("v1");
    expect(typeof opens[0].client).toBe("string");
    expect(opens[0].client.length).toBeGreaterThan(0);
    expect(Object.keys(opens[0]).sort()).toEqual(["client", "kind", "viewer"]);
    expect(env.bus.posts[0].channel).toBe(CHANNEL);
    expect(env.bus.posts[0].raw).toBe(JSON.stringify(opens[0])); // a JSON string, per D11
  },

  viewer_id_is_percent_decoded(load) {
    const env = load({ search: "?viewer=a%20b%2Fc" });
    env.connect();
    expect(env.opens()[0].viewer).toBe("a b/c");
  },

  each_socket_mints_its_own_client_id(load) {
    const env = load();
    env.connect();
    env.connect();
    const [a, b] = env.opens();
    expect(a.client).not.toBe(b.client);
  },

  accept_opens_the_socket_once(load) {
    const env = load();
    const socket = env.connect();
    let opened = 0;
    socket.onopen = () => opened++;
    expect(socket.readyState).toBe(0);
    env.accept();
    expect(socket.readyState).toBe(1);
    expect(opened).toBe(1);
    env.accept(); // a duplicate accept changes nothing
    expect(opened).toBe(1);
    env.clock.advance(60000); // the accept timeout was cleared
    expect(env.posted("bye")).toHaveLength(0);
    expect(socket.readyState).toBe(1);
  },

  onopen_may_be_assigned_after_construction(load) {
    const env = load();
    const socket = env.connect();
    env.clock.advance(1000);
    let event = null;
    socket.onopen = (e) => (event = e);
    env.accept();
    expect(event).not.toBeNull();
    expect(event.type).toBe("open");
  },

  send_while_connecting_throws_invalid_state_error(load) {
    const env = load();
    const socket = env.connect();
    let thrown = null;
    try {
      socket.send("hello");
    } catch (error) {
      thrown = error;
    }
    expect(thrown).not.toBeNull();
    expect(thrown.name).toBe("InvalidStateError");
    expect(thrown instanceof DOMException).toBe(true);
    expect(env.posted("msg")).toHaveLength(0);
  },

  send_while_open_posts_msg_with_viewer_client_and_the_exact_string(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    const payload = JSON.stringify({ event: "hello", data: { backend: "WebGL2" } });
    socket.send(payload);
    const msgs = env.posted("msg");
    expect(msgs).toHaveLength(1);
    expect(msgs[0]).toEqual({ kind: "msg", viewer: "v1", client: env.clientOf(), data: payload });
  },

  send_rejects_non_string_data_loudly(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    expect(() => socket.send(new ArrayBuffer(4))).toThrow(TypeError);
    expect(() => socket.send({ a: 1 })).toThrow(TypeError);
    expect(env.posted("msg")).toHaveLength(0);
  },

  send_after_close_is_dropped_silently(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    socket.close();
    expect(() => socket.send("late")).not.toThrow();
    env.clock.advance(0);
    expect(() => socket.send("later")).not.toThrow();
    expect(env.posted("msg")).toHaveLength(0);
  },

  msg_is_delivered_to_onmessage_as_the_exact_string(load) {
    const env = load();
    const socket = env.connect();
    const got = [];
    socket.onmessage = (event) => got.push(event.data);
    env.accept();
    const scene = JSON.stringify({ event: "scene", data: { n: 1 } });
    env.deliver({ kind: "msg", viewer: "v1", client: env.clientOf(), data: scene });
    expect(got).toEqual([scene]);
    expect(typeof got[0]).toBe("string");
  },

  msg_before_accept_is_dropped(load) {
    const env = load();
    const socket = env.connect();
    const got = [];
    socket.onmessage = (event) => got.push(event.data);
    env.deliver({ kind: "msg", viewer: "v1", client: env.clientOf(), data: "early" });
    expect(got).toEqual([]);
  },

  messages_for_another_client_or_viewer_are_ignored(load) {
    const env = load();
    const socket = env.connect();
    const got = [];
    let opened = 0;
    let closed = 0;
    socket.onmessage = (event) => got.push(event.data);
    socket.onopen = () => opened++;
    socket.onclose = () => closed++;
    const mine = env.clientOf();
    // another client, same viewer
    env.deliver({ kind: "accept", viewer: "v1", client: "other" });
    // same client id, another viewer
    env.deliver({ kind: "accept", viewer: "v2", client: mine });
    expect(opened).toBe(0);
    expect(socket.readyState).toBe(0);
    env.accept();
    expect(opened).toBe(1);
    env.deliver({ kind: "msg", viewer: "v1", client: "other", data: "x" });
    env.deliver({ kind: "msg", viewer: "v2", client: mine, data: "y" });
    env.deliver({ kind: "evict", viewer: "v1", client: "other" });
    env.deliver({ kind: "evict", viewer: "v2", client: mine });
    env.deliver({ kind: "close", viewer: "v2", reason: "stop" });
    expect(got).toEqual([]);
    expect(closed).toBe(0);
    expect(socket.readyState).toBe(1);
  },

  malformed_or_unknown_messages_are_dropped_without_throwing(load) {
    const env = load();
    const socket = env.connect();
    const got = [];
    let opened = 0;
    let closed = 0;
    socket.onmessage = (event) => got.push(event.data);
    socket.onopen = () => opened++;
    socket.onclose = () => closed++;
    const mine = env.clientOf();
    const junk = [
      "not json {",
      "",
      "null",
      "42",
      '"accept"',
      "[]",
      '[{"kind":"accept","viewer":"v1","client":"' + mine + '"}]',
      "{}",
      JSON.stringify({ kind: "teleport", viewer: "v1", client: mine }),
      JSON.stringify({ kind: 7, viewer: "v1", client: mine }),
      JSON.stringify({ kind: "accept" }),
      JSON.stringify({ kind: "accept", viewer: "v1" }),
      JSON.stringify({ kind: "accept", client: mine }),
      JSON.stringify({ kind: "accept", viewer: 1, client: mine }),
      JSON.stringify({ kind: "accept", viewer: "v1", client: 5 }),
      JSON.stringify({ kind: "evict", viewer: "v1" }),
      JSON.stringify({ kind: "query" }),
      JSON.stringify({ kind: "announce", viewer: "v1", deck: "d", session: "s" }),
    ];
    for (const raw of junk) expect(() => env.deliverRaw(raw)).not.toThrow();
    // non-string event data (a foreign context posting an object) is also dropped
    for (const odd of [{ kind: "accept", viewer: "v1", client: mine }, null, 12, undefined]) {
      expect(() => env.deliverRaw(odd)).not.toThrow();
    }
    expect(opened).toBe(0);
    expect(closed).toBe(0);
    expect(socket.readyState).toBe(0);
    env.accept();
    expect(opened).toBe(1);
    // a msg whose data is not a string is dropped once open
    for (const data of [1, null, { a: 1 }, ["x"], undefined]) {
      env.deliver({ kind: "msg", viewer: "v1", client: mine, data });
    }
    // and announce/query from other parties leave an open socket alone
    env.deliver({ kind: "announce", viewer: "v1", deck: "d", session: "s" });
    env.deliver({ kind: "query" });
    expect(got).toEqual([]);
    expect(closed).toBe(0);
    expect(socket.readyState).toBe(1);
  },

  close_posts_bye_exactly_once_and_then_fires_onclose(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    let closed = 0;
    socket.onclose = () => closed++;
    const client = env.clientOf();
    socket.close();
    expect(env.posted("bye")).toEqual([{ kind: "bye", viewer: "v1", client }]);
    expect(socket.readyState).toBe(2); // CLOSING until the close event
    socket.close(); // a second close posts nothing
    socket.close(1000, "again");
    env.clock.advance(0);
    expect(socket.readyState).toBe(3);
    expect(closed).toBe(1);
    socket.close();
    env.clock.advance(10000);
    expect(env.posted("bye")).toHaveLength(1);
    expect(closed).toBe(1);
  },

  close_while_connecting_posts_bye_and_stops_the_timeout(load) {
    const env = load();
    const socket = env.connect();
    let closed = 0;
    socket.onclose = () => closed++;
    socket.close();
    env.clock.advance(60000); // the 3 s timer must not add a second bye or a second onclose
    expect(env.posted("bye")).toHaveLength(1);
    expect(closed).toBe(1);
    expect(env.clock.pending).toBe(0);
  },

  close_releases_the_channel_and_the_pagehide_listener(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    expect(env.listenerCount("pagehide")).toBe(1);
    socket.close();
    env.clock.advance(0);
    expect(env.listenerCount("pagehide")).toBe(0);
    expect(env.openChannels()).toBe(0);
  },

  pagehide_posts_bye_exactly_once(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    const client = env.clientOf();
    env.dispatch("pagehide", { persisted: false });
    expect(env.posted("bye")).toEqual([{ kind: "bye", viewer: "v1", client }]);
    env.dispatch("pagehide", { persisted: true });
    socket.close();
    env.clock.advance(60000);
    expect(env.posted("bye")).toHaveLength(1);
    expect(socket.readyState).toBe(3);
  },

  pagehide_while_connecting_posts_bye_and_ignores_a_late_accept(load) {
    const env = load();
    const socket = env.connect();
    let opened = 0;
    socket.onopen = () => opened++;
    env.dispatch("pagehide");
    expect(env.posted("bye")).toHaveLength(1);
    env.accept();
    env.clock.advance(3000);
    expect(opened).toBe(0);
    expect(env.posted("bye")).toHaveLength(1);
    expect(socket.readyState).toBe(3);
  },

  accept_timeout_posts_bye_once_and_fires_onclose(load) {
    const env = load();
    const socket = env.connect();
    let closed = 0;
    socket.onclose = () => closed++;
    const client = env.clientOf();
    env.clock.advance(2999);
    expect(env.posted("bye")).toHaveLength(0);
    expect(closed).toBe(0);
    expect(socket.readyState).toBe(0);
    env.clock.advance(1);
    expect(env.posted("bye")).toEqual([{ kind: "bye", viewer: "v1", client }]);
    expect(closed).toBe(1);
    expect(socket.readyState).toBe(3);
    env.dispatch("pagehide");
    socket.close();
    env.clock.advance(60000);
    expect(env.posted("bye")).toHaveLength(1);
    expect(closed).toBe(1);
  },

  late_accept_after_timeout_is_ignored(load) {
    const env = load();
    const socket = env.connect();
    let opened = 0;
    socket.onopen = () => opened++;
    env.clock.advance(3000);
    env.accept();
    expect(socket.readyState).toBe(3);
    expect(opened).toBe(0);
    const got = [];
    socket.onmessage = (e) => got.push(e.data);
    env.deliver({ kind: "msg", viewer: "v1", client: env.clientOf(), data: "x" });
    expect(got).toEqual([]);
    expect(() => socket.send("x")).not.toThrow();
    expect(env.posted("msg")).toHaveLength(0);
  },

  late_accept_after_close_is_ignored(load) {
    const env = load();
    const socket = env.connect();
    let opened = 0;
    socket.onopen = () => opened++;
    socket.close();
    env.accept(); // still CLOSING
    env.clock.advance(0);
    env.accept(); // now CLOSED
    expect(opened).toBe(0);
    expect(socket.readyState).toBe(3);
  },

  evict_for_this_client_fires_onclose_without_a_bye(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    let closed = 0;
    socket.onclose = () => closed++;
    env.deliver({ kind: "evict", viewer: "v1", client: env.clientOf() });
    expect(closed).toBe(1);
    expect(socket.readyState).toBe(3);
    // the kernel already dropped this client, so nothing more is owed to it
    env.dispatch("pagehide");
    socket.close();
    env.clock.advance(60000);
    expect(env.posted("bye")).toHaveLength(0);
    expect(closed).toBe(1);
    expect(env.openChannels()).toBe(0);
  },

  evict_for_another_client_is_ignored(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    let closed = 0;
    socket.onclose = () => closed++;
    env.deliver({ kind: "evict", viewer: "v1", client: "somebody-else" });
    env.deliver({ kind: "evict", viewer: "v1", client: env.clientOf() + "x" });
    expect(closed).toBe(0);
    expect(socket.readyState).toBe(1);
  },

  evict_only_closes_the_addressed_socket_among_several(load) {
    const env = load();
    const first = env.connect();
    const second = env.connect();
    env.accept(0);
    env.accept(1);
    const closes = { first: 0, second: 0 };
    first.onclose = () => closes.first++;
    second.onclose = () => closes.second++;
    env.deliver({ kind: "evict", viewer: "v1", client: env.clientOf(0) });
    expect(closes).toEqual({ first: 1, second: 0 });
    expect(first.readyState).toBe(3);
    expect(second.readyState).toBe(1);
  },

  after_evict_the_pages_reconnect_loop_gets_a_fresh_client(load) {
    const env = load();
    const first = env.connect();
    env.accept();
    // transport.js: onclose -> new WebSocket after RECONNECT_MS
    let next = null;
    first.onclose = () => (next = env.connect());
    env.deliver({ kind: "evict", viewer: "v1", client: env.clientOf() });
    expect(next).not.toBeNull();
    expect(env.opens()).toHaveLength(2);
    expect(env.opens()[1].client).not.toBe(env.opens()[0].client);
    env.accept();
    expect(next.readyState).toBe(1);
  },

  kernel_close_for_this_viewer_fires_onclose(load) {
    const env = load();
    const socket = env.connect();
    env.accept();
    let closed = 0;
    socket.onclose = () => closed++;
    env.deliver({ kind: "close", viewer: "v1", reason: "stop" });
    expect(closed).toBe(1);
    expect(socket.readyState).toBe(3);
    env.clock.advance(60000);
    expect(closed).toBe(1);
    expect(env.openChannels()).toBe(0);
  },

  kernel_close_while_connecting_fires_onclose_too(load) {
    const env = load();
    const socket = env.connect();
    let closed = 0;
    socket.onclose = () => closed++;
    env.deliver({ kind: "close", viewer: "v1", reason: "stop" });
    expect(closed).toBe(1);
    env.clock.advance(60000);
    expect(closed).toBe(1);
  },

  the_page_never_posts_close_query_announce_accept_or_evict(load) {
    const env = load();
    const a = env.connect();
    env.accept();
    a.send("x");
    a.close();
    env.clock.advance(0);
    const b = env.connect();
    env.clock.advance(3000);
    const c = env.connect();
    env.dispatch("pagehide");
    void b;
    void c;
    const kinds = new Set(env.posted().map((m) => m.kind));
    for (const kind of kinds) expect(["open", "msg", "bye"]).toContain(kind);
    expect(kinds.has("close")).toBe(false);
  },

  transport_js_surface(load) {
    // static/transport.js: `new WebSocket(window.WS_URL)`, compares readyState with
    // WebSocket.OPEN / WebSocket.CONNECTING, assigns onopen / onclose / onmessage,
    // calls send() from inside onopen, and reconnects by making a new socket.
    const env = load();
    const WS = env.win.WebSocket;
    const socket = new WS("ws://localhost:/?token=abc");
    expect(socket.readyState === WS.CONNECTING).toBe(true);
    expect(socket.onopen).toBeNull();
    expect(socket.onclose).toBeNull();
    expect(socket.onmessage).toBeNull();
    for (const method of ["send", "close"]) expect(typeof socket[method]).toBe("function");
    const order = [];
    socket.onopen = () => {
      order.push("open");
      socket.send(JSON.stringify({ event: "hello", data: {} })); // legal inside onopen
    };
    socket.onmessage = (event) => order.push(JSON.parse(event.data).event);
    env.accept();
    expect(socket.readyState === WS.OPEN).toBe(true);
    const client = env.clientOf();
    env.deliver({ kind: "msg", viewer: "v1", client, data: JSON.stringify({ event: "scene", data: { a: 1 } }) });
    env.deliver({ kind: "msg", viewer: "v1", client, data: JSON.stringify({ event: "state", data: { b: 2 } }) });
    expect(order).toEqual(["open", "scene", "state"]); // arrival order is kept
    expect(env.posted("msg")).toHaveLength(1); // the hello
  },

  an_empty_query_string_posts_nothing_at_all(load) {
    const env = load({ search: "" });
    const socket = env.connect();
    env.clock.advance(3000);
    socket.close();
    env.dispatch("pagehide");
    expect(env.bus.posts).toHaveLength(0);
  },
};

function runAll(load) {
  const failed = [];
  for (const [name, fn] of Object.entries(scenarios)) {
    try {
      fn(load);
    } catch (error) {
      failed.push(name);
    }
  }
  return failed;
}

const realLoad = (options) => createEnv(options);

/** A regex for `snippet` that tolerates any whitespace (a formatter may re-wrap the source). */
function looseSource(snippet) {
  const escape = (ch) => ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp([...snippet.replace(/\s+/g, "")].map(escape).join("\\s*"));
}

function mutantLoader(edits) {
  const original = readFileSync(SOCKET_PATH, "utf8");
  let mutated = original;
  for (const [from, to] of edits) {
    const pattern = looseSource(from);
    expect(pattern.test(mutated)).toBe(true); // a mutation that finds nothing is vacuous
    mutated = mutated.replace(pattern, () => to);
  }
  expect(mutated).not.toBe(original);
  return (options) => createEnv({ ...options, source: mutated });
}

// ------------------------------------------------------ socket.js: the suite

describe("AC-32: socket.js against the D11 protocol", () => {
  for (const [name, fn] of Object.entries(scenarios)) {
    test(name.replaceAll("_", " "), () => fn(realLoad));
  }

  test("positive control: every scenario passes on the real shim", () => {
    expect(runAll(realLoad)).toEqual([]);
  });
});

describe("AC-32 negative controls: a broken shim must fail the scenarios", () => {
  const mutants = [
    {
      name: "never posts bye",
      edits: [['const KIND_BYE = "bye";', 'const KIND_BYE = "bye_disabled";']],
      mustFail: [
        "close_posts_bye_exactly_once_and_then_fires_onclose",
        "pagehide_posts_bye_exactly_once",
        "accept_timeout_posts_bye_once_and_fires_onclose",
      ],
    },
    {
      name: "no bye on the accept timeout",
      edits: [["function onAcceptTimeout() { postBye();", "function onAcceptTimeout() {"]],
      mustFail: ["accept_timeout_posts_bye_once_and_fires_onclose", "factory_takes_the_channel_constructor_and_accept_timeout"],
    },
    {
      name: "no bye on pagehide",
      edits: [["function onPageHide() { self.close(); }", "function onPageHide() {}"]],
      mustFail: ["pagehide_posts_bye_exactly_once", "pagehide_while_connecting_posts_bye_and_ignores_a_late_accept"],
    },
    {
      name: "answers evict for the wrong client",
      edits: [['m.kind === "evict" && isMine(m)', 'm.kind === "evict" && m.viewer === viewer']],
      mustFail: ["evict_for_another_client_is_ignored", "evict_only_closes_the_addressed_socket_among_several"],
    },
    {
      name: "accepts a late accept",
      edits: [
        ['m.kind === "accept" && isMine(m) && state === CONNECTING', 'm.kind === "accept" && isMine(m)'],
        ['channel.removeEventListener("message", onChannelMessage);', ""],
        ["channel.close();", ""],
      ],
      mustFail: ["late_accept_after_timeout_is_ignored", "late_accept_after_close_is_ignored"],
    },
    {
      name: "posts without a viewer id",
      edits: [
        ["if (viewer) post(", "post("],
        ["byeSent || !viewer", "byeSent"],
      ],
      mustFail: ["no_viewer_posts_nothing_and_closes_after_3s", "no_viewer_pagehide_and_close_before_timeout_post_nothing"],
    },
  ];

  for (const mutant of mutants) {
    test(`mutant "${mutant.name}" is caught`, () => {
      const failed = runAll(mutantLoader(mutant.edits));
      for (const name of mutant.mustFail) expect(failed).toContain(name);
    });
  }
});

// ------------------------------------------------------- source hygiene

describe("socket.js and embed.js are plain, offline browser code", () => {
  const forbidden = [
    [/\beval\s*\(/, "eval"],
    [/new\s+Function\b/, "new Function"],
    [/\bfetch\s*\(/, "fetch"],
    [/XMLHttpRequest/, "XMLHttpRequest"],
    [/\bimportScripts\b/, "importScripts"],
    [/https?:\/\//, "an absolute URL"],
    [/cdn\./i, "a CDN"],
    [/__praxis_test|data-praxis-test/, "a test-only switch"],
  ];
  for (const [label, path] of [
    ["socket.js", SOCKET_PATH],
    ["embed.js", EMBED_PATH],
    ["embed.css", EMBED_CSS_PATH],
  ]) {
    test(`${label} contains none of the forbidden constructs`, () => {
      const text = readFileSync(path, "utf8");
      for (const [pattern, what] of forbidden) {
        expect(pattern.test(text) ? what : null).toBeNull();
      }
    });
  }

  test("socket.js is a classic script: no import or export statements", () => {
    const text = readFileSync(SOCKET_PATH, "utf8");
    expect(/^\s*(import|export)\b/m.test(text)).toBe(false);
    expect(/\bimport\s*\(/.test(text)).toBe(false);
  });

  test("socket.js touches no storage and no other channel", () => {
    const text = readFileSync(SOCKET_PATH, "utf8");
    expect(/localStorage|sessionStorage|indexedDB/.test(text)).toBe(false);
    expect(/praxis_repl|praxis_viz["'\s,)]/.test(text)).toBe(false);
    expect(text.includes(CHANNEL)).toBe(true);
  });
});

// --------------------------------------------------------------- embed.js

function createEmbedEnv({ search = "?embed=1&view=top&viewer=v1", parentMode = "other" } = {}) {
  class FakeCustomEvent {
    constructor(type, init = {}) {
      this.type = type;
      this.detail = init.detail;
    }
  }
  const classes = new Set();
  const attrs = new Map();
  const head = { children: [], appendChild(el) { this.children.push(el); return el; } };
  const doc = {
    documentElement: {
      classList: { add: (c) => classes.add(c), contains: (c) => classes.has(c) },
      setAttribute: (k, v) => attrs.set(k, String(v)),
      getAttribute: (k) => (attrs.has(k) ? attrs.get(k) : null),
    },
    head,
    createElement: (tag) => ({ tag, attrs: {}, setAttribute(k, v) { this.attrs[k] = String(v); } }),
  };
  const listeners = new Map();
  const parentEvents = [];
  const parent = { CustomEvent: FakeCustomEvent, dispatchEvent: (e) => (parentEvents.push(e), true) };
  const win = {
    location: { search },
    CustomEvent: FakeCustomEvent,
    addEventListener(type, fn) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    dispatch(type, detail) {
      for (const fn of listeners.get(type) || []) fn({ type, detail });
    },
    listenerCount: (type) => (listeners.get(type) || []).length,
  };
  if (parentMode === "other") win.parent = parent;
  else if (parentMode === "self") win.parent = win;
  else if (parentMode === "throws") {
    Object.defineProperty(win, "parent", {
      get() {
        throw new Error("SecurityError: blocked a frame");
      },
    });
  }
  return { win, doc, parentEvents, classes, attrs, head };
}

async function importEmbed() {
  return import(EMBED_PATH);
}

describe("embed.js: embed mode (D12)", () => {
  const CSS_HREF = "http-less-test/embed.css";

  test("does nothing without embed=1", async () => {
    const { installEmbed } = await importEmbed();
    for (const search of ["", "?viewer=v1", "?embed=0&viewer=v1", "?embed=10", "?embed=", "?xembed=1"]) {
      const env = createEmbedEnv({ search });
      const result = installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
      expect(result.active).toBe(false);
      expect(env.classes.has("praxis-embed")).toBe(false);
      expect(env.head.children).toHaveLength(0);
      expect(env.win.listenerCount("plr:status")).toBe(0);
      expect(env.win.listenerCount("plr:gone")).toBe(0);
    }
  });

  test("embed=1 marks the document and injects embed.css once", async () => {
    const { installEmbed } = await importEmbed();
    const env = createEmbedEnv();
    const result = installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
    expect(result.active).toBe(true);
    expect(env.classes.has("praxis-embed")).toBe(true);
    expect(env.attrs.get("data-praxis-embed")).toBe("1");
    expect(env.head.children).toHaveLength(1);
    const link = env.head.children[0];
    expect(link.tag).toBe("link");
    expect(link.attrs.rel).toBe("stylesheet");
    expect(link.attrs.href).toBe(CSS_HREF);
    installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF }); // idempotent
    expect(env.head.children).toHaveLength(1);
    expect(env.win.listenerCount("plr:status")).toBe(1);
    expect(env.win.listenerCount("plr:gone")).toBe(1);
  });

  test("plr:status is forwarded to the parent as praxis:dock-status", async () => {
    const { installEmbed } = await importEmbed();
    const env = createEmbedEnv();
    installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
    env.win.dispatch("plr:status", { connected: true });
    env.win.dispatch("plr:status", { connected: false });
    expect(env.parentEvents.map((e) => e.type)).toEqual(["praxis:dock-status", "praxis:dock-status"]);
    expect(env.parentEvents.map((e) => e.detail)).toEqual([
      { event: "plr:status", connected: true, viewer: "v1" },
      { event: "plr:status", connected: false, viewer: "v1" },
    ]);
  });

  test("plr:gone is forwarded to the parent as praxis:dock-status", async () => {
    const { installEmbed } = await importEmbed();
    const env = createEmbedEnv();
    installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
    env.win.dispatch("plr:gone", undefined);
    expect(env.parentEvents).toHaveLength(1);
    expect(env.parentEvents[0].type).toBe("praxis:dock-status");
    expect(env.parentEvents[0].detail).toEqual({ event: "plr:gone", viewer: "v1" });
  });

  test("the forwarded detail carries a null viewer when there is none", async () => {
    const { installEmbed } = await importEmbed();
    const env = createEmbedEnv({ search: "?embed=1" });
    installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
    env.win.dispatch("plr:gone", undefined);
    expect(env.parentEvents[0].detail).toEqual({ event: "plr:gone", viewer: null });
  });

  test("a page that is its own parent forwards nothing and does not throw", async () => {
    const { installEmbed } = await importEmbed();
    const env = createEmbedEnv({ parentMode: "self" });
    installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
    expect(() => env.win.dispatch("plr:gone", undefined)).not.toThrow();
    expect(env.parentEvents).toHaveLength(0);
  });

  test("a parent that cannot be reached does not break the page", async () => {
    const { installEmbed } = await importEmbed();
    const env = createEmbedEnv({ parentMode: "throws" });
    installEmbed({ win: env.win, doc: env.doc, cssHref: CSS_HREF });
    expect(() => env.win.dispatch("plr:status", { connected: true })).not.toThrow();
    expect(() => env.win.dispatch("plr:gone", undefined)).not.toThrow();
  });

  test("importing embed.js with no document does nothing and throws nothing", async () => {
    expect(typeof globalThis.document).toBe("undefined");
    const mod = await importEmbed();
    expect(typeof mod.installEmbed).toBe("function");
  });

  test("on a page with embed=1 the module installs itself on load", async () => {
    const env = createEmbedEnv();
    const saved = { window: globalThis.window, document: globalThis.document, location: globalThis.location };
    globalThis.window = env.win;
    globalThis.document = env.doc;
    globalThis.location = env.win.location;
    try {
      await import(`${EMBED_PATH}?selfinstall=${Math.random()}`);
    } finally {
      for (const [k, v] of Object.entries(saved)) {
        if (v === undefined) delete globalThis[k];
        else globalThis[k] = v;
      }
    }
    expect(env.classes.has("praxis-embed")).toBe(true);
    expect(env.head.children).toHaveLength(1);
    expect(env.head.children[0].attrs.href.endsWith("embed.css")).toBe(true);
  });
});

describe("embed.css: what embed mode hides and paints (D12)", () => {
  const css = () => readFileSync(EMBED_CSS_PATH, "utf8");

  /** The declaration block of the rule whose selector list contains `selector`. */
  function ruleFor(text, selector) {
    const rules = [...text.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
    return rules.filter(([, sel]) => sel.split(",").some((s) => s.trim().endsWith(selector)));
  }

  for (const selector of [".navbar", "#toolbar-left", "#stats-panel", "#sidepanel", "#toolbar"]) {
    test(`${selector} is display: none, scoped to embed mode`, () => {
      const rules = ruleFor(css(), selector);
      expect(rules.length).toBeGreaterThan(0);
      const hidden = rules.some(([, , body]) => /display\s*:\s*none\s*(!important)?\s*;?/.test(body));
      expect(hidden).toBe(true);
      const scoped = rules.every(([, sel]) =>
        sel
          .split(",")
          .filter((s) => s.trim().endsWith(selector))
          .every((s) => s.includes(".praxis-embed")),
      );
      expect(scoped).toBe(true);
    });
  }

  test("the page ground is #EEF1F4", () => {
    expect(/#eef1f4/i.test(css())).toBe(true);
  });

  test("the content area is not cropped by the 60px the navbar used to take", () => {
    const rules = ruleFor(css(), ".content");
    expect(rules.some(([, , body]) => /height\s*:\s*100%/.test(body))).toBe(true);
  });

  test("no imports, no urls, no remote fonts", () => {
    expect(/@import|url\s*\(|@font-face/.test(css())).toBe(false);
  });
});

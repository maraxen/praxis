/**
 * Praxis Visualizer3D socket shim (task C4; spec D11 "Transport" and "Protocol on praxis_viz3d").
 *
 * The vendored page (../visualizer3d/, byte-identical to the PyLabRobot pin) opens exactly one
 * WebSocket, `new WebSocket(window.WS_URL)` (static/transport.js:63), and nothing serves a
 * websocket in the REPL. This CLASSIC script runs before every module of the page (index.html
 * carries its tag immediately before the first <script) and replaces `window.WebSocket`, in that
 * iframe page only, with `PraxisSocket`: a WebSocket-shaped class over the BroadcastChannel
 * "praxis_viz3d". The page's own transport keeps working unchanged: it compares `readyState`
 * with `WebSocket.OPEN` / `WebSocket.CONNECTING`, assigns `onopen` / `onclose` / `onmessage`,
 * calls `send` from inside `onopen`, and reconnects by making a new socket.
 *
 * Every message on the channel is a JSON string. Page to kernel:
 *   {kind: "open", viewer, client}          posted on construction (only with a viewer id)
 *   {kind: "msg",  viewer, client, data}    `data` is the exact string the websocket would carry
 *   {kind: "bye",  viewer, client}          posted once, on close(), on pagehide, on accept timeout
 * Kernel to page (anything else is dropped without an exception):
 *   {kind: "accept", viewer, client}        the kernel took this client: readyState OPEN, onopen
 *   {kind: "msg",    viewer, client, data}  delivered to onmessage as {data}
 *   {kind: "evict",  viewer, client}        the kernel dropped THIS client: onclose
 *   {kind: "close",  viewer, reason}        the viewer stopped: onclose for every client of it
 * The page never posts `close`, `query`, `announce`, `accept` or `evict`.
 *
 * The viewer id is `viewer=<id>` in location.search, written by the shell's deck panel from an
 * announce. Without one the shim posts nothing at all (not even `bye`) and fires `onclose` after
 * the accept timeout, so the page's own 60 s give-up path is reached and never a spin.
 *
 * No `accept` within 3 s: the shim posts `bye`, fires `onclose` and ignores any later `accept`
 * for that client; the page's reconnect loop retries with a new client.
 */
(function (root) {
  "use strict";

  const CHANNEL_NAME = "praxis_viz3d";
  const DEFAULT_ACCEPT_TIMEOUT_MS = 3000;

  const KIND_OPEN = "open";
  const KIND_MSG = "msg";
  const KIND_BYE = "bye";
  const KIND_ACCEPT = "accept";
  const KIND_EVICT = "evict";
  const KIND_CLOSE = "close";

  const CONNECTING = 0;
  const OPEN = 1;
  const CLOSING = 2;
  const CLOSED = 3;

  /** The viewer id of this page, or null (no query parameter, or an empty one). */
  function readViewer(loc) {
    const search = loc && typeof loc.search === "string" ? loc.search : "";
    const viewer = new URLSearchParams(search).get("viewer");
    return viewer ? viewer : null;
  }

  /** One kernel envelope, or null when it is not a JSON object of a kind the page understands. */
  function parseEnvelope(data) {
    if (typeof data !== "string") return null;
    let m;
    try {
      m = JSON.parse(data);
    } catch (error) {
      return null;
    }
    if (m === null || typeof m !== "object" || Array.isArray(m)) return null;
    if (typeof m.viewer !== "string") return null;
    if (m.kind === KIND_ACCEPT || m.kind === KIND_MSG || m.kind === KIND_EVICT) {
      return typeof m.client === "string" ? m : null;
    }
    if (m.kind === KIND_CLOSE) return m;
    return null;
  }

  function invalidStateError(message) {
    if (typeof DOMException === "function") return new DOMException(message, "InvalidStateError");
    const error = new Error(message);
    error.name = "InvalidStateError";
    return error;
  }

  /**
   * The WebSocket-shaped class. `options` (all optional): `acceptTimeoutMs` (default 3000),
   * `location` (default the page's), `pageTarget` (where `pagehide` is heard; default the
   * page), `setTimeout` / `clearTimeout` (default the page's), `newClientId`.
   */
  function makePraxisSocketClass(BroadcastChannelCtor, options) {
    const opts = options || {};
    const acceptTimeoutMs =
      typeof opts.acceptTimeoutMs === "number" ? opts.acceptTimeoutMs : DEFAULT_ACCEPT_TIMEOUT_MS;
    let counter = 0;

    function newClientId() {
      if (typeof opts.newClientId === "function") return String(opts.newClientId());
      const c = root.crypto;
      if (c && typeof c.randomUUID === "function") return "c-" + c.randomUUID();
      counter += 1;
      return (
        "c-" + Date.now().toString(36) + "-" + counter.toString(36) + "-" +
        Math.random().toString(36).slice(2, 10)
      );
    }
    function setT(fn, ms) {
      return opts.setTimeout ? opts.setTimeout(fn, ms) : root.setTimeout(fn, ms);
    }
    function clearT(id) {
      if (opts.clearTimeout) opts.clearTimeout(id);
      else root.clearTimeout(id);
    }

    function PraxisSocket(url) {
      if (!(this instanceof PraxisSocket)) {
        throw new TypeError("Failed to construct 'WebSocket': Please use the 'new' operator");
      }
      const self = this;
      const viewer = readViewer(opts.location || root.location);
      const clientId = newClientId();
      const pageTarget = opts.pageTarget || root;

      let state = CONNECTING;
      let channel = null;
      let timer = null;
      let byeSent = false;
      let listeningPageHide = false;

      self.url = url === undefined ? "" : String(url);
      self.protocol = "";
      self.extensions = "";
      self.bufferedAmount = 0;
      self.binaryType = "blob";
      self.onopen = null;
      self.onmessage = null;
      self.onclose = null;
      self.onerror = null;
      Object.defineProperty(self, "readyState", {
        get: function () {
          return state;
        },
        enumerable: true,
      });

      function fire(handler, event) {
        const fn = self[handler];
        if (typeof fn === "function") fn.call(self, event);
      }
      function live() {
        return state === CONNECTING || state === OPEN;
      }
      function isMine(m) {
        return m.viewer === viewer && m.client === clientId;
      }
      function post(message) {
        channel.postMessage(JSON.stringify(message));
      }
      function postBye() {
        if (byeSent || !viewer) return;
        byeSent = true;
        post({ kind: KIND_BYE, viewer: viewer, client: clientId });
      }
      /** Give back the timer, the channel and the pagehide listener. */
      function release() {
        if (timer !== null) {
          clearT(timer);
          timer = null;
        }
        if (channel) {
          channel.removeEventListener("message", onChannelMessage);
          channel.close();
          channel = null;
        }
        if (listeningPageHide) {
          pageTarget.removeEventListener("pagehide", onPageHide);
          listeningPageHide = false;
        }
      }
      /** The other side ended this socket (or the accept timer ran out): CLOSED at once. */
      function endNow() {
        release();
        state = CLOSED;
        fire("onclose", { type: "close", code: 1006, reason: "", wasClean: false });
      }

      function onAcceptTimeout() {
        postBye();
        timer = null;
        endNow();
      }
      function onPageHide() { self.close(); }
      function onChannelMessage(event) {
        const m = parseEnvelope(event && event.data);
        if (m === null) return;
        if (m.kind === "accept" && isMine(m) && state === CONNECTING) {
          clearT(timer);
          timer = null;
          state = OPEN;
          fire("onopen", { type: "open" });
        } else if (m.kind === "msg" && isMine(m) && state === OPEN && typeof m.data === "string") {
          fire("onmessage", { type: "message", data: m.data, origin: "", lastEventId: "" });
        } else if (m.kind === "evict" && isMine(m)) {
          if (live()) endNow();
        } else if (m.kind === KIND_CLOSE && m.viewer === viewer) {
          if (live()) endNow();
        }
      }

      self.send = function (data) {
        if (state === CONNECTING) {
          throw invalidStateError("Failed to execute 'send' on 'WebSocket': Still in CONNECTING state.");
        }
        if (state !== OPEN) return;
        if (typeof data !== "string") {
          throw new TypeError("PraxisSocket carries text only: send() needs a string");
        }
        post({ kind: KIND_MSG, viewer: viewer, client: clientId, data: data });
      };

      self.close = function () {
        if (state === CLOSING || state === CLOSED) return;
        state = CLOSING;
        postBye();
        release();
        setT(function () {
          state = CLOSED;
          fire("onclose", { type: "close", code: 1000, reason: "", wasClean: true });
        }, 0);
      };

      if (viewer) {
        channel = new BroadcastChannelCtor(CHANNEL_NAME);
        channel.addEventListener("message", onChannelMessage);
        pageTarget.addEventListener("pagehide", onPageHide);
        listeningPageHide = true;
      }
      timer = setT(onAcceptTimeout, acceptTimeoutMs);
      if (viewer) post({ kind: KIND_OPEN, viewer: viewer, client: clientId });
    }

    const statics = { CONNECTING: CONNECTING, OPEN: OPEN, CLOSING: CLOSING, CLOSED: CLOSED };
    Object.keys(statics).forEach(function (name) {
      PraxisSocket[name] = statics[name];
      PraxisSocket.prototype[name] = statics[name];
    });
    return PraxisSocket;
  }

  root.makePraxisSocketClass = makePraxisSocketClass;
  if (typeof document !== "undefined" && typeof root.BroadcastChannel === "function") {
    root.WebSocket = makePraxisSocketClass(root.BroadcastChannel, {});
  }
})(typeof window !== "undefined" ? window : globalThis);

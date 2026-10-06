// device/connect.js -- the page's answer to the kernel's USER_INTERACTION requests.
//
// The kernel (Pyodide, in a Web Worker) asks for user interaction through
// `web_bridge.request_user_interaction`, which posts on the `praxis_repl`
// BroadcastChannel:
//
//   {type: "USER_INTERACTION", payload: {id, interaction_type, payload}}
//
// and waits for
//
//   {type: "praxis:interaction_response", id, value}
//
// which the bootstrap's channel listener hands to
// `web_bridge.handle_interaction_response`. Until this module existed, the only
// thing that ever answered was the Angular app. Once that was dropped, every
// request went unanswered: `lh.setup()` on a WebUSB machine waited forever and the
// browser never showed its device picker.
//
// THE PICKER HAS TO OPEN HERE. `navigator.usb.requestDevice()`,
// `navigator.hid.requestDevice()` and `navigator.serial.requestPort()` do not
// exist in workers, and on the page they need a user gesture. So a
// `device_connect` request shows a small dialog whose Connect button calls the
// picker synchronously inside its click handler. Once the user picks a device,
// the worker's `getDevices()`/`getPorts()` lists it, because permissions are per
// origin.
//
// ACK FIRST. Every request is acknowledged with `{type:
// "praxis:interaction_ack", id}` on receipt, before the user does anything, so
// the kernel can tell "the user is deciding" from "nothing is listening" and
// fail in seconds in the second case.
//
// Interactions answered here (HANDLED_INTERACTIONS; a CI test checks that every
// type the kernel sends is in this list):
//   device_connect  payload {api: "usb"|"hid"|"serial", filters, message}
//                   value   {success: true, device} | {success: false, error}
//   pause           payload {message}  value true once the user continues
//   confirm         payload {message}  value true | false
//   input           payload {prompt}   value the typed string | null on cancel
//
// Plain text only: messages come from the kernel and are set with textContent,
// never as markup.

export const CHANNEL_NAME = "praxis_repl";
export const REQUEST_TYPE = "USER_INTERACTION";
export const ACK_TYPE = "praxis:interaction_ack";
export const RESPONSE_TYPE = "praxis:interaction_response";
export const HANDLED_INTERACTIONS = Object.freeze(["device_connect", "pause", "confirm", "input"]);
export const DEVICE_APIS = Object.freeze(["usb", "hid", "serial"]);
export const DIALOG_ATTR = "data-praxis-interaction";

/** Normalize a channel message into `{id, interactionType, payload}`, or null when
 * it is not a USER_INTERACTION request. Accepts the JSON-string form too. */
export function parseRequest(data) {
  let msg = data;
  if (typeof msg === "string") {
    try {
      msg = JSON.parse(msg);
    } catch {
      return null;
    }
  }
  if (!msg || msg.type !== REQUEST_TYPE || !msg.payload) return null;
  const { id, interaction_type: interactionType, payload } = msg.payload;
  if (typeof id !== "string" || typeof interactionType !== "string") return null;
  return { id, interactionType, payload: payload || {} };
}

/** The options object for the browser picker. Filters arrive in WebUSB's
 * `{vendorId, productId}` shape for every api; Web Serial calls them
 * `usbVendorId`/`usbProductId`. */
export function chooserOptions(api, filters) {
  const list = Array.isArray(filters) ? filters : [];
  if (api === "serial") {
    return {
      filters: list
        .filter((f) => f && f.vendorId !== undefined)
        .map((f) => {
          const out = { usbVendorId: f.vendorId };
          if (f.productId !== undefined) out.usbProductId = f.productId;
          return out;
        }),
    };
  }
  return { filters: list.map((f) => ({ ...f })) };
}

/** The chosen device from a picker result: HID's `requestDevice` resolves to an
 * array (empty when the user picked nothing); USB and serial resolve to one. */
export function pickedDevice(api, result) {
  if (api !== "hid") return result;
  if (!result || result.length === 0) {
    const err = new Error("No device selected.");
    err.name = "NotFoundError";
    throw err;
  }
  return result[0];
}

/** A plain, structured-cloneable summary of the chosen device. */
export function describeDevice(api, device) {
  if (!device) return {};
  if (api === "serial") {
    const info = typeof device.getInfo === "function" ? device.getInfo() : {};
    return { vendorId: info.usbVendorId, productId: info.usbProductId };
  }
  return {
    vendorId: device.vendorId,
    productId: device.productId,
    productName: device.productName,
    serialNumber: device.serialNumber,
  };
}

/** The error text sent back when the picker rejects. */
export function pickerErrorMessage(err) {
  if (err && err.name === "NotFoundError") return "No device selected.";
  if (err && err.name === "SecurityError") {
    return `The browser refused to open the device picker: ${err.message}`;
  }
  return (err && err.message) || String(err);
}

function styleDialog(el) {
  Object.assign(el.style, {
    position: "fixed",
    right: "16px",
    bottom: "16px",
    zIndex: "10000",
    maxWidth: "360px",
    padding: "12px 14px",
    borderRadius: "8px",
    background: "var(--jp-layout-color1, #fff)",
    color: "var(--jp-ui-font-color1, #111)",
    border: "1px solid var(--jp-border-color1, #999)",
    boxShadow: "0 4px 16px rgba(0, 0, 0, 0.25)",
    font: "13px/1.4 var(--jp-ui-font-family, system-ui, sans-serif)",
  });
}

/**
 * Listen on the praxis_repl channel and answer USER_INTERACTION requests.
 *
 * `options` (all optional, for tests): `channel` (a BroadcastChannel-like object),
 * `document`, `navigator`. Returns `{channel, pending(), dispose()}`.
 */
export function mountInteractions(win, options = {}) {
  const doc = options.document || win.document;
  const nav = options.navigator || win.navigator;
  const channel = options.channel || new win.BroadcastChannel(CHANNEL_NAME);
  const open = new Map(); // request id -> dialog element

  function close(id) {
    const el = open.get(id);
    if (!el) return;
    open.delete(id);
    if (el.parentNode) el.parentNode.removeChild(el);
  }

  function respond(id, value) {
    close(id);
    channel.postMessage({ type: RESPONSE_TYPE, id, value });
  }

  function button(label, action, primary) {
    const b = doc.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.setAttribute("data-action", action);
    Object.assign(b.style, { marginLeft: "8px", padding: "4px 12px", fontWeight: primary ? "600" : "400" });
    return b;
  }

  function show(req) {
    const { id, interactionType, payload } = req;
    const dialog = doc.createElement("div");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute(DIALOG_ATTR, interactionType);
    dialog.setAttribute("data-interaction-id", id);
    styleDialog(dialog);

    const text = doc.createElement("p");
    text.style.margin = "0 0 10px 0";
    text.textContent = String(
      (interactionType === "input" ? payload.prompt : payload.message) ||
        (interactionType === "device_connect" ? "Connect a device" : "Praxis needs your input"),
    );
    dialog.appendChild(text);

    let field = null;
    if (interactionType === "input") {
      field = doc.createElement("input");
      field.type = "text";
      field.setAttribute("data-field", "input");
      field.style.width = "100%";
      field.style.marginBottom = "10px";
      dialog.appendChild(field);
    }

    const row = doc.createElement("div");
    row.style.textAlign = "right";
    dialog.appendChild(row);

    if (interactionType === "device_connect") {
      const api = payload.api;
      const cancel = button("Cancel", "cancel", false);
      const connect = button("Connect…", "connect", true);
      cancel.addEventListener("click", () => respond(id, { success: false, error: "Cancelled by the user." }));
      // A named, synchronous on...Click function with the picker call directly in
      // it: the call is what spends the click's user activation, so nothing may
      // await or defer before it (web-repl/scripts/check_gesture_invariant.py).
      function onConnectClick() {
        const options = chooserOptions(api, payload.filters);
        const target = nav && nav[api];
        let picking;
        try {
          if (!target) {
            throw new Error(`navigator.${api} is not available in this browser (use Chrome or Edge)`);
          } else if (api === "serial") {
            picking = target.requestPort(options);
          } else {
            picking = target.requestDevice(options);
          }
        } catch (err) {
          picking = Promise.reject(err);
        }
        Promise.resolve(picking)
          .then((result) => pickedDevice(api, result))
          .then(
            (device) => respond(id, { success: true, device: describeDevice(api, device) }),
            (err) => respond(id, { success: false, error: pickerErrorMessage(err) }),
          );
      }
      connect.addEventListener("click", onConnectClick);
      row.appendChild(cancel);
      row.appendChild(connect);
    } else if (interactionType === "pause") {
      const go = button("Continue", "continue", true);
      go.addEventListener("click", () => respond(id, true));
      row.appendChild(go);
    } else if (interactionType === "confirm") {
      const no = button("Cancel", "cancel", false);
      const yes = button("OK", "ok", true);
      no.addEventListener("click", () => respond(id, false));
      yes.addEventListener("click", () => respond(id, true));
      row.appendChild(no);
      row.appendChild(yes);
    } else if (interactionType === "input") {
      const no = button("Cancel", "cancel", false);
      const yes = button("OK", "ok", true);
      no.addEventListener("click", () => respond(id, null));
      yes.addEventListener("click", () => respond(id, field.value));
      row.appendChild(no);
      row.appendChild(yes);
    }

    open.set(id, dialog);
    doc.body.appendChild(dialog);
  }

  function onMessage(event) {
    const data = event && event.data;
    // Answered from another tab on the same origin: drop our copy of the dialog.
    if (data && data.type === RESPONSE_TYPE && open.has(data.id)) {
      close(data.id);
      return;
    }
    const req = parseRequest(data);
    if (!req || open.has(req.id)) return;
    const handled = HANDLED_INTERACTIONS.includes(req.interactionType);
    channel.postMessage({ type: ACK_TYPE, id: req.id, interaction_type: req.interactionType, handled });
    if (!handled) {
      respond(req.id, {
        success: false,
        error: `The page has no handler for interaction ${JSON.stringify(req.interactionType)}.`,
      });
      return;
    }
    if (req.interactionType === "device_connect" && !DEVICE_APIS.includes(req.payload.api)) {
      respond(req.id, { success: false, error: `unknown device api ${JSON.stringify(req.payload.api)}` });
      return;
    }
    show(req);
  }

  channel.addEventListener("message", onMessage);

  return {
    channel,
    pending: () => [...open.keys()],
    dispose() {
      channel.removeEventListener("message", onMessage);
      for (const id of [...open.keys()]) close(id);
    },
  };
}

export function mount(win) {
  return mountInteractions(win);
}

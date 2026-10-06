// connect.test.js -- the page side of the kernel's USER_INTERACTION protocol
// (device/connect.js). Run with `bun test web-repl/shell/device`.
//
// The bug this guards (2026-10-06): `lh.setup()` on a WebUSB machine waited
// forever because nothing on the page answered `device_connect`. These pin that
// every request is acknowledged on receipt, that every handled type produces an
// answer, and that the device picker is opened INSIDE the click (the call is what
// spends the user gesture; opening it after an await is refused by the browser).

import { describe, expect, test } from "bun:test";

import {
  ACK_TYPE,
  HANDLED_INTERACTIONS,
  RESPONSE_TYPE,
  chooserOptions,
  mountInteractions,
  parseRequest,
} from "../connect.js";

// --- minimal fakes ----------------------------------------------------------

class FakeElement {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.attrs = {};
    this.style = {};
    this.children = [];
    this.parentNode = null;
    this.listeners = {};
    this.textContent = "";
    this.value = "";
  }
  setAttribute(k, v) {
    this.attrs[k] = String(v);
  }
  getAttribute(k) {
    return k in this.attrs ? this.attrs[k] : null;
  }
  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }
  removeChild(child) {
    this.children = this.children.filter((c) => c !== child);
    child.parentNode = null;
  }
  addEventListener(type, fn) {
    (this.listeners[type] ||= []).push(fn);
  }
  click() {
    for (const fn of this.listeners.click || []) fn({ type: "click" });
  }
  find(pred) {
    if (pred(this)) return this;
    for (const c of this.children) {
      const hit = c.find(pred);
      if (hit) return hit;
    }
    return null;
  }
}

function fakeDocument() {
  const body = new FakeElement("body");
  return {
    body,
    createElement: (tag) => new FakeElement(tag),
    dialogs: () => body.children.filter((c) => c.getAttribute("role") === "dialog"),
  };
}

function fakeChannel() {
  const listeners = [];
  return {
    posted: [],
    postMessage(msg) {
      this.posted.push(msg);
    },
    addEventListener(type, fn) {
      if (type === "message") listeners.push(fn);
    },
    removeEventListener(type, fn) {
      const i = listeners.indexOf(fn);
      if (i >= 0) listeners.splice(i, 1);
    },
    deliver(data) {
      for (const fn of listeners.slice()) fn({ data });
    },
  };
}

function request(id, interactionType, payload) {
  return { type: "USER_INTERACTION", payload: { id, interaction_type: interactionType, payload } };
}

function setup(nav = {}) {
  const doc = fakeDocument();
  const channel = fakeChannel();
  const handle = mountInteractions({}, { document: doc, navigator: nav, channel });
  return { doc, channel, handle };
}

function buttonIn(dialog, action) {
  return dialog.find((el) => el.getAttribute("data-action") === action);
}

const flush = () => new Promise((r) => setTimeout(r, 0));
const responses = (channel) => channel.posted.filter((m) => m.type === RESPONSE_TYPE);

// --- tests ------------------------------------------------------------------

describe("ack on receipt", () => {
  test("every request is acknowledged before the user does anything", () => {
    const { channel } = setup();
    channel.deliver(request("r1", "device_connect", { api: "usb", filters: [] }));
    expect(channel.posted[0]).toEqual({ type: ACK_TYPE, id: "r1", interaction_type: "device_connect", handled: true });
    expect(responses(channel)).toEqual([]);
  });

  test("an unknown interaction is acked as unhandled and answered with an error", () => {
    const { channel, doc } = setup();
    channel.deliver(request("r2", "frobnicate", {}));
    expect(channel.posted[0].handled).toBe(false);
    expect(responses(channel)[0].value.success).toBe(false);
    expect(responses(channel)[0].value.error).toContain("frobnicate");
    expect(doc.dialogs()).toEqual([]);
  });

  test("non-requests and repeats are ignored", () => {
    const { channel, doc } = setup();
    channel.deliver({ type: "praxis:shell-ping" });
    channel.deliver(request("r3", "pause", { message: "hi" }));
    channel.deliver(request("r3", "pause", { message: "hi" }));
    expect(channel.posted.filter((m) => m.type === ACK_TYPE).length).toBe(1);
    expect(doc.dialogs().length).toBe(1);
  });

  test("the JSON-string form of a request is accepted", () => {
    expect(parseRequest(JSON.stringify(request("r4", "pause", {})))).toEqual({
      id: "r4",
      interactionType: "pause",
      payload: {},
    });
    expect(parseRequest("not json")).toBeNull();
  });
});

describe("device_connect", () => {
  const STAR = { vendorId: 0x08af, productId: 0x8000 };

  test("Connect opens the USB picker synchronously inside the click, then reports the device", async () => {
    const calls = [];
    const nav = {
      usb: {
        requestDevice(options) {
          calls.push(options);
          return Promise.resolve({ vendorId: 0x08af, productId: 0x8000, productName: "STAR", serialNumber: "SN1" });
        },
      },
    };
    const { channel, doc } = setup(nav);
    channel.deliver(request("u1", "device_connect", { api: "usb", filters: [STAR], message: "Connect STAR" }));
    const [dialog] = doc.dialogs();
    expect(dialog.getAttribute("data-praxis-interaction")).toBe("device_connect");
    expect(dialog.children[0].textContent).toBe("Connect STAR");

    buttonIn(dialog, "connect").click();
    // No await between the click and the picker call: that is the user gesture.
    expect(calls).toEqual([{ filters: [STAR] }]);

    await flush();
    expect(responses(channel)).toEqual([
      {
        type: RESPONSE_TYPE,
        id: "u1",
        value: { success: true, device: { vendorId: 0x08af, productId: 0x8000, productName: "STAR", serialNumber: "SN1" } },
      },
    ]);
    expect(doc.dialogs()).toEqual([]);
  });

  test("closing the picker without choosing answers 'No device selected.'", async () => {
    const nav = {
      usb: {
        requestDevice: () => Promise.reject(Object.assign(new Error("No device selected."), { name: "NotFoundError" })),
      },
    };
    const { channel, doc } = setup(nav);
    channel.deliver(request("u2", "device_connect", { api: "usb", filters: [STAR] }));
    buttonIn(doc.dialogs()[0], "connect").click();
    await flush();
    expect(responses(channel)[0].value).toEqual({ success: false, error: "No device selected." });
  });

  test("Cancel answers without opening the picker", () => {
    let opened = false;
    const nav = { usb: { requestDevice: () => ((opened = true), Promise.resolve({})) } };
    const { channel, doc } = setup(nav);
    channel.deliver(request("u3", "device_connect", { api: "usb", filters: [] }));
    buttonIn(doc.dialogs()[0], "cancel").click();
    expect(opened).toBe(false);
    expect(responses(channel)[0].value).toEqual({ success: false, error: "Cancelled by the user." });
  });

  test("a browser without the api answers with an error naming it", async () => {
    const { channel, doc } = setup({});
    channel.deliver(request("u4", "device_connect", { api: "usb", filters: [] }));
    buttonIn(doc.dialogs()[0], "connect").click();
    await flush();
    expect(responses(channel)[0].value.success).toBe(false);
    expect(responses(channel)[0].value.error).toContain("navigator.usb is not available");
  });

  test("an unknown api is refused on receipt", () => {
    const { channel, doc } = setup({});
    channel.deliver(request("u5", "device_connect", { api: "bluetooth", filters: [] }));
    expect(doc.dialogs()).toEqual([]);
    expect(responses(channel)[0].value.error).toContain("bluetooth");
  });

  test("serial maps filters to usbVendorId/usbProductId and uses requestPort", async () => {
    const calls = [];
    const nav = {
      serial: {
        requestPort(options) {
          calls.push(options);
          return Promise.resolve({ getInfo: () => ({ usbVendorId: 0x2341, usbProductId: 0x43 }) });
        },
      },
    };
    const { channel, doc } = setup(nav);
    channel.deliver(request("s1", "device_connect", { api: "serial", filters: [{ vendorId: 0x2341, productId: 0x43 }] }));
    buttonIn(doc.dialogs()[0], "connect").click();
    expect(calls).toEqual([{ filters: [{ usbVendorId: 0x2341, usbProductId: 0x43 }] }]);
    await flush();
    expect(responses(channel)[0].value).toEqual({ success: true, device: { vendorId: 0x2341, productId: 0x43 } });
    expect(chooserOptions("serial", [{}])).toEqual({ filters: [] });
  });

  test("hid: an empty selection is 'No device selected.'", async () => {
    const nav = { hid: { requestDevice: () => Promise.resolve([]) } };
    const { channel, doc } = setup(nav);
    channel.deliver(request("h1", "device_connect", { api: "hid", filters: [] }));
    buttonIn(doc.dialogs()[0], "connect").click();
    await flush();
    expect(responses(channel)[0].value).toEqual({ success: false, error: "No device selected." });
  });

  test("an answer from another tab closes this tab's dialog", () => {
    const { channel, doc } = setup({});
    channel.deliver(request("t1", "device_connect", { api: "usb", filters: [] }));
    expect(doc.dialogs().length).toBe(1);
    channel.deliver({ type: RESPONSE_TYPE, id: "t1", value: { success: true } });
    expect(doc.dialogs()).toEqual([]);
    expect(responses(channel)).toEqual([]);
  });
});

describe("pause / confirm / input", () => {
  test("pause answers true on Continue", () => {
    const { channel, doc } = setup();
    channel.deliver(request("p1", "pause", { message: "Load the plate" }));
    expect(doc.dialogs()[0].children[0].textContent).toBe("Load the plate");
    buttonIn(doc.dialogs()[0], "continue").click();
    expect(responses(channel)[0].value).toBe(true);
  });

  test("confirm answers true / false", () => {
    const { channel, doc } = setup();
    channel.deliver(request("c1", "confirm", { message: "Go?" }));
    buttonIn(doc.dialogs()[0], "ok").click();
    channel.deliver(request("c2", "confirm", { message: "Go?" }));
    buttonIn(doc.dialogs()[0], "cancel").click();
    expect(responses(channel).map((m) => m.value)).toEqual([true, false]);
  });

  test("input answers the typed text, or null on cancel", () => {
    const { channel, doc } = setup();
    channel.deliver(request("i1", "input", { prompt: "Barcode?" }));
    const dialog = doc.dialogs()[0];
    expect(dialog.children[0].textContent).toBe("Barcode?");
    dialog.find((el) => el.getAttribute("data-field") === "input").value = "ABC123";
    buttonIn(dialog, "ok").click();
    channel.deliver(request("i2", "input", { prompt: "Barcode?" }));
    buttonIn(doc.dialogs()[0], "cancel").click();
    expect(responses(channel).map((m) => m.value)).toEqual(["ABC123", null]);
  });

  test("messages are plain text, never markup", () => {
    const { channel, doc } = setup();
    channel.deliver(request("x1", "pause", { message: "<img src=x onerror=alert(1)>" }));
    const p = doc.dialogs()[0].children[0];
    expect(p.textContent).toBe("<img src=x onerror=alert(1)>");
    expect(p.children).toEqual([]);
  });
});

test("every handled interaction produces an answer from its dialog", async () => {
  // The JS half of the protocol gate (the Python half checks the kernel only
  // sends types listed in HANDLED_INTERACTIONS): each listed type must render a
  // dialog whose buttons each answer.
  const nav = { usb: { requestDevice: () => Promise.resolve({ vendorId: 1, productId: 2 }) } };
  for (const type of HANDLED_INTERACTIONS) {
    const payload = type === "device_connect" ? { api: "usb", filters: [] } : { message: "m", prompt: "p" };
    const probe = setup(nav);
    probe.channel.deliver(request(`all-${type}`, type, payload));
    const [dialog] = probe.doc.dialogs();
    expect(dialog).toBeDefined();
    const buttons = [];
    dialog.find((el) => (el.tagName === "BUTTON" && buttons.push(el), false));
    expect(buttons.length).toBeGreaterThan(0);
    for (const b of buttons) {
      const p = setup(nav);
      p.channel.deliver(request(`btn-${type}`, type, payload));
      buttonIn(p.doc.dialogs()[0], b.getAttribute("data-action")).click();
      await flush();
      expect(responses(p.channel).length).toBe(1);
    }
  }
});

test("dispose stops listening and removes open dialogs", () => {
  const { channel, doc, handle } = setup();
  channel.deliver(request("d1", "pause", {}));
  handle.dispose();
  expect(doc.dialogs()).toEqual([]);
  channel.deliver(request("d2", "pause", {}));
  expect(doc.dialogs()).toEqual([]);
  expect(handle.pending()).toEqual([]);
});

"""The kernel -> page user-interaction protocol, and the shims' device authorization.

What broke (2026-10-06): ``lh.setup()`` on a Hamilton STAR stalled forever in the
browser and no USB picker ever appeared. ``WebUSB.setup()`` posts a
``USER_INTERACTION`` ``device_connect`` request and awaited the answer with no
timeout, and nothing on the page answered: the Angular app that used to was
dropped, and ``praxis-shell.js`` only answered ``praxis:shell-ping``. The shim
contract gate checked constructor signatures, not who answers ``setup()``'s
requests, so this reached hardware testing.

This file pins three things:

1. ``web_bridge.request_user_interaction`` fails in seconds with
   ``InteractionUnavailableError`` when no page handler acknowledges a request,
   instead of hanging; an acknowledged request still waits for the user.
2. Each shim, when no device is authorized, asks the page through
   ``web_bridge.request_device_authorization`` with the right api and filters,
   then picks up the device the user authorized.
3. The protocol gate: every interaction type the kernel can send has a handler in
   ``shell/device/connect.js``, the message-type constants agree between the JS and
   the bootstrap, and the shell loads the handler on every entry. Each check has a
   negative control.

The JS side's own behavior (ack on receipt, picker opened inside the click, every
handled type produces an answer) is in ``web-repl/shell/device/connect.test.js``;
the full journey in a real browser is ``scripts/device_connect_check.py``.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_OVERLAY_PYTHON_DIR = _WEB_REPL / "overlay" / "assets" / "python"
_SHIMS_DIR = _WEB_REPL / "overlay" / "assets" / "shims"
_WEB_BRIDGE_PATH = _OVERLAY_PYTHON_DIR / "web_bridge.py"
_CONNECT_JS = _WEB_REPL / "shell" / "device" / "connect.js"
_SHELL_JS = _WEB_REPL / "shell" / "praxis-shell.js"
_BOOTSTRAP = _WEB_REPL / "bootstrap" / "praxis_bootstrap.py"
_BUILD_REPL = _WEB_REPL / "scripts" / "build_repl.py"
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
for _p in (_SHIMS_DIR, _FIXTURES_DIR):
  if str(_p) not in sys.path:
    sys.path.insert(0, str(_p))

import fake_pyodide  # noqa: E402

# ---------------------------------------------------------------------------
# 1. web_bridge: ack, then answer
# ---------------------------------------------------------------------------


class FakeChannel:
  """A BroadcastChannel stand-in: records posts and plays the page's part."""

  def __init__(self, bridge, *, ack: bool, answer=None, answer_after: float = 0.0):
    self.bridge = bridge
    self.ack = ack
    self.answer = answer
    self.answer_after = answer_after
    self.posted: list[dict] = []

  def postMessage(self, msg):
    self.posted.append(msg)
    request_id = msg["payload"]["id"]
    loop = asyncio.get_event_loop()
    if self.ack:
      loop.call_soon(self.bridge.handle_interaction_ack, request_id)
    if self.answer is not None:
      loop.call_later(
        self.answer_after, self.bridge.handle_interaction_response, request_id, self.answer
      )


@pytest.fixture
def bridge(monkeypatch):
  """The real web_bridge.py, loaded with a stub ``js``/``pyodide`` (browser mode on)."""
  js_stub = types.ModuleType("js")
  js_stub.Object = types.SimpleNamespace(fromEntries=dict)
  js_stub.postMessage = lambda *_a, **_k: None
  pyodide = types.ModuleType("pyodide")
  ffi = types.ModuleType("pyodide.ffi")
  ffi.to_js = lambda value, *a, **k: value
  pyodide.ffi = ffi
  monkeypatch.setitem(sys.modules, "js", js_stub)
  monkeypatch.setitem(sys.modules, "pyodide", pyodide)
  monkeypatch.setitem(sys.modules, "pyodide.ffi", ffi)
  name = "web_bridge_interaction_under_test"
  spec = importlib.util.spec_from_file_location(name, _WEB_BRIDGE_PATH)
  module = importlib.util.module_from_spec(spec)
  monkeypatch.setitem(sys.modules, name, module)
  already = {m for m in sys.modules if m == "experimental" or m.startswith("experimental.")}
  sys.path.insert(0, str(_OVERLAY_PYTHON_DIR))
  try:
    spec.loader.exec_module(module)
  finally:
    sys.path.remove(str(_OVERLAY_PYTHON_DIR))
    for m in [m for m in sys.modules if m == "experimental" or m.startswith("experimental.")]:
      if m not in already:
        del sys.modules[m]
  assert module.IS_BROWSER_MODE, "stub pyodide must put web_bridge in browser mode"
  return module


def test_unacknowledged_request_fails_fast_instead_of_hanging(bridge):
  """Negative control for the original bug: no handler -> a clear error in ack_timeout."""
  channel = FakeChannel(bridge, ack=False)
  bridge.register_broadcast_channel(channel)

  async def go():
    return await bridge.request_user_interaction(
      "device_connect", {"api": "usb", "filters": []}, ack_timeout=0.05
    )

  with pytest.raises(bridge.InteractionUnavailableError, match="device_connect"):
    asyncio.run(asyncio.wait_for(go(), 2))
  assert channel.posted and channel.posted[0]["type"] == "USER_INTERACTION"
  assert not bridge._pending_interactions and not bridge._pending_acks


def test_acknowledged_request_waits_for_the_user(bridge):
  """An ack means the user is deciding: it must outlive ack_timeout."""
  channel = FakeChannel(bridge, ack=True, answer={"success": True}, answer_after=0.2)
  bridge.register_broadcast_channel(channel)

  async def go():
    return await bridge.request_user_interaction("confirm", {"message": "ok?"}, ack_timeout=0.05)

  assert asyncio.run(go()) == {"success": True}


def test_answer_without_ack_still_resolves(bridge):
  """A response implies receipt, even if its ack was lost."""
  channel = FakeChannel(bridge, ack=False, answer=True, answer_after=0.0)
  bridge.register_broadcast_channel(channel)

  async def go():
    return await bridge.request_user_interaction("pause", {"message": "x"}, ack_timeout=1.0)

  assert asyncio.run(go()) is True


def test_user_timeout_raises_timeout_error(bridge):
  channel = FakeChannel(bridge, ack=True)
  bridge.register_broadcast_channel(channel)

  async def go():
    return await bridge.request_user_interaction(
      "input", {"prompt": "x"}, ack_timeout=1.0, timeout=0.05
    )

  with pytest.raises(TimeoutError, match="input"):
    asyncio.run(go())


@pytest.mark.parametrize(
  ("answer", "error"),
  [
    ({"success": False, "error": "No device selected."}, "No device selected"),
    ({"success": False}, "no response"),
    (None, "no response"),
  ],
)
def test_device_authorization_raises_on_refusal(bridge, answer, error):
  async def fake_request(interaction_type, payload, **_kw):
    assert interaction_type == "device_connect"
    return answer

  bridge.request_user_interaction = fake_request

  async def go():
    return await bridge.request_device_authorization("usb", [], "m")

  with pytest.raises(RuntimeError, match=error):
    asyncio.run(go())


def test_device_authorization_sends_api_filters_and_message(bridge):
  channel = FakeChannel(bridge, ack=True, answer={"success": True, "device": {"vendorId": 1}})
  bridge.register_broadcast_channel(channel)
  filters = [{"vendorId": 0x08AF, "productId": 0x8000}]

  async def go():
    return await bridge.request_device_authorization("usb", filters, "Connect STAR")

  assert asyncio.run(go())["success"] is True
  sent = channel.posted[0]["payload"]
  assert sent["interaction_type"] == "device_connect"
  assert sent["payload"] == {"api": "usb", "filters": filters, "message": "Connect STAR"}


# ---------------------------------------------------------------------------
# 2. The shims ask the page, then use the device the user authorized
# ---------------------------------------------------------------------------

_SHIM_MODULES = ("web_usb_shim", "web_serial_shim", "web_hid_shim", "web_ftdi_shim")


class FakeBridge(types.ModuleType):
  """Stands in for web_bridge: records requests, 'authorizes' by adding a device."""

  def __init__(self, on_authorize=None, refuse: str | None = None):
    super().__init__("web_bridge")
    self.calls: list[tuple[str, list, str]] = []
    self.on_authorize = on_authorize
    self.refuse = refuse

  async def request_device_authorization(self, api, filters, message):
    self.calls.append((api, filters, message))
    if self.refuse:
      raise RuntimeError(f"Device authorization failed: {self.refuse}")
    if self.on_authorize:
      self.on_authorize()
    return {"success": True}


class FakeSerial:
  def __init__(self):
    self.ports: list = []

  async def getPorts(self):
    return list(self.ports)


class FakeHID:
  def __init__(self):
    self.devices: list = []

  async def getDevices(self):
    return list(self.devices)


@pytest.fixture
def browser(monkeypatch):
  nav = types.SimpleNamespace(usb=fake_pyodide.FakeUSB(), serial=FakeSerial(), hid=FakeHID())
  fake_pyodide.install(nav)
  for name in _SHIM_MODULES:
    sys.modules.pop(name, None)
  yield nav
  for name in (*_SHIM_MODULES, "web_bridge"):
    sys.modules.pop(name, None)
  fake_pyodide.uninstall()


def _use_bridge(monkeypatch, fake: FakeBridge) -> FakeBridge:
  monkeypatch.setitem(sys.modules, "web_bridge", fake)
  return fake


def _star_device():
  return fake_pyodide.FakeUSBDevice(
    0x08AF,
    0x8000,
    serialNumber="SN1",
    endpoints=[fake_pyodide.Endpoint(1, "in", 64), fake_pyodide.Endpoint(2, "out", 64)],
  )


def test_webusb_setup_asks_the_page_then_uses_the_authorized_device(browser, monkeypatch):
  """The Hamilton path: nothing authorized -> page picker -> device opened."""
  dev = _star_device()
  fake = _use_bridge(monkeypatch, FakeBridge(on_authorize=lambda: browser.usb.devices.append(dev)))
  WebUSB = importlib.import_module("web_usb_shim").WebUSB
  usb = WebUSB(0x08AF, 0x8000, "Hamilton Liquid Handler", packet_read_timeout=0.05)

  asyncio.run(usb.setup())

  assert usb.dev is dev
  [(api, filters, message)] = fake.calls
  assert api == "usb"
  assert filters == [{"vendorId": 0x08AF, "productId": 0x8000}]
  assert "Hamilton Liquid Handler" in message


def test_webusb_setup_skips_the_page_when_already_authorized(browser, monkeypatch):
  browser.usb.devices.append(_star_device())
  fake = _use_bridge(monkeypatch, FakeBridge())
  usb = importlib.import_module("web_usb_shim").WebUSB(0x08AF, 0x8000, packet_read_timeout=0.05)
  asyncio.run(usb.setup())
  assert fake.calls == []


def test_webusb_setup_reports_a_refused_picker(browser, monkeypatch):
  _use_bridge(monkeypatch, FakeBridge(refuse="No device selected."))
  usb = importlib.import_module("web_usb_shim").WebUSB(0x08AF, 0x8000)
  with pytest.raises(RuntimeError, match="No device selected"):
    asyncio.run(usb.setup())


def test_webusb_setup_reports_a_non_matching_choice(browser, monkeypatch):
  other = fake_pyodide.FakeUSBDevice(0x1234, 0x5678, serialNumber="X", endpoints=[])
  _use_bridge(monkeypatch, FakeBridge(on_authorize=lambda: browser.usb.devices.append(other)))
  usb = importlib.import_module("web_usb_shim").WebUSB(0x08AF, 0x8000, "STAR")
  with pytest.raises(RuntimeError, match="No matching USB device for 'STAR'"):
    asyncio.run(usb.setup())


def test_webftdi_setup_asks_the_page_with_its_vid_pid(browser, monkeypatch):
  dev = fake_pyodide.FakeUSBDevice(
    0x0403,
    0x6001,
    serialNumber="FT1",
    endpoints=[fake_pyodide.Endpoint(1, "in", 64), fake_pyodide.Endpoint(2, "out", 64)],
  )
  fake = _use_bridge(monkeypatch, FakeBridge(on_authorize=lambda: browser.usb.devices.append(dev)))
  WebFTDI = importlib.import_module("web_ftdi_shim").WebFTDI
  ftdi = WebFTDI("Plate reader", pid=0x6001)
  asyncio.run(ftdi.setup())
  assert ftdi._device is dev
  [(api, filters, _message)] = fake.calls
  assert api == "usb"
  assert filters == [{"vendorId": 0x0403, "productId": 0x6001}]


def test_webserial_setup_asks_the_page_for_a_port(browser, monkeypatch):
  port = fake_pyodide.FakeSerialPort()
  port.readable = types.SimpleNamespace(getReader=lambda: "reader")
  port.writable = types.SimpleNamespace(getWriter=lambda: "writer")
  fake = _use_bridge(
    monkeypatch, FakeBridge(on_authorize=lambda: browser.serial.ports.append(port))
  )
  WebSerial = importlib.import_module("web_serial_shim").WebSerial
  serial = WebSerial("Shaker", vid=0x2341, pid=0x0043, baudrate=115200)
  asyncio.run(serial.setup())
  assert port.opened_with["baudRate"] == 115200
  [(api, filters, _message)] = fake.calls
  assert api == "serial"
  assert filters == [{"vendorId": 0x2341, "productId": 0x0043}]


def test_webserial_no_vid_sends_no_filter(browser, monkeypatch):
  fake = _use_bridge(monkeypatch, FakeBridge())
  serial = importlib.import_module("web_serial_shim").WebSerial("Shaker")
  with pytest.raises(RuntimeError, match="No authorized serial port for 'Shaker'"):
    asyncio.run(serial.setup())
  assert fake.calls == [("serial", [], "Connect Shaker (serial port)")]


def test_webhid_setup_asks_the_page(browser, monkeypatch):
  fake = _use_bridge(monkeypatch, FakeBridge(refuse="Cancelled by the user."))
  WebHID = importlib.import_module("web_hid_shim").WebHID
  hid = WebHID("Scale", vid=0x0922, pid=0x8003)
  with pytest.raises(RuntimeError, match="Cancelled by the user"):
    asyncio.run(hid.setup())
  [(api, filters, _message)] = fake.calls
  assert api == "hid"
  assert filters == [{"vendorId": 0x0922, "productId": 0x8003}]


# ---------------------------------------------------------------------------
# 3. Protocol gate: every request the kernel sends has a handler on the page
# ---------------------------------------------------------------------------


def _js_string_array(source: str, name: str) -> list[str]:
  m = re.search(rf"export const {name} = Object\.freeze\(\[([^\]]*)\]\)", source)
  assert m, f"connect.js no longer declares {name} as a frozen string array"
  return re.findall(r'"([^"]+)"', m.group(1))


def _js_string_const(source: str, name: str) -> str:
  m = re.search(rf'export const {name} = "([^"]+)";', source)
  assert m, f"connect.js no longer declares {name}"
  return m.group(1)


def kernel_interactions(sources: dict[str, str]) -> tuple[set[str], set[str], list[str]]:
  """(interaction types, device apis, problems) the kernel-side Python can send.

  Walks every ``request_user_interaction(...)`` and
  ``request_device_authorization(...)`` call. A first argument that is not a
  string literal is a problem: the gate could not see what it sends.
  """
  types_: set[str] = set()
  apis: set[str] = set()
  problems: list[str] = []
  for label, src in sources.items():
    for node in ast.walk(ast.parse(src)):
      if not isinstance(node, ast.Call):
        continue
      fn = node.func
      name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
      if name not in ("request_user_interaction", "request_device_authorization"):
        continue
      if not node.args:
        problems.append(f"{label}:{node.lineno}: {name}() with no positional args")
        continue
      first = node.args[0]
      if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        problems.append(f"{label}:{node.lineno}: {name}() first arg is not a string literal")
        continue
      if name == "request_user_interaction":
        types_.add(first.value)
      else:
        types_.add("device_connect")
        apis.add(first.value)
  return types_, apis, problems


def _kernel_sources() -> dict[str, str]:
  paths = [
    *sorted(_SHIMS_DIR.glob("*.py")),
    *sorted(_OVERLAY_PYTHON_DIR.rglob("*.py")),
    *sorted((_WEB_REPL / "bootstrap").glob("*.py")),
  ]
  return {str(p.relative_to(_WEB_REPL)): p.read_text() for p in paths}


def test_every_kernel_interaction_has_a_page_handler():
  js = _CONNECT_JS.read_text()
  handled = set(_js_string_array(js, "HANDLED_INTERACTIONS"))
  device_apis = set(_js_string_array(js, "DEVICE_APIS"))
  sent, apis, problems = kernel_interactions(_kernel_sources())

  assert not problems, problems
  # Sanity: the scan sees the calls that motivated this gate.
  assert {"device_connect", "pause", "confirm", "input"} <= sent
  assert {"usb", "hid", "serial"} <= apis
  assert sent <= handled, (
    f"kernel sends interactions the page cannot answer: {sorted(sent - handled)}"
  )
  assert apis <= device_apis, f"device apis the page cannot open: {sorted(apis - device_apis)}"


def test_gate_flags_an_unhandled_interaction_and_a_dynamic_type():
  """Negative control: the scanner must see what a new call would send."""
  src = (
    "async def f(kind):\n"
    "    await request_user_interaction('frobnicate', {})\n"
    "    await web_bridge.request_device_authorization('bluetooth', [], 'x')\n"
    "    await request_user_interaction(kind, {})\n"
  )
  sent, apis, problems = kernel_interactions({"synthetic.py": src})
  handled = set(_js_string_array(_CONNECT_JS.read_text(), "HANDLED_INTERACTIONS"))
  assert "frobnicate" in sent - handled
  assert apis == {"bluetooth"}
  assert len(problems) == 1 and "synthetic.py:4" in problems[0]


def test_message_type_constants_agree_between_page_kernel_and_bootstrap():
  js = _CONNECT_JS.read_text()
  bridge_src = _WEB_BRIDGE_PATH.read_text()
  bootstrap_src = _BOOTSTRAP.read_text()
  assert f'"type": "{_js_string_const(js, "REQUEST_TYPE")}"' in bridge_src
  assert _js_string_const(js, "CHANNEL_NAME") == "praxis_repl"
  for const in ("ACK_TYPE", "RESPONSE_TYPE"):
    value = _js_string_const(js, const)
    assert f'msg_type == "{value}"' in bootstrap_src, (
      f"praxis_bootstrap.py does not route {value!r} to web_bridge"
    )
  assert "handle_interaction_ack" in bootstrap_src


def test_shell_loads_the_handler_on_every_entry():
  """The persistence/display loaders are lab/-only; this one must not be."""
  shell = _SHELL_JS.read_text()
  marker = 'import(new URL("device/connect.js", thisScript.src).href)'
  assert marker in shell
  block = shell[shell.rindex("(function () {", 0, shell.index(marker)) : shell.index(marker)]
  assert "/lab/" not in block, "device-connect loader must run on every entry, not only lab/"
  build = _BUILD_REPL.read_text()
  assert 'SHELL_DIR / "device"' in build
  assert 'out_dir / "shell" / "device" / "connect.js"' in build

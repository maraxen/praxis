"""A minimal stand-in for Pyodide's ``js`` / ``pyodide.ffi`` modules and the
browser's WebUSB / WebSerial objects, so the shims in
``web-repl/overlay/assets/shims/`` can be driven from plain CPython.

Faithful where the shims' correctness depends on it:

- ``FakeUSBDevice.transferIn`` BLOCKS until a packet is queued, returns at most
  one packet (<= ``length`` bytes) per call, and cannot be cancelled -- exactly
  like WebUSB, which has no transfer timeout and whose Promise keeps running
  when the awaiting Python task is cancelled. A shim that abandons a pending
  transfer on timeout loses the next packet here just as it would on hardware.
- Packets are served per endpoint number.

Everything else (``to_js``, ``create_proxy``, ``Uint8Array.new``) is identity-ish.

Used both in-process by ``test_shim_behavior.py`` and inside the wheel venv by
``test_shim_contract.py`` (via ``install()``), so stdlib only.
"""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass, field
from typing import Any


class JSArray(list):
    """A Python list that also has JS's ``.length`` (WebHID iterates by index)."""

    @property
    def length(self) -> int:
        return len(self)


class DataView:
    def __init__(self, payload: bytes):
        self._payload = bytes(payload)
        self.byteLength = len(self._payload)

    def getUint8(self, i: int) -> int:
        return self._payload[i]

    def getUint16(self, offset: int, little_endian: bool = False) -> int:
        return int.from_bytes(self._payload[offset : offset + 2], "little" if little_endian else "big")


@dataclass
class TransferResult:
    status: str = "ok"
    data: DataView | None = None
    bytesWritten: int = 0


@dataclass
class Endpoint:
    endpointNumber: int
    direction: str  # "in" | "out"
    packetSize: int = 64


@dataclass
class Alternate:
    endpoints: list[Endpoint]


@dataclass
class Interface:
    alternate: Alternate


@dataclass
class Configuration:
    interfaces: list[Interface]


class FakeUSBDevice:
    def __init__(
        self,
        vendorId: int,
        productId: int,
        serialNumber: str | None = None,
        endpoints: list[Endpoint] | None = None,
        productName: str = "fake",
    ):
        self.vendorId = vendorId
        self.productId = productId
        self.serialNumber = serialNumber
        self.productName = productName
        self.configuration = Configuration(
            [Interface(Alternate(endpoints or [Endpoint(1, "in"), Endpoint(2, "out")]))]
        )
        self.opened = False
        self.claimed: list[int] = []
        self.out: list[tuple[int, bytes]] = []
        self.control_out: list[dict] = []
        self._queues: dict[int, asyncio.Queue] = {}
        self.transfer_in_calls: list[tuple[int, int]] = []

    def _q(self, endpoint: int) -> asyncio.Queue:
        return self._queues.setdefault(endpoint, asyncio.Queue())

    def queue_in(self, endpoint: int, *packets: bytes) -> None:
        for packet in packets:
            self._q(endpoint).put_nowait(bytes(packet))

    async def open(self):
        self.opened = True

    async def close(self):
        self.opened = False

    async def selectConfiguration(self, n: int):
        pass

    async def claimInterface(self, n: int):
        self.claimed.append(n)

    async def releaseInterface(self, n: int):
        pass

    async def transferOut(self, endpoint: int, data: Any) -> TransferResult:
        payload = bytes(data)
        self.out.append((endpoint, payload))
        return TransferResult(bytesWritten=len(payload))

    def transferIn(self, endpoint: int, length: int) -> asyncio.Future[TransferResult]:
        """Like a JS Promise: abandoning the await does NOT cancel the transfer.

        The transfer stays in flight and still consumes the next queued packet,
        whose data then goes to nobody -- which is what WebUSB does when a
        Pyodide task awaiting ``transferIn`` is cancelled (e.g. by ``wait_for``).
        """
        self.transfer_in_calls.append((endpoint, length))

        async def _complete() -> TransferResult:
            packet = await self._q(endpoint).get()
            return TransferResult(data=DataView(packet[:length]))

        return asyncio.shield(asyncio.ensure_future(_complete()))

    async def controlTransferOut(self, setup: dict, data: Any = None) -> TransferResult:
        self.control_out.append(dict(setup))
        return TransferResult()

    async def controlTransferIn(self, setup: dict, length: int) -> TransferResult:
        return TransferResult(data=DataView(b"\x00" * length))


class FakeUSB:
    def __init__(self, devices: list[FakeUSBDevice] | None = None):
        self.devices = JSArray(devices or [])

    async def getDevices(self):
        return self.devices

    async def requestDevice(self, options):
        raise RuntimeError("requestDevice needs a user gesture (fake)")


class FakeSerialPort:
    def __init__(self):
        self.signals: list[dict] = []
        self.opened_with: dict | None = None

    async def open(self, options):
        self.opened_with = dict(options)

    async def close(self):
        pass

    async def setSignals(self, signals: dict):
        self.signals.append(dict(signals))


@dataclass
class FakeNavigator:
    usb: FakeUSB = field(default_factory=FakeUSB)


class _Uint8Array:
    @staticmethod
    def new(values):
        return bytes(values)


class _Proxy:
    def __init__(self, fn):
        self._fn = fn
        self.destroyed = False

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def destroy(self):
        self.destroyed = True


def install(navigator: Any | None = None) -> FakeNavigator:
    """Put fake ``js`` / ``pyodide`` / ``pyodide.ffi`` modules in ``sys.modules``.

    Must run before a shim module is (re-)imported: each shim decides
    ``IN_PYODIDE`` at import time.
    """
    navigator = navigator if navigator is not None else FakeNavigator()
    js = types.ModuleType("js")
    js.navigator = navigator
    js.Uint8Array = _Uint8Array
    js.Object = dict
    pyodide = types.ModuleType("pyodide")
    ffi = types.ModuleType("pyodide.ffi")
    ffi.to_js = lambda value, *a, **k: value
    ffi.create_proxy = _Proxy
    pyodide.ffi = ffi
    sys.modules["js"] = js
    sys.modules["pyodide"] = pyodide
    sys.modules["pyodide.ffi"] = ffi
    return navigator


def uninstall() -> None:
    for name in ("js", "pyodide", "pyodide.ffi"):
        sys.modules.pop(name, None)

"""Behavioral tests for the browser IO shims, driven from CPython against the fake
Pyodide/WebUSB layer in ``fixtures/fake_pyodide.py``.

``check_shim_contract.py`` (and ``test_shim_contract.py``) prove the shims accept
every call pylabrobot makes. These prove the shims do the right thing with them,
in particular the transfer semantics where a plausible-looking shim silently
loses device data:

- WebUSB's ``transferIn`` has no timeout and cannot be cancelled. A read that
  times out and simply abandons it hands the device's *next* packet to nobody.
  pylabrobot's ``setup()`` drains on open, so a shim that drains naively eats
  the first reply of every session.
- pylabrobot 1.0's ``FTDI.readline`` reads one byte at a time. A shim whose
  ``read(1)`` fetches a 64-byte packet and returns one byte drops the rest.

Pure CPython; no wheel, no browser.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_SHIMS_DIR = _TESTS_DIR.parent / "overlay" / "assets" / "shims"
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
for _p in (_SHIMS_DIR, _FIXTURES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import fake_pyodide  # noqa: E402

_SHIM_MODULES = ("web_usb_shim", "web_serial_shim", "web_hid_shim", "web_ftdi_shim")


@pytest.fixture
def nav():
    """Fresh fake browser + freshly imported shim modules (IN_PYODIDE is import-time)."""
    navigator = fake_pyodide.install()
    for name in _SHIM_MODULES:
        sys.modules.pop(name, None)
    yield navigator
    for name in _SHIM_MODULES:
        sys.modules.pop(name, None)
    fake_pyodide.uninstall()


def _shim(module: str, cls: str):
    return getattr(importlib.import_module(module), cls)


def _usb(nav, *, packet_size=64, endpoints=None, **kwargs):
    dev = fake_pyodide.FakeUSBDevice(
        0x08AF,
        0x8000,
        serialNumber="SN1",
        endpoints=endpoints
        or [fake_pyodide.Endpoint(1, "in", packet_size), fake_pyodide.Endpoint(2, "out", packet_size)],
    )
    nav.usb.devices.append(dev)
    WebUSB = _shim("web_usb_shim", "WebUSB")
    kwargs.setdefault("packet_read_timeout", 0.05)
    kwargs.setdefault("read_timeout", 0.5)
    usb = WebUSB(id_vendor=0x08AF, id_product=0x8000, **kwargs)
    return usb, dev


# --- WebUSB ------------------------------------------------------------------


def test_webusb_accepts_the_hamilton_constructor_call(nav):
    """The exact call from pylabrobot's hamilton/base.py that raised TypeError."""
    WebUSB = _shim("web_usb_shim", "WebUSB")
    usb = WebUSB(
        human_readable_device_name="Hamilton Liquid Handler",
        id_vendor=0x08AF,
        id_product=0x8000,
        device_address=None,
        write_timeout=30,
        serial_number=None,
    )
    assert usb.human_readable_device_name == "Hamilton Liquid Handler"


def test_webusb_positional_order_matches_pylabrobot(nav):
    WebUSB = _shim("web_usb_shim", "WebUSB")
    usb = WebUSB(0x1, 0x2, "Name", 7, "SN")
    assert (usb._device_address, usb._serial_number, usb.human_readable_device_name) == (7, "SN", "Name")


def test_webusb_read_concatenates_full_size_packets(nav):
    usb, dev = _usb(nav)

    async def go():
        await usb.setup(empty_buffer=False)
        dev.queue_in(1, b"A" * 64, b"B" * 64, b"C" * 10, b"next")
        first = await usb.read()
        second = await usb.read()
        return first, second

    first, second = asyncio.run(go())
    assert first == b"A" * 64 + b"B" * 64 + b"C" * 10
    assert second == b"next"


def test_webusb_read_honors_size(nav):
    usb, dev = _usb(nav)

    async def go():
        await usb.setup(empty_buffer=False)
        dev.queue_in(1, b"0123456789")
        return await usb.read(size=4), await usb.read()

    assert asyncio.run(go()) == (b"0123", b"456789")


def test_webusb_timed_out_read_does_not_lose_the_next_packet(nav):
    """NEGATIVE-control shape: a shim that abandons the pending transferIn passes
    the timeout assertion but fails the second one, because the abandoned transfer
    consumes ``late``.
    """
    usb, dev = _usb(nav)

    async def go():
        await usb.setup(empty_buffer=False)
        with pytest.raises(TimeoutError):
            await usb.read(timeout=0.1)
        dev.queue_in(1, b"late")
        return await usb.read()

    assert asyncio.run(go()) == b"late"
    # One transfer carried both reads: the timed-out one was resumed, not re-issued.
    assert len([c for c in dev.transfer_in_calls if c[0] == 1]) == 1


def test_webusb_setup_drains_stale_data_by_default(nav):
    usb, dev = _usb(nav)
    dev.queue_in(1, b"stale-1", b"stale-2")

    async def go():
        await usb.setup()
        dev.queue_in(1, b"fresh")
        return await usb.read()

    assert asyncio.run(go()) == b"fresh"


def test_webusb_setup_empty_buffer_false_keeps_data(nav):
    usb, dev = _usb(nav)
    dev.queue_in(1, b"keep")

    async def go():
        await usb.setup(empty_buffer=False)
        return await usb.read()

    assert asyncio.run(go()) == b"keep"


def test_webusb_drain_then_read_gets_new_data(nav):
    usb, dev = _usb(nav)

    async def go():
        await usb.setup(empty_buffer=False)
        dev.queue_in(1, b"junk")
        await usb.drain()
        dev.queue_in(1, b"reply")
        return await usb.read()

    assert asyncio.run(go()) == b"reply"


def test_webusb_endpoint_addresses_select_endpoints(nav):
    eps = [
        fake_pyodide.Endpoint(1, "in"),
        fake_pyodide.Endpoint(3, "in"),
        fake_pyodide.Endpoint(2, "out"),
        fake_pyodide.Endpoint(4, "out"),
    ]
    usb, dev = _usb(nav, endpoints=eps, read_endpoint_address=0x83, write_endpoint_address=0x04)

    async def go():
        await usb.setup(empty_buffer=False)
        await usb.write(b"cmd")
        dev.queue_in(3, b"from-ep3")
        return await usb.read()

    assert asyncio.run(go()) == b"from-ep3"
    assert dev.out == [(4, b"cmd")]


def test_webusb_read_endpoint_argument(nav):
    """nanodrop_1000.py calls read(timeout=..., size=64, endpoint=self.EP_IN)."""
    eps = [fake_pyodide.Endpoint(1, "in"), fake_pyodide.Endpoint(5, "in"), fake_pyodide.Endpoint(2, "out")]
    usb, dev = _usb(nav, endpoints=eps)

    async def go():
        await usb.setup(empty_buffer=False)
        dev.queue_in(5, b"ep5")
        return await usb.read(timeout=0.5, size=64, endpoint=0x85)

    assert asyncio.run(go()) == b"ep5"


def test_webusb_serial_number_selects_device(nav):
    other = fake_pyodide.FakeUSBDevice(0x08AF, 0x8000, serialNumber="OTHER")
    nav.usb.devices.append(other)
    usb, dev = _usb(nav, serial_number="SN1")
    asyncio.run(usb.setup(empty_buffer=False))
    assert usb.dev is dev


def test_webusb_serialize_matches_pylabrobot_keys(nav):
    usb, _ = _usb(nav, human_readable_device_name="X", read_endpoint_address=0x81)
    data = usb.serialize()
    assert {
        "human_readable_device_name",
        "id_vendor",
        "id_product",
        "device_address",
        "serial_number",
        "packet_read_timeout",
        "read_timeout",
        "write_timeout",
        "read_endpoint_address",
    } <= set(data)
    clone = type(usb).deserialize(data)
    assert clone.serialize() == data


# --- WebFTDI -----------------------------------------------------------------


def _ftdi(nav, *devices, **kwargs):
    for d in devices:
        nav.usb.devices.append(d)
    WebFTDI = _shim("web_ftdi_shim", "WebFTDI")
    return WebFTDI(**kwargs)


def _ftdi_dev(serial="FT1", pid=0x6001):
    return fake_pyodide.FakeUSBDevice(0x0403, pid, serialNumber=serial)


def test_webftdi_read_one_byte_does_not_drop_the_rest(nav):
    dev = _ftdi_dev()
    ftdi = _ftdi(nav, dev, human_readable_device_name="reader")

    async def go():
        await ftdi.setup()
        dev.queue_in(1, b"\x01\x60" + b"abc")  # 2 modem-status bytes + payload
        # Bounded: a shim that dropped "bc" blocks forever in its next transferIn.
        return [await asyncio.wait_for(ftdi.read(1), 2) for _ in range(3)]

    assert asyncio.run(go()) == [b"a", b"b", b"c"]


def test_webftdi_readline_matches_pylabrobot_contract(nav):
    dev = _ftdi_dev()
    ftdi = _ftdi(nav, dev, human_readable_device_name="reader")

    async def go():
        await ftdi.setup()
        dev.queue_in(1, b"\x01\x60OK\r", b"\x01\x60\nrest")
        line = await asyncio.wait_for(ftdi.readline(terminator=b"\r\n", timeout=1), 2)
        tail = await asyncio.wait_for(ftdi.read(4), 2)
        return line, tail

    assert asyncio.run(go()) == (b"OK\r\n", b"rest")


def test_webftdi_readline_rejects_empty_terminator(nav):
    ftdi = _ftdi(nav, _ftdi_dev())

    async def go():
        await ftdi.setup()
        await ftdi.readline(terminator=b"")

    with pytest.raises(ValueError):
        asyncio.run(go())


def test_webftdi_selects_device_by_device_id_and_reports_it(nav):
    a, b = _ftdi_dev("AAA"), _ftdi_dev("BBB")
    ftdi = _ftdi(nav, a, b, human_readable_device_name="x", device_id="BBB")

    async def go():
        await ftdi.setup()
        return ftdi.device_id, await ftdi.request_serial()

    assert asyncio.run(go()) == ("BBB", "BBB")
    assert ftdi._device is b


def test_webftdi_device_id_before_setup_raises(nav):
    ftdi = _ftdi(nav, _ftdi_dev())
    with pytest.raises(RuntimeError):
        _ = ftdi.device_id


def test_webftdi_interface_select_claims_that_interface(nav):
    dev = _ftdi_dev(pid=0x6010)
    dev.configuration.interfaces.append(
        fake_pyodide.Interface(fake_pyodide.Alternate([fake_pyodide.Endpoint(3, "in"), fake_pyodide.Endpoint(4, "out")]))
    )
    ftdi = _ftdi(nav, dev, interface_select=2)
    asyncio.run(ftdi.setup())
    assert dev.claimed == [1]
    assert (ftdi._ep_in, ftdi._ep_out) == (3, 4)


# --- WebSerial ---------------------------------------------------------------


def test_webserial_no_arg_construction_still_works(nav):
    """scripts/repl_smoke.py probes ``builtins.WebSerial()`` with no arguments."""
    WebSerial = _shim("web_serial_shim", "WebSerial")
    assert WebSerial().human_readable_device_name


def test_webserial_positional_name_first(nav):
    WebSerial = _shim("web_serial_shim", "WebSerial")
    s = WebSerial("Scale", None, 0x1, 0x2, 115200)
    assert (s.human_readable_device_name, s._vid, s._pid, s.baudrate) == ("Scale", 1, 2, 115200)


def test_webserial_temporary_timeout_restores(nav):
    WebSerial = _shim("web_serial_shim", "WebSerial")
    s = WebSerial("x", timeout=1)
    with s.temporary_timeout(5):
        assert s.get_read_timeout() == 5
    assert s.get_read_timeout() == 1
    with pytest.raises(KeyError), s.temporary_timeout(9):
        raise KeyError
    assert s.get_read_timeout() == 1


def test_webserial_send_break_toggles_break_signal(nav):
    WebSerial = _shim("web_serial_shim", "WebSerial")
    port = fake_pyodide.FakeSerialPort()
    s = WebSerial("x", port=port)
    asyncio.run(s.send_break(0.01))
    assert port.signals == [{"break": True}, {"break": False}]


def test_webserial_send_break_on_ftdi_sets_and_clears_break_bit(nav):
    WebSerial = _shim("web_serial_shim", "WebSerial")
    s = WebSerial("x")
    dev = _ftdi_dev()
    s._is_ftdi, s._device = True, dev
    asyncio.run(s.send_break(0.01))
    values = [c["value"] for c in dev.control_out if c["request"] == 4]
    assert len(values) == 2
    assert values[0] & (1 << 14) and not values[1] & (1 << 14)
    assert values[0] & ~(1 << 14) == values[1]


# --- WebHID ------------------------------------------------------------------


def test_webhid_positional_order_matches_pylabrobot(nav):
    WebHID = _shim("web_hid_shim", "WebHID")
    h = WebHID("Inheco", 0x1, 0x2, "SN")
    assert (h.human_readable_device_name, h.vid, h.pid, h.serial_number) == ("Inheco", 1, 2, "SN")
    assert h.serialize() == {
        "human_readable_device_name": "Inheco",
        "vid": 1,
        "pid": 2,
        "serial_number": "SN",
    }


def test_every_shim_still_refuses_to_construct_outside_pyodide():
    """IN_PYODIDE gating survives the signature changes (no fake installed here)."""
    fake_pyodide.uninstall()
    for name in _SHIM_MODULES:
        sys.modules.pop(name, None)
    try:
        for module, cls in [
            ("web_usb_shim", "WebUSB"),
            ("web_serial_shim", "WebSerial"),
            ("web_hid_shim", "WebHID"),
            ("web_ftdi_shim", "WebFTDI"),
        ]:
            klass = _shim(module, cls)
            required = [
                p
                for p in list(inspect.signature(klass).parameters.values())
                if p.default is inspect.Parameter.empty
            ]
            with pytest.raises(RuntimeError, match="Pyodide"):
                klass(*[1] * len(required))
    finally:
        for name in _SHIM_MODULES:
            sys.modules.pop(name, None)

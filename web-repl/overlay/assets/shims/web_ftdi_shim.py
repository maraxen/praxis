"""WebFTDI Shim for Pyodide/Browser Environment

This module provides a WebUSB-based implementation of pylabrobot's FTDI interface,
enabling FTDI USB-to-Serial communication from the browser using the WebUSB API.

This is specifically for backends like CLARIOstarBackend that use FTDI directly:
    from pylabrobot.io.ftdi import FTDI
    self.io = FTDI(human_readable_device_name="CLARIOstar", device_id=device_id)

Usage in JupyterLite/Pyodide:
    from web_ftdi_shim import WebFTDI

    # Patch FTDI before importing backends
    import pylabrobot.io.ftdi as plr_ftdi
    plr_ftdi.FTDI = WebFTDI

    # Now CLARIOstarBackend will use WebFTDI
    from pylabrobot.legacy.plate_reading.bmg_labtech.clario_star_backend import CLARIOstarBackend
"""

import asyncio
import logging
from typing import Any

# Import Pyodide's JavaScript bridge
try:
  from js import Object, Uint8Array, navigator
  from pyodide.ffi import create_proxy, to_js

  IN_PYODIDE = True
except ImportError:
  IN_PYODIDE = False
  navigator = None

logger = logging.getLogger(__name__)

# FTDI Vendor ID
FTDI_VENDOR_ID = 0x0403

# Common FTDI Product IDs
FTDI_PRODUCT_IDS = {
  0x6001: "FT232R/FT232BM",
  0x6010: "FT2232",
  0x6014: "FT232H",
  0x6015: "FT-X Series",
  0xBB68: "CLARIOstar",
}

# Common baud rate divisors for FTDI
BAUD_DIVISORS = {
  9600: (0x4138, 0x0000),
  19200: (0x809C, 0x0000),
  38400: (0xC04E, 0x0000),
  57600: (0x0034, 0x0000),
  115200: (0x001A, 0x0000),
  125000: (0x0018, 0x0000),  # CLARIOstar uses this
  230400: (0x000D, 0x0000),
}


class WebFTDI:
  """WebUSB-based FTDI implementation for browser environments.

  Implements the same interface as pylabrobot.io.ftdi.FTDI but uses
  the browser's WebUSB API via Pyodide's JS bridge.

  This is a drop-in replacement for FTDI when running in the browser. The
  constructor and method signatures mirror the pylabrobot pin exactly (parameter
  order included) -- ``web-repl/scripts/check_shim_contract.py`` fails CI if
  they drift.
  """

  def __init__(
    self,
    human_readable_device_name: str = "WebFTDI device",
    device_id: str | None = None,
    vid: int | None = None,
    pid: int | None = None,
    interface_select: int | None = None,
    usb_address: str | None = None,
  ):
    """Initialize WebFTDI.

    Args:
        human_readable_device_name: Name used in log and error messages
        device_id: Serial number of the device to use. None = any matching device.
        vid: USB vendor ID to match (default: the FTDI vendor ID, 0x0403)
        pid: USB product ID to match. None = any FTDI product.
        interface_select: 1-based FTDI interface (A=1, B=2, ...) on multi-port chips.
        usb_address: '<bus>-<port>[.<port>...]' topology path. WebUSB does not expose
          bus topology, so it is accepted for compatibility and warned about at setup.

    """
    if not IN_PYODIDE:
      raise RuntimeError("WebFTDI is only available in Pyodide/browser environment")

    self.human_readable_device_name = human_readable_device_name
    self._requested_device_id = device_id
    self._device_id: str | None = None  # resolved serial number, set by setup()
    self._vid = vid
    self._pid = pid
    self._interface_select = interface_select
    self._usb_address = usb_address
    self._interface_number = (interface_select or 1) - 1
    self._rx_buffer = bytearray()
    self._device: Any = None
    self._ep_in: int = 1
    self._ep_out: int = 2
    self._baudrate: int = 9600
    self._port_name: str = "WebFTDI"

    logger.info(f"[WebFTDI] Created instance with device_id={device_id}")

  async def setup(self):
    """Initialize the FTDI connection.

    This will search for authorized FTDI devices via WebUSB and
    configure the serial parameters.
    """
    if not hasattr(navigator, "usb"):
      raise RuntimeError(
        "WebUSB is not supported in this browser. Please use Chrome, Edge, or Opera."
      )

    logger.info("[WebFTDI] setup() called, looking for FTDI devices...")

    # Get authorized USB devices
    try:
      usb_devices = await navigator.usb.getDevices()
      logger.info(f"[WebFTDI] Found {len(list(usb_devices))} authorized USB devices")
    except Exception as e:
      raise RuntimeError(f"[WebFTDI] Failed to get USB devices: {e}")

    if self._usb_address is not None:
      logger.warning(
        "[WebFTDI] %s: usb_address=%r cannot be resolved in the browser (WebUSB "
        "exposes no bus topology); matching on device_id/vid/pid only.",
        self.human_readable_device_name,
        self._usb_address,
      )

    # Find FTDI device
    want_vid = self._vid if self._vid is not None else FTDI_VENDOR_ID
    self._device = None
    for device in usb_devices:
      vid = device.vendorId
      pid = device.productId
      logger.info(f"[WebFTDI] Checking device {hex(vid)}:{hex(pid)}")

      if vid != want_vid or (self._pid is not None and pid != self._pid):
        continue
      if (
        self._requested_device_id is not None
        and getattr(device, "serialNumber", None) != self._requested_device_id
      ):
        continue
      product_name = FTDI_PRODUCT_IDS.get(pid, "Unknown FTDI")
      logger.info(f"[WebFTDI] Found FTDI device: {product_name} ({hex(vid)}:{hex(pid)})")
      self._device = device
      break

    if self._device is None:
      raise RuntimeError(
        f"[WebFTDI] No FTDI device found for '{self.human_readable_device_name}'. "
        "Please authorize an FTDI device via the Hardware Discovery dialog first."
      )
    self._device_id = (
      str(self._device.serialNumber) if getattr(self._device, "serialNumber", None) else ""
    ) or self._requested_device_id or f"{hex(self._device.vendorId)}:{hex(self._device.productId)}"
    self._rx_buffer.clear()

    # Open and configure the device
    try:
      await self._device.open()
      logger.info("[WebFTDI] Device opened")
    except Exception as e:
      if "already open" in str(e).lower():
        logger.info("[WebFTDI] Device already open")
      else:
        raise RuntimeError(f"[WebFTDI] Failed to open device: {e}")

    # Select configuration
    if self._device.configuration is None:
      try:
        await self._device.selectConfiguration(1)
        logger.info("[WebFTDI] Configuration 1 selected")
      except Exception as e:
        logger.warning(f"[WebFTDI] selectConfiguration failed: {e}")

    # Claim the selected interface (interface_select is 1-based, like libftdi)
    try:
      await self._device.claimInterface(self._interface_number)
      logger.info(f"[WebFTDI] Interface {self._interface_number} claimed")
    except Exception as e:
      if "already claimed" in str(e).lower():
        logger.info("[WebFTDI] Interface already claimed")
      else:
        raise RuntimeError(f"[WebFTDI] Failed to claim interface: {e}")

    # Find endpoints
    try:
      config = self._device.configuration
      if config and config.interfaces:
        iface = config.interfaces[self._interface_number]
        if hasattr(iface, "alternate") and iface.alternate:
          for ep in iface.alternate.endpoints:
            if ep.direction == "in":
              self._ep_in = ep.endpointNumber
            if ep.direction == "out":
              self._ep_out = ep.endpointNumber
      logger.info(f"[WebFTDI] Endpoints: IN={self._ep_in}, OUT={self._ep_out}")
    except Exception as e:
      logger.warning(f"[WebFTDI] Could not enumerate endpoints: {e}")

    # Reset device
    await self._control_transfer(0, 0, 0)  # RESET
    logger.info("[WebFTDI] Device reset complete")

    self._port_name = f"WebFTDI[{hex(self._device.vendorId)}:{hex(self._device.productId)}]"
    logger.info(f"[WebFTDI] Setup complete: {self._port_name}")

  async def stop(self):
    """Close the FTDI connection."""
    if self._device is None:
      return

    try:
      await self._device.releaseInterface(self._interface_number)
      await self._device.close()
      self._device = None
      logger.info("[WebFTDI] Device closed")
    except Exception as e:
      logger.warning(f"[WebFTDI] Error closing device: {e}")

  async def _control_transfer(self, request: int, value: int, index: int):
    """Send a control transfer to the FTDI device."""
    await self._device.controlTransferOut(
      to_js(
        {
          "requestType": "vendor",
          "recipient": "device",
          "request": request,
          "value": value,
          "index": index,
        }
      )
    )

  async def set_baudrate(self, baudrate: int):
    """Set the baud rate."""
    self._baudrate = baudrate
    value, index = self._calculate_baud_divisors(baudrate)
    await self._control_transfer(3, value, index)  # SET_BAUD_RATE
    logger.info(f"[WebFTDI] Baud rate set to {baudrate}")

  def _calculate_baud_divisors(self, baud: int) -> tuple:
    """Calculate FTDI baud rate divisors."""
    if baud in BAUD_DIVISORS:
      return BAUD_DIVISORS[baud]

    # For non-standard baud rates, calculate divisor
    # FTDI uses 3MHz base clock with fractional divisor
    base_clock = 3000000
    divisor = int(base_clock / baud)

    if divisor < 1:
      divisor = 1
    if divisor > 0x3FFF:
      divisor = 0x3FFF

    return (divisor, 0)

  async def set_line_property(self, bits: int, stopbits: int, parity: int):
    """Set line properties (data bits, stop bits, parity).

    Args:
        bits: Data bits (7 or 8)
        stopbits: Stop bits (0=1 stop bit, 2=2 stop bits)
        parity: Parity (0=None, 1=Odd, 2=Even)

    """
    value = bits  # Data bits in lower byte
    value |= parity << 8  # Parity in bits 8-10
    value |= stopbits << 11  # Stop bits in bits 11-12

    await self._control_transfer(4, value, 0)  # SET_DATA
    logger.info(f"[WebFTDI] Line property set: {bits}N{1 if stopbits == 0 else 2}")

  async def set_latency_timer(self, latency: int):
    """Set the latency timer (affects read timeout granularity)."""
    await self._control_transfer(9, latency, 0)  # SET_LATENCY_TIMER
    logger.info(f"[WebFTDI] Latency timer set to {latency}ms")

  async def set_rts(self, level: bool):
    """Set RTS line state."""
    value = 0x0200 | (0x0002 if level else 0x0000)
    await self._control_transfer(1, value, 0)  # SET_MODEM_CTRL

  async def set_dtr(self, level: bool):
    """Set DTR line state."""
    value = 0x0100 | (0x0001 if level else 0x0000)
    await self._control_transfer(1, value, 0)  # SET_MODEM_CTRL

  async def usb_reset(self):
    """Reset the USB device."""
    await self._control_transfer(0, 0, 0)  # RESET
    logger.info("[WebFTDI] USB reset")

  async def usb_purge_rx_buffer(self):
    """Purge the receive buffer."""
    self._rx_buffer.clear()
    await self._control_transfer(0, 1, 0)  # RESET_RX
    logger.info("[WebFTDI] RX buffer purged")

  async def usb_purge_tx_buffer(self):
    """Purge the transmit buffer."""
    await self._control_transfer(0, 2, 0)  # RESET_TX
    logger.info("[WebFTDI] TX buffer purged")

  async def set_flowctrl(self, flowctrl: int):
    """Set flow control mode."""
    # flowctrl: 0=None, 1=RTS/CTS, 2=DTR/DSR, 3=XON/XOFF
    await self._control_transfer(2, 0, flowctrl << 8)  # SET_FLOW_CTRL

  async def poll_modem_status(self) -> int:
    """Poll modem status lines."""
    try:
      result = await self._device.controlTransferIn(
        to_js(
          {
            "requestType": "vendor",
            "recipient": "device",
            "request": 5,  # GET_MODEM_STATUS
            "value": 0,
            "index": 0,
          }
        ),
        2,  # 2 bytes
      )
      if result.status == "ok" and result.data:
        return result.data.getUint16(0, True)
    except Exception as e:
      logger.warning(f"[WebFTDI] poll_modem_status failed: {e}")
    return 0

  @property
  def device_id(self) -> str:
    """Serial number of the connected device (pylabrobot's FTDI.device_id)."""
    if self._device_id is None:
      raise RuntimeError("Device not initialized. Call setup() first.")
    return self._device_id

  async def request_serial(self) -> str:
    return self.device_id

  async def get_serial(self) -> str:
    """Get the device serial number."""
    if self._device and hasattr(self._device, "serialNumber"):
      return str(self._device.serialNumber) if self._device.serialNumber else ""
    return ""

  async def write(self, data: bytes) -> int:
    """Write data to the FTDI device.

    Returns:
        Number of bytes written.

    """
    if self._device is None:
      raise RuntimeError("[WebFTDI] Device not connected. Call setup() first.")

    js_data = Uint8Array.new(list(data))

    try:
      result = await self._device.transferOut(self._ep_out, js_data)
      bytes_written = len(data)
      logger.debug(f"[WebFTDI] Wrote {bytes_written} bytes: {data.hex()}")
      return bytes_written
    except Exception as e:
      raise RuntimeError(f"[WebFTDI] Write failed: {e}")

  async def read(self, num_bytes: int = 1) -> bytes:
    """Read up to ``num_bytes`` from the FTDI device (b"" if nothing is waiting).

    FTDI prepends 2 modem status bytes to each packet; they are stripped. Bytes
    beyond ``num_bytes`` stay buffered for the next read rather than being dropped
    (pylabrobot's readline reads one byte at a time).
    """
    if self._device is None:
      raise RuntimeError("[WebFTDI] Device not connected. Call setup() first.")

    if not self._rx_buffer:
      try:
        result = await self._device.transferIn(self._ep_in, max(64, num_bytes + 2))
        if result.status == "ok" and result.data and result.data.byteLength > 2:
          dv = result.data
          self._rx_buffer.extend(dv.getUint8(i) for i in range(2, dv.byteLength))
      except Exception as e:
        logger.warning(f"[WebFTDI] Read failed: {e}")
        return b""

    chunk = bytes(self._rx_buffer[:num_bytes])
    del self._rx_buffer[:num_bytes]
    if chunk:
      logger.debug(f"[WebFTDI] Read {len(chunk)} bytes: {chunk.hex()}")
    return chunk

  async def readline(self, terminator: bytes = b"\n", timeout: float | None = None) -> bytes:
    """Read until ``terminator``, returning the line with the terminator on it.

    Same contract as pylabrobot's FTDI.readline: ValueError on an empty
    terminator, TimeoutError if no complete line arrives within ``timeout``
    seconds (None waits indefinitely).
    """
    if not terminator:
      raise ValueError("terminator must be at least one byte")
    loop = asyncio.get_running_loop()
    deadline = None if timeout is None else loop.time() + timeout
    line = bytearray()
    while not line.endswith(terminator):
      chunk = await self.read(1)
      if chunk:
        line.extend(chunk)
        continue
      if deadline is not None and loop.time() >= deadline:
        raise TimeoutError(
          f"'{self.human_readable_device_name}' sent no complete line within {timeout} s; "
          f"received {bytes(line)!r} so far."
        )
      await asyncio.sleep(0)
    return bytes(line)

  def serialize(self) -> dict:
    """Serialize the backend to a dictionary."""
    return {
      "type": "WebFTDI",
      "human_readable_device_name": self.human_readable_device_name,
      "device_id": self._device_id if self._device_id is not None else self._requested_device_id,
      "vid": self._vid,
      "pid": self._pid,
      "usb_address": self._usb_address,
      "baudrate": self._baudrate,
    }

  @classmethod
  def deserialize(cls, data: dict) -> "WebFTDI":
    """Deserialize from dict."""
    return cls(
      human_readable_device_name=data.get("human_readable_device_name", "WebFTDI device"),
      device_id=data.get("device_id"),
      vid=data.get("vid"),
      pid=data.get("pid"),
      usb_address=data.get("usb_address"),
    )


# For backwards compatibility with pylabrobot.io.ftdi
FTDI = WebFTDI

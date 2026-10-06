"""WebUSB Shim for Pyodide/Browser Environment

This module provides a WebUSB-based implementation of pylabrobot's USB interface,
enabling USB device communication from the browser using the WebUSB API.

Usage in JupyterLite:
    from web_usb_shim import WebUSB

    # Request a USB device (user must approve in browser dialog)
    usb = WebUSB(id_vendor=0x0483, id_product=0x5740)
    await usb.setup()

    # Use like regular USB
    await usb.write(b"command")
    response = await usb.read()
"""

import asyncio
import logging
import time
from collections.abc import Callable
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


class WebUSB:
  """WebUSB-based USB implementation for browser environments.

  Implements the same interface as pylabrobot.io.USB but uses
  the browser's WebUSB API via Pyodide's JS bridge. The constructor and method
  signatures mirror the pylabrobot pin exactly (parameter order included) --
  ``web-repl/scripts/check_shim_contract.py`` fails CI if they drift.
  """

  def __init__(
    self,
    id_vendor: int,
    id_product: int,
    human_readable_device_name: str = "WebUSB device",
    device_address: int | None = None,
    serial_number: str | None = None,
    packet_read_timeout: float = 3,
    read_timeout: int = 30,
    write_timeout: int = 30,
    configuration_callback: Callable[[Any], None] | None = None,
    max_workers: int = 1,
    read_endpoint_address: int | None = None,
    write_endpoint_address: int | None = None,
  ):
    """Initialize WebUSB.

    Args:
        id_vendor: USB Vendor ID
        id_product: USB Product ID
        human_readable_device_name: Name used in log and error messages
        device_address: Device address. Accepted for signature compatibility;
          WebUSB does not expose bus addresses, so it cannot be used to pick a device.
        serial_number: Device serial number (optional, used to pick a device)
        packet_read_timeout: Packet read timeout in seconds
        read_timeout: Overall read timeout in seconds
        write_timeout: Write timeout in seconds
        configuration_callback: pylabrobot calls this with a pyusb Device. There is
          no pyusb Device in the browser, so it is accepted and ignored (with a
          warning at setup); configuration 1 is selected instead.
        max_workers: Thread-pool size in pylabrobot. WebUSB transfers are already
          awaitable, so it is accepted and ignored.
        read_endpoint_address: IN endpoint address (e.g. 0x81). None = first IN endpoint.
        write_endpoint_address: OUT endpoint address (e.g. 0x02). None = first OUT endpoint.

    """
    if not IN_PYODIDE:
      raise RuntimeError("WebUSB is only available in Pyodide/browser environment")

    self._id_vendor = id_vendor
    self._id_product = id_product
    self._device_address = device_address
    self._serial_number = serial_number
    self.human_readable_device_name = human_readable_device_name

    self.packet_read_timeout = packet_read_timeout
    self.read_timeout = read_timeout
    self.write_timeout = write_timeout
    self.configuration_callback = configuration_callback
    self.max_workers = max_workers
    self.read_endpoint_address = read_endpoint_address
    self.write_endpoint_address = write_endpoint_address

    self.dev: Any | None = None
    self._interface_number: int = 0
    self._endpoint_in: int = 1  # Default IN endpoint
    self._endpoint_out: int = 1  # Default OUT endpoint
    self._packet_size_in: int = 64
    self._pending_in: dict[int, asyncio.Future] = {}
    self._in_buffer: dict[int, bytearray] = {}

    self._unique_id = f"[{hex(id_vendor)}:{hex(id_product)}]"

  def _matches(self, d: Any) -> bool:
    if d.vendorId != self._id_vendor or d.productId != self._id_product:
      return False
    if self._serial_number is not None and getattr(d, "serialNumber", None) != self._serial_number:
      return False
    return True

  async def setup(self, empty_buffer=True):
    """Initialize the WebUSB connection.

    This will trigger a browser dialog for the user to select a USB device.

    Args:
        empty_buffer: Drain any stale IN data after opening, as pylabrobot does.

    """
    if self.dev is not None:
      logger.warning("USB device already connected. Closing previous connection.")
      await self.stop()
    if self.configuration_callback is not None:
      logger.warning(
        "%s: configuration_callback expects a pyusb Device and cannot run in the "
        "browser; selecting configuration 1 instead.",
        self.human_readable_device_name,
      )
    if not hasattr(navigator, "usb"):
      raise RuntimeError(
        "WebUSB is not supported in this browser. Please use Chrome, Edge, or Opera."
      )

    # Request device — try getDevices() first (works without gesture for
    # already-authorized devices), then delegate to main thread via UI dialog.
    filters = [{"vendorId": self._id_vendor, "productId": self._id_product}]

    try:
      devices = await navigator.usb.getDevices()
      for d in devices:
        if self._matches(d):
          self.dev = d
          break
    except Exception:
      pass  # getDevices not supported or failed

    if self.dev is None:
      # Not authorized yet. requestDevice() does not exist in the kernel's Web
      # Worker, so the page shows the picker from a click (shell/device/connect.js).
      try:
        import web_bridge
      except ImportError:
        web_bridge = None
      if web_bridge is None:
        self.dev = await navigator.usb.requestDevice(to_js({"filters": filters}))
      else:
        await web_bridge.request_device_authorization(
          "usb",
          filters,
          f"Connect {self.human_readable_device_name} "
          f"(USB {self._id_vendor:04x}:{self._id_product:04x})",
        )
        devices = await navigator.usb.getDevices()
        for d in devices:
          if self._matches(d):
            self.dev = d
            break

    if self.dev is None:
      raise RuntimeError(
        f"No matching USB device for '{self.human_readable_device_name}' "
        f"({self._id_vendor:04x}:{self._id_product:04x}"
        + (f", serial {self._serial_number}" if self._serial_number else "")
        + "). It is not among the devices this kernel can see "
        "(navigator.usb.getDevices()). Choose that device in the browser's picker; "
        "if you did, reload the page and run setup again."
      )

    # Open the device
    try:
      await self.dev.open()
    except Exception as e:
      raise RuntimeError(f"Failed to open USB device: {e}")

    # Select configuration (usually configuration 1)
    if self.dev.configuration is None:
      try:
        await self.dev.selectConfiguration(1)
      except Exception as e:
        raise RuntimeError(f"Failed to select configuration: {e}")

    # Claim interface
    try:
      await self.dev.claimInterface(self._interface_number)
    except Exception as e:
      raise RuntimeError(f"Failed to claim interface: {e}")

    # Find endpoints
    try:
      config = self.dev.configuration
      if config and config.interfaces:
        for iface in config.interfaces:
          if hasattr(iface, "alternate") and iface.alternate:
            for endpoint in iface.alternate.endpoints:
              # USB endpoint address = direction bit (0x80 = IN) | endpoint number.
              address = endpoint.endpointNumber | (0x80 if endpoint.direction == "in" else 0)
              if endpoint.direction == "in":
                if self.read_endpoint_address is None or address == self.read_endpoint_address:
                  self._endpoint_in = endpoint.endpointNumber
                  self._packet_size_in = getattr(endpoint, "packetSize", 64) or 64
              elif endpoint.direction == "out":
                if self.write_endpoint_address is None or address == self.write_endpoint_address:
                  self._endpoint_out = endpoint.endpointNumber
    except Exception as e:
      logger.warning(f"Could not enumerate endpoints, using defaults: {e}")
      if self.read_endpoint_address is not None:
        self._endpoint_in = self.read_endpoint_address & 0x0F
      if self.write_endpoint_address is not None:
        self._endpoint_out = self.write_endpoint_address & 0x0F

    # Update unique ID with serial if available
    try:
      if self.dev.serialNumber:
        self._unique_id = (
          f"[{hex(self._id_vendor)}:{hex(self._id_product)}][{self.dev.serialNumber}]"
        )
    except:
      pass

    logger.info(f"WebUSB device opened: {self._unique_id}")

    if empty_buffer:
      await self.drain()

  async def stop(self):
    """Close the USB connection."""
    if self.dev is None:
      raise ValueError("USB device was not connected.")

    try:
      await self.dev.releaseInterface(self._interface_number)
      await self.dev.close()
      self.dev = None
      for pending in self._pending_in.values():
        pending.cancel()
      self._pending_in.clear()
      self._in_buffer.clear()
      logger.info("WebUSB device closed")
    except Exception as e:
      logger.warning(f"Error closing WebUSB device: {e}")

  async def write(self, data: bytes, timeout: float | None = None) -> int:
    """Write data to the USB device.

    Returns:
        Number of bytes written.

    """
    if self.dev is None:
      raise RuntimeError("Device not connected. Call setup() first.")

    if timeout is None:
      timeout = self.write_timeout

    # Convert bytes to Uint8Array
    js_data = Uint8Array.new(list(data))

    try:
      result = await self.dev.transferOut(self._endpoint_out, js_data)
      # Debug logging
      print(
        f"[WebUSB] transferOut result: status={result.status}, bytesWritten={getattr(result, 'bytesWritten', 'N/A')}"
      )
      if result.status != "ok":
        raise RuntimeError(f"Write failed with status: {result.status}")
      logger.debug(f"{self._unique_id} write: {data}")
      # Return number of bytes written (bytesWritten from USBOutTransferResult)
      # If bytesWritten is 0 but status is ok, the data was sent - use data length
      bytes_written = getattr(result, "bytesWritten", len(data))
      if bytes_written == 0:
        print(f"[WebUSB] bytesWritten is 0, but status=ok, returning len(data)={len(data)}")
        bytes_written = len(data)
      print(f"[WebUSB] Returning {bytes_written}")
      return bytes_written
    except Exception as e:
      raise RuntimeError(f"Write failed: {e}")

  async def _transfer_in(self, endpoint_number: int, length: int) -> bytes | None:
    """One WebUSB IN transfer. None when the transfer completed without data."""
    try:
      result = await self.dev.transferIn(endpoint_number, length)
    except Exception as e:
      logger.debug(f"{self._unique_id} transferIn failed: {e}")
      await asyncio.sleep(0.01)
      return None
    if result.status == "ok" and result.data and result.data.byteLength:
      data_view = result.data
      return bytes([data_view.getUint8(i) for i in range(data_view.byteLength)])
    return None

  async def _read_packet(
    self,
    size: int | None = None,
    timeout: float | None = None,
    endpoint: int | None = None,
  ) -> bytes | None:
    """Read one packet, or None if nothing arrives within ``timeout`` seconds.

    WebUSB's transferIn has no timeout of its own, and abandoning one does not
    cancel it: the browser still completes it and hands it the next packet. So a
    timed-out transfer is kept pending (per endpoint) and the next read awaits it
    instead of issuing another -- otherwise every read timeout, and every drain(),
    would silently swallow the device's next packet.
    """
    if self.dev is None:
      raise RuntimeError(f"USB device for '{self.human_readable_device_name}' is not connected.")
    endpoint_number = (endpoint & 0x0F) if endpoint is not None else self._endpoint_in
    if timeout is None:
      timeout = self.packet_read_timeout

    buffered = self._in_buffer.get(endpoint_number)
    if buffered:
      take = len(buffered) if size is None else min(size, len(buffered))
      chunk = bytes(buffered[:take])
      del buffered[:take]
      return chunk

    pending = self._pending_in.get(endpoint_number)
    if pending is None:
      pending = asyncio.ensure_future(
        self._transfer_in(endpoint_number, max(size or 0, self._packet_size_in))
      )
      self._pending_in[endpoint_number] = pending
    try:
      data = await asyncio.wait_for(asyncio.shield(pending), timeout=timeout)
    except asyncio.TimeoutError:
      return None  # still pending; the next read on this endpoint picks it up
    self._pending_in.pop(endpoint_number, None)
    if data and size is not None and len(data) > size:
      self._in_buffer.setdefault(endpoint_number, bytearray()).extend(data[size:])
      data = data[:size]
    return data

  async def read(
    self,
    timeout: int | None = None,
    size: int | None = None,
    endpoint: int | None = None,
  ) -> bytes:
    """Read data from the USB device, the same way pylabrobot's USB.read does.

    Keeps reading while packets come back full-size (a full packet means more may
    follow), up to ``size`` bytes if given. Raises TimeoutError if nothing arrives
    within ``timeout`` seconds (default ``read_timeout``).

    Args:
        timeout: Overall timeout in seconds.
        size: Maximum number of bytes to read. None = everything available.
        endpoint: IN endpoint address to read from. None = the configured one.

    """
    if self.dev is None:
      raise RuntimeError("Device not connected. Call setup() first.")

    if timeout is None:
      timeout = self.read_timeout
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
      resp = bytearray()
      while True:
        remaining = size - len(resp) if size is not None else None
        packet_timeout = max(0.0, min(self.packet_read_timeout, deadline - time.monotonic()))
        packet = await self._read_packet(size=remaining, timeout=packet_timeout, endpoint=endpoint)
        if packet:
          resp += packet
        if not packet or len(packet) != self._packet_size_in:
          break
        if size is not None and len(resp) >= size:
          break
      if resp:
        logger.debug(f"{self._unique_id} read: {bytes(resp)}")
        return bytes(resp)

    raise TimeoutError(f"Timeout while reading from USB device '{self.human_readable_device_name}'.")

  async def drain(
    self,
    endpoint: int | None = None,
    timeout: float = 0.05,
    size: int = 512,
    max_duration: float = 1,
  ) -> None:
    """Discard buffered IN data until a read of ``timeout`` seconds comes back empty.

    Raises TimeoutError if the device is still sending after ``max_duration`` seconds.
    """
    if self.dev is None:
      raise RuntimeError(f"USB device for '{self.human_readable_device_name}' is not connected.")
    deadline = time.monotonic() + max_duration
    while time.monotonic() < deadline:
      packet = await self._read_packet(size=size, timeout=timeout, endpoint=endpoint)
      if packet is None:
        return
    raise TimeoutError(f"Timed out draining USB device '{self.human_readable_device_name}'.")

  def get_available_devices(self) -> list[Any]:
    """Get list of available devices (requires prior requestDevice)."""
    # In WebUSB, we can only access devices that were previously authorized
    logger.warning("get_available_devices not fully supported in WebUSB")
    return []

  def list_available_devices(self) -> None:
    """List available devices."""
    logger.warning("list_available_devices not fully supported in WebUSB")
    print("WebUSB requires user interaction to list devices.")

  def ctrl_transfer(
    self,
    bmRequestType: int,
    bRequest: int,
    wValue: int,
    wIndex: int,
    data_or_wLength: int,
    timeout: int | None = None,
  ) -> bytearray:
    """Perform a control transfer (synchronous API not supported)."""
    raise NotImplementedError(
      "Synchronous ctrl_transfer not supported in WebUSB. Use async version instead."
    )

  async def ctrl_transfer_async(
    self,
    bmRequestType: int,
    bRequest: int,
    wValue: int,
    wIndex: int,
    data_or_wLength: int,
    timeout: int | None = None,
  ) -> bytearray:
    """Perform an async control transfer."""
    if self.dev is None:
      raise RuntimeError("Device not connected. Call setup() first.")

    # Determine if this is an IN or OUT transfer
    is_in = (bmRequestType & 0x80) != 0

    setup = {
      "requestType": "vendor",  # Could be determined from bmRequestType
      "recipient": "device",  # Could be determined from bmRequestType
      "request": bRequest,
      "value": wValue,
      "index": wIndex,
    }

    try:
      if is_in:
        result = await self.dev.controlTransferIn(to_js(setup), data_or_wLength)
        if result.status == "ok" and result.data:
          data_view = result.data
          return bytearray([data_view.getUint8(i) for i in range(data_view.byteLength)])
        return bytearray()
      data = Uint8Array.new([0] * data_or_wLength)
      result = await self.dev.controlTransferOut(to_js(setup), data)
      return bytearray()
    except Exception as e:
      raise RuntimeError(f"Control transfer failed: {e}")

  def serialize(self) -> dict:
    """Serialize to the same keys as pylabrobot's USB.serialize()."""
    d = {
      "type": "WebUSB",
      "human_readable_device_name": self.human_readable_device_name,
      "id_vendor": self._id_vendor,
      "id_product": self._id_product,
      "device_address": self._device_address,
      "serial_number": self._serial_number,
      "packet_read_timeout": self.packet_read_timeout,
      "read_timeout": self.read_timeout,
      "write_timeout": self.write_timeout,
    }
    if self.read_endpoint_address is not None:
      d["read_endpoint_address"] = self.read_endpoint_address
    if self.write_endpoint_address is not None:
      d["write_endpoint_address"] = self.write_endpoint_address
    return d

  @classmethod
  def deserialize(cls, data: dict) -> "WebUSB":
    """Deserialize from dict (device must be re-requested)."""
    return cls(
      id_vendor=data["id_vendor"],
      id_product=data["id_product"],
      human_readable_device_name=data.get("human_readable_device_name", "WebUSB device"),
      device_address=data.get("device_address"),
      serial_number=data.get("serial_number"),
      packet_read_timeout=data.get("packet_read_timeout", 3),
      read_timeout=data.get("read_timeout", 30),
      write_timeout=data.get("write_timeout", 30),
      read_endpoint_address=data.get("read_endpoint_address"),
      write_endpoint_address=data.get("write_endpoint_address"),
    )

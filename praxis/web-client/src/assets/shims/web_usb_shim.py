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
  the browser's WebUSB API via Pyodide's JS bridge.
  """

  def __init__(
    self,
    id_vendor: int,
    id_product: int,
    device_address: int | None = None,
    serial_number: str | None = None,
    packet_read_timeout: int = 3,
    read_timeout: int = 30,
    write_timeout: int = 30,
  ):
    """Initialize WebUSB.

    Args:
        id_vendor: USB Vendor ID
        id_product: USB Product ID
        device_address: Device address (optional, for multiple devices)
        serial_number: Device serial number (optional)
        packet_read_timeout: Packet read timeout in seconds
        read_timeout: Overall read timeout in seconds
        write_timeout: Write timeout in seconds

    """
    if not IN_PYODIDE:
      raise RuntimeError("WebUSB is only available in Pyodide/browser environment")

    self._id_vendor = id_vendor
    self._id_product = id_product
    self._device_address = device_address
    self._serial_number = serial_number

    self.packet_read_timeout = packet_read_timeout
    self.read_timeout = read_timeout
    self.write_timeout = write_timeout

    self.dev: Any | None = None
    self._interface_number: int = 0
    self._endpoint_in: int = 1  # Default IN endpoint
    self._endpoint_out: int = 1  # Default OUT endpoint

    self._unique_id = f"[{hex(id_vendor)}:{hex(id_product)}]"

  async def setup(self):
    """Initialize the WebUSB connection.

    This will trigger a browser dialog for the user to select a USB device.
    """
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
        if d.vendorId == self._id_vendor and d.productId == self._id_product:
          self.dev = d
          break
    except Exception:
      pass  # getDevices not supported or failed

    if self.dev is None:
      # No pre-authorized device — delegate to Angular UI for user gesture
      try:
        import web_bridge
        result = await web_bridge.request_user_interaction('device_connect', {
          'api': 'usb',
          'filters': filters,
          'message': f'Connect USB device {hex(self._id_vendor)}:{hex(self._id_product)}'
        })
        if not result or not result.get('success'):
          error_msg = result.get('error', 'denied') if result else 'no response'
          raise RuntimeError(f"Device authorization failed: {error_msg}")
        # Re-query — the device is now authorized
        devices = await navigator.usb.getDevices()
        for d in devices:
          if d.vendorId == self._id_vendor and d.productId == self._id_product:
            self.dev = d
            break
      except ImportError:
        # web_bridge not available — fall back to direct request (will fail without gesture)
        self.dev = await navigator.usb.requestDevice(to_js({"filters": filters}))

    if self.dev is None:
      raise RuntimeError("No USB device selected")

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
              if endpoint.direction == "in":
                self._endpoint_in = endpoint.endpointNumber
              elif endpoint.direction == "out":
                self._endpoint_out = endpoint.endpointNumber
    except Exception as e:
      logger.warning(f"Could not enumerate endpoints, using defaults: {e}")

    # Update unique ID with serial if available
    try:
      if self.dev.serialNumber:
        self._unique_id = (
          f"[{hex(self._id_vendor)}:{hex(self._id_product)}][{self.dev.serialNumber}]"
        )
    except:
      pass

    logger.info(f"WebUSB device opened: {self._unique_id}")

  async def stop(self):
    """Close the USB connection."""
    if self.dev is None:
      raise ValueError("USB device was not connected.")

    try:
      await self.dev.releaseInterface(self._interface_number)
      await self.dev.close()
      self.dev = None
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

  async def read(self, timeout: int | None = None) -> bytes:
    """Read data from the USB device."""
    if self.dev is None:
      raise RuntimeError("Device not connected. Call setup() first.")

    if timeout is None:
      timeout = self.read_timeout

    result = bytearray()

    try:
      # Read with timeout - WebUSB uses transferIn
      read_task = asyncio.create_task(self._read_packet())
      try:
        chunk = await asyncio.wait_for(read_task, timeout=timeout)
        if chunk:
          result.extend(chunk)
      except asyncio.TimeoutError:
        if len(result) == 0:
          raise TimeoutError("Timeout while reading.")
    except TimeoutError:
      raise
    except Exception as e:
      raise RuntimeError(f"Read failed: {e}")

    if result:
      logger.debug(f"{self._unique_id} read: {bytes(result)}")

    return bytes(result)

  async def _read_packet(self, length: int = 64) -> bytes:
    """Read a packet from the USB device."""
    try:
      result = await self.dev.transferIn(self._endpoint_in, length)
      if result.status == "ok" and result.data:
        # Convert DataView to bytes
        data_view = result.data
        return bytes([data_view.getUint8(i) for i in range(data_view.byteLength)])
      return b""
    except Exception:
      return b""

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
    """Serialize the backend to a dictionary."""
    return {
      "id_vendor": self._id_vendor,
      "id_product": self._id_product,
      "device_address": self._device_address,
      "serial_number": self._serial_number,
      "packet_read_timeout": self.packet_read_timeout,
      "read_timeout": self.read_timeout,
      "write_timeout": self.write_timeout,
      "type": "WebUSB",
    }

  @classmethod
  def deserialize(cls, data: dict) -> "WebUSB":
    """Deserialize from dict (device must be re-requested)."""
    return cls(
      id_vendor=data["id_vendor"],
      id_product=data["id_product"],
      device_address=data.get("device_address"),
      serial_number=data.get("serial_number"),
      packet_read_timeout=data.get("packet_read_timeout", 3),
      read_timeout=data.get("read_timeout", 30),
      write_timeout=data.get("write_timeout", 30),
    )

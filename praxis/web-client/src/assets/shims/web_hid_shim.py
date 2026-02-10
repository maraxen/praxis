"""WebHID Shim for Pyodide/Browser Environment.

This module provides a WebHID-based implementation of pylabrobot's HID interface,
enabling HID device communication from the browser using the WebHID API.

This is specifically for backends like Inheco that use HID:
    from pylabrobot.io.hid import HID
    self.io = HID(vid=vid, pid=pid)

Usage in JupyterLite/Pyodide:
    # Auto-patched by pyodide_io_patch.py
    import pylabrobot.io.hid as hid
    hid.HID = WebHID
"""

import asyncio
import logging
from typing import Any

# Import Pyodide's JavaScript bridge
try:
  from js import Uint8Array, navigator
  from pyodide.ffi import create_proxy, to_js

  IN_PYODIDE = True
except ImportError:
  IN_PYODIDE = False
  navigator = None

logger = logging.getLogger(__name__)


class WebHID:
  """WebHID-based HID implementation for browser environments.

  Implements the same interface as pylabrobot.io.hid.HID but uses
  the browser's WebHID API via Pyodide's JS bridge.

  Refined Flow:
  1. Checks navigator.hid.getDevices() for previously granted permissions.
  2. If not found, attempts requestDevice (requires user gesture).
  3. Uses asyncio.Queue to bridge WebHID's push-based input reports to PLR's pull-based read().
  """

  def __init__(
    self,
    vid: int = 0x03EB,
    pid: int = 0x2023,
    serial_number: str | None = None,
  ):
    """Initialize WebHID.

    Args:
        vid: Vendor ID (default matches Inheco/Atmel)
        pid: Product ID
        serial_number: Optional serial number

    """
    if not IN_PYODIDE:
      msg = "WebHID is only available in Pyodide/browser environment"
      raise RuntimeError(msg)

    self.vid = vid
    self.pid = pid
    self.serial_number = serial_number

    self.device: Any = None
    self._input_queue: asyncio.Queue = asyncio.Queue()
    self._report_handler_proxy = None
    self._disconnect_handler_proxy = None

    # Identify device string for logs
    self._unique_id = f"[{hex(vid)}:{hex(pid)}]"
    if serial_number:
      self._unique_id += f":{serial_number}"

  async def setup(self):
    """Initialize the HID connection.

    Strategy:
    1. Check `navigator.hid.getDevices()` for existing permissions (ideal).
    2. Fallback to `requestDevice()` if no matching device found (requires user gesture).
    """
    if not hasattr(navigator, "hid"):
      msg = "WebHID is not supported in this browser."
      raise RuntimeError(msg)

    logger.info(f"Seting up WebHID for {self._unique_id}")

    target_device = None

    # 1. Try to find an already authorized device
    try:
      existing_devices = await navigator.hid.getDevices()
      # Iterate through JS array
      for i in range(existing_devices.length):
        d = existing_devices[i]
        if d.vendorId == self.vid and d.productId == self.pid:
          # If serial is required, check it
          if self.serial_number and getattr(d, "serialNumber", "") != self.serial_number:
            continue

          target_device = d
          logger.info(f"Found previously authorized HID device: {d.productName}")
          break
    except Exception as e:
      logger.warning(f"Failed to check existing devices: {e}")

    # 2. If not found, delegate to Angular UI for user gesture
    if not target_device:
      logger.info("Requesting new HID device via UI dialog (User Interaction Required)...")
      filters = [{"vendorId": self.vid, "productId": self.pid}]
      try:
        import web_bridge
        result = await web_bridge.request_user_interaction('device_connect', {
          'api': 'hid',
          'filters': filters,
          'message': f'Connect HID device {self._unique_id}'
        })
        if not result or not result.get('success'):
          error_msg = result.get('error', 'denied') if result else 'no response'
          raise RuntimeError(f"Device authorization failed: {error_msg}")
        # Re-query — the device is now authorized
        existing_devices = await navigator.hid.getDevices()
        for i in range(existing_devices.length):
          d = existing_devices[i]
          if d.vendorId == self.vid and d.productId == self.pid:
            if self.serial_number and getattr(d, "serialNumber", "") != self.serial_number:
              continue
            target_device = d
            break
      except ImportError:
        # web_bridge not available — fall back to direct request (will fail without gesture)
        devices = await navigator.hid.requestDevice(to_js({"filters": filters}))
        if devices.length > 0:
          target_device = devices[0]

    if not target_device:
      msg = "No HID device selected or found."
      raise RuntimeError(msg)

    self.device = target_device

    # 3. Open the device
    if not self.device.opened:
      try:
        await self.device.open()
        logger.info("WebHID device opened successfully.")
      except Exception as e:
        msg = f"Failed to open HID device: {e}"
        raise RuntimeError(msg) from e

    # 4. Setup Input Report Listener (Read Queue)
    # WebHID pushes data via 'inputreport' events. We push these to an asyncio Queue.
    def handle_input_report(event):
      try:
        # event.data is a DataView
        # event.reportId is the Report ID (int)
        data_view = event.data
        report_id = event.reportId

        # Convert DataView to bytes
        payload = bytes([data_view.getUint8(i) for i in range(data_view.byteLength)])

        # PLR Expectation:
        # If report_id > 0, it expects bytes to be [report_id, ...payload]
        # If report_id == 0, it just expects payload.
        # However, standard hidapi often includes the report_id as the first byte
        # if the device uses report IDs, even in read().
        # For Inheco (and general safety), if we have a non-zero report ID, prepend it.

        final_packet = bytes([report_id]) + payload if report_id != 0 else payload
        self._input_queue.put_nowait(final_packet)

      except Exception as e:
        logger.error(f"Error handling HID input report: {e}")

    self._report_handler_proxy = create_proxy(handle_input_report)
    self.device.addEventListener("inputreport", self._report_handler_proxy)

    # 5. Setup Disconnect Listener
    def handle_disconnect(event):
      logger.warning(f"WebHID device disconnected: {self._unique_id}")
      self.device = None

    self._disconnect_handler_proxy = create_proxy(handle_disconnect)
    self.device.addEventListener("disconnect", self._disconnect_handler_proxy)

  async def write(self, data: bytes, report_id: bytes = b"\x00"):
    """Write data to the HID device.

    Args:
        data: The payload to write.
        report_id: The report ID (first byte). PLR convention is to pass it separately,
                   but sometimes data includes it.

    """
    if not self.device or not self.device.opened:
      msg = "Device not connected. Call setup() first."
      raise RuntimeError(msg)

    # Parse Report ID
    # PLR passes report_id as bytes (default b'\x00').
    rid_int = 0
    if report_id and len(report_id) > 0:
      rid_int = report_id[0]

    # Convert data to Uint8Array
    # Note: sendReport takes (reportId, data). 'data' should not contain the reportId itself
    # unless it's part of the substantial payload, which for WebHID it usually isn't.
    js_data = Uint8Array.new(list(data))

    try:
      await self.device.sendReport(rid_int, js_data)
      # logging at debug level to avoid spam
      # logger.debug(f"Wrote HID report {rid_int}: {data.hex()}")
    except Exception as e:
      msg = f"WebHID Write Failed: {e}"
      raise RuntimeError(msg) from e

  async def read(self, size: int, timeout: int) -> bytes:
    """Read data from the device.

    Args:
        size: Number of bytes to read (ignored in WebHID event model,
              we return whatever packet comes next).
        timeout: Timeout in seconds (PLR uses int/float usually, assuming seconds).

    """
    if not self.device or not self.device.opened:
      msg = "Device not connected. Call setup() first."
      raise RuntimeError(msg)

    try:
      # Wait for the next packet from the queue
      return await asyncio.wait_for(self._input_queue.get(), timeout=timeout)
    except asyncio.TimeoutError as e:
      # PLR expects explicit timeout behavior (sometimes return empty, sometimes raise)
      # Looking at PLR's code, it often catches timeouts or returns empty bytes depending on impl.
      # But 'hidapi' usually blocks until timeout.
      # We'll propagate TimeoutError as it's cleaner, or return empty bytes if that's what PLR prefers.
      # PLR HID.read implementation signature returns bytes.
      # Inheco driver catches timeout?
      # Re-checking PLR hid.py: It casts return to bytes.
      # Let's raise TimeoutError to be safe, caller handles it.
      msg = "WebHID read timeout"
      raise TimeoutError(msg) from e

  async def stop(self):
    """Close the HID connection."""
    if self.device:
      if self._report_handler_proxy:
        self.device.removeEventListener("inputreport", self._report_handler_proxy)
        self._report_handler_proxy.destroy()
        self._report_handler_proxy = None

      if self._disconnect_handler_proxy:
        self.device.removeEventListener("disconnect", self._disconnect_handler_proxy)
        self._disconnect_handler_proxy.destroy()
        self._disconnect_handler_proxy = None

      if self.device.opened:
        await self.device.close()

      self.device = None
      logger.info(f"Closed WebHID device {self._unique_id}")

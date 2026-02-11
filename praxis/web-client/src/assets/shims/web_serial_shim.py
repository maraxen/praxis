"""WebSerial Shim for Pyodide/Browser Environment

This module provides a WebSerial-based implementation of pylabrobot's Serial interface,
enabling hardware communication from the browser using the WebSerial API.

Usage in JupyterLite:
    from web_serial_shim import WebSerial

    # Request a serial port (user must approve in browser dialog)
    serial = WebSerial(baudrate=9600)
    await serial.setup()

    # Use like regular Serial
    await serial.write(b"command")
    response = await serial.read(100)
"""

import asyncio
import logging
from typing import Any

# Import Pyodide's JavaScript bridge
try:
  from js import Object, Uint8Array, navigator, window
  from pyodide.ffi import create_proxy, to_js

  IN_PYODIDE = True
except ImportError:
  IN_PYODIDE = False
  navigator = None

logger = logging.getLogger(__name__)


# =============================================================================
# SerialProxy - Main Thread Delegation (Phase B)
# =============================================================================


class SerialProxy:
  """Serial proxy that delegates I/O to the main thread via BroadcastChannel.

  This class provides the same interface as WebSerial but sends all operations
  to the Angular main thread where the actual USB I/O occurs. This improves
  performance and simplifies debugging.

  The main thread SerialManager service handles the actual device communication
  using the FtdiSerial driver (or other drivers via DriverRegistry).
  """

  # Class-level pending requests and channel
  _channel = None
  _pending: dict = {}
  _request_counter = 0
  _initialized = False

  def __init__(
    self,
    port: Any | None = None,
    vid: int | None = None,
    pid: int | None = None,
    baudrate: int = 9600,
    bytesize: int = 8,
    parity: str = "N",
    stopbits: int = 1,
    write_timeout: float = 1,
    timeout: float = 5,
    rtscts: bool = False,
    dsrdtr: bool = False,
  ):
    """Initialize SerialProxy with same interface as WebSerial."""
    if not IN_PYODIDE:
      raise RuntimeError("SerialProxy is only available in Pyodide/browser environment")

    self._port = port
    self._vid = vid
    self._pid = pid
    self.baudrate = baudrate
    self.bytesize = bytesize
    self.parity = parity
    self.stopbits = stopbits
    self.write_timeout = write_timeout
    self.timeout = timeout
    self.rtscts = rtscts
    self.dsrdtr = dsrdtr

    self._device_id: str | None = None
    self._port_name = "SerialProxy"
    self._is_open = False

    self.parity_map = {"N": "none", "E": "even", "O": "odd"}

  @classmethod
  def _init_channel(cls):
    """Initialize the BroadcastChannel for main thread communication."""
    if cls._initialized:
      return

    import js

    try:
      cls._channel = js.BroadcastChannel.new("praxis_serial")

      def on_message(event):
        try:
          data = event.data
          if hasattr(data, "to_py"):
            data = data.to_py()

          if isinstance(data, dict) and data.get("type") == "serial:response":
            request_id = data.get("requestId")
            if request_id in cls._pending:
              future = cls._pending.pop(request_id)
              if not future.done():
                future.set_result(data)
        except Exception as e:
          logger.error(f"SerialProxy message handler error: {e}")

      cls._channel.onmessage = create_proxy(on_message)
      cls._initialized = True
      logger.info("SerialProxy: BroadcastChannel initialized")
    except Exception as e:
      logger.error(f"SerialProxy: Failed to initialize channel: {e}")
      raise

  async def _send_request(self, request_type: str, **kwargs) -> dict:
    """Send a request to the main thread and wait for response."""
    self._init_channel()

    if self._channel is None:
      raise RuntimeError("SerialProxy channel not initialized")

    SerialProxy._request_counter += 1
    request_id = f"py-{SerialProxy._request_counter}"

    request = {
      "type": request_type,
      "requestId": request_id,
      "deviceId": self._device_id,
      **kwargs,
    }

    # Create future for response
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    SerialProxy._pending[request_id] = future

    # Send request
    self._channel.postMessage(to_js(request))
    logger.debug(f"SerialProxy: Sent {request_type} (id={request_id})")

    # Wait for response with timeout
    try:
      response = await asyncio.wait_for(future, timeout=self.timeout)
      if not response.get("success"):
        raise RuntimeError(response.get("error", "Unknown error"))
      return response
    except asyncio.TimeoutError:
      SerialProxy._pending.pop(request_id, None)
      raise RuntimeError(f"SerialProxy: Request {request_type} timed out")

  @property
  def port(self) -> str:
    """Return port identifier."""
    return self._port_name

  async def setup(self):
    """Initialize the serial connection via main thread.

    Sends an open request to the main thread SerialManager which will
    find the device and connect using the appropriate driver.
    """
    # Try to find FTDI device for VID/PID
    vid = self._vid
    pid = self._pid

    if vid is None or pid is None:
      # Auto-detect FTDI devices
      if hasattr(navigator, "usb"):
        try:
          usb_devices = await navigator.usb.getDevices()
          for device in usb_devices:
            if device.vendorId == 0x0403:  # FTDI
              vid = device.vendorId
              pid = device.productId
              logger.info(f"SerialProxy: Auto-detected FTDI device {hex(vid)}:{hex(pid)}")
              break
        except Exception as e:
          logger.warning(f"SerialProxy: USB device enumeration failed: {e}")

    if vid is None or pid is None:
      raise RuntimeError("No device VID/PID specified and auto-detection failed")

    self._device_id = f"usb-{vid:x}-{pid:x}"

    try:
      await self._send_request(
        "serial:open",
        vendorId=vid,
        productId=pid,
        options={
          "baudRate": self.baudrate,
          "dataBits": self.bytesize,
          "stopBits": self.stopbits,
          "parity": self.parity_map.get(self.parity, "none"),
        },
      )
      self._is_open = True
      self._port_name = f"SerialProxy[{self._device_id}]"
      logger.info(f"SerialProxy: Connected to {self._device_id}")
    except Exception as e:
      logger.error(f"SerialProxy: Connection failed: {e}")
      raise

  async def stop(self):
    """Close the serial connection."""
    if not self._is_open:
      return

    try:
      await self._send_request("serial:close")
    except Exception as e:
      logger.warning(f"SerialProxy: Error closing: {e}")
    finally:
      self._is_open = False
      logger.info("SerialProxy: Closed")

  async def write(self, data: bytes) -> int:
    """Write data to the serial port via main thread."""
    if not self._is_open:
      raise RuntimeError("Port not open. Call setup() first.")

    await self._send_request("serial:write", data=list(data))
    logger.debug(f"SerialProxy: Wrote {len(data)} bytes")
    return len(data)

  async def read(self, num_bytes: int = 1) -> bytes:
    """Read data from the serial port via main thread."""
    if not self._is_open:
      raise RuntimeError("Port not open. Call setup() first.")

    response = await self._send_request("serial:read", length=num_bytes)
    data = bytes(response.get("data", []))
    if data:
      logger.debug(f"SerialProxy: Read {len(data)} bytes")
    return data

  async def readline(self) -> bytes:
    """Read a line from the serial port."""
    result = bytearray()
    while True:
      try:
        chunk = await asyncio.wait_for(self.read(64), timeout=self.timeout)
        if not chunk:
          break
        result.extend(chunk)
        if b"\n" in chunk:
          break
      except asyncio.TimeoutError:
        break
    return bytes(result)

  async def reset_input_buffer(self):
    """Clear the input buffer (no-op for proxy)."""

  async def reset_output_buffer(self):
    """Clear the output buffer (no-op for proxy)."""

  async def set_baudrate(self, baudrate):
    """Set the baud rate (requires reconnection)."""
    self.baudrate = baudrate
    logger.warning("SerialProxy: Baud rate change requires reconnection")

  async def set_line_property(self, data_bits, stop_bits, parity):
    """Set line properties (no-op for proxy)."""

  async def set_latency_timer(self, latency):
    """Set latency timer (no-op for proxy)."""

  @property
  def dtr(self) -> bool:
    return False

  @dtr.setter
  def dtr(self, value: bool):
    pass

  @property
  def rts(self) -> bool:
    return False

  @rts.setter
  def rts(self, value: bool):
    pass

  def serialize(self) -> dict:
    """Serialize configuration."""
    return {
      "port": self._port_name,
      "baudrate": self.baudrate,
      "bytesize": self.bytesize,
      "parity": self.parity,
      "stopbits": self.stopbits,
      "timeout": self.timeout,
      "type": "SerialProxy",
    }

  @classmethod
  def deserialize(cls, data: dict) -> "SerialProxy":
    """Deserialize from dict."""
    return cls(
      baudrate=data.get("baudrate", 9600),
      bytesize=data.get("bytesize", 8),
      parity=data.get("parity", "N"),
      stopbits=data.get("stopbits", 1),
      timeout=data.get("timeout", 5),
    )


# =============================================================================
# WebSerial - Legacy Direct I/O (Phase A fallback)
# =============================================================================


class WebSerial:
  """WebSerial-based Serial implementation for browser environments.

  Implements the same interface as pylabrobot.io.Serial but uses
  the browser's WebSerial API via Pyodide's JS bridge.
  """

  def __init__(
    self,
    port: Any | None = None,  # SerialPort object from requestPort
    vid: int | None = None,
    pid: int | None = None,
    baudrate: int = 9600,
    bytesize: int = 8,
    parity: str = "N",
    stopbits: int = 1,
    write_timeout: float = 1,
    timeout: float = 1,
    rtscts: bool = False,
    dsrdtr: bool = False,
  ):
    """Initialize WebSerial.

    Args:
        port: Optional SerialPort object. If None, will request in setup().
        vid: USB Vendor ID for filtering (optional)
        pid: USB Product ID for filtering (optional)
        baudrate: Baud rate (default 9600)
        bytesize: Data bits (5-8, default 8)
        parity: Parity ('N', 'E', 'O', default 'N')
        stopbits: Stop bits (1 or 2, default 1)
        write_timeout: Write timeout in seconds
        timeout: Read timeout in seconds
        rtscts: Enable RTS/CTS flow control
        dsrdtr: Enable DSR/DTR flow control

    """
    if not IN_PYODIDE:
      raise RuntimeError("WebSerial is only available in Pyodide/browser environment")

    self._port = port
    self._vid = vid
    self._pid = pid
    self.baudrate = baudrate
    self.bytesize = bytesize
    self.parity = parity
    self.stopbits = stopbits
    self.write_timeout = write_timeout
    self.timeout = timeout
    self.rtscts = rtscts
    self.dsrdtr = dsrdtr

    self._reader: Any | None = None
    self._writer: Any | None = None
    self._port_name: str = "WebSerial"

    self.parity_map = {"N": "none", "E": "even", "O": "odd"}
    self.stopbits_map = {1: 1, 2: 2}

  @property
  def port(self) -> str:
    """Return port identifier."""
    return self._port_name

  async def setup(self):
    """Initialize the WebSerial connection.

    Uses navigator.serial.getPorts() (and polyfill) to find an already authorized port.
    The frontend (React/Angular) is responsible for calling requestPort()
    via a user gesture before this code runs.
    """
    ports = []

    # 1. Native WebSerial
    if hasattr(navigator, "serial"):
      try:
        native_ports = await navigator.serial.getPorts()
        ports.extend(native_ports)
      except Exception as e:
        logger.warning(f"Native WebSerial getPorts failed: {e}")

    # 2. Polyfill (WebUSB)
    # Check if exposed on window by frontend
    # Note: Accessing window in Worker requires care
    import js

    window = getattr(js, "window", getattr(js, "self", None))

    if window:
      polyfill = getattr(window, "polyfillSerial", None)
      if not polyfill and hasattr(window, "parent"):
        polyfill = getattr(window.parent, "polyfillSerial", None)

      if polyfill:
        try:
          poly_ports = await polyfill.getPorts()
          ports.extend(poly_ports)
        except Exception as e:
          logger.warning(f"Polyfill port fetch failed: {e}")

    # 3. FTDI Driver (Direct WebUSB implementation)
    # Check for FTDI devices in authorized USB devices
    if hasattr(navigator, "usb"):
      try:
        usb_devices = await navigator.usb.getDevices()
        for device in usb_devices:
          if device.vendorId == 0x0403:  # FTDI Vendor ID
            logger.info(f"Found FTDI device: {device.productName}")
            await self._setup_ftdi(device)
            return
      except Exception as e:
        logger.warning(f"FTDI device check failed: {e}")

    # Fallback to standard WebSerial (Native or Polyfill)
    if not ports:
      # Try polyfill again with checking 'self' interaction if needed,
      # but standard WebSerial checked above.
      pass

    if not ports and self._port is None:
      raise RuntimeError(
        "No authorized devices found. "
        "Please use the 'Insert' button in the Inventory sidebar "
        "to authorize the device first."
      )

    if self._port is None:
      # Grab the most recently authorized port (usually the last one)
      self._port = ports[-1]

      # Open standard WebSerial port
      options = {
        "baudRate": self.baudrate,
        "dataBits": self.bytesize,
        "parity": self.parity_map.get(self.parity, "none"),
        "stopBits": self.stopbits_map.get(self.stopbits, 1),
        "flowControl": "hardware" if self.rtscts else "none",
      }

      try:
        await self._port.open(to_js(options))
      except Exception as e:
        if "The port is already open" in str(e):
          pass
        else:
          raise

      self._reader = self._port.readable.getReader()
      self._writer = self._port.writable.getWriter()
      self._is_ftdi = False
      self._port_name = "WebSerial"

  async def _setup_ftdi(self, device):
    """Setup FTDI device using WebUSB directly."""
    self._is_ftdi = True
    self._device = device
    await self._device.open()

    if self._device.configuration is None:
      await self._device.selectConfiguration(1)

    # Claim interface 0
    await self._device.claimInterface(0)

    # Reset
    await self._device.controlTransferOut(
      to_js(
        {
          "requestType": "vendor",
          "recipient": "device",
          "request": 0,  # RESET
          "value": 0,
          "index": 0,
        }
      )
    )

    # Set Baud Rate
    value, index = self._calculate_ftdi_baud(self.baudrate)
    await self._device.controlTransferOut(
      to_js(
        {
          "requestType": "vendor",
          "recipient": "device",
          "request": 3,  # SET_BAUD_RATE
          "value": value,
          "index": index,
        }
      )
    )

    # Set Data Characteristics
    # value: DataBits | Parity | StopBits
    # DataBits: 7 or 8
    # Parity: 0=None, 1=Odd, 2=Even
    # StopBits: 0=1, 2=2 (Note: FTDI mapping is weird, usually 0 for 1 stop bit, 2 for 2 stop bits)

    val = 0
    if self.bytesize == 8:
      val |= 8
    else:
      val |= 7

    if self.parity == "O":
      val |= 1 << 8
    elif self.parity == "E":
      val |= 2 << 8

    if self.stopbits == 2:
      val |= 2 << 11

    await self._device.controlTransferOut(
      to_js(
        {
          "requestType": "vendor",
          "recipient": "device",
          "request": 4,  # SET_DATA
          "value": val,
          "index": 0,
        }
      )
    )

    # Endpoints
    # Usually IN=1, OUT=2 or similar. Need to find them.
    self._ep_in = 1
    self._ep_out = 2

    # Simple endpoint scan
    config = self._device.configuration
    if config and config.interfaces:
      iface = config.interfaces[0]
      if hasattr(iface, "alternate") and iface.alternate:
        for ep in iface.alternate.endpoints:
          if ep.direction == "in":
            self._ep_in = ep.endpointNumber
          if ep.direction == "out":
            self._ep_out = ep.endpointNumber

    self._port_name = f"FTDI[{hex(device.vendorId)}:{hex(device.productId)}]"
    logger.info(f"FTDI Device initialized: {self._port_name}")

  def _calculate_ftdi_baud(self, baud):
    """Calculate FTDI baud rate divisors."""
    # Simplified lookup for common rates
    divisors = {
      9600: (0x4138, 0x0000),
      19200: (0x809C, 0x0000),
      38400: (0xC04E, 0x0000),
      57600: (0x0034, 0x0000),
      115200: (0x001A, 0x0000),
      125000: (0x0018, 0x0000),  # 3000000 / 24
      230400: (0x000D, 0x0000),
    }
    return divisors.get(baud, (0x4138, 0x0000))  # Default to 9600

    logger.info(f"WebSerial port opened: {self._port_name}")

  async def stop(self):
    """Close the serial port."""
    try:
      if self._reader:
        await self._reader.cancel()
        self._reader.releaseLock()
        self._reader = None

      if self._writer:
        await self._writer.close()
        self._writer = None

      if self._port:
        await self._port.close()
        self._port = None

      logger.info("WebSerial port closed")
    except Exception as e:
      logger.warning(f"Error closing WebSerial port: {e}")

  async def set_line_property(self, data_bits, stop_bits, parity):
    """No-op for WebSerial (handled in browser dialog/open options)."""
    logger.debug(f"[{self._port_name}] set_line_property ignored")

  async def set_latency_timer(self, latency):
    """No-op for WebSerial."""
    logger.debug(f"[{self._port_name}] set_latency_timer ignored")

  async def write(self, data: bytes) -> int:
    """Write data to the serial port."""
    # Convert bytes to Uint8Array
    js_data = Uint8Array.new(list(data))

    if getattr(self, "_is_ftdi", False):
      try:
        await self._device.transferOut(self._ep_out, js_data)
        return len(data)
      except Exception as e:
        raise RuntimeError(f"FTDI Write failed: {e}")

    if self._writer is None:
      raise RuntimeError("Port not open. Call setup() first.")

    try:
      await self._writer.write(js_data)
      logger.debug(f"[{self._port_name}] write: {data}")
      return len(data)
    except Exception as e:
      raise RuntimeError(f"Write failed: {e}")

  async def read(self, num_bytes: int = 1) -> bytes:
    """Read data from the serial port."""
    # Bypass check for FTDI
    if not getattr(self, "_is_ftdi", False) and self._reader is None:
      raise RuntimeError("Port not open. Call setup() first.")

    result = bytearray()

    try:
      # Read with timeout
      read_task = asyncio.create_task(self._read_chunk())
      try:
        chunk = await asyncio.wait_for(read_task, timeout=self.timeout)
        if chunk:
          result.extend(chunk[:num_bytes])
      except asyncio.TimeoutError:
        logger.debug(f"[{self._port_name}] read timeout")
    except Exception as e:
      raise RuntimeError(f"Read failed: {e}")

    if result:
      logger.debug(f"[{self._port_name}] read: {bytes(result)}")

    return bytes(result)

  async def _read_chunk(self) -> bytes:
    """Read a chunk of data from the reader."""
    if getattr(self, "_is_ftdi", False):
      try:
        result = await self._device.transferIn(self._ep_in, 64)
        if result.status == "ok" and result.data and result.data.byteLength > 2:
          dv = result.data
          # FTDI adds 2 modem status bytes at start
          return bytes([dv.getUint8(i) for i in range(2, dv.byteLength)])
        return b""
      except Exception:
        return b""

    result = await self._reader.read()
    if result.done:
      return b""
    # Convert Uint8Array to bytes
    return bytes(result.value.to_py())

  async def readline(self) -> bytes:
    """Read a line (until newline) from the serial port."""
    if self._reader is None:
      raise RuntimeError("Port not open. Call setup() first.")

    result = bytearray()

    try:
      while True:
        read_task = asyncio.create_task(self._read_chunk())
        try:
          chunk = await asyncio.wait_for(read_task, timeout=self.timeout)
          if not chunk:
            break
          result.extend(chunk)
          if b"\n" in chunk:
            break
        except asyncio.TimeoutError:
          break
    except Exception as e:
      raise RuntimeError(f"Readline failed: {e}")

    if result:
      logger.debug(f"[{self._port_name}] readline: {bytes(result)}")

    return bytes(result)

  async def reset_input_buffer(self):
    """Clear the input buffer (no-op for WebSerial)."""
    logger.debug(f"[{self._port_name}] reset_input_buffer (no-op)")

  async def reset_output_buffer(self):
    """Clear the output buffer (no-op for WebSerial)."""
    logger.debug(f"[{self._port_name}] reset_output_buffer (no-op)")

  async def set_baudrate(self, baudrate):
    """Set the baud rate."""
    self.baudrate = baudrate

    if getattr(self, "_is_ftdi", False):
      value, index = self._calculate_ftdi_baud(baudrate)
      await self._device.controlTransferOut(
        to_js(
          {
            "requestType": "vendor",
            "recipient": "device",
            "request": 3,  # SET_BAUD_RATE
            "value": value,
            "index": index,
          }
        )
      )
    else:
      logger.warning("set_baudrate not supported for standard WebSerial after open")

  @property
  def dtr(self) -> bool:
    """Get DTR state (not fully supported in WebSerial)."""
    return False

  @dtr.setter
  def dtr(self, value: bool):
    """Set DTR state."""
    logger.warning("DTR control not fully supported in WebSerial")

  @property
  def rts(self) -> bool:
    """Get RTS state (not fully supported in WebSerial)."""
    return False

  @rts.setter
  def rts(self, value: bool):
    """Set RTS state."""
    logger.warning("RTS control not fully supported in WebSerial")

  def serialize(self) -> dict:
    """Serialize configuration."""
    return {
      "port": self._port_name,
      "baudrate": self.baudrate,
      "bytesize": self.bytesize,
      "parity": self.parity,
      "stopbits": self.stopbits,
      "write_timeout": self.write_timeout,
      "timeout": self.timeout,
      "rtscts": self.rtscts,
      "dsrdtr": self.dsrdtr,
      "type": "WebSerial",
    }

  @classmethod
  def deserialize(cls, data: dict) -> "WebSerial":
    """Deserialize from dict (port must be re-requested)."""
    return cls(
      baudrate=data.get("baudrate", 9600),
      bytesize=data.get("bytesize", 8),
      parity=data.get("parity", "N"),
      stopbits=data.get("stopbits", 1),
      write_timeout=data.get("write_timeout", 1),
      timeout=data.get("timeout", 1),
      rtscts=data.get("rtscts", False),
      dsrdtr=data.get("dsrdtr", False),
    )

"""Hardware discovery service for detecting available lab equipment.

This service provides methods to discover hardware connected to the system,
including serial devices, network devices, and available simulators.

Supports:
- Serial/USB devices via pyserial
- Network devices via mDNS/Zeroconf (Opentrons, Tecan, Hamilton, etc.)
- PyLabRobot simulators
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class NetworkSignature(TypedDict):
  """Type definition for network device signatures."""

  manufacturer: str
  model_parser: Callable[[str], str]
  plr_backend: str | None


class ConnectionType(str, Enum):
  """Type of hardware connection."""

  SERIAL = "serial"
  USB = "usb"
  NETWORK = "network"
  SIMULATOR = "simulator"


class DeviceStatus(str, Enum):
  """Status of a discovered device."""

  AVAILABLE = "available"
  BUSY = "busy"
  ERROR = "error"
  UNKNOWN = "unknown"


@dataclass
class DiscoveredDevice:
  """Represents a discovered hardware device."""

  id: str
  name: str
  connection_type: ConnectionType
  status: DeviceStatus
  port: str | None = None
  ip_address: str | None = None
  manufacturer: str | None = None
  model: str | None = None
  serial_number: str | None = None
  plr_backend: str | None = None  # Suggested PyLabRobot backend class
  properties: dict[str, Any] | None = None


class HardwareDiscoveryService:
  """Service for discovering available hardware devices."""

  # Known USB VID/PID pairs for lab equipment
  KNOWN_DEVICES = {
    # Hamilton devices
    (0x08BB, 0x0106): {
      "manufacturer": "Hamilton",
      "model": "STAR",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.hamilton.STAR",
    },
    (0x08BB, 0x0107): {
      "manufacturer": "Hamilton",
      "model": "Starlet",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.hamilton.Starlet",
    },
    # Opentrons devices
    (0x04D8, 0xE11A): {
      "manufacturer": "Opentrons",
      "model": "OT-2",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.opentrons.OT2",
    },
    # Add more known devices here
  }

  # Known network device signatures for mDNS discovery
  # Keyed by mDNS service type
  NETWORK_SERVICE_TYPES = [
    "_opentrons._tcp.local.",  # Opentrons OT-2/Flex
    "_http._tcp.local.",  # Generic HTTP devices (many lab equipment)
    "_ipp._tcp.local.",  # Label printers
    "_pdl-datastream._tcp.local.",  # Some industrial printers
  ]

  # Device signatures for identifying equipment by name patterns
  NETWORK_SIGNATURES: dict[str, NetworkSignature] = {
    "opentrons": {
      "manufacturer": "Opentrons",
      "model_parser": lambda name: "Flex" if "flex" in name.lower() else "OT-2",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.opentrons_backend.OpentronsBackend",
    },
    "hamilton": {
      "manufacturer": "Hamilton",
      "model_parser": lambda name: "STAR" if "star" in name.lower() else "Starlet",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.hamilton.STAR",
    },
    "tecan": {
      "manufacturer": "Tecan",
      "model_parser": lambda name: "Freedom EVO" if "evo" in name.lower() else "Fluent",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.tecan.Tecan",
    },
    "beckman": {
      "manufacturer": "Beckman Coulter",
      "model_parser": lambda name: "Biomek",
      "plr_backend": "pylabrobot.legacy.liquid_handling.backends.beckman.Biomek",
    },
    "agilent": {
      "manufacturer": "Agilent",
      "model_parser": lambda name: "Bravo",
      "plr_backend": None,  # Not yet supported in PLR
    },
  }

  def __init__(self) -> None:
    """Initialize the hardware discovery service."""
    self._cached_devices: list[DiscoveredDevice] = []

  async def discover_serial_ports(self) -> list[DiscoveredDevice]:
    """Discover devices connected via serial/USB ports.

    Returns:
        List of discovered serial devices.

    """
    devices: list[DiscoveredDevice] = []

    try:
      # Try to import serial.tools.list_ports
      from serial.tools import list_ports

      ports = list_ports.comports()
      for port in ports:
        device_info = self._identify_device(port.vid, port.pid)

        device = DiscoveredDevice(
          id=f"serial-{port.device}",
          name=port.description or port.device,
          connection_type=ConnectionType.SERIAL,
          status=DeviceStatus.AVAILABLE,
          port=port.device,
          manufacturer=device_info.get("manufacturer") or port.manufacturer,
          model=device_info.get("model"),
          serial_number=port.serial_number,
          plr_backend=device_info.get("plr_backend"),
          properties={
            "vid": port.vid,
            "pid": port.pid,
            "hwid": port.hwid,
          },
        )
        devices.append(device)
        logger.debug("Discovered serial device: %s on %s", device.name, port.device)

    except ImportError:
      logger.warning("pyserial not installed. Serial port discovery unavailable.")
    except Exception as e:
      logger.exception("Error discovering serial ports: %s", e)

    return devices

  async def discover_simulators(self) -> list[DiscoveredDevice]:
    """Discover available PLR simulator backends.

    Returns:
        List of available simulators.

    """
    return [
      DiscoveredDevice(
        id="sim-liquid-handler",
        name="Simulated Liquid Handler",
        connection_type=ConnectionType.SIMULATOR,
        status=DeviceStatus.AVAILABLE,
        manufacturer="PyLabRobot",
        model="SimulatedLiquidHandler",
        plr_backend="pylabrobot.legacy.liquid_handling.backends.simulation.SimulatorBackend",
        properties={"simulated": True, "visualizer": True},
      ),
      DiscoveredDevice(
        id="sim-plate-reader",
        name="Simulated Plate Reader",
        connection_type=ConnectionType.SIMULATOR,
        status=DeviceStatus.AVAILABLE,
        manufacturer="PyLabRobot",
        model="SimulatedPlateReader",
        plr_backend="pylabrobot.legacy.plate_reading.backends.simulation.SimulatedPlateReader",
        properties={"simulated": True},
      ),
      DiscoveredDevice(
        id="sim-heater-shaker",
        name="Simulated Heater Shaker",
        connection_type=ConnectionType.SIMULATOR,
        status=DeviceStatus.AVAILABLE,
        manufacturer="PyLabRobot",
        model="SimulatedHeaterShaker",
        plr_backend="pylabrobot.legacy.heating_shaking.backends.simulation.SimulatedHeaterShaker",
        properties={"simulated": True},
      ),
    ]

  async def discover_network_devices(
    self,
    scan_range: str | None = None,
    timeout: float = 3.0,
  ) -> list[DiscoveredDevice]:
    """Discover devices on the network via mDNS/Zeroconf.

    Scans for lab equipment advertising mDNS services. Recognizes
    Opentrons, Hamilton, Tecan, Beckman, and other devices.

    Args:
        scan_range: Optional IP range (not used, mDNS is broadcast-based).
        timeout: Timeout for discovery in seconds.

    Returns:
        List of discovered network devices.

    """
    devices: list[DiscoveredDevice] = []

    try:
      from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
      logger.warning(
        "zeroconf not installed. Network discovery unavailable. "
        "Install with: pip install zeroconf"
      )
      return devices

    class LabDeviceListener(ServiceListener):
      """Listener for mDNS service discovery."""

      def __init__(self) -> None:
        self.discovered: list[tuple[str, str, dict[str, Any]]] = []

      def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        try:
          info = zc.get_service_info(type_, name, timeout=1000)
          if info:
            self.discovered.append(
              (
                type_,
                name,
                {
                  "addresses": [str(addr) for addr in info.parsed_addresses()],
                  "port": info.port,
                  "server": info.server,
                  "properties": {
                    k.decode() if isinstance(k, bytes) else k: v.decode()
                    if isinstance(v, bytes)
                    else v
                    for k, v in (info.properties or {}).items()
                  },
                },
              )
            )
            logger.debug("mDNS discovered: %s (%s)", name, type_)
        except Exception as e:
          logger.debug("Error getting service info for %s: %s", name, e)

      def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed."""

      def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated."""

    try:
      zeroconf = Zeroconf()
      listener = LabDeviceListener()

      # Start browsers for all service types
      browsers = [ServiceBrowser(zeroconf, stype, listener) for stype in self.NETWORK_SERVICE_TYPES]

      # Wait for discovery
      await asyncio.sleep(timeout)

      # Process discovered devices
      for stype, name, info in listener.discovered:
        device = self._parse_network_device(stype, name, info)
        if device:
          devices.append(device)

      # Cleanup
      for browser in browsers:
        browser.cancel()
      zeroconf.close()

      logger.info("mDNS discovery found %d devices", len(devices))

    except Exception as e:
      logger.exception("Error during network discovery: %s", e)

    return devices

  def _parse_network_device(
    self,
    service_type: str,
    name: str,
    info: dict[str, Any],
  ) -> DiscoveredDevice | None:
    """Parse discovered mDNS service into a DiscoveredDevice.

    Args:
        service_type: The mDNS service type (e.g., "_opentrons._tcp.local.").
        name: The service name.
        info: Service info including addresses, port, properties.

    Returns:
        DiscoveredDevice if recognized, None otherwise.

    """
    # Get first IP address
    addresses = info.get("addresses", [])
    ip_address = addresses[0] if addresses else None
    port = info.get("port")
    properties = info.get("properties", {})
    server = info.get("server", "")

    # Extract clean name (remove service type suffix)
    clean_name = name.replace(service_type, "").strip(".")

    # Check if it's an Opentrons device (special service type)
    if "_opentrons._tcp" in service_type:
      sig = self.NETWORK_SIGNATURES["opentrons"]
      model = sig["model_parser"](clean_name)
      return DiscoveredDevice(
        id=f"network-opentrons-{ip_address}",
        name=f"Opentrons {model}",
        connection_type=ConnectionType.NETWORK,
        status=DeviceStatus.AVAILABLE,
        ip_address=ip_address,
        port=str(port) if port else None,
        manufacturer=sig["manufacturer"],
        model=model,
        plr_backend=sig["plr_backend"],
        properties={
          "service_type": service_type,
          "server": server,
          **properties,
        },
      )

    # Check for known manufacturers in name or properties
    name_lower = clean_name.lower()
    for key, sig in self.NETWORK_SIGNATURES.items():
      if key in name_lower or key in str(properties).lower():
        model = sig["model_parser"](clean_name)
        return DiscoveredDevice(
          id=f"network-{key}-{ip_address}",
          name=f"{sig['manufacturer']} {model}",
          connection_type=ConnectionType.NETWORK,
          status=DeviceStatus.AVAILABLE,
          ip_address=ip_address,
          port=str(port) if port else None,
          manufacturer=sig["manufacturer"],
          model=model,
          plr_backend=sig["plr_backend"],
          properties={
            "service_type": service_type,
            "server": server,
            **properties,
          },
        )

    # For unrecognized HTTP devices, still return them
    if "_http._tcp" in service_type or "_ipp._tcp" in service_type:
      return DiscoveredDevice(
        id=f"network-{clean_name}-{ip_address}",
        name=clean_name or f"Network Device ({ip_address})",
        connection_type=ConnectionType.NETWORK,
        status=DeviceStatus.UNKNOWN,
        ip_address=ip_address,
        port=str(port) if port else None,
        manufacturer=None,
        model=None,
        plr_backend=None,
        properties={
          "service_type": service_type,
          "server": server,
          **properties,
        },
      )

    return None

  async def discover_all(self) -> list[DiscoveredDevice]:
    """Discover all available hardware devices.

    Returns:
        Combined list of all discovered devices.

    """
    all_devices: list[DiscoveredDevice] = []

    # Discover serial devices
    serial_devices = await self.discover_serial_ports()
    all_devices.extend(serial_devices)

    # Discover simulators
    simulators = await self.discover_simulators()
    all_devices.extend(simulators)

    # Discover network devices
    network_devices = await self.discover_network_devices()
    all_devices.extend(network_devices)

    # Cache for quick access
    self._cached_devices = all_devices

    logger.info(
      "Discovered %d devices: %d serial, %d simulators, %d network",
      len(all_devices),
      len(serial_devices),
      len(simulators),
      len(network_devices),
    )

    return all_devices

  def _identify_device(self, vid: int | None, pid: int | None) -> dict[str, str]:
    """Identify a device by its USB VID/PID.

    Args:
        vid: USB Vendor ID.
        pid: USB Product ID.

    Returns:
        Device information dict if recognized, empty dict otherwise.

    """
    if vid is None or pid is None:
      return {}
    return self.KNOWN_DEVICES.get((vid, pid), {})

  def get_cached_devices(self) -> list[DiscoveredDevice]:
    """Get the most recently discovered devices.

    Returns:
        Cached list of discovered devices.

    """
    return self._cached_devices

"""Stub for pylibftdi — provides symbols without native FTDI hardware.

This package satisfies `import pylibftdi` and `from pylibftdi import ...`
in environments where the real C-extension-based pylibftdi cannot be
installed (Pyodide/WASM, CI without libftdi, headless test runners).

Exported symbols match the subset actually used by pylabrobot:
  - FtdiError         (pylabrobot/io/ftdi.py, biotek_synergyh1_backend.py)
  - LibraryMissingError (lib/pylabrobot/pylabrobot/io/ftdi.py)
  - Device            (pylabrobot/io/ftdi.py)
  - driver            (hamilton_hepa_fan_backend.py — mutates USB_VID_LIST / USB_PID_LIST)
"""


class FtdiError(Exception):
  """Drop-in replacement for pylibftdi.FtdiError."""


class LibraryMissingError(Exception):
  """Drop-in replacement for pylibftdi.LibraryMissingError."""


class Device:
  """Phantom Device — will never be instantiated in stub context.

  Accepts the same kwargs as the real Device so that `Device(lazy_open=True, ...)`
  does not crash at construction, but any attempt to *use* the device raises.
  """

  def __init__(self, **kwargs):
    self._kwargs = kwargs
    self.closed = True

  def open(self):
    raise RuntimeError(
      "pylibftdi Device.open() called, but only the stub package is installed. "
      "Install the real pylibftdi to use FTDI hardware."
    )

  def close(self):
    pass

  def read(self, num_bytes=1):
    raise RuntimeError("pylibftdi stub: cannot read without real hardware")

  def write(self, data):
    raise RuntimeError("pylibftdi stub: cannot write without real hardware")

  def readline(self):
    raise RuntimeError("pylibftdi stub: cannot readline without real hardware")


class _DriverStub:
  """Mimics pylibftdi.driver with mutable VID/PID lists.

  hamilton_hepa_fan_backend.py does:
      from pylibftdi import driver
      driver.USB_VID_LIST.append(0x0856)
      driver.USB_PID_LIST.append(0xAC11)

  This stub provides those lists so the module-level mutation succeeds.
  """

  USB_VID_LIST: list[int] = [0x0403]
  USB_PID_LIST: list[int] = [0x6001, 0x6010, 0x6014, 0x6015]


driver = _DriverStub()

__version__ = "0.0.0+stub"

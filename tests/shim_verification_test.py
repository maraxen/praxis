
# Add the shims directory to sys.path so we can import pyodide_io_patch
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath("praxis/web-client/src/assets/shims"))

class TestPyodideIOPatch(unittest.TestCase):
    def setUp(self):
        # Clean up sys.modules to ensure isolation
        self.original_modules = sys.modules.copy()

        # Simulates Pyodide environment
        sys.modules["pyodide"] = MagicMock()

        # Remove serial/usb/hid if they exist locally so we test the shim
        for mod in ["serial", "serial.tools", "serial.tools.list_ports", "usb", "usb.core", "hid"]:
            if mod in sys.modules:
                del sys.modules[mod]

    def tearDown(self):
        sys.modules = self.original_modules

    def test_serial_shim_injection(self):
        import pyodide_io_patch

        # Run the patch
        pyodide_io_patch.patch_pylabrobot_io()

        # 1. Verify 'serial' is injected
        self.assertIn("serial", sys.modules, "serial module was not injected into sys.modules")

        import serial

        # 2. Verify constants
        self.assertEqual(serial.EIGHTBITS, 8)
        self.assertEqual(serial.PARITY_NONE, "N")
        self.assertEqual(serial.STOPBITS_ONE, 1)

        # 3. Verify Serial class
        # It should be our generic WebSerial shim or a class that behaves like it
        self.assertTrue(hasattr(serial, "Serial"))
        self.assertTrue(hasattr(serial, "SerialException"))

    def test_serial_tools_injection(self):
        import pyodide_io_patch
        pyodide_io_patch.patch_pylabrobot_io()

        self.assertIn("serial.tools", sys.modules)
        self.assertIn("serial.tools.list_ports", sys.modules)

        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        self.assertEqual(ports, [], "comports() should return empty list to avoid errors")

    def test_usb_injection(self):
        import pyodide_io_patch
        pyodide_io_patch.patch_pylabrobot_io()

        self.assertIn("usb", sys.modules)
        self.assertIn("usb.core", sys.modules)

        import usb.core
        self.assertTrue(hasattr(usb.core, "find"))

    def test_hid_injection(self):
        import pyodide_io_patch
        pyodide_io_patch.patch_pylabrobot_io()

        self.assertIn("hid", sys.modules)
        import hid
        self.assertTrue(hasattr(hid, "device"))
        self.assertTrue(hasattr(hid, "enumerate"))

if __name__ == "__main__":
    unittest.main()

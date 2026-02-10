import { Injectable, signal } from '@angular/core';

interface PyodideInterface {
    runPythonAsync: (code: string) => Promise<unknown>;
    loadPackage: (packages: string | string[]) => Promise<void>;
    globals: { get: (name: string) => unknown };
    FS: {
        writeFile: (path: string, data: string | Uint8Array, options?: { encoding?: string }) => void;
        mkdir: (path: string) => void;
        readdir: (path: string) => string[];
    };
}

declare global {
    interface Window {
        loadPyodide?: (options?: { indexURL?: string }) => Promise<PyodideInterface>;
    }
}

/**
 * Dedicated Pyodide kernel for Direct Control.
 * 
 * This service manages a standalone Pyodide instance used by Direct Control
 * to execute Python commands on machines. It's separate from JupyterLite
 * to avoid iframe lifecycle issues and provide a more responsive experience.
 */
@Injectable({
    providedIn: 'root'
})
export class DirectControlKernelService {
    private pyodide: PyodideInterface | null = null;
    private bootPromise: Promise<void> | null = null;

    // Track instantiated machines by accession_id
    private instantiatedMachines = new Map<string, string>(); // accession_id -> varName

    // Signals for UI state
    isReady = signal(false);
    isBooting = signal(false);
    bootError = signal<string | null>(null);
    lastOutput = signal<string>('');

    /**
     * Initialize the Pyodide kernel if not already done.
     * This is idempotent - multiple calls will return the same boot promise.
     */
    async boot(): Promise<void> {
        if (this.pyodide) {
            return; // Already booted
        }

        if (this.bootPromise) {
            return this.bootPromise; // Boot in progress
        }

        this.isBooting.set(true);
        this.bootError.set(null);

        this.bootPromise = this.performBoot();

        try {
            await this.bootPromise;
        } finally {
            this.isBooting.set(false);
        }
    }

    private async performBoot(): Promise<void> {
        try {
            // Load Pyodide script if not already loaded
            if (!window.loadPyodide) {
                await this.loadPyodideScript();
            }

            console.log('[DirectControlKernel] Loading Pyodide...');
            this.pyodide = await window.loadPyodide!({
                indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/'
            });

            console.log('[DirectControlKernel] Installing pylabrobot...');
            await this.pyodide.loadPackage(['micropip']);

            // Install pylabrobot from local wheel (same as JupyterLite bootstrap)
            await this.pyodide.runPythonAsync(`
import micropip
# Install from local wheel to get all modules including backends
# Use relative path (no leading slash) for GitHub Pages compatibility
await micropip.install('assets/wheels/pylabrobot-0.1.6-py3-none-any.whl')
print("PyLabRobot installed from local wheel")
`);

            // Install pylibftdi stub wheel (provides real FtdiError, Device, driver types)
            // and mock remaining native dependencies not available in browser
            await this.pyodide.runPythonAsync(`
import micropip, sys
from unittest.mock import MagicMock

# Install pylibftdi stub — proper types so except FtdiError clauses work
await micropip.install('assets/wheels/pylibftdi-0.0.0-py3-none-any.whl', deps=False)
print("✓ pylibftdi stub installed from wheel")

# Mock other native dependencies that may cause issues
sys.modules["usb"] = MagicMock()
sys.modules["usb.core"] = MagicMock()
sys.modules["usb.util"] = MagicMock()
sys.modules["serial"] = MagicMock()
sys.modules["serial.tools"] = MagicMock()
sys.modules["serial.tools.list_ports"] = MagicMock()

print("Browser mocks installed")
`);

            // Load browser I/O shims (WebSerial, WebUSB, WebFTDI)
            // Use relative paths (no leading slash) for GitHub Pages compatibility
            const cacheBust = Date.now();
            console.log('[DirectControlKernel] Loading browser shims...');

            const shims = [
                { file: 'web_serial_shim.py', name: 'WebSerial' },
                { file: 'web_usb_shim.py', name: 'WebUSB' },
                { file: 'web_ftdi_shim.py', name: 'WebFTDI' },
                { file: 'web_hid_shim.py', name: 'WebHID' }
            ];

            for (const shim of shims) {
                try {
                    const response = await fetch(`assets/shims/${shim.file}?v=${cacheBust}`);
                    const code = await response.text();
                    this.pyodide.FS.writeFile(shim.file, code);
                    console.log(`✓ ${shim.name} shim loaded`);
                } catch (e) {
                    console.error(`! Failed to load ${shim.name} shim:`, e);
                }
            }

            // Inject shims into builtins
            await this.pyodide.runPythonAsync(`
import builtins
import sys

# Add shims to builtins if they were written to FS
_SHIM_MAP = {"WebSerial": "web_serial_shim.py", "WebUSB": "web_usb_shim.py", "WebFTDI": "web_ftdi_shim.py", "WebHID": "web_hid_shim.py"}
for shim_name, shim_file in _SHIM_MAP.items():
    try:
        with open(shim_file, 'r') as f:
            exec(f.read(), globals())
        setattr(builtins, shim_name, globals()[shim_name])
        print(f"✓ {shim_name} injected into builtins")
    except Exception as e:
        print(f"! Failed to inject {shim_name}: {e}")
`);

            // CRITICAL: Patch pylabrobot.io BEFORE importing any backends
            // CLARIOstarBackend uses FTDI, not USB - this was the root cause!
            await this.pyodide.runPythonAsync(`
# Patch pylabrobot.io to use browser shims (BEFORE importing backends!)
import pylabrobot.io.serial as _ser
import pylabrobot.io.usb as _usb
import pylabrobot.io.ftdi as _ftdi

# Patch Serial, USB, and FTDI
_ser.Serial = WebSerial
_usb.USB = WebUSB 
print("✓ pylabrobot.io.serial patched with WebSerial")
print("✓ pylabrobot.io.usb patched with WebUSB")

# CRITICAL: Patch FTDI - this is what CLARIOstarBackend actually uses!
_ftdi.FTDI = WebFTDI
_ftdi.HAS_PYLIBFTDI = True  # Prevent import error check
print("✓ pylabrobot.io.ftdi patched with WebFTDI")

# Patch HID for Inheco and similar HID-based devices
try:
    import pylabrobot.io.hid as _hid
    _hid.HID = WebHID
    print("✓ pylabrobot.io.hid patched with WebHID")
except Exception as e:
    print(f"! HID patch skipped: {e}")

# Verify the patches took effect
print(f"[DIAG] pylabrobot.io.usb.USB = {_usb.USB}")
print(f"[DIAG] pylabrobot.io.ftdi.FTDI = {_ftdi.FTDI}")
print(f"[DIAG] FTDI is WebFTDI? {_ftdi.FTDI is WebFTDI}")
`);

            // Now import pylabrobot (backends will use the patched FTDI/USB/Serial)
            // and preload web_bridge.py into the Pyodide filesystem
            console.log('[DirectControlKernel] Preloading web_bridge.py...');
            try {
                const bridgeResponse = await fetch(`assets/python/web_bridge.py?v=${cacheBust}`);
                const bridgeCode = await bridgeResponse.text();
                this.pyodide.FS.writeFile('web_bridge.py', bridgeCode);
                console.log('✓ web_bridge.py written to FS');
            } catch (e) {
                console.error('! Failed to fetch web_bridge.py:', e);
            }

            await this.pyodide.runPythonAsync(`
import sys, os, importlib
import pylabrobot
from pylabrobot.resources import *
print(f"PyLabRobot {pylabrobot.__version__} ready for Direct Control")

# Import web_bridge.py - FS.writeFile ensures it's in the default import path
try:
    importlib.invalidate_caches()
    import web_bridge
    print(f"✓ web_bridge.py imported successfully")
except Exception as e:
    print(f"! Failed to import web_bridge.py: {e}")
`);

            this.isReady.set(true);
            console.log('[DirectControlKernel] Ready!');

        } catch (error) {
            console.error('[DirectControlKernel] Boot failed:', error);
            this.bootError.set(error instanceof Error ? error.message : String(error));
            this.pyodide = null;
            this.bootPromise = null;
            throw error;
        }
    }

    private loadPyodideScript(): Promise<void> {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js';
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load Pyodide script'));
            document.head.appendChild(script);
        });
    }

    /**
     * Execute Python code and return the output.
     */
    async execute(code: string): Promise<string> {
        if (!this.pyodide) {
            await this.boot();
        }

        try {
            // Capture stdout
            await this.pyodide!.runPythonAsync(`
import sys
from io import StringIO
_stdout_capture = StringIO()
_old_stdout = sys.stdout
sys.stdout = _stdout_capture
`);

            // Execute the code
            const result = await this.pyodide!.runPythonAsync(code);

            // Get captured output
            const output = await this.pyodide!.runPythonAsync(`
sys.stdout = _old_stdout
_output = _stdout_capture.getvalue()
_stdout_capture.close()
_output
`) as string;

            const finalOutput = output + (result !== undefined && result !== null ? String(result) : '');
            this.lastOutput.set(finalOutput);
            return finalOutput;

        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            this.lastOutput.set(`Error: ${errorMsg}`);
            throw error;
        }
    }

    /**
     * Ensure a machine is instantiated in the kernel.
     * Returns the variable name for the machine.
     */
    async ensureMachineInstantiated(
        machineId: string,
        machineName: string,
        varName: string,
        backendFqn: string,
        category: string
    ): Promise<string> {
        if (this.instantiatedMachines.has(machineId)) {
            return this.instantiatedMachines.get(machineId)!;
        }

        if (!this.pyodide) {
            await this.boot();
        }

        console.log(`[DirectControlKernel] Instantiating ${machineName} as ${varName} (${category})...`);

        // Sanitize names for Python string literals
        const safeName = machineName.replace(/['"\\]/g, '_');
        const safeVar = varName.replace(/[^a-zA-Z0-9_]/g, '_');

        const configJson = JSON.stringify({
            backend_fqn: backendFqn || 'pylabrobot.liquid_handling.backends.simulation.SimulatorBackend',
            is_simulated: true
        }).replace(/\\/g, '\\\\').replace(/'/g, "\\'");

        const initCode = `
# Initialize: ${safeName}
from web_bridge import create_configured_backend, create_machine_frontend
import json

config = json.loads('${configJson}')
backend = create_configured_backend(config)
${safeVar} = create_machine_frontend("${category}", backend, name="${safeName}")
print(f"Created: ${safeVar} ({safeName})")
`;

        await this.execute(initCode);
        this.instantiatedMachines.set(machineId, safeVar);

        return safeVar;
    }

    /**
     * Execute a method on an instantiated machine.
     */
    async executeMethod(
        varName: string,
        methodName: string,
        args: Record<string, unknown>
    ): Promise<string> {
        const argList = Object.entries(args)
            .filter(([, val]) => val !== undefined && val !== null && val !== '')
            .map(([key, val]) => {
                const valStr = typeof val === 'string' ? `"${val}"` : val;
                return `${key}=${valStr}`;
            })
            .join(', ');

        const code = `await ${varName}.${methodName}(${argList})`;
        console.log(`[DirectControlKernel] Executing: ${code}`);

        return this.execute(code);
    }

    /**
     * Get the current kernel state for debugging.
     */
    getState() {
        return {
            isReady: this.isReady(),
            isBooting: this.isBooting(),
            instantiatedMachines: Array.from(this.instantiatedMachines.entries()),
            hasError: !!this.bootError()
        };
    }

    /**
     * Reset the kernel (for debugging/recovery).
     */
    reset(): void {
        this.pyodide = null;
        this.bootPromise = null;
        this.instantiatedMachines.clear();
        this.isReady.set(false);
        this.isBooting.set(false);
        this.bootError.set(null);
        this.lastOutput.set('');
        console.log('[DirectControlKernel] Reset');
    }
}

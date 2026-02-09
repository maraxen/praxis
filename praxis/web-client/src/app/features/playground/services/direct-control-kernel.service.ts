import { Injectable, signal } from '@angular/core';

interface PyodideInterface {
    runPythonAsync: (code: string) => Promise<unknown>;
    loadPackage: (packages: string | string[]) => Promise<void>;
    globals: { get: (name: string) => unknown };
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
            // Add cache-busting timestamp to ensure latest version is loaded
            // Use relative paths (no leading slash) for GitHub Pages compatibility
            const cacheBust = Date.now();
            console.log('[DirectControlKernel] Loading browser shims...');
            await this.pyodide.runPythonAsync(`
import pyodide.http
import builtins

# Load WebSerial shim
print("Loading WebSerial shim...")
try:
    _shim_code = await (await pyodide.http.pyfetch('assets/shims/web_serial_shim.py?v=${cacheBust}')).string()
    exec(_shim_code, globals())
    builtins.WebSerial = WebSerial
    print("✓ WebSerial shim loaded and added to builtins")
except Exception as e:
    print(f"! Failed to load WebSerial shim: {e}")

# Load WebUSB shim
print("Loading WebUSB shim...")
try:
    _shim_code = await (await pyodide.http.pyfetch('assets/shims/web_usb_shim.py?v=${cacheBust}')).string()
    exec(_shim_code, globals())
    builtins.WebUSB = WebUSB
    print("✓ WebUSB shim loaded and added to builtins")
except Exception as e:
    print(f"! Failed to load WebUSB shim: {e}")

# Load WebFTDI shim (CRITICAL for CLARIOstarBackend!)
print("Loading WebFTDI shim...")
try:
    _shim_code = await (await pyodide.http.pyfetch('assets/shims/web_ftdi_shim.py?v=${cacheBust}')).string()
    exec(_shim_code, globals())
    builtins.WebFTDI = WebFTDI
    print("✓ WebFTDI shim loaded and added to builtins")
except Exception as e:
    print(f"! Failed to load WebFTDI shim: {e}")
`);

            // CRITICAL: Patch pylabrobot.io BEFORE importing any backends
            // CLARIOstarBackend uses FTDI, not USB - this was the root cause!
            await this.pyodide.runPythonAsync(`
# Patch pylabrobot.io to use browser shims (BEFORE importing backends!)
import pylabrobot.io.serial as _ser
import pylabrobot.io.usb as _usb
import pylabrobot.io.ftdi as _ftdi

# Patch Serial and USB
_ser.Serial = WebSerial
_usb.USB = WebUSB 
print("✓ pylabrobot.io.serial patched with WebSerial")
print("✓ pylabrobot.io.usb patched with WebUSB")

# CRITICAL: Patch FTDI - this is what CLARIOstarBackend actually uses!
_ftdi.FTDI = WebFTDI
_ftdi.HAS_PYLIBFTDI = True  # Prevent import error check
print("✓ pylabrobot.io.ftdi patched with WebFTDI")
print("[DIAG] CLARIOstarBackend will now use WebFTDI for USB-to-Serial!")

# Verify the patches took effect
print(f"[DIAG] pylabrobot.io.usb.USB = {_usb.USB}")
print(f"[DIAG] pylabrobot.io.ftdi.FTDI = {_ftdi.FTDI}")
print(f"[DIAG] FTDI is WebFTDI? {_ftdi.FTDI is WebFTDI}")
`);

            // Now import pylabrobot (backends will use the patched FTDI/USB/Serial)
            await this.pyodide.runPythonAsync(`
import pylabrobot
from pylabrobot.resources import *
print(f"PyLabRobot {pylabrobot.__version__} ready for Direct Control")

# Verify what the plate_reading backend will use
from pylabrobot.plate_reading.clario_star_backend import CLARIOstarBackend
# Check what FTDI class it imports
import pylabrobot.io.ftdi as verify_ftdi
print(f"[DIAG] After backend import, pylabrobot.io.ftdi.FTDI = {verify_ftdi.FTDI}")
print(f"[DIAG] FTDI is WebFTDI? {verify_ftdi.FTDI is WebFTDI}")

# Check CLARIOstarBackend's __init__ to see what it uses
import inspect
try:
    src = inspect.getsource(CLARIOstarBackend.__init__)
    if 'FTDI' in src:
        print("[DIAG] CLARIOstarBackend uses FTDI in __init__ - CORRECT!")
    elif 'USB' in src or 'usb' in src:
        print("[DIAG] CLARIOstarBackend uses USB in __init__")
except:
    print("[DIAG] Could not inspect CLARIOstarBackend")
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

        console.log(`[DirectControlKernel] Instantiating ${machineName} as ${varName}...`);

        // Generate import code based on category
        const frontendMap: Record<string, { module: string; cls: string }> = {
            'PlateReader': { module: 'pylabrobot.plate_reading', cls: 'PlateReader' },
            'LiquidHandler': { module: 'pylabrobot.liquid_handling', cls: 'LiquidHandler' },
            'Shaker': { module: 'pylabrobot.shaking', cls: 'Shaker' },
            'HeaterShaker': { module: 'pylabrobot.heating_shaking', cls: 'HeaterShaker' },
            'Centrifuge': { module: 'pylabrobot.centrifuge', cls: 'Centrifuge' },
            'Incubator': { module: 'pylabrobot.incubator', cls: 'Incubator' },
        };

        const frontend = frontendMap[category] || { module: 'pylabrobot.liquid_handling', cls: 'LiquidHandler' };
        const backendClass = backendFqn.split('.').pop() || 'Backend';
        const backendModule = backendFqn.substring(0, backendFqn.lastIndexOf('.'));

        // Different machine types need different constructor arguments
        let frontendArgs: string;

        if (category === 'PlateReader') {
            // PlateReader requires size dimensions - use typical microplate reader dimensions
            frontendArgs = `name="${machineName}", size_x=400.0, size_y=400.0, size_z=200.0, backend=${backendClass}()`;
        } else if (category === 'LiquidHandler') {
            // LiquidHandler takes just name and backend
            frontendArgs = `name="${machineName}", backend=${backendClass}()`;
        } else {
            // Default: name and backend
            frontendArgs = `name="${machineName}", backend=${backendClass}()`;
        }

        const initCode = `
# Initialize: ${machineName}
from ${backendModule} import ${backendClass}
from ${frontend.module} import ${frontend.cls}

${varName} = ${frontend.cls}(${frontendArgs})
print("Created: ${varName} (${machineName})")

# DIAGNOSTIC: Check what USB type the backend is using
backend = ${varName}.backend
print(f"[DIAG-INST] Backend type: {type(backend)}")
print(f"[DIAG-INST] Backend __dict__:")
for k, v in backend.__dict__.items():
    print(f"  {k}: {type(v).__name__} = {repr(v)[:100]}")
`;

        await this.execute(initCode);
        this.instantiatedMachines.set(machineId, varName);

        return varName;
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

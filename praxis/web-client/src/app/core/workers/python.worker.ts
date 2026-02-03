/// <reference lib="webworker" />

import { loadPyodide, PyodideInterface } from 'pyodide';

// Define a typed worker scope
interface PythonWorkerGlobalScope extends WorkerGlobalScope {
  protocol_bytes: Uint8Array;
  machine_config: any;
  deck_setup_script: string;
  handlePythonOutput: (type: string, content: string) => void;
}
declare const self: PythonWorkerGlobalScope;

let pyodide: PyodideInterface;
let pyConsole: {
  push: (code: string) => any;
  complete: (code: string) => any;
};

interface PythonMessage {
  type: 'INIT' | 'INIT_WITH_SNAPSHOT' | 'DUMP_SNAPSHOT' | 'PUSH' | 'EXEC' | 'INSTALL' | 'COMPLETE' | 'SIGNATURES' | 'PLR_COMMAND' | 'RAW_IO' | 'RAW_IO_RESPONSE' | 'WELL_STATE_UPDATE' | 'FUNCTION_CALL_LOG' | 'EXECUTE_BLOB' | 'USER_INTERACTION' | 'USER_INTERACTION_RESPONSE' | 'INTERRUPT';
  id?: string;
  payload?: unknown;
}

// Payload Interfaces
interface PLRCommandPayload {
  command: string;
  data: any;
}

interface WellStateUpdatePayload {
  [resource_name: string]: {
    liquid_mask?: string;
    volumes?: number[];
    tip_mask?: string;
  };
}

interface FunctionCallLogPayload {
  call_id: string;
  run_id: string;
  sequence: number;
  method_name: string;
  args: any;
  state_before: any;
  state_after: any;
  status: string;
  start_time: number;
  end_time?: number;
  duration_ms?: number;
  error_message?: string;
}

interface UserInteractionPayload {
  id: string;
  interaction_type: string;
  payload: any;
}

const interruptBuffer = new Uint8Array(new SharedArrayBuffer(1));
let currentExecutionId: string | undefined;

addEventListener('message', async (event) => {
  let data = event.data;

  // If data is a string, it might be a JSON message from Python
  if (typeof data === 'string') {
    try {
      data = JSON.parse(data);
    } catch {
      // Not JSON, ignore or treat as raw
    }
  }

  const { type, id, payload } = data as PythonMessage;

  // Handle RAW_IO messages from Python (forward to Angular main thread)
  if (type === 'RAW_IO') {
    postMessage({ type: 'RAW_IO', id: currentExecutionId, payload });
    return;
  }

  // Handle RAW_IO_RESPONSE from Angular (route back to Python)
  if (type === 'RAW_IO_RESPONSE') {
    if (pyodide) {
      try {
        const bridge = pyodide.pyimport('web_bridge');
        const payload = data.payload as { request_id: string; data: any };
        bridge.handle_io_response(payload.request_id, payload.data);
      } catch (err) {
        console.error('Error routing IO response to Python:', err);
      }
    }
    return;
  }

  // Handle USER_INTERACTION_RESPONSE from Angular (route back to Python)
  if (type === 'USER_INTERACTION_RESPONSE') {
    if (pyodide) {
      try {
        const bridge = pyodide.pyimport('web_bridge');
        const payload = data.payload as { request_id: string; value: any };
        bridge.handle_interaction_response(payload.request_id, payload.value);
      } catch (err) {
        console.error('Error routing interaction response to Python:', err);
      }
    }
    return;
  }

  if (type === 'INTERRUPT') {
    interruptBuffer[0] = 2; // Trigger KeyboardInterrupt in Pyodide
    return;
  }

  try {
    switch (type) {
      case 'INIT':
        await initializePyodide(id);
        break;

      case 'INIT_WITH_SNAPSHOT':
        await initializeFromSnapshot(id, payload as { snapshot: ArrayBuffer });
        break;

      case 'DUMP_SNAPSHOT':
        await dumpSnapshot(id);
        break;

      case 'PUSH':
      case 'EXEC':
        // Both PUSH and EXEC now use the console's push method
        if (!pyodide || !pyConsole) throw new Error('Pyodide not initialized');
        currentExecutionId = id;
        try {
          const { code: runCode } = payload as { code: string };
          await executePush(id!, runCode);
        } finally {
          currentExecutionId = undefined;
        }
        break;

      case 'PLR_COMMAND':
        postMessage({ type: 'PLR_COMMAND', id: currentExecutionId, payload: payload as PLRCommandPayload });
        break;

      case 'WELL_STATE_UPDATE':
        postMessage({ type: 'WELL_STATE_UPDATE', id: currentExecutionId, payload: payload as WellStateUpdatePayload });
        break;

      case 'FUNCTION_CALL_LOG':
        postMessage({ type: 'FUNCTION_CALL_LOG', id: currentExecutionId, payload: payload as FunctionCallLogPayload });
        break;

      case 'USER_INTERACTION':
        postMessage({ type: 'USER_INTERACTION', id: currentExecutionId, payload: payload as UserInteractionPayload });
        break;

      case 'INSTALL':
        if (!pyodide) throw new Error('Pyodide not initialized');
        currentExecutionId = id;
        try {
          const micropip = pyodide.pyimport('micropip');
          const packages = (payload as { packages: string[] }).packages;
          await micropip.install(packages);
          postMessage({ type: 'INSTALL_COMPLETE', id });
        } finally {
          currentExecutionId = undefined;
        }
        break;

      case 'COMPLETE':
        if (!pyodide || !pyConsole) throw new Error('Pyodide not initialized');
        try {
          // Use Console.complete() - returns (completions: list[str], start: int)
          const { code: completeCode } = payload as { code: string };
          const resultProxy = pyConsole.complete(completeCode);
          const result = resultProxy.toJs();
          resultProxy.destroy();

          // result is [completions_list, start_index]
          const completions = result[0] || [];
          const matches = completions.map((name: string) => ({
            name,
            type: 'unknown',
            description: ''
          }));
          postMessage({ type: 'COMPLETE_RESULT', id, payload: { matches } });
        } catch (err: unknown) {
          console.error('Completion error:', err);
          postMessage({ type: 'COMPLETE_RESULT', id, payload: { matches: [] } });
        }
        break;

      case 'SIGNATURES':
        // PyodideConsole doesn't have built-in signature help
        // We can try to use Jedi if available, or return empty
        if (!pyodide) throw new Error('Pyodide not initialized');
        try {
          const bridge = pyodide.pyimport('web_bridge');
          const { code: sigCode } = payload as { code: string };
          const signaturesProxy = bridge.get_signatures(sigCode);
          const signatures = signaturesProxy.toJs();
          signaturesProxy.destroy();
          postMessage({ type: 'SIGNATURE_RESULT', id, payload: { signatures } });
        } catch (err: unknown) {
          // Signature help is optional, just return empty
          postMessage({ type: 'SIGNATURE_RESULT', id, payload: { signatures: [] } });
        }
        break;

      case 'EXECUTE_BLOB':
        if (!pyodide) throw new Error('Pyodide not initialized');
        currentExecutionId = id;
        try {
          const { blob, machine_config, deck_setup_script } = payload as { blob: ArrayBuffer, machine_config: any, deck_setup_script?: string };
          self.protocol_bytes = new Uint8Array(blob);
          self.machine_config = machine_config;
          self.deck_setup_script = deck_setup_script || '';

          await pyodide.runPythonAsync(`
import cloudpickle
import js
import inspect
import sys
from web_bridge import create_configured_backend, create_browser_deck

# Load function from bytes
protocol_bytes = bytes(js.protocol_bytes)
protocol_func = cloudpickle.loads(protocol_bytes)

# Inspect signature to inject arguments
sig = inspect.signature(protocol_func)
kwargs = {}

# Get config from JS
config_proxy = js.machine_config

if 'backend' in sig.parameters:
    # Pass the proxy directly, the python function handles conversion
    kwargs['backend'] = create_configured_backend(config_proxy)

# Setup Deck
deck = None
try:
    if js.deck_setup_script:
        # Run the serialized deck setup script
        print("[Browser] Running deck setup script...")
        setup_ns = {}
        exec(js.deck_setup_script, setup_ns)
        if 'deck' in setup_ns:
            deck = setup_ns['deck']
        else:
            print("Warning: 'deck' variable not found in setup script.", file=sys.stderr)
            deck = create_browser_deck()
    else:
        # Fallback to default empty deck
        deck = create_browser_deck()
except Exception as e:
    print(f"Error during deck setup: {e}", file=sys.stderr)
    deck = create_browser_deck()

if 'deck' in sig.parameters:
    if deck is not None:
        kwargs['deck'] = deck
    else:
        print("Warning: 'deck' argument requested but Deck could not be instantiated.", file=sys.stderr)

# Execute
async def run_wrapper():
    if inspect.iscoroutinefunction(protocol_func):
        await protocol_func(**kwargs)
    else:
        # Check if it returns a coroutine (e.g. if it was decorated)
        result = protocol_func(**kwargs)
        if inspect.isawaitable(result):
            await result

await run_wrapper()
          `);
        } finally {
          currentExecutionId = undefined;
          postMessage({ type: 'EXEC_COMPLETE', id, payload: null });
        }
        break;
    }
  } catch (error: unknown) {
    postMessage({
      type: 'ERROR',
      id,
      payload: (error as Error).message || String(error)
    });
  }
});

// Expose callbacks for Python to call
self.handlePythonOutput = (type: string, content: string) => {
  // Always log to console for debugging/testing visibility
  console.log(`[Python ${type}]: ${content}`);

  if (currentExecutionId) {
    postMessage({ type, id: currentExecutionId, payload: content });
  } else {
    // Output without an ID (e.g. background logs)
    // Already logged above
  }
};

async function initializePyodide(id?: string) {
  // Load Pyodide with core files from local assets, packages from CDN
  // Use relative path (no leading slash) to respect base href on GitHub Pages
  pyodide = await loadPyodide({
    indexURL: 'assets/pyodide/',
    lockFileURL: 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide-lock.json'
  });

  // Set the interrupt buffer for graceful interruption
  pyodide.setInterruptBuffer(interruptBuffer);

  // Install micropip for package management
  await pyodide.loadPackage('micropip');

  // Install basic dependencies including PLR and Jedi
  // Note: We use a try-catch for pylabrobot as it might have complex deps
  try {
    const micropip = pyodide.pyimport('micropip');
    await micropip.install(['jedi', 'pylabrobot', 'cloudpickle']);
    console.log('PyLabRobot and Jedi installed successfully');
  } catch (err) {
    console.error('Failed to install PyLabRobot/Jedi:', err);
  }

  // Load WebSerial, WebUSB, and WebFTDI Shims (must be before bridge if bridge depends on them)
  // CRITICAL: WebFTDI is required for CLARIOstarBackend and similar FTDI-based devices
  // OPTIMIZATION: Fetch all shims in parallel for faster init
  const shims = [
    { file: 'web_serial_shim.py', name: 'WebSerial' },
    { file: 'web_usb_shim.py', name: 'WebUSB' },
    { file: 'web_ftdi_shim.py', name: 'WebFTDI' },
    { file: 'web_hid_shim.py', name: 'WebHID' }
  ];

  // Parallel fetch all shims + web_bridge + praxis package
  const [shimResults, bridgeCode, praxisInit, praxisInteractive, backendStubs, protocolStubs] = await Promise.all([
    // Fetch all shims in parallel
    Promise.all(shims.map(async (shim) => {
      try {
        const response = await fetch(`assets/shims/${shim.file}`);
        if (response.ok) {
          return { shim, code: await response.text(), error: null };
        }
        return { shim, code: null, error: response.statusText };
      } catch (err) {
        return { shim, code: null, error: err };
      }
    })),
    // Fetch web_bridge
    fetch('assets/python/web_bridge.py').then(r => r.text()),
    // Fetch praxis package files
    fetch('assets/python/praxis/__init__.py').then(r => r.text()).catch(() => null),
    fetch('assets/python/praxis/interactive.py').then(r => r.text()).catch(() => null),
    // Fetch praxis.backend stubs for cloudpickle deserialization
    Promise.all([
      fetch('assets/python/praxis/backend/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/backend/core/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/backend/core/decorators/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/backend/core/decorators/models.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/backend/models/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/backend/models/domain/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/backend/models/domain/protocol.py').then(r => r.text()).catch(() => null),
    ]),
    // Fetch praxis.protocol stubs for cloudpickle deserialization
    Promise.all([
      fetch('assets/python/praxis/protocol/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/protocol/protocols/__init__.py').then(r => r.text()).catch(() => null),
      fetch('assets/python/praxis/protocol/protocols/selective_transfer.py').then(r => r.text()).catch(() => null),
    ])
  ]);


  // Write shims to Pyodide FS
  for (const { shim, code, error } of shimResults) {
    if (code) {
      pyodide.FS.writeFile(shim.file, code);
      console.log(`${shim.name} Shim loaded successfully`);
    } else {
      console.error(`Failed to load ${shim.name} Shim:`, error);
    }
  }

  // Verify files exist
  try {
    const files = pyodide.FS.readdir('.');
    console.log('Pyodide FS root files:', files.filter((f: string) => f.endsWith('.py')));
  } catch (e) {
    console.warn('Could not list FS:', e);
  }

  // Write web_bridge
  pyodide.FS.writeFile('web_bridge.py', bridgeCode);

  // Write praxis package
  try {
    pyodide.FS.mkdir('praxis');
    if (praxisInit) pyodide.FS.writeFile('praxis/__init__.py', praxisInit);
    if (praxisInteractive) pyodide.FS.writeFile('praxis/interactive.py', praxisInteractive);
    console.log('Praxis package loaded successfully');
  } catch (err) {
    console.error('Error loading praxis package:', err);
  }

  // Write praxis.backend stubs for cloudpickle protocol deserialization
  const [
    backendInit, coreInit, decoratorsInit, decoratorsModels,
    modelsInit, domainInit, domainProtocol
  ] = backendStubs;

  try {
    // Create directory structure
    pyodide.FS.mkdir('praxis/backend');
    pyodide.FS.mkdir('praxis/backend/core');
    pyodide.FS.mkdir('praxis/backend/core/decorators');
    pyodide.FS.mkdir('praxis/backend/models');
    pyodide.FS.mkdir('praxis/backend/models/domain');

    // Write stub files
    if (backendInit) pyodide.FS.writeFile('praxis/backend/__init__.py', backendInit);
    if (coreInit) pyodide.FS.writeFile('praxis/backend/core/__init__.py', coreInit);
    if (decoratorsInit) pyodide.FS.writeFile('praxis/backend/core/decorators/__init__.py', decoratorsInit);
    if (decoratorsModels) pyodide.FS.writeFile('praxis/backend/core/decorators/models.py', decoratorsModels);
    if (modelsInit) pyodide.FS.writeFile('praxis/backend/models/__init__.py', modelsInit);
    if (domainInit) pyodide.FS.writeFile('praxis/backend/models/domain/__init__.py', domainInit);
    if (domainProtocol) pyodide.FS.writeFile('praxis/backend/models/domain/protocol.py', domainProtocol);

    console.log('Praxis backend stubs loaded for cloudpickle');
  } catch (err) {
    console.error('Error loading praxis backend stubs:', err);
  }

  // Write praxis.protocol stubs for cloudpickle protocol deserialization
  const [protocolInit, protocolsInit, selectiveTransfer] = protocolStubs;

  try {
    // Create directory structure
    pyodide.FS.mkdir('praxis/protocol');
    pyodide.FS.mkdir('praxis/protocol/protocols');

    // Write stub files
    if (protocolInit) pyodide.FS.writeFile('praxis/protocol/__init__.py', protocolInit);
    if (protocolsInit) pyodide.FS.writeFile('praxis/protocol/protocols/__init__.py', protocolsInit);
    if (selectiveTransfer) pyodide.FS.writeFile('praxis/protocol/protocols/selective_transfer.py', selectiveTransfer);

    console.log('Praxis protocol stubs loaded for cloudpickle');
  } catch (err) {
    console.error('Error loading praxis protocol stubs:', err);
  }

  // Create PyodideConsole with stream callbacks
  const consoleCode = `
from pyodide.console import PyodideConsole
import js
import sys

def stdout_callback(s):
    # Use the exposed JS handler
    js.handlePythonOutput("STDOUT", s)

def stderr_callback(s):
    js.handlePythonOutput("STDERR", s)

# Create console with our callbacks
console = PyodideConsole(
    stdout_callback=stdout_callback,
    stderr_callback=stderr_callback
)

# Import web_bridge to make it available
import web_bridge

# Bootstrap the Playground environment (redirects sys.stdout/stderr, auto-imports)
web_bridge.bootstrap_playground(console.globals)

console
`;

  const consoleProxy = await pyodide.runPythonAsync(consoleCode);
  pyConsole = consoleProxy;

  // Verification call
  try {
    const checkCode = `
import builtins
print(f"SCOPE CHECK: WebSerial in builtins: {hasattr(builtins, 'WebSerial')}")
print(f"SCOPE CHECK: WebUSB in builtins: {hasattr(builtins, 'WebUSB')}")
print(f"SCOPE CHECK: WebFTDI in builtins: {hasattr(builtins, 'WebFTDI')}")
print(f"SCOPE CHECK: WebHID in builtins: {hasattr(builtins, 'WebHID')}")

# Verify FTDI patching (critical for CLARIOstarBackend)
try:
    import pylabrobot.io.ftdi as _ftdi
    print(f"SCOPE CHECK: pylabrobot.io.ftdi.FTDI = {_ftdi.FTDI}")
    print(f"SCOPE CHECK: FTDI is WebFTDI? {'WebFTDI' in str(_ftdi.FTDI)}")
except Exception as e:
    print(f"SCOPE CHECK: FTDI check failed: {e}")

# Verify HID patching (critical for Inheco)
try:
    import pylabrobot.io.hid as _hid
    print(f"SCOPE CHECK: pylabrobot.io.hid.HID = {_hid.HID}")
    print(f"SCOPE CHECK: HID is WebHID? {'WebHID' in str(_hid.HID)}")
except Exception as e:
    print(f"SCOPE CHECK: HID check failed: {e}")
    `.trim();
    pyConsole.push(checkCode);
  } catch (e) {
    console.warn('Scope check failed:', e);
  }

  postMessage({ type: 'INIT_COMPLETE', id });
}

async function executePush(id: string, code: string) {
  // PyodideConsole.push() returns a ConsoleFuture
  // For multi-line code, we split by lines and push each
  const lines = code.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    try {
      const futureProxy = pyConsole.push(line);

      const syntaxCheck = futureProxy.syntax_check;

      if (syntaxCheck === 'syntax-error') {
        futureProxy.destroy();
        break;
      }

      if (syntaxCheck === 'complete') {
        const resultProxy = await futureProxy;

        if (resultProxy !== undefined && resultProxy !== null) {
          const formatted = String(resultProxy);
          if (formatted && formatted !== 'None' && formatted !== 'undefined') {
            // result output
            postMessage({ type: 'STDOUT', id, payload: formatted + '\n' });
          }
        }

        if (typeof resultProxy?.destroy === 'function') {
          resultProxy.destroy();
        }
      }

      futureProxy.destroy();

    } catch (err: any) {
      console.error('Execution error:', err);
      // Get full Python traceback using traceback.format_exc()
      let errorMessage = '';
      try {
        const tracebackCode = `
import sys
import traceback
_tb = traceback.format_exc()
# If no exception is active, format_exc returns 'NoneType: None\\n'
_tb if _tb and _tb.strip() != 'NoneType: None' else str(sys.exc_info()[1]) if sys.exc_info()[1] else ''
`;
        const tracebackProxy = pyodide.runPython(tracebackCode);
        errorMessage = String(tracebackProxy);
        if (typeof tracebackProxy?.destroy === 'function') {
          tracebackProxy.destroy();
        }
      } catch {
        // Fallback to basic error string
        errorMessage = '';
      }

      // If we couldn't get a Python traceback, use the JS error
      if (!errorMessage || errorMessage.trim() === '') {
        errorMessage = String(err);
      }

      postMessage({ type: 'STDERR', id, payload: errorMessage + '\n' });
    }
  }

  postMessage({ type: 'EXEC_COMPLETE', id, payload: null });
}

/**
 * Initialize Pyodide from a snapshot. Much faster than fresh init.
 * Falls back to fresh init if snapshot restore fails.
 */
async function initializeFromSnapshot(id?: string, payload?: { snapshot: ArrayBuffer }) {
  if (!payload?.snapshot) {
    console.warn('[Worker] No snapshot provided, falling back to fresh init');
    await initializePyodide(id);
    return;
  }

  try {
    console.log('[Worker] Restoring from snapshot...');

    // Load base Pyodide without packages (they're in the snapshot)
    pyodide = await loadPyodide({
      indexURL: 'assets/pyodide/',
      lockFileURL: 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide-lock.json'
    });

    // Set the interrupt buffer
    pyodide.setInterruptBuffer(interruptBuffer);

    // Restore from snapshot
    const snapshotData = new Uint8Array(payload.snapshot);
    await (pyodide as any).loadSnapshot(snapshotData);

    console.log('[Worker] Snapshot restored, setting up console...');

    // Get the console from the restored snapshot
    const consoleCode = `
from pyodide.console import PyodideConsole
import js
import web_bridge

# Try to get existing console from globals, or create new one
try:
    console = web_bridge._console
except AttributeError:
    # Create new console with our callbacks
    def stdout_callback(s):
        js.handlePythonOutput("STDOUT", s)
    def stderr_callback(s):
        js.handlePythonOutput("STDERR", s)
    console = PyodideConsole(
        stdout_callback=stdout_callback,
        stderr_callback=stderr_callback
    )
    web_bridge.bootstrap_playground(console.globals)

console
`;
    const consoleProxy = await pyodide.runPythonAsync(consoleCode);
    pyConsole = consoleProxy;

    console.log('[Worker] Snapshot restore complete');
    postMessage({ type: 'INIT_COMPLETE', id, payload: { fromSnapshot: true } });

  } catch (err) {
    console.error('[Worker] Snapshot restore failed, falling back to fresh init:', err);
    await initializePyodide(id);
  }
}

/**
 * Dump the current Pyodide state as a snapshot.
 */
async function dumpSnapshot(id?: string) {
  if (!pyodide) {
    postMessage({ type: 'ERROR', id, payload: 'Pyodide not initialized' });
    return;
  }

  try {
    console.log('[Worker] Dumping snapshot...');
    const snapshot = await (pyodide as any).dumpSnapshot();
    console.log('[Worker] Snapshot dumped, size:', snapshot.byteLength, 'bytes');
    postMessage({ type: 'SNAPSHOT_DATA', id, payload: snapshot.buffer });
  } catch (err) {
    console.error('[Worker] Failed to dump snapshot:', err);
    postMessage({ type: 'ERROR', id, payload: (err as Error).message });
  }
}

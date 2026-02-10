"""
Test harness for praxis_bootstrap.py — validates logic with mocked browser APIs.
Run with: uv run python test_bootstrap.py
"""
import sys
import os
import types
import traceback

# ============================================================================
# 1. Mock Browser APIs (js, micropip, pyodide modules)
# ============================================================================

class MockXHR:
    """Mock XMLHttpRequest that returns dummy content."""
    _files = {
        'web_serial_shim.py': 'class WebSerial:\n    """Mock WebSerial"""\n    pass\n',
        'web_usb_shim.py': 'class WebUSB:\n    """Mock WebUSB"""\n    pass\n',
        'web_ftdi_shim.py': 'class WebFTDI:\n    """Mock WebFTDI"""\n    pass\n',
        'web_hid_shim.py': 'class WebHID:\n    """Mock WebHID"""\n    pass\n',
        'web_bridge.py': (
            'import builtins, sys, os\n'
            '_broadcast_channel = None\n'
            'def register_broadcast_channel(ch): global _broadcast_channel; _broadcast_channel = ch\n'
            'def handle_interaction_response(req_id, value): pass\n'
            'def bootstrap_playground(ns=None):\n'
            '    print("[web_bridge] bootstrap_playground called")\n'
            '    if ns is not None: ns["_playground_ready"] = True\n'
            'class StdoutRedirector:\n'
            '    def __init__(self, name): self.name = name\n'
            '    def write(self, text): pass\n'
            '    def flush(self): pass\n'
        ),
        'praxis/__init__.py': '# Praxis package\n__version__ = "0.1.0"\n',
        'praxis/interactive.py': '# Praxis interactive\n',
    }

    def __init__(self):
        self.status = 0
        self.responseText = ''
        self._url = ''

    def open(self, method, url, sync):
        self._url = url

    def send(self, data):
        # Match URL to file
        for filename, content in self._files.items():
            if filename in self._url:
                self.status = 200
                self.responseText = content
                return
        self.status = 404
        self.responseText = ''


class MockBroadcastChannel:
    """Mock BroadcastChannel."""
    def __init__(self, name=''):
        self.name = name
        self.onmessage = None
        self._messages = []

    def postMessage(self, msg):
        self._messages.append(msg)


class MockConsole:
    """Mock console that collects messages."""
    def __init__(self):
        self.logs = []
        self.warnings = []
        self.errors = []

    def log(self, *args):
        msg = ' '.join(str(a) for a in args)
        self.logs.append(msg)
        print(f'  [LOG] {msg}')

    def warn(self, *args):
        msg = ' '.join(str(a) for a in args)
        self.warnings.append(msg)
        print(f'  [WARN] {msg}')

    def error(self, *args):
        msg = ' '.join(str(a) for a in args)
        self.errors.append(msg)
        print(f'  [ERROR] {msg}')


class MockObjectEntries:
    """Mock js.Object.fromEntries."""
    @staticmethod
    def fromEntries(pairs):
        return dict(pairs)


def create_mock_js():
    """Create the mock `js` module."""
    js = types.ModuleType('js')
    js.console = MockConsole()
    js.XMLHttpRequest = types.SimpleNamespace(new=lambda: MockXHR())
    js.BroadcastChannel = types.SimpleNamespace(new=lambda name: MockBroadcastChannel(name))
    js.Object = MockObjectEntries()
    return js


# ============================================================================
# 2. Test Runner
# ============================================================================

def test_syntax_valid():
    """Test 1: praxis_bootstrap.py is valid Python syntax."""
    print('\n[TEST 1] Syntax validation...')
    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()
    
    try:
        compile(source, 'praxis_bootstrap.py', 'exec')
        print('  ✓ Syntax is valid')
        return True
    except SyntaxError as e:
        print(f'  ✗ Syntax error: {e}')
        return False


def test_functions_defined():
    """Test 2: All expected functions are defined."""
    print('\n[TEST 2] Function definitions...')
    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()
    
    # Install mock js module
    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    ns = {}
    try:
        exec(compile(source, 'praxis_bootstrap.py', 'exec'), ns)
    except Exception as e:
        print(f'  ✗ Exec failed: {e}')
        return False

    expected_funcs = [
        '_sync_fetch', '_install_wheels', '_mock_native_deps',
        '_patch_io_modules', '_import_resources',
        '_setup_broadcast_listener', 'praxis_main'
    ]

    all_ok = True
    for func_name in expected_funcs:
        if func_name in ns and callable(ns[func_name]):
            print(f'  ✓ {func_name} defined')
        else:
            print(f'  ✗ {func_name} NOT found')
            all_ok = False
    
    return all_ok


def test_sync_fetch():
    """Test 3: _sync_fetch works with MockXHR."""
    print('\n[TEST 3] _sync_fetch with MockXHR...')
    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()

    ns = {}
    exec(compile(source, 'praxis_bootstrap.py', 'exec'), ns)

    result = ns['_sync_fetch']('http://host/assets/shims/web_serial_shim.py')
    if result and 'WebSerial' in result:
        print(f'  ✓ Fetched web_serial_shim.py ({len(result)} bytes)')
        return True
    else:
        print(f'  ✗ Fetch failed: {result}')
        return False


def test_mock_native_deps():
    """Test 4: _mock_native_deps adds expected modules."""
    print('\n[TEST 4] Native dependency mocking...')
    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()

    ns = {}
    exec(compile(source, 'praxis_bootstrap.py', 'exec'), ns)

    # Remove any pre-existing mocks
    for mod in ['ssl', 'usb', 'usb.core', 'usb.util']:
        sys.modules.pop(mod, None)

    ns['_mock_native_deps']()

    expected = ['ssl', 'usb', 'usb.core', 'usb.util', 'serial', 'serial.tools']
    all_ok = True
    for mod in expected:
        if mod in sys.modules:
            print(f'  ✓ {mod} mocked')
        else:
            print(f'  ✗ {mod} NOT mocked')
            all_ok = False

    return all_ok


def test_shim_injection():
    """Test 5: Shim exec + builtins injection works."""
    print('\n[TEST 5] Shim injection into builtins...')
    import builtins

    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    # Simulate what praxis_main does with fetched shim files
    shim_code = 'class WebSerial:\n    """Test WebSerial"""\n    pass\n'
    ns = {}
    exec(shim_code, ns)

    if 'WebSerial' in ns:
        setattr(builtins, 'WebSerial', ns['WebSerial'])
        if hasattr(builtins, 'WebSerial'):
            print(f'  ✓ WebSerial injected into builtins: {builtins.WebSerial}')
            # Cleanup
            delattr(builtins, 'WebSerial')
            return True

    print('  ✗ Injection failed')
    return False


def test_broadcast_listener_setup():
    """Test 6: BroadcastChannel listener is set up correctly."""
    print('\n[TEST 6] BroadcastChannel listener setup...')
    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()

    ns = {'__builtins__': __builtins__}
    exec(compile(source, 'praxis_bootstrap.py', 'exec'), ns)

    # Mock web_bridge in sys.modules
    wb = types.ModuleType('web_bridge')
    wb._broadcast_channel = None
    wb.register_broadcast_channel = lambda ch: setattr(wb, '_broadcast_channel', ch)
    wb.handle_interaction_response = lambda rid, val: None
    sys.modules['web_bridge'] = wb

    ns['_setup_broadcast_listener']()

    if '_praxis_channel' in ns:
        ch = ns['_praxis_channel']
        if ch.onmessage is not None:
            print(f'  ✓ Channel created with onmessage handler')
        else:
            print(f'  ✗ onmessage not set')
            return False

        if wb._broadcast_channel is not None:
            print(f'  ✓ Channel registered with web_bridge')
        else:
            print(f'  ✗ Channel NOT registered with web_bridge')
            return False

        return True
    else:
        print('  ✗ _praxis_channel not set in globals')
        return False


def test_praxis_main_flow():
    """Test 7: Full praxis_main flow with all mocks."""
    print('\n[TEST 7] Full praxis_main execution flow...')
    import builtins

    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    # Mock micropip
    micropip = types.ModuleType('micropip')
    installed_packages = []
    async def mock_install(url, deps=True):
        installed_packages.append(url)
    micropip.install = mock_install
    sys.modules['micropip'] = micropip

    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()

    ns = {'__builtins__': __builtins__}
    exec(compile(source, 'praxis_bootstrap.py', 'exec'), ns)

    # Run praxis_main — this will skip _install_wheels and _patch_io_modules
    # since we don't have real pylabrobot, but everything else should work
    host_root = 'http://localhost:4200/'
    
    try:
        import asyncio
        asyncio.run(ns['praxis_main'](host_root))
    except Exception as e:
        # Some failures expected (no pylabrobot), but we want to see the flow
        print(f'  [Expected partial failure] {e}')

    console = mock_js.console
    
    # Check log messages for expected steps
    expected_logs = [
        'Starting with host_root',
        'Fetched web_serial_shim.py',
        'Fetched web_usb_shim.py',
        'Fetched web_bridge.py',
        'injected into builtins',
    ]

    all_ok = True
    for expected in expected_logs:
        found = any(expected in log for log in console.logs)
        if found:
            print(f'  ✓ Log contains: "{expected}"')
        else:
            print(f'  ✗ Missing log: "{expected}"')
            all_ok = False

    # Check shims were injected
    for shim in ['WebSerial', 'WebUSB', 'WebFTDI', 'WebHID']:
        if hasattr(builtins, shim):
            print(f'  ✓ {shim} in builtins')
            delattr(builtins, shim)
        else:
            print(f'  ✗ {shim} NOT in builtins')
            all_ok = False

    if console.errors:
        print(f'  [Errors (some expected)]: {console.errors}')

    return all_ok


def test_execute_message_handling():
    """Test 8: praxis:execute message handler works."""
    print('\n[TEST 8] praxis:execute message handling...')
    mock_js = create_mock_js()
    sys.modules['js'] = mock_js

    bootstrap_path = os.path.join(
        os.path.dirname(__file__),
        'src', 'assets', 'jupyterlite', 'praxis_bootstrap.py'
    )
    with open(bootstrap_path) as f:
        source = f.read()

    # Mock web_bridge
    wb = types.ModuleType('web_bridge')
    wb._broadcast_channel = None
    wb.register_broadcast_channel = lambda ch: setattr(wb, '_broadcast_channel', ch)
    wb.handle_interaction_response = lambda rid, val: None
    sys.modules['web_bridge'] = wb

    ns = {'__builtins__': __builtins__}
    exec(compile(source, 'praxis_bootstrap.py', 'exec'), ns)
    ns['_setup_broadcast_listener']()

    ch = ns['_praxis_channel']

    # Simulate a praxis:execute message with simple code
    class MockEvent:
        def __init__(self, data):
            self.data = data

    # Test simple exec (non-async)
    import io
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    event = MockEvent({'type': 'praxis:execute', 'code': 'x = 42\nprint(f"x={x}")'})
    ch.onmessage(event)

    sys.stdout = old_stdout
    output = captured.getvalue()

    if 'x=42' in output:
        print(f'  ✓ Code executed, output: {output.strip()}')
        return True
    else:
        print(f'  ✗ Unexpected output: {output.strip()}')
        return False


# ============================================================================
# 3. Run All Tests
# ============================================================================

if __name__ == '__main__':
    print('=' * 60)
    print('Praxis Bootstrap Test Harness')
    print('=' * 60)

    results = {}
    tests = [
        ('syntax_valid', test_syntax_valid),
        ('functions_defined', test_functions_defined),
        ('sync_fetch', test_sync_fetch),
        ('mock_native_deps', test_mock_native_deps),
        ('shim_injection', test_shim_injection),
        ('broadcast_listener', test_broadcast_listener_setup),
        ('praxis_main_flow', test_praxis_main_flow),
        ('execute_message', test_execute_message_handling),
    ]

    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f'  ✗ EXCEPTION: {e}')
            traceback.print_exc()
            results[name] = False

    print('\n' + '=' * 60)
    print('Results:')
    print('=' * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = '✓ PASS' if ok else '✗ FAIL'
        print(f'  {status}: {name}')
    print(f'\n{passed}/{total} tests passed')
    
    sys.exit(0 if passed == total else 1)

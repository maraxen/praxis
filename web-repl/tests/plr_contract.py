"""Declarative pylabrobot symbol contract for the web REPL browser payload.

Wheel spec ``.praxia/docs/specs/260817_spec-wheel-build-plr-upgrade.md``
T15 (:325-329) and ADR
``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 4.3 describe this file as "a module-level tuple of (module_path,
symbol_name) covering everything the browser path needs -- at minimum
pylabrobot.io.{serial.Serial,usb.USB,hid.HID,ftdi.FTDI} plus
HAS_SERIAL/USE_USB/USE_HID/HAS_PYLIBFTDI, pylabrobot.resources.{Deck,
Resource,Plate,Well,TipRack,TipSpot,Container,create_equally_spaced_2d},
pylabrobot.resources.carrier.PlateHolder,
pylabrobot.resources.resource_holder.ResourceHolder,
pylabrobot.resources.coordinate.Coordinate, and the six experimental machine
frontends including pylabrobot.storage.Incubator."

CONTRACT is intentionally a SUPERSET of that "at minimum" list: it also
covers the deeper submodules the current browser source (``web_bridge.py``,
``web_ftdi_shim.py``) actually imports for the deferred/experimental machine
paths (``pylabrobot.legacy.liquid_handling.backends[.hamilton]``,
``pylabrobot.legacy.plate_reading.bmg_labtech.clario_star_backend``) -- these are exactly the
module set ``web-repl/tests/test_contract_covers_imports.py`` (D3, ADR
Sec 2.3) checks first-party imports against. D3's own module docstring
records the intended wiring once this file exists: replace its stand-in
``_CONTRACT_MODULES`` with ``{path for path, _symbol in
plr_contract.CONTRACT}``. Keeping this file's module set a strict superset
of D3's stand-in list is what makes that swap a no-op instead of a new
failure.

PLR 1.0 (pin ``786ac2c4e``): the six machine-frontend packages, and the deeper
liquid_handling / plate_reading submodules, are named at their explicit
``pylabrobot.legacy.*`` homes. The old top-level paths still import but are
``DeprecationWarning`` shims, and this contract's probe escalates warnings to
errors -- so a shim path here could only ever fail.

THE INCUBATOR ENTRY IS DELIBERATELY THE CORRECTED PATH.
``pylabrobot.incubator`` does not exist at any pin this repo has used
(originally ``d9651e2098cd269fc47e6aff80c9242a82d1b587``) -- ``Incubator``'s real
home was ``pylabrobot.storage`` and is now ``pylabrobot.legacy.storage`` (spike-verified,
``.praxia/docs/research/260817_spike-evidence-repl-refocus.md`` :259).
``web_bridge.py``'s still-inline ``_MACHINE_CLASS_MAP`` has NOT been fixed
yet (that is Phase 4 / P4.2, a separate task) and still maps to the stale
``pylabrobot.incubator`` string -- this contract does not, and must not,
list that stale path. ``test_plr_contract.py``'s filter self-test asserts
this directly: the stale entry is absent, proving CONTRACT is a curated
list, not "whatever currently happens to import."

WHY THIS IS A BARE TUPLE, NOT A GENERATED/FILTERED VIEW OF PLR's OWN
namespace: pyproject.toml's ``pylabrobot = {path = "external/pylabrobot",
editable = true}`` source means a filter walking the live PLR package would
silently probe the submodule, not the built wheel -- exactly the shadowing
bug ``test_plr_contract.py`` exists to catch. A hand-curated, static tuple
has no such failure mode: it names what the product needs regardless of
which pylabrobot install is on ``sys.path``.
"""

from __future__ import annotations

# (module_path, symbol_name) pairs. Order follows the wheel spec's own
# grouping: io capability probes, resources, then the six experimental
# machine frontends plus their deeper submodules actually referenced by the
# browser source (see module docstring).
CONTRACT: tuple[tuple[str, str], ...] = (
    # -- pylabrobot.io.* capability probes: classes + their HAS_*/USE_* flags.
    ("pylabrobot.io.serial", "Serial"),
    ("pylabrobot.io.serial", "HAS_SERIAL"),
    ("pylabrobot.io.usb", "USB"),
    ("pylabrobot.io.usb", "USE_USB"),
    ("pylabrobot.io.hid", "HID"),
    ("pylabrobot.io.hid", "USE_HID"),
    ("pylabrobot.io.ftdi", "FTDI"),
    ("pylabrobot.io.ftdi", "HAS_PYLIBFTDI"),
    # -- pylabrobot.resources.* -- the REPL's core, builtins-sprayed surface
    # (praxis_bootstrap.py's _import_resources, preserved verbatim).
    ("pylabrobot.resources", "Deck"),
    ("pylabrobot.resources", "Resource"),
    ("pylabrobot.resources", "Plate"),
    ("pylabrobot.resources", "Well"),
    ("pylabrobot.resources", "TipRack"),
    ("pylabrobot.resources", "TipSpot"),
    ("pylabrobot.resources", "Container"),
    ("pylabrobot.resources", "create_equally_spaced_2d"),
    ("pylabrobot.resources.carrier", "PlateHolder"),
    ("pylabrobot.resources.resource_holder", "ResourceHolder"),
    ("pylabrobot.resources.coordinate", "Coordinate"),
    # -- the six experimental machine frontends (_MACHINE_CLASS_MAP's module
    # halves, web_bridge.py:407-414), Incubator corrected to its real home.
    # PLR 1.0 turned the old top-level packages into DeprecationWarning shims
    # over ``pylabrobot.legacy.*`` (the gate runs with warnings as errors, so
    # relying on a shim fails it), hence the explicit ``.legacy`` homes.
    ("pylabrobot.legacy.liquid_handling", "LiquidHandler"),
    ("pylabrobot.legacy.plate_reading", "PlateReader"),
    ("pylabrobot.legacy.heating_shaking", "HeaterShaker"),
    ("pylabrobot.legacy.shaking", "Shaker"),
    ("pylabrobot.legacy.centrifuge", "Centrifuge"),
    ("pylabrobot.legacy.storage", "Incubator"),
    # -- deeper submodules the current browser source actually imports for
    # the deferred/experimental machine paths (web_bridge.py:1301-1435,
    # web_ftdi_shim.py:18). Kept in the contract so D3's AST import-coverage
    # test (test_contract_covers_imports.py) finds them covered once wired
    # to this file's module set.
    ("pylabrobot.legacy.liquid_handling.backends", "LiquidHandlerBackend"),
    ("pylabrobot.legacy.liquid_handling.backends.hamilton", "STAR"),
    # Not ``pylabrobot.legacy.plate_reading.clario_star_backend``: that module is
    # itself a warn-on-import re-export of this one.
    ("pylabrobot.legacy.plate_reading.bmg_labtech.clario_star_backend", "CLARIOstarBackend"),
    # -- the visualizer base class praxis/viz/browser.py subclasses (P6.4).
    # Added because D3 caught its absence: BrowserVisualizer imports this module
    # and the contract did not cover it, so the wheel could have stopped
    # providing it without any check going red. Importing the module is safe
    # without websockets installed -- the HAS_WEBSOCKETS guard raises in
    # Visualizer.__init__, not at import time -- so the throwaway-venv contract
    # check does not need websockets to verify this symbol resolves.
    ("pylabrobot.visualizer.visualizer", "Visualizer"),
)

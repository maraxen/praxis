---
title: 'Component Audit: Playground & Run Protocol'
---

# Component Audit: Playground & Run Protocol

## Mock Data / Hardcoded Values

### Playground

- [ ] `praxis/web-client/src/app/features/playground/drivers/mock-serial.ts`: Full mock implementation of `ISerialDriver` used for testing/browser mode.
- [ ] `praxis/web-client/src/app/features/playground/playground.component.ts:558`: `sys.modules["pylibftdi"] = MagicMock()` injected into Python kernel.
- [ ] `praxis/web-client/src/app/features/playground/playground.component.ts:391`: `mockChannels` global variable usage for testing broadcast channels.

### Run Protocol

- [ ] `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts:71`: `getCompatibility` returns hardcoded/mock compatibility data in browser mode.
- [ ] `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts:366`: `startRun` generates simulation placeholder code if protocol import fails.
- [ ] `praxis/web-client/src/app/features/run-protocol/services/deck-generator.service.ts:12`: `DEFAULT_DIMENSIONS` constant used as fallback for resource dimensions.
- [ ] `praxis/web-client/src/app/features/run-protocol/services/deck-catalog.service.ts:34`: Hardcoded Hamilton STAR rail spacing and offsets.
- [ ] `praxis/web-client/src/app/features/run-protocol/services/deck-catalog.service.ts:644`: Hardcoded `getHamiltonCarriers` definitions.
- [ ] `praxis/web-client/src/app/features/run-protocol/services/carrier-inference.service.ts:11`: Hardcoded `CARRIER_COMPATIBILITY` map.

## TODO Comments

### Playground

- [ ] `praxis/web-client/src/app/features/playground/services/device-manager.service.ts`: (implied) Error handling for WebSerial permission denial is minimal.

### Run Protocol

- [ ] `praxis/web-client/src/app/features/run-protocol/services/deck-generator.service.ts:87`: `state: {} // TODO: Populate state if needed`
- [ ] `praxis/web-client/src/app/features/run-protocol/components/deck-setup-wizard/deck-setup-wizard.component.ts:337`: `// TODO: Add confirmation dialog` in `onSkip()`.

## Missing Error Handling

- [ ] `PlaygroundComponent.insertAsset`: `catch` block catches permission errors but generic handling is "Failed to check hardware permissions".
- [ ] `ExecutionService.executeBrowserProtocol`: `catch` block handles execution errors but `pythonRuntime.executeBlob` error propagation could be more granular (currently just logs to console/UI log).
- [ ] `DeckGeneratorService.getResourceDimensions`: Silently catches errors and falls back to defaults (`console.debug` only).

## Incomplete Features

- [ ] **Deck Auto-Placement**: `DeckGeneratorService` has commented out logic for placing assigned assets (`// Removed auto-placement logic`), relying on starting empty.
- [ ] **Carrier Inference**: `CarrierInferenceService` uses string matching (`name.includes('plate')`) which is brittle compared to proper type checking against the definition.
- [ ] **Browser I/O Shims**: `web_serial_shim.py` and `web_usb_shim.py` are dynamically fetched/injected. If these assets are missing, the REPL will fail to initialize hardware support silently or with a generic error.

## Manual Verification Needed

- [ ] **WebSerial Handling**: Verify `PlaygroundComponent` correctly asks for permission and handles "Cancel" in the permission dialog.
- [ ] **JupyterLite Boot**: Verify `getOptimizedBootstrap` correctly injects the Python shims and `pylabrobot` wheel without 404s.
- [ ] **Deck Visualization**: Verify `DeckSetupWizard` correctly renders the inferred deck layout (carriers + resources) despite `DeckGeneratorService` stripping some logic.
- [ ] **Protocol Simulation**: Verify `ExecutionService` correctly runs the "simulation placeholder" path when a real protocol file isn't present in `assets/protocols`.

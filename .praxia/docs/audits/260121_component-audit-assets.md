---
title: 'Component Audit: Assets & Protocols'
---

# Component Audit: Assets & Protocols

## Mock Data / Hardcoded Values

- [ ] Location: `praxis/web-client/src/app/features/assets/components/machine-list/machine-details-dialog.component.ts:466` - `mockUtilization` is generated randomly for visualization.
- [ ] Location: `praxis/web-client/src/app/features/protocols/components/protocol-detail/protocol-detail.component.ts:68` - HTML placeholder for future sections (Parameters Preview, Source Code).
- [ ] Location: `praxis/web-client/src/app/features/assets/models/asset.models.ts:140, 161` - `backend_type` definition explicitly allows 'mock' as a valid type.

## TODO Comments

- [ ] Location: `praxis/web-client/src/app/features/assets/components/machine-list/machine-list.component.ts:517` - "TODO: Implement machine editing"
- [ ] Location: `praxis/web-client/src/app/features/assets/components/machine-list/machine-list.component.ts:521` - "TODO: Implement machine duplication"
- [ ] Location: `praxis/web-client/src/app/features/assets/components/resource-list/resource-list.component.ts:249` - "TODO: Implement resource editing"
- [ ] Location: `praxis/web-client/src/app/features/assets/components/resource-list/resource-list.component.ts:253` - "TODO: Implement resource duplication"
- [ ] Location: `praxis/web-client/src/app/features/assets/components/resource-accordion/resource-instances-dialog.component.ts:220` - "TODO: Implement status update via service"
- [ ] Location: `praxis/web-client/src/app/features/assets/components/resource-accordion/resource-instances-dialog.component.ts:224` - "TODO: Implement cleaning workflow"
- [ ] Location: `praxis/web-client/src/app/features/assets/components/resource-accordion/resource-instances-dialog.component.ts:228` - "TODO: Open add resource dialog with pre-selected definition"

## Missing Error Handling

- [ ] `ResourceAccordionComponent.loadData()` - Subscribes to `getResources`, `getResourceDefinitions`, and `getMachines` without any error handling blocks.
- [ ] `ProtocolLibraryComponent.loadProtocols()` - Uses `console.error` only; no UI feedback for failed fetches.
- [ ] `ProtocolLibraryComponent.uploadProtocol()` - Only logs error to console; user is not notified if upload fails.
- [ ] `MachineListComponent.loadMachines()` / `loadMachineDefinitions()` / `deleteMachine()` - All use `console.error` for errors; needs a snackbar or error state UI.

## Incomplete Features

- [ ] **Asset Management**: Machine and Resource editing/duplication are placeholders only.
- [ ] **Resource Lifecycle**: Marking resources as discarded or sending them for cleaning is not implemented.
- [ ] **Resource Creation**: The "Add Instance" button in the instances dialog is a placeholder.
- [ ] **Protocol Details**: Detailed view for protocols is missing source code preview and parameter validation preview.

## Manual Verification Needed

- [ ] **SQLite Integration**: Verify that `AssetService` correctly interacts with the SQLite service in `BrowserMode` for all CRUD operations.
- [ ] **Real Utilization Data**: Ensure machine utilization charts switch from random data to actual historical data once exposed by the backend.
- [ ] **Protocol Upload**: Test the `.py` file upload flow end-to-end to ensure proper parsing on the backend.
- [ ] **AppStore State**: Verify that global settings like `infiniteConsumables` correctly update the UI state across different views.

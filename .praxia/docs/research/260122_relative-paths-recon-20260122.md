---
title: 'Web Client Relative Path Audit Report'
---

# Web Client Relative Path Audit Report

## 1. Summary

This report analyzes the usage of relative paths in the Angular web client's TypeScript, HTML, and SCSS files. The audit found that while there are no relative paths used for asset references in HTML, SCSS, or TypeScript, there is extensive use of relative paths for module imports in TypeScript files.

### Summary Statistics

*   **Relative Asset Paths:** 0 instances found.
*   **Relative Import Paths:**
    *   Depth 1 (`../`): 533
    *   Depth 2 (`../../`): 218
    *   Depth 3 (`../../../`): 111
    *   Depth 4 (`../../../../`): 39
    *   Depth 5 (`../../../../../`): 2
    *   Depth 6 (`../../../../../../`): 0

## 2. File-by-File Breakdown (Worst Offenders)

The following files have the highest number of deep relative path imports:

### Depth 6 (`../../../../../../`)



### Depth 5 (`../../../../../`)

* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/workcell-group/workcell-group.component.ts:import { WorkcellGroup, MachineWithRuntime } from '../../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/machine-tree-node/machine-tree-node.component.ts:import { MachineWithRuntime } from '../../../../../features/workcell/models/workcell-view.models';

### Depth 4 (`../../../../`)

* praxis/web-client/src/app/features/protocols/components/protocol-library/protocol-library.component.ts:import { ViewControlsComponent } from '../../../../shared/components/view-controls/view-controls.component';
* praxis/web-client/src/app/features/protocols/components/protocol-library/protocol-library.component.ts:import { ViewControlsConfig, ViewControlsState } from '../../../../shared/components/view-controls/view-controls.types';
* praxis/web-client/src/app/features/assets/components/maintenance-badge/maintenance-badge.component.ts:import { AppStore } from '../../../../core/store/app.store';
* praxis/web-client/src/app/features/assets/components/spatial-view/spatial-view.component.ts:import { ViewControlsComponent } from '../../../../shared/components/view-controls/view-controls.component';
* praxis/web-client/src/app/features/assets/components/spatial-view/spatial-view.component.ts:import { ViewControlsConfig, ViewControlsState } from '../../../../shared/components/view-controls/view-controls.types';
* praxis/web-client/src/app/features/assets/components/resource-filters/resource-filters.component.spec.ts:import { FilterResultService } from '../../../../shared/services/filter-result.service';
* praxis/web-client/src/app/features/assets/components/resource-filters/resource-filters.component.ts:import { PraxisMultiselectComponent } from '../../../../shared/components/praxis-multiselect/praxis-multiselect.component';
* praxis/web-client/src/app/features/assets/components/resource-filters/resource-filters.component.ts:import { FilterOption, FilterResultService } from '../../../../shared/services/filter-result.service';
* praxis/web-client/src/app/features/assets/components/resource-filters/resource-filters.component.ts:import { extractUniqueNameParts } from '../../../../shared/utils/name-parser';
* praxis/web-client/src/app/features/assets/components/machine-filters/machine-filters.component.ts:import { extractUniqueNameParts } from '../../../../shared/utils/name-parser';
* praxis/web-client/src/app/features/assets/components/machine-list/machine-list.component.ts:import { ViewControlsComponent } from '../../../../shared/components/view-controls/view-controls.component';
* praxis/web-client/src/app/features/assets/components/machine-list/machine-list.component.ts:import { ViewControlsConfig, ViewControlsState } from '../../../../shared/components/view-controls/view-controls.types';
* praxis/web-client/src/app/features/assets/components/machine-list/machine-list.component.ts:import { AppStore } from '../../../../core/store/app.store';
* praxis/web-client/src/app/features/assets/components/machine-list/machine-details-dialog.component.ts:import { DeckVisualizerComponent } from '../../../../features/run-protocol/components/deck-visualizer/deck-visualizer.component';
* praxis/web-client/src/app/features/assets/components/machine-list/machine-details-dialog.component.ts:import { AppStore } from '../../../../core/store/app.store';
* praxis/web-client/src/app/features/assets/components/asset-filters/asset-filters.component.ts:import { PraxisSelectComponent } from '../../../../shared/components/praxis-select/praxis-select.component';
* praxis/web-client/src/app/features/assets/components/asset-filters/asset-filters.component.ts:import { PraxisMultiselectComponent } from '../../../../shared/components/praxis-multiselect/praxis-multiselect.component';
* praxis/web-client/src/app/features/assets/components/asset-filters/asset-filters.component.ts:import { SelectOption } from '../../../../shared/components/praxis-select/praxis-select.component';
* praxis/web-client/src/app/features/assets/components/asset-filters/asset-filters.component.ts:import { extractUniqueNameParts } from '../../../../shared/utils/name-parser';
* praxis/web-client/src/app/features/assets/components/resource-accordion/resource-accordion.component.spec.ts:import { AppStore } from '../../../../core/store/app.store';
* praxis/web-client/src/app/features/assets/components/resource-accordion/resource-accordion.component.ts:import { AppStore } from '../../../../core/store/app.store';
* praxis/web-client/src/app/features/assets/components/resource-accordion/resource-accordion.component.ts:import { ViewControlsComponent } from '../../../../shared/components/view-controls/view-controls.component';
* praxis/web-client/src/app/features/assets/components/resource-accordion/resource-accordion.component.ts:import { ViewControlsConfig, ViewControlsState } from '../../../../shared/components/view-controls/view-controls.types';
* praxis/web-client/src/app/features/docs/components/system-topology/system-topology.component.ts:import { AppStore } from '../../../../core/store/app.store';
* praxis/web-client/src/app/features/docs/components/system-topology/system-topology.component.ts:import { DiagramOverlayComponent } from '../../../../shared/components/diagram-overlay/diagram-overlay.component';
* praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.ts:import { MachineRead } from '../../../../core/api-generated/models/MachineRead';
* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/workcell-explorer.component.spec.ts:import { WorkcellGroup, MachineWithRuntime } from '../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/workcell-explorer.component.spec.ts:import { MachineStatus } from '../../../../features/assets/models/asset.models';
* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/workcell-group/workcell-group.component.ts:import { WorkcellGroup, MachineWithRuntime } from '../../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/machine-tree-node/machine-tree-node.component.ts:import { MachineWithRuntime } from '../../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/workcell-explorer/workcell-explorer.component.ts:import { WorkcellGroup, MachineWithRuntime } from '../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/machine-card/machine-card-mini.component.spec.ts:import { MachineWithRuntime } from '../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/machine-card/machine-card-mini.component.spec.ts:import { MachineStatus } from '../../../../features/assets/models/asset.models';
* praxis/web-client/src/app/shared/components/workcell/machine-card/machine-card-mini.component.ts:import { MachineWithRuntime } from '../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/machine-card/machine-card.component.ts:import { MachineWithRuntime } from '../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/machine-card/machine-card.component.spec.ts:import { MachineWithRuntime } from '../../../../features/workcell/models/workcell-view.models';
* praxis/web-client/src/app/shared/components/workcell/machine-card/machine-card.component.spec.ts:import { MachineStatus } from '../../../../features/assets/models/asset.models';
* praxis/web-client/src/app/shared/components/workcell/machine-status-badge/machine-status-badge.component.ts:import { MachineStatus } from '../../../../features/assets/models/asset.models';
* praxis/web-client/src/app/shared/components/workcell/machine-status-badge/machine-status-badge.component.spec.ts:import { MachineStatus } from '../../../../features/assets/models/asset.models';

## 3. Angular Path Configuration

The `tsconfig.json` file already has a comprehensive set of path aliases configured:

```json
"paths": {
    "@core/*": [
    "src/app/core/*"
    ],
    "@features/*": [
    "src/app/features/*"
    ],
    "@shared/*": [
    "src/app/shared/*"
    ],
    "@env/*": [
    "src/environments/*"
    ],
    "@assets/*": [
    "src/assets/*"
    ],
    "@api/*": [
    "src/app/core/api-generated/*"
    ],
    "@api": [
    "src/app/core/api-generated/index.ts"
    ]
}
```

## 4. Replacement Recommendations

Given the existing path aliases, the migration strategy is straightforward. All relative import paths should be replaced with the appropriate path alias.

### Proposed Path Alias Usage

*   Imports from `src/app/core` should use `@core/`.
*   Imports from `src/app/features` should use `@features/`.
*   Imports from `src/app/shared` should use `@shared/`.
*   Imports from `src/environments` should use `@env/`.
*   Imports from `src/assets` should use `@assets/`.
*   Imports from `src/app/core/api-generated` should use `@api/`.

### Migration Strategy

1.  **Prioritize Deepest Paths:** Start by replacing the deepest relative paths (depth 6, then 5, etc.). This will have the most significant impact on code readability and maintainability.

2.  **Automated Refactoring:** Use a tool like a global find-and-replace with a regular expression to update the import paths. For example, to replace imports to the `@shared` directory, you could use a regex to find imports that match the pattern `from '[..\/]+shared/([\w\/.-]+)'` and replace it with `from '@shared/'`.

3.  **Manual Verification:** After automated replacement, it is essential to manually verify the changes to ensure that no incorrect paths have been introduced.

By following this strategy, the web client's codebase can be significantly improved, making it more readable, maintainable, and easier to refactor in the future.

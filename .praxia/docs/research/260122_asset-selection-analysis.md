# Asset Selection Logic & Status Report

**Date:** 2026-01-21
**Component:** `RunProtocolComponent` > `GuidedSetupComponent`

## 1. Overview

The asset selection phase is Step 4 in the Run Protocol wizard. Its purpose is to map abstract **Asset Requirements** defined in the protocol (e.g., "1x 96-well PCR Plate") to concrete **Inventory Resources** (e.g., "plate_123").

## 2. Architecture & Data Flow

* **Host:** `RunProtocolComponent` coordinates the wizard.
* **Logic Handler:** `GuidedSetupComponent` (`app-guided-setup`) executes the matching logic.
* **Input:** `ProtocolDefinition.assets` (List of requirements).
* **Inventory Source:** `AssetService.getResources()` (Fetches full inventory).
* **Output:** `configuredAssets` signal (Map: `accession_id` -> `Resource`).

## 3. Matching Logic (`getCompatibleResources`)

The system employs a multi-strategy approach to find compatible inventory items for a given requirement. A resource is considered compatible if it satisfies **any** of the following strategies (checked in order), provided it is **not a Carrier**:

1. **Exact FQN Match:** `resource.fqn` === `requirement.fqn`
2. **Class Name Match:** The last part of the FQN matches (e.g., `...Plate96` matches `...Plate96`).
3. **Type Hint Match:** The `requirement.type_hint_str` is found within the resource's class name.
4. **Category Match:** (High Priority) If `requirement.required_plr_category` is set, it matches against the resource's PLR definition category.

**Constraint:** Carrier resources are explicitly excluded from this selection step (they are handled in Deck Setup).

## 4. Auto-Selection Algorithm (`autoSelect`)

To reduce user effort, the system attempts to auto-fill selections when the step loads:

1. **Scope:** Iterates through all requirements in the protocol.
2. **Exclusion:** Skips requirements that already have a manual selection.
3. **Search:** Finds all compatible resources for the requirement.
4. **Prioritization:** Separation into "Exact Matches" (FQN match) and "Other Compatible". Exact matches are preferred.
5. **Availability Check:** Maintains a local `usedResourceIds` set to ensure a physical resource is not assigned to multiple requirements within the same run.
6. **Assignment:** Selects the first available candidate and marks the requirement as `Autofilled`.

## 5. Validation Rules

* **Required Fields:** The step is invalid if any **non-optional** requirement has no assigned resource.
* **Optional Fields:** Can be left empty (`null`).

## 6. Current Status & Limitations

### ✅ Working Features

* **Robust Matching:** The 4-layer matching strategy covers most use cases (specific vs generic).
* **Auto-Complete:** Reduces setup time significantly.
* **Visual Feedback:** Clear badges for "Auto", "Set", and "Optional".
* **Inline/Dialog Mode:** Component works both inside the wizard (`isInline=true`) and as a standalone dialog.

### ⚠️ Identified Gaps (Technical Debt)

1. **Missing Inspection UI:** Users cannot click an asset to see its details (e.g., volume, remaining quantity). This was confirmed via deep research (Dispatch `d260121152102336_4225`).
2. **Status Filtering:** The logic currently does not appear to filter out resources based on their global status (e.g., `IN_USE`, `DEPLETED`). It relies on the user or the `AssetService` logic (which currently returns all items).
3. **Strictness:** The "Type Hint" match (Strategy 3) uses `string.includes()`, which might be too loose for complex inventories (e.g., "Plate" matching "PlateLid").

## 7. Investigation Addendum

**Topic:** Asset Selection UI Capabilities

### Findings

1. **Dialog vs. Autocomplete:**
    * **Current State:** There is **NO** option for a dedicated dialog to select items. The UI exclusively uses `app-praxis-autocomplete` (lines 97-102 of `guided-setup.component.ts`) for item selection.
    * **Implication:** Users can only search and select via the dropdown. They cannot browse a full table or view detailed metadata in a separate modal during selection.

2. **Reselection Logic:**
    * **Feasibility:** The code supports reselection. The `updateSelection` method (line 655) updates the `selectedAssets` signal, which is bound to the autocomplete's `ngModel`.
    * **Behavior:**
        * When a user manually changes a selection, the `autofilledIds` set is updated to remove that requirement ID (lines 667-672), ensuring the "Auto" badge is replaced by "Set" (or nothing).
        * This explicit state management confirms that **manual reselection is intended and logically supported**, overriding any initial auto-selection.
    * **Testing:** There are **NO** unit tests for `GuidedSetupComponent` (`guided-setup.component.spec.ts` does not exist). Therefore, while the logic appears sound, it has likely **not been rigorously tested** for edge cases (e.g., clearing a selection, re-selecting the same auto-filled item).

3. **Retriggering Autoselection:**
    * **Availability:** There is **NO** button in the UI to manually retrigger the `autoSelect()` logic.
    * **Execution:** `autoSelect()` is only called once: inside the `ngOnInit` subscription block (line 381) when the inventory is first loaded.
    * **Consequence:** If a user manually clears several selections and wants to "reset" to the system's best guess, they must reload the entire component/wizard step.

## 8. Recommendations

1. **Implement specific click handlers** for asset rows to trigger a `ResourceDetailsDialog`.
2. **Enhance filtering** to exclude `DEPLETED` resources automatically.
3. **Add "In Use" warnings** if a selected resource is currently active in another run (requires backend support).
4. **Add Reset Button:** Implement a "Reset to Defaults" or "Auto-Fill" button in the summary section (near line 111) that calls `autoSelect()`. This would allow users to recover from accidental manual changes.
5. **Verify Reselection:** Create a unit test suite (`guided-setup.component.spec.ts`) to specifically verify that `updateSelection` correctly handles null values (clearing) and new resource assignments, and updates the `autofilled` state accordingly.
6. **Add Clear Selection Button:** Add an explicit "Clear" button to each selection row to allow users to easily unassign a resource without needing to search/select 'null'.
7. **Reuse Existing Components:** When implementing the detailed item selection dialog, strictly **reuse existing components** to maintain consistency. Options include:
    * `ResourceInstancesDialog` or `AssetList` (standard lists).
    * `AssetSelectionWizard` (with the first step bypassed to focus purely on resource selection).
    * **Action:** Review these candidates to determine the best approach before implementation.

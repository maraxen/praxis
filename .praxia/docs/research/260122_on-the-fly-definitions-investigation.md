# Investigation: On-the-Fly Simulation Definition Creation

## Executive Summary

The Playground currently lacks a UI for creating *definitions* (types of machines/resources) on the fly. While the backend API fully supports creating `MachineDefinition`, `ResourceDefinition`, and `DeckDefinition` entities via POST endpoints, the frontend `AssetWizard` only allows instantiating *existing* definitions.

## Findings

### 1. Existing Capabilities

- **Frontend Search**: `grep` confirmed no "create definition" logic exists in `AssetWizard` or `Playground`.
- **Backend API**: The following endpoints are generated and available in `MachineDefinitionsService`, `ResourceDefinitionsService`, and `DeckTypeDefinitionsService`:
  - `POST /api/v1/machines/definitions`
  - `POST /api/v1/resources/definitions`
  - `POST /api/v1/decks/types`

### 2. "On-the-Fly" Creation Scope

To support true dynamic simulation, the user needs to define the *topology* of the simulated hardware, not just instantiate it.

- **Machines**:
  - **Use Case**: User wants to simulate a generic "3-Axis Portal" or a "Custom Shaker" that isn't in the PLR catalog.
  - **Fields Needed**: Name, Capabilities (RPM, Temp), Dimensions (x, y, z), Compatible Backends (set to 'Simulated').
- **Resources**:
  - **Use Case**: User uses a specific brand of 96-well plate not in the library.
  - **Fields Needed**: Dimensions (x, y, z), Well Count, Well Volume, Well Shape (V-bottom/Flat), Tip Volume.
- **Decks**:
  - **Use Case**: User has a custom bench layout.
  - **Fields Needed**: Slot definitions (coordinates, carrier types).

## Feature Specification

### New Feature: Definition Builder

A standalone dialog or a "Create New" action within the `AssetWizard` search step.

#### Workflow

1. User opens Inventory -> Add Asset.
2. In the "Select Definition" step, if search yields no results (or explicitly via button), user clicks **"Create Custom Definition"**.
3. **Definition Wizard** opens:
    - **Step 1: Category**: Machine vs Resource.
    - **Step 2: Basic Info**: Name, Model, Manufacturer.
    - **Step 3: Geometry/Physics**:
        - *Resource*: X, Y, Z, Wells, Volume.
        - *Machine*: Capabilities (JSON editor or form fields).
    - **Step 4: Save**: Calls `createApiV1...Post`.
4. The new definition is automatically selected in the `AssetWizard`.

## Effort Estimate

- **Backend**: **Low** (0 days). Endpoints exist.
- **Frontend**: **High** (3-5 days).
  - Requires robust forms for geometric data validation.
  - Requires UI for defining capabilities (possibly JSON schema form).
  - Integration into existing `AssetWizard` flow.
  - Browser-mode mock support (needs to persist new definitions to SQLite `machine_definitions` table).

## Recommendation

Implement a "Basic Resource Builder" first (plate/tube rack) as it has the highest impact for simulation fidelity. Complex machine definitions can remain a "Configuration Code" task for now.

# Report: Simulation Backend Dropdown Bug Fix

## Problem

In the Run Protocol wizard, when configuring a simulation, the "Simulation Backend" dropdown displayed malformed options (e.g., individual characters or JSON brackets) instead of full backend names.

## Root Cause

The `MachineDefinition` table in the browser SQLite database stores `available_simulation_backends` as a JSON string. However, the generic `SqliteRepository` was only configured to automatically parse columns ending in `_json`. Since `available_simulation_backends` (and other columns like `capabilities`, `compatible_backends`, etc.) did not follow this naming convention, they were returned as raw strings. The Angular `@for` directive then iterated over the characters of the string instead of the elements of an array.

## Implementation

Instead of a localized fix in the component, a systemic fix was implemented in the database infrastructure:

- Modified `praxis/web-client/src/app/core/db/sqlite-repository.ts` to:
  - Automatically deserialize columns ending in `_config`.
  - Automatically deserialize specific known JSON columns: `capabilities`, `compatible_backends`, `available_simulation_backends`, `user_configured_capabilities`, `plr_state`, `plr_definition`, `allowed_resource_definition_names`, `compatible_resource_fqns`, and `tags`.
  - Correctly map boolean columns `requires_deck` and `is_simulated_frontend` from SQLite (0/1) to TypeScript (boolean).

## Verification

- Code review confirms that `available_simulation_backends` is now correctly parsed into an array before reaching the component.
- The fix also addresses potential metadata corruption in other areas (e.g., `capabilities` and `capabilities_config`) that were suffering from the same lack of deserialization.

## Status

Fixed in repository layer.

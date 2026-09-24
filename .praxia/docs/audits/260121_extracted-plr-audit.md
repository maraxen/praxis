---
title: 'PLR Category Architecture Audit - Extraction Report'
---

# PLR Category Architecture Audit - Extraction Report

## Summary

The session focused on implementing a standardized filtering mechanism for PyLabRobot (PLR) categories across the backend and frontend. This enables more granular discovery of resources (e.g., plates, tip racks) in the Asset Management system.

## Extracted Findings & Improvements

### 1. Backend: Standardized Filtering

- **Model Enhancements**: Added `plr_category` field to `SearchFilters` in `praxis/backend/models/pydantic_internals/filters.py`.
- **Query Builder**: Implemented `apply_plr_category_filter` in `praxis/backend/services/utils/query_builder.py` and integrated it into the main `apply_search_filters` pipeline.
- **Deduplication**: Cleaned up `CRUDBase.get_multi` in `praxis/backend/services/utils/crud_base.py` by removing redundant hand-coded filter application logic in favor of the centralized `apply_search_filters`.

### 2. Frontend: Dynamic Filtering UI

- **Component Update**: Added a "Category" dropdown to `ResourceDialogComponent` (`praxis/web-client/src/app/features/assets/components/resource-dialog.component.ts`).
- **Reactive Updates**: Implemented `onCategoryChange` to trigger a re-fetch of resource definitions whenever the category selection changes.
- **Service Integration**: Updated `AssetService.getResourceDefinitions` to support the optional `plrCategory` parameter using `HttpParams`.

### 3. Verification

- **New Tests**: Created `praxis/backend/tests/api/test_resource_filtering.py` to verify:
  - Filtering resource definitions by `plate`.
  - Filtering resource definitions by `tip_rack`.
  - Default behavior when no filter is provided.

## Architectural Recommendations for Future Work

- **Consistency**: Ensure all ORM models for resources (Machines, Labware, etc.) implement the `plr_category` attribute to fully utilize the new filter.
- **Expansion**: Consider adding more standard PLR categories (e.g., `shaker`, `heater`, `pump`) to the `mat-select` options in the frontend as they are added to the system.
- **Dynamic Options**: Ideally, the list of categories should be fetched from an endpoint rather than hardcoded in the template.

## ⚠️ Path Discrepancies

During extraction, several discrepancies between the session diff and the current codebase were noted:

- **Filters Model**: The diff references `praxis/backend/models/pydantic_internals/filters.py`, but the current location is `praxis/backend/models/domain/filters.py`.
- **ORM Models**: The diff uses `praxis.backend.models.orm.resource`, but the classes are actually in `praxis.backend.models.domain.resource`.
- **Integration**: While the diff simplifies `CRUDBase.get_multi`, the changes should be applied to the correct paths in `praxis/backend/services/utils/crud_base.py`.

---
**Extracted from session**: `9570037443858871469`
**Reference Task**: TD-401

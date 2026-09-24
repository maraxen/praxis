---
title: 'Frontend UI/UX Guide & Style System'
---

# Frontend UI/UX Guide & Style System

> **Framework**: Angular v21 + Angular Material 3
> **Design Philosophy**: Hybrid Density (Standard Shell / Dense Data)

---

## 1. Core Architecture Decisions

### A. Data Grid Strategy: `MatTable`

* **Choice**: Native Angular Material Table (`MatTable`).
* **Reasoning**: Consistent visual style with Material 3, lightweight dependency.
* **Usage**:
  * Used for all asset lists (Machines, Resources), protocol libraries, and run history.
  * **Pagination**: Required for lists > 20 items.
  * **Sorting**: Enabled on all main text/date columns.
  * **Filtering**: Simple text filter bar above table.

### B. Dynamic Forms: `Formly`

* **Choice**: `@ngx-formly` with Material UI bindings.
* **Reasoning**: JSON-schema driven forms are essential for the "Protocol Parameter Configuration" step, where the form structure is dictated by the Python protocol definition.
* **Customization**:
  * **Wrappers**: Custom wrappers for "Field Groups" (e.g., Dictionary keys).
  * **Types**: Custom types for "Labware Selector" and "Machine Selector".

### C. Visualization: SVG (Future Integration)

* **Choice**: SVG-based rendering.
* **Plan**:
  * Initial MVP: Simple list/grid view of deck slots.
  * Phase 4: Integrate `pylabrobot`'s native visualization tools (likely SVG or Canvas based) to render the deck state.
  * *Note*: Avoid premature optimization with Three.js/WebGL unless specifically required for 3D manipulation.

### D. Layout Density: Hybrid

* **Shell (Nav/Sidebar)**: **Standard Density**. Large touch targets (48dp), generous whitespace. Friendly and accessible.
* **Data Views (Tables/Parameters)**: **High Density**.
  * Table Row Height: 40px - 48px (vs standard 52px).
  * Form Spacing: Compact vertical rhythm.
  * Font Size: 13px/14px for data cells.

### E. Feedback & Error Handling

* **Global Status Bar**: A persistent, thin bar at the top (or bottom) of the viewport indicating the connection state (WebSocket Connected/Disconnected) and critical System Status (e.g., "Robot E-Stop Active").
* **Toasts (`MatSnackBar`)**: For transient success/info messages (e.g., "Protocol Saved", "Asset Created").
* **Dialogs (`MatDialog`)**: For critical errors requiring user acknowledgement or complex interactions.

---

## 2. Type Mapping Strategy (Python -> Formly)

| Python Type | Formly Type | UI Component | Notes |
| :--- | :--- | :--- | :--- |
| `str` | `input` | `mat-input` | Standard text field. |
| `int` | `input` | `mat-input` type="number" | Integer validation. |
| `float` | `input` | `mat-input` type="number" | Decimal validation. |
| `bool` | `toggle` | `mat-slide-toggle` | For simple flags. |
| `bool` (alt) | `chips` | `mat-chip-listbox` | For "Enable/Disable" style selection. |
| `Enum` | `select` | `mat-select` | Dropdown. |
| `List[T]` | `repeat` | Custom Array Component | "Add/Remove" rows. |
| `List[Enum]` | `multiselect` | `mat-chip-grid` | Multi-select chips for concise display. |
| `Dict` | `json-editor` | Custom Key-Value Editor | Two inputs per row (Key, Value). |
| `Labware` | `asset-selector`| `mat-autocomplete` | Searchable dropdown querying `AssetService`. |
| `Machine` | `asset-selector`| `mat-autocomplete` | Searchable dropdown querying `AssetService`. |

---

## 3. Style System (Material 3)

### Color Palette (Scientific/Clean)

* **Primary**: Deep Blue / Indigo (Trust, Precision).
* **Secondary**: Teal / Cyan (Action, Progress).
* **Error**: Red (Critical Alerts).
* **Warning**: Amber (Non-blocking issues).
* **Success**: Green (Run complete).
* **Background**: Neutral Light Grey (`#FAFAFA`) to reduce eye strain.
* **Surface**: White (`#FFFFFF`) for cards and tables.

### Typography

* **Headings**: Roboto, Medium weight.
* **Body**: Roboto, Regular weight.
* **Monospace**: Roboto Mono (for logs, JSON, IDs).

### Component Guidelines

#### Cards (`mat-card`)

* Use `outlined` variant for data groupings to reduce visual noise.
* Use `elevated` variant only for draggable items or modal content.

#### Buttons (`mat-button`)

* **Primary Action**: `mat-flat-button` (Filled).
* **Secondary Action**: `mat-stroked-button` (Outlined).
* **Destructive Action**: `mat-button` (Text) with `color="warn"`.

#### Status Indicators

* **Icons**: Use generic status icons (Check, Warning, Error) with standardized colors.
* **Badges**: Small text badges for status columns in tables (e.g., "RUNNING" in green pill).

---

## 4. Implementation Priorities

1. **Shared Module Setup**: Export `MatTable`, `MatInput`, `MatSelect`, `MatAutocomplete`, `MatChips`, etc.
2. **Formly Config**: Register custom types (`asset-selector`, `repeat`, `chips`) in `app.config.ts`.
3. **Status Bar Component**: Create the global status bar in `MainLayout`.
4. **Asset Selectors**: Implement the `AssetService` lookup logic for the autocomplete components.

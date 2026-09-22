---
title: 'Inventory Wizard Redesign Spec'
---

# Inventory Wizard Redesign Spec

## Component Hierarchy

- **`AppAssetWizard`** (Main Container, Helper Dialog)
  - **`WizardHeader`** (Title, Close Button, Progress Indicator)
  - **`CategorySelectionStep`** (Step 1)
    - `CategoryCard` (Grid Item)
  - **`DefinitionBrowserStep`** (Step 2)
    - `SearchToolbar` (Search Input + Filter Chips)
    - `DefinitionGrid` (Responsive Grid)
      - `DefinitionCard` (Thumbnail, Title, Metadata)
    - `DefinitionEmptyState` (Create Simulation CTA)
  - **`ConfigurationStep`** (Step 3)
    - `ConfigurationForm` (Dynamic fields based on type)
  - **`ReviewStep`** (Step 4)
    - `AssetSummaryCard`

## Screen 1: Category Selection (Step 1)

**Visual Strategy:** A visually rich entry point that categorizes assets clearly. Using large, touch-friendly cards with icons and descriptions to guide the user (especially helpful for new users distinguishing between 'Machine' and 'Resource').

**Layout:**

- **Grid:** CSS Grid with `auto-fill` (min-width: 240px).
  - **Mobile:** 1 Column
  - **Tablet:** 2 Columns
  - **Desktop:** 3-4 Columns
- **Cards:**
  - **Machine:** Icon: `precision_manufacturing` or `smart_toy`
    - Label: "Machine"
    - Desc: "Liquid handlers, plate readers, centrifuges."
  - **Resource:** Icon: `science` or `inventory_2`
    - Label: "Resource"
    - Desc: "Labware, plates, tips, tubes."
- **Interaction:**
  - Cards have hover intent (elevation lift + border highlight).
  - Single click selects and auto-advances or reveals sub-category selection below (if expanded).
- **Sub-Category Selector:**
  - A visible list of chips (e.g., "Liquid Handler", "Plate Reader") appears when a Type is selected, allowing refinement *before* the next step.

## Screen 2: Definition Browser (Step 2)

**Visual Strategy:** A marketplace-like browsing experience. Focus on discoverability.

**Layout & Interactions:**

- **Search Bar:** Sticky top bar.
  - Full-width `mat-form-field` with "search" icon prefix.
  - **Autocomplete:** Suggestions based on vendor or common names.
- **Filter Bar:** Horizontal scrollable row of `mat-chip-listbox`.
  - Chips: `Simulated Only`, `Vendor: Hamilton`, `Type: 96-Well`, `Type: 384-Well`.
- **Definition Grid:**
  - **Card Design:**
    - **Asset Thumbnail:** (Placeholder or generated icon based on geometry).
    - **Header:** Definition Name (Bold), Vendor (Subtitle).
    - **Badge:** `Simulated` (Green), `Hardware` (Blue).
    - **Footer:** Dimensions (X/Y/Z) or Volume (µL).
  - **Empty State:**
    - Illustration (SVG).
    - Text: "No matching definitions found."
    - **CTA:** Primary Button "Create Custom Definition" (Triggers new side-dialog).
    - Secondary Link: "Import from PLR Library".

## Component Details

### `CategoryCard`

- **Props:** `icon: string`, `title: string`, `description: string`, `selected: boolean`
- **Styling:**
  - Border: 1px solid `var(--mat-sys-outline-variant)`
  - Background: `var(--mat-sys-surface-container-low)`
  - Selected State: Border `primary`, Background `primary-container` (low opacity).

### `DefinitionCard`

- **Props:** `definition: MachineDefinition | ResourceDefinition`
- **Dimensions:** Fixed height (~180px) to ensure uniform grid.
- **Content:**
  - Uses `text-overflow: ellipsis` for long names.
  - Vendor logo (if available) or text fallback.

## Animation & Transitions

- **Step Transition:** Slide-over effect (Material standard) or cross-fade.
- **Card Hover:** `transform: translateY(-2px); box-shadow: var(--mat-sys-elevation-level2); transition: all 0.2s ease-out;`
- **Selection:** Ripple effect on click.

## Theme Integration

- Uses standard Material Design 3 tokens:
  - Surface: `--mat-sys-surface`, `--mat-sys-surface-container`
  - On-Surface: `--mat-sys-on-surface`
  - Primary: `--mat-sys-primary`

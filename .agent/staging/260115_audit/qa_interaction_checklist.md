# QA Interaction Checklist

This checklist covers user-facing interactions across the PyLabPraxis web client. Use this to verify feature coverage during manual QA or when designing automated tests.

## 1. Setup (Assets & Machines)

**Context**: `/assets`

### 1.1 Navigation & Views

- [ ] **View Asset Dashboard**: Navigate to `/assets`. Verify "Overview" tab loads.
- [ ] **Switch Tabs**: Click "Spatial View", "Machines", "Resources", "Registry".
- [ ] **Asset Filters**: Use search bar or filter chips to filter lists.

### 1.2 Machine Management

- [ ] **Add Machine (Manual)**:
  - Click "Add Machine" (or "Add Asset" -> "Machine").
  - Enter Name, Type (e.g., Hamilton STAR), IP Address.
  - Submit and verify new machine appears in list.
- [ ] **Hardware Discovery**:
  - Click "Discover Hardware" button.
  - Verify dialog displays discovered devices (mock or real).
  - Select device and "Register".
- [ ] **Machine Status**: Verify status indicators (Idle, Busy, Error) reflect state.

### 1.3 Resource Management

- [ ] **Add Resource (Manual)**:
  - Click "Add Resource" (or "Add Asset" -> "Resource").
  - Select Resource Type (e.g., TipRack, Plate) and Definition.
  - Submit and verify new resource appears in list.
- [ ] **Sync Registry**:
  - Navigate to "Registry" tab.
  - Click "Sync Definitions" (if backend connected).

## 2. Protocol Configuration

**Context**: `/protocols`

### 2.1 Library Management

- [ ] **View Library**: Navigate to `/protocols`. Verify cards load.
- [ ] **Search/Filter**: Enter text in search; filter by Category/Author.
- [ ] **Upload Protocol**:
  - Click "Upload Protocol".
  - Drag & drop `.py` file.
  - Verify parsing success and card appearance.

### 2.2 Protocol Details

- [ ] **View Details**: Click a protocol card.
- [ ] **Verify Metadata**: Check Description, Author, Estimated Time are correct.

## 3. Execution (Run Protocol)

**Context**: `/run`

### 3.1 Step 1: Protocol Selection

- [ ] **Select Protocol**: Choose a protocol from the grid.
- [ ] **Simulation Toggle**: Toggle "Simulation Mode" on/off in top bar.
- [ ] **Verify Selection**: Confirm "Protocol Details" card appears.

### 3.2 Step 2: Parameters

- [ ] **Configure Inputs**: Enter values for defined protocol parameters (Int, Float, String, Boolean).
- [ ] **Validation**: Verify "Continue" is disabled if required fields are empty.

### 3.3 Step 3: Machine Selection

- [ ] **Select Machine**: Choose a compatible machine card.
- [ ] **Compatibility Check**: Verify incompatible machines are disabled/warned.
- [ ] **Simulation Override**: If in Physical mode but machine is Simulated, verify warning.

### 3.4 Step 4: Asset Selection

- [ ] **Auto-Match**: Verify system auto-selects available matching inventory.
- [ ] **Manual Override**: Change a selected asset (e.g., swap TipRack A for TipRack B).
- [ ] **Missing Asset Warning**: Verify warning if required asset type is missing.

### 3.5 Step 5: Well Selection (Conditional)

*Only if protocol requires specific well inputs.*

- [ ] **Open Selector**: Click "Select Wells" for a parameter.
- [ ] **Select Logic**: Click/Drag to select wells on grid.
- [ ] **Confirm**: Save selection and verify parameter is updated.

### 3.6 Step 6: Deck Setup (Conditional)

*Only if protocol requires deck interactions.*

- [ ] **Wizard Config**: Follow inline wizard steps to place items on deck.
- [ ] **Visualizer**: Verify deck map updates as items are placed.

### 3.7 Step 7: Review & Launch

- [ ] **Review Summary**: Check Protocol, Machine, Parameter values.
- [ ] **Run Metadata**: Enter "Run Name" and "Notes".
- [ ] **Start Run**: Click "Start Execution". Verify redirection to Monitor.

## 4. Execution Monitoring

**Context**: `/monitor` / `/running/:id`

### 4.1 Live Status

- [ ] **Progress Bar**: Verify progress bar advances.
- [ ] **Step Indicator**: Current active step is highlighted.
- [ ] **Live Deck View**: Deck visualization reflects current state (e.g., tip movement).

### 4.2 Control Interactions

- [ ] **Pause/Resume**: Click Pause -> Verify Sim/Machine stops. Click Resume -> Continues.
- [ ] **Stop/Cancel**: Click Stop -> Verify Run status changes to "Cancelled".

### 4.3 Logs & Data

- [ ] **Log Stream**: Verify "Console/Logs" panel updates with protocol output.
- [ ] **State Inspection**: Click "State" tab to view current Tip/Liquid state.

## 5. Analysis & History

**Context**: `/data` / `/history`

### 5.1 Run History

- [ ] **View List**: See table of past runs.
- [ ] **Filter Status**: Filter by "Completed", "Failed", "Cancelled".

### 5.2 Run Results

- [ ] **View Result**: Click a completed run.
- [ ] **Data Visualization**: Verify charts/graphs render for result data.
- [ ] **Export**: Click "Export Data" (CSV/JSON) if available.

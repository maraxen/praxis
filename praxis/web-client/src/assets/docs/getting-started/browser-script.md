# Praxis Demo Script

This script provides a step-by-step walkthrough of the Praxis platform in **Browser Mode**. It highlights key features including asset management, protocol execution, and live monitoring.

## Prerequisites

Ensure you have the application running in Browser Mode:

```bash
bun run start:browser
```

Open your browser to [http://localhost:4200](http://localhost:4200).

## 1. Dashboard Overview

**Goal**: Familiarize yourself with the main landing page.

1. **Landing**: You land on the **Home** dashboard.
2. **Quick Actions**: Notice the cards for "New Protocol Run", "Manage Assets", etc.
3. **Active Runs**: In Browser Mode, you might see 0 active runs initially.
4. **System Status**: Check the "System Health" widget (mocked) showing "Operational".

## 2. Asset Management

**Goal**: Explore the inventory of labware and machines.

### Resources (Labware)

1. Click **Assets** in the sidebar.
2. Switch to the **Resources** tab.
3. **Filter**: Type "Plate" in the search bar.
    * *Verify*: The list filters to show only plates.
4. **Inspect**: Click on a resource (e.g., "Corning 96 Well Plate").
    * *Observation*: A drawer opens with details like "Category: Plate", "Wells: 96", "Volume: 300uL".

### Machines

1. Switch to the **Machines** tab.
2. **View List**: You should see pre-seeded machines like "Opentrons Flex" and "Hamilton STAR".
3. **Status**: Notice their status is currently "IDLE" or "OFFLINE".
4. **Add Machine** (Simulation):
    * Click **+ Add Machine**.
    * Enter random details.
    * *Note*: In browser-only mode, this will persist to local storage only.

## 3. Protocol Execution

**Goal**: Setup and run a liquid handling experiment.

### Step 1: Selection

1. Navigate to **Protocols**.
2. You will see a card view of available protocols.
3. Click **Run** on the **"Simple Liquid Transfer"** protocol.
4. **Parameter Configuration**:
    * Leave the default parameter (e.g., `num_samples`).
    * Click **Next**.

### Step 2: Deck Setup (Guided)

1. You are now in the **Deck Setup** wizard.
2. **Visualizer**: You see a 2D/3D representation of the deck (e.g., standard ANSI/SLAS deck).
3. **Missing Assets**: The wizard highlights that "Source Plate" and "Dest Plate" are required.
4. **Assignment**:
    * Click on the highlighted **Source Plate** slot.
    * Select "Corning 96 Well Plate" from the dropdown.
    * Repeat for **Dest Plate** and **Tip Rack**.
5. **Validation**: Once all required assets are placed, the "Next" button becomes active.
6. Click **Next**.

### Step 3: Review & Run

1. **Summary**: Review the configuration.
2. **Mode**: Ensure "Simulation" is checked (default in demo).
3. **Execute**: Click **Start Run**.

## 4. Execution Monitoring

**Goal**: Monitor the live progress of the experiment.

1. **Redirect**: You are automatically redirected to the **Execution Monitor**.
2. **Live Visuals**:
    * **Timeline**: Watch the progress bar advance.
    * **Logs**: See real-time log entries appearing (e.g., "Aspirating 50uL from Well A1").
    * **Status**: Indicates "RUNNING".
3. **Interactivity**:
    * Click **Pause**. The timeline stops.
    * Click **Resume**. The timeline continues.
4. **Completion**:
    * Wait for the run to finish (progress 100%).
    * Status changes to "COMPLETED".

## 5. History & Analysis

1. Navigate to **Runs** (History).
2. You should see your newly completed run at the top of the list.
3. Click it to view the **Run Report**.
    * See total duration, errors (if any), and the full log transcript.

---

## Conclusion

You have successfully navigated the core lifecycle of a Praxis experiment: **Setup -> Run -> Monitor -> Analyze**.

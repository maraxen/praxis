# Protocols

Protocols are the core of Praxis - Python scripts that define automated laboratory workflows.

## What is a Protocol?

A protocol is a Python function decorated with `@protocol` that describes a sequence of laboratory operations:

```python
from praxis import protocol, PraxisRunContext

@protocol(
    name="Simple Transfer",
    description="Transfer liquid from source to destination plate",
    parameters={
        "volume": {"type": "float", "default": 100, "min": 1, "max": 1000},
        "wells": {"type": "int", "default": 96, "options": [8, 24, 96, 384]}
    }
)
async def simple_transfer(ctx: PraxisRunContext):
    lh = ctx.get_machine("liquid_handler")
    source = ctx.get_resource("source_plate")
    dest = ctx.get_resource("dest_plate")
    tips = ctx.get_resource("tip_rack")

    await lh.pick_up_tips(tips["A1:H1"])
    await lh.aspirate(source["A1:H1"], volume=ctx.params["volume"])
    await lh.dispense(dest["A1:H1"], volume=ctx.params["volume"])
    await lh.discard_tips()

    return {"transferred": ctx.params["wells"]}
```

## Protocol Library

### Browsing Protocols

Navigate to **Protocols** in the sidebar to see all available protocols.

Features:

- **Search**: Find protocols by name or description
- **Filter**: Filter by category, author, or status
- **Sort**: Sort by name, date created, or last run
- **Cards**: Each protocol shows key info at a glance

### Protocol Details

Click a protocol to see its full details:

- **Description**: What the protocol does
- **Parameters**: Configurable inputs with types and constraints
- **Requirements**: Required machines and resources
- **History**: Past execution runs
- **Code**: View the Python source (if authorized)

## Running a Protocol

### The 7-Step Wizard

Click **Run Protocol** to launch the execution wizard:

#### Step 1: Select Protocol

Choose which protocol to run:

- Browse the protocol library
- Search by name or category
- View protocol details and parameters

#### Step 2: Configure Parameters

Configure the protocol inputs:

- Fill in required parameters
- Adjust optional parameters as needed
- See validation errors in real-time

#### Step 3: Select Machines

Assign hardware:

- See required machine types
- Select from connected machines
- Check status (must be IDLE)
- View connection info

#### Step 4: Select Assets

Select labware and resources:

- See required resource types
- Select from available inventory
- Filter by category or properties
- Check quantities for consumables

#### Step 5: Select Wells *(conditional)*

Choose target wells on plates:

- Interactive well grid selector
- Select individual wells or ranges
- Only shown when the protocol requires well selection

#### Step 6: Deck Setup *(conditional)*

Configure the deck layout:

- Assign resources to deck positions
- Optional when the protocol does not require a deck (`requires_deck === false`)

#### Step 7: Review & Run

Confirm and execute:

- Review all selections
- Toggle **Simulation Mode** to dry-run without hardware
- Click **Run** to start
- Or **Schedule** for later

### Execution Monitor

Once running, the monitor shows:

| Panel | Information |
|-------|-------------|
| **Progress** | Current step, percentage complete |
| **Logs** | Real-time log stream |
| **Deck View** | Visual representation of the deck |
| **Controls** | Pause, Resume, Cancel buttons |

### Simulation Mode

Toggle **Simulation** to run without actual hardware:

- All commands are logged but not executed
- Useful for testing and validation
- No risk to real samples
- Faster execution

## Protocol Discovery

Praxis automatically discovers protocols from Python files.

### How Discovery Works

1. Backend scans configured protocol directories
2. Python files are parsed using AST
3. Functions with `@protocol` decorator are extracted
4. Metadata is stored in the database

### Syncing Protocols

To sync new or updated protocols:

**Via API:**

```bash
curl -X POST http://localhost:8000/api/v1/discovery/sync-all
```

**Via UI:**

1. Navigate to **Protocols**
2. Click the **Sync** button

### Protocol Organization

Organize protocols in directories:

```
protocols/
├── transfers/
│   ├── simple_transfer.py
│   ├── serial_dilution.py
│   └── plate_replication.py
├── assays/
│   ├── elisa_setup.py
│   └── pcr_prep.py
└── maintenance/
    ├── deck_wash.py
    └── tip_inventory.py
```

## Writing Protocols

### Basic Structure

```python
from praxis import protocol, PraxisRunContext

@protocol(
    name="My Protocol",
    description="What this protocol does",
    category="Transfers",
    author="Your Name",
    version="1.0.0",
    parameters={...},
    requirements={
        "machines": ["liquid_handler"],
        "resources": ["plate", "tip_rack"]
    }
)
async def my_protocol(ctx: PraxisRunContext):
    # Your protocol logic here
    pass
```

### Parameters

Define configurable inputs:

```python
parameters={
    # Basic types
    "volume": {"type": "float", "default": 100},
    "count": {"type": "int", "required": True},
    "name": {"type": "str", "default": "Sample"},
    "enabled": {"type": "bool", "default": True},

    # With constraints
    "temperature": {
        "type": "float",
        "min": 4,
        "max": 95,
        "default": 37,
        "unit": "°C"
    },

    # With options
    "plate_type": {
        "type": "str",
        "options": ["96-well", "384-well"],
        "default": "96-well"
    }
}
```

### Accessing Resources

```python
async def my_protocol(ctx: PraxisRunContext):
    # Get machines by role
    lh = ctx.get_machine("liquid_handler")
    reader = ctx.get_machine("plate_reader")

    # Get resources by role
    source = ctx.get_resource("source_plate")
    dest = ctx.get_resource("dest_plate")
    tips = ctx.get_resource("tip_rack")

    # Access wells
    source_wells = source["A1:H12"]  # All 96 wells
    first_column = source["A1:H1"]   # First column
    single_well = source["A1"]       # Single well
```

### Logging and Progress

```python
async def my_protocol(ctx: PraxisRunContext):
    ctx.log("Starting transfer...")

    for i, well in enumerate(wells):
        ctx.log(f"Processing well {well}")
        ctx.set_progress(i + 1, len(wells))
        # ... process well

    ctx.log("Transfer complete!")
```

### Returning Data

```python
async def my_protocol(ctx: PraxisRunContext) -> dict:
    results = []

    for well in wells:
        reading = await reader.measure(well)
        results.append({"well": well, "value": reading})

    # Return structured data
    return {
        "readings": results,
        "mean": sum(r["value"] for r in results) / len(results),
        "timestamp": datetime.now().isoformat()
    }
```

### Error Handling

```python
async def my_protocol(ctx: PraxisRunContext):
    try:
        await lh.pick_up_tips(tips["A1:H1"])
    except NoTipsError:
        ctx.log("No tips available, trying backup rack", level="WARNING")
        await lh.pick_up_tips(backup_tips["A1:H1"])

    # Protocol-level errors
    if volume < 1:
        raise ProtocolError("Volume too low for accurate transfer")
```

## Best Practices

### 1. Use Descriptive Names

```python
# Good
@protocol(name="96-Well Serial Dilution (1:2)")

# Bad
@protocol(name="Protocol 1")
```

### 2. Document Parameters

```python
parameters={
    "dilution_factor": {
        "type": "float",
        "default": 2,
        "description": "Fold dilution for each step (e.g., 2 = 1:2 dilution)"
    }
}
```

### 3. Validate Early

```python
async def my_protocol(ctx: PraxisRunContext):
    # Validate at the start
    if ctx.params["volume"] > tips.max_volume:
        raise ProtocolError(
            f"Volume {ctx.params['volume']}µL exceeds tip capacity "
            f"({tips.max_volume}µL)"
        )

    # Then proceed
    ...
```

### 4. Log Key Steps

```python
ctx.log(f"Transferring {volume}µL from {source.name} to {dest.name}")
ctx.log(f"Using tips from {tips.name} (remaining: {tips.quantity})")
```

### 5. Handle Cleanup

```python
async def my_protocol(ctx: PraxisRunContext):
    try:
        await lh.pick_up_tips(tips["A1:H1"])
        await lh.aspirate(source["A1:H1"], volume)
        await lh.dispense(dest["A1:H1"], volume)
    finally:
        # Always discard tips
        if lh.has_tips:
            await lh.discard_tips()
```

---

## See Also

- [Protocol Inference Sharp Bits](./protocol-inference-sharp-bits.md) - Edge cases, gotchas, and limitations of the protocol inference system
- [Data Visualization](./data-visualization.md) - Using `@data_view` decorators
- [Hardware Discovery](./hardware-discovery.md) - Connecting machines
- [Assets](./assets.md) - Managing resources and machines

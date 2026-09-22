# Assets

Assets in Praxis are the physical items in your lab - machines (instruments) and resources (labware and consumables).

## Asset Types

### Machines

Laboratory instruments that perform operations:

| Type | Examples |
|------|----------|
| **Liquid Handlers** | Opentrons Flex, Hamilton STAR, Tecan EVO |
| **Plate Readers** | BMG CLARIOstar, Molecular Devices SpectraMax |
| **Incubators** | Liconic StoreX, Inheco ODTC |
| **Sealers/Peelers** | Agilent PlateLoc, Brooks XPeel |
| **Washers** | BioTek 405 LS, Tecan HydroFlex |

### Resources

Labware and consumable items:

| Type | Examples |
|------|----------|
| **Plates** | 96-well, 384-well, deep well, PCR plates |
| **Tip Racks** | 20µL, 200µL, 1000µL tips |
| **Reservoirs** | Single-channel, multi-channel troughs |
| **Tubes** | Microcentrifuge tubes, falcon tubes |
| **Consumables** | Reagents, buffers, samples |

## Managing Assets

Navigate to **Assets** in the sidebar.

### Machines Tab

View and manage your lab instruments:

- **Status indicators**: IDLE (green), RUNNING (blue), OFFLINE (gray)
- **Connection info**: IP address, port, driver type
- **Actions**: Connect, disconnect, configure

### Resources Tab

Organized by category with accordion groups:

- **Plates**: Microplates of various formats
- **Tip Racks**: Pipette tips organized by volume
- **Reservoirs**: Reagent troughs and containers
- **Other**: Miscellaneous labware

### Definitions Tab

Browse PyLabRobot type definitions:

- Pre-defined labware from PLR library
- Machine type definitions
- Use as templates when adding new assets

## Adding Assets

### Add a Machine

1. Click **Add Machine**
2. Select a PLR definition (optional but recommended)
3. Fill in details:
   - **Name**: Friendly identifier (e.g., "Main Liquid Handler")
   - **Model**: Hardware model
   - **Manufacturer**: Vendor name
   - **Status**: Initial status (usually OFFLINE)
   - **Connection Info**: JSON with connection details

Example connection info:
```json
{
  "host": "192.168.1.100",
  "port": 31950,
  "driver": "opentrons_flex"
}
```

### Add a Resource

1. Click **Add Resource**
2. Select a PLR definition
3. Fill in details:
   - **Name**: Friendly identifier
   - **Category**: Plate, TipRack, Reservoir, etc.
   - **Properties**: Consumable, reusable, quantity

### Hardware Discovery

Automatically detect connected devices:

1. Click **Discover Hardware**
2. Grant browser permissions for WebSerial/WebUSB
3. Click **Scan All** or select specific types
4. Review detected devices
5. Click **Register as Machine** to add

## Asset Properties

### Common Properties

All assets have:

| Property | Description |
|----------|-------------|
| **Accession ID** | Unique identifier (auto-generated) |
| **Name** | Human-readable name |
| **FQN** | Fully Qualified Name in PLR (e.g., `opentrons.Flex`) |
| **Status** | Current availability state |

### Machine Properties

| Property | Description |
|----------|-------------|
| **Connection Info** | How to connect (host, port, driver) |
| **PLR State** | Serialized PyLabRobot object state |
| **Capabilities** | What the machine can do |

### Resource Properties

| Property | Description |
|----------|-------------|
| **Category** | Type of labware (Plate, TipRack, etc.) |
| **Consumable** | Whether it gets used up |
| **Quantity** | Amount remaining (for consumables) |
| **Location** | Where on the deck |

## Asset Status

### Machine States

| Status | Meaning |
|--------|---------|
| `IDLE` | Available for use |
| `RUNNING` | Currently executing a protocol |
| `MAINTENANCE` | Under maintenance, not available |
| `OFFLINE` | Not connected |
| `ERROR` | Connection or hardware error |

### Resource States

| Status | Meaning |
|--------|---------|
| `AVAILABLE` | Can be used |
| `IN_USE` | Currently in a protocol |
| `DEPLETED` | Consumable exhausted |
| `RESERVED` | Reserved for scheduled run |

## Filtering and Search

### Chip-Based Filtering

Click chips to filter by:

- **Category**: Plate, TipRack, Reservoir
- **Properties**: Consumable, Reusable
- **Status**: Available, In Use

### Search

Type in the search box to filter by:

- Name
- Description
- Accession ID

## Asset in Protocol Execution

### Selection During Run

When running a protocol:

1. **Requirements shown**: Protocol declares what it needs
2. **Available assets listed**: Only compatible, available items shown
3. **Validation**: Checks quantities, status, compatibility

### Automatic Allocation

For scheduled runs:

1. Assets are reserved at scheduling time
2. Locks prevent double-booking
3. Resources released after completion

### Quantity Tracking

For consumables like tips:

1. Initial quantity set when added
2. Decremented after protocol use
3. Alerts when running low
4. Can manually adjust quantities

## PLR Integration

### Understanding FQN

The Fully Qualified Name (FQN) links assets to PyLabRobot types:

```
pylabrobot.resources.corning_costar.Cos_96_EZWash
├── pylabrobot.resources  → PLR module
├── corning_costar        → Submodule
└── Cos_96_EZWash         → Class name
```

### Factory Functions

Some PLR types use factory functions:

```python
# FQN: pylabrobot.resources.corning.Cos_96_PCR_Skirted
# This is a factory function that returns a configured Plate
```

### Backend/Frontend Types

For machines:

- **Frontend**: Abstract interface (e.g., `LiquidHandler`)
- **Backend**: Specific driver (e.g., `OpentronsBackend`)

When adding machines, select the frontend type. The backend is configured via connection info.

## Best Practices

### 1. Use Meaningful Names

```
Good: "Main Flex - Bay 1"
Bad: "LH1"
```

### 2. Keep Status Updated

- Mark machines OFFLINE when disconnecting
- Set MAINTENANCE during calibration
- Update quantities after manual changes

### 3. Organize by Location

Include location in names or use properties:

```
"Flex - Room 123 Bay A"
"Tip Rack - Drawer 2B"
```

### 4. Track Consumables

- Set initial quantities when adding
- Check before long runs
- Set up low-quantity alerts

### 5. Regular Audits

- Periodically verify inventory
- Remove outdated entries
- Update connection info as needed

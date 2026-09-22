# Protocol Inference: Sharp Bits & Gotchas

This document covers edge cases, limitations, and best practices for working with Praxis's automatic protocol inference system. Understanding these "sharp bits" will help you write protocols that are correctly analyzed and avoid common pitfalls.

## Overview

Praxis uses **static analysis** (powered by LibCST) to infer:

- Resource requirements from type hints
- Machine capability requirements from method calls
- Deck layout preconditions
- Execution order and dependencies

This approach is fast and doesn't require running your code, but it has inherent limitations that you should be aware of.

---

## Type Inference Limitations

### When Explicit Types Are Needed

The inference system relies on **type hints** to understand your protocol's requirements. Without proper type hints, resources may not be detected.

**❌ Problem: Missing type hints**

```python
@protocol_function
async def my_protocol(plate, tips):  # No type hints!
    lh = get_liquid_handler()
    await lh.aspirate(plate["A1"])
```

**✅ Solution: Always use type hints**

```python
@protocol_function
async def my_protocol(plate: Plate, tips: TipRack):
    lh = get_liquid_handler()
    await lh.aspirate(plate["A1"])
```

### Complex Generic Types

The parser handles common generic patterns but may struggle with deeply nested or unusual generic types.

**✅ Supported generic patterns:**

```python
# Simple container types
wells: list[Well]
tips: Sequence[TipSpot]
plates: tuple[Plate, Plate]

# Optional types
plate: Plate | None
plate: Optional[Plate]
```

**⚠️ May not parse correctly:**

```python
# Deeply nested generics
items: dict[str, list[tuple[Well, int]]]  # Only outer container detected

# Complex union types with multiple containers
resources: list[Well] | list[TipSpot]  # May detect only first type

# Type variables and forward references
T = TypeVar('T', bound=Resource)
def my_func(resource: T) -> T:  # Type variable not resolved
```

### Union Types Handling

Union types are supported, but with some caveats:

```python
# ✅ Works: Simple Optional
plate: Plate | None

# ✅ Works: Union of resource types (first match extracted)
source: Plate | TipRack

# ⚠️ Gotcha: All types in the union should be resources
# Non-resource types in unions are filtered out
input: str | Plate  # Only "Plate" is detected
```

### Forward References and String Annotations

Forward references (string annotations) are parsed via regex pattern matching:

```python
# ✅ Works: Forward references for known PLR types
plate: "Plate"
wells: "list[Well]"

# ⚠️ Gotcha: Custom class names are NOT detected
my_container: "MyCustomWellContainer"  # Not recognized as a resource
```

**Known PLR types** that are recognized:

- `Well`, `TipSpot`, `Spot`, `Tube`
- `Plate`, `TipRack`, `Trough`, `TubeRack`, `Container`
- `PlateCarrier`, `TipCarrier`, `TroughCarrier`, `Carrier`
- `Deck`, `Slot`, `Resource`, `Lid`

---

## Resource Hierarchy Assumptions

### How Parent Resources Are Inferred

The system uses a **static hierarchy registry** to understand parent-child relationships:

```
Well → Plate → PlateCarrier → Deck  (carrier-based decks like Hamilton STAR)
Well → Plate → Slot → Deck          (slot-based decks like OT-2)
```

This means:

- If your protocol uses `Well`, it automatically requires a `Plate` on deck
- The system doesn't need—and can't see—runtime instances

### Deck Layout Type Detection

The deck layout type is inferred from the deck class name:

```python
# Detected as SLOT_BASED (OT-2 style):
# - "otdeck", "opentrons", "ot-2", "ot2", "flex"

# Detected as CARRIER_BASED (Hamilton style):
# - "hamilton", "star", "nimbus", "vantage", "tecan", "beckman"
```

**⚠️ Gotcha:** If your deck class doesn't match these patterns, it defaults to `CARRIER_BASED`.

### When Explicit Parent Hints Are Needed

The static registry handles standard PLR types. For custom resources:

```python
# ⚠️ Problem: Custom resource type not recognized
my_wells: list[CustomWell]  # Unknown hierarchy

# ✅ Solution: Use standard PLR types as base classes
# Or use decorator hints (see "Best Practices" section)
```

### Itemized Resource Child Detection

When accessing children of containers, the system infers types based on patterns:

```python
# ✅ Correctly inferred:
plate: Plate
wells = plate["A1:H1"]  # Inferred as list[Well]
well = plate["A1"]      # Inferred as Well

# ✅ Also works:
wells = plate.wells()   # Inferred as list[Well]

# ⚠️ Not inferred for unknown container types:
my_container: CustomContainer
items = my_container["A1:H1"]  # Type unknown
```

---

## Sequences and Container Type Handling

### `list[Well]` vs `Sequence[Well]`

Both are handled equivalently in most cases:

```python
# These are treated the same for resource detection:
wells: list[Well]
wells: Sequence[Well]
wells: tuple[Well, ...]
```

**⚠️ Gotcha:** The `collections.abc.Sequence` and `typing.Sequence` are both recognized, but if you use a custom `Sequence` subclass, it may not be detected.

### Nested Container Types

Nested containers are partially supported:

```python
# ✅ Works: First level extracted
all_wells: list[list[Well]]  # "Well" is detected

# ⚠️ Gotcha: Only first PLR type in complex nesting
data: dict[str, list[Well]]  # "Well" detected (dict values checked)
```

### Variable-Length Sequences

Variable-length annotations are supported:

```python
# ✅ Works:
wells: tuple[Well, ...]  # Arbitrary number of wells
plates: list[Plate]      # Any number of plates

# ✅ Also works:
items: tuple[Plate, TipRack]  # First PLR type extracted (Plate)
```

---

## Known Unsupported Patterns

### Dynamic Type Construction

Static analysis cannot handle runtime-determined types:

```python
# ❌ Not detectable:
@protocol_function
async def my_protocol(resource_type: str):
    ResourceClass = get_class_by_name(resource_type)
    resource: ResourceClass = create_resource()  # Type unknown at analysis time
```

### Dynamically Created Resources

Resources created at runtime from external data aren't detected:

```python
# ❌ Not detectable:
@protocol_function  
async def my_protocol(config: dict):
    plates = [Plate(name=c["name"]) for c in config["plates"]]
    # Number and type of plates unknown until runtime
```

### Conditional Resource Usage

Resources used only in conditional branches are detected, but the conditionality isn't captured:

```python
# ⚠️ Partial support:
@protocol_function
async def my_protocol(plate: Plate, backup_plate: Plate, use_backup: bool):
    if use_backup:
        await lh.aspirate(backup_plate["A1"])
    else:
        await lh.aspirate(plate["A1"])
    # Both plates are marked as required, 
    # even though only one is used at runtime
```

The system sets `has_conditionals: True` in the computation graph, but doesn't model conditional resource requirements.

### Loop-Dependent Quantities

Loop iterations aren't evaluated:

```python
# ⚠️ Detected but not fully modeled:
@protocol_function
async def my_protocol(plates: list[Plate], tip_rack: TipRack):
    for i, plate in enumerate(plates):
        await lh.pick_up_tips(tip_rack[f"A{i+1}"])
        await lh.transfer(plate["A1"], plate["B1"])
        await lh.drop_tips()
    # The system knows there's a loop, but doesn't know
    # how many tips will be used
```

The system sets `has_loops: True` in the computation graph for informational purposes.

### Method Calls on Non-Standard Receivers

Machine type is inferred from variable naming patterns. Non-standard names aren't recognized:

```python
# ✅ Recognized variable names:
lh  / liquid_handler  → liquid_handler
pr  / plate_reader / reader → plate_reader
hs  / heater_shaker → heater_shaker
cf  / centrifuge → centrifuge
tc  / thermocycler → thermocycler

# ❌ Not recognized:
robot.aspirate(...)  # "robot" isn't a known pattern
hamilton.pick_up_tips(...)  # "hamilton" isn't in the pattern list
```

### Async Context Managers

Resources obtained from async context managers may not be tracked:

```python
# ⚠️ May not be fully tracked:
async with get_plate_reader() as pr:
    await pr.read_absorbance(plate)
```

---

## Workarounds for Unsupported Patterns

### Use Explicit Parameters

Instead of dynamic resources, use explicit typed parameters:

```python
# ❌ Dynamic (not detectable):
@protocol_function
async def my_protocol(num_plates: int):
    plates = [Plate(name=f"plate_{i}") for i in range(num_plates)]

# ✅ Explicit (fully detected):
@protocol_function
async def my_protocol(plate1: Plate, plate2: Plate, plate3: Plate):
    plates = [plate1, plate2, plate3]
```

### Use Standard Variable Names

Stick to recognized machine variable naming conventions:

```python
# ✅ Good - uses recognized patterns:
lh = ctx.get_machine("liquid_handler")   # "lh" recognized
pr = ctx.get_machine("plate_reader")     # "pr" recognized

# ❌ Avoid - not recognized:
robot = ctx.get_machine("liquid_handler")  # Machine type not inferred
```

### Pre-Declare Variables with Type Hints

If you must create resources dynamically, pre-declare with type hints:

```python
@protocol_function
async def my_protocol(config: dict):
    wells: list[Well] = []  # Type hint helps inference
    for well_name in config["wells"]:
        wells.append(plate[well_name])
```

---

## Best Practices

### 1. Use Explicit Type Hints on All Parameters

```python
# ✅ Perfect - every parameter typed:
@protocol_function
async def transfer_protocol(
    source_plate: Plate,
    dest_plate: Plate,
    tips: TipRack,
    volume: float = 100.0,
    mix_cycles: int = 3,
) -> dict[str, Any]:
    ...
```

### 2. Use Standard PLR Types

Prefer standard PyLabRobot types over custom subclasses when possible:

```python
# ✅ Good - standard types:
plate: Plate
tips: TipRack

# ⚠️ May not work:
plate: MyCustomPlate96Well  # Custom types not in registry
```

### 3. Use Recognized Machine Variable Names

```python
# ✅ Good:
lh = ctx.get_machine("liquid_handler")  # or liquid_handler, hamilton
pr = ctx.get_machine("plate_reader")    # or plate_reader, reader
hs = ctx.get_machine("heater_shaker")   # or heater_shaker
tc = ctx.get_machine("thermocycler")    # or thermocycler

# ❌ Avoid:
robot = ctx.get_machine("liquid_handler")
my_lh = ctx.get_machine("liquid_handler")  # Prefix breaks detection
```

### 4. Keep Resource Access Simple

```python
# ✅ Easy to analyze:
wells = plate["A1:H1"]
await lh.aspirate(wells)

# ⚠️ Harder to track:
await lh.aspirate(get_wells_from_config(config)["filtered"])
```

### 5. Avoid Deeply Nested Generics

```python
# ✅ Simple and clear:
plates: list[Plate]
wells: list[Well]

# ⚠️ Complex - may lose some info:
plate_mapping: dict[str, dict[str, list[Well]]]
```

### 6. Document Edge Cases in Docstrings

If your protocol uses patterns that static analysis can't fully capture, document the actual requirements:

```python
@protocol_function
async def dynamic_protocol(config: dict):
    """Transfer protocol with dynamic plate count.
    
    Note: This protocol requires between 2-8 plates depending
    on config["plate_count"]. Static analysis will only detect
    the base resource types, not the quantity.
    
    Runtime Requirements:
    - Plates: config["plate_count"] (2-8)
    - TipRack: 1 box of 96 tips
    """
    ...
```

---

## Common Mistakes to Avoid

### 1. Forgetting Type Hints

```python
# ❌ Resources not detected:
async def bad_protocol(plate, tips):
    ...

# ✅ Resources properly detected:
async def good_protocol(plate: Plate, tips: TipRack):
    ...
```

### 2. Using Non-Standard Variable Names for Machines

```python
# ❌ Capabilities not inferred:
robot = ctx.get_machine("liquid_handler")
await robot.aspirate(wells)  # "robot" not recognized

# ✅ Capabilities properly inferred:
lh = ctx.get_machine("liquid_handler")  
await lh.aspirate(wells)  # "lh" → liquid_handler
```

### 3. Assuming All Conditional Paths Are Modeled

```python
# ⚠️ Both resources marked as required regardless of condition:
async def protocol(mode: str, plate_a: Plate, plate_b: Plate):
    if mode == "a":
        use_plate(plate_a)  # Both plates are...
    else:
        use_plate(plate_b)  # ...marked as required
```

### 4. Expecting Runtime Values in Static Analysis

```python
# ⚠️ Static analysis can't know len(plates):
async def protocol(plates: list[Plate]):
    for plate in plates:  # Iteration count unknown
        process(plate)
```

---

## Troubleshooting Guide

### "Resource Not Detected"

1. **Check type hints** - Is the parameter properly annotated?
2. **Check type name** - Is it a recognized PLR type (`Plate`, `Well`, etc.)?
3. **Check import** - Is the type imported from `pylabrobot.resources`?

### "Machine Capabilities Not Inferred"

1. **Check variable name** - Are you using a recognized pattern (`lh`, `pr`, etc.)?
2. **Check method calls** - Are you calling known capability methods?

### "Deck Layout Incorrect"

1. **Check deck class name** - Does it match known patterns (OT-2, Hamilton)?
2. **Check resource types** - Are they recognized container types?

### "Computation Graph Missing Operations"

1. **Check async/await** - Are machine calls wrapped with `await`?
2. **Check receiver** - Is the method called on a machine variable?
3. **Check scope** - Is the method call at the top level of the function?

---

## Technical Reference

### Recognized Variable Patterns for Machine Detection

| Variable Pattern | Inferred Machine Type |
|------------------|----------------------|
| `lh`, `liquid_handler` | `liquid_handler` |
| `pr`, `plate_reader`, `reader` | `plate_reader` |
| `hs`, `heater_shaker` | `heater_shaker` |
| `shaker` | `shaker` |
| `cf`, `centrifuge` | `centrifuge` |
| `tc`, `thermocycler` | `thermocycler` |
| `incubator` | `incubator` |

### Methods That Imply Capability Requirements

| Method | Inferred Capability |
|--------|---------------------|
| `aspirate_submerge_swap` | `has_core96: True` |
| `dispense_submerge_swap` | `has_core96: True` |
| `get_plate`, `put_plate`, `move_lid` | `has_iswap: True` |
| `read_absorbance` | `absorbance: True` |
| `read_fluorescence` | `fluorescence: True` |
| `read_luminescence` | `luminescence: True` |

### Resource Hierarchy (Carrier-Based Decks)

```
Well/TipSpot/Tube → Container (Plate/TipRack/TubeRack) → Carrier → Deck
```

### Resource Hierarchy (Slot-Based Decks)

```
Well/TipSpot/Tube → Container (Plate/TipRack/TubeRack) → Slot → Deck
```

---

## See Also

- [Protocols Guide](./protocols.md) - General protocol writing guide
- [Data Visualization](./data-visualization.md) - Using `@data_view` decorators
- [Hardware Discovery](./hardware-discovery.md) - Connecting machines

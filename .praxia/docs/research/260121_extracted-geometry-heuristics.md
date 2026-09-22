# Extracted Geometry Heuristics Code (TD-702)

This report documents the extracted geometry heuristics implementation and fixes from Jules session `16235462376134233538` (Fix Geometry Heuristics in web_bridge.py).

## 1. Implementation Details

The implementation enhances `read_plate_data_visualization` in `praxis/backend/services/plate_viz.py` to dynamically determine plate geometry based on the associated resource definition.

### Changes to `praxis/backend/services/plate_viz.py`

```python
# Added import
from praxis.backend.services.resource import resource_service

# Enhanced plate layout detection logic
async def read_plate_data_visualization(
    db: AsyncSession,
    plate_resource_accession_id: uuid.UUID,
    data_type: DataOutputTypeEnum,
) -> Optional[PlateDataVisualization]:
    # ... (existing data fetching) ...

    # Get plate information
    resource = await resource_service.get(db, plate_resource_accession_id)
    plate_layout = {"rows": 8, "columns": 12, "total_wells": 96, "format": "96-well"}
    
    if resource and resource.resource_definition and resource.resource_definition.definition:
        try:
            # Safely extract dimensions from resource definition
            definition = resource.resource_definition.definition
            num_items_x = definition.get("num_items_x")
            num_items_y = definition.get("num_items_y")
            
            if num_items_x and num_items_y:
                plate_layout = {
                    "rows": num_items_y,
                    "columns": num_items_x,
                    "total_wells": num_items_x * num_items_y,
                    "format": f"{num_items_x * num_items_y}-well",
                }
        except (AttributeError, KeyError) as e:
            logger.warning(
                "Could not parse plate geometry from resource definition for plate "
                f"{plate_resource_accession_id}. Error: {e}",
            )
    
    # ... (rest of the function) ...
```

## 2. Test Verification

Added comprehensive test coverage in `tests/services/test_plate_viz.py` to verify the new logic.

### New Test Cases

- **Case 1**: Plate with defined geometry (e.g., 384-well, 24x16).
- **Case 2**: Plate with no definition (fallback to 96-well).

```python
@pytest.mark.asyncio
@patch("praxis.backend.services.plate_viz.resource_service", new_callable=AsyncMock)
async def test_read_plate_data_visualization_with_geometry(
    mock_resource_service: AsyncMock,
    mock_db_session: AsyncMock,
) -> None:
    # (Setup mock data and relationships)
    
    # Case 1: Plate with defined geometry (384-well)
    resource_def_384 = ResourceDefinitionOrm(
        definition={"num_items_x": 24, "num_items_y": 16},
    )
    # ...
    assert result_384.plate_layout["rows"] == 16
    assert result_384.plate_layout["columns"] == 24
    assert result_384.plate_layout["format"] == "384-well"

    # Case 2: Fallback
    # ...
    assert result_96.plate_layout["format"] == "96-well"
```

## 3. Key Findings

- **Safe Parsing**: Uses `.get()` on the definition dictionary to avoid `KeyError` on non-standard labware definitions.
- **Improved Fallback**: Decouples visualization from a hardcoded 96-well format, allowing the system to handle 384-well and bespoke formats if they are defined in the metadata.
- **Service Dependency**: Introducing `resource_service` into `plate_viz` adds a dependency but correctly centralizes the "truth" about labware geometry.

"""Browser stub for praxis.protocol.protocols.plate_reader_assay module.

This includes ALL functions from the backend that cloudpickle may reference
during protocol deserialization and execution.
"""

from pylabrobot.resources import Plate


def plate_reader_assay(*args, **kwargs):
    """Stub - actual function comes from pickle."""
    pass


def _parse_well_selection(selection: str, plate: Plate) -> list[str]:
    """Parse a well selection string into a list of well positions.

    Supports formats:
    - Range: 'A1:H12' (rectangle selection)
    - List: 'A1,B2,C3' (specific wells)
    - Column: 'A1:A8' (single column)
    - Row: 'A1:H1' (single row)
    """
    wells = []

    if ":" in selection and "," not in selection:
        # Range selection
        start, end = selection.split(":")
        start_row, start_col = start[0], int(start[1:])
        end_row, end_col = end[0], int(end[1:])

        for row_ord in range(ord(start_row), ord(end_row) + 1):
            for col in range(start_col, end_col + 1):
                wells.append(f"{chr(row_ord)}{col}")
    elif "," in selection:
        # List selection
        wells = [w.strip() for w in selection.split(",")]
    else:
        # Single well
        wells = [selection.strip()]

    return wells

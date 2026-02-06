"""Browser stub for praxis.protocol.protocols.kinetic_assay module.

This includes ALL functions from the backend that cloudpickle may reference
during protocol deserialization and execution.
"""


def kinetic_assay(*args, **kwargs):
    """Stub - actual function comes from pickle."""
    pass


def _parse_well_selection(selection: str) -> list[str]:
    """Parse a well selection string into a list of well positions."""
    wells = []

    if ":" in selection and "," not in selection:
        start, end = selection.split(":")
        start_row, start_col = start[0].upper(), int(start[1:])
        end_row, end_col = end[0].upper(), int(end[1:])

        for row_ord in range(ord(start_row), ord(end_row) + 1):
            for col in range(start_col, end_col + 1):
                wells.append(f"{chr(row_ord)}{col}")
    elif "," in selection:
        wells = [w.strip().upper() for w in selection.split(",")]
    else:
        wells = [selection.strip().upper()]

    return wells

"""Browser stub for praxis.protocol.protocols package.

This mirrors the structure of the backend package so that cloudpickle
can find all protocol modules when deserializing pickled protocols.
"""

from praxis.protocol.protocols.kinetic_assay import kinetic_assay
from praxis.protocol.protocols.plate_preparation import plate_preparation
from praxis.protocol.protocols.plate_reader_assay import plate_reader_assay
from praxis.protocol.protocols.selective_transfer import selective_transfer
from praxis.protocol.protocols.serial_dilution import serial_dilution
from praxis.protocol.protocols.simple_transfer import simple_transfer

__all__ = [
    # Liquid Handling Protocols
    "simple_transfer",
    "serial_dilution",
    "plate_preparation",
    "selective_transfer",
    # Plate Reader Protocols (no-deck)
    "plate_reader_assay",
    "kinetic_assay",
]

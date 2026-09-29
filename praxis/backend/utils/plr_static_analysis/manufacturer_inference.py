"""Manufacturer inference from module paths."""

# Module path patterns to manufacturer names
# Based on VENDOR_MODULE_PATTERNS from resource_type_definition.py
MANUFACTURER_PATTERNS: dict[str, str] = {
  # Liquid handler manufacturers
  "hamilton": "Hamilton",
  "opentrons": "Opentrons",
  "tecan": "Tecan",
  "beckman": "Beckman Coulter",
  # Plate reader manufacturers
  "agilent": "Agilent",
  "biotek": "BioTek",
  "molecular_devices": "Molecular Devices",
  "clario": "BMG Labtech",
  "bmg": "BMG Labtech",
  "perkin": "PerkinElmer",
  # Resource vendors
  "corning": "Corning",
  "azenta": "Azenta",
  "alpaqua": "Alpaqua",
  "boekel": "Boekel",
  "greiner": "Greiner",
  "thermo": "Thermo Fisher",
  "revvity": "Revvity",
  "porvair": "Porvair",
  "agenbio": "AgenBio",
  "bioer": "Bioer",
  "biorad": "Bio-Rad",
  "celltreat": "Celltreat",
  "cellvis": "Cellvis",
  "eppendorf": "Eppendorf",
  "falcon": "Falcon",
  "imcs": "IMCS",
  "nest": "NEST",
  "sergi": "Sergi",
  "stanley": "Stanley",
  "vwr": "VWR",
  "inheco": "INHECO",
  "bioshake": "QInstruments",
}

# Module path patterns that indicate a vendor resource directory
VENDOR_MODULE_PATTERNS: tuple[str, ...] = (
  "pylabrobot.resources.hamilton",
  "pylabrobot.resources.opentrons",
  "pylabrobot.resources.tecan",
  "pylabrobot.resources.corning",
  "pylabrobot.resources.azenta",
  "pylabrobot.resources.alpaqua",
  "pylabrobot.resources.boekel",
  "pylabrobot.resources.greiner",
  "pylabrobot.resources.thermo",
  "pylabrobot.resources.revvity",
  "pylabrobot.resources.porvair",
  "pylabrobot.resources.agenbio",
  "pylabrobot.resources.agilent",
  "pylabrobot.resources.bioer",
  "pylabrobot.resources.biorad",
  "pylabrobot.resources.celltreat",
  "pylabrobot.resources.cellvis",
  "pylabrobot.resources.diy",
  "pylabrobot.resources.eppendorf",
  "pylabrobot.resources.falcon",
  "pylabrobot.resources.imcs",
  "pylabrobot.resources.nest",
  "pylabrobot.resources.perkin_elmer",
  "pylabrobot.resources.sergi",
  "pylabrobot.resources.stanley",
  "pylabrobot.resources.thermo_fisher",
  "pylabrobot.resources.vwr",
)


def infer_manufacturer(module_path: str) -> str | None:
  """Infer manufacturer from module path.

  Args:
    module_path: The module path (e.g., 'pylabrobot.legacy.liquid_handling.backends.hamilton.STAR')

  Returns:
    The manufacturer name if found, None otherwise.

  """
  lower_path = module_path.lower()

  for pattern, manufacturer in MANUFACTURER_PATTERNS.items():
    if pattern in lower_path:
      return manufacturer

  return None


def infer_vendor(module_path: str) -> str | None:
  """Infer vendor from module path for resources.

  Args:
    module_path: The module path

  Returns:
    The vendor name if in a vendor directory, None otherwise.

  """
  for vendor_pattern in VENDOR_MODULE_PATTERNS:
    if module_path.startswith(vendor_pattern):
      # Extract vendor from pattern (e.g., 'pylabrobot.resources.hamilton' -> 'hamilton')
      vendor_key = vendor_pattern.split(".")[-1]
      return MANUFACTURER_PATTERNS.get(vendor_key, vendor_key.title())

  return None


def is_vendor_module(module_path: str) -> bool:
  """Check if module path is in a vendor-specific directory.

  Args:
    module_path: The module path

  Returns:
    True if the module is in a vendor directory.

  """
  return any(module_path.startswith(pattern) for pattern in VENDOR_MODULE_PATTERNS)

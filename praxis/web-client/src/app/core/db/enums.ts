/**
 * Auto-generated TypeScript enums from Python enums
 * Generated at: 2026-01-21T18:31:14.016015
 * DO NOT EDIT MANUALLY - regenerate using: uv run scripts/generate_browser_schema.py
 */

/**
 * Enumeration for the status of a asset reservation.
 */
export type AssetReservationStatus =
  | 'reserved'
  | 'pending'
  | 'active'
  | 'released'
  | 'expired'
  | 'failed';

export const AssetReservationStatusValues = {
  RESERVED: 'reserved' as const,
  PENDING: 'pending' as const,
  ACTIVE: 'active' as const,
  RELEASED: 'released' as const,
  EXPIRED: 'expired' as const,
  FAILED: 'failed' as const,
} as const;

/**
 * Enum for the different types of assets.
 */
export type AssetType =
  | 'MACHINE'
  | 'RESOURCE'
  | 'MACHINE_RESOURCE'
  | 'DECK'
  | 'GENERIC_ASSET';

export const AssetTypeValues = {
  MACHINE: 'MACHINE' as const,
  RESOURCE: 'RESOURCE' as const,
  MACHINE_RESOURCE: 'MACHINE_RESOURCE' as const,
  DECK: 'DECK' as const,
  ASSET: 'GENERIC_ASSET' as const,
} as const;

/**
 * Type of machine backend implementation.

Used to distinguish between different types of backends:
- REAL_HARDWARE: Connects to a physical device
- SIMULATOR: PLR visualizer/simulator
- CHATTERBOX: Print-only, no hardware connection
- MOCK: For testing purposes only

 */
export type BackendType =
  | 'real_hardware'
  | 'simulator'
  | 'chatterbox'
  | 'mock';

export const BackendTypeValues = {
  REAL_HARDWARE: 'real_hardware' as const,
  SIMULATOR: 'simulator' as const,
  CHATTERBOX: 'chatterbox' as const,
  MOCK: 'mock' as const,
} as const;

/**
 * Enumeration for different types of data outputs.
 */
export type DataOutputType =
  | 'absorbance_reading'
  | 'fluorescence_reading'
  | 'luminescence_reading'
  | 'optical_density'
  | 'temperature_reading'
  | 'volume_measurement'
  | 'generic_measurement'
  | 'plate_image'
  | 'microscopy_image'
  | 'camera_snapshot'
  | 'raw_data_file'
  | 'analysis_report'
  | 'configuration_file'
  | 'calculated_concentration'
  | 'kinetic_analysis'
  | 'statistical_summary'
  | 'machine_status'
  | 'liquid_level'
  | 'error_log'
  | 'unknown';

export const DataOutputTypeValues = {
  ABSORBANCE_READING: 'absorbance_reading' as const,
  FLUORESCENCE_READING: 'fluorescence_reading' as const,
  LUMINESCENCE_READING: 'luminescence_reading' as const,
  OPTICAL_DENSITY: 'optical_density' as const,
  TEMPERATURE_READING: 'temperature_reading' as const,
  VOLUME_MEASUREMENT: 'volume_measurement' as const,
  GENERIC_MEASUREMENT: 'generic_measurement' as const,
  PLATE_IMAGE: 'plate_image' as const,
  MICROSCOPY_IMAGE: 'microscopy_image' as const,
  CAMERA_SNAPSHOT: 'camera_snapshot' as const,
  RAW_DATA_FILE: 'raw_data_file' as const,
  ANALYSIS_REPORT: 'analysis_report' as const,
  CONFIGURATION_FILE: 'configuration_file' as const,
  CALCULATED_CONCENTRATION: 'calculated_concentration' as const,
  KINETIC_ANALYSIS: 'kinetic_analysis' as const,
  STATISTICAL_SUMMARY: 'statistical_summary' as const,
  MACHINE_STATUS: 'machine_status' as const,
  LIQUID_LEVEL: 'liquid_level' as const,
  ERROR_LOG: 'error_log' as const,
  UNKNOWN: 'unknown' as const,
} as const;

/**
 * Enumeration for the outcome status of an individual function call.
 */
export type FunctionCallStatus =
  | 'success'
  | 'error'
  | 'pending'
  | 'in_progress'
  | 'skipped'
  | 'canceled'
  | 'unknown';

export const FunctionCallStatusValues = {
  SUCCESS: 'success' as const,
  ERROR: 'error' as const,
  PENDING: 'pending' as const,
  IN_PROGRESS: 'in_progress' as const,
  SKIPPED: 'skipped' as const,
  CANCELED: 'canceled' as const,
  UNKNOWN: 'unknown' as const,
} as const;

/**
 * Enumeration for classifying machines into predefined categories.

These categories help in broad classification of machines based on their
functionality, mapping to PyLabRobot's machine types.

 */
export type MachineCategory =
  | 'LiquidHandler'
  | 'PlateReader'
  | 'Incubator'
  | 'Shaker'
  | 'HeaterShaker'
  | 'Pump'
  | 'Fan'
  | 'TemperatureController'
  | 'Tilting'
  | 'Thermocycler'
  | 'Sealer'
  | 'FlowCytometer'
  | 'Scale'
  | 'Centrifuge'
  | 'Arm'
  | 'GeneralAutomationDevice'
  | 'OtherInstrument'
  | 'Unknown';

export const MachineCategoryValues = {
  LIQUID_HANDLER: 'LiquidHandler' as const,
  PLATE_READER: 'PlateReader' as const,
  INCUBATOR: 'Incubator' as const,
  SHAKER: 'Shaker' as const,
  HEATER_SHAKER: 'HeaterShaker' as const,
  PUMP: 'Pump' as const,
  FAN: 'Fan' as const,
  TEMPERATURE_CONTROLLER: 'TemperatureController' as const,
  TILTING: 'Tilting' as const,
  THERMOCYCLER: 'Thermocycler' as const,
  SEALER: 'Sealer' as const,
  FLOW_CYTOMETER: 'FlowCytometer' as const,
  SCALE: 'Scale' as const,
  CENTRIFUGE: 'Centrifuge' as const,
  ARM: 'Arm' as const,
  GENERAL_AUTOMATION_DEVICE: 'GeneralAutomationDevice' as const,
  OTHER_INSTRUMENT: 'OtherInstrument' as const,
  UNKNOWN: 'Unknown' as const,
} as const;

/**
 * Enumeration for the possible operational statuses of a machine.
 */
export type MachineStatus =
  | 'AVAILABLE'
  | 'IN_USE'
  | 'ERROR'
  | 'OFFLINE'
  | 'INITIALIZING'
  | 'MAINTENANCE';

export const MachineStatusValues = {
  AVAILABLE: 'AVAILABLE' as const,
  IN_USE: 'IN_USE' as const,
  ERROR: 'ERROR' as const,
  OFFLINE: 'OFFLINE' as const,
  INITIALIZING: 'INITIALIZING' as const,
  MAINTENANCE: 'MAINTENANCE' as const,
} as const;

/**
 * Enumeration for the operational status of a protocol run.
 */
export type ProtocolRunStatus =
  | 'QUEUED'
  | 'PENDING'
  | 'PREPARING'
  | 'RUNNING'
  | 'PAUSING'
  | 'PAUSED'
  | 'RESUMING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELING'
  | 'CANCELLED'
  | 'INTERVENING'
  | 'REQUIRES_INTERVENTION';

export const ProtocolRunStatusValues = {
  QUEUED: 'QUEUED' as const,
  PENDING: 'PENDING' as const,
  PREPARING: 'PREPARING' as const,
  RUNNING: 'RUNNING' as const,
  PAUSING: 'PAUSING' as const,
  PAUSED: 'PAUSED' as const,
  RESUMING: 'RESUMING' as const,
  COMPLETED: 'COMPLETED' as const,
  FAILED: 'FAILED' as const,
  CANCELING: 'CANCELING' as const,
  CANCELLED: 'CANCELLED' as const,
  INTERVENING: 'INTERVENING' as const,
  REQUIRES_INTERVENTION: 'REQUIRES_INTERVENTION' as const,
} as const;

/**
 * Enumeration for the status of a protocol source (repository or file system).
 */
export type ProtocolSourceStatus =
  | 'active'
  | 'archived'
  | 'syncing'
  | 'inactive'
  | 'sync_error'
  | 'pending_deletion';

export const ProtocolSourceStatusValues = {
  ACTIVE: 'active' as const,
  ARCHIVED: 'archived' as const,
  SYNCING: 'syncing' as const,
  INACTIVE: 'inactive' as const,
  SYNC_ERROR: 'sync_error' as const,
  PENDING_DELETION: 'pending_deletion' as const,
} as const;

/**
 * Actions taken after state resolution.
 */
export type ResolutionAction =
  | 'resume'
  | 'abort'
  | 'retry';

export const ResolutionActionValues = {
  RESUME: 'resume' as const,
  ABORT: 'abort' as const,
  RETRY: 'retry' as const,
} as const;

/**
 * Types of state resolution.
 */
export type ResolutionType =
  | 'confirmed_success'
  | 'confirmed_failure'
  | 'partial'
  | 'arbitrary'
  | 'unknown';

export const ResolutionTypeValues = {
  CONFIRMED_SUCCESS: 'confirmed_success' as const,
  CONFIRMED_FAILURE: 'confirmed_failure' as const,
  PARTIAL: 'partial' as const,
  ARBITRARY: 'arbitrary' as const,
  UNKNOWN: 'unknown' as const,
} as const;

/**
 * Enumeration for the categories of resources in the catalog.

This enum defines the main categories of lab resources based on a hierarchical
classification, used to classify resources in the catalog.

 */
export type ResourceCategory =
  | 'Arm'
  | 'Carrier'
  | 'Container'
  | 'Deck'
  | 'ItemizedResource'
  | 'ResourceHolder'
  | 'Lid'
  | 'PlateAdapter'
  | 'ResourceStack'
  | 'Other'
  | 'MFXCarrier'
  | 'PlateCarrier'
  | 'TipCarrier'
  | 'TroughCarrier'
  | 'TubeCarrier'
  | 'PetriDish'
  | 'Trough'
  | 'Tube'
  | 'Well'
  | 'OTDeck'
  | 'HamiltonDeck'
  | 'TecanDeck'
  | 'Plate'
  | 'TipRack'
  | 'TubeRack'
  | 'PlateHolder'
  | 'Shaker'
  | 'HeaterShaker'
  | 'PlateReader'
  | 'TemperatureController'
  | 'Centrifuge'
  | 'Incubator'
  | 'Tilter'
  | 'Thermocycler'
  | 'Scale';

export const ResourceCategoryValues = {
  ARM: 'Arm' as const,
  CARRIER: 'Carrier' as const,
  CONTAINER: 'Container' as const,
  DECK: 'Deck' as const,
  ITEMIZED_RESOURCE: 'ItemizedResource' as const,
  RESOURCE_HOLDER: 'ResourceHolder' as const,
  LID: 'Lid' as const,
  PLATE_ADAPTER: 'PlateAdapter' as const,
  RESOURCE_STACK: 'ResourceStack' as const,
  OTHER: 'Other' as const,
  MFX_CARRIER: 'MFXCarrier' as const,
  PLATE_CARRIER: 'PlateCarrier' as const,
  TIP_CARRIER: 'TipCarrier' as const,
  TROUGH_CARRIER: 'TroughCarrier' as const,
  TUBE_CARRIER: 'TubeCarrier' as const,
  PETRI_DISH: 'PetriDish' as const,
  TROUGH: 'Trough' as const,
  TUBE: 'Tube' as const,
  WELL: 'Well' as const,
  OT_DECK: 'OTDeck' as const,
  HAMILTON_DECK: 'HamiltonDeck' as const,
  TECAN_DECK: 'TecanDeck' as const,
  PLATE: 'Plate' as const,
  TIP_RACK: 'TipRack' as const,
  TUBE_RACK: 'TubeRack' as const,
  PLATE_HOLDER: 'PlateHolder' as const,
  SHAKER: 'Shaker' as const,
  HEATERSHAKER: 'HeaterShaker' as const,
  PLATE_READER: 'PlateReader' as const,
  TEMPERATURE_CONTROLLER: 'TemperatureController' as const,
  CENTRIFUGE: 'Centrifuge' as const,
  INCUBATOR: 'Incubator' as const,
  TILTER: 'Tilter' as const,
  THERMOCYCLER: 'Thermocycler' as const,
  SCALE: 'Scale' as const,
} as const;

/**
 * Enumeration for the possible operational statuses of a resource instance.
 */
export type ResourceStatus =
  | 'available_in_storage'
  | 'available_on_deck'
  | 'in_use'
  | 'empty'
  | 'partially_filled'
  | 'full'
  | 'needs_refill'
  | 'to_be_disposed'
  | 'disposed'
  | 'to_be_cleaned'
  | 'cleaned'
  | 'error'
  | 'unknown';

export const ResourceStatusValues = {
  AVAILABLE_IN_STORAGE: 'available_in_storage' as const,
  AVAILABLE_ON_DECK: 'available_on_deck' as const,
  IN_USE: 'in_use' as const,
  EMPTY: 'empty' as const,
  PARTIALLY_FILLED: 'partially_filled' as const,
  FULL: 'full' as const,
  NEEDS_REFILL: 'needs_refill' as const,
  TO_BE_DISPOSED: 'to_be_disposed' as const,
  DISPOSED: 'disposed' as const,
  TO_BE_CLEANED: 'to_be_cleaned' as const,
  CLEANED: 'cleaned' as const,
  ERROR: 'error' as const,
  UNKNOWN: 'unknown' as const,
} as const;

/**
 * Enumeration for spatial context types.
 */
export type SpatialContext =
  | 'well_specific'
  | 'plate_level'
  | 'machine_level'
  | 'deck_position'
  | 'global';

export const SpatialContextValues = {
  WELL_SPECIFIC: 'well_specific' as const,
  PLATE_LEVEL: 'plate_level' as const,
  MACHINE_LEVEL: 'machine_level' as const,
  DECK_POSITION: 'deck_position' as const,
  GLOBAL: 'global' as const,
} as const;

/**
 * Enumeration for workcell status.

This enum defines the possible statuses a workcell can have.

 */
export type WorkcellStatus =
  | 'active'
  | 'in_use'
  | 'reserved'
  | 'available'
  | 'error'
  | 'inactive'
  | 'maintenance';

export const WorkcellStatusValues = {
  ACTIVE: 'active' as const,
  IN_USE: 'in_use' as const,
  RESERVED: 'reserved' as const,
  AVAILABLE: 'available' as const,
  ERROR: 'error' as const,
  INACTIVE: 'inactive' as const,
  MAINTENANCE: 'maintenance' as const,
} as const;

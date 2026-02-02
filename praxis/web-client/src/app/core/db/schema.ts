/**
 * Auto-generated TypeScript interfaces from SQLAlchemy ORM models
 * Generated at: 2026-01-21T18:31:14.015294
 * DO NOT EDIT MANUALLY - regenerate using: uv run scripts/generate_browser_schema.py
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import type {
  AssetType,
  BackendType,
  DataOutputType,
  FunctionCallStatus,
  MachineCategory,
  MachineStatus,
  ProtocolRunStatus,
  ProtocolSourceStatus,
  ResolutionAction,
  ResolutionType,
  ResourceStatus,
  SpatialContext,
  WorkcellStatus,
} from './enums';

/**
 * Interface for the 'deck_definition_catalog' table
 */
export interface DeckDefinitionCatalog {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string;
  version: string | null;
  positioning_config: Record<string, unknown> | null;
  description: string | null;
  plr_category: string | null;
  default_size_x_mm: number | null;
  default_size_y_mm: number | null;
  default_size_z_mm: number | null;
  serialized_constructor_args_json: Record<string, unknown> | null;
  serialized_assignment_methods_json: Record<string, unknown> | null;
  serialized_constructor_hints_json: Record<string, unknown> | null;
  additional_properties_json: Record<string, unknown> | null;
  positioning_config_json: Record<string, unknown> | null;
  asset_requirement_accession_id: string | null;
  resource_definition_accession_id: string | null;
  parent_accession_id: string | null;
}

/**
 * Interface for the 'deck_position_definitions' table
 */
export interface DeckPositionDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  position_accession_id: string | null;
  nominal_x_mm: number | null;
  nominal_y_mm: number | null;
  nominal_z_mm: number | null;
  pylabrobot_position_type_name: string | null;
  accepts_tips: boolean | null;
  accepts_plates: boolean | null;
  accepts_tubes: boolean | null;
  notes: string | null;
  allowed_resource_definition_names: Record<string, unknown> | null;
  compatible_resource_fqns: Record<string, unknown> | null;
  deck_type_id: string;
}

/**
 * Interface for the 'decks' table
 */
export interface Deck {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string;
  properties_json: Record<string, unknown> | null;
  asset_type: AssetType | null;
  fqn: string | null;
  location: string | null;
  plr_state: Record<string, unknown> | null;
  plr_definition: Record<string, unknown> | null;
  status: ResourceStatus | null;
  status_details: string | null;
  location_label: string | null;
  current_deck_position_name: string | null;
  parent_accession_id: string | null;
  parent_machine_accession_id: string | null;
  deck_type_id: string | null;
  workcell_accession_id: string | null;
  resource_definition_accession_id: string | null;
}

/**
 * Interface for the 'file_system_protocol_sources' table
 */
export interface FileSystemProtocolSource {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  base_path: string | null;
  is_recursive: boolean | null;
  status: ProtocolSourceStatus | null;
}

/**
 * Interface for the 'function_call_logs' table
 */
export interface FunctionCallLog {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  sequence_in_run: number;
  start_time: string | null;
  end_time: string | null;
  duration_ms: number | null;
  error_message_text: string | null;
  error_traceback_text: string | null;
  status: FunctionCallStatus | null;
  input_args_json: Record<string, unknown> | null;
  return_value_json: Record<string, unknown> | null;
  state_before_json: Record<string, unknown> | null;
  state_after_json: Record<string, unknown> | null;
  protocol_run_accession_id: string;
  function_protocol_definition_accession_id: string;
  parent_function_call_log_accession_id: string | null;
}

/**
 * Interface for the 'function_data_outputs' table
 */
export interface FunctionDataOutput {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  data_key: string | null;
  spatial_coordinates_json: Record<string, unknown> | null;
  data_units: string | null;
  data_quality_score: number | null;
  measurement_conditions_json: Record<string, unknown> | null;
  sequence_in_function: number | null;
  file_path: string | null;
  file_size_bytes: number | null;
  mime_type: string | null;
  measurement_timestamp: string | null;
  data_type: DataOutputType | null;
  spatial_context: SpatialContext | null;
  data_value_json: Record<string, unknown> | null;
  data_value_numeric: number | null;
  data_value_text: string | null;
  data_value_binary: Uint8Array | null;
  function_call_log_accession_id: string | null;
  protocol_run_accession_id: string | null;
  machine_accession_id: string | null;
  resource_accession_id: string | null;
  deck_accession_id: string | null;
  derived_from_data_output_accession_id: string | null;
}

/**
 * Interface for the 'function_protocol_definitions' table
 */
export interface FunctionProtocolDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string;
  version: string | null;
  description: string | null;
  source_file_path: string | null;
  module_name: string | null;
  function_name: string | null;
  is_top_level: boolean | null;
  solo_execution: boolean | null;
  preconfigure_deck: boolean | null;
  requires_deck: boolean | null;
  deck_param_name: string | null;
  deck_construction_function_fqn: string | null;
  deck_layout_path: string | null;
  state_param_name: string | null;
  requires_linked_indices: boolean | null;
  category: string | null;
  deprecated: boolean | null;
  source_hash: string | null;
  graph_cached_at: string | null;
  simulation_version: string | null;
  simulation_cached_at: string | null;
  bytecode_python_version: string | null;
  bytecode_cache_version: string | null;
  bytecode_cached_at: string | null;
  commit_hash: string | null;
  tags: Record<string, unknown> | null;
  hardware_requirements_json: Record<string, unknown> | null;
  data_views_json: Record<string, unknown> | null;
  computation_graph_json: Record<string, unknown> | null;
  setup_instructions_json: Record<string, unknown> | null;
  simulation_result_json: Record<string, unknown> | null;
  inferred_requirements_json: Record<string, unknown> | null;
  failure_modes_json: Record<string, unknown> | null;
  cached_bytecode: Uint8Array | null;
  source_repository_accession_id: string | null;
  file_system_source_accession_id: string | null;
}

/**
 * Interface for the 'machine_backend_definitions' table
 */
export interface MachineBackendDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string;
  description: string | null;
  connection_config: Record<string, unknown> | null;
  manufacturer: string | null;
  model: string | null;
  is_deprecated: boolean | null;
  backend_type: BackendType | null;
  frontend_definition_accession_id: string;
}

/**
 * Interface for the 'machine_definitions' table
 */
export interface MachineDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string;
  description: string | null;
  plr_category: string | null;
  material: string | null;
  manufacturer: string | null;
  model: string | null;
  size_x_mm: number | null;
  size_y_mm: number | null;
  size_z_mm: number | null;
  frontend_fqn: string | null;
  nominal_volume_ul: number | null;
  plr_definition_details_json: Record<string, unknown> | null;
  rotation_json: Record<string, unknown> | null;
  setup_method_json: Record<string, unknown> | null;
  capabilities: Record<string, unknown> | null;
  compatible_backends: Record<string, unknown> | null;
  capabilities_config: Record<string, unknown> | null;
  connection_config: Record<string, unknown> | null;
  is_simulated_frontend: boolean | null;
  available_simulation_backends: Record<string, unknown> | null;
  machine_category: MachineCategory | null;
  has_deck: boolean | null;
  resource_definition_accession_id: string | null;
  deck_definition_accession_id: string | null;
  asset_requirement_accession_id: string | null;
}

/**
 * Interface for the 'machine_frontend_definitions' table
 */
export interface MachineFrontendDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string;
  description: string | null;
  plr_category: string | null;
  capabilities: Record<string, unknown> | null;
  capabilities_config: Record<string, unknown> | null;
  has_deck: boolean | null;
  manufacturer: string | null;
  model: string | null;
  machine_category: MachineCategory | null;
  deck_definition_accession_id: string | null;
}

/**
 * Interface for the 'machines' table
 */
export interface Machine {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string;
  properties_json: Record<string, unknown> | null;
  asset_type: AssetType | null;
  fqn: string | null;
  location: string | null;
  plr_state: Record<string, unknown> | null;
  plr_definition: Record<string, unknown> | null;
  description: string | null;
  manufacturer: string | null;
  model: string | null;
  location_label: string | null;
  installation_date: string | null;
  status_details: string | null;
  is_simulation_override: boolean | null;
  last_seen_online: string | null;
  maintenance_enabled: boolean | null;
  connection_info: Record<string, unknown> | null;
  user_configured_capabilities: Record<string, unknown> | null;
  maintenance_schedule_json: Record<string, unknown> | null;
  last_maintenance_json: Record<string, unknown> | null;
  simulation_backend_name: string | null;
  machine_category: MachineCategory | null;
  status: MachineStatus | null;
  serial_number: string | null;
  workcell_accession_id: string | null;
  resource_counterpart_accession_id: string | null;
  deck_child_accession_id: string | null;
  deck_child_definition_accession_id: string | null;
  current_protocol_run_accession_id: string | null;
  machine_definition_accession_id: string | null;
  frontend_definition_accession_id: string | null;
  backend_definition_accession_id: string | null;
  backend_config: Record<string, unknown> | null;
}

/**
 * Interface for the 'parameter_definitions' table
 */
export interface ParameterDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  type_hint: string | null;
  fqn: string | null;
  is_deck_param: boolean | null;
  optional: boolean | null;
  default_value_repr: string | null;
  description: string | null;
  field_type: string | null;
  is_itemized: boolean | null;
  linked_to: string | null;
  constraints_json: Record<string, unknown> | null;
  itemized_spec_json: Record<string, unknown> | null;
  ui_hint_json: Record<string, unknown> | null;
  protocol_definition_accession_id: string;
}

/**
 * Interface for the 'protocol_asset_requirements' table
 */
export interface ProtocolAssetRequirement {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  type_hint_str: string | null;
  fqn: string | null;
  actual_type_str: string | null;
  optional: boolean | null;
  default_value_repr: string | null;
  description: string | null;
  required_plr_category: string | null;
  constraints_json: Record<string, unknown> | null;
  location_constraints_json: Record<string, unknown> | null;
  protocol_definition_accession_id: string;
}

/**
 * Metadata for a protocol run, stored in properties_json
 */
export interface RunMetadata {
  notes?: string;
  simulation_mode?: boolean;
  lastHeartbeat?: number; // Unix timestamp (ms)
  checkpointStep?: number;
  checkpointState?: any;
}

/**
 * Interface for the 'protocol_runs' table
 */
export interface ProtocolRun {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: RunMetadata | null;
  start_time: string | null;
  end_time: string | null;
  data_directory_path: string | null;
  duration_ms: number | null;
  status: ProtocolRunStatus | null;
  input_parameters_json: Record<string, unknown> | null;
  resolved_assets_json: Record<string, unknown> | null;
  output_data_json: Record<string, unknown> | null;
  initial_state_json: Record<string, unknown> | null;
  final_state_json: Record<string, unknown> | null;
  created_by_user: Record<string, unknown> | null;
  top_level_protocol_definition_accession_id: string;
  protocol_definition_accession_id: string | null;
  previous_accession_id: string | null;
}

/**
 * Interface for the 'protocol_source_repositories' table
 */
export interface ProtocolSourceRepository {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  git_url: string | null;
  default_ref: string | null;
  local_checkout_path: string | null;
  last_synced_commit: string | null;
  status: ProtocolSourceStatus | null;
  auto_sync_enabled: boolean | null;
}

/**
 * Interface for the 'resource_definitions' table
 */
export interface ResourceDefinition {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string;
  description: string | null;
  plr_category: string | null;
  resource_type: string | null;
  is_consumable: boolean | null;
  is_reusable: boolean | null;
  nominal_volume_ul: number | null;
  material: string | null;
  manufacturer: string | null;
  model: string | null;
  ordering: string | null;
  size_x_mm: number | null;
  size_y_mm: number | null;
  size_z_mm: number | null;
  num_items: number | null;
  plate_type: string | null;
  well_volume_ul: number | null;
  tip_volume_ul: number | null;
  vendor: string | null;
  plr_definition_details_json: Record<string, unknown> | null;
  rotation_json: Record<string, unknown> | null;
  deck_definition_accession_id: string | null;
  asset_requirement_accession_id: string | null;
}

/**
 * Interface for the 'resources' table
 */
export interface Resource {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string;
  properties_json: Record<string, unknown> | null;
  asset_type: AssetType | null;
  fqn: string | null;
  location: string | null;
  plr_state: Record<string, unknown> | null;
  plr_definition: Record<string, unknown> | null;
  status_details: string | null;
  location_label: string | null;
  current_deck_position_name: string | null;
  status: ResourceStatus | null;
  resource_definition_accession_id: string | null;
  parent_accession_id: string | null;
  current_protocol_run_accession_id: string | null;
  machine_location_accession_id: string | null;
  deck_location_accession_id: string | null;
  workcell_accession_id: string | null;
}

/**
 * Interface for the 'state_resolution_log' table
 */
export interface StateResolutionLog {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  operation_id: string;
  operation_description: string;
  error_message: string;
  error_type: string | null;
  uncertain_states_json: Record<string, unknown> | null;
  resolution_json: Record<string, unknown> | null;
  resolution_type: ResolutionType;
  resolved_by: string | null;
  resolved_at: string | null;
  notes: string | null;
  action_taken: ResolutionAction;
  schedule_entry_accession_id: string;
  protocol_run_accession_id: string;
}

/**
 * Interface for the 'well_data_outputs' table
 */
export interface WellDataOutput {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  well_position: string | null;
  measurement_type: string | null;
  value: number | null;
  unit: string | null;
  well_name: string | null;
  data_value: number | null;
  well_row: number | null;
  well_column: number | null;
  well_index: number | null;
  metadata_json: Record<string, unknown> | null;
  function_data_output_accession_id: string | null;
  resource_accession_id: string | null;
  plate_resource_accession_id: string | null;
}

/**
 * Interface for the 'workcells' table
 */
export interface Workcell {
  accession_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  name: string | null;
  properties_json: Record<string, unknown> | null;
  fqn: string | null;
  description: string | null;
  physical_location: string | null;
  last_state_update_time: string | null;
  status: WorkcellStatus | null;
  latest_state_json: Record<string, unknown> | null;
}

// =============================================================================
// TYPE ALIASES FOR BACKWARD COMPATIBILITY
// =============================================================================

/** Legacy alias for MachineDefinition (was 'machine_definition_catalog' table) */
export type MachineDefinitionCatalog = MachineDefinition;

/** Legacy alias for ResourceDefinition (was 'resource_definition_catalog' table) */
export type ResourceDefinitionCatalog = ResourceDefinition;

/**
 * Asset is the base type for Machine, Resource, and Deck entities.
 * In the backend, these use Joined Table Inheritance (JTI).
 */
export type Asset = Machine | Resource | Deck;

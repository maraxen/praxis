
export enum MachineStatus {
  OFFLINE = 'offline',
  IDLE = 'idle',
  RUNNING = 'running',
  ERROR = 'error',
  MAINTENANCE = 'maintenance',
  UNKNOWN = 'unknown'
}

export enum ResourceStatus {
  AVAILABLE = 'available',
  RESERVED = 'reserved',
  IN_USE = 'in_use',
  DEPLETED = 'depleted',
  EXPIRED = 'expired',
  UNKNOWN = 'unknown'
}

export interface MaintenanceInterval {
  type: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'custom';
  interval_days: number;
  description?: string;
  checklist?: string[];
  required: boolean;
}

export interface MaintenanceSchedule {
  intervals: MaintenanceInterval[];
  enabled: boolean;
  notes?: string;
}

export interface MaintenanceRecord {
  type: string;
  completed_at: string; // ISO date string
  completed_by?: string;
  notes?: string;
}

export interface AssetBase {
  accession_id: string;
  name: string;
  fqn?: string;
  location?: string;
  location_label?: string; // e.g. "Room 101, Bench A"
  asset_type?: string;
  description?: string;
  plr_state?: any;
  plr_definition?: any;
  created_at?: string;
  updated_at?: string;
}

export interface Machine extends AssetBase {
  status: MachineStatus;
  status_details?: string;
  machine_category?: string;
  machine_type?: string; // Legacy/UI alias
  description?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  connection_info?: Record<string, any>;
  is_simulation_override?: boolean;
  user_configured_capabilities?: Record<string, any>;
  simulation_backend_name?: string;

  // Maintenance fields
  maintenance_enabled?: boolean;
  maintenance_schedule_json?: MaintenanceSchedule;
  last_maintenance_json?: Record<string, MaintenanceRecord>;
  workcell_accession_id?: string;
  frontend_definition_accession_id?: string;
  backend_definition_accession_id?: string;
  backend_config?: Record<string, any>;

  // Joined fields
  frontend_definition?: MachineFrontendDefinition;
  backend_definition?: MachineBackendDefinition;
}

export interface MachineCreate {
  name: string;
  status?: MachineStatus;
  machine_category?: string;
  machine_type?: string;
  description?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  connection_info?: Record<string, any>;
  is_simulation_override?: boolean;
  user_configured_capabilities?: Record<string, any>;
  simulation_backend_name?: string;
  machine_definition_accession_id?: string;
  frontend_definition_accession_id?: string;
  backend_definition_accession_id?: string;
  backend_config?: Record<string, any>;
  deck_type?: string; // FQN of selected deck definition (for LiquidHandler machines)
  maintenance_enabled?: boolean;
  maintenance_schedule_json?: MaintenanceSchedule;
  last_maintenance_json?: Record<string, MaintenanceRecord>;
}

export interface Resource extends AssetBase {
  status: ResourceStatus;
  status_details?: string;
  resource_definition_accession_id?: string;
  parent_accession_id?: string;
  machine_location_accession_id?: string;
  workcell_accession_id?: string;
  children?: Resource[];
  properties_json?: Record<string, any>;
}

export interface ResourceCreate {
  name: string;
  status?: ResourceStatus;
  resource_definition_accession_id?: string;
  parent_accession_id?: string;
  properties_json?: Record<string, any>;
}

export interface MachineDefinition {
  accession_id: string;
  name: string;
  fqn?: string;
  description?: string;
  plr_category?: string;
  machine_category?: string;
  manufacturer?: string;
  model?: string;
  nominal_volume_ul?: number;
  capabilities?: Record<string, any> | null;
  compatible_backends?: string[];
  capabilities_config?: any;
  connection_config?: any;
  frontend_fqn?: string;
  is_simulated_frontend?: boolean;
  available_simulation_backends?: string[];
  frontend_definition_accession_id?: string;
  backend_type?: 'hardware' | 'simulator' | 'mock';
}

export interface MachineFrontendDefinition {
  accession_id: string;
  name?: string;
  fqn: string;
  description?: string;
  machine_category?: string;
  has_deck?: boolean;
  capabilities?: Record<string, any>;
  capabilities_config?: Record<string, any>;
  manufacturer?: string;
  model?: string;
}

export interface MachineBackendDefinition {
  accession_id: string;
  name?: string;
  fqn: string;
  description?: string;
  backend_type?: 'hardware' | 'simulator' | 'mock';
  connection_config?: Record<string, any>;
  manufacturer?: string;
  model?: string;
  is_deprecated?: boolean;
  frontend_definition_accession_id: string;
}

export interface MachineCapabilityConfigSchema {
  machine_type: string;
  config_fields: CapabilityConfigField[];
}

export interface CapabilityConfigField {
  field_name: string;
  display_name: string;
  field_type: 'boolean' | 'number' | 'select' | 'multiselect';
  default_value: any;
  options?: string[];
  help_text?: string;
  depends_on?: string;
  required?: boolean;
  min?: number;
  max?: number;
}
export interface ResourceDefinition {
  accession_id: string;
  name: string;
  fqn?: string;
  description?: string;
  resource_type?: string;
  manufacturer?: string;
  model?: string;
  nominal_volume_ul?: number;
  is_consumable: boolean;
  // Dynamic filter fields
  num_items?: number;
  plate_type?: string;
  well_volume_ul?: number;
  tip_volume_ul?: number;
  vendor?: string;
  plr_category?: string;
  size_x_mm?: number;
  size_y_mm?: number;
  size_z_mm?: number;
}

// Active facet filters for dynamic querying
export interface ActiveFilters {
  plr_category: (string | number)[];
  vendor: (string | number)[];
  num_items: (string | number)[];
  plate_type: (string | number)[];
}

export interface Workcell {
  accession_id: string;
  name: string;
  description?: string;
  physical_location?: string;
  status: string;
}


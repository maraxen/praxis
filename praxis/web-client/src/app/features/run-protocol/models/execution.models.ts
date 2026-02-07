
export enum ExecutionStatus {
  QUEUED = 'QUEUED',
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED'
}

export interface ExecutionMessage {
  type: 'status' | 'log' | 'progress' | 'error' | 'complete' | 'telemetry' | 'well_state_update';
  payload: any;
  timestamp: string;
}

/**
 * Compressed well state update from backend.
 * Keys are resource names (e.g., "plate_1", "tip_rack_1").
 */
export interface WellStateUpdate {
  [resourceName: string]: {
    liquid_mask?: string;  // Hex bitmask of wells with liquid
    volumes?: number[];    // Sparse array of volumes for wells with liquid
    tip_mask?: string;     // Hex bitmask of tips present
  };
}

export interface ExecutionState {
  runId: string;
  protocolName: string;
  status: ExecutionStatus;
  progress: number;
  currentStep?: string;
  logs: string[];
  startTime?: string;
  endTime?: string;
  /** Latest telemetry data */
  telemetry?: {
    temperature?: number;
    absorbance?: number;
  };
  /** Compressed well state updates */
  wellState?: WellStateUpdate;
  /** Deck definition for visualization */
  plr_definition?: any;
}


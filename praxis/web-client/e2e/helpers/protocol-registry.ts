/**
 * Protocol Test Registry
 *
 * Registry of all protocols available for E2E testing.
 * Used by protocol-simulation-matrix.spec.ts to dynamically generate tests.
 */

/**
 * Entry describing a protocol for matrix testing
 */
export interface ProtocolTestEntry {
    /** Protocol accession_id (UUID from .pkl filename) */
    id: string;
    /** Human-readable name for test output */
    name: string;
    /** If true, skip in browser simulation (requires real hardware) */
    requiresHardware: boolean;
    /** Expected execution duration in seconds (used for timeout calculation) */
    expectedDuration: number;
    /** Known issues that affect this protocol (for documentation) */
    knownIssues?: string[];
}

/**
 * All known protocol entries from src/assets/protocols/*.pkl
 *
 * Protocol IDs are extracted from pickle filenames.
 * Names are placeholder labels - can be enriched once protocols are better documented.
 */
export const PROTOCOL_TEST_REGISTRY: ProtocolTestEntry[] = [
    {
        id: '03f20569-f5f6-035d-8b42-f403e97b3b70',
        name: 'Kinetic Assay',
        requiresHardware: false,
        expectedDuration: 60,
    },
    {
        id: '7f605eec-a223-a5e3-0913-0d27a5ef0286',
        name: 'Plate Reader Assay',
        requiresHardware: false,
        expectedDuration: 45,
    },
    {
        id: '84bcb2f2-81f4-416f-5b33-060dd3b05d4d',
        name: 'Simple Transfer',
        requiresHardware: false,
        expectedDuration: 50,
    },
    {
        id: 'cf6d9160-17a2-a7b7-8d35-ddd185df8296',
        name: 'Plate Preparation',
        requiresHardware: false,
        expectedDuration: 60,
    },
    {
        id: 'f4b413c6-5c09-4d03-1bb6-2546539ff29c',
        name: 'Serial Dilution',
        requiresHardware: false,
        expectedDuration: 60,
    },
    {
        id: 'f93dda87-fd67-34e9-52d9-b9901c134899',
        name: 'Selective Transfer',
        requiresHardware: false,
        expectedDuration: 45,
    },
];

/**
 * Protocols that can run in simulation mode (no real hardware required)
 */
export const SIMULATABLE_PROTOCOLS = PROTOCOL_TEST_REGISTRY.filter(
    (p) => !p.requiresHardware
);

/**
 * Look up a protocol entry by ID
 */
export function getProtocolById(id: string): ProtocolTestEntry | undefined {
    return PROTOCOL_TEST_REGISTRY.find((p) => p.id === id);
}

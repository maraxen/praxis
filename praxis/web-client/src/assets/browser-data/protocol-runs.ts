/**
 * Mock protocol runs for browser mode
 */
export const MOCK_PROTOCOL_RUNS = [
    {
        accession_id: 'aaaa1111-1111-1111-1111-111111111111',
        protocol_definition_accession_id: '11111111-1111-1111-1111-111111111111',
        protocol_name: 'PCR Prep (96-well)',
        status: 'completed',
        input_parameters_json: {
            source_plate: 'plate-001',
            destination_plate: 'plate-002',
            volume_ul: 25.0
        },
        resolved_assets_json: {
            source_plate: { accession_id: 'res-001', name: 'Source Plate A' },
            destination_plate: { accession_id: 'res-002', name: 'Destination Plate B' }
        },
        created_at: '2024-12-28T14:30:00Z',
        started_at: '2024-12-28T14:31:00Z',
        completed_at: '2024-12-28T14:35:22Z',
        created_by_user: { id: 'user-1', username: 'lab_tech_1' }
    },
    {
        accession_id: 'aaaa2222-2222-2222-2222-222222222222',
        protocol_definition_accession_id: '22222222-2222-2222-2222-222222222222',
        protocol_name: 'Cell Culture Feed (24-well)',
        status: 'running',
        input_parameters_json: {
            plate: 'plate-003',
            media_volume_ul: 500.0
        },
        current_step: 'Feeding row B',
        progress_percent: 62.5,
        created_at: '2024-12-29T09:15:00Z',
        started_at: '2024-12-29T09:16:00Z',
        created_by_user: { id: 'user-2', username: 'scientist_jane' }
    },
    {
        accession_id: 'aaaa3333-3333-3333-3333-333333333333',
        protocol_definition_accession_id: '33333333-3333-3333-3333-333333333333',
        protocol_name: 'Daily System Maintenance',
        status: 'queued',
        input_parameters_json: {
            wash_cycles: 2
        },
        created_at: '2024-12-29T10:00:00Z',
        created_by_user: { id: 'user-1', username: 'lab_tech_1' }
    },
    {
        accession_id: 'aaaa4444-4444-4444-4444-444444444444',
        protocol_definition_accession_id: '11111111-1111-1111-1111-111111111111',
        protocol_name: 'PCR Prep (96-well)',
        status: 'failed',
        input_parameters_json: {
            source_plate: 'plate-005',
            destination_plate: 'plate-006',
            volume_ul: 25.0
        },
        error_message: 'Insufficient volume in source plate well A1',
        created_at: '2024-12-27T16:45:00Z',
        started_at: '2024-12-27T16:46:00Z',
        completed_at: '2024-12-27T16:47:12Z',
        created_by_user: { id: 'user-3', username: 'researcher_bob' }
    }
];

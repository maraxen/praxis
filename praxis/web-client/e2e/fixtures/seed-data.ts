export const SEED_RESOURCES = [
    {
        accession_id: 'res_test_001',
        name: 'Corning 96 Well Plate',
        fqn: 'pylabrobot.resources.corning_costar.Corning_96_Wellplate_360ul_Flat',
        resource_type: 'plate',
        vendor: 'Corning',
        description: 'Standard 96 well plate',
        properties_json: { well_count: 96, max_volume: 360 },
        is_consumable: true,
        is_reusable: false
    },
    {
        accession_id: 'res_test_002',
        name: 'Hamilton Core96 Tip Rack',
        fqn: 'pylabrobot.resources.hamilton.TipRack_96_1000ul',
        resource_type: 'tip_rack',
        vendor: 'Hamilton',
        description: 'High volume tip rack',
        properties_json: { tip_count: 96, tip_volume: 1000 },
        is_consumable: true,
        is_reusable: false
    }
];

export const SEED_MACHINES = [
    {
        accession_id: 'mach_test_001',
        name: 'Hamilton STAR',
        fqn: 'pylabrobot.legacy.liquid_handling.backends.hamilton.STAR',
        machine_category: 'liquid_handler',
        manufacturer: 'Hamilton',
        description: 'High throughput liquid handler',
        has_deck: true,
        properties_json: {},
        compatible_backends: ['pylabrobot.legacy.liquid_handling.backends.hamilton.STAR', 'pylabrobot.legacy.liquid_handling.backends.simulation.Simulator']
    },
    {
        accession_id: 'mach_test_002',
        name: 'BMG CLARIOstar',
        fqn: 'pylabrobot.legacy.plate_reading.backend.bmg.CLARIOstar',
        machine_category: 'plate_reader',
        manufacturer: 'BMG Labtech',
        description: 'Multimode plate reader',
        has_deck: false,
        properties_json: {},
        compatible_backends: ['pylabrobot.legacy.plate_reading.backend.bmg.CLARIOstar']
    }
];

/**
 * Comprehensive PLR Resource and Machine Definitions for Browser Mode
 *
 * This is a curated list of common PyLabRobot resources and machines.
 * In production, these would be discovered dynamically from the backend.
 */

export interface PlrResourceDefinition {
    accession_id: string;
    name: string;
    fqn: string;
    plr_category: 'Plate' | 'TipRack' | 'Reservoir' | 'Carrier' | 'Deck' | 'Tube' | 'Resource';
    vendor?: string;
    description?: string;
    num_items?: number;
    is_consumable: boolean;
    is_reusable: boolean;
    properties_json: Record<string, unknown>;
}

export interface PlrMachineDefinition {
    accession_id: string;
    name: string;
    fqn: string;
    vendor?: string;
    description?: string;
    has_deck: boolean;
    machine_type: 'LiquidHandler' | 'PlateReader' | 'Shaker' | 'Centrifuge' | 'Incubator' | 'Other';
    properties_json: Record<string, unknown>;
    capabilities_config?: any;
    frontend_fqn?: string;
    is_simulated_frontend?: boolean;
    available_simulation_backends?: string[];
}

export interface PlrFrontendDefinition {
    accession_id: string;
    name: string;
    fqn: string;
    description?: string;
    machine_category: 'LiquidHandler' | 'PlateReader' | 'Imager' | 'HeaterShaker' | 'Shaker' | 'TemperatureController' | 'Centrifuge' | 'Thermocycler' | 'Pump' | 'PumpArray' | 'Fan' | 'Sealer' | 'Peeler' | 'PowderDispenser' | 'Incubator' | 'Arm';
    has_deck: boolean;
    capabilities?: Record<string, unknown>;
    capabilities_config?: any;
}

export interface PlrBackendDefinition {
    accession_id: string;
    name: string;
    fqn: string;
    frontend_definition_accession_id: string;
    description?: string;
    backend_type: 'hardware' | 'simulator';
    connection_config?: any;
    manufacturer?: string;
    model?: string;
}

// Fallback/Override capabilities for machines that don't expose them statically (e.g. auto-detected hardware)
// Used to allow configuration in offline/virtual modes.
export const OFFLINE_CAPABILITY_OVERRIDES: Record<string, any> = {
    'pylabrobot.liquid_handling.backends.hamilton.Starlet': {
        machine_type: 'Starlet',
        config_fields: [
            {
                field_name: 'has_core96',
                display_name: '96-Channel Head (CoRe 96)',
                field_type: 'boolean',
                default_value: false,
                help_text: 'Includes the CoRe 96-channel head for high-throughput pipetting.'
            },
            {
                field_name: 'has_iswap',
                display_name: 'iSWAP Gripper',
                field_type: 'boolean',
                default_value: false,
                help_text: 'Includes the iSWAP gripper for plate transport.'
            }
        ]
    }
};

// ============================================================================
// PLATES
// ============================================================================
const PLATES: PlrResourceDefinition[] = [
    // Corning plates
    { accession_id: 'plr-plate-001', name: 'Cor_96_wellplate_360ul_Fb', fqn: 'pylabrobot.resources.corning_costar.plates.Cor_96_wellplate_360ul_Fb', plr_category: 'Plate', vendor: 'Corning', description: 'Corning 96-well flat bottom plate, 360µL', num_items: 96, is_consumable: true, is_reusable: true, properties_json: { wells: 96, volume_ul: 360, well_shape: 'flat' } },
    { accession_id: 'plr-plate-002', name: 'Cor_384_wellplate_112ul_Fb', fqn: 'pylabrobot.resources.corning_costar.plates.Cor_384_wellplate_112ul_Fb', plr_category: 'Plate', vendor: 'Corning', description: 'Corning 384-well flat bottom plate', num_items: 384, is_consumable: true, is_reusable: true, properties_json: { wells: 384, volume_ul: 112, well_shape: 'flat' } },
    { accession_id: 'plr-plate-003', name: 'Cor_96_wellplate_Vb', fqn: 'pylabrobot.resources.corning_costar.plates.Cor_96_wellplate_Vb', plr_category: 'Plate', vendor: 'Corning', description: 'Corning 96-well V-bottom plate', num_items: 96, is_consumable: true, is_reusable: true, properties_json: { wells: 96, well_shape: 'V-bottom' } },

    // Greiner plates
    { accession_id: 'plr-plate-010', name: 'Gre_96_Fl_Fb', fqn: 'pylabrobot.resources.greiner.plates.Gre_96_Fl_Fb', plr_category: 'Plate', vendor: 'Greiner', description: 'Greiner 96-well flat bottom plate', num_items: 96, is_consumable: true, is_reusable: true, properties_json: { wells: 96, well_shape: 'flat' } },
    { accession_id: 'plr-plate-011', name: 'Gre_384_Sq_Fb', fqn: 'pylabrobot.resources.greiner.plates.Gre_384_Sq_Fb', plr_category: 'Plate', vendor: 'Greiner', description: 'Greiner 384-well square flat bottom', num_items: 384, is_consumable: true, is_reusable: true, properties_json: { wells: 384, well_shape: 'square' } },
    { accession_id: 'plr-plate-012', name: 'Gre_96_DWP_2mL_Rb', fqn: 'pylabrobot.resources.greiner.plates.Gre_96_DWP_2mL_Rb', plr_category: 'Plate', vendor: 'Greiner', description: 'Greiner 96 deep well plate 2mL round bottom', num_items: 96, is_consumable: true, is_reusable: true, properties_json: { wells: 96, volume_ul: 2000, well_shape: 'round', deep_well: true } },

    // Thermo Fisher plates
    { accession_id: 'plr-plate-020', name: 'Thermo_96_Nunc_Fb', fqn: 'pylabrobot.resources.thermo_fisher.plates.Thermo_96_Nunc_Fb', plr_category: 'Plate', vendor: 'Thermo Fisher', description: 'Thermo Nunc 96-well flat bottom', num_items: 96, is_consumable: true, is_reusable: true, properties_json: { wells: 96, well_shape: 'flat' } },
    { accession_id: 'plr-plate-021', name: 'Thermo_384_Nunc_Fb', fqn: 'pylabrobot.resources.thermo_fisher.plates.Thermo_384_Nunc_Fb', plr_category: 'Plate', vendor: 'Thermo Fisher', description: 'Thermo Nunc 384-well flat bottom', num_items: 384, is_consumable: true, is_reusable: true, properties_json: { wells: 384, well_shape: 'flat' } },

    // Eppendorf plates
    { accession_id: 'plr-plate-030', name: 'Epp_96_DWP_1mL', fqn: 'pylabrobot.resources.eppendorf.plates.Epp_96_DWP_1mL', plr_category: 'Plate', vendor: 'Eppendorf', description: 'Eppendorf 96 deep well plate 1mL', num_items: 96, is_consumable: true, is_reusable: true, properties_json: { wells: 96, volume_ul: 1000, deep_well: true } },

    // Bio-Rad plates
    { accession_id: 'plr-plate-040', name: 'BioRad_96_PCR', fqn: 'pylabrobot.resources.biorad.plates.BioRad_96_PCR', plr_category: 'Plate', vendor: 'Bio-Rad', description: 'Bio-Rad 96-well PCR plate', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { wells: 96, pcr_compatible: true } },
];

// ============================================================================
// TIP RACKS
// ============================================================================
const TIP_RACKS: PlrResourceDefinition[] = [
    // Hamilton tips
    { accession_id: 'plr-tips-001', name: 'HT_P_300uL_NTR_96', fqn: 'pylabrobot.resources.hamilton.tips.HT_P_300uL_NTR_96', plr_category: 'TipRack', vendor: 'Hamilton', description: 'Hamilton 300µL non-filtered tips', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 300, filtered: false } },
    { accession_id: 'plr-tips-002', name: 'HT_P_1000uL_NTR_96', fqn: 'pylabrobot.resources.hamilton.tips.HT_P_1000uL_NTR_96', plr_category: 'TipRack', vendor: 'Hamilton', description: 'Hamilton 1000µL non-filtered tips', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 1000, filtered: false } },
    { accession_id: 'plr-tips-003', name: 'HT_P_50uL_F_96', fqn: 'pylabrobot.resources.hamilton.tips.HT_P_50uL_F_96', plr_category: 'TipRack', vendor: 'Hamilton', description: 'Hamilton 50µL filtered tips', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 50, filtered: true } },

    // Opentrons tips
    { accession_id: 'plr-tips-010', name: 'opentrons_96_tiprack_300ul', fqn: 'pylabrobot.resources.opentrons.tip_racks.opentrons_96_tiprack_300ul', plr_category: 'TipRack', vendor: 'Opentrons', description: 'Opentrons 300µL tip rack', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 300 } },
    { accession_id: 'plr-tips-011', name: 'opentrons_96_tiprack_20ul', fqn: 'pylabrobot.resources.opentrons.tip_racks.opentrons_96_tiprack_20ul', plr_category: 'TipRack', vendor: 'Opentrons', description: 'Opentrons 20µL tip rack', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 20 } },
    { accession_id: 'plr-tips-012', name: 'opentrons_96_tiprack_1000ul', fqn: 'pylabrobot.resources.opentrons.tip_racks.opentrons_96_tiprack_1000ul', plr_category: 'TipRack', vendor: 'Opentrons', description: 'Opentrons 1000µL tip rack', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 1000 } },

    // Tecan tips
    { accession_id: 'plr-tips-020', name: 'Tecan_DiTi_200ul', fqn: 'pylabrobot.resources.tecan.tips.Tecan_DiTi_200ul', plr_category: 'TipRack', vendor: 'Tecan', description: 'Tecan 200µL disposable tips', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 200, disposable: true } },
    { accession_id: 'plr-tips-021', name: 'Tecan_DiTi_1000ul', fqn: 'pylabrobot.resources.tecan.tips.Tecan_DiTi_1000ul', plr_category: 'TipRack', vendor: 'Tecan', description: 'Tecan 1000µL disposable tips', num_items: 96, is_consumable: true, is_reusable: false, properties_json: { tips: 96, volume_ul: 1000, disposable: true } },
];

// ============================================================================
// RESERVOIRS / TROUGHS
// ============================================================================
const RESERVOIRS: PlrResourceDefinition[] = [
    { accession_id: 'plr-res-001', name: 'Agilent_1_reservoir_290ml', fqn: 'pylabrobot.resources.agilent.troughs.Agilent_1_reservoir_290ml', plr_category: 'Reservoir', vendor: 'Agilent', description: 'Agilent 290mL single-well reservoir', num_items: 1, is_consumable: false, is_reusable: true, properties_json: { wells: 1, volume_ml: 290 } },
    { accession_id: 'plr-res-002', name: 'Nest_12_reservoir_15ml', fqn: 'pylabrobot.resources.nest.troughs.Nest_12_reservoir_15ml', plr_category: 'Reservoir', vendor: 'Nest', description: 'Nest 12-channel reservoir 15mL per channel', num_items: 12, is_consumable: false, is_reusable: true, properties_json: { wells: 12, volume_ml: 15 } },
    { accession_id: 'plr-res-003', name: 'USA_Scientific_12_reservoir_22ml', fqn: 'pylabrobot.resources.usascientific.troughs.USA_Scientific_12_reservoir_22ml', plr_category: 'Reservoir', vendor: 'USA Scientific', description: 'USA Scientific 12-channel reservoir', num_items: 12, is_consumable: false, is_reusable: true, properties_json: { wells: 12, volume_ml: 22 } },
    { accession_id: 'plr-res-004', name: 'Generic_1_trough_100ml', fqn: 'pylabrobot.resources.generic.troughs.Generic_1_trough_100ml', plr_category: 'Reservoir', vendor: 'Generic', description: 'Generic single-well trough 100mL', num_items: 1, is_consumable: true, is_reusable: false, properties_json: { wells: 1, volume_ml: 100 } },
];

// ============================================================================
// CARRIERS
// ============================================================================
const CARRIERS: PlrResourceDefinition[] = [
    // Hamilton carriers
    { accession_id: 'plr-car-001', name: 'PLT_CAR_L5AC_A00', fqn: 'pylabrobot.resources.hamilton.carriers.PLT_CAR_L5AC_A00', plr_category: 'Carrier', vendor: 'Hamilton', description: 'Hamilton 5-position plate carrier', num_items: 5, is_consumable: false, is_reusable: true, properties_json: { positions: 5, carrier_type: 'plate' } },
    { accession_id: 'plr-car-002', name: 'TIP_CAR_480_A00', fqn: 'pylabrobot.resources.hamilton.carriers.TIP_CAR_480_A00', plr_category: 'Carrier', vendor: 'Hamilton', description: 'Hamilton tip carrier (480 tips)', num_items: 5, is_consumable: false, is_reusable: true, properties_json: { positions: 5, carrier_type: 'tip' } },
    { accession_id: 'plr-car-003', name: 'TIP_CAR_288_A00', fqn: 'pylabrobot.resources.hamilton.carriers.TIP_CAR_288_A00', plr_category: 'Carrier', vendor: 'Hamilton', description: 'Hamilton tip carrier (288 tips)', num_items: 3, is_consumable: false, is_reusable: true, properties_json: { positions: 3, carrier_type: 'tip' } },

    // Tecan carriers
    { accession_id: 'plr-car-010', name: 'MP_3Pos_Fixed', fqn: 'pylabrobot.resources.tecan.carriers.MP_3Pos_Fixed', plr_category: 'Carrier', vendor: 'Tecan', description: 'Tecan 3-position microplate carrier', num_items: 3, is_consumable: false, is_reusable: true, properties_json: { positions: 3, carrier_type: 'plate' } },
    { accession_id: 'plr-car-011', name: 'DiTi_4Pos', fqn: 'pylabrobot.resources.tecan.carriers.DiTi_4Pos', plr_category: 'Carrier', vendor: 'Tecan', description: 'Tecan 4-position DiTi carrier', num_items: 4, is_consumable: false, is_reusable: true, properties_json: { positions: 4, carrier_type: 'tip' } },
];

// ============================================================================
// TUBES
// ============================================================================
const TUBES: PlrResourceDefinition[] = [
    { accession_id: 'plr-tube-001', name: 'Eppendorf_1_5mL', fqn: 'pylabrobot.resources.eppendorf.tubes.Eppendorf_1_5mL', plr_category: 'Tube', vendor: 'Eppendorf', description: 'Eppendorf 1.5mL microcentrifuge tube', num_items: 1, is_consumable: true, is_reusable: true, properties_json: { volume_ml: 1.5 } },
    { accession_id: 'plr-tube-002', name: 'Eppendorf_2mL', fqn: 'pylabrobot.resources.eppendorf.tubes.Eppendorf_2mL', plr_category: 'Tube', vendor: 'Eppendorf', description: 'Eppendorf 2mL microcentrifuge tube', num_items: 1, is_consumable: true, is_reusable: true, properties_json: { volume_ml: 2 } },
    { accession_id: 'plr-tube-003', name: 'Falcon_15mL', fqn: 'pylabrobot.resources.corning.falcon.tubes.Falcon_15mL', plr_category: 'Tube', vendor: 'Corning', description: 'Falcon 15mL conical tube', num_items: 1, is_consumable: true, is_reusable: true, properties_json: { volume_ml: 15, conical: true } },
    { accession_id: 'plr-tube-004', name: 'Falcon_50mL', fqn: 'pylabrobot.resources.corning.falcon.tubes.Falcon_50mL', plr_category: 'Tube', vendor: 'Corning', description: 'Falcon 50mL conical tube', num_items: 1, is_consumable: true, is_reusable: true, properties_json: { volume_ml: 50, conical: true } },
];

// ============================================================================
// MACHINES
// ============================================================================
export const PLR_MACHINE_DEFINITIONS: PlrMachineDefinition[] = [
    // Hamilton
    { accession_id: 'plr-mach-001', name: 'STAR', fqn: 'pylabrobot.liquid_handling.backends.hamilton.STAR', vendor: 'Hamilton', description: 'Hamilton STAR liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { channels: 8, volume_range: '0.5-1000µL' }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },
    { accession_id: 'plr-mach-002', name: 'Starlet', fqn: 'pylabrobot.liquid_handling.backends.hamilton.Starlet', vendor: 'Hamilton', description: 'Hamilton Starlet liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { channels: 8, volume_range: '0.5-1000µL' }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },
    { accession_id: 'plr-mach-003', name: 'Vantage', fqn: 'pylabrobot.liquid_handling.backends.hamilton.Vantage', vendor: 'Hamilton', description: 'Hamilton Vantage liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { channels: 8, volume_range: '0.5-1000µL' }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },

    // Opentrons
    { accession_id: 'plr-mach-010', name: 'OT2', fqn: 'pylabrobot.liquid_handling.backends.opentrons.OT2', vendor: 'Opentrons', description: 'Opentrons OT-2 liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { pipettes: 2, deck_slots: 11 }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },
    { accession_id: 'plr-mach-011', name: 'Flex', fqn: 'pylabrobot.liquid_handling.backends.opentrons.Flex', vendor: 'Opentrons', description: 'Opentrons Flex liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { pipettes: 2, deck_slots: 12 }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },

    // Tecan
    { accession_id: 'plr-mach-020', name: 'EVO', fqn: 'pylabrobot.liquid_handling.backends.tecan.EVO', vendor: 'Tecan', description: 'Tecan Freedom EVO liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { channels: 8 }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },
    { accession_id: 'plr-mach-021', name: 'Fluent', fqn: 'pylabrobot.liquid_handling.backends.tecan.Fluent', vendor: 'Tecan', description: 'Tecan Fluent liquid handler', has_deck: true, machine_type: 'LiquidHandler', properties_json: { channels: 8 }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler' },

    // Plate readers
    { accession_id: 'plr-mach-030', name: 'CLARIOstarBackend', fqn: 'pylabrobot.plate_reading.clario_star_backend.CLARIOstarBackend', vendor: 'BMG Labtech', description: 'BMG CLARIOstar plate reader backend', has_deck: false, machine_type: 'PlateReader', properties_json: { detection_modes: ['absorbance', 'fluorescence', 'luminescence'] }, frontend_fqn: 'pylabrobot.plate_reading.PlateReader' },
    { accession_id: 'plr-mach-031', name: 'SPECTROstar', fqn: 'pylabrobot.plate_reading.backends.bmg.SPECTROstar', vendor: 'BMG Labtech', description: 'BMG SPECTROstar plate reader', has_deck: false, machine_type: 'PlateReader', properties_json: { detection_modes: ['absorbance'] }, frontend_fqn: 'pylabrobot.plate_reading.PlateReader' },

    // Shakers
    { accession_id: 'plr-mach-040', name: 'HamiltonHeaterShaker', fqn: 'pylabrobot.heating_shaking.backends.hamilton.HamiltonHeaterShaker', vendor: 'Hamilton', description: 'Hamilton heater shaker', has_deck: false, machine_type: 'Shaker', properties_json: { temp_range: '4-105°C', rpm_range: '100-2000' }, frontend_fqn: 'pylabrobot.heating_shaking.HeaterShaker' },
    { accession_id: 'plr-mach-041', name: 'InhecoTEC', fqn: 'pylabrobot.heating_shaking.backends.inheco.InhecoTEC', vendor: 'Inheco', description: 'Inheco TEC controller', has_deck: false, machine_type: 'Shaker', properties_json: { temp_range: '4-110°C' }, frontend_fqn: 'pylabrobot.heating_shaking.HeaterShaker' },

    // Generic Simulated Frontends
    { accession_id: 'sim-mach-001', name: 'Simulated Liquid Handler', fqn: 'praxis.simulated.LiquidHandler', vendor: 'PyLabRobot', description: 'Simulated Liquid Handler - select backend at instantiation', has_deck: true, machine_type: 'LiquidHandler', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.liquid_handling.LiquidHandler', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.liquid_handling.backends.ChatterboxBackend', 'pylabrobot.liquid_handling.backends.LiquidHandlerChatterboxBackend'] },
    { accession_id: 'sim-mach-002', name: 'Simulated Plate Reader', fqn: 'praxis.simulated.PlateReader', vendor: 'PyLabRobot', description: 'Simulated Plate Reader - select backend at instantiation', has_deck: false, machine_type: 'PlateReader', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.plate_reading.PlateReader', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.plate_reading.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-003', name: 'Simulated Heater Shaker', fqn: 'praxis.simulated.HeaterShaker', vendor: 'PyLabRobot', description: 'Simulated Heater Shaker - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.heating_shaking.HeaterShaker', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.heating_shaking.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-004', name: 'Simulated Shaker', fqn: 'praxis.simulated.Shaker', vendor: 'PyLabRobot', description: 'Simulated Shaker - select backend at instantiation', has_deck: false, machine_type: 'Shaker', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.shaking.Shaker', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.shaking.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-005', name: 'Simulated Temperature Controller', fqn: 'praxis.simulated.TemperatureController', vendor: 'PyLabRobot', description: 'Simulated Temperature Controller - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.temperature_controlling.TemperatureController', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.temperature_controlling.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-006', name: 'Simulated Centrifuge', fqn: 'praxis.simulated.Centrifuge', vendor: 'PyLabRobot', description: 'Simulated Centrifuge - select backend at instantiation', has_deck: false, machine_type: 'Centrifuge', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.centrifuging.Centrifuge', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.centrifuging.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-007', name: 'Simulated Thermocycler', fqn: 'praxis.simulated.Thermocycler', vendor: 'PyLabRobot', description: 'Simulated Thermocycler - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.thermocycling.Thermocycler', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.thermocycling.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-008', name: 'Simulated Pump', fqn: 'praxis.simulated.Pump', vendor: 'PyLabRobot', description: 'Simulated Pump - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.pumping.Pump', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.pumping.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-009', name: 'Simulated Pump Array', fqn: 'praxis.simulated.PumpArray', vendor: 'PyLabRobot', description: 'Simulated Pump Array - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.pumping.PumpArray', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.pumping.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-010', name: 'Simulated Fan', fqn: 'praxis.simulated.Fan', vendor: 'PyLabRobot', description: 'Simulated Fan - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.fans.Fan', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.fans.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-011', name: 'Simulated Plate Sealer', fqn: 'praxis.simulated.Sealer', vendor: 'PyLabRobot', description: 'Simulated Plate Sealer - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.plate_sealing.Sealer', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.plate_sealing.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-012', name: 'Simulated Plate Peeler', fqn: 'praxis.simulated.Peeler', vendor: 'PyLabRobot', description: 'Simulated Plate Peeler - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.plate_peeling.Peeler', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.plate_peeling.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-013', name: 'Simulated Powder Dispenser', fqn: 'praxis.simulated.PowderDispenser', vendor: 'PyLabRobot', description: 'Simulated Powder Dispenser - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.powder_dispensing.PowderDispenser', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.powder_dispensing.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-014', name: 'Simulated Incubator', fqn: 'praxis.simulated.Incubator', vendor: 'PyLabRobot', description: 'Simulated Incubator - select backend at instantiation', has_deck: false, machine_type: 'Incubator', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.incubating.Incubator', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.incubating.backends.ChatterboxBackend'] },
    { accession_id: 'sim-mach-015', name: 'Simulated SCARA Robot', fqn: 'praxis.simulated.SCARA', vendor: 'PyLabRobot', description: 'Simulated SCARA Robot - select backend at instantiation', has_deck: false, machine_type: 'Other', properties_json: { simulated: true }, frontend_fqn: 'pylabrobot.scara.SCARA', is_simulated_frontend: true, available_simulation_backends: ['pylabrobot.scara.backends.ChatterboxBackend'] },
];

// ============================================================================
// NEW FRONTEND AND BACKEND DEFINITIONS
// ============================================================================

export const PLR_FRONTEND_DEFINITIONS: PlrFrontendDefinition[] = [
    { accession_id: 'fdef-lh', name: 'Liquid Handler', fqn: 'pylabrobot.liquid_handling.LiquidHandler', machine_category: 'LiquidHandler', has_deck: true },
    { accession_id: 'fdef-pr', name: 'Plate Reader', fqn: 'pylabrobot.plate_reading.PlateReader', machine_category: 'PlateReader', has_deck: false },
    { accession_id: 'fdef-img', name: 'Imager', fqn: 'pylabrobot.plate_reading.Imager', machine_category: 'Imager', has_deck: false },
    { accession_id: 'fdef-hs', name: 'Heater Shaker', fqn: 'pylabrobot.heating_shaking.HeaterShaker', machine_category: 'HeaterShaker', has_deck: false },
    { accession_id: 'fdef-sh', name: 'Shaker', fqn: 'pylabrobot.shaking.Shaker', machine_category: 'Shaker', has_deck: false },
    { accession_id: 'fdef-tc', name: 'Temperature Controller', fqn: 'pylabrobot.temperature_controlling.TemperatureController', machine_category: 'TemperatureController', has_deck: false },
    { accession_id: 'fdef-ce', name: 'Centrifuge', fqn: 'pylabrobot.centrifuging.Centrifuge', machine_category: 'Centrifuge', has_deck: false },
    { accession_id: 'fdef-th', name: 'Thermocycler', fqn: 'pylabrobot.thermocycling.Thermocycler', machine_category: 'Thermocycler', has_deck: false },
    { accession_id: 'fdef-pu', name: 'Pump', fqn: 'pylabrobot.pumping.Pump', machine_category: 'Pump', has_deck: false },
    { accession_id: 'fdef-pa', name: 'Pump Array', fqn: 'pylabrobot.pumping.PumpArray', machine_category: 'PumpArray', has_deck: false },
    { accession_id: 'fdef-fa', name: 'Fan', fqn: 'pylabrobot.fans.Fan', machine_category: 'Fan', has_deck: false },
    { accession_id: 'fdef-se', name: 'Plate Sealer', fqn: 'pylabrobot.plate_sealing.Sealer', machine_category: 'Sealer', has_deck: false },
    { accession_id: 'fdef-pee', name: 'Plate Peeler', fqn: 'pylabrobot.plate_peeling.Peeler', machine_category: 'Peeler', has_deck: false },
    { accession_id: 'fdef-po', name: 'Powder Dispenser', fqn: 'pylabrobot.powder_dispensing.PowderDispenser', machine_category: 'PowderDispenser', has_deck: false },
    { accession_id: 'fdef-in', name: 'Incubator', fqn: 'pylabrobot.incubating.Incubator', machine_category: 'Incubator', has_deck: false },
    { accession_id: 'fdef-sc', name: 'SCARA Robot', fqn: 'pylabrobot.scara.SCARA', machine_category: 'Arm', has_deck: false },
];

export const PLR_BACKEND_DEFINITIONS: PlrBackendDefinition[] = PLR_MACHINE_DEFINITIONS.map(m => {
    let frontendId = 'fdef-lh';
    if (m.frontend_fqn === 'pylabrobot.plate_reading.PlateReader') frontendId = 'fdef-pr';
    else if (m.frontend_fqn === 'pylabrobot.heating_shaking.HeaterShaker') frontendId = 'fdef-hs';
    else if (m.frontend_fqn === 'pylabrobot.shaking.Shaker') frontendId = 'fdef-sh';
    else if (m.frontend_fqn === 'pylabrobot.temperature_controlling.TemperatureController') frontendId = 'fdef-tc';
    else if (m.frontend_fqn === 'pylabrobot.centrifuging.Centrifuge') frontendId = 'fdef-ce';
    else if (m.frontend_fqn === 'pylabrobot.thermocycling.Thermocycler') frontendId = 'fdef-th';
    else if (m.frontend_fqn === 'pylabrobot.pumping.Pump') frontendId = 'fdef-pu';
    else if (m.frontend_fqn === 'pylabrobot.pumping.PumpArray') frontendId = 'fdef-pa';
    else if (m.frontend_fqn === 'pylabrobot.fans.Fan') frontendId = 'fdef-fa';
    else if (m.frontend_fqn === 'pylabrobot.plate_sealing.Sealer') frontendId = 'fdef-se';
    else if (m.frontend_fqn === 'pylabrobot.plate_peeling.Peeler') frontendId = 'fdef-pee';
    else if (m.frontend_fqn === 'pylabrobot.powder_dispensing.PowderDispenser') frontendId = 'fdef-po';
    else if (m.frontend_fqn === 'pylabrobot.incubating.Incubator') frontendId = 'fdef-in';
    else if (m.frontend_fqn === 'pylabrobot.plate_reading.Imager') frontendId = 'fdef-img';
    else if (m.frontend_fqn === 'pylabrobot.scara.SCARA') frontendId = 'fdef-sc';

    return {
        accession_id: m.accession_id.replace('mach', 'bdef').replace('sim-', 'sim-bdef-'),
        name: m.name,
        fqn: m.fqn,
        frontend_definition_accession_id: frontendId,
        description: m.description,
        backend_type: (m.fqn.includes('Chatterbox') || m.fqn.includes('praxis.simulated')) ? 'simulator' : 'hardware',
        manufacturer: m.vendor,
        model: m.name
    };
});


// ============================================================================
// COMBINED EXPORTS
// ============================================================================
export const PLR_RESOURCE_DEFINITIONS: PlrResourceDefinition[] = [
    ...PLATES,
    ...TIP_RACKS,
    ...RESERVOIRS,
    ...CARRIERS,
    ...TUBES,
];

// Summary stats
export const PLR_DEFINITION_STATS = {
    plates: PLATES.length,
    tipRacks: TIP_RACKS.length,
    reservoirs: RESERVOIRS.length,
    carriers: CARRIERS.length,
    tubes: TUBES.length,
    machines: PLR_MACHINE_DEFINITIONS.length,
    total: PLR_RESOURCE_DEFINITIONS.length + PLR_MACHINE_DEFINITIONS.length,
};

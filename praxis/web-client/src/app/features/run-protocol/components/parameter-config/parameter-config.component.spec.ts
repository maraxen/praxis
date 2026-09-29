import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { FormlyModule } from '@ngx-formly/core';
import { ParameterMetadata, ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { ParameterConfigComponent } from './parameter-config.component';

describe('ParameterConfigComponent', () => {
    let component: ParameterConfigComponent;
    let fixture: ComponentFixture<ParameterConfigComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                ParameterConfigComponent,
                ReactiveFormsModule,
                FormlyModule.forRoot(),
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(ParameterConfigComponent);
        component = fixture.componentInstance;
        component.formGroup = new FormGroup({});
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should group linked parameters into a row', () => {
        const mockProtocol: ProtocolDefinition = {
            accession_id: '123',
            name: 'Linked Test',
            version: '1.0.0',
            is_top_level: true,
            assets: [],
            parameters: [
                {
                    name: 'param1',
                    type_hint: 'float',
                    fqn: 'float',
                    is_deck_param: false,
                    optional: false,
                    constraints: {},
                    linked_to: 'param2'
                } as ParameterMetadata,
                {
                    name: 'param2',
                    type_hint: 'float',
                    fqn: 'float',
                    is_deck_param: false,
                    optional: false,
                    constraints: {},
                    linked_to: 'param1'
                } as ParameterMetadata
            ]
        };

        component.protocol = mockProtocol;
        component.ngOnChanges({
            protocol: {
                currentValue: mockProtocol,
                previousValue: null,
                firstChange: true,
                isFirstChange: () => true
            }
        });

        const fields = component.paramFields();
        expect(fields.length).toBe(1); // Should be 1 group
        expect(fields[0].fieldGroupClassName).toBe('linked-parameter-row');
        expect(fields[0].fieldGroup?.length).toBe(3); // param1, checkbox, param2
        expect(fields[0].fieldGroup![0].key).toBe('param1');
        expect(fields[0].fieldGroup![1].key).toContain('_unlink_');
        expect(fields[0].fieldGroup![1].type).toBe('checkbox');
        expect(fields[0].fieldGroup![2].key).toBe('param2');
    });

    it('should not group independent parameters', () => {
        const mockProtocol: ProtocolDefinition = {
            accession_id: '456',
            name: 'Independent Test',
            version: '1.0.0',
            is_top_level: true,
            assets: [],
            parameters: [
                {
                    name: 'param1',
                    type_hint: 'int',
                    fqn: 'int',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata,
                {
                    name: 'param2',
                    type_hint: 'str',
                    fqn: 'str',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata
            ]
        };

        component.protocol = mockProtocol;
        component.ngOnChanges({
            protocol: {
                currentValue: mockProtocol,
                previousValue: null,
                firstChange: true,
                isFirstChange: () => true
            }
        });

        const fields = component.paramFields();
        expect(fields.length).toBe(2);
        expect(fields[0].key).toBe('param1');
        expect(fields[1].key).toBe('param2');
    });

    it('should filter out machine/resource parameters', () => {
        const mockProtocol: ProtocolDefinition = {
            accession_id: '789',
            name: 'Machine Filter Test',
            version: '1.0.0',
            is_top_level: true,
            assets: [
                {
                    accession_id: 'asset-1',
                    name: 'lh',
                    fqn: 'pylabrobot.legacy.liquid_handling.LiquidHandler',
                    type_hint_str: 'LiquidHandler',
                    optional: false,
                    constraints: {
                        required_methods: [],
                        required_attributes: [],
                        required_method_signatures: {},
                        required_method_args: {}
                    },
                    location_constraints: {
                        location_requirements: [],
                        on_resource_type: '',
                        stack: false,
                        directly_position: false,
                        position_condition: []
                    }
                }
            ],
            parameters: [
                {
                    name: 'lh',
                    type_hint: 'pylabrobot.legacy.liquid_handling.LiquidHandler',
                    fqn: 'pylabrobot.legacy.liquid_handling.LiquidHandler',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata,
                {
                    name: 'volume',
                    type_hint: 'float',
                    fqn: 'float',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata,
                {
                    name: 'plate',
                    type_hint: 'pylabrobot.resources.Plate',
                    fqn: 'pylabrobot.resources.Plate',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata
            ]
        };

        component.protocol = mockProtocol;
        component.ngOnChanges({
            protocol: {
                currentValue: mockProtocol,
                previousValue: null,
                firstChange: true,
                isFirstChange: () => true
            }
        });

        const fields = component.paramFields();
        // Should only have 'volume' - 'lh' and 'plate' should be filtered out
        expect(fields.length).toBe(1);
        expect(fields[0].key).toBe('volume');
    });

    it('should filter out well parameters', () => {
        const mockProtocol: ProtocolDefinition = {
            accession_id: 'abc',
            name: 'Well Filter Test',
            version: '1.0.0',
            is_top_level: true,
            assets: [],
            parameters: [
                {
                    name: 'source_wells',
                    type_hint: 'Sequence[Well]',
                    fqn: 'Sequence',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata,
                {
                    name: 'incubation_time',
                    type_hint: 'float',
                    fqn: 'float',
                    is_deck_param: false,
                    optional: false,
                    constraints: {}
                } as ParameterMetadata,
                {
                    name: 'target_well_ids',
                    type_hint: 'List[str]',
                    fqn: 'List',
                    is_deck_param: false,
                    optional: false,
                    constraints: {},
                    ui_hint: { type: 'well_selector' }
                } as ParameterMetadata
            ]
        };

        component.protocol = mockProtocol;
        component.ngOnChanges({
            protocol: {
                currentValue: mockProtocol,
                previousValue: null,
                firstChange: true,
                isFirstChange: () => true
            }
        });

        const fields = component.paramFields();
        // Should only have 'incubation_time'
        expect(fields.length).toBe(1);
        expect(fields[0].key).toBe('incubation_time');
    });
});

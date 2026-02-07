import { ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges, signal } from '@angular/core';

import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatDividerModule } from '@angular/material/divider';
import { FormlyFieldConfig, FormlyModule } from '@ngx-formly/core';
import { ParameterMetadata, ProtocolDefinition } from '@features/protocols/models/protocol.models';

@Component({
  selector: 'app-parameter-config',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    FormlyModule,
    MatDividerModule
  ],
  template: `
    <div class="parameter-config-container">
      @if (hasParameters()) {
        <section class="section-header">
          <h3>Parameters</h3>
          <p class="section-subtitle">Configure the protocol execution parameters</p>
        </section>
        <formly-form [form]="formGroup" [fields]="paramFields()" [model]="model"></formly-form>
      }

      @if (!hasParameters()) {
        <div class="empty-state">
          <p>This protocol has no configurable parameters.</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .parameter-config-container {
      padding: 16px 0;
    }
    .section-header {
      margin-bottom: 16px;
    }
    .section-header h3 {
      margin: 0 0 4px;
      font-size: 1.1rem;
    }
    .section-subtitle {
      margin: 0;
      color: var(--sys-on-surface-variant);
      font-size: 0.9rem;
    }
    mat-divider {
      margin: 24px 0;
    }
    .empty-state {
      text-align: center;
      padding: 32px;
      color: var(--sys-on-surface-variant);
    }
    ::ng-deep .linked-parameter-row {
      display: flex;
      gap: 16px;
      align-items: center; /* Center align with checkbox */
    }
    ::ng-deep .linked-parameter-row > .flex-grow {
      flex: 1;
      width: 0;
    }
    ::ng-deep .unlink-toggle {
      margin-top: 16px; /* Align with input fields mostly */
      min-width: 80px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParameterConfigComponent implements OnChanges {
  @Input() protocol: ProtocolDefinition | null = null;
  @Input() formGroup: FormGroup = new FormGroup({});

  model: Record<string, unknown> = {};
  paramFields = signal<FormlyFieldConfig[]>([]);

  hasParameters = signal(false);

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['protocol'] && this.protocol) {
      this.buildForm(this.protocol);
    }
  }

  private buildForm(protocol: ProtocolDefinition) {
    // Filter out:
    // 1. Deck parameters (handled by deck setup)
    // 2. State parameter (internal)
    // 3. Machine/resource parameters (handled by asset selection)
    const params = (protocol.parameters || []).filter(p => {
      // Skip deck params and state
      if (p.is_deck_param || p.name === 'state') return false;

      // Skip if this parameter matches an asset requirement by name or fqn
      if (this.isAssetParameter(p, protocol)) return false;

      // Allow itemized/index selectors explicitly
      if (['itemized-selector', 'index_selector', 'dict-input'].includes(p.field_type || '')) {
        return true;
      }

      // Skip well parameters
      if (this.isWellParameter(p)) return false;

      return true;
    });

    const paramConfigs: FormlyFieldConfig[] = [];
    const processedParams = new Set<string>();

    for (const param of params) {
      if (processedParams.has(param.name)) continue;

      // Check for linked parameters
      if (param.linked_to) {
        const partner = params.find(p => p.name === param.linked_to);

        // If partner exists and hasn't been processed yet
        if (partner && !processedParams.has(partner.name)) {
          const unlinkKey = `_unlink_${param.name}_${partner.name}`;

          // Modify fields to handle dynamic linking
          const param1Field = this.createParamField(param);
          const param2Field = this.createParamField(partner);

          // Add expression properties for linking
          param1Field.expressionProperties = {
            'props.linkedTo': (model: any) => model[unlinkKey] ? null : partner.name
          };
          param2Field.expressionProperties = {
            'props.linkedTo': (model: any) => model[unlinkKey] ? null : param.name
          };

          // Add them as a side-by-side group with an unlink toggle
          paramConfigs.push({
            fieldGroupClassName: 'linked-parameter-row',
            fieldGroup: [
              { ...param1Field, className: 'flex-grow' },
              {
                key: unlinkKey,
                type: 'checkbox',
                defaultValue: false,
                className: 'unlink-toggle',
                props: {
                  label: 'Unlink',
                  attributes: {
                    title: 'Unlink these parameters to select independently'
                  }
                }
              },
              { ...param2Field, className: 'flex-grow' }
            ]
          });
          processedParams.add(param.name);
          processedParams.add(partner.name);
          continue;
        }
      }

      // Default: add single field
      paramConfigs.push(this.createParamField(param));
      processedParams.add(param.name);
    }

    this.paramFields.set(paramConfigs);
    this.hasParameters.set(paramConfigs.length > 0);

    // Initialize model with defaults
    protocol.parameters?.forEach(param => {
      if (param.default_value_repr && param.default_value_repr !== 'None') {
        try {
          this.model[param.name] = JSON.parse(param.default_value_repr);
        } catch {
          this.model[param.name] = param.default_value_repr;
        }
      }
    });
  }

  private createParamField(param: ParameterMetadata): FormlyFieldConfig {
    const baseConfig: FormlyFieldConfig = {
      key: param.name,
      props: {
        label: this.formatLabel(param.name),
        required: !param.optional,
        description: param.description,
      },
    };

    // Check for explicit dict input
    if (param.field_type === 'dict-input') {
      return {
        ...baseConfig,
        type: 'dict-input',
      };
    }

    // Check for explicit field_type from backend
    if ((param.field_type === 'index_selector' || param.field_type === 'itemized-selector') && param.itemized_spec) {
      return {
        ...baseConfig,
        type: 'index-selector',
        props: {
          ...baseConfig.props,
          itemsX: param.itemized_spec.items_x,
          itemsY: param.itemized_spec.items_y,
          linkedTo: param.linked_to,
          mode: (param.field_type === 'itemized-selector') ? 'multiple' : 'single',
        },
      };
    }

    // Map type to input type
    const typeHint = param.type_hint.toLowerCase();
    if (typeHint.includes('float') || typeHint.includes('int')) {
      return {
        ...baseConfig,
        type: 'input',
        props: {
          ...baseConfig.props,
          type: 'number',
          min: param.constraints.min_value,
          max: param.constraints.max_value,
        },
      };
    } else if (typeHint.includes('bool')) {
      return {
        ...baseConfig,
        type: 'checkbox',
      };
    } else if (param.constraints.options && param.constraints.options.length > 0) {
      return {
        ...baseConfig,
        type: 'select',
        props: {
          ...baseConfig.props,
          options: param.constraints.options.map(opt => ({ label: String(opt), value: opt })),
        },
      };
    } else {
      // Default: text input
      return {
        ...baseConfig,
        type: 'input',
        props: {
          ...baseConfig.props,
          type: 'text',
        },
      };
    }
  }

  private formatLabel(name: string): string {
    // Convert snake_case to Title Case
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  /**
   * Check if a parameter is an asset/machine/resource parameter that should
   * be filtered from the user-configurable form. These are handled by the
   * asset selection step instead.
   */
  private isAssetParameter(param: ParameterMetadata, protocol: ProtocolDefinition): boolean {
    // Check if this parameter matches an asset requirement by name or fqn
    const assetNames = protocol.assets?.map(a => a.name) || [];
    const assetFqns = protocol.assets?.map(a => a.fqn) || [];

    if (assetNames.includes(param.name) || assetFqns.includes(param.fqn)) {
      return true;
    }

    // Check for machine/resource type hints
    const machinePatterns = [
      'pylabrobot.machines',
      'pylabrobot.liquid_handling',
      'LiquidHandler',
      'Machine',
    ];

    const resourcePatterns = [
      'pylabrobot.resources',
      'Plate',
      'TipRack',
      'Carrier',
      'Deck',
    ];

    const typeHint = param.type_hint || '';

    return machinePatterns.some(p => typeHint.includes(p)) ||
      resourcePatterns.some(p => typeHint.includes(p));
  }

  private isWellParameter(param: ParameterMetadata): boolean {
    const name = (param.name || '').toLowerCase();

    // Check name patterns - hide if it looks like a well selection parameter
    // These are handled by the separate Well Selection step in the wizard
    const wellNamePatterns = ['well', 'wells', 'source_wells', 'target_wells', 'well_ids', 'indices'];
    if (wellNamePatterns.some(p => name.includes(p))) {
      return true;
    }

    // Check ui_hint if available
    const uiHint = (param as any).ui_hint;
    if (uiHint === 'well_selector' || uiHint?.type === 'well_selector') {
      return true;
    }

    return false;
  }
}

import { Component, Inject, ChangeDetectionStrategy } from '@angular/core';
import { humanize } from '@core/utils/plr-display.utils';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MachineDefinition } from '@features/assets/models/asset.models';

export interface SimulationConfigData {
  definition: MachineDefinition;
}

export interface SimulationConfigResult {
  name: string;
  simulation_backend_name: string;
}

@Component({
  selector: 'app-simulation-config-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule
  ],
  template: `
    <div class="p-6 min-w-[400px]">
      <div class="flex items-center gap-3 mb-6">
        <div class="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
          <mat-icon class="!w-6 !h-6 !text-[24px]">precision_manufacturing</mat-icon>
        </div>
        <div>
          <h2 class="text-xl font-bold text-sys-text-primary mb-1">Configure Simulation</h2>
          <p class="text-sys-text-secondary text-sm">{{ data.definition.name }} template</p>
        </div>
      </div>

      <form [formGroup]="form" class="flex flex-col gap-4">
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Instance Name</mat-label>
          <input matInput formControlName="name" placeholder="e.g. Hamilton STAR (Sim)">
          @if (form.get('name')?.hasError('required')) {
            <mat-error>Name is required</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Simulation Backend</mat-label>
          <mat-select formControlName="simulation_backend_name">
            @for (backend of backends; track backend) {
              <mat-option [value]="backend">{{ humanize(backend) }}</mat-option>
            }
          </mat-select>
          <mat-hint>Choose the driver for simulated interaction</mat-hint>
          @if (form.get('simulation_backend_name')?.hasError('required')) {
            <mat-error>Backend selection is required</mat-error>
          }
        </mat-form-field>
      </form>

      <div class="flex justify-end gap-3 mt-8">
        <button mat-button (click)="cancel()" class="!rounded-xl !px-6">Cancel</button>
        <button mat-flat-button color="primary" (click)="confirm()" 
                [disabled]="form.invalid" class="!rounded-xl !px-8 shadow-lg shadow-primary/20">
          Create Simulation
        </button>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SimulationConfigDialogComponent {
  humanize = humanize;
  form: FormGroup;
  backends: string[] = [];

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<SimulationConfigDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: SimulationConfigData
  ) {
    this.backends = data.definition.available_simulation_backends || ['Chatterbox', 'Simulator'];

    this.form = this.fb.group({
      name: [`${data.definition.name} (Sim)`, Validators.required],
      simulation_backend_name: [this.backends[0], Validators.required]
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }

  confirm(): void {
    if (this.form.valid) {
      this.dialogRef.close(this.form.value);
    }
  }
}

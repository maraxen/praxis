import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';

@Component({
  selector: 'app-interaction-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule
  ],
  template: `
    <h2 mat-dialog-title>Interaction Required</h2>
    <mat-dialog-content>
      <div *ngIf="data.interaction_type === 'pause'">
        <p>{{ data.payload.message }}</p>
      </div>

      <div *ngIf="data.interaction_type === 'confirm'">
        <p>{{ data.payload.message }}</p>
      </div>

      <div *ngIf="data.interaction_type === 'input'">
        <p>{{ data.payload.prompt }}</p>
        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Input</mat-label>
          <input matInput [(ngModel)]="inputValue">
        </mat-form-field>
      </div>

      <div *ngIf="data.interaction_type === 'device_connect'">
        <p>{{ data.payload.message || 'Connect your device to continue.' }}</p>
        <p class="hint" *ngIf="!deviceError">Click "Connect" to open the browser device picker.</p>
        <p class="error" *ngIf="deviceError">{{ deviceError }}</p>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <ng-container [ngSwitch]="data.interaction_type">
        <button mat-button *ngSwitchCase="'pause'" (click)="dialogRef.close(true)">Resume</button>
        
        <ng-container *ngSwitchCase="'confirm'">
          <button mat-button (click)="dialogRef.close(false)">No</button>
          <button mat-raised-button color="primary" (click)="dialogRef.close(true)">Yes</button>
        </ng-container>

        <button mat-raised-button color="primary" *ngSwitchCase="'input'" (click)="dialogRef.close(inputValue)">Submit</button>

        <ng-container *ngSwitchCase="'device_connect'">
          <button mat-button (click)="dialogRef.close({ success: false, error: 'cancelled' })">Cancel</button>
          <button mat-raised-button color="primary" [disabled]="deviceConnecting" (click)="connectDevice()">
            {{ deviceConnecting ? 'Connecting...' : 'Connect' }}
          </button>
        </ng-container>
      </ng-container>
    </mat-dialog-actions>
  `,
  styles: [`
    .full-width {
      width: 100%;
    }
    mat-dialog-content {
      min-width: 300px;
    }
    .hint {
      color: var(--mat-sys-on-surface-variant, #666);
      font-size: 0.85em;
    }
    .error {
      color: var(--mat-sys-error, #d32f2f);
      font-size: 0.85em;
    }
  `]
})
export class InteractionDialogComponent {
  inputValue: string = '';
  deviceConnecting = false;
  deviceError: string | null = null;

  constructor(
    public dialogRef: MatDialogRef<InteractionDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { interaction_type: string, payload: any }
  ) { }

  /**
   * Connect a device using the Web Device API.
   * Called directly from the (click) handler to preserve transient activation
   * (user gesture) required by requestDevice/requestPort.
   */
  async connectDevice(): Promise<void> {
    this.deviceConnecting = true;
    this.deviceError = null;
    const api: string = this.data.payload?.api || 'usb';
    const filters = this.data.payload?.filters || [];

    try {
      if (api === 'usb' && navigator.usb) {
        await navigator.usb.requestDevice({ filters });
      } else if (api === 'serial' && (navigator as any).serial) {
        await (navigator as any).serial.requestPort({ filters });
      } else if (api === 'hid' && (navigator as any).hid) {
        await (navigator as any).hid.requestDevice({ filters });
      } else {
        throw new Error('Unsupported or unavailable device API: ' + api);
      }
      this.dialogRef.close({ success: true });
    } catch (e: any) {
      this.deviceConnecting = false;
      if (e.name === 'NotFoundError' || e.message?.includes('cancelled')) {
        // User cancelled the picker — let them try again
        this.deviceError = 'No device selected. Click Connect to try again.';
      } else {
        this.dialogRef.close({ success: false, error: e.message });
      }
    }
  }
}


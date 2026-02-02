import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { OrphanedRun } from '@core/services/session-recovery.service';

@Component({
  selector: 'app-session-recovery',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  template: `
    <h1 mat-dialog-title>Protocol Run Interrupted</h1>
    <div mat-dialog-content>
      <p>A protocol run was interrupted and may need attention:</p>
      <ul>
        @for (run of data.runs; track run.accession_id) {
          <li>{{ run.name || 'Unnamed Run' }} ({{ run.accession_id }})</li>
        }
      </ul>
      <p>Would you like to mark {{ data.runs.length > 1 ? 'them' : 'it' }} as failed?</p>
    </div>
    <div mat-dialog-actions align="end">
      <button mat-button (click)="onDismiss()">Dismiss</button>
      <button mat-flat-button color="warn" (click)="onMarkAsFailed()">Mark as Failed</button>
    </div>
  `,
})
export class SessionRecoveryComponent {
  constructor(
    public dialogRef: MatDialogRef<SessionRecoveryComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { runs: OrphanedRun[] }
  ) { }

  onDismiss(): void {
    this.dialogRef.close();
  }

  onMarkAsFailed(): void {
    this.dialogRef.close('mark-as-failed');
  }
}

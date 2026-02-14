import { Component, ChangeDetectionStrategy, Inject, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { FormsModule } from '@angular/forms';
import { Resource, ResourceDefinition, ResourceStatus } from '../../models/asset.models';
import { LocationBreadcrumbComponent } from '../location-breadcrumb/location-breadcrumb.component';
import { AssetService } from '../../services/asset.service';
import { AssetWizard } from '@shared/components/asset-wizard/asset-wizard';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

export interface InstancesDialogData {
  definition: ResourceDefinition;
  instances: Resource[];
  showDiscarded: boolean;
}

@Component({
  selector: 'app-resource-instances-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatSlideToggleModule,
    FormsModule,
    LocationBreadcrumbComponent
  ],
  template: `
    <h2 mat-dialog-title>
      {{ data.definition.name }}
      <span class="subtitle">Instances</span>
    </h2>

    <mat-dialog-content>
      <div class="header-row">
        <div class="stats">
          <span class="stat">
            <strong>{{ activeInstances.length }}</strong> active
          </span>
          @if (discardedInstances.length > 0) {
            <span class="stat discarded">
              <strong>{{ discardedInstances.length }}</strong> discarded
            </span>
          }
        </div>
        <mat-slide-toggle [(ngModel)]="showDiscarded">
          Show Discarded
        </mat-slide-toggle>
      </div>

      @if (visibleInstances.length > 0) {
        <table mat-table [dataSource]="visibleInstances" class="instances-table">
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let instance">{{ instance.name }}</td>
          </ng-container>

          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let instance">
              <mat-chip [class]="'status-' + instance.status.toLowerCase()">
                {{ instance.status | titlecase }}
              </mat-chip>
            </td>
          </ng-container>

          <ng-container matColumnDef="location">
            <th mat-header-cell *matHeaderCellDef>Location</th>
            <td mat-cell *matCellDef="let instance">
              <app-location-breadcrumb [location]="instance.location"></app-location-breadcrumb>
            </td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let instance">
              @if (instance.status === 'AVAILABLE' || instance.status === 'IN_USE') {
                <button mat-icon-button color="warn" 
                        matTooltip="Mark as discarded"
                        (click)="markDiscarded(instance)">
                  <mat-icon>delete_outline</mat-icon>
                </button>
                @if (isReusable) {
                  <button mat-icon-button color="primary" 
                          matTooltip="Mark for cleaning"
                          (click)="markForCleaning(instance)">
                    <mat-icon>cleaning_services</mat-icon>
                  </button>
                }
              }
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
        </table>
      } @else {
        <div class="empty-state">
          <mat-icon>inventory_2</mat-icon>
          <p>No instances to display</p>
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Close</button>
      <button mat-flat-button color="primary" (click)="addInstance()">
        <mat-icon>add</mat-icon>
        Add Instance
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .subtitle {
      font-size: 0.9rem;
      font-weight: normal;
      color: var(--sys-on-surface-variant);
      margin-left: 8px;
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .stats {
      display: flex;
      gap: 16px;
    }

    .stat {
      font-size: 0.9rem;
    }

    .stat.discarded {
      color: var(--sys-error);
    }

    .instances-table {
      width: 100%;
    }

    .status-available {
      background-color: var(--sys-primary-container) !important;
      color: var(--sys-on-primary-container) !important;
    }

    .status-in_use {
      background-color: var(--sys-secondary-container) !important;
      color: var(--sys-on-secondary-container) !important;
    }

    .status-depleted, .status-expired {
      background-color: var(--sys-error-container) !important;
      color: var(--sys-on-error-container) !important;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: var(--sys-on-surface-variant);
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 16px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResourceInstancesDialogComponent {
  private assetService = inject(AssetService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  showDiscarded: boolean;
  displayedColumns = ['name', 'status', 'location', 'actions'];

  constructor(
    public dialogRef: MatDialogRef<ResourceInstancesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: InstancesDialogData
  ) {
    this.showDiscarded = data.showDiscarded;
  }

  get activeInstances(): Resource[] {
    return this.data.instances.filter(i =>
      i.status !== ResourceStatus.DEPLETED && i.status !== ResourceStatus.EXPIRED
    );
  }

  get discardedInstances(): Resource[] {
    return this.data.instances.filter(i =>
      i.status === ResourceStatus.DEPLETED || i.status === ResourceStatus.EXPIRED
    );
  }

  get visibleInstances(): Resource[] {
    if (this.showDiscarded) {
      return this.data.instances;
    }
    return this.activeInstances;
  }

  get isReusable(): boolean {
    return (this.data.definition as any).is_reusable ?? false;
  }

  markDiscarded(instance: Resource) {
    this.assetService.updateResource(instance.accession_id, {
      status: ResourceStatus.DEPLETED
    }).subscribe({
      next: (updated) => {
        instance.status = updated.status;
        this.snackBar.open(`Resource ${instance.name} marked as discarded`, 'OK', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error updating resource status', err);
        this.snackBar.open('Failed to update resource status', 'OK', { duration: 5000 });
      }
    });
  }

  markForCleaning(instance: Resource) {
    // Cleaning workflow: for now, just mark it as AVAILABLE again if it was IN_USE or DEPLETED
    this.assetService.updateResource(instance.accession_id, {
      status: ResourceStatus.AVAILABLE
    }).subscribe({
      next: (updated) => {
        instance.status = updated.status;
        this.snackBar.open(`Resource ${instance.name} is now clean and available`, 'OK', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error in cleaning workflow', err);
        this.snackBar.open('Failed to trigger cleaning workflow', 'OK', { duration: 5000 });
      }
    });
  }

  addInstance() {
    const dialogRef = this.dialog.open(AssetWizard, {
      minWidth: '600px',
      maxWidth: '1000px',
      width: '80vw',
      height: '85vh',
      data: {
        preselectedType: 'RESOURCE',
        preselectedDefinition: this.data.definition
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.dialogRef.close(true); // Signal that an instance was added
      }
    });
  }
}

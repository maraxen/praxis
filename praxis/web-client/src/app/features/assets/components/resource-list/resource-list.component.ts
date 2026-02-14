import { Component, ChangeDetectionStrategy, inject, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { AssetService } from '../../services/asset.service';
import { Resource } from '../../models/asset.models';
import { ResourceFiltersComponent, ResourceFilterState } from '../resource-filters/resource-filters.component';
import { AssetEditDialogComponent } from '../asset-edit-dialog.component';

@Component({
  selector: 'app-resource-list',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatMenuModule,
    MatDividerModule,
    ResourceFiltersComponent
  ],
  template: `
    <div class="resource-list-container">
      <app-resource-filters
        [resources]="resources()"
        (filtersChange)="onFiltersChange($event)">
      </app-resource-filters>

      <div class="table-container">
        <table mat-table [dataSource]="filteredResources()" class="resource-table">
          <!-- Name Column -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef> Name </th>
            <td mat-cell *matCellDef="let resource"> {{ resource.name }} </td>
          </ng-container>

        <!-- Status Column -->
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef> Status </th>
          <td mat-cell *matCellDef="let resource">
            <span class="status-badge" [ngClass]="resource.status">
              {{ resource.status | titlecase }}
            </span>
          </td>
        </ng-container>

        <!-- Definition Column -->
        <ng-container matColumnDef="definition">
          <th mat-header-cell *matHeaderCellDef> Definition </th>
          <td mat-cell *matCellDef="let resource"> {{ resource.resource_definition_accession_id || 'N/A' }} </td>
        </ng-container>

        <!-- Parent Column -->
        <ng-container matColumnDef="parent">
          <th mat-header-cell *matHeaderCellDef> Parent </th>
          <td mat-cell *matCellDef="let resource"> {{ resource.parent_accession_id || 'N/A' }} </td>
        </ng-container>

        <!-- Actions Column -->
        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef> Actions </th>
          <td mat-cell *matCellDef="let resource">
            <button mat-icon-button color="primary" matTooltip="View Details">
              <mat-icon>info</mat-icon>
            </button>
            <button mat-icon-button color="accent" matTooltip="Edit Resource" (click)="editResource(resource)">
              <mat-icon>edit</mat-icon>
            </button>
            <button mat-icon-button color="warn" matTooltip="Delete Resource" (click)="deleteResource(resource)">
              <mat-icon>delete</mat-icon>
            </button>
          </td>
        </ng-container>

        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns;"
            (contextmenu)="onContextMenu($event, row)"
            class="resource-row"></tr>

        <!-- Row shown when there is no matching data. -->
        <tr class="mat-row" *matNoDataRow>
          <td class="mat-cell" colspan="5">No resources matching the filters</td>
        </tr>
      </table>

      <!-- Context Menu -->
      <div style="visibility: hidden; position: fixed"
           [style.left]="contextMenuPosition.x"
           [style.top]="contextMenuPosition.y"
           [matMenuTriggerFor]="contextMenu">
      </div>
      <mat-menu #contextMenu="matMenu">
        <ng-template matMenuContent let-item="item">
          <button mat-menu-item (click)="editResource(item)">
            <mat-icon>edit</mat-icon>
            <span>Edit</span>
          </button>
          <button mat-menu-item (click)="duplicateResource(item)">
            <mat-icon>content_copy</mat-icon>
            <span>Duplicate</span>
          </button>
          <mat-divider></mat-divider>
          <button mat-menu-item (click)="deleteResource(item)">
            <mat-icon color="warn">delete</mat-icon>
            <span style="color: var(--mat-sys-error)">Delete</span>
          </button>
        </ng-template>
      </mat-menu>
    </div>
  `,
  styles: [`
    .resource-list-container {
      padding: 16px;
    }

    .table-container {
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 8px;
      overflow: hidden;
      margin-top: 16px;
    }

    .resource-table {
      width: 100%;
    }

    .resource-row {
      transition: background-color 0.2s ease;
      cursor: pointer;
    }

    .resource-row:hover {
      background-color: var(--mat-sys-surface-container-highest);
    }

    .status-badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-weight: bold;
      color: white;
      font-size: 0.75em;
      text-transform: uppercase;
    }

    .status-badge.available { background-color: var(--mat-sys-color-primary); }
    .status-badge.in_use { background-color: var(--mat-sys-color-secondary); }
    .status-badge.depleted { background-color: var(--mat-sys-color-warn); }
    .status-badge.expired { background-color: var(--mat-sys-color-error); }
    .status-badge.unknown { background-color: var(--mat-sys-color-outline); }

    .mat-no-data-row {
      text-align: center;
      font-style: italic;
      color: var(--mat-sys-color-on-surface-variant);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResourceListComponent {
  private assetService = inject(AssetService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  resources = signal<Resource[]>([]);
  filteredResources = signal<Resource[]>([]);

  displayedColumns: string[] = ['name', 'status', 'definition', 'parent', 'actions'];

  @ViewChild(MatMenuTrigger) contextMenuTrigger!: MatMenuTrigger;
  contextMenuPosition = { x: '0px', y: '0px' };

  constructor() {
    this.loadResources();
  }

  loadResources(): void {
    this.assetService.getResources().subscribe(
      (data) => {
        this.resources.set(data);
        this.filteredResources.set(data); // Initial set
      },
      (error) => {
        console.error('Error fetching resources:', error);
      }
    );
  }

  onFiltersChange(filters: ResourceFilterState): void {
    const data = this.resources();
    const searchLower = filters.search.toLowerCase();

    const filtered = data.filter(resource => {
      // Search
      const matchesSearch = !filters.search ||
        resource.name.toLowerCase().includes(searchLower) ||
        resource.resource_definition_accession_id?.toLowerCase().includes(searchLower) ||
        resource.parent_accession_id?.toLowerCase().includes(searchLower);

      // Status
      const matchesStatus = filters.status.length === 0 ||
        (resource.status && filters.status.includes(resource.status));

      // Category
      const matchesCategory = filters.categories.length === 0 ||
        ((resource as any).plr_category && filters.categories.includes((resource as any).plr_category));

      // Brand
      const matchesBrand = filters.brands.length === 0 ||
        ((resource as any).definition?.vendor && filters.brands.includes((resource as any).definition.vendor));

      return matchesSearch && matchesStatus && matchesCategory && matchesBrand;
    });

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (filters.sort_by) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'category':
          const catA = (a as any).plr_category || '';
          const catB = (b as any).plr_category || '';
          comparison = catA.localeCompare(catB);
          break;
        case 'created_at':
          // Assuming created_at exists, if not fall back to name or 0
          const dateA = (a as any).created_at ? new Date((a as any).created_at).getTime() : 0;
          const dateB = (b as any).created_at ? new Date((b as any).created_at).getTime() : 0;
          comparison = dateA - dateB;
          break;
      }
      return filters.sort_order === 'asc' ? comparison : -comparison;
    });

    this.filteredResources.set(filtered);
  }

  onContextMenu(event: MouseEvent, resource: Resource) {
    event.preventDefault();
    this.contextMenuPosition.x = event.clientX + 'px';
    this.contextMenuPosition.y = event.clientY + 'px';
    this.contextMenuTrigger.menuData = { item: resource };
    this.contextMenuTrigger.openMenu();
  }

  editResource(resource: Resource) {
    const dialogRef = this.dialog.open(AssetEditDialogComponent, {
      width: '500px',
      data: {
        asset: resource,
        type: 'resource'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.assetService.updateResource(resource.accession_id, result).subscribe({
          next: () => {
            this.loadResources();
            this.snackBar.open('Resource updated successfully', 'OK', { duration: 3000 });
          },
          error: (err) => {
            console.error('Error updating resource', err);
            this.snackBar.open('Failed to update resource', 'OK', { duration: 5000 });
          }
        });
      }
    });
  }

  duplicateResource(resource: Resource) {
    this.assetService.duplicateResource(resource).subscribe({
      next: () => {
        this.loadResources();
        this.snackBar.open('Resource duplicated successfully', 'OK', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error duplicating resource', err);
        this.snackBar.open('Failed to duplicate resource', 'OK', { duration: 5000 });
      }
    });
  }

  deleteResource(resource: Resource) {
    if (confirm(`Are you sure you want to delete resource "${resource.name}"?`)) {
      this.assetService.deleteResource(resource.accession_id).subscribe({
        next: () => {
          this.loadResources();
        },
        error: (err) => console.error('Error deleting resource', err)
      });
    }
  }
}


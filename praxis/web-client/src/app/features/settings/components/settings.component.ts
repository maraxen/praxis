
import { Component, inject } from '@angular/core';

import { MatCardModule } from '@angular/material/card';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDividerModule } from '@angular/material/divider';
import { AppStore } from '@core/store/app.store';
import { OnboardingService } from '@core/services/onboarding.service';
import { MatButtonModule } from '@angular/material/button';
import { BrowserService } from '@core/services/browser.service';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { SqliteService } from '@core/services/sqlite';
import { ConfirmationDialogComponent } from '@shared/components/confirmation-dialog';
import { ModeService } from '@core/services/mode.service';

type Theme = 'light' | 'dark' | 'system';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    MatCardModule,
    MatButtonToggleModule,
    MatIconModule,
    MatListModule,
    MatSlideToggleModule,
    MatExpansionModule,
    MatButtonModule,
    MatDividerModule,
    MatTooltipModule
  ],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold mb-6">Settings</h1>

      <div class="max-w-5xl mx-auto space-y-6">
        <!-- Appearance -->
        <mat-card class="glass-panel">
          <mat-card-header>
            <mat-icon mat-card-avatar class="text-primary scale-125 ml-1 box-content">palette</mat-icon>
            <mat-card-title>Appearance</mat-card-title>
            <mat-card-subtitle>Customize application look and feel</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="pt-4">
             <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
               <div>
                 <h3 class="font-medium">Theme</h3>
                 <p class="text-sm text-secondary">Select your preferred color theme</p>
               </div>

               <mat-button-toggle-group hideSingleSelectionIndicator [value]="store.theme()" (change)="setTheme($event.value)">
                 <mat-button-toggle value="light" aria-label="Light Mode" matTooltip="Light Mode">
                    <mat-icon>light_mode</mat-icon>
                 </mat-button-toggle>
                 <mat-button-toggle value="system" aria-label="System Preference" matTooltip="System Preference">
                    <mat-icon>brightness_auto</mat-icon>
                 </mat-button-toggle>
                 <mat-button-toggle value="dark" aria-label="Dark Mode" matTooltip="Dark Mode">
                    <mat-icon>dark_mode</mat-icon>
                 </mat-button-toggle>
               </mat-button-toggle-group>
             </div>
          </mat-card-content>
        </mat-card>

        <!-- Features -->
        <mat-card class="glass-panel">
          <mat-card-header>
            <mat-icon mat-card-avatar class="text-accent scale-125 ml-1 box-content">extension</mat-icon>
            <mat-card-title>Features</mat-card-title>
            <mat-card-subtitle>Enable or disable optional capabilities</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="pt-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="font-medium">Maintenance Tracking</h3>
                <p class="text-sm text-secondary">Track asset maintenance schedules and alerts</p>
              </div>
              <mat-slide-toggle 
                [checked]="store.maintenanceEnabled()" 
                (change)="store.setMaintenanceEnabled($event.checked)"
                color="primary">
              </mat-slide-toggle>
            </div>
            
            <mat-divider class="settings-divider"></mat-divider>

            <div class="flex items-center justify-between">
              <div>
                <h3 class="font-medium">Infinite Consumables</h3>
                <p class="text-sm text-secondary">Auto-replenish tips and plates during simulation</p>
              </div>
              <mat-slide-toggle 
                [checked]="store.infiniteConsumables()" 
                (change)="store.setInfiniteConsumables($event.checked)"
                color="primary">
              </mat-slide-toggle>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Onboarding -->
        <mat-card class="glass-panel" data-tour-id="settings-onboarding">
          <mat-card-header>
            <mat-icon mat-card-avatar class="text-primary scale-125 ml-1 box-content">school</mat-icon>
            <mat-card-title>Onboarding & Help</mat-card-title>
            <mat-card-subtitle>Manage onboarding and hint settings</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="pt-4 space-y-4">
             <div class="flex items-center justify-between">
               <div>
                 <h3 class="font-medium">Page Hints</h3>
                 <p class="text-sm text-secondary">
                   Show contextual tooltips on key features across the application.
                 </p>
               </div>
               <div class="flex items-center gap-4">
                 <mat-slide-toggle 
                   [checked]="onboarding.showHints()" 
                   (change)="$event.checked ? onboarding.enableHints() : onboarding.disableHints()"
                   color="primary">
                 </mat-slide-toggle>
                 <button mat-stroked-button color="accent" (click)="onboarding.resetTooltips()" [disabled]="!onboarding.showHints()">
                   <mat-icon class="mr-1">restart_alt</mat-icon> Reset Hints
                 </button>
               </div>
             </div>
          </mat-card-content>
        </mat-card>

        <!-- Remote Hardware Access -->
        <mat-card class="glass-panel">
          <mat-card-header>
            <mat-icon mat-card-avatar class="text-warning scale-125 ml-1 box-content">lan</mat-icon>
            <mat-card-title>Remote Hardware Access</mat-card-title>
            <mat-card-subtitle>Connect local hardware to cloud execution</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="pt-4">
            <p class="mb-4 text-sm opacity-80">
              To expose local lab equipment to cloud-based protocol execution:
            </p>
            <mat-list>
              <mat-list-item>
                <mat-icon matListItemIcon class="text-primary">download</mat-icon>
                <span matListItemTitle>1. Install the Praxis Agent</span>
                <code matListItemLine class="font-mono text-xs bg-surface-container px-2 py-0.5 rounded">pip install praxis-agent</code>
              </mat-list-item>
              <mat-list-item>
                <mat-icon matListItemIcon class="text-primary">terminal</mat-icon>
                <span matListItemTitle>2. Run with your API token</span>
                <code matListItemLine class="font-mono text-xs bg-surface-container px-2 py-0.5 rounded">praxis-agent --token YOUR_TOKEN</code>
              </mat-list-item>
              <mat-list-item>
                <mat-icon matListItemIcon class="text-primary">check_circle</mat-icon>
                <span matListItemTitle>3. Devices appear in discovery</span>
                <span matListItemLine class="text-sm opacity-70">Local hardware is now accessible remotely</span>
              </mat-list-item>
            </mat-list>
            <mat-expansion-panel class="mt-4">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="mr-2 text-sm">info</mat-icon>
                  Alternative: ngrok tunneling
                </mat-panel-title>
              </mat-expansion-panel-header>
              <div class="p-4 space-y-2">
                <p class="text-sm">For direct serial port forwarding:</p>
                <code class="block bg-surface-container p-2 rounded font-mono text-xs">ngrok tcp 9600 --region=us</code>
                <p class="text-xs opacity-70 mt-2">
                  Configure the tunnel URL in machine connection settings.
                </p>
              </div>
            </mat-expansion-panel>
          </mat-card-content>
        </mat-card>

        <!-- System Info / About -->
        <mat-card class="glass-panel">
          <mat-card-header>
            <mat-icon mat-card-avatar class="text-secondary scale-125 ml-1 box-content">info</mat-icon>
            <mat-card-title>About</mat-card-title>
             <mat-card-subtitle>System Information</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="pt-4">
             <mat-list>
                <mat-list-item>
                    <span matListItemTitle>Version</span>
                    <span matListItemLine>0.1.0-alpha</span>
                </mat-list-item>
                <mat-list-item>
                    <span matListItemTitle>Frontend Framework</span>
                    <span matListItemLine>Angular v21.0.2</span>
                </mat-list-item>
                 <mat-list-item>
                    <span matListItemTitle>Backend API</span>
                    <span matListItemLine>/api/v1 (FastAPI)</span>
                </mat-list-item>
             </mat-list>
          </mat-card-content>
        </mat-card>
         <!-- Data Management -->
         <mat-card class="glass-panel">
          <mat-card-header>
            <mat-icon mat-card-avatar class="text-warn scale-125 ml-1 box-content">storage</mat-icon>
            <mat-card-title>Data Management</mat-card-title>
             <mat-card-subtitle>Manage local database</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content class="pt-4">
             <div class="mb-6">
                <h3 class="font-medium">Export/Import State</h3>
                <p class="text-sm text-secondary mb-4">
                  Export your browser data for backup or import a previous backup.
                </p>
                <div class="flex gap-4">
                  <button mat-stroked-button (click)="exportData()">
                    <mat-icon>download</mat-icon> Export Database
                  </button>
                  <button mat-stroked-button (click)="fileInput.click()">
                    <mat-icon>upload</mat-icon> Import Database
                  </button>
                  <input #fileInput type="file" accept=".db" hidden (change)="importData($event)" />
                </div>
             </div>

             <mat-divider class="settings-divider"></mat-divider>

             <div class="flex items-center justify-between">
               <div>
                 <h3 class="font-medium">Reset Asset Inventory</h3>
                 <p class="text-sm text-secondary">
                   Reset all resources and machines to default simulated state. <br>
                   <span class="text-warn text-xs font-bold">WARNING: This will delete all user-created items.</span>
                 </p>
               </div>
               <button mat-flat-button color="warn" (click)="resetToDefaults()">
                 <mat-icon class="mr-1">restore</mat-icon> Reset to Defaults
               </button>
             </div>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    mat-icon {
        vertical-align: middle;
    }

    .glass-panel {
      background: var(--glass-bg) !important; /* Darker, more opaque */
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--theme-border);
      box-shadow: var(--glass-shadow);
      border-radius: 16px;
    }

    .settings-divider {
      margin: 1.5rem 0;
      opacity: 0.3;
    }

    .text-status-success {
      color: var(--theme-status-success);
    }
    
    /* Fix for icon cutoff due to scaling */
    mat-card-header {
      overflow: visible !important;
    }
    
    ::ng-deep .mat-mdc-card-header-text {
      overflow: visible !important;
    }

    /* Override avatar clipping */
    ::ng-deep .mat-mdc-card-header .mat-mdc-card-avatar {
      border-radius: 0 !important;
      overflow: visible !important;
      margin-right: 16px !important; /* Ensure consistent gap to text */
    }
  `]
})
export class SettingsComponent {
  store = inject(AppStore);
  onboarding = inject(OnboardingService);
  sqlite = inject(SqliteService);
  dialog = inject(MatDialog);
  snackBar = inject(MatSnackBar);
  browserService = inject(BrowserService);
  modeService = inject(ModeService);


  setTheme(theme: Theme) {
    this.store.setTheme(theme);
  }

  // Removed hasTutorialProgress, resumeTutorial, restartTutorial methods
  // as they are replaced by onboarding service methods and template logic.

  resetToDefaults() {
    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Reset Inventory?',
        message: 'This will delete all your custom resources and machines and restore the default simulated assets. This action cannot be undone.',
        confirmText: 'Reset Everything',
        color: 'warn',
        icon: 'delete_forever'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open('Resetting database...', '', { duration: 0 });
        this.sqlite.resetToDefaults().subscribe({
          next: () => {
            this.snackBar.open('Database reset complete. Reloading...', 'OK', { duration: 2000 });
            // Reload the page to reinitialize all services with fresh data
            setTimeout(() => window.location.reload(), 1500);
          },
          error: (err: Error) => {
            console.error('[Settings] Reset failed:', err);
            this.snackBar.open('Reset failed: ' + err.message, 'Close', { duration: 5000 });
          }
        });
      }
    });
  }

  async exportData() {
    try {
      this.sqlite.exportDatabase().subscribe({
        next: (data: Uint8Array) => {
          const blob = new Blob([new Uint8Array(data).buffer as ArrayBuffer], { type: 'application/x-sqlite3' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `praxis-backup-${new Date().toISOString().slice(0, 10)}.db`;
          a.click();
          URL.revokeObjectURL(url);
          this.snackBar.open('Database exported', 'OK', { duration: 3000 });
        },
        error: (err: Error) => {
          console.error(err);
          this.snackBar.open('Export failed', 'OK', { duration: 3000 });
        }
      });
    } catch (err) {
      console.error(err);
      this.snackBar.open('Export failed', 'OK', { duration: 3000 });
    }
  }

  async importData(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Import Database?',
        message: 'This will replace all current data with the backup file. This action cannot be undone and the page will refresh.',
        confirmText: 'Import and Refresh',
        color: 'warn',
        icon: 'upload'
      }
    });

    dialogRef.afterClosed().subscribe(async result => {
      if (result) {
        try {
          const buffer = await file.arrayBuffer();
          const data = new Uint8Array(buffer);
          this.sqlite.importDatabase(data).subscribe({
            next: () => {
              this.snackBar.open('Database imported - refreshing...', 'OK', { duration: 2000 });
              setTimeout(() => this.browserService.reload(), 2000);
            },
            error: (err: Error) => {
              console.error(err);
              this.snackBar.open('Import failed', 'OK', { duration: 3000 });
            }
          });
        } catch (err) {
          console.error(err);
          this.snackBar.open('Import failed', 'OK', { duration: 3000 });
        }
      }
      // Reset input value so same file can be selected again
      input.value = '';
    });
  }
}

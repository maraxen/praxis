import { Component, signal, inject, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { SqliteService } from './core/services/sqlite';
import { ApiConfigService } from './core/services/api-config.service';
import { SessionRecoveryService } from './core/services/session-recovery.service';
import { SessionRecoveryComponent } from './core/components/session-recovery/session-recovery.component';
import { filter, switchMap } from 'rxjs/operators';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  host: {
    '[attr.data-sqlite-ready]': 'sqlite.isReady() ? \"true\" : \"false\"'
  }
})
export class App implements OnInit {
  protected readonly title = signal('web-client');
  private apiConfig = inject(ApiConfigService);
  private sessionRecoveryService = inject(SessionRecoveryService);
  private dialog = inject(MatDialog);

  constructor(protected sqlite: SqliteService) {
    // Initialize API client configuration
    this.apiConfig.initialize();

    // Expose for E2E testing (legacy - use data-sqlite-ready attribute instead)
    (window as any).sqliteService = this.sqlite;
  }

  ngOnInit(): void {
    this.sessionRecoveryService.checkForOrphanedRuns().subscribe(orphanedRuns => {
      if (orphanedRuns.length > 0) {
        const dialogRef = this.dialog.open(SessionRecoveryComponent, {
          data: { runs: orphanedRuns },
          disableClose: true,
        });

        dialogRef.afterClosed().pipe(
          filter(result => result === 'mark-as-failed'),
          switchMap(() => {
            const updates = orphanedRuns.map(run =>
              this.sessionRecoveryService.markAsFailed(run.accession_id!)
            );
            return forkJoin(updates);
          })
        ).subscribe(() => {
          console.log('Orphaned runs marked as failed.');
        });
      }
    });
  }
}

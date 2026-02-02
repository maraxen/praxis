import { Injectable, inject } from '@angular/core';
import { Observable, from } from 'rxjs';
import { switchMap, map } from 'rxjs/operators';
import { SqliteService } from 'src/app/core/services/sqlite/sqlite.service';
import { ProtocolRun } from '@core/db/schema';
import { ProtocolRunStatusValues } from '@core/db/enums';

export type OrphanedRun = ProtocolRun;

@Injectable({
  providedIn: 'root'
})
export class SessionRecoveryService {
  private sqliteService = inject(SqliteService);

  /**
   * Checks for orphaned protocol runs.
   * An orphaned run is a run that has a status of 'running', 'pausing', or 'resuming'
   * and has not had a heartbeat in the last 30 seconds.
   */
  checkForOrphanedRuns(): Observable<OrphanedRun[]> {
    const staleThreshold = Date.now() - 30000; // 30 seconds
    const activeStatuses = [
      ProtocolRunStatusValues.RUNNING,
      ProtocolRunStatusValues.PAUSING,
      ProtocolRunStatusValues.RESUMING
    ];

    return this.sqliteService.protocolRuns.pipe(
      switchMap(repo => from(repo.findByStatus(activeStatuses))),
      map((runs: OrphanedRun[]) => runs.filter((run: OrphanedRun) => {
        const lastHeartbeat = run.properties_json?.lastHeartbeat ?? 0;
        return lastHeartbeat < staleThreshold;
      }))
    );
  }

  /**
   * Marks an orphaned run as failed.
   */
  markAsFailed(runId: string): Observable<void> {
    return this.sqliteService.protocolRuns.pipe(
      switchMap(repo => from(repo.update(runId, { status: ProtocolRunStatusValues.FAILED })))
    ).pipe(map(() => void 0));
  }

  /**
   * Marks all orphaned runs as failed.
   */
  markAllAsFailed(runs: OrphanedRun[]): Observable<void> {
    if (runs.length === 0) {
      return from(Promise.resolve());
    }
    return this.sqliteService.protocolRuns.pipe(
      switchMap(async repo => {
        for (const run of runs) {
          if (run.accession_id) {
            await repo.update(run.accession_id, { status: ProtocolRunStatusValues.FAILED });
          }
        }
      }),
      map(() => void 0)
    );
  }
}

import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { ModeService } from '@core/services/mode.service';
import { SqliteService } from '@core/services/sqlite';
import { ProtocolRun } from '@core/db/schema';
import {
    RunSummary,
    RunDetail,
    RunHistoryParams,
    RunStatus,
} from '../models/monitor.models';
import { ProtocolsService } from '@api/services/ProtocolsService';
import { SchedulerService as SchedulerApiService } from '@api/services/SchedulerService';
import { ApiWrapperService } from '@core/services/api-wrapper.service';

@Injectable({
    providedIn: 'root',
})
export class RunHistoryService {
    private readonly modeService = inject(ModeService);
    private readonly sqliteService = inject(SqliteService);
    private readonly apiWrapper = inject(ApiWrapperService);

    /**
     * Get paginated run history.
     */
    getRunHistory(params?: RunHistoryParams): Observable<RunSummary[]> {
        // Browser mode: use SqliteService with client-side filtering
        if (this.modeService.isBrowserMode()) {
            return this.sqliteService.getProtocolRuns().pipe(
                map(runs => {
                    let filtered = (runs as unknown as ProtocolRun[]).map(run => ({
                        ...run,
                        protocol_accession_id: run.top_level_protocol_definition_accession_id,
                        status: run.status as unknown as RunStatus
                    } as unknown as RunSummary));

                    // Apply status filter
                    if (params?.status && params.status.length > 0) {
                        const statusList = Array.isArray(params.status) ? params.status : [params.status];
                        filtered = filtered.filter(r => statusList.includes(r.status as RunStatus));
                    }

                    // Apply protocol filter
                    if (params?.protocol_id) {
                        const protocolIds = Array.isArray(params.protocol_id) ? params.protocol_id : [params.protocol_id];
                        filtered = filtered.filter(r => protocolIds.includes(r.protocol_accession_id || ''));
                    }

                    // Apply machine filter (Note: schema might need update to support this directly)
                    if (params?.machine_id) {
                        const machineIds = Array.isArray(params.machine_id) ? params.machine_id : [params.machine_id];
                        // Temporary check against property until column is guaranteed
                        filtered = filtered.filter(r => {
                            const rid = (r as any).machine_accession_id || (r as any).machine_id;
                            return machineIds.includes(rid || '');
                        });
                    }

                    // Apply sorting
                    const sortBy = params?.sort_by || 'created_at';
                    const sortOrder = params?.sort_order || 'desc';
                    filtered.sort((a, b) => {
                        const aVal = (a as any)[sortBy] || '';
                        const bVal = (b as any)[sortBy] || '';
                        const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
                        return sortOrder === 'desc' ? -comparison : comparison;
                    });

                    // Apply pagination
                    const offset = params?.offset || 0;
                    const limit = params?.limit || 50;
                    return filtered.slice(offset, offset + limit);
                }),
                catchError(err => {
                    console.error('[RunHistoryService] Browser mode error:', err);
                    return of([]);
                })
            );
        }

        return this.apiWrapper.wrap(ProtocolsService.getMultiApiV1ProtocolsRunsGet(
            params?.limit,
            params?.offset,
            params?.sort_by,
            undefined, // date_range_start
            undefined, // date_range_end
            params?.protocol_id as string | undefined,
            params?.machine_id as string | undefined,
            undefined, // resource_accession_id
            undefined, // parent_accession_id
            undefined, // requestBody
        )).pipe(
            map(runs => runs as unknown as RunSummary[]),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to fetch run history:', err);
                return of([]);
            })
        );
    }

    /**
     * Get active (in-progress) runs.
     * Uses the /runs/queue endpoint which returns pending, preparing, queued, running statuses.
     */
    getActiveRuns(): Observable<RunSummary[]> {
        // Browser mode: filter for active statuses
        if (this.modeService.isBrowserMode()) {
            const activeStatuses: RunStatus[] = ['pending', 'preparing', 'queued', 'running', 'paused'];
            return this.sqliteService.getProtocolRuns().pipe(
                map(runs => (runs as unknown as ProtocolRun[]).map(run => ({
                    ...run,
                    protocol_accession_id: run.top_level_protocol_definition_accession_id,
                    status: run.status as unknown as RunStatus
                } as unknown as RunSummary)).filter(r => activeStatuses.includes(r.status as RunStatus))),
                catchError(err => {
                    console.error('[RunHistoryService] Browser mode getActiveRuns error:', err);
                    return of([]);
                })
            );
        }

        return this.apiWrapper.wrap(ProtocolsService.getProtocolQueueApiV1ProtocolsRunsQueueGet()).pipe(
            map(runs => runs as unknown as RunSummary[]),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to fetch active runs:', err);
                return of([]);
            })
        );
    }

    /**
     * Get detailed information for a specific run.
     */
    getRunDetail(runId: string): Observable<RunDetail | null> {
        // Browser mode: use SqliteService
        if (this.modeService.isBrowserMode()) {
            return this.sqliteService.getProtocolRun(runId).pipe(
                map(run => {
                    if (!run) return null;
                    return {
                        ...run,
                        protocol_accession_id: run.top_level_protocol_definition_accession_id,
                        status: run.status as unknown as RunStatus
                    } as unknown as RunDetail;
                }),
                catchError(err => {
                    console.error('[RunHistoryService] Browser mode getRunDetail error:', err);
                    return of(null);
                })
            );
        }

        return this.apiWrapper.wrap(ProtocolsService.getApiV1ProtocolsRunsAccessionIdGet(runId)).pipe(
            map(run => run as unknown as RunDetail | null),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to fetch run detail:', err);
                return of(null);
            })
        );
    }

    /**
     * Returns color class based on run status.
     */
    getStatusColor(status: RunStatus): string {
        const s = status?.toLowerCase();
        switch (s) {
            case 'running':
                return 'text-sys-primary';
            case 'queued':
            case 'preparing':
                return 'text-sys-secondary';
            case 'pending':
                return 'text-sys-tertiary';
            case 'completed':
                return 'text-sys-success';
            case 'failed':
                return 'text-sys-error';
            case 'cancelled':
                return 'text-sys-on-surface-variant';
            case 'paused':
                return 'text-sys-warning';
            default:
                return 'text-sys-on-surface-variant';
        }
    }

    /**
     * Returns icon name based on run status.
     */
    getStatusIcon(status: RunStatus): string {
        const s = status?.toLowerCase();
        switch (s) {
            case 'running':
                return 'play_circle';
            case 'queued':
                return 'schedule';
            case 'preparing':
                return 'hourglass_empty';
            case 'pending':
                return 'pending';
            case 'completed':
                return 'check_circle';
            case 'failed':
                return 'error';
            case 'cancelled':
                return 'cancel';
            case 'paused':
                return 'pause_circle_filled';
            default:
                return 'help';
        }
    }

    /**
     * Format duration in milliseconds to human-readable string.
     */
    formatDuration(durationMs?: number): string {
        if (!durationMs) return '-';
        const seconds = Math.floor(durationMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    // =========================================================================
    // State Resolution Methods
    // =========================================================================

    /**
     * Get uncertain states for a failed/paused run.
     */
    getUncertainStates(runId: string): Observable<import('../models/state-resolution.models').UncertainStateChange[]> {
        // Browser mode: return empty (no uncertain states tracked locally yet)
        if (this.modeService.isBrowserMode()) {
            console.warn('[RunHistoryService] State resolution not yet implemented in browser mode');
            return of([]);
        }

        return this.apiWrapper.wrap(SchedulerApiService.getUncertainStatesApiV1SchedulerScheduleEntryAccessionIdUncertainStateGet(runId)).pipe(
            map(states => states as unknown as import('../models/state-resolution.models').UncertainStateChange[]),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to fetch uncertain states:', err);
                return of([]);
            })
        );
    }

    /**
     * Submit a state resolution for a failed operation.
     */
    resolveStates(
        runId: string,
        request: import('../models/state-resolution.models').StateResolutionRequest
    ): Observable<import('../models/state-resolution.models').StateResolutionLogResponse | null> {
        // Browser mode: store resolution locally
        if (this.modeService.isBrowserMode()) {
            return this.sqliteService.saveStateResolution(runId, request).pipe(
                map(() => ({
                    id: crypto.randomUUID(),
                    run_id: runId,
                    operation_id: request.operation_id,
                    operation_description: 'Browser mode resolution',
                    resolution_type: request.resolution_type,
                    action_taken: request.action,
                    resolved_at: new Date().toISOString(),
                    resolved_by: 'user',
                })),
                catchError((err) => {
                    console.error('[RunHistoryService] Failed to save resolution:', err);
                    return of(null);
                })
            );
        }

        return this.apiWrapper.wrap(SchedulerApiService.resolveStateApiV1SchedulerScheduleEntryAccessionIdResolveStatePost(runId, request)).pipe(
            map(res => res as unknown as import('../models/state-resolution.models').StateResolutionLogResponse),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to submit resolution:', err);
                return of(null);
            })
        );
    }

    /**
     * Resume a run after state resolution.
     */
    resumeRun(runId: string): Observable<boolean> {
        // Browser mode: update run status locally
        if (this.modeService.isBrowserMode()) {
            return this.sqliteService.updateProtocolRunStatus(runId, 'running').pipe(
                map(() => true),
                catchError((err) => {
                    console.error('[RunHistoryService] Failed to resume run:', err);
                    return of(false);
                })
            );
        }

        return this.apiWrapper.wrap(SchedulerApiService.resumeRunApiV1SchedulerScheduleEntryAccessionIdResumePost(runId)).pipe(
            map(() => true),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to resume run:', err);
                return of(false);
            })
        );
    }

    /**
     * Abort a run after state resolution.
     */
    abortRun(runId: string, reason?: string): Observable<boolean> {
        // Browser mode: update run status locally
        if (this.modeService.isBrowserMode()) {
            return this.sqliteService.updateProtocolRunStatus(runId, 'cancelled').pipe(
                map(() => true),
                catchError((err) => {
                    console.error('[RunHistoryService] Failed to abort run:', err);
                    return of(false);
                })
            );
        }

        return this.apiWrapper.wrap(SchedulerApiService.abortRunApiV1SchedulerScheduleEntryAccessionIdAbortPost(runId, reason)).pipe(
            map(() => true),
            catchError((err) => {
                console.error('[RunHistoryService] Failed to abort run:', err);
                return of(false);
            })
        );
    }
}

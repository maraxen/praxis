import { TestBed } from '@angular/core/testing';
import { SessionRecoveryService, OrphanedRun } from './session-recovery.service';
import { SqliteService } from './sqlite.service';
import { of } from 'rxjs';
import { ProtocolRunStatusValues } from '@core/db/enums';

describe('SessionRecoveryService', () => {
  let service: SessionRecoveryService;
  let sqliteService: jasmine.SpyObj<SqliteService>;

  const mockRuns: OrphanedRun[] = [
    {
      accession_id: '1',
      name: 'run-1',
      properties_json: { lastHeartbeat: Date.now() - 60000 }, // 1 minute ago
      status: ProtocolRunStatusValues.RUNNING,
      created_at: '',
      updated_at: '',
      start_time: '',
      end_time: '',
      data_directory_path: '',
      duration_ms: 0,
      input_parameters_json: {},
      resolved_assets_json: {},
      output_data_json: {},
      initial_state_json: {},
      final_state_json: {},
      created_by_user: {},
      top_level_protocol_definition_accession_id: '',
      protocol_definition_accession_id: ''
    },
    {
      accession_id: '2',
      name: 'run-2',
      properties_json: { lastHeartbeat: Date.now() - 10000 }, // 10 seconds ago
      status: ProtocolRunStatusValues.RUNNING,
      created_at: '',
      updated_at: '',
      start_time: '',
      end_time: '',
      data_directory_path: '',
      duration_ms: 0,
      input_parameters_json: {},
      resolved_assets_json: {},
      output_data_json: {},
      initial_state_json: {},
      final_state_json: {},
      created_by_user: {},
      top_level_protocol_definition_accession_id: '',
      protocol_definition_accession_id: ''
    },
    {
      accession_id: '3',
      name: 'run-3',
      properties_json: { lastHeartbeat: Date.now() - 90000 }, // 1.5 minutes ago
      status: ProtocolRunStatusValues.PAUSING,
      created_at: '',
      updated_at: '',
      start_time: '',
      end_time: '',
      data_directory_path: '',
      duration_ms: 0,
      input_parameters_json: {},
      resolved_assets_json: {},
      output_data_json: {},
      initial_state_json: {},
      final_state_json: {},
      created_by_user: {},
      top_level_protocol_definition_accession_id: '',
      protocol_definition_accession_id: ''
    },
  ];

  beforeEach(() => {
    const sqliteServiceSpy = jasmine.createSpyObj('SqliteService', ['protocolRuns']);
    TestBed.configureTestingModule({
      providers: [
        SessionRecoveryService,
        { provide: SqliteService, useValue: sqliteServiceSpy },
      ],
    });
    service = TestBed.inject(SessionRecoveryService);
    sqliteService = TestBed.inject(SqliteService) as jasmine.SpyObj<SqliteService>;
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should identify orphaned runs', () => {
    const protocolRunsRepoSpy = jasmine.createSpyObj('AsyncProtocolRunRepository', ['findByStatus']);
    protocolRunsRepoSpy.findByStatus.and.returnValue(of(mockRuns));
    sqliteService.protocolRuns = of(protocolRunsRepoSpy);

    service.checkForOrphanedRuns().subscribe(orphanedRuns => {
      expect(orphanedRuns.length).toBe(2);
      expect(orphanedRuns.map(r => r.accession_id)).toEqual(['1', '3']);
    });

    expect(protocolRunsRepoSpy.findByStatus).toHaveBeenCalledWith([
      ProtocolRunStatusValues.RUNNING,
      ProtocolRunStatusValues.PAUSING,
      ProtocolRunStatusValues.RESUMING,
    ]);
  });

  it('should handle no orphaned runs', () => {
    const protocolRunsRepoSpy = jasmine.createSpyObj('AsyncProtocolRunRepository', ['findByStatus']);
    protocolRunsRepoSpy.findByStatus.and.returnValue(of(mockRuns.slice(1,2)));
    sqliteService.protocolRuns = of(protocolRunsRepoSpy);

    service.checkForOrphanedRuns().subscribe(orphanedRuns => {
      expect(orphanedRuns.length).toBe(0);
    });
  });

  it('should mark a run as failed', () => {
    const protocolRunsRepoSpy = jasmine.createSpyObj('AsyncProtocolRunRepository', ['update']);
    protocolRunsRepoSpy.update.and.returnValue(of(void 0));
    sqliteService.protocolRuns = of(protocolRunsRepoSpy);

    service.markAsFailed('1').subscribe(() => {
      expect(protocolRunsRepoSpy.update).toHaveBeenCalledWith('1', { status: ProtocolRunStatusValues.FAILED });
    });
  });
});

import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { ProtocolDefinitionsService } from '@core/api-generated/services/ProtocolDefinitionsService';
import { ProtocolsService } from '@core/api-generated/services/ProtocolsService';
import { ApiWrapperService } from '@core/services/api-wrapper.service';
import { FunctionProtocolDefinitionRead } from '@core/api-generated/models/FunctionProtocolDefinitionRead';
import { ProtocolRunRead } from '@core/api-generated/models/ProtocolRunRead';
import { ProtocolDefinition } from '../models/protocol.models';

@Injectable({
  providedIn: 'root'
})
export class ProtocolService {
  constructor() {
    if (typeof window !== 'undefined') {
      (window as any).protocolService = this;
    }
  }

  private apiWrapper = inject(ApiWrapperService);
  private http = inject(HttpClient);
  private readonly API_URL = '/api/v1';

  getProtocols(): Observable<ProtocolDefinition[]> {
    return this.apiWrapper.wrap(ProtocolDefinitionsService.getMultiApiV1ProtocolsDefinitionsGet()) as unknown as Observable<ProtocolDefinition[]>;
  }

  getRuns(): Observable<ProtocolRunRead[]> {
    return this.apiWrapper.wrap(ProtocolsService.getMultiApiV1ProtocolsRunsGet());
  }

  getTransferLogs(runId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.API_URL}/protocols/runs/${runId}/transfer-logs`);
  }

  // If uploading a file
  // NOTE: This endpoint is not yet in the generated API client
  uploadProtocol(file: File): Observable<FunctionProtocolDefinitionRead> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<FunctionProtocolDefinitionRead>(`${this.API_URL}/protocols/upload`, formData);
  }
}

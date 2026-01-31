import { Component, signal, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SqliteService } from './core/services/sqlite';
import { ApiConfigService } from './core/services/api-config.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  host: {
    '[attr.data-sqlite-ready]': 'sqlite.isReady() ? \"true\" : \"false\"'
  }
})
export class App {
  protected readonly title = signal('web-client');
  private apiConfig = inject(ApiConfigService);

  constructor(protected sqlite: SqliteService) {
    // Initialize API client configuration
    this.apiConfig.initialize();

    // Expose for E2E testing (legacy - use data-sqlite-ready attribute instead)
    (window as any).sqliteService = this.sqlite;
  }
}

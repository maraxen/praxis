
import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';

import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatBadgeModule } from '@angular/material/badge';
import { Subscription } from 'rxjs';

import { AssetService } from '@features/assets/services/asset.service';
import { ProtocolService } from '@features/protocols/services/protocol.service';
import { ExecutionService } from '@features/run-protocol/services/execution.service';
import { HardwareDiscoveryButtonComponent } from '@shared/components/hardware-discovery-button/hardware-discovery-button.component';
import { SparklineComponent } from '@shared/components/sparkline/sparkline.component';
import { PageTooltipComponent } from '@shared/components/page-tooltip/page-tooltip.component';
import { ModeService } from '@core/services/mode.service';
import { Machine, Resource, MachineStatus } from '@features/assets/models/asset.models';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { ExecutionStatus } from '@features/run-protocol/models/execution.models';

interface RecentRun {
  id: string;
  name: string;
  protocolName: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  progress: number;
  startedAt: Date;
  duration?: string;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    RouterLink,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatTooltipModule,
    MatBadgeModule,
    HardwareDiscoveryButtonComponent,
    SparklineComponent,
    PageTooltipComponent
  ],
  template: `
    <div class="p-6 max-w-screen-2xl mx-auto" #dashboardRoot>
      <app-page-tooltip 
        id="home-intro" 
        text="Welcome to your Praxis dashboard. Here you can see active runs, hardware status, and quick lab stats at a glance." 
        [target]="dashboardRoot"
        [isFirst]="true">
      </app-page-tooltip>
      <!-- Header with Quick Actions -->
      <header class="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div class="greeting">
          <h1 class="text-3xl font-bold text-sys-text-primary mb-1">Welcome back</h1>
          <p class="text-sys-text-secondary">Here's what's happening in your lab</p>
        </div>
        <div class="flex gap-3 w-full md:w-auto">
          <a mat-flat-button class="!bg-gradient-to-br !from-primary !to-primary-dark !text-white !rounded-xl !px-6 !py-6 !font-semibold flex items-center gap-2 flex-1 md:flex-none justify-center shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all hover:-translate-y-0.5" routerLink="/app/run">
            <mat-icon>play_circle</mat-icon>
            Run Protocol
          </a>
          <app-hardware-discovery-button></app-hardware-discovery-button>
          @if (!modeService.isBrowserMode()) {
            <a mat-stroked-button class="!border-[var(--theme-border)] !text-sys-text-primary !rounded-xl !px-6 !py-6 flex items-center gap-2 flex-1 md:flex-none justify-center hover:bg-[var(--mat-sys-surface-variant)] transition-all" routerLink="/app/protocols">
              <mat-icon>schedule</mat-icon>
              Schedule
            </a>
          }
        </div>
      </header>

      <!-- Stats Overview -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div class="praxis-card premium group cursor-pointer" routerLink="/app/monitor" matTooltip="View active protocol runs">
          <!-- Glow effect via cards.scss aurora hint -->
          <div class="card-header pb-0">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-primary/20 to-secondary/20 shrink-0">
              <mat-icon class="text-primary">play_arrow</mat-icon>
            </div>
            <div class="w-16 h-8 ml-auto">
              <app-sparkline [data]="runTrend()" color="var(--mat-sys-primary)" />
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">{{ runningCount() }}</span>
            <span class="card-subtitle">Running Protocols</span>
          </div>
          <div class="absolute top-4 right-4 w-2 h-2 bg-[var(--mat-sys-primary)] rounded-full animate-pulse shadow-[0_0_8px_var(--mat-sys-primary)]"></div>
        </div>

        <div class="praxis-card premium group cursor-pointer" routerLink="/app/assets" matTooltip="View laboratory machines">
          <div class="card-header pb-0">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-[var(--mat-sys-tertiary-container)] shrink-0">
              <mat-icon class="text-[var(--mat-sys-tertiary)]">precision_manufacturing</mat-icon>
            </div>
            <div class="flex flex-col items-end ml-auto">
              <span class="text-sm font-bold text-sys-text-secondary">{{ simulatedOnlineMachines() }}/{{ simulatedMachinesCount() }}</span>
              <span class="text-[8px] uppercase font-bold tracking-tighter text-sys-text-tertiary">Simulated</span>
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">
              {{ physicalOnlineMachines() }}<span class="text-base font-normal text-sys-text-tertiary">/{{ physicalMachinesCount() }}</span>
            </span>
            <span class="card-subtitle">Physical Hardware</span>
          </div>
        </div>

        <div class="praxis-card premium group cursor-pointer" routerLink="/app/protocols" matTooltip="Manage protocols">
          <div class="card-header pb-0">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-[var(--mat-sys-surface-variant)] shrink-0">
              <mat-icon class="text-[var(--theme-text-primary)]">science</mat-icon>
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">{{ totalProtocols() }}</span>
            <span class="card-subtitle">Available Protocols</span>
          </div>
        </div>

        <div class="praxis-card premium group cursor-pointer" routerLink="/app/assets" matTooltip="Manage resources">
          <div class="card-header pb-0">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-[var(--mat-sys-warning-container)] shrink-0">
              <mat-icon class="text-[var(--mat-sys-warning)]">inventory_2</mat-icon>
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">{{ totalResources() }}</span>
            <span class="card-subtitle">Active Resources</span>
          </div>
        </div>
      </section>

      <!-- Main Content Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Live Experiments Panel -->
        <section class="lg:col-span-2 praxis-card">
          <div class="card-header border-b border-[var(--theme-border)] bg-[var(--mat-sys-surface-variant)]">
            <div class="flex justify-between items-center w-full">
              <h2 class="text-lg font-semibold text-sys-text-primary flex items-center gap-2">
                <mat-icon class="text-primary">monitor_heart</mat-icon>
                Live Experiments
              </h2>
              @if (runningCount() > 0) {
                <span class="flex items-center gap-2 text-sm font-medium text-[var(--mat-sys-primary)] bg-[var(--mat-sys-primary-container)] px-3 py-1 rounded-full border border-[var(--mat-sys-primary)]/20">
                  <span class="w-1.5 h-1.5 rounded-full bg-[var(--mat-sys-primary)] animate-pulse"></span>
                  {{ runningCount() }} Active
                </span>
              }
            </div>
          </div>

          <div class="card-content">
            @if (hasRunningExperiments()) {
              @for (run of currentRuns(); track run.id) {
                <div class="praxis-card-min group cursor-pointer mb-3 hover:bg-[var(--mat-sys-surface-variant)] transition-all" 
                     [routerLink]="['/app/monitor', run.id]"
                     matTooltip="View run details">
                  <div class="flex justify-between items-start mb-3">
                    <div class="min-w-0">
                      <h3 class="font-semibold text-sys-text-primary group-hover:text-primary transition-colors truncate">{{ run.name }}</h3>
                      <span class="text-xs text-sys-text-secondary truncate block">{{ run.protocolName }}</span>
                    </div>
                    <span [class]="getStatusClass(run.status) + ' px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider'">
                      {{ run.status }}
                    </span>
                  </div>

                  @if (run.status === 'running') {
                    <div class="flex items-center gap-4 mb-3">
                      <mat-progress-bar mode="determinate" [value]="run.progress" class="flex-1 rounded-full overflow-hidden !h-1.5"></mat-progress-bar>
                      <span class="text-xs font-bold text-primary min-w-[2.5rem] text-right">{{ run.progress }}%</span>
                    </div>
                  }

                  <div class="flex justify-between items-center text-xs text-sys-text-tertiary">
                    <span class="flex items-center gap-1.5">
                      <mat-icon class="!w-3.5 !h-3.5 !text-[14px]">schedule</mat-icon>
                      Started {{ formatTimeAgo(run.startedAt) }}
                    </span>
                    <mat-icon class="!w-4 !h-4 !text-[16px] opacity-0 group-hover:opacity-100 transition-opacity">visibility</mat-icon>
                  </div>
                </div>
              }
            } @else {
              <div class="flex flex-col items-center justify-center py-12 empty-state-text">
                <mat-icon class="!w-16 !h-16 !text-[64px] mb-4">science</mat-icon>
                <p class="mb-4 text-center">No experiments running right now</p>
                <a mat-stroked-button class="!border-primary !text-primary hover:!bg-primary/10" routerLink="/app/run">Start a Protocol</a>
              </div>
            }
          </div>
        </section>

        <div class="flex flex-col gap-6">
          <!-- Recent Activity -->
          <section class="praxis-card">
            <div class="card-header border-b border-[var(--theme-border)] bg-[var(--mat-sys-surface-variant)]">
              <div class="flex justify-between items-center w-full">
                <h2 class="text-lg font-semibold text-sys-text-primary flex items-center gap-2">
                  <mat-icon class="text-[var(--mat-sys-tertiary)]">history</mat-icon>
                  Recent Activity
                </h2>
                <a mat-button class="!text-sys-text-secondary hover:!text-sys-text-primary" routerLink="/app/monitor">View All</a>
              </div>
            </div>

            <div class="card-content pt-2">
              @if (recentRuns().length > 0) {
                @for (run of recentRuns(); track run.id) {
                  <a class="flex items-center gap-3 p-3 hover:bg-[var(--mat-sys-surface-variant)] rounded-xl transition-all cursor-pointer group no-underline"
                     [routerLink]="['/app/monitor', run.id]"
                     [matTooltip]="'View run details'"
                     matTooltipPosition="left">
                    <div class="w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105" [class]="getStatusBgClass(run.status)">
                      <mat-icon class="!text-sys-text-primary !w-5 !h-5 !text-[20px]">{{ getStatusIcon(run.status) }}</mat-icon>
                    </div>
                    <div class="flex-1 min-w-0">
                      <div class="font-medium text-sys-text-primary truncate group-hover:text-primary transition-colors">{{ run.name }}</div>
                      <div class="text-xs text-sys-text-tertiary truncate">{{ run.protocolName }} • {{ run.duration }}</div>
                    </div>
                    <mat-icon class="!text-sys-text-tertiary !w-4 !h-4 !text-[16px] opacity-0 group-hover:opacity-100 transition-opacity">chevron_right</mat-icon>
                  </a>
                }

              } @else {
                <div class="p-8 text-center empty-state-text">
                  <mat-icon class="!w-12 !h-12 !text-[48px] mb-2">history</mat-icon>
                  <p>No recent activity</p>
                </div>
              }
            </div>
          </section>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
    }

    /* Improve card visibility in dark mode */
    .praxis-card {
      background: var(--mat-sys-surface-container-low);
      border: 1px solid var(--mat-sys-outline-variant) !important;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
      position: relative;
      overflow: hidden;
    }

    /* Premium cards with gradient and enhanced aurora glow */
    .praxis-card.premium {
      background: linear-gradient(135deg, var(--mat-sys-surface-container-low) 0%, var(--mat-sys-surface-container) 100%) !important;
    }

    .praxis-card.premium::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: radial-gradient(circle at 20% 20%, var(--mat-sys-primary-container) 0%, transparent 40%),
                  radial-gradient(circle at 80% 80%, var(--mat-sys-secondary-container) 0%, transparent 40%);
      opacity: 0.15;
      pointer-events: none;
      z-index: 0;
    }

    /* Better empty state visibility */
    .empty-state-text {
      color: var(--mat-sys-on-surface-variant) !important;
      opacity: 1 !important;
    }

    /* Improve secondary text contrast */
    .text-sys-text-secondary {
      color: var(--mat-sys-on-surface-variant) !important;
    }

    .card-subtitle {
      color: var(--mat-sys-on-surface-variant);
      font-size: 0.875rem;
      font-weight: 500;
    }
  `]
})
export class HomeComponent implements OnInit, OnDestroy {
  private assetService = inject(AssetService);
  private protocolService = inject(ProtocolService);
  private executionService = inject(ExecutionService);
  public modeService = inject(ModeService);
  private subscription = new Subscription();

  // Stats signals
  totalProtocols = signal(0);
  totalResources = signal(0);
  allMachines = signal<Machine[]>([]);

  // Trend data for sparkline (mock data representing run activity over last 7 days)
  runTrend = signal([2, 1, 3, 2, 4, 3, 5]);

  // Runs signals
  currentRuns = signal<RecentRun[]>([]);
  recentRuns = signal<RecentRun[]>([]);

  // Computed
  runningCount = computed(() => this.currentRuns().filter(r => r.status === 'running').length);
  hasRunningExperiments = computed(() => this.currentRuns().length > 0);

  physicalMachinesCount = computed(() => this.allMachines().filter(m => !m.is_simulation_override).length);
  simulatedMachinesCount = computed(() => this.allMachines().filter(m => m.is_simulation_override).length);

  physicalOnlineMachines = computed(() =>
    this.allMachines().filter(m => !m.is_simulation_override && m.status !== MachineStatus.OFFLINE && m.status !== MachineStatus.ERROR).length
  );
  simulatedOnlineMachines = computed(() =>
    this.allMachines().filter(m => m.is_simulation_override && m.status !== MachineStatus.OFFLINE && m.status !== MachineStatus.ERROR).length
  );

  ngOnInit() {
    this.loadStats();
    this.loadRuns();
    this.subscribeToExecution();
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
  }

  private loadStats() {
    // Load machines
    this.subscription.add(
      this.assetService.getMachines().subscribe((machines: Machine[]) => {
        this.allMachines.set(machines);
      })
    );

    // Load resources
    this.subscription.add(
      this.assetService.getResources().subscribe((resources: Resource[]) => {
        this.totalResources.set(resources.length);
      })
    );

    // Load protocols
    this.subscription.add(
      this.protocolService.getProtocols().subscribe((protocols: ProtocolDefinition[]) => {
        this.totalProtocols.set(protocols.length);
      })
    );
  }



  private loadRuns() {
    // Start with empty recent runs - real runs will be populated by the application state
    this.recentRuns.set([]);
  }

  private subscribeToExecution() {
    // Watch for active runs from ExecutionService
    const currentRun = this.executionService.currentRun();
    if (currentRun) {
      this.currentRuns.set([{
        id: currentRun.runId,
        name: currentRun.protocolName,
        protocolName: currentRun.protocolName,
        status: this.mapExecutionStatus(currentRun.status),
        progress: currentRun.progress,
        startedAt: new Date()
      }]);
    }
  }

  private mapExecutionStatus(status: ExecutionStatus): 'running' | 'completed' | 'failed' | 'pending' {
    switch (status) {
      case ExecutionStatus.RUNNING: return 'running';
      case ExecutionStatus.COMPLETED: return 'completed';
      case ExecutionStatus.FAILED: return 'failed';
      case ExecutionStatus.CANCELLED: return 'failed';
      default: return 'pending';
    }
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'running': return 'play_arrow';
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'pending': return 'schedule';
      default: return 'help';
    }
  }

  formatTimeAgo(date: Date): string {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'running': return '!bg-[var(--mat-sys-primary-container)] !text-[var(--mat-sys-primary)]';
      case 'completed': return '!bg-[var(--mat-sys-success-container)] !text-[var(--mat-sys-success)]';
      case 'failed': return '!bg-[var(--mat-sys-error-container)] !text-[var(--mat-sys-error)]';
      case 'pending': return '!bg-[var(--mat-sys-warning-container)] !text-[var(--mat-sys-warning)]';
      default: return '!bg-[var(--mat-sys-surface-variant)] !text-sys-text-primary';
    }
  }

  getStatusBgClass(status: string): string {
    switch (status) {
      case 'running': return 'bg-[var(--mat-sys-primary-container)]';
      case 'completed': return 'bg-[var(--mat-sys-success-container)]';
      case 'failed': return 'bg-[var(--mat-sys-error-container)]';
      case 'pending': return 'bg-[var(--mat-sys-warning-container)]';
      default: return 'bg-[var(--mat-sys-surface-variant)]';
    }
  }

}

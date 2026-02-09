import { Component, inject, OnInit, OnDestroy, signal, computed, ChangeDetectionStrategy } from '@angular/core';

import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { Subscription, forkJoin } from 'rxjs';
import { NgxSkeletonLoaderModule } from 'ngx-skeleton-loader';
import { AssetService } from '../../services/asset.service';
import { Machine, Resource, ResourceStatus, MachineStatus } from '../../models/asset.models';
import { ModeService } from '@core/services/mode.service';


@Component({
  selector: 'app-asset-dashboard',
  standalone: true,
  imports: [
    MatIconModule,
    MatButtonModule,
    MatCardModule,
    MatTooltipModule,
    NgxSkeletonLoaderModule
  ],
  template: `
    <div class="h-full flex flex-col gap-6 overflow-y-auto">
      <!-- Stats Cards -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Machine Health Card -->
        <div class="group relative bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-6 flex items-center gap-4 hover:bg-surface-elevated transition-all cursor-pointer" 
             (click)="navigateTo('machine')">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-blue-500/20 to-cyan-500/20">
            <mat-icon class="text-blue-400">precision_manufacturing</mat-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-2xl font-bold text-sys-text-primary">
              @if (isLoading()) {
                 <ngx-skeleton-loader count="1" appearance="line" [theme]="{ width: '40px', height: '24px', 'margin-bottom': '0' }"></ngx-skeleton-loader>
              } @else {
                 {{ physicalOnlineMachinesCount() }}<span class="text-lg font-normal text-sys-text-secondary">/{{ physicalMachinesCount() }}</span>
              }
            </span>
            <span class="text-xs font-semibold text-sys-text-secondary uppercase tracking-wider leading-tight">Physical Machines Online</span>
          </div>
          <!-- Simulated Counter Mini -->
          <div class="ml-auto flex flex-col items-end opacity-60">
            <span class="text-sm font-bold text-sys-text-secondary">
              @if (!isLoading()) {
                {{ simulatedOnlineMachinesCount() }}/{{ simulatedMachinesCount() }}
              }
            </span>
            <span class="text-[10px] uppercase font-bold tracking-tight">Simulated</span>
          </div>
          @if (machinesAttentionCount() > 0) {
            <div class="absolute -top-2 -right-2 flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-400/10 border border-red-400/20 backdrop-blur-md shadow-lg">
              <span class="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse"></span>
              <span class="text-xs font-bold text-red-400">{{ machinesAttentionCount() }} Issues</span>
            </div>
          }
        </div>

        <!-- Resource Inventory Card -->
        <div class="group relative bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-6 flex items-center gap-4 hover:bg-surface-elevated transition-all cursor-pointer"
             (click)="navigateTo('resource')">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-orange-500/20 to-amber-500/20">
            <mat-icon class="text-orange-400">inventory_2</mat-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-2xl font-bold text-sys-text-primary">
               @if (isLoading()) {
                 <ngx-skeleton-loader count="1" appearance="line" [theme]="{ width: '40px', height: '24px', 'margin-bottom': '0' }"></ngx-skeleton-loader>
               } @else {
                 {{ totalResourcesCount() }}<span class="text-lg font-normal text-sys-text-secondary">/{{ totalDefinitionsCount() }}</span>
               }
            </span>
            <span class="text-xs font-semibold text-sys-text-secondary uppercase tracking-wider leading-tight">Instances · Types</span>
          </div>
          @if (lowStockCount() > 0) {
            <div class="absolute top-4 right-4 flex items-center gap-1.5 px-2 py-1 rounded-full bg-amber-400/10 border border-amber-400/20">
              <mat-icon class="text-amber-400 !w-3 !h-3 !text-[12px]">warning</mat-icon>
              <span class="text-xs font-bold text-amber-400">{{ lowStockCount() }} Low Stock</span>
            </div>
          }
        </div>

        <!-- Registry Card -->
        <div class="group relative bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-6 flex items-center gap-4 hover:bg-surface-elevated transition-all cursor-pointer"
             (click)="navigateTo('registry')">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-purple-500/20 to-pink-500/20">
            <mat-icon class="text-purple-400">inventory_2</mat-icon>
          </div>
          <div class="flex flex-col">
            <span class="text-2xl font-bold text-sys-text-primary">
               @if (isLoading()) {
                 <ngx-skeleton-loader count="1" appearance="line" [theme]="{ width: '40px', height: '24px', 'margin-bottom': '0' }"></ngx-skeleton-loader>
               } @else {
                 {{ totalDefinitionsCount() }}
               }
            </span>
            <span class="text-xs font-semibold text-sys-text-secondary uppercase tracking-wider leading-tight">Registry Types</span>
          </div>
          <div class="absolute top-4 right-4 text-xs font-semibold text-sys-text-secondary bg-[var(--mat-sys-surface-variant)] px-2 py-1 rounded border border-[var(--theme-border)]">
            Hardware Definitions
          </div>
        </div>
      </section>

      <!-- Section Labels -->
      <div class="flex items-center gap-4 px-1">
        <span class="text-lg font-semibold text-sys-text-secondary">Inventory</span>
        <div class="flex-1 h-px bg-[var(--theme-border)]"></div>
        <span class="text-xs font-medium text-sys-text-secondary">What you have</span>
      </div>

      <!-- Main Content Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        <!-- Quick Actions -->
        <section class="bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl overflow-hidden flex flex-col">
          <div class="p-4 border-b border-[var(--theme-border)] flex items-center justify-between">
            <h3 class="text-lg font-semibold text-sys-text-primary flex items-center gap-2">
              <mat-icon class="text-green-400">bolt</mat-icon>
              Quick Actions
            </h3>
          </div>
          <div class="p-4 grid grid-cols-2 gap-3">
             <button mat-stroked-button class="!border-[var(--theme-border)] !text-sys-text-secondary !justify-start !px-4 !py-4 hover:!bg-[var(--mat-sys-surface-variant)] hover:!border-primary/50 hover:!text-primary transition-all group flex items-center" (click)="triggerAction('add-machine')">
               <mat-icon class="mr-2 group-hover:text-primary transition-colors">add_circle</mat-icon>
               Add Machine
             </button>
             <button mat-stroked-button class="!border-[var(--theme-border)] !text-sys-text-secondary !justify-start !px-4 !py-4 hover:!bg-[var(--mat-sys-surface-variant)] hover:!border-primary/50 hover:!text-primary transition-all group flex items-center" (click)="triggerAction('add-resource')">
               <mat-icon class="mr-2 group-hover:text-primary transition-colors">add_box</mat-icon>
               Add Resource
             </button>
             <button mat-stroked-button class="!border-[var(--theme-border)] !text-sys-text-secondary !justify-start !px-4 !py-4 hover:!bg-[var(--mat-sys-surface-variant)] hover:!border-primary/50 hover:!text-primary transition-all group flex items-center" (click)="triggerAction('discover')">
               <mat-icon class="mr-2 group-hover:text-primary transition-colors">usb</mat-icon>
               Discover Hardware
             </button>
             <button mat-stroked-button class="!border-[var(--theme-border)] !text-sys-text-secondary !justify-start !px-4 !py-4 hover:!bg-[var(--mat-sys-surface-variant)] hover:!border-primary/50 hover:!text-primary transition-all group flex items-center" (click)="navigateTo('registry')">
               <mat-icon class="mr-2 group-hover:text-primary transition-colors">search</mat-icon>
               Browse Registry
             </button>
             @if (isBrowserMode) {
               <button mat-stroked-button class="!border-red-500/30 !text-red-400 !justify-start !px-4 !py-4 hover:!bg-red-500/10 hover:!border-red-500/50 transition-all group flex items-center col-span-2" (click)="triggerAction('reset-lab')">
                 <mat-icon class="mr-2 text-red-400 group-hover:text-red-300 transition-colors">restart_alt</mat-icon>
                 Reset Lab to Defaults
               </button>
             }
          </div>
        </section>

        <!-- Alerts & Attention -->
        <section class="bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl overflow-hidden flex flex-col h-full">
          <div class="p-4 border-b border-[var(--theme-border)] flex items-center justify-between">
            <h3 class="text-lg font-semibold text-sys-text-primary flex items-center gap-2">
              <mat-icon class="text-amber-400">notifications_active</mat-icon>
              Needs Attention
            </h3>
            @if (allAlerts().length > 0) {
              <span class="text-xs font-bold text-amber-400 bg-amber-400/10 px-2 py-1 rounded-full">{{ allAlerts().length }} Items</span>
            }
          </div>
          
          <div class="flex-1 overflow-y-auto max-h-[300px] p-2">
            @if (allAlerts().length > 0) {
              <div class="flex flex-col gap-2">
                @for (alert of allAlerts(); track alert.id) {
                  <div class="flex items-center gap-3 p-3 rounded-xl bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] hover:bg-surface-elevated transition-colors cursor-pointer group"
                       (click)="navigateTo(alert.type === 'machine' ? 'machine' : 'resource')">
                    <div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mr-1" 
                         [class.bg-red-400-20]="alert.severity === 'error'"
                         [class.bg-amber-400-20]="alert.severity === 'warning'">
                      <mat-icon [class.text-red-400]="alert.severity === 'error'"
                                [class.text-amber-400]="alert.severity === 'warning'"
                                class="!w-6 !h-6 !text-[24px]">
                        {{ alert.icon }}
                      </mat-icon>
                    </div>
                    
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center justify-between mb-1">
                        <span class="font-medium text-sys-text-primary truncate max-w-[70%] group-hover:text-primary transition-colors">{{ alert.name }}</span>
                        <span class="text-xs uppercase font-bold tracking-wider opacity-60 ml-2">{{ alert.type }}</span>
                      </div>
                      <p class="text-xs text-sys-text-secondary truncate">{{ alert.message }}</p>
                    </div>

                    <mat-icon class="text-sys-text-secondary group-hover:text-sys-text-primary">chevron_right</mat-icon>
                  </div>
                }
              </div>
            } @else {
              <div class="h-full flex flex-col items-center justify-center text-sys-text-secondary p-8">
                <mat-icon class="!w-12 !h-12 !text-[48px] mb-4 text-green-500/30">check_circle</mat-icon>
                <p class="text-lg font-semibold">All systems operational</p>
              </div>
            }
          </div>
        </section>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }
    .bg-red-400-20 { background-color: rgba(248, 113, 113, 0.2); }
    .bg-amber-400-20 { background-color: rgba(251, 191, 36, 0.2); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AssetDashboardComponent implements OnInit, OnDestroy {
  private assetService = inject(AssetService);
  private modeService = inject(ModeService);
  private router = inject(Router);
  private subscription = new Subscription();

  isBrowserMode = this.modeService.isBrowserMode();

  // Signals
  machines = signal<Machine[]>([]);
  resources = signal<Resource[]>([]);
  totalDefinitionsCount = signal(0);
  isLoading = signal(true);

  // Computed Stats
  totalMachinesCount = computed(() => this.machines().length);

  physicalMachines = computed(() => this.machines().filter(m => !m.is_simulation_override));
  simulatedMachines = computed(() => this.machines().filter(m => m.is_simulation_override));

  physicalMachinesCount = computed(() => this.physicalMachines().length);
  simulatedMachinesCount = computed(() => this.simulatedMachines().length);

  physicalOnlineMachinesCount = computed(() =>
    this.physicalMachines().filter(m => m.status !== MachineStatus.OFFLINE && m.status !== MachineStatus.ERROR).length
  );
  simulatedOnlineMachinesCount = computed(() =>
    this.simulatedMachines().filter(m => m.status !== MachineStatus.OFFLINE && m.status !== MachineStatus.ERROR).length
  );

  machinesAttentionCount = computed(() =>
    this.machines().filter(m => m.status === MachineStatus.ERROR || m.status === MachineStatus.OFFLINE).length
  );

  totalResourcesCount = computed(() => this.resources().length);
  lowStockCount = computed(() =>
    this.resources().filter(r => r.status === ResourceStatus.DEPLETED || r.status === ResourceStatus.EXPIRED).length
  );

  // Consolidated Alerts
  allAlerts = computed(() => {
    const alerts: any[] = [];

    // Machine Alerts
    this.machines().forEach(m => {
      if (m.status === MachineStatus.ERROR) {
        alerts.push({
          id: m.accession_id,
          type: 'machine',
          name: m.name,
          message: 'Machine reported an error state',
          severity: 'error',
          icon: 'error'
        });
      } else if (m.status === MachineStatus.OFFLINE) {
        alerts.push({
          id: m.accession_id,
          type: 'machine',
          name: m.name,
          message: 'Machine is offline',
          severity: 'error',
          icon: 'cloud_off'
        });
      }
    });

    // Resource Alerts
    this.resources().forEach(r => {
      if (r.status === ResourceStatus.DEPLETED) {
        alerts.push({
          id: r.accession_id,
          type: 'resource',
          name: 'Resource Depleted', // Ideally fetch definition name, simple for now
          message: 'Resource has been depleted',
          severity: 'warning',
          icon: 'remove_circle'
        });
      } else if (r.status === ResourceStatus.EXPIRED) {
        alerts.push({
          id: r.accession_id,
          type: 'resource',
          name: 'Resource Expired',
          message: 'Resource expiration date passed',
          severity: 'warning',
          icon: 'event_busy'
        });
      }
    });

    return alerts;
  });

  ngOnInit() {
    this.refreshData();
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
  }

  refreshData() {
    this.isLoading.set(true);
    this.subscription.add(
      forkJoin({
        machines: this.assetService.getMachines(),
        resources: this.assetService.getResources(),
        definitions: this.assetService.getResourceDefinitions()
      }).subscribe({
        next: (results) => {
          this.machines.set(results.machines);
          this.resources.set(results.resources);
          this.totalDefinitionsCount.set(results.definitions.length);
          this.isLoading.set(false);
        },
        error: (err) => {
          console.error('Failed to load dashboard data', err);
          this.isLoading.set(false);
        }
      })
    );
  }

  navigateTo(type: 'machine' | 'resource' | 'registry') {
    this.router.navigate([], {
      queryParams: { type: type },
      queryParamsHandling: 'merge'
    });
  }

  triggerAction(action: string) {
    // Dispatch custom event that parent AssetsComponent listens to?
    // Or navigate/open dialog directly?
    // Using custom event is cleaner to keep dialog logic in parent
    const event = new CustomEvent('asset-dashboard-action', { detail: action });
    window.dispatchEvent(event);
  }
}

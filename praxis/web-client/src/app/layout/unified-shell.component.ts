import { Component, inject, computed, OnInit } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';

import { CommonModule } from '@angular/common';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { AppStore } from '@core/store/app.store';
import { ModeService } from '@core/services/mode.service';
import { ExecutionService } from '@features/run-protocol/services/execution.service';
import { ExecutionStatus } from '@features/run-protocol/models/execution.models';
import { CommandRegistryService } from '@core/services/command-registry.service';
import { HardwareDiscoveryService } from '@core/services/hardware-discovery.service';
import { HardwareDiscoveryDialogComponent } from '@shared/components/hardware-discovery-dialog/hardware-discovery-dialog.component';
import { OnboardingService } from '@core/services/onboarding.service';
import { SessionRecoveryService } from '@core/services/session-recovery.service';
import { SessionRecoveryComponent } from '@core/components/session-recovery/session-recovery.component';
import { PRAXIS_LOGO_SVG_DATA } from '@shared/constants/logo';

@Component({
  selector: 'app-unified-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatIconModule,
    MatTooltipModule,
    MatTooltipModule,
    MatButtonModule
  ],
  template: `
    <div class="shell-layout">
      <!-- Thin Sidebar Rail -->
      <nav class="sidebar-rail">
        <!-- Logo / Home -->
        <a class="nav-item logo-item" [routerLink]="modeService.isBrowserMode() ? '/app/home' : (store.auth().isAuthenticated ? '/app/home' : '/')" matTooltip="Home" matTooltipPosition="right">
          <div class="logo-container">
            <div class="logo-image" data-testid="praxis-logo" [style]="logoCssVar()"></div>

          </div>
        </a>

        <div class="nav-divider"></div>

        <!-- Action -->
        <a class="nav-item" data-tour-id="nav-run" routerLink="/app/run" routerLinkActive="active" matTooltip="Run Protocol" matTooltipPosition="right">
          <mat-icon>play_circle</mat-icon>
          <span class="nav-label">Run</span>
        </a>
        <a class="nav-item" data-tour-id="nav-monitor" routerLink="/app/monitor" routerLinkActive="active" matTooltip="Execution Monitor" matTooltipPosition="right">
          <mat-icon>monitor_heart</mat-icon>
          <span class="nav-label">Monitor</span>
        </a>

        <div class="nav-divider"></div>

        <!-- Management -->
        <a class="nav-item" data-tour-id="nav-assets" routerLink="/app/assets" routerLinkActive="active" matTooltip="Assets" matTooltipPosition="right">
          <mat-icon>precision_manufacturing</mat-icon>
          <span class="nav-label">Assets</span>
        </a>
        <a class="nav-item" data-tour-id="nav-protocols" routerLink="/app/protocols" routerLinkActive="active" matTooltip="Protocols" matTooltipPosition="right">
          <mat-icon>science</mat-icon>
          <span class="nav-label">Protocols</span>
        </a>

        <div class="nav-divider"></div>

        <!-- Views -->
        <a class="nav-item" data-tour-id="nav-workcell" routerLink="/app/workcell" routerLinkActive="active" matTooltip="Workcell View" matTooltipPosition="right">
          <mat-icon>view_in_ar</mat-icon>
          <span class="nav-label">Workcell</span>
        </a>
        <a class="nav-item" data-tour-id="nav-data" routerLink="/app/data" routerLinkActive="active" matTooltip="Data Analysis" matTooltipPosition="right">
          <mat-icon>bar_chart</mat-icon>
          <span class="nav-label">Data</span>
        </a>

        <div class="nav-divider"></div>

        <!-- Knowledge -->
        <a class="nav-item" routerLink="/docs" routerLinkActive="active" matTooltip="Documentation" matTooltipPosition="right">
          <mat-icon>menu_book</mat-icon>
          <span class="nav-label">Docs</span>
        </a>

        <!-- Tools -->
        <a class="nav-item" data-tour-id="nav-playground" routerLink="/app/playground" routerLinkActive="active" matTooltip="Playground" matTooltipPosition="right">
          <mat-icon>terminal</mat-icon>
          <span class="nav-label">Playground</span>
        </a>

        <div class="spacer"></div>

        <!-- System -->
        <a class="nav-item" data-tour-id="nav-settings" routerLink="/app/settings" routerLinkActive="active" matTooltip="Settings" matTooltipPosition="right">
          <mat-icon>settings</mat-icon>
          <span class="nav-label">Settings</span>
        </a>

        <div class="nav-divider"></div>


        <button
          class="nav-item control-btn theme-toggle"
          data-tour-id="theme-toggle"
          (click)="cycleTheme()"
          [matTooltip]="'Theme: ' + (store.theme() | titlecase)"
          matTooltipPosition="right">
          <mat-icon>{{ themeIcon() }}</mat-icon>
          <span class="nav-label small">{{ store.theme() }}</span>
        </button>

        <div 
          class="mode-badge" 
          data-tour-id="status-indicator"
          [class]="systemStatus().color"
          [matTooltip]="systemStatus().message" 
          matTooltipPosition="right">
          <mat-icon>{{ systemStatus().icon }}</mat-icon>
          <span class="nav-label">{{ modeService.modeLabel() }}</span>
        </div>

        @if (store.auth().isAuthenticated && !modeService.isBrowserMode()) {
          <button
            class="nav-item control-btn"
            (click)="logout()"
            matTooltip="Logout"
            matTooltipPosition="right">
            <mat-icon>logout</mat-icon>
            <span class="nav-label">Logout</span>
          </button>
        } @else if (!modeService.isBrowserMode()) {
          <a
            class="nav-item"
            routerLink="/login"
            matTooltip="Sign In"
            matTooltipPosition="right">
            <mat-icon>login</mat-icon>
            <span class="nav-label">Login</span>
          </a>
        }
      </nav>

      <!-- Main Content -->
      <div class="main-wrapper">
        <main class="main-content">
          <router-outlet></router-outlet>
        </main>

        <footer class="app-footer">
            <a href="https://github.com/maraxen/praxis" target="_blank" class="footer-link" matTooltip="GitHub Repository">
                <mat-icon>code</mat-icon>
            </a>
            <a href="https://github.com/maraxen/praxis" target="_blank" class="footer-link" matTooltip="Star on GitHub">
                <mat-icon>star_border</mat-icon>
            </a>
            <a href="https://github.com/maraxen/praxis/issues/new" target="_blank" class="footer-link" matTooltip="Raise an Issue">
                <mat-icon>bug_report</mat-icon>
            </a>
            <div class="footer-divider"></div>
            <a href="https://labautomation.io" target="_blank" class="footer-link" matTooltip="LabAutomation.io">
                <mat-icon>forum</mat-icon>
            </a>
            <a href="https://pylabrobot.org" target="_blank" class="footer-link" matTooltip="PyLabRobot.org">
                <mat-icon>biotech</mat-icon>
            </a>
        </footer>
      </div>
    </div>
  `,
  styles: [`
    .shell-layout {
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      background: var(--theme-bg-gradient);
    }

    /* Sidebar Rail */
    .sidebar-rail {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 5rem;
      min-width: 5rem;
      background: var(--mat-sys-surface-container);
      border-right: 1px solid var(--mat-sys-outline-variant);
      z-index: 100;
      padding: 0.75rem 0;
      gap: 0.25rem;
    }

    .nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 64px;
      height: 56px;
      border-radius: 12px;
      margin: 2px 0;
      color: var(--mat-sys-on-surface-variant);
      text-decoration: none;
      transition: all 0.2s ease;
      cursor: pointer;
      border: none;
      background: transparent;
      gap: 2px;
    }

    .nav-item:hover {
      background: var(--mat-sys-surface-variant);
      color: var(--mat-sys-on-surface);
    }

    .nav-item.active {
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
    }

    /* Gradient Hover & Active State for Icons */
    .nav-item:hover mat-icon,
    .nav-item.active mat-icon {
      background: linear-gradient(135deg, var(--primary-color) 0%, var(--tertiary-color) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .nav-item mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }

    .nav-label {
      display: none; /* Hidden in rail mode - rely on tooltips */
    }

    /* Logo */
    .logo-item {
      margin-bottom: 8px;
      opacity: 1 !important;
      height: 48px; /* Restore simpler height for logo */
    }

    .logo-container {
      width: 80px;
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: none;
      border: none;
      outline: none;
      transition: all 0.3s ease;
    }

    .logo-item:hover .logo-container {
      transform: scale(1.05);
    }

    .logo-item:hover {
        background: none !important;
    }

    .logo-image {
      --logo-svg: none;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, var(--primary-color) 0%, var(--tertiary-color) 100%);
      -webkit-mask: var(--logo-svg) no-repeat center;
      mask: var(--logo-svg) no-repeat center;
      -webkit-mask-size: contain;
      mask-size: contain;
    }
    /* Divider */
    .nav-divider {
      width: 40px;
      height: 1px;
      background: var(--mat-sys-outline-variant);
      margin: 4px 0;
    }

    /* Spacer */
    .spacer {
      flex: 1;
    }

    /* Control Buttons */
    .control-btn {
      color: var(--mat-sys-on-surface-variant);
    }

    /* Mode Badge */
    .mode-badge {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 64px;
      height: 56px;
      border-radius: 12px;
      margin: 2px 0;
      background: var(--mat-sys-surface-container-high);
      border: 1px solid var(--mat-sys-outline-variant);
      color: var(--mat-sys-on-surface-variant);
      gap: 2px;
    }

    .mode-badge.good {
      background: var(--mat-sys-success-container);
      border-color: var(--status-success);
      color: var(--status-success);
    }

    .mode-badge.attention {
      background: var(--mat-sys-warning-container);
      border-color: var(--status-warning);
      color: var(--status-warning);
    }

    .mode-badge.problem {
      background: var(--mat-sys-error-container);
      border-color: var(--status-error);
      color: var(--status-error);
    }

    .theme-toggle {
      height: 48px;
    }

    .mode-badge mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

  /* Main Content */
    .main-wrapper {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-width: 0;
      position: relative; /* For stacking context if needed */
    }

    .main-content {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      /* Add padding if needed, or rely on child components */
    }

    /* Footer */
    .app-footer {
        height: 2rem;
        min-height: 2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        background: var(--mat-sys-surface-container);
        border-top: 1px solid var(--mat-sys-outline-variant);
        padding: 0 1rem;
        z-index: 10;
        font-size: 0.75rem;
    }

    .footer-link {
        color: var(--mat-sys-on-surface-variant);
        opacity: 0.5;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        width: 1.5rem;
        height: 1.5rem;
        border-radius: 50%;
    }

    .footer-link:hover {
        opacity: 1;
        background: var(--mat-sys-surface-variant);
        color: var(--mat-sys-primary);
    }

    .footer-link mat-icon {
        font-size: 1rem;
        width: 1rem;
        height: 1rem;
    }

    .footer-divider {
        width: 1px;
        height: 1rem;
        background: var(--mat-sys-outline-variant);
        opacity: 0.5;
    }

    /* Responsive */
    @media (max-width: 768px) {
      .sidebar-rail {
        width: 4rem;
        min-width: 4rem;
      }
      
      .nav-item {
        width: 3.25rem;
        height: 3.25rem;
      }

      .nav-label {
        font-size: 0.55rem;
      }

      .nav-divider {
        width: 2rem;
      }
    }
  `]
})
export class UnifiedShellComponent implements OnInit {
  readonly logoData = PRAXIS_LOGO_SVG_DATA;
  private sanitizer = inject(DomSanitizer);
  readonly logoCssVar = computed(() =>
    this.sanitizer.bypassSecurityTrustStyle(`--logo-svg: url("${this.logoData}")`)
  );
  store = inject(AppStore);

  router = inject(Router);
  modeService = inject(ModeService);
  executionService = inject(ExecutionService);
  private commandRegistry = inject(CommandRegistryService);
  private hardwareDiscovery = inject(HardwareDiscoveryService);
  private dialog = inject(MatDialog);
  private onboarding = inject(OnboardingService);
  private sessionRecovery = inject(SessionRecoveryService);

  constructor() {
    this.registerCommands();
  }

  ngOnInit() {
    // On first visit, auto-enable hints instead of showing a welcome dialog
    if (this.onboarding.shouldShowWelcome()) {
      this.onboarding.enableHints();
      this.onboarding.markOnboardingComplete();
    }

    // Check for orphaned runs
    this.checkForOrphanedRuns();
  }

  private checkForOrphanedRuns(): void {
    this.sessionRecovery.checkForOrphanedRuns().subscribe(orphanedRuns => {
      if (orphanedRuns.length > 0) {
        const dialogRef = this.dialog.open(SessionRecoveryComponent, {
          data: { runs: orphanedRuns },
          width: '500px',
          disableClose: false
        });

        dialogRef.afterClosed().subscribe(result => {
          if (result === 'mark-as-failed') {
            this.sessionRecovery.markAllAsFailed(orphanedRuns).subscribe();
          }
        });
      }
    });
  }

  private registerCommands() {
    this.commandRegistry.registerCommand({
      id: 'hardware.discover',
      label: 'Discover Hardware',
      description: 'Scan for connected devices (Serial/USB)',
      icon: 'usb',
      category: 'Hardware',
      action: () => {
        this.dialog.open(HardwareDiscoveryDialogComponent, {
          width: '800px',
          maxHeight: '90vh'
        });
        if (!this.hardwareDiscovery.isDiscovering()) {
          this.hardwareDiscovery.discoverAll();
        }
      }
    });
  }

  readonly systemStatus = computed(() => {
    const isBrowser = this.modeService.isBrowserMode();
    const isConnected = this.executionService.isConnected();
    const run = this.executionService.currentRun();
    const mode = this.modeService.modeLabel();

    // Problem State: Disconnected (non-browser) or run failed
    if ((!isBrowser && !isConnected && (mode === 'Production' || mode === 'Lite')) || run?.status === ExecutionStatus.FAILED) {
      return {
        color: 'problem',
        icon: 'error_outline',
        message: run?.status === ExecutionStatus.FAILED ? `Run Failed: ${run.protocolName}` : 'System Disconnected'
      };
    }

    // Attention State: Running, pending or cancelled
    if (run?.status === ExecutionStatus.RUNNING || run?.status === ExecutionStatus.PENDING || run?.status === ExecutionStatus.CANCELLED) {
      return {
        color: 'attention',
        icon: run.status === ExecutionStatus.RUNNING ? 'running_with_errors' : 'hourglass_empty',
        message: `Protocol ${run.status}: ${run.protocolName}`
      };
    }

    // Good State: Everything else
    return {
      color: 'good',
      icon: isBrowser ? 'cloud_done' : 'check_circle_outline',
      message: `System Ready - ${mode} Mode`
    };
  });

  // Check if current route is in /app/*
  isInApp(): boolean {
    return this.router.url.startsWith('/app');
  }

  themeIcon(): string {
    switch (this.store.theme()) {
      case 'light': return 'light_mode';
      case 'dark': return 'dark_mode';
      case 'system': return 'brightness_auto';
      default: return 'brightness_auto';
    }
  }

  cycleTheme(): void {
    const themes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(this.store.theme());
    const nextIndex = (currentIndex + 1) % themes.length;
    this.store.setTheme(themes[nextIndex]);
  }

  logout(): void {
    this.store.logout();
  }
}

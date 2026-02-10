import { Component, Input, OnInit, OnDestroy, inject, ViewChild, TemplateRef, ViewContainerRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Overlay, OverlayRef, OverlayModule } from '@angular/cdk/overlay';
import { TemplatePortal } from '@angular/cdk/portal';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { OnboardingService } from '@core/services/onboarding.service';
import { animate, style, transition, trigger } from '@angular/animations';

@Component({
  selector: 'app-page-tooltip',
  standalone: true,
  imports: [CommonModule, OverlayModule, MatButtonModule, MatIconModule],
  template: `
    <ng-template #tooltipTemplate>
      <div class="page-tooltip-panel glass-panel" [@tooltipAnimation] role="status" [attr.aria-label]="text">
        <div class="tooltip-arrow"></div>
        <div class="tooltip-header">
           <mat-icon class="hint-icon">lightbulb_outline</mat-icon>
           <span class="hint-title">Praxis Hint</span>
           <button mat-icon-button class="dismiss-btn" (click)="dismiss()" aria-label="Dismiss hint">
             <mat-icon>close</mat-icon>
           </button>
        </div>
        <div class="tooltip-body">
            <p [innerHTML]="text"></p>
        </div>
        @if (isFirst) {
          <div class="tooltip-footer">
            <button mat-button class="dismiss-all-link" (click)="dismissAll()">
              Dismiss all hints
            </button>
          </div>
        }
      </div>
    </ng-template>
  `,
  styles: [`
    .page-tooltip-panel {
      position: relative;
      padding: 1rem;
      max-width: 280px;
      margin: 12px;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      z-index: 1000;
      pointer-events: auto;
    }

    .glass-panel {
      background: rgba(var(--mat-sys-surface-container-rgb), 0.9);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--theme-border);
    }

    .tooltip-header {
      display: flex;
      align-items: center;
      margin-bottom: 0.5rem;
      gap: 0.5rem;
    }

    .hint-icon {
      color: var(--mat-sys-primary);
      font-size: 1.25rem;
      width: 1.25rem;
      height: 1.25rem;
    }

    .hint-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--mat-sys-primary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      flex: 1;
    }

    .dismiss-btn {
      width: 24px;
      height: 24px;
      line-height: 24px;
      margin-right: -8px;
      margin-top: -8px;
    }

    .dismiss-btn mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .tooltip-body {
      font-size: 0.95rem;
      line-height: 1.4;
      color: var(--mat-sys-on-surface);
    }

    .tooltip-footer {
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px solid var(--theme-border);
      display: flex;
      justify-content: flex-end;
    }

    .dismiss-all-link {
       font-size: 0.75rem;
       height: 28px;
       padding: 0 8px;
       color: var(--mat-sys-on-surface-variant);
       opacity: 0.8;
    }

    .dismiss-all-link:hover {
       opacity: 1;
       color: var(--mat-sys-primary);
    }

    .tooltip-arrow {
      position: absolute;
      width: 0;
      height: 0;
      border-style: solid;
      /* Positioning logic handled by overlay strategy if we want, 
         but simple css for now assuming default 'bottom' placement */
    }

    @media (prefers-reduced-motion: reduce) {
      .page-tooltip-panel {
        animation: none !important;
        transition: none !important;
      }
    }
  `],
  animations: [
    trigger('tooltipAnimation', [
      transition(':enter', [
        style({ opacity: 0, transform: 'scale(0.95) translateY(5px)' }),
        animate('250ms cubic-bezier(0.2, 0, 0, 1)', style({ opacity: 1, transform: 'scale(1) translateY(0)' }))
      ]),
      transition(':leave', [
        animate('150ms ease-in', style({ opacity: 0, transform: 'scale(0.95) translateY(5px)' }))
      ])
    ])
  ]
})
export class PageTooltipComponent implements OnInit, OnDestroy {
  @Input({ required: true }) id!: string;
  @Input({ required: true }) text!: string;
  @Input({ required: true }) target!: HTMLElement;
  @Input() isFirst = false;

  @ViewChild('tooltipTemplate') tooltipTemplate!: TemplateRef<any>;

  private overlay = inject(Overlay);
  private viewContainerRef = inject(ViewContainerRef);
  private onboarding = inject(OnboardingService);
  private overlayRef?: OverlayRef;

  ngOnInit() {
    // Small delay to ensure host is rendered and signals are ready
    setTimeout(() => {
      if (this.onboarding.showHints() && !this.onboarding.isTooltipDismissed(this.id)) {
        this.show();
      }
    }, 500);
  }

  ngOnDestroy() {
    this.hide();
  }

  show() {
    const positionStrategy = this.overlay.position()
      .flexibleConnectedTo(this.target)
      .withPositions([
        {
          originX: 'center',
          originY: 'bottom',
          overlayX: 'center',
          overlayY: 'top',
        },
        {
          originX: 'end',
          originY: 'center',
          overlayX: 'start',
          overlayY: 'center',
        },
        {
          originX: 'start',
          originY: 'center',
          overlayX: 'end',
          overlayY: 'center',
        },
        {
          originX: 'center',
          originY: 'top',
          overlayX: 'center',
          overlayY: 'bottom',
        }
      ]);

    this.overlayRef = this.overlay.create({
      positionStrategy,
      scrollStrategy: this.overlay.scrollStrategies.reposition(),
      hasBackdrop: false
    });

    const portal = new TemplatePortal(this.tooltipTemplate, this.viewContainerRef);
    this.overlayRef.attach(portal);
  }

  hide() {
    if (this.overlayRef) {
      this.overlayRef.detach();
      this.overlayRef.dispose();
      this.overlayRef = undefined;
    }
  }

  dismiss() {
    this.onboarding.dismissTooltip(this.id);
    this.hide();
  }

  dismissAll() {
    this.onboarding.disableHints();
    this.hide();
  }
}

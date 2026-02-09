import { Component, inject, input, output, computed, OnInit, signal } from '@angular/core';

import { DragDropModule, CdkDragDrop } from '@angular/cdk/drag-drop';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';

import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { PlrResource } from '@core/models/plr.models';
import { WizardStateService } from '../../services/wizard-state.service';
import { CarrierPlacementStepComponent } from './carrier-placement-step.component';
import { ResourcePlacementStepComponent } from './resource-placement-step.component';
import { VerificationStepComponent } from './verification-step.component';
import { DeckViewComponent } from '@shared/components/deck-view/deck-view.component';
import { SetupInstructionsComponent } from '../setup-instructions/setup-instructions.component';
import { RequirementsPanelComponent, DeckValidationState } from '../requirement-indicator';

/**
 * Main container for the 3-step Guided Deck Setup wizard.
 */
@Component({
    selector: 'app-deck-setup-wizard',
    standalone: true,
    imports: [
        MatStepperModule,
        MatButtonModule,
        MatIconModule,
        MatProgressBarModule,
        MatProgressBarModule,
        MatDialogModule,
        DragDropModule,
        CarrierPlacementStepComponent,
        ResourcePlacementStepComponent,
        VerificationStepComponent,
        DeckViewComponent,
        SetupInstructionsComponent,
        RequirementsPanelComponent
    ],
    template: `
        <div class="wizard-container" cdkDropListGroup>
            <div class="wizard-header">
                <h2>
                    <mat-icon>dashboard_customize</mat-icon>
                    Guided Deck Setup
                </h2>
                <mat-progress-bar 
                    mode="determinate" 
                    [value]="wizardState.progress()">
                </mat-progress-bar>
            </div>
            
            <!-- Setup Instructions Panel (shown before main content) -->
            @if (protocol()?.setup_instructions?.length) {
                <app-setup-instructions
                    [instructions]="protocol()?.setup_instructions ?? null"
                    [showLegend]="true"
                    (allRequiredChecked)="onAllRequiredInstructionsChecked($event)">
                </app-setup-instructions>
            }
            
            <div class="wizard-content">
                <div class="step-panel">
                    <!-- Requirements Panel -->
                    @if (protocol()?.accession_id) {
                        <app-requirements-panel
                            [protocolId]="protocol()!.accession_id"
                            [deckState]="deckValidationState()">
                        </app-requirements-panel>
                    }
                    
                    @switch (wizardState.currentStep()) {
                        @case ('carrier-placement') {
                            <app-carrier-placement-step
                                [carrierRequirements]="wizardState.carrierRequirements()"
                                (carrierPlaced)="onCarrierPlaced($event)">
                            </app-carrier-placement-step>
                        }
                        @case ('resource-placement') {
                            <app-resource-placement-step
                                [assignments]="wizardState.slotAssignments()"
                                (resourcePlaced)="onResourcePlaced($event)">
                            </app-resource-placement-step>
                        }
                        @case ('verification') {
                            <app-verification-step
                                [carrierRequirements]="wizardState.carrierRequirements()"
                                [slotAssignments]="wizardState.slotAssignments()"
                                (confirmed)="onConfirm()">
                            </app-verification-step>
                        }
                    }
                </div>
                
                <div class="deck-preview">
                    @if (liveDeckResource()) {
                        <app-deck-view 
                            [resource]="liveDeckResource()"
                            [state]="{}"
                            (itemDropped)="onDropOnDeck($event)">
                        </app-deck-view>
                    }
                </div>
            </div>
            
            <div class="wizard-footer">
                <button mat-stroked-button 
                        color="warn"
                        (click)="onSkip()">
                    Skip Setup
                </button>
                
                <div class="spacer"></div>
                
                @if (wizardState.currentStep() !== 'carrier-placement') {
                    <button mat-stroked-button (click)="onBack()">
                        <mat-icon>arrow_back</mat-icon>
                        Back
                    </button>
                }
                
                @if (wizardState.currentStep() !== 'verification') {
                    <button mat-flat-button 
                            color="primary" 
                            [disabled]="!canProceed()"
                            (click)="onNext()">
                        Next
                        <mat-icon>arrow_forward</mat-icon>
                    </button>
                } @else {
                    <button mat-flat-button 
                            color="primary" 
                            (click)="onConfirm()">
                        <mat-icon>check</mat-icon>
                        Confirm & Continue
                    </button>
                }
            </div>
        </div>
    `,
    styles: [`
        :host {
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }

        .wizard-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            min-height: 0; /* Allow shrinking below previous 500px fixed min */
        }
        
        .wizard-header {
            padding: 16px 24px;
            border-bottom: 1px solid var(--sys-outline-variant);
            flex-shrink: 0;
        }
        
        .wizard-header h2 {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 12px 0;
            color: var(--sys-on-surface);
        }
        
        .wizard-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: minmax(0, 1fr);
            gap: 24px;
            flex: 1; /* Grow to fill available space */
            padding: 24px;
            overflow: hidden; /* Prevent this level from scrolling */
            min-height: 0;
        }
        
        .step-panel {
            overflow-y: auto; /* Allow items list to scroll */
            min-height: 0;
            padding-right: 8px;
        }
        
        .deck-preview {
            background: var(--sys-surface-container);
            border-radius: 8px;
            padding: 16px;
            overflow: auto;
            min-height: 0;
        }
        
        .wizard-footer {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 24px;
            border-top: 1px solid var(--sys-outline-variant);
            flex-shrink: 0; /* Footer must never shrink or disappear */
            background: var(--sys-surface);
            z-index: 10;
        }
        
        .spacer {
            flex: 1;
        }
        
        @media (max-width: 992px) {
            .wizard-content {
                grid-template-columns: 1fr;
                grid-template-rows: auto 1fr;
                overflow-y: auto;
            }
            
            .step-panel {
                flex: none;
                overflow: visible;
                max-height: 400px;
                overflow-y: auto;
            }

            .deck-preview {
                min-height: 300px;
                flex: 1;
            }
        }
    `]
})
export class DeckSetupWizardComponent implements OnInit {
    // Input for inline usage (when not opened via dialog)
    data = input<{ protocol: ProtocolDefinition, deckResource: PlrResource | null, assetMap?: Record<string, any>, deckType?: string } | null>(null);

    // Signals initialized from Dialog Data or Input
    protocol = signal<ProtocolDefinition | null>(null);
    deckResource = signal<PlrResource | null>(null);

    /**
     * Reactive deck resource that updates as items are placed in the wizard.
     * Falls back to the static input resource when wizard hasn't built anything.
     */
    liveDeckResource = computed(() => {
        const wizardResource = this.wizardState.deckResource();
        // Use wizard-built tree once it has meaningful dimensions (i.e. initialized)
        // Otherwise fall back to the static input resource
        return wizardResource?.size_x > 0 ? wizardResource : this.deckResource();
    });

    setupComplete = output<void>();
    setupSkipped = output<void>();

    wizardState = inject(WizardStateService);
    private dialog = inject(MatDialog);
    // Optional injection in case it's not opened via dialog
    private dialogRef = inject(MatDialogRef, { optional: true });

    /** Deck validation state for requirements panel */
    deckValidationState = computed<DeckValidationState>(() => {
        const placedResources = new Set<string>();
        const liquidConfirmed = new Set<string>();
        let hasTipRack = false;

        // Collect placed resources from carrier requirements
        const carriers = this.wizardState.carrierRequirements();
        for (const carrier of carriers) {
            if (carrier.placed) {
                placedResources.add(carrier.carrierFqn);
            }
        }

        // Collect placed resources from slot assignments
        const assignments = this.wizardState.slotAssignments();
        for (const assignment of assignments) {
            if (assignment.placed && assignment.resource) {
                placedResources.add(assignment.resource.name);
                // Check if it's a tip rack
                if (assignment.resource.name.toLowerCase().includes('tip')) {
                    hasTipRack = true;
                }
            }
        }

        return { placedResources, liquidConfirmed, hasTipRack };
    });

    // Optional dialog data injection
    private dialogData = inject<{ protocol: ProtocolDefinition, deckResource: PlrResource } | null>(MAT_DIALOG_DATA, { optional: true });

    constructor() {
        // Initialize from dialog data if present
        if (this.dialogData) {
            this.protocol.set(this.dialogData.protocol);
            this.deckResource.set(this.dialogData.deckResource);
        }
    }

    canProceed = computed(() => {
        const step = this.wizardState.currentStep();
        if (step === 'carrier-placement') {
            return this.wizardState.allCarriersPlaced();
        }
        if (step === 'resource-placement') {
            return this.wizardState.allResourcesPlaced();
        }
        return true;
    });

    ngOnInit(): void {
        // Check input binding (for inline usage) if dialog data wasn't available
        const inputData = this.data();
        if (inputData && !this.protocol()) {
            this.protocol.set(inputData.protocol);
            this.deckResource.set(inputData.deckResource);
        }

        const p = this.protocol();
        if (p) {
            // Extract assetMap from input data if available
            // For dialog usage, we might need to update the dialog data interface too, 
            // but currently the priority is inline usage.
            const assetMap = (inputData as any)?.assetMap || {};
            const deckType = (inputData as any)?.deckType || 'HamiltonSTARDeck';
            this.wizardState.initialize(p, deckType, assetMap);
        }
    }


    onCarrierPlaced(event: { carrierFqn: string; placed: boolean }): void {
        this.wizardState.markCarrierPlaced(event.carrierFqn, event.placed);
    }

    onResourcePlaced(event: { resourceName: string; placed: boolean }): void {
        this.wizardState.markResourcePlaced(event.resourceName, event.placed);
    }

    onNext(): void {
        this.wizardState.nextStep();
    }

    onBack(): void {
        this.wizardState.previousStep();
    }

    onSkip(): void {
        // TODO: Add confirmation dialog
        this.wizardState.skip();
        this.setupSkipped.emit();
        this.dialogRef?.close();
    }

    onConfirm(): void {
        this.wizardState.complete();
        this.setupComplete.emit();
        // Return expected result format for RunProtocolComponent
        const result = {
            assetMap: this.wizardState.getAssetMap()
        };
        this.dialogRef?.close(result);
    }

    onDropOnDeck(event: any): void {
        // Handle drop event from DeckView
        if (event && event.item && event.item.data) {
            const assignment = event.item.data;
            if (assignment && assignment.resource) {
                this.onResourcePlaced({
                    resourceName: assignment.resource.name,
                    placed: true
                });
            }
        }
    }

    /**
     * Signal tracking whether all required setup instructions are checked.
     * Defaults to true if there are no instructions.
     */
    allRequiredInstructionsCompleted = signal<boolean>(true);

    /**
     * Handler for when setup instructions completion state changes.
     */
    onAllRequiredInstructionsChecked(allComplete: boolean): void {
        this.allRequiredInstructionsCompleted.set(allComplete);
    }
}

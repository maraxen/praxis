import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { DeckDefinitionSpec } from '../../../features/run-protocol/models/deck-layout.models';

export interface DeckSelectorDialogData {
    decks: DeckDefinitionSpec[];
    frontendName: string;
    backendName: string;
}

@Component({
    selector: 'app-deck-selector-dialog',
    standalone: true,
    imports: [CommonModule, MatDialogModule, MatIconModule, MatButtonModule],
    template: `
    <div class="deck-dialog">
      <h2 mat-dialog-title>
        <mat-icon>dashboard</mat-icon>
        Select Deck Layout
      </h2>

      <mat-dialog-content>
        <p class="deck-dialog-description">
          Choose a deck layout for your <strong>{{ data.frontendName }}</strong>
          with <strong>{{ data.backendName }}</strong> driver.
        </p>

        <div class="deck-grid">
          @for (deck of data.decks; track deck.fqn) {
            <div class="deck-card"
                 [class.selected]="selectedDeck?.fqn === deck.fqn"
                 (click)="selectDeck(deck)">
              <div class="deck-card-icon">
                <mat-icon>dashboard</mat-icon>
              </div>
              <div class="deck-card-info">
                <span class="deck-name">{{ deck.name }}</span>
                <span class="deck-manufacturer">{{ deck.manufacturer }}</span>
                <div class="deck-specs">
                  <span class="deck-chip">
                    {{ deck.layoutType === 'rail-based' ? deck.numRails + ' rails' : deck.numSlots + ' slots' }}
                  </span>
                  <span class="deck-chip">
                    {{ deck.dimensions.width }}×{{ deck.dimensions.height }}mm
                  </span>
                </div>
              </div>
              @if (selectedDeck?.fqn === deck.fqn) {
                <mat-icon class="check-icon">check_circle</mat-icon>
              }
            </div>
          }
        </div>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button (click)="cancel()">Cancel</button>
        <button mat-flat-button color="primary" [disabled]="!selectedDeck" (click)="confirm()">
          Select Deck
        </button>
      </mat-dialog-actions>
    </div>
  `,
    styles: [`
    .deck-dialog {
      min-width: 400px;
      max-width: 600px;
    }
    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      padding: 16px 24px;
      font-size: 18px;
      font-weight: 500;
    }
    .deck-dialog-description {
      margin: 0 0 16px;
      color: var(--mat-sys-on-surface-variant, #666);
      font-size: 13px;
      line-height: 1.5;
    }
    .deck-grid {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .deck-card {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border: 1px solid var(--mat-sys-outline-variant, #ddd);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      background: var(--mat-sys-surface, #fff);
    }
    .deck-card:hover {
      border-color: var(--mat-sys-primary, #6750a4);
      background: var(--mat-sys-primary-container, #f3edf7);
    }
    .deck-card.selected {
      border-color: var(--mat-sys-primary, #6750a4);
      background: var(--mat-sys-primary-container, #f3edf7);
      box-shadow: 0 0 0 1px var(--mat-sys-primary, #6750a4);
    }
    .deck-card-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: var(--mat-sys-tertiary-container, #e8def8);
      color: var(--mat-sys-tertiary, #7d5260);
      flex-shrink: 0;
    }
    .deck-card-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .deck-name {
      font-weight: 500;
      font-size: 14px;
      color: var(--mat-sys-on-surface, #1d1b20);
    }
    .deck-manufacturer {
      font-size: 12px;
      color: var(--mat-sys-on-surface-variant, #49454f);
    }
    .deck-specs {
      display: flex;
      gap: 6px;
      margin-top: 4px;
    }
    .deck-chip {
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      background: var(--mat-sys-surface-variant, #e7e0ec);
      color: var(--mat-sys-on-surface-variant, #49454f);
    }
    .check-icon {
      color: var(--mat-sys-primary, #6750a4);
      flex-shrink: 0;
    }
    mat-dialog-actions {
      padding: 12px 24px 16px;
    }
  `]
})
export class DeckSelectorDialogComponent {
    readonly data = inject<DeckSelectorDialogData>(MAT_DIALOG_DATA);
    private dialogRef = inject(MatDialogRef<DeckSelectorDialogComponent>);

    selectedDeck: DeckDefinitionSpec | null = null;

    selectDeck(deck: DeckDefinitionSpec) {
        this.selectedDeck = deck;
    }

    confirm() {
        this.dialogRef.close(this.selectedDeck);
    }

    cancel() {
        this.dialogRef.close(null);
    }
}

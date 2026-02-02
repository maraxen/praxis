import { Component, OnInit, AfterViewInit, inject, signal, computed, ViewChild, ElementRef, PLATFORM_ID, ViewEncapsulation, effect } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { toSignal } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, startWith, switchMap, map } from 'rxjs/operators';
import { of, combineLatest } from 'rxjs';
import { CommandRegistryService, Command } from '../../services/command-registry.service';
import { AssetSearchService } from '../../../features/assets/services/asset-search.service';

@Component({
  selector: 'app-command-palette',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatInputModule,
    MatListModule,
    MatIconModule,
    MatDividerModule
],
  template: `
    <div class="command-palette-container" data-testid="command-palette">
      <div class="search-header">
        <mat-icon>search</mat-icon>
        <input
          #searchInput
          [formControl]="searchControl"
          data-testid="command-palette-input"
          placeholder="Type a command or search..."
          autoFocus
          (keydown)="handleKeyDown($event)"
          />
        <span class="esc-hint">ESC to close</span>
      </div>
    
      <mat-divider></mat-divider>
    
      <mat-action-list class="command-list" #commandList>
        @for (command of filteredCommands(); track command.id; let i = $index) {
          <button
            mat-list-item
            (click)="execute(command)"
            [class.selected-item]="i === selectedIndex()"
            (mouseenter)="selectedIndex.set(i)"
            tabindex="-1"
            >
            <mat-icon matListItemIcon>{{ command.icon || 'terminal' }}</mat-icon>
            <div matListItemTitle>{{ command.label }}</div>
            <div matListItemLine class="description">{{ command.description }}</div>
    
            <div matListItemMeta class="meta-container">
              @if (command.shortcut) {
                <span class="shortcut-badge">{{ formatShortcut(command.shortcut) }}</span>
              }
              @if (command.category) {
                <div class="category-chip">
                  {{ command.category }}
                </div>
              }
            </div>
          </button>
          } @empty {
          <div class="no-results">No commands found matching your search.</div>
        }
      </mat-action-list>
    
      <div class="palette-footer">
        <div class="shortcuts">
          <span><kbd>↑↓</kbd> to navigate</span>
          <span><kbd>↵</kbd> to select</span>
        </div>
      </div>
    </div>
    `,
  styles: [`
    .command-palette-panel .mat-mdc-dialog-container .mat-mdc-dialog-surface {
      background: transparent !important;
      box-shadow: none !important;
      overflow: visible !important;
    }

    .command-palette-container {
      width: 600px;
      max-width: 90vw;
      background: var(--mat-sys-surface-container-high);
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
      border: 1px solid var(--theme-border);
    }

    .search-header {
      display: flex;
      align-items: center;
      padding: 16px;
      gap: 12px;

      mat-icon {
        color: var(--theme-text-secondary);
      }

      input {
        flex: 1;
        background: transparent;
        border: none;
        outline: none;
        color: var(--theme-text-primary);
        font-size: 1.1rem;
        font-family: inherit;

        &::placeholder {
          color: var(--theme-text-tertiary);
        }
      }

      .esc-hint {
        font-size: 0.75rem;
        color: var(--theme-text-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
    }

    .command-list {
      max-height: 400px;
      overflow-y: auto;
      padding: 8px 0;
      scroll-behavior: smooth;

      button {
        transition: background-color 0.15s ease;

        &:hover:not(.selected-item) {
          background-color: var(--mat-sys-surface-variant) !important;
        }
      }

      .selected-item {
        /* Distinct background using primary color with transparency */
        background-color: rgba(237, 122, 155, 0.15) !important;
        position: relative;

        /* Side bar indicator */
        &::before {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 4px;
          background-color: var(--primary-color);
          border-radius: 0 4px 4px 0;
        }

        /* Ensure text contrast is correct */
        .mat-mdc-list-item-title {
           color: var(--theme-text-primary) !important;
           font-weight: 600 !important;
        }

        mat-icon {
          color: var(--primary-color) !important;
        }

        /* Description with good contrast */
        .description {
          color: var(--theme-text-secondary) !important;
        }

        /* Highlight shortcut badge */
        .shortcut-badge {
          background: rgba(237, 122, 155, 0.2) !important;
          border-color: var(--primary-color) !important;
          color: var(--primary-color) !important;
        }
      }

      .description {
        font-size: 0.85rem;
        color: var(--theme-text-secondary);
      }

      .meta-container {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
        margin-left: 12px;
      }

      .shortcut-badge {
        font-size: 0.7rem;
        font-weight: 600;
        background: var(--theme-surface);
        color: var(--theme-text-secondary);
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid var(--theme-border);
        font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
        white-space: nowrap;
        letter-spacing: 0.02em;
      }

      .category-chip {
        font-size: 0.65rem;
        background: var(--mat-sys-surface-variant);
        padding: 3px 8px;
        border-radius: 12px;
        color: var(--theme-text-tertiary);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 500;
        white-space: nowrap;
      }
    }

    .no-results {
      padding: 32px;
      text-align: center;
      color: var(--theme-text-tertiary);
    }

    .palette-footer {
      padding: 12px 16px;
      background: var(--theme-surface);
      border-top: 1px solid var(--theme-border);

      .shortcuts {
        display: flex;
        gap: 16px;
        font-size: 0.75rem;
        color: var(--theme-text-tertiary);

        kbd {
          background: var(--theme-surface-elevated);
          padding: 2px 4px;
          border-radius: 3px;
          border: 1px solid var(--theme-border);
          font-family: monospace;
        }
      }
    }
  `],
})
export class CommandPaletteComponent implements OnInit, AfterViewInit {
  private dialogRef = inject(MatDialogRef<CommandPaletteComponent>);
  private registry = inject(CommandRegistryService);
  private assetSearchService = inject(AssetSearchService);
  private platformId = inject(PLATFORM_ID);

  searchControl = new FormControl('');
  searchQuery = toSignal(this.searchControl.valueChanges, { initialValue: '' });

  selectedIndex = signal(0);
  isMac = signal(false);

  @ViewChild('searchInput') searchInput!: ElementRef;
  @ViewChild('commandList', { read: ElementRef }) commandList!: ElementRef;

  filteredCommands = toSignal(
    this.searchControl.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      distinctUntilChanged(),
      switchMap(query => {
        const normalized = (query || '').toLowerCase();

        // Filter static commands
        const staticCommands = this.registry.commands().filter(c =>
          !normalized ||
          c.label.toLowerCase().includes(normalized) ||
          c.description?.toLowerCase().includes(normalized) ||
          c.category?.toLowerCase().includes(normalized) ||
          c.keywords?.some(k => k.toLowerCase().includes(normalized))
        );

        if (!normalized || normalized.length < 2) {
          return of(staticCommands);
        }

        // Search assets and merge
        return this.assetSearchService.search(normalized).pipe(
          map(assetCommands => [...staticCommands, ...assetCommands]),
          startWith(staticCommands)
        );
      })
    ),
    { initialValue: [] }
  );

  constructor() {
    // Reactive scrolling effect
    effect(() => {
      const index = this.selectedIndex();
      const listEl = this.commandList?.nativeElement;
      if (listEl) {
        const buttons = listEl.querySelectorAll('button[mat-list-item]');
        const selectedEl = buttons[index] as HTMLElement;
        if (selectedEl) {
          selectedEl.scrollIntoView({ block: 'nearest' });
        }
      }
    });
  }

  ngOnInit() {
    this.searchControl.valueChanges.subscribe(() => {
      this.selectedIndex.set(0);
    });

    if (isPlatformBrowser(this.platformId)) {
      this.isMac.set(navigator.userAgent.includes('Mac'));
    }
  }

  ngAfterViewInit() {
    setTimeout(() => {
      this.searchInput?.nativeElement?.focus();
    });
  }

  handleKeyDown(event: KeyboardEvent) {
    // Stop propagation to prevent global listeners (e.g. KeyboardService) from reacting
    event.stopPropagation();

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.moveSelection(1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.moveSelection(-1);
        break;
      case 'Enter':
        event.preventDefault();
        this.executeSelected();
        break;
      case 'Escape':
        event.preventDefault();
        this.dialogRef.close();
        break;
    }
  }

  moveSelection(delta: number) {
    const count = this.filteredCommands().length;
    if (count === 0) return;

    this.selectedIndex.update(current => {
      return (current + delta + count) % count;
    });
  }

  executeSelected() {
    const commands = this.filteredCommands();
    if (commands.length > 0) {
      this.execute(commands[this.selectedIndex()]);
    }
  }

  execute(command: Command) {
    this.dialogRef.close();
    command.action();
  }

  formatShortcut(shortcut: string): string {
    if (!shortcut) return '';
    if (this.isMac()) {
      return shortcut
        .replace('Alt', '⌥')
        .replace('Control', '⌃')
        .replace('Ctrl', '⌃')
        .replace('Shift', '⇧')
        .replace('Meta', '⌘')
        .replace('Cmd', '⌘');
    }
    return shortcut;
  }
}

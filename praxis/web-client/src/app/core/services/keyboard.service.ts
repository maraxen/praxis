import { Injectable, inject, RendererFactory2, Renderer2 } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { AppStore } from '../store/app.store';
import { CommandPaletteComponent } from '../components/command-palette/command-palette.component';
import { CommandRegistryService } from './command-registry.service';

@Injectable({
  providedIn: 'root',
})
export class KeyboardService {
  private dialog = inject(MatDialog);
  private router = inject(Router);
  private registry = inject(CommandRegistryService);
  private rendererFactory = inject(RendererFactory2);
  private renderer: Renderer2;
  private store = inject(AppStore);

  constructor() {
    this.renderer = this.rendererFactory.createRenderer(null, null);
    this.initGlobalListeners();
    this.registerDefaultCommands();
  }

  private initGlobalListeners() {
    this.renderer.listen('window', 'keydown', (event: KeyboardEvent) => {
      // Check if user is in an input field
      const activeElement = document.activeElement;
      const isInput = activeElement instanceof HTMLInputElement ||
        activeElement instanceof HTMLTextAreaElement ||
        (activeElement instanceof HTMLElement && activeElement.isContentEditable);

      const isCmdOrCtrl = event.metaKey || event.ctrlKey;
      const isAlt = event.altKey;

      // Cmd+K or Ctrl+K: Command Palette (Keep this as Cmd/Ctrl)
      if (isCmdOrCtrl && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        this.openCommandPalette();
      }

      // Safe Navigation Shortcuts (only if not in input)
      // Moved from Cmd to Alt/Option to avoid browser conflicts (Cmd+R, etc)
      // Use event.code instead of event.key because Option+Key on Mac produces special chars (e.g. Option+p = π)
      if (!isInput && isAlt) {
        switch (event.code) {
          case 'Backquote':
            event.preventDefault();
            this.router.navigate(['/app/playground']);
            break;
          case 'KeyP':
            event.preventDefault();
            this.router.navigate(['/app/protocols']);
            break;
          case 'KeyR':
            event.preventDefault();
            this.router.navigate(['/app/assets'], { queryParams: { type: 'resource' } });
            break;
          case 'KeyM':
            event.preventDefault();
            this.router.navigate(['/app/assets'], { queryParams: { type: 'machine' } });
            break;
          case 'KeyD':
            event.preventDefault();
            this.registry.executeCommand('hardware-discovery');
            break;
          case 'KeyH':
            event.preventDefault();
            this.router.navigate(['/app/home']);
            break;
        }
      }
    });
  }

  private openCommandPalette() {
    // Prevent multiple instances
    if (this.dialog.openDialogs.some(d => d.componentInstance instanceof CommandPaletteComponent)) {
      return;
    }

    this.dialog.open(CommandPaletteComponent, {
      width: '600px',
      maxWidth: '90vw',
      panelClass: ['command-palette-panel', '!bg-transparent', '!shadow-none'],
      position: { top: '10%' },
    });
  }

  private registerDefaultCommands() {
    this.registry.registerCommand({
      id: 'nav-home',
      label: 'Go to Home',
      description: 'Navigate to the dashboard',
      icon: 'home',
      category: 'Navigation',
      shortcut: 'Alt+H',
      action: () => this.router.navigate(['/app/home']),
      keywords: ['dashboard', 'main'],
    });

    this.registry.registerCommand({
      id: 'nav-protocols',
      label: 'Go to Protocols',
      description: 'View the protocol library',
      icon: 'science',
      category: 'Navigation',
      shortcut: 'Alt+P',
      action: () => this.router.navigate(['/app/protocols']),
      keywords: ['scripts', 'definitions'],
    });

    this.registry.registerCommand({
      id: 'nav-playground',
      label: 'Open Playground',
      description: 'Interactive Python console for hardware control',
      icon: 'terminal',
      category: 'Navigation',
      shortcut: 'Alt+`',
      action: () => this.router.navigate(['/app/playground']),
      keywords: ['console', 'terminal', 'python', 'interactive', 'repl'],
    });

    this.registry.registerCommand({
      id: 'nav-assets',
      label: 'Go to Assets',
      description: 'Manage machines and resources',
      icon: 'inventory_2',
      category: 'Navigation',
      shortcut: 'Alt+A',
      action: () => this.router.navigate(['/app/assets']),
      keywords: ['machines', 'labware', 'equipment'],
    });

    this.registry.registerCommand({
      id: 'hardware-discovery',
      label: 'Discover Hardware',
      description: 'Scan for connected USB and serial devices',
      icon: 'usb',
      category: 'Actions',
      shortcut: 'Alt+D',
      action: () => {
        // Navigate to assets (machines tab) and open discovery dialog
        this.router.navigate(['/app/assets'], { queryParams: { type: 'machine' } }).then(() => {
          // Small delay to ensure the component is loaded
          setTimeout(() => {
            const event = new CustomEvent('open-hardware-discovery');
            window.dispatchEvent(event);
          }, 100);
        });
      },
      keywords: ['usb', 'serial', 'scan', 'detect', 'connect'],
    });

    this.registry.registerCommand({
      id: 'nav-settings',
      label: 'Go to Settings',
      description: 'Manage application preferences and hints',
      icon: 'settings',
      category: 'Navigation',
      shortcut: 'Alt+S',
      action: () => this.router.navigate(['/app/settings']),
      keywords: ['configuration', 'preferences', 'options', 'hints'],
    });

    this.registry.registerCommand({
      id: 'theme-toggle',
      label: 'Toggle Theme',
      description: 'Switch between light and dark mode',
      icon: 'contrast',
      category: 'Settings',
      action: () => {
        const currentTheme = this.store.theme();
        const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.store.setTheme(nextTheme);
      },
    });
  }
}

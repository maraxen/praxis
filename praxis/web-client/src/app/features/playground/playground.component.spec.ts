import { Component, signal, WritableSignal, NO_ERRORS_SCHEMA } from '@angular/core';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Mock sub-components MUST be defined BEFORE PlaygroundComponent is imported
vi.mock('./components/direct-control/direct-control.component', () => ({
    DirectControlComponent: Component({ selector: 'app-direct-control', standalone: true, template: '' })(class { })
}));
vi.mock('@shared/components/hardware-discovery-button/hardware-discovery-button.component', () => ({
    HardwareDiscoveryButtonComponent: Component({ selector: 'app-hardware-discovery-button', standalone: true, template: '' })(class { })
}));
vi.mock('@shared/components/page-tooltip/page-tooltip.component', () => ({
    PageTooltipComponent: Component({ selector: 'app-page-tooltip', standalone: true, template: '' })(class { })
}));
vi.mock('@shared/components/praxis-select/praxis-select.component', () => ({
    PraxisSelectComponent: Component({ selector: 'app-praxis-select', standalone: true, template: '', inputs: ['options', 'placeholder'] })(class { }),
    SelectOption: class { }
}));

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PlaygroundComponent } from './playground.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AppStore } from '@core/store/app.store';
import { ModeService } from '@core/services/mode.service';
import { AssetService } from '@features/assets/services/asset.service';
import { SerialManagerService } from '@core/services/serial-manager.service';
import { SqliteService } from '@core/services/sqlite';
import { PlaygroundJupyterliteService } from './services/playground-jupyterlite.service';
import { CommandRegistryService } from '@core/services/command-registry.service';
import { InteractionService } from '@core/services/interaction.service';
import { JupyterChannelService } from './services/jupyter-channel.service';
import { DirectControlKernelService } from './services/direct-control-kernel.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { Overlay } from '@angular/cdk/overlay';
import { of, BehaviorSubject } from 'rxjs';

// Mock BroadcastChannel
class MockBroadcastChannel {
    name: string;
    onmessage: ((event: MessageEvent) => void) | null = null;
    closed = false;

    constructor(name: string) {
        this.name = name;
        (globalThis as any).mockChannels = (globalThis as any).mockChannels || {};
        (globalThis as any).mockChannels[name] = this;
    }

    postMessage(message: any) { }
    close() { this.closed = true; }
}

describe('PlaygroundComponent', () => {
    let component: PlaygroundComponent;
    let fixture: ComponentFixture<PlaygroundComponent>;

    let themeSignal: WritableSignal<string>;
    let modeLabelSignal: WritableSignal<string>;
    let isReady$ = new BehaviorSubject<boolean>(true);

    let jupyterliteMock = {
        isLoading: signal(true),
        jupyterliteUrl: signal<string | undefined>(undefined),
        loadingError: signal<string | null>(null),
        initialize: vi.fn(),
        destroy: vi.fn(),
        reload: vi.fn()
    };

    beforeEach(async () => {
        themeSignal = signal('light');
        modeLabelSignal = signal('Test Mode');

        (globalThis as any).BroadcastChannel = MockBroadcastChannel;
        (globalThis as any).mockChannels = {};

        await TestBed.configureTestingModule({
            imports: [PlaygroundComponent, NoopAnimationsModule],
            schemas: [NO_ERRORS_SCHEMA],
            providers: [
                {
                    provide: AppStore,
                    useValue: { theme: themeSignal }
                },
                {
                    provide: ModeService,
                    useValue: { modeLabel: modeLabelSignal }
                },
                {
                    provide: AssetService,
                    useValue: {
                        getMachines: () => of([]),
                        getResources: () => of([])
                    }
                },
                {
                    provide: SqliteService,
                    useValue: { isReady$: isReady$.asObservable() }
                },
                {
                    provide: PlaygroundJupyterliteService,
                    useValue: jupyterliteMock
                },
                {
                    provide: CommandRegistryService,
                    useValue: { registerCommand: vi.fn() }
                },
                {
                    provide: InteractionService,
                    useValue: { handleInteraction: vi.fn() }
                },
                {
                    provide: JupyterChannelService,
                    useValue: { message$: of(), postMessage: vi.fn() }
                },
                {
                    provide: DirectControlKernelService,
                    useValue: { execute: vi.fn() }
                },
                { provide: SerialManagerService, useValue: { availablePorts: signal([]) } },
                { provide: MatSnackBar, useValue: { open: vi.fn() } },
                { provide: MatDialog, useValue: { open: vi.fn() } },
                { provide: Overlay, useValue: { create: vi.fn(), position: vi.fn() } }
            ]
        })
            .compileComponents();

        fixture = TestBed.createComponent(PlaygroundComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    afterEach(() => {
        delete (globalThis as any).BroadcastChannel;
        delete (globalThis as any).mockChannels;
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize jupyterlite on init', () => {
        expect(jupyterliteMock.initialize).toHaveBeenCalled();
    });

    it('should show loading when jupyterlite is loading', () => {
        jupyterliteMock.isLoading.set(true);
        fixture.detectChanges();
        const loadingOverlay = fixture.debugElement.nativeElement.querySelector('.loading-overlay');
        expect(loadingOverlay).toBeTruthy();
    });
});



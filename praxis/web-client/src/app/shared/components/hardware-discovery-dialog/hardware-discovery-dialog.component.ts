import { Component, ChangeDetectionStrategy, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';

import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import {
    HardwareDiscoveryService,
    DiscoveredDevice,
    ConnectionType,
    DeviceStatus,
} from '@core/services/hardware-discovery.service';

@Component({
    selector: 'app-hardware-discovery-dialog',
    standalone: true,
    imports: [
        FormsModule,
        MatDialogModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatTooltipModule,
        MatChipsModule,
        MatExpansionModule,
        MatFormFieldModule,
        MatInputModule,
        MatInputModule,
        MatSnackBarModule,
        MatCheckboxModule
    ],
    template: `
        <h2 mat-dialog-title>
            <mat-icon>usb</mat-icon>
            Hardware Discovery
        </h2>

        <mat-dialog-content>
            <!-- Browser API Support Status -->
            <div class="api-status">
                <div class="status-item" [class.supported]="hardwareService.webSerialSupported()">
                    <mat-icon>{{ hardwareService.webSerialSupported() ? 'check_circle' : 'cancel' }}</mat-icon>
                    <span>WebSerial</span>
                </div>
                <div class="status-item" [class.supported]="hardwareService.webUsbSupported()">
                    <mat-icon>{{ hardwareService.webUsbSupported() ? 'check_circle' : 'cancel' }}</mat-icon>
                    <span>WebUSB</span>
                </div>
            </div>

            <!-- Scan Actions -->
            <div class="scan-actions">
                <button
                    mat-stroked-button
                    (click)="scanAll()"
                    [disabled]="hardwareService.isDiscovering()"
                >
                    @if (hardwareService.isDiscovering()) {
                        <mat-spinner diameter="20"></mat-spinner>
                    } @else {
                        <mat-icon>refresh</mat-icon>
                    }
                    Scan All
                </button>

                <button
                    mat-stroked-button
                    (click)="requestSerialDevice()"
                    [disabled]="!hardwareService.webSerialSupported()"
                    matTooltip="Request access to a serial port"
                >
                    <mat-icon>settings_ethernet</mat-icon>
                    Add Serial
                </button>

                <button
                    mat-stroked-button
                    (click)="requestUsbDevice()"
                    [disabled]="!hardwareService.webUsbSupported()"
                    matTooltip="Request access to a USB device"
                >
                    <mat-icon>usb</mat-icon>
                    Add USB
                </button>
            </div>

            <!-- Discovered Devices List -->
            <div class="devices-section">
                <h3>
                    Discovered Devices
                    <span class="count">({{ filteredDevices().length }})</span>
                </h3>

                @if (filteredDevices().length === 0) {
                    <div class="empty-state">
                        <mat-icon>devices</mat-icon>
                        <p>No devices discovered yet</p>
                        <p class="hint">Click "Scan All" or add a specific device</p>
                    </div>
                } @else {
                    <div class="device-list">
                        @for (device of filteredDevices(); track device.id) {
                            <mat-expansion-panel class="device-panel" [class.supported]="hardwareService.isPlrSupported(device)">
                                <mat-expansion-panel-header>
                                    <mat-panel-title>
                                        <mat-icon class="device-icon">{{ getDeviceIcon(device.connectionType) }}</mat-icon>
                                        <span class="device-name">{{ device.name }}</span>
                                    </mat-panel-title>
                                    <mat-panel-description>
                                        <mat-chip [class]="'status-' + device.status">
                                            {{ device.status }}
                                        </mat-chip>
                                        @if (hardwareService.isPlrSupported(device)) {
                                            <mat-chip class="plr-chip" matTooltip="PyLabRobot compatible">
                                                PLR
                                            </mat-chip>
                                        }
                                    </mat-panel-description>
                                </mat-expansion-panel-header>

                                <div class="device-details">
                                    <div class="detail-row">
                                        <span class="label">Connection:</span>
                                        <span class="value">{{ device.connectionType }}</span>
                                    </div>
                                    @if (device.manufacturer) {
                                        <div class="detail-row">
                                            <span class="label">Manufacturer:</span>
                                            <span class="value">{{ device.manufacturer }}</span>
                                        </div>
                                    }
                                    @if (device.productName) {
                                        <div class="detail-row">
                                            <span class="label">Model:</span>
                                            <span class="value">{{ device.productName }}</span>
                                        </div>
                                    }
                                    @if (device.serialNumber) {
                                        <div class="detail-row">
                                            <span class="label">Serial:</span>
                                            <span class="value mono">{{ device.serialNumber }}</span>
                                        </div>
                                    }
                                    @if (device.vendorId && device.productId) {
                                        <div class="detail-row">
                                            <span class="label">VID/PID:</span>
                                            <span class="value mono">
                                                {{ formatHex(device.vendorId) }}:{{ formatHex(device.productId) }}
                                            </span>
                                        </div>
                                    }
                                    @if (device.plrBackend) {
                                        <div class="detail-row">
                                            <span class="label">PLR Backend:</span>
                                            <span class="value mono small">{{ device.plrBackend }}</span>
                                        </div>
                                    }

                                    <!-- Configuration Section (if required) -->
                                    @if (device.requiresConfiguration && device.configurationSchema) {
                                        <div class="config-section">
                                            <h4>Configuration Required</h4>
                                            @for (field of getConfigFields(device); track field.key) {
                                                @if (field.config.type === 'string' || field.config.type === 'number') {
                                                    <mat-form-field appearance="outline" class="config-field">
                                                        <mat-label>{{ field.config.label }}</mat-label>
                                                        <input matInput
                                                            [type]="field.config.type === 'number' ? 'number' : 'text'"
                                                            [value]="getConfigValue(device, field.key)"
                                                            (input)="setConfigValue(device, field.key, $event)">
                                                        @if (field.config.description) {
                                                            <mat-hint>{{ field.config.description }}</mat-hint>
                                                        }
                                                    </mat-form-field>
                                                } @else if (field.config.type === 'boolean') {
                                                    <div class="checkbox-field">
                                                        <mat-checkbox
                                                            [checked]="getBoolConfigValue(device, field.key)"
                                                            (change)="setBoolConfigValue(device, field.key, $event.checked)">
                                                            {{ field.config.label }}
                                                        </mat-checkbox>
                                                        @if (field.config.description) {
                                                            <div class="field-hint">{{ field.config.description }}</div>
                                                        }
                                                    </div>
                                                }
                                            }
                                        </div>
                                    }

                                    <!-- Error Message Display -->
                                    @if (device.status === 'error' && device.errorMessage) {
                                        <div class="error-message">
                                            <mat-icon>error</mat-icon>
                                            <span>{{ device.errorMessage }}</span>
                                        </div>
                                    }

                                    <!-- Device Actions -->
                                    <div class="device-actions">
                                        @if (device.status === 'available' && (device.connectionType === 'serial' || device.connectionType === 'network')) {
                                            <button mat-stroked-button (click)="connectDevice(device)" [disabled]="connectingDevices().has(device.id)">
                                                @if (connectingDevices().has(device.id)) {
                                                    <mat-spinner diameter="18"></mat-spinner>
                                                } @else {
                                                    <mat-icon>link</mat-icon>
                                                }
                                                {{ connectingDevices().has(device.id) ? 'Connecting...' : 'Connect' }}
                                            </button>
                                        }
                                        @if (device.status === 'connecting') {
                                            <button mat-stroked-button disabled>
                                                <mat-spinner diameter="18"></mat-spinner>
                                                Connecting...
                                            </button>
                                        }
                                        @if (device.status === 'connected') {
                                            <button mat-stroked-button (click)="disconnectDevice(device)">
                                                <mat-icon>link_off</mat-icon>
                                                Disconnect
                                            </button>
                                        }
                                        @if (device.status === 'error') {
                                            <button mat-stroked-button color="warn" (click)="retryConnection(device)">
                                                <mat-icon>refresh</mat-icon>
                                                Retry
                                            </button>
                                        }
                                        @if (hardwareService.isPlrSupported(device) && device.status !== 'requires_config' && device.status !== 'error') {
                                            @if (registeredDevices().has(device.id)) {
                                                <button mat-flat-button color="accent" (click)="goToAsset(registeredDevices().get(device.id)!)">
                                                    <mat-icon>arrow_forward</mat-icon>
                                                    Go to Asset
                                                </button>
                                            }
                                        }
                                        <button mat-icon-button color="warn" (click)="removeDevice(device)" matTooltip="Remove from list">
                                            <mat-icon>delete</mat-icon>
                                        </button>
                                    </div>
                                </div>
                            </mat-expansion-panel>
                        }
                    </div>
                }
            </div>

            <!-- Supported Devices Summary -->
            @if (hardwareService.supportedDevices().length > 0) {
                <div class="summary-section">
                    <mat-icon>check_circle</mat-icon>
                    <span>{{ hardwareService.supportedDevices().length }} PLR-compatible device(s) found</span>
                </div>
            }
        </mat-dialog-content>

        <mat-dialog-actions align="end">
            <button mat-button mat-dialog-close>Close</button>
        </mat-dialog-actions>
    `,
    styles: [`
        :host {
            display: block;
        }

        h2[mat-dialog-title] {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        mat-dialog-content {
            min-width: 500px;
            max-height: 70vh;
        }

        .api-status {
            display: flex;
            gap: 16px;
            padding: 12px;
            background: var(--sys-surface-container);
            border-radius: 8px;
            margin-bottom: 16px;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--sys-error);
        }

        .status-item.supported {
            color: var(--sys-primary);
        }

        .status-item mat-icon {
            font-size: 18px;
            width: 18px;
            height: 18px;
        }

        .scan-actions {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }

        .scan-actions button {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .scan-actions mat-spinner {
            margin-right: 4px;
        }

        .devices-section h3 {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            font-size: 1rem;
            font-weight: 500;
        }

        .devices-section .count {
            color: var(--sys-on-surface-variant);
            font-weight: 400;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 32px;
            color: var(--sys-on-surface-variant);
            text-align: center;
        }

        .empty-state mat-icon {
            font-size: 48px;
            width: 48px;
            height: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }

        .empty-state .hint {
            font-size: 0.85rem;
            opacity: 0.7;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .device-panel {
            border-left: 3px solid transparent;
        }

        .device-panel.supported {
            border-left-color: var(--sys-primary);
        }

        .device-icon {
            margin-right: 8px;
        }

        .device-name {
            font-weight: 500;
        }

        mat-panel-description {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .status-available {
            background: var(--sys-primary-container) !important;
            color: var(--sys-on-primary-container) !important;
        }

        .status-connected {
            background: var(--sys-tertiary-container) !important;
            color: var(--sys-on-tertiary-container) !important;
        }

        .status-requires_config {
            background: var(--sys-secondary-container) !important;
            color: var(--sys-on-secondary-container) !important;
        }

        .status-error {
            background: var(--sys-error-container) !important;
            color: var(--sys-on-error-container) !important;
        }

        .status-connecting, .status-busy {
            background: var(--sys-tertiary-container) !important;
            color: var(--sys-on-tertiary-container) !important;
            animation: pulse 1.5s ease-in-out infinite;
        }

        .status-disconnected, .status-unknown {
            background: var(--sys-outline-variant) !important;
            color: var(--sys-on-surface-variant) !important;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .plr-chip {
            background: var(--sys-primary) !important;
            color: var(--sys-on-primary) !important;
            font-weight: 600;
            font-size: 0.7rem;
        }

        .device-details {
            padding-top: 8px;
        }

        .detail-row {
            display: flex;
            padding: 4px 0;
            font-size: 0.9rem;
        }

        .detail-row .label {
            width: 120px;
            color: var(--sys-on-surface-variant);
            flex-shrink: 0;
        }

        .detail-row .value {
            color: var(--sys-on-surface);
        }

        .detail-row .value.mono {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }

        .detail-row .value.small {
            font-size: 0.75rem;
            word-break: break-all;
        }

        .config-section {
            margin-top: 16px;
            padding: 12px;
            background: var(--sys-surface-container-high);
            border-radius: 8px;
        }

        .config-section h4 {
            margin: 0 0 12px 0;
            font-size: 0.9rem;
            font-weight: 500;
        }

        .config-field {
            width: 100%;
            margin-bottom: 8px;
        }

        .error-message {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 12px;
            margin-top: 12px;
            background: var(--sys-error-container);
            color: var(--sys-on-error-container);
            border-radius: 8px;
            font-size: 0.85rem;
        }

        .error-message mat-icon {
            flex-shrink: 0;
            font-size: 20px;
            width: 20px;
            height: 20px;
        }

        .device-actions {
            display: flex;
            gap: 8px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--sys-outline-variant);
            flex-wrap: wrap;
        }

        .device-actions button mat-spinner {
            margin-right: 4px;
        }

        .summary-section {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px;
            margin-top: 16px;
            background: var(--sys-primary-container);
            color: var(--sys-on-primary-container);
            border-radius: 8px;
        }

        .summary-section mat-icon {
            color: var(--sys-primary);
        }
    `],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HardwareDiscoveryDialogComponent {
    readonly hardwareService = inject(HardwareDiscoveryService);
    private readonly dialogRef = inject(MatDialogRef<HardwareDiscoveryDialogComponent>);
    private readonly snackBar = inject(MatSnackBar);
    private readonly router = inject(Router);

    /** Tracks devices currently being connected */
    readonly connectingDevices = signal<Set<string>>(new Set());

    /** Tracks newly registered devices: device.id -> asset.accession_id */
    readonly registeredDevices = signal<Map<string, string>>(new Map());

    readonly filteredDevices = computed(() => {
        return this.hardwareService.discoveredDevices().filter((d: DiscoveredDevice) =>
            d.connectionType !== 'simulator' &&
            !(d.plrBackend && d.plrBackend.toLowerCase().includes('simulator')) &&
            !d.plrMachineDefinition?.is_simulated_frontend
        );
    });

    async scanAll(): Promise<void> {
        await this.hardwareService.discoverAll();
    }

    async requestSerialDevice(): Promise<void> {
        const device = await this.hardwareService.requestSerialPort();
        if (device) {
            if (this.hardwareService.isPlrSupported(device)) {
                await this.registerAsMachine(device);
            } else {
                this.snackBar.open(`Added: ${device.name}`, 'OK', { duration: 3000 });
            }
        }
    }

    async requestUsbDevice(): Promise<void> {
        const device = await this.hardwareService.requestUsbDevice();
        if (device) {
            if (this.hardwareService.isPlrSupported(device)) {
                await this.registerAsMachine(device);
            } else {
                this.snackBar.open(`Added: ${device.name}`, 'OK', { duration: 3000 });
            }
        }
    }

    async connectDevice(device: DiscoveredDevice): Promise<void> {
        // Add to connecting set
        this.connectingDevices.update(set => {
            const newSet = new Set(set);
            newSet.add(device.id);
            return newSet;
        });

        try {
            const success = await this.hardwareService.openSerialConnection(device);
            if (success) {
                this.snackBar.open(`Connected to ${device.name}`, 'OK', { duration: 3000 });
            } else {
                this.snackBar.open(`Failed to connect to ${device.name}`, 'Dismiss', { duration: 5000 });
            }
        } finally {
            // Remove from connecting set
            this.connectingDevices.update(set => {
                const newSet = new Set(set);
                newSet.delete(device.id);
                return newSet;
            });
        }
    }

    async disconnectDevice(device: DiscoveredDevice): Promise<void> {
        const success = await this.hardwareService.closeSerialConnection(device);
        if (success) {
            this.snackBar.open(`Disconnected from ${device.name}`, 'OK', { duration: 3000 });
        }
    }

    async retryConnection(device: DiscoveredDevice): Promise<void> {
        // Clear error state and retry
        this.hardwareService.clearDeviceError(device.id);
        await this.connectDevice(device);
    }

    async registerAsMachine(device: DiscoveredDevice): Promise<void> {
        const result = await this.hardwareService.registerAsMachine(device) as any;
        if (result) {
            this.snackBar.open(`Registered: ${result.name}`, 'View Asset', {
                duration: 5000
            }).onAction().subscribe(() => {
                this.router.navigate(['/assets/machines', result.accession_id]);
                this.dialogRef.close();
            });

            // Update local state to show "Go to Asset" button
            this.registeredDevices.update(map => {
                const newMap = new Map(map);
                newMap.set(device.id, result.accession_id);
                return newMap;
            });

            // Dispatch global event so machine lists can refresh
            window.dispatchEvent(new CustomEvent('machine-registered', {
                detail: { accession_id: result.accession_id, name: result.name }
            }));
        } else {
            this.snackBar.open('Failed to register device', 'Dismiss', { duration: 5000 });
        }
    }

    goToAsset(accessionId: string): void {
        this.router.navigate(['/assets/machines', accessionId]);
        this.dialogRef.close();
    }

    removeDevice(device: DiscoveredDevice): void {
        this.hardwareService.removeDevice(device.id);
    }

    getDeviceIcon(connectionType: ConnectionType): string {
        const icons: Record<ConnectionType, string> = {
            serial: 'settings_ethernet',
            usb: 'usb',
            network: 'lan',
            simulator: 'smart_toy',
        };
        return icons[connectionType] || 'devices';
    }

    formatHex(value: number): string {
        return '0x' + value.toString(16).toUpperCase().padStart(4, '0');
    }

    getConfigFields(device: DiscoveredDevice): { key: string; config: any }[] {
        if (!device.configurationSchema) return [];
        return Object.entries(device.configurationSchema).map(([key, config]) => ({ key, config }));
    }

    getConfigValue(device: DiscoveredDevice, key: string): string {
        return (device.configuration?.[key] as string) || '';
    }

    setConfigValue(device: DiscoveredDevice, key: string, event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        const config = { ...(device.configuration || {}), [key]: value };
        this.hardwareService.updateDeviceConfiguration(device.id, config);
    }

    getBoolConfigValue(device: DiscoveredDevice, key: string): boolean {
        return !!(device.configuration?.[key]);
    }

    setBoolConfigValue(device: DiscoveredDevice, key: string, value: boolean): void {
        const config = { ...(device.configuration || {}), [key]: value };
        this.hardwareService.updateDeviceConfiguration(device.id, config);
    }
}

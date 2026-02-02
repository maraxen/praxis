/**
 * Hardware Discovery Service
 *
 * Provides browser-based hardware discovery using WebSerial and WebUSB APIs.
 * Integrates with backend API for machine registration and PLR backend inference.
 */

import { Injectable, inject, signal, computed } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { PLR_MACHINE_DEFINITIONS, PlrMachineDefinition, PLR_BACKEND_DEFINITIONS, PlrBackendDefinition } from '@assets/browser-data/plr-definitions';

export type ConnectionType = 'serial' | 'usb' | 'network' | 'simulator';
export type DeviceStatus = 'available' | 'connected' | 'connecting' | 'disconnected' | 'busy' | 'error' | 'requires_config' | 'unknown';

export interface DiscoveredDevice {
    id: string;
    name: string;
    connectionType: ConnectionType;
    status: DeviceStatus;
    port?: SerialPort;
    usbDevice?: USBDevice;
    manufacturer?: string;
    productName?: string;
    serialNumber?: string;
    vendorId?: number;
    productId?: number;
    plrBackend?: string;
    plrMachineDefinition?: PlrMachineDefinition;
    plrBackendDefinition?: PlrBackendDefinition;
    frontendDefinitionAccessionId?: string;
    backendDefinitionAccessionId?: string;
    requiresConfiguration?: boolean;
    configurationSchema?: Record<string, ConfigurationField>;
    configuration?: Record<string, unknown>;
    errorMessage?: string;
    ipAddress?: string;
}

export interface ConfigurationField {
    type: 'string' | 'number' | 'boolean' | 'select';
    label: string;
    required: boolean;
    default?: unknown;
    options?: { value: string; label: string }[];
    description?: string;
}

export interface BackendDevice {
    id: string;
    name: string;
    connection_type: string;
    status: string;
    port?: string;
    ip_address?: string;
    manufacturer?: string;
    model?: string;
    serial_number?: string;
    plr_backend?: string;
    properties?: Record<string, unknown>;
}

export interface RegisterMachineRequest {
    device_id: string;
    name: string;
    plr_backend: string;
    connection_type: string;
    port?: string;
    ip_address?: string;
    configuration?: Record<string, unknown>;
}

export interface RegisterMachineResponse {
    accession_id: string;
    name: string;
    status: string;
    message: string;
}

// Shared schema configuration (Temporary: see hardware_definitions_sync.md)
const HAMILTON_CONFIG_SCHEMA: Record<string, ConfigurationField> = {
    deck_layout: { type: 'string', label: 'Deck Layout', required: false, description: 'Custom deck layout file' },
};

// Known USB Vendor/Product IDs for lab equipment
// To add a new device, find its VID/PID (e.g., from https://usb-ids.gowdy.us/)
// and map it to the correct PyLabRobot backend FQN.
const KNOWN_DEVICES: Record<string, { manufacturer: string; model: string; plrBackend: string; configSchema?: Record<string, ConfigurationField> }> = {
    // Hamilton devices
    '0x08BB:0x0106': {
        manufacturer: 'Hamilton',
        model: 'STAR',
        plrBackend: 'pylabrobot.liquid_handling.backends.hamilton.STAR',
        configSchema: HAMILTON_CONFIG_SCHEMA,
    },
    '0x08BB:0x0107': {
        manufacturer: 'Hamilton',
        model: 'Starlet',
        plrBackend: 'pylabrobot.liquid_handling.backends.hamilton.Starlet',
        configSchema: HAMILTON_CONFIG_SCHEMA,
    },
    // Opentrons devices
    '0x04D8:0xE11A': {
        manufacturer: 'Opentrons',
        model: 'OT-2',
        plrBackend: 'pylabrobot.liquid_handling.backends.opentrons.OT2',
        configSchema: {
            simulate: { type: 'boolean', label: 'Simulation Mode', required: false, default: false },
        },
    },
    // B&B Electronics USOPTL4 (Common Hamilton Adapter)
    '0x0856:0xAC11': {
        manufacturer: 'Hamilton',
        model: 'STAR/Starlet (via B&B Adapter)',
        plrBackend: 'pylabrobot.liquid_handling.backends.hamilton.STAR',
        configSchema: HAMILTON_CONFIG_SCHEMA,
    },
    // BMG CLARIOstar Plate Reader
    '0x0403:0xBB68': {
        manufacturer: 'BMG LABTECH',
        model: 'CLARIOstar',
        plrBackend: 'pylabrobot.plate_reading.clario_star_backend.CLARIOstarBackend',
        // configSchema removed per user request (no simulation config needed for physical discovery)
    },
    // MCT Adapter (Found on RPi for Hamilton)
    '0x08AF:0x8000': {
        manufacturer: 'Hamilton',
        model: 'STAR/Starlet (via MCT Adapter)',
        plrBackend: 'pylabrobot.liquid_handling.backends.hamilton.STAR',
        configSchema: HAMILTON_CONFIG_SCHEMA
    },
    // Generic USB-Serial adapters
    '0x1A86:0x7523': { manufacturer: 'Generic', model: 'USB-Serial (CH340)', plrBackend: '' },
    '0x0403:0x6001': { manufacturer: 'FTDI', model: 'USB-Serial (FT232)', plrBackend: '' },
    '0x067B:0x2303': { manufacturer: 'Prolific', model: 'USB-Serial (PL2303)', plrBackend: '' },

    // Agilent Devices (No direct PLR backend, but can be identified)
    '0x0957:0x0818': {
        manufacturer: 'Agilent',
        model: 'Generic Plate Reader',
        plrBackend: '', // No specific PLR backend for this model
    },

    // Another common FTDI chip
    '0x0403:0x6015': {
        manufacturer: 'FTDI',
        model: 'USB-Serial (FT230X)',
        plrBackend: '',
    },

    // Common Silicon Labs CP210x USB-to-Serial adapter
    '0x10C4:0xEA70': {
        manufacturer: 'Silicon Labs',
        model: 'USB-Serial (CP210x)',
        plrBackend: '',
    },

    // Note: Specific VIDs/PIDs for many lab devices (e.g., Tecan, Inheco) are not
    // publicly available as they often use generic USB-to-Serial adapters.
    // User testing is the most reliable way to identify the correct VID/PID
    // for a specific device. The following are common OEM identifiers.
    '0x10C4:0xEA60': { manufacturer: 'Silicon Labs', model: 'CP2102 USB to UART Bridge', plrBackend: '' },
    '0x0403:0x6010': { manufacturer: 'FTDI', model: 'FT2232H HS USB-Serial', plrBackend: '' },
};

import { HardwareService } from '../api-generated/services/HardwareService';
import { ApiWrapperService } from './api-wrapper.service';
import { DiscoveredDeviceResponse } from '../api-generated/models/DiscoveredDeviceResponse';
import { ConnectionStateResponse } from '../api-generated/models/ConnectionStateResponse';

@Injectable({
    providedIn: 'root'
})
export class HardwareDiscoveryService {
    private readonly apiWrapper = inject(ApiWrapperService);

    // Reactive state
    readonly discoveredDevices = signal<DiscoveredDevice[]>([]);
    readonly isDiscovering = signal(false);
    readonly webSerialSupported = signal(false);
    readonly webUsbSupported = signal(false);

    // Computed signals
    readonly supportedDevices = computed(() =>
        this.discoveredDevices().filter(d => d.plrBackend && d.plrBackend.length > 0)
    );
    readonly unconfiguredDevices = computed(() =>
        this.discoveredDevices().filter(d => d.status === 'requires_config')
    );
    readonly connectedDevices = computed(() =>
        this.discoveredDevices().filter(d => d.status === 'connected')
    );

    constructor() {
        // Check browser API support
        this.webSerialSupported.set('serial' in navigator);
        this.webUsbSupported.set('usb' in navigator);
    }

    /**
     * Check if WebSerial API is available
     */
    hasWebSerialSupport(): boolean {
        return 'serial' in navigator;
    }

    /**
     * Check if WebUSB API is available
     */
    hasWebUsbSupport(): boolean {
        return 'usb' in navigator;
    }

    /**
     * Request access to a serial port via WebSerial API
     * This prompts the user to select a device
     */
    async requestSerialPort(): Promise<DiscoveredDevice | null> {
        if (!this.hasWebSerialSupport()) {
            console.warn('WebSerial not supported in this browser');
            return null;
        }

        try {
            const port = await navigator.serial.requestPort();
            const device = this.createDeviceFromSerialPort(port, `serial-${Date.now()}`);

            // Add to discovered devices
            this.discoveredDevices.update(devices => [...devices, device]);

            return device;
        } catch (error) {
            if ((error as Error).name !== 'NotAllowedError') {
                console.error('Error requesting serial port:', error);
            }
            return null;
        }
    }

    /**
     * DEBUG ONLY: Requests access to a serial port without any filters.
     * Useful for identifying devices that don't match known VID/PID.
     */
    async discoverAllDebug(): Promise<void> {
        if (!this.hasWebSerialSupport()) {
            console.warn('[HardwareDiscovery] WebSerial not supported');
            return;
        }

        try {
            console.log('[HardwareDiscovery] Requesting ALL ports (no filters)...');
            // Explicitly pass empty filters array to be sure
            const port = await navigator.serial.requestPort({ filters: [] });
            const portInfo = port.getInfo();
            console.log('[HardwareDiscovery] Selected Debug Port:', portInfo);

            const device = this.createDeviceFromSerialPort(port, `debug-${Date.now()}`);

            this.discoveredDevices.update(devices => {
                // Remove existing if present
                const filtered = devices.filter(d => d.id !== device.id);
                return [...filtered, device];
            });

        } catch (err) {
            console.error('[HardwareDiscovery] Debug Discovery failed:', err);
        }
    }

    /**
     * Request access to a USB device via WebUSB API
     */
    async requestUsbDevice(): Promise<DiscoveredDevice | null> {
        if (!this.hasWebUsbSupport()) {
            console.warn('WebUSB not supported in this browser');
            return null;
        }

        try {
            const usbDevice = await navigator.usb.requestDevice({
                filters: [] // Allow all devices
            });

            const device = this.createDeviceFromUSB(usbDevice, `usb-${Date.now()}`);
            this.discoveredDevices.update(devices => [...devices, device]);

            return device;
        } catch (error) {
            if ((error as Error).name !== 'NotAllowedError') {
                console.error('Error requesting USB device:', error);
            }
            return null;
        }
    }

    /**
     * Create a DiscoveredDevice from a SerialPort
     */
    private createDeviceFromSerialPort(port: SerialPort, id: string): DiscoveredDevice {
        const info = port.getInfo();
        const deviceKey = this.formatDeviceKey(info.usbVendorId, info.usbProductId);
        const knownDevice = this.logAndGetKnownDevice(deviceKey);
        const backendDef = this.inferBackendDefinition(knownDevice?.plrBackend);
        const plrDef = backendDef ? PLR_MACHINE_DEFINITIONS.find(m => m.fqn === backendDef.fqn) : undefined;

        const hasConfig = !!(knownDevice?.configSchema && Object.keys(knownDevice.configSchema).length > 0);

        return {
            id,
            name: knownDevice?.model || backendDef?.name || plrDef?.name || 'Serial Device',
            connectionType: 'serial',
            status: hasConfig ? 'requires_config' : 'available',
            port,
            vendorId: info.usbVendorId,
            productId: info.usbProductId,
            manufacturer: knownDevice?.manufacturer || backendDef?.manufacturer || plrDef?.vendor,
            productName: knownDevice?.model || backendDef?.name || plrDef?.name,
            plrBackend: knownDevice?.plrBackend || backendDef?.fqn || plrDef?.fqn,
            plrBackendDefinition: backendDef,
            plrMachineDefinition: plrDef,
            frontendDefinitionAccessionId: backendDef?.frontend_definition_accession_id,
            backendDefinitionAccessionId: backendDef?.accession_id,
            requiresConfiguration: hasConfig,
            configurationSchema: knownDevice?.configSchema,
        };
    }

    /**
     * Create a DiscoveredDevice from a USBDevice
     */
    private createDeviceFromUSB(usbDevice: USBDevice, id: string): DiscoveredDevice {
        const deviceKey = this.formatDeviceKey(usbDevice.vendorId, usbDevice.productId);
        const knownDevice = this.logAndGetKnownDevice(deviceKey);
        const backendDef = this.inferBackendDefinition(knownDevice?.plrBackend);
        const plrDef = backendDef ? PLR_MACHINE_DEFINITIONS.find(m => m.fqn === backendDef.fqn) : undefined;

        const hasConfig = !!(knownDevice?.configSchema && Object.keys(knownDevice.configSchema).length > 0);

        return {
            id,
            name: usbDevice.productName || knownDevice?.model || backendDef?.name || plrDef?.name || 'USB Device',
            connectionType: 'usb',
            status: hasConfig ? 'requires_config' : 'available',
            usbDevice,
            vendorId: usbDevice.vendorId,
            productId: usbDevice.productId,
            manufacturer: usbDevice.manufacturerName || knownDevice?.manufacturer || backendDef?.manufacturer || plrDef?.vendor,
            productName: usbDevice.productName || knownDevice?.model || backendDef?.name || plrDef?.name,
            serialNumber: usbDevice.serialNumber,
            plrBackend: knownDevice?.plrBackend || backendDef?.fqn || plrDef?.fqn,
            plrBackendDefinition: backendDef,
            plrMachineDefinition: plrDef,
            frontendDefinitionAccessionId: backendDef?.frontend_definition_accession_id,
            backendDefinitionAccessionId: backendDef?.accession_id,
            requiresConfiguration: hasConfig,
            configurationSchema: knownDevice?.configSchema,
        };
    }

    /**
     * Format device key from vendor/product IDs
     */
    private formatDeviceKey(vendorId?: number, productId?: number): string {
        if (vendorId === undefined || productId === undefined) return '';
        return `0x${vendorId.toString(16).toUpperCase().padStart(4, '0')}:0x${productId.toString(16).toUpperCase().padStart(4, '0')}`;
    }

    /**
     * Log unknown devices and return the known device if it exists
     */
    private logAndGetKnownDevice(deviceKey: string) {
        const knownDevice = KNOWN_DEVICES[deviceKey];
        if (!knownDevice) {
            console.info(`Unknown device ${deviceKey}. Consider adding to KNOWN_DEVICES table.`);
        }
        return knownDevice;
    }

    /**
     * Infer PLR backend definition from FQN
     */
    private inferBackendDefinition(plrBackend?: string): PlrBackendDefinition | undefined {
        if (plrBackend) {
            return PLR_BACKEND_DEFINITIONS.find(b => b.fqn === plrBackend);
        }
        return undefined;
    }

    /**
     * Get previously authorized serial ports
     */
    async getAuthorizedSerialPorts(): Promise<DiscoveredDevice[]> {
        if (!this.hasWebSerialSupport()) {
            return [];
        }

        try {
            const ports = await navigator.serial.getPorts();
            return ports.map((port: SerialPort, index: number) =>
                this.createDeviceFromSerialPort(port, `serial-authorized-${index}`)
            );
        } catch (error) {
            console.error('Error getting authorized serial ports:', error);
            return [];
        }
    }

    /**
     * Get previously authorized USB devices
     */
    async getAuthorizedUsbDevices(): Promise<DiscoveredDevice[]> {
        if (!this.hasWebUsbSupport()) {
            return [];
        }

        try {
            const devices = await navigator.usb.getDevices();
            return devices.map((device: USBDevice, index: number) =>
                this.createDeviceFromUSB(device, `usb-authorized-${index}`)
            );
        } catch (error) {
            console.error('Error getting authorized USB devices:', error);
            return [];
        }
    }

    /**
     * Discover all available hardware
     * Combines browser APIs and backend discovery
     */
    async discoverAll(): Promise<DiscoveredDevice[]> {
        this.isDiscovering.set(true);
        const allDevices: DiscoveredDevice[] = [];

        try {
            // Get authorized devices from browser APIs (parallel)
            const [serialDevices, usbDevices, backendDevices] = await Promise.all([
                this.getAuthorizedSerialPorts(),
                this.getAuthorizedUsbDevices(),
                this.fetchBackendDevices(),
            ]);

            // Merge and deduplicate
            allDevices.push(...serialDevices, ...usbDevices);

            // Add backend devices that aren't already discovered via browser
            for (const bd of backendDevices) {
                const exists = allDevices.some(d =>
                    d.serialNumber === bd.serialNumber ||
                    (d.vendorId === bd.vendorId && d.productId === bd.productId)
                );
                if (!exists) {
                    allDevices.push(bd);
                }
            }

            this.discoveredDevices.set(allDevices);
        } catch (error) {
            console.error('Error during device discovery:', error);
        } finally {
            this.isDiscovering.set(false);
        }

        return allDevices;
    }

    /**
     * Fetch discovered devices from backend
     */
    private async fetchBackendDevices(): Promise<DiscoveredDevice[]> {
        try {
            const response = await firstValueFrom(
                this.apiWrapper.wrap(HardwareService.discoverHardwareApiV1HardwareDiscoverGet())
            );

            if (!response?.devices) return [];

            return (response.devices as Array<DiscoveredDeviceResponse>).map(d => {
                const backendDef = d.plr_backend
                    ? PLR_BACKEND_DEFINITIONS.find(b => b.fqn === d.plr_backend)
                    : undefined;
                const plrDef = d.plr_backend
                    ? PLR_MACHINE_DEFINITIONS.find(m => m.fqn === d.plr_backend)
                    : undefined;

                return {
                    id: d.id,
                    name: d.name,
                    connectionType: d.connection_type as ConnectionType,
                    status: d.status as DeviceStatus,
                    manufacturer: d.manufacturer ?? undefined,
                    productName: d.model ?? undefined,
                    serialNumber: d.serial_number ?? undefined,
                    plrBackend: d.plr_backend ?? undefined,
                    plrBackendDefinition: backendDef,
                    plrMachineDefinition: plrDef,
                    frontendDefinitionAccessionId: backendDef?.frontend_definition_accession_id,
                    backendDefinitionAccessionId: backendDef?.accession_id,
                };
            });
        } catch (error) {
            console.warn('Could not fetch devices from backend:', error);
            return [];
        }
    }

    /**
     * Update device configuration
     */
    updateDeviceConfiguration(deviceId: string, config: Record<string, unknown>): void {
        this.discoveredDevices.update(devices =>
            devices.map(d => {
                if (d.id !== deviceId) return d;
                return {
                    ...d,
                    configuration: config,
                    status: 'available' as DeviceStatus,
                };
            })
        );
    }

    /**
     * Register a discovered device as a machine in the backend
     */
    async registerAsMachine(device: DiscoveredDevice, name?: string): Promise<unknown | null> {
        if (!device.plrBackend) {
            console.error('Cannot register device without PLR backend');
            return null;
        }

        if (device.requiresConfiguration && !device.configuration) {
            console.error('Device requires configuration before registration');
            return null;
        }

        try {
            const response = await firstValueFrom(
                this.apiWrapper.wrap(HardwareService.registerMachineApiV1HardwareRegisterPost({
                    device_id: device.id,
                    name: name || device.name,
                    plr_backend: device.plrBackend,
                    connection_type: device.connectionType,
                    configuration: device.configuration as Record<string, unknown>,
                    // NOTE: frontend/backend definition IDs are tracked on the device object
                    // but not sent in the API request (API uses plr_backend to infer these)
                }))
            );
            return response;
        } catch (error) {
            console.error('Error registering device as machine:', error);
            return null;
        }
    }

    /**
     * Open a serial connection
     */
    async openSerialConnection(device: DiscoveredDevice, options: SerialOptions = { baudRate: 9600 }): Promise<boolean> {
        if (!device.port) {
            console.error('No serial port available for device');
            return false;
        }

        try {
            await device.port.open(options);
            this.discoveredDevices.update(devices =>
                devices.map(d => d.id === device.id ? { ...d, status: 'connected' as DeviceStatus } : d)
            );
            return true;
        } catch (error) {
            console.error('Error opening serial connection:', error);
            this.discoveredDevices.update(devices =>
                devices.map(d => d.id === device.id ? { ...d, status: 'error' as DeviceStatus } : d)
            );
            return false;
        }
    }

    /**
     * Close a serial connection
     */
    async closeSerialConnection(device: DiscoveredDevice): Promise<boolean> {
        if (!device.port) return false;

        try {
            await device.port.close();
            this.discoveredDevices.update(devices =>
                devices.map(d => d.id === device.id ? { ...d, status: 'available' as DeviceStatus } : d)
            );
            return true;
        } catch (error) {
            console.error('Error closing serial connection:', error);
            return false;
        }
    }

    /**
     * Remove a device from the discovered list
     */
    removeDevice(deviceId: string): void {
        this.discoveredDevices.update(devices =>
            devices.filter(d => d.id !== deviceId)
        );
    }

    /**
     * Clear error state for a device
     */
    clearDeviceError(deviceId: string): void {
        this.discoveredDevices.update(devices =>
            devices.map(d => d.id === deviceId
                ? { ...d, status: 'available' as DeviceStatus, errorMessage: undefined }
                : d
            )
        );
    }

    /**
     * Set device error state
     */
    setDeviceError(deviceId: string, errorMessage: string): void {
        this.discoveredDevices.update(devices =>
            devices.map(d => d.id === deviceId
                ? { ...d, status: 'error' as DeviceStatus, errorMessage }
                : d
            )
        );
    }

    /**
     * Check if a device is a recognized PLR-supported device
     */
    isPlrSupported(device: DiscoveredDevice): boolean {
        return !!(device.plrBackend && device.plrBackend.length > 0);
    }

    // =========================================================================
    // Backend Connection Management
    // =========================================================================

    /**
     * Connect to a device via backend API (persists connection state)
     */
    async connectViaBackend(device: DiscoveredDevice): Promise<boolean> {
        try {
            const response = await firstValueFrom(
                this.apiWrapper.wrap(HardwareService.connectDeviceApiV1HardwareConnectPost({
                    device_id: device.id,
                    backend_class: device.plrBackend || '',
                    config: {
                        port: device.port ? 'webserial' : undefined,
                        ip_address: device.ipAddress,
                        ...device.configuration,
                    },
                }))
            );

            if (response.status === 'connected') {
                this.discoveredDevices.update(devices =>
                    devices.map(d => d.id === device.id
                        ? { ...d, status: 'connected' as DeviceStatus, errorMessage: undefined }
                        : d
                    )
                );
                return true;
            }
            return false;
        } catch (error) {
            console.error('Backend connection failed:', error);
            this.setDeviceError(device.id, (error as Error).message || 'Connection failed');
            return false;
        }
    }

    /**
     * Disconnect from a device via backend API
     */
    async disconnectViaBackend(device: DiscoveredDevice): Promise<boolean> {
        try {
            await firstValueFrom(
                this.apiWrapper.wrap(HardwareService.disconnectDeviceApiV1HardwareDisconnectPost({
                    device_id: device.id,
                }))
            );

            this.discoveredDevices.update(devices =>
                devices.map(d => d.id === device.id
                    ? { ...d, status: 'available' as DeviceStatus }
                    : d
                )
            );
            return true;
        } catch (error) {
            console.error('Backend disconnection failed:', error);
            return false;
        }
    }

    /**
     * Fetch active connections from backend
     */
    async fetchBackendConnections(): Promise<void> {
        try {
            const connections = await firstValueFrom(
                this.apiWrapper.wrap(HardwareService.listConnectionsApiV1HardwareConnectionsGet())
            );

            // Update device statuses based on backend state
            this.discoveredDevices.update(devices =>
                devices.map(d => {
                    const conn = (connections as Array<ConnectionStateResponse>).find(c => c.device_id === d.id);
                    if (conn) {
                        return {
                            ...d,
                            status: conn.status as DeviceStatus,
                            errorMessage: conn.error_message || undefined,
                        };
                    }
                    return d;
                })
            );
        } catch (error) {
            // Silently fail - backend might not be available
            console.debug('Could not fetch backend connections:', error);
        }
    }

    /**
     * Send heartbeat for a connected device
     */
    async sendHeartbeat(deviceId: string): Promise<boolean> {
        try {
            const response = await firstValueFrom(
                this.apiWrapper.wrap(HardwareService.sendHeartbeatApiV1HardwareHeartbeatPost({
                    device_id: deviceId,
                }))
            );
            return !!response.success;
        } catch (error) {
            console.debug('Heartbeat failed:', error);
            return false;
        }
    }

    // =========================================================================
    // Low-level Port I/O Methods (for WebBridgeIO integration)
    // =========================================================================

    /**
     * Track open ports with their stream readers/writers
     */
    private openPorts = new Map<string, {
        port: SerialPort;
        reader: ReadableStreamDefaultReader<Uint8Array>;
        writer: WritableStreamDefaultWriter<Uint8Array>;
    }>();

    /**
     * Open a serial port by device ID
     */
    async openPort(portId: string, options: { baudRate?: number } = {}): Promise<void> {
        const device = this.discoveredDevices().find(d => d.id === portId);
        if (!device?.port) {
            throw new Error(`Port ${portId} not found in discovered devices`);
        }

        // Check if already open
        if (this.openPorts.has(portId)) {
            console.warn(`Port ${portId} is already open`);
            return;
        }

        const baudRate = options.baudRate || 9600;
        await device.port.open({ baudRate });

        const reader = device.port.readable?.getReader();
        const writer = device.port.writable?.getWriter();

        if (!reader || !writer) {
            throw new Error(`Failed to get reader/writer for port ${portId}`);
        }

        this.openPorts.set(portId, {
            port: device.port,
            reader,
            writer
        });

        // Update device status
        this.discoveredDevices.update(devices =>
            devices.map(d => d.id === portId ? { ...d, status: 'connected' as DeviceStatus } : d)
        );

        console.log(`[HardwareDiscovery] Opened port ${portId} at ${baudRate} baud`);
    }

    /**
     * Close a serial port by device ID
     */
    async closePort(portId: string): Promise<void> {
        const conn = this.openPorts.get(portId);
        if (!conn) {
            console.warn(`Port ${portId} is not open`);
            return;
        }

        try {
            conn.reader.releaseLock();
            conn.writer.releaseLock();
            await conn.port.close();
        } finally {
            this.openPorts.delete(portId);

            // Update device status
            this.discoveredDevices.update(devices =>
                devices.map(d => d.id === portId ? { ...d, status: 'available' as DeviceStatus } : d)
            );
        }

        console.log(`[HardwareDiscovery] Closed port ${portId}`);
    }

    /**
     * Write data to a serial port
     */
    async writeToPort(portId: string, data: Uint8Array): Promise<void> {
        const conn = this.openPorts.get(portId);
        if (!conn) {
            throw new Error(`Port ${portId} is not open`);
        }

        await conn.writer.write(data);
    }

    /**
     * Read a specific number of bytes from a serial port
     */
    async readFromPort(portId: string, size: number): Promise<Uint8Array> {
        const conn = this.openPorts.get(portId);
        if (!conn) {
            throw new Error(`Port ${portId} is not open`);
        }

        const chunks: Uint8Array[] = [];
        let bytesRead = 0;

        while (bytesRead < size) {
            const { value, done } = await conn.reader.read();
            if (done || !value) break;
            chunks.push(value);
            bytesRead += value.length;
        }

        // Concatenate chunks
        const result = new Uint8Array(bytesRead);
        let offset = 0;
        for (const chunk of chunks) {
            result.set(chunk, offset);
            offset += chunk.length;
        }

        return result.slice(0, size);
    }

    /**
     * Read a line (until newline) from a serial port
     */
    async readLineFromPort(portId: string): Promise<Uint8Array> {
        const conn = this.openPorts.get(portId);
        if (!conn) {
            throw new Error(`Port ${portId} is not open`);
        }

        const chunks: number[] = [];
        const NEWLINE = 0x0A; // \n

        while (true) {
            const { value, done } = await conn.reader.read();
            if (done || !value) break;

            for (let i = 0; i < value.length; i++) {
                chunks.push(value[i]);
                if (value[i] === NEWLINE) {
                    return new Uint8Array(chunks);
                }
            }
        }

        return new Uint8Array(chunks);
    }

    /**
     * Check if a port is currently open
     */
    isPortOpen(portId: string): boolean {
        return this.openPorts.has(portId);
    }
}


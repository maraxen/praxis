/**
 * Serial Manager Service
 *
 * Central service managing all serial connections from the main thread.
 * Provides an abstraction layer between Pyodide worker and physical hardware.
 *
 * This service:
 * - Maintains a registry of active ISerial connections
 * - Handles connection lifecycle (open/close)
 * - Proxies read/write operations for the Pyodide worker
 * - Emits status events via rxjs subjects
 * - Integrates with DriverRegistry for automatic driver selection
 */

import { Injectable, inject, OnDestroy, signal } from '@angular/core';
import { Subject, Observable } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { ISerial, SerialOpenOptions } from '../../features/playground/drivers/serial-interface';
import { findDriverForDevice } from '../../features/playground/drivers/driver-registry';
import { PlaygroundComponent } from '../../features/playground/playground.component';
import { FtdiSerial } from '../../features/playground/drivers/ftdi-web-serial';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface SerialConnectionState {
    deviceId: string;
    status: ConnectionStatus;
    vendorId?: number;
    productId?: number;
    errorMessage?: string;
}

export interface SerialStatusEvent {
    deviceId: string;
    status: ConnectionStatus;
    errorMessage?: string;
}

/**
 * Request message from Python worker for serial operations.
 */
export interface SerialRequest {
    type: 'serial:open' | 'serial:close' | 'serial:read' | 'serial:write';
    requestId: string;
    deviceId?: string;
    vendorId?: number;
    productId?: number;
    data?: number[];
    length?: number;
    options?: {
        baudRate?: number;
        dataBits?: 7 | 8;
        stopBits?: 1 | 2;
        parity?: 'none' | 'even' | 'odd';
    };
}

/**
 * Response message back to Python worker.
 */
export interface SerialResponse {
    type: 'serial:response';
    requestId: string;
    success: boolean;
    data?: number[];
    deviceId?: string;
    error?: string;
}

@Injectable({
    providedIn: 'root'
})
export class SerialManagerService implements OnDestroy {
    // Registry of active connections: deviceId -> ISerial
    private connectionMap = new Map<string, ISerial>();

    // Track connection metadata
    private connectionStates = new Map<string, SerialConnectionState>();

    // Status updates observable
    private statusSubject = new Subject<SerialStatusEvent>();
    readonly status$: Observable<SerialStatusEvent> = this.statusSubject.asObservable();

    // Active connections list (reactive signal)
    readonly connections = signal<SerialConnectionState[]>([]);

    /** Observable for RxJS interop */
    readonly connections$: Observable<SerialConnectionState[]> = toObservable(this.connections);

    // BroadcastChannel for communication with Pyodide worker
    private channel: BroadcastChannel | null = null;

    constructor() {
        this.initializeChannel();
    }

    ngOnDestroy(): void {
        this.channel?.close();
        // Close all connections
        for (const deviceId of this.connectionMap.keys()) {
            this.disconnect(deviceId).catch(console.error);
        }
    }

    /**
     * Initialize the BroadcastChannel for worker communication.
     */
    private initializeChannel(): void {
        if (typeof BroadcastChannel === 'undefined') {
            console.warn('[SerialManager] BroadcastChannel not available');
            return;
        }

        this.channel = new BroadcastChannel('praxis_serial');
        this.channel.onmessage = (event: MessageEvent) => {
            this.handleWorkerMessage(event.data);
        };

        console.log('[SerialManager] Initialized with BroadcastChannel');
    }

    /**
     * Handle incoming message from Pyodide worker.
     */
    private async handleWorkerMessage(request: SerialRequest): Promise<void> {
        if (!request?.type?.startsWith('serial:')) {
            return;
        }

        console.log('[SerialManager] Received request:', request.type, request.requestId);

        try {
            let response: SerialResponse;

            switch (request.type) {
                case 'serial:open':
                    await this.handleOpenRequest(request);
                    response = {
                        type: 'serial:response',
                        requestId: request.requestId,
                        success: true,
                        deviceId: request.deviceId,
                    };
                    break;

                case 'serial:close':
                    await this.disconnect(request.deviceId!);
                    response = {
                        type: 'serial:response',
                        requestId: request.requestId,
                        success: true,
                    };
                    break;

                case 'serial:read':
                    const data = await this.read(request.deviceId!, request.length || 64);
                    response = {
                        type: 'serial:response',
                        requestId: request.requestId,
                        success: true,
                        data: Array.from(data),
                    };
                    break;

                case 'serial:write':
                    await this.write(request.deviceId!, new Uint8Array(request.data || []));
                    response = {
                        type: 'serial:response',
                        requestId: request.requestId,
                        success: true,
                    };
                    break;

                default:
                    response = {
                        type: 'serial:response',
                        requestId: request.requestId,
                        success: false,
                        error: `Unknown request type: ${request.type}`,
                    };
            }

            this.sendResponse(response);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            console.error('[SerialManager] Request failed:', errorMessage);

            this.sendResponse({
                type: 'serial:response',
                requestId: request.requestId,
                success: false,
                error: errorMessage,
            });
        }
    }

    /**
     * Handle open request - find device and connect.
     */
    private async handleOpenRequest(request: SerialRequest): Promise<void> {
        const { vendorId, productId, options } = request;

        if (!vendorId || !productId) {
            throw new Error('vendorId and productId are required for open');
        }

        // Generate device ID from VID/PID if not provided
        const deviceId = request.deviceId || `usb-${vendorId.toString(16)}-${productId.toString(16)}`;

        // Check if already connected
        if (this.connectionMap.has(deviceId)) {
            console.log(`[SerialManager] Device ${deviceId} already connected`);
            return;
        }

        // Find matching driver
        const driver = findDriverForDevice(vendorId, productId);
        if (!driver) {
            throw new Error(`No driver found for device VID=${vendorId.toString(16)} PID=${productId.toString(16)}`);
        }

        // Find the USB device
        const devices = await navigator.usb.getDevices();
        const usbDevice = devices.find(
            (d) => d.vendorId === vendorId && d.productId === productId
        );

        if (!usbDevice) {
            throw new Error(`USB device not found. Make sure it's authorized via the UI.`);
        }

        // Connect using driver
        this.updateConnectionState(deviceId, 'connecting', vendorId, productId);

        const serial = await driver.connect(usbDevice);
        await serial.open({
            baudRate: options?.baudRate ?? 9600,
            dataBits: options?.dataBits ?? 8,
            stopBits: options?.stopBits ?? 1,
            parity: options?.parity ?? 'none',
        });

        this.connectionMap.set(deviceId, serial);
        this.updateConnectionState(deviceId, 'connected', vendorId, productId);

        console.log(`[SerialManager] Connected to ${deviceId} via ${driver.driverName}`);
    }

    /**
     * Send response back to worker via BroadcastChannel.
     */
    private sendResponse(response: SerialResponse): void {
        if (!this.channel) {
            console.error('[SerialManager] Cannot send response: no channel');
            return;
        }
        this.channel.postMessage(response);
    }

    /**
     * Update connection state and emit events.
     */
    private updateConnectionState(
        deviceId: string,
        status: ConnectionStatus,
        vendorId?: number,
        productId?: number,
        errorMessage?: string
    ): void {
        const state: SerialConnectionState = {
            deviceId,
            status,
            vendorId,
            productId,
            errorMessage,
        };

        if (status === 'disconnected') {
            this.connectionStates.delete(deviceId);
        } else {
            this.connectionStates.set(deviceId, state);
        }

        // Emit status event
        this.statusSubject.next({ deviceId, status, errorMessage });

        // Update connections list
        this.connections.set(Array.from(this.connectionStates.values()));
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * Connect to a USB device by VID/PID.
     */
    async connect(
        vendorId: number,
        productId: number,
        options?: SerialOpenOptions
    ): Promise<string> {
        const deviceId = `usb-${vendorId.toString(16)}-${productId.toString(16)}`;

        await this.handleOpenRequest({
            type: 'serial:open',
            requestId: 'direct-connect',
            deviceId,
            vendorId,
            productId,
            options: options as SerialRequest['options'],
        });

        return deviceId;
    }

    /**
     * Disconnect from a device.
     */
    async disconnect(deviceId: string): Promise<void> {
        const serial = this.connectionMap.get(deviceId);
        if (!serial) {
            console.warn(`[SerialManager] Device ${deviceId} not connected`);
            return;
        }

        try {
            await serial.close();
        } catch (error) {
            console.error(`[SerialManager] Error closing ${deviceId}:`, error);
        } finally {
            this.connectionMap.delete(deviceId);
            this.updateConnectionState(deviceId, 'disconnected');
        }
    }

    /**
     * Check if a device is connected.
     */
    isConnected(deviceId: string): boolean {
        const serial = this.connectionMap.get(deviceId);
        return serial?.isOpen ?? false;
    }

    /**
     * Write data to a connected device.
     */
    async write(deviceId: string, data: Uint8Array): Promise<void> {
        const serial = this.connectionMap.get(deviceId);
        if (!serial) {
            throw new Error(`Device ${deviceId} not connected`);
        }
        if (!serial.isOpen) {
            throw new Error(`Device ${deviceId} is not open`);
        }

        await serial.write(data);
    }

    /**
     * Read data from a connected device.
     */
    async read(deviceId: string, length: number): Promise<Uint8Array> {
        const serial = this.connectionMap.get(deviceId);
        if (!serial) {
            throw new Error(`Device ${deviceId} not connected`);
        }
        if (!serial.isOpen) {
            throw new Error(`Device ${deviceId} is not open`);
        }

        return serial.read(length);
    }

    /**
     * Get all active connections.
     */
    getActiveConnections(): SerialConnectionState[] {
        return Array.from(this.connectionStates.values());
    }

    /**
     * Get connection state for a specific device.
     */
    getConnectionState(deviceId: string): SerialConnectionState | undefined {
        return this.connectionStates.get(deviceId);
    }
}

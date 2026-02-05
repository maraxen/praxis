import { TestBed } from '@angular/core/testing';
import { HardwareDiscoveryService } from './hardware-discovery.service';
import { ApiWrapperService } from './api-wrapper.service';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('HardwareDiscoveryService', () => {
    let service: HardwareDiscoveryService;

    const mockReader = {
        read: vi.fn(),
        releaseLock: vi.fn(),
    };

    const mockWriter = {
        write: vi.fn(),
        releaseLock: vi.fn(),
    };

    const mockPort = {
        open: vi.fn().mockResolvedValue(undefined),
        close: vi.fn().mockResolvedValue(undefined),
        readable: {
            getReader: () => mockReader,
        },
        writable: {
            getWriter: () => mockWriter,
        },
    };

    const mockApiWrapper = {
        wrap: vi.fn(),
    };

    beforeEach(() => {
        vi.stubGlobal('navigator', {
            serial: {
                getPorts: vi.fn().mockResolvedValue([mockPort]),
                requestPort: vi.fn().mockResolvedValue(mockPort),
            }
        });

        TestBed.configureTestingModule({
            providers: [
                HardwareDiscoveryService,
                { provide: ApiWrapperService, useValue: mockApiWrapper }
            ]
        });
        service = TestBed.inject(HardwareDiscoveryService);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.clearAllMocks();
    });

    describe('Read Operations with Buffering', () => {
        const portId = 'test-port';

        beforeEach(async () => {
            // Manually add the device to discovered list
            service.discoveredDevices.set([{
                id: portId,
                name: 'Test Port',
                connectionType: 'serial',
                status: 'available',
                port: mockPort as any
            }]);

            await service.openPort(portId);
        });

        it('readFromPort should buffer excess data', async () => {
            // First read returns 5 bytes when only 2 were requested
            mockReader.read.mockResolvedValueOnce({
                value: new Uint8Array([1, 2, 3, 4, 5]),
                done: false
            });

            const result1 = await service.readFromPort(portId, 2);
            expect(result1).toEqual(new Uint8Array([1, 2]));
            expect(mockReader.read).toHaveBeenCalledTimes(1);

            // Second read should come from buffer
            const result2 = await service.readFromPort(portId, 2);
            expect(result2).toEqual(new Uint8Array([3, 4]));
            expect(mockReader.read).toHaveBeenCalledTimes(1);

            // Third read should call reader.read again as buffer only has [5]
            mockReader.read.mockResolvedValueOnce({
                value: new Uint8Array([6, 7]),
                done: false
            });
            const result3 = await service.readFromPort(portId, 2);
            expect(result3).toEqual(new Uint8Array([5, 6]));
            expect(mockReader.read).toHaveBeenCalledTimes(2);
        });

        it('readLineFromPort should buffer data after newline', async () => {
            // Chunk contains a full line and start of next line
            mockReader.read.mockResolvedValueOnce({
                value: new Uint8Array([0x41, 0x42, 0x0A, 0x43, 0x44]), // "AB\nCD"
                done: false
            });

            const line1 = await service.readLineFromPort(portId);
            expect(line1).toEqual(new Uint8Array([0x41, 0x42, 0x0A]));
            expect(mockReader.read).toHaveBeenCalledTimes(1);

            // Second call should return "CD" from buffer when stream ends
            mockReader.read.mockResolvedValueOnce({
                value: undefined,
                done: true
            });
            const line2 = await service.readLineFromPort(portId);
            expect(line2).toEqual(new Uint8Array([0x43, 0x44]));
        });

        it('readLineFromPort should handle partial lines across multiple reads', async () => {
            mockReader.read.mockResolvedValueOnce({
                value: new Uint8Array([0x41]), // "A"
                done: false
            });
            mockReader.read.mockResolvedValueOnce({
                value: new Uint8Array([0x42, 0x0A]), // "B\n"
                done: false
            });

            const line = await service.readLineFromPort(portId);
            expect(line).toEqual(new Uint8Array([0x41, 0x42, 0x0A]));
            expect(mockReader.read).toHaveBeenCalledTimes(2);
        });

        it('readLineFromPort should return multiple lines from one chunk sequentially', async () => {
            // Chunk contains two full lines
            mockReader.read.mockResolvedValueOnce({
                value: new Uint8Array([0x41, 0x0A, 0x42, 0x0A]), // "A\nB\n"
                done: false
            });

            const line1 = await service.readLineFromPort(portId);
            expect(line1).toEqual(new Uint8Array([0x41, 0x0A]));
            
            const line2 = await service.readLineFromPort(portId);
            expect(line2).toEqual(new Uint8Array([0x42, 0x0A]));
            
            expect(mockReader.read).toHaveBeenCalledTimes(1);
        });
    });
});

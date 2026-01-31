# WebSerial Port Persistence Audit

## Status: ✅ Good - Authorized Ports Persist

---

## Authorization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    WebSerial Authorization                       │
├─────────────────────────────────────────────────────────────────┤
│  1. User clicks "Request Device"                                 │
│  2. navigator.serial.requestPort() → browser picker dialog       │
│  3. User selects device → permission granted                     │
│  4. Permission persists in browser storage                       │
│  5. On next visit: navigator.serial.getPorts() → authorized list │
└─────────────────────────────────────────────────────────────────┘
```

---

## Port Enumeration

[hardware-discovery.service.ts:350-363](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/hardware-discovery.service.ts#L350-363)

```typescript
async getAuthorizedSerialPorts(): Promise<DiscoveredDevice[]> {
    if (!this.hasWebSerialSupport()) return [];

    try {
        const ports = await navigator.serial.getPorts();
        return ports.map((port, index) =>
            this.createDeviceFromSerialPort(port, `serial-authorized-${index}`)
        );
    } catch (error) {
        console.error('Error getting authorized serial ports:', error);
        return [];
    }
}
```

**Assessment**: ✅ Authorized ports enumerated on discovery

---

## Connection Lifecycle

| Event | Behavior |
|-------|----------|
| Page refresh | Port authorization persists, connection lost |
| Browser restart | Port authorization persists, connection lost |
| USB disconnect | `disconnect` event fires, device removed from list |
| USB reconnect | Device appears in `getPorts()` if previously authorized |

---

## Connection State Tracking

[hardware-discovery.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/hardware-discovery.service.ts)

```typescript
interface DiscoveredDevice {
    status: 'available' | 'connecting' | 'connected' | 'busy' | 'disconnected' | 'error';
}
```

**Assessment**: ✅ Device state properly tracked

---

## Reconnection Handling

- `navigator.serial.ondisconnect` and `navigator.serial.onconnect` events available
- Current implementation uses polling via `discoverAll()`

---

## Recommendations

1. **Add Event Listeners**: Use `onconnect`/`ondisconnect` for real-time updates
2. **Auto-Reconnect**: Attempt reconnection when previously-used device reappears
3. **Connection Health Check**: Periodically verify open ports are still responsive

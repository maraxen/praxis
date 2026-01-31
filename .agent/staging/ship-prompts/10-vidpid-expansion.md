# VID/PID Table Expansion (P2)

> **Stream**: 5 - Hardware Support  
> **Effort**: M (2-3 hours)  
> **Priority**: P2

---

## Objective

Expand the KNOWN_DEVICES table to cover more PLR backends (currently 9 entries vs 33 backends = 73% gap), improving automatic device detection.

---

## Context Files (Read First)

1. `.agent/staging/logic-audits/comprehensive_logic_audit.md` → Section "VID/PID Lookup Completeness"
2. `src/app/core/services/hardware-discovery.service.ts`
3. `src/assets/browser-data/plr-definitions.ts`

---

## Root Cause Analysis

**Problem**: KNOWN_DEVICES only covers 9 VID/PID pairs, but there are 33 PLR backend definitions.

**Current coverage**:
- Hamilton STAR/Starlet ✅
- Opentrons OT-2 ✅
- BMG CLARIOstar ✅
- Tecan (EVO, Freedom) ❌
- Inheco (heaters/shakers) ❌
- Agilent ❌
- Many plate readers ❌

**Impact**: Unrecognized devices show as "Unknown Device" and require manual backend selection.

---

## Scope

### Change
- Expand `KNOWN_DEVICES` table in `hardware-discovery.service.ts`
- Add VID/PID entries for common lab equipment

### Do NOT Change
- Discovery logic
- Backend instantiation code
- PLR definitions

---

## Implementation Steps

1. **Research VID/PID values**
   - Search PLR source code for device identifiers
   - Reference manufacturer documentation
   - Check USB ID database: https://usb-ids.gowdy.us/

2. **Prioritize by usage**
   - Tecan EVO/Freedom (high usage)
   - Inheco heaters (common accessory)
   - Agilent readers (common in labs)

3. **Add entries to KNOWN_DEVICES**
   ```typescript
   // hardware-discovery.service.ts
   const KNOWN_DEVICES: Record<string, DeviceInfo> = {
     // Existing...
     
     // Tecan
     '0x0E7E:0x0001': { manufacturer: 'Tecan', model: 'EVO', plrBackend: 'tecan.EVO' },
     '0x0E7E:0x0002': { manufacturer: 'Tecan', model: 'Freedom', plrBackend: 'tecan.Freedom' },
     
     // Inheco
     '0x1234:0x5678': { manufacturer: 'Inheco', model: 'CPAC', plrBackend: 'inheco.CPAC' },
     // ... more entries
   };
   ```

4. **Add fallback for unknown devices**
   ```typescript
   // Show helpful message for unrecognized VID/PID
   if (!KNOWN_DEVICES[vidPid]) {
     console.info(`Unknown device ${vidPid}. Consider adding to KNOWN_DEVICES table.`);
     // Still return device with generic info
   }
   ```

5. **Document the table**
   - Add comment explaining how to add new entries
   - Link to USB ID database

---

## Verification

```bash
# Run hardware-related E2E tests
npx playwright test machine-frontend-backend.spec.ts --reporter=line 2>&1 | tail -10

# Manual verification:
# 1. Connect a known device
# 2. Verify it's correctly identified
# 3. Connect an unknown device
# 4. Verify helpful console message appears
```

---

## Success Criteria

- [ ] At least 5 new VID/PID entries added
- [ ] Fallback message for unknown devices
- [ ] Documentation added to KNOWN_DEVICES
- [ ] No regression in device detection for existing entries

---

## Notes

If VID/PID values cannot be found for specific devices, document which backends are missing and recommend:
1. User testing to capture VID/PID values
2. Backend API fallback for device matching

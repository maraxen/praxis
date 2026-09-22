# Storage Quotas Audit

## Status: ⚠️ LocalStorage Handled, OPFS Quota Not Monitored

---

## LocalStorage Quota Handling

[local-storage.adapter.ts:84-86](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/local-storage.adapter.ts#L84-86)

```typescript
// Handle quota exceeded
if (e.name === 'QuotaExceededError') {
    console.error('[LocalStorageAdapter] Storage quota exceeded!');
}
```

**Assessment**: ✅ Catches and logs quota errors

### Storage Stats

```typescript
getStorageStats(): { used: number; quota: number; percentage: number } {
    const used = new Blob(Object.values(localStorage)).size;
    const quota = 5 * 1024 * 1024; // 5MB assumed
    return { used, quota, percentage: Math.round((used / quota) * 100) };
}
```

**Assessment**: ✅ Can monitor usage percentage

---

## OPFS Quota (SQLite Database)

| Concern | Status |
|---------|--------|
| Quota exceeded handling | ❌ Not implemented |
| Storage estimate API | ❌ Not used |
| User warning at threshold | ❌ Not implemented |

### Potential OPFS Limits

| Browser | Origin Quota |
|---------|--------------|
| Chrome | 60% of available disk |
| Firefox | 50% of available disk |
| Safari | ~1GB (varies) |

---

## StorageManager API (Not Currently Used)

```typescript
// Could be added to monitor OPFS usage
const estimate = await navigator.storage.estimate();
console.log(`Used: ${estimate.usage}, Quota: ${estimate.quota}`);
```

---

## Recommendations

1. **Add OPFS Quota Monitoring**: Use `navigator.storage.estimate()` to track usage
2. **Warn at 80% Threshold**: Show toast when approaching quota limit
3. **Implement Cleanup Strategy**: Offer to delete old protocol runs when near quota
4. **Request Persistent Storage**: Use `navigator.storage.persist()` to prevent eviction

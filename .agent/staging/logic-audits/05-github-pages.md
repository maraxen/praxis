# GitHub Pages Pathing Audit

## baseHref Calculation Patterns

Found **3 different implementations** across the codebase:

| Location | Pattern | Notes |
|----------|---------|-------|
| `asset.service.ts:545` | `baseHref.endsWith('/') ? baseHref : baseHref + '/'` | Ensures trailing slash |
| `playground-jupyterlite.service.ts:363` | `baseHref.startsWith('/') ? baseHref : '/' + baseHref` | Ensures leading slash only |
| `playground.component.ts:893-894` | Same as above | Duplicate of jupyterlite service |

## calculateHostRoot Logic

[playground-jupyterlite.service.ts:354-367](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L354-367)

```typescript
private calculateHostRoot(): string {
  const href = window.location.href;
  const anchor = '/assets/jupyterlite/';

  // If already in jupyterlite iframe, extract parent origin
  if (href.includes(anchor)) {
    return href.split(anchor)[0] + '/';
  }

  // Otherwise compute from <base> tag
  const baseHref = document.querySelector('base')?.getAttribute('href') || '/';
  const cleanBase = baseHref.startsWith('/') ? baseHref : '/' + baseHref;
  const finalBase = cleanBase.endsWith('/') ? cleanBase : cleanBase + '/';

  return window.location.origin + finalBase;
}
```

## Assessment: ⚠️ Inconsistent Patterns

**Issue**: Three different slash normalization approaches could lead to edge-case failures.

**Recommendation**: Create `PathUtils.normalizeBaseHref()` helper:

```typescript
export function normalizeBaseHref(base: string): string {
  let result = base;
  if (!result.startsWith('/')) result = '/' + result;
  if (!result.endsWith('/')) result = result + '/';
  return result;
}
```

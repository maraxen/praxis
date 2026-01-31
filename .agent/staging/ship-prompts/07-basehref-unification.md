# Unify baseHref Patterns (P1)

> **Stream**: 2 - Code Quality  
> **Effort**: S (1 hour)  
> **Priority**: P1 (Quick Win)

---

## Objective

Consolidate 3 different baseHref normalization patterns into a single `PathUtils.normalizeBaseHref()` utility to prevent edge-case path failures on GitHub Pages deployment.

---

## Context Files (Read First)

1. `.agent/staging/logic-audits/comprehensive_logic_audit.md` → Section "GitHub Pages Implementation Pathing"
2. `src/app/features/assets/services/asset.service.ts:545`
3. `src/app/features/playground/services/playground-jupyterlite.service.ts:363`
4. `src/app/features/playground/components/playground/playground.component.ts:893-894`

---

## Root Cause Analysis

**Problem**: Three different slash normalization approaches:

| Location | Pattern |
|----------|---------|
| `asset.service.ts` | Ensures trailing slash only |
| `jupyterlite.service.ts` | Ensures leading slash only |
| `calculateHostRoot` | Ensures both |

**Risk**: Edge cases where path is `/praxis` vs `praxis/` vs `/praxis/` could break asset loading.

---

## Scope

### Change
- Create `src/app/core/utils/path.utils.ts`
- Update 3 locations to use the new utility

### Do NOT Change
- Route configurations
- Build configuration
- Any other path handling

---

## Implementation Steps

1. **Create PathUtils**
   ```typescript
   // src/app/core/utils/path.utils.ts
   export class PathUtils {
     /**
      * Normalizes baseHref to have both leading and trailing slashes.
      * Examples:
      *   'praxis' → '/praxis/'
      *   '/praxis' → '/praxis/'
      *   'praxis/' → '/praxis/'
      *   '/praxis/' → '/praxis/'
      *   '' → '/'
      *   '/' → '/'
      */
     static normalizeBaseHref(baseHref: string | null | undefined): string {
       if (!baseHref || baseHref === '/') return '/';
       
       let normalized = baseHref;
       if (!normalized.startsWith('/')) {
         normalized = '/' + normalized;
       }
       if (!normalized.endsWith('/')) {
         normalized = normalized + '/';
       }
       return normalized;
     }
   }
   ```

2. **Write unit test**
   ```typescript
   // src/app/core/utils/path.utils.spec.ts
   describe('PathUtils.normalizeBaseHref', () => {
     it('handles all variations', () => {
       expect(PathUtils.normalizeBaseHref('praxis')).toBe('/praxis/');
       expect(PathUtils.normalizeBaseHref('/praxis')).toBe('/praxis/');
       expect(PathUtils.normalizeBaseHref('praxis/')).toBe('/praxis/');
       expect(PathUtils.normalizeBaseHref('/praxis/')).toBe('/praxis/');
       expect(PathUtils.normalizeBaseHref('')).toBe('/');
       expect(PathUtils.normalizeBaseHref('/')).toBe('/');
       expect(PathUtils.normalizeBaseHref(null)).toBe('/');
     });
   });
   ```

3. **Update asset.service.ts**
   ```bash
   # Find the line
   grep -n "endsWith('/')" src/app/features/assets/services/asset.service.ts
   ```

4. **Update playground-jupyterlite.service.ts**
   ```bash
   grep -n "startsWith('/')" src/app/features/playground/services/playground-jupyterlite.service.ts
   ```

5. **Update playground.component.ts**
   ```bash
   grep -n "startsWith('/')" src/app/features/playground/components/playground/playground.component.ts
   ```

---

## Verification

```bash
# Run unit tests
npm run test -- --include="**/path.utils.spec.ts"

# Build for GH Pages
npm run build -- --base-href=/praxis/

# Run ghpages deployment spec
npx playwright test ghpages-deployment.spec.ts --reporter=line 2>&1 | tail -10
```

---

## Success Criteria

- [ ] `PathUtils.normalizeBaseHref()` created with tests
- [ ] 3 locations updated to use utility
- [ ] `ghpages-deployment.spec.ts` passes
- [ ] No build errors

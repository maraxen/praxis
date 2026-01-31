# Shipping Readiness Criteria

## Critical User Paths

### 1. Database & Seeding
- [ ] `praxis.db` pre-packaged and loads correctly
- [ ] Seed data contains valid machines, assets, protocols

### 2. Protocol Execution Flow
- [ ] Parameters inferred and presented correctly
- [ ] Machine selection works with seeded data
- [ ] Asset selection options populated and selectable
- [ ] Parameter serialization functional when running protocols

### 3. JupyterLite Integration
- [ ] Bootstrap completes successfully
- [ ] Works in standard dev server
- [ ] Works in GH Pages deployment
- [ ] Loading machines/resources into session works

### 4. Direct Control
- [ ] Playground direct control operational
- [ ] Commands execute as expected

### 5. UI/UX
- [ ] Navigation stable
- [ ] Error handling graceful
- [ ] Logo/branding correct

## E2E Test Coverage Requirements
- Smoke tests passing
- Critical path specs passing
- No blocking errors in console

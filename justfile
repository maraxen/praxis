# Praxis Web-Client Development Commands
# Usage: just <command>
# Install just: brew install just

# Default working directory for web-client commands
wc := "praxis/web-client"
logs := "tmp/logs"

# ===== BUILD COMMANDS =====

# Build the web-client with output logged
build:
    @mkdir -p {{logs}}
    cd {{wc}} && npm run build 2>&1 | tee {{justfile_directory()}}/{{logs}}/build-$(date +%Y%m%d_%H%M%S).log

# Build for GitHub Pages deployment (static bundle)
build-ghpages:
    @mkdir -p {{logs}}
    cd {{wc}} && npm run build:browser 2>&1 | tee {{justfile_directory()}}/{{logs}}/build-ghpages-$(date +%Y%m%d_%H%M%S).log

# Quick build without logging (faster for iteration)
build-quiet:
    cd {{wc}} && npm run build

# ===== DEV SERVERS =====

# Start the Angular dev server (browser mode)
dev:
    cd {{wc}} && npm run start:browser

# Start static server for pre-built bundle (mimics GH Pages)
serve-static:
    cd {{wc}} && npx -y serve dist/web-client/browser -l 8080 --single -c scripts/serve-static.json

# Start static server with COOP/COEP headers (for SharedArrayBuffer)
serve-static-headers:
    @echo '{"headers":[{"source":"**/*","headers":[{"key":"Cross-Origin-Opener-Policy","value":"same-origin"},{"key":"Cross-Origin-Embedder-Policy","value":"require-corp"}]}]}' > /tmp/serve-headers.json
    cd {{wc}} && npx -y serve dist/web-client/browser -l 8080 --single -c /tmp/serve-headers.json

# ===== TEST COMMANDS =====

# Run unit tests with vitest
test:
    cd {{wc}} && npm run test

# Run unit tests in watch mode
test-watch:
    cd {{wc}} && npm run test -- --watch

# Run E2E tests with default Playwright config (uses dev server)
e2e:
    @mkdir -p {{logs}}
    cd {{wc}} && npx playwright test 2>&1 | tee {{justfile_directory()}}/{{logs}}/e2e-$(date +%Y%m%d_%H%M%S).log

# Run E2E tests with static config (faster, uses pre-built bundle)
e2e-static:
    @mkdir -p {{logs}}
    cd {{wc}} && npx playwright test --config=playwright.static.config.ts 2>&1 | tee {{justfile_directory()}}/{{logs}}/e2e-static-$(date +%Y%m%d_%H%M%S).log

# Run smoke tests only (fastest)
e2e-smoke:
    cd {{wc}} && npx playwright test smoke.spec.ts --config=playwright.static.config.ts

# Run E2E with UI mode for debugging
e2e-ui:
    cd {{wc}} && npx playwright test --ui

# Run slow/integration tests explicitly
e2e-slow:
    cd {{wc}} && RUN_SLOW_TESTS=1 npx playwright test --config=playwright.static.config.ts --grep @slow

# ===== UTILITY COMMANDS =====

# Install dependencies
install:
    cd {{wc}} && npm install

# Clean build artifacts
clean:
    cd {{wc}} && rm -rf dist node_modules/.cache .angular/cache

# Check TypeScript types without building
typecheck:
    cd {{wc}} && npx tsc --noEmit

# Run ESLint
lint:
    cd {{wc}} && npm run lint

# Format code with prettier
format:
    cd {{wc}} && npx prettier --write "src/**/*.{ts,html,scss}"

# ===== COMPOUND COMMANDS =====

# Full build and static test cycle
verify: build-ghpages e2e-static

# Quick development cycle: typecheck and unit tests
check: typecheck test

# Full CI simulation
ci: install build test e2e

# Deploy to GH Pages (build and push)
deploy-ghpages: build-ghpages
    @echo "Built static bundle. Run 'git push' to deploy to GH Pages."

# ===== JULES & ORCHESTRATION =====

# List Jules sessions
jules-list:
    jules remote list --session 2>&1 | head -20

# Pull diff from a Jules session
jules-pull session:
    @mkdir -p tmp/jules_diffs
    jules remote pull --session {{session}} > tmp/jules_diffs/{{session}}.diff 2>&1
    @cat tmp/jules_diffs/{{session}}.diff

# Apply diff from a Jules session
jules-apply session:
    jules remote pull --session {{session}} --apply 2>&1

# ===== HELP =====

# List all available commands
help:
    @just --list

#!/bin/bash
# Frontend development script with auto Docker management
# Starts ephemeral Docker stack before ng serve, cleans up on exit

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/praxis/web-client"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[dev]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[dev]${NC} $1"
}

log_error() {
    echo -e "${RED}[dev]${NC} $1"
}

# Check if Docker daemon is running, start if needed
ensure_docker_running() {
    if docker info > /dev/null 2>&1; then
        log_info "Docker daemon is running."
        return 0
    fi

    log_warn "Docker daemon is not running."

    # macOS: Try to start Docker Desktop
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [ -d "/Applications/Docker.app" ]; then
            log_info "Starting Docker Desktop..."
            open -a Docker

            # Wait for Docker to be ready (up to 60 seconds)
            log_info "Waiting for Docker to start (this may take a moment)..."
            for i in {1..60}; do
                if docker info > /dev/null 2>&1; then
                    log_info "Docker is ready!"
                    return 0
                fi
                echo -n "."
                sleep 1
            done
            echo ""
            log_error "Docker failed to start within 60 seconds."
            log_error "Please start Docker Desktop manually and try again."
            exit 1
        else
            log_error "Docker Desktop not found at /Applications/Docker.app"
            log_error "Please install Docker Desktop: https://www.docker.com/products/docker-desktop"
            exit 1
        fi
    # Linux: Try to start docker service
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "Attempting to start Docker service..."
        if command -v systemctl > /dev/null 2>&1; then
            sudo systemctl start docker || {
                log_error "Failed to start Docker. Try: sudo systemctl start docker"
                exit 1
            }
            sleep 2
            if docker info > /dev/null 2>&1; then
                log_info "Docker is ready!"
                return 0
            fi
        else
            log_error "Please start Docker daemon manually: sudo dockerd"
            exit 1
        fi
    else
        log_error "Unsupported OS. Please start Docker manually."
        exit 1
    fi
}

# Cleanup function - called on exit
cleanup() {
    echo ""
    log_info "Shutting down development environment..."
    cd "$PROJECT_ROOT"
    make dev-ephemeral-down 2>/dev/null || true
    log_info "Cleanup complete."
}

# Set trap to cleanup on exit, interrupt, or termination
trap cleanup EXIT INT TERM

# Ensure Docker is running
ensure_docker_running

# Start ephemeral Docker stack
log_info "Starting ephemeral Docker stack (data in RAM)..."
cd "$PROJECT_ROOT"
make dev-ephemeral

# Wait for services to be healthy
log_info "Waiting for services to be ready..."
sleep 3

# Check if services are up
if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    log_info "Docker services are running."
else
    log_error "Docker services failed to start!"
    exit 1
fi

# Start Angular dev server
log_info "Starting Angular development server..."
cd "$FRONTEND_DIR"
bun run start

# Note: cleanup() will be called automatically when ng serve exits

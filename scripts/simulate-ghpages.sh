#!/bin/bash
# GitHub Pages environment simulation script
# Builds and serves the app as if deployed to /praxis/ subdirectory
#
# Usage: ./scripts/simulate-ghpages.sh [--no-build]
#
# Options:
#   --no-build    Skip the build step (use existing dist)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WEB_CLIENT_DIR="$PROJECT_DIR/praxis/web-client"
SIM_DIR="/tmp/ghpages-sim"
PORT="${PORT:-8080}"

NO_BUILD=false
if [[ "$1" == "--no-build" ]]; then
    NO_BUILD=true
fi

echo "🎯 GitHub Pages Simulation"
echo "   Project: $PROJECT_DIR"
echo "   Port: $PORT"
echo ""

# Step 1: Build (optional)
if [[ "$NO_BUILD" == false ]]; then
    echo "🏗️  Building for GH Pages..."
    cd "$WEB_CLIENT_DIR"
    bun run build:gh-pages
    echo ""
fi

# Step 2: Verify build exists
if [[ ! -d "$WEB_CLIENT_DIR/dist/web-client/browser" ]]; then
    echo "❌ Error: Build directory not found!"
    echo "   Expected: $WEB_CLIENT_DIR/dist/web-client/browser"
    echo "   Run without --no-build to create it."
    exit 1
fi

# Step 3: Clean and create simulation directory
echo "📁 Creating simulation directory..."
rm -rf "$SIM_DIR"
mkdir -p "$SIM_DIR/praxis"

# Step 4: Copy build artifacts
echo "📋 Copying build artifacts to /praxis/ subdirectory..."
cp -r "$WEB_CLIENT_DIR/dist/web-client/browser/"* "$SIM_DIR/praxis/"

# Step 5: Create 404.html for SPA routing (GitHub Pages pattern)
echo "📝 Creating 404.html for SPA routing..."
cp "$SIM_DIR/praxis/index.html" "$SIM_DIR/404.html"
# Also copy to praxis subdirectory
cp "$SIM_DIR/praxis/index.html" "$SIM_DIR/praxis/404.html"

# Step 6: Create serve configuration with required headers
echo "🔧 Creating server configuration..."
cat > "$SIM_DIR/serve.json" << 'EOF'
{
  "headers": [
    {
      "source": "**/*",
      "headers": [
        { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" },
        { "key": "Cross-Origin-Embedder-Policy", "value": "require-corp" },
        { "key": "Cross-Origin-Resource-Policy", "value": "cross-origin" }
      ]
    }
  ],
  "rewrites": [
    { "source": "praxis/app/**", "destination": "/praxis/index.html" },
    { "source": "praxis/assets/**", "destination": "/praxis/index.html" },
    { "source": "praxis/protocols/**", "destination": "/praxis/index.html" },
    { "source": "praxis/run/**", "destination": "/praxis/index.html" },
    { "source": "praxis/playground", "destination": "/praxis/index.html" },
    { "source": "praxis/settings/**", "destination": "/praxis/index.html" }
  ]
}
EOF

# Step 7: Kill any existing server on the port
echo "🔄 Checking for existing server on port $PORT..."
lsof -ti:$PORT | xargs kill -9 2>/dev/null || true

# Step 8: Start the server
echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "🚀 Starting GH Pages simulation server"
echo ""
echo "   Local URL:    http://localhost:$PORT/praxis/"
echo "   App Home:     http://localhost:$PORT/praxis/app/home?mode=browser"
echo "   Playground:   http://localhost:$PORT/praxis/playground"
echo ""
echo "   This simulates: https://phrxmd.github.io/praxis/"
echo ""
echo "   Headers enabled:"
echo "     - Cross-Origin-Opener-Policy: same-origin"
echo "     - Cross-Origin-Embedder-Policy: require-corp"
echo ""
echo "   Press Ctrl+C to stop"
echo "══════════════════════════════════════════════════════════════════"
echo ""

cd "$SIM_DIR"
exec npx -y serve -l "$PORT" --config serve.json

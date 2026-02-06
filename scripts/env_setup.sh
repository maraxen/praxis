#!/bin/bash

# This script sets up the Praxis environment on a Linux system.
# It creates a systemd service for the Praxis browser and installs dependencies.
# This way the env can be snapshotted and restored, with the browser app running.

# 1. Variables - Update these if your paths differ
APP_DIR="/app/praxis/web-client"
LOG_DIR="$HOME/tmp"
LOG_FILE="$LOG_DIR/browser_log.log"
BUN_PATH=$(which bun)
USER_NAME=$(whoami)

echo "--- Starting Praxis Environment Setup ---"

# 2. Ensure log directory exists
mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

# 3. Navigate to app and install dependencies
# We do this now so the VM is 'ready' before the service takes over
cd "$APP_DIR" || { echo "Directory $APP_DIR not found"; exit 1; }
echo "Installing dependencies with Bun..."
$BUN_PATH install

# 4. Create the systemd service file
# This is what makes the setup 'snapshottable' and persistent
echo "Creating systemd service..."
sudo bash -c "cat <<EOF > /etc/systemd/system/praxis-browser.service
[Unit]
Description=Praxis Web Client Browser Service
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$APP_DIR
ExecStart=$BUN_PATH run start:browser
# Redirect both stdout and stderr to your log file
StandardOutput=append:$LOG_FILE
StandardError=inherit
Restart=always
RestartSec=5
Environment=PATH=/usr/bin:/usr/local/bin:$(dirname $BUN_PATH)

[Install]
WantedBy=multi-user.target
EOF"

# 5. Enable and Start the service
echo "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable praxis-browser.service
sudo systemctl start praxis-browser.service

echo "--- Setup Complete ---"
echo "The app is now running in the background."
echo "You can check logs with: tail -f $LOG_FILE"
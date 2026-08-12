#!/bin/bash
set -e

INSTALL_DIR="/opt/log_agent"
SERVICE_FILE="/etc/systemd/system/log_agent.service"

echo "🧹 Starting cleanup process for Log Agent..."

# 1. Stop and disable the systemd service if it exists
if systemctl list-unit-files | grep -q "log_agent.service"; then
    echo "Stopping log_agent service..."
    sudo systemctl stop log_agent || true
    echo "Disabling log_agent service..."
    sudo systemctl disable log_agent || true
fi

# 2. Remove the systemd service file
if [ -f "$SERVICE_FILE" ]; then
    echo "Removing systemd service file..."
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
fi

# 3. Remove the installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Deleting installation directory: $INSTALL_DIR..."
    sudo rm -rf "$INSTALL_DIR"
fi

echo "✅ Cleanup complete! The system is ready for a fresh installation."
echo "Note: If you added the automated cleanup cron job earlier, you can manually remove it by running 'sudo crontab -e'."

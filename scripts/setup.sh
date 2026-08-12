#!/bin/bash
set -e

# Default installation directory
INSTALL_DIR="/opt/log_agent"

echo "Setting up Log Agent in $INSTALL_DIR..."

# Create the base application folders
sudo mkdir -p "$INSTALL_DIR"/{config,src,systemd,drop_zones}
sudo mkdir -p "$INSTALL_DIR/src/prompts"

# Create drop zones for default users (alice and bob)
sudo mkdir -p "$INSTALL_DIR"/drop_zones/alice/{logs_in,reports_out}
sudo mkdir -p "$INSTALL_DIR"/drop_zones/bob/{logs_in,reports_out}

# Set appropriate permissions so users can SCP via terminal
sudo chmod -R 777 "$INSTALL_DIR"/drop_zones

# Setup Python environment
echo "Setting up Python virtual environment..."
cd "$INSTALL_DIR"
sudo python3 -m venv venv

# Copy files from repository to the installation directory
echo "Copying files to $INSTALL_DIR..."
# Assuming script is run from repo root
sudo cp -r src/* "$INSTALL_DIR/src/"
sudo cp requirements.txt "$INSTALL_DIR/"

if [ ! -f "$INSTALL_DIR/.env" ]; then
    sudo cp .env.example "$INSTALL_DIR/.env"
fi

# Install dependencies
echo "Installing dependencies..."
sudo "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "Setup complete. Please review the environment variables in $INSTALL_DIR/.env or in your systemd service file."
echo "To install the systemd service, copy systemd/log_agent.service to /etc/systemd/system/ and run:"
echo "sudo systemctl daemon-reload && sudo systemctl enable --now log_agent"

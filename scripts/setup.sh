#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# RPi Timelapse Cam - Setup Script
# ============================================================
# Installs system dependencies, creates a Python virtual
# environment, copies the default config, and installs the
# systemd service unit.
#
# Safe to run multiple times (idempotent).
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
CONFIG_DEST="$HOME/timelapse-config.yml"
OUTPUT_DIR="$HOME/timelapse-images"

echo ""
echo "============================================================"
echo "  RPi Timelapse Cam - Setup"
echo "============================================================"
echo ""

# ----------------------------------------------------------
# Check prerequisites
# ----------------------------------------------------------

echo "Checking prerequisites..."

# Check for Python 3.11+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 not found. Install with: sudo apt install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "ERROR: Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "  Python $PYTHON_VERSION OK"

# Check for apt (Raspberry Pi OS / Debian)
if ! command -v apt &>/dev/null; then
    echo "WARNING: apt not found. You may need to install dependencies manually."
    echo "  Required: python3-picamera2, python3-opencv, python3-venv"
fi

echo ""

# ----------------------------------------------------------
# Install system packages
# ----------------------------------------------------------

echo "Installing system packages..."
sudo apt install -y python3-picamera2 python3-opencv python3-pip python3-venv
echo "  System packages installed"
echo ""

# ----------------------------------------------------------
# Create virtual environment with system site-packages
# ----------------------------------------------------------
# --system-site-packages is REQUIRED for picamera2 and cv2 access.
# These libraries are installed as system packages on Pi OS and
# cannot be pip-installed into a venv (PEP 668 / externally-managed).

echo "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
    echo "  Created venv at $VENV_DIR"
else
    echo "  Venv already exists at $VENV_DIR"
fi

# Install Python dependencies inside venv
"$VENV_DIR/bin/pip" install --quiet pyyaml
echo "  Python dependencies installed"
echo ""

# ----------------------------------------------------------
# Copy example config (if not already present)
# ----------------------------------------------------------

echo "Setting up configuration..."
if [ ! -f "$CONFIG_DEST" ]; then
    cp "$PROJECT_DIR/config/timelapse.yml" "$CONFIG_DEST"
    echo "  Copied example config to $CONFIG_DEST"
else
    echo "  Config already exists at $CONFIG_DEST"
fi
echo ""

# ----------------------------------------------------------
# Create default output directory
# ----------------------------------------------------------

echo "Setting up output directory..."
mkdir -p "$OUTPUT_DIR"
echo "  Output directory: $OUTPUT_DIR"
echo ""

# ----------------------------------------------------------
# Install systemd service unit
# ----------------------------------------------------------

echo "Installing systemd service..."
sudo cp "$PROJECT_DIR/systemd/timelapse-capture.service" /etc/systemd/system/
sudo systemctl daemon-reload
echo "  Service installed and daemon reloaded"
echo ""

# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------

echo "============================================================"
echo "  Setup Complete!"
echo "============================================================"
echo ""
echo "  Config file:    $CONFIG_DEST"
echo "  Output dir:     $OUTPUT_DIR"
echo "  Venv:           $VENV_DIR"
echo "  Service:        timelapse-capture.service"
echo ""
echo "  Next steps:"
echo "    1. Edit your config:  nano $CONFIG_DEST"
echo "    2. Start the daemon:  sudo systemctl start timelapse-capture"
echo "    3. Enable on boot:    sudo systemctl enable timelapse-capture"
echo "    4. View logs:         journalctl -u timelapse-capture -f"
echo "    5. Reload config:     sudo systemctl reload timelapse-capture"
echo ""
echo "  For production installs, consider using /var/lib/timelapse"
echo "  as the output directory instead of ~/timelapse-images."
echo ""

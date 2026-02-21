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
# Python/pip resolves pypi.org via getaddrinfo, which by default prefers IPv4
# (per /etc/gai.conf on Debian/Pi OS). If IPv4 is unreachable but IPv6 works,
# pip will hang waiting on the IPv4 connection attempt. Detect this and prefer
# IPv6 by temporarily adjusting gai.conf.
if curl -4 --max-time 5 -sI https://pypi.org >/dev/null 2>&1; then
    echo "  IPv4 connectivity OK"
    "$VENV_DIR/bin/pip" install --quiet --timeout 60 --retries 3 pyyaml flask pillow python-pam flask-httpauth
elif curl -6 --max-time 5 -sI https://pypi.org >/dev/null 2>&1; then
    echo "  IPv4 unreachable, IPv6 OK — configuring pip to prefer IPv6"
    # Temporarily prepend IPv6 preference to gai.conf so getaddrinfo returns
    # AAAA records first. Restored after pip finishes (trap handles set -e).
    GAI_CONF="/etc/gai.conf"
    GAI_MARKER="# rpi-timelapse-setup: prefer-ipv6"
    if ! grep -q "$GAI_MARKER" "$GAI_CONF" 2>/dev/null; then
        sudo cp "$GAI_CONF" "${GAI_CONF}.bak" 2>/dev/null || true
        echo -e "$GAI_MARKER\nprecedence ::0/0  100" | sudo tee -a "$GAI_CONF" > /dev/null
        trap 'sudo mv -f "${GAI_CONF}.bak" "$GAI_CONF" 2>/dev/null || true' EXIT
    fi
    "$VENV_DIR/bin/pip" install --quiet --timeout 60 --retries 3 pyyaml flask pillow python-pam flask-httpauth
    # Restore original gai.conf
    sudo mv -f "${GAI_CONF}.bak" "$GAI_CONF" 2>/dev/null || true
    trap - EXIT
else
    echo "ERROR: Cannot reach pypi.org over IPv4 or IPv6."
    echo "  Check your network connection and try again."
    exit 1
fi
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

echo "Installing systemd services..."
sudo cp "$PROJECT_DIR/systemd/timelapse-capture.service" /etc/systemd/system/
sudo cp "$PROJECT_DIR/systemd/timelapse-web.service" /etc/systemd/system/
sudo systemctl daemon-reload
echo "  Services installed and daemon reloaded"
echo ""

# ----------------------------------------------------------
# Create sudoers drop-in for web UI daemon control
# ----------------------------------------------------------
# The web UI needs passwordless sudo for exactly three systemctl
# commands to start/stop/check the capture daemon.

echo "Setting up sudoers for web UI..."
SUDOERS_FILE="/etc/sudoers.d/timelapse-web"
SUDOERS_CONTENT="pi ALL=(root) NOPASSWD: /usr/bin/systemctl start timelapse-capture
pi ALL=(root) NOPASSWD: /usr/bin/systemctl stop timelapse-capture
pi ALL=(root) NOPASSWD: /usr/bin/systemctl is-active timelapse-capture"

echo "$SUDOERS_CONTENT" | sudo tee "$SUDOERS_FILE" > /dev/null
sudo chmod 0440 "$SUDOERS_FILE"

# Validate sudoers syntax
if sudo visudo -cf "$SUDOERS_FILE"; then
    echo "  Sudoers file created and validated"
else
    echo "ERROR: Sudoers file has syntax errors, removing it"
    sudo rm -f "$SUDOERS_FILE"
    exit 1
fi
echo ""

# ----------------------------------------------------------
# Add shadow group for PAM authentication
# ----------------------------------------------------------

echo "Setting up PAM authentication..."
sudo usermod -aG shadow pi
echo "  Added pi user to shadow group for PAM auth"
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
echo "  Services:       timelapse-capture.service, timelapse-web.service"
echo "  Sudoers:        /etc/sudoers.d/timelapse-web"
echo ""
echo "  Next steps:"
echo "    1. Edit your config:  nano $CONFIG_DEST"
echo ""
echo "  Capture daemon:"
echo "    2. Start the daemon:  sudo systemctl start timelapse-capture"
echo "    3. Enable on boot:    sudo systemctl enable timelapse-capture"
echo "    4. View logs:         journalctl -u timelapse-capture -f"
echo "    5. Reload config:     sudo systemctl reload timelapse-capture"
echo ""
echo "  Web UI:"
echo "    6. Start the web UI:  sudo systemctl start timelapse-web"
echo "    7. Enable on boot:    sudo systemctl enable timelapse-web"
echo "    8. View logs:         journalctl -u timelapse-web -f"
echo "    9. Open in browser:   http://<pi-ip>:8080"
echo ""
echo "  For production installs, consider using /var/lib/timelapse"
echo "  as the output directory instead of ~/timelapse-images."
echo ""

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
# pip uses Python's getaddrinfo() which returns both A (IPv4) and AAAA (IPv6)
# records. urllib3 tries them sequentially - if the preferred protocol has no
# working route, pip hangs until that attempt times out. The gai.conf
# precedence trick only reorders results; urllib3 still tries all of them.
# Fix: when one protocol is broken, force DNS resolution via /etc/hosts so
# getaddrinfo() only returns addresses for the working protocol.
PIP_HOSTS_MARKER="# rpi-timelapse-setup"
PIP_HOSTS="pypi.org files.pythonhosted.org"

pip_install_deps() {
    "$VENV_DIR/bin/pip" install --quiet --timeout 60 --retries 3 \
        pyyaml flask pillow python-pam flask-httpauth
}

force_hosts_ipv6() {
    # Pin pypi hosts to their IPv6 addresses in /etc/hosts so getaddrinfo()
    # never returns an IPv4 address that pip would hang trying to reach.
    for host in $PIP_HOSTS; do
        ipv6=$(python3 -c "import socket; r=socket.getaddrinfo('$host',443,socket.AF_INET6); print(r[0][4][0])" 2>/dev/null)
        if [ -n "$ipv6" ]; then
            echo "$ipv6 $host $PIP_HOSTS_MARKER" | sudo tee -a /etc/hosts > /dev/null
        fi
    done
}

force_hosts_ipv4() {
    # Pin pypi hosts to their IPv4 addresses in /etc/hosts so getaddrinfo()
    # never returns an IPv6 address that pip would hang trying to reach.
    for host in $PIP_HOSTS; do
        ipv4=$(python3 -c "import socket; r=socket.getaddrinfo('$host',443,socket.AF_INET); print(r[0][4][0])" 2>/dev/null)
        if [ -n "$ipv4" ]; then
            echo "$ipv4 $host $PIP_HOSTS_MARKER" | sudo tee -a /etc/hosts > /dev/null
        fi
    done
}

cleanup_hosts() {
    sudo sed -i "/$PIP_HOSTS_MARKER/d" /etc/hosts 2>/dev/null || true
}
trap cleanup_hosts EXIT

if curl -4 --max-time 5 -sI https://pypi.org >/dev/null 2>&1; then
    if curl -6 --max-time 5 -sI https://pypi.org >/dev/null 2>&1; then
        echo "  IPv4 and IPv6 connectivity OK"
    else
        echo "  IPv4 OK, IPv6 unreachable - pinning pip to IPv4"
        force_hosts_ipv4
    fi
    pip_install_deps
elif curl -6 --max-time 5 -sI https://pypi.org >/dev/null 2>&1; then
    echo "  IPv4 unreachable, IPv6 OK - pinning pip to IPv6"
    force_hosts_ipv6
    pip_install_deps
else
    echo "ERROR: Cannot reach pypi.org over IPv4 or IPv6."
    echo "  Check your network connection and try again."
    exit 1
fi

cleanup_hosts
trap - EXIT
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

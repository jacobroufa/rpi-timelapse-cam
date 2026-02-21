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
RUN_USER="${SUDO_USER:-$USER}"
RUN_HOME=$(eval echo "~$RUN_USER")
CONFIG_DEST="$RUN_HOME/timelapse-config.yml"
OUTPUT_DIR="$RUN_HOME/timelapse-images"

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
# The default MTU of 1500 can be too large for some network paths (PPPoE,
# VPN, or routers that drop ICMP "fragmentation needed" packets). TCP
# connects fine with small SYN packets, but TLS handshakes fail because
# the larger ServerHello+Certificate packets are silently dropped.
# Detect this by attempting a TLS handshake and reduce MTU if it fails.
NET_IFACE=$(ip route show default | awk '{print $5; exit}')
ORIGINAL_MTU=$(ip link show "$NET_IFACE" | awk '/mtu/{for(i=1;i<=NF;i++) if($i=="mtu") print $(i+1)}')
MTU_REDUCED=""

tls_test() {
    "$VENV_DIR/bin/python3" -c "
import ssl, socket
ctx = ssl.create_default_context()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(('pypi.org', 443))
ss = ctx.wrap_socket(s, server_hostname='pypi.org')
ss.close()
" 2>/dev/null
}

if ! tls_test; then
    echo "  TLS handshake failed at MTU $ORIGINAL_MTU - reducing MTU to 1200"
    sudo ip link set "$NET_IFACE" mtu 1200
    MTU_REDUCED="1"
    if ! tls_test; then
        echo "ERROR: TLS handshake to pypi.org still fails at MTU 1200."
        echo "  Check your network connection and try again."
        sudo ip link set "$NET_IFACE" mtu "$ORIGINAL_MTU"
        exit 1
    fi
    echo "  TLS handshake OK at MTU 1200"
fi

# --break-system-packages: the venv uses --system-site-packages for
# picamera2/cv2 access, which can trigger PEP 668 on Pi OS Bookworm+.
"$VENV_DIR/bin/pip" install --break-system-packages \
    --timeout 60 --retries 3 --prefer-binary --no-cache-dir \
    pyyaml flask pillow python-pam flask-httpauth

# Install the project itself in editable mode so `python -m timelapse` works.
# Editable install symlinks back to src/ -- code changes take effect immediately.
"$VENV_DIR/bin/pip" install --break-system-packages --no-cache-dir -e "$PROJECT_DIR"

# Restore original MTU if we changed it
if [ "$MTU_REDUCED" = "1" ]; then
    sudo ip link set "$NET_IFACE" mtu "$ORIGINAL_MTU"
    echo "  Restored MTU to $ORIGINAL_MTU"
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
# Template the service units with the actual username and project path.
# The shipped .service files use 'pi' and '/home/pi/...' as defaults.
sed -e "s|User=pi|User=$RUN_USER|g" \
    -e "s|Group=pi|Group=$RUN_USER|g" \
    -e "s|/home/pi/rpi-timelapse-cam|$PROJECT_DIR|g" \
    -e "s|/home/pi/timelapse-config.yml|$CONFIG_DEST|g" \
    "$PROJECT_DIR/systemd/timelapse-capture.service" | sudo tee /etc/systemd/system/timelapse-capture.service > /dev/null
sed -e "s|User=pi|User=$RUN_USER|g" \
    -e "s|Group=pi|Group=$RUN_USER|g" \
    -e "s|/home/pi/rpi-timelapse-cam|$PROJECT_DIR|g" \
    -e "s|/home/pi/timelapse-config.yml|$CONFIG_DEST|g" \
    "$PROJECT_DIR/systemd/timelapse-web.service" | sudo tee /etc/systemd/system/timelapse-web.service > /dev/null
sudo systemctl daemon-reload
echo "  Services installed for user $RUN_USER and daemon reloaded"
echo ""

# ----------------------------------------------------------
# Create sudoers drop-in for web UI daemon control
# ----------------------------------------------------------
# The web UI needs passwordless sudo for exactly three systemctl
# commands to start/stop/check the capture daemon.

echo "Setting up sudoers for web UI..."
SUDOERS_FILE="/etc/sudoers.d/timelapse-web"
SUDOERS_CONTENT="$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl start timelapse-capture
$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl stop timelapse-capture
$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl is-active timelapse-capture"

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
sudo usermod -aG shadow "$RUN_USER"
echo "  Added $RUN_USER to shadow group for PAM auth"
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

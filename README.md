# RPi Timelapse Cam

A three-part toolkit for Raspberry Pi that automates interval photography, provides a web interface for browsing captured images and monitoring system health, and generates timelapse videos from collected images using FFmpeg.

## Features

- **Capture Daemon** -- Configurable interval photography with Pi Camera (picamera2) or USB webcam (OpenCV) support, SIGHUP config reload, disk space monitoring, and optional auto-cleanup of old images
- **Web UI** -- Flask-based interface with three tabs: Timeline (scrollable filmstrip with keyboard navigation and date picker), Latest Image (auto-refreshing still), and Control (PAM-authenticated daemon management)
- **Timelapse Generator** -- Standalone FFmpeg wrapper that compresses any date range into a video, with configurable duration, subsampling, dry-run mode, and thumbnail preview support

## Requirements

- Python 3.11+
- Raspberry Pi with Pi Camera Module or USB webcam
- FFmpeg (for video generation)
- Raspberry Pi OS / Debian (for `apt`-based setup)

## Quick Start

```bash
git clone https://github.com/jacobroufa/rpi-timelapse-cam.git
cd rpi-timelapse-cam
bash scripts/setup.sh
```

The setup script:
1. Installs system packages (`python3-picamera2`, `python3-opencv`, `python3-venv`)
2. Creates a Python virtual environment with system site-packages (required for picamera2/cv2)
3. Installs Python dependencies (`pyyaml`, `flask`, `pillow`, `python-pam`, `flask-httpauth`)
4. Copies the default config to `~/timelapse-config.yml`
5. Creates the output directory at `~/timelapse-images`
6. Installs and configures systemd services
7. Sets up sudoers rules and PAM auth for the web UI control tab

After setup, enable the services:

```bash
sudo systemctl enable --now timelapse-capture
sudo systemctl enable --now timelapse-web
```

## Configuration

All settings live in a YAML config file. The lookup order is:

1. `--config PATH` (explicit)
2. `/etc/timelapse/timelapse.yml`
3. `./config/timelapse.yml`

Every setting is optional -- defaults apply when omitted.

### Capture

| Option | Default | Description |
|--------|---------|-------------|
| `capture.interval` | `60` | Seconds between captures |
| `capture.source` | `"auto"` | Camera source: `"auto"`, `"picamera"`, or `"usb"` |
| `capture.jpeg_quality` | `85` | JPEG compression quality, 1--100 |
| `capture.resolution` | `[1920, 1080]` | Capture resolution as `[width, height]` |

### Storage

| Option | Default | Description |
|--------|---------|-------------|
| `storage.output_dir` | `"~/timelapse-images"` | Directory for captured images (supports `~`) |
| `storage.stop_threshold` | `90` | Hard stop: refuse captures above this disk usage % |
| `storage.warn_threshold` | `85` | Log a warning above this disk usage % |
| `storage.cleanup_enabled` | `false` | Enable auto-cleanup of old images |
| `storage.retention_days` | `30` | Days to retain images when cleanup is enabled |

### Logging

| Option | Default | Description |
|--------|---------|-------------|
| `logging.gap_tracking` | `false` | Track and log missed/failed captures |

### Web

| Option | Default | Description |
|--------|---------|-------------|
| `web.port` | `8080` | Port to listen on |
| `web.host` | `"0.0.0.0"` | Host to bind to |

## Usage

### Capture Daemon

The daemon is the default subcommand:

```bash
# Run directly
python -m timelapse --config /path/to/timelapse.yml

# Or via systemd
sudo systemctl start timelapse-capture
sudo systemctl stop timelapse-capture

# Reload config without restarting (sends SIGHUP)
sudo systemctl reload timelapse-capture

# View logs
journalctl -u timelapse-capture -f
```

### Web UI

Access the web interface at `http://<pi-ip>:8080`. Three tabs are available:

- **Timeline** -- Scrollable horizontal filmstrip of captured images with keyboard navigation (arrow keys, Home/End) and a date picker for jumping to specific days
- **Latest Image** -- Auto-refreshing view of the most recent capture
- **Control** -- Start/stop the capture daemon and view system status. Requires PAM authentication (Pi user credentials)

```bash
sudo systemctl start timelapse-web
journalctl -u timelapse-web -f
```

### Timelapse Generation

Generate videos from captured images using the `generate` subcommand:

```bash
# Basic: one week starting Feb 1, default 2-minute video
python -m timelapse generate --start 2026-02-01 --range 1w

# Custom duration, specific end date
python -m timelapse generate --start 2026-02-01 --end 2026-02-14 --duration 90s

# Dry run: see what would happen without encoding
python -m timelapse generate --start 2026-02-01 --range 7d --dry-run

# Use thumbnails for quick preview
python -m timelapse generate --start 2026-02-01 --range 1w --thumbnails

# Custom output path, resolution, and every 3rd image
python -m timelapse generate --start 2026-02-01 --range 1w \
  --output my-timelapse.mp4 --resolution 1280x720 --every 3

# Use images from a different directory
python -m timelapse generate --start 2026-02-01 --range 1w \
  --images /mnt/usb/timelapse-images
```

**Generate flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--start DATE` | *(required)* | Start date (YYYY-MM-DD) |
| `--end DATE` | | End date (mutually exclusive with `--range`) |
| `--range RANGE` | | Relative range from start (e.g. `7d`, `2w`, `1m`) |
| `--duration DUR` | `2m` | Target video duration (e.g. `90s`, `2m`, `1h30m`) |
| `--images PATH` | from config | Override image directory |
| `--output PATH` | auto-generated | Output video file path |
| `--thumbnails` | off | Use thumbnail images for quick preview |
| `--every N` | `1` | Use every Nth image |
| `--sort ORDER` | `filename` | Sort order: `filename`, `mtime`, `random` |
| `--resolution WxH` | source | Output resolution (e.g. `1920x1080`) |
| `--codec CODEC` | `libx264` | FFmpeg video codec |
| `--dry-run` | off | Show plan without encoding |
| `--summary-only` | off | Suppress progress bar |
| `--verbose` | off | Show FFmpeg output |
| `--silent` | off | Suppress gap warnings |

**Backfill thumbnails** for existing images:

```bash
python -m timelapse generate-thumbnails
```

## Storage

Images are stored in a date-based directory structure:

```
~/timelapse-images/
  2026/
    02/
      01/
        120000.jpg
        120100.jpg
        thumbs/
          120000.jpg
          120100.jpg
      02/
        ...
```

Disk management is handled automatically:

- **Warning threshold** (default 85%) -- logs a warning when disk usage exceeds this level; shown in the web UI
- **Stop threshold** (default 90%) -- the daemon refuses to capture when disk usage exceeds this level
- **Auto-cleanup** (off by default) -- when enabled, deletes the oldest full day directories beyond the retention period

## Systemd Services

Two service units are provided:

### timelapse-capture.service

Runs the capture daemon as the `pi` user in the `video` group (for camera access). Waits for NTP time sync before starting.

```bash
sudo systemctl enable timelapse-capture   # start on boot
sudo systemctl start timelapse-capture    # start now
sudo systemctl stop timelapse-capture     # stop
sudo systemctl reload timelapse-capture   # reload config (SIGHUP)
journalctl -u timelapse-capture -f        # follow logs
```

Resource limits: 256M memory, 50% CPU.

### timelapse-web.service

Runs the Flask web UI on port 8080. Starts after the network and capture daemon.

```bash
sudo systemctl enable timelapse-web
sudo systemctl start timelapse-web
sudo systemctl stop timelapse-web
journalctl -u timelapse-web -f
```

Resource limits: 128M memory, 25% CPU.

## Development

The project uses lazy imports for hardware-specific libraries (`picamera2`, `cv2`), so you can run most of the codebase on any machine without Pi hardware.

To set up a development environment without the setup script:

```bash
python3 -m venv venv
source venv/bin/activate
pip install pyyaml flask pillow python-pam flask-httpauth
```

Run the daemon or web UI directly:

```bash
python -m timelapse --config config/timelapse.yml
python -m flask --app timelapse.web run --host 0.0.0.0 --port 8080
```

## License

[MIT](LICENSE)

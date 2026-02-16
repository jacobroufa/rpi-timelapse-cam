# Technology Stack

**Project:** RPi Timelapse Cam
**Researched:** 2026-02-16
**Overall confidence:** MEDIUM (training data only -- web search and Context7 were unavailable; versions and current status should be verified against PyPI/official docs before implementation)

## Language Decision: Python

**Recommendation:** Python 3.11+ (whatever ships with Raspberry Pi OS Bookworm)
**Confidence:** HIGH

**Why Python:**
- `picamera2` (the official Raspberry Pi camera library) is Python-only -- there is no serious alternative
- v4l2 tooling (`v4l2-ctl`, `fswebcam`, `opencv-python`) all have mature Python bindings
- Flask/FastAPI ecosystem is the natural fit for a small local web server
- Shell scripts for FFmpeg wrapping are an option, but Python provides better argument parsing, error handling, and consistency with the rest of the codebase
- The Pi community overwhelmingly uses Python for camera projects; documentation and examples are abundant

**Why NOT Node.js/Go/Rust:**
- No first-class `libcamera` bindings outside Python
- Node.js adds a heavier runtime for no benefit on a resource-constrained Pi
- Go/Rust would require FFI to libcamera, adding build complexity on ARM

## Recommended Stack

### Camera Capture

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **picamera2** | 0.3.x+ | Pi Camera Module capture via libcamera | Official Raspberry Pi Foundation library. Replaced the deprecated `picamera`. Only supported way to use Pi Camera Modules on Bookworm. Pre-installed on Raspberry Pi OS. | HIGH |
| **opencv-python-headless** | 4.9+ | USB webcam capture via v4l2 | `cv2.VideoCapture(0)` is the standard cross-platform way to grab frames from USB webcams. The `-headless` variant skips GUI dependencies (no X11/Qt needed on a headless Pi). | HIGH |
| **libcamera** (system) | OS-provided | Underlying camera framework | Ships with Raspberry Pi OS. picamera2 is its Python frontend. Do NOT install via pip -- use the system package. | HIGH |

**Architecture note:** The capture daemon should use a camera abstraction layer. At init, detect which camera is present (Pi Camera via `picamera2`, USB webcam via `opencv-python`) and instantiate the appropriate backend. Both backends expose a single `capture_image() -> Path` method.

### Web Server

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Flask** | 3.x | Web server for UI and API | Minimal, well-documented, low overhead. Ideal for serving a few pages on a local network. FastAPI's async benefits are unnecessary for this workload (one user, local network, simple endpoints). | HIGH |
| **Jinja2** | 3.x (bundled with Flask) | HTML templating | Ships with Flask. Server-side rendering is the right call -- no need for a JS framework for 2 tabs. | HIGH |

**Why NOT FastAPI:** FastAPI is excellent for async API-heavy services, but this project serves a simple 2-tab UI to one user on a local network. Flask's simplicity, smaller dependency tree, and synchronous model are advantages here. FastAPI would add `uvicorn`, `starlette`, `pydantic`, and `anyio` as transitive dependencies for no practical benefit.

**Why NOT a JS frontend framework (React/Vue/Svelte):** Two tabs with an image gallery and a refreshing image do not justify a build toolchain, node_modules, or client-side routing. Vanilla HTML/CSS/JS with Jinja2 templates keeps the stack simple and the Pi's storage/build burden zero.

### Frontend (In-Browser)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Vanilla HTML/CSS/JS** | N/A | Web UI | Two tabs. One scrolls images horizontally, one auto-refreshes an image. This is 50-100 lines of JS. No framework needed. | HIGH |
| **htmx** (optional) | 2.x | Progressive enhancement | If the live view auto-refresh or image loading benefits from server-driven partial updates, htmx is a single 14KB script tag. No build step. Consider only if vanilla JS feels clunky. | MEDIUM |

**Anti-recommendation:** Do NOT use Tailwind CSS (requires a build step and node toolchain). Use a small CSS file or a classless CSS framework like Pico CSS (~10KB, no build step) for clean default styling.

### Timelapse Generation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **FFmpeg** (system) | OS-provided | Timelapse video assembly | The industry standard. Available via `apt install ffmpeg` on Pi OS and pre-installed on most Linux/macOS systems. | HIGH |
| **Python subprocess** | stdlib | FFmpeg invocation | Use `subprocess.run()` to call FFmpeg. No wrapper library needed -- FFmpeg's CLI is the stable interface. | HIGH |

**Why NOT `ffmpeg-python` or `moviepy`:** These are Python wrappers around FFmpeg's CLI. They add dependencies without adding value for a straightforward `ffmpeg -framerate X -i img_%05d.jpg -c:v libx264 output.mp4` invocation. Direct subprocess call is more transparent and debuggable.

### Process Management

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **systemd** | OS-provided | Daemon management | The capture daemon and web server should run as systemd services. This provides auto-restart on crash, boot-time startup, and standard logging via `journalctl`. Every Pi runs systemd. | HIGH |

**Why NOT supervisor/pm2/docker:** systemd is already running on the Pi. Adding another process manager increases complexity. Docker on Pi adds significant overhead (storage, memory, startup time) for no benefit in a single-purpose appliance.

### Storage & Configuration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **YAML config** (via PyYAML) | 6.x | Configuration file format | Human-readable, easy to edit over SSH. Better than JSON (supports comments) and simpler than TOML for this use case. | MEDIUM |
| **pathlib** | stdlib | File path management | Modern Python path handling. Use throughout for cross-platform safety. | HIGH |
| **shutil.disk_usage()** | stdlib | Disk space monitoring | Built-in, zero dependencies. Returns total/used/free for any path. | HIGH |
| **SQLite** (optional) | stdlib | Image metadata index | Only if you need to query images by date range efficiently. For v1, the filesystem (date-organized directories) is sufficient. Reconsider if browsing thousands of images gets slow. | LOW -- defer |

**Image storage structure:**
```
~/timelapse/
  captures/
    2026/
      02/
        16/
          20260216_143000.jpg
          20260216_143030.jpg
  timelapses/
    2026-02-09_to_2026-02-16.mp4
```

**Why date-organized directories:** Enables efficient browsing by date in the web UI, trivial cleanup by age, and natural FFmpeg glob input. Flat directories with 100K+ files become slow to list.

### Scheduling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **`time.sleep()` in a loop** | stdlib | Capture interval timing | For a simple "capture every N seconds" daemon, a sleep loop is correct. Do NOT use `cron` -- it cannot reliably schedule sub-minute intervals and adds unnecessary indirection. | HIGH |
| **`threading.Timer`** (alternative) | stdlib | Drift-corrected timing | If capture takes variable time and you want consistent intervals (e.g., exactly every 30s wall-clock), use a timer that accounts for capture duration. | MEDIUM |

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **pytest** | 8.x | Test runner | Python standard. | HIGH |
| **pytest-cov** | 5.x | Coverage reporting | Lightweight coverage integration. | MEDIUM |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Camera (Pi) | picamera2 | `libcamera-still` via subprocess | Subprocess calls work but lose fine-grained control (exposure, white balance). picamera2 is the official Python API. |
| Camera (USB) | opencv-python-headless | `fswebcam` via subprocess | fswebcam works but is unmaintained (last release ~2014). OpenCV is actively maintained and more capable. |
| Web framework | Flask | FastAPI | Unnecessary async complexity, larger dependency tree, no practical benefit for 1-user local UI. |
| Frontend | Vanilla JS | React/Vue/Svelte | Build toolchain overhead for 2 tabs is absurd. |
| Config format | YAML | TOML | TOML is fine too (and in stdlib via `tomllib` in 3.11+). YAML chosen for broader Pi community familiarity. |
| Process mgmt | systemd | Docker | Docker on Pi wastes 200MB+ RAM, adds storage overhead, and complicates camera device passthrough. |
| FFmpeg wrapper | subprocess.run() | ffmpeg-python | Extra dependency that just generates the same CLI command. |
| Scheduling | sleep loop | cron | Cron's minimum interval is 1 minute. 30-second captures need sub-minute scheduling. |
| Storage | Filesystem (date dirs) | SQLite | Premature optimization. Filesystem is queryable, browsable, and FFmpeg-compatible. |

## System Dependencies (installed via apt)

```bash
# Camera support (usually pre-installed on Raspberry Pi OS)
sudo apt install -y libcamera-apps python3-picamera2

# FFmpeg for timelapse generation
sudo apt install -y ffmpeg

# OpenCV system dependencies (for USB webcam support)
sudo apt install -y python3-opencv
```

## Python Dependencies (installed via pip in venv)

```bash
# Create venv that can access system packages (needed for picamera2, cv2)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Web server
pip install flask

# Configuration
pip install pyyaml

# Development
pip install pytest pytest-cov
```

**Critical note on `--system-site-packages`:** The `picamera2` and `opencv-python` packages on Raspberry Pi OS are installed as system packages (via `apt`) because they have compiled C extensions linked to system libraries. The venv MUST use `--system-site-packages` to access them.

## Key Technical Notes

### picamera2 Gotchas
- picamera2 must be imported AFTER any display environment is configured. On a headless Pi, this is fine.
- `capture_file()` is the simplest method for still captures.
- picamera2 holds the camera open. The daemon should keep a single instance alive rather than creating/destroying per capture (startup is slow, ~1-2 seconds).

### OpenCV USB Webcam Gotchas
- `cv2.VideoCapture(0)` may grab the wrong device if multiple cameras exist. Support a configurable device index.
- USB webcams need a moment to adjust auto-exposure. Add a brief warm-up delay (~0.5s) after opening.
- Always call `cap.release()` when switching cameras or shutting down.

### FFmpeg Timelapse Command
- Core command: `ffmpeg -framerate <fps> -pattern_type glob -i 'captures/**/*.jpg' -c:v libx264 -pix_fmt yuv420p output.mp4`
- Calculate framerate: `fps = total_images / desired_output_seconds`
- `-pix_fmt yuv420p` is required for compatibility with most video players

### Storage Arithmetic
- A typical Pi Camera v2 JPEG at 1920x1080: ~500KB-1MB
- At 30-second intervals: 2 captures/minute = 120/hour = 2,880/day
- At 750KB average: **~2.1 GB/day**, **~14.7 GB/week**
- A 32GB SD card fills in ~2 weeks without cleanup
- Auto-cleanup and disk warnings are essential

## Sources

- Raspberry Pi picamera2 documentation (training data, MEDIUM confidence)
- Flask documentation (training data, HIGH confidence)
- OpenCV Python documentation (training data, HIGH confidence)
- FFmpeg documentation (training data, HIGH confidence)
- Raspberry Pi OS Bookworm release notes (training data, MEDIUM confidence)

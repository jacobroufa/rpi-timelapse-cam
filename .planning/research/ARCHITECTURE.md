# Architecture Patterns

**Domain:** Raspberry Pi timelapse camera toolkit
**Researched:** 2026-02-16
**Confidence:** MEDIUM overall -- mature, stable patterns but specific library versions should be verified during implementation.

## Recommended Architecture

Three independent processes sharing a filesystem convention:

```
                                    [Filesystem]
                                   /images/YYYY-MM-DD/
                                   HH-MM-SS.jpg
                                        |
            +-----------+               |               +----------------+
            |  Capture  |---writes----->|<---reads------|  Web Server    |
            |  Daemon   |               |               |  (Timeline +   |
            +-----------+               |               |   Live View)   |
                                        |               +----------------+
                                        |
                                        |               +----------------+
                                        +<---reads------| FFmpeg Script  |
                                                        | (Standalone)   |
                                                        +----------------+
```

**Key architectural principle:** The filesystem IS the integration layer. No database, no message queue, no IPC. Images on disk are the shared state. Each component reads/writes files independently.

### Component Boundaries

| Component | Responsibility | Communicates With | Process Model |
|-----------|---------------|-------------------|---------------|
| Capture Daemon | Take photos at intervals, write to organized directory structure, manage disk space | Filesystem (write), Camera hardware (libcamera/v4l2) | Long-running daemon (systemd service) |
| Web Server | Serve timeline UI, serve live view, report disk status | Filesystem (read), Camera hardware (read-only for live view) | Long-running daemon (systemd service) |
| FFmpeg Script | Compile images into timelapse video | Filesystem (read), FFmpeg binary (exec) | One-shot CLI invocation |
| Camera Abstraction | Unified interface over libcamera and v4l2 | Camera hardware | Library, not a process |
| Storage Manager | Monitor disk space, enforce cleanup policies, emit warnings | Filesystem (read/delete) | Library used by Capture Daemon; status read by Web Server |

### Data Flow

**Capture Flow (primary data path):**
```
Camera Hardware
    |
    v
Camera Abstraction Layer (picamera2 / opencv)
    |
    v
Capture Daemon (interval timer + retry logic)
    |
    v
Filesystem: /images/2026/02/16/14-30-00.jpg
    |
    v
Storage Manager (check disk, cleanup old if policy enabled)
```

**Timeline View Flow:**
```
Browser (GET /api/images?date=2026-02-16)
    |
    v
Web Server (scan filesystem, return image list)
    |
    v
Browser renders horizontal scrollable timeline
    |
    v
Browser (GET /images/2026/02/16/14-30-00.jpg)
    |
    v
Web Server serves static file
```

**Live View Flow:**
```
Browser (polling GET /api/live every N seconds)
    |
    v
Web Server captures a single still from camera
    |
    v
Returns JPEG bytes (ephemeral -- NOT saved to disk)
    |
    v
Browser replaces <img> src with new blob/data URL
```

**Timelapse Generation Flow:**
```
User runs CLI: ./timelapse.py --start 2026-02-09 --end 2026-02-16 --duration 120
    |
    v
Script scans /images/ for date range, builds file list
    |
    v
Calculates frame rate: (total_images / output_duration_seconds)
    |
    v
Invokes FFmpeg with image sequence input + calculated fps
    |
    v
Outputs: timelapse-2026-02-09-to-2026-02-16.mp4
```

## Component Deep Dives

### 1. Camera Abstraction Layer

Pi Camera and USB webcams use fundamentally different capture stacks.

**Pi Camera (libcamera):**
- Modern Raspberry Pi OS uses `libcamera` exclusively (raspistill is deprecated)
- CLI tool: `rpicam-still` (renamed from `libcamera-still` in Bookworm)
- Python: `picamera2` library (wraps libcamera natively)

**USB Webcam (v4l2):**
- Standard Linux video interface
- Python: `cv2.VideoCapture()` from OpenCV
- CLI alternative: `fswebcam` (lightweight, purpose-built)

**Abstraction approach:**
```
interface CameraBackend:
    capture(output_path: str) -> Result
    check_available() -> bool
    get_live_frame() -> bytes
```

**Live view consideration:** The web server needs to capture a frame on-demand. This must NOT conflict with the capture daemon's camera access. Use a file lock (`/tmp/camera.lock`) to prevent simultaneous access. Camera hardware generally does not support simultaneous access.

### 2. Capture Daemon

**Process model:** systemd service with simple sleep loop (not cron) because sub-minute intervals are awkward with cron.

**Core loop:**
```
while running:
    acquire camera lock
    capture image to /images/YYYY/MM/DD/HH-MM-SS.jpg
    release camera lock
    check disk space
    if cleanup_enabled and disk_usage > threshold:
        delete oldest images
    sleep(interval)
```

**Directory structure:** `YYYY/MM/DD/HH-MM-SS.jpg` -- date-based hierarchy. Critical because:
- FFmpeg script needs chronologically sorted file lists
- Web timeline needs to query by date
- Cleanup deletes by age (oldest directories first)
- Human-readable when browsing via SSH

**Error handling:** Log failures but keep running. Track consecutive failures. Never crash the loop on a single capture failure.

### 3. Web Server

**Endpoints:**
```
GET /                        -> SPA HTML (tabs: Timeline | Live View)
GET /api/images              -> JSON list of available dates
GET /api/images/:date        -> JSON list of images for that date
GET /api/live                -> JPEG bytes (ephemeral capture or latest image)
GET /api/status              -> JSON disk space, capture stats, camera status
GET /images/...              -> Static file serving for captured images
```

**Live view implementation:** Two approaches:
- **Approach A (simpler):** Serve the most recently captured image. "Live" is only as fresh as the capture interval (30s).
- **Approach B (true live):** Web server captures an ephemeral frame on each request. Requires camera lock coordination.

Recommendation: **Start with Approach A**, add Approach B if needed.

### 4. FFmpeg Timelapse Script

**Design:** Standalone Python script. Takes a date range and output duration, calculates correct FFmpeg parameters.

**Key calculation:**
```
total_images = count files in date range
input_fps = total_images / output_duration_seconds

ffmpeg -framerate {input_fps} -pattern_type glob -i '/images/.../*.jpg' \
    -c:v libx264 -pix_fmt yuv420p output.mp4
```

### 5. Storage Manager

**Not a separate process** -- a shared library/module used by:
- Capture daemon: checks disk after each capture, runs cleanup if enabled
- Web server: reads disk status for the status API endpoint

**Cleanup strategy:** Delete oldest date directories first (entire days, not individual images).

## Patterns to Follow

### Pattern 1: Filesystem as Database
Use the directory structure as the queryable data store. No SQLite, no JSON manifest. Eliminates sync bugs, works with standard tools, survives crashes.

### Pattern 2: Camera Lock File
Simple file-based mutex preventing simultaneous camera access between daemon and web server live view.

### Pattern 3: Graceful Degradation
Each component handles the absence of others. FFmpeg script works without daemon running. Web server shows existing images even if daemon stops.

### Pattern 4: Configuration File
Single YAML configuration file read by all components:
```yaml
capture:
  interval: 30
  camera: auto       # auto | picamera | usb
  resolution: 1920x1080
  output_dir: /home/pi/timelapse/images

storage:
  warn_threshold: 15  # percent free
  cleanup_enabled: false
  cleanup_max_age: 30  # days

web:
  port: 8080
  host: 0.0.0.0

timelapse:
  default_duration: 120  # seconds output
  default_period: 7      # days input
  output_dir: /home/pi/timelapse/videos
```

### Pattern 5: Systemd Service Units
Both daemon and web server run as systemd services with auto-restart, proper logging, and resource limits.

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Instead |
|-------------|---------|---------|
| Database for image metadata | Adds complexity, sync bugs, dependency | Filesystem structure + timestamped filenames |
| MJPEG streaming for live view | CPU-intensive, holds camera open permanently | Auto-refreshing still image |
| SPA framework for web UI | Build step, node_modules, overkill for 2 tabs | Vanilla HTML/CSS/JS |
| Cron for sub-minute capture | 1-minute minimum resolution, no state | Long-running daemon with sleep loop |
| Monolithic single process | Capture bug kills web server and vice versa | Three separate components |

## Suggested Build Order

```
Phase 1: Camera Abstraction + Capture Daemon
    |     (no dependencies -- can run standalone)
    |     Produces: images on disk
    |
Phase 2: Web Server + Timeline UI
    |     (depends on: images existing on disk)
    |
Phase 3: FFmpeg Timelapse Script + Storage Management
    |     (depends on: images existing on disk)
    |     Could parallel with Phase 2
```

## Scalability Considerations

| Concern | Day 1 (100s of images) | Month 1 (50K images) | Month 6 (300K images) |
|---------|----------------------|---------------------|----------------------|
| Disk space | No concern | ~5-15 GB | 30-100 GB, need USB storage or cleanup |
| Directory listing | Instant | Fast (2880 files/day) | Fast per-day, paginate API |
| Timeline UI | Trivial | Must lazy-load. Do NOT load 2880 thumbnails at once. | Date picker + lazy load |
| FFmpeg input | Trivial | May need concat demuxer for large file lists | Definitely need concat demuxer |
| SD card wear | No concern | Moderate write load | Consider USB storage |

## Sources

- Raspberry Pi camera documentation (MEDIUM confidence -- based on training data)
- fswebcam as standard USB webcam capture tool (HIGH confidence)
- FFmpeg image sequence patterns (HIGH confidence)
- systemd service patterns for Pi daemons (HIGH confidence)
- Filesystem-as-database pattern for image timelapse projects (MEDIUM confidence)

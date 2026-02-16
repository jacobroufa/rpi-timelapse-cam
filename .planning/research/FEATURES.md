# Feature Landscape

**Domain:** Raspberry Pi timelapse camera toolkit
**Researched:** 2026-02-16
**Confidence:** MEDIUM (training data only -- web search and fetch tools unavailable)

## Ecosystem Context

The Raspberry Pi timelapse camera space is mature and well-documented. Established projects include:

- **RPi_Cam_Web_Interface** -- full-featured web UI for Pi Camera with timelapse, motion detection, and camera controls
- **motionEye / motionEyeOS** -- surveillance-oriented multi-camera system with timelapse and motion detection
- **allsky** -- all-sky camera project with timelapse, overlays, and keograms
- **picamera2** -- official Python library for libcamera on Pi, replacing legacy picamera

This project targets a specific niche: a lightweight, self-contained toolkit that does interval capture, browsing, and timelapse assembly without the bloat of surveillance-oriented platforms.

## Table Stakes

Features users expect. Missing = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Configurable capture interval** | Core function. Every timelapse tool does this. | Low | Default 30s. Must support range from ~5s to hours. |
| **Pi Camera support (libcamera)** | Pi Camera Module is the default camera for Raspberry Pi. | Medium | picamera2 Python bindings or libcamera-still/rpicam-still CLI. |
| **USB webcam support (v4l2)** | Many users have USB webcams, not Pi Camera Modules. | Medium | OpenCV VideoCapture or fswebcam. Device discovery needed. |
| **Live camera preview** | Users need to aim/focus the camera and verify it's working. | Low | Auto-refreshing still image. Lighter than MJPEG streaming. |
| **Image timeline/browser** | Users need to review captures without SSH. | Medium | Horizontal scrollable timeline. Must handle thousands of images (lazy loading, thumbnails). |
| **Timelapse video generation** | The whole point of capturing interval photos. | Medium | FFmpeg is the standard tool. Standalone script is correct. |
| **Timestamped filenames** | Users need to correlate images to real time. | Low | ISO 8601 sortable format. Critical for FFmpeg frame ordering. |
| **Disk space monitoring** | SD cards fill up fast at 30s intervals. | Low | Warn at configurable threshold (15% default). Display on web UI. |
| **Auto-cleanup of old images** | Without this, the SD card fills and capture stops. | Low | Delete images older than N days. Opt-in (off by default). |
| **Capture start/stop control** | Users need to pause capture without killing the daemon. | Low | Web UI toggle or signal-based control. |
| **Systemd service integration** | Daemon must survive reboots. Headless operation expected. | Low | systemd unit file. Auto-start on boot. |
| **Basic configuration file** | Users need to change settings without editing code. | Low | Single config file (YAML). |

## Differentiators

Features that set this product apart from existing tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Unified three-part toolkit** | Most solutions are either capture-only scripts or heavy surveillance platforms. A lightweight toolkit is a clear niche. | N/A (architectural) | Core differentiator. |
| **Camera source abstraction** | Seamless switching between Pi Camera and USB webcam via config. Most tools support one or the other. | Medium | Wraps libcamera and v4l2 behind common interface. |
| **Smart timelapse duration mapping** | "Compress 1 week into 2 minutes" is more intuitive than FFmpeg framerate math. | Medium | Much better UX than raw FFmpeg flags. |
| **Thumbnail generation for timeline** | Fast browsing of thousands of images without loading full-resolution files. | Medium | Generate thumbnails at capture time (200-300px wide). |
| **Date range filtering in timeline** | Jump to a specific day or range. Critical once capture runs for weeks. | Medium | Date picker or calendar widget. |
| **Capture health indicator** | Show on web UI whether the daemon is running, last capture time. | Low | Simple heartbeat check. |
| **Configurable JPEG quality** | Trade storage space for image quality. | Low | JPEG quality 70-95 range. |
| **Storage location configuration** | Support capture to USB drive or NAS mount, not just SD card. | Low | Configurable output directory. |
| **Timelapse preview in web UI** | Trigger and view timelapse generation from the web UI. | High | Background job management, progress reporting. Nice-to-have. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **MJPEG live streaming** | CPU-intensive on Pi, overkill for aiming a camera. | Auto-refreshing still image at 1-3 second intervals. |
| **Motion detection** | Turns a timelapse tool into a surveillance system. motionEye does this far better. | Fixed interval capture only. |
| **Cloud sync / remote access** | Adds auth, networking complexity, third-party deps. | Local network only. |
| **Multi-camera simultaneous capture** | Doubles complexity everywhere. Rare use case. | One camera at a time, switchable via config. |
| **Mobile app** | Massive scope expansion. | Responsive web UI works on mobile browsers. |
| **Video recording / continuous capture** | Completely different requirements. | Still images only. Timelapse from stills. |
| **User authentication** | Local network, personal use. Near-zero security benefit. | No auth for v1. |
| **Database for image metadata** | Adds dependency and failure mode. | Filesystem-based. Timestamped filenames. |
| **Plugin / extension system** | Premature abstraction. | Well-structured code that's easy to modify. |

## Feature Dependencies

```
Configurable capture interval
  --> Timestamped filenames (naming determines sort order)
  --> Disk space monitoring (fast intervals fill disk)
  --> Auto-cleanup (long-running capture needs space management)

Camera source abstraction
  --> Pi Camera support (libcamera backend)
  --> USB webcam support (v4l2 backend)

Live camera preview
  --> Camera source abstraction (must work with both camera types)

Image timeline browser
  --> Timestamped filenames (browsing requires sorted, parseable names)
  --> Thumbnail generation (performance requires thumbnails)
  --> Date range filtering (usability at scale)

Timelapse video generation
  --> Timestamped filenames (FFmpeg needs ordered frames)
  --> Smart duration mapping (UX layer on top of FFmpeg)

Web UI
  --> Live camera preview (tab 1)
  --> Image timeline browser (tab 2)
  --> Capture start/stop control (daemon management)
  --> Capture health indicator (status display)
  --> Disk space monitoring (warning display)

Systemd service
  --> Capture daemon (what gets managed as a service)
  --> Basic configuration file (service reads config on start)
```

## MVP Recommendation

**Phase 1 -- Capture foundation (build first, everything depends on it):**
1. Camera source abstraction (Pi Camera + USB webcam)
2. Configurable capture interval with timestamped filenames
3. Basic configuration file
4. Systemd service integration
5. Disk space monitoring (log warnings)

**Phase 2 -- Web UI (makes the tool usable without SSH):**
1. Live camera preview (auto-refreshing still)
2. Image timeline browser with thumbnails
3. Capture start/stop control
4. Capture health indicator
5. Disk space warning display

**Phase 3 -- Timelapse generation (the payoff):**
1. FFmpeg timelapse script with smart duration mapping
2. Auto-cleanup of old images

## Sources

- Training data knowledge of RPi_Cam_Web_Interface, motionEye/motionEyeOS, allsky, picamera2 ecosystem (MEDIUM confidence)
- Project context from `.planning/PROJECT.md` (HIGH confidence)
- General Linux camera tooling knowledge (HIGH confidence)

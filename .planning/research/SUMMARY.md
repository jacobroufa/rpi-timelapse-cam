# Project Research Summary

**Project:** RPi Timelapse Cam
**Domain:** Raspberry Pi timelapse camera toolkit
**Researched:** 2026-02-16
**Confidence:** MEDIUM

## Executive Summary

This project targets a specific niche in the mature Raspberry Pi camera ecosystem: a lightweight, self-contained timelapse camera toolkit consisting of three independent components (capture daemon, web UI, FFmpeg script) that communicate via a filesystem convention rather than a database or messaging system. The recommended approach prioritizes simplicity and resource efficiency suitable for headless Pi operation, using Python for all components due to the `picamera2` library's exclusive Python support and the strong Pi community ecosystem around Python-based camera projects.

The core technical recommendation is to build three independent processes: a capture daemon (systemd service) that writes timestamped images to date-organized directories, a Flask-based web server for timeline browsing and live preview, and a standalone FFmpeg script for timelapse generation. The filesystem acts as the integration layer, eliminating the need for databases or IPC mechanisms. Critical technology choices include `picamera2` for Pi Camera support, `opencv-python-headless` for USB webcam support, Flask for the web server (avoiding FastAPI's unnecessary async complexity), and vanilla HTML/CSS/JS (no frontend framework for two simple tabs).

The primary risks center on SD card wear from continuous writes, disk-full conditions that can crash the entire system, and the complexity of supporting two fundamentally different camera APIs (libcamera vs v4l2). Mitigation strategies must be built into Phase 1: use external USB storage or high-endurance SD cards, implement aggressive disk space monitoring with automatic cleanup policies, and create a camera abstraction layer that unifies the Pi Camera and USB webcam interfaces. These are not nice-to-haves but foundational requirements that prevent data loss and system failure.

## Key Findings

### Recommended Stack

Python 3.11+ is the only viable choice due to `picamera2` being Python-exclusive. The stack emphasizes minimal dependencies, leveraging system packages where possible, and avoiding build toolchains on the Pi. Flask provides the web server (simpler and lighter than FastAPI for this single-user, local-network use case), with vanilla HTML/CSS/JS for the frontend (no React/Vue/Svelte — the two-tab UI doesn't justify a build pipeline).

**Core technologies:**
- **picamera2** (Python): Official library for Pi Camera Module via libcamera — the only supported way to use Pi Camera on modern Raspberry Pi OS
- **opencv-python-headless** (Python): USB webcam capture via v4l2, cross-platform, actively maintained
- **Flask 3.x**: Minimal web framework for serving the 2-tab UI and API — synchronous model is an advantage here, not a limitation
- **FFmpeg** (system): Industry-standard timelapse assembly via direct subprocess calls (no wrapper library needed)
- **systemd**: Process management for daemon and web server (already present on Pi, no Docker/supervisor needed)
- **YAML config** (PyYAML): Human-readable configuration file editable over SSH

**Critical version notes:**
- Must use Python 3.11+ (ships with Raspberry Pi OS Bookworm)
- Requires Raspberry Pi OS Bookworm (2023+) for modern libcamera stack
- System packages (`picamera2`, `opencv-python`, `ffmpeg`) installed via `apt`, not pip
- Venv must use `--system-site-packages` to access system-installed camera libraries

**Why NOT alternatives:**
- Node.js/Go/Rust: No first-class libcamera bindings, adds build complexity on ARM
- FastAPI: Unnecessary async overhead, larger dependency tree for single-user local UI
- React/Vue/Svelte: Build toolchain absurdity for 50 lines of vanilla JS
- Docker: 200MB+ RAM overhead, complicates camera device passthrough
- SQLite: Premature optimization — filesystem is queryable and FFmpeg-compatible

### Expected Features

The feature landscape divides cleanly into table stakes (expected by users), differentiators (competitive advantages), and anti-features (scope creep to avoid).

**Must have (table stakes):**
- Configurable capture interval (default 30s, range 5s to hours) — core function
- Pi Camera and USB webcam support via unified abstraction — users have both
- Live camera preview (auto-refreshing still, not MJPEG) — essential for aiming
- Image timeline browser with horizontal scrolling — reviewing captures without SSH
- Timelapse video generation via FFmpeg — the entire point of interval capture
- Disk space monitoring with warnings — SD cards fill in ~2 weeks at 30s intervals
- Auto-cleanup of old images (opt-in) — prevents disk-full crash
- Capture start/stop control — pause without killing daemon
- Systemd service integration — headless operation, survive reboots
- Timestamped filenames in ISO 8601 format — critical for FFmpeg ordering

**Should have (differentiators):**
- Camera source abstraction (seamless Pi Camera ↔ USB switch) — most tools support one or other
- Smart timelapse duration mapping ("compress 1 week into 2 minutes") — better UX than raw FFmpeg math
- Thumbnail generation for timeline (200-300px) — fast browsing of thousands of images
- Date range filtering in timeline — jump to specific day once weeks of captures exist
- Capture health indicator (daemon status, last capture time) — diagnostics without SSH
- Configurable JPEG quality (70-95 range) — storage vs quality tradeoff
- Storage location configuration (USB drive, NAS mount) — avoid SD card wear

**Defer (v2+):**
- MJPEG live streaming (CPU-intensive, unnecessary for aiming camera)
- Motion detection (turns timelapse tool into surveillance system)
- Cloud sync / remote access (auth and networking complexity)
- Multi-camera simultaneous capture (doubles complexity everywhere)
- Mobile app (responsive web UI sufficient)
- User authentication (local network, personal use)
- Plugin / extension system (premature abstraction)

**Feature dependency insights:**
- Timeline browser depends on timestamped filenames and thumbnail generation
- FFmpeg script depends on chronologically ordered, date-organized files
- Disk monitoring must exist before capture starts (not a v2 feature)
- Camera abstraction must support both live view and interval capture

### Architecture Approach

Three independent processes sharing a filesystem convention: capture daemon writes images to date-organized directories (`YYYY/MM/DD/HH-MM-SS.jpg`), web server reads existing images and serves timeline UI, FFmpeg script reads images and generates video. The filesystem IS the integration layer — no database, no message queue, no IPC. This architectural choice enables graceful degradation (each component handles absence of others), eliminates sync bugs, and works with standard Unix tools.

**Major components:**
1. **Capture Daemon** (systemd service) — Manages camera (Pi Camera or USB webcam), captures at configured intervals, writes to date-organized directories, monitors disk space, runs cleanup policies, handles camera disconnects gracefully
2. **Web Server** (Flask, systemd service) — Serves 2-tab UI (timeline browser + live view), exposes API endpoints for image listings and system status, serves static images directly from capture directories, coordinates camera access via file lock
3. **FFmpeg Script** (standalone CLI) — Scans date range for images, calculates framerate from desired output duration, invokes FFmpeg with correct parameters, runs independently of other components
4. **Camera Abstraction Layer** (shared library) — Unifies picamera2 and opencv interfaces behind common API (`capture()`, `check_available()`, `get_live_frame()`), detects available camera at startup, prevents simultaneous access conflicts
5. **Storage Manager** (shared library) — Monitors disk usage via `shutil.disk_usage()`, enforces cleanup policies (delete oldest date directories first), exposes status for web UI

**Key architectural patterns:**
- Filesystem-as-database: Directory structure is the queryable data store
- Camera lock file: Simple file-based mutex prevents simultaneous camera access
- Date-based hierarchy: `YYYY/MM/DD/` enables efficient querying, FFmpeg ordering, and age-based cleanup
- Graceful degradation: Components work independently, handle absence of others
- Configuration file: Single YAML config read by all components

**Build order recommendation:**
1. Phase 1: Camera abstraction + capture daemon (no dependencies, runs standalone)
2. Phase 2: Web server + timeline UI (depends on images existing on disk)
3. Phase 3: FFmpeg script + storage management (depends on images existing, can parallel with Phase 2)

### Critical Pitfalls

The research identified three critical pitfalls that cause data loss or system failure if not addressed in Phase 1, plus two high-impact pitfalls for subsequent phases.

1. **SD Card Wear from Continuous Writes** — Writing a JPEG every 30 seconds (2,880 writes/day) causes premature SD card failure. Consumer cards lack wear leveling for server workloads. After weeks/months, filesystem corruption destroys all captures. **Prevention:** Use external USB storage for images, high-endurance SD cards for OS, mount `/tmp` and `/var/log` as tmpfs, disable swap. **Phase 1 requirement.**

2. **Disk Full Condition Crashes Entire System** — At 2.1 GB/day, a 32GB SD card fills in ~10-20 days. When storage hits 100%, OS logging fails, services crash, Pi becomes unresponsive. **Prevention:** Implement storage management from day one (not a nice-to-have), reserve 15-20% for OS, oldest-first deletion policy, pre-capture space check before every write, expose disk usage prominently in web UI. **Phase 1 requirement.**

3. **libcamera vs Legacy raspistill API Confusion** — Many tutorials reference deprecated `raspistill`/`raspivid`. Developers copy legacy code that silently fails on modern Pi OS. The `picamera` v1 library does not work with new libcamera stack. **Prevention:** Target modern stack exclusively (`rpicam-still`/`libcamera-still` for Pi Camera, v4l2 for USB), use `picamera2` (not `picamera`) in Python, implement camera detection at startup, abstract camera interface, document minimum OS as Bookworm. **Phase 1 requirement.**

4. **Capture Process Hangs or Zombies** — Camera capture commands hang indefinitely (USB disconnect, GPU memory failure). Daemon waits forever, misses captures, zombie processes accumulate. **Prevention:** Always use timeouts on subprocess calls (15-30s max), implement watchdog for consecutive failures, use systemd `WatchdogSec`, detect USB disconnect gracefully, log every capture attempt with timing. **Phase 1 requirement.**

5. **Running Web Server as Root / Without Resource Limits** — Web server runs as root for camera access convenience. Serving full-resolution images without pagination consumes all RAM on a 512MB Pi Zero. **Prevention:** Run each service as dedicated non-root user with `video` group membership, use systemd `User=`, `MemoryMax=`, `CPUQuota=` directives, generate thumbnails for timeline (200-300px vs 500KB-2MB), paginate image listings (max 50-100 per request). **Phase 2 requirement.**

**Additional moderate pitfalls:**
- Inconsistent image naming and timezone issues (wait for NTP sync, ISO 8601 timestamps)
- FFmpeg blocks system during encoding (use `nice -n 19 ionice -c3`, never run automatically)
- Single-directory performance collapse after 50K+ files (date hierarchy essential from start)
- No graceful degradation on camera disconnect (exponential backoff, status in web UI)
- Pi Camera auto-exposure settling (keep pipeline open, 2-3s settling time)

## Implications for Roadmap

Based on combined research, the roadmap should follow a strict dependency order dictated by the filesystem-as-integration-layer architecture. Each phase must complete and produce testable artifacts before the next begins.

### Phase 1: Camera Foundation & Capture Daemon

**Rationale:** Everything depends on images existing on disk. Web UI has nothing to display without captures. FFmpeg has nothing to process. The capture daemon is the foundational component. Additionally, the three critical pitfalls (SD card wear, disk full, libcamera confusion) must all be addressed in this phase — they cannot be deferred.

**Delivers:** Working capture daemon that writes timestamped images to date-organized directories, supports both Pi Camera and USB webcams via abstraction layer, monitors disk space, runs as systemd service.

**Addresses these features:**
- Configurable capture interval (table stakes)
- Pi Camera support via libcamera/picamera2 (table stakes)
- USB webcam support via v4l2/opencv (table stakes)
- Timestamped filenames in date-organized directories (table stakes)
- Disk space monitoring with warnings (table stakes)
- Auto-cleanup of old images (table stakes)
- Systemd service integration (table stakes)
- Camera source abstraction (differentiator)

**Avoids these pitfalls:**
- SD card wear (external storage strategy, high-endurance cards)
- Disk full crash (storage manager with cleanup policies)
- libcamera API confusion (camera abstraction with modern stack)
- Capture hangs (timeouts, watchdog, graceful degradation)
- Image naming issues (ISO 8601 timestamps, date hierarchy)

**Uses from stack:**
- Python 3.11+, picamera2, opencv-python-headless, systemd, PyYAML, pathlib, shutil

**Success criteria:**
- Daemon captures from Pi Camera OR USB webcam every N seconds
- Images written to `~/timelapse/captures/YYYY/MM/DD/HHMMSS.jpg`
- Disk space checked before every capture
- Old images deleted when threshold reached (if enabled)
- Daemon survives camera disconnect (exponential backoff, logs warning)
- Systemd service auto-starts on boot, restarts on crash
- Single YAML config file controls interval, camera, storage policies

### Phase 2: Web UI & Timeline Browser

**Rationale:** With images accumulating on disk, users need a way to review captures, verify camera is working, and aim the camera without SSH access. Web UI makes the tool usable for non-technical users. This phase depends on Phase 1 producing images but is independent of FFmpeg.

**Delivers:** Flask web server with 2-tab UI (live preview + timeline browser), API endpoints for image listings and system status, thumbnail generation for fast browsing, date range filtering.

**Addresses these features:**
- Live camera preview (table stakes)
- Image timeline browser (table stakes)
- Capture start/stop control (table stakes)
- Capture health indicator (differentiator)
- Thumbnail generation for timeline (differentiator)
- Date range filtering (differentiator)

**Avoids these pitfalls:**
- Running as root / no resource limits (dedicated user, systemd limits)
- No remote diagnostics (health dashboard in web UI)
- Thermal throttling monitoring (CPU temp in status API)

**Uses from stack:**
- Flask 3.x, Jinja2, vanilla HTML/CSS/JS, systemd (separate service from daemon)

**Implements architecture component:**
- Web Server (Flask service with API endpoints and static file serving)
- Camera lock coordination (file-based mutex for live view)

**Success criteria:**
- Web UI accessible at `http://timelapse.local:8080`
- Live view tab shows auto-refreshing image (every 3s)
- Timeline tab displays horizontal scrollable image gallery with thumbnails
- Date picker allows jumping to specific date range
- Status dashboard shows disk usage, last capture time, daemon status, CPU temp
- Start/stop button controls capture daemon
- Web server runs as non-root user with video group membership
- Serves full-resolution images on click, thumbnails for scrolling

### Phase 3: Timelapse Generation & Export

**Rationale:** With weeks of images accumulated and browsable via web UI, users need to compile them into video. FFmpeg script is independent of other components and can be developed in parallel with Phase 2 if desired.

**Delivers:** Standalone Python script that takes date range and desired output duration, calculates correct FFmpeg parameters, generates timelapse video.

**Addresses these features:**
- Timelapse video generation (table stakes)
- Smart timelapse duration mapping (differentiator)

**Avoids these pitfalls:**
- FFmpeg blocks system (nice/ionice, never runs automatically)
- Incorrect framerate math (calculate frame count first, verify output duration)

**Uses from stack:**
- FFmpeg (system), subprocess.run() (no wrapper library)

**Success criteria:**
- CLI: `./timelapse.py --start 2026-02-09 --end 2026-02-16 --duration 120`
- Script scans date range, counts images, calculates input fps
- Invokes FFmpeg with correct parameters (`-framerate`, `-pix_fmt yuv420p`)
- Output video duration matches requested duration (±5%)
- Uses nice/ionice to avoid starving daemon and web server
- Logs progress, handles missing dates gracefully

### Phase Ordering Rationale

This strict sequential ordering is dictated by the filesystem-as-integration-layer architecture:

- **Phase 1 must complete first** because Phases 2 and 3 both depend on images existing on disk. The web UI has nothing to display without captures. FFmpeg has nothing to process.
- **Phase 2 and Phase 3 are independent** and could theoretically parallel, but Phase 2 delivers more user value (makes the tool usable without SSH) and should be prioritized.
- **Critical pitfalls concentrate in Phase 1** (SD card wear, disk full, libcamera confusion, capture hangs) — these cannot be deferred without risking data loss or system failure.
- **Each phase produces testable artifacts** that validate the architecture: Phase 1 = images on disk, Phase 2 = browsable web UI, Phase 3 = timelapse video.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Medium complexity. Camera abstraction layer requires understanding both libcamera (`picamera2`) and v4l2 (`opencv-python`) APIs. USB webcam device discovery and hotplug handling are non-trivial. Storage management arithmetic needs validation (how much headroom to reserve, cleanup granularity). **Recommend targeted research on camera abstraction patterns and USB webcam error handling.**
- **Phase 2:** Low complexity. Flask + vanilla JS is well-documented. Thumbnail generation is straightforward. Lazy-loading patterns for image galleries are standard. **Standard patterns, skip research-phase.**
- **Phase 3:** Low complexity. FFmpeg timelapse generation is well-documented. The framerate calculation is arithmetic. The primary challenge is testing with realistic file counts. **Standard patterns, skip research-phase.**

Phases with standard patterns (skip research-phase):
- **Phase 2:** Flask web server and image gallery UI are solved problems with abundant examples.
- **Phase 3:** FFmpeg timelapse generation has canonical documentation and examples.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Training data only (web search and Context7 unavailable). Specific library versions should be verified against PyPI/official docs before implementation. Stack choices are well-established in Pi community, but version compatibility should be confirmed. |
| Features | MEDIUM | Based on training data knowledge of RPi_Cam_Web_Interface, motionEye, allsky, and general Pi camera ecosystem. Feature categorization is solid, but user validation would strengthen confidence. |
| Architecture | MEDIUM | Filesystem-as-database and three-process design are proven patterns in Pi projects. Training data coverage is good for systemd, libcamera, and FFmpeg. Architecture is sound but unvalidated on this specific project. |
| Pitfalls | MEDIUM | Based on training data knowledge of SD card failures, disk-full crashes, and libcamera migration challenges. Community reports are consistent. Pitfall severity is well-established in Pi community, but specific manifestations should be monitored. |

**Overall confidence:** MEDIUM

The medium confidence reflects that all research was conducted via training data only — web search and Context7 tools were unavailable. The stack choices, architecture patterns, and pitfall warnings are well-established in the Raspberry Pi community and consistent across multiple sources in training data. However, specific library versions, current API status, and recent Raspberry Pi OS changes should be verified against official documentation during implementation.

The architectural recommendations are high-confidence (filesystem-as-database, three-process design, systemd services), but implementation details like camera abstraction layer specifics and USB webcam error handling will need validation during Phase 1 development.

### Gaps to Address

Research gaps that need attention during planning and implementation:

- **Library versions and compatibility:** Verify `picamera2`, `opencv-python-headless`, Flask versions against current PyPI. Confirm Raspberry Pi OS Bookworm packages `libcamera-apps` and `python3-picamera2`. Check if command rename (`libcamera-still` → `rpicam-still`) is complete.
- **USB webcam device discovery:** Research robust patterns for detecting `/dev/videoN` devices, handling multiple cameras, and udev rules for hotplug events. This is critical for camera abstraction but underdeveloped in research.
- **Thumbnail generation strategy:** Decide whether to generate thumbnails at capture time (slower capture, no delay in UI) or on-demand (faster capture, lazy generation). Evaluate trade-offs on Pi Zero vs Pi 4.
- **Camera lock mechanism details:** File-based lock is recommended but implementation needs validation. Consider `fcntl.flock()` vs lockfile libraries. Test that picamera2 and opencv respect the lock.
- **FFmpeg hardware acceleration:** Training data mentions `h264_v4l2m2m` encoder for Pi 4/5 but unclear if it's stable/recommended. Validate during Phase 3 development.
- **Storage arithmetic validation:** 2.1 GB/day estimate needs validation with actual Pi Camera v2/v3 and USB webcam captures at various quality settings. Test on 32GB SD card to confirm fill timeline.

**Recommended approach for gaps:**
- Validate library versions during Phase 1 setup (5-10 minutes per library)
- Prototype USB webcam detection in first Phase 1 task before committing to abstraction design
- Test thumbnail generation strategies early in Phase 2 with 1000+ dummy images
- Prototype camera lock mechanism in Phase 1, validate in Phase 2 when live view added
- Defer FFmpeg hardware acceleration to Phase 3 optimization (nice-to-have, not blocker)
- Measure actual storage usage in Phase 1 testing, adjust cleanup policies accordingly

## Sources

### Primary (HIGH confidence)
- Python standard library documentation (pathlib, shutil, subprocess, threading) — training data, actively maintained
- FFmpeg documentation on image sequences and framerate — training data, canonical reference
- systemd unit file documentation — training data, stable API

### Secondary (MEDIUM confidence)
- Raspberry Pi picamera2 documentation — training data, official library but version details may be outdated
- Flask documentation — training data, stable framework
- OpenCV Python documentation — training data, stable API for VideoCapture
- Raspberry Pi OS Bookworm release notes — training data, libcamera transition is confirmed but specific package versions unavailable
- Community patterns for SD card wear and disk-full crashes in Pi projects — training data, consistent reports

### Tertiary (LOW confidence)
- Specific versions of picamera2, opencv-python-headless, Flask — inferred from training data, need verification against PyPI
- Command rename (libcamera-still → rpicam-still) — mentioned in training data but timeline unclear
- Hardware-accelerated FFmpeg encoding on Pi 4/5 — mentioned but stability/recommendation unclear

**Sources limitation:** All research conducted via training data only. Web search and Context7 tools were unavailable. This limits confidence in:
- Current library versions and recent API changes
- Recent Raspberry Pi OS updates and package availability
- Community consensus on best practices (forums, GitHub issues)
- Real-world timelapse project implementations for validation

**Recommendation:** During Phase 1 setup, allocate time to verify library versions, test camera detection, and validate storage arithmetic with actual hardware.

---
*Research completed: 2026-02-16*
*Ready for roadmap: yes*

# Common Pitfalls

**Domain:** Raspberry Pi timelapse camera toolkit
**Researched:** 2026-02-16
**Confidence:** MEDIUM (training data only -- well-established ecosystem patterns)

## Critical Pitfalls

Mistakes that cause data loss, system failure, or require significant rework.

### Pitfall 1: SD Card Wear and Corruption from Continuous Writes

**What goes wrong:** Writing a JPEG every 30 seconds (2,880 writes/day) to a consumer SD card causes premature wear. SD cards use flash memory with limited write cycles. After weeks/months of continuous operation, the card develops bad sectors, the filesystem corrupts, and all captured images are lost.

**Why it happens:** SD cards are designed for intermittent use (cameras, phones), not continuous server workloads. Consumer cards lack wear leveling sophistication.

**Prevention:**
1. Use external USB storage for image writes. Keep OS SD card as read-only as possible.
2. Use high-endurance SD cards (Samsung PRO Endurance, SanDisk High Endurance).
3. Mount `/tmp` and `/var/log` as tmpfs. Disable swap.
4. Monitor disk health with periodic checks.

**Phase:** Must be addressed in Phase 1 (Capture Daemon). Storage strategy is foundational.

### Pitfall 2: Disk Full Condition Crashes the Entire System

**What goes wrong:** At 30-second intervals, ~2.1 GB/day of images are generated. A 32GB SD card fills in ~10-20 days. When storage hits 100%, the OS itself cannot function: logging fails, services crash, the Pi becomes unresponsive.

**Why it happens:** Developers implement capture but defer storage management to "later."

**Prevention:**
1. Implement storage management from day one -- not a nice-to-have.
2. Reserve space for the OS (never let images consume more than 80-85%).
3. Oldest-first deletion policy when threshold is reached.
4. Pre-capture space check before every write.
5. Expose disk usage prominently in the web UI.

**Detection:** Capture daemon should check `shutil.disk_usage()` before every write.

**Phase:** Must be addressed in Phase 1 (Capture Daemon).

### Pitfall 3: libcamera vs. Legacy raspistill API Confusion

**What goes wrong:** Many tutorials still reference deprecated `raspistill`/`raspivid` commands. Developers copy legacy code that silently fails on modern Pi OS. The `picamera` v1 library does not work with the new libcamera stack.

**Prevention:**
1. Target modern stack exclusively: `rpicam-still`/`libcamera-still` for Pi Camera, v4l2 for USB webcams.
2. Use `picamera2` (not `picamera`) if using Python bindings.
3. Implement camera detection at startup (`rpicam-still --list-cameras`, `v4l2-ctl --list-devices`).
4. Abstract the camera interface to hide libcamera vs. v4l2 differences.
5. Document minimum OS: Raspberry Pi OS Bookworm (2023+).
6. Note the command rename: Bookworm renamed `libcamera-still` to `rpicam-still`.

**Phase:** Must be addressed in Phase 1 (Capture Daemon).

### Pitfall 4: Capture Process Hangs or Zombies

**What goes wrong:** Camera capture commands hang indefinitely (USB disconnect, GPU memory failure). The daemon waits forever, misses captures, and zombie processes accumulate until the Pi freezes.

**Prevention:**
1. Always use timeouts on subprocess calls (15-30 second max per capture).
2. Implement watchdog: if N consecutive captures fail, restart daemon.
3. Use systemd's `WatchdogSec` directive.
4. Clean up zombie processes after killing timed-out captures.
5. Detect USB webcam disconnect (`/dev/videoN` disappearance) and degrade gracefully.
6. Log every capture attempt with timing and success/failure.

**Phase:** Phase 1 (Capture Daemon).

### Pitfall 5: Running Web Server as Root / Without Resource Limits

**What goes wrong:** Web server runs as root for camera access convenience. Serving full-resolution images in the timeline without pagination consumes all RAM on a 512MB Pi Zero.

**Prevention:**
1. Run each service as a dedicated non-root user with `video` group membership.
2. Use systemd `User=`, `MemoryMax=`, `CPUQuota=` directives.
3. Generate thumbnails for timeline view (200-300px wide, ~10-20KB vs 500KB-2MB).
4. Paginate image listings (max 50-100 per request).
5. Bind web server to local network interface only.

**Phase:** Phases 1-2 (service setup and web server).

## Moderate Pitfalls

### Pitfall 6: Inconsistent Image Naming and Timezone Issues

**What goes wrong:** Sequential numbering restarts on reboot, overwriting images. Pi has no battery-backed RTC, so time may be wrong at boot until NTP syncs.

**Prevention:**
1. Use ISO 8601 timestamps in filenames: `YYYYMMDD_HHMMSS.jpg`
2. Organize into date-based directories: `YYYY/MM/DD/`
3. Wait for NTP sync before starting captures (check if year > 2024).
4. Handle duplicate timestamps with sequence numbers.

**Phase:** Phase 1 (Capture Daemon).

### Pitfall 7: FFmpeg Timelapse Blocks the System

**What goes wrong:** FFmpeg encoding consumes 100% CPU for hours on a Pi Zero. Capture daemon misses shots, web server becomes unresponsive.

**Prevention:**
1. Use `nice -n 19 ionice -c3 ffmpeg ...` to lower priority.
2. Consider hardware-accelerated encoding (`h264_v4l2m2m`) on Pi 4/5.
3. Only run FFmpeg when explicitly triggered, never automatically.
4. Process in chunks (daily segments, then concatenate).
5. Provide option to export images for encoding on a more powerful machine.

**Phase:** Phase 3 (FFmpeg Script).

### Pitfall 8: Single-Directory File Listing Performance Collapse

**What goes wrong:** All images in one flat directory. After 50,000+ files, `readdir()` is extremely slow on SD card I/O. Web server takes 30+ seconds to list images.

**Prevention:**
1. Use date-based directory hierarchy from the start: `YYYY/MM/DD/`
2. Never use `os.listdir()` on the image root -- always scope to date.
3. Test with realistic file counts (50,000+ dummy files) early.

**Phase:** Phase 1 (Capture Daemon). Must be correct from the start.

### Pitfall 9: No Graceful Degradation on Camera Disconnect

**What goes wrong:** USB webcam unplugged. Daemon crashes, systemd restarts it, camera still gone, crash loop fills logs and may trigger systemd rate limiting.

**Prevention:**
1. Check device presence before each capture.
2. Exponential backoff on repeated failures (5s, 10s, 30s, 60s, up to 5min).
3. Log disconnection as warning, not crash.
4. Expose camera status in web UI.
5. Consider udev rules for hotplug detection.

**Phase:** Phase 1 (Capture Daemon).

### Pitfall 10: Pi Camera Auto-Exposure Settling

**What goes wrong:** First frames from Pi Camera are incorrectly exposed. AGC/AWB algorithms need several frames to converge, especially in low light. Results in timelapse flicker.

**Prevention:**
1. Keep camera pipeline open between captures (picamera2 supports this).
2. For CLI, use `rpicam-still --timelapse <ms>` to keep camera open.
3. Allow 2-3 seconds settling time before capturing.
4. Consider fixed exposure/white balance for consistent timelapse frames.
5. Test at dawn/dusk transitions.

**Phase:** Phase 1 (Capture Daemon).

## Minor Pitfalls

### Pitfall 11: No Remote Diagnostics

**What goes wrong:** Headless Pi deployed without a monitor. Every bug requires physical access.

**Prevention:** Expose system health in web UI (CPU temp, disk, uptime, last capture, service status). Use mDNS (`timelapse.local`) for discovery. Enable hardware watchdog.

**Phase:** Phase 2 (Web Server).

### Pitfall 12: Incorrect FFmpeg Framerate Math

**What goes wrong:** Wrong duration output. `-framerate` before `-i` is input rate; `-r` after is output rate. Getting confused produces unexpected results.

**Prevention:** Calculate frame count first, derive input fps, test with small sets, verify output duration matches expectations.

**Phase:** Phase 3 (FFmpeg Script).

### Pitfall 13: Thermal Throttling in Enclosed Cases

**What goes wrong:** Pi in sealed enclosure overheats. CPU throttles, capture timing becomes inconsistent.

**Prevention:** Ventilation holes, heatsink, monitor CPU temp via `/sys/class/thermal/thermal_zone0/temp`, expose in web UI.

**Phase:** Phase 2 (Web Server health metrics).

### Pitfall 14: Not Testing on Target Hardware

**What goes wrong:** Development on Pi 4 (4GB, 4 cores). Deployment on Pi Zero 2W (512MB, slow cores). Everything breaks.

**Prevention:** Develop on or regularly test on lowest-spec target hardware. Set memory limits in development. Profile resource usage.

**Phase:** All phases.

## Phase-Specific Warning Summary

| Phase | Key Pitfalls | Critical Actions |
|-------|-------------|-----------------|
| Phase 1 (Capture) | SD card wear, disk full, API confusion, hangs, naming, camera disconnect, auto-exposure | Storage strategy, disk monitoring, camera abstraction, timeouts, date-based dirs |
| Phase 2 (Web UI) | Root/resource limits, no diagnostics, thermal monitoring | Non-root user, thumbnails, pagination, health dashboard |
| Phase 3 (FFmpeg) | CPU blocking, framerate math, thermal throttling | nice/ionice, correct fps calculation, chunk processing |

## Sources

- Raspberry Pi camera documentation (MEDIUM confidence -- training data)
- Community reports of SD card failures in continuous-write RPi projects (MEDIUM confidence)
- FFmpeg documentation on image sequences and framerate (HIGH confidence)
- Raspberry Pi thermal throttling behavior (HIGH confidence)
- picamera2 library documentation (MEDIUM confidence)

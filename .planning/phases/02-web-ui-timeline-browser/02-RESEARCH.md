# Phase 2: Web UI & Timeline Browser - Research

**Researched:** 2026-02-16
**Domain:** Flask web server, image browsing UI, PAM authentication, systemd service control
**Confidence:** HIGH

## Summary

This phase builds a Flask web server serving a three-tab interface (Timeline, Latest Image, Control) on the local network. The data source is the filesystem of date-organized images produced by Phase 1 (YYYY/MM/DD/HHMMSS.jpg). The daemon's `.status.json` file provides health/state information. The UI requires keyboard-driven navigation for the filmstrip timeline, auto-refreshing for the Latest Image tab, and PAM-authenticated daemon control on the Control tab.

The stack is straightforward: Flask 3.1.x with Jinja2 templates, Pico CSS for styling, vanilla JavaScript for interactivity, Pillow for thumbnail generation, `python-pam` for PAM authentication combined with `Flask-HTTPAuth` for HTTP Basic Auth, and `subprocess` for systemd service management via passwordless `sudo`. The architecture follows Flask's application factory pattern with three blueprints (timeline, latest, control). The main risks are: getting keyboard navigation right in the filmstrip, handling the sudo/PAM permission model correctly, and efficiently serving images from a potentially large filesystem.

**Primary recommendation:** Use Flask application factory with three blueprints, Pico CSS for clean default styling, pre-generated thumbnails (at capture time in Phase 1's daemon), and `python-pam` + `Flask-HTTPAuth` for the Control tab's PAM authentication. Keep JavaScript vanilla -- no build step, no framework.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Horizontal filmstrip of small thumbnails (100-120px) at the top of the Timeline tab
- Left/right arrow keys navigate between individual thumbnails; mouse click also selects
- Currently selected thumbnail displays as a large image below the filmstrip
- No modals, no inline expansion, no separate full-image page -- filmstrip is always visible above the selected image
- Up/down arrow keys step between days (previous/next day)
- "d" key opens a date picker for jumping to any specific day
- All navigation fully keyboard-usable
- Renamed from "Live View" to "Latest Image" for accuracy
- Refreshes at the configured capture interval (not faster)
- Displays the configured capture interval so the user knows how often to expect updates
- When camera is offline or daemon stopped: shows last captured image with a clear status banner
- Small timestamp overlay on the image showing when it was captured
- View-only -- no manual "capture now" button
- Top tab bar: Timeline | Latest Image | Control
- Desktop-first layout; mobile should be functional but not the priority
- Subtle health indicators visible on all tabs (disk usage, daemon status, last capture time)
- Hover state popup on any piece of the health indicators reveals the full set of system info
- Visual style: polished but not overdone -- clean, someone put effort into it, but not flashy or over the top
- Separate "Control" tab requiring PAM authentication (Pi system username/password) to view
- HTTP Basic Auth or session-based auth against PAM -- auth prompt before any Control tab content is visible
- Dedicated Start and Stop buttons (not a toggle)
- Confirmation prompt on Stop action (starting is safe, stopping interrupts capture)
- Inline status text near controls: "Starting...", "Running", "Stopped" -- updates in place
- Comprehensive machine status and health details displayed on the Control tab (full disk info, uptime, daemon state, config summary)

### Claude's Discretion
- Flask project structure and blueprint organization
- Thumbnail generation strategy (on-the-fly vs pre-generated)
- Exact CSS framework or approach (vanilla, minimal framework, etc.)
- Date picker widget implementation
- How to poll/refresh the Latest Image tab (JS interval, SSE, etc.)
- PAM session handling details (session duration, re-auth policy)
- Exact health metrics shown in the subtle indicators vs the full Control tab view

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WEB-01 | Flask web server serves a tabbed interface (Timeline / Latest Image / Control) | Flask 3.1.x with application factory pattern, Jinja2 template inheritance with base layout + tab navigation, Pico CSS for styling |
| WEB-02 | Latest Image tab shows an auto-refreshing still image (ephemeral, no storage impact) | JavaScript `setInterval` with cache-busting timestamp query param; Flask endpoint serves latest file from filesystem (no new capture needed) |
| WEB-03 | Timeline tab displays a scrollable horizontal strip of captured images | Horizontal filmstrip via CSS `overflow-x: auto` + `display: flex`, vanilla JS for keyboard navigation with `tabindex` and `ArrowLeft`/`ArrowRight` key handlers |
| WEB-04 | Thumbnails generated at capture time for fast timeline browsing | Pillow `Image.thumbnail()` with JPEG draft optimization; generate 120px thumbnails alongside full images in capture daemon (Phase 1 enhancement) |
| WEB-05 | Date picker allows jumping to specific days in the timeline | Native HTML `<input type="date">` with `showPicker()` API triggered by "d" key; populate available dates from filesystem directory listing |
| WEB-06 | Disk space warning displays on web UI when free space drops below configurable threshold | Read from `.status.json` (already written by Phase 1 daemon); compare `disk_usage_percent` against `warn_threshold` from config; display banner on all tabs |
| WEB-07 | Capture health indicator shows daemon status and last capture time | Read from `.status.json`; subtle footer/header indicator on all tabs showing daemon state, last capture time, disk usage |
| WEB-08 | User can start/stop capture from the web UI | PAM-authenticated Control tab; `subprocess.run(["sudo", "systemctl", "start/stop", "timelapse-capture"])` with sudoers NOPASSWD rule for the web server user |
| WEB-09 | Web server runs as a systemd service | New `timelapse-web.service` unit file, similar pattern to existing `timelapse-capture.service` |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.x (3.1.2 latest) | Web framework | Minimal, low-overhead, synchronous -- ideal for a local network single-user app on Pi. Already selected in Phase 1 research. |
| Jinja2 | 3.x (bundled with Flask) | HTML templating | Ships with Flask. Server-side rendering appropriate for this workload. |
| Pillow | 12.1.x (12.1.1 latest) | Thumbnail generation | Standard Python imaging library. Has JPEG draft mode optimization for fast thumbnail creation. Pre-built ARM64 wheels available on piwheels. |
| python-pam | 2.0.2 | PAM authentication | Pure Python (ctypes), no compilation needed. 249K weekly downloads. Simple `authenticate(username, password)` API. |
| Flask-HTTPAuth | 4.8.0 | HTTP Basic Auth | Miguel Grinberg's well-tested extension. Provides `verify_password` callback decorator for clean integration with python-pam. 265K weekly downloads. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pico CSS | 2.x | Classless CSS framework | Base styling for all pages. ~10KB gzipped, no JS, no build step. Styles semantic HTML directly. Includes dark/light mode, responsive typography, form styling. |
| Vanilla JS | N/A | Client-side interactivity | Keyboard navigation, image refresh, date picker triggering, confirmation dialogs. No framework needed -- estimated 200-300 lines total. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pico CSS | Water.css (2KB) | Smaller but less polished. Pico better matches the "polished but not overdone" requirement. |
| Pico CSS | Vanilla CSS | More control but more work. Pico gives a polished baseline for free. |
| Flask-HTTPAuth + python-pam | Flask-PAM | Flask-PAM is inactive (18 weekly downloads). Better to use the well-maintained components separately. |
| Flask-HTTPAuth (Basic Auth) | Flask-Login (sessions) | Sessions add complexity (secret key, session store). Basic Auth is simpler for a single protected tab on a local network. Browser caches credentials for the session. |
| subprocess (systemctl) | pystemd (D-Bus) | pystemd is more robust but adds a dependency and requires systemd headers. subprocess is sufficient for start/stop/is-active on two services. |
| setInterval (polling) | Server-Sent Events (SSE) | SSE is more efficient but adds complexity. Polling every N seconds (matching capture interval) is simple and perfectly adequate. |

**Installation:**
```bash
pip install "flask>=3.1,<4" "pillow>=12.0" "python-pam>=2.0" "Flask-HTTPAuth>=4.8"
```

Pico CSS is loaded via CDN or vendored as a single CSS file (no pip install):
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
```

For a Pi without reliable internet, vendor the file into `static/css/pico.min.css`.

## Architecture Patterns

### Recommended Project Structure

```
src/timelapse/
    web/
        __init__.py          # create_app() factory function
        blueprints/
            __init__.py
            timeline.py      # Timeline tab routes + API endpoints
            latest.py        # Latest Image tab routes + API endpoints
            control.py       # Control tab routes (PAM-protected)
        templates/
            base.html        # Base layout: tab bar, health indicators, CSS/JS includes
            timeline.html    # Timeline tab content
            latest.html      # Latest Image tab content
            control.html     # Control tab content (behind auth)
        static/
            css/
                pico.min.css # Vendored Pico CSS
                app.css      # Custom overrides (filmstrip, health indicators, etc.)
            js/
                timeline.js  # Keyboard nav, filmstrip scrolling, date picker
                latest.js    # Auto-refresh polling
                control.js   # Start/stop buttons, confirmation, status polling
        auth.py              # PAM authentication helper (wraps python-pam + Flask-HTTPAuth)
        health.py            # Status file reader + disk space + system info aggregation
        thumbnails.py        # Thumbnail generation logic (called from capture daemon)
```

### Pattern 1: Application Factory with Blueprints

**What:** Flask application factory (`create_app()`) that registers three blueprints (timeline, latest, control) and configures shared resources (config path, output directory, status file path).

**When to use:** Always -- this is the standard Flask pattern for non-trivial apps.

**Example:**
```python
# Source: Flask 3.1.x official docs - Application Factories
from flask import Flask

def create_app(config_path=None):
    app = Flask(__name__)

    # Load timelapse config to get output_dir, thresholds, etc.
    from timelapse.config import load_config
    timelapse_config = load_config(config_path or _find_config())
    app.config["TIMELAPSE"] = timelapse_config
    app.config["OUTPUT_DIR"] = timelapse_config["storage"]["output_dir"]
    app.config["SECRET_KEY"] = "local-network-only"  # For flash messages

    from timelapse.web.blueprints.timeline import timeline_bp
    from timelapse.web.blueprints.latest import latest_bp
    from timelapse.web.blueprints.control import control_bp

    app.register_blueprint(timeline_bp)
    app.register_blueprint(latest_bp, url_prefix="/latest")
    app.register_blueprint(control_bp, url_prefix="/control")

    return app
```

### Pattern 2: PAM Authentication via Flask-HTTPAuth + python-pam

**What:** HTTP Basic Auth with PAM as the credential backend. The browser prompts for username/password. Credentials are verified against the system's PAM stack (Linux user accounts).

**When to use:** Control tab only. All other tabs are unauthenticated.

**Example:**
```python
# Source: Flask-HTTPAuth docs + python-pam PyPI
import pam
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_pam(username, password):
    """Verify credentials against Linux PAM."""
    if not username or not password:
        return None
    p = pam.pam()
    if p.authenticate(username, password):
        return username
    return None

# In the control blueprint:
@control_bp.route("/")
@auth.login_required
def control_panel():
    return render_template("control.html", user=auth.current_user())
```

**Important:** The web server process needs access to the PAM stack. On Raspberry Pi OS, the user running the Flask process should be in the `shadow` group, or PAM should be configured to use a service that does not require shadow access (e.g., `login` or a custom service). Test with: `python3 -c "import pam; p=pam.pam(); print(p.authenticate('pi', 'password'))"`.

### Pattern 3: Filesystem-as-Database for Timeline Data

**What:** The Phase 1 directory structure (YYYY/MM/DD/HHMMSS.jpg) IS the database. No database, no index file. API endpoints scan the filesystem.

**When to use:** All timeline browsing operations.

**Example:**
```python
# List available dates (years/months/days)
from pathlib import Path

def list_available_dates(output_dir: Path) -> list[str]:
    """Return sorted list of date strings (YYYY-MM-DD) with images."""
    dates = []
    for year_dir in sorted(output_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                # Verify at least one image exists
                if any(day_dir.glob("*.jpg")):
                    dates.append(f"{year_dir.name}-{month_dir.name}-{day_dir.name}")
    return dates

def list_images_for_date(output_dir: Path, date_str: str) -> list[str]:
    """Return sorted list of image filenames for a given date."""
    year, month, day = date_str.split("-")
    day_dir = output_dir / year / month / day
    if not day_dir.is_dir():
        return []
    return sorted(f.name for f in day_dir.iterdir() if f.suffix == ".jpg")
```

### Pattern 4: JavaScript Image Refresh with Cache Busting

**What:** Auto-refresh the Latest Image by updating the `src` attribute with a timestamp query parameter on a `setInterval`.

**When to use:** Latest Image tab.

**Example:**
```javascript
// Source: Standard web pattern for auto-refreshing images
const img = document.getElementById("latest-image");
const intervalDisplay = document.getElementById("capture-interval");
const captureInterval = parseInt(intervalDisplay.dataset.interval, 10) * 1000;

function refreshLatestImage() {
    const baseUrl = "/latest/image";
    img.src = `${baseUrl}?t=${Date.now()}`;
}

setInterval(refreshLatestImage, captureInterval);
```

### Pattern 5: Keyboard-Navigable Filmstrip

**What:** Horizontal scrollable container with `tabindex="0"`, listening for arrow keys. Left/Right moves between thumbnails within a day. Up/Down steps between days. "d" opens the date picker.

**When to use:** Timeline tab.

**Example:**
```javascript
// Source: MDN Keyboard-navigable JavaScript widgets
const filmstrip = document.getElementById("filmstrip");
const mainImage = document.getElementById("main-image");
let currentIndex = 0;
let thumbnails = filmstrip.querySelectorAll(".thumb");

filmstrip.addEventListener("keydown", (e) => {
    switch (e.key) {
        case "ArrowLeft":
            e.preventDefault();
            navigateTo(currentIndex - 1);
            break;
        case "ArrowRight":
            e.preventDefault();
            navigateTo(currentIndex + 1);
            break;
        case "ArrowUp":
            e.preventDefault();
            loadPreviousDay();
            break;
        case "ArrowDown":
            e.preventDefault();
            loadNextDay();
            break;
        case "d":
            e.preventDefault();
            document.getElementById("date-picker").showPicker();
            break;
    }
});

function navigateTo(index) {
    if (index < 0 || index >= thumbnails.length) return;
    thumbnails[currentIndex].classList.remove("selected");
    currentIndex = index;
    thumbnails[currentIndex].classList.add("selected");
    thumbnails[currentIndex].scrollIntoView({ behavior: "smooth", inline: "center" });
    mainImage.src = thumbnails[currentIndex].dataset.fullUrl;
}
```

### Anti-Patterns to Avoid

- **Loading all images at once:** Do NOT load thumbnails for all dates into the DOM. Load one day at a time. A day at 30-second intervals has ~2880 images; at 60-second intervals, ~1440. Load thumbnails lazily (e.g., `loading="lazy"` attribute) and paginate if a day has too many.
- **Database for image metadata:** The filesystem IS the database. Do not add SQLite or any ORM. The directory structure provides all needed indexing.
- **SPA with client-side routing:** Do not build a single-page app. Use server-rendered tabs with progressive JavaScript enhancement. Each tab is a separate Jinja2 template extending the base layout.
- **Generating thumbnails on every request:** Generate thumbnails once (at capture time) and serve from disk. On-the-fly generation would hammer the Pi's CPU on every timeline browse.
- **Polling the Control tab without auth:** Never expose systemctl operations without authentication. The PAM check must happen before any control endpoint responds.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS styling | Custom CSS from scratch | Pico CSS 2.x | Responsive, accessible, dark mode, semantic HTML styling in ~10KB. The "polished but not overdone" aesthetic matches Pico's design philosophy. |
| HTTP authentication | Custom auth middleware | Flask-HTTPAuth | Battle-tested, handles the HTTP Basic Auth protocol details (WWW-Authenticate headers, 401 responses, credential parsing). |
| PAM integration | Raw ctypes calls to libpam | python-pam 2.0.2 | Wraps the ctypes complexity. Single `authenticate()` call. Handles PAM conversation callbacks. |
| Image thumbnailing | ImageMagick subprocess calls | Pillow `Image.thumbnail()` | Native Python, uses JPEG draft mode for fast scaling, no subprocess overhead. |
| Date picker | Custom calendar widget | Native `<input type="date">` + `showPicker()` | Browser-native, accessible, keyboard-usable, no JS library needed. Supported in all modern browsers. |

**Key insight:** Every "simple" UI widget (date picker, image scroller, auth flow) has edge cases that libraries handle correctly. The user's "polished" requirement means these details matter.

## Common Pitfalls

### Pitfall 1: PAM Authentication Requires Elevated Permissions

**What goes wrong:** `python-pam` calls `pam_authenticate()` which needs to read `/etc/shadow`. If the Flask process runs as a regular user, PAM authentication silently fails.

**Why it happens:** On Raspberry Pi OS, `/etc/shadow` is readable only by root and the `shadow` group.

**How to avoid:** Add the web server user to the `shadow` group: `sudo usermod -aG shadow pi`. Alternatively, configure PAM to use a service that does not require shadow access. Test authentication works before deploying.

**Warning signs:** `p.authenticate()` always returns `False` even with correct credentials.

### Pitfall 2: systemctl Requires sudo, sudo Requires NOPASSWD

**What goes wrong:** `subprocess.run(["systemctl", "start", "timelapse-capture"])` fails because systemctl requires root privileges. Even with `sudo`, the web server process has no TTY to enter a password.

**Why it happens:** systemd service management requires root. Without a NOPASSWD sudoers rule, sudo prompts for a password that nobody can type.

**How to avoid:** Create a sudoers drop-in file `/etc/sudoers.d/timelapse-web`:
```
pi ALL=(root) NOPASSWD: /usr/bin/systemctl start timelapse-capture
pi ALL=(root) NOPASSWD: /usr/bin/systemctl stop timelapse-capture
pi ALL=(root) NOPASSWD: /usr/bin/systemctl is-active timelapse-capture
```
Use the full path to systemctl. Limit to exactly these three commands and the exact service name.

**Warning signs:** "sudo: a terminal is required to read the password" in logs.

### Pitfall 3: Browser Caches Prevent Image Refresh

**What goes wrong:** The Latest Image tab shows a stale image even though the server has a new one. The browser cache serves the old response because the URL hasn't changed.

**Why it happens:** Browsers aggressively cache image responses. If the URL is `/latest/image` and it never changes, the browser may not even make a new request.

**How to avoid:** Append a cache-busting query parameter: `/latest/image?t=1708123456789`. Also set `Cache-Control: no-store` on the response header for the latest image endpoint.

**Warning signs:** Image in Latest Image tab never updates after first load.

### Pitfall 4: Thumbnail Generation Performance on Pi

**What goes wrong:** Generating thumbnails on-the-fly for every request makes the Timeline tab extremely slow, especially on a Raspberry Pi where CPU is constrained.

**Why it happens:** Pillow must decode the full JPEG, resize, and re-encode for every thumbnail. On a Pi, this can take 200-500ms per image.

**How to avoid:** Generate thumbnails at capture time. Store them alongside the originals in a parallel directory structure or with a `.thumb.jpg` suffix. The capture daemon already processes each image -- adding thumbnail generation is a ~50ms additional cost per capture. Alternatively, store thumbnails in a `thumbs/` subdirectory within each day: `YYYY/MM/DD/thumbs/HHMMSS.jpg`.

**Warning signs:** Timeline tab takes >5 seconds to load for a single day.

### Pitfall 5: Large Day Directories Overwhelm the Browser

**What goes wrong:** At 30-second intervals, a single day produces 2,880 images. Loading 2,880 thumbnail `<img>` tags into the filmstrip causes the browser to make 2,880 HTTP requests and the page to become unresponsive.

**Why it happens:** No pagination or lazy loading strategy.

**How to avoid:** Use `loading="lazy"` on thumbnail images so only visible thumbnails are fetched. The filmstrip container with `overflow-x: scroll` naturally limits visible thumbnails to maybe 10-20 at a time. Also consider serving thumbnail metadata via a JSON API and rendering thumbnails dynamically as the user scrolls (intersection observer pattern), but start simple with lazy loading first.

**Warning signs:** Browser tab crashes or shows "Out of Memory" on days with many captures.

### Pitfall 6: Race Condition Between Daemon and Web Server on Status File

**What goes wrong:** The web server reads `.status.json` at the exact moment the daemon is writing it, getting a partial or corrupt file.

**Why it happens:** File writes are not atomic by default.

**How to avoid:** Phase 1 already handles this -- `write_status()` uses atomic write (write to temp file, then `os.rename()`). The web server's `read_status()` function handles `JSONDecodeError` gracefully and returns `None`. No additional work needed.

**Warning signs:** Occasional "Could not read status file" warnings in web server logs (acceptable and handled).

### Pitfall 7: showPicker() Requires User Activation

**What goes wrong:** Calling `dateInput.showPicker()` from a keyboard event handler throws `NotAllowedError` if the browser considers it not triggered by a user gesture.

**Why it happens:** `showPicker()` requires "transient activation" (a recent user interaction). Most browsers accept keyboard events as activation, but some edge cases exist.

**How to avoid:** Wrap in try/catch. If `showPicker()` fails, fall back to focusing the date input (which still allows keyboard entry). The date input should be visible but small/unobtrusive so users can also click it directly.

**Warning signs:** Console error "NotAllowedError: HTMLInputElement.showPicker()" on some browsers.

## Code Examples

### Flask Application Factory with Config Integration

```python
# Source: Flask 3.1.x official docs + project-specific integration
# src/timelapse/web/__init__.py

from pathlib import Path
from flask import Flask

def create_app(config_path: Path | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Reuse Phase 1 config loader
    from timelapse.config import load_config
    if config_path is None:
        config_path = _find_config()
    timelapse_cfg = load_config(config_path)

    app.config["TIMELAPSE"] = timelapse_cfg
    app.config["OUTPUT_DIR"] = Path(timelapse_cfg["storage"]["output_dir"])
    app.config["STATUS_FILE"] = app.config["OUTPUT_DIR"] / ".status.json"
    app.config["SECRET_KEY"] = "timelapse-local"  # Only for flash messages

    # Register blueprints
    from timelapse.web.blueprints.timeline import timeline_bp
    from timelapse.web.blueprints.latest import latest_bp
    from timelapse.web.blueprints.control import control_bp

    app.register_blueprint(timeline_bp)
    app.register_blueprint(latest_bp, url_prefix="/latest")
    app.register_blueprint(control_bp, url_prefix="/control")

    # Register context processor for health indicators on all pages
    @app.context_processor
    def inject_health():
        from timelapse.web.health import get_health_summary
        return {"health": get_health_summary(app.config["STATUS_FILE"], timelapse_cfg)}

    return app

def _find_config() -> Path:
    """Config fallback chain (same as daemon)."""
    for path in [Path("/etc/timelapse/timelapse.yml"), Path("./config/timelapse.yml")]:
        if path.exists():
            return path
    raise SystemExit("No config file found")
```

### Thumbnail Generation at Capture Time

```python
# Source: Pillow 12.x docs - Image.thumbnail()
# src/timelapse/web/thumbnails.py

from pathlib import Path
from PIL import Image

THUMB_SIZE = (120, 120)
THUMB_QUALITY = 60

def generate_thumbnail(image_path: Path, thumb_dir: Path | None = None) -> Path:
    """Generate a thumbnail for an image, saving it in a thumbs/ subdirectory.

    Args:
        image_path: Path to the full-size JPEG.
        thumb_dir: Directory for thumbnails. Defaults to image_path.parent / "thumbs".

    Returns:
        Path to the generated thumbnail.
    """
    if thumb_dir is None:
        thumb_dir = image_path.parent / "thumbs"
    thumb_dir.mkdir(exist_ok=True)

    thumb_path = thumb_dir / image_path.name
    if thumb_path.exists():
        return thumb_path

    # Image.open() is lazy -- thumbnail() uses JPEG draft mode for fast decode
    with Image.open(image_path) as im:
        im.thumbnail(THUMB_SIZE)
        im.save(thumb_path, "JPEG", quality=THUMB_QUALITY)

    return thumb_path
```

### Serving Images Securely with send_from_directory

```python
# Source: Flask 3.1.x docs - send_from_directory
# In timeline blueprint

from flask import Blueprint, send_from_directory, current_app, abort

timeline_bp = Blueprint("timeline", __name__)

@timeline_bp.route("/image/<year>/<month>/<day>/<filename>")
def serve_image(year, month, day, filename):
    """Serve a full-size image from the output directory."""
    output_dir = current_app.config["OUTPUT_DIR"]
    image_dir = output_dir / year / month / day
    if not image_dir.is_dir():
        abort(404)
    return send_from_directory(image_dir, filename, mimetype="image/jpeg")

@timeline_bp.route("/thumb/<year>/<month>/<day>/<filename>")
def serve_thumbnail(year, month, day, filename):
    """Serve a thumbnail from the thumbs/ subdirectory."""
    output_dir = current_app.config["OUTPUT_DIR"]
    thumb_dir = output_dir / year / month / day / "thumbs"
    if not thumb_dir.is_dir():
        abort(404)
    return send_from_directory(
        thumb_dir, filename, mimetype="image/jpeg",
        max_age=86400  # Thumbnails are immutable, cache aggressively
    )
```

### Latest Image Endpoint

```python
# Source: project-specific
# In latest blueprint

from flask import Blueprint, current_app, send_file, jsonify, abort
from pathlib import Path

latest_bp = Blueprint("latest", __name__)

@latest_bp.route("/image")
def latest_image():
    """Serve the most recently captured image."""
    output_dir = current_app.config["OUTPUT_DIR"]
    latest = _find_latest_image(output_dir)
    if latest is None:
        abort(404)
    response = send_file(latest, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "no-store"
    return response

def _find_latest_image(output_dir: Path) -> Path | None:
    """Walk the directory tree in reverse to find the newest image."""
    for year_dir in sorted(output_dir.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            for day_dir in sorted(month_dir.iterdir(), reverse=True):
                if not day_dir.is_dir():
                    continue
                images = sorted(
                    (f for f in day_dir.iterdir() if f.suffix == ".jpg" and f.name != "thumbs"),
                    reverse=True,
                )
                if images:
                    return images[0]
    return None
```

### Systemd Service Control with Sudoers

```python
# Source: subprocess + systemctl pattern
# In control blueprint

import subprocess

SERVICE_NAME = "timelapse-capture"

def get_service_status() -> str:
    """Check if the capture service is running."""
    result = subprocess.run(
        ["sudo", "systemctl", "is-active", SERVICE_NAME],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip()  # "active", "inactive", "failed", etc.

def start_service() -> tuple[bool, str]:
    """Start the capture service. Returns (success, message)."""
    result = subprocess.run(
        ["sudo", "systemctl", "start", SERVICE_NAME],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        return True, "Service started"
    return False, result.stderr.strip()

def stop_service() -> tuple[bool, str]:
    """Stop the capture service. Returns (success, message)."""
    result = subprocess.run(
        ["sudo", "systemctl", "stop", SERVICE_NAME],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        return True, "Service stopped"
    return False, result.stderr.strip()
```

### Health Indicator Data Aggregation

```python
# Source: project-specific
# src/timelapse/web/health.py

import shutil
import subprocess
from pathlib import Path
from timelapse.status import read_status

def get_health_summary(status_path: Path, config: dict) -> dict:
    """Aggregate health data for the base template's health indicators."""
    status = read_status(status_path) or {}
    warn_threshold = config["storage"]["warn_threshold"]
    disk_pct = status.get("disk_usage_percent", -1)

    return {
        "daemon_state": status.get("daemon", "unknown"),
        "last_capture": status.get("last_capture"),
        "disk_usage_percent": disk_pct,
        "disk_free_gb": status.get("disk_free_gb", -1),
        "disk_warning": disk_pct >= warn_threshold if disk_pct >= 0 else False,
        "captures_today": status.get("captures_today", 0),
        "consecutive_failures": status.get("consecutive_failures", 0),
        "camera": status.get("camera", "unknown"),
        "uptime_seconds": status.get("uptime_seconds", 0),
        "config_loaded": status.get("config_loaded", "unknown"),
    }

def get_full_system_info() -> dict:
    """Extended system info for the Control tab."""
    try:
        uptime = subprocess.run(
            ["uptime", "-p"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        uptime = "unknown"

    try:
        usage = shutil.disk_usage("/")
        disk_total_gb = round(usage.total / (1024**3), 1)
        disk_used_gb = round(usage.used / (1024**3), 1)
        disk_free_gb = round(usage.free / (1024**3), 1)
    except Exception:
        disk_total_gb = disk_used_gb = disk_free_gb = -1

    return {
        "system_uptime": uptime,
        "disk_total_gb": disk_total_gb,
        "disk_used_gb": disk_used_gb,
        "disk_free_gb": disk_free_gb,
    }
```

### Base Template with Tab Navigation and Health Indicators

```html
{# Source: Flask Jinja2 template inheritance + Pico CSS #}
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}Timelapse{% endblock %} - RPi Timelapse</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/pico.min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
</head>
<body>
    <header class="container">
        <nav>
            <ul>
                <li><strong>RPi Timelapse</strong></li>
            </ul>
            <ul>
                <li><a href="{{ url_for('timeline.index') }}"
                       {% if request.blueprint == 'timeline' %}aria-current="page"{% endif %}>
                    Timeline</a></li>
                <li><a href="{{ url_for('latest.index') }}"
                       {% if request.blueprint == 'latest' %}aria-current="page"{% endif %}>
                    Latest Image</a></li>
                <li><a href="{{ url_for('control.index') }}"
                       {% if request.blueprint == 'control' %}aria-current="page"{% endif %}>
                    Control</a></li>
            </ul>
        </nav>
        {# Subtle health indicators #}
        <div class="health-bar" title="Click for details">
            <span class="health-item {% if health.disk_warning %}warning{% endif %}"
                  data-tooltip="Disk: {{ health.disk_usage_percent }}% used ({{ health.disk_free_gb }}GB free)">
                Disk {{ health.disk_usage_percent }}%
            </span>
            <span class="health-item {{ health.daemon_state }}"
                  data-tooltip="Daemon: {{ health.daemon_state }} | Last: {{ health.last_capture or 'never' }}">
                {{ health.daemon_state | capitalize }}
            </span>
        </div>
    </header>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    {% block scripts %}{% endblock %}
</body>
</html>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask-PAM (all-in-one) | python-pam + Flask-HTTPAuth (composable) | Flask-PAM has been inactive since ~2020 | Use composable libraries instead of monolithic inactive ones |
| Custom calendar JS widgets | Native `<input type="date">` + `showPicker()` | Chromium 99+ (2022), Safari 16+ (2022) | No third-party date picker library needed |
| `os.listdir()` for directory scanning | `pathlib.iterdir()` (uses `os.scandir()` internally since 3.13) | Python 3.13 (2024) | Faster directory listing, less memory |
| jQuery for DOM manipulation | Vanilla JS (`querySelector`, `addEventListener`, `fetch`) | ~2020 onwards | No jQuery dependency needed for modern browser APIs |
| Separate thumbnail generation script | Inline thumbnail generation in capture loop | N/A (project design) | One-time cost at capture vs. on-demand cost at browse |

**Deprecated/outdated:**
- `Flask-PAM`: Inactive, 18 weekly downloads. Do not use.
- `picamera` (v1): Replaced by `picamera2`. Not relevant to web phase but worth noting.
- jQuery: Not needed for this project's JS requirements.

## Discretion Recommendations

Based on research, here are recommendations for the Claude's Discretion items:

### Flask Project Structure and Blueprint Organization
**Recommendation:** Three blueprints (timeline, latest, control) registered in an application factory. This matches the three tabs and keeps concerns cleanly separated. See the project structure above.

### Thumbnail Generation Strategy
**Recommendation:** Pre-generate thumbnails at capture time. This requires a small enhancement to the Phase 1 capture daemon -- after saving the full image, call `generate_thumbnail()` to create a 120px JPEG in a `thumbs/` subdirectory within each day's folder. The additional ~50ms per capture is negligible vs. the massive performance win when browsing. Lazy generation (generate on first request, cache on disk) is the fallback if modifying Phase 1 feels too invasive, but pre-generation is strongly preferred.

### CSS Framework
**Recommendation:** Pico CSS 2.x. It matches the "polished but not overdone" aesthetic requirement precisely. Classless by default (styles semantic HTML), includes dark/light mode, responsive typography, form elements, and navigation. ~10KB gzipped, no JS, no build step. Vendor the CSS file into `static/css/` for offline use on the Pi.

### Date Picker Widget
**Recommendation:** Native `<input type="date">` element with `showPicker()` API. Triggered by the "d" key. The date input can be visually small/hidden but accessible. Populate the `min` and `max` attributes from the earliest and latest available dates in the filesystem. Use the `change` event to load the selected day's images.

### Latest Image Tab Refresh Strategy
**Recommendation:** JavaScript `setInterval()` polling. Set the interval to match the configured capture interval (passed to the template from the server). On each tick, update the image `src` with a cache-busting timestamp parameter. Also set `Cache-Control: no-store` on the server response. This is the simplest approach and perfectly adequate for a single-user local network app. SSE would be over-engineered.

### PAM Session Handling
**Recommendation:** Use HTTP Basic Auth (not sessions). The browser caches HTTP Basic Auth credentials for the lifetime of the browser tab. This means:
- User authenticates once when first visiting the Control tab
- Credentials are sent on every request to `/control/*` (browser handles this automatically)
- Closing the tab clears the credentials
- No server-side session storage needed
- No session duration or re-auth configuration needed

This is the simplest approach and appropriate for a local-network, personal-use tool.

### Health Indicators: Subtle vs. Full
**Recommendation for subtle indicators (all tabs):**
- Disk usage percentage (with warning color when above threshold)
- Daemon state (Running/Stopped/Error with color coding)
- Small text, shown in the header bar below the tab navigation

**Recommendation for full health view (Control tab):**
- Everything from the subtle indicators, plus:
- Disk free space (GB), total space (GB), used space (GB)
- System uptime
- Camera type (picamera/usb)
- Last capture timestamp and success/failure
- Captures today count
- Consecutive failures count
- Config file path
- Capture interval

## Open Questions

1. **Thumbnail backfill for existing images**
   - What we know: Phase 1 already has images on disk without thumbnails. Phase 2 needs thumbnails.
   - What's unclear: Should there be a one-time migration script to generate thumbnails for existing images, or should the timeline show a placeholder for images without thumbnails?
   - Recommendation: Include a `generate-thumbnails` management command that can be run once to backfill. The timeline should also handle missing thumbnails gracefully (show a placeholder or generate on-demand with caching).

2. **Web server port configuration**
   - What we know: Flask's default is port 5000, but the user might want a different port.
   - What's unclear: Should the port be in the existing YAML config or a CLI argument?
   - Recommendation: Add a `web:` section to the YAML config with `port` (default 8080) and `host` (default "0.0.0.0"). Also accept `--port` and `--host` CLI overrides.

3. **Phase 1 modification scope**
   - What we know: WEB-04 requires thumbnails generated at capture time, which means modifying the Phase 1 daemon.
   - What's unclear: How much Phase 1 code needs to change for Phase 2?
   - Recommendation: The daemon's `_capture_once()` method should call thumbnail generation after a successful capture. Pillow needs to be added as a dependency. This is a small, well-scoped change.

## Sources

### Primary (HIGH confidence)
- [Flask 3.1.x Official Docs - Application Factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) - Application factory pattern, blueprint registration
- [Flask 3.1.x Official Docs - Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/) - Blueprint architecture and URL prefixes
- [Flask 3.1.x Official Docs - Template Inheritance](https://flask.palletsprojects.com/en/stable/patterns/templateinheritance/) - Base layout and block system
- [Pillow 12.1.1 Docs - Image.thumbnail()](https://pillow.readthedocs.io/en/stable/reference/Image.html) - Thumbnail generation API and JPEG draft mode
- [MDN - Keyboard-navigable JavaScript widgets](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Keyboard-navigable_JavaScript_widgets) - tabindex, arrow key navigation pattern
- [MDN - HTMLInputElement.showPicker()](https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/showPicker) - Programmatic date picker opening
- [Pico CSS Official Site](https://picocss.com) - Framework features, version, size

### Secondary (MEDIUM confidence)
- [python-pam on PyPI](https://pypi.org/project/python-pam/) - Version 2.0.2, pure ctypes, 249K weekly downloads
- [Flask-HTTPAuth on PyPI](https://pypi.org/project/Flask-HTTPAuth/) - Version 4.8.0, verify_password callback pattern
- [Flask on PyPI](https://pypi.org/project/Flask/) - Version 3.1.2, release date Aug 2025
- [Pillow on PyPI/piwheels](https://www.piwheels.org/project/pillow/) - ARM64 wheel availability for Raspberry Pi
- [Baeldung - Restarting Systemd Service with Specific User](https://www.baeldung.com/linux/systemd-service-restart-specific-user) - sudoers NOPASSWD pattern for systemctl
- [Miguel Grinberg - Running Flask as a Service with Systemd](https://blog.miguelgrinberg.com/post/running-a-flask-application-as-a-service-with-systemd) - systemd service file for Flask

### Tertiary (LOW confidence)
- [Aleksandr Hovhannisyan - Accessible Image Carousel](https://www.aleksandrhovhannisyan.com/blog/image-carousel-tutorial/) - Filmstrip carousel pattern (single blog post, but well-aligned with requirements)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Flask, Pillow, python-pam all verified on PyPI with current versions and ARM64 support
- Architecture: HIGH - Flask application factory + blueprints is the documented standard pattern
- Pitfalls: HIGH - PAM permissions, sudoers, caching, and thumbnail performance are well-documented issues
- Keyboard navigation: MEDIUM - Standard pattern (MDN) but implementation details are custom
- Pico CSS tabs: MEDIUM - Pico does not have a built-in tab component; tabs will need custom CSS + ARIA roles

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (30 days -- stable stack, no fast-moving dependencies)

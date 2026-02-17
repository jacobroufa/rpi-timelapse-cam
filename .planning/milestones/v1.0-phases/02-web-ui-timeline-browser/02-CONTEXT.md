# Phase 2: Web UI & Timeline Browser - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Flask web server serving a three-tab interface (Timeline, Latest Image, Control) on the local network. Users can browse captured images with keyboard-driven navigation, view the most recent capture, and manage the daemon behind PAM authentication. The filesystem of date-organized images from Phase 1 is the data source.

</domain>

<decisions>
## Implementation Decisions

### Timeline browsing
- Horizontal filmstrip of small thumbnails (100-120px) at the top of the Timeline tab
- Left/right arrow keys navigate between individual thumbnails; mouse click also selects
- Currently selected thumbnail displays as a large image below the filmstrip
- No modals, no inline expansion, no separate full-image page -- filmstrip is always visible above the selected image
- Up/down arrow keys step between days (previous/next day)
- "d" key opens a date picker for jumping to any specific day
- All navigation fully keyboard-usable

### Latest Image tab
- Renamed from "Live View" to "Latest Image" for accuracy -- this is not a live stream
- Refreshes at the configured capture interval (not faster)
- Displays the configured capture interval so the user knows how often to expect updates
- When camera is offline or daemon stopped: shows last captured image with a clear status banner
- Small timestamp overlay on the image showing when it was captured
- View-only -- no manual "capture now" button

### Page layout & navigation
- Top tab bar: Timeline | Latest Image | Control
- Desktop-first layout; mobile should be functional but not the priority
- Subtle health indicators visible on all tabs (disk usage, daemon status, last capture time)
- Hover state popup on any piece of the health indicators reveals the full set of system info
- Visual style: polished but not overdone -- clean, someone put effort into it, but not flashy or over the top

### Daemon control (Control tab)
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

</decisions>

<specifics>
## Specific Ideas

- Keyboard navigation is a priority -- the UI should feel like an image viewer application, not a typical web page
- The filmstrip + large image below pattern is similar to classic photo management tools (Lightroom library, image gallery apps)
- Health indicators should be unobtrusive -- you notice them when something is wrong, not when everything is fine
- The Control tab serves double duty: daemon management AND the "full dashboard" for system health

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02-web-ui-timeline-browser*
*Context gathered: 2026-02-16*

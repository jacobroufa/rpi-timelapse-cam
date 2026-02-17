/**
 * Control tab - daemon start/stop handlers and status polling.
 *
 * All fetch calls include credentials: "same-origin" so the browser
 * sends cached HTTP Basic Auth credentials automatically.
 */

(function () {
    "use strict";

    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const statusEl = document.getElementById("service-status");
    const messageEl = document.getElementById("action-message");

    /**
     * Update UI button states based on service status.
     */
    function updateButtonStates(status) {
        const isActive = status === "active";
        startBtn.disabled = isActive;
        stopBtn.disabled = !isActive;
    }

    /**
     * Update the service status display text and CSS class.
     */
    function updateStatusDisplay(status) {
        statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusEl.className = "service-status " + status;
    }

    /**
     * Show an inline action message (e.g. "Starting...", "Service started").
     */
    function showMessage(text, isError) {
        messageEl.textContent = text;
        messageEl.className = "action-message" + (isError ? " error" : "");
    }

    /**
     * Disable both buttons during an in-flight request.
     */
    function disableButtons() {
        startBtn.disabled = true;
        stopBtn.disabled = true;
    }

    // -- Start button handler (no confirmation needed) --
    startBtn.addEventListener("click", function () {
        showMessage("Starting...", false);
        disableButtons();

        fetch("/control/start", {
            method: "POST",
            credentials: "same-origin",
        })
            .then(function (resp) {
                return resp.json();
            })
            .then(function (data) {
                if (data.success) {
                    updateStatusDisplay(data.status);
                    updateButtonStates(data.status);
                    showMessage("Service started", false);
                } else {
                    updateButtonStates(data.status);
                    showMessage(data.message || "Failed to start", true);
                }
            })
            .catch(function (err) {
                showMessage("Error: " + err.message, true);
                // Re-fetch status to restore correct button states
                pollStatus();
            });
    });

    // -- Stop button handler (with confirmation) --
    stopBtn.addEventListener("click", function () {
        if (!confirm("Stop the capture daemon? This will interrupt image capture.")) {
            return;
        }

        showMessage("Stopping...", false);
        disableButtons();

        fetch("/control/stop", {
            method: "POST",
            credentials: "same-origin",
        })
            .then(function (resp) {
                return resp.json();
            })
            .then(function (data) {
                if (data.success) {
                    updateStatusDisplay(data.status);
                    updateButtonStates(data.status);
                    showMessage("Service stopped", false);
                } else {
                    updateButtonStates(data.status);
                    showMessage(data.message || "Failed to stop", true);
                }
            })
            .catch(function (err) {
                showMessage("Error: " + err.message, true);
                pollStatus();
            });
    });

    // -- Status polling (every 5 seconds) --
    function pollStatus() {
        fetch("/control/status", {
            credentials: "same-origin",
        })
            .then(function (resp) {
                return resp.json();
            })
            .then(function (data) {
                // Update service status
                updateStatusDisplay(data.service_status);
                updateButtonStates(data.service_status);

                // Update health values
                var h = data.health;
                var si = data.system_info;

                var diskPct = document.getElementById("disk-pct");
                var diskBar = document.getElementById("disk-bar");
                if (diskPct) {
                    diskPct.textContent = h.disk_usage_percent + "%";
                    diskPct.className = "disk-pct" + (h.disk_warning ? " warning" : "");
                }
                if (diskBar) {
                    var pct = h.disk_usage_percent >= 0 ? h.disk_usage_percent : 0;
                    diskBar.style.width = pct + "%";
                    diskBar.className = "disk-bar" + (h.disk_warning ? " warning" : "");
                }

                var diskTotal = document.getElementById("disk-total");
                var diskUsed = document.getElementById("disk-used");
                var diskFree = document.getElementById("disk-free");
                if (diskTotal) diskTotal.textContent = si.disk_total_gb + " GB";
                if (diskUsed) diskUsed.textContent = si.disk_used_gb + " GB";
                if (diskFree) diskFree.textContent = si.disk_free_gb + " GB";

                var daemonState = document.getElementById("daemon-state");
                if (daemonState) {
                    daemonState.textContent = h.daemon_state.charAt(0).toUpperCase() + h.daemon_state.slice(1);
                    daemonState.className = h.daemon_state;
                }

                var lastCapture = document.getElementById("last-capture");
                if (lastCapture) lastCapture.textContent = h.last_capture || "Never";

                var capturesToday = document.getElementById("captures-today");
                if (capturesToday) capturesToday.textContent = h.captures_today;

                var failures = document.getElementById("consecutive-failures");
                if (failures) {
                    failures.textContent = h.consecutive_failures;
                    failures.className = h.consecutive_failures > 0 ? "failure-highlight" : "";
                }

                var camera = document.getElementById("camera-type");
                if (camera) {
                    var cam = h.camera || "unknown";
                    camera.textContent = cam.charAt(0).toUpperCase() + cam.slice(1);
                }

                var uptime = document.getElementById("system-uptime");
                if (uptime) uptime.textContent = si.system_uptime;

                var daemonUptime = document.getElementById("daemon-uptime");
                if (daemonUptime) daemonUptime.textContent = h.uptime_seconds + "s";
            })
            .catch(function () {
                // Silently ignore poll errors (e.g. network issue)
            });
    }

    // Poll every 5 seconds
    setInterval(pollStatus, 5000);
})();

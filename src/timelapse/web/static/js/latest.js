/**
 * Latest Image auto-refresh polling.
 *
 * Reads the capture interval from a data attribute and polls the
 * /latest/image and /latest/status endpoints on that interval.
 * Updates the image (with cache-busting), the status banner, and
 * the capture timestamp overlay.
 */
(function () {
    "use strict";

    var configEl = document.getElementById("latest-config");
    if (!configEl) return;

    var intervalSeconds = parseInt(configEl.dataset.interval, 10) || 60;
    var intervalMs = intervalSeconds * 1000;

    var imageEl = document.getElementById("latest-image");
    var bannerEl = document.getElementById("status-banner");
    var messageEl = document.getElementById("status-message");
    var timestampEl = document.getElementById("capture-timestamp");

    /**
     * Refresh the latest image and update status.
     */
    function refreshImage() {
        // Update image src with cache-busting timestamp
        if (imageEl) {
            var newSrc = "/latest/image?t=" + Date.now();
            var tempImg = new Image();
            tempImg.onload = function () {
                imageEl.src = newSrc;
            };
            // On error, keep showing the last successfully loaded image
            tempImg.onerror = function () {
                // Silently ignore -- the current image stays visible
            };
            tempImg.src = newSrc;
        }

        // Fetch status to update banner and timestamp
        fetch("/latest/status")
            .then(function (response) {
                if (!response.ok) return null;
                return response.json();
            })
            .then(function (data) {
                if (!data) return;

                // Update status banner
                if (bannerEl && messageEl) {
                    if (data.daemon_state === "running" && data.has_image) {
                        bannerEl.style.display = "none";
                    } else if (data.daemon_state === "stopped") {
                        messageEl.textContent = "Daemon is stopped \u2014 showing last captured image";
                        bannerEl.style.display = "block";
                    } else if (data.daemon_state === "error") {
                        messageEl.textContent = "Camera offline \u2014 showing last captured image";
                        bannerEl.style.display = "block";
                    } else if (data.daemon_state === "unknown") {
                        messageEl.textContent = "Daemon status unknown \u2014 showing last captured image";
                        bannerEl.style.display = "block";
                    }
                }

                // Update timestamp overlay
                if (timestampEl && data.last_capture) {
                    timestampEl.textContent = data.last_capture;
                }
            })
            .catch(function () {
                // Network error -- keep current state, do not disrupt the UI
            });
    }

    // Start polling at the configured interval
    setInterval(refreshImage, intervalMs);
})();

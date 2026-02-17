/**
 * Timeline tab - filmstrip navigation and keyboard controls.
 *
 * State:
 *   currentIndex   - currently selected thumbnail index
 *   currentDate    - currently displayed date (YYYY-MM-DD)
 *   availableDates - array of date strings from /api/dates
 *   images         - image objects for the current day
 */

(function () {
  "use strict";

  // ── State ───────────────────────────────────────────────────────────

  let currentIndex = 0;
  let currentDate = "";
  let availableDates = [];
  let images = [];

  // ── DOM references ──────────────────────────────────────────────────

  const filmstrip = document.getElementById("filmstrip");
  const mainImage = document.getElementById("main-image");
  const timestamp = document.getElementById("image-timestamp");
  const datePicker = document.getElementById("date-picker");
  const dateDisplay = document.getElementById("current-date-display");
  const dataEl = document.getElementById("timeline-data");

  // If no filmstrip (no images page), bail out early
  if (!filmstrip) return;

  // ── Initialization ──────────────────────────────────────────────────

  function init() {
    // Read current date from data attribute
    currentDate = dataEl ? dataEl.dataset.currentDate : "";

    // Parse initial images from the server-rendered thumbnails
    images = parseImagesFromDOM();
    currentIndex = 0;

    // Fetch available dates for day navigation
    fetch("/api/dates")
      .then(function (resp) { return resp.json(); })
      .then(function (dates) {
        availableDates = dates;
      })
      .catch(function () {
        availableDates = [];
      });

    // Attach event listeners
    filmstrip.addEventListener("keydown", handleKeydown);
    filmstrip.addEventListener("click", handleClick);
    datePicker.addEventListener("change", handleDateChange);

    // Focus filmstrip so keyboard events work immediately
    filmstrip.focus();
  }

  /**
   * Parse image objects from the thumbnails already rendered in the DOM.
   */
  function parseImagesFromDOM() {
    var thumbs = filmstrip.querySelectorAll(".thumb");
    var result = [];
    for (var i = 0; i < thumbs.length; i++) {
      result.push({
        thumb_url: thumbs[i].src,
        full_url: thumbs[i].dataset.fullUrl,
        time: thumbs[i].dataset.time,
      });
    }
    return result;
  }

  // ── Navigation ──────────────────────────────────────────────────────

  /**
   * Navigate to a specific thumbnail index within the current day.
   */
  function navigateTo(index) {
    if (index < 0 || index >= images.length) return;

    var thumbs = filmstrip.querySelectorAll(".thumb");

    // Deselect current
    if (thumbs[currentIndex]) {
      thumbs[currentIndex].classList.remove("selected");
    }

    currentIndex = index;

    // Select new
    if (thumbs[currentIndex]) {
      thumbs[currentIndex].classList.add("selected");
      thumbs[currentIndex].scrollIntoView({
        behavior: "smooth",
        inline: "center",
        block: "nearest",
      });
    }

    // Update main image
    mainImage.src = images[currentIndex].full_url;
    mainImage.alt = "Capture at " + images[currentIndex].time;
    timestamp.textContent = images[currentIndex].time;
  }

  /**
   * Load a new day's images via the JSON API and rebuild the filmstrip.
   */
  function loadDay(dateStr) {
    fetch("/api/images/" + dateStr)
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.length === 0) return;

        currentDate = dateStr;
        images = data;

        // Rebuild filmstrip DOM
        filmstrip.innerHTML = "";
        for (var i = 0; i < images.length; i++) {
          var img = document.createElement("img");
          img.className = "thumb" + (i === 0 ? " selected" : "");
          img.src = images[i].thumb_url;
          img.dataset.fullUrl = images[i].full_url;
          img.dataset.index = i;
          img.dataset.time = images[i].time;
          img.loading = "lazy";
          img.alt = "Capture at " + images[i].time;
          filmstrip.appendChild(img);
        }

        // Reset to first image
        currentIndex = 0;
        mainImage.src = images[0].full_url;
        mainImage.alt = "Capture at " + images[0].time;
        timestamp.textContent = images[0].time;

        // Update date display and picker
        dateDisplay.textContent = currentDate;
        datePicker.value = currentDate;

        // Re-focus filmstrip for keyboard navigation
        filmstrip.focus();
      })
      .catch(function (err) {
        console.error("Failed to load day:", err);
      });
  }

  // ── Event Handlers ──────────────────────────────────────────────────

  function handleKeydown(e) {
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
        navigatePrevDay();
        break;

      case "ArrowDown":
        e.preventDefault();
        navigateNextDay();
        break;

      case "d":
      case "D":
        e.preventDefault();
        openDatePicker();
        break;
    }
  }

  function handleClick(e) {
    var target = e.target;
    if (!target.classList.contains("thumb")) return;

    var index = parseInt(target.dataset.index, 10);
    if (!isNaN(index)) {
      navigateTo(index);
    }
  }

  function handleDateChange() {
    var selected = datePicker.value;
    if (availableDates.indexOf(selected) !== -1) {
      loadDay(selected);
    }
  }

  function navigatePrevDay() {
    var idx = availableDates.indexOf(currentDate);
    if (idx > 0) {
      loadDay(availableDates[idx - 1]);
    }
  }

  function navigateNextDay() {
    var idx = availableDates.indexOf(currentDate);
    if (idx >= 0 && idx < availableDates.length - 1) {
      loadDay(availableDates[idx + 1]);
    }
  }

  function openDatePicker() {
    try {
      datePicker.showPicker();
    } catch (_) {
      datePicker.focus();
    }
  }

  // ── Start ───────────────────────────────────────────────────────────

  init();
})();

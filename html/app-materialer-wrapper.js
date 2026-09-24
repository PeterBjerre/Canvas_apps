(function () {
  const MODE_DRIFT = "drift";
  const MODE_PROJECT = "project";

  // Resolved once: the shell wrapper relocates these buttons into the parent
  // document's header card, so they are no longer findable from this document.
  let driftButton = null;
  let projectButton = null;

  document.addEventListener("DOMContentLoaded", initWrapper);

  function initWrapper() {
    const params = new URLSearchParams(window.location.search);
    const mode = normalizeMode(params.get("mode"));
    const embedded = isEmbedded(params.get("embed"));

    applyEmbeddedMode(embedded);

    bindModeButtons();
    applyMode(mode, true);
  }

  function isEmbedded(value) {
    const normalized = String(value == null ? "" : value).trim().toLowerCase();
    return normalized === "1" || normalized === "true" || normalized === "yes";
  }

  function applyEmbeddedMode(embedded) {
    if (!embedded) return;

    document.documentElement.setAttribute("data-embedded", "true");
    document.body.setAttribute("data-embedded", "true");
  }

  function normalizeMode(mode) {
    const value = String(mode == null ? "" : mode).trim().toLowerCase();
    if (value === "project" || value === "projekt") return MODE_PROJECT;
    return MODE_DRIFT;
  }

  function bindModeButtons() {
    driftButton = document.getElementById("btnModeDrift");
    projectButton = document.getElementById("btnModeProject");

    if (driftButton) {
      driftButton.addEventListener("click", () => {
        applyMode(MODE_DRIFT, true);
      });
    }

    if (projectButton) {
      projectButton.addEventListener("click", () => {
        applyMode(MODE_PROJECT, true);
      });
    }
  }

  function applyMode(mode, syncUrl) {
    const root = document.body;
    root.setAttribute("data-materialer-mode", mode);

    if (mode === MODE_DRIFT) {
      updateCopyForDrift();
    } else {
      updateCopyForProject();
    }

    syncModeButtons(mode);

    if (syncUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set("mode", mode);
      window.history.replaceState({}, "", url.toString());
    }
  }

  function syncModeButtons(mode) {
    if (driftButton) {
      driftButton.setAttribute("aria-pressed", mode === MODE_DRIFT ? "true" : "false");
    }

    if (projectButton) {
      projectButton.setAttribute("aria-pressed", mode === MODE_PROJECT ? "true" : "false");
    }
  }

  function updateCopyForDrift() {
    const eyebrow = document.querySelector(".eyebrow");
    if (eyebrow) {
      eyebrow.textContent = "Materialer Drift";
    }

    const heading = document.querySelector(".hero h1");
    if (heading) {
      heading.textContent = "Supplier Intake (Drift)";
    }

    const rowsHeading = document.querySelector(".rows-section .panel-head h2");
    if (rowsHeading) {
      rowsHeading.textContent = "Saved Rows";
    }

    const footerHint = document.querySelector(".foot-note p");
    if (footerHint) {
      footerHint.textContent = "Drift mode.";
    }
  }

  function updateCopyForProject() {
    const eyebrow = document.querySelector(".eyebrow");
    if (eyebrow) {
      eyebrow.textContent = "Materialer Projekt";
    }

    const heading = document.querySelector(".hero h1");
    if (heading) {
      heading.textContent = "Supplier Intake (Project)";
    }

    const rowsHeading = document.querySelector(".rows-section .panel-head h2");
    if (rowsHeading) {
      rowsHeading.textContent = "Saved Rows";
    }

    const footerHint = document.querySelector(".foot-note p");
    if (footerHint) {
      footerHint.textContent = "Project mode.";
    }
  }
})();

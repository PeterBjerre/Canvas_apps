(function () {
  document.addEventListener("DOMContentLoaded", init);

  function init() {
    setBuildDate();
    bindCardSpotlight();
  }

  function bindCardSpotlight() {
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    document.querySelectorAll(".card-grid .nav-card").forEach((card) => {
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--spot-x", `${event.clientX - rect.left}px`);
        card.style.setProperty("--spot-y", `${event.clientY - rect.top}px`);
      });
    });
  }

  function setBuildDate() {
    const node = document.getElementById("buildDate");
    if (!node) return;

    const now = new Date();
    const formatted = now.toISOString().slice(0, 10);
    node.textContent = `Build ${formatted}`;
  }
})();

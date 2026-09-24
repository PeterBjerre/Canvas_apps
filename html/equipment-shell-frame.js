(function () {
  const CHANNEL = "kv-embed";

  document.addEventListener("DOMContentLoaded", initEquipmentShellFrame);

  function initEquipmentShellFrame() {
    const frame = document.querySelector("iframe[data-equipment-frame]");
    if (!frame) return;

    const hero = document.querySelector(".site-hero");
    const emailButton = document.getElementById("btnSendEmailEquipmentShell");

    const send = (kind, action) => {
      if (!frame.contentWindow) return;
      frame.contentWindow.postMessage({ channel: CHANNEL, kind, action }, "*");
    };

    if (emailButton) {
      emailButton.disabled = true;
      emailButton.addEventListener("click", () => send("command", "send-email"));
    }

    document.querySelectorAll("[data-shell-command]").forEach((button) => {
      button.addEventListener("click", () => send("command", button.dataset.shellCommand));
    });

    // Every file:// document gets its own opaque origin, so the origin string is
    // always "null" here and the frame has to be identified by its window.
    window.addEventListener("message", (event) => {
      if (event.source !== frame.contentWindow) return;

      const data = event.data;
      if (!data || data.channel !== CHANNEL) return;

      if (data.kind === "height" && data.height > 0) {
        frame.style.height = `${data.height}px`;
        return;
      }

      if (data.kind === "state") applyState(data);
    });

    frame.addEventListener("load", () => send("sync"));
    send("sync");

    function applyState(state) {
      if (hero) {
        setCounter("rows", state.rows);
        setCounter("valid", state.valid);
        setCounter("invalid", state.invalid);

        const proxy = hero.querySelector('[data-shell-command="toggle-proxy"]');
        if (proxy) {
          if (state.proxyLabel) proxy.textContent = state.proxyLabel;
          proxy.setAttribute("aria-pressed", state.proxyOn ? "true" : "false");
        }

        const exportCsv = hero.querySelector('[data-shell-command="export-csv"]');
        if (exportCsv) exportCsv.disabled = state.canExport === false;
      }

      if (emailButton) emailButton.disabled = state.canEmail === false;
    }

    function setCounter(name, value) {
      const node = hero.querySelector(`[data-shell-kpi="${name}"]`);
      if (node && typeof value === "string") node.textContent = value;
    }
  }
})();

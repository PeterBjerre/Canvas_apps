(function () {
  const CHANNEL = "kv-embed";

  // Browsers give every file:// document its own opaque origin, so the wrapper
  // page cannot reach into this one. Everything the page header needs is pushed
  // out over postMessage instead, and commands come back the same way.
  const COMMAND_TARGETS = {
    "export-csv": ["btnExportCsv"],
    "toggle-proxy": ["btnLocalProxy"],
    "send-email": ["btnSendEmailMaterialer", "btnSendEmailEquipment"]
  };

  const params = new URLSearchParams(window.location.search);
  const embedRaw = String(params.get("embed") || "").toLowerCase();
  const embedded = embedRaw === "1" || embedRaw === "true" || embedRaw === "yes";

  if (!embedded || window.parent === window) return;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    document.documentElement.setAttribute("data-embedded", "true");
    document.body.setAttribute("data-embedded", "true");

    const emailButton = resolveCommand("send-email");
    if (emailButton) emailButton.style.display = "none";

    let lastState = "";
    let lastHeight = 0;

    const post = (payload) => {
      payload.channel = CHANNEL;
      window.parent.postMessage(payload, "*");
    };

    const publishHeight = () => {
      const height = measureHeight();
      if (height <= 0 || height === lastHeight) return;
      lastHeight = height;
      post({ kind: "height", height });
    };

    const publishState = () => {
      const state = readState();
      const encoded = JSON.stringify(state);
      if (encoded === lastState) return;
      lastState = encoded;
      state.kind = "state";
      post(state);
    };

    const publish = () => {
      publishState();
      publishHeight();
    };

    observeSize(publishHeight);
    observeState(publishState);

    window.addEventListener("message", (event) => {
      if (event.source !== window.parent) return;

      const data = event.data;
      if (!data || data.channel !== CHANNEL) return;

      if (data.kind === "sync") {
        lastState = "";
        lastHeight = 0;
        publish();
        return;
      }

      if (data.kind !== "command") return;

      const target = resolveCommand(data.action);
      if (target) target.click();
    });

    window.addEventListener("load", publish);
    publish();
  }

  function readState() {
    const proxy = document.getElementById("btnLocalProxy");

    return {
      rows: readCounter("kpiRows"),
      valid: readCounter("kpiValid"),
      invalid: readCounter("kpiInvalid"),
      proxyLabel: proxy ? proxy.textContent.trim() : "",
      proxyOn: proxy ? proxy.getAttribute("aria-pressed") === "true" : false,
      mode: document.body.getAttribute("data-materialer-mode") || "",
      canEmail: resolveCommand("send-email") != null,
      canExport: resolveCommand("export-csv") != null
    };
  }

  function readCounter(id) {
    const node = document.getElementById(id);
    return node ? node.textContent.trim() : "0";
  }

  function resolveCommand(action) {
    const ids = COMMAND_TARGETS[action];
    if (!ids) return null;

    for (const id of ids) {
      const node = document.getElementById(id);
      if (node) return node;
    }

    return null;
  }

  function measureHeight() {
    const shell = document.querySelector(".app-shell");
    let height = 0;

    if (shell) {
      const computed = getComputedStyle(shell);
      const marginTop = parseFloat(computed.marginTop) || 0;
      const marginBottom = parseFloat(computed.marginBottom) || 0;
      height = Math.ceil(shell.getBoundingClientRect().height + marginTop + marginBottom);
    }

    return Math.max(height, document.body.scrollHeight, document.documentElement.scrollHeight);
  }

  function observeSize(callback) {
    if (typeof ResizeObserver !== "function") {
      window.addEventListener("resize", callback);
      return;
    }

    const observer = new ResizeObserver(callback);
    observer.observe(document.documentElement);
    observer.observe(document.body);

    const shell = document.querySelector(".app-shell");
    if (shell) observer.observe(shell);
  }

  // Only the nodes the page header mirrors are watched; observing the whole
  // document would fire on every keystroke and every table repaint.
  function observeState(callback) {
    const observer = new MutationObserver(callback);
    const options = { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ["aria-pressed"] };

    ["kpiRows", "kpiValid", "kpiInvalid", "btnLocalProxy"].forEach((id) => {
      const node = document.getElementById(id);
      if (node) observer.observe(node, options);
    });

    observer.observe(document.body, { attributes: true, attributeFilter: ["data-materialer-mode"] });
  }
})();

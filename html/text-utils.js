(function () {
  function toText(value) {
    return value == null ? "" : String(value).trim();
  }

  function normalizeUpper(value) {
    return toText(value).toUpperCase();
  }

  function clipText(value, maxLength) {
    const text = toText(value);
    if (!text || text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(0, maxLength - 3))}...`;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  window.TextUtils = Object.freeze({ toText, normalizeUpper, clipText, escapeHtml });
})();

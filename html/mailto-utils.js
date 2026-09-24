(function () {
  const { toText, clipText } = window.TextUtils;

  function buildMailtoHref(recipient, subject, body) {
    const target = toText(recipient).replace(/[\r\n]/g, "");
    const safeSubject = toText(subject);
    const safeBody = toText(body);
    return `mailto:${target}?subject=${encodeURIComponent(safeSubject)}&body=${encodeURIComponent(safeBody)}`;
  }

  function finalizeMailtoHref(options) {
    const recipient = toText(options && options.recipient);
    const subject = toText(options && options.subject);
    const detailedBody = toText(options && options.detailedBody);
    const summaryBody = toText(options && options.summaryBody) || detailedBody;
    const maxUrlLength = Number(options && options.maxUrlLength) || 1850;
    const minBodyLength = Number(options && options.minBodyLength) || 220;
    const trimRatio = Number(options && options.trimRatio) || 0.82;
    const truncationNote = toText(options && options.truncationNote) || "[truncated]";

    if (!recipient || !subject || !detailedBody) {
      return { ok: false, mode: "failed", href: "" };
    }

    let body = detailedBody;
    let href = buildMailtoHref(recipient, subject, body);
    let mode = "full";

    if (href.length > maxUrlLength) {
      body = summaryBody;
      href = buildMailtoHref(recipient, subject, body);
      mode = "summary";
    }

    while (href.length > maxUrlLength && body.length > minBodyLength) {
      body = `${clipText(body, Math.max(120, Math.floor(body.length * trimRatio))).trim()}\n\n${truncationNote}`;
      href = buildMailtoHref(recipient, subject, body);
      mode = "trimmed";
    }

    if (href.length > maxUrlLength) {
      return { ok: false, mode: "failed", href: "" };
    }

    return { ok: true, mode, href };
  }

  window.MailtoUtils = {
    clipText,
    buildMailtoHref,
    finalizeMailtoHref,
  };
})();

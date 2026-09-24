(function (global) {
  "use strict";

  const MARK_CLASS = "req-mark";
  const TEXT_HOST_CLASS = "req-label";
  const SCOPE_SELECTOR = "label, .form-block";
  const CONTROL_SELECTOR = "input:not([type='hidden']):not([type='file']), select, textarea";

  function resolveScope(node) {
    if (!(node instanceof Element)) return null;
    if (node.matches(SCOPE_SELECTOR)) return node;
    return node.closest(SCOPE_SELECTOR);
  }

  function resolveLabel(scope) {
    if (scope.tagName === "LABEL") return scope;
    return scope.querySelector("label");
  }

  // The label text is a bare text node; wrapping it keeps text and marker on one
  // line inside the column-flex labels used by the equipment/materialer grids.
  function ensureTextHost(label) {
    const existing = label.querySelector(`:scope > .${TEXT_HOST_CLASS}`);
    if (existing) return existing;

    const leading = [];
    for (const node of Array.from(label.childNodes)) {
      if (node.nodeType !== Node.TEXT_NODE) break;
      leading.push(node);
    }

    const host = document.createElement("span");
    host.className = TEXT_HOST_CLASS;
    host.textContent = leading.map((node) => node.textContent).join("").trim();
    leading.forEach((node) => node.remove());
    label.insertBefore(host, label.firstChild);
    return host;
  }

  function set(target, isRequired) {
    const scope = resolveScope(target);
    if (!scope) return;

    const required = !!isRequired;
    const control = target instanceof Element && target.matches(CONTROL_SELECTOR)
      ? target
      : scope.querySelector(CONTROL_SELECTOR);

    if (control) {
      control.setAttribute("aria-required", required ? "true" : "false");
    }

    scope.setAttribute("data-required", required ? "true" : "false");

    const label = resolveLabel(scope);
    if (!label) return;

    const host = ensureTextHost(label);
    const mark = host.querySelector(`.${MARK_CLASS}`);

    if (required && !mark) {
      const node = document.createElement("span");
      node.className = MARK_CLASS;
      node.setAttribute("aria-hidden", "true");
      node.textContent = "*";
      host.appendChild(node);
      return;
    }

    if (!required && mark) mark.remove();
  }

  function apply(root) {
    const scope = root instanceof Element ? root : document;
    scope.querySelectorAll('[data-required="true"]').forEach((node) => set(node, true));
  }

  global.RequiredFields = { set, apply };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => apply());
  } else {
    apply();
  }
}(window));

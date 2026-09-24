/* Shared application shell: navigation rail, command palette and density control.
   Additive only. It reads existing markup and never mutates application state. */
(function () {
  "use strict";

  const DENSITY_KEY = "kelvin.density";
  const DENSITY_VALUES = ["comfortable", "compact", "condensed"];
  const MAX_INDEXED_ROWS = 2000;

  const NAV_ITEMS = [
    { key: "home", label: "Forside", href: "index.html", hint: "Oversigt over alle moduler", icon: "M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5" },
    { key: "functional-location", label: "Functional Location", href: "functional-location.html", hint: "KKS-syntaks og klassebestemmelse", icon: "M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" },
    { key: "vh-plan", label: "VH-plan", href: "vh-plan.html", hint: "Planlægning og vedligehold", icon: "M4 6.5h16M4 12h16M4 17.5h10 M17.5 16.5l1.6 1.6 3-3.2" },
    { key: "materialer", label: "Materialer", href: "materialer.html", hint: "Projekt- og driftmaterialer", icon: "M12 3 21 8v8l-9 5-9-5V8l9-5Z M3 8l9 5 9-5 M12 13v8" },
    { key: "equipment", label: "Equipment", href: "equipment.html", hint: "Oprettelse af equipment", icon: "M7 7h10v10H7z M4.5 10.5h2.5M4.5 13.5h2.5M17 10.5h2.5M17 13.5h2.5M10.5 4.5V7M13.5 4.5V7M10.5 17v2.5M13.5 17v2.5" },
    { key: "kks", label: "KKS", href: "kks-kks.html", hint: "KKS-opslag og nøgler", icon: "M4 5h7v7H4z M13 5h7v7h-7z M4 14h7v5H4z M13 14h7v5h-7z" },
    { key: "vgb", label: "VGB", href: "vgb-aggregat.html", hint: "VGB aggregat- og komponentnøgle", icon: "M5 4h11l3 3v13H5z M16 4v3h3 M8.5 12h7M8.5 15.5h5" },
    { key: "faq", label: "FAQ", href: "faq.html", hint: "Ofte stillede spørgsmål", icon: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M9.5 9.5a2.5 2.5 0 1 1 3.2 2.4c-.6.2-1 .8-1 1.4v.4 M12 16.8h.01" },
  ];

  const SVG_NS = "http://www.w3.org/2000/svg";

  let paletteRoot = null;
  let paletteInput = null;
  let paletteList = null;
  let paletteItems = [];
  let paletteIndex = 0;
  let lastFocused = null;
  let rowIndexCache = null;

  function isEmbedded() {
    if (document.body.dataset.embedded === "true") return true;
    return new URLSearchParams(window.location.search).get("embed") === "1";
  }

  function readStoredDensity() {
    try {
      const stored = window.localStorage.getItem(DENSITY_KEY);
      return DENSITY_VALUES.includes(stored) ? stored : "comfortable";
    } catch (_error) {
      return "comfortable";
    }
  }

  function syncDensityButtons() {
    const density = document.documentElement.dataset.density || "comfortable";
    document.querySelectorAll("[data-density-value]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.densityValue === density));
    });
  }

  function applyDensity(value, persist) {
    const density = DENSITY_VALUES.includes(value) ? value : "comfortable";
    document.documentElement.dataset.density = density;

    syncDensityButtons();

    if (!persist) return;
    try {
      window.localStorage.setItem(DENSITY_KEY, density);
    } catch (_error) {
      /* Storage unavailable; density stays for this page only. */
    }
  }

  function svgIcon(path) {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    path.split(" M").forEach((segment, index) => {
      const node = document.createElementNS(SVG_NS, "path");
      node.setAttribute("d", index === 0 ? segment : `M${segment}`);
      svg.appendChild(node);
    });
    return svg;
  }

  function buildRail(currentPage) {
    const rail = document.createElement("nav");
    rail.className = "kv-rail";
    rail.setAttribute("aria-label", "Primær navigation");

    const brand = document.createElement("a");
    brand.className = "kv-rail-brand";
    brand.href = "index.html";
    brand.setAttribute("aria-label", "BIO SAP forside");

    const mark = document.createElement("span");
    mark.className = "kv-rail-mark";
    mark.setAttribute("aria-hidden", "true");
    mark.textContent = "BS";

    const wordmark = document.createElement("span");
    wordmark.className = "kv-rail-wordmark";
    wordmark.textContent = "BIO SAP";

    brand.append(mark, wordmark);

    const list = document.createElement("ul");
    list.className = "kv-rail-list";

    NAV_ITEMS.forEach((item) => {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.className = "kv-rail-item";
      link.href = item.href;
      link.dataset.nav = item.key;
      // The visible label is clipped while the rail is collapsed.
      link.setAttribute("aria-label", item.label);
      link.title = item.label;

      const icon = document.createElement("span");
      icon.className = "kv-rail-icon";
      icon.appendChild(svgIcon(item.icon));

      const label = document.createElement("span");
      label.className = "kv-rail-label";
      label.textContent = item.label;

      link.append(icon, label);

      if (item.key === currentPage) {
        link.setAttribute("aria-current", "page");
      }

      li.appendChild(link);
      list.appendChild(li);
    });

    const foot = document.createElement("div");
    foot.className = "kv-rail-foot";
    foot.append(buildPaletteButton(), buildDensityControl());

    rail.append(brand, list, foot);
    return rail;
  }

  function buildPaletteButton() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "kv-rail-item";
    button.dataset.kvAction = "palette";
    button.setAttribute("aria-label", "Åbn søgning og kommandopalette");
    button.title = "Søg (Ctrl+K)";

    const icon = document.createElement("span");
    icon.className = "kv-rail-icon";
    icon.appendChild(svgIcon("M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z M20 20l-4-4"));

    const label = document.createElement("span");
    label.className = "kv-rail-label";
    label.textContent = "Søg";

    const kbd = document.createElement("kbd");
    kbd.className = "kv-rail-kbd";
    kbd.textContent = "Ctrl K";

    button.append(icon, label, kbd);
    button.addEventListener("click", openPalette);
    return button;
  }

  function buildDensityControl() {
    const wrap = document.createElement("div");
    wrap.className = "kv-density";

    const group = document.createElement("div");
    group.className = "kv-density-group";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Tæthed");

    const DENSITY_BARS = { comfortable: 2, compact: 3, condensed: 4 };
    const DENSITY_LABELS = { comfortable: "Luftig", compact: "Kompakt", condensed: "Tæt" };

    DENSITY_VALUES.forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "kv-density-btn";
      button.dataset.densityValue = value;
      button.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-label", `Tæthed: ${DENSITY_LABELS[value]}`);
      button.title = DENSITY_LABELS[value];

      for (let index = 0; index < DENSITY_BARS[value]; index += 1) {
        const bar = document.createElement("i");
        bar.setAttribute("aria-hidden", "true");
        button.appendChild(bar);
      }

      button.addEventListener("click", () => applyDensity(value, true));
      group.appendChild(button);
    });

    const label = document.createElement("span");
    label.className = "kv-density-label";
    label.textContent = "Tæthed";

    wrap.append(group, label);
    return wrap;
  }

  /* ------------------------------------------------------- palette */

  function buildPalette() {
    const backdrop = document.createElement("div");
    backdrop.className = "kv-palette-backdrop";
    backdrop.hidden = true;

    const dialog = document.createElement("div");
    dialog.className = "kv-palette";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", "Kommandopalette");

    const inputWrap = document.createElement("div");
    inputWrap.className = "kv-palette-input-wrap";
    inputWrap.appendChild(svgIcon("M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z M20 20l-4-4"));

    paletteInput = document.createElement("input");
    paletteInput.type = "text";
    paletteInput.className = "kv-palette-input";
    paletteInput.setAttribute("role", "combobox");
    paletteInput.setAttribute("aria-expanded", "true");
    paletteInput.setAttribute("aria-controls", "kvPaletteList");
    paletteInput.setAttribute("aria-autocomplete", "list");
    paletteInput.setAttribute("autocomplete", "off");
    paletteInput.setAttribute("spellcheck", "false");
    paletteInput.placeholder = "Søg sider, handlinger og rækker på siden…";

    const esc = document.createElement("kbd");
    esc.textContent = "Esc";

    inputWrap.append(paletteInput, esc);

    paletteList = document.createElement("ul");
    paletteList.className = "kv-palette-list";
    paletteList.id = "kvPaletteList";
    paletteList.setAttribute("role", "listbox");

    const foot = document.createElement("div");
    foot.className = "kv-palette-foot";
    foot.append(
      hintNode("↑ ↓", "naviger"),
      hintNode("Enter", "vælg"),
      hintNode("Esc", "luk")
    );

    dialog.append(inputWrap, paletteList, foot);
    backdrop.appendChild(dialog);

    backdrop.addEventListener("mousedown", (event) => {
      if (event.target === backdrop) closePalette();
    });

    paletteInput.addEventListener("input", () => renderPalette(paletteInput.value));
    paletteInput.addEventListener("keydown", onPaletteKeydown);

    return backdrop;
  }

  function hintNode(keyText, description) {
    const span = document.createElement("span");
    const kbd = document.createElement("kbd");
    kbd.textContent = keyText;
    span.append(kbd, document.createTextNode(description));
    return span;
  }

  function collectPageActions() {
    const selector = ".hero-actions button, .panel-head button, .form-head-actions button, .material-table-toolbar button, .hero-action-row a";
    const seen = new Set();
    const actions = [];

    document.querySelectorAll(selector).forEach((element) => {
      const label = (element.textContent || "").trim().replace(/\s+/g, " ");
      if (!label || label.length > 60 || seen.has(label)) return;
      if (element.disabled || element.closest("[hidden]")) return;
      seen.add(label);
      actions.push({
        title: label,
        sub: "Handling på denne side",
        run: () => element.click(),
      });
    });

    return actions;
  }

  /* Rows are indexed once per open so typing stays responsive on large tables. */
  function collectPageRows() {
    if (rowIndexCache) return rowIndexCache;

    const rows = [];
    document.querySelectorAll("table tbody tr").forEach((tr) => {
      if (rows.length >= MAX_INDEXED_ROWS) return;
      const text = (tr.textContent || "").trim().replace(/\s+/g, " ");
      if (!text) return;
      const firstCell = tr.querySelector("td");
      rows.push({
        title: firstCell ? (firstCell.textContent || "").trim() || text.slice(0, 60) : text.slice(0, 60),
        sub: text.slice(0, 120),
        haystack: text.toLowerCase(),
        element: tr,
      });
    });

    rowIndexCache = rows;
    return rows;
  }

  function scoreMatch(haystack, query) {
    const index = haystack.indexOf(query);
    if (index < 0) return -1;
    return index === 0 ? 0 : 1;
  }

  function highlight(text, query) {
    const fragment = document.createDocumentFragment();
    if (!query) {
      fragment.appendChild(document.createTextNode(text));
      return fragment;
    }

    const lower = text.toLowerCase();
    let cursor = 0;

    for (;;) {
      const found = lower.indexOf(query, cursor);
      if (found < 0) break;
      if (found > cursor) {
        fragment.appendChild(document.createTextNode(text.slice(cursor, found)));
      }
      const mark = document.createElement("mark");
      mark.textContent = text.slice(found, found + query.length);
      fragment.appendChild(mark);
      cursor = found + query.length;
    }

    if (cursor < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(cursor)));
    }
    return fragment;
  }

  function buildGroups(rawQuery) {
    const query = rawQuery.trim().toLowerCase();
    const groups = [];

    const navMatches = NAV_ITEMS
      .map((item) => ({ item, score: scoreMatch(`${item.label} ${item.hint}`.toLowerCase(), query) }))
      .filter((entry) => !query || entry.score >= 0)
      .slice(0, 8)
      .map((entry) => ({
        title: entry.item.label,
        sub: entry.item.hint,
        run: () => { window.location.href = entry.item.href; },
      }));

    if (navMatches.length) groups.push({ label: "Gå til", items: navMatches });

    const actionMatches = collectPageActions()
      .filter((action) => !query || action.title.toLowerCase().includes(query))
      .slice(0, 6);

    if (actionMatches.length) groups.push({ label: "Handlinger", items: actionMatches });

    if (query.length >= 2) {
      const rowMatches = collectPageRows()
        .filter((row) => row.haystack.includes(query))
        .slice(0, 20)
        .map((row) => ({
          title: row.title,
          sub: row.sub,
          run: () => {
            row.element.scrollIntoView({ block: "center", behavior: "smooth" });
            row.element.classList.remove("kv-flash");
            void row.element.offsetWidth;
            row.element.classList.add("kv-flash");
          },
        }));

      if (rowMatches.length) groups.push({ label: "Rækker på siden", items: rowMatches });
    }

    return { groups, query };
  }

  function renderPalette(rawQuery) {
    const { groups, query } = buildGroups(rawQuery || "");
    paletteList.textContent = "";
    paletteItems = [];

    if (!groups.length) {
      const empty = document.createElement("li");
      empty.className = "kv-palette-empty";
      empty.textContent = "Ingen resultater";
      paletteList.appendChild(empty);
      return;
    }

    groups.forEach((group) => {
      const heading = document.createElement("li");
      heading.className = "kv-palette-group";
      heading.setAttribute("role", "presentation");
      heading.textContent = group.label;
      paletteList.appendChild(heading);

      group.items.forEach((entry) => {
        const li = document.createElement("li");
        li.className = "kv-palette-item";
        li.setAttribute("role", "option");
        li.id = `kvPaletteItem${paletteItems.length}`;

        const body = document.createElement("span");
        body.className = "kv-palette-body";

        const title = document.createElement("span");
        title.className = "kv-palette-title";
        title.appendChild(highlight(entry.title, query));

        body.appendChild(title);

        if (entry.sub) {
          const sub = document.createElement("span");
          sub.className = "kv-palette-sub";
          sub.appendChild(highlight(entry.sub, query));
          body.appendChild(sub);
        }

        li.appendChild(body);
        li.addEventListener("mousemove", () => setPaletteIndex(paletteItems.indexOf(li)));
        li.addEventListener("click", () => {
          closePalette();
          entry.run();
        });

        li.__run = entry.run;
        paletteItems.push(li);
        paletteList.appendChild(li);
      });
    });

    setPaletteIndex(0);
  }

  function setPaletteIndex(next) {
    if (!paletteItems.length) return;
    paletteIndex = (next + paletteItems.length) % paletteItems.length;

    paletteItems.forEach((item, index) => {
      const selected = index === paletteIndex;
      item.setAttribute("aria-selected", String(selected));
      if (selected) {
        paletteInput.setAttribute("aria-activedescendant", item.id);
        item.scrollIntoView({ block: "nearest" });
      }
    });
  }

  function onPaletteKeydown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setPaletteIndex(paletteIndex + 1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setPaletteIndex(paletteIndex - 1);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const active = paletteItems[paletteIndex];
      if (!active) return;
      closePalette();
      active.__run();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closePalette();
    }
  }

  function openPalette() {
    if (!paletteRoot || !paletteRoot.hidden) return;
    lastFocused = document.activeElement;
    rowIndexCache = null;
    paletteRoot.hidden = false;
    paletteInput.value = "";
    renderPalette("");
    paletteInput.focus();
  }

  function closePalette() {
    if (!paletteRoot || paletteRoot.hidden) return;
    paletteRoot.hidden = true;
    rowIndexCache = null;
    if (lastFocused && document.contains(lastFocused)) {
      lastFocused.focus();
    }
    lastFocused = null;
  }

  function isTypingTarget(target) {
    if (!target) return false;
    const tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
  }

  function onGlobalKeydown(event) {
    const isPaletteChord = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";
    if (isPaletteChord) {
      event.preventDefault();
      if (paletteRoot.hidden) openPalette();
      else closePalette();
      return;
    }

    if (event.key === "/" && paletteRoot.hidden && !isTypingTarget(event.target)) {
      event.preventDefault();
      openPalette();
    }
  }

  function addSkipLink(main) {
    if (!main) return;
    if (!main.id) main.id = "kvMain";
    main.setAttribute("role", "main");
    main.setAttribute("tabindex", "-1");

    const skip = document.createElement("a");
    skip.className = "kv-skip";
    skip.href = `#${main.id}`;
    skip.textContent = "Spring til indhold";
    document.body.insertBefore(skip, document.body.firstChild);
  }

  function init() {
    applyDensity(readStoredDensity(), false);

    // Keeps embedded app frames in sync when density changes in the parent.
    window.addEventListener("storage", (event) => {
      if (event.key === DENSITY_KEY && event.newValue) applyDensity(event.newValue, false);
    });

    if (isEmbedded()) return;

    const currentPage = document.body.dataset.page || "";
    document.body.dataset.shell = "rail";

    const main = document.querySelector(".site-shell, .app-shell");
    addSkipLink(main);

    document.body.appendChild(buildRail(currentPage));
    syncDensityButtons();

    paletteRoot = buildPalette();
    document.body.appendChild(paletteRoot);

    document.addEventListener("keydown", onGlobalKeydown);
  }

  window.KelvinShell = {
    openPalette,
    closePalette,
    setDensity: (value) => applyDensity(value, true),
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

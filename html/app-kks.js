(function () {
  const { toText, normalizeUpper, escapeHtml } = window.TextUtils;

  const ORDER = ["HOME", "A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];
  const SOURCE = Array.isArray(window.KKS_DATA) ? window.KKS_DATA : [];
  const LEVEL3_ENABLED = !document.body || document.body.dataset.kksDetail !== "off";
  const BILINGUAL_LAYOUT = !!(document.body && document.body.dataset && document.body.dataset.page === "vgb");
  const VGB_SECTION_MODE = toText(document.body && document.body.dataset ? document.body.dataset.vgbSection : "").toLowerCase();

  const MODEL = buildModel(SOURCE);
  const INITIAL_LEVEL1 = "ALL";

  const state = {
    query: "",
    searchLanguage: "da",
    level1: INITIAL_LEVEL1 || "ALL",
    level2: "",
    level3: "",
    navMode: "classic",
    suggestions: [],
    activeSuggestionIndex: -1,
    history: [],
    historyIndex: -1,
    suppressHistoryPush: false,
    lastSnapshot: "",
  };

  const dom = {};

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    bindDom();
    bindEvents();
    render();
    commitHistorySnapshot();
  }

  function bindDom() {
    dom.search = document.getElementById("kksSearch");
    dom.suggestions = document.getElementById("kksSearchSuggestions");
    dom.level1Row = document.getElementById("kksLevel1Row");
    dom.level2Row = document.getElementById("kksLevel2Row");
    dom.level3Row = document.getElementById("kksLevel3Row");
    dom.path = document.getElementById("kksPath");
    dom.previewTitle = document.getElementById("kksPreviewTitle");
    dom.rowsBody = document.getElementById("kksRowsBody");
    dom.rowsEmpty = document.getElementById("kksRowsEmpty");
    dom.modeClassic = document.getElementById("kksNavModeClassic");
    dom.modeExplorer = document.getElementById("kksNavModeExplorer");
    dom.classicShell = document.getElementById("kksClassicShell");
    dom.explorerShell = document.getElementById("kksExplorerShell");
    dom.explorerBack = document.getElementById("kksExplorerBack");
    dom.explorerForward = document.getElementById("kksExplorerForward");
    dom.explorerUp = document.getElementById("kksExplorerUp");
    dom.explorerCrumbs = document.getElementById("kksExplorerCrumbs");
    dom.explorerNodes = document.getElementById("kksExplorerNodes");
    dom.searchRail = document.getElementById("kksSearchRail");
  }

  function bindEvents() {
    if (dom.search) {
      dom.search.addEventListener("input", onSearchInput);
      dom.search.addEventListener("keydown", onSearchKeyDown);
      dom.search.addEventListener("focus", render);
      dom.search.addEventListener("blur", () => {
        window.setTimeout(hideSearchSuggestions, 120);
      });
    }

    [dom.level1Row, dom.level2Row, dom.level3Row].forEach((row) => {
      if (!row) return;
      row.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const button = target.closest("button[data-level][data-value]");
        if (!(button instanceof HTMLButtonElement)) return;
        if (button.disabled) return;

        const level = Number(button.getAttribute("data-level"));
        const value = normalizeUpper(button.getAttribute("data-value"));

        if (level === 1) {
          state.level1 = value || "ALL";
          state.level2 = "";
          state.level3 = "";
        } else if (level === 2) {
          state.level2 = value;
          state.level3 = "";
        } else if (level === 3 && LEVEL3_ENABLED) {
          state.level3 = value;
        }

        render();
        commitHistorySnapshot();
      });
    });

    [dom.modeClassic, dom.modeExplorer].forEach((button) => {
      if (!button) return;
      button.addEventListener("click", () => {
        const mode = toText(button.getAttribute("data-mode"));
        if (!mode || mode === state.navMode) return;
        setNavMode(mode);
      });
    });

    if (dom.explorerShell) {
      dom.explorerShell.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const actionButton = target.closest("button[data-action]");
        if (actionButton instanceof HTMLButtonElement) {
          const action = toText(actionButton.getAttribute("data-action"));
          if (action === "back") {
            navigateHistory(-1);
            return;
          }
          if (action === "forward") {
            navigateHistory(1);
            return;
          }
          if (action === "up") {
            navigateUp();
            return;
          }
        }

        const crumbButton = target.closest("button[data-crumb]");
        if (crumbButton instanceof HTMLButtonElement) {
          const depth = Number(crumbButton.getAttribute("data-crumb"));
          applyCrumb(depth);
          return;
        }

        const nodeButton = target.closest("button[data-node-level][data-node-value]");
        if (nodeButton instanceof HTMLButtonElement) {
          applyExplorerNode(nodeButton);
        }
      });
    }

    if (dom.path) {
      dom.path.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const button = target.closest("button[data-action]");
        if (!(button instanceof HTMLButtonElement)) return;

        const action = toText(button.getAttribute("data-action"));
        if (action === "search-lang") {
          const lang = toText(button.getAttribute("data-lang")).toLowerCase();
          const nextLang = lang === "de" ? "de" : "da";
          if (nextLang !== state.searchLanguage) {
            state.searchLanguage = nextLang;
            render();
          }
          return;
        }

        if (action !== "reset-nav") return;

        resetNavigation();
        commitHistorySnapshot();
      });
    }

    if (dom.suggestions) {
      dom.suggestions.addEventListener("mousedown", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const button = target.closest("button[data-suggestion-index]");
        if (!(button instanceof HTMLButtonElement)) return;

        event.preventDefault();
        const index = Number(button.getAttribute("data-suggestion-index"));
        applySuggestionByIndex(index);
      });
    }

    if (dom.rowsBody) {
      dom.rowsBody.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const row = target.closest("tr[data-source]");
        if (!(row instanceof HTMLTableRowElement)) return;

        navigateToRowSource(row);
      });

      dom.rowsBody.addEventListener("keydown", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (event.key !== "Enter" && event.key !== " ") return;

        const row = target.closest("tr[data-source]");
        if (!(row instanceof HTMLTableRowElement)) return;

        event.preventDefault();
        navigateToRowSource(row);
      });
    }
  }

  function onSearchInput() {
    if (!dom.search) return;
    state.query = toText(dom.search.value);
    state.activeSuggestionIndex = -1;
    render();
  }

  function onSearchKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveSuggestion(1);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      moveSuggestion(-1);
      return;
    }

    if (event.key === "Enter") {
      if (state.activeSuggestionIndex >= 0) {
        event.preventDefault();
        applySuggestionByIndex(state.activeSuggestionIndex);
      } else if (state.suggestions.length === 1) {
        event.preventDefault();
        applySuggestionByIndex(0);
      }
      return;
    }

    if (event.key === "Escape") {
      hideSearchSuggestions();
    }
  }

  function render() {
    if (!LEVEL3_ENABLED && state.level3) {
      state.level3 = "";
    }

    renderLevel1();
    renderLevel2();
    renderLevel3();
    renderPath();
    renderSearchInputMeta();
    renderModeShells();
    renderExplorer();
    renderRows();
    syncSuggestionsPanel();
    syncModeButtons();
  }

  function renderSearchInputMeta() {
    if (!dom.search || !BILINGUAL_LAYOUT) return;

    const useGerman = state.searchLanguage === "de";
    const placeholder = useGerman ? "Søg VGB kode eller Tysk term" : "Søg VGB kode eller Dansk term";
    dom.search.placeholder = placeholder;
    dom.search.setAttribute("aria-label", placeholder);
  }

  function renderModeShells() {
    const explorerMode = state.navMode === "explorer";
    if (dom.classicShell) {
      dom.classicShell.hidden = explorerMode;
    }
    if (dom.explorerShell) {
      dom.explorerShell.hidden = !explorerMode;
    }
    if (dom.searchRail) {
      dom.searchRail.hidden = explorerMode;
    }
  }

  function syncModeButtons() {
    if (dom.modeClassic) {
      dom.modeClassic.setAttribute("aria-pressed", String(state.navMode === "classic"));
    }
    if (dom.modeExplorer) {
      dom.modeExplorer.setAttribute("aria-pressed", String(state.navMode === "explorer"));
    }
  }

  function renderLevel1() {
    if (!dom.level1Row) return;

    const keys = MODEL.level1Keys.filter((key) => key !== "HOME");
    if (shouldSplitComponentLevel1Groups(keys)) {
      dom.level1Row.innerHTML = buildComponentLevel1Layout(keys);
      return;
    }

    dom.level1Row.innerHTML = ["ALL", ...keys]
      .map((key) => buildLevel1ButtonHtml(key))
      .join("");
  }

  function shouldSplitComponentLevel1Groups(keys) {
    if (!BILINGUAL_LAYOUT || VGB_SECTION_MODE !== "component") return false;
    return keys.some((key) => isSymbolLevel1Key(key));
  }

  function buildComponentLevel1Layout(keys) {
    const letterKeys = [];
    const symbolKeys = [];
    const otherKeys = [];

    keys.forEach((key) => {
      if (isLetterLevel1Key(key)) {
        letterKeys.push(key);
        return;
      }
      if (isSymbolLevel1Key(key)) {
        symbolKeys.push(key);
        return;
      }
      otherKeys.push(key);
    });

    const parts = [buildLevel1ButtonHtml("ALL")];
    if (symbolKeys.length) {
      parts.push(buildLevel1ClusterHtml(symbolKeys, "symbol", "Med bindestreg"));
    }
    if (letterKeys.length) {
      parts.push(buildLevel1ClusterHtml(letterKeys, "plain", "Uden bindestreg"));
    }
    if (otherKeys.length) {
      parts.push(buildLevel1ClusterHtml(otherKeys, "other", "Andet"));
    }

    return parts.join("");
  }

  function buildLevel1ClusterHtml(keys, variant, ariaLabel) {
    const buttons = keys.map((key) => buildLevel1ButtonHtml(key)).join("");
    const variantClass = variant ? ` kks-level1-cluster-${escapeHtml(variant)}` : "";
    const labelAttr = ariaLabel ? ` aria-label="${escapeHtml(ariaLabel)}"` : "";
    return `<span class="kks-level1-cluster${variantClass}"${labelAttr}>${buttons}</span>`;
  }

  function buildLevel1ButtonHtml(key) {
    const value = toText(key) || "ALL";
    return buildNavButtonHtml({
      level: 1,
      value,
      label: value,
      pressed: state.level1 === value,
    });
  }

  function isLetterLevel1Key(key) {
    return /^[A-Z]$/.test(normalizeUpper(key));
  }

  function isSymbolLevel1Key(key) {
    return /^-[A-Z]$/.test(normalizeUpper(key));
  }

  function renderLevel2() {
    if (!dom.level2Row) return;

    const hideLevel2ForSymbolGroup =
      BILINGUAL_LAYOUT &&
      VGB_SECTION_MODE === "component" &&
      isSymbolLevel1Key(state.level1);

    if (hideLevel2ForSymbolGroup) {
      dom.level2Row.hidden = true;
      dom.level2Row.innerHTML = "";
      state.level2 = "";
      return;
    }

    dom.level2Row.hidden = false;

    if (!state.level1 || state.level1 === "ALL") {
      renderNoteRow(dom.level2Row, "Vælg et bogstav for at se undergrupper.");
      return;
    }

    const baseRows = getRowsForLevel1(state.level1);
    const prefixes = collectPrefixes(baseRows, 2, state.level1);
    if (!prefixes.length) {
      renderNoteRow(dom.level2Row, "Ingen undergrupper fundet.");
      return;
    }

    const options = prefixes
      .map((prefix) => {
        const rows = baseRows.filter((row) => row.prefix2 === prefix);
        return {
          value: prefix,
          label: prefix,
          count: getRowCount(rows),
        };
      })
      .filter((item) => !state.query || item.count > 0 || item.value === state.level2);

    if (!options.length && state.query) {
      renderNoteRow(dom.level2Row, "Ingen undergrupper matcher den aktuelle søgning.");
      return;
    }

    const allButton = buildNavButtonHtml({
      level: 2,
      value: "",
      label: "ALL",
      pressed: !state.level2,
    });

    dom.level2Row.innerHTML =
      allButton +
      options
        .map((item) =>
          buildNavButtonHtml({
            level: 2,
            value: item.value,
            label: item.label,
            pressed: state.level2 === item.value,
          })
        )
        .join("");
  }

  function renderLevel3() {
    if (!dom.level3Row) return;
    if (!LEVEL3_ENABLED) {
      dom.level3Row.innerHTML = "";
      return;
    }

    if (!state.level1 || state.level1 === "ALL") {
      renderNoteRow(dom.level3Row, "Vælg et bogstav for at se detaljegrupper.");
      return;
    }

    if (!state.level2) {
      renderNoteRow(dom.level3Row, "Vælg en undergruppe for at se detaljegrupper.");
      return;
    }

    const level2Rows = getRowsForLevel1(state.level1).filter((row) => row.prefix2 === state.level2);
    const prefixes = collectPrefixes(level2Rows, 3, state.level2);
    if (!prefixes.length) {
      renderNoteRow(dom.level3Row, "Ingen detaljegrupper fundet.");
      return;
    }

    const options = prefixes
      .map((prefix) => {
        const rows = level2Rows.filter((row) => row.prefix3 === prefix);
        return {
          value: prefix,
          label: prefix,
          count: getRowCount(rows),
        };
      })
      .filter((item) => !state.query || item.count > 0 || item.value === state.level3);

    if (!options.length && state.query) {
      renderNoteRow(dom.level3Row, "Ingen detaljegrupper matcher den aktuelle søgning.");
      return;
    }

    const allButton = buildNavButtonHtml({
      level: 3,
      value: "",
      label: "ALL",
      pressed: !state.level3,
    });

    dom.level3Row.innerHTML =
      allButton +
      options
        .map((item) =>
          buildNavButtonHtml({
            level: 3,
            value: item.value,
            label: item.label,
            pressed: state.level3 === item.value,
          })
        )
        .join("");
  }

  function renderPath() {
    if (!dom.path) return;

    if (BILINGUAL_LAYOUT) {
      const daPressed = state.searchLanguage !== "de";
      const dePressed = state.searchLanguage === "de";
      dom.path.innerHTML = `
        <button type="button" class="kks-path-reset" data-action="reset-nav">Reset</button>
        <span class="kks-search-lang-switch" role="group" aria-label="Soegesprog">
          <button type="button" class="kks-search-lang-btn" data-action="search-lang" data-lang="da" aria-pressed="${daPressed}">Dansk</button>
          <button type="button" class="kks-search-lang-btn" data-action="search-lang" data-lang="de" aria-pressed="${dePressed}">Tysk</button>
        </span>
      `;
      return;
    }

    dom.path.innerHTML = `<button type="button" class="kks-path-reset" data-action="reset-nav">Reset</button>`;
  }

  function renderRows() {
    if (!dom.rowsBody) return;

    const rows = getVisibleRows();

    if (dom.previewTitle) {
      dom.previewTitle.textContent = buildPreviewTitle();
    }

    dom.rowsBody.innerHTML = rows
      .map(
        (row) => {
          const sourceLabel = toText(row.sourceLabel) || row.sourceKey;
          const danish = toText(row.description);
          const german = toText(row.german);

          if (BILINGUAL_LAYOUT) {
            return `
          <tr class="kks-row-nav" data-source="${escapeHtml(row.sourceKey)}" data-code="${escapeHtml(row.code)}" tabindex="0" title="Klik for at navigere til ${escapeHtml(row.sourceKey)}">
            <td><strong>${escapeHtml(row.code)}</strong></td>
            <td>${escapeHtml(danish)}</td>
            <td>${escapeHtml(german)}</td>
            <td><span class="class-pill">${escapeHtml(sourceLabel)}</span></td>
          </tr>
        `;
          }

          return `
          <tr class="kks-row-nav" data-source="${escapeHtml(row.sourceKey)}" data-code="${escapeHtml(row.code)}" tabindex="0" title="Klik for at navigere til ${escapeHtml(row.sourceKey)}">
            <td><strong>${escapeHtml(row.code)}</strong></td>
            <td>${escapeHtml(danish)}</td>
            <td><span class="class-pill">${escapeHtml(sourceLabel)}</span></td>
          </tr>
        `;
        }
      )
      .join("");

    if (dom.rowsEmpty) {
      dom.rowsEmpty.hidden = rows.length > 0;
    }
  }

  function syncSuggestionsPanel() {
    if (!dom.search || !dom.suggestions) return;

    const hasFocus = document.activeElement === dom.search;
    if (!hasFocus || !state.query) {
      hideSearchSuggestions();
      return;
    }

    renderSearchSuggestions();
  }

  function renderSearchSuggestions() {
    if (!dom.suggestions) return;

    const query = normalizeUpper(state.query);
    if (!query) {
      hideSearchSuggestions();
      return;
    }

    state.suggestions = findSuggestions(query);
    if (!state.suggestions.length) {
      hideSearchSuggestions();
      return;
    }

    if (state.activeSuggestionIndex >= state.suggestions.length) {
      state.activeSuggestionIndex = -1;
    }

    dom.suggestions.innerHTML = state.suggestions
      .map((row, index) => {
        const activeClass = index === state.activeSuggestionIndex ? " active" : "";
        const trail = [row.sourceKey, row.prefix2, LEVEL3_ENABLED ? row.prefix3 : ""].filter(Boolean).join(" / ");
        const trailText = trail ? ` - ${trail}` : "";
        const suggestionText = getRowSuggestionText(row);
        return `
          <button type="button" class="combo-item${activeClass}" data-suggestion-index="${index}">
            <span class="combo-key">${escapeHtml(row.code)}</span>
            <span class="combo-text">${escapeHtml(suggestionText)}${escapeHtml(trailText)}</span>
          </button>
        `;
      })
      .join("");

    dom.suggestions.hidden = false;
  }

  function hideSearchSuggestions() {
    if (!dom.suggestions) return;
    dom.suggestions.hidden = true;
    dom.suggestions.innerHTML = "";
    state.suggestions = [];
    state.activeSuggestionIndex = -1;
  }

  function moveSuggestion(step) {
    if (!state.suggestions.length) {
      renderSearchSuggestions();
    }

    const length = state.suggestions.length;
    if (!length) return;

    let nextIndex = state.activeSuggestionIndex + step;
    if (nextIndex < 0) nextIndex = length - 1;
    if (nextIndex >= length) nextIndex = 0;

    state.activeSuggestionIndex = nextIndex;
    renderSearchSuggestions();
  }

  function applySuggestionByIndex(index) {
    if (!Number.isInteger(index)) return;
    const suggestion = state.suggestions[index];
    if (!suggestion) return;
    applySuggestion(suggestion);
  }

  function applySuggestion(row) {
    if (!row) return;

    state.level1 = resolveLevel1ForRecord(row.sourceKey, row.codeUpper);
    if (state.level1 === "ALL") {
      state.level2 = "";
      state.level3 = "";
    } else {
      state.level2 = row.prefix2;
      state.level3 = LEVEL3_ENABLED ? row.prefix3 : "";
    }

    state.query = row.code;
    if (dom.search) {
      dom.search.value = row.code;
    }

    render();
    hideSearchSuggestions();
    commitHistorySnapshot();
  }

  function navigateToRowSource(rowElement) {
    const source = normalizeUpper(rowElement.getAttribute("data-source"));
    const code = normalizeUpper(rowElement.getAttribute("data-code"));
    if (!source && !code) return;

    const isTopLevelLetter = code.length === 1 && MODEL.sectionsByKey.has(code) && code !== "HOME";

    state.level1 = isTopLevelLetter ? code : resolveLevel1ForRecord(source, code);
    if (state.level1 === "ALL" || isTopLevelLetter) {
      state.level2 = "";
      state.level3 = "";
    } else {
      state.level2 = code.length >= 2 ? code.slice(0, 2) : resolveDefaultLevel2(state.level1, code);
      state.level3 = LEVEL3_ENABLED && code.length >= 3 ? code.slice(0, 3) : "";
    }

    state.query = "";

    if (dom.search) {
      dom.search.value = "";
    }

    hideSearchSuggestions();
    render();
    commitHistorySnapshot();
  }

  function resetNavigation() {
    state.level1 = INITIAL_LEVEL1 || "ALL";
    state.level2 = "";
    state.level3 = "";
    state.query = "";
    if (dom.search) {
      dom.search.value = "";
    }
    hideSearchSuggestions();
    render();
    commitHistorySnapshot();
  }

  function setNavMode(mode) {
    const next = mode === "explorer" ? "explorer" : "classic";
    state.navMode = next;
    render();
  }

  function navigateHistory(step) {
    if (!step) return;
    const nextIndex = state.historyIndex + step;
    if (nextIndex < 0 || nextIndex >= state.history.length) return;
    const snapshot = state.history[nextIndex];
    if (!snapshot) return;

    state.suppressHistoryPush = true;
    applySnapshot(snapshot);
    state.historyIndex = nextIndex;
    render();
  }

  function navigateUp() {
    if (LEVEL3_ENABLED && state.level3) {
      state.level3 = "";
    } else if (state.level2) {
      state.level2 = "";
      state.level3 = "";
    } else if (state.level1 !== "ALL") {
      state.level1 = "ALL";
      state.level2 = "";
      state.level3 = "";
    } else {
      return;
    }

    render();
    commitHistorySnapshot();
  }

  function applyCrumb(depth) {
    if (depth <= 0) {
      state.level1 = "ALL";
      state.level2 = "";
      state.level3 = "";
    } else if (depth === 1) {
      state.level2 = "";
      state.level3 = "";
    } else if (depth === 2) {
      state.level3 = "";
    }

    render();
    commitHistorySnapshot();
  }

  function applyExplorerNode(button) {
    const level = Number(button.getAttribute("data-node-level"));
    const value = normalizeUpper(button.getAttribute("data-node-value"));
    if (!level || !value) return;

    if (level === 1) {
      state.level1 = value;
      state.level2 = "";
      state.level3 = "";
    } else if (level === 2) {
      state.level2 = value;
      state.level3 = "";
    } else if (level === 3 && LEVEL3_ENABLED) {
      state.level3 = value;
    }

    render();
    commitHistorySnapshot();
  }

  function renderExplorer() {
    if (!dom.explorerShell) return;

    renderExplorerCrumbs();
    renderExplorerNodes();
    syncExplorerHistoryButtons();
    syncExplorerUpButton();
  }

  function renderExplorerCrumbs() {
    if (!dom.explorerCrumbs) return;

    const crumbs = [{ depth: 0, code: "ALL", active: state.level1 === "ALL" }];
    if (state.level1 !== "ALL") {
      crumbs.push({ depth: 1, code: state.level1, active: !state.level2 && (!LEVEL3_ENABLED || !state.level3) });
    }
    if (state.level2) {
      crumbs.push({ depth: 2, code: state.level2, active: !LEVEL3_ENABLED || !state.level3 });
    }
    if (LEVEL3_ENABLED && state.level3) {
      crumbs.push({ depth: 3, code: state.level3, active: true });
    }

    const html = [];
    crumbs.forEach((crumb, index) => {
      if (index > 0) {
        html.push('<span class="kks-crumb-sep">/</span>');
      }
      const label = getCrumbLabel(crumb.code);
      const cls = crumb.active ? "kks-crumb-btn active" : "kks-crumb-btn";
      html.push(`<button type="button" class="${cls}" data-crumb="${crumb.depth}">${escapeHtml(label)}</button>`);
    });

    dom.explorerCrumbs.innerHTML = html.join("");
  }

  function renderExplorerNodes() {
    if (!dom.explorerNodes) return;

    const nodes = getExplorerNodes();
    if (!nodes.length) {
      dom.explorerNodes.innerHTML = '<div class="kks-explorer-empty">Ingen undermapper pa dette niveau.</div>';
      return;
    }

    dom.explorerNodes.innerHTML = nodes
      .map((node) => {
        const text = node.text ? `<span class="kks-explorer-node-text">${escapeHtml(node.text)}</span>` : "";
        return `
          <button type="button" class="kks-explorer-node" data-node-level="${node.level}" data-node-value="${escapeHtml(node.code)}">
            <span class="kks-explorer-node-key">${escapeHtml(node.code)}</span>
            ${text}
          </button>
        `;
      })
      .join("");
  }

  function getExplorerNodes() {
    if (state.level1 === "ALL") {
      return MODEL.level1Keys
        .filter((key) => key !== "HOME")
        .map((key) => ({
          level: 1,
          code: key,
          text: resolveLevel1Heading(key),
        }));
    }

    if (!state.level2) {
      const rows = getRowsForLevel1(state.level1);
      const prefixes = collectPrefixes(rows, 2, state.level1);
      return prefixes.map((prefix) => ({
        level: 2,
        code: prefix,
        text: resolveLevel2Heading(prefix),
      }));
    }

    if (LEVEL3_ENABLED && !state.level3) {
      const rows = getRowsForLevel1(state.level1).filter((row) => row.prefix2 === state.level2);
      const prefixes = collectPrefixes(rows, 3, state.level2);
      return prefixes.map((prefix) => ({
        level: 3,
        code: prefix,
        text: resolveLevel3Heading(prefix),
      }));
    }

    return [];
  }

  function getCrumbLabel(code) {
    const key = normalizeUpper(code);
    if (key === "ALL") return "ALL";

    if (key.length === 1) {
      const heading = resolveLevel1Heading(key);
      return heading ? `${key} - ${heading}` : key;
    }

    if (key.length === 2) {
      const heading = resolveLevel2Heading(key);
      return heading ? `${key} - ${heading}` : key;
    }

    if (key.length === 3) {
      const heading = resolveLevel3Heading(key);
      return heading ? `${key} - ${heading}` : key;
    }

    return key;
  }

  function syncExplorerHistoryButtons() {
    const canGoBack = state.historyIndex > 0;
    const canGoForward = state.historyIndex >= 0 && state.historyIndex < state.history.length - 1;

    if (dom.explorerBack) {
      dom.explorerBack.disabled = !canGoBack;
    }
    if (dom.explorerForward) {
      dom.explorerForward.disabled = !canGoForward;
    }
  }

  function syncExplorerUpButton() {
    if (!dom.explorerUp) return;
    const canUp = state.level1 !== "ALL" || state.level2 || (LEVEL3_ENABLED && state.level3);
    dom.explorerUp.disabled = !canUp;
  }

  function getCurrentSnapshot() {
    return {
      level1: state.level1 || "ALL",
      level2: state.level2 || "",
      level3: LEVEL3_ENABLED ? state.level3 || "" : "",
    };
  }

  function getSnapshotKey(snapshot) {
    return `${snapshot.level1}|${snapshot.level2}|${snapshot.level3}`;
  }

  function applySnapshot(snapshot) {
    if (!snapshot) return;
    state.level1 = snapshot.level1 || "ALL";
    state.level2 = snapshot.level2 || "";
    state.level3 = LEVEL3_ENABLED ? snapshot.level3 || "" : "";
  }

  function commitHistorySnapshot() {
    const snapshot = getCurrentSnapshot();
    const key = getSnapshotKey(snapshot);
    if (key === state.lastSnapshot) return;

    state.lastSnapshot = key;
    if (state.suppressHistoryPush) {
      state.suppressHistoryPush = false;
      return;
    }

    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(snapshot);
    state.historyIndex = state.history.length - 1;
  }

  function getVisibleRows() {
    const scopeRows = getScopeRows();
    return filterRowsByQuery(scopeRows);
  }

  function getScopeRows() {
    let rows = getRowsForLevel1(state.level1 || "ALL");

    if (state.level2) {
      rows = rows.filter((row) => row.prefix2 === state.level2);
    }

    if (LEVEL3_ENABLED && state.level3) {
      rows = rows.filter((row) => row.prefix3 === state.level3);
    }

    return rows;
  }

  function getRowsForLevel1(level1) {
    const selected = level1 || "ALL";
    if (selected === "ALL") {
      return MODEL.rows.slice();
    }

    const section = MODEL.sectionsByKey.get(selected);
    if (section) {
      return section.rows.slice();
    }

    if (selected.length === 1) {
      return MODEL.rows.filter((row) => row.prefix1 === selected);
    }

    return [];
  }

  function filterRowsByQuery(rows) {
    const query = normalizeUpper(state.query);
    if (!query) {
      return rows.slice();
    }

    return rows.filter((row) => getRowSearchBlob(row).includes(query));
  }

  function getRowSearchBlob(row) {
    if (BILINGUAL_LAYOUT && state.searchLanguage === "de") {
      return toText(row.searchBlobDe) || toText(row.searchBlobDa) || toText(row.searchBlob);
    }
    return toText(row.searchBlobDa) || toText(row.searchBlob);
  }

  function getRowSuggestionText(row) {
    if (BILINGUAL_LAYOUT && state.searchLanguage === "de") {
      return toText(row.german) || toText(row.description);
    }
    return toText(row.description);
  }

  function getRowSuggestionTextUpper(row) {
    return normalizeUpper(getRowSuggestionText(row));
  }

  function collectPrefixes(rows, length, startsWith) {
    const list = new Set();

    rows.forEach((row) => {
      const code = row.codeUpper;
      if (code.length < length) return;

      const prefix = code.slice(0, length);
      if (startsWith && !prefix.startsWith(startsWith)) return;
      list.add(prefix);
    });

    return Array.from(list).sort((a, b) => a.localeCompare(b));
  }

  function buildNavButtonHtml({ level, value, label, pressed }) {
    const safeValue = escapeHtml(value);
    const safeLabel = escapeHtml(label);
    return `
      <button type="button" class="kks-filter-btn" data-level="${level}" data-value="${safeValue}" aria-pressed="${pressed}">
        <span class="kks-filter-key">${safeLabel}</span>
      </button>
    `;
  }

  function renderNoteRow(target, text) {
    target.innerHTML = `<button type="button" class="kks-filter-btn kks-filter-note" disabled>${escapeHtml(text)}</button>`;
  }

  function getRowCount(rows) {
    return filterRowsByQuery(rows).length;
  }

  function buildPreviewTitle() {
    if (state.level1 === "ALL") {
      if (state.query) return `ALL - Alle sektioner - Søgning`;
      return "ALL - Alle sektioner";
    }

    const section = MODEL.sectionsByKey.get(state.level1);
    const sectionTitle = section ? section.title : state.level1;
    const sameAsLevel1 = normalizeUpper(sectionTitle) === normalizeUpper(state.level1);

    let title = sameAsLevel1 ? state.level1 : `${state.level1} - ${sectionTitle}`;
    if (!state.level2 && (!LEVEL3_ENABLED || !state.level3)) {
      const level1Heading = resolveLevel1Heading(state.level1);
      title = appendHeadingIfUseful(title, state.level1, level1Heading);
    }

    if (state.level2) {
      title += ` / ${state.level2}`;
      if (!LEVEL3_ENABLED || !state.level3) {
        const level2Heading = resolveLevel2Heading(state.level2);
        title = appendHeadingIfUseful(title, state.level2, level2Heading);
      }
    }

    if (LEVEL3_ENABLED && state.level3) {
      title += ` / ${state.level3}`;
      const level3Heading = resolveLevel3Heading(state.level3);
      title = appendHeadingIfUseful(title, state.level3, level3Heading);
    }

    if (state.query) title += " - Søgning";
    return title;
  }

  function resolveLevel1Heading(level1) {
    if (!MODEL.level1HeadingByCode) return "";
    const raw = MODEL.level1HeadingByCode.get(normalizeUpper(level1));
    if (!raw) return "";
    return formatHeading(raw);
  }

  function resolveLevel2Heading(level2) {
    if (!MODEL.level2HeadingByCode) return "";
    const raw = MODEL.level2HeadingByCode.get(normalizeUpper(level2));
    if (!raw) return "";
    return formatHeading(raw);
  }

  function resolveLevel3Heading(level3) {
    if (!MODEL.level3HeadingByCode) return "";
    const raw = MODEL.level3HeadingByCode.get(normalizeUpper(level3));
    if (!raw) return "";
    return formatHeading(raw);
  }

  function appendHeadingIfUseful(title, code, heading) {
    const text = toText(heading);
    if (!text) return title;
    if (normalizeUpper(text) === normalizeUpper(code)) return title;
    return `${title} - ${text}`;
  }

  function formatHeading(text) {
    const value = toText(text);
    if (!value) return "";
    const lower = value.toLocaleLowerCase("da-DK");
    return lower.charAt(0).toLocaleUpperCase("da-DK") + lower.slice(1);
  }

  function findSuggestions(query) {
    const rows = getSuggestionScopeRows();
    const scored = [];

    rows.forEach((row) => {
      const score = getSuggestionScore(row, query);
      if (!Number.isFinite(score)) return;
      scored.push({ row, score });
    });

    scored.sort((a, b) => {
      if (a.score !== b.score) return a.score - b.score;
      const codeRank = a.row.codeUpper.localeCompare(b.row.codeUpper);
      if (codeRank !== 0) return codeRank;
      return a.row.descriptionUpper.localeCompare(b.row.descriptionUpper);
    });

    return scored.slice(0, 12).map((entry) => entry.row);
  }

  function getSuggestionScopeRows() {
    return getRowsForLevel1(state.level1 || "ALL");
  }

  function getSuggestionScore(row, query) {
    if (row.codeUpper === query) return 0;
    if (row.codeUpper.startsWith(query)) return 1;
    if (row.prefix3 && row.prefix3 === query) return 2;
    if (row.prefix2 && row.prefix2 === query) return 3;

    const codeIndex = row.codeUpper.indexOf(query);
    if (codeIndex >= 0) return 4 + Math.min(codeIndex, 3);

    const suggestionUpper = getRowSuggestionTextUpper(row);
    if (suggestionUpper.startsWith(query)) return 8;

    const descIndex = suggestionUpper.indexOf(query);
    if (descIndex >= 0) return 9 + Math.min(descIndex, 8);

    return Number.POSITIVE_INFINITY;
  }

  function resolveLevel1ForRecord(source, code) {
    if (source === "HOME") {
      const prefix = code.slice(0, 1);
      if (prefix && MODEL.sectionsByKey.has(prefix) && prefix !== "HOME") {
        return prefix;
      }
      return "ALL";
    }

    if (source && MODEL.sectionsByKey.has(source)) {
      return source;
    }

    const prefix = code.slice(0, 1);
    if (prefix && MODEL.sectionsByKey.has(prefix)) {
      return prefix;
    }

    return "ALL";
  }

  function resolveDefaultLevel2(level1, preferredCode) {
    const key = normalizeUpper(level1);
    if (!key || key === "ALL") return "";

    const rows = getRowsForLevel1(key);
    const prefixes = collectPrefixes(rows, 2, key);
    if (!prefixes.length) return "";

    const preferred = normalizeUpper(preferredCode);
    if (preferred.length >= 2) {
      const preferredPrefix = preferred.slice(0, 2);
      if (prefixes.includes(preferredPrefix)) {
        return preferredPrefix;
      }
    }

    const nPrefix = `${key}N`;
    if (prefixes.includes(nPrefix)) {
      return nPrefix;
    }

    return prefixes[0];
  }

  function buildModel(source) {
    const sectionsByKey = new Map();

    source.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;

      const keyBase = toText(entry.key) || toText(entry.fileName).replace(/\.aspx$/i, "");
      const key = normalizeUpper(keyBase);
      if (!key) return;

      const title = toText(entry.title) || key;
      const titleUpper = normalizeUpper(title);
      const rawRows = Array.isArray(entry.rows) ? entry.rows : [];

      const rows = [];
      const dedup = new Set();

      rawRows.forEach((row) => {
        if (!row || typeof row !== "object") return;

        const code = toText(row.code);
        const description = toText(row.description);
        const german = toText(row.german);
        const searchText = toText(row.searchText) || description;
        if (!code || !description) return;

        const codeUpper = normalizeUpper(code);
        const descriptionUpper = normalizeUpper(description);
        const germanUpper = normalizeUpper(german);
        const searchUpper = normalizeUpper(searchText);
        const fingerprint = `${codeUpper}||${descriptionUpper}||${germanUpper}`;
        if (dedup.has(fingerprint)) return;
        dedup.add(fingerprint);

        rows.push({
          code,
          codeUpper,
          description,
          descriptionUpper,
          german,
          searchText,
          sourceKey: key,
          sourceLabel: toText(row.sourceLabel),
          sourceTitle: title,
          prefix1: codeUpper.slice(0, 1),
          prefix2: codeUpper.length >= 2 ? codeUpper.slice(0, 2) : "",
          prefix3: codeUpper.length >= 3 ? codeUpper.slice(0, 3) : "",
          searchBlobDa: `${codeUpper} ${searchUpper} ${key} ${titleUpper}`,
          searchBlobDe: `${codeUpper} ${germanUpper} ${key} ${titleUpper}`,
          searchBlob: `${codeUpper} ${searchUpper} ${key} ${titleUpper}`,
        });
      });

      sectionsByKey.set(key, {
        key,
        title,
        rows,
      });
    });

    const level1Keys = orderKeys(Array.from(sectionsByKey.keys()));
    const rows = [];

    level1Keys.forEach((key) => {
      const section = sectionsByKey.get(key);
      if (!section) return;
      section.rows.forEach((row) => rows.push(row));
    });

    const level1HeadingByCode = new Map();
    const homeSection = sectionsByKey.get("HOME");
    if (homeSection && Array.isArray(homeSection.rows)) {
      homeSection.rows.forEach((row) => {
        const key = normalizeUpper(row.code);
        if (key.length !== 1) return;
        if (!level1HeadingByCode.has(key)) {
          level1HeadingByCode.set(key, row.description);
        }
      });
    }

    const level2HeadingByCode = new Map();
    const level3HeadingByCode = new Map();

    rows.forEach((row) => {
      if (!row || typeof row !== "object") return;

      const code2 = normalizeUpper(row.prefix2);
      if (code2 && row.codeUpper === code2 && !level2HeadingByCode.has(code2)) {
        level2HeadingByCode.set(code2, row.description);
      }

      const code3 = normalizeUpper(row.prefix3);
      if (code3 && row.codeUpper === code3 && !level3HeadingByCode.has(code3)) {
        level3HeadingByCode.set(code3, row.description);
      }
    });

    level1Keys.forEach((key) => {
      if (key === "HOME") return;
      if (level1HeadingByCode.has(key)) return;

      const section = sectionsByKey.get(key);
      if (!section || !Array.isArray(section.rows) || !section.rows.length) return;

      const direct = section.rows.find((row) => row.codeUpper === key);
      if (direct && direct.description) {
        level1HeadingByCode.set(key, direct.description);
        return;
      }

      const fallbackL2 = section.rows.find((row) => row.codeUpper === row.prefix2 && row.prefix2.startsWith(key));
      if (fallbackL2 && fallbackL2.description) {
        level1HeadingByCode.set(key, fallbackL2.description);
      }
    });

    return {
      sectionsByKey,
      level1Keys,
      rows,
      level1HeadingByCode,
      level2HeadingByCode,
      level3HeadingByCode,
    };
  }

  function orderKeys(keys) {
    const rank = new Map();
    ORDER.forEach((key, index) => {
      rank.set(key, index);
    });

    return keys.slice().sort((a, b) => {
      const aRank = rank.has(a) ? rank.get(a) : 1000;
      const bRank = rank.has(b) ? rank.get(b) : 1000;
      if (aRank !== bRank) return aRank - bRank;
      return a.localeCompare(b);
    });
  }
})();

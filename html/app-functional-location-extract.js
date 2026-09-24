(() => {
  const { normalizeUpper, escapeHtml } = window.TextUtils;

  const RULES_URL = "js/data/fl-classification-data.json";
  const RULE_ENGINE = window.FlRuleEngine;

  const state = {
    ruleData: {
      loaded: false,
      componentMap: {},
      aggregateMap: {},
      functionKeySet: new Set(),
      allowedPlantSet: new Set(),
      br18ByAggregate: {},
      meta: null,
    },
    parsedRows: [],
    classBuckets: {},
    activeClassTab: "ALL",
  };

  const dom = {
    input: document.getElementById("flExtractInput"),
    runBtn: document.getElementById("btnExtractClassify"),
    runtime: document.getElementById("flExtractRuntime"),
    tabs: document.getElementById("flExtractClassTabs"),
    output: document.getElementById("flExtractOutput"),
    metricRows: document.getElementById("flExtractMetricRows"),
    metricClasses: document.getElementById("flExtractMetricClasses"),
    dataState: document.getElementById("flExtractDataState"),
    meta: document.getElementById("flExtractMeta"),
  };

  if (!dom.input || !dom.runBtn) return;

  init().catch((err) => {
    setRuntime(`Failed to initialize extract rules: ${err.message}`);
  });

  async function init() {
    if (!RULE_ENGINE) {
      dom.dataState.textContent = "Failed";
      dom.meta.textContent = "fl-rule-engine.js not loaded.";
      setRuntime("Rule engine missing.");
      return;
    }

    await loadRuleData();
    dom.runBtn.addEventListener("click", runExtract);
    renderExtractOutput();
  }

  async function loadRuleData() {
    setRuntime("Loading rules...");
    try {
      const data = await resolveRulesPayload();
      state.ruleData = RULE_ENGINE.buildRuleData(data, window.FL_LOOKUPS);

      dom.dataState.textContent = "Loaded";
      if (state.ruleData.meta) {
        dom.meta.textContent = `${state.ruleData.meta.componentCount} / ${state.ruleData.meta.aggregateCount} / ${state.ruleData.meta.functionKeyCount}`;
      } else {
        dom.meta.textContent = `Comp ${Object.keys(state.ruleData.componentMap).length}, Agg ${Object.keys(state.ruleData.aggregateMap).length}`;
      }
      setRuntime("Extract ready.");
      return;
    } catch (error) {
      if (window.FL_LOOKUPS && typeof window.FL_LOOKUPS === "object") {
        state.ruleData = RULE_ENGINE.buildRuleData({}, window.FL_LOOKUPS);
        dom.dataState.textContent = "Lookup";
        dom.meta.textContent = `${Object.keys(state.ruleData.componentMap).length} / ${Object.keys(state.ruleData.aggregateMap).length} / ${state.ruleData.functionKeySet.size}`;
        setRuntime("Extract ready (lookup fallback).");
        return;
      }

      dom.dataState.textContent = "Failed";
      dom.meta.textContent = error && error.message ? error.message : String(error);
      setRuntime("Extract rules missing.");
    }
  }

  async function resolveRulesPayload() {
    if (window.FL_CLASSIFICATION_DATA && typeof window.FL_CLASSIFICATION_DATA === "object") {
      return window.FL_CLASSIFICATION_DATA;
    }

    const response = await fetch(RULES_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function runExtract() {
    const lines = splitLines(dom.input.value);
    state.parsedRows = lines
      .map((line, idx) => parseLine(line, idx + 1))
      .filter((row) => row.fl);

    state.classBuckets = distributeRowsIntoClasses(state.parsedRows);
    state.activeClassTab = "ALL";

    renderExtractOutput();
    setRuntime(`Extracted ${state.parsedRows.length} row(s).`);
  }

  function splitLines(input) {
    return String(input || "")
      .replaceAll("\r", "")
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean);
  }

  function parseLine(line, index) {
    const parts = line.split(";");
    const fl = normalizeFunctionalLocation(parts[0] || "");
    const actClass = normalizeUpper(parts[1] || "");
    const syntaxInfo = evaluateKksSyntax(fl);
    const classInfo = determineClass(fl, syntaxInfo.syntaxClass);

    const blockingIssues = [...(classInfo.blockingIssues || [])];
    const warnings = [...(classInfo.warnings || [])];
    if (syntaxInfo.blockingIssue) blockingIssues.unshift(syntaxInfo.blockingIssue);
    if (syntaxInfo.warning) warnings.push(syntaxInfo.warning);

    return {
      index,
      source: line,
      fl,
      actClass,
      assignedClass: classInfo.className || "NO CLASS",
      candidateClasses: [classInfo.className || "NO CLASS"],
      warnings,
      notes: classInfo.notes,
      blockingIssues,
    };
  }

  function evaluateKksSyntax(fl) {
    return RULE_ENGINE.evaluateKksSyntax(fl);
  }

  function determineClass(fl, syntaxClass) {
    return RULE_ENGINE.determineClass(fl, syntaxClass, state.ruleData);
  }

  function distributeRowsIntoClasses(rows) {
    const buckets = {};

    rows.forEach((row) => {
      const className = normalizeUpper(row.assignedClass) || "NO CLASS";
      if (!buckets[className]) buckets[className] = [];
      buckets[className].push(row);
    });

    return buckets;
  }

  function renderExtractOutput() {
    const classNames = Object.keys(state.classBuckets).sort();
    const rows =
      state.activeClassTab === "ALL"
        ? dedupeRowsByIndex(classNames.flatMap((className) => state.classBuckets[className].map((row) => ({ ...row, __className: className }))))
        : (state.classBuckets[state.activeClassTab] || []).map((row) => ({ ...row, __className: state.activeClassTab }));

    dom.tabs.innerHTML = renderTabs(classNames);
    bindTabs();

    dom.output.innerHTML = rows.length
      ? `
        <div class="data-table-wrap">
          <table class="data-table data-table-fl-extract">
            <thead>
              <tr>
                <th>#</th>
                <th>FL</th>
                <th>ACT_CLASS</th>
                <th>Assigned</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map(renderOutputRow).join("")}
            </tbody>
          </table>
        </div>
      `
      : '<p class="small-muted">No rows classified.</p>';

    dom.metricRows.textContent = String(state.parsedRows.length);
    dom.metricClasses.textContent = String(classNames.length);
  }

  function renderTabs(classNames) {
    const allCount = dedupeRowsByIndex(classNames.flatMap((x) => state.classBuckets[x] || [])).length;

    const allBtn = `<button class="pill-tab ${state.activeClassTab === "ALL" ? "active" : ""}" data-class-tab="ALL">ALL (${allCount})</button>`;
    const classBtns = classNames
      .map((className) => {
        const count = (state.classBuckets[className] || []).length;
        const active = state.activeClassTab === className ? "active" : "";
        return `<button class="pill-tab ${active}" data-class-tab="${escapeHtml(className)}">${escapeHtml(className)} (${count})</button>`;
      })
      .join("");

    return allBtn + classBtns;
  }

  function bindTabs() {
    dom.tabs.querySelectorAll("[data-class-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeClassTab = btn.getAttribute("data-class-tab") || "ALL";
        renderExtractOutput();
      });
    });
  }

  function renderOutputRow(row) {
    const issueText = row.blockingIssues.length ? row.blockingIssues.join("; ") : "OK";
    return `
      <tr>
        <td>${row.index}</td>
        <td><code>${escapeHtml(row.fl)}</code></td>
        <td>${row.actClass ? `<span class="class-pill">${escapeHtml(row.actClass)}</span>` : "-"}</td>
        <td>${renderClassPills(row)}</td>
        <td>${escapeHtml(issueText)}</td>
      </tr>
    `;
  }

  function renderClassPills(row) {
    const className = normalizeUpper(row.assignedClass);
    return className ? `<span class="class-pill">${escapeHtml(className)}</span>` : "-";
  }

  function normalizeFunctionalLocation(value) {
    return RULE_ENGINE.normalizeFunctionalLocation(value);
  }

  function dedupeRowsByIndex(rows) {
    const seen = new Set();
    return rows.filter((row) => {
      if (seen.has(row.index)) return false;
      seen.add(row.index);
      return true;
    });
  }

  function setRuntime(message) {
    dom.runtime.textContent = message;
  }
})();

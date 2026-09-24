(function () {
  const { toText, normalizeUpper, escapeHtml } = window.TextUtils;

  const RULE_ENGINE = window.FlRuleEngine;
  const DEFAULT_SPOOL_COLUMNS = [
    "SAP status",
    "Info",
    "StrIndicator",
    "Functional Location",
    "Description",
    "IP class",
    "Junction box",
    "Mechanical measur. range from",
    "Mechanical measuring range to",
    "Mechanical measuring range uom",
    "Operating pressure",
    "Operating pressure uom",
    "Operating temperature",
    "Operating temperature uom",
    "Output value",
    "Output value uom",
    "Remarks",
    "Signal applications",
    "Supply from",
    "Test Method",
    "Test Method 2",
    "Typekredse",
    "TRM assignment",
    "EX-Marking",
    "Safety Critical Equipment",
    "GIV_EXT assignment",
    "Other Information",
    "Owner",
    "ABC Indic.",
    "Long text",
    "Manufacturer",
    "Model Number",
    "Manufacturer Part Number",
    "Manufacturer Serial Number",
    "Room",
    "Sort Field",
    "Atex",
    "Risiko",
    "Asbestos",
    "PTW",
    "Warranty Start",
    "Warranty End",
    "User status",
    "System status",
    "DLFL",
    "Superior FL",
    "Datasheet",
    "1",
    "Location",
    "Unit",
    "Document number",
    "2",
  ];

  const CLASS_VIEW_PRESETS = {
    compact: "compact",
    all: "all",
  };

  const COMPACT_COLUMN_ORDER = ["SAP status", "Info", "StrIndicator", "Functional Location", "Description"];

  const CLASS_TABLE_FIXED_COLUMNS = Object.freeze([
    { key: "__ROW_NO__", label: "#" },
    { key: "Functional Location", label: "Functional Location" },
    { key: "Description", label: "Description" },
    { key: "StrIndicator", label: "StrIndicator" },
    { key: "Class", label: "Class" },
  ]);

  const CLASS_HELP = {
    AUTOMATIK: "AUTOMATIK",
    CONNECTIONINFO: "EL CONNECTION INFO",
    DISCOS: "DISCOS INSTALLATION",
    ELF: "ELECT. POWER CONSUMERS",
    GENEREL: "GENEREL KLASSE",
    GIV: "TRANSDUSERS",
    GIV_EXT: "EXTERNAL OWNED METERS",
    HOVEDLEDNINFO: "EL HOVEDLEDNING",
    HOVST_TEK_OLIEOP: "TEKNISK PLADS HOVEDSTATION OLIEOPSAMLING",
    IA_LEV: "LEVTID",
    INFONOTES: "INFONOTES",
    KAB: "CABLES",
    MAA: "MEASURING POINTS",
    MAF: "MEASURING POINTS SETTLEMENT",
    MKP: "MACHINE COMPONENTS",
    MKP_AC: "MACHINE COMPONENTS: ACTUATOR",
    MKP_FA: "MACHINE COMPONENTS: FAN",
    MKP_FI: "MACHINE COMPONENTS: FILTER",
    MKP_HE: "MACHINE COMPONENTS: HEAT",
    MKP_PI: "MACHINE COMPONENTS: PIPE",
    MKP_PU: "MACHINE COMPONENTS: PUMP",
    MKP_TA: "MACHINE COMPONENTS: TANK",
    MKP_VA: "MACHINE COMPONENTS: VALVE",
    RBR: "PIPE SUPPORTS",
    RFI: "PIPELINES",
    STD_HOVST_DATA: "STANDARD HOVEDSTATION DATA",
    STIKINFO: "EL STIKLEDNING",
    TAF: "TERMINAL BOARD",
    TEKNISKPLADS: "TEKNISK PLADS",
    TILSLUTNINGSOBJEKT: "TILSLUTNINGSOBJEKT",
    TRM: "TECHNICAL RISK MANAGEMENT",
    UNF: "JUNCTION BOXES",
    VENDOR_RDS_CODE: "ALTERNATIVE VENDOR RDS-PP CODE",
    WCM: "WCM",
    WP_FMT_T2: "WIND FARM SITE FOR WP",
    WP_WTG: "WIND POWER WTG MASTER DATA",
    WP_WTG_TEMPLATE: "WIND POWER WTG TEMPLATE FOR ECM",
  };

  const READ_ONLY_SPOOL_COLUMNS = new Set([
    "CLASS",
    "SAP STATUS",
    "INFO",
    "STRINDICATOR",
    "STR. INDICATOR",
    "USER STATUS",
    "SYSTEM STATUS",
  ]);

  const DROPDOWN_TABLE_BY_FIELD = Object.freeze({
    "DESIGN PRESSURE UOM": "Design_pressure_uom",
    "OPERATING PRESSURE UOM": "Design_pressure_uom",
    "DESIGN TEMPERATURE UOM": "Design_Temp_uom",
    "OPERATING TEMPERATURE UOM": "Design_Temp_uom",
    "DESIGN FLOW UOM": "Design_flow_uom",
    "TEST METHOD": "TestMethod",
    "TEST METHOD 2": "TestMethod",
    TYPEKREDSE: "TypekredsTabel",
    "FIRE CLASSIFICATION": "FireClassification",
    "FIRE SEALING TYPE": "Table20",
  });

  const DROPDOWN_TABLE_BY_SEARCH_KEY = Object.freeze({
    K0210: "Design_pressure_uom",
    K0410: "Design_pressure_uom",
    K0190: "Design_Temp_uom",
    K0380: "Design_Temp_uom",
    K0070: "Design_flow_uom",
    K1430: "TestMethod",
    K1440: "TestMethod",
    K1420: "TypekredsTabel",
  });

  const BUILTIN_ALLOWED_VALUES_BY_FIELD = Object.freeze({
    ATEX: ["X"],
    RISIKO: ["X"],
    ASBESTOS: ["X"],
    PTW: ["X"],
    "ABC INDIC.": ["A"],
    STRINDICATOR: ["KKS", "AKS", "ROS", "KKSKV", "KKSKA"],
    "TRM ASSIGNMENT": ["X"],
  });

  const FIELD_REGEX_RULES = Object.freeze({
    "DESIGN PRESSURE": /^[0-9.,\-\/+]*$/,
    "OPERATING PRESSURE": /^[0-9.,\-\/+]*$/,
    "DESIGN TEMPERATURE": /^[0-9.,\-\/+]*$/,
    "OPERATING TEMPERATURE": /^[0-9.,\-\/+]*$/,
    "DESIGN FLOW": /^[0-9.,\-\/+]*$/,
    "FULL LOAD CURRENT [A]": /^[0-9,]*$/,
    "POWER [KW]": /^[0-9,]*$/,
    "VOLTAGE [V]": /^[0-9.,]*$/,
    "DRAWN CABLE LENGTH [M]": /^[0-9,]*$/,
    "CLOSE TORQUE IN NM": /^[0-9.,]*$/,
    "DRIVE TIME REQUIREMENTS IN SEC": /^[0-9.,]*$/,
    "OPEN TORQUE IN NM": /^[0-9.,]*$/,
    "DESIGN LIFTING HEIGHT": /^[0-9.,]*$/,
    "SETTING COLD VERTICAL [KN]": /^[0-9.,]*$/,
    "SETTING COLD VERTICAL [MM]": /^[0-9.,]*$/,
    "SETTING WARM VERTICAL [KN]": /^[0-9.,]*$/,
    "SETTING WARM VERTICAL [MM]": /^[0-9.,]*$/,
  });

  const DATE_FIELD_SET = new Set(["WARRANTY START", "WARRANTY END"]);

  const CLASS_STEP_RULES = Object.freeze({
    ELF: ["Verify_Master_Data_FL", "ELF", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    GIV: ["Verify_Master_Data_FL", "GIV", "TRMNEW", "Operating_temperature_", "Operating_pressure_", "TestMethod", "Typekreds", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    KAB: ["Verify_Master_Data_FL", "KAB", "KKS_Syntax"],
    MAA: ["Verify_Master_Data_FL", "MAA", "Design_pressure_", "Design_temperature_", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP: ["Verify_Master_Data_FL", "MKP", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_AC: ["Verify_Master_Data_FL", "MKP_AC", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_FA: ["Verify_Master_Data_FL", "MKP_FA", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_FI: ["Verify_Master_Data_FL", "MKP_FI", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_HE: ["Verify_Master_Data_FL", "MKP_HE", "TRMNEW", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_PI: ["Verify_Master_Data_FL", "MKP_PI", "TRMNEW", "Design_pressure_", "Design_temperature_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_PU: ["Verify_Master_Data_FL", "MKP_PU", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_TA: ["Verify_Master_Data_FL", "MKP_TA", "TRMNEW", "Design_pressure_", "Design_temperature_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    MKP_VA: ["Verify_Master_Data_FL", "MKP_VA", "TRMNEW", "Design_pressure_", "Design_temperature_", "Design_flow_", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    RBR: ["Verify_Master_Data_FL", "RBR", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    TAF: ["Verify_Master_Data_FL", "TAF", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    UNF: ["Verify_Master_Data_FL", "UNF", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    "NO CLASS": ["TRMNEW", "Verify_Master_Data_FL", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    SIGNAL: ["TRMNEW", "Verify_Master_Data_FL", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
    DEFAULT: ["Verify_Master_Data_FL", "TRMNEW", "VerifyFunctionalLocationClasses", "KKS_Syntax"],
  });

  const MASTERDATA_FIELD_RULES = Object.freeze({
    MANUFACTURER: { maxLength: 30 },
    DESCRIPTION: { maxLength: 40, required: true },
    "MODEL NUMBER": { maxLength: 20 },
    "MANUFACTURER PART NUMBER": { maxLength: 30 },
    "MANUFACTURER SERIAL NUMBER": { maxLength: 30 },
    "SORT FIELD": { maxLength: 30 },
    ROOM: { maxLength: 8 },
    "WARRANTY START": { maxLength: 10 },
    "WARRANTY END": { maxLength: 10 },
  });

  const STEP_FIELD_RULES = Object.freeze({
    Design_pressure_: {
      "DESIGN PRESSURE": { maxLength: 8, regex: /^[0-9.,\-\/+]*$/ },
    },
    Operating_pressure_: {
      "OPERATING PRESSURE": { maxLength: 12, regex: /^[0-9.,\-\/+]*$/ },
    },
    Design_temperature_: {
      "DESIGN TEMPERATURE": { maxLength: 8, regex: /^[0-9.,\-\/+]*$/ },
    },
    Operating_temperature_: {
      "OPERATING TEMPERATURE": { maxLength: 10, regex: /^[0-9.,\-\/+]*$/ },
    },
    Design_flow_: {
      "DESIGN FLOW": { maxLength: 10, regex: /^[0-9.,\-\/+]*$/ },
    },
    TRMNEW: {
      "EX-MARKING": { maxLength: 30 },
    },
  });

  const CLASS_SPECIFIC_FIELD_RULES = Object.freeze({
    ELF: {
      "FULL LOAD CURRENT [A]": { maxLength: 8, regex: /^[0-9,]*$/ },
      "IP CLASS": { maxLength: 30 },
      "POWER [KW]": { maxLength: 13, regex: /^[0-9,]*$/ },
      REMARKS: { maxLength: 30 },
      "SUPPLY FROM": { maxLength: 30 },
      "VOLTAGE [V]": { maxLength: 7, regex: /^[0-9,]*$/ },
      "SWITCHING LOCATION": { maxLength: 30 },
    },
    GIV: {
      "IP CLASS": { maxLength: 30 },
      "JUNCTION BOX": { maxLength: 18 },
      "MECHANICAL MEASUR. RANGE FROM": { maxLength: 30 },
      "MECHANICAL MEASURING RANGE TO": { maxLength: 12 },
      "MECHANICAL MEASURING RANGE UOM": { maxLength: 17 },
      "OUTPUT VALUE": { maxLength: 30 },
      "OUTPUT VALUE UOM": { maxLength: 18 },
      REMARKS: { maxLength: 30 },
      "SIGNAL APPLICATIONS": { maxLength: 20 },
      "SUPPLY FROM": { maxLength: 30 },
      "OTHER INFORMATION": { maxLength: 30 },
      OWNER: { maxLength: 30 },
    },
    KAB: {
      "CABLE TYPE": { maxLength: 18 },
      DIMENSION: { maxLength: 18 },
      "DIMENSION UOM": { maxLength: 15 },
      "DRAWN CABLE LENGTH [M]": { maxLength: 5, regex: /^[0-9,]*$/ },
      "FROM FUNCTIONAL LOCATION": { maxLength: 30 },
      "TO FUNCTIONAL LOCATION": { maxLength: 30 },
      "VOLTAGE [V]": { maxLength: 7, regex: /^[0-9,]*$/ },
      REMARKS: { maxLength: 30 },
    },
    MAA: {
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP: {
      REMARKS: { maxLength: 30 },
    },
    MKP_AC: {
      "CLOSE TORQUE IN NM": { maxLength: 10, regex: /^[0-9.,]*$/ },
      "DRIVE TIME REQUIREMENTS IN SEC": { maxLength: 10, regex: /^[0-9.,]*$/ },
      "OPEN TORQUE IN NM": { maxLength: 10, regex: /^[0-9.,]*$/ },
      REMARKS: { maxLength: 30 },
    },
    MKP_FA: {
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP_FI: {
      "CONTROL CLASS (LOVPLIGTIG)": { maxLength: 5 },
      "DN/VOLUME": { maxLength: 15 },
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP_HE: {
      "SECONDARY MEDIUM": { maxLength: 30 },
      "PRIMARY MEDIUM": { maxLength: 20 },
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP_PI: {
      "CONTROL CLASS (LOVPLIGTIG)": { maxLength: 5 },
      "DN/VOLUME": { maxLength: 15 },
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP_PU: {
      "DESIGN LIFTING HEIGHT": { maxLength: 8, regex: /^[0-9.,]*$/ },
      "DESIGN LIFTING HEIGHT UOM": { maxLength: 15 },
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP_TA: {
      "CONTROL CLASS (LOVPLIGTIG)": { maxLength: 5 },
      "DN/VOLUME": { maxLength: 15 },
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    MKP_VA: {
      "DN/VOLUME": { maxLength: 15 },
      MEDIUM: { maxLength: 20 },
      REMARKS: { maxLength: 30 },
    },
    RBR: {
      "DESIGN POS COLD": { maxLength: 10 },
      "DESIGN POS WARM": { maxLength: 10 },
      "DIRECTION OF MOVEMENT": { maxLength: 17 },
      REMARKS: { maxLength: 30 },
      "SETTING COLD VERTICAL [KN]": { maxLength: 17, regex: /^[0-9.,]*$/ },
      "SETTING COLD VERTICAL [MM]": { maxLength: 17, regex: /^[0-9.,]*$/ },
      "SETTING WARM VERTICAL [KN]": { maxLength: 17, regex: /^[0-9.,]*$/ },
      "SETTING WARM VERTICAL [MM]": { maxLength: 17, regex: /^[0-9.,]*$/ },
    },
    TAF: {
      "CONSUMER FL": { maxLength: 30 },
      "NOMINEL CURRENT, COMPARTMENT": { maxLength: 10 },
      REMARKS: { maxLength: 30 },
      "VOLTAGE [V]": { maxLength: 7, regex: /^[0-9.,]*$/ },
    },
    UNF: {
      REMARKS: { maxLength: 30 },
    },
  });

  const state = {
    rows: [],
    nextId: 1,
    pendingRowFocus: null,
    classBuckets: {},
    activeClassTab: "ALL",
    classViewPreset: CLASS_VIEW_PRESETS.compact,
    classTableScrollTop: 0,
    classTableScrollLeft: 0,
    detailGridScrollTop: 0,
    detailGridScrollLeft: 0,
    flSelectUi: {
      entries: [],
      outsideBound: false,
    },
    detailRowId: null,
    detailRowClassName: "",
    detailShowEmpty: false,
    verificationInProgress: false,
    ruleData: {
      loaded: false,
      componentMap: {},
      aggregateMap: {},
      functionKeySet: new Set(),
      allowedPlantSet: new Set(),
      br18ByAggregate: {},
      meta: null,
    },
    spoolRules: {
      charByClass: {},
      dropdownValuesByTable: {},
      sceByClass: {},
      classSteps: {},
    },
  };

  const dom = {};

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    bindDom();
    bindEvents();
    bindHoverHints();

    if (!RULE_ENGINE) {
      setRuntime("Rule engine missing.");
      if (dom.dataState) dom.dataState.textContent = "Failed";
      if (dom.metaState) dom.metaState.textContent = "fl-rule-engine.js not loaded.";
      return;
    }

    setRuntime("Loading rules...");
    await loadClassificationData();
    buildSpoolRuleIndex();

    addRow();
    renderRows();
    renderClassTabs();
    renderMetrics();
    setRuntime("Ready.");
  }

  function bindDom() {
    dom.rowsBody = document.getElementById("flRowsBody");
    dom.classTabs = document.getElementById("classTabs");
    dom.classTabContent = document.getElementById("classTabContent");
    dom.runtimeInfo = document.getElementById("flRuntimeInfo");
    dom.btnAddRow = document.getElementById("btnAddFlRow");
    dom.btnVerify = document.getElementById("btnVerifyFl");
    dom.btnExport = document.getElementById("btnExportFlJson");
    dom.metricTotal = document.getElementById("flMetricTotal");
    dom.metricReady = document.getElementById("flMetricReady");
    dom.metricIssues = document.getElementById("flMetricIssues");
    dom.dataState = document.getElementById("flDataState");
    dom.metaState = document.getElementById("flMetaState");
    dom.hoverHint = document.getElementById("hoverHint");
  }

  function bindEvents() {
    if (dom.btnAddRow) {
      dom.btnAddRow.addEventListener("click", () => {
        addRow();
        renderRows();
        renderMetrics();
      });
    }

    if (dom.btnVerify) {
      dom.btnVerify.addEventListener("click", () => {
        runVerification();
      });
    }

    if (dom.btnExport) {
      dom.btnExport.addEventListener("click", exportJson);
    }

    if (dom.rowsBody) {
      dom.rowsBody.addEventListener("input", onTableInput);

      dom.rowsBody.addEventListener("keydown", handleValidationTableKeydown);

      dom.rowsBody.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        let focusHint = resolveRowFocusHintAfterFlChange(target);
        if (!focusHint && target.getAttribute("data-field") === "functionalLocation") {
          const rowId = Number(target.getAttribute("data-row-id"));
          if (
            Number.isFinite(rowId) &&
            state.pendingRowFocus &&
            state.pendingRowFocus.field === "description" &&
            state.pendingRowFocus.rowId === rowId
          ) {
            focusHint = { ...state.pendingRowFocus };
          }
        }
        runVerification(focusHint);
      });

      dom.rowsBody.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        if (target.matches("[data-action='delete-row']")) {
          const rowId = Number(target.getAttribute("data-row-id"));
          if (!Number.isFinite(rowId)) return;

          state.rows = state.rows.filter((row) => row.id !== rowId);
          if (!state.rows.length) addRow();

          renderRows();
          renderMetrics();
          distributeRowsIntoClasses();
          renderClassTabs();
        }
      });
    }

    if (dom.classTabs) {
      dom.classTabs.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.matches("[data-class-tab]")) return;

        state.activeClassTab = target.getAttribute("data-class-tab") || "ALL";
        closeDetailModal();
        renderClassTabs();
      });
    }

    if (dom.classTabContent) {
      dom.classTabContent.addEventListener("click", handleClassTabContentClick);
      dom.classTabContent.addEventListener("input", (event) => {
        handleClassTabContentEdit(event, false);
      });
      dom.classTabContent.addEventListener("change", (event) => {
        handleClassTabContentEdit(event, true);
      });
    }

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (state.detailRowId === null) return;
      closeDetailModal();
      renderClassTabs();
    });
  }

  function handleClassTabContentClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    const presetButton = target.closest("[data-class-view]");
    if (presetButton instanceof HTMLElement) {
      const preset = presetButton.getAttribute("data-class-view") || "";
      if (preset === CLASS_VIEW_PRESETS.compact || preset === CLASS_VIEW_PRESETS.all) {
        state.classViewPreset = preset;
        renderClassTabs();
      }
      return;
    }

    const openDetailsButton = target.closest("[data-action='open-class-details']");
    if (openDetailsButton instanceof HTMLElement) {
      const rowId = Number(openDetailsButton.getAttribute("data-row-id"));
      if (!Number.isFinite(rowId)) return;

      state.detailRowId = rowId;
      state.detailRowClassName = normalizeUpper(openDetailsButton.getAttribute("data-row-class") || "");
      state.detailShowEmpty = false;
      renderClassTabs();
      return;
    }

    if (target.closest("[data-action='close-class-details']")) {
      closeDetailModal();
      renderClassTabs();
      return;
    }

    if (target.closest("[data-action='toggle-empty-details']")) {
      state.detailShowEmpty = !state.detailShowEmpty;
      renderClassTabs();
    }
  }

  function closeDetailModal() {
    state.detailRowId = null;
    state.detailRowClassName = "";
    state.detailShowEmpty = false;
  }

  function handleClassTabContentEdit(event, commitChange) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement)) return;
    if (target.getAttribute("data-action") !== "spool-edit") return;

    const rowId = Number(target.getAttribute("data-row-id"));
    const columnName = target.getAttribute("data-column") || "";
    if (!Number.isFinite(rowId) || !columnName) return;

    const editContext = commitChange ? captureEditViewContext(target, rowId, columnName) : null;
    applySpoolEdit(rowId, columnName, target.value, commitChange, editContext);
  }

  function applySpoolEdit(rowId, columnName, rawValue, commitChange, editContext) {
    const row = state.rows.find((item) => item.id === rowId);
    if (!row) return;

    ensureRowSpoolState(row);
    setSpoolColumnValue(row, normalizeUpper(columnName), rawValue);

    if (!commitChange) return;

    revalidateRowsAndRender("Spool value updated.", editContext);
  }

  function setSpoolColumnValue(row, normalizedColumn, rawValue) {
    const value = toText(rawValue);
    if (!normalizedColumn) return;

    if (normalizedColumn === "FUNCTIONAL LOCATION") {
      row.functionalLocation = normalizeFlTyped(value);
      return;
    }

    if (normalizedColumn === "DESCRIPTION") {
      row.description = value;
      return;
    }

    if (!row.spoolValues || typeof row.spoolValues !== "object") {
      row.spoolValues = {};
    }

    if (!value) {
      delete row.spoolValues[normalizedColumn];
      return;
    }

    row.spoolValues[normalizedColumn] = value;
  }

  function revalidateRowsAndRender(runtimeMessage, editContext) {
    const duplicateMap = buildDuplicateCountMap(state.rows);
    state.rows.forEach((row) => {
      applyLocalValidation(row, duplicateMap);
    });

    renderRows();
    renderMetrics();
    distributeRowsIntoClasses();
    renderClassTabs();
    restoreEditViewContext(editContext);

    if (runtimeMessage) setRuntime(runtimeMessage);
  }

  function captureEditViewContext(target, rowId, columnName) {
    const tableWrap = dom.classTabContent ? dom.classTabContent.querySelector(".data-table-wrap") : null;
    const detailWrap = dom.classTabContent ? dom.classTabContent.querySelector(".class-detail-grid-wrap") : null;
    const context = {
      rowId,
      columnName,
      pageX: window.scrollX,
      pageY: window.scrollY,
      tableScrollTop: tableWrap ? tableWrap.scrollTop : state.classTableScrollTop,
      tableScrollLeft: tableWrap ? tableWrap.scrollLeft : state.classTableScrollLeft,
      detailScrollTop: detailWrap ? detailWrap.scrollTop : state.detailGridScrollTop,
      detailScrollLeft: detailWrap ? detailWrap.scrollLeft : state.detailGridScrollLeft,
    };

    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      context.selectionStart = Number.isFinite(target.selectionStart) ? target.selectionStart : null;
      context.selectionEnd = Number.isFinite(target.selectionEnd) ? target.selectionEnd : null;
    }

    return context;
  }

  function restoreEditViewContext(context) {
    if (!context) return;

    requestAnimationFrame(() => {
      const tableWrap = dom.classTabContent ? dom.classTabContent.querySelector(".data-table-wrap") : null;
      const detailWrap = dom.classTabContent ? dom.classTabContent.querySelector(".class-detail-grid-wrap") : null;

      const editor = findSpoolEditor(context.rowId, context.columnName);
      if (editor instanceof HTMLElement) {
        editor.focus({ preventScroll: true });

        if (editor instanceof HTMLInputElement || editor instanceof HTMLTextAreaElement) {
          const start = Number.isFinite(context.selectionStart) ? context.selectionStart : editor.value.length;
          const end = Number.isFinite(context.selectionEnd) ? context.selectionEnd : start;
          const safeStart = Math.max(0, Math.min(start, editor.value.length));
          const safeEnd = Math.max(0, Math.min(end, editor.value.length));
          editor.setSelectionRange(safeStart, safeEnd);
        }
      }

      window.scrollTo(context.pageX || 0, context.pageY || 0);
      if (tableWrap) {
        tableWrap.scrollTop = context.tableScrollTop || 0;
        tableWrap.scrollLeft = context.tableScrollLeft || 0;
        state.classTableScrollTop = tableWrap.scrollTop;
        state.classTableScrollLeft = tableWrap.scrollLeft;
      }
      if (detailWrap) {
        detailWrap.scrollTop = context.detailScrollTop || 0;
        detailWrap.scrollLeft = context.detailScrollLeft || 0;
        state.detailGridScrollTop = detailWrap.scrollTop;
        state.detailGridScrollLeft = detailWrap.scrollLeft;
      }
    });
  }

  function findSpoolEditor(rowId, columnName) {
    if (!dom.classTabContent) return null;

    const editors = dom.classTabContent.querySelectorAll("[data-action='spool-edit']");
    for (const editor of editors) {
      const editorRowId = Number(editor.getAttribute("data-row-id"));
      const editorColumn = editor.getAttribute("data-column") || "";
      if (editorRowId !== rowId) continue;
      if (editorColumn !== columnName) continue;
      return editor;
    }

    return null;
  }

  function bindHoverHints() {
    hideHoverHint();
  }

  function bindHintTargets(rootElement) {
    if (!dom.hoverHint || !(rootElement instanceof Element)) return;

    const targets = rootElement.querySelectorAll(".hintable[data-hint]");
    targets.forEach((target) => {
      if (!(target instanceof HTMLElement)) return;
      if (target.dataset.hintBound === "1") return;
      target.dataset.hintBound = "1";

      target.addEventListener("mouseenter", (event) => {
        const text = target.getAttribute("data-hint") || "";
        if (!text) return;
        showHoverHint(text, event);
      });

      target.addEventListener("mousemove", (event) => {
        if (dom.hoverHint && !dom.hoverHint.hidden) {
          placeHoverHint(event);
        }
      });

      target.addEventListener("mouseleave", () => {
        hideHoverHint();
      });
    });
  }

  function showHoverHint(text, event) {
    if (!dom.hoverHint) return;
    dom.hoverHint.textContent = text;
    dom.hoverHint.hidden = false;
    placeHoverHint(event);
  }

  function placeHoverHint(event) {
    if (!dom.hoverHint) return;
    const x = Math.min(window.innerWidth - dom.hoverHint.offsetWidth - 8, Math.max(8, event.clientX + 12));
    const y = Math.min(window.innerHeight - dom.hoverHint.offsetHeight - 8, Math.max(8, event.clientY + 12));
    dom.hoverHint.style.left = `${x}px`;
    dom.hoverHint.style.top = `${y}px`;
  }

  function hideHoverHint() {
    if (!dom.hoverHint) return;
    dom.hoverHint.hidden = true;
  }

  async function loadClassificationData() {
    try {
      const payload = await resolveClassificationPayload();
      state.ruleData = RULE_ENGINE.buildRuleData(payload, window.FL_LOOKUPS);

      if (dom.dataState) {
        dom.dataState.textContent = "Loaded";
        dom.dataState.classList.remove("error");
        dom.dataState.classList.add("ok");
      }

      const meta = state.ruleData.meta;
      if (dom.metaState) {
        if (meta) {
          dom.metaState.textContent = `${meta.componentCount} / ${meta.aggregateCount} / ${meta.functionKeyCount}`;
        } else {
          dom.metaState.textContent = `${Object.keys(state.ruleData.componentMap).length} / ${Object.keys(state.ruleData.aggregateMap).length}`;
        }
      }
    } catch (error) {
      try {
        if (window.FL_LOOKUPS && typeof window.FL_LOOKUPS === "object") {
          state.ruleData = RULE_ENGINE.buildRuleData({}, window.FL_LOOKUPS);
          if (dom.dataState) {
            dom.dataState.textContent = "Lookup";
            dom.dataState.classList.remove("error");
            dom.dataState.classList.add("ok");
          }
          if (dom.metaState) {
            dom.metaState.textContent = `${Object.keys(state.ruleData.componentMap).length} / ${Object.keys(state.ruleData.aggregateMap).length} / ${state.ruleData.functionKeySet.size}`;
          }
          setRuntime("Rules loaded from local lookup fallback.");
          return;
        }
      } catch (fallbackError) {
        const fallbackText = fallbackError && fallbackError.message ? fallbackError.message : String(fallbackError);
        const primaryText = error && error.message ? error.message : String(error);
        if (dom.metaState) {
          dom.metaState.textContent = `${primaryText} | fallback: ${fallbackText}`;
        }
      }

      state.ruleData.loaded = false;
      if (dom.dataState) {
        dom.dataState.textContent = "Failed";
        dom.dataState.classList.remove("ok");
        dom.dataState.classList.add("error");
      }
      if (dom.metaState && !dom.metaState.textContent) {
        dom.metaState.textContent = error && error.message ? error.message : String(error);
      }
      setRuntime("Rules missing.");
    }
  }

  function buildSpoolRuleIndex() {
    const lookups = window.FL_LOOKUPS && typeof window.FL_LOOKUPS === "object" ? window.FL_LOOKUPS : {};
    const charByClass = {};

    const charRows = Array.isArray(lookups.Char && lookups.Char.rows) ? lookups.Char.rows : [];
    charRows.forEach((entry) => {
      if (!Array.isArray(entry)) return;

      const className = normalizeUpper(entry[0]);
      const fieldName = toText(entry[1]);
      const searchKey = toText(entry[2]);
      const maxLengthToken = toText(entry[3]);

      if (!className || !fieldName) return;

      if (!charByClass[className]) charByClass[className] = {};

      const normalizedField = normalizeUpper(fieldName);
      const parsedLength = Number.parseInt(maxLengthToken, 10);

      charByClass[className][normalizedField] = {
        fieldName,
        searchKey,
        maxLength: Number.isFinite(parsedLength) ? parsedLength : 0,
        dropdown: normalizeUpper(maxLengthToken) === "DROPDOWN",
      };
    });

    const dropdownValuesByTable = {};
    Object.values(DROPDOWN_TABLE_BY_FIELD).forEach((tableName) => {
      dropdownValuesByTable[tableName] = buildDropdownValuesFromTable(lookups, tableName);
    });

    state.spoolRules.charByClass = charByClass;
    state.spoolRules.dropdownValuesByTable = dropdownValuesByTable;
    state.spoolRules.sceByClass = buildSceByClass(lookups);
    state.spoolRules.classSteps = buildClassSteps(lookups);
  }

  function buildClassSteps(lookups) {
    const result = {};
    const table = lookups && lookups.ClassVerifyConfig;
    const rows = Array.isArray(table && table.rows) ? table.rows : [];

    rows.forEach((entry) => {
      if (!Array.isArray(entry)) return;
      const className = normalizeUpper(entry[0]);
      const rawSteps = toText(entry[1]);
      if (!className || !rawSteps) return;

      const parsedSteps = rawSteps
        .replaceAll("\r", ",")
        .replaceAll("\n", ",")
        .replaceAll(";", ",")
        .replaceAll("|", ",")
        .split(",")
        .map((step) => toText(step))
        .filter(Boolean);

      if (parsedSteps.length) {
        result[className] = parsedSteps;
      }
    });

    return result;
  }

  function buildDropdownValuesFromTable(lookups, tableName) {
    const table = lookups && lookups[tableName];
    const rows = Array.isArray(table && table.rows) ? table.rows : [];
    const values = rows
      .map((entry) => (Array.isArray(entry) ? toText(entry[0]) : ""))
      .filter(Boolean);

    return dedupeMessages(values);
  }

  function buildSceByClass(lookups) {
    const table = lookups && lookups.SCEq;
    const headers = Array.isArray(table && table.headers) ? table.headers : [];
    const rows = Array.isArray(table && table.rows) ? table.rows : [];
    const result = {};

    if (!headers.length || !rows.length) return result;

    for (let colIndex = 1; colIndex < headers.length; colIndex += 1) {
      const className = normalizeUpper(headers[colIndex]);
      if (!className) continue;

      const values = [];
      rows.forEach((row) => {
        if (!Array.isArray(row)) return;
        const value = toText(row[colIndex]);
        if (value) values.push(value);
      });

      result[className] = dedupeMessages(values);
    }

    return result;
  }

  async function resolveClassificationPayload() {
    if (window.FL_CLASSIFICATION_DATA && typeof window.FL_CLASSIFICATION_DATA === "object") {
      return window.FL_CLASSIFICATION_DATA;
    }

    const response = await fetch("js/data/fl-classification-data.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  function addRow() {
    state.rows.push({
      id: state.nextId,
      functionalLocation: "",
      description: "",
      spoolValues: {},
      spoolFieldIssues: {},
      kksType: "",
      assignedClass: "",
      candidateClasses: [],
      sapDescription: "",
      status: "draft",
      blockingIssues: [],
      warnings: [],
      notes: [],
    });

    state.nextId += 1;
  }

  function onTableInput(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;

    const field = target.getAttribute("data-field");
    const rowId = Number(target.getAttribute("data-row-id"));
    if (!field || !Number.isFinite(rowId)) return;

    const row = state.rows.find((item) => item.id === rowId);
    if (!row) return;

    ensureRowSpoolState(row);

    if (field === "functionalLocation") {
      const normalized = normalizeFlTyped(target.value);
      row.functionalLocation = normalized;
      target.value = normalized;
    } else if (field === "description") {
      row.description = toText(target.value);
    }

    row.status = "draft";
    row.blockingIssues = [];
    row.warnings = [];
    row.notes = [];
    row.spoolFieldIssues = {};
    row.kksType = "";
    row.assignedClass = "";
    row.candidateClasses = [];
    row.sapDescription = "";

    renderMetrics();
  }

  function handleValidationTableKeydown(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.getAttribute("data-field") !== "functionalLocation") return;
    if (event.key !== "Tab" || event.shiftKey || event.ctrlKey || event.altKey || event.metaKey) return;

    const rowId = Number(target.getAttribute("data-row-id"));
    if (!Number.isFinite(rowId) || !dom.rowsBody) return;

    const descriptionInput = dom.rowsBody.querySelector(`input[data-field="description"][data-row-id="${rowId}"]`);
    if (!(descriptionInput instanceof HTMLInputElement)) return;

    event.preventDefault();
    state.pendingRowFocus = {
      rowId,
      field: "description",
    };
    descriptionInput.focus();

    const caret = descriptionInput.value.length;
    descriptionInput.setSelectionRange(caret, caret);
  }

  function resolveRowFocusHintAfterFlChange(target) {
    if (!(target instanceof HTMLInputElement)) return null;
    if (target.getAttribute("data-field") !== "functionalLocation") return null;

    const rowId = Number(target.getAttribute("data-row-id"));
    if (!Number.isFinite(rowId)) return null;

    const activeElement = document.activeElement;
    if (!(activeElement instanceof HTMLInputElement)) return null;
    if (activeElement.getAttribute("data-field") !== "description") return null;

    const activeRowId = Number(activeElement.getAttribute("data-row-id"));
    if (activeRowId !== rowId) return null;

    return {
      rowId,
      field: "description",
    };
  }

  async function runVerification(focusHint = null) {
    if (state.verificationInProgress) return;

    state.pendingRowFocus = focusHint || null;

    state.verificationInProgress = true;
    if (dom.btnVerify) {
      dom.btnVerify.disabled = true;
      dom.btnVerify.textContent = "Verifying...";
    }

    setRuntime("Running local checks...");

    try {
      const rowsToVerify = state.rows.filter((row) => !isRowBlank(row));
      if (!rowsToVerify.length) {
        revalidateRowsAndRender("");
        setRuntime("No rows to verify.");
        return;
      }

      revalidateRowsAndRender("");

      setRuntime("Done.");
    } finally {
      state.verificationInProgress = false;
      if (dom.btnVerify) {
        dom.btnVerify.disabled = false;
        dom.btnVerify.textContent = "Verify";
      }
    }
  }

  function buildDuplicateCountMap(rows) {
    const map = new Map();

    rows.forEach((row) => {
      const fl = normalizeFunctionalLocation(row.functionalLocation);
      if (!fl) return;
      map.set(fl, (map.get(fl) || 0) + 1);
    });

    return map;
  }

  function applyLocalValidation(row, duplicateMap) {
    const fl = normalizeFunctionalLocation(row.functionalLocation);
    const description = toText(row.description);

    const blockingIssues = [];
    const warnings = [];
    const notes = [];

    ensureRowSpoolState(row);

    row.functionalLocation = fl;
    row.description = description;
    row.sapDescription = "";
    row.kksType = "";
    row.assignedClass = "";
    row.candidateClasses = [];

    if (isRowBlank({ functionalLocation: fl, description })) {
      row.blockingIssues = [];
      row.warnings = [];
      row.notes = [];
      row.spoolFieldIssues = {};
      row.status = "draft";
      return;
    }

    if (!fl) {
      blockingIssues.push("FL required.");
    }

    if (fl && duplicateMap.get(fl) > 1) {
      blockingIssues.push("Duplicate FL.");
    }

    if (!description) {
      blockingIssues.push("Description required before Ready for SAP.");
    }

    if (description.length > 40) {
      blockingIssues.push("Description > 40.");
    }

    const syntaxInfo = evaluateKksSyntax(fl);
    row.kksType = syntaxInfo.kksType;

    if (syntaxInfo.blockingIssue) blockingIssues.push(syntaxInfo.blockingIssue);
    if (syntaxInfo.warning) warnings.push(syntaxInfo.warning);

    const classInfo = determineClass(fl, syntaxInfo.syntaxClass);

    row.assignedClass = classInfo.className || "";
    row.candidateClasses = row.assignedClass ? [row.assignedClass] : [];
    if (classInfo.notes.length) notes.push(...classInfo.notes);
    if (classInfo.warnings.length) warnings.push(...classInfo.warnings);
    if (classInfo.blockingIssues.length) blockingIssues.push(...classInfo.blockingIssues);

    if (!row.assignedClass && !blockingIssues.length) {
      row.assignedClass = "NO CLASS";
      row.candidateClasses = ["NO CLASS"];
    }

    const spoolValidation = validateSpoolFields(row);
    if (spoolValidation.blockingIssues.length) blockingIssues.push(...spoolValidation.blockingIssues);
    if (spoolValidation.warnings.length) warnings.push(...spoolValidation.warnings);
    row.spoolFieldIssues = spoolValidation.fieldIssues;

    row.blockingIssues = dedupeMessages(blockingIssues);
    row.warnings = dedupeMessages(warnings);
    row.notes = dedupeMessages(notes);

    if (row.blockingIssues.length) {
      row.status = "invalid";
    } else if (row.warnings.length) {
      row.status = "warning";
    } else {
      row.status = "valid";
    }
  }

  function evaluateKksSyntax(fl) {
    return RULE_ENGINE.evaluateKksSyntax(fl);
  }

  function determineClass(fl, syntaxClass) {
    return RULE_ENGINE.determineClass(fl, syntaxClass, state.ruleData);
  }

  function ensureRowSpoolState(row) {
    if (!row || typeof row !== "object") return;
    if (!row.spoolValues || typeof row.spoolValues !== "object") {
      row.spoolValues = {};
    }
    if (!row.spoolFieldIssues || typeof row.spoolFieldIssues !== "object") {
      row.spoolFieldIssues = {};
    }
  }

  function validateSpoolFields(row) {
    const className = normalizeUpper(row.assignedClass || "NO CLASS");
    const classRules = (state.spoolRules.charByClass && state.spoolRules.charByClass[className]) || {};
    const classSteps = resolveClassSteps(className);

    const fieldIssues = {};
    const blockingIssues = [];
    const warnings = [];
    const issueSet = new Set();

    const addIssue = (normalizedField, message) => {
      const fieldLabel = resolveColumnLabel(className, normalizedField);
      if (!fieldIssues[normalizedField]) {
        fieldIssues[normalizedField] = message;
      }

      const fullMessage = `${fieldLabel}: ${message}`;
      if (!issueSet.has(fullMessage)) {
        issueSet.add(fullMessage);
        blockingIssues.push(fullMessage);
      }
    };

    const addRuleViolation = (normalizedField, message) => {
      addIssue(normalizedField, message);
    };

    Object.keys(classRules).forEach((normalizedField) => {
      const rule = classRules[normalizedField];
      const value = toText(getSpoolColumnValue(row, normalizedField));
      if (!value) return;

      if (rule.maxLength > 0 && value.length > rule.maxLength) {
        addRuleViolation(normalizedField, `Max ${rule.maxLength} characters.`);
      }

      if (rule.dropdown) {
        const options = resolveDropdownOptions(className, normalizedField);
        if (options.length && !valueMatchesAllowedList(value, options)) {
          addRuleViolation(normalizedField, "Value must match dropdown options.");
        }
      }
    });

    runMasterDataValidation(row, addRuleViolation);

    classSteps.forEach((step) => {
      if (step === "Design_pressure_") runDesignPressureValidation(row, className, addRuleViolation);
      if (step === "Operating_pressure_") runOperatingPressureValidation(row, className, addRuleViolation);
      if (step === "Design_temperature_") runDesignTemperatureValidation(row, className, addRuleViolation);
      if (step === "Operating_temperature_") runOperatingTemperatureValidation(row, className, addRuleViolation);
      if (step === "Design_flow_") runDesignFlowValidation(row, className, addRuleViolation);
      if (step === "Typekreds") runTypekredsValidation(row, className, addRuleViolation);
      if (step === "TestMethod") runTestMethodValidation(row, className, addRuleViolation);
      if (step === "TRMNEW") runTrmValidation(row, className, addRuleViolation);
      if (CLASS_SPECIFIC_FIELD_RULES[step]) runClassSpecificValidation(row, step, addRuleViolation);
      if (step === "KKS_Syntax") runKksSyntaxValidation(row, addRuleViolation);
    });

    return {
      fieldIssues,
      blockingIssues,
      warnings,
    };
  }

  function resolveClassSteps(className) {
    if (state.spoolRules.classSteps && state.spoolRules.classSteps[className]) {
      return state.spoolRules.classSteps[className];
    }

    if (CLASS_STEP_RULES[className]) return CLASS_STEP_RULES[className];
    return CLASS_STEP_RULES.DEFAULT;
  }

  function runMasterDataValidation(row, addIssue) {
    Object.keys(MASTERDATA_FIELD_RULES).forEach((normalizedField) => {
      const value = toText(getSpoolColumnValue(row, normalizedField));
      const rule = MASTERDATA_FIELD_RULES[normalizedField];

      if (rule.required && !value) {
        addIssue(normalizedField, "Required field.");
      }

      if (rule.maxLength > 0 && value.length > rule.maxLength) {
        addIssue(normalizedField, `Max ${rule.maxLength} characters.`);
      }

      if (DATE_FIELD_SET.has(normalizedField) && value && !isValidWarrantyDate(value)) {
        addIssue(normalizedField, "Use DD.MM.YYYY or YYYYMMDD.");
      }
    });

    Object.keys(BUILTIN_ALLOWED_VALUES_BY_FIELD).forEach((normalizedField) => {
      const value = toText(getSpoolColumnValue(row, normalizedField));
      if (!value) return;

      const allowed = BUILTIN_ALLOWED_VALUES_BY_FIELD[normalizedField] || [];
      if (!valueMatchesAllowedList(value, allowed)) {
        addIssue(normalizedField, `Allowed values: ${allowed.join(", ")}.`);
      }
    });
  }

  function runDesignPressureValidation(row, className, addIssue) {
    runStepFieldValidation(row, className, "Design_pressure_", addIssue);
    validateDropdownField(row, className, "DESIGN PRESSURE UOM", addIssue);
  }

  function runOperatingPressureValidation(row, className, addIssue) {
    runStepFieldValidation(row, className, "Operating_pressure_", addIssue);
    validateDropdownField(row, className, "OPERATING PRESSURE UOM", addIssue);
  }

  function runDesignTemperatureValidation(row, className, addIssue) {
    runStepFieldValidation(row, className, "Design_temperature_", addIssue);
    validateDropdownField(row, className, "DESIGN TEMPERATURE UOM", addIssue);
  }

  function runOperatingTemperatureValidation(row, className, addIssue) {
    runStepFieldValidation(row, className, "Operating_temperature_", addIssue);
    validateDropdownField(row, className, "OPERATING TEMPERATURE UOM", addIssue);
  }

  function runDesignFlowValidation(row, className, addIssue) {
    runStepFieldValidation(row, className, "Design_flow_", addIssue);
    validateDropdownField(row, className, "DESIGN FLOW UOM", addIssue);
  }

  function runTypekredsValidation(row, className, addIssue) {
    validateDropdownField(row, className, "TYPEKREDSE", addIssue);
  }

  function runTestMethodValidation(row, className, addIssue) {
    validateDropdownField(row, className, "TEST METHOD", addIssue);
    validateDropdownField(row, className, "TEST METHOD 2", addIssue);
  }

  function runTrmValidation(row, className, addIssue) {
    runStepFieldValidation(row, className, "TRMNEW", addIssue);

    validateDropdownField(row, className, "SAFETY CRITICAL EQUIPMENT", addIssue);

    if (className === "MKP" || className === "NO CLASS") {
      validateDropdownField(row, className, "FIRE CLASSIFICATION", addIssue);
      validateDropdownField(row, className, "FIRE SEALING TYPE", addIssue);
    }

    const hasAnyTrmInput = ["EX-MARKING", "SAFETY CRITICAL EQUIPMENT", "FIRE CLASSIFICATION", "FIRE SEALING TYPE", "FIRE SEALING PRODUCT"].some((field) =>
      toText(getSpoolColumnValue(row, field))
    );

    if (hasAnyTrmInput) {
      setSpoolColumnValue(row, "TRM ASSIGNMENT", "X");
      setSpoolColumnValue(row, "ABC INDIC.", "A");
    } else {
      setSpoolColumnValue(row, "TRM ASSIGNMENT", "");
    }

    if (className === "MKP") {
      const fl = normalizeFunctionalLocation(row.functionalLocation);
      const key12 = fl.length >= 13 ? fl.slice(11, 13) : "";
      const key17 = fl.length >= 18 ? fl.slice(16, 18) : "";

      if (key12 === "UE") {
        setSpoolColumnValue(row, "TRM ASSIGNMENT", "X");

        if (!toText(getSpoolColumnValue(row, "FIRE CLASSIFICATION"))) {
          addIssue("FIRE CLASSIFICATION", "Required when aggregate key is UE.");
        }

        if (key17 === "FP") {
          if (!toText(getSpoolColumnValue(row, "FIRE SEALING TYPE"))) {
            addIssue("FIRE SEALING TYPE", "Required for UE/FP.");
          }
          if (!toText(getSpoolColumnValue(row, "FIRE SEALING PRODUCT"))) {
            addIssue("FIRE SEALING PRODUCT", "Required for UE/FP.");
          }
        }
      }
    }
  }

  function runClassSpecificValidation(row, className, addIssue) {
    const rules = CLASS_SPECIFIC_FIELD_RULES[className] || {};
    Object.keys(rules).forEach((normalizedField) => {
      validateFieldByRule(row, normalizedField, rules[normalizedField], addIssue);
    });
  }

  function runKksSyntaxValidation(row, addIssue) {
    const fl = normalizeFunctionalLocation(row.functionalLocation);
    if (!fl) return;

    const syntaxInfo = evaluateKksSyntax(fl);
    if (syntaxInfo.blockingIssue) {
      addIssue("FUNCTIONAL LOCATION", syntaxInfo.blockingIssue);
    }
  }

  function runStepFieldValidation(row, className, stepName, addIssue) {
    const rules = STEP_FIELD_RULES[stepName] || {};
    Object.keys(rules).forEach((field) => {
      validateFieldByRule(row, field, rules[field], addIssue);
    });

    const classRules = (state.spoolRules.charByClass && state.spoolRules.charByClass[className]) || {};
    Object.keys(classRules).forEach((field) => {
      const classRule = classRules[field];
      if (!classRule || !classRule.dropdown) return;

      const tableName = DROPDOWN_TABLE_BY_SEARCH_KEY[normalizeUpper(classRule.searchKey)];
      if (!tableName) return;

      validateDropdownField(row, className, field, addIssue);
    });
  }

  function validateFieldByRule(row, normalizedField, rule, addIssue) {
    const value = toText(getSpoolColumnValue(row, normalizedField));
    if (!value) {
      if (rule.required) addIssue(normalizedField, "Required field.");
      return;
    }

    if (rule.maxLength > 0 && value.length > rule.maxLength) {
      addIssue(normalizedField, `Max ${rule.maxLength} characters.`);
    }

    if (rule.regex instanceof RegExp && !rule.regex.test(value)) {
      addIssue(normalizedField, "Invalid value format.");
    }
  }

  function validateDropdownField(row, className, normalizedField, addIssue) {
    const value = toText(getSpoolColumnValue(row, normalizedField));
    if (!value) return;

    const options = resolveDropdownOptions(className, normalizeUpper(normalizedField));
    if (options.length && !valueMatchesAllowedList(value, options)) {
      addIssue(normalizeUpper(normalizedField), "Value must match dropdown options.");
    }
  }

  function resolveDropdownOptions(className, normalizedField) {
    if (BUILTIN_ALLOWED_VALUES_BY_FIELD[normalizedField]) {
      return BUILTIN_ALLOWED_VALUES_BY_FIELD[normalizedField];
    }

    if (normalizedField === "SAFETY CRITICAL EQUIPMENT") {
      return (state.spoolRules.sceByClass && state.spoolRules.sceByClass[className]) || [];
    }

    const tableName = DROPDOWN_TABLE_BY_FIELD[normalizedField];
    if (tableName) {
      return (state.spoolRules.dropdownValuesByTable && state.spoolRules.dropdownValuesByTable[tableName]) || [];
    }

    const classRules = (state.spoolRules.charByClass && state.spoolRules.charByClass[className]) || {};
    const classRule = classRules[normalizedField];
    if (classRule && classRule.dropdown) {
      const fallbackTable = DROPDOWN_TABLE_BY_SEARCH_KEY[normalizeUpper(classRule.searchKey)];
      if (fallbackTable) {
        return (state.spoolRules.dropdownValuesByTable && state.spoolRules.dropdownValuesByTable[fallbackTable]) || [];
      }
    }

    return [];
  }

  function valueMatchesAllowedList(value, allowedValues) {
    const normalizedAllowed = new Set((allowedValues || []).map((entry) => normalizeUpper(entry)).filter(Boolean));
    if (!normalizedAllowed.size) return true;

    const tokens = toText(value)
      .split("|")
      .map((entry) => toText(entry))
      .filter(Boolean);

    if (!tokens.length) return true;

    return tokens.every((token) => normalizedAllowed.has(normalizeUpper(token)));
  }

  function isValidWarrantyDate(value) {
    const text = toText(value);
    if (!text) return true;

    const compact = /^\d{8}$/;
    const dotted = /^\d{2}\.\d{2}\.\d{4}$/;
    if (!compact.test(text) && !dotted.test(text)) return false;

    if (compact.test(text)) {
      const year = Number.parseInt(text.slice(0, 4), 10);
      const month = Number.parseInt(text.slice(4, 6), 10);
      const day = Number.parseInt(text.slice(6, 8), 10);
      const parsed = new Date(year, month - 1, day);
      return parsed.getFullYear() === year && parsed.getMonth() === month - 1 && parsed.getDate() === day;
    }

    const [dayText, monthText, yearText] = text.split(".");
    const year = Number.parseInt(yearText, 10);
    const month = Number.parseInt(monthText, 10);
    const day = Number.parseInt(dayText, 10);
    const parsed = new Date(year, month - 1, day);
    return parsed.getFullYear() === year && parsed.getMonth() === month - 1 && parsed.getDate() === day;
  }

  function resolveColumnLabel(className, normalizedField) {
    const classRules = (state.spoolRules.charByClass && state.spoolRules.charByClass[className]) || {};
    const classRule = classRules[normalizedField];
    if (classRule && classRule.fieldName) return classRule.fieldName;

    const fromDefault = DEFAULT_SPOOL_COLUMNS.find((column) => normalizeUpper(column) === normalizedField);
    if (fromDefault) return fromDefault;

    return normalizedField;
  }

  function distributeRowsIntoClasses() {
    const buckets = {};

    state.rows.forEach((row) => {
      if (row.status === "draft") return;
      const className = normalizeUpper(row.assignedClass);
      if (!className) return;
      if (!buckets[className]) buckets[className] = [];
      buckets[className].push(row);
    });

    Object.keys(buckets).forEach((className) => {
      buckets[className].sort((a, b) => a.functionalLocation.localeCompare(b.functionalLocation));
    });

    state.classBuckets = buckets;

    if (state.activeClassTab !== "ALL" && !state.classBuckets[state.activeClassTab]) {
      state.activeClassTab = "ALL";
    }
  }

  function renderRows() {
    dom.rowsBody.innerHTML = "";

    state.rows.forEach((row, index) => {
      const tr = document.createElement("tr");

      const validationBadges = renderValidationBadges(row);

      tr.innerHTML = `
        <td>${index + 1}</td>
        <td>
          <input class="table-input ${getFieldStateClass(row, "functionalLocation")}" data-field="functionalLocation" data-row-id="${row.id}" value="${escapeHtml(row.functionalLocation)}" maxlength="40" autocomplete="off" />
        </td>
        <td>
          <input class="table-input ${getFieldStateClass(row, "description")}" data-field="description" data-row-id="${row.id}" value="${escapeHtml(row.description)}" maxlength="40" autocomplete="off" />
        </td>
        <td>${row.kksType ? `<span class="kks-type-pill">${escapeHtml(row.kksType)}</span>` : "-"}</td>
        <td>${renderClassCell(row)}</td>
        <td>
          ${validationBadges}
        </td>
        <td>
          <button class="action-btn danger" type="button" data-action="delete-row" data-row-id="${row.id}">Delete</button>
        </td>
      `;

      dom.rowsBody.appendChild(tr);
    });

    bindHintTargets(dom.rowsBody);
    restorePendingRowFocus();
  }

  function restorePendingRowFocus() {
    const focusHint = state.pendingRowFocus;
    state.pendingRowFocus = null;

    if (!focusHint || !dom.rowsBody) return;

    requestAnimationFrame(() => {
      const selector = `input[data-field="${focusHint.field}"][data-row-id="${focusHint.rowId}"]`;
      const input = dom.rowsBody.querySelector(selector);
      if (!(input instanceof HTMLInputElement)) return;

      input.focus({ preventScroll: true });
      const caret = input.value.length;
      input.setSelectionRange(caret, caret);
    });
  }

  function renderValidationBadges(row) {
    const label = row.status === "draft" ? "Draft" : row.status === "valid" ? "Valid" : row.status === "warning" ? "Warning" : "Invalid";
    const issue = row.blockingIssues.length ? row.blockingIssues[0] : "";
    const warning = row.warnings.length ? row.warnings[0] : "";
    const badges = [];

    if (!(row.status === "invalid" && issue)) {
      badges.push(`<span class="status-chip ${row.status}">${label}</span>`);
    }

    if (issue) {
      const issueHelp = resolveValidationIssueHelpText(row, issue);
      const issueHintAttr = issueHelp ? ` data-hint="${escapeHtml(issueHelp)}"` : "";
      const issueHintClass = issueHelp ? " hintable" : "";
      badges.push(`<span class="validation-msg-badge error${issueHintClass}" aria-label="Validation issue"${issueHintAttr}>${escapeHtml(issue)}</span>`);
    } else if (warning) {
      const warningHelp = resolveValidationIssueHelpText(row, warning);
      const warningHintAttr = warningHelp ? ` data-hint="${escapeHtml(warningHelp)}"` : "";
      const warningHintClass = warningHelp ? " hintable" : "";
      badges.push(`<span class="validation-msg-badge warn${warningHintClass}" aria-label="Validation warning"${warningHintAttr}>${escapeHtml(warning)}</span>`);
    }

    if (!badges.length) return "";
    return `<div class="validation-badge-row">${badges.join("")}</div>`;
  }

  function resolveValidationIssueHelpText(row, issueText) {
    const issue = toText(issueText);
    if (!issue) return "";

    const fl = normalizeFunctionalLocation(row && row.functionalLocation);
    const key0 = fl.length >= 3 ? fl.slice(0, 3) : "";
    const key7 = fl.length >= 9 ? fl.slice(6, 9) : "";
    const key12 = fl.length >= 13 ? fl.slice(11, 13) : "";
    const key17 = fl.length >= 18 ? fl.slice(16, 18) : "";
    const key18 = fl.length >= 19 ? fl.slice(17, 19) : "";

    if (issue === "Function key invalid.") {
      const keyLabel = key7 || "missing";
      return `Function key is FL position 7-9 (${keyLabel}). It must exist in FunctionKeyDict lookup.`;
    }

    if (issue === "Plant key invalid.") {
      const keyLabel = key0 || "missing";
      return `Plant key is FL position 1-3 (${keyLabel}). It must exist in Plant lookup.`;
    }

    if (issue === "Component key invalid.") {
      const keyLabel = key18 || "missing";
      return `Component key is FL position 18-19 (${keyLabel}). No class mapping was found for this key.`;
    }

    if (issue === "Equipment key invalid.") {
      const keyLabel = key12 || "missing";
      return `Equipment/Aggregate key is FL position 12-13 (${keyLabel}). No aggregate mapping was found.`;
    }

    if (issue === "UF/UE requires U function key.") {
      const key12Label = key12 || "missing";
      const key7Label = key7 || "missing";
      return `For aggregate ${key12Label}, function key (position 7-9) must start with U. Current value: ${key7Label}.`;
    }

    if (/^BR18 key17 invalid for /.test(issue)) {
      const key12Label = key12 || "missing";
      const key17Label = key17 || "missing";
      return `BR18 check failed: for aggregate ${key12Label}, key17 (position 17-18) value ${key17Label} is not allowed.`;
    }

    if (/^BR18 rules missing for /.test(issue)) {
      const key12Label = key12 || "missing";
      return `No BR18 rule set is loaded for aggregate key ${key12Label}.`;
    }

    if (issue === "KKS invalid.") {
      return "Functional Location does not match the allowed KKS patterns.";
    }

    if (issue === "Class not determined.") {
      return "KKS structure is valid, but no class rule matched component/aggregate/fallback mapping.";
    }

    return "";
  }

  function renderClassTabs() {
    const classNames = Object.keys(state.classBuckets).sort((a, b) => a.localeCompare(b));
    const tabDefinitions = [
      {
        key: "ALL",
        label: `ALL (${classNames.reduce((acc, name) => acc + state.classBuckets[name].length, 0)})`,
      },
      ...classNames.map((className) => ({
        key: className,
        label: `${className} (${state.classBuckets[className].length})`,
      })),
    ];

    dom.classTabs.innerHTML = "";

    tabDefinitions.forEach((tab) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "pill-tab";
      button.setAttribute("data-class-tab", tab.key);
      button.setAttribute("aria-selected", state.activeClassTab === tab.key ? "true" : "false");
      const helpText = resolveClassHelpText(tab.key);
      if (helpText) {
        button.title = `${tab.key}: ${helpText}`;
      }
      button.textContent = tab.label;
      dom.classTabs.appendChild(button);
    });

    const rows =
      state.activeClassTab === "ALL"
        ? dedupeRowsById(classNames.flatMap((className) => state.classBuckets[className].map((row) => ({ ...row, __className: className }))))
        : (state.classBuckets[state.activeClassTab] || []).map((row) => ({ ...row, __className: state.activeClassTab }));

    if (!rows.length) {
      dom.classTabContent.innerHTML = '<p class="small-muted">No rows.</p>';
      return;
    }

    const spoolColumns = resolveSpoolColumns(state.activeClassTab === "ALL" ? "" : state.activeClassTab);
    const viewColumns = resolveVisibleColumns(spoolColumns, state.classViewPreset);
    const tableColumns = buildClassTableColumns(viewColumns);

    const host = document.createElement("div");
    host.className = "class-view-shell";

    const toolbar = document.createElement("div");
    toolbar.className = "class-view-toolbar";
    toolbar.innerHTML = `
      <div class="class-view-presets">
        <button type="button" class="class-view-btn" data-class-view="compact" aria-pressed="${state.classViewPreset === CLASS_VIEW_PRESETS.compact}">Compact</button>
        <button type="button" class="class-view-btn" data-class-view="all" aria-pressed="${state.classViewPreset === CLASS_VIEW_PRESETS.all}">All columns</button>
      </div>
      <p class="small-muted class-view-meta">Showing ${tableColumns.length} columns</p>
    `;
    host.appendChild(toolbar);

    const table = document.createElement("table");
    table.className = `data-table data-table-fl-classes ${state.classViewPreset === CLASS_VIEW_PRESETS.all ? "mode-all" : "mode-compact"}`;
    table.innerHTML = `
      <thead>
        <tr>
          ${tableColumns.map((column) => `<th>${escapeHtml(resolveClassTableHeader(column))}</th>`).join("")}
          <th class="details-col">Details</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row, rowIndex) => `
          <tr>
            ${tableColumns.map((column) => `<td>${renderSpoolColumnCell(row, column, rowIndex)}</td>`).join("")}
            <td class="details-col"><button type="button" class="row-detail-btn" data-action="open-class-details" data-row-id="${row.id}" data-row-class="${escapeHtml(normalizeUpper(row.__className || row.assignedClass || "NO CLASS"))}">Open</button></td>
          </tr>
        `
          )
          .join("")}
      </tbody>
    `;

    const wrap = document.createElement("div");
    wrap.className = "data-table-wrap";
    wrap.style.maxHeight = "48vh";
    wrap.appendChild(table);

    host.appendChild(wrap);

    const detailModal = renderDetailModal(rows);
    if (detailModal) {
      host.appendChild(detailModal);
    }

    dom.classTabContent.innerHTML = "";
    dom.classTabContent.appendChild(host);
    syncClassTabScrollState();
    enhanceClassTabSelects();
    bindHintTargets(dom.classTabContent);
  }

  function enhanceClassTabSelects() {
    if (!dom.classTabContent) return;

    const selects = Array.from(dom.classTabContent.querySelectorAll("select[data-action='spool-edit']"));
    const entries = [];

    selects.forEach((select) => {
      if (!(select instanceof HTMLSelectElement)) return;
      if (select.dataset.flStyled === "1") return;

      const parent = select.parentElement;
      if (!parent) return;

      const wrapper = document.createElement("div");
      wrapper.className = "vh-select-wrap fl-select-wrap";

      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "vh-select-trigger fl-select-trigger";
      trigger.setAttribute("aria-haspopup", "listbox");
      trigger.setAttribute("aria-expanded", "false");

      const panel = document.createElement("div");
      panel.className = "combo-panel-lite vh-select-panel fl-select-panel";
      panel.hidden = true;

      parent.insertBefore(wrapper, select);
      wrapper.appendChild(select);
      wrapper.appendChild(trigger);
      wrapper.appendChild(panel);

      select.dataset.flStyled = "1";
      select.classList.add("vh-select-native", "fl-select-native");

      const entry = { select, wrapper, trigger, panel };
      entries.push(entry);

      trigger.addEventListener("click", () => {
        const willOpen = panel.hidden;
        state.flSelectUi.entries.forEach((other) => {
          if (other !== entry) {
            closeClassTabStyledSelect(other);
          }
        });

        if (!willOpen) {
          closeClassTabStyledSelect(entry);
          return;
        }

        renderClassTabStyledSelectOptions(entry);
        panel.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        wrapper.classList.add("open");
      });

      select.addEventListener("change", () => syncClassTabStyledSelect(select));
      syncClassTabStyledSelectEntry(entry);
    });

    state.flSelectUi.entries = entries;

    if (!state.flSelectUi.outsideBound) {
      document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Node)) return;

        state.flSelectUi.entries.forEach((entry) => {
          if (!entry.wrapper.contains(target)) {
            closeClassTabStyledSelect(entry);
          }
        });
      });

      state.flSelectUi.outsideBound = true;
    }
  }

  function renderClassTabStyledSelectOptions(entry) {
    entry.panel.innerHTML = "";

    const options = Array.from(entry.select.options || []);
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "combo-option";
      const optionText = toText(opt.textContent || opt.value || "");
      btn.textContent = optionText || "Select";

      if (opt.value === entry.select.value) {
        btn.classList.add("active");
      }

      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        entry.select.value = opt.value;
        entry.select.dispatchEvent(new Event("input", { bubbles: true }));
        entry.select.dispatchEvent(new Event("change", { bubbles: true }));
        closeClassTabStyledSelect(entry);
      });

      entry.panel.appendChild(btn);
    });
  }

  function closeClassTabStyledSelect(entry) {
    entry.panel.hidden = true;
    entry.trigger.setAttribute("aria-expanded", "false");
    entry.wrapper.classList.remove("open");
  }

  function syncClassTabStyledSelect(select) {
    const entry = state.flSelectUi.entries.find((x) => x.select === select);
    if (!entry) return;

    syncClassTabStyledSelectEntry(entry);
  }

  function syncClassTabStyledSelectEntry(entry) {
    if (!entry || !entry.select || !entry.trigger) return;

    const selectedOption = entry.select.options[entry.select.selectedIndex];
    const text = selectedOption ? toText(selectedOption.textContent || "") : "";
    entry.trigger.textContent = text || "Select";

    entry.trigger.classList.remove("valid", "warning", "invalid");
    ["valid", "warning", "invalid"].forEach((cssClass) => {
      if (entry.select.classList.contains(cssClass)) {
        entry.trigger.classList.add(cssClass);
      }
    });

    const issueText = toText(entry.select.getAttribute("title"));
    if (issueText) {
      entry.trigger.classList.add("hintable");
      entry.trigger.setAttribute("data-hint", issueText);
    } else {
      entry.trigger.classList.remove("hintable");
      entry.trigger.removeAttribute("data-hint");
    }
  }

  function syncClassTabScrollState() {
    if (!dom.classTabContent) return;

    const tableWrap = dom.classTabContent.querySelector(".data-table-wrap");
    if (tableWrap instanceof HTMLElement) {
      if (tableWrap.dataset.scrollBound !== "1") {
        tableWrap.dataset.scrollBound = "1";
        tableWrap.addEventListener("scroll", () => {
          state.classTableScrollTop = tableWrap.scrollTop;
          state.classTableScrollLeft = tableWrap.scrollLeft;
        });
      }

      tableWrap.scrollTop = state.classTableScrollTop || 0;
      tableWrap.scrollLeft = state.classTableScrollLeft || 0;
    }

    const detailWrap = dom.classTabContent.querySelector(".class-detail-grid-wrap");
    if (detailWrap instanceof HTMLElement) {
      if (detailWrap.dataset.scrollBound !== "1") {
        detailWrap.dataset.scrollBound = "1";
        detailWrap.addEventListener("scroll", () => {
          state.detailGridScrollTop = detailWrap.scrollTop;
          state.detailGridScrollLeft = detailWrap.scrollLeft;
        });
      }

      detailWrap.scrollTop = state.detailGridScrollTop || 0;
      detailWrap.scrollLeft = state.detailGridScrollLeft || 0;
    }
  }

  function resolveVisibleColumns(spoolColumns, preset) {
    const cleanColumns = spoolColumns.map(toText).filter(Boolean);
    if (!cleanColumns.length) return [];

    if (preset === CLASS_VIEW_PRESETS.all) {
      return cleanColumns;
    }

    const byKey = new Map(cleanColumns.map((column) => [normalizeUpper(column), column]));
    const compactColumns = COMPACT_COLUMN_ORDER.map((column) => byKey.get(normalizeUpper(column))).filter(Boolean);

    if (compactColumns.length) {
      return compactColumns;
    }

    return cleanColumns.slice(0, Math.min(10, cleanColumns.length));
  }

  function buildClassTableColumns(viewColumns) {
    const fixedColumnKeys = CLASS_TABLE_FIXED_COLUMNS.map((entry) => entry.key);
    const seen = new Set(fixedColumnKeys.map((column) => normalizeClassTableColumnKey(column)));

    const dynamicColumns = [];
    viewColumns.forEach((column) => {
      const text = toText(column);
      if (!text) return;
      if (isHiddenClassTableColumn(text)) return;

      const normalized = normalizeClassTableColumnKey(text);
      if (seen.has(normalized)) return;

      seen.add(normalized);
      dynamicColumns.push(text);
    });

    return [...fixedColumnKeys, ...dynamicColumns];
  }

  function resolveClassTableHeader(columnKey) {
    const fixed = CLASS_TABLE_FIXED_COLUMNS.find((entry) => entry.key === columnKey);
    if (fixed) return fixed.label;
    return columnKey;
  }

  function normalizeClassTableColumnKey(columnKey) {
    const normalized = normalizeUpper(columnKey);
    if (normalized === "STR. INDICATOR") return "STRINDICATOR";
    return normalized;
  }

  function isHiddenClassTableColumn(columnKey) {
    const normalized = normalizeClassTableColumnKey(columnKey);
    return normalized === "SAP STATUS";
  }

  function renderDetailModal(rows) {
    if (!Number.isFinite(state.detailRowId)) return null;

    const detailRow = rows.find((row) => {
      if (row.id !== state.detailRowId) return false;
      if (!state.detailRowClassName) return true;
      return normalizeUpper(row.__className || row.assignedClass || "") === state.detailRowClassName;
    });

    if (!detailRow) {
      closeDetailModal();
      return null;
    }

    const className = normalizeUpper(detailRow.__className || detailRow.assignedClass || "NO CLASS");
    const detailColumns = resolveSpoolColumns(className);
    const detailEntries = detailColumns.map((column) => {
      const normalized = normalizeUpper(column);
      const value = toText(getSpoolColumnValue(detailRow, normalized));
      const issue = resolveSpoolFieldIssue(detailRow, normalized);
      const editor = renderSpoolEditor(detailRow, column, className, "detail");
      return { column, normalized, value, issue, editor };
    });

    const visibleEntries = state.detailShowEmpty ? detailEntries : detailEntries.filter((entry) => entry.value || entry.issue);
    const detailBody =
      visibleEntries.length > 0
        ? `
      <table class="class-detail-table">
        <thead>
          <tr>
            <th>Column</th>
            <th>Value</th>
            <th>Validation</th>
          </tr>
        </thead>
        <tbody>
          ${visibleEntries
            .map(
              (entry) => `
            <tr>
              <td>${escapeHtml(entry.column)}</td>
              <td>${entry.editor || renderSpoolReadonlyValue(detailRow, entry.normalized, entry.value)}</td>
              <td>${entry.issue ? `<span class="validation-msg-badge error">${escapeHtml(entry.issue)}</span>` : ""}</td>
            </tr>
          `
            )
            .join("")}
        </tbody>
      </table>
    `
        : '<p class="small-muted">No populated fields for this row.</p>';

    const modal = document.createElement("div");
    modal.className = "class-detail-backdrop";
    modal.innerHTML = `
      <div class="class-detail-modal" role="dialog" aria-modal="true" aria-label="Class row details">
        <div class="class-detail-head">
          <div>
            <h3>Row details</h3>
            <p class="small-muted">Class: ${escapeHtml(className)} | FL: ${escapeHtml(detailRow.functionalLocation || "-")}</p>
          </div>
          <div class="class-detail-actions">
            <button type="button" class="action-btn" data-action="toggle-empty-details">${state.detailShowEmpty ? "Hide empty" : "Show empty"}</button>
            <button type="button" class="action-btn primary" data-action="close-class-details">Close</button>
          </div>
        </div>
        <div class="class-detail-grid-wrap">
          ${detailBody}
        </div>
      </div>
    `;

    return modal;
  }

  function resolveSpoolColumns(className) {
    const configured = window.FL_SPOOL_COLUMNS;

    if (Array.isArray(configured)) {
      const values = configured.map(toText).filter(Boolean);
      if (values.length) return values;
    }

    if (configured && typeof configured === "object") {
      const key = normalizeUpper(className);
      const byClass = configured[key] || configured.DEFAULT;
      if (Array.isArray(byClass)) {
        const values = byClass.map(toText).filter(Boolean);
        if (values.length) return values;
      }
    }

    return DEFAULT_SPOOL_COLUMNS.slice();
  }

  function renderSpoolColumnCell(row, columnName, rowIndex) {
    if (columnName === "__ROW_NO__") {
      return String((Number.isFinite(rowIndex) ? rowIndex : 0) + 1);
    }

    const normalized = normalizeUpper(columnName);
    const className = normalizeUpper(row.__className || row.assignedClass || "NO CLASS");

    if (normalized === "CLASS") {
      return renderClassBadge(className);
    }

    const editor = renderSpoolEditor(row, columnName, className, "table");
    if (editor) return editor;

    const value = getSpoolColumnValue(row, normalized);
    return renderSpoolReadonlyValue(row, normalized, value);
  }

  function renderSpoolReadonlyValue(row, normalizedColumn, rawValue) {
    const value = toText(rawValue);
    if (!value) return "";

    if (normalizedColumn === "SAP STATUS") {
      return `<span class="status-chip ${row.status}">${escapeHtml(getSapStatusText(row))}</span>`;
    }

    if (normalizedColumn === "INFO") {
      const tone = row.blockingIssues && row.blockingIssues.length ? "error" : row.warnings && row.warnings.length ? "warn" : "info";
      const helpText = resolveValidationIssueHelpText(row, value);
      const hintAttr = helpText ? ` data-hint="${escapeHtml(helpText)}"` : "";
      const hintClass = helpText ? " hintable" : "";
      return `<span class="validation-msg-badge ${tone}${hintClass}"${hintAttr}>${escapeHtml(value)}</span>`;
    }

    if (normalizedColumn === "STRINDICATOR" || normalizedColumn === "STR. INDICATOR") {
      return `<span class="kks-type-pill">${escapeHtml(value)}</span>`;
    }

    return escapeHtml(value);
  }

  function renderSpoolEditor(row, columnName, className, context) {
    const normalized = normalizeUpper(columnName);
    if (!isEditableSpoolColumn(normalized)) return "";

    const value = toText(getSpoolColumnValue(row, normalized));
    const options = resolveDropdownOptions(className, normalized);
    const fieldState = resolveSpoolFieldStateClass(row, normalized);
    const issue = resolveSpoolFieldIssue(row, normalized);
    const maxLength = resolveMaxLengthForField(className, normalized);
    const maxLengthAttr = maxLength > 0 ? ` maxlength="${maxLength}"` : "";
    const cssClass = context === "detail" ? "class-detail-input" : "class-cell-input";
    const selectClass = context === "detail" ? "class-detail-select" : "class-cell-select";
    const titleAttr = issue ? ` title="${escapeHtml(issue)}"` : "";

    if (options.length) {
      const normalizedValue = normalizeUpper(value);
      const hasSelectedOption = options.some((entry) => normalizeUpper(entry) === normalizedValue);
      const optionMarkup = options
        .map((entry) => {
          const text = toText(entry);
          const selected = normalizedValue === normalizeUpper(text) ? " selected" : "";
          return `<option value="${escapeHtml(text)}"${selected}>${escapeHtml(text)}</option>`;
        })
        .join("");

      const customInvalidOption = value && !hasSelectedOption ? `<option value="${escapeHtml(value)}" selected>${escapeHtml(value)}</option>` : "";

      return `
        <select class="${selectClass} ${fieldState}" data-action="spool-edit" data-row-id="${row.id}" data-row-class="${escapeHtml(className)}" data-column="${escapeHtml(columnName)}"${titleAttr}>
          <option value=""></option>
          ${customInvalidOption}
          ${optionMarkup}
        </select>
      `;
    }

    return `<input class="${cssClass} ${fieldState}" data-action="spool-edit" data-row-id="${row.id}" data-row-class="${escapeHtml(className)}" data-column="${escapeHtml(columnName)}" value="${escapeHtml(value)}" autocomplete="off"${maxLengthAttr}${titleAttr} />`;
  }

  function isEditableSpoolColumn(normalizedColumn) {
    return !READ_ONLY_SPOOL_COLUMNS.has(normalizedColumn);
  }

  function resolveSpoolFieldStateClass(row, normalizedColumn) {
    if (normalizedColumn === "FUNCTIONAL LOCATION") {
      return getFieldStateClass(row, "functionalLocation");
    }

    if (normalizedColumn === "DESCRIPTION") {
      return getFieldStateClass(row, "description");
    }

    const issue = resolveSpoolFieldIssue(row, normalizedColumn);
    if (issue) return "invalid";

    const value = toText(getSpoolColumnValue(row, normalizedColumn));
    return value ? "valid" : "";
  }

  function resolveSpoolFieldIssue(row, normalizedColumn) {
    if (!row) return "";

    if (normalizedColumn === "FUNCTIONAL LOCATION") {
      const issue = (row.blockingIssues || []).find(isFunctionalLocationIssue);
      return toText(issue);
    }

    if (normalizedColumn === "DESCRIPTION") {
      const issue = (row.blockingIssues || []).find(isDescriptionIssue);
      return toText(issue);
    }

    if (row.spoolFieldIssues && row.spoolFieldIssues[normalizedColumn]) {
      return toText(row.spoolFieldIssues[normalizedColumn]);
    }

    const fallback = (row.blockingIssues || []).find((entry) => {
      const text = toText(entry);
      if (!text.includes(":")) return false;
      const fieldToken = normalizeUpper(text.split(":")[0]);
      return fieldToken === normalizedColumn;
    });

    if (!fallback) return "";
    const full = toText(fallback);
    const separatorIndex = full.indexOf(":");
    if (separatorIndex < 0) return "";
    return toText(full.slice(separatorIndex + 1));
  }

  function resolveMaxLengthForField(className, normalizedColumn) {
    if (normalizedColumn === "DESCRIPTION") return 40;

    const classRules = (state.spoolRules.charByClass && state.spoolRules.charByClass[className]) || {};
    const classRule = classRules[normalizedColumn];
    if (classRule && classRule.maxLength > 0) return classRule.maxLength;

    if (normalizedColumn === "FUNCTIONAL LOCATION") return 40;
    return 0;
  }

  function getSapStatusText(row) {
    if (!row || row.status === "draft") return "Draft";
    if (row.status === "invalid") return "Error not ready for SAP";
    return "Ready for SAP";
  }

  function getSpoolColumnValue(row, normalizedColumn) {
    if (!row) return "";

    ensureRowSpoolState(row);

    if (normalizedColumn === "INFO") {
      if (row.blockingIssues && row.blockingIssues.length) return row.blockingIssues[0];
      if (row.warnings && row.warnings.length) return row.warnings[0];
      if (row.notes && row.notes.length) return row.notes[0];
      return "";
    }

    if (normalizedColumn === "STRINDICATOR" || normalizedColumn === "STR. INDICATOR") {
      return row.kksType || "";
    }

    if (normalizedColumn === "FUNCTIONAL LOCATION") {
      return row.functionalLocation || "";
    }

    if (normalizedColumn === "DESCRIPTION") {
      return row.description || "";
    }

    if (normalizedColumn === "LONG TEXT") {
      return row.spoolValues[normalizedColumn] || row.description || "";
    }

    if (normalizedColumn === "USER STATUS") {
      return row.status ? row.status.toUpperCase() : "";
    }

    if (normalizedColumn === "SYSTEM STATUS") {
      return "LOCAL";
    }

    return row.spoolValues[normalizedColumn] || "";
  }

  function renderMetrics() {
    const total = state.rows.length;
    const ready = state.rows.filter((row) => row.status === "valid" || row.status === "warning").length;
    const issues = state.rows.filter((row) => row.status === "invalid").length;

    if (dom.metricTotal) dom.metricTotal.textContent = String(total);
    if (dom.metricReady) dom.metricReady.textContent = String(ready);
    if (dom.metricIssues) dom.metricIssues.textContent = String(issues);
  }

  function exportJson() {
    const payload = {
      generatedAt: new Date().toISOString(),
      source: "functional-location-web-shell",
      rows: state.rows,
      classBuckets: state.classBuckets,
      ruleMeta: state.ruleData.meta,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `functional_location_export_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    setRuntime("Exported JSON.");
  }

  function isRowBlank(row) {
    const fl = normalizeFunctionalLocation(row && row.functionalLocation);
    const description = toText(row && row.description);
    return !fl && !description;
  }

  function getFieldStateClass(row, field) {
    if (!row || row.status === "draft") return "";

    if (field === "functionalLocation") {
      if (row.blockingIssues.some(isFunctionalLocationIssue)) return "invalid";
      return "valid";
    }

    if (field === "description") {
      if (row.blockingIssues.some(isDescriptionIssue)) return "invalid";
      return row.description ? "valid" : "";
    }

    if (row.status === "invalid") return "invalid";
    if (row.status === "warning") return "warning";
    return "valid";
  }

  function isFunctionalLocationIssue(message) {
    const text = toText(message);
    return (
      text.includes("FL") ||
      text.includes("KKS") ||
      text.includes("Plant") ||
      text.includes("Function") ||
      text.includes("Component") ||
      text.includes("Equipment") ||
      text.includes("BR18") ||
      text.includes("Class")
    );
  }

  function isDescriptionIssue(message) {
    return toText(message).includes("Description");
  }

  function dedupeMessages(messages) {
    const set = new Set();
    messages.forEach((message) => {
      const text = toText(message);
      if (text) set.add(text);
    });
    return Array.from(set.values());
  }

  function setRuntime(message) {
    if (dom.runtimeInfo) {
      dom.runtimeInfo.textContent = message;
    }
  }

  function renderClassCell(row) {
    const primary = normalizeUpper(row.assignedClass);
    if (!primary) return "-";
    return renderClassBadge(primary);
  }

  function renderClassBadge(className) {
    const primary = normalizeUpper(className);
    if (!primary) return "-";

    const helpText = resolveClassHelpText(primary);
    if (!helpText) {
      return `<span class="class-pill">${escapeHtml(primary)}</span>`;
    }

    return `<span class="class-pill hintable" data-hint="${escapeHtml(primary + ": " + helpText)}">${escapeHtml(primary)}</span>`;
  }

  function resolveClassHelpText(className) {
    const key = normalizeUpper(className);
    if (!key || key === "ALL" || key === "NO CLASS") return "";
    return CLASS_HELP[key] || "";
  }

  function dedupeRowsById(rows) {
    const seen = new Set();
    return rows.filter((row) => {
      if (seen.has(row.id)) return false;
      seen.add(row.id);
      return true;
    });
  }

  function normalizeFlTyped(value) {
    return String(value == null ? "" : value)
      .replaceAll("\u00A0", " ")
      .replaceAll("\r", "")
      .replaceAll("\n", "")
      .toUpperCase();
  }

  function normalizeFunctionalLocation(value) {
    return RULE_ENGINE.normalizeFunctionalLocation(value);
  }
})();

(function () {
  const { toText, normalizeUpper, clipText, escapeHtml } = window.TextUtils;

  const FIELD_KEYS = [
    "functionalLocation",
    "manufacturer",
    "modelNumber",
    "manufacturerPartNo",
    "materialDescription",
    "documentation",
    "stockUnit",
    "price",
    "priceUnit",
    "deliveringTime",
    "recommendedStock",
    "supplier",
    "supplierPartNo",
    "strategicPart",
    "wearPart",
  ];

  const FIELD_LABELS = {
    functionalLocation: "Functional Location",
    manufacturer: "Manufacturer",
    modelNumber: "Model Number",
    manufacturerPartNo: "Manufacturer Part No.",
    materialDescription: "Material Description",
    documentation: "Documentation",
    stockUnit: "Stock Unit",
    price: "Price",
    priceUnit: "Price unit",
    deliveringTime: "Delivering time",
    recommendedStock: "Recommended stock",
    supplier: "Supplier",
    supplierPartNo: "Supplier's Part no.",
    strategicPart: "Strategic part",
    wearPart: "Wear part",
  };

  const REQUIRED_FIELDS = [
    "manufacturer",
    "modelNumber",
    "manufacturerPartNo",
    "materialDescription",
    "stockUnit",
    "price",
    "priceUnit",
  ];

  const MATERIAL_TABLE_VIEW = Object.freeze({
    compact: "compact",
    all: "all",
  });

  const COMPACT_FIELD_KEYS = [
    "functionalLocation",
    "materialDescription",
    "manufacturer",
    "manufacturerPartNo",
    "supplier",
  ];

  const ALLOWED_PLANTS = new Set(["SSV", "SKV", "HEV", "HCV", "ASV", "AVV", "KYV", "STV", "SMV"]);
  const FL_MIN_LEN_OK = 16;
  const MIN_DELIVERING_TIME = 30;
  const DEFAULT_DELIVERING_TIME = String(MIN_DELIVERING_TIME);
  const PLANT_NAME_BY_PREFIX = {
    SKV: "Skærbækværket",
    SSV: "Studstrupværket",
    ASV: "Asnæsværket",
    AVV: "Avedøreværket",
    HCV: "H.C. Ørsted Værket",
    KYV: "Kyndbyværket",
    HEV: "Herningværket",
    STV: "STV",
    SMV: "SMV",
  };

  const ODATA_BASE_URL = "https://sapap1yq2.de-prod.dk:44302/sap/opu/odata/sap/ZEAM_ODATA_SRV/UpDownFL";
  const ODATA_SELECT_FIELDS = "Tplnr,Pltxt";
  const ODATA_PROXY_BASE = "http://127.0.0.1:8765";
  const ODATA_TIMEOUT_MS = 20000;
  const ODATA_SUGGEST_TIMEOUT_MS = 8000;
  const ODATA_SUGGEST_MAX_PAGES = 6;
  const ODATA_CACHE_MS = 10 * 60 * 1000;
  const ODATA_SUGGEST_CACHE_MS = 5 * 60 * 1000;
  const ODATA_MAX_CACHE_ENTRIES = 220;
  const FL_SUGGEST_MIN_CHARS = 7;
  const SUGGEST_DEBOUNCE_MS = 140;
  const SUGGEST_FALLBACK_MAX_STEPS = 2;
  const ODATA_SUGGEST_FAILURE_COOLDOWN_MS = 15000;
  const SEARCH_DOTS_INTERVAL_MS = 280;
  const SEARCH_INPUT_DEBOUNCE_MS = 120;
  const MAILTO_MAX_URL_LENGTH = 1850;
  const MAILTO_RECIPIENT = "sapvedligehold@orsted.com";
  const EMAIL_FIELD_LABELS_DA = {
    functionalLocation: "Funktionslokation",
    manufacturer: "Producent",
    modelNumber: "Modelnummer",
    manufacturerPartNo: "Producent varenummer",
    materialDescription: "Materialebeskrivelse",
    documentation: "Dokumentation",
    stockUnit: "Lagerenhed",
    price: "Pris",
    priceUnit: "Prisenhed",
    deliveringTime: "Leveringstid",
    recommendedStock: "Anbefalet lager",
    supplier: "Leverandør",
    supplierPartNo: "Leverandør varenummer",
    strategicPart: "Strategisk del",
    wearPart: "Sliddel",
  };

  const STOCK_UNIT_OPTIONS = [
    ["PC", "PIECE"],
    ["EA", "EACH"],
    ["SET", "SET"],
    ["PR", "PAIR"],
    ["M", "METER"],
    ["CM", "CENTIMETER"],
    ["MM", "MILLIMETER"],
    ["M2", "SQUARE METER"],
    ["M3", "CUBIC METER"],
    ["KG", "KILOGRAM"],
    ["G", "GRAM"],
    ["L", "LITER"],
    ["ML", "MILLILITER"],
    ["H", "HOUR"],
  ];

  const PRICE_UNIT_OPTIONS = [
    ["PC", "PRICE PER PIECE"],
    ["EA", "PRICE PER EACH"],
    ["10", "PRICE PER 10"],
    ["100", "PRICE PER 100"],
    ["1000", "PRICE PER 1000"],
    ["SET", "PRICE PER SET"],
    ["KG", "PRICE PER KILOGRAM"],
    ["L", "PRICE PER LITER"],
    ["M", "PRICE PER METER"],
  ];

  const YES_NO_OPTIONS = [
    ["YES", "YES"],
    ["NO", "NO"],
  ];

  const STOCK_UNIT_SET = new Set(STOCK_UNIT_OPTIONS.map((entry) => entry[0]));
  const PRICE_UNIT_SET = new Set(PRICE_UNIT_OPTIONS.map((entry) => entry[0]));
  const NO_SUCCESS_GLOW_FIELDS = new Set(["strategicPart", "wearPart"]);
  const STOCK_UNIT_MAP = new Map(STOCK_UNIT_OPTIONS);
  const PRICE_UNIT_MAP = new Map(PRICE_UNIT_OPTIONS);
  const YES_NO_MAP = new Map(YES_NO_OPTIONS);

  const FL_PATTERNS = [
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z]?$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FD|FG|FH|FW|FC|FP)$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z\s][-A-Z]{2}\d{2}$/i,
    /^[A-Z]{3}\d{2,3}$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{1,3}$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{4}$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{1}\d{4}$/i,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\s{3}\d{4}$/i,
  ];

  const state = {
    rows: [],
    nextRowId: 1,
    editIndex: null,
    editRowId: null,
    previewToken: 0,
    filters: { search: "", status: "all", plant: "all" },
    tableView: MATERIAL_TABLE_VIEW.compact,
    detailRowId: null,
    fl: {
      lookupCache: new Map(),
      inFlight: new Map(),
      suggestionCache: new Map(),
      suggestionInFlight: new Map(),
      suggestAbortController: null,
      suggestions: [],
      activeIndex: -1,
      debounceTimer: null,
      token: 0,
      interacted: false,
      searchDotsTimer: null,
      searchDotsCount: 0,
      isSuggesting: false,
      suggestBackoffUntil: 0,
      verifyDebounceTimer: null,
    },
    net: {
      useLocalProxy: false,
      localProxyBase: ODATA_PROXY_BASE,
    },
    ui: {
      deliveringTimeInteracted: false,
      searchDebounceTimer: null,
      lastTableHeadKey: "",
      saveInProgress: false,
    },
    units: {
      stock: { suggestions: [], activeIndex: -1 },
      price: { suggestions: [], activeIndex: -1 },
      strategic: { suggestions: [], activeIndex: -1 },
      wear: { suggestions: [], activeIndex: -1 },
    },
    styledSelects: [],
  };

  const dom = {};

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    bindDom();
    initializeLocalProxyUi();
    setupClearButtons();
    bindEvents();
    initializeUnitHints();
    setupStyledSelects();
    resetForm(true);
    syncFlBypassUI();
    renderAll();
    setRuntime("Ready.");
  }

  function bindDom() {
    dom.form = document.getElementById("spareForm");
    dom.validationList = document.getElementById("validationList");
    dom.rowsBody = document.getElementById("rowsBody");
    dom.searchInput = document.getElementById("searchInput");
    dom.statusFilter = document.getElementById("statusFilter");
    dom.plantFilter = document.getElementById("plantFilter");
    dom.btnSave = document.getElementById("btnSave");
    dom.btnSubmitRows = document.getElementById("btnSubmitRows");
    dom.btnExportCsv = document.getElementById("btnExportCsv");
    dom.btnSendEmail = document.getElementById("btnSendEmailMaterialer");
    dom.btnReset = document.getElementById("btnReset");
    dom.btnLocalProxy = document.getElementById("btnLocalProxy");
    dom.bypassFunctionalLocation = document.getElementById("bypassFunctionalLocation");
    dom.btnToggleNoBom = document.getElementById("btnToggleNoBom");
    dom.functionalLocation = document.getElementById("functionalLocation");
    dom.functionalLocationDesc = document.getElementById("functionalLocationDesc");
    dom.functionalLocationSuggestions = document.getElementById("functionalLocationSuggestions");
    dom.btnPickDocumentation = document.getElementById("btnPickDocumentation");
    dom.documentationFile = document.getElementById("documentationFile");
    dom.detectedPlant = document.getElementById("detectedPlant");
    dom.detectedStatus = document.getElementById("detectedStatus");
    dom.kpiRows = document.getElementById("kpiRows");
    dom.kpiValid = document.getElementById("kpiValid");
    dom.kpiInvalid = document.getElementById("kpiInvalid");
    dom.stockUnit = document.getElementById("stockUnit");
    dom.priceUnit = document.getElementById("priceUnit");
    dom.stockUnitSuggestions = document.getElementById("stockUnitSuggestions");
    dom.priceUnitSuggestions = document.getElementById("priceUnitSuggestions");
    dom.strategicPart = document.getElementById("strategicPart");
    dom.wearPart = document.getElementById("wearPart");
    dom.strategicPartSuggestions = document.getElementById("strategicPartSuggestions");
    dom.wearPartSuggestions = document.getElementById("wearPartSuggestions");
    dom.runtimeInfo = document.getElementById("runtimeInfo");
    dom.rowsTable = document.getElementById("rowsTable");
    dom.tableWrap = document.querySelector(".spareparts-table-wrap");
    dom.btnMaterialViewCompact = document.getElementById("btnMaterialViewCompact");
    dom.btnMaterialViewAll = document.getElementById("btnMaterialViewAll");
    dom.materialDetailsHost = document.getElementById("materialDetailsHost");
  }

  function initializeUnitHints() {
    const stockInput = document.getElementById("stockUnit");
    const priceInput = document.getElementById("priceUnit");
    const strategicInput = document.getElementById("strategicPart");
    const wearInput = document.getElementById("wearPart");
    if (stockInput) updateUnitFieldHint(stockInput, STOCK_UNIT_MAP, "Stock Unit: choose a unit code.");
    if (priceInput) updateUnitFieldHint(priceInput, PRICE_UNIT_MAP, "Price unit: choose a unit code.");
    if (strategicInput) updateUnitFieldHint(strategicInput, YES_NO_MAP, "Strategic part: choose YES or NO.");
    if (wearInput) updateUnitFieldHint(wearInput, YES_NO_MAP, "Wear part: choose YES or NO.");
  }

  function updateUnitFieldHint(input, unitMap, defaultText) {
    const label = input && input.closest("label");
    if (!label) return;
    const code = normalizeUpper(input.value);
    if (code && unitMap.has(code)) {
      label.setAttribute("data-hint", `${code}: ${unitMap.get(code)}`);
      input.title = unitMap.get(code);
      return;
    }
    label.setAttribute("data-hint", defaultText);
    input.removeAttribute("title");
  }

  function bindEvents() {
    dom.form.addEventListener("submit", onSave);

    dom.btnReset.addEventListener("click", () => {
      resetForm(true);
      previewValidation();
      setRuntime("Form reset.");
    });

    dom.searchInput.addEventListener("input", () => {
      state.filters.search = toText(dom.searchInput.value).toLowerCase();
      scheduleSearchRender();
    });

    dom.statusFilter.addEventListener("change", () => {
      state.filters.status = dom.statusFilter.value;
      renderRows();
    });

    dom.plantFilter.addEventListener("change", () => {
      state.filters.plant = dom.plantFilter.value;
      renderRows();
    });

    if (dom.btnMaterialViewCompact) {
      dom.btnMaterialViewCompact.addEventListener("click", () => {
        state.tableView = MATERIAL_TABLE_VIEW.compact;
        renderRows();
      });
    }

    if (dom.btnMaterialViewAll) {
      dom.btnMaterialViewAll.addEventListener("click", () => {
        state.tableView = MATERIAL_TABLE_VIEW.all;
        renderRows();
      });
    }

    if (dom.btnSubmitRows) {
      dom.btnSubmitRows.addEventListener("click", () => {
        setRuntime("Submit not connected.");
      });
    }

    dom.btnExportCsv.addEventListener("click", exportCsv);

    if (dom.btnSendEmail) {
      dom.btnSendEmail.addEventListener("click", sendRowsAsEmail);
    }

    if (dom.rowsBody) {
      dom.rowsBody.addEventListener("click", onRowsBodyClick);
    }

    if (dom.materialDetailsHost) {
      dom.materialDetailsHost.addEventListener("click", onMaterialDetailsClick);
    }

    if (dom.btnLocalProxy) {
      dom.btnLocalProxy.addEventListener("click", async () => {
        if (state.net.useLocalProxy) {
          setLocalProxyEnabled(false);
          setRuntime("Local proxy disabled.");
          return;
        }

        const ok = await probeLocalProxy();
        if (!ok) {
          setLocalProxyEnabled(true);
          setRuntime("Local proxy enabled (fallback mode). Proxy health check failed, but requests will still try proxy first.");
          return;
        }

        setLocalProxyEnabled(true);
        setRuntime("Local proxy enabled.");
      });
    }

    dom.btnToggleNoBom.addEventListener("click", () => {
      dom.bypassFunctionalLocation.checked = !dom.bypassFunctionalLocation.checked;
      syncFlBypassUI();
      previewValidation();
    });

    dom.btnPickDocumentation.addEventListener("click", () => {
      dom.documentationFile.click();
    });

    dom.documentationFile.addEventListener("change", () => {
      const file = dom.documentationFile.files && dom.documentationFile.files[0];
      if (!file) return;
      const docInput = document.getElementById("documentation");
      if (!docInput) return;
      docInput.value = file.name;
      refreshClearButton(docInput);
      previewValidation();
      setRuntime(`Selected file: ${file.name}`);
    });

    FIELD_KEYS.forEach((key) => {
      const input = document.getElementById(key);
      if (!input) return;
      input.addEventListener("input", () => {
        if (key === "deliveringTime") {
          state.ui.deliveringTimeInteracted = true;
        }
        if (key === "stockUnit") {
          updateUnitFieldHint(input, STOCK_UNIT_MAP, "Stock Unit: choose a unit code.");
        }
        if (key === "priceUnit") {
          updateUnitFieldHint(input, PRICE_UNIT_MAP, "Price unit: choose a unit code.");
        }
        if (key === "strategicPart") {
          updateUnitFieldHint(input, YES_NO_MAP, "Strategic part: choose YES or NO.");
        }
        if (key === "wearPart") {
          updateUnitFieldHint(input, YES_NO_MAP, "Wear part: choose YES or NO.");
        }
        refreshClearButton(input);
        previewValidation();
      });
      input.addEventListener("change", () => {
        if (key === "deliveringTime") {
          state.ui.deliveringTimeInteracted = true;
        }
        if (key === "stockUnit") {
          updateUnitFieldHint(input, STOCK_UNIT_MAP, "Stock Unit: choose a unit code.");
        }
        if (key === "priceUnit") {
          updateUnitFieldHint(input, PRICE_UNIT_MAP, "Price unit: choose a unit code.");
        }
        if (key === "strategicPart") {
          updateUnitFieldHint(input, YES_NO_MAP, "Strategic part: choose YES or NO.");
        }
        if (key === "wearPart") {
          updateUnitFieldHint(input, YES_NO_MAP, "Wear part: choose YES or NO.");
        }
        refreshClearButton(input);
        previewValidation();
      });
    });

    if (dom.stockUnit) {
      dom.stockUnit.addEventListener("focus", () => {
        renderUnitSuggestions("stock", "");
      });
      dom.stockUnit.addEventListener("input", () => {
        renderUnitSuggestions("stock", dom.stockUnit.value);
      });
      dom.stockUnit.addEventListener("keydown", (event) => {
        onUnitKeyDown("stock", event);
      });
      dom.stockUnit.addEventListener("blur", () => {
        setTimeout(() => hideUnitSuggestions("stock"), 120);
      });
    }

    if (dom.priceUnit) {
      dom.priceUnit.addEventListener("focus", () => {
        renderUnitSuggestions("price", "");
      });
      dom.priceUnit.addEventListener("input", () => {
        renderUnitSuggestions("price", dom.priceUnit.value);
      });
      dom.priceUnit.addEventListener("keydown", (event) => {
        onUnitKeyDown("price", event);
      });
      dom.priceUnit.addEventListener("blur", () => {
        setTimeout(() => hideUnitSuggestions("price"), 120);
      });
    }

    if (dom.strategicPart) {
      dom.strategicPart.addEventListener("focus", () => {
        renderUnitSuggestions("strategic", "");
      });
      dom.strategicPart.addEventListener("input", () => {
        renderUnitSuggestions("strategic", dom.strategicPart.value);
      });
      dom.strategicPart.addEventListener("keydown", (event) => {
        onUnitKeyDown("strategic", event);
      });
      dom.strategicPart.addEventListener("blur", () => {
        setTimeout(() => hideUnitSuggestions("strategic"), 120);
      });
    }

    if (dom.wearPart) {
      dom.wearPart.addEventListener("focus", () => {
        renderUnitSuggestions("wear", "");
      });
      dom.wearPart.addEventListener("input", () => {
        renderUnitSuggestions("wear", dom.wearPart.value);
      });
      dom.wearPart.addEventListener("keydown", (event) => {
        onUnitKeyDown("wear", event);
      });
      dom.wearPart.addEventListener("blur", () => {
        setTimeout(() => hideUnitSuggestions("wear"), 120);
      });
    }

    const markFlInteractedAndValidate = () => {
      if (state.fl.interacted) return;
      state.fl.interacted = true;
      previewValidation();
    };

    dom.functionalLocation.addEventListener("pointerdown", markFlInteractedAndValidate);
    dom.functionalLocation.addEventListener("focus", markFlInteractedAndValidate);
    dom.functionalLocation.addEventListener("input", onFunctionalLocationInput);
    dom.functionalLocation.addEventListener("keydown", onFunctionalLocationKeyDown);
    dom.functionalLocation.addEventListener("blur", () => {
      state.fl.interacted = true;
      setTimeout(hideFlSuggestions, 120);
      queueBackgroundFlLookup(normalizeUpper(dom.functionalLocation.value).trim());
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (state.detailRowId === null) return;
      state.detailRowId = null;
      renderMaterialDetailModal();
    });
  }

  function scheduleSearchRender() {
    if (state.ui.searchDebounceTimer) {
      window.clearTimeout(state.ui.searchDebounceTimer);
    }

    state.ui.searchDebounceTimer = window.setTimeout(() => {
      state.ui.searchDebounceTimer = null;
      renderRows();
    }, SEARCH_INPUT_DEBOUNCE_MS);
  }

  function setupClearButtons() {
    const selector = 'input:not([type="file"]):not([type="hidden"]):not([type="checkbox"])';
    document.querySelectorAll(selector).forEach((input) => {
      if (input.closest(".doc-picker")) return;
      if (input.classList.contains("no-clear-btn")) return;

      const parent = input.parentElement;
      if (!parent) return;

      if (!input.parentElement.classList.contains("input-wrap")) {
        const wrap = document.createElement("div");
        wrap.className = "input-wrap";
        parent.insertBefore(wrap, input);
        wrap.appendChild(input);
      }

      const wrap = input.parentElement;
      if (!wrap.querySelector(".clear-btn")) {
        const clearBtn = document.createElement("button");
        clearBtn.type = "button";
        clearBtn.className = "clear-btn";
        clearBtn.textContent = "x";
        clearBtn.hidden = !toText(input.value);
        clearBtn.addEventListener("click", () => {
          input.value = "";
          refreshClearButton(input);
          previewValidation();
          input.focus();
        });
        wrap.appendChild(clearBtn);
      }

      refreshClearButton(input);
    });
  }

  function refreshClearButton(input) {
    const wrap = input.parentElement;
    if (!wrap || !wrap.classList.contains("input-wrap")) return;
    const clearBtn = wrap.querySelector(".clear-btn");
    if (!clearBtn) return;
    clearBtn.hidden = !toText(input.value);
  }

  async function onSave(event) {
    event.preventDefault();

    if (state.ui.saveInProgress) {
      return;
    }

    state.ui.saveInProgress = true;
    if (dom.btnSave) {
      dom.btnSave.disabled = true;
      dom.btnSave.textContent = "Saving...";
    }

    try {
      const row = normalizeRow(readForm());
      const validation = await validateRow(row, true);

      renderValidation(validation);
      updateValidationMeta(validation, row);
      applyFieldValidationState(validation.fieldErrors);

      if (validation.status === "invalid") {
        setRuntime("Fix validation errors.");
        return;
      }

      const currentRowId = state.editRowId || (state.editIndex === null ? null : ensureRowId(state.rows[state.editIndex]));

      const payload = {
        ...row,
        _rowId: currentRowId || state.nextRowId++,
        _skipFunctionalLocation: row._skipFunctionalLocation,
        _status: validation.status,
        _plant: validation.detectedPlant || getPlantLabelFromFl(row.functionalLocation),
        _flDescription: validation.flDescription || "",
        _issues: validation.errors.map((e) => e.text),
        _updatedAt: new Date().toISOString(),
      };

      payload._searchBlob = buildRowSearchBlob(payload);

      if (state.editIndex === null && !state.editRowId) {
        state.rows.unshift(payload);
      } else {
        let targetIndex = -1;
        if (state.editRowId) {
          targetIndex = getRowIndexById(state.editRowId);
        }
        if (targetIndex < 0 && state.editIndex !== null) {
          targetIndex = state.editIndex;
        }

        if (targetIndex >= 0) {
          state.rows[targetIndex] = payload;
        } else {
          state.rows.unshift(payload);
        }

        state.editIndex = null;
        state.editRowId = null;
      }

      resetForm(false);
      renderAll();
      previewValidation();
      setRuntime("Row saved.");
    } finally {
      state.ui.saveInProgress = false;
      if (dom.btnSave) {
        dom.btnSave.disabled = false;
        dom.btnSave.textContent = "Save row";
      }
    }
  }

  async function previewValidation() {
    const token = ++state.previewToken;
    const row = normalizeRow(readForm());
    const validation = await validateRow(row, false);
    if (token !== state.previewToken) return;

    renderValidation(validation);
    updateValidationMeta(validation, row);
    applyFieldValidationState(validation.fieldErrors);
  }

  function readForm() {
    const row = {};
    FIELD_KEYS.forEach((key) => {
      const input = document.getElementById(key);
      row[key] = toText(input ? input.value : "");
    });
    row._skipFunctionalLocation = !!dom.bypassFunctionalLocation.checked;
    return row;
  }

  function setForm(row) {
    FIELD_KEYS.forEach((key) => {
      const input = document.getElementById(key);
      if (!input) return;
      input.value = row[key] || "";
      refreshClearButton(input);
    });

    dom.bypassFunctionalLocation.checked = !!row._skipFunctionalLocation;
    state.fl.interacted = true;
    state.ui.deliveringTimeInteracted = true;
    syncFlBypassUI();
    initializeUnitHints();

    if (dom.functionalLocationDesc) {
      dom.functionalLocationDesc.className = row._flDescription ? "field-meta ok" : "field-meta";
      dom.functionalLocationDesc.textContent = row._flDescription || "";
    }
  }

  function normalizeRow(row) {
    return {
      ...row,
      functionalLocation: normalizeUpper(row.functionalLocation),
      stockUnit: normalizeUnitValue(row.stockUnit),
      priceUnit: normalizeUnitValue(row.priceUnit),
      strategicPart: normalizeYesNoStrict(row.strategicPart),
      wearPart: normalizeYesNoStrict(row.wearPart),
      deliveringTime: normalizeDeliveringTime(row.deliveringTime),
    };
  }

  function ensureRowId(row) {
    if (!row) return 0;

    const existing = Number(row._rowId);
    if (Number.isInteger(existing) && existing > 0) {
      if (existing >= state.nextRowId) {
        state.nextRowId = existing + 1;
      }
      return existing;
    }

    const rowId = state.nextRowId++;
    row._rowId = rowId;
    return rowId;
  }

  function buildRowSearchBlob(row) {
    return [
      row.functionalLocation,
      row._flDescription,
      row.manufacturer,
      row.modelNumber,
      row.manufacturerPartNo,
      row.materialDescription,
      row.documentation,
      row.supplier,
      row.supplierPartNo,
    ]
      .join(" ")
      .toLowerCase();
  }

  async function queueBackgroundFlLookup(fl) {
    const normalized = normalizeSuggestQuery(fl);
    if (!normalized || normalized.length < FL_SUGGEST_MIN_CHARS || dom.bypassFunctionalLocation.checked) return;

    const result = await verifyFlInOData(normalized);
    if (normalizeUpper(dom.functionalLocation.value).trim() !== normalized) return;

    if (!result.ok) {
      if (isAbortLikeError(result.error || "")) {
        return;
      }
      updateFlMetaText(formatODataErrorHint(result.error || "SAP lookup unavailable."), "warn");
      return;
    }

    if (result.exists) {
      updateFlMetaText(result.pltxt || "Tplnr found in SAP.", "ok");
    } else {
      updateFlMetaText("Tplnr not found in SAP.", "warn");
    }
  }

  async function onFunctionalLocationInput() {
    state.fl.interacted = true;
    const typed = normalizeFlTyped(dom.functionalLocation.value);
    dom.functionalLocation.value = typed;
    const fl = typed.trim();

    if (dom.bypassFunctionalLocation.checked) {
      stopFlSearchDots();
      hideFlSuggestions();
      return;
    }

    if (!shouldQuerySuggestions(fl)) {
      if (state.fl.verifyDebounceTimer) {
        window.clearTimeout(state.fl.verifyDebounceTimer);
        state.fl.verifyDebounceTimer = null;
      }
      state.fl.isSuggesting = false;
      stopFlSearchDots();
      if (state.fl.suggestAbortController) {
        state.fl.suggestAbortController.abort();
        state.fl.suggestAbortController = null;
      }
      hideFlSuggestions();
      updateFlMetaText("", "");
      return;
    }

    if (state.fl.verifyDebounceTimer) {
      window.clearTimeout(state.fl.verifyDebounceTimer);
      state.fl.verifyDebounceTimer = null;
    }
    if (!dom.bypassFunctionalLocation.checked && fl.length >= FL_MIN_LEN_OK && isValidKks(fl)) {
      const targetFl = fl;
      state.fl.verifyDebounceTimer = window.setTimeout(() => {
        state.fl.verifyDebounceTimer = null;
        queueBackgroundFlLookup(targetFl);
      }, 320);
    }

    state.fl.isSuggesting = true;
    startFlSearchDots();

    const warmSuggestions = readWarmPrefixSuggestions(fl, Date.now());
    if (warmSuggestions.length) {
      renderFlSuggestions(warmSuggestions);
      state.fl.isSuggesting = false;
      return;
    }

    if (state.fl.debounceTimer) clearTimeout(state.fl.debounceTimer);
    if (state.fl.suggestAbortController) state.fl.suggestAbortController.abort();
    const token = ++state.fl.token;
    const controller = new AbortController();
    state.fl.suggestAbortController = controller;
    const debounceMs = SUGGEST_DEBOUNCE_MS;

    state.fl.debounceTimer = setTimeout(async () => {
      try {
        const suggestions = await fetchFlSuggestions(fl, { signal: controller.signal });
        if (token !== state.fl.token) return;
        if (normalizeUpper(dom.functionalLocation.value).trim() !== fl) return;
        renderFlSuggestions(suggestions);
      } catch (error) {
        const raw = error && error.message ? error.message : String(error);
        if (isAbortLikeError(raw)) {
          return;
        }
        stopFlSearchDots();
        updateFlMetaText(`FL suggestion lookup failed: ${formatODataErrorHint(raw)}`, "warn");
        hideFlSuggestions();
      } finally {
        state.fl.isSuggesting = false;
        stopFlSearchDots();
        if (state.fl.suggestAbortController === controller) {
          state.fl.suggestAbortController = null;
        }
      }
    }, debounceMs);
  }

  function onFunctionalLocationKeyDown(event) {
    if (!dom.functionalLocationSuggestions || dom.functionalLocationSuggestions.hidden) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveFlSuggestion(1);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      moveFlSuggestion(-1);
      return;
    }

    if (event.key === "Enter" && state.fl.activeIndex >= 0) {
      event.preventDefault();
      const suggestion = state.fl.suggestions[state.fl.activeIndex];
      if (suggestion) applyFlSuggestion(suggestion);
      return;
    }

    if (event.key === "Escape") {
      hideFlSuggestions();
    }
  }

  function moveFlSuggestion(step) {
    const len = state.fl.suggestions.length;
    if (!len) return;

    let index = state.fl.activeIndex + step;
    if (index < 0) index = len - 1;
    if (index >= len) index = 0;
    state.fl.activeIndex = index;

    dom.functionalLocationSuggestions.querySelectorAll(".combo-item").forEach((node, i) => {
      node.classList.toggle("active", i === index);
    });
  }

  function renderFlSuggestions(suggestions) {
    stopFlSearchDots();
    state.fl.suggestions = suggestions;
    state.fl.activeIndex = -1;
    dom.functionalLocationSuggestions.innerHTML = "";

    if (!suggestions.length) {
      dom.functionalLocationSuggestions.hidden = true;
      updateFlMetaText("No SAP suggestions found.", "warn");
      return;
    }

    updateFlMetaText(`Found ${suggestions.length} SAP suggestion(s).`, "ok");

    suggestions.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "combo-item";
      btn.innerHTML = `<span class="combo-key">${escapeHtml(item.tplnr)}</span><span class="combo-text">${escapeHtml(item.pltxt || "")}</span>`;

      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        applyFlSuggestion(item);
      });

      dom.functionalLocationSuggestions.appendChild(btn);
    });

    dom.functionalLocationSuggestions.hidden = false;
  }

  function hideFlSuggestions() {
    state.fl.isSuggesting = false;
    stopFlSearchDots();
    dom.functionalLocationSuggestions.hidden = true;
    dom.functionalLocationSuggestions.innerHTML = "";
    state.fl.suggestions = [];
    state.fl.activeIndex = -1;
  }

  function hasVisibleFlSuggestions() {
    if (!dom.functionalLocationSuggestions) return false;
    if (dom.functionalLocationSuggestions.hidden) return false;
    return state.fl.suggestions.length > 0;
  }

  function getUnitContext(type) {
    if (type === "stock") {
      return {
        input: dom.stockUnit,
        panel: dom.stockUnitSuggestions,
        options: STOCK_UNIT_OPTIONS,
        unitMap: STOCK_UNIT_MAP,
        defaultHint: "Stock Unit: choose a unit code.",
        stateRef: state.units.stock,
      };
    }

    if (type === "strategic") {
      return {
        input: dom.strategicPart,
        panel: dom.strategicPartSuggestions,
        options: YES_NO_OPTIONS,
        unitMap: YES_NO_MAP,
        defaultHint: "Strategic part: choose YES or NO.",
        stateRef: state.units.strategic,
      };
    }

    if (type === "wear") {
      return {
        input: dom.wearPart,
        panel: dom.wearPartSuggestions,
        options: YES_NO_OPTIONS,
        unitMap: YES_NO_MAP,
        defaultHint: "Wear part: choose YES or NO.",
        stateRef: state.units.wear,
      };
    }

    return {
      input: dom.priceUnit,
      panel: dom.priceUnitSuggestions,
      options: PRICE_UNIT_OPTIONS,
      unitMap: PRICE_UNIT_MAP,
      defaultHint: "Price unit: choose a unit code.",
      stateRef: state.units.price,
    };
  }

  function filterUnitSuggestions(options, query) {
    const normalized = normalizeUpper(query);
    if (!normalized) return options.slice(0, 20);

    return options
      .filter(([code, label]) => {
        const c = normalizeUpper(code);
        const l = normalizeUpper(label);
        return c.includes(normalized) || l.includes(normalized);
      })
      .sort((a, b) => {
        const aCode = normalizeUpper(a[0]);
        const bCode = normalizeUpper(b[0]);
        const aStarts = aCode.startsWith(normalized) ? 0 : 1;
        const bStarts = bCode.startsWith(normalized) ? 0 : 1;
        if (aStarts !== bStarts) return aStarts - bStarts;
        return aCode.localeCompare(bCode);
      })
      .slice(0, 20);
  }

  function renderUnitSuggestions(type, query) {
    const context = getUnitContext(type);
    if (!context.input || !context.panel) return;

    const matches = filterUnitSuggestions(context.options, query);
    context.stateRef.suggestions = matches;
    context.stateRef.activeIndex = -1;
    context.panel.innerHTML = "";

    if (!matches.length) {
      context.panel.hidden = true;
      return;
    }

    matches.forEach(([code, label]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "combo-item";
      btn.innerHTML = `<span class="combo-key">${escapeHtml(code)}</span><span class="combo-text">${escapeHtml(label)}</span>`;
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        applyUnitSuggestion(type, code);
      });
      context.panel.appendChild(btn);
    });

    context.panel.hidden = false;
  }

  function hideUnitSuggestions(type) {
    const context = getUnitContext(type);
    if (!context.panel) return;
    context.panel.hidden = true;
    context.panel.innerHTML = "";
    context.stateRef.suggestions = [];
    context.stateRef.activeIndex = -1;
  }

  function moveUnitSuggestion(type, step) {
    const context = getUnitContext(type);
    const len = context.stateRef.suggestions.length;
    if (!len || !context.panel) return;

    let index = context.stateRef.activeIndex + step;
    if (index < 0) index = len - 1;
    if (index >= len) index = 0;
    context.stateRef.activeIndex = index;

    context.panel.querySelectorAll(".combo-item").forEach((node, i) => {
      node.classList.toggle("active", i === index);
    });
  }

  function applyUnitSuggestion(type, code) {
    const context = getUnitContext(type);
    if (!context.input) return;
    context.input.value = normalizeUpper(code);
    updateUnitFieldHint(context.input, context.unitMap, context.defaultHint);
    refreshClearButton(context.input);
    hideUnitSuggestions(type);
    previewValidation();
  }

  function onUnitKeyDown(type, event) {
    const context = getUnitContext(type);
    if (!context.panel || context.panel.hidden) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveUnitSuggestion(type, 1);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      moveUnitSuggestion(type, -1);
      return;
    }

    if (event.key === "Enter" && context.stateRef.activeIndex >= 0) {
      event.preventDefault();
      const selected = context.stateRef.suggestions[context.stateRef.activeIndex];
      if (selected) applyUnitSuggestion(type, selected[0]);
      return;
    }

    if (event.key === "Escape") {
      hideUnitSuggestions(type);
    }
  }

  async function applyFlSuggestion(item) {
    dom.functionalLocation.value = normalizeUpper(item.tplnr);
    refreshClearButton(dom.functionalLocation);
    hideFlSuggestions();

    const result = await verifyFlInOData(normalizeUpper(item.tplnr));
    if (result.ok && result.exists) {
      updateFlMetaText(result.pltxt || "Tplnr found in SAP.", "ok");
    }

    previewValidation();
  }

  async function validateRow(row, strictOData) {
    const errors = [];
    const notes = [];
    const fieldErrors = {};

    const pushErr = (text, details, fields) => {
      errors.push({ text, details: details || "" });
      (fields || []).forEach((field) => {
        if (!fieldErrors[field]) fieldErrors[field] = [];
        fieldErrors[field].push(text);
      });
    };

    const pushOk = (text) => notes.push({ text });

    REQUIRED_FIELDS.forEach((field) => {
      if (!toText(row[field])) {
        pushErr(`${FIELD_LABELS[field]} is required.`, "", [field]);
      }
    });

    if (row.manufacturer.length > 30) pushErr("Manufacturer too long.", `${row.manufacturer.length}/30`, ["manufacturer"]);
    if (row.modelNumber.length > 30) pushErr("Model Number too long.", `${row.modelNumber.length}/30`, ["modelNumber"]);
    if (row.manufacturerPartNo.length > 30) pushErr("Manufacturer Part No. too long.", `${row.manufacturerPartNo.length}/30`, ["manufacturerPartNo"]);
    if (row.materialDescription.length > 40) pushErr("Material Description too long.", `${row.materialDescription.length}/40`, ["materialDescription"]);

    if (row.deliveringTime) {
      const lead = Number(row.deliveringTime);
      if (!Number.isFinite(lead) || lead < MIN_DELIVERING_TIME) {
        pushErr(`Delivering time must be at least ${MIN_DELIVERING_TIME}.`, "", ["deliveringTime"]);
      }
    }

    const flResult = await validateFunctionalLocation(row, strictOData, pushErr, pushOk);
    validateDoc(row.documentation, pushErr, pushOk);

    if (row.stockUnit && !STOCK_UNIT_SET.has(row.stockUnit)) {
      pushErr(`Stock Unit must be one of: ${Array.from(STOCK_UNIT_SET).join(", ")}.`, "", ["stockUnit"]);
    }

    if (row.priceUnit && !PRICE_UNIT_SET.has(row.priceUnit)) {
      pushErr(`Price unit must be one of: ${Array.from(PRICE_UNIT_SET).join(", ")}.`, "", ["priceUnit"]);
    }

    const detectedPlant = flResult.plant || getPlantLabelFromFl(row.functionalLocation) || "-";

    return {
      status: errors.length ? "invalid" : "valid",
      detectedPlant,
      flDescription: flResult.pltxt || "",
      errors,
      notes,
      fieldErrors,
    };
  }

  async function validateFunctionalLocation(row, strictOData, pushErr, pushOk) {
    if (row._skipFunctionalLocation) {
      updateFlMetaText("No BOM mode enabled. FL is optional.", "warn");
      pushOk("Functional Location bypass enabled (not required for non-BOM material).");
      return { ok: true, pltxt: "" };
    }

    const fl = normalizeUpper(row.functionalLocation).trim();
    if (!strictOData && !fl) {
      updateFlMetaText("", "");
      return { ok: true, pltxt: "", className: "", plant: "" };
    }

    if (!fl) {
      updateFlMetaText("Functional Location is required.", "error");
      pushErr("Functional Location is required.", "", ["functionalLocation"]);
      return { ok: false, pltxt: "" };
    }

    const prefix = fl.slice(0, 3);
    const hardcodedPlant = getPlantLabelFromFl(fl);
    // During live preview we tolerate partial/in-progress FL input to avoid flicker.
    if (!strictOData) {
      if (!ALLOWED_PLANTS.has(prefix)) {
        updateFlMetaText("Unknown plant prefix.", "warn");
        return { ok: true, pltxt: "", className: "", plant: hardcodedPlant };
      }

      if (hasLineBreak(fl)) {
        pushErr("Functional Location invalid.", "Use one code per cell.", ["functionalLocation"]);
        updateFlMetaText("Local syntax/rules failed.", "error");
        return { ok: false, pltxt: "", className: "", plant: hardcodedPlant };
      }

      if (fl.length < FL_MIN_LEN_OK || !isValidKks(fl)) {
        if (!hasVisibleFlSuggestions()) {
          updateFlMetaText("Typing... continue for validation", "warn");
        }
        return { ok: true, pltxt: "", className: "", plant: hardcodedPlant };
      }
    }

    let hasLocalError = false;

    if (!ALLOWED_PLANTS.has(prefix)) {
      hasLocalError = true;
      pushErr("Plant not defined.", `Prefix ${prefix}. Allowed: SSV, SKV, HEV, HCV, ASV, AVV, KYV, STV, SMV`, ["functionalLocation"]);
    }

    if (hasLineBreak(fl)) {
      hasLocalError = true;
      pushErr("Functional Location invalid.", "Use one code per cell.", ["functionalLocation"]);
    }

    if (fl.length < FL_MIN_LEN_OK) {
      hasLocalError = true;
      pushErr("Functional Location not eligible for materials.", `Minimum ${FL_MIN_LEN_OK} characters required.`, ["functionalLocation"]);
    }

    if (!isValidKks(fl)) {
      hasLocalError = true;
      pushErr("Functional Location invalid.", "Invalid KKS format.", ["functionalLocation"]);
    }

    if (hasLocalError) {
      updateFlMetaText("Local syntax/rules failed.", "error");
      return { ok: false, pltxt: "", className: "", plant: "" };
    }

    if (!strictOData) {
      if (state.fl.isSuggesting) {
        if (!hasVisibleFlSuggestions()) {
          updateFlMetaText("Searching SAP suggestions...", "warn");
        }
        return { ok: true, pltxt: "", className: "", plant: hardcodedPlant };
      }

      const cache = state.fl.lookupCache.get(fl);
      if (cache) {
        if (cache.exists) updateFlMetaText(cache.pltxt || "Tplnr found in SAP.", "ok");
        else updateFlMetaText("Tplnr not found in SAP.", "warn");
        return { ok: true, pltxt: cache.exists ? cache.pltxt : "", className: cache.className || "", plant: hardcodedPlant };
      }

      updateFlMetaText("SAP lookup pending...", "warn");
      return { ok: true, pltxt: "", className: "", plant: hardcodedPlant };
    }

    const lookup = await verifyFlInOData(fl);
    if (!lookup.ok) {
      const hint = formatODataErrorHint(lookup.error || "SAP lookup failed.");
      updateFlMetaText(`SAP advisory: ${hint}`, "warn");
      pushOk(`SAP advisory: Could not verify Functional Location in SAP OData. ${hint}`);
      return { ok: true, pltxt: "", className: "", plant: hardcodedPlant };
    }

    if (!lookup.exists) {
      updateFlMetaText("SAP advisory: Tplnr not found in SAP.", "warn");
      pushOk("SAP advisory: Functional Location not found in SAP OData (Tplnr). Save is still allowed.");
      return { ok: true, pltxt: "", className: "", plant: hardcodedPlant };
    }

    updateFlMetaText(lookup.pltxt || "Tplnr found in SAP.", "ok");
    pushOk("Functional Location exists in SAP OData.");
    if (lookup.pltxt) pushOk(`Pltxt: ${lookup.pltxt}`);
    return { ok: true, pltxt: lookup.pltxt || "", className: lookup.className || "", plant: hardcodedPlant };
  }

  function validateDoc(documentation, pushErr, pushOk) {
    if (!documentation) {
      return;
    }

    const value = toText(documentation);
    const normalized = normalizeUpper(value);
    const hasFileNamePattern = /^[^\\/:*?"<>|]+\.[A-Za-z0-9]{1,10}$/.test(value);

    if (normalized === "DECA" || hasFileNamePattern) {
      pushOk("Documentation accepted.");
      return;
    }

    pushErr("Documentation must be DECA or a valid file name.", "", ["documentation"]);
  }

  async function verifyFlInOData(fl, options) {
    if (!fl) return { ok: false, exists: false, error: "Empty FL." };

    const cached = state.fl.lookupCache.get(fl);
    if (cached && Date.now() - cached.ts <= ODATA_CACHE_MS) {
      return {
        ok: true,
        exists: cached.exists,
        pltxt: cached.pltxt || "",
        className: cached.className || "",
        plant: cached.plant || "",
      };
    }

    if (state.fl.inFlight.has(fl)) {
      return state.fl.inFlight.get(fl);
    }

    const task = requestFlRecords(fl, options && options.fast ? { forSuggestions: true } : null)
      .then((records) => {
        const seededSuggestions = rankSuggestions(records, fl);
        if (seededSuggestions.length) {
          state.fl.suggestionCache.set(fl, { items: seededSuggestions, ts: Date.now() });
          trimLruMap(state.fl.suggestionCache, ODATA_MAX_CACHE_ENTRIES);

          if (
            dom.functionalLocation === document.activeElement &&
            normalizeUpper(dom.functionalLocation.value).trim() === fl &&
            !dom.bypassFunctionalLocation.checked
          ) {
            renderFlSuggestions(seededSuggestions);
          }
        }

        const exact = records.find((r) => normalizeUpper(r.tplnr) === fl) || null;
        const exists = !!exact;
        const pltxt = exact ? toText(exact.pltxt) : "";
        const className = exact ? toText(exact.className) : "";
        const plant = getPlantLabelFromFl(fl);

        state.fl.lookupCache.set(fl, {
          exists,
          pltxt,
          className,
          plant,
          ts: Date.now(),
        });

        return { ok: true, exists, pltxt, className, plant };
      })
      .catch((error) => ({
        ok: false,
        exists: false,
        className: "",
        plant: "",
        error: error && error.message ? error.message : "Network error",
      }))
      .finally(() => {
        state.fl.inFlight.delete(fl);
      });

    state.fl.inFlight.set(fl, task);
    return task;
  }

  async function fetchFlSuggestions(query, options) {
    const fl = normalizeSuggestQuery(query);
    if (!fl || fl.length < FL_SUGGEST_MIN_CHARS) return [];

    const now = Date.now();
    if (now < state.fl.suggestBackoffUntil) {
      return [];
    }

    const exactCache = state.fl.suggestionCache.get(fl);
    if (exactCache && now - exactCache.ts <= ODATA_SUGGEST_CACHE_MS) {
      touchMapKey(state.fl.suggestionCache, fl);
      return rankSuggestions(exactCache.items, fl);
    }

    const warmCached = readWarmPrefixSuggestions(fl, now);
    if (warmCached.length) {
      return warmCached;
    }

    if (state.fl.suggestionInFlight.has(fl)) {
      return state.fl.suggestionInFlight.get(fl);
    }

    const task = fetchSuggestionRecordsWithFallback(fl, options)
      .then((records) => {
        state.fl.suggestBackoffUntil = 0;
        const suggestions = rankSuggestions(records, fl);
        state.fl.suggestionCache.set(fl, { items: suggestions, ts: Date.now() });
        trimLruMap(state.fl.suggestionCache, ODATA_MAX_CACHE_ENTRIES);
        return suggestions;
      })
      .catch((error) => {
        state.fl.suggestBackoffUntil = Date.now() + ODATA_SUGGEST_FAILURE_COOLDOWN_MS;
        const raw = error && error.message ? error.message : String(error || "");
        if (/http\s*400/i.test(raw)) {
          return [];
        }
        throw error;
      })
      .finally(() => {
        state.fl.suggestionInFlight.delete(fl);
      });

    state.fl.suggestionInFlight.set(fl, task);
    return task;
  }

  async function fetchSuggestionRecordsWithFallback(fl, options) {
    const candidates = buildSuggestionFallbackCandidates(fl);
    let merged = [];
    let lastError = null;

    for (const candidate of candidates) {
      try {
        const records = await requestFlRecords(candidate, { forSuggestions: true, signal: options && options.signal });
        merged = mergeFlRecordsByTplnr(merged, records);
        if (rankSuggestions(merged, fl).length > 0) {
          return merged;
        }
      } catch (error) {
        lastError = error;
      }
    }

    if (!merged.length && lastError) {
      throw lastError;
    }

    return merged;
  }

  async function requestFlRecords(fl, options) {
    const timeoutMs = getODataTimeout(options);
    const maxPages = getODataMaxPages(options);

    if (options && options.forSuggestions) {
      if (state.net.useLocalProxy) {
        try {
          return await fetchRecordsWithPagination(
            buildProxyUrl(fl, options),
            timeoutMs,
            options && options.signal,
            { includeCredentials: false },
            maxPages
          );
        } catch (proxyError) {
          if (isAbortLikeError(proxyError && proxyError.message ? proxyError.message : "")) {
            throw proxyError;
          }
        }
      }

      try {
        return await fetchRecordsWithPagination(
          buildODataUrl(fl, true, options),
          timeoutMs,
          options && options.signal,
          null,
          maxPages
        );
      } catch (error1) {
        return await fetchRecordsWithPagination(
          buildODataUrl(fl, false, options),
          timeoutMs,
          options && options.signal,
          null,
          maxPages
        ).catch((error2) => {
          throw error2 || error1;
        });
      }
    }

    if (state.net.useLocalProxy) {
      try {
        return await fetchRecordsWithPagination(
          buildProxyUrl(fl, options),
          timeoutMs,
          options && options.signal,
          { includeCredentials: false },
          maxPages
        );
      } catch (_) {
      }
    }

    try {
      return await fetchRecordsWithPagination(
        buildODataUrl(fl, true, options),
        timeoutMs,
        options && options.signal,
        null,
        maxPages
      );
    } catch (error1) {
      try {
        return await fetchRecordsWithPagination(
          buildODataUrl(fl, false, options),
          timeoutMs,
          options && options.signal,
          null,
          maxPages
        );
      } catch (error2) {
        if (isLocalFileContext()) {
          const ok = await probeLocalProxy();
          if (ok) {
            setLocalProxyEnabled(true);
            return await fetchRecordsWithPagination(
              buildProxyUrl(fl, options),
              timeoutMs,
              options && options.signal,
              { includeCredentials: false },
              maxPages
            );
          }
        }

        throw error2 || error1;
      }
    }
  }

  function buildODataUrl(fl, useDollarFormat, options) {
    const encoded = encodeURIComponent(`'${fl}'`);
    const selectParam = `$select=${encodeURIComponent(ODATA_SELECT_FIELDS)}`;
    const formatParam = useDollarFormat ? "$format=json" : "format=json";
    const up = 1;
    const down = 1;
    return `${ODATA_BASE_URL}?Tplnr=${encoded}&Up=${up}&Down=${down}&${selectParam}&${formatParam}`;
  }

  function buildProxyUrl(fl, options) {
    const selectParam = `$select=${encodeURIComponent(ODATA_SELECT_FIELDS)}`;
    const up = 1;
    const down = 1;
    return `${state.net.localProxyBase}/odata?Tplnr=${encodeURIComponent(fl)}&Up=${up}&Down=${down}&${selectParam}&format=json`;
  }

  async function fetchWithTimeout(url, timeoutMs, externalSignal, requestOptions) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    let abortHandler = null;
    const includeCredentials = !(requestOptions && requestOptions.includeCredentials === false);

    if (externalSignal) {
      abortHandler = () => controller.abort();
      if (externalSignal.aborted) {
        controller.abort();
      } else {
        externalSignal.addEventListener("abort", abortHandler, { once: true });
      }
    }

    try {
      const response = await fetch(url, {
        method: "GET",
        headers: { Accept: "application/json" },
        mode: "cors",
        credentials: includeCredentials ? "include" : "omit",
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response;
    } finally {
      window.clearTimeout(timeoutId);
      if (externalSignal && abortHandler) {
        externalSignal.removeEventListener("abort", abortHandler);
      }
    }
  }

  async function fetchRecordsWithPagination(startUrl, timeoutMs, externalSignal, requestOptions, maxPages) {
    const cap = Math.max(1, Number(maxPages) || 1);
    const records = [];
    let nextUrl = startUrl;

    for (let page = 0; page < cap && nextUrl; page += 1) {
      const response = await fetchWithTimeout(nextUrl, timeoutMs, externalSignal, requestOptions);
      const payload = await response.json();
      records.push(...extractFlRecords(payload));
      nextUrl = getODataNextLink(payload, nextUrl);
    }

    return records;
  }

  function getODataNextLink(payload, currentUrl) {
    if (!payload || typeof payload !== "object") return "";

    let raw = "";
    if (payload.d && typeof payload.d === "object") {
      raw = payload.d.__next || payload.d.next || "";
    }

    if (!raw) {
      raw = payload["@odata.nextLink"] || payload["odata.nextLink"] || payload.nextLink || "";
    }

    const link = toText(raw);
    if (!link) return "";

    try {
      return new URL(link, currentUrl).toString();
    } catch (_) {
      return link;
    }
  }

  function getODataTimeout(options) {
    return options && options.forSuggestions ? ODATA_SUGGEST_TIMEOUT_MS : ODATA_TIMEOUT_MS;
  }

  function getODataMaxPages(options) {
    return options && options.forSuggestions ? ODATA_SUGGEST_MAX_PAGES : 1;
  }

  function normalizeSuggestQuery(value) {
    return normalizeUpper(value).replace(/\s+/g, " ").trim();
  }

  function buildSuggestionFallbackCandidates(fl) {
    const list = [];
    let current = fl;

    for (let step = 0; step <= SUGGEST_FALLBACK_MAX_STEPS; step += 1) {
      if (!current || compactKks(current).length < FL_SUGGEST_MIN_CHARS) break;
      if (!list.includes(current)) {
        list.push(current);
      }
      current = current.slice(0, -1);
    }

    return list;
  }

  function mergeFlRecordsByTplnr(existing, incoming) {
    const map = new Map();

    existing.forEach((record) => {
      const key = normalizeUpper(record && record.tplnr);
      if (!key || map.has(key)) return;
      map.set(key, record);
    });

    incoming.forEach((record) => {
      const key = normalizeUpper(record && record.tplnr);
      if (!key || map.has(key)) return;
      map.set(key, record);
    });

    return Array.from(map.values());
  }

  function shouldQuerySuggestions(value) {
    const fl = normalizeSuggestQuery(value);
    if (!fl || fl.length < FL_SUGGEST_MIN_CHARS) return false;
    return true;
  }

  function rankSuggestions(records, fl) {
    const normalized = normalizeUpper(fl);
    const compact = compactKks(normalized);
    const dedup = new Map();

    records.forEach((record) => {
      const tplnr = normalizeUpper(record && record.tplnr);
      if (!tplnr) return;
      if (!dedup.has(tplnr)) {
        dedup.set(tplnr, {
          tplnr,
          pltxt: toText(record && record.pltxt),
        });
      }
    });

    return Array.from(dedup.values())
      .filter((item) => {
        const itemCompact = compactKks(item.tplnr);
        return item.tplnr.includes(normalized) || itemCompact.includes(compact);
      })
      .sort((a, b) => {
        const aCompact = compactKks(a.tplnr);
        const bCompact = compactKks(b.tplnr);

        const aExact = a.tplnr === normalized || aCompact === compact ? 0 : 1;
        const bExact = b.tplnr === normalized || bCompact === compact ? 0 : 1;
        if (aExact !== bExact) return aExact - bExact;

        const aStarts = a.tplnr.startsWith(normalized) || aCompact.startsWith(compact) ? 0 : 1;
        const bStarts = b.tplnr.startsWith(normalized) || bCompact.startsWith(compact) ? 0 : 1;
        if (aStarts !== bStarts) return aStarts - bStarts;

        if (a.tplnr.length !== b.tplnr.length) return a.tplnr.length - b.tplnr.length;
        return a.tplnr.localeCompare(b.tplnr);
      });
  }

  function readWarmPrefixSuggestions(fl, now) {
    let best = null;

    for (const [key, value] of state.fl.suggestionCache.entries()) {
      if (!value || !Array.isArray(value.items)) continue;
      if (now - value.ts > ODATA_SUGGEST_CACHE_MS) continue;
      if (!fl.startsWith(key)) continue;
      if (!best || key.length > best.key.length) {
        best = { key, value };
      }
    }

    if (!best) return [];
    touchMapKey(state.fl.suggestionCache, best.key);
    return rankSuggestions(best.value.items, fl);
  }

  function touchMapKey(map, key) {
    if (!map.has(key)) return;
    const value = map.get(key);
    map.delete(key);
    map.set(key, value);
  }

  function trimLruMap(map, maxEntries) {
    while (map.size > maxEntries) {
      const first = map.keys().next();
      if (first.done) break;
      map.delete(first.value);
    }
  }

  function extractFlRecords(payload) {
    const records = [];

    const walk = (node) => {
      if (!node) return;

      if (Array.isArray(node)) {
        node.forEach(walk);
        return;
      }

      if (typeof node !== "object") return;

      const tplnr = getCaseInsensitive(node, ["Tplnr", "tplnr", "TPLNR"]);
      const pltxt = getCaseInsensitive(node, ["Pltxt", "pltxt", "PLTXT", "Description"]);
      const className = pickClassName(node);

      if (toText(tplnr)) {
        records.push({
          tplnr: toText(tplnr),
          pltxt: toText(pltxt),
          plant: getPlantLabelFromFl(tplnr),
          className: toText(className),
        });
      }

      Object.values(node).forEach(walk);
    };

    walk(payload);
    return records;
  }

  function getCaseInsensitive(obj, keys) {
    if (!obj || typeof obj !== "object") return "";

    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) return obj[key];
    }

    const map = new Map(Object.keys(obj).map((k) => [k.toLowerCase(), k]));
    for (const key of keys) {
      const actual = map.get(String(key).toLowerCase());
      if (actual) return obj[actual];
    }

    return "";
  }

  function pickClassName(row) {
    const candidates = [
      getCaseInsensitive(row, ["ClassName", "className", "Class", "class", "ZzClass", "zzclass"]),
      getCaseInsensitive(row, ["Atwrt", "atwrt"]),
      getCaseInsensitive(row, ["Tplkz", "tplkz"]),
      getCaseInsensitive(row, ["Aklar", "aklar", "Iklar", "iklar"]),
    ];

    for (const value of candidates) {
      const text = toText(value);
      if (!text) continue;
      if (/^kks$/i.test(text)) continue;
      if (/^\d+$/.test(text)) continue;
      return text;
    }

    return "";
  }

  function derivePlantLabel(tplnr, row) {
    const code = toText(tplnr);
    if (code.length >= 3) {
      return getPlantLabelFromFl(code);
    }

    return "";
  }

  function renderValidation(result) {
    dom.validationList.innerHTML = "";

    result.errors.forEach((issue) => {
      const item = document.createElement("div");
      item.className = "note";
      item.textContent = issue.details ? `${issue.text} ${issue.details}` : issue.text;
      dom.validationList.appendChild(item);
    });

    result.notes.forEach((note) => {
      const item = document.createElement("div");
      item.className = "note ok";
      item.textContent = note.text;
      dom.validationList.appendChild(item);
    });
  }

  function updateValidationMeta(result, row) {
    dom.detectedPlant.textContent = result.detectedPlant || "-";
    dom.detectedStatus.textContent = result.status === "valid" ? "Valid" : "Needs attention";
  }

  function applyFieldValidationState(fieldErrors) {
    FIELD_KEYS.forEach((key) => {
      const input = document.getElementById(key);
      if (!input) return;
      const hasValue = !!toText(input.value);

      input.classList.remove("field-valid", "field-invalid");
      input.removeAttribute("aria-invalid");

      if (fieldErrors[key] && fieldErrors[key].length > 0 && hasValue) {
        if (key === "deliveringTime" && !state.ui.deliveringTimeInteracted) {
          return;
        }
        input.classList.add("field-invalid");
        input.setAttribute("aria-invalid", "true");
        return;
      }

      if (key === "deliveringTime" && !state.ui.deliveringTimeInteracted) {
        return;
      }

      if (hasValue && !NO_SUCCESS_GLOW_FIELDS.has(key)) {
        input.classList.add("field-valid");
        input.setAttribute("aria-invalid", "false");
      }
    });
  }

  function renderAll() {
    renderRows();
    renderKpis();
    renderPlantFilter();
  }

  function renderRows() {
    syncMaterialTableViewUi();

    const visibleFieldKeys = state.tableView === MATERIAL_TABLE_VIEW.compact ? COMPACT_FIELD_KEYS : FIELD_KEYS.slice();
    renderMaterialTableHead(visibleFieldKeys);

    const fragment = document.createDocumentFragment();
    const filteredRows = getFilteredRows();

    filteredRows.forEach((row) => {
      const rowId = ensureRowId(row);
      const tr = document.createElement("tr");
      tr.setAttribute("data-row-id", String(rowId));

      const noBomBadge = row._skipFunctionalLocation ? '<span class="sub-badge">NO BOM</span>' : "";

      const fieldCells = visibleFieldKeys
        .map((fieldKey) => {
          const value = toText(row[fieldKey]);
          if (fieldKey === "functionalLocation") {
            return `<td>${escapeHtml(value)} ${noBomBadge}</td>`;
          }
          return `<td>${escapeHtml(value)}</td>`;
        })
        .join("");

      const detailsCell =
        state.tableView === MATERIAL_TABLE_VIEW.compact
          ? `<button class="table-btn" type="button" data-action="material-details" data-row-id="${rowId}">Details</button>`
          : "";

      tr.innerHTML = `
      <td><span class="status ${row._status}">${row._status.toUpperCase()}</span></td>
      ${fieldCells}
      ${state.tableView === MATERIAL_TABLE_VIEW.compact ? `<td>${detailsCell}</td>` : ""}
      <td>
        <button class="table-btn" type="button" data-action="edit-material-row" data-row-id="${rowId}">Edit</button>
        <button class="table-btn" type="button" data-action="copy-material-row" data-row-id="${rowId}">Copy</button>
        <button class="table-btn danger" type="button" data-action="delete-material-row" data-row-id="${rowId}">Delete</button>
      </td>
    `;

      fragment.appendChild(tr);
    });

    dom.rowsBody.replaceChildren(fragment);

    renderMaterialDetailModal();
  }

  function renderMaterialTableHead(visibleFieldKeys) {
    if (!dom.rowsTable) return;
    const head = dom.rowsTable.querySelector("thead");
    if (!head) return;

    const tableHeadKey = `${state.tableView}|${visibleFieldKeys.join(",")}`;
    if (state.ui.lastTableHeadKey === tableHeadKey) return;
    state.ui.lastTableHeadKey = tableHeadKey;

    const fieldHeaders = visibleFieldKeys.map((fieldKey) => `<th>${escapeHtml(FIELD_LABELS[fieldKey])}</th>`).join("");
    const detailsHeader = state.tableView === MATERIAL_TABLE_VIEW.compact ? "<th>Details</th>" : "";

    head.innerHTML = `
      <tr>
        <th>Status</th>
        ${fieldHeaders}
        ${detailsHeader}
        <th>Actions</th>
      </tr>
    `;
  }

  function syncMaterialTableViewUi() {
    const compactPressed = state.tableView === MATERIAL_TABLE_VIEW.compact;
    if (dom.btnMaterialViewCompact) {
      dom.btnMaterialViewCompact.setAttribute("aria-pressed", compactPressed ? "true" : "false");
    }
    if (dom.btnMaterialViewAll) {
      dom.btnMaterialViewAll.setAttribute("aria-pressed", compactPressed ? "false" : "true");
    }
    if (dom.tableWrap) {
      dom.tableWrap.classList.toggle("all-columns", state.tableView === MATERIAL_TABLE_VIEW.all);
    }
    if (dom.rowsTable) {
      dom.rowsTable.classList.toggle("spareparts-table-all", state.tableView === MATERIAL_TABLE_VIEW.all);
    }
  }

  function onRowsBodyClick(event) {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;

    const actionTarget = rawTarget.closest("[data-action]");
    if (!actionTarget || !dom.rowsBody.contains(actionTarget)) return;

    const action = actionTarget.getAttribute("data-action");
    const rowId = readRowIdFromActionTarget(actionTarget);
    if (!rowId) return;

    if (action === "material-details") {
      state.detailRowId = rowId;
      renderMaterialDetailModal();
      return;
    }

    const rowIndex = getRowIndexById(rowId);
    if (rowIndex < 0) return;

    if (action === "edit-material-row") {
      const row = state.rows[rowIndex];
      if (!row) return;
      state.editIndex = rowIndex;
      state.editRowId = rowId;
      setForm(row);
      previewValidation();
      setRuntime(`Editing row ${rowIndex + 1}.`);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    if (action === "copy-material-row") {
      const row = state.rows[rowIndex];
      if (!row) return;
      const cloned = {
        ...row,
        _rowId: state.nextRowId++,
        _issues: Array.isArray(row._issues) ? row._issues.slice() : [],
        _updatedAt: new Date().toISOString(),
      };
      cloned._searchBlob = buildRowSearchBlob(cloned);

      state.rows.splice(rowIndex + 1, 0, cloned);
      if (state.editIndex !== null && state.editIndex > rowIndex) {
        state.editIndex += 1;
      }

      renderAll();
      setRuntime(`Row ${rowIndex + 1} copied as a new row.`);
      return;
    }

    if (action === "delete-material-row") {
      state.rows.splice(rowIndex, 1);
      if (state.detailRowId === rowId) {
        state.detailRowId = null;
      }
      if (state.editRowId === rowId) {
        state.editRowId = null;
        state.editIndex = null;
      } else if (state.editIndex !== null && state.editIndex > rowIndex) {
        state.editIndex -= 1;
      }
      renderAll();
      setRuntime("Row deleted.");
      return;
    }
  }

  function onMaterialDetailsClick(event) {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;

    const closeBtn = rawTarget.closest("[data-action='close-material-details']");
    if (!closeBtn || !dom.materialDetailsHost.contains(closeBtn)) return;
    state.detailRowId = null;
    renderMaterialDetailModal();
  }

  function readRowIdFromActionTarget(actionTarget) {
    const direct = Number(actionTarget.getAttribute("data-row-id"));
    if (Number.isInteger(direct) && direct > 0) {
      return direct;
    }

    const rowNode = actionTarget.closest("tr[data-row-id]");
    if (!rowNode) return 0;

    const fromRow = Number(rowNode.getAttribute("data-row-id"));
    return Number.isInteger(fromRow) && fromRow > 0 ? fromRow : 0;
  }

  function getRowIndexById(rowId) {
    if (!Number.isInteger(rowId) || rowId <= 0) return -1;

    for (let index = 0; index < state.rows.length; index += 1) {
      if (ensureRowId(state.rows[index]) === rowId) {
        return index;
      }
    }

    return -1;
  }

  function getRowById(rowId) {
    const index = getRowIndexById(rowId);
    return index >= 0 ? state.rows[index] : null;
  }

  function renderMaterialDetailModal() {
    if (!dom.materialDetailsHost) return;

    const activeRowId = Number(state.detailRowId);
    if (!Number.isInteger(activeRowId) || activeRowId <= 0) {
      dom.materialDetailsHost.innerHTML = "";
      return;
    }

    const row = getRowById(activeRowId);
    if (!row) {
      state.detailRowId = null;
      dom.materialDetailsHost.innerHTML = "";
      return;
    }

    const entries = FIELD_KEYS.filter((key) => !COMPACT_FIELD_KEYS.includes(key)).map((key) => {
      return {
        label: FIELD_LABELS[key],
        value: toText(row[key]),
      };
    });

    dom.materialDetailsHost.innerHTML = `
      <div class="class-detail-backdrop">
        <div class="class-detail-modal" role="dialog" aria-modal="true" aria-label="Material row details">
          <div class="class-detail-head">
            <div>
              <h3>Row details</h3>
              <p class="small-muted">Functional Location: ${escapeHtml(toText(row.functionalLocation) || "-")}</p>
            </div>
            <div class="class-detail-actions">
              <button type="button" class="action-btn primary" data-action="close-material-details">Close</button>
            </div>
          </div>
          <div class="class-detail-grid-wrap">
            <table class="class-detail-table">
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                ${entries
                  .map(
                    (entry) => `
                  <tr>
                    <td>${escapeHtml(entry.label)}</td>
                    <td>${escapeHtml(entry.value)}</td>
                  </tr>
                `
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  function getFilteredRows() {
    return state.rows.filter((row) => {
      if (state.filters.status !== "all" && row._status !== state.filters.status) return false;
      if (state.filters.plant !== "all" && row._plant !== state.filters.plant) return false;

      const query = state.filters.search;
      if (!query) return true;

      const hay = row._searchBlob || buildRowSearchBlob(row);
      if (!row._searchBlob) {
        row._searchBlob = hay;
      }

      return hay.includes(query);
    });
  }

  function renderKpis() {
    const total = state.rows.length;
    const valid = state.rows.filter((row) => row._status === "valid").length;

    dom.kpiRows.textContent = String(total);
    dom.kpiValid.textContent = String(valid);
    dom.kpiInvalid.textContent = String(total - valid);
  }

  function renderPlantFilter() {
    const current = dom.plantFilter.value;
    const plants = Array.from(new Set(state.rows.map((row) => row._plant).filter(Boolean))).sort();

    dom.plantFilter.innerHTML = '<option value="all">All plants</option>';
    plants.forEach((plant) => {
      const option = document.createElement("option");
      option.value = plant;
      option.textContent = plant;
      dom.plantFilter.appendChild(option);
    });

    dom.plantFilter.value = plants.includes(current) ? current : "all";
    state.filters.plant = dom.plantFilter.value;
    syncStyledSelect(dom.plantFilter);
  }

  // Native selects render an OS list that cannot be themed; these two filters
  // are the last ones in the product, so they use the shared select widget.
  function setupStyledSelects() {
    [dom.statusFilter, dom.plantFilter].filter(Boolean).forEach(enhanceSelect);

    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Node)) return;

      state.styledSelects.forEach((entry) => {
        if (!entry.wrapper.contains(event.target)) closeStyledSelect(entry);
      });
    });
  }

  function enhanceSelect(select) {
    const parent = select.parentElement;
    if (!parent) return;

    const wrapper = document.createElement("div");
    wrapper.className = "eq-select-wrap";

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "eq-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");

    const panel = document.createElement("div");
    panel.className = "combo-panel eq-select-panel";
    panel.hidden = true;

    parent.insertBefore(wrapper, select);
    wrapper.appendChild(select);
    wrapper.appendChild(trigger);
    wrapper.appendChild(panel);
    select.classList.add("eq-select-native");

    const entry = { select, wrapper, trigger, panel };
    state.styledSelects.push(entry);

    trigger.addEventListener("click", () => {
      if (select.disabled) return;

      const willOpen = panel.hidden;
      state.styledSelects.forEach((other) => {
        if (other !== entry) closeStyledSelect(other);
      });

      if (!willOpen) {
        closeStyledSelect(entry);
        return;
      }

      renderStyledSelectOptions(entry);
      panel.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      wrapper.classList.add("open");
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeStyledSelect(entry);
    });

    select.addEventListener("change", () => syncStyledSelect(select));
    syncStyledSelect(select);
  }

  function renderStyledSelectOptions(entry) {
    entry.panel.innerHTML = "";

    Array.from(entry.select.options || []).forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "combo-item eq-select-option";
      button.textContent = option.textContent || option.value || "";

      if (option.value === entry.select.value) button.classList.add("active");

      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        entry.select.value = option.value;
        entry.select.dispatchEvent(new Event("input", { bubbles: true }));
        entry.select.dispatchEvent(new Event("change", { bubbles: true }));
        closeStyledSelect(entry);
      });

      entry.panel.appendChild(button);
    });
  }

  function closeStyledSelect(entry) {
    entry.panel.hidden = true;
    entry.trigger.setAttribute("aria-expanded", "false");
    entry.wrapper.classList.remove("open");
  }

  function syncStyledSelect(select) {
    const entry = state.styledSelects.find((item) => item.select === select);
    if (!entry) return;

    const selected = select.options[select.selectedIndex];
    entry.trigger.textContent = (selected && selected.textContent) || "Select";
    entry.trigger.disabled = !!select.disabled;
    entry.wrapper.classList.toggle("is-disabled", !!select.disabled);
  }

  const CSV_FORMULA_LEAD = /^[=+@\t\r]/;
  const CSV_PLAIN_NUMBER = /^-?\d+(?:[.,]\d+)?$/;

  function toCsvCell(value) {
    let text = String(value == null ? "" : value);
    // Neutralise spreadsheet formula injection, but keep genuine negative numbers numeric.
    if (CSV_FORMULA_LEAD.test(text) || (text.startsWith("-") && !CSV_PLAIN_NUMBER.test(text))) {
      text = `'${text}`;
    }
    return `"${text.replaceAll("\"", "\"\"")}"`;
  }

  function exportCsv() {
    const rows = getFilteredRows();
    if (!rows.length) {
      setRuntime("No rows to export.");
      return;
    }

    const headers = ["Status", ...FIELD_KEYS.map((k) => FIELD_LABELS[k]), "FL Description", "No BOM", "Issues"];
    const csvRows = [headers];

    rows.forEach((row) => {
      csvRows.push([
        row._status,
        ...FIELD_KEYS.map((k) => row[k] || ""),
        row._flDescription || "",
        row._skipFunctionalLocation ? "YES" : "NO",
        (row._issues || []).join(" | "),
      ]);
    });

    const csv = csvRows
      .map((line) => line.map(toCsvCell).join(","))
      .join("\r\n");

    // Leading BOM so Excel opens the file as UTF-8 instead of the local ANSI codepage.
    const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `spare_parts_export_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    setRuntime(`Exported ${rows.length} rows.`);
  }

  function sendRowsAsEmail() {
    if (state.ui.saveInProgress) {
      setRuntime("Gemning er i gang. Vent et øjeblik og prøv igen.");
      return;
    }

    const snapshot = buildMaterialMailSnapshot();
    const hasDraftValues = FIELD_KEYS.some((key) => !!toText(snapshot.draft[key])) || !!snapshot.draft._skipFunctionalLocation;

    if (!window.MailtoUtils || typeof window.MailtoUtils.finalizeMailtoHref !== "function") {
      setRuntime("Mailfunktion er ikke tilgængelig.");
      return;
    }

    if (!snapshot.rows.length && !hasDraftValues) {
      setRuntime("Ingen data at sende.");
      return;
    }

    const subject = buildMaterialEmailSubject(snapshot);
    const detailedBody = buildMaterialEmailBody(snapshot, false);
    const summaryBody = buildMaterialEmailBody(snapshot, true);
    const resolved = window.MailtoUtils.finalizeMailtoHref({
      recipient: MAILTO_RECIPIENT,
      subject,
      detailedBody,
      summaryBody,
      maxUrlLength: MAILTO_MAX_URL_LENGTH,
      truncationNote: "[afkortet pga. mail-længde]",
    });

    if (!resolved.ok) {
      setRuntime("Mailindholdet er for stort. Brug Export CSV.");
      return;
    }

    window.location.href = resolved.href;

    const qualityLine = `Kontrol: ${snapshot.statusCounts.invalid} ugyldige, ${snapshot.statusCounts.warning} med advarsel.`;

    if (resolved.mode === "full") {
      setRuntime(`Åbner mailkladde i mailklient (intet sendes automatisk). Fuldt materialeindhold. ${qualityLine}`);
      return;
    }

    if (resolved.mode === "summary") {
      setRuntime(`Åbner mailkladde i mailklient (intet sendes automatisk). Oversigt. ${qualityLine}`);
      return;
    }

    setRuntime(`Åbner mailkladde i mailklient (intet sendes automatisk). Afkortet oversigt. ${qualityLine}`);
  }

  function buildMaterialMailSnapshot() {
    const rows = state.rows.slice();
    const draft = normalizeRow(readForm());
    return {
      generatedAt: new Date(),
      rows,
      draft,
      modeLabel: getMaterialModeLabel(),
      plantLabel: inferMaterialSubjectPlant(rows, draft),
      statusCounts: countMaterialStatuses(rows),
      activeFilters: {
        search: state.filters.search,
        status: state.filters.status,
        plant: state.filters.plant,
      },
    };
  }

  function countMaterialStatuses(rows) {
    const counts = {
      valid: 0,
      warning: 0,
      invalid: 0,
      draft: 0,
    };

    rows.forEach((row) => {
      const status = toText(row._status).toLowerCase();
      if (status === "valid") {
        counts.valid += 1;
        return;
      }
      if (status === "warning") {
        counts.warning += 1;
        return;
      }
      if (status === "invalid") {
        counts.invalid += 1;
        return;
      }
      counts.draft += 1;
    });

    return counts;
  }

  function buildMaterialEmailSubject(snapshot) {
    const dateStamp = new Date().toISOString().slice(0, 10);
    const rowCount = snapshot.rows.length;
    const rowLabel = rowCount === 1 ? "række" : "rækker";
    return `SAP Vedligehold | Materialer ${snapshot.modeLabel} | ${snapshot.plantLabel} | ${rowCount} ${rowLabel} | Fejl ${snapshot.statusCounts.invalid} | ${dateStamp}`;
  }

  function inferMaterialSubjectPlant(rows, draft) {
    const draftPlant = normalizeMaterialPlantLabel(getPlantLabelFromFl(draft && draft.functionalLocation));
    if (draftPlant) return draftPlant;

    for (let index = 0; index < rows.length; index += 1) {
      const row = rows[index];
      const rowPlant = normalizeMaterialPlantLabel(toText(row._plant))
        || normalizeMaterialPlantLabel(getPlantLabelFromFl(row.functionalLocation));
      if (rowPlant) return rowPlant;
    }

    const filterPlant = normalizeMaterialPlantLabel(toText(state.filters.plant));
    if (filterPlant && filterPlant.toLowerCase() !== "all") return filterPlant;

    return "Uden anlæg";
  }

  function normalizeMaterialPlantLabel(value) {
    const text = toText(value);
    if (!text) return "";
    if (text === "-" || text.toLowerCase() === "n/a") return "";
    return text;
  }

  function buildMaterialEmailBody(snapshot, compact) {
    const lines = [];
    const rows = snapshot.rows;
    const draft = snapshot.draft;
    const generatedAt = snapshot.generatedAt.toLocaleString();
    const rowLimit = compact ? Math.min(rows.length, 8) : rows.length;
    const statusFilterLabel = toText(snapshot.activeFilters.status).toLowerCase() === "all"
      ? "Alle"
      : toText(snapshot.activeFilters.status) || "Alle";
    const plantFilterLabel = toText(snapshot.activeFilters.plant).toLowerCase() === "all"
      ? "Alle"
      : toText(snapshot.activeFilters.plant) || "Alle";

    lines.push(`MATERIALER - ${snapshot.modeLabel.toUpperCase()} MAILUDKAST`);
    lines.push(`Modtager: ${MAILTO_RECIPIENT}`);
    lines.push(`Genereret: ${generatedAt}`);
    lines.push("========================================");
    lines.push("01) OVERSIGT");
    lines.push(`- Gemte rækker: ${rows.length}`);
    lines.push(`- Gyldige: ${snapshot.statusCounts.valid}`);
    lines.push(`- Gyldige med advarsel: ${snapshot.statusCounts.warning}`);
    lines.push(`- Ugyldige: ${snapshot.statusCounts.invalid}`);
    lines.push(`- Kladder: ${snapshot.statusCounts.draft}`);
    lines.push(`- Aktivt statusfilter (UI): ${statusFilterLabel}`);
    lines.push(`- Aktivt plantefilter (UI): ${plantFilterLabel}`);
    lines.push(`- Aktiv søgetekst (UI): ${toText(snapshot.activeFilters.search) || "-"}`);
    lines.push("- Mailen inkluderer alle gemte rækker uanset aktive filtre.");
    lines.push("- Datagrundlag: Normaliserede/finale værdier fra appen.");
    lines.push("");
    lines.push("02) AKTUELT FORMULARUDKAST");

    FIELD_KEYS.forEach((key) => {
      const value = toText(draft[key]);
      if (compact && !value) return;
      lines.push(formatFieldLine(getEmailFieldLabel(key), value || "-"));
    });

    lines.push(formatFieldLine("Ikke-BOM post", toJaNej(draft._skipFunctionalLocation)));

    lines.push("");
    lines.push(compact ? "03) GEMTE RÆKKER (KOMPRIMERET)" : "03) GEMTE RÆKKER (DETALJER)");

    if (!rows.length) {
      lines.push("- Ingen gemte rækker.");
      return lines.join("\n");
    }

    for (let index = 0; index < rowLimit; index += 1) {
      const row = rows[index];
      lines.push("");
      lines.push(`Række ${index + 1} | Status: ${mapMaterialStatusToDanish(row._status)}`);
      lines.push("----------------------------------------");

      if (compact) {
        lines.push(formatFieldLine("Funktionslokation", toText(row.functionalLocation) || "-"));
        lines.push(formatFieldLine("Materialebeskrivelse", toText(row.materialDescription) || "-"));
        lines.push(formatFieldLine("Producent varenummer", toText(row.manufacturerPartNo) || "-"));
        lines.push(formatFieldLine("Leverandør", toText(row.supplier) || "-"));
        lines.push(formatFieldLine("Leverandør varenummer", toText(row.supplierPartNo) || "-"));
      } else {
        lines.push(formatFieldLine("Status", mapMaterialStatusToDanish(row._status)));
        FIELD_KEYS.forEach((key) => {
          lines.push(formatFieldLine(getEmailFieldLabel(key), clipText(row[key], 220) || "-"));
        });
        lines.push(formatFieldLine("FL-beskrivelse", clipText(row._flDescription, 220) || "-"));
        lines.push(formatFieldLine("Anlæg", toText(row._plant) || "-"));
        lines.push(formatFieldLine("Ikke-BOM post", toJaNej(row._skipFunctionalLocation)));
        if (row._issues && row._issues.length) {
          lines.push(formatFieldLine("Valideringsfejl", clipText(row._issues.join(" | "), 320)));
        } else {
          lines.push(formatFieldLine("Valideringsfejl", "-"));
        }
      }
    }

    if (rows.length > rowLimit) {
      lines.push("");
      lines.push(`... ${rows.length - rowLimit} flere rækker er ikke medtaget.`);
    }

    if (compact) {
      lines.push("");
      lines.push("Brug Export CSV i appen for komplet datasat.");
    }

    return lines.join("\n");
  }

  function getMaterialModeLabel() {
    const mode = toText(document.body.getAttribute("data-materialer-mode")).toLowerCase();
    return mode === "drift" ? "Drift" : "Projekt";
  }

  function getEmailFieldLabel(key) {
    return EMAIL_FIELD_LABELS_DA[key] || FIELD_LABELS[key] || key;
  }

  function mapMaterialStatusToDanish(status) {
    const normalized = toText(status).toLowerCase();
    if (normalized === "valid") return "Gyldig";
    if (normalized === "invalid") return "Ugyldig";
    if (normalized === "warning") return "Gyldig med advarsel";
    if (normalized === "draft") return "Kladde";
    return toText(status).toUpperCase() || "-";
  }

  function toJaNej(value) {
    return value ? "JA" : "NEJ";
  }

  function formatFieldLine(label, value) {
    const left = toText(label) || "-";
    const right = toText(value) || "-";
    return `${left.padEnd(30, " ")}: ${right}`;
  }

  function isValidKks(functionalLocation) {
    const fl = normalizeUpper(functionalLocation);
    if (!fl) return true;
    return FL_PATTERNS.some((pattern) => pattern.test(fl));
  }

  function normalizeYesNoStrict(value) {
    const upper = normalizeUpper(value);
    return upper === "YES" ? "YES" : "NO";
  }

  function compactKks(value) {
    return normalizeUpper(value).replace(/\s+/g, "");
  }

  function normalizeUnitValue(value) {
    const text = normalizeUpper(value);
    if (!text) return "";
    const split = text.indexOf(" - ");
    return split > -1 ? text.slice(0, split) : text;
  }

  function normalizeDeliveringTime(value) {
    const text = toText(value);
    if (!text) return "";
    const n = Number(text.replace(",", "."));
    if (!Number.isFinite(n)) return text;
    return String(Math.max(MIN_DELIVERING_TIME, Math.round(n)));
  }

  function getPlantLabelFromFl(functionalLocation) {
    const normalized = normalizeUpper(functionalLocation);
    if (normalized.length < 3) return "";
    const code = normalized.slice(0, 3);
    return PLANT_NAME_BY_PREFIX[code] || code;
  }

  function hasLineBreak(value) {
    return /[\r\n]/.test(value || "");
  }

  function normalizeFlTyped(value) {
    return String(value == null ? "" : value).toUpperCase();
  }

  function formatODataErrorHint(message) {
    const text = String(message || "").trim();
    const lower = text.toLowerCase();
    if (lower.includes("failed to fetch") || lower.includes("networkerror") || lower.includes("err_aborted")) {
      return `${text} (local Edge file:// may block CORS/auth to SAP)`;
    }
    if (lower.includes("401")) {
      return `${text} (missing SAP login/session in browser)`;
    }
    if (state.net.useLocalProxy) {
      return `${text} (via local proxy)`;
    }
    return text;
  }

  function isAbortLikeError(message) {
    const text = String(message || "").toLowerCase();
    return text.includes("aborted") || text.includes("aborterror") || text.includes("signal is aborted");
  }

  function isLocalFileContext() {
    return window.location && window.location.protocol === "file:";
  }

  function initializeLocalProxyUi() {
    const shouldEnable = false;
    setLocalProxyEnabled(shouldEnable, true);

    if (isLocalFileContext()) {
      setRuntime("Proxy available via local script.");
    }
  }

  function setLocalProxyEnabled(enabled, silent) {
    state.net.useLocalProxy = !!enabled;
    if (dom.btnLocalProxy) {
      dom.btnLocalProxy.textContent = state.net.useLocalProxy ? "Local proxy: ON" : "Local proxy: OFF";
      dom.btnLocalProxy.setAttribute("aria-pressed", state.net.useLocalProxy ? "true" : "false");
    }
    if (!silent) {
      previewValidation();
    }
  }

  async function probeLocalProxy() {
    const base = state.net.localProxyBase;

    try {
      const response = await fetchWithTimeout(`${base}/health`, 1500);
      if (response.ok) return true;
    } catch (_) {
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 1500);

    try {
      const response = await fetch(`${base}/odata`, {
        method: "GET",
        mode: "cors",
        signal: controller.signal,
      });

      return response.status >= 200 && response.status < 500;
    } catch (_) {
      return false;
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  function syncFlBypassUI() {
    const bypass = !!dom.bypassFunctionalLocation.checked;
    dom.functionalLocation.required = !bypass;
    dom.functionalLocation.placeholder = bypass ? "Optional for non-BOM material" : "";
    dom.functionalLocation.classList.toggle("field-bypass", bypass);

    if (window.RequiredFields) {
      window.RequiredFields.set(dom.functionalLocation, !bypass);
    }

    if (bypass) {
      updateFlMetaText("No-BOM mode: FL optional.", "warn");
      hideFlSuggestions();
    }

    dom.btnToggleNoBom.textContent = bypass ? "No BOM Item: ON" : "No BOM Item: OFF";
    dom.btnToggleNoBom.setAttribute("aria-pressed", bypass ? "true" : "false");
  }

  function resetForm(clearValidation) {
    dom.form.reset();
    state.editIndex = null;
    state.editRowId = null;

    const strategicPart = document.getElementById("strategicPart");
    if (strategicPart) strategicPart.value = "NO";

    const wearPart = document.getElementById("wearPart");
    if (wearPart) wearPart.value = "NO";

    const deliveringTime = document.getElementById("deliveringTime");
    if (deliveringTime) deliveringTime.value = DEFAULT_DELIVERING_TIME;

    dom.bypassFunctionalLocation.checked = false;
    state.fl.interacted = false;
    if (state.fl.verifyDebounceTimer) {
      window.clearTimeout(state.fl.verifyDebounceTimer);
      state.fl.verifyDebounceTimer = null;
    }
    state.ui.deliveringTimeInteracted = false;

    updateFlMetaText("", "");
    hideFlSuggestions();
    hideUnitSuggestions("stock");
    hideUnitSuggestions("price");
    hideUnitSuggestions("strategic");
    hideUnitSuggestions("wear");
    syncFlBypassUI();
    applyFieldValidationState({});

    FIELD_KEYS.forEach((key) => {
      const input = document.getElementById(key);
      if (input) refreshClearButton(input);
    });
    initializeUnitHints();

    if (clearValidation) {
      dom.validationList.innerHTML = "";
      dom.detectedPlant.textContent = "-";
      dom.detectedStatus.textContent = "Not validated";
    }
  }

  function updateFlMetaText(text, mode) {
    if (!dom.functionalLocationDesc) return;
    dom.functionalLocationDesc.classList.remove("ok", "warn", "error");
    dom.functionalLocationDesc.textContent = toText(text);
    if (mode) dom.functionalLocationDesc.classList.add(mode);
  }

  function startFlSearchDots() {
    if (!dom.functionalLocationDesc) return;
    stopFlSearchDots();
    state.fl.searchDotsCount = 1;
    updateFlMetaText("Searching SAP suggestions.", "warn");
    state.fl.searchDotsTimer = window.setInterval(() => {
      state.fl.searchDotsCount = state.fl.searchDotsCount >= 3 ? 1 : state.fl.searchDotsCount + 1;
      updateFlMetaText(`Searching SAP suggestions${".".repeat(state.fl.searchDotsCount)}`, "warn");
    }, SEARCH_DOTS_INTERVAL_MS);
  }

  function stopFlSearchDots() {
    if (!state.fl.searchDotsTimer) return;
    window.clearInterval(state.fl.searchDotsTimer);
    state.fl.searchDotsTimer = null;
  }

  function setRuntime(message) {
    dom.runtimeInfo.textContent = message;
  }
})();

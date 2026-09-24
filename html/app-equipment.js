(function () {
  const { toText, normalizeUpper, clipText, escapeHtml } = window.TextUtils;

  const FIELD_KEYS = [
    "requestType",
    "plant",
    "equipmentNumber",
    "description",
    "equipmentCategory",
    "manufacturer",
    "typeDesignation",
    "serialNumber",
    "functionalLocation",
    "functionalLocation1",
    "functionalLocation2",
    "classData",
    "roomCoordinates",
    "placement",
    "warrantyStart",
    "warrantyEnd",
    "documentType",
    "documentLink",
  ];

  const FIELD_LABELS = {
    requestType: "Status",
    plant: "Plant",
    equipmentNumber: "Equipmentnummer",
    description: "Beskrivelse",
    equipmentCategory: "Equipment type",
    manufacturer: "Fabrikat",
    typeDesignation: "Type betegnelse",
    serialNumber: "Serienummer",
    functionalLocation: "Func. location",
    functionalLocation1: "Func. loc. 1",
    functionalLocation2: "Functional location 2",
    classData: "Klasse data",
    roomCoordinates: "ROOM (koordinater)",
    placement: "Placering",
    warrantyStart: "Garanti start",
    warrantyEnd: "Garanti slut",
    documentType: "Dokument type",
    documentLink: "Dokument link",
  };

  const EMAIL_FIELD_LABELS_DA = {
    requestType: "Status",
    plant: "Anlaeg",
    equipmentNumber: "Equipmentnummer",
    description: "Beskrivelse",
    equipmentCategory: "Equipment type",
    manufacturer: "Fabrikat",
    typeDesignation: "Typebetegnelse",
    serialNumber: "Serienummer",
    functionalLocation: "Funktionslokation",
    functionalLocation1: "Funktionslokation 1",
    functionalLocation2: "Funktionslokation 2",
    classData: "Klasse data",
    roomCoordinates: "ROOM (koordinater)",
    placement: "Placering",
    warrantyStart: "Garanti start",
    warrantyEnd: "Garanti slut",
    documentType: "Dokument type",
    documentLink: "Dokument link",
  };

  const REQUIRED_FIELDS_FOR_NEW = new Set([
    "requestType",
    "plant",
    "description",
    "equipmentCategory",
    "manufacturer",
    "typeDesignation",
    "functionalLocation",
  ]);

  const REQUIRED_FIELDS_FOR_CHANGE_DELETE = new Set([
    "requestType",
    "plant",
  ]);

  const REQUEST_TYPES = Object.freeze({
    NEW: "new",
    CHANGE: "change",
    DELETE: "delete",
  });

  const REQUEST_TYPE_LABELS = Object.freeze({
    [REQUEST_TYPES.NEW]: "Ny",
    [REQUEST_TYPES.CHANGE]: "Ændre",
    [REQUEST_TYPES.DELETE]: "Slettes",
  });

  const NON_CONTENT_FIELD_KEYS = new Set([
    "requestType",
  ]);

  const MAX_LENGTH_BY_FIELD = {
    requestType: 12,
    plant: 30,
    equipmentNumber: 30,
    description: 40,
    equipmentCategory: 60,
    manufacturer: 30,
    typeDesignation: 30,
    serialNumber: 30,
    functionalLocation: 30,
    functionalLocation1: 30,
    functionalLocation2: 30,
    classData: 40,
    roomCoordinates: 8,
    placement: 30,
    warrantyStart: 10,
    warrantyEnd: 10,
    documentType: 30,
    documentLink: 255,
  };

  const UPPERCASE_FIELDS = new Set([
    "plant",
    "equipmentNumber",
    "functionalLocation",
    "functionalLocation1",
    "functionalLocation2",
  ]);

  const DATE_FIELD_KEYS = new Set([
    "warrantyStart",
    "warrantyEnd",
  ]);

  const FIELD_NOTES = Object.freeze({
    equipmentNumber:
      "Ved ny oprettelse skal feltet være tomt.\n\nHvis equipmentet skal ændres eller slettes, skal equipmentnummeret indsættes i cellen.",
    functionalLocation:
      "Denne kolonne anvendes hvis equipmentet ikke skal oprettes i Z-strukturen. Ellers brug kolonne J+K.",
    functionalLocation1:
      "Hvilket værk og blok skal equipmentet tilknyttes?",
    functionalLocation2:
      "Hvilken functional location skal equipmentet være tilknyttet? Den påsatte functional location vil samtidig være omkostningsbæreren.",
    classData:
      "Hvilken klasse hører equipmentet til?\n\nVælg den korrekte klasse, så de rigtige informationer bliver tilknyttet equipmentet.",
    roomCoordinates: "Se evt. en oversigt over bygningskoordinater.",
    placement: "Hvor er equipmentet placeret?",
  });

  const EQUIPMENT_CODE_PATTERN = /^[A-Z0-9._/\-]*$/;
  const DATE_PATTERN_LOCAL = /^\d{2}\/\d{2}\/\d{4}$/;
  const DATE_PATTERN_DOTTED_LEGACY = /^\d{2}\.\d{2}\.\d{4}$/;
  const DATE_PATTERN_ISO = /^\d{4}-\d{2}-\d{2}$/;

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

  const FALLBACK_PLANT_SET = new Set(["SSV", "SKV", "HEV", "HCV", "ASV", "AVV", "KYV", "SMV", "STV"]);
  const PLANT_NAME_BY_PREFIX = {
    SKV: "Skaerbaekvaerket",
    SSV: "Studstrupvaerket",
    ASV: "Asnaesvaerket",
    AVV: "Avedoerevaerket",
    HCV: "H.C. Oersted Vaerket",
    KYV: "Kyndbyvaerket",
    HEV: "Herningvaerket",
    STV: "STV",
    SMV: "SMV",
  };

  const TABLE_VIEW = Object.freeze({
    compact: "compact",
    all: "all",
  });

  const COMPACT_FIELD_KEYS = [
    "requestType",
    "plant",
    "functionalLocation",
    "equipmentNumber",
    "description",
    "equipmentCategory",
  ];

  const MAILTO_MAX_URL_LENGTH = 1850;
  const MAILTO_RECIPIENT = "sapvedligehold@orsted.com";

  const FL_MIN_LEN_OK = 16;
  const FL_SUGGEST_MIN_CHARS = 7;
  const SUGGEST_DEBOUNCE_MS = 140;
  const SEARCH_INPUT_DEBOUNCE_MS = 120;

  const state = {
    rows: [],
    nextRowId: 1,
    editIndex: null,
    editRowId: null,
    detailRowId: null,
    previewToken: 0,
    tableView: TABLE_VIEW.compact,
    filters: {
      search: "",
      status: "all",
      plant: "all",
    },
    options: {
      plants: [],
      plantSet: new Set(),
      categoryValues: [],
      categorySet: new Set(),
      documentTypes: [],
      documentTypeSet: new Set(),
    },
    net: {
      useLocalProxy: false,
    },
    ui: {
      saveInProgress: false,
      searchDebounceTimer: null,
      lastTableHeadKey: "",
    },
    fl: {
      interacted: false,
      lookupCache: new Map(),
      suggestions: [],
      activeIndex: -1,
      debounceTimer: null,
      token: 0,
      isSuggesting: false,
      searchDotsTimer: null,
      searchDotsCount: 0,
    },
    styledSelects: [],
    fieldNoteKey: "",
  };

  const dom = {
    fields: {},
  };

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    applyEmbeddedModeFromQuery();
    bindDom();
    hydrateLookupOptions();
    renderStaticSelects();
    initializeStyledSelects();
    initializeLocalProxyUi();
    setupFieldNotes();
    setupClearButtons();
    setupDatePickerUi();
    bindEvents();
    resetForm(true);
    renderAll();
    setRuntime("Ready.");
  }

  function applyEmbeddedModeFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const embedRaw = toText(params.get("embed")).toLowerCase();
    const embedded = embedRaw === "1" || embedRaw === "true" || embedRaw === "yes";

    if (!embedded) return;

    document.documentElement.setAttribute("data-embedded", "true");
    document.body.setAttribute("data-embedded", "true");
  }

  function bindDom() {
    dom.form = document.getElementById("equipmentForm");
    dom.validationList = document.getElementById("validationList");
    dom.rowsBody = document.getElementById("rowsBody");
    dom.rowsTable = document.getElementById("rowsTable");
    dom.tableWrap = document.querySelector(".spareparts-table-wrap");
    dom.materialDetailsHost = document.getElementById("equipmentDetailsHost");
    dom.fieldNoteHost = document.getElementById("fieldNoteHost");

    dom.searchInput = document.getElementById("searchInput");
    dom.statusFilter = document.getElementById("statusFilter");
    dom.plantFilter = document.getElementById("plantFilter");

    dom.btnSave = document.getElementById("btnSave");
    dom.btnReset = document.getElementById("btnReset");
    dom.btnSubmitRows = document.getElementById("btnSubmitRows");
    dom.btnExportCsv = document.getElementById("btnExportCsv");
    dom.btnSendEmail = document.getElementById("btnSendEmailEquipment");
    dom.btnLocalProxy = document.getElementById("btnLocalProxy");
    dom.btnEquipmentViewCompact = document.getElementById("btnEquipmentViewCompact");
    dom.btnEquipmentViewAll = document.getElementById("btnEquipmentViewAll");

    dom.detectedPlant = document.getElementById("detectedPlant");
    dom.detectedStatus = document.getElementById("detectedStatus");
    dom.kpiRows = document.getElementById("kpiRows");
    dom.kpiValid = document.getElementById("kpiValid");
    dom.kpiInvalid = document.getElementById("kpiInvalid");
    dom.runtimeInfo = document.getElementById("runtimeInfo");

    dom.functionalLocationDesc = document.getElementById("functionalLocationDesc");
    dom.functionalLocationSuggestions = document.getElementById("functionalLocationSuggestions");
    dom.datePickers = {};
    dom.dateTriggers = {};

    FIELD_KEYS.forEach((key) => {
      dom.fields[key] = document.getElementById(key);

      if (DATE_FIELD_KEYS.has(key)) {
        dom.datePickers[key] = document.getElementById(`${key}Picker`);
        dom.dateTriggers[key] = document.querySelector(`.eq-date-trigger[data-date-target="${key}"]`);
      }
    });
  }

  function bindEvents() {
    if (dom.form) {
      dom.form.addEventListener("submit", onSave);
      dom.form.addEventListener("click", onFormClick);
    }

    if (dom.btnReset) {
      dom.btnReset.addEventListener("click", () => {
        resetForm(true);
        previewValidation();
        setRuntime("Form reset.");
      });
    }

    if (dom.searchInput) {
      dom.searchInput.addEventListener("input", () => {
        state.filters.search = toText(dom.searchInput.value).toLowerCase();
        scheduleSearchRender();
      });
    }

    if (dom.statusFilter) {
      dom.statusFilter.addEventListener("change", () => {
        state.filters.status = toText(dom.statusFilter.value).toLowerCase() || "all";
        renderRows();
      });
    }

    if (dom.plantFilter) {
      dom.plantFilter.addEventListener("change", () => {
        state.filters.plant = toText(dom.plantFilter.value).toLowerCase() || "all";
        renderRows();
      });
    }

    if (dom.btnEquipmentViewCompact) {
      dom.btnEquipmentViewCompact.addEventListener("click", () => {
        state.tableView = TABLE_VIEW.compact;
        renderRows();
      });
    }

    if (dom.btnEquipmentViewAll) {
      dom.btnEquipmentViewAll.addEventListener("click", () => {
        state.tableView = TABLE_VIEW.all;
        renderRows();
      });
    }

    if (dom.btnSubmitRows) {
      dom.btnSubmitRows.addEventListener("click", () => {
        setRuntime("Submit not connected.");
      });
    }

    if (dom.btnExportCsv) {
      dom.btnExportCsv.addEventListener("click", exportCsv);
    }

    if (dom.btnSendEmail) {
      dom.btnSendEmail.addEventListener("click", sendRowsAsEmail);
    }

    if (dom.btnLocalProxy) {
      dom.btnLocalProxy.addEventListener("click", () => {
        state.net.useLocalProxy = !state.net.useLocalProxy;
        syncLocalProxyUi();
        previewValidation();
        setRuntime(state.net.useLocalProxy ? "Local proxy enabled." : "Local proxy disabled.");
      });
    }

    if (dom.rowsBody) {
      dom.rowsBody.addEventListener("click", onRowsBodyClick);
    }

    if (dom.materialDetailsHost) {
      dom.materialDetailsHost.addEventListener("click", onDetailsHostClick);
    }

    if (dom.fieldNoteHost) {
      dom.fieldNoteHost.addEventListener("click", onFieldNoteHostClick);
    }

    FIELD_KEYS.forEach((key) => {
      const node = getFieldNode(key);
      if (!node) return;

      if (key === "requestType") {
        node.addEventListener("change", () => {
          applyRequestTypeState();
          previewValidation();
        });
        return;
      }

      if (key === "functionalLocation") {
        node.addEventListener("pointerdown", markFlInteractedAndValidate);
        node.addEventListener("focus", markFlInteractedAndValidate);
        node.addEventListener("input", onFunctionalLocationInput);
        node.addEventListener("keydown", onFunctionalLocationKeyDown);
        node.addEventListener("blur", () => {
          state.fl.interacted = true;
          setTimeout(hideFlSuggestions, 120);
          queueBackgroundFlLookup(normalizeUpper(node.value).trim());
        });
        return;
      }

      node.addEventListener("input", () => {
        if (UPPERCASE_FIELDS.has(key) && node.tagName === "INPUT") {
          node.value = normalizeUpper(node.value);
        }
        refreshClearButton(node);
        previewValidation();
      });

      node.addEventListener("change", () => {
        if (UPPERCASE_FIELDS.has(key) && node.tagName === "INPUT") {
          node.value = normalizeUpper(node.value);
        }
        refreshClearButton(node);
        previewValidation();
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;

      closeAllStyledSelects();

      if (state.detailRowId !== null) {
        state.detailRowId = null;
        renderDetailModal();
      }

      if (state.fieldNoteKey) {
        closeFieldNoteModal();
      }

      hideFlSuggestions();
    });

    document.addEventListener("mousedown", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;

      if (target.closest(".eq-select-wrap")) return;
      closeAllStyledSelects();
    });
  }

  function hydrateLookupOptions() {
    const lookups = window.FL_LOOKUPS && typeof window.FL_LOOKUPS === "object" ? window.FL_LOOKUPS : {};

    const plantTable = lookups.Plant;
    const plantRows = getTableRows(plantTable);
    const plantKeyIndex = getColumnIndex(plantTable, ["Plant Key", "Plant"], 0);
    state.options.plants = dedupeValues(
      plantRows
        .map((row) => normalizeUpper(Array.isArray(row) ? row[plantKeyIndex] : ""))
        .filter(Boolean)
    );

    if (!state.options.plants.length) {
      state.options.plants = Array.from(FALLBACK_PLANT_SET);
    }

    state.options.plantSet = new Set(state.options.plants.map((value) => normalizeUpper(value)));

    const eqCatTable = lookups.EQ_Cat;
    const eqRows = getTableRows(eqCatTable);
    const eqDescIndex = getColumnIndex(eqCatTable, ["Equipment category description"], 1);
    state.options.categoryValues = dedupeValues(
      eqRows
        .map((row) => toText(Array.isArray(row) ? row[eqDescIndex] : ""))
        .filter(Boolean)
    );
    state.options.categorySet = new Set(state.options.categoryValues.map((value) => normalizeUpper(value)));

    const docTypeTable = lookups.Table5;
    const docRows = getTableRows(docTypeTable);
    const docTypeIndex = getColumnIndex(docTypeTable, ["Filetype"], 0);
    state.options.documentTypes = dedupeValues(
      docRows
        .map((row) => toText(Array.isArray(row) ? row[docTypeIndex] : ""))
        .filter(Boolean)
    );
    state.options.documentTypeSet = new Set(state.options.documentTypes.map((value) => normalizeUpper(value)));
  }

  function renderStaticSelects() {
    renderRequestTypeSelect();
    renderSelectOptions(dom.fields.plant, state.options.plants, "Choose plant");
    renderSelectOptions(dom.fields.equipmentCategory, state.options.categoryValues, "Choose equipment type");
    renderSelectOptions(dom.fields.documentType, state.options.documentTypes, "Choose document type");
  }

  function renderRequestTypeSelect() {
    const selectNode = dom.fields.requestType;
    if (!selectNode) return;

    const options = [
      { value: REQUEST_TYPES.NEW, label: REQUEST_TYPE_LABELS[REQUEST_TYPES.NEW] },
      { value: REQUEST_TYPES.CHANGE, label: REQUEST_TYPE_LABELS[REQUEST_TYPES.CHANGE] },
      { value: REQUEST_TYPES.DELETE, label: REQUEST_TYPE_LABELS[REQUEST_TYPES.DELETE] },
    ]
      .map((entry) => `<option value="${entry.value}">${escapeHtml(entry.label)}</option>`)
      .join("");

    selectNode.innerHTML = options;
    selectNode.value = REQUEST_TYPES.NEW;
  }

  function renderSelectOptions(selectNode, values, placeholder) {
    if (!selectNode) return;

    const options = [`<option value="">${escapeHtml(toText(placeholder) || "Choose")}</option>`]
      .concat(
        (values || []).map((entry) => {
          const value = toText(entry);
          return `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`;
        })
      )
      .join("");

    selectNode.innerHTML = options;
    syncStyledSelect(selectNode);
  }

  function initializeStyledSelects() {
    const targets = [
      dom.fields.requestType,
      dom.fields.plant,
      dom.fields.equipmentCategory,
      dom.fields.documentType,
      dom.statusFilter,
      dom.plantFilter,
    ].filter(Boolean);

    targets.forEach((selectNode) => setupStyledSelect(selectNode));
    syncAllStyledSelects();
  }

  function setupStyledSelect(selectNode) {
    if (!selectNode) return;
    if (state.styledSelects.some((entry) => entry.select === selectNode)) return;

    const parent = selectNode.parentElement;
    if (!parent) return;

    const wrapper = document.createElement("div");
    wrapper.className = "eq-select-wrap";

    parent.insertBefore(wrapper, selectNode);
    wrapper.appendChild(selectNode);

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "eq-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    wrapper.appendChild(trigger);

    const panel = document.createElement("div");
    panel.className = "combo-panel eq-select-panel";
    panel.hidden = true;
    wrapper.appendChild(panel);

    selectNode.classList.add("eq-select-native");

    const entry = {
      select: selectNode,
      wrapper,
      trigger,
      panel,
    };

    state.styledSelects.push(entry);

    trigger.addEventListener("click", () => {
      if (selectNode.disabled) return;

      if (!panel.hidden) {
        closeStyledSelect(entry);
        return;
      }

      closeAllStyledSelects(selectNode);
      renderStyledSelectOptions(entry);
      panel.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      wrapper.classList.add("open");
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        trigger.click();
      }

      if (event.key === "Escape") {
        closeStyledSelect(entry);
      }
    });

    selectNode.addEventListener("change", () => syncStyledSelect(selectNode));
    syncStyledSelect(selectNode);
  }

  function renderStyledSelectOptions(entry) {
    entry.panel.innerHTML = "";

    const options = Array.from(entry.select.options || []);
    options.forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "combo-item eq-select-option";
      button.textContent = option.textContent || option.value || "";

      if (option.value === entry.select.value) {
        button.classList.add("active");
      }

      if (option.disabled) {
        button.disabled = true;
        button.classList.add("is-disabled");
      }

      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
      });

      button.addEventListener("click", () => {
        if (option.disabled) return;

        entry.select.value = option.value;
        entry.select.dispatchEvent(new Event("input", { bubbles: true }));
        entry.select.dispatchEvent(new Event("change", { bubbles: true }));
        closeStyledSelect(entry);
      });

      entry.panel.appendChild(button);
    });
  }

  function closeStyledSelect(entry) {
    if (!entry) return;

    entry.panel.hidden = true;
    entry.trigger.setAttribute("aria-expanded", "false");
    entry.wrapper.classList.remove("open");
  }

  function closeAllStyledSelects(exceptSelect) {
    state.styledSelects.forEach((entry) => {
      if (exceptSelect && entry.select === exceptSelect) return;
      closeStyledSelect(entry);
    });
  }

  function syncStyledSelect(selectNode) {
    const entry = state.styledSelects.find((item) => item.select === selectNode);
    if (!entry) return;

    const selectedOption = selectNode.options[selectNode.selectedIndex];
    const selectedText = selectedOption ? (selectedOption.textContent || "") : "Select";
    entry.trigger.textContent = selectedText || "Select";
    entry.trigger.disabled = !!selectNode.disabled;
    entry.wrapper.classList.toggle("is-disabled", !!selectNode.disabled);

    entry.trigger.classList.toggle("field-valid", selectNode.classList.contains("field-valid"));
    entry.trigger.classList.toggle("field-invalid", selectNode.classList.contains("field-invalid"));
  }

  function syncAllStyledSelects() {
    state.styledSelects.forEach((entry) => syncStyledSelect(entry.select));
  }

  function initializeLocalProxyUi() {
    state.net.useLocalProxy = false;
    syncLocalProxyUi();
  }

  function syncLocalProxyUi() {
    if (!dom.btnLocalProxy) return;

    dom.btnLocalProxy.textContent = state.net.useLocalProxy ? "Local proxy: ON" : "Local proxy: OFF";
    dom.btnLocalProxy.setAttribute("aria-pressed", state.net.useLocalProxy ? "true" : "false");
  }

  function resolveRequestType(value) {
    const normalized = toText(value).toLowerCase();
    if (normalized === REQUEST_TYPES.CHANGE) return REQUEST_TYPES.CHANGE;
    if (normalized === REQUEST_TYPES.DELETE) return REQUEST_TYPES.DELETE;
    return REQUEST_TYPES.NEW;
  }

  function getRequestTypeLabel(value) {
    const resolved = resolveRequestType(value);
    return REQUEST_TYPE_LABELS[resolved] || REQUEST_TYPE_LABELS[REQUEST_TYPES.NEW];
  }

  function inferRequestTypeFromRow(row) {
    const explicit = resolveRequestType(row && row.requestType);
    if (row && toText(row.requestType)) {
      return explicit;
    }

    const hasEquipmentNumber = !!toText(row && row.equipmentNumber);
    return hasEquipmentNumber ? REQUEST_TYPES.CHANGE : REQUEST_TYPES.NEW;
  }

  function applyRequestTypeState() {
    const requestTypeNode = getFieldNode("requestType");
    const equipmentNumberNode = getFieldNode("equipmentNumber");
    if (!requestTypeNode || !equipmentNumberNode) return;

    const requestType = resolveRequestType(requestTypeNode.value);
    requestTypeNode.value = requestType;

    const lockEquipmentNumber = requestType === REQUEST_TYPES.NEW;
    equipmentNumberNode.disabled = lockEquipmentNumber;
    equipmentNumberNode.classList.toggle("field-bypass", lockEquipmentNumber);
    equipmentNumberNode.placeholder = lockEquipmentNumber
      ? "Låst ved Ny"
      : "Indtast eksisterende equipmentnummer";

    if (lockEquipmentNumber && toText(equipmentNumberNode.value)) {
      equipmentNumberNode.value = "";
    }

    refreshClearButton(equipmentNumberNode);
    syncStyledSelect(requestTypeNode);
    syncRequiredMarkers(requestType);
  }

  function syncRequiredMarkers(requestType) {
    const marker = window.RequiredFields;
    if (!marker) return;

    const requiredFields = requestType === REQUEST_TYPES.NEW
      ? REQUIRED_FIELDS_FOR_NEW
      : REQUIRED_FIELDS_FOR_CHANGE_DELETE;

    FIELD_KEYS.forEach((key) => {
      const node = getFieldNode(key);
      if (!node) return;

      const isRequired = requiredFields.has(key)
        || (key === "equipmentNumber" && requestType !== REQUEST_TYPES.NEW);

      marker.set(node, isRequired);
    });
  }

  function setupClearButtons() {
    const selector = 'input:not([type="file"]):not([type="hidden"]):not([type="checkbox"]):not([type="date"])';
    document.querySelectorAll(selector).forEach((input) => {
      const parent = input.parentElement;
      if (!parent) return;
      if (input.classList.contains("no-clear-btn")) return;

      if (!parent.classList.contains("input-wrap")) {
        const wrapper = document.createElement("div");
        wrapper.className = "input-wrap";
        parent.insertBefore(wrapper, input);
        wrapper.appendChild(input);
      }

      const wrapper = input.parentElement;
      if (!wrapper) return;

      if (!wrapper.querySelector(".clear-btn")) {
        const clearButton = document.createElement("button");
        clearButton.type = "button";
        clearButton.className = "clear-btn";
        clearButton.textContent = "x";
        clearButton.hidden = !toText(input.value);
        clearButton.addEventListener("click", () => {
          input.value = "";
          refreshClearButton(input);
          previewValidation();
          input.focus();
        });
        wrapper.appendChild(clearButton);
      }

      refreshClearButton(input);
    });
  }

  function refreshClearButton(input) {
    if (!input) return;

    const wrapper = input.parentElement;
    if (!wrapper || !wrapper.classList.contains("input-wrap")) return;

    const clearButton = wrapper.querySelector(".clear-btn");
    if (!clearButton) return;

    clearButton.hidden = !toText(input.value);
  }

  function setupDatePickerUi() {
    DATE_FIELD_KEYS.forEach((key) => {
      const textInput = getFieldNode(key);
      const pickerInput = dom.datePickers ? dom.datePickers[key] : null;
      const trigger = dom.dateTriggers ? dom.dateTriggers[key] : null;

      if (!textInput || !pickerInput || !trigger) return;

      syncDatePickerInputFromText(key);

      textInput.addEventListener("input", () => {
        textInput.value = normalizeTypedDateText(textInput.value);
        syncDatePickerInputFromText(key);
      });

      textInput.addEventListener("blur", () => {
        textInput.value = normalizeDateForStorage(textInput.value);
        syncDatePickerInputFromText(key);
      });

      trigger.addEventListener("click", () => {
        syncDatePickerInputFromText(key);

        // showPicker() throws in framed/file contexts; focus keeps the field usable.
        if (typeof pickerInput.showPicker === "function") {
          try {
            pickerInput.showPicker();
            return;
          } catch (error) {
            pickerInput.focus();
            return;
          }
        }

        pickerInput.focus();
      });

      pickerInput.addEventListener("change", () => {
        textInput.value = isoDateToLocal(pickerInput.value);
        refreshClearButton(textInput);
        textInput.dispatchEvent(new Event("input", { bubbles: true }));
        textInput.dispatchEvent(new Event("change", { bubbles: true }));
        textInput.focus();
      });
    });
  }

  function syncDatePickerInputFromText(fieldKey) {
    const textInput = getFieldNode(fieldKey);
    const pickerInput = dom.datePickers ? dom.datePickers[fieldKey] : null;
    if (!textInput || !pickerInput) return;

    const normalized = normalizeDateForStorage(textInput.value);
    if (normalized !== textInput.value) {
      textInput.value = normalized;
    }

    pickerInput.value = toInputDateValue(normalized);
  }

  function syncAllDatePickerInputs() {
    DATE_FIELD_KEYS.forEach((key) => syncDatePickerInputFromText(key));
  }

  function normalizeTypedDateText(value) {
    const text = String(value == null ? "" : value)
      .replaceAll(".", "/")
      .replaceAll("-", "/")
      .replace(/[^0-9/]/g, "")
      .slice(0, 10);

    const digits = text.replaceAll("/", "").slice(0, 8);
    if (!digits) return "";
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
  }

  function setupFieldNotes() {
    Object.keys(FIELD_NOTES).forEach((fieldKey) => {
      const field = getFieldNode(fieldKey);
      if (!field) return;

      const label = field.closest("label");
      if (!label) return;

      label.classList.add("has-field-note");

      if (label.querySelector(`.field-note-btn[data-field-key="${fieldKey}"]`)) {
        return;
      }

      const button = document.createElement("button");
      button.type = "button";
      button.className = "field-note-btn";
      button.setAttribute("data-action", "open-field-note");
      button.setAttribute("data-field-key", fieldKey);
      button.setAttribute("aria-label", `Vis note for ${FIELD_LABELS[fieldKey] || fieldKey}`);
      button.textContent = "i";
      label.appendChild(button);
    });
  }

  function onFormClick(event) {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;

    const noteNode = rawTarget.closest('[data-action="open-field-note"]');
    if (!noteNode || !dom.form || !dom.form.contains(noteNode)) return;

    const fieldKey = toText(noteNode.getAttribute("data-field-key"));
    if (!fieldKey || !FIELD_NOTES[fieldKey]) return;

    openFieldNoteModal(fieldKey);
  }

  function onFieldNoteHostClick(event) {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;

    if (rawTarget.matches(".field-note-backdrop")) {
      closeFieldNoteModal();
      return;
    }

    const closeNode = rawTarget.closest('[data-action="close-field-note"]');
    if (!closeNode || !dom.fieldNoteHost || !dom.fieldNoteHost.contains(closeNode)) return;

    closeFieldNoteModal();
  }

  function openFieldNoteModal(fieldKey) {
    if (!FIELD_NOTES[fieldKey]) return;
    state.fieldNoteKey = fieldKey;
    renderFieldNoteModal();
  }

  function closeFieldNoteModal() {
    state.fieldNoteKey = "";
    if (dom.fieldNoteHost) {
      dom.fieldNoteHost.innerHTML = "";
    }
  }

  function renderFieldNoteModal() {
    if (!dom.fieldNoteHost) return;

    const fieldKey = toText(state.fieldNoteKey);
    const noteText = FIELD_NOTES[fieldKey];
    if (!fieldKey || !noteText) {
      dom.fieldNoteHost.innerHTML = "";
      return;
    }

    const title = FIELD_LABELS[fieldKey] || fieldKey;
    dom.fieldNoteHost.innerHTML = `
      <div class="field-note-backdrop">
        <div class="field-note-modal" role="dialog" aria-modal="true" aria-label="Feltnote">
          <div class="field-note-head">
            <h3>${escapeHtml(title)}</h3>
            <button type="button" class="action-btn primary" data-action="close-field-note">Luk</button>
          </div>
          <div class="field-note-body">${escapeMultilineHtml(noteText)}</div>
        </div>
      </div>
    `;
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
        _status: validation.status,
        _plantKey: validation.detectedPlantKey || row.plant,
        _plant: validation.detectedPlantLabel || getPlantLabelFromKey(row.plant),
        _flDescription: validation.flDescription || "",
        _issues: validation.errors.map((item) => item.text),
        _notes: validation.notes.map((item) => item.text),
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
      const node = getFieldNode(key);
      const value = toText(node ? node.value : "");
      row[key] = DATE_FIELD_KEYS.has(key) ? normalizeDateForStorage(value) : value;
    });
    return row;
  }

  function setForm(row) {
    const requestTypeFromRow = inferRequestTypeFromRow(row);

    FIELD_KEYS.forEach((key) => {
      const node = getFieldNode(key);
      if (!node) return;

      if (key === "requestType") {
        node.value = requestTypeFromRow;
        refreshClearButton(node);
        syncStyledSelect(node);
        return;
      }

      if (DATE_FIELD_KEYS.has(key)) {
        node.value = normalizeDateForStorage(row[key]);
      } else {
        node.value = toText(row[key]);
      }

      refreshClearButton(node);
      syncStyledSelect(node);
    });

    applyRequestTypeState();

    syncAllDatePickerInputs();

    state.fl.interacted = true;

    if (dom.functionalLocationDesc) {
      dom.functionalLocationDesc.className = row._flDescription ? "field-meta ok" : "field-meta";
      dom.functionalLocationDesc.textContent = row._flDescription || "";
    }
  }

  function resetForm(clearValidation) {
    if (dom.form) {
      dom.form.reset();
    }

    state.editIndex = null;
    state.editRowId = null;
    state.fl.interacted = false;

    FIELD_KEYS.forEach((key) => {
      const node = getFieldNode(key);
      if (!node) return;
      refreshClearButton(node);
      node.classList.remove("field-valid", "field-invalid");
      node.removeAttribute("aria-invalid");
    });

    if (dom.fields.plant) {
      dom.fields.plant.value = "";
      syncStyledSelect(dom.fields.plant);
    }

    if (dom.fields.requestType) {
      dom.fields.requestType.value = REQUEST_TYPES.NEW;
      syncStyledSelect(dom.fields.requestType);
    }

    if (dom.fields.equipmentCategory) {
      dom.fields.equipmentCategory.value = "";
      syncStyledSelect(dom.fields.equipmentCategory);
    }

    if (dom.fields.documentType) {
      dom.fields.documentType.value = "";
      syncStyledSelect(dom.fields.documentType);
    }

    if (dom.functionalLocationDesc) {
      dom.functionalLocationDesc.className = "field-meta";
      dom.functionalLocationDesc.textContent = "";
    }

    hideFlSuggestions();

    if (clearValidation && dom.validationList) {
      dom.validationList.innerHTML = "";
    }

    if (dom.detectedPlant) {
      dom.detectedPlant.textContent = "-";
    }

    if (dom.detectedStatus) {
      dom.detectedStatus.textContent = "Not validated";
    }

    applyRequestTypeState();
    syncAllDatePickerInputs();
    syncAllStyledSelects();
  }

  function normalizeRow(row) {
    const normalized = {};

    FIELD_KEYS.forEach((key) => {
      const value = toText(row[key]);
      if (key === "requestType") {
        normalized[key] = resolveRequestType(value);
        return;
      }

      normalized[key] = UPPERCASE_FIELDS.has(key) ? normalizeUpper(value) : value;
    });

    return normalized;
  }

  async function validateRow(row, strictOData) {
    const errors = [];
    const notes = [];
    const fieldErrors = {};
    const requestType = resolveRequestType(row.requestType);
    row.requestType = requestType;

    const requiredFields = requestType === REQUEST_TYPES.NEW
      ? REQUIRED_FIELDS_FOR_NEW
      : REQUIRED_FIELDS_FOR_CHANGE_DELETE;

    const pushErr = (text, details, fields) => {
      errors.push({ text, details: details || "" });
      (fields || []).forEach((field) => {
        if (!fieldErrors[field]) fieldErrors[field] = [];
        fieldErrors[field].push(text);
      });
    };

    const pushNote = (text) => {
      notes.push({ text });
    };

    FIELD_KEYS.forEach((key) => {
      const value = toText(row[key]);
      const maxLen = MAX_LENGTH_BY_FIELD[key] || 0;

      if (requiredFields.has(key) && !value) {
        pushErr(`${FIELD_LABELS[key]} is required.`, "", [key]);
      }

      if (maxLen > 0 && value.length > maxLen) {
        pushErr(`${FIELD_LABELS[key]} too long.`, `${value.length}/${maxLen}`, [key]);
      }
    });

    if (requestType === REQUEST_TYPES.NEW && row.equipmentNumber) {
      pushErr(
        "Equipmentnummer must be empty when Status is Ny.",
        "Ved ny oprettelse skal feltet være tomt.",
        ["equipmentNumber", "requestType"]
      );
    }

    if (requestType !== REQUEST_TYPES.NEW && !row.equipmentNumber) {
      pushErr(
        "Equipmentnummer is required when Status is Ændre or Slettes.",
        "Indsæt eksisterende equipmentnummer.",
        ["equipmentNumber", "requestType"]
      );
    }

    if (row.equipmentNumber && !EQUIPMENT_CODE_PATTERN.test(row.equipmentNumber)) {
      pushErr("Equipmentnummer invalid.", "Only A-Z, 0-9, ., _, /, - are allowed.", ["equipmentNumber"]);
    }

    if (row.functionalLocation1 && !EQUIPMENT_CODE_PATTERN.test(row.functionalLocation1)) {
      pushErr("Func. loc. 1 invalid.", "Only A-Z, 0-9, ., _, /, - are allowed.", ["functionalLocation1"]);
    }

    if (row.functionalLocation2 && !EQUIPMENT_CODE_PATTERN.test(row.functionalLocation2)) {
      pushErr("Functional location 2 invalid.", "Only A-Z, 0-9, ., _, /, - are allowed.", ["functionalLocation2"]);
    }

    if (row.warrantyStart && !isValidLocalDate(row.warrantyStart)) {
      pushErr("Garanti start invalid.", "Use dd/mm/yyyy.", ["warrantyStart"]);
    }

    if (row.warrantyEnd && !isValidLocalDate(row.warrantyEnd)) {
      pushErr("Garanti slut invalid.", "Use dd/mm/yyyy.", ["warrantyEnd"]);
    }

    const normalizedPlant = normalizeUpper(row.plant);
    if (normalizedPlant && state.options.plantSet.size && !state.options.plantSet.has(normalizedPlant)) {
      pushErr("Plant invalid.", "Select a valid plant key.", ["plant"]);
    }

    const normalizedCategory = normalizeUpper(row.equipmentCategory);
    if (normalizedCategory && state.options.categorySet.size && !state.options.categorySet.has(normalizedCategory)) {
      pushErr("Equipment type invalid.", "Select a value from dropdown.", ["equipmentCategory"]);
    }

    const normalizedDocumentType = normalizeUpper(row.documentType);
    if (normalizedDocumentType && state.options.documentTypeSet.size && !state.options.documentTypeSet.has(normalizedDocumentType)) {
      pushErr("Dokument type invalid.", "Select a value from dropdown.", ["documentType"]);
    }

    const shouldValidateFunctionalLocation = requestType === REQUEST_TYPES.NEW || !!toText(row.functionalLocation);
    if (!shouldValidateFunctionalLocation) {
      updateFlMetaText("", "");
    }

    const flResult = shouldValidateFunctionalLocation
      ? await validateFunctionalLocation(row.functionalLocation, strictOData, pushErr, pushNote)
      : { ok: true, pltxt: "", plantKey: "", advisory: false };

    const flPlantKey = getPlantKeyFromFl(row.functionalLocation);
    if (shouldValidateFunctionalLocation && normalizedPlant && flPlantKey && normalizedPlant !== flPlantKey) {
      pushErr("Plant mismatch.", `FL starts with ${flPlantKey} but selected Plant is ${normalizedPlant}.`, ["plant", "functionalLocation"]);
    }

    const hasAdvisory = notes.some((item) => normalizeUpper(item.text).startsWith("SAP ADVISORY"));

    const detectedPlantKey = flPlantKey || normalizedPlant;
    const detectedPlantLabel = getPlantLabelFromKey(detectedPlantKey);

    return {
      status: errors.length ? "invalid" : hasAdvisory ? "warning" : "valid",
      detectedPlantKey,
      detectedPlantLabel,
      flDescription: flResult.pltxt || "",
      errors,
      notes,
      fieldErrors,
    };
  }

  async function validateFunctionalLocation(flRaw, strictOData, pushErr, pushNote) {
    const fl = normalizeUpper(flRaw).trim();
    const plantKey = getPlantKeyFromFl(fl);
    let hasLocalError = false;

    if (!strictOData && !fl) {
      updateFlMetaText("", "");
      return { ok: true, pltxt: "", plantKey: "", advisory: false };
    }

    if (!fl) {
      updateFlMetaText("Functional Location is required.", "error");
      pushErr("Func. location is required.", "", ["functionalLocation"]);
      return { ok: false, pltxt: "", plantKey: "", advisory: false };
    }

    if (!strictOData) {
      if (!getAllowedPlantSet().has(plantKey)) {
        updateFlMetaText("Unknown plant prefix.", "warn");
        return { ok: true, pltxt: "", plantKey, advisory: false };
      }

      if (fl.length < FL_MIN_LEN_OK || !isValidKks(fl)) {
        updateFlMetaText("Typing... continue for validation", "warn");
        return { ok: true, pltxt: "", plantKey, advisory: false };
      }
    }

    if (!getAllowedPlantSet().has(plantKey)) {
      hasLocalError = true;
      pushErr("Plant key invalid for Func. location.", "Allowed: SSV, SKV, HEV, HCV, ASV, AVV, KYV, SMV, STV", ["functionalLocation"]);
    }

    if (hasLineBreak(fl)) {
      hasLocalError = true;
      pushErr("Func. location invalid.", "Use one code per cell.", ["functionalLocation"]);
    }

    if (fl.length < FL_MIN_LEN_OK) {
      hasLocalError = true;
      pushErr("Func. location too short.", `Minimum ${FL_MIN_LEN_OK} characters.`, ["functionalLocation"]);
    }

    if (!isValidKks(fl)) {
      hasLocalError = true;
      pushErr("Func. location invalid.", "Invalid KKS format.", ["functionalLocation"]);
    }

    if (hasLocalError) {
      updateFlMetaText("Local syntax/rules failed.", "error");
      return { ok: false, pltxt: "", plantKey, advisory: false };
    }

    if (strictOData) {
      const lookup = await verifyFlInOData(fl);
      if (!lookup.ok) {
        const hint = formatODataErrorHint(lookup.error || "SAP lookup failed.");
        updateFlMetaText(`SAP advisory: ${hint}`, "warn");
        pushNote(`SAP advisory: Could not verify Functional Location in SAP OData. ${hint}`);
        return { ok: true, pltxt: "", plantKey, advisory: true };
      }

      if (!lookup.exists) {
        updateFlMetaText("SAP advisory: Tplnr not found in SAP.", "warn");
        pushNote("SAP advisory: Functional Location not found in SAP OData (Tplnr). Save is still allowed.");
        return { ok: true, pltxt: "", plantKey, advisory: true };
      }

      updateFlMetaText(lookup.pltxt || "Tplnr found in SAP.", "ok");
      pushNote("Functional Location exists in SAP OData.");
      if (lookup.pltxt) {
        pushNote(`Pltxt: ${lookup.pltxt}`);
      }

      return { ok: true, pltxt: lookup.pltxt || "", plantKey, advisory: false };
    }

    const cached = state.fl.lookupCache.get(fl);
    if (cached && cached.ok) {
      if (cached.exists) {
        updateFlMetaText(cached.pltxt || "Tplnr found in SAP.", "ok");
      } else {
        updateFlMetaText("Tplnr not found in SAP.", "warn");
      }
      return { ok: true, pltxt: cached.exists ? cached.pltxt : "", plantKey, advisory: !cached.exists };
    }

    updateFlMetaText("Local syntax valid. SAP lookup pending...", "warn");
    return { ok: true, pltxt: "", plantKey, advisory: false };
  }

  function getAllowedPlantSet() {
    return state.options.plantSet && state.options.plantSet.size ? state.options.plantSet : FALLBACK_PLANT_SET;
  }

  function getPlantKeyFromFl(fl) {
    const normalized = normalizeUpper(fl);
    return normalized.length >= 3 ? normalized.slice(0, 3) : "";
  }

  function getPlantLabelFromKey(key) {
    const normalized = normalizeUpper(key);
    if (!normalized) return "";
    return PLANT_NAME_BY_PREFIX[normalized] || normalized;
  }

  async function verifyFlInOData(fl) {
    const normalized = normalizeUpper(fl);
    if (!normalized) {
      return { ok: false, exists: false, pltxt: "", error: "Empty FL." };
    }

    const cached = state.fl.lookupCache.get(normalized);
    if (cached) {
      return cached;
    }

    if (!window.OrstedOData || typeof window.OrstedOData.lookupFunctionalLocation !== "function") {
      return { ok: false, exists: false, pltxt: "", error: "OData client unavailable." };
    }

    try {
      const result = await window.OrstedOData.lookupFunctionalLocation(normalized, {
        useLocalProxy: state.net.useLocalProxy,
        timeoutMs: 20000,
      });

      const normalizedResult = {
        ok: !!(result && result.ok),
        exists: !!(result && result.exists),
        pltxt: toText(result && result.pltxt),
        error: result && result.error ? String(result.error) : "",
      };

      state.fl.lookupCache.set(normalized, normalizedResult);
      return normalizedResult;
    } catch (error) {
      return {
        ok: false,
        exists: false,
        pltxt: "",
        error: error && error.message ? error.message : String(error),
      };
    }
  }

  function updateFlMetaText(text, tone) {
    if (!dom.functionalLocationDesc) return;

    const normalizedTone = toText(tone).toLowerCase();
    dom.functionalLocationDesc.className = "field-meta";

    if (normalizedTone === "ok") {
      dom.functionalLocationDesc.classList.add("ok");
    } else if (normalizedTone === "warn") {
      dom.functionalLocationDesc.classList.add("warn");
    } else if (normalizedTone === "error") {
      dom.functionalLocationDesc.classList.add("error");
    }

    dom.functionalLocationDesc.textContent = toText(text);
  }

  function renderValidation(validation) {
    if (!dom.validationList) return;

    const blocks = [];

    (validation.errors || []).forEach((entry) => {
      const detailSuffix = toText(entry.details) ? ` ${escapeHtml(entry.details)}` : "";
      blocks.push(`<span class="note">${escapeHtml(entry.text)}${detailSuffix}</span>`);
    });

    (validation.notes || []).forEach((entry) => {
      blocks.push(`<span class="note ok">${escapeHtml(entry.text)}</span>`);
    });

    dom.validationList.innerHTML = blocks.join("");
  }

  function updateValidationMeta(validation, row) {
    if (dom.detectedPlant) {
      const plantText = toText(validation.detectedPlantLabel)
        || getPlantLabelFromKey(row.plant)
        || "-";
      dom.detectedPlant.textContent = plantText;
    }

    if (dom.detectedStatus) {
      dom.detectedStatus.textContent = mapStatusToDanish(validation.status);
    }

    if (dom.functionalLocationDesc && !toText(dom.functionalLocationDesc.textContent)) {
      if (validation.flDescription) {
        updateFlMetaText(validation.flDescription, "ok");
      }
    }
  }

  function applyFieldValidationState(fieldErrors) {
    FIELD_KEYS.forEach((key) => {
      const node = getFieldNode(key);
      if (!node) return;

      node.classList.remove("field-valid", "field-invalid");
      node.removeAttribute("aria-invalid");

      const errors = fieldErrors && fieldErrors[key] ? fieldErrors[key] : [];
      const hasValue = !!toText(node.value);

      if (errors.length) {
        node.classList.add("field-invalid");
        node.setAttribute("aria-invalid", "true");
        return;
      }

      if (hasValue) {
        node.classList.add("field-valid");
        node.setAttribute("aria-invalid", "false");
      }

      syncStyledSelect(node);
    });
  }

  function renderAll() {
    renderRows();
    renderKpis();
    renderPlantFilter();
    syncAllStyledSelects();
  }

  function renderRows() {
    if (!dom.rowsBody) return;

    syncTableViewUi();

    const visibleFieldKeys = state.tableView === TABLE_VIEW.compact ? COMPACT_FIELD_KEYS : FIELD_KEYS.slice();
    renderTableHead(visibleFieldKeys);

    const fragment = document.createDocumentFragment();
    const filteredRows = getFilteredRows();

    filteredRows.forEach((row) => {
      const rowId = ensureRowId(row);
      const tr = document.createElement("tr");
      tr.setAttribute("data-row-id", String(rowId));

      const fieldCells = visibleFieldKeys
        .map((fieldKey) => `<td>${escapeHtml(formatFieldDisplayValue(fieldKey, row[fieldKey]) || "-")}</td>`)
        .join("");

      const detailsCell =
        state.tableView === TABLE_VIEW.compact
          ? `<button class="table-btn" type="button" data-action="equipment-details" data-row-id="${rowId}">Details</button>`
          : "";

      tr.innerHTML = `
        <td><span class="status ${escapeHtml(toText(row._status).toLowerCase())}">${escapeHtml(toText(row._status).toUpperCase())}</span></td>
        ${fieldCells}
        ${state.tableView === TABLE_VIEW.compact ? `<td>${detailsCell}</td>` : ""}
        <td>
          <button class="table-btn" type="button" data-action="edit-equipment-row" data-row-id="${rowId}">Edit</button>
          <button class="table-btn" type="button" data-action="copy-equipment-row" data-row-id="${rowId}">Copy</button>
          <button class="table-btn danger" type="button" data-action="delete-equipment-row" data-row-id="${rowId}">Delete</button>
        </td>
      `;

      fragment.appendChild(tr);
    });

    dom.rowsBody.replaceChildren(fragment);
    renderDetailModal();
  }

  function renderTableHead(visibleFieldKeys) {
    if (!dom.rowsTable) return;

    const head = dom.rowsTable.querySelector("thead");
    if (!head) return;

    const signature = `${state.tableView}|${visibleFieldKeys.join(",")}`;
    if (state.ui.lastTableHeadKey === signature) return;
    state.ui.lastTableHeadKey = signature;

    const fieldHeaders = visibleFieldKeys
      .map((fieldKey) => `<th>${escapeHtml(FIELD_LABELS[fieldKey])}</th>`)
      .join("");

    const detailsHeader = state.tableView === TABLE_VIEW.compact ? "<th>Details</th>" : "";

    head.innerHTML = `
      <tr>
        <th>Validation</th>
        ${fieldHeaders}
        ${detailsHeader}
        <th>Actions</th>
      </tr>
    `;
  }

  function syncTableViewUi() {
    const compactPressed = state.tableView === TABLE_VIEW.compact;

    if (dom.btnEquipmentViewCompact) {
      dom.btnEquipmentViewCompact.setAttribute("aria-pressed", compactPressed ? "true" : "false");
    }

    if (dom.btnEquipmentViewAll) {
      dom.btnEquipmentViewAll.setAttribute("aria-pressed", compactPressed ? "false" : "true");
    }

    if (dom.tableWrap) {
      dom.tableWrap.classList.toggle("all-columns", state.tableView === TABLE_VIEW.all);
    }

    if (dom.rowsTable) {
      dom.rowsTable.classList.toggle("spareparts-table-all", state.tableView === TABLE_VIEW.all);
    }
  }

  function renderKpis() {
    const total = state.rows.length;
    const valid = state.rows.filter((row) => toText(row._status).toLowerCase() === "valid").length;
    const warning = state.rows.filter((row) => toText(row._status).toLowerCase() === "warning").length;
    const invalid = state.rows.filter((row) => toText(row._status).toLowerCase() === "invalid").length;

    if (dom.kpiRows) dom.kpiRows.textContent = String(total);
    if (dom.kpiValid) dom.kpiValid.textContent = String(valid + warning);
    if (dom.kpiInvalid) dom.kpiInvalid.textContent = String(invalid);
  }

  function renderPlantFilter() {
    if (!dom.plantFilter) return;

    const previousValue = toText(dom.plantFilter.value).toLowerCase() || "all";
    const plantLabels = Array.from(
      new Set(
        state.rows
          .map((row) => toText(row._plantKey) || toText(row.plant))
          .map((entry) => normalizeUpper(entry))
          .filter(Boolean)
      )
    ).sort();

    const options = [`<option value="all">All plants</option>`]
      .concat(
        plantLabels.map((entry) => {
          const label = escapeHtml(entry);
          return `<option value="${label.toLowerCase()}">${label}</option>`;
        })
      )
      .join("");

    dom.plantFilter.innerHTML = options;

    const hasPrevious = Array.from(dom.plantFilter.options).some((option) => option.value === previousValue);
    dom.plantFilter.value = hasPrevious ? previousValue : "all";
    state.filters.plant = dom.plantFilter.value;
    syncStyledSelect(dom.plantFilter);
  }

  function getFilteredRows() {
    const search = toText(state.filters.search).toLowerCase();
    const statusFilter = toText(state.filters.status).toLowerCase();
    const plantFilter = toText(state.filters.plant).toLowerCase();

    return state.rows.filter((row) => {
      if (statusFilter !== "all" && toText(row._status).toLowerCase() !== statusFilter) {
        return false;
      }

      const rowPlant = normalizeUpper(toText(row._plantKey) || toText(row.plant)).toLowerCase();
      if (plantFilter !== "all" && rowPlant !== plantFilter) {
        return false;
      }

      if (search) {
        const blob = toText(row._searchBlob);
        if (!blob.includes(search)) return false;
      }

      return true;
    });
  }

  function onRowsBodyClick(event) {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;

    const actionNode = rawTarget.closest("[data-action]");
    if (!actionNode || !dom.rowsBody.contains(actionNode)) return;

    const action = toText(actionNode.getAttribute("data-action"));
    const rowId = readRowIdFromActionNode(actionNode);
    if (!rowId) return;

    if (action === "equipment-details") {
      state.detailRowId = rowId;
      renderDetailModal();
      return;
    }

    const rowIndex = getRowIndexById(rowId);
    if (rowIndex < 0) return;

    if (action === "edit-equipment-row") {
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

    if (action === "copy-equipment-row") {
      const row = state.rows[rowIndex];
      if (!row) return;

      const cloned = {
        ...row,
        _rowId: state.nextRowId++,
        _issues: Array.isArray(row._issues) ? row._issues.slice() : [],
        _notes: Array.isArray(row._notes) ? row._notes.slice() : [],
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

    if (action === "delete-equipment-row") {
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
    }
  }

  function onDetailsHostClick(event) {
    const rawTarget = event.target;
    if (!(rawTarget instanceof Element)) return;

    const closeNode = rawTarget.closest("[data-action='close-equipment-details']");
    if (!closeNode || !dom.materialDetailsHost.contains(closeNode)) return;

    state.detailRowId = null;
    renderDetailModal();
  }

  function renderDetailModal() {
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

    const details = FIELD_KEYS.filter((key) => !COMPACT_FIELD_KEYS.includes(key)).map((key) => ({
      label: FIELD_LABELS[key],
      value: formatFieldDisplayValue(key, row[key]),
    }));

    dom.materialDetailsHost.innerHTML = `
      <div class="class-detail-backdrop">
        <div class="class-detail-modal" role="dialog" aria-modal="true" aria-label="Equipment row details">
          <div class="class-detail-head">
            <div>
              <h3>Row details</h3>
              <p class="small-muted">Func. location: ${escapeHtml(toText(row.functionalLocation) || "-")}</p>
            </div>
            <div class="class-detail-actions">
              <button type="button" class="action-btn primary" data-action="close-equipment-details">Close</button>
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
                ${details
                  .map(
                    (entry) => `
                    <tr>
                      <td>${escapeHtml(entry.label)}</td>
                      <td>${escapeHtml(entry.value || "-")}</td>
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

  function sendRowsAsEmail() {
    if (state.ui.saveInProgress) {
      setRuntime("Gemning er i gang. Vent et oejeblik og proev igen.");
      return;
    }

    const snapshot = buildEquipmentMailSnapshot();
    const hasDraftValues = FIELD_KEYS
      .filter((key) => !NON_CONTENT_FIELD_KEYS.has(key))
      .some((key) => !!toText(snapshot.draft[key]));

    if (!window.MailtoUtils || typeof window.MailtoUtils.finalizeMailtoHref !== "function") {
      setRuntime("Mailfunktion er ikke tilgaengelig.");
      return;
    }

    if (!snapshot.rows.length && !hasDraftValues) {
      setRuntime("Ingen data at sende.");
      return;
    }

    const subject = buildEquipmentEmailSubject(snapshot);
    const detailedBody = buildEquipmentEmailBody(snapshot, false);
    const summaryBody = buildEquipmentEmailBody(snapshot, true);

    const resolved = window.MailtoUtils.finalizeMailtoHref({
      recipient: MAILTO_RECIPIENT,
      subject,
      detailedBody,
      summaryBody,
      maxUrlLength: MAILTO_MAX_URL_LENGTH,
      truncationNote: "[afkortet pga. mail-laengde]",
    });

    if (!resolved.ok) {
      setRuntime("Mailindholdet er for stort. Brug Export CSV.");
      return;
    }

    window.location.href = resolved.href;

    if (resolved.mode === "full") {
      setRuntime("Aabner mailkladde i mailklient. Fuldt indhold.");
      return;
    }

    if (resolved.mode === "summary") {
      setRuntime("Aabner mailkladde i mailklient. Oversigt.");
      return;
    }

    setRuntime("Aabner mailkladde i mailklient. Afkortet oversigt.");
  }

  function buildEquipmentMailSnapshot() {
    const rows = state.rows.slice();
    const draft = normalizeRow(readForm());

    return {
      generatedAt: new Date(),
      rows,
      draft,
      statusCounts: countEquipmentStatuses(rows),
      plantLabel: inferMailPlant(rows, draft),
      activeFilters: {
        search: state.filters.search,
        status: state.filters.status,
        plant: state.filters.plant,
      },
    };
  }

  function countEquipmentStatuses(rows) {
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

  function buildEquipmentEmailSubject(snapshot) {
    const dateStamp = new Date().toISOString().slice(0, 10);
    const rowCount = snapshot.rows.length;
    const rowLabel = rowCount === 1 ? "raekke" : "raekker";
    return `SAP Vedligehold | Equipment Drift | ${snapshot.plantLabel} | ${rowCount} ${rowLabel} | Fejl ${snapshot.statusCounts.invalid} | ${dateStamp}`;
  }

  function inferMailPlant(rows, draft) {
    const draftPlant = normalizePlantLabel(draft && draft.plant);
    if (draftPlant) return draftPlant;

    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i];
      const rowPlant = normalizePlantLabel(row._plantKey || row.plant);
      if (rowPlant) return rowPlant;
    }

    const filterPlant = normalizePlantLabel(state.filters.plant);
    if (filterPlant && filterPlant.toLowerCase() !== "all") return filterPlant;

    return "Uden anlaeg";
  }

  function normalizePlantLabel(value) {
    const text = normalizeUpper(value);
    if (!text || text === "-" || text === "N/A") return "";
    return text;
  }

  function buildEquipmentEmailBody(snapshot, compact) {
    const lines = [];
    const rows = snapshot.rows;
    const draft = snapshot.draft;
    const generatedAt = snapshot.generatedAt.toLocaleString();
    const rowLimit = compact ? Math.min(rows.length, 8) : rows.length;

    lines.push("EQUIPMENT DRIFT MAILUDKAST");
    lines.push(`Modtager: ${MAILTO_RECIPIENT}`);
    lines.push(`Genereret: ${generatedAt}`);
    lines.push("========================================");
    lines.push("01) OVERSIGT");
    lines.push(`- Gemte raekker: ${rows.length}`);
    lines.push(`- Gyldige: ${snapshot.statusCounts.valid}`);
    lines.push(`- Advarsler: ${snapshot.statusCounts.warning}`);
    lines.push(`- Ugyldige: ${snapshot.statusCounts.invalid}`);
    lines.push(`- Kladder: ${snapshot.statusCounts.draft}`);
    lines.push(`- Aktivt statusfilter (UI): ${toText(snapshot.activeFilters.status) || "all"}`);
    lines.push(`- Aktivt plantefilter (UI): ${toText(snapshot.activeFilters.plant) || "all"}`);
    lines.push(`- Aktiv soegetekst (UI): ${toText(snapshot.activeFilters.search) || "-"}`);
    lines.push("- Mailen inkluderer alle gemte raekker uanset aktive filtre.");
    lines.push("");
    lines.push("02) AKTUELT FORMULARUDKAST");

    FIELD_KEYS.forEach((key) => {
      const value = formatFieldDisplayValue(key, draft[key]);
      if (compact && !value) return;
      lines.push(formatFieldLine(getEmailFieldLabel(key), value || "-"));
    });

    lines.push("");
    lines.push(compact ? "03) GEMTE RAEKKER (KOMPRIMERET)" : "03) GEMTE RAEKKER (DETALJER)");

    if (!rows.length) {
      lines.push("- Ingen gemte raekker.");
      return lines.join("\n");
    }

    for (let index = 0; index < rowLimit; index += 1) {
      const row = rows[index];
      lines.push("");
      lines.push(`Raekke ${index + 1} | Status: ${mapStatusToDanish(row._status)}`);
      lines.push("----------------------------------------");

      if (compact) {
        lines.push(formatFieldLine("Status", formatFieldDisplayValue("requestType", row.requestType) || "-"));
        lines.push(formatFieldLine("Anlaeg", toText(row.plant) || "-"));
        lines.push(formatFieldLine("Funktionslokation", toText(row.functionalLocation) || "-"));
        lines.push(formatFieldLine("Equipmentnummer", toText(row.equipmentNumber) || "-"));
        lines.push(formatFieldLine("Beskrivelse", toText(row.description) || "-"));
        lines.push(formatFieldLine("Equipment type", toText(row.equipmentCategory) || "-"));
      } else {
        FIELD_KEYS.forEach((key) => {
          lines.push(formatFieldLine(getEmailFieldLabel(key), clipText(formatFieldDisplayValue(key, row[key]), 220) || "-"));
        });
        lines.push(formatFieldLine("FL-beskrivelse", clipText(row._flDescription, 220) || "-"));
        lines.push(formatFieldLine("Valideringsfejl", row._issues && row._issues.length ? clipText(row._issues.join(" | "), 320) : "-"));
        lines.push(formatFieldLine("Noter", row._notes && row._notes.length ? clipText(row._notes.join(" | "), 320) : "-"));
      }
    }

    if (rows.length > rowLimit) {
      lines.push("");
      lines.push(`... ${rows.length - rowLimit} flere raekker er ikke medtaget.`);
    }

    if (compact) {
      lines.push("");
      lines.push("Brug Export CSV i appen for komplet datasat.");
    }

    return lines.join("\n");
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
    const rows = state.rows.slice();
    if (!rows.length) {
      setRuntime("No rows to export.");
      return;
    }

    const headers = ["Status", ...FIELD_KEYS.map((key) => FIELD_LABELS[key]), "FL Description", "Issues", "Notes"];
    const csvRows = [headers];

    rows.forEach((row) => {
      csvRows.push([
        row._status,
        ...FIELD_KEYS.map((key) => formatFieldDisplayValue(key, row[key]) || ""),
        row._flDescription || "",
        (row._issues || []).join(" | "),
        (row._notes || []).join(" | "),
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
    link.download = `equipment_export_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    setRuntime(`Exported ${rows.length} rows.`);
  }

  function onFunctionalLocationInput() {
    state.fl.interacted = true;

    const input = getFieldNode("functionalLocation");
    if (!input) return;

    input.value = normalizeUpper(input.value);
    refreshClearButton(input);

    const fl = toText(input.value);
    previewValidation();

    if (!shouldQuerySuggestions(fl)) {
      stopFlSearchDots();
      hideFlSuggestions();
      return;
    }

    if (state.fl.debounceTimer) {
      window.clearTimeout(state.fl.debounceTimer);
      state.fl.debounceTimer = null;
    }

    const token = ++state.fl.token;

    state.fl.debounceTimer = window.setTimeout(async () => {
      state.fl.debounceTimer = null;

      if (token !== state.fl.token) return;

      startFlSearchDots();
      state.fl.isSuggesting = true;

      const items = await searchFunctionalLocationSuggestions(fl);

      state.fl.isSuggesting = false;
      stopFlSearchDots();

      if (token !== state.fl.token) return;
      if (toText(getFieldNode("functionalLocation").value) !== fl) return;

      if (!items.length) {
        hideFlSuggestions();
        return;
      }

      renderFlSuggestions(items);
    }, SUGGEST_DEBOUNCE_MS);
  }

  function shouldQuerySuggestions(fl) {
    const normalized = normalizeUpper(fl);
    if (!normalized || normalized.length < FL_SUGGEST_MIN_CHARS) return false;

    const plantKey = getPlantKeyFromFl(normalized);
    return getAllowedPlantSet().has(plantKey);
  }

  async function searchFunctionalLocationSuggestions(query) {
    if (!window.OrstedOData || typeof window.OrstedOData.searchFunctionalLocations !== "function") {
      return [];
    }

    try {
      const results = await window.OrstedOData.searchFunctionalLocations(query, {
        minChars: FL_SUGGEST_MIN_CHARS,
        limit: 12,
        maxFallbackSteps: 2,
        timeoutMs: 8000,
        useLocalProxy: state.net.useLocalProxy,
      });

      return (results || []).map((item) => ({
        tplnr: normalizeUpper(item && item.tplnr),
        pltxt: toText(item && item.pltxt),
      })).filter((item) => item.tplnr);
    } catch (_) {
      return [];
    }
  }

  function renderFlSuggestions(items) {
    if (!dom.functionalLocationSuggestions) return;

    state.fl.suggestions = items.slice();
    state.fl.activeIndex = -1;

    dom.functionalLocationSuggestions.innerHTML = "";

    const fragment = document.createDocumentFragment();

    items.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "combo-item";
      button.setAttribute("data-index", String(index));
      button.innerHTML = `
        <span class="combo-key">${escapeHtml(item.tplnr)}</span>
        <span class="combo-text">${escapeHtml(item.pltxt || "-")}</span>
      `;

      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
      });

      button.addEventListener("click", () => {
        applyFlSuggestion(item);
      });

      fragment.appendChild(button);
    });

    dom.functionalLocationSuggestions.appendChild(fragment);
    dom.functionalLocationSuggestions.hidden = false;
  }

  async function applyFlSuggestion(item) {
    const input = getFieldNode("functionalLocation");
    if (!input) return;

    input.value = normalizeUpper(item.tplnr);
    refreshClearButton(input);
    hideFlSuggestions();

    await queueBackgroundFlLookup(item.tplnr);
    previewValidation();
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
      const selected = state.fl.suggestions[state.fl.activeIndex];
      if (selected) {
        applyFlSuggestion(selected);
      }
      return;
    }

    if (event.key === "Escape") {
      hideFlSuggestions();
    }
  }

  function moveFlSuggestion(step) {
    if (!state.fl.suggestions.length) return;

    let nextIndex = state.fl.activeIndex + step;
    if (nextIndex < 0) nextIndex = state.fl.suggestions.length - 1;
    if (nextIndex >= state.fl.suggestions.length) nextIndex = 0;

    state.fl.activeIndex = nextIndex;

    const nodes = dom.functionalLocationSuggestions.querySelectorAll(".combo-item");
    nodes.forEach((node, index) => {
      node.classList.toggle("active", index === nextIndex);
      if (index === nextIndex) {
        node.scrollIntoView({ block: "nearest" });
      }
    });
  }

  function hideFlSuggestions() {
    if (!dom.functionalLocationSuggestions) return;

    dom.functionalLocationSuggestions.hidden = true;
    dom.functionalLocationSuggestions.innerHTML = "";
    state.fl.suggestions = [];
    state.fl.activeIndex = -1;
  }

  async function queueBackgroundFlLookup(fl) {
    const normalized = normalizeUpper(fl);
    if (!normalized || !isLikelyCompleteFl(normalized)) return;

    const input = getFieldNode("functionalLocation");
    if (!input) return;

    const lookup = await verifyFlInOData(normalized);

    if (normalizeUpper(input.value).trim() !== normalized) return;

    if (!lookup.ok) {
      if (hasVisibleFlSuggestions()) return;
      updateFlMetaText(formatODataErrorHint(lookup.error || "SAP lookup unavailable."), "warn");
      return;
    }

    if (lookup.exists) {
      updateFlMetaText(lookup.pltxt || "Tplnr found in SAP.", "ok");
    } else {
      updateFlMetaText("Tplnr not found in SAP.", "warn");
    }
  }

  function isLikelyCompleteFl(fl) {
    const normalized = normalizeUpper(fl);
    if (!normalized || normalized.length < FL_MIN_LEN_OK) return false;
    if (!isValidKks(normalized)) return false;

    const plantKey = getPlantKeyFromFl(normalized);
    return getAllowedPlantSet().has(plantKey);
  }

  function hasVisibleFlSuggestions() {
    if (!dom.functionalLocationSuggestions) return false;
    return !dom.functionalLocationSuggestions.hidden;
  }

  function startFlSearchDots() {
    stopFlSearchDots();

    state.fl.searchDotsCount = 0;
    state.fl.searchDotsTimer = window.setInterval(() => {
      if (!state.fl.isSuggesting) return;
      state.fl.searchDotsCount = (state.fl.searchDotsCount + 1) % 4;
      const dots = ".".repeat(state.fl.searchDotsCount) || ".";
      updateFlMetaText(`Searching SAP suggestions${dots}`, "warn");
    }, 280);
  }

  function stopFlSearchDots() {
    if (state.fl.searchDotsTimer) {
      window.clearInterval(state.fl.searchDotsTimer);
      state.fl.searchDotsTimer = null;
    }
  }

  function markFlInteractedAndValidate() {
    if (state.fl.interacted) return;
    state.fl.interacted = true;
    previewValidation();
  }

  function scheduleSearchRender() {
    if (state.ui.searchDebounceTimer) {
      window.clearTimeout(state.ui.searchDebounceTimer);
      state.ui.searchDebounceTimer = null;
    }

    state.ui.searchDebounceTimer = window.setTimeout(() => {
      state.ui.searchDebounceTimer = null;
      renderRows();
    }, SEARCH_INPUT_DEBOUNCE_MS);
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

  function readRowIdFromActionNode(actionNode) {
    const direct = Number(actionNode.getAttribute("data-row-id"));
    if (Number.isInteger(direct) && direct > 0) {
      return direct;
    }

    const rowNode = actionNode.closest("tr[data-row-id]");
    if (!rowNode) return 0;

    const fallback = Number(rowNode.getAttribute("data-row-id"));
    return Number.isInteger(fallback) && fallback > 0 ? fallback : 0;
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

  function buildRowSearchBlob(row) {
    return FIELD_KEYS
      .map((key) => formatFieldDisplayValue(key, row[key]))
      .concat([toText(row._flDescription), toText(row._plant), toText(row._plantKey)])
      .join(" ")
      .toLowerCase();
  }

  function getTableRows(table) {
    if (!table || !Array.isArray(table.rows)) return [];
    return table.rows;
  }

  function getColumnIndex(table, preferredHeaders, fallbackIndex) {
    if (!table || !Array.isArray(table.headers)) return fallbackIndex;

    const normalized = table.headers.map((header) => normalizeUpper(header));

    for (let i = 0; i < preferredHeaders.length; i += 1) {
      const wanted = normalizeUpper(preferredHeaders[i]);
      const found = normalized.indexOf(wanted);
      if (found >= 0) return found;
    }

    return fallbackIndex;
  }

  function dedupeValues(values) {
    const seen = new Set();
    const output = [];

    (values || []).forEach((entry) => {
      const text = toText(entry);
      if (!text) return;
      const key = normalizeUpper(text);
      if (seen.has(key)) return;
      seen.add(key);
      output.push(text);
    });

    return output;
  }

  function getFieldNode(key) {
    return dom.fields[key] || null;
  }

  function getEmailFieldLabel(key) {
    return EMAIL_FIELD_LABELS_DA[key] || FIELD_LABELS[key] || key;
  }

  function formatFieldDisplayValue(key, value) {
    if (key === "requestType") {
      return getRequestTypeLabel(value);
    }

    return toText(value);
  }

  function mapStatusToDanish(status) {
    const normalized = toText(status).toLowerCase();
    if (normalized === "valid") return "Gyldig";
    if (normalized === "warning") return "Gyldig med advarsel";
    if (normalized === "invalid") return "Ugyldig";
    return toText(status).toUpperCase() || "-";
  }

  function formatFieldLine(label, value) {
    const left = toText(label) || "-";
    const right = toText(value) || "-";
    return `${left.padEnd(32, " ")}: ${right}`;
  }

  function setRuntime(text) {
    if (!dom.runtimeInfo) return;
    dom.runtimeInfo.textContent = toText(text);
  }

  function isValidKks(functionalLocation) {
    const normalized = normalizeUpper(functionalLocation);
    if (!normalized) return true;
    return FL_PATTERNS.some((pattern) => pattern.test(normalized));
  }

  function hasLineBreak(value) {
    return /[\r\n]/.test(toText(value));
  }

  function normalizeDateForStorage(value) {
    const text = toText(value);
    if (!text) return "";

    if (DATE_PATTERN_LOCAL.test(text)) {
      return text;
    }

    if (DATE_PATTERN_DOTTED_LEGACY.test(text)) {
      return text.replaceAll(".", "/");
    }

    if (DATE_PATTERN_ISO.test(text)) {
      return isoDateToLocal(text);
    }

    return text;
  }

  function toInputDateValue(value) {
    const text = toText(value);
    if (!text) return "";

    if (DATE_PATTERN_ISO.test(text)) {
      return text;
    }

    if (DATE_PATTERN_LOCAL.test(text)) {
      return localDateToIso(text);
    }

    if (DATE_PATTERN_DOTTED_LEGACY.test(text)) {
      return localDateToIso(text.replaceAll(".", "/"));
    }

    return "";
  }

  function localDateToIso(value) {
    const text = toText(value);
    if (!DATE_PATTERN_LOCAL.test(text)) return "";

    const parts = text.split("/");
    const day = parts[0];
    const month = parts[1];
    const year = parts[2];
    return `${year}-${month}-${day}`;
  }

  function isoDateToLocal(value) {
    const text = toText(value);
    if (!DATE_PATTERN_ISO.test(text)) return "";

    const parts = text.split("-");
    const year = parts[0];
    const month = parts[1];
    const day = parts[2];
    return `${day}/${month}/${year}`;
  }

  function isValidLocalDate(value) {
    const text = normalizeDateForStorage(value);
    if (!DATE_PATTERN_LOCAL.test(text)) return false;

    const parts = text.split("/");
    const day = Number.parseInt(parts[0], 10);
    const month = Number.parseInt(parts[1], 10);
    const year = Number.parseInt(parts[2], 10);

    if (!Number.isInteger(day) || !Number.isInteger(month) || !Number.isInteger(year)) return false;
    if (month < 1 || month > 12) return false;
    if (day < 1 || day > 31) return false;

    const date = new Date(year, month - 1, day);
    return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day;
  }

  function formatODataErrorHint(message) {
    const text = toText(message);
    if (!text) return "SAP lookup unavailable.";

    if (window.OrstedOData && typeof window.OrstedOData.formatLookupError === "function") {
      return window.OrstedOData.formatLookupError(text, state.net.useLocalProxy);
    }

    return text;
  }

  function escapeMultilineHtml(value) {
    return escapeHtml(value).replaceAll("\n", "<br>");
  }
})();

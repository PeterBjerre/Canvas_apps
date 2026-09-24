(function () {
  const { toText, normalizeUpper, clipText, escapeHtml } = window.TextUtils;

  const state = {
    optionsLoaded: false,
    options: {},
    tasklistsLoaded: false,
    tasklists: {},
    tasklistSource: "",
    tasklistVersion: "",
    plan: {
      plant: "",
      status: "New",
      planText: "",
      sortField: "",
      cycle: "",
      unit: "",
      callHorizon: "",
      schedulingIndicator: "",
      firstCallDay: "",
      firstCallMonth: "",
      firstCallYear: "",
      statutorySortField: "",
    },
    planCommitted: false,
    planLocked: false,
    lastCommittedPlant: "",
    items: [],
    nextItemId: 1,
    activeItemId: null,
    activeOperationIndex: -1,
    validationRunning: false,
    net: {
      useLocalProxy: false,
    },
    flSuggest: {
      items: [],
      activeIndex: -1,
      timer: null,
      token: 0,
      abortController: null,
    },
    tasklistPicker: {
      open: false,
      filter: "",
      templates: [],
      visibleIndices: [],
      selectedIndices: new Set(),
    },
    styledSelects: [],
  };

  const dom = {};
  const MAILTO_MAX_URL_LENGTH = 1850;
  const MAILTO_RECIPIENT = "sapvedligehold@orsted.com";
  const VH_PLAN_FIELDS_FOR_EMAIL = [
    ["plant", "Vaerk"],
    ["status", "Status"],
    ["planText", "Plantekst"],
    ["sortField", "Sorteringsfelt"],
    ["cycle", "Cyklus"],
    ["unit", "Enhed"],
    ["callHorizon", "Kaldshorisont"],
    ["schedulingIndicator", "Planlaegningsindikator"],
    ["firstCallDay", "Foerste kald dag"],
    ["firstCallMonth", "Foerste kald maaned"],
    ["firstCallYear", "Foerste kald aar"],
    ["statutorySortField", "Lovpligtigt sorteringsfelt"],
  ];

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    bindDom();
    bindEvents();
    setupStyledSelects();

    updateProxyButton();
    setRuntime("Loading options and tasklists...");

    await Promise.all([loadOptions(), loadTasklists()]);

    syncPlanToForm();
    renderItemRail();
    loadActiveItemIntoEditor();
    renderTasklistControls();
    applyPlanInteractionState();

    setRuntime("Fill plan data, then click Save.");
  }

  function bindDom() {
    dom.runtime = document.getElementById("vhRuntimeInfo");
    dom.optionsState = document.getElementById("vhOptionsState");
    dom.planMeta = document.getElementById("vhPlanMeta");
    dom.planLockState = document.getElementById("vhPlanLockState");
    dom.planStatusInline = document.getElementById("vhPlanStatusInline");
    dom.tasklistHintInline = document.getElementById("vhTasklistHintInline");
    dom.stepPlan = document.getElementById("vhStepPlan");
    dom.stepItem = document.getElementById("vhStepItem");
    dom.stepTasklist = document.getElementById("vhStepTasklist");
    dom.stepOperations = document.getElementById("vhStepOperations");
    dom.stepDispatch = document.getElementById("vhStepDispatch");

    dom.planPlant = document.getElementById("planPlant");
    dom.planStatus = document.getElementById("planStatus");
    dom.planText = document.getElementById("planText");
    dom.planSortField = document.getElementById("planSortField");
    dom.planCycle = document.getElementById("planCycle");
    dom.planUnit = document.getElementById("planUnit");
    dom.planCallHorizon = document.getElementById("planCallHorizon");
    dom.planSchedulingIndicator = document.getElementById("planSchedulingIndicator");
    dom.planFirstCallDay = document.getElementById("planFirstCallDay");
    dom.planFirstCallMonth = document.getElementById("planFirstCallMonth");
    dom.planFirstCallYear = document.getElementById("planFirstCallYear");
    dom.planStatutorySortField = document.getElementById("planStatutorySortField");

    dom.btnProxy = document.getElementById("btnVhProxy");
    dom.btnCommitPlan = document.getElementById("btnCommitVhPlan");
    dom.btnVerifyFl = document.getElementById("btnVhVerifyFl");
    dom.btnAddItem = document.getElementById("btnAddVhItem");
    dom.btnCopyItem = document.getElementById("btnCopyVhItem");
    dom.btnRemoveItem = document.getElementById("btnRemoveVhItem");
    dom.btnSaveItem = document.getElementById("btnSaveVhItem");
    dom.itemMeta = document.getElementById("vhItemMeta");
    dom.btnValidate = document.getElementById("btnValidateVh");
    dom.btnExport = document.getElementById("btnExportVh");
    dom.btnSendEmail = document.getElementById("btnSendEmailVh");
    dom.btnApplyTasklist = document.getElementById("btnApplyTasklist");
    dom.btnAddTasklistLines = document.getElementById("btnAddTasklistLines");
    dom.btnAddOperation = document.getElementById("btnAddOperation");
    dom.btnRemoveOperation = document.getElementById("btnRemoveOperation");

    dom.itemsRail = document.getElementById("vhItemsRail");

    dom.itemShortText = document.getElementById("itemShortText");
    dom.itemMainWorkCenter = document.getElementById("itemMainWorkCenter");
    dom.itemActivityType = document.getElementById("itemActivityType");
    dom.itemFunctionalLocation = document.getElementById("itemFunctionalLocation");
    dom.itemObjectList = document.getElementById("itemObjectList");
    dom.itemRevision = document.getElementById("itemRevision");
    dom.itemLongText = document.getElementById("itemLongText");
    dom.itemOrstedResponsible = document.getElementById("itemOrstedResponsible");
    dom.itemInitials = document.getElementById("itemInitials");
    dom.itemTasklistSelect = document.getElementById("itemTasklistSelect");

    dom.itemFlMeta = document.getElementById("vhFlMeta");
    dom.itemFlDescription = document.getElementById("vhFlDescription");
    dom.itemFlSuggestions = document.getElementById("vhFlSuggestions");

    dom.tasklistMeta = document.getElementById("vhTasklistMeta");
    dom.operationsBody = document.getElementById("vhOperationsBody");

    dom.tasklistPickerModal = document.getElementById("vhTasklistPickerModal");
    dom.tasklistPickerSearch = document.getElementById("vhTasklistPickerSearch");
    dom.tasklistPickerSelectAll = document.getElementById("vhTasklistPickerSelectAll");
    dom.tasklistPickerInfo = document.getElementById("vhTasklistPickerInfo");
    dom.tasklistPickerBody = document.getElementById("vhTasklistPickerBody");
    dom.btnTasklistPickerClose = document.getElementById("btnTasklistPickerClose");
    dom.btnTasklistPickerCancel = document.getElementById("btnTasklistPickerCancel");
    dom.btnTasklistPickerAddSelected = document.getElementById("btnTasklistPickerAddSelected");
  }

  function bindEvents() {
    if (dom.btnProxy) {
      dom.btnProxy.addEventListener("click", () => {
        state.net.useLocalProxy = !state.net.useLocalProxy;
        updateProxyButton();
        setRuntime(state.net.useLocalProxy ? "Proxy ON" : "Proxy OFF");
      });
    }

    dom.btnCommitPlan.addEventListener("click", onPlanPrimaryAction);
    dom.btnSaveItem.addEventListener("click", onItemPrimaryAction);

    dom.btnVerifyFl.addEventListener("click", () => {
      lookupExactFlForActiveItem();
    });

    dom.btnAddItem.addEventListener("click", () => {
      addItem();
    });

    if (dom.btnCopyItem) {
      dom.btnCopyItem.addEventListener("click", () => {
        copyActiveItem();
      });
    }

    dom.btnRemoveItem.addEventListener("click", () => {
      removeActiveItem();
    });

    dom.btnValidate.addEventListener("click", () => {
      validatePlanAndItems();
    });

    dom.btnExport.addEventListener("click", exportPayload);

    if (dom.btnSendEmail) {
      dom.btnSendEmail.addEventListener("click", sendPayloadAsEmail);
    }

    dom.btnApplyTasklist.addEventListener("click", applySelectedTasklistToActiveItem);
    dom.btnAddTasklistLines.addEventListener("click", openTasklistPickerModal);
    dom.btnAddOperation.addEventListener("click", addOperationToActiveItem);
    dom.btnRemoveOperation.addEventListener("click", removeSelectedOperationFromActiveItem);

    dom.btnTasklistPickerClose.addEventListener("click", closeTasklistPickerModal);
    dom.btnTasklistPickerCancel.addEventListener("click", closeTasklistPickerModal);
    dom.btnTasklistPickerAddSelected.addEventListener("click", addSelectedTasklistLinesToActiveItem);

    dom.tasklistPickerModal.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.hasAttribute("data-modal-close")) {
        closeTasklistPickerModal();
      }
    });

    dom.tasklistPickerSearch.addEventListener("input", () => {
      state.tasklistPicker.filter = toText(dom.tasklistPickerSearch.value);
      renderTasklistPickerRows();
    });

    dom.tasklistPickerSelectAll.addEventListener("change", () => {
      const shouldSelect = !!dom.tasklistPickerSelectAll.checked;
      state.tasklistPicker.visibleIndices.forEach((index) => {
        const key = String(index);
        if (shouldSelect) {
          state.tasklistPicker.selectedIndices.add(key);
        } else {
          state.tasklistPicker.selectedIndices.delete(key);
        }
      });
      renderTasklistPickerRows();
    });

    dom.tasklistPickerBody.addEventListener("change", onTasklistPickerRowToggle);
    dom.tasklistPickerBody.addEventListener("click", onTasklistPickerRowClick);

    document.addEventListener("keydown", (event) => {
      if (!state.tasklistPicker.open) return;
      if (event.key === "Escape") {
        closeTasklistPickerModal();
      }
    });

    dom.itemTasklistSelect.addEventListener("change", () => {
      const item = getActiveItem();
      renderTasklistMeta(item, true);
    });

    dom.itemsRail.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;

      const card = target.closest("[data-item-id]");
      if (!card) return;

      const itemId = Number(card.getAttribute("data-item-id"));
      if (!Number.isFinite(itemId)) return;

      persistEditorToActiveItem();
      closeTasklistPickerModal();
      state.activeItemId = itemId;
      state.activeOperationIndex = -1;
      renderItemRail();
      loadActiveItemIntoEditor();
      renderTasklistControls();
      applyPlanInteractionState();
    });

    getPlanInputs().forEach((input) => {
      input.addEventListener("input", () => {
        persistPlanFromForm();
        updatePlanSaveButtonState();
      });
      input.addEventListener("change", () => {
        persistPlanFromForm();
        updatePlanSaveButtonState();
      });
    });

    dom.planPlant.addEventListener("change", () => {
      applyPlantPrefixToPlanText();
      persistPlanFromForm();
      updatePlanSaveButtonState();
      closeTasklistPickerModal();
      renderTasklistControls();
      if (state.planCommitted && !state.planLocked) {
        setRuntime("Plant changed in edit mode. Save the plan again to apply tasklist rebinding.");
      }
    });

    getItemInputs().forEach((input) => {
      input.addEventListener("input", () => {
        if (input === dom.itemFunctionalLocation) {
          upperCaseFlInputInPlace();
          queueFlSuggestions(input.value);
        }

        persistEditorToActiveItem();
        renderItemRail();
        updateItemSaveButtonState();
      });

      input.addEventListener("change", () => {
        persistEditorToActiveItem();
        updateItemSaveButtonState();
      });
    });

    dom.itemFunctionalLocation.addEventListener("keydown", onFlKeyDown);
    dom.itemFunctionalLocation.addEventListener("blur", () => {
      persistEditorToActiveItem();
      const item = getActiveItem();
      if (item) {
        dom.itemFunctionalLocation.value = item.functionalLocation;
      }
      setTimeout(hideFlSuggestions, 110);
      lookupExactFlForActiveItem();
    });

    dom.itemFunctionalLocation.addEventListener("focus", () => {
      queueFlSuggestions(dom.itemFunctionalLocation.value);
    });

    dom.operationsBody.addEventListener("click", onOperationTableClick);
    dom.operationsBody.addEventListener("input", onOperationTableInput);
    dom.operationsBody.addEventListener("change", onOperationTableChange);
  }

  function getPlanInputs() {
    return [
      dom.planPlant,
      dom.planStatus,
      dom.planText,
      dom.planSortField,
      dom.planCycle,
      dom.planUnit,
      dom.planCallHorizon,
      dom.planSchedulingIndicator,
      dom.planFirstCallDay,
      dom.planFirstCallMonth,
      dom.planFirstCallYear,
      dom.planStatutorySortField,
    ];
  }

  function getPlantCodes() {
    if (!dom.planPlant) return [];
    return Array.from(dom.planPlant.options)
      .map((option) => toText(option.value).toUpperCase())
      .filter(Boolean);
  }

  function applyPlantPrefixToPlanText() {
    const plant = toText(dom.planPlant.value).toUpperCase();
    if (!plant) return;

    let rest = toText(dom.planText.value);
    const restUpper = rest.toUpperCase();
    const previous = getPlantCodes().find((code) => restUpper === code || restUpper.startsWith(`${code} `));
    if (previous) {
      rest = rest.slice(previous.length).replace(/^\s+/, "");
    }

    dom.planText.value = `${plant} ${rest}`.slice(0, 40);
    state.plan.planText = dom.planText.value;
  }

  function updatePlanSaveButtonState() {
    if (!dom.btnCommitPlan) return;

    const isLockedPlan = state.planCommitted && state.planLocked;
    dom.btnCommitPlan.textContent = isLockedPlan ? "Edit" : "Save";
    dom.btnCommitPlan.disabled = !isLockedPlan && collectPlanIssues(state.plan).length > 0;
  }

  function onPlanPrimaryAction() {
    if (!state.planCommitted) {
      commitPlanAndCreateFirstItem();
      return;
    }

    togglePlanEditState();
  }

  function collectItemHeaderIssues(item) {
    const issues = [];
    if (!item) return ["No active item."];

    if (!toText(item.shortText)) {
      issues.push("Item short text is required.");
    } else if (toText(item.shortText).length > 40) {
      issues.push("Item short text exceeds 40 characters.");
    }

    if (!toText(item.mainWorkCenter)) {
      issues.push("Main Work Center is required.");
    }

    if (!toText(item.activityType)) {
      issues.push("Maintenance Activity Type is required.");
    }

    if (!toText(item.functionalLocation)) {
      issues.push("Functional Location is required.");
    }

    return issues;
  }

  function updateItemSaveButtonState() {
    if (!dom.btnSaveItem) return;

    const item = getActiveItem();
    const isLockedItem = !!(item && item.committed && item.locked);

    dom.btnSaveItem.textContent = isLockedItem ? "Edit" : "Save";
    dom.btnSaveItem.disabled = !state.planCommitted || !item || (!isLockedItem && collectItemHeaderIssues(item).length > 0);

    if (dom.itemMeta) {
      dom.itemMeta.className = "inline-helper";
      if (!item) {
        dom.itemMeta.textContent = "";
      } else if (isLockedItem) {
        dom.itemMeta.textContent = "Item saved. Click Edit to change item fields.";
        dom.itemMeta.classList.add("ok");
      } else {
        dom.itemMeta.textContent = "";
      }
    }
  }

  function onItemPrimaryAction() {
    const item = getActiveItem();
    if (!item) {
      setRuntime("Select an item first.");
      return;
    }

    if (item.committed && item.locked) {
      item.locked = false;
      applyPlanInteractionState();
      renderItemRail();
      setRuntime("Item unlocked for editing.");
      return;
    }

    persistEditorToActiveItem();

    const issues = collectItemHeaderIssues(item);
    if (issues.length) {
      if (dom.itemMeta) {
        dom.itemMeta.textContent = issues[0];
        dom.itemMeta.className = "inline-helper error";
      }
      setRuntime("Item contains issues. Fix item fields before saving.");
      return;
    }

    item.committed = true;
    item.locked = true;

    applyPlanInteractionState();
    renderItemRail();
    setRuntime("Item saved. Continue with tasklist and operations.");
  }

  function getItemInputs() {
    return [
      dom.itemShortText,
      dom.itemMainWorkCenter,
      dom.itemActivityType,
      dom.itemFunctionalLocation,
      dom.itemObjectList,
      dom.itemRevision,
      dom.itemLongText,
      dom.itemOrstedResponsible,
      dom.itemInitials,
    ];
  }

  async function loadOptions() {
    const fallbackPlants = ["ASV", "AVV", "HEV", "HCV", "KYV", "SKV", "SMV", "SSV"];

    try {
      const payload = await resolveVhOptionsPayload();
      state.options = payload.options || {};
      state.optionsLoaded = true;

      populateSelect(dom.planPlant, fallbackPlants, state.plan.plant);
      populateSelect(dom.planStatus, state.options.Status || ["New", "Draft", "Delete"], "New");
      populateSelect(dom.planUnit, state.options.Unit || ["DAY", "WK", "MON", "YR", "H", "COUNT"], "");
      populateSelect(dom.planSortField, state.options["Sort field"] || [], "");
      populateSelect(dom.planCallHorizon, state.options["Call Horizon"] || [], "");

      populateSelect(dom.itemMainWorkCenter, state.options["Main Work Center - Item"] || [], "");
      populateSelect(dom.itemActivityType, state.options["Maintenance activity type"] || [], "");
      populateSelect(dom.itemRevision, state.options.Revision || ["REV - General"], "");

      dom.optionsState.textContent = "";
      dom.optionsState.className = "inline-helper";
    } catch (error) {
      state.optionsLoaded = false;

      populateSelect(dom.planPlant, fallbackPlants, state.plan.plant);
      populateSelect(dom.planStatus, ["New", "Draft", "Published"], "New");
      populateSelect(dom.planUnit, ["DAY", "WK", "MON", "YR", "H", "COUNT"], "");
      populateSelect(dom.planSortField, ["Regulatory Requirements", "Safety Valves", "Inspection"], "");
      populateSelect(dom.planCallHorizon, ["2 Days", "7 Days", "15 Days"], "");
      populateSelect(dom.itemMainWorkCenter, ["HEVSERVM", "SUPERVISOR"], "");
      populateSelect(dom.itemActivityType, ["110 - Statutory inspection", "102 - Predetermined maintenance"], "");
      populateSelect(dom.itemRevision, ["REV - General Revision Mark"], "");

      dom.optionsState.textContent = "Dropdown data could not be loaded. Fallback values are in use.";
      dom.optionsState.className = "inline-helper warn";
    }

    syncPlanToForm();
  }

  async function loadTasklists() {
    try {
      const payload = await resolveTasklistPayload();
      const plants = payload && typeof payload === "object" ? payload.plants || {} : {};

      state.tasklists = plants;
      state.tasklistsLoaded = Object.keys(plants).length > 0;
      state.tasklistSource = toText(payload && payload.source) || "n/a";
      state.tasklistVersion = toText(payload && payload.version) || "";

      if (state.tasklistsLoaded) {
        setTasklistMeta(`Tasklists loaded from ${state.tasklistSource}.`, "ok");
      } else {
        setTasklistMeta("Tasklists not available. Use custom operations.", "warn");
      }
    } catch (error) {
      state.tasklistsLoaded = false;
      state.tasklists = {};
      state.tasklistSource = "n/a";
      setTasklistMeta("Tasklists not available. Use custom operations.", "warn");
    }

    renderTasklistControls();
  }

  async function resolveVhOptionsPayload() {
    if (window.VH_PLAN_OPTIONS_DATA && typeof window.VH_PLAN_OPTIONS_DATA === "object") {
      return window.VH_PLAN_OPTIONS_DATA;
    }

    const response = await fetch("js/data/vh-plan-options.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  async function resolveTasklistPayload() {
    if (window.VH_TASKLIST_DATA && typeof window.VH_TASKLIST_DATA === "object") {
      return window.VH_TASKLIST_DATA;
    }

    const response = await fetch("js/data/vh-tasklist-data.json", { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  function populateSelect(select, options, currentValue) {
    if (!select) return;

    const normalizedOptions = Array.isArray(options)
      ? options.map((value) => toText(value)).filter(Boolean)
      : [];

    select.innerHTML = "";

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "Select";
    select.appendChild(emptyOption);

    normalizedOptions.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });

    if (currentValue && normalizedOptions.includes(currentValue)) {
      select.value = currentValue;
    }

    syncStyledSelect(select);
  }

  function setupStyledSelects() {
    const selects = [
      dom.planPlant,
      dom.planStatus,
      dom.planSortField,
      dom.planUnit,
      dom.planCallHorizon,
      dom.itemMainWorkCenter,
      dom.itemActivityType,
      dom.itemRevision,
      dom.itemTasklistSelect,
    ].filter(Boolean);

    selects.forEach((select) => {
      if (select.dataset.vhStyled === "1") return;
      enhanceSelect(select);
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;

      state.styledSelects.forEach((entry) => {
        if (!entry.wrapper.contains(target)) {
          closeStyledSelect(entry);
        }
      });
    });
  }

  function enhanceSelect(select) {
    const wrapper = document.createElement("div");
    wrapper.className = "vh-select-wrap";

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "vh-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");

    const panel = document.createElement("div");
    panel.className = "combo-panel-lite vh-select-panel";
    panel.hidden = true;

    const parent = select.parentElement;
    if (!parent) return;

    parent.insertBefore(wrapper, select);
    wrapper.appendChild(select);
    wrapper.appendChild(trigger);
    wrapper.appendChild(panel);

    select.dataset.vhStyled = "1";
    select.classList.add("vh-select-native");

    const entry = { select, wrapper, trigger, panel };
    state.styledSelects.push(entry);

    trigger.addEventListener("click", () => {
      if (entry.select.disabled) {
        return;
      }

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

    select.addEventListener("change", () => syncStyledSelect(select));
    syncStyledSelect(select);
  }

  function renderStyledSelectOptions(entry) {
    entry.panel.innerHTML = "";

    const options = Array.from(entry.select.options || []);
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "combo-option";
      btn.textContent = opt.textContent || opt.value || "";

      if (opt.value === entry.select.value) {
        btn.classList.add("active");
      }

      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        entry.select.value = opt.value;
        entry.select.dispatchEvent(new Event("input", { bubbles: true }));
        entry.select.dispatchEvent(new Event("change", { bubbles: true }));
        closeStyledSelect(entry);
      });

      entry.panel.appendChild(btn);
    });
  }

  function closeStyledSelect(entry) {
    entry.panel.hidden = true;
    entry.trigger.setAttribute("aria-expanded", "false");
    entry.wrapper.classList.remove("open");
  }

  function syncStyledSelect(select) {
    const entry = state.styledSelects.find((x) => x.select === select);
    if (!entry) return;

    const selectedOption = select.options[select.selectedIndex];
    const text = selectedOption ? selectedOption.textContent || "" : "Select";
    entry.trigger.textContent = text || "Select";
    entry.trigger.disabled = !!select.disabled;
    entry.wrapper.classList.toggle("is-disabled", !!select.disabled);
  }

  function commitPlanAndCreateFirstItem() {
    persistPlanFromForm();
    const planIssues = validatePlan();

    if (planIssues.length > 0) {
      setRuntime("Plan contains issues. Fix plan fields before creating items.");
      return;
    }

    if (!state.planCommitted) {
      const created = createEmptyItem();
      state.items.push(created);
      state.activeItemId = created.id;
      state.activeOperationIndex = created.operations.length ? 0 : -1;
      state.planCommitted = true;
      state.lastCommittedPlant = state.plan.plant;
    }

    state.planLocked = true;
    applyPlanInteractionState();
    renderItemRail();
    loadActiveItemIntoEditor();
    renderTasklistControls();
    setRuntime("Plan saved. Fill in the item fields and save the item.");
  }

  function togglePlanEditState() {
    if (!state.planCommitted) return;

    if (state.planLocked) {
      state.planLocked = false;
      applyPlanInteractionState();
      setRuntime("Plan unlocked for editing.");
      return;
    }

    persistPlanFromForm();
    const planIssues = validatePlan();
    if (planIssues.length > 0) {
      setRuntime("Plan still has issues. Fix them before locking again.");
      return;
    }

    const previousPlant = toText(state.lastCommittedPlant);
    const nextPlant = toText(state.plan.plant);

    if (previousPlant && nextPlant && previousPlant !== nextPlant && state.items.length) {
      const proceed = window.confirm(
        `Plant changed from ${previousPlant} to ${nextPlant}. This will rebind tasklists and reset operations on all items. Continue?`
      );

      if (!proceed) {
        state.plan.plant = previousPlant;
        syncPlanToForm();
        renderTasklistControls();
        setRuntime("Plant change canceled.");
        return;
      }

      rebindAllItemsToPlant(nextPlant);
    }

    state.lastCommittedPlant = state.plan.plant;
    state.planLocked = true;
    applyPlanInteractionState();
    renderItemRail();
    loadActiveItemIntoEditor();
    renderTasklistControls();
    setRuntime("Plan locked.");
  }

  function rebindAllItemsToPlant(plantCode) {
    const defaultTasklist = getDefaultTasklistForPlant(plantCode);
    state.items.forEach((item) => {
      if (defaultTasklist) {
        applyTasklistToItem(item, defaultTasklist, { replaceOperations: false, markDraft: true });
        item.operations = [];
      } else {
        item.tasklistKey = "";
        item.tasklistName = "";
        item.taskListGroup = "";
        item.operations = [];
        markItemAsDraft(item);
      }
    });
    state.activeOperationIndex = -1;
  }

  function applyPlanInteractionState() {
    const activeItem = getActiveItem();
    const hasActiveItem = !!activeItem;
    const canWorkOnItems = state.planCommitted;
    const hasTasklistBound = !!(activeItem && toText(activeItem.tasklistKey));
    const hasOperations = !!(activeItem && activeItem.operations.length);

    setElementsDisabled(getPlanInputs(), state.planLocked);

    updatePlanSaveButtonState();

    dom.btnAddItem.disabled = !canWorkOnItems;
    if (dom.btnCopyItem) {
      dom.btnCopyItem.disabled = !canWorkOnItems || !hasActiveItem;
    }
    dom.btnRemoveItem.disabled = !canWorkOnItems || !hasActiveItem;

    const itemLocked = !!(activeItem && activeItem.committed && activeItem.locked);
    setElementsDisabled(getItemInputs(), !canWorkOnItems || !hasActiveItem || itemLocked);
    dom.btnVerifyFl.disabled = !canWorkOnItems || !hasActiveItem || itemLocked;
    updateItemSaveButtonState();

    dom.btnValidate.disabled = state.validationRunning || !state.planCommitted;
    dom.btnExport.disabled = !state.planCommitted;
    if (dom.btnSendEmail) {
      dom.btnSendEmail.disabled = !state.planCommitted;
    }

    const tasklistDisabled = !canWorkOnItems || !hasActiveItem;
    dom.itemTasklistSelect.disabled = tasklistDisabled;
    dom.btnApplyTasklist.disabled = tasklistDisabled;
    dom.btnAddTasklistLines.disabled = tasklistDisabled || !hasTasklistBound;
    dom.btnAddOperation.disabled = tasklistDisabled || !hasTasklistBound;
    dom.btnRemoveOperation.disabled = tasklistDisabled || !hasOperations;

    if (tasklistDisabled && state.tasklistPicker.open) {
      closeTasklistPickerModal();
    }

    refreshActionLabels(activeItem, hasTasklistBound, hasOperations);

    state.styledSelects.forEach((entry) => {
      syncStyledSelect(entry.select);
    });

    if (!state.planCommitted) {
      setPlanLockState("Plan is in draft mode. Complete plan header first.", "warn");
      if (dom.planStatusInline) {
        dom.planStatusInline.textContent = "Create plan to unlock item and tasklist workflow.";
      }
      if (dom.tasklistHintInline) {
        dom.tasklistHintInline.textContent = "Tasklist is linked per item and available after plan creation.";
      }
      refreshObjectPageState();
      return;
    }

    if (state.planLocked) {
      setPlanLockState("Plan is locked. Click Edit to adjust header fields.", "ok");
      if (dom.planStatusInline) {
        dom.planStatusInline.textContent = "Plan header locked. Item and operations are editable.";
      }
    } else {
      setPlanLockState("Plan is unlocked for edit. Lock again to finalize plant/tasklist context.", "warn");
      if (dom.planStatusInline) {
        dom.planStatusInline.textContent = "Edit mode active. Changing plant may rebind all item tasklists on lock.";
      }
    }

    refreshObjectPageState();
  }

  function refreshActionLabels(activeItem, hasTasklistBound, hasOperations) {
    const activeStep = getCurrentProcessStep();
    const selectedTasklistKey = toText(dom.itemTasklistSelect ? dom.itemTasklistSelect.value : "");

    if (dom.btnApplyTasklist) {
      if (!activeItem) {
        dom.btnApplyTasklist.textContent = "Apply tasklist";
      } else if (!hasTasklistBound) {
        dom.btnApplyTasklist.textContent = "Apply tasklist";
      } else if (selectedTasklistKey && selectedTasklistKey !== toText(activeItem.tasklistKey)) {
        dom.btnApplyTasklist.textContent = "Switch tasklist";
      } else {
        dom.btnApplyTasklist.textContent = "Tasklist linked";
      }
    }

    if (dom.btnAddTasklistLines) {
      if (!activeItem) {
        dom.btnAddTasklistLines.textContent = "Add lines from tasklist";
      } else if (!hasTasklistBound) {
        dom.btnAddTasklistLines.textContent = "Apply tasklist first";
      } else if (!hasOperations) {
        dom.btnAddTasklistLines.textContent = "Add first lines";
      } else {
        dom.btnAddTasklistLines.textContent = "Add more lines";
      }
    }

    if (dom.btnAddOperation) {
      if (!activeItem) {
        dom.btnAddOperation.textContent = "Add manual operation";
      } else if (!hasTasklistBound) {
        dom.btnAddOperation.textContent = "Apply tasklist first";
      } else if (!hasOperations) {
        dom.btnAddOperation.textContent = "Add first manual operation";
      } else {
        dom.btnAddOperation.textContent = "Add manual operation";
      }
    }

    if (dom.btnRemoveOperation) {
      if (!activeItem) {
        dom.btnRemoveOperation.textContent = "Remove selected operation";
      } else if (!hasOperations) {
        dom.btnRemoveOperation.textContent = "No operation selected";
      } else {
        dom.btnRemoveOperation.textContent = "Remove selected operation";
      }
    }

    if (dom.btnValidate && !state.validationRunning) {
      if (!state.planCommitted) {
        dom.btnValidate.textContent = "Validate";
      } else {
        dom.btnValidate.textContent = activeStep >= 5 ? "Validate for dispatch" : "Validate draft";
      }
    }

    if (dom.btnExport) {
      const itemCount = state.items.length;
      dom.btnExport.textContent = state.planCommitted
        ? `Export JSON (${itemCount} item${itemCount === 1 ? "" : "s"})`
        : "Export JSON";
    }

    if (dom.btnSendEmail) {
      dom.btnSendEmail.textContent = activeStep >= 5 ? "Send as email" : "Send as email (draft)";
    }
  }

  function refreshObjectPageState() {
    const activeStep = getCurrentProcessStep();
    setProcessStepState(dom.stepPlan, 1, activeStep);
    setProcessStepState(dom.stepItem, 2, activeStep);
    setProcessStepState(dom.stepTasklist, 3, activeStep);
    setProcessStepState(dom.stepOperations, 4, activeStep);
    setProcessStepState(dom.stepDispatch, 5, activeStep);
  }

  function getCurrentProcessStep() {
    if (!state.planCommitted) {
      return 1;
    }

    const activeItem = getActiveItem();
    if (!activeItem || !activeItem.committed || !activeItem.locked) {
      return 2;
    }

    if (!toText(activeItem.tasklistKey)) {
      return 3;
    }

    if (!activeItem.operations.length) {
      return 4;
    }

    return 5;
  }

  function setProcessStepState(node, stepNumber, activeStep) {
    if (!node) return;

    node.classList.remove("done", "active", "upcoming");
    node.removeAttribute("aria-current");

    if (stepNumber < activeStep) {
      node.classList.add("done");
      return;
    }

    if (stepNumber === activeStep) {
      node.classList.add("active");
      node.setAttribute("aria-current", "step");
      return;
    }

    node.classList.add("upcoming");
  }

  function setPlanLockState(text, mode) {
    if (!dom.planLockState) return;
    dom.planLockState.textContent = text;
    dom.planLockState.className = "inline-helper";
    if (mode) {
      dom.planLockState.classList.add(mode);
    }
  }

  function setElementsDisabled(elements, disabled) {
    elements.forEach((element) => {
      if (!element) return;
      element.disabled = !!disabled;
      syncStyledSelect(element);
    });
  }

  function createEmptyItem() {
    const item = {
      id: state.nextItemId,
      shortText: "",
      mainWorkCenter: "",
      activityType: "",
      functionalLocation: "",
      flDescription: "",
      objectList: "",
      taskListGroup: "",
      tasklistKey: "",
      tasklistName: "",
      revision: "",
      longText: "",
      orstedResponsible: "",
      initials: "",
      operations: [],
      status: "draft",
      committed: false,
      locked: false,
      issues: [],
      warnings: [],
    };

    state.nextItemId += 1;

    const defaultTasklist = getDefaultTasklistForPlant(state.plan.plant);
    if (defaultTasklist) {
      applyTasklistToItem(item, defaultTasklist, { replaceOperations: false, markDraft: false });
    }

    return item;
  }

  function addItem() {
    if (!state.planCommitted) {
      setRuntime("Create plan first before adding items.");
      return;
    }

    persistEditorToActiveItem();
    closeTasklistPickerModal();

    const item = createEmptyItem();
    state.items.push(item);
    state.activeItemId = item.id;
    state.activeOperationIndex = item.operations.length ? 0 : -1;

    renderItemRail();
    loadActiveItemIntoEditor();
    renderTasklistControls();
    applyPlanInteractionState();
    setRuntime(`Item ${state.items.length} created.`);
  }

  function copyActiveItem() {
    if (!state.planCommitted) {
      setRuntime("Create plan first before copying items.");
      return;
    }

    persistEditorToActiveItem();
    closeTasklistPickerModal();

    const source = getActiveItem();
    if (!source) {
      setRuntime("Select an item to copy.");
      return;
    }

    const copied = createCopiedItem(source);
    const sourceIndex = state.items.findIndex((item) => item.id === source.id);

    if (sourceIndex >= 0) {
      state.items.splice(sourceIndex + 1, 0, copied);
    } else {
      state.items.push(copied);
    }

    state.activeItemId = copied.id;
    state.activeOperationIndex = copied.operations.length ? 0 : -1;

    renderItemRail();
    loadActiveItemIntoEditor();
    renderTasklistControls();
    applyPlanInteractionState();
    setRuntime("Item copied. Functional Location cleared on copied item.");
  }

  function createCopiedItem(sourceItem) {
    const item = {
      id: state.nextItemId,
      shortText: toText(sourceItem.shortText),
      mainWorkCenter: toText(sourceItem.mainWorkCenter),
      activityType: toText(sourceItem.activityType),
      functionalLocation: "",
      flDescription: "",
      objectList: toText(sourceItem.objectList),
      taskListGroup: toText(sourceItem.taskListGroup),
      tasklistKey: toText(sourceItem.tasklistKey),
      tasklistName: toText(sourceItem.tasklistName),
      revision: toText(sourceItem.revision),
      longText: toText(sourceItem.longText),
      orstedResponsible: toText(sourceItem.orstedResponsible),
      initials: toText(sourceItem.initials),
      operations: Array.isArray(sourceItem.operations)
        ? sourceItem.operations.map((operation) => ({
          operationNo: normalizeOperationNo(toText(operation.operationNo), true),
          operationShortText: toText(operation.operationShortText),
          workHours: toText(operation.workHours),
          durationHours: toText(operation.durationHours),
          mainWorkCenter: toText(operation.mainWorkCenter),
          vendor: toText(operation.vendor),
          longText: toText(operation.longText),
          controlKey: toText(operation.controlKey),
        }))
        : [],
      status: "draft",
      committed: false,
      locked: false,
      issues: [],
      warnings: [],
    };

    state.nextItemId += 1;
    return item;
  }

  function removeActiveItem() {
    if (!state.planCommitted) return;
    if (!state.items.length) return;

    const active = getActiveItem();
    if (!active) return;

    closeTasklistPickerModal();

    state.items = state.items.filter((item) => item.id !== active.id);
    state.activeItemId = state.items.length ? state.items[0].id : null;
    state.activeOperationIndex = -1;

    renderItemRail();
    loadActiveItemIntoEditor();
    renderTasklistControls();
    applyPlanInteractionState();
    setRuntime("Active item removed.");
  }

  function getActiveItem() {
    return state.items.find((item) => item.id === state.activeItemId) || null;
  }

  function renderItemRail() {
    dom.itemsRail.innerHTML = "";

    if (!state.items.length) {
      const empty = document.createElement("div");
      empty.className = "items-rail-empty";
      empty.textContent = "No items yet. Create plan first, then add items.";
      dom.itemsRail.appendChild(empty);
      return;
    }

    state.items.forEach((item, index) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "item-card";
      if (item.id === state.activeItemId) card.classList.add("active");
      card.setAttribute("data-item-id", String(item.id));

      const title = item.shortText || `Item ${index + 1}`;
      const fl = item.functionalLocation || "No FL";
      const tasklistLabel = item.tasklistName || "No tasklist";
      const opCount = item.operations.length;
      const isSavedDraft = item.status === "draft" && item.committed && item.locked;
      const statusClass = isSavedDraft ? "saved" : item.status;
      const status = (isSavedDraft ? "saved" : item.status).toUpperCase();

      card.innerHTML = `
        <div class="title">${escapeHtml(title)}</div>
        <div class="sub">${escapeHtml(fl)}</div>
        <div class="sub">${escapeHtml(tasklistLabel)} | Ops: ${opCount}</div>
        <div class="sub"><span class="status-chip ${statusClass}">${escapeHtml(status)}</span></div>
      `;

      dom.itemsRail.appendChild(card);
    });
  }

  function loadActiveItemIntoEditor() {
    const item = getActiveItem();
    if (!item) {
      clearItemEditor();
      applyPlanInteractionState();
      return;
    }

    dom.itemShortText.value = item.shortText;
    dom.itemMainWorkCenter.value = item.mainWorkCenter;
    dom.itemActivityType.value = item.activityType;
    dom.itemFunctionalLocation.value = item.functionalLocation;
    dom.itemObjectList.value = item.objectList;
    dom.itemRevision.value = item.revision;
    dom.itemLongText.value = item.longText;
    dom.itemOrstedResponsible.value = item.orstedResponsible;
    dom.itemInitials.value = item.initials;

    setFlMeta(item.flDescription || "", item.flDescription ? "ok" : "");
    setFlDescription(item.flDescription || "");

    syncStyledSelect(dom.itemMainWorkCenter);
    syncStyledSelect(dom.itemActivityType);
    syncStyledSelect(dom.itemRevision);

    applyPlanInteractionState();
  }

  function clearItemEditor() {
    dom.itemShortText.value = "";
    dom.itemMainWorkCenter.value = "";
    dom.itemActivityType.value = "";
    dom.itemFunctionalLocation.value = "";
    dom.itemObjectList.value = "";
    dom.itemRevision.value = "";
    dom.itemLongText.value = "";
    dom.itemOrstedResponsible.value = "";
    dom.itemInitials.value = "";
    setFlMeta("", "");
    setFlDescription("");

    syncStyledSelect(dom.itemMainWorkCenter);
    syncStyledSelect(dom.itemActivityType);
    syncStyledSelect(dom.itemRevision);
  }

  function persistEditorToActiveItem() {
    const item = getActiveItem();
    if (!item) return;

    const previousFl = item.functionalLocation;

    item.shortText = toText(dom.itemShortText.value);
    item.mainWorkCenter = toText(dom.itemMainWorkCenter.value);
    item.activityType = toText(dom.itemActivityType.value);
    item.functionalLocation = normalizeFunctionalLocation(dom.itemFunctionalLocation.value);

    if (item.functionalLocation !== previousFl) {
      item.flDescription = "";
      setFlDescription("");
      setFlMeta("", "");
    }

    item.objectList = toText(dom.itemObjectList.value);
    item.revision = toText(dom.itemRevision.value);
    item.longText = toText(dom.itemLongText.value);
    item.orstedResponsible = toText(dom.itemOrstedResponsible.value);
    item.initials = toText(dom.itemInitials.value);

    markItemAsDraft(item);
  }

  function markItemAsDraft(item) {
    item.status = "draft";
    item.issues = [];
    item.warnings = [];
  }

  function persistPlanFromForm() {
    state.plan.plant = toText(dom.planPlant.value);
    state.plan.status = toText(dom.planStatus.value);
    state.plan.planText = toText(dom.planText.value);
    state.plan.sortField = toText(dom.planSortField.value);
    state.plan.cycle = toText(dom.planCycle.value);
    state.plan.unit = toText(dom.planUnit.value);
    state.plan.callHorizon = toText(dom.planCallHorizon.value);
    state.plan.schedulingIndicator = toText(dom.planSchedulingIndicator.value);
    state.plan.firstCallDay = toText(dom.planFirstCallDay.value);
    state.plan.firstCallMonth = toText(dom.planFirstCallMonth.value);
    state.plan.firstCallYear = toText(dom.planFirstCallYear.value);
    state.plan.statutorySortField = toText(dom.planStatutorySortField.value);
  }

  function syncPlanToForm() {
    dom.planPlant.value = state.plan.plant;
    dom.planStatus.value = state.plan.status;
    dom.planText.value = state.plan.planText;
    dom.planSortField.value = state.plan.sortField;
    dom.planCycle.value = state.plan.cycle;
    dom.planUnit.value = state.plan.unit;
    dom.planCallHorizon.value = state.plan.callHorizon;
    dom.planSchedulingIndicator.value = state.plan.schedulingIndicator;
    dom.planFirstCallDay.value = state.plan.firstCallDay;
    dom.planFirstCallMonth.value = state.plan.firstCallMonth;
    dom.planFirstCallYear.value = state.plan.firstCallYear;
    dom.planStatutorySortField.value = state.plan.statutorySortField;

    syncStyledSelect(dom.planPlant);
    syncStyledSelect(dom.planStatus);
    syncStyledSelect(dom.planSortField);
    syncStyledSelect(dom.planUnit);
    syncStyledSelect(dom.planCallHorizon);
  }

  function renderTasklistControls() {
    const item = getActiveItem();
    const plantTasklists = getTasklistsForPlant(state.plan.plant);

    dom.itemTasklistSelect.innerHTML = "";

    if (!plantTasklists.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No tasklists available";
      dom.itemTasklistSelect.appendChild(option);
      dom.itemTasklistSelect.value = "";
      renderOperationsTable(item);
      renderTasklistMeta(item, false);
      syncStyledSelect(dom.itemTasklistSelect);
      return;
    }

    const selectOption = document.createElement("option");
    selectOption.value = "";
    selectOption.textContent = "Select tasklist";
    dom.itemTasklistSelect.appendChild(selectOption);

    plantTasklists.forEach((tasklist) => {
      const option = document.createElement("option");
      option.value = tasklist.key;
      option.textContent = tasklist.name;
      dom.itemTasklistSelect.appendChild(option);
    });

    if (item && item.tasklistKey && plantTasklists.some((x) => x.key === item.tasklistKey)) {
      dom.itemTasklistSelect.value = item.tasklistKey;
    } else {
      dom.itemTasklistSelect.value = "";
    }

    renderOperationsTable(item);
    renderTasklistMeta(item, false);
    syncStyledSelect(dom.itemTasklistSelect);
  }

  function getTasklistsForPlant(plantCode) {
    const key = toText(plantCode).toUpperCase();
    if (!key || !state.tasklists[key]) return [];
    const tasklists = state.tasklists[key].tasklists;
    return Array.isArray(tasklists) ? tasklists : [];
  }

  function getDefaultTasklistForPlant(plantCode) {
    const tasklists = getTasklistsForPlant(plantCode);
    if (!tasklists.length) return null;

    const preferred = tasklists.find((tasklist) => !tasklist.key.endsWith("-CUSTOM"));
    return preferred || tasklists[0];
  }

  function getTasklistByKey(plantCode, tasklistKey) {
    const key = toText(tasklistKey);
    if (!key) return null;

    const tasklists = getTasklistsForPlant(plantCode);
    return tasklists.find((tasklist) => tasklist.key === key) || null;
  }

  function applySelectedTasklistToActiveItem() {
    const item = getActiveItem();
    if (!item) {
      setRuntime("Select an item before applying tasklist.");
      return;
    }

    const tasklistKey = toText(dom.itemTasklistSelect.value);
    if (!tasklistKey) {
      setRuntime("Select a tasklist first.");
      return;
    }

    const tasklist = getTasklistByKey(state.plan.plant, tasklistKey);
    if (!tasklist) {
      setRuntime("Tasklist not found for selected plant.");
      return;
    }

    if (item.tasklistKey === tasklist.key) {
      setRuntime("Tasklist is already applied on active item.");
      return;
    }

    applyTasklistToItem(item, tasklist, { replaceOperations: false, markDraft: true });
    if (!item.operations.length) {
      state.activeOperationIndex = -1;
    }

    renderTasklistControls();
    renderItemRail();
    applyPlanInteractionState();
    setRuntime(`Tasklist ${tasklist.name} linked. Add lines from tasklist to build operations.`);
  }

  function applyTasklistToItem(item, tasklist, options) {
    const replaceOperations = !!(options && options.replaceOperations);
    const markDraft = !!(options && options.markDraft);

    item.tasklistKey = tasklist.key;
    item.tasklistName = tasklist.name;
    item.taskListGroup = tasklist.key;

    if (replaceOperations) {
      const templates = Array.isArray(tasklist.operations) ? tasklist.operations : [];
      item.operations = templates.map((template) => ({
        operationNo: normalizeOperationNo(toText(template.operationNo), true),
        operationShortText: toText(template.operationShortText),
        workHours: toText(template.workHours),
        durationHours: toText(template.durationHours),
        mainWorkCenter: toText(template.mainWorkCenter) || toText(item.mainWorkCenter),
        vendor: toText(template.vendor),
        longText: toText(template.longText),
        controlKey: toText(template.controlKey),
      }));
    }

    if (!toText(item.mainWorkCenter)) {
      const firstOperation = item.operations.length ? item.operations[0] : null;
      const firstTemplate = Array.isArray(tasklist.operations) && tasklist.operations.length
        ? tasklist.operations[0]
        : null;

      if (firstOperation) {
        item.mainWorkCenter = toText(firstOperation.mainWorkCenter);
      } else if (firstTemplate) {
        item.mainWorkCenter = toText(firstTemplate.mainWorkCenter);
      }
    }

    if (markDraft) {
      markItemAsDraft(item);
    }
  }

  function addOperationToActiveItem() {
    const item = getActiveItem();
    if (!item) {
      setRuntime("Select an item before adding operations.");
      return;
    }

    if (!item.tasklistKey) {
      setRuntime("Apply tasklist first.");
      return;
    }

    const newOperation = {
      operationNo: nextOperationNumber(item.operations),
      operationShortText: "",
      workHours: "1",
      durationHours: "1",
      mainWorkCenter: toText(item.mainWorkCenter),
      vendor: "",
      longText: "",
      controlKey: "",
    };

    item.operations.push(newOperation);
    state.activeOperationIndex = item.operations.length - 1;
    markItemAsDraft(item);

    renderOperationsTable(item);
    renderTasklistMeta(item, false);
    renderItemRail();
    applyPlanInteractionState();
  }

  function openTasklistPickerModal() {
    const item = getActiveItem();
    if (!item) {
      setRuntime("Select an item before adding tasklist lines.");
      return;
    }

    if (!item.tasklistKey) {
      setRuntime("Apply tasklist first.");
      return;
    }

    const tasklist = getTasklistByKey(state.plan.plant, item.tasklistKey);
    if (!tasklist) {
      setRuntime("Tasklist data missing for active item.");
      return;
    }

    const templates = Array.isArray(tasklist.operations) ? tasklist.operations : [];
    if (!templates.length) {
      setRuntime("Selected tasklist has no predefined lines.");
      return;
    }

    state.tasklistPicker.open = true;
    state.tasklistPicker.filter = "";
    state.tasklistPicker.templates = templates;
    state.tasklistPicker.visibleIndices = [];
    state.tasklistPicker.selectedIndices = new Set();

    dom.tasklistPickerSearch.value = "";
    dom.tasklistPickerSelectAll.checked = false;
    dom.tasklistPickerSelectAll.indeterminate = false;

    renderTasklistPickerRows();
    dom.tasklistPickerModal.hidden = false;

    window.setTimeout(() => {
      dom.tasklistPickerSearch.focus();
    }, 0);
  }

  function closeTasklistPickerModal() {
    state.tasklistPicker.open = false;
    state.tasklistPicker.filter = "";
    state.tasklistPicker.templates = [];
    state.tasklistPicker.visibleIndices = [];
    state.tasklistPicker.selectedIndices = new Set();

    if (dom.tasklistPickerModal) {
      dom.tasklistPickerModal.hidden = true;
    }
  }

  function onTasklistPickerRowToggle(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.type !== "checkbox") return;

    const index = Number(target.getAttribute("data-picker-index"));
    if (!Number.isFinite(index)) return;

    const key = String(index);
    if (target.checked) {
      state.tasklistPicker.selectedIndices.add(key);
    } else {
      state.tasklistPicker.selectedIndices.delete(key);
    }

    renderTasklistPickerRows();
  }

  function onTasklistPickerRowClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.closest("input[type=\"checkbox\"]")) return;

    const row = target.closest("tr");
    if (!row) return;

    const checkbox = row.querySelector("input[type=\"checkbox\"][data-picker-index]");
    if (!(checkbox instanceof HTMLInputElement)) return;

    checkbox.checked = !checkbox.checked;
    checkbox.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function renderTasklistPickerRows() {
    dom.tasklistPickerBody.innerHTML = "";

    const query = toText(state.tasklistPicker.filter).toLowerCase();
    const templates = state.tasklistPicker.templates;
    const visible = [];

    templates.forEach((template, index) => {
      const opNo = normalizeOperationNo(toText(template.operationNo), true);
      const shortText = toText(template.operationShortText);
      const workCenter = toText(template.mainWorkCenter);
      const controlKey = toText(template.controlKey);
      const workHours = toText(template.workHours);
      const durationHours = toText(template.durationHours);

      const searchable = `${opNo} ${shortText} ${workCenter} ${controlKey} ${workHours} ${durationHours}`.toLowerCase();
      if (query && !searchable.includes(query)) {
        return;
      }

      visible.push(index);

      const key = String(index);
      const checked = state.tasklistPicker.selectedIndices.has(key);

      const row = document.createElement("tr");
      row.innerHTML = `
        <td><input type="checkbox" data-picker-index="${index}" ${checked ? "checked" : ""} /></td>
        <td>${escapeHtml(opNo || "-")}</td>
        <td>${escapeHtml(shortText || "-")}</td>
        <td>${escapeHtml(workCenter || "-")}</td>
        <td>${escapeHtml(controlKey || "-")}</td>
        <td>${escapeHtml(workHours || "-")}</td>
        <td>${escapeHtml(durationHours || "-")}</td>
      `;
      dom.tasklistPickerBody.appendChild(row);
    });

    state.tasklistPicker.visibleIndices = visible;

    if (!visible.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="7" class="ops-empty">No matching tasklist lines.</td>';
      dom.tasklistPickerBody.appendChild(row);
    }

    const selectedVisible = visible.filter((index) => state.tasklistPicker.selectedIndices.has(String(index))).length;
    const totalSelected = state.tasklistPicker.selectedIndices.size;
    dom.tasklistPickerInfo.textContent = `${selectedVisible}/${visible.length} visible selected (${totalSelected} total selected).`;

    if (!visible.length) {
      dom.tasklistPickerSelectAll.checked = false;
      dom.tasklistPickerSelectAll.indeterminate = false;
      return;
    }

    if (selectedVisible === 0) {
      dom.tasklistPickerSelectAll.checked = false;
      dom.tasklistPickerSelectAll.indeterminate = false;
      return;
    }

    if (selectedVisible === visible.length) {
      dom.tasklistPickerSelectAll.checked = true;
      dom.tasklistPickerSelectAll.indeterminate = false;
      return;
    }

    dom.tasklistPickerSelectAll.checked = false;
    dom.tasklistPickerSelectAll.indeterminate = true;
  }

  function addSelectedTasklistLinesToActiveItem() {
    const item = getActiveItem();
    if (!item) {
      closeTasklistPickerModal();
      return;
    }

    const indices = Array.from(state.tasklistPicker.selectedIndices.values())
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value))
      .sort((a, b) => a - b);

    if (!indices.length) {
      setRuntime("Select at least one tasklist line.");
      return;
    }

    const templates = state.tasklistPicker.templates;
    let added = 0;

    indices.forEach((index) => {
      const template = templates[index];
      if (!template) return;

      const operation = {
        operationNo: nextOperationNumber(item.operations),
        operationShortText: toText(template.operationShortText),
        workHours: toText(template.workHours) || "1",
        durationHours: toText(template.durationHours) || "1",
        mainWorkCenter: toText(template.mainWorkCenter) || toText(item.mainWorkCenter),
        vendor: "",
        longText: "",
        controlKey: toText(template.controlKey),
      };

      item.operations.push(operation);
      added += 1;
    });

    if (added <= 0) {
      setRuntime("No tasklist lines were added.");
      return;
    }

    state.activeOperationIndex = item.operations.length - 1;
    markItemAsDraft(item);

    closeTasklistPickerModal();
    renderOperationsTable(item);
    renderTasklistMeta(item, false);
    renderItemRail();
    applyPlanInteractionState();
    setRuntime(`Added ${added} tasklist line${added === 1 ? "" : "s"} to active item.`);
  }

  function removeSelectedOperationFromActiveItem() {
    const item = getActiveItem();
    if (!item || !item.operations.length) return;

    let index = state.activeOperationIndex;
    if (!Number.isFinite(index) || index < 0 || index >= item.operations.length) {
      index = item.operations.length - 1;
    }

    item.operations.splice(index, 1);

    if (!item.operations.length) {
      state.activeOperationIndex = -1;
    } else {
      state.activeOperationIndex = Math.min(index, item.operations.length - 1);
    }

    markItemAsDraft(item);
    renderOperationsTable(item);
    renderTasklistMeta(item, false);
    renderItemRail();
    applyPlanInteractionState();
  }

  function renderOperationsTable(item) {
    dom.operationsBody.innerHTML = "";

    if (!item) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="8" class="ops-empty">Select item to manage operations.</td>';
      dom.operationsBody.appendChild(row);
      return;
    }

    if (!item.operations.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="8" class="ops-empty">No operations yet. Add lines from tasklist or add operations manually.</td>';
      dom.operationsBody.appendChild(row);
      return;
    }

    item.operations.forEach((operation, index) => {
      const isActive = index === state.activeOperationIndex;
      const row = document.createElement("tr");
      if (isActive) row.classList.add("active");

      row.innerHTML = `
        <td>
          <button type="button" class="op-select-btn" data-op-select-index="${index}">${isActive ? "●" : "○"}</button>
        </td>
        <td>
          <input type="text" maxlength="4" data-op-index="${index}" data-op-field="operationNo" value="${escapeHtml(operation.operationNo)}" />
        </td>
        <td>
          <input type="text" maxlength="80" data-op-index="${index}" data-op-field="operationShortText" value="${escapeHtml(operation.operationShortText)}" />
        </td>
        <td>
          <input type="text" maxlength="10" data-op-index="${index}" data-op-field="workHours" value="${escapeHtml(operation.workHours)}" />
        </td>
        <td>
          <input type="text" maxlength="10" data-op-index="${index}" data-op-field="durationHours" value="${escapeHtml(operation.durationHours)}" />
        </td>
        <td>
          <input type="text" maxlength="24" data-op-index="${index}" data-op-field="mainWorkCenter" value="${escapeHtml(operation.mainWorkCenter)}" />
        </td>
        <td>
          <input type="text" maxlength="40" data-op-index="${index}" data-op-field="vendor" value="${escapeHtml(operation.vendor)}" />
        </td>
        <td>
          <textarea data-op-index="${index}" data-op-field="longText">${escapeHtml(operation.longText)}</textarea>
        </td>
      `;

      dom.operationsBody.appendChild(row);
    });
  }

  function renderTasklistMeta(item, fromSelection) {
    if (!item) {
      setTasklistMeta("Create plan and select item to manage tasklist.", "warn");
      return;
    }

    const selectedKey = toText(dom.itemTasklistSelect.value);

    if (!item.tasklistKey) {
      if (selectedKey && fromSelection) {
        setTasklistMeta("Tasklist selected in dropdown. Click Apply tasklist to bind it to active item.", "warn");
        return;
      }
      setTasklistMeta("No tasklist bound to active item.", "warn");
      return;
    }

    const sourceMeta = state.tasklists[toText(state.plan.plant)] || null;
    const sourceSheet = sourceMeta ? toText(sourceMeta.sourceSheet) : "n/a";
    const sheetCode = sourceMeta ? toText(sourceMeta.sheetCode) : "n/a";
    const opCount = item.operations.length;

    if (selectedKey && selectedKey !== item.tasklistKey && fromSelection) {
      setTasklistMeta(
        `Active: ${item.tasklistName} (${opCount} ops). Selected: ${selectedKey}. Click Apply tasklist to switch binding.`,
        "warn"
      );
      return;
    }

    setTasklistMeta(
      `Active tasklist: ${item.tasklistName} (${item.tasklistKey}) | Ops: ${opCount} | Sheet: ${sheetCode} | Source: ${sourceSheet} | Use Add lines from tasklist to import selected lines.`,
      "ok"
    );
  }

  function setTasklistMeta(text, mode) {
    if (!dom.tasklistMeta) return;
    dom.tasklistMeta.textContent = text;
    dom.tasklistMeta.className = "inline-helper";
    if (mode) {
      dom.tasklistMeta.classList.add(mode);
    }
  }

  function nextOperationNumber(operations) {
    let max = 0;
    operations.forEach((operation) => {
      const value = Number.parseInt(toText(operation.operationNo), 10);
      if (Number.isFinite(value) && value > max) {
        max = value;
      }
    });

    const next = max > 0 ? max + 10 : 10;
    return String(next).padStart(4, "0");
  }

  function onOperationTableClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    const selectButton = target.closest("[data-op-select-index]");
    if (!selectButton) return;

    const index = Number(selectButton.getAttribute("data-op-select-index"));
    if (!Number.isFinite(index)) return;

    state.activeOperationIndex = index;
    renderOperationsTable(getActiveItem());
    applyPlanInteractionState();
  }

  function onOperationTableInput(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;

    const item = getActiveItem();
    if (!item) return;

    const index = Number(target.getAttribute("data-op-index"));
    const field = toText(target.getAttribute("data-op-field"));

    if (!Number.isFinite(index) || index < 0 || index >= item.operations.length) return;
    if (!field) return;

    const operation = item.operations[index];
    let value = toText(target.value);

    if (field === "operationNo") {
      value = value.replace(/[^0-9]/g, "").slice(0, 4);
      target.value = value;
    }

    operation[field] = value;

    if (field === "mainWorkCenter") {
      operation[field] = normalizeUpper(operation[field]);
      target.value = operation[field];
    }

    markItemAsDraft(item);
    state.activeOperationIndex = index;
    renderItemRail();
    renderTasklistMeta(item, false);
  }

  function onOperationTableChange(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;

    const item = getActiveItem();
    if (!item) return;

    const index = Number(target.getAttribute("data-op-index"));
    const field = toText(target.getAttribute("data-op-field"));

    if (!Number.isFinite(index) || index < 0 || index >= item.operations.length) return;
    if (!field) return;

    if (field === "operationNo") {
      item.operations[index].operationNo = normalizeOperationNo(item.operations[index].operationNo, true);
      target.value = item.operations[index].operationNo;
    }

    markItemAsDraft(item);
    renderItemRail();
  }

  async function validatePlanAndItems() {
    if (state.validationRunning) return;
    if (!state.planCommitted) {
      setRuntime("Create plan first.");
      return;
    }

    state.validationRunning = true;
    dom.btnValidate.disabled = true;
    dom.btnValidate.textContent = "Validating...";

    try {
      persistPlanFromForm();
      persistEditorToActiveItem();

      const planIssues = validatePlan();
      if (!state.items.length) {
        planIssues.push("At least one item is required.");
      }

      state.items.forEach((item) => validateItemLocal(item));

      renderItemRail();

      if (state.items.length) {
        setRuntime("Running SAP lookup for item Functional Locations...");
        await Promise.all(state.items.map((item) => validateItemFlInSap(item)));
      }

      renderItemRail();

      const blockingItemCount = state.items.filter((item) => item.issues.length > 0).length;
      const warningItemCount = state.items.filter((item) => item.warnings.length > 0).length;

      if (planIssues.length || blockingItemCount) {
        const planIssueText = planIssues.length ? `${planIssues.length} plan issues` : "plan ok";
        setRuntime(`Validation: ${planIssueText}, ${blockingItemCount} items with errors, ${warningItemCount} with warnings.`);
      } else {
        setRuntime(`Validation complete: ${state.items.length} items ready (${warningItemCount} with warnings).`);
      }

      loadActiveItemIntoEditor();
      renderTasklistControls();
    } finally {
      state.validationRunning = false;
      dom.btnValidate.disabled = false;
      dom.btnValidate.textContent = "Validate";
      applyPlanInteractionState();
    }
  }

  function collectPlanIssues(plan) {
    const issues = [];
    const plant = toText(plan && plan.plant);
    const status = toText(plan && plan.status);
    const planText = toText(plan && plan.planText);
    const cycleText = toText(plan && plan.cycle);
    const unit = toText(plan && plan.unit);
    const day = Number(toText(plan && plan.firstCallDay));
    const month = Number(toText(plan && plan.firstCallMonth));
    const year = Number(toText(plan && plan.firstCallYear));

    if (!plant) {
      issues.push("Plant is required.");
    }

    if (!status) {
      issues.push("Status is required.");
    }

    if (!planText) {
      issues.push("Plan text is required.");
    } else {
      if (planText.length > 40) {
        issues.push("Plan text exceeds 40 characters.");
      }

      if (plant && !planText.toUpperCase().startsWith(plant.toUpperCase())) {
        issues.push("Plan text should start with plant initials.");
      }
    }

    const cycle = Number(cycleText.replace(",", "."));
    if (!cycleText || !Number.isFinite(cycle) || cycle <= 0) {
      issues.push("Cycle must be a positive number.");
    }

    if (!unit) {
      issues.push("Unit is required.");
    }

    if (!Number.isFinite(day) || day < 1 || day > 31) {
      issues.push("First call day must be 1..31.");
    }

    if (!Number.isFinite(month) || month < 1 || month > 12) {
      issues.push("First call month must be 1..12.");
    }

    if (!Number.isFinite(year) || year < 2020 || year > 2100) {
      issues.push("First call year must be a valid year.");
    }

    return issues;
  }

  function validatePlan() {
    const issues = collectPlanIssues(state.plan);

    if (dom.planMeta) {
      if (issues.length) {
        dom.planMeta.textContent = issues[0];
        dom.planMeta.className = "inline-helper error";
      } else {
        dom.planMeta.textContent = "Plan OK";
        dom.planMeta.className = "inline-helper ok";
      }
    }

    return issues;
  }

  function validateItemLocal(item) {
    const issues = [];
    const warnings = [];

    if (!item.shortText) {
      issues.push("Item short text is required.");
    } else if (item.shortText.length > 40) {
      issues.push("Item short text exceeds 40 characters.");
    }

    if (!item.mainWorkCenter) {
      issues.push("Main Work Center is required.");
    }

    if (!item.activityType) {
      issues.push("Maintenance Activity Type is required.");
    }

    if (!item.functionalLocation) {
      issues.push("Functional Location is required.");
    }

    if (!item.tasklistKey) {
      issues.push("Tasklist is required.");
    }

    if (!item.operations.length) {
      issues.push("At least one operation is required.");
    }

    const operationValidation = validateOperations(item.operations);
    issues.push(...operationValidation.issues);
    warnings.push(...operationValidation.warnings);

    item.issues = dedupe(issues);
    item.warnings = dedupe(warnings);

    if (item.issues.length) item.status = "invalid";
    else if (item.warnings.length) item.status = "warning";
    else item.status = "valid";
  }

  function validateOperations(operations) {
    const issues = [];
    const warnings = [];
    const operationNoSet = new Set();

    operations.forEach((operation, index) => {
      const prefix = `Operation ${index + 1}`;

      const operationNo = normalizeOperationNo(operation.operationNo, true);
      operation.operationNo = operationNo;

      if (!/^\d{4}$/.test(operationNo)) {
        issues.push(`${prefix}: operation no. must be 4 digits.`);
      } else if (operationNoSet.has(operationNo)) {
        issues.push(`${prefix}: duplicate operation no. ${operationNo}.`);
      } else {
        operationNoSet.add(operationNo);
      }

      if (!toText(operation.operationShortText)) {
        issues.push(`${prefix}: operation short text is required.`);
      }

      if (!isPositiveNumber(operation.workHours)) {
        issues.push(`${prefix}: Work (H) must be a positive number.`);
      }

      if (!isPositiveNumber(operation.durationHours)) {
        issues.push(`${prefix}: Dur. (H) must be a positive number.`);
      }

      if (!toText(operation.mainWorkCenter)) {
        issues.push(`${prefix}: Main Work Center is required.`);
      }

      const controlKey = toText(operation.controlKey).toUpperCase();
      if ((controlKey === "PM02" || controlKey === "PM03") && !toText(operation.vendor)) {
        warnings.push(`${prefix}: Vendor should be filled for ${controlKey}.`);
      }
    });

    return {
      issues: dedupe(issues),
      warnings: dedupe(warnings),
    };
  }

  async function validateItemFlInSap(item) {
    if (!window.OrstedOData) return;
    if (item.issues.length) return;

    const fl = normalizeFunctionalLocation(item.functionalLocation);
    if (!fl) return;

    const lookup = await window.OrstedOData.lookupFunctionalLocation(fl, {
      useLocalProxy: state.net.useLocalProxy,
      timeoutMs: 13000,
    });

    if (!lookup.ok) {
      item.warnings = dedupe([
        ...item.warnings,
        window.OrstedOData.formatLookupError(lookup.error, state.net.useLocalProxy),
      ]);
      item.status = "warning";
      return;
    }

    if (!lookup.exists) {
      item.issues = dedupe([...item.issues, "Functional Location not found in SAP OData."]);
      item.status = "invalid";
      return;
    }

    item.flDescription = lookup.pltxt || "";
    item.status = item.warnings.length ? "warning" : "valid";

    if (item.id === state.activeItemId) {
      setFlMeta(item.flDescription || "Functional Location found in SAP.", item.flDescription ? "ok" : "warn");
      setFlDescription(item.flDescription || "");
    }
  }

  function queueFlSuggestions(query) {
    const value = normalizeFunctionalLocation(query);

    if (!window.OrstedOData || value.length < 7) {
      cancelFlSuggestionRequest();
      hideFlSuggestions();
      if (!value) {
        setFlMeta("", "");
        setFlDescription("");
      }
      return;
    }

    if (state.flSuggest.timer) {
      window.clearTimeout(state.flSuggest.timer);
      state.flSuggest.timer = null;
    }

    cancelFlSuggestionRequest();

    const token = ++state.flSuggest.token;
    setFlMeta("Searching...", "warn");

    state.flSuggest.timer = window.setTimeout(async () => {
      const controller = new AbortController();
      state.flSuggest.abortController = controller;

      try {
        const suggestions = await window.OrstedOData.searchFunctionalLocations(value, {
          useLocalProxy: state.net.useLocalProxy,
          minChars: 7,
          limit: 12,
          signal: controller.signal,
        });

        if (token !== state.flSuggest.token) return;

        state.flSuggest.items = suggestions;
        state.flSuggest.activeIndex = -1;
        renderFlSuggestions();

        if (!suggestions.length) {
          setFlMeta("No suggestions.", "warn");
        } else {
          setFlMeta(`${suggestions.length} suggestions.`, "ok");
        }
      } catch (error) {
        const message = error && error.message ? String(error.message).toLowerCase() : "";
        if (message.includes("abort")) {
          return;
        }
        setFlMeta(
          window.OrstedOData.formatLookupError(
            error && error.message ? error.message : String(error),
            state.net.useLocalProxy
          ),
          "warn"
        );
      } finally {
        if (state.flSuggest.abortController === controller) {
          state.flSuggest.abortController = null;
        }
      }
    }, 180);
  }

  function cancelFlSuggestionRequest() {
    if (!state.flSuggest.abortController) return;
    state.flSuggest.abortController.abort();
    state.flSuggest.abortController = null;
  }

  function renderFlSuggestions() {
    dom.itemFlSuggestions.innerHTML = "";

    if (!state.flSuggest.items.length) {
      dom.itemFlSuggestions.hidden = true;
      return;
    }

    state.flSuggest.items.forEach((entry, index) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "combo-option";
      option.innerHTML = `<strong>${escapeHtml(entry.tplnr)}</strong>${entry.pltxt ? ` - ${escapeHtml(entry.pltxt)}` : ""}`;
      option.classList.toggle("active", index === state.flSuggest.activeIndex);

      option.addEventListener("mousedown", (event) => {
        event.preventDefault();
        applyFlSuggestion(entry);
      });

      dom.itemFlSuggestions.appendChild(option);
    });

    dom.itemFlSuggestions.hidden = false;
  }

  function hideFlSuggestions() {
    state.flSuggest.items = [];
    state.flSuggest.activeIndex = -1;
    dom.itemFlSuggestions.hidden = true;
    dom.itemFlSuggestions.innerHTML = "";
  }

  function onFlKeyDown(event) {
    if (dom.itemFlSuggestions.hidden) return;

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

    if (event.key === "Enter") {
      if (state.flSuggest.activeIndex >= 0) {
        event.preventDefault();
        const selected = state.flSuggest.items[state.flSuggest.activeIndex];
        if (selected) applyFlSuggestion(selected);
      }
      return;
    }

    if (event.key === "Escape") {
      hideFlSuggestions();
    }
  }

  function moveFlSuggestion(step) {
    const length = state.flSuggest.items.length;
    if (!length) return;

    let index = state.flSuggest.activeIndex + step;
    if (index < 0) index = length - 1;
    if (index >= length) index = 0;

    state.flSuggest.activeIndex = index;
    renderFlSuggestions();
  }

  function applyFlSuggestion(entry) {
    dom.itemFunctionalLocation.value = normalizeFunctionalLocation(entry.tplnr);
    persistEditorToActiveItem();

    const item = getActiveItem();
    if (item) {
      item.flDescription = toText(entry.pltxt);
      setFlMeta(item.flDescription || "Functional Location selected.", item.flDescription ? "ok" : "warn");
      setFlDescription(item.flDescription || "");
    }

    hideFlSuggestions();
    renderItemRail();
  }

  async function lookupExactFlForActiveItem() {
    const item = getActiveItem();
    if (!item || !window.OrstedOData) return;

    const fl = normalizeFunctionalLocation(item.functionalLocation);
    if (!fl || fl.length < 7) {
      item.flDescription = "";
      setFlMeta("", "");
      setFlDescription("");
      return;
    }

    const lookup = await window.OrstedOData.lookupFunctionalLocation(fl, {
      useLocalProxy: state.net.useLocalProxy,
      timeoutMs: 12000,
    });

    if (!lookup.ok) {
      setFlMeta(window.OrstedOData.formatLookupError(lookup.error, state.net.useLocalProxy), "warn");
      setFlDescription("");
      return;
    }

    if (!lookup.exists) {
      item.flDescription = "";
      setFlMeta("Functional Location not found in SAP.", "error");
      setFlDescription("");
      return;
    }

    item.flDescription = lookup.pltxt || "";
    setFlMeta(item.flDescription || "Functional Location found in SAP.", "ok");
    setFlDescription(item.flDescription || "");
    renderItemRail();
  }

  function exportPayload() {
    persistPlanFromForm();
    persistEditorToActiveItem();

    const payload = {
      generatedAt: new Date().toISOString(),
      source: "vh-plan-web-shell",
      useLocalProxy: state.net.useLocalProxy,
      optionsLoaded: state.optionsLoaded,
      tasklistsLoaded: state.tasklistsLoaded,
      tasklistSource: state.tasklistSource,
      tasklistVersion: state.tasklistVersion,
      planMeta: {
        planCommitted: state.planCommitted,
        planLocked: state.planLocked,
        lastCommittedPlant: state.lastCommittedPlant,
      },
      plan: state.plan,
      items: serializeItems(),
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `vh_plan_shell_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
    setRuntime("Exported JSON.");
  }

  function serializeItems() {
    return state.items.map((item, index) => ({
      id: item.id,
      sequence: index + 1,
      shortText: item.shortText,
      mainWorkCenter: item.mainWorkCenter,
      activityType: item.activityType,
      functionalLocation: item.functionalLocation,
      flDescription: item.flDescription,
      objectList: item.objectList,
      taskListGroup: item.taskListGroup,
      tasklistKey: item.tasklistKey,
      tasklistName: item.tasklistName,
      revision: item.revision,
      longText: item.longText,
      orstedResponsible: item.orstedResponsible,
      initials: item.initials,
      status: item.status,
      issues: [...item.issues],
      warnings: [...item.warnings],
      operations: item.operations.map((operation) => ({
        operationNo: operation.operationNo,
        operationShortText: operation.operationShortText,
        workHours: operation.workHours,
        durationHours: operation.durationHours,
        mainWorkCenter: operation.mainWorkCenter,
        vendor: operation.vendor,
        longText: operation.longText,
        controlKey: operation.controlKey,
      })),
    }));
  }

  function sendPayloadAsEmail() {
    const snapshot = buildVhMailSnapshot();

    if (!window.MailtoUtils || typeof window.MailtoUtils.finalizeMailtoHref !== "function") {
      setRuntime("Mailfunktion er ikke tilgaengelig.");
      return;
    }

    const subject = buildVhEmailSubject(snapshot);
    const detailedBody = buildVhEmailBody(snapshot);
    const summaryBody = buildVhSummaryBody(snapshot);
    const resolved = window.MailtoUtils.finalizeMailtoHref({
      recipient: MAILTO_RECIPIENT,
      subject,
      detailedBody,
      summaryBody,
      maxUrlLength: MAILTO_MAX_URL_LENGTH,
      truncationNote: "[afkortet pga. mail-laengde]",
    });

    if (!resolved.ok) {
      setRuntime("Mailindholdet er for stort. Brug Export JSON.");
      return;
    }

    window.location.href = resolved.href;

    const invalidCount = snapshot.statusCounts.invalid;
    const warningCount = snapshot.statusCounts.warning;
    const planIssueCount = snapshot.planIssues.length;
    const qualityLine = `Kontrol: ${invalidCount} fejl, ${warningCount} advarsler${planIssueCount ? `, ${planIssueCount} planfejl` : ""}.`;

    if (resolved.mode === "full") {
      setRuntime(`Aabner mailkladde i mailklient. Fuldt VH-plan indhold. ${qualityLine}`);
      return;
    }

    if (resolved.mode === "summary") {
      setRuntime(`Aabner mailkladde i mailklient. Oversigt. ${qualityLine}`);
      return;
    }

    setRuntime(`Aabner mailkladde i mailklient. Afkortet oversigt. ${qualityLine}`);
  }

  function buildVhMailSnapshot() {
    persistPlanFromForm();
    persistEditorToActiveItem();

    const plan = { ...state.plan };
    const items = state.items.map((item) => cloneVhItemForMail(item));
    items.forEach((item) => {
      validateItemLocal(item);
    });

    return {
      generatedAt: new Date(),
      plan,
      planLocked: state.planLocked,
      planIssues: collectPlanIssues(plan),
      items,
      statusCounts: countVhStatuses(items),
      useLocalProxy: state.net.useLocalProxy,
      optionsLoaded: state.optionsLoaded,
      tasklistSource: state.tasklistSource,
    };
  }

  function cloneVhItemForMail(item) {
    return {
      id: item.id,
      shortText: toText(item.shortText),
      mainWorkCenter: toText(item.mainWorkCenter),
      activityType: toText(item.activityType),
      functionalLocation: normalizeFunctionalLocation(item.functionalLocation),
      flDescription: toText(item.flDescription),
      objectList: toText(item.objectList),
      taskListGroup: toText(item.taskListGroup),
      tasklistKey: toText(item.tasklistKey),
      tasklistName: toText(item.tasklistName),
      revision: toText(item.revision),
      longText: toText(item.longText),
      orstedResponsible: toText(item.orstedResponsible),
      initials: toText(item.initials),
      status: toText(item.status).toLowerCase() || "draft",
      issues: Array.isArray(item.issues) ? [...item.issues] : [],
      warnings: Array.isArray(item.warnings) ? [...item.warnings] : [],
      operations: Array.isArray(item.operations)
        ? item.operations.map((operation) => ({
          operationNo: normalizeOperationNo(toText(operation.operationNo), true),
          operationShortText: toText(operation.operationShortText),
          workHours: toText(operation.workHours),
          durationHours: toText(operation.durationHours),
          mainWorkCenter: toText(operation.mainWorkCenter),
          vendor: toText(operation.vendor),
          longText: toText(operation.longText),
          controlKey: toText(operation.controlKey),
        }))
        : [],
    };
  }

  function countVhStatuses(items) {
    const counts = {
      valid: 0,
      warning: 0,
      invalid: 0,
      draft: 0,
    };

    items.forEach((item) => {
      const status = toText(item.status).toLowerCase();
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

  function buildVhEmailSubject(snapshot) {
    const dateStamp = new Date().toISOString().slice(0, 10);
    const plant = toText(snapshot.plan.plant) || "Ukendt vaerk";
    const itemCount = snapshot.items.length;
    const invalidCount = snapshot.statusCounts.invalid;
    const itemLabel = itemCount === 1 ? "post" : "poster";
    return `SAP Vedligehold | VH-plan | ${plant} | ${itemCount} ${itemLabel} | Fejl ${invalidCount} | ${dateStamp}`;
  }

  function buildVhEmailBody(snapshot) {
    const lines = [];
    const generatedAt = snapshot.generatedAt.toLocaleString();
    const readyCount = snapshot.statusCounts.valid + snapshot.statusCounts.warning;

    lines.push("VH-PLAN - MAILUDKAST");
    lines.push(`Modtager: ${MAILTO_RECIPIENT}`);
    lines.push(`Genereret: ${generatedAt}`);
    lines.push("========================================");
    lines.push("01) OVERSIGT");
    lines.push(`- Antal poster: ${snapshot.items.length}`);
    lines.push(`- Klar til behandling: ${readyCount}`);
    lines.push(`- Med fejl: ${snapshot.statusCounts.invalid}`);
    lines.push(`- Klar med advarsler: ${snapshot.statusCounts.warning}`);
    lines.push(`- Kladder: ${snapshot.statusCounts.draft}`);
    lines.push(`- Planlaas: ${snapshot.planLocked ? "Laast" : "Aaben"}`);
    lines.push(`- Lokal proxy: ${snapshot.useLocalProxy ? "JA" : "NEJ"}`);
    lines.push(`- Valgmuligheder indlaest: ${snapshot.optionsLoaded ? "JA" : "NEJ"}`);
    lines.push(`- Tasklistkilde: ${snapshot.tasklistSource || "n/a"}`);
    if (snapshot.planIssues.length) {
      lines.push(`- Planvalidering: ${snapshot.planIssues.length} fejl`);
    } else {
      lines.push("- Planvalidering: OK");
    }
    lines.push("- Datagrundlag: Normaliserede/finale vaerdier fra appen.");

    if (snapshot.planIssues.length) {
      lines.push("");
      lines.push("Planvalideringsfejl");
      snapshot.planIssues.forEach((issue) => {
        lines.push(`  * ${issue}`);
      });
    }

    lines.push("");
    lines.push("02) PLANOPLYSNINGER");

    VH_PLAN_FIELDS_FOR_EMAIL.forEach(([key, label]) => {
      lines.push(formatFieldLine(label, toText(snapshot.plan[key]) || "-"));
    });

    lines.push("");
    lines.push("03) POSTER (DETALJER)");

    if (!snapshot.items.length) {
      lines.push("- Ingen poster oprettet.");
      return lines.join("\n");
    }

    snapshot.items.forEach((item, index) => {
      lines.push("");
      lines.push(`Post ${index + 1} | Status: ${mapVhStatusToDanish(item.status)}`);
      lines.push("----------------------------------------");
      lines.push(formatFieldLine("Kort tekst", toText(item.shortText) || "-"));
      lines.push(formatFieldLine("Hovedarbejdscenter", toText(item.mainWorkCenter) || "-"));
      lines.push(formatFieldLine("Vedligeholdelsesaktivitet", toText(item.activityType) || "-"));
      lines.push(formatFieldLine("Funktionslokation", toText(item.functionalLocation) || "-"));
      lines.push(formatFieldLine("FL-beskrivelse", toText(item.flDescription) || "-"));
      lines.push(formatFieldLine("Objektliste", toText(item.objectList) || "-"));
      lines.push(formatFieldLine("Taskliste", toText(item.tasklistName) || "-"));
      lines.push(formatFieldLine("Tasklistekode", toText(item.tasklistKey) || "-"));
      lines.push(formatFieldLine("Tasklistegruppe(alias)", toText(item.taskListGroup) || "-"));
      lines.push(formatFieldLine("Revision", toText(item.revision) || "-"));
      lines.push(formatFieldLine("Orsted ansvarlig", toText(item.orstedResponsible) || "-"));
      lines.push(formatFieldLine("Initialer", toText(item.initials) || "-"));
      lines.push(formatFieldLine("Lang tekst", clipText(item.longText, 500) || "-"));
      lines.push(formatFieldLine("Operationer", String(item.operations.length)));

      lines.push("Operationer:");
      if (!item.operations.length) {
        lines.push("  - Ingen operationer.");
      }

      item.operations.forEach((operation, opIndex) => {
        lines.push(`  ${opIndex + 1}. Op ${toText(operation.operationNo) || "----"} | ${clipText(toText(operation.operationShortText) || "-", 80)}`);
        lines.push(
          `     Work: ${toText(operation.workHours) || "-"}h | Dur: ${toText(operation.durationHours) || "-"}h | WC: ${toText(operation.mainWorkCenter) || "-"} | Vendor: ${toText(operation.vendor) || "-"}`
        );

        if (toText(operation.longText)) {
          lines.push(`     Note: ${clipText(toText(operation.longText), 180)}`);
        }
      });

      if (item.issues && item.issues.length) {
        lines.push("Valideringsfejl:");
        item.issues.forEach((issue) => {
          lines.push(`  * ${issue}`);
        });
      }

      if (item.warnings && item.warnings.length) {
        lines.push("Advarsler:");
        item.warnings.forEach((warning) => {
          lines.push(`  * ${warning}`);
        });
      }
    });

    return lines.join("\n");
  }

  function buildVhSummaryBody(snapshot) {
    const lines = [];
    const generatedAt = snapshot.generatedAt.toLocaleString();
    const limit = Math.min(8, snapshot.items.length);

    lines.push("VH-PLAN - MAILOVERSIGT");
    lines.push(`Modtager: ${MAILTO_RECIPIENT}`);
    lines.push(`Genereret: ${generatedAt}`);
    lines.push("========================================");
    lines.push("");
    lines.push("01) OVERSIGT");
    lines.push(`- Vaerk: ${toText(snapshot.plan.plant) || "-"}`);
    lines.push(`- Antal poster: ${snapshot.items.length}`);
    lines.push(`- Klar til behandling: ${snapshot.statusCounts.valid + snapshot.statusCounts.warning}`);
    lines.push(`- Med fejl: ${snapshot.statusCounts.invalid}`);
    lines.push(`- Kladder: ${snapshot.statusCounts.draft}`);
    lines.push(`- Planlaas: ${snapshot.planLocked ? "Laast" : "Aaben"}`);
    lines.push("- Datagrundlag: Normaliserede/finale vaerdier fra appen.");

    if (snapshot.planIssues.length) {
      lines.push(`- Planvalidering: ${snapshot.planIssues.length} fejl`);
    } else {
      lines.push("- Planvalidering: OK");
    }

    lines.push("");
    lines.push("02) POSTER (KOMPRIMERET)");

    if (!snapshot.items.length) {
      lines.push("- Ingen poster oprettet.");
    }

    for (let index = 0; index < limit; index += 1) {
      const item = snapshot.items[index];
      lines.push(
        `${index + 1}. [${mapVhStatusToDanish(item.status)}] ${toText(item.shortText) || "-"}`
      );
      lines.push(
        `   FL: ${toText(item.functionalLocation) || "-"} | Tasklist: ${toText(item.tasklistKey) || "-"} | Ops: ${item.operations.length}`
      );

      if (item.issues && item.issues.length) {
        lines.push(`   Fejl: ${clipText(item.issues.join(" | "), 160)}`);
      }

      if (item.warnings && item.warnings.length) {
        lines.push(`   Advarsler: ${clipText(item.warnings.join(" | "), 160)}`);
      }
    }

    if (snapshot.items.length > limit) {
      lines.push(`... ${snapshot.items.length - limit} flere poster er ikke medtaget.`);
    }

    lines.push("");
    lines.push("Brug Export JSON i appen for komplet datasat.");

    return lines.join("\n");
  }

  function mapVhStatusToDanish(status) {
    const normalized = toText(status).toLowerCase();
    if (normalized === "valid") return "Klar";
    if (normalized === "warning") return "Klar med advarsler";
    if (normalized === "invalid") return "Har fejl";
    if (normalized === "draft") return "Kladde";
    return toText(status).toUpperCase() || "-";
  }

  function formatFieldLine(label, value) {
    const left = toText(label) || "-";
    const right = toText(value) || "-";
    return `${left.padEnd(30, " ")}: ${right}`;
  }

  function updateProxyButton() {
    if (!dom.btnProxy) return;
    dom.btnProxy.textContent = state.net.useLocalProxy ? "Local proxy: ON" : "Local proxy: OFF";
    dom.btnProxy.setAttribute("aria-pressed", state.net.useLocalProxy ? "true" : "false");
  }

  function setFlMeta(text, mode) {
    dom.itemFlMeta.textContent = text;
    dom.itemFlMeta.className = "inline-helper";
    if (mode) dom.itemFlMeta.classList.add(mode);
  }

  function setFlDescription(text) {
    if (!dom.itemFlDescription) return;
    dom.itemFlDescription.textContent = toText(text);
    dom.itemFlDescription.className = "inline-helper";
    if (toText(text)) dom.itemFlDescription.classList.add("ok");
  }

  function setRuntime(message) {
    dom.runtime.textContent = message;
  }

  function dedupe(messages) {
    const set = new Set();
    messages.forEach((value) => {
      const text = toText(value);
      if (text) set.add(text);
    });
    return Array.from(set.values());
  }

  function normalizeOperationNo(value, pad) {
    const digits = toText(value).replace(/[^0-9]/g, "").slice(0, 4);
    if (!digits) return "";
    if (!pad) return digits;
    return digits.padStart(4, "0");
  }

  function normalizeFunctionalLocation(value) {
    return String(value == null ? "" : value)
      .replaceAll("\u00A0", " ")
      .replaceAll("\r", "")
      .replaceAll("\n", "")
      .trim()
      .toUpperCase();
  }

  // Uppercases without trimming, so spaces can still be typed inside the FL value.
  function upperCaseFlInputInPlace() {
    const input = dom.itemFunctionalLocation;
    const next = String(input.value)
      .replaceAll("\u00A0", " ")
      .replace(/[\r\n]/g, "")
      .toUpperCase();

    if (next === input.value) return;

    const caret = input.selectionStart;
    input.value = next;
    if (caret !== null) {
      input.setSelectionRange(caret, caret);
    }
  }

  function isPositiveNumber(value) {
    const text = toText(value).replace(",", ".");
    const num = Number(text);
    return Number.isFinite(num) && num > 0;
  }
})();

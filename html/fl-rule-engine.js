(() => {
  const { toText, normalizeUpper } = window.TextUtils;

  const ALLOWED_PLANT_PREFIXES = new Set(["AVV", "ASV", "HEV", "KYV", "SSV", "SKV", "HCV", "SMV"]);

  const KKS_PATTERNS = [
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z]$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}$/,
    /^[A-Z]{3}\d{2}[\d\s]U[A-Z]{2}\d{2}UE\d{3}(FP|FD|FG|FH)$/,
    /^[A-Z]{3}\d{2}[\d\s]U[A-Z]{2}\d{2}UF\d{3}[DGH]$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z\s][-A-Z]{2}\d{2}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{5}[\w\s][-A-Z]{2}\d{2}$/,
    /^[A-Z]{3}\d{2,3}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{1,3}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{4}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{1}\d{4}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\s{3}\d{4}$/,
  ];

  const LEGACY_PATTERN = /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}[A-Z\s][-A-Z]{2}\d{1,3}$/;
  const SHORT_PATTERN_SET = [
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{2}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{1}$/,
    /^[A-Z]{3}\d{2,3}$/,
    /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}$/,
    /^[A-Z]{3}\d{2}[\d\s][C-Z][A-Z]{2}\d{2}$/,
  ];
  const ELF_FALLBACK_PATTERN = /^[A-Z]{3}\d{2}[\d\s][A-B][A-Z]{2}\d{2}$/;
  const MKP_ERROR_PATTERN = /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FD|FG|FH|FW|FC)$/;
  const FP_ERROR_PATTERN = /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}[A-Z]{2}\d{3}(FP)$/;

  function buildRuleData(payload, lookups) {
    const safePayload = payload && typeof payload === "object" ? payload : {};
    const functionKeys = Array.isArray(safePayload.functionKeys)
      ? safePayload.functionKeys
      : Array.isArray(safePayload.functionValues)
        ? safePayload.functionValues
        : [];

    const ruleData = {
      loaded: true,
      componentMap: normalizeMap(safePayload.componentMap || {}),
      aggregateMap: normalizeMap(safePayload.aggregateMap || {}),
      functionKeySet: new Set(functionKeys.map(normalizeUpper).filter(Boolean)),
      allowedPlantSet: new Set(ALLOWED_PLANT_PREFIXES),
      br18ByAggregate: buildBr18Index(Array.isArray(safePayload.br18Rules) ? safePayload.br18Rules : []),
      meta: safePayload.meta || null,
    };

    applyLookupOverrides(ruleData, lookups || window.FL_LOOKUPS);
    return ruleData;
  }

  function evaluateKksSyntax(fl) {
    if (!fl) {
      return {
        kksType: "",
        syntaxClass: "",
      };
    }

    const matchedPattern = KKS_PATTERNS.find((pattern) => pattern.test(fl));

    if (!matchedPattern) {
      if (LEGACY_PATTERN.test(fl)) {
        return {
          kksType: "KKS",
          syntaxClass: "",
          warning: "Legacy format.",
        };
      }

      return {
        kksType: "",
        syntaxClass: "",
        blockingIssue: "KKS invalid.",
      };
    }

    if (/^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{2}\s{1}\d{4}$/.test(fl) || /^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\s{3}\d{4}$/.test(fl)) {
      return {
        kksType: "KKSKV",
        syntaxClass: "KAB",
      };
    }

    if (/^[A-Z]{3}\d{2}[\d\s][A-Z]{3}\d{4}$/.test(fl)) {
      return {
        kksType: "KKSKA",
        syntaxClass: "KAB",
      };
    }

    return {
      kksType: "KKS",
      syntaxClass: "",
    };
  }

  function determineClass(fl, syntaxClass, ruleData) {
    const data = ensureRuleData(ruleData);
    const result = {
      className: "",
      candidateClasses: [],
      blockingIssues: [],
      warnings: [],
      notes: [],
    };

    if (!fl) {
      return result;
    }

    if (!data.loaded) {
      result.blockingIssues.push("Rules data missing.");
      return result;
    }

    const key0 = fl.slice(0, 3);
    const key7 = fl.slice(6, 9);
    const key12 = fl.slice(11, 13);
    const key17 = fl.slice(16, 18);
    const key18 = fl.slice(17, 19);

    if (!data.allowedPlantSet.has(key0)) {
      result.blockingIssues.push("Plant key invalid.");
    }

    if (data.functionKeySet.size && !data.functionKeySet.has(key7)) {
      result.blockingIssues.push("Function key invalid.");
    }

    const br18Check = validateBr18Rule(key12, key17, key7, data);
    if (br18Check.blockingIssues.length) result.blockingIssues.push(...br18Check.blockingIssues);
    if (br18Check.notes.length) result.notes.push(...br18Check.notes);

    if (syntaxClass === "KAB") {
      result.className = "KAB";
      result.candidateClasses = ["KAB"];
      return result;
    }

    const key18Resolution = resolveClassByKey18(key18, key12, data);
    if (key18Resolution.relevant) {
      result.className = key18Resolution.className;
      result.candidateClasses = key18Resolution.candidateClasses || [];
      if (key18Resolution.blockingIssues.length) {
        result.blockingIssues.push(...key18Resolution.blockingIssues);
      }
      if (key18Resolution.notes.length) {
        result.notes.push(...key18Resolution.notes);
      }
      return result;
    }

    const fallbackResolution = resolveClassByKey12AndFallback(fl, key12, data);
    result.className = fallbackResolution.className;
    result.candidateClasses = fallbackResolution.candidateClasses || [];
    if (fallbackResolution.notes.length) result.notes.push(...fallbackResolution.notes);
    if (fallbackResolution.warnings.length) result.warnings.push(...fallbackResolution.warnings);
    if (fallbackResolution.blockingIssues.length) result.blockingIssues.push(...fallbackResolution.blockingIssues);

    return result;
  }

  function resolveClassByKey18(key18, key12, ruleData) {
    const result = {
      relevant: key18.length === 2,
      className: "",
      candidateClasses: [],
      blockingIssues: [],
      notes: [],
    };

    if (!result.relevant) {
      return result;
    }

    const hasComponent = !!ruleData.componentMap[key18];
    const hasAggregate = !!ruleData.aggregateMap[key12];

    if (hasComponent && hasAggregate) {
      result.className = ruleData.componentMap[key18];
      result.candidateClasses.push(result.className);
      return result;
    }

    if (!hasComponent) {
      result.blockingIssues.push("Component key invalid.");
    }

    if (!hasAggregate) {
      result.blockingIssues.push("Equipment key invalid.");
    }

    return result;
  }

  function resolveClassByKey12AndFallback(fl, key12, ruleData) {
    const result = {
      className: "",
      candidateClasses: [],
      blockingIssues: [],
      warnings: [],
      notes: [],
    };

    if (ruleData.aggregateMap[key12]) {
      result.className = ruleData.aggregateMap[key12];
      result.candidateClasses = [result.className];
      return result;
    }

    if (MKP_ERROR_PATTERN.test(fl) || FP_ERROR_PATTERN.test(fl)) {
      result.blockingIssues.push("Equipment key invalid.");
      return result;
    }

    const shortMatch = SHORT_PATTERN_SET.some((pattern) => pattern.test(fl));
    if (shortMatch) {
      result.className = "NO CLASS";
      result.candidateClasses = ["NO CLASS"];
      return result;
    }

    if (ELF_FALLBACK_PATTERN.test(fl)) {
      result.className = "ELF";
      result.candidateClasses = ["ELF"];
      return result;
    }

    result.blockingIssues.push("Class not determined.");
    return result;
  }

  function validateBr18Rule(key12, key17, key7, ruleData) {
    const result = {
      blockingIssues: [],
      notes: [],
    };

    if (key12 !== "UE" && key12 !== "UF") {
      return result;
    }

    if (!key7 || key7[0] !== "U") {
      result.blockingIssues.push("UF/UE requires U function key.");
    }

    const ruleSet = ruleData.br18ByAggregate[key12];
    if (!ruleSet) {
      result.blockingIssues.push(`BR18 rules missing for ${key12}.`);
      return result;
    }

    if (!ruleSet[key17]) {
      result.blockingIssues.push(`BR18 key17 invalid for ${key12}.`);
    }

    return result;
  }

  function applyLookupOverrides(ruleData, lookups) {
    if (!lookups || typeof lookups !== "object") return;

    const plantKeys = getColumnValues(lookups.Plant, ["Plant Key", "Plant"], 0).map(normalizeUpper).filter(Boolean);
    if (plantKeys.length) {
      ruleData.allowedPlantSet = new Set(plantKeys);
    }

    const functionKeys = getColumnValues(lookups.FunctionKeyDict, ["Function Key", "FunctionKey", "Key"], 0).map(normalizeUpper).filter(Boolean);
    if (functionKeys.length) {
      ruleData.functionKeySet = new Set(functionKeys);
    }

    const componentMap = toUpperKeyedMap(lookups.ClassDeterminationComponentKey, ["Component Key", "Key"], ["Class", "Class Name"], 0, 1);
    if (Object.keys(componentMap).length) {
      ruleData.componentMap = componentMap;
    }

    const aggregateMap = toUpperKeyedMap(lookups.ClassDeterminationAggregateKey, ["Aggregate Key", "Key"], ["Class", "Class Name"], 0, 1);
    if (Object.keys(aggregateMap).length) {
      ruleData.aggregateMap = aggregateMap;
    }

    const br18ByAggregate = buildBr18IndexFromLookup(lookups.BR18_Keys);
    if (Object.keys(br18ByAggregate).length) {
      ruleData.br18ByAggregate = br18ByAggregate;
    }
  }

  function ensureRuleData(ruleData) {
    return {
      loaded: !!(ruleData && ruleData.loaded),
      componentMap: (ruleData && ruleData.componentMap) || {},
      aggregateMap: (ruleData && ruleData.aggregateMap) || {},
      functionKeySet: (ruleData && ruleData.functionKeySet) || new Set(),
      allowedPlantSet: (ruleData && ruleData.allowedPlantSet) || new Set(ALLOWED_PLANT_PREFIXES),
      br18ByAggregate: (ruleData && ruleData.br18ByAggregate) || {},
      meta: (ruleData && ruleData.meta) || null,
    };
  }

  function buildBr18Index(rules) {
    const index = {};

    rules.forEach((entry) => {
      const aggregateKey = normalizeUpper(entry && entry.aggregateKey);
      const key17 = normalizeUpper(entry && entry.key17);
      const description = toText(entry && entry.description);

      if (!aggregateKey || !key17) return;
      if (!index[aggregateKey]) index[aggregateKey] = {};
      index[aggregateKey][key17] = description || key17;
    });

    return index;
  }

  function buildBr18IndexFromLookup(table) {
    const index = {};
    if (!table || !Array.isArray(table.rows)) return index;

    table.rows.forEach((row) => {
      if (!Array.isArray(row)) return;
      const aggregateKey = normalizeUpper(row[0]);
      const key17 = normalizeUpper(row[1]);
      const description = toText(row[2]);
      if (!aggregateKey || !key17) return;
      if (!index[aggregateKey]) index[aggregateKey] = {};
      index[aggregateKey][key17] = description || key17;
    });

    return index;
  }

  function normalizeMap(source) {
    const output = {};
    Object.keys(source || {}).forEach((key) => {
      const normalizedKey = normalizeUpper(key);
      const normalizedValue = normalizeUpper(source[key]);
      if (!normalizedKey || !normalizedValue) return;
      output[normalizedKey] = normalizedValue;
    });
    return output;
  }

  function getColumnValues(table, preferredHeaders, fallbackIndex) {
    if (!table || !Array.isArray(table.rows)) return [];
    const idx = getColumnIndex(table, preferredHeaders, fallbackIndex);
    return uniqueNonEmpty(table.rows.map((row) => (Array.isArray(row) ? row[idx] : "")));
  }

  function toUpperKeyedMap(table, keyHeaders, valueHeaders, keyIndex, valueIndex) {
    const out = {};
    if (!table || !Array.isArray(table.rows)) return out;

    const keyCol = getColumnIndex(table, keyHeaders, keyIndex);
    const valCol = getColumnIndex(table, valueHeaders, valueIndex);

    table.rows.forEach((row) => {
      if (!Array.isArray(row)) return;
      const key = normalizeUpper(row[keyCol]);
      const value = normalizeUpper(row[valCol]);
      if (!key || !value) return;
      out[key] = value;
    });

    return out;
  }

  function getColumnIndex(table, preferredHeaders, fallbackIndex) {
    if (!table || !Array.isArray(table.headers)) return fallbackIndex;
    const normalized = table.headers.map((h) => normalizeUpper(h));
    for (const header of preferredHeaders) {
      const i = normalized.indexOf(normalizeUpper(header));
      if (i >= 0) return i;
    }
    return fallbackIndex;
  }

  function uniqueNonEmpty(items) {
    const seen = new Set();
    const out = [];
    items.forEach((item) => {
      const value = normalizeUpper(item);
      if (!value || seen.has(value)) return;
      seen.add(value);
      out.push(value);
    });
    return out;
  }

  function normalizeFunctionalLocation(value) {
    return String(value == null ? "" : value)
      .replaceAll("\u00A0", " ")
      .replaceAll("\r", "")
      .replaceAll("\n", "")
      .trim()
      .toUpperCase();
  }

  window.FlRuleEngine = Object.freeze({
    buildRuleData,
    evaluateKksSyntax,
    determineClass,
    normalizeFunctionalLocation,
    normalizeUpper,
  });
})();

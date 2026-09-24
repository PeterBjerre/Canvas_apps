(function () {
  const { toText } = window.TextUtils;

  const ODATA_FUNCTION_BASE_URL = "https://sapap1yq2.de-prod.dk:44302/sap/opu/odata/sap/ZEAM_ODATA_SRV/UpDownFL";
  const ODATA_PROXY_BASE = "http://127.0.0.1:8765";
  const ODATA_SELECT_FIELDS = "Tplnr,Pltxt";
  const ODATA_LOOKUP_CACHE_MS = 10 * 60 * 1000;
  const ODATA_SUGGEST_CACHE_MS = 5 * 60 * 1000;
  const ODATA_CACHE_MAX_ENTRIES = 220;

  const lookupCache = new Map();
  const requestInFlight = new Map();
  const lookupInFlight = new Map();
  const searchCache = new Map();
  const searchInFlight = new Map();

  function sanitizeFunctionalLocation(value) {
    return String(value == null ? "" : value)
      .replaceAll("\u00A0", " ")
      .replaceAll("\r", "")
      .replaceAll("\n", "")
      .trim();
  }

  // Not the shared normalizeUpper: FL lookups must strip NBSP and line breaks first.
  function normalizeUpper(value) {
    return sanitizeFunctionalLocation(value).toUpperCase();
  }

  function buildFunctionUrl(fl, useDollarFormat, quoteFl) {
    const tplnrValue = quoteFl ? `'${fl}'` : fl;
    const encodedFl = encodeURIComponent(tplnrValue);
    const selectParam = `$select=${encodeURIComponent(ODATA_SELECT_FIELDS)}`;
    const formatParam = useDollarFormat ? "$format=json" : "format=json";
    return `${ODATA_FUNCTION_BASE_URL}?Tplnr=${encodedFl}&Up=1&Down=1&${selectParam}&${formatParam}`;
  }

  function buildProxyFunctionUrl(fl) {
    const selectParam = `$select=${encodeURIComponent(ODATA_SELECT_FIELDS)}`;
    return `${ODATA_PROXY_BASE}/odata?Tplnr=${encodeURIComponent(fl)}&Up=1&Down=1&${selectParam}&format=json`;
  }

  function extractRecords(payload) {
    const records = [];

    function walk(node) {
      if (!node) return;

      if (Array.isArray(node)) {
        node.forEach(walk);
        return;
      }

      if (typeof node !== "object") return;

      const tplnr = getCaseInsensitive(node, ["Tplnr", "tplnr", "TPLNR"]);
      const pltxt = getCaseInsensitive(node, ["Pltxt", "pltxt", "PLTXT", "Description"]);

      if (toText(tplnr)) {
        records.push({
          tplnr: toText(tplnr),
          pltxt: toText(pltxt),
        });
      }

      Object.values(node).forEach(walk);
    }

    walk(payload);
    return records;
  }

  function getCaseInsensitive(obj, keys) {
    if (!obj || typeof obj !== "object") return "";

    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      if (Object.prototype.hasOwnProperty.call(obj, key)) return obj[key];
    }

    const loweredMap = new Map(Object.keys(obj).map((key) => [String(key).toLowerCase(), key]));

    for (let i = 0; i < keys.length; i += 1) {
      const key = String(keys[i]).toLowerCase();
      const actual = loweredMap.get(key);
      if (actual) return obj[actual];
    }

    return "";
  }

  async function fetchWithTimeout(url, timeoutMs, requestOptions) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    const externalSignal = requestOptions && requestOptions.signal;
    let abortHandler = null;

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
        credentials: requestOptions && requestOptions.includeCredentials === false ? "omit" : "include",
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return response;
    } finally {
      window.clearTimeout(timeoutId);
      if (externalSignal && abortHandler) {
        externalSignal.removeEventListener("abort", abortHandler);
      }
    }
  }

  async function fetchRecords(url, timeoutMs, requestOptions) {
    const response = await fetchWithTimeout(url, timeoutMs, requestOptions || null);
    const payload = await response.json();
    return extractRecords(payload);
  }

  function resolveTimeoutMs(options) {
    return options && options.timeoutMs ? options.timeoutMs : 12000;
  }

  function resolveUseLocalProxy(options) {
    return options && Object.prototype.hasOwnProperty.call(options, "useLocalProxy")
      ? !!options.useLocalProxy
      : false;
  }

  function buildRequestCacheKey(fl, useLocalProxy, timeoutMs) {
    return `${normalizeUpper(fl)}|proxy:${useLocalProxy ? "1" : "0"}|timeout:${timeoutMs}`;
  }

  async function requestFunctionRecords(fl, options) {
    const timeoutMs = resolveTimeoutMs(options);
    const useLocalProxy = resolveUseLocalProxy(options);
    const signal = options && options.signal;
    const requestKey = buildRequestCacheKey(fl, useLocalProxy, timeoutMs);

    if (!signal && requestInFlight.has(requestKey)) {
      return requestInFlight.get(requestKey);
    }

    const task = (async () => {
      if (useLocalProxy) {
        try {
          return await fetchRecords(buildProxyFunctionUrl(fl), timeoutMs, {
            includeCredentials: false,
            signal,
          });
        } catch (_) {
        }
      }

      try {
        return await fetchRecords(buildFunctionUrl(fl, true, true), timeoutMs, { signal });
      } catch (errorDollarQuoted) {
        try {
          return await fetchRecords(buildFunctionUrl(fl, false, true), timeoutMs, { signal });
        } catch (errorFormatQuoted) {
          try {
            return await fetchRecords(buildFunctionUrl(fl, true, false), timeoutMs, { signal });
          } catch (errorDollarRaw) {
            try {
              return await fetchRecords(buildFunctionUrl(fl, false, false), timeoutMs, { signal });
            } catch (errorFormatRaw) {
              throw errorFormatRaw || errorDollarRaw || errorFormatQuoted || errorDollarQuoted;
            }
          }
        }
      }
    })();

    if (!signal) {
      requestInFlight.set(requestKey, task);
      task.finally(() => {
        requestInFlight.delete(requestKey);
      });
    }

    return task;
  }

  async function lookupFunctionalLocation(fl, options) {
    const normalized = normalizeUpper(fl);

    if (!normalized) {
      return { ok: false, exists: false, error: "Empty Functional Location." };
    }

    const timeoutMs = resolveTimeoutMs(options);
    const useLocalProxy = resolveUseLocalProxy(options);
    const signal = options && options.signal;
    const now = Date.now();
    const cacheKey = buildRequestCacheKey(normalized, useLocalProxy, timeoutMs);

    const cached = lookupCache.get(cacheKey);
    if (cached && now - cached.ts <= ODATA_LOOKUP_CACHE_MS) {
      touchMapKey(lookupCache, cacheKey);
      return {
        ok: true,
        exists: cached.exists,
        pltxt: cached.pltxt,
        records: cached.records.slice(),
      };
    }

    if (!signal && lookupInFlight.has(cacheKey)) {
      return lookupInFlight.get(cacheKey);
    }

    const task = (async () => {
      try {
        const records = await requestFunctionRecords(normalized, {
          ...(options || {}),
          timeoutMs,
          useLocalProxy,
          signal,
        });
        const exact = records.find((record) => normalizeUpper(record.tplnr) === normalized);
        const result = {
          ok: true,
          exists: !!exact,
          pltxt: exact ? toText(exact.pltxt) : "",
          records,
        };

        if (!signal) {
          lookupCache.set(cacheKey, {
            exists: result.exists,
            pltxt: result.pltxt,
            records: result.records,
            ts: Date.now(),
          });
          trimLruMap(lookupCache, ODATA_CACHE_MAX_ENTRIES);
        }

        return result;
      } catch (error) {
        return {
          ok: false,
          exists: false,
          pltxt: "",
          records: [],
          error: error && error.message ? error.message : String(error),
        };
      }
    })();

    if (!signal) {
      lookupInFlight.set(cacheKey, task);
      task.finally(() => {
        lookupInFlight.delete(cacheKey);
      });
    }

    return task;
  }

  function buildFallbackCandidates(normalizedQuery, maxSteps) {
    const list = [];
    let query = normalizedQuery;

    for (let step = 0; step <= maxSteps; step += 1) {
      if (!query) break;
      if (!list.includes(query)) list.push(query);
      query = query.slice(0, -1);
    }

    return list;
  }

  function rankSuggestions(records, query) {
    const normalizedQuery = normalizeUpper(query);
    const compactQuery = normalizedQuery.replace(/\s+/g, "");

    const dedup = new Map();
    records.forEach((record) => {
      const key = normalizeUpper(record.tplnr);
      if (!key || dedup.has(key)) return;
      dedup.set(key, {
        tplnr: key,
        pltxt: toText(record.pltxt),
      });
    });

    return Array.from(dedup.values())
      .filter((record) => {
        const compact = record.tplnr.replace(/\s+/g, "");
        return record.tplnr.includes(normalizedQuery) || compact.includes(compactQuery);
      })
      .sort((a, b) => {
        const aStarts = a.tplnr.startsWith(normalizedQuery) ? 0 : 1;
        const bStarts = b.tplnr.startsWith(normalizedQuery) ? 0 : 1;
        if (aStarts !== bStarts) return aStarts - bStarts;
        if (a.tplnr.length !== b.tplnr.length) return a.tplnr.length - b.tplnr.length;
        return a.tplnr.localeCompare(b.tplnr);
      });
  }

  async function searchFunctionalLocations(query, options) {
    const normalized = normalizeUpper(query).replace(/\s+/g, " ").trim();
    const minChars = options && options.minChars ? Number(options.minChars) : 7;

    if (!normalized || normalized.length < minChars) {
      return [];
    }

    const timeoutMs = resolveTimeoutMs(options);
    const useLocalProxy = resolveUseLocalProxy(options);
    const signal = options && options.signal;
    const limit = options && options.limit ? Number(options.limit) : 15;
    const clampedLimit = Math.max(1, limit);
    const signature = buildSearchCacheSignature(useLocalProxy, timeoutMs);
    const cacheKey = buildSearchCacheKey(normalized, signature);
    const now = Date.now();

    const exactCache = searchCache.get(cacheKey);
    if (exactCache && now - exactCache.ts <= ODATA_SUGGEST_CACHE_MS) {
      touchMapKey(searchCache, cacheKey);
      return rankSuggestions(exactCache.items, normalized).slice(0, clampedLimit);
    }

    const warmCached = readWarmSearchCache(normalized, signature, now);
    if (warmCached.length) {
      return warmCached.slice(0, clampedLimit);
    }

    if (!signal && searchInFlight.has(cacheKey)) {
      return searchInFlight.get(cacheKey);
    }

    const maxFallbackSteps = options && Number.isFinite(options.maxFallbackSteps) ? options.maxFallbackSteps : 2;
    const candidates = buildFallbackCandidates(normalized, Math.max(0, maxFallbackSteps));

    const task = (async () => {
      let merged = [];
      for (let i = 0; i < candidates.length; i += 1) {
        const candidate = candidates[i];
        try {
          const records = await requestFunctionRecords(candidate, {
            ...(options || {}),
            timeoutMs,
            useLocalProxy,
            signal,
          });
          merged = mergeRecords(merged, records);
          const ranked = rankSuggestions(merged, normalized);
          if (ranked.length) {
            if (!signal) {
              searchCache.set(cacheKey, { query: normalized, signature, items: ranked, ts: Date.now() });
              trimLruMap(searchCache, ODATA_CACHE_MAX_ENTRIES);
            }
            return ranked.slice(0, clampedLimit);
          }
        } catch (_) {
        }
      }

      if (!signal) {
        searchCache.set(cacheKey, { query: normalized, signature, items: [], ts: Date.now() });
        trimLruMap(searchCache, ODATA_CACHE_MAX_ENTRIES);
      }

      return [];
    })();

    if (!signal) {
      searchInFlight.set(cacheKey, task);
      task.finally(() => {
        searchInFlight.delete(cacheKey);
      });
    }

    return task;
  }

  function mergeRecords(base, next) {
    const map = new Map();

    base.forEach((record) => {
      const key = normalizeUpper(record.tplnr);
      if (!key || map.has(key)) return;
      map.set(key, record);
    });

    next.forEach((record) => {
      const key = normalizeUpper(record.tplnr);
      if (!key || map.has(key)) return;
      map.set(key, record);
    });

    return Array.from(map.values());
  }

  function buildSearchCacheSignature(useLocalProxy, timeoutMs) {
    return `proxy:${useLocalProxy ? "1" : "0"}|timeout:${timeoutMs}`;
  }

  function buildSearchCacheKey(normalizedQuery, signature) {
    return `${normalizedQuery}|${signature}`;
  }

  function readWarmSearchCache(normalizedQuery, signature, now) {
    let best = null;

    for (const [key, value] of searchCache.entries()) {
      if (!value || !Array.isArray(value.items)) continue;
      if (value.signature !== signature) continue;
      if (now - value.ts > ODATA_SUGGEST_CACHE_MS) continue;
      if (!normalizedQuery.startsWith(value.query)) continue;
      if (!best || value.query.length > best.query.length) {
        best = { key, query: value.query, items: value.items };
      }
    }

    if (!best) return [];
    touchMapKey(searchCache, best.key);
    return rankSuggestions(best.items, normalizedQuery);
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

  function clearCaches() {
    lookupCache.clear();
    requestInFlight.clear();
    lookupInFlight.clear();
    searchCache.clear();
    searchInFlight.clear();
  }

  function formatLookupError(message, isProxyMode) {
    const text = toText(message);
    const lower = text.toLowerCase();

    if (!text) return "SAP lookup unavailable.";

    if (lower.includes("failed to fetch") || lower.includes("networkerror") || lower.includes("err_aborted")) {
      return `${text} (browser CORS/auth or network)`;
    }

    if (lower.includes("401")) {
      return `${text} (SAP login/session missing in browser)`;
    }

    if (isProxyMode) {
      return `${text} (via local proxy)`;
    }

    return text;
  }

  async function probeConnection(options) {
    const probeFl = "HEV120";

    try {
      await requestFunctionRecords(probeFl, options || null);
      return { ok: true, error: "" };
    } catch (error) {
      return {
        ok: false,
        error: error && error.message ? error.message : String(error),
      };
    }
  }

  window.OrstedOData = {
    lookupFunctionalLocation,
    searchFunctionalLocations,
    formatLookupError,
    probeConnection,
    clearCaches,
  };
})();

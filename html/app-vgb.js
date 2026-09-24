(function () {
  const { toText } = window.TextUtils;

  const SOURCE_TEXT_URL = "data/vgb-docx-extract.txt";
  const CODE_PATTERN = /^(?:[A-Z]{2,3}|[A-Z]{2,3}\d{1,2}|-[A-Z0-9]{1,3})$/;
  const SKIP_PATTERNS = [/^VGB-B/i, /^Kilde:/i, /^(?:Del|Teil)\s+\d+/i, /^Tysk$/i, /^Dansk$/i];
  const SECTION_BY_MODE = {
    aggregate: 2,
    component: 3,
  };
  const CP1252_TO_BYTE = {
    0x20ac: 0x80,
    0x201a: 0x82,
    0x0192: 0x83,
    0x201e: 0x84,
    0x2026: 0x85,
    0x2020: 0x86,
    0x2021: 0x87,
    0x02c6: 0x88,
    0x2030: 0x89,
    0x0160: 0x8a,
    0x2039: 0x8b,
    0x0152: 0x8c,
    0x017d: 0x8e,
    0x2018: 0x91,
    0x2019: 0x92,
    0x201c: 0x93,
    0x201d: 0x94,
    0x2022: 0x95,
    0x2013: 0x96,
    0x2014: 0x97,
    0x02dc: 0x98,
    0x2122: 0x99,
    0x0161: 0x9a,
    0x203a: 0x9b,
    0x0153: 0x9c,
    0x017e: 0x9e,
    0x0178: 0x9f,
  };

  // Lead sequences left behind when UTF-8 bytes are re-read as CP1252.
  const MOJIBAKE_PATTERN = /[\u00C2\u00C3]|\u00E2(?:\u20AC|\u201E)/;

  document.addEventListener("DOMContentLoaded", initVgb);

  async function initVgb() {
    const mode = resolveSectionMode();
    setPreviewText("Indlaeser VGB data...");

    try {
      const lines = await loadSourceLines();
      const rows = buildRowsForMode(lines, mode);
      const data = groupRowsAsKksData(dedupeRows(rows), mode);

      if (!Array.isArray(data) || data.length === 0) {
        throw new Error("No VGB rows could be parsed from source text.");
      }

      window.KKS_DATA = data;
      setPreviewText("Vaelg en sektion");
      await loadKksAppScript();
    } catch (error) {
      window.KKS_DATA = buildFallbackData(mode);
      setPreviewText("VGB data kunne ikke indlaeses. Viser fallback-data.");
      await loadKksAppScript();
    }
  }

  function resolveSectionMode() {
    const value = toText(document.body && document.body.dataset ? document.body.dataset.vgbSection : "").toLowerCase();
    if (value === "component") {
      return value;
    }
    return "aggregate";
  }

  async function loadSourceLines() {
    const inlineLines = getInlineSourceLines();
    if (inlineLines.length > 0) {
      return inlineLines;
    }

    let lastError = null;

    try {
      const response = await fetch(SOURCE_TEXT_URL, { cache: "no-cache" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const buffer = await response.arrayBuffer();
      const text = decodeSourceBuffer(buffer);
      const lines = toNormalizedLines(text);
      if (lines.length > 0) {
        return lines;
      }
      throw new Error("Decoded source text did not contain parseable lines.");
    } catch (error) {
      lastError = error;
    }

    try {
      const iframeText = await loadSourceTextViaIFrame();
      const lines = toNormalizedLines(iframeText);
      if (lines.length > 0) {
        return lines;
      }
      throw new Error("IFrame fallback returned no parseable lines.");
    } catch (error) {
      const fallbackError = error instanceof Error ? error.message : String(error);
      const fetchError = lastError instanceof Error ? lastError.message : String(lastError || "Unknown fetch error");
      throw new Error(`Failed to load VGB source via fetch (${fetchError}) and iframe fallback (${fallbackError}).`);
    }
  }

  function getInlineSourceLines() {
    const raw = window.__VGB_SOURCE_LINES;
    if (!Array.isArray(raw) || raw.length === 0) {
      return [];
    }

    return raw
      .map((line) => normalizeLine(line))
      .filter((line) => line.length > 0);
  }

  function toNormalizedLines(text) {
    return String(text == null ? "" : text)
      .split(/\r?\n/)
      .map((line) => normalizeLine(line))
      .filter((line) => line.length > 0);
  }

  function decodeSourceBuffer(buffer) {
    const bytes = new Uint8Array(buffer);
    const candidates = [];

    if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
      candidates.push(safeDecode(bytes, "utf-8"));
    }

    if (bytes.length >= 2 && bytes[0] === 0xff && bytes[1] === 0xfe) {
      candidates.push(safeDecode(bytes, "utf-16le"));
    }

    if (bytes.length >= 2 && bytes[0] === 0xfe && bytes[1] === 0xff) {
      candidates.push(safeDecode(bytes, "utf-16be"));
    }

    candidates.push(safeDecode(bytes, "utf-8"));
    candidates.push(safeDecode(bytes, "utf-16le"));
    candidates.push(safeDecode(bytes, "utf-16be"));
    candidates.push(safeDecode(bytes, "windows-1252"));

    const ranked = candidates
      .filter((item) => item && item.text)
      .map((item) => ({
        text: item.text,
        score: scoreDecodedText(item.text),
      }))
      .sort((a, b) => b.score - a.score);

    if (ranked.length === 0) {
      return "";
    }

    return ranked[0].text;
  }

  function safeDecode(bytes, encoding) {
    try {
      return {
        encoding,
        text: new TextDecoder(encoding, { fatal: false }).decode(bytes),
      };
    } catch (_error) {
      return null;
    }
  }

  function scoreDecodedText(text) {
    const value = String(text == null ? "" : text);
    if (!value) return Number.NEGATIVE_INFINITY;

    let score = 0;
    if (/(?:Del|Teil)\s+1\s*-\s*(?:Termliste|Begriffsliste)/i.test(value)) score += 20;
    if (/(?:Del|Teil)\s+2\s*-\s*Aggregateliste/i.test(value)) score += 50;
    if (/(?:Del|Teil)\s+3\s*-\s*(?:Driftmiddelliste|Betriebsmittelliste)/i.test(value)) score += 50;
    if (/\bTysk\b/i.test(value)) score += 10;
    if (/\bDansk\b/i.test(value)) score += 10;
    if (/\u0000/.test(value)) score -= 80;

    const lines = value.split(/\r?\n/).length;
    if (lines > 3000) score += 15;
    return score;
  }

  function loadSourceTextViaIFrame() {
    return new Promise((resolve, reject) => {
      const frame = document.createElement("iframe");
      frame.hidden = true;
      frame.src = SOURCE_TEXT_URL;

      const cleanup = () => {
        if (frame.parentNode) {
          frame.parentNode.removeChild(frame);
        }
      };

      const fail = (message) => {
        cleanup();
        reject(new Error(message));
      };

      const timer = window.setTimeout(() => {
        fail("IFrame source load timed out.");
      }, 6000);

      frame.onload = () => {
        window.clearTimeout(timer);
        try {
          const doc = frame.contentDocument;
          const body = doc && doc.body ? doc.body : null;
          const text = body ? body.innerText || body.textContent || "" : "";
          cleanup();
          if (!text) {
            reject(new Error("IFrame source body was empty."));
            return;
          }
          resolve(text);
        } catch (error) {
          fail(`IFrame source access failed: ${error instanceof Error ? error.message : String(error)}`);
        }
      };

      frame.onerror = () => {
        window.clearTimeout(timer);
        fail("IFrame source load failed.");
      };

      document.body.appendChild(frame);
    });
  }

  function normalizeLine(value) {
    const trimmed = String(value == null ? "" : value).replace(/\u0000/g, "").trim();
    if (!trimmed) return "";

    const repaired = repairMojibakeUtf8(trimmed);
    const normalized = repairBrokenGlyphs(repaired);
    return normalized.replace(/\s+/g, " ").trim();
  }

  function repairBrokenGlyphs(value) {
    let text = String(value == null ? "" : value);

    text = text
      .replace(/\uFFFD\u0013/g, "Ö")
      .replace(/\uFFFDS/g, "Ü")
      .replace(/\uFFFDx/g, "ß")
      .replace(/\uFFFDX/g, "ß");

    text = text.replace(/[\u200B-\u200D\uFEFF]/g, "");
    text = text.replace(/[\u0001-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
    return text;
  }

  function repairMojibakeUtf8(value) {
    const text = String(value == null ? "" : value);
    if (!MOJIBAKE_PATTERN.test(text)) return text;

    const bytes = [];

    for (const char of text) {
      const codePoint = char.codePointAt(0);
      if (codePoint == null) return text;

      if (codePoint <= 0xff) {
        bytes.push(codePoint);
        continue;
      }

      const mapped = CP1252_TO_BYTE[codePoint];
      if (mapped == null) return text;
      bytes.push(mapped);
    }

    let decoded;
    try {
      // fatal:true makes a partially-encoded line throw instead of losing characters to U+FFFD.
      decoded = new TextDecoder("utf-8", { fatal: true }).decode(Uint8Array.from(bytes));
    } catch (_error) {
      return text;
    }

    if (!decoded || decoded.indexOf("\uFFFD") >= 0) return text;
    return decoded;
  }

  function shouldSkipLine(value) {
    for (let index = 0; index < SKIP_PATTERNS.length; index += 1) {
      if (SKIP_PATTERNS[index].test(value)) return true;
    }
    return false;
  }

  function isCodeLine(value) {
    return CODE_PATTERN.test(toText(value).toUpperCase());
  }

  function buildRowsForMode(lines, mode) {
    const sections = splitIntoSections(lines);
    const sectionNumber = SECTION_BY_MODE[mode] || 2;
    const sectionLines = sections.get(sectionNumber) || [];
    const sourceLabel = `VGB-B 105.1 Del ${sectionNumber}`;
    return parseSectionTwoOrThreeRows(sectionLines, sourceLabel);
  }

  function splitIntoSections(lines) {
    const sections = new Map([
      [2, []],
      [3, []],
    ]);

    let activeSection = 0;
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      if (!line) continue;

      const marker = line.match(/^(?:Del|Teil)\s+([23])\b/i);
      if (marker) {
        activeSection = Number(marker[1]);
        continue;
      }

      if (!activeSection || !sections.has(activeSection)) {
        continue;
      }

      sections.get(activeSection).push(line);
    }

    return sections;
  }

  function parseSectionTwoOrThreeRows(lines, sourceLabel) {
    const rows = [];
    let code = "";
    let german = "";

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      if (!line || shouldSkipLine(line)) continue;

      if (!code) {
        if (isCodeLine(line)) {
          code = line.toUpperCase();
        }
        continue;
      }

      if (!german) {
        if (isCodeLine(line)) {
          code = line.toUpperCase();
          continue;
        }
        german = line;
        continue;
      }

      if (isCodeLine(line)) {
        code = line.toUpperCase();
        german = "";
        continue;
      }

      const danish = line;
      rows.push({
        code,
        description: danish,
        german,
        searchText: danish,
        sourceLabel,
      });

      code = "";
      german = "";
    }

    return rows;
  }

  function dedupeRows(rows) {
    const seen = new Set();
    const output = [];

    rows.forEach((row) => {
      const code = toText(row.code).toUpperCase();
      const description = toText(row.description);
      const german = toText(row.german);
      const searchText = toText(row.searchText) || description;
      if (!code || !description || !german) return;

      const fingerprint = `${code}||${description.toUpperCase()}||${german.toUpperCase()}`;
      if (seen.has(fingerprint)) return;
      seen.add(fingerprint);

      output.push({
        code,
        description,
        german,
        searchText,
        sourceLabel: toText(row.sourceLabel) || "VGB-B 105.1",
      });
    });

    return output;
  }

  function groupRowsAsKksData(rows, mode) {
    const bySection = new Map();

    rows.forEach((row) => {
      const code = toText(row.code).toUpperCase();
      let sectionKey = /^[A-Z]/.test(code) ? code.slice(0, 1) : "SYM";

      if (mode === "component" && /^-[A-Z]/.test(code)) {
        sectionKey = code.slice(0, 2);
      }

      if (!bySection.has(sectionKey)) {
        bySection.set(sectionKey, []);
      }
      bySection.get(sectionKey).push(row);
    });

    const orderedAlphaKeys = [];
    for (let code = 65; code <= 90; code += 1) {
      orderedAlphaKeys.push(String.fromCharCode(code));
    }

    const symbolKeys = Array.from(bySection.keys())
      .filter((key) => !orderedAlphaKeys.includes(key) && key !== "SYM")
      .sort((a, b) => a.localeCompare(b));

    const orderedKeys = orderedAlphaKeys.concat(symbolKeys);
    if (bySection.has("SYM")) {
      orderedKeys.push("SYM");
    }

    const sections = [];
    orderedKeys.forEach((key) => {
      if (!bySection.has(key)) return;

      const sectionRows = bySection
        .get(key)
        .slice()
        .sort((a, b) => {
          const codeRank = a.code.localeCompare(b.code);
          if (codeRank !== 0) return codeRank;
          return a.description.localeCompare(b.description);
        });

      sections.push({
        key,
        fileName: `${key}.aspx`,
        title: key === "SYM" ? "Special" : key,
        rows: sectionRows,
      });
    });

    return sections;
  }

  function buildFallbackData(mode) {
    const sectionNumber = SECTION_BY_MODE[mode] || 2;
    return [
      {
        key: "V",
        fileName: "V.aspx",
        title: "V",
        rows: [
          {
            code: "VGB",
            description: `VGB source could not be parsed from docx extraction (Del ${sectionNumber}).`,
            german: "-",
            searchText: "VGB source",
            sourceLabel: `VGB-B 105.1 Del ${sectionNumber}`,
          },
        ],
      },
      {
        key: "HOME",
        fileName: "Home.aspx",
        title: "VGB term list",
        rows: [
          { code: "V", description: "VGB fallback section" },
        ],
      },
    ];
  }

  function setPreviewText(message) {
    const title = document.getElementById("kksPreviewTitle");
    if (title) {
      title.textContent = message;
    }
  }

  function loadKksAppScript() {
    return new Promise((resolve, reject) => {
      if (window.__kksAppLoaded) {
        resolve();
        return;
      }

      const script = document.createElement("script");
      script.src = "js/app-kks.js";
      script.async = false;
      script.onload = () => {
        window.__kksAppLoaded = true;
        resolve();
      };
      script.onerror = () => {
        reject(new Error("Failed to load app-kks.js"));
      };
      document.body.appendChild(script);
    });
  }
})();

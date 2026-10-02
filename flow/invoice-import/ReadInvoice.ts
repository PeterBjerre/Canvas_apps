/*
 * ReadInvoice - Office Script til BIO SAP, Materials: "Import invoice".
 *
 * Laeser en faktura - en PDF med tekst eller en OIOUBL/Peppol-XML - og
 * svarer med fakturaens linjer som JSON. Flowet BioSap-Material-ReadInvoice
 * koerer det med Excel Online (Business) > "Run script from SharePoint
 * library", og appen laegger linjerne ind som kladderaekker i en ny
 * anmodning. Se docs/34-faktura-import.md.
 *
 * HVORFOR ET OFFICE SCRIPT
 * ------------------------
 * Power Automate kan ikke selv pakke en PDF ud: der er ingen standardhandling,
 * der dekomprimerer en PDF-stroem eller laeser dens tekst. AI Builder kan,
 * men AI Builder er PREMIUM. Excel Online (Business) er en STANDARD-connector,
 * og "Run script" koerer TypeScript - saa laesningen staar her, i ren kode,
 * uden eksterne kald (dem tillader Power Automate heller ikke i et script).
 *
 * Det betyder ogsaa graensen: en SCANNET faktura (et billede) har ingen
 * tekst, og den kan kun laeses med OCR - dvs. AI Builder. Scriptet siger det
 * i stedet for at gaette.
 *
 * KONTRAKTEN
 * ----------
 *     ind  fileName      filens navn (kun til at kende typen)
 *          fileContent   filen som base64 - triggerens file.contentBytes
 *     ud   en JSON-STRENG: InvoiceResult nedenfor
 *
 * Feltnavnene staar ogsaa i "Material App/build/invoice_parts.py", og
 * tools/invoice/harness.mjs stopper byggeriet, hvis de to glider fra
 * hinanden. Ret aldrig et navn det ene sted.
 *
 * REGLER FOR OFFICE SCRIPTS (TypeScript 4.0)
 * ------------------------------------------
 * Ingen "any" (heller ikke underforstaaet), kun pilefunktioner som
 * argument til Array-metoder, ingen eval, ingen TextDecoder/atob (findes
 * ikke, naar Power Automate koerer scriptet). Kildeteksten er ren ASCII,
 * saa den kan kopieres ind i Excels kodeeditor uden tegnsaetsfejl - de
 * danske bogstaver staar som \u-koder.
 */

function main(workbook: ExcelScript.Workbook, fileName: string, fileContent: string): string {
  // ALT STAAR INDEN I main. Office Scripts koerer main - og Microsoft
  // skriver selv, at kode uden for en funktion ikke koeres. En konstant
  // paa oeverste niveau kunne dermed vaere udefineret, naar main bruger
  // den. Herinde koeres hver erklaering, foer readInvoice kaldes nederst.

  // ===========================================================================
  // Kontrakten
  // ===========================================================================
  interface InvoiceLine {
    lineNo: number;
    description: string;
    extraText: string;
    supplierPartNo: string;
    manufacturer: string;
    manufacturerPartNo: string;
    model: string;
    gtin: string;
    quantity: number | null;
    unit: string;
    unitPrice: number | null;
    priceUnit: number | null;
    discountPct: number | null;
    amount: number | null;
    isCharge: boolean;
    check: string;
  }

  interface InvoiceResult {
    ok: boolean;
    error: string;
    version: string;
    source: string;
    format: string;
    fileName: string;
    supplierName: string;
    supplierVatNo: string;
    invoiceNo: string;
    invoiceDate: string;
    orderNo: string;
    currency: string;
    netTotal: number | null;
    linesTotal: number | null;
    plantHint: string;
    pages: number;
    lines: InvoiceLine[];
    warnings: string[];
    text: string;
  }

  const READER_VERSION = "1.0";
  // Saa meget af den laeste tekst sendes med tilbage - nok til at se, hvad
  // der blev laest, og lille nok til ikke at fylde i appen.
  const MAX_TEXT = 6000;

  // ===========================================================================
  // Indgangen
  // ===========================================================================
  let lastError = "";

  function fail(msg: string): never {
    lastError = msg;
    throw new Error(msg);
  }

  function readInvoice(fileName: string, fileContent: string): InvoiceResult {
    lastError = "";
    const res = newResult(fileName);
    try {
      const bytes = decodeInput(fileContent || "");
      if (bytes.length === 0) {
        res.error = "The file is empty.";
        return res;
      }
      const kind = sniff(bytes, fileName || "");
      if (kind === "pdf") {
        readPdfInvoice(bytes, res);
      } else if (kind === "xml") {
        readXmlInvoice(bytes, res);
      } else {
        res.error = "Only PDF and XML invoices (OIOUBL/Peppol) can be read.";
        return res;
      }
      finishResult(res);
      res.ok = res.error === "";
    } catch {
      res.ok = false;
      res.error = "The invoice could not be read: " + (lastError || "unexpected content.");
    }
    return res;
  }

  function newResult(fileName: string): InvoiceResult {
    return {
      ok: false, error: "", version: READER_VERSION, source: "", format: "",
      fileName: fileName || "", supplierName: "", supplierVatNo: "", invoiceNo: "",
      invoiceDate: "", orderNo: "", currency: "", netTotal: null, linesTotal: null,
      plantHint: "", pages: 0, lines: [], warnings: [], text: ""
    };
  }

  function finishResult(res: InvoiceResult): void {
    let sum = 0;
    let have = false;
    for (let i = 0; i < res.lines.length; i++) {
      const l = res.lines[i];
      l.lineNo = i + 1;
      if (l.amount !== null) {
        sum += l.amount;
        have = true;
      }
    }
    res.linesTotal = have ? round(sum, 2) : null;
    if (res.netTotal !== null && res.linesTotal !== null && res.lines.length > 0) {
      const diff = Math.abs(res.netTotal - res.linesTotal);
      if (diff > Math.max(0.05, Math.abs(res.netTotal) * 0.005)) {
        res.warnings.push("The lines add up to " + fmtNum(res.linesTotal) + ", but the invoice subtotal is "
          + fmtNum(res.netTotal) + ". Check that no lines are missing.");
      }
    }
    // Negative beloeb er krediteringer og rabatter. Er ALLE linjer negative,
    // er det en kreditnota, og den har sin egen advarsel.
    const neg = res.lines.filter((l) => l.amount !== null && l.amount < 0).length;
    const charges = res.lines.filter((l) => l.isCharge).length - neg;
    if (charges > 0) {
      res.warnings.push(charges + " line(s) look like freight, fees or services and are not selected.");
    }
    if (neg > 0 && neg < res.lines.length) {
      res.warnings.push(neg + " line(s) have a negative amount (a credit or discount) and are not selected.");
    }
    const bad = res.lines.filter((l) => l.check === "mismatch").length;
    if (bad > 0) {
      res.warnings.push(bad + " line(s): quantity x price does not match the amount - check them.");
    }
    if (res.lines.length === 0 && res.error === "" && res.text !== "") {
      res.warnings.push("No invoice lines were recognised. Create the rows by hand - or use the XML version of the invoice, if the supplier sends one.");
    }
    if (res.text.length > MAX_TEXT) {
      res.text = res.text.substring(0, MAX_TEXT) + "\n...";
    }
  }

  // ===========================================================================
  // Bytes og tegn
  // ===========================================================================
  interface ContentEnvelope {
    "$content"?: string;
  }

  // Flowet sender file.contentBytes - base64. Men Power Automate kan ogsaa
  // finde paa at sende { "$content": ... } eller selve teksten, saa alle tre
  // former tages imod.
  function decodeInput(content: string): Uint8Array {
    let i = 0;
    while (i < content.length && (content.charCodeAt(i) <= 32 || content.charCodeAt(i) === 0xfeff)) {
      i++;
    }
    let s = content.substring(i);
    if (s.charAt(0) === "{") {
      try {
        const env = JSON.parse(s) as ContentEnvelope;
        if (env && typeof env["$content"] === "string") {
          s = env["$content"];
        }
      } catch {
        // ikke JSON - videre som tekst
      }
    }
    if (s.substring(0, 5) === "data:") {
      const c = s.indexOf(",");
      if (c >= 0) {
        s = s.substring(c + 1);
      }
    }
    if (s.substring(0, 5) === "%PDF-" || s.charAt(0) === "<") {
      return stringToBytes(s);
    }
    return base64ToBytes(s);
  }

  const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

  function base64ToBytes(s: string): Uint8Array {
    const lookup: number[] = [];
    for (let i = 0; i < 256; i++) {
      lookup.push(-1);
    }
    for (let i = 0; i < 64; i++) {
      lookup[B64.charCodeAt(i)] = i;
    }
    lookup[45] = 62; // -  (base64url)
    lookup[95] = 63; // _
    const out = new Uint8Array(Math.floor(s.length * 3 / 4) + 3);
    let n = 0;
    let buf = 0;
    let bits = 0;
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      if (c > 255) {
        continue;
      }
      const v = lookup[c];
      if (v < 0) {
        continue; // linjeskift, mellemrum og =
      }
      buf = (buf << 6) | v;
      bits += 6;
      if (bits >= 8) {
        bits -= 8;
        out[n++] = (buf >> bits) & 0xff;
        buf &= (1 << bits) - 1;
      }
    }
    return out.subarray(0, n);
  }

  function stringToBytes(s: string): Uint8Array {
    const out: number[] = [];
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      if (c < 256) {
        out.push(c);
      } else if (c < 0x800) {
        out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
      } else {
        out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
      }
    }
    return new Uint8Array(out);
  }

  function codesToString(codes: number[]): string {
    const parts: string[] = [];
    for (let i = 0; i < codes.length; i += 8192) {
      parts.push(String.fromCharCode.apply(null, codes.slice(i, i + 8192)));
    }
    return parts.join("");
  }

  function bytesToLatin1(b: Uint8Array, start: number, end: number): string {
    const parts: string[] = [];
    for (let i = start; i < end; i += 8192) {
      const n = Math.min(8192, end - i);
      const codes: number[] = [];
      for (let j = 0; j < n; j++) {
        codes.push(b[i + j]);
      }
      parts.push(String.fromCharCode.apply(null, codes));
    }
    return parts.join("");
  }

  function latin1(b: Uint8Array): string {
    return bytesToLatin1(b, 0, b.length);
  }

  function latin1ToBytes(s: string): Uint8Array {
    const out = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) {
      out[i] = s.charCodeAt(i) & 0xff;
    }
    return out;
  }

  // UTF-8 uden TextDecoder. invalid != 0 betyder, at noget ikke var UTF-8.
  interface Decoded {
    text: string;
    invalid: number;
  }

  function utf8Decode(b: Uint8Array, start: number): Decoded {
    const parts: string[] = [];
    let chunk: number[] = [];
    let invalid = 0;
    let i = start;
    const end = b.length;
    while (i < end) {
      const c = b[i];
      let cp = 0xfffd;
      let n = 1;
      if (c < 0x80) {
        cp = c;
      } else if (c >= 0xc2 && c < 0xe0 && i + 1 < end && (b[i + 1] & 0xc0) === 0x80) {
        cp = ((c & 0x1f) << 6) | (b[i + 1] & 0x3f);
        n = 2;
      } else if (c >= 0xe0 && c < 0xf0 && i + 2 < end && (b[i + 1] & 0xc0) === 0x80
        && (b[i + 2] & 0xc0) === 0x80) {
        cp = ((c & 0x0f) << 12) | ((b[i + 1] & 0x3f) << 6) | (b[i + 2] & 0x3f);
        n = 3;
      } else if (c >= 0xf0 && c < 0xf5 && i + 3 < end && (b[i + 1] & 0xc0) === 0x80
        && (b[i + 2] & 0xc0) === 0x80 && (b[i + 3] & 0xc0) === 0x80) {
        cp = ((c & 0x07) << 18) | ((b[i + 1] & 0x3f) << 12) | ((b[i + 2] & 0x3f) << 6) | (b[i + 3] & 0x3f);
        n = 4;
      } else {
        invalid++;
      }
      if (cp > 0xffff) {
        cp -= 0x10000;
        chunk.push(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff));
      } else {
        chunk.push(cp);
      }
      i += n;
      if (chunk.length >= 8192) {
        parts.push(String.fromCharCode.apply(null, chunk));
        chunk = [];
      }
    }
    parts.push(String.fromCharCode.apply(null, chunk));
    return { text: parts.join(""), invalid: invalid };
  }

  // Windows-1252: Latin-1 plus de 27 tegn i 0x80-0x9F.
  const CP1252_HIGH: number[] = [
    0x20ac, 0, 0x201a, 0x0192, 0x201e, 0x2026, 0x2020, 0x2021, 0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0, 0x017d, 0,
    0, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014, 0x02dc, 0x2122, 0x0161, 0x203a, 0x0153, 0, 0x017e, 0x0178
  ];

  function cp1252Decode(b: Uint8Array, start: number): string {
    const codes: number[] = [];
    for (let i = start; i < b.length; i++) {
      const c = b[i];
      codes.push(c >= 0x80 && c < 0xa0 ? (CP1252_HIGH[c - 0x80] || 0x3f) : c);
    }
    return codesToString(codes);
  }

  function sniff(b: Uint8Array, name: string): string {
    const head = bytesToLatin1(b, 0, Math.min(b.length, 1024));
    if (head.indexOf("%PDF-") >= 0) {
      return "pdf";
    }
    let p = 0;
    if (b.length >= 3 && b[0] === 0xef && b[1] === 0xbb && b[2] === 0xbf) {
      p = 3;
    }
    while (p < b.length && (b[p] === 32 || b[p] === 9 || b[p] === 10 || b[p] === 13)) {
      p++;
    }
    if (p < b.length && b[p] === 0x3c) {
      return "xml";
    }
    if (/\.pdf$/i.test(name) && bytesToLatin1(b, 0, Math.min(b.length, 65536)).indexOf("%PDF-") >= 0) {
      return "pdf";
    }
    return "";
  }

  // ===========================================================================
  // Tekstnormalisering
  // ===========================================================================
  // ae oe aa og accenter foldes til ASCII, saa ordlisterne kan staa i ASCII.
  const FOLD_FROM = "\u00e6\u00f8\u00e5\u00e4\u00f6\u00fc\u00df\u00e9\u00e8\u00ea\u00eb\u00e1\u00e0\u00e2\u00e3"
    + "\u00ed\u00ec\u00ee\u00ef\u00f3\u00f2\u00f4\u00f5\u00fa\u00f9\u00fb\u00e7\u00f1\u00fd\u00ff\u2212\u2013\u2014";
  const FOLD_TO: string[] = ["ae", "oe", "aa", "ae", "oe", "ue", "ss", "e", "e", "e", "e", "a", "a", "a", "a",
    "i", "i", "i", "i", "o", "o", "o", "o", "u", "u", "u", "c", "n", "y", "y", "-", "-", "-"];

  function fold(s: string): string {
    const low = s.toLowerCase();
    const parts: string[] = [];
    let start = 0;
    for (let i = 0; i < low.length; i++) {
      const c = low.charCodeAt(i);
      if (c < 0x80) {
        continue;
      }
      const k = FOLD_FROM.indexOf(low.charAt(i));
      parts.push(low.substring(start, i));
      parts.push(k >= 0 ? FOLD_TO[k] : low.charAt(i));
      start = i + 1;
    }
    parts.push(low.substring(start));
    return parts.join("");
  }

  // Et ord, som ordlisterne kender det: foldet, uden tegnsaetning.
  function normWord(s: string): string {
    return fold(s).replace(/[^a-z0-9%]/g, "");
  }

  function words(s: string): string[] {
    return s.split(/\s+/).filter((w) => w !== "");
  }

  function collapse(s: string): string {
    return s.replace(/[\s\u00a0]+/g, " ").trim();
  }

  function round(v: number, dec: number): number {
    const f = Math.pow(10, dec);
    return Math.round(v * f) / f;
  }

  function fmtNum(v: number): string {
    return round(v, 2).toFixed(2);
  }

  // ===========================================================================
  // Tal: 1.234,56  1,234.56  1 234,56  125,00-  (125,00)
  // ===========================================================================
  // Dansk og engelsk form. En tusindtalsgruppe er PRAECIS tre cifre - ellers
  // var "01.10.2026" et tal.
  const NUM_DA = /^(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$/;
  const NUM_EN = /^(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$/;

  function parseNumber(tok: string, dec: string): number | null {
    let t = tok.replace(/[\s\u00a0\u202f']/g, "");
    t = t.replace(/^(dkk|eur|usd|sek|nok|gbp|chf|kr\.?|\u20ac|\$|\u00a3)/i, "");
    t = t.replace(/(dkk|eur|usd|sek|nok|gbp|chf|kr\.?|,-|\u20ac|\$|\u00a3|%)$/i, "");
    if (t === "") {
      return null;
    }
    let neg = false;
    if (t.charAt(0) === "(" && t.charAt(t.length - 1) === ")") {
      neg = true;
      t = t.substring(1, t.length - 1);
    }
    if (t.charAt(t.length - 1) === "-") {
      neg = !neg;
      t = t.substring(0, t.length - 1);
    }
    if (t.charAt(0) === "-" || t.charAt(0) === "\u2212") {
      neg = !neg;
      t = t.substring(1);
    } else if (t.charAt(0) === "+") {
      t = t.substring(1);
    }
    if (/^[.,]\d+$/.test(t)) {
      t = "0" + t;
    }
    const da = NUM_DA.test(t);
    const en = NUM_EN.test(t);
    if (!da && !en) {
      return null;
    }
    // Begge former passer ("1.234", "1,234"): dokumentets decimaltegn afgoer.
    const useDa = da && en ? dec === "," : da;
    const norm = useDa ? t.replace(/\./g, "").replace(",", ".") : t.replace(/,/g, "");
    const v = parseFloat(norm);
    if (!isFinite(v)) {
      return null;
    }
    return neg ? -v : v;
  }

  // Decimaltegnet i hele dokumentet: "125,00" eller "125.00"? Datoer taeller ikke.
  function detectDecimal(text: string): string {
    const t = text.replace(/\b\d{1,4}[.\/-]\d{1,2}[.\/-]\d{2,4}\b/g, " ");
    const comma = (t.match(/\d,\d{2}(?!\d)/g) || []).length;
    const dot = (t.match(/\d\.\d{2}(?!\d)/g) || []).length;
    return dot > comma ? "." : ",";
  }

  // ===========================================================================
  // Datoer -> yyyy-mm-dd
  // ===========================================================================
  const MONTHS: string[][] = [
    ["jan", "januar", "january", "janvier"], ["feb", "februar", "february"],
    ["mar", "marts", "march", "maerz", "mrz"], ["apr", "april"], ["maj", "may", "mai"],
    ["jun", "juni", "june"], ["jul", "juli", "july"], ["aug", "august"],
    ["sep", "sept", "september"], ["okt", "oct", "oktober", "october"],
    ["nov", "november"], ["dec", "dez", "december", "dezember"]
  ];

  function monthOf(word: string): number {
    const w = normWord(word);
    for (let m = 0; m < MONTHS.length; m++) {
      if (MONTHS[m].indexOf(w) >= 0) {
        return m + 1;
      }
    }
    return 0;
  }

  function isoDate(y: number, m: number, d: number): string {
    if (y < 100) {
      y += 2000;
    }
    if (y < 1990 || y > 2100 || m < 1 || m > 12 || d < 1 || d > 31) {
      return "";
    }
    return y + "-" + (m < 10 ? "0" : "") + m + "-" + (d < 10 ? "0" : "") + d;
  }

  function parseDate(s: string): string {
    const t = s.trim();
    let m = /(\d{4})[-.\/](\d{1,2})[-.\/](\d{1,2})/.exec(t);
    if (m) {
      return isoDate(parseInt(m[1], 10), parseInt(m[2], 10), parseInt(m[3], 10));
    }
    m = /(\d{1,2})[-.\/](\d{1,2})[-.\/](\d{4}|\d{2})(?!\d)/.exec(t);
    if (m) {
      const a = parseInt(m[1], 10);
      const b = parseInt(m[2], 10);
      // Dag foerst (dansk og tysk). Kun hvis det ikke kan vaere en dag, er
      // det amerikansk maaned/dag.
      if (b > 12 && a <= 12) {
        return isoDate(parseInt(m[3], 10), a, b);
      }
      return isoDate(parseInt(m[3], 10), b, a);
    }
    m = /(\d{1,2})\.?\s*([A-Za-z\u00e4\u00c4]{3,9})\.?\s*(\d{4})/.exec(t);
    if (m && monthOf(m[2]) > 0) {
      return isoDate(parseInt(m[3], 10), monthOf(m[2]), parseInt(m[1], 10));
    }
    m = /([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})/.exec(t);
    if (m && monthOf(m[1]) > 0) {
      return isoDate(parseInt(m[3], 10), monthOf(m[1]), parseInt(m[2], 10));
    }
    return "";
  }

  // ===========================================================================
  // Inflate (zlib/deflate) - PDF'ens FlateDecode
  // ===========================================================================
  class ByteBuf {
    a: Uint8Array;
    n: number;
    constructor(cap: number) {
      this.a = new Uint8Array(Math.max(cap, 256));
      this.n = 0;
    }
    push(b: number): void {
      if (this.n >= this.a.length) {
        const bigger = new Uint8Array(this.a.length * 2);
        bigger.set(this.a);
        this.a = bigger;
      }
      this.a[this.n++] = b;
    }
    copyBack(dist: number, len: number): void {
      if (dist > this.n || dist <= 0) {
        fail("damaged compressed stream");
      }
      for (let i = 0; i < len; i++) {
        this.push(this.a[this.n - dist]);
      }
    }
    result(): Uint8Array {
      return this.a.subarray(0, this.n);
    }
  }

  class BitReader {
    d: Uint8Array;
    pos: number;
    buf: number;
    cnt: number;
    constructor(d: Uint8Array, pos: number) {
      this.d = d;
      this.pos = pos;
      this.buf = 0;
      this.cnt = 0;
    }
    bit(): number {
      if (this.cnt === 0) {
        if (this.pos >= this.d.length) {
          fail("compressed stream ended early");
        }
        this.buf = this.d[this.pos++];
        this.cnt = 8;
      }
      const b = this.buf & 1;
      this.buf >>= 1;
      this.cnt--;
      return b;
    }
    bits(n: number): number {
      let v = 0;
      for (let i = 0; i < n; i++) {
        v |= this.bit() << i;
      }
      return v;
    }
  }

  class Huff {
    counts: number[];
    symbols: number[];
    constructor(lengths: number[], n: number) {
      this.counts = [];
      for (let i = 0; i < 16; i++) {
        this.counts.push(0);
      }
      for (let s = 0; s < n; s++) {
        this.counts[lengths[s]]++;
      }
      this.counts[0] = 0;
      const offs: number[] = [];
      for (let i = 0; i < 16; i++) {
        offs.push(0);
      }
      for (let len = 1; len < 15; len++) {
        offs[len + 1] = offs[len] + this.counts[len];
      }
      this.symbols = [];
      for (let s = 0; s < n; s++) {
        this.symbols.push(0);
      }
      for (let s = 0; s < n; s++) {
        if (lengths[s] !== 0) {
          this.symbols[offs[lengths[s]]++] = s;
        }
      }
    }
  }

  function decodeSym(br: BitReader, h: Huff): number {
    let code = 0;
    let first = 0;
    let index = 0;
    for (let len = 1; len < 16; len++) {
      code |= br.bit();
      const count = h.counts[len];
      if (code - count < first) {
        return h.symbols[index + (code - first)];
      }
      index += count;
      first += count;
      first <<= 1;
      code <<= 1;
    }
    return fail("damaged compressed stream");
  }

  const LBASE: number[] = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99,
    115, 131, 163, 195, 227, 258];
  const LEXT: number[] = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0];
  const DBASE: number[] = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025,
    1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577];
  const DEXT: number[] = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12,
    13, 13];
  const CL_ORDER: number[] = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];

  let fixedLit: Huff | null = null;
  let fixedDist: Huff | null = null;

  function fixedTables(): Huff[] {
    if (fixedLit === null || fixedDist === null) {
      const l: number[] = [];
      for (let i = 0; i < 288; i++) {
        l.push(i < 144 ? 8 : i < 256 ? 9 : i < 280 ? 7 : 8);
      }
      const d: number[] = [];
      for (let i = 0; i < 30; i++) {
        d.push(5);
      }
      fixedLit = new Huff(l, 288);
      fixedDist = new Huff(d, 30);
    }
    return [fixedLit, fixedDist];
  }

  function inflateBlock(br: BitReader, out: ByteBuf, lit: Huff, dist: Huff): void {
    for (;;) {
      const sym = decodeSym(br, lit);
      if (sym < 256) {
        out.push(sym);
      } else if (sym === 256) {
        return;
      } else {
        const li = sym - 257;
        if (li >= 29) {
          fail("damaged compressed stream");
        }
        const len = LBASE[li] + br.bits(LEXT[li]);
        const ds = decodeSym(br, dist);
        if (ds >= 30) {
          fail("damaged compressed stream");
        }
        out.copyBack(DBASE[ds] + br.bits(DEXT[ds]), len);
      }
    }
  }

  function dynamicTables(br: BitReader): Huff[] {
    const nlen = br.bits(5) + 257;
    const ndist = br.bits(5) + 1;
    const ncode = br.bits(4) + 4;
    const lengths: number[] = [];
    for (let i = 0; i < 320; i++) {
      lengths.push(0);
    }
    for (let i = 0; i < ncode; i++) {
      lengths[CL_ORDER[i]] = br.bits(3);
    }
    const lencode = new Huff(lengths, 19);
    for (let i = 0; i < 320; i++) {
      lengths[i] = 0;
    }
    let index = 0;
    while (index < nlen + ndist) {
      const sym = decodeSym(br, lencode);
      if (sym < 16) {
        lengths[index++] = sym;
      } else {
        let len = 0;
        let rep = 0;
        if (sym === 16) {
          if (index === 0) {
            fail("damaged compressed stream");
          }
          len = lengths[index - 1];
          rep = 3 + br.bits(2);
        } else if (sym === 17) {
          rep = 3 + br.bits(3);
        } else {
          rep = 11 + br.bits(7);
        }
        if (index + rep > nlen + ndist) {
          fail("damaged compressed stream");
        }
        while (rep-- > 0) {
          lengths[index++] = len;
        }
      }
    }
    const dl: number[] = lengths.slice(nlen, nlen + ndist);
    return [new Huff(lengths, nlen), new Huff(dl, ndist)];
  }

  function inflate(data: Uint8Array): Uint8Array {
    const out = new ByteBuf(data.length * 4 + 64);
    let start = 0;
    if (data.length >= 2 && (data[0] & 0x0f) === 8 && ((data[0] << 8) + data[1]) % 31 === 0) {
      start = 2; // zlib-hoved; ellers raa deflate
    }
    const br = new BitReader(data, start);
    try {
      let last = 0;
      do {
        last = br.bit();
        const type = br.bits(2);
        if (type === 0) {
          br.cnt = 0;
          if (br.pos + 4 > data.length) {
            fail("compressed stream ended early");
          }
          const len = data[br.pos] | (data[br.pos + 1] << 8);
          br.pos += 4;
          for (let i = 0; i < len && br.pos < data.length; i++) {
            out.push(data[br.pos++]);
          }
        } else if (type === 1) {
          const t = fixedTables();
          inflateBlock(br, out, t[0], t[1]);
        } else if (type === 2) {
          const t = dynamicTables(br);
          inflateBlock(br, out, t[0], t[1]);
        } else {
          fail("damaged compressed stream");
        }
      } while (!last);
    } catch {
      // En afkortet eller let beskadiget stroem rummer som regel stadig
      // teksten - det, der naaede at blive pakket ud, bruges.
    }
    return out.result();
  }

  // PNG- og TIFF-praediktorer (DecodeParms). Bruges mest af xref- og
  // objektstroemme.
  function predict(data: Uint8Array, predictor: number, colors: number, bpc: number, columns: number): Uint8Array {
    if (predictor < 2) {
      return data;
    }
    const bpp = Math.max(1, Math.ceil(colors * bpc / 8));
    const rowLen = Math.ceil(colors * bpc * columns / 8);
    if (predictor === 2) {
      const out = new Uint8Array(data.length);
      out.set(data);
      if (bpc === 8) {
        for (let r = 0; r + rowLen <= out.length; r += rowLen) {
          for (let i = bpp; i < rowLen; i++) {
            out[r + i] = (out[r + i] + out[r + i - bpp]) & 0xff;
          }
        }
      }
      return out;
    }
    const out = new ByteBuf(data.length);
    let prev = new Uint8Array(rowLen);
    let p = 0;
    while (p < data.length) {
      const ft = data[p++];
      const row = new Uint8Array(rowLen);
      for (let i = 0; i < rowLen; i++) {
        const raw = p + i < data.length ? data[p + i] : 0;
        const left = i >= bpp ? row[i - bpp] : 0;
        const up = prev[i];
        const ul = i >= bpp ? prev[i - bpp] : 0;
        let v = raw;
        if (ft === 1) {
          v = raw + left;
        } else if (ft === 2) {
          v = raw + up;
        } else if (ft === 3) {
          v = raw + ((left + up) >> 1);
        } else if (ft === 4) {
          const pa = Math.abs(up - ul);
          const pb = Math.abs(left - ul);
          const pc = Math.abs(left + up - 2 * ul);
          v = raw + (pa <= pb && pa <= pc ? left : pb <= pc ? up : ul);
        }
        row[i] = v & 0xff;
        out.push(row[i]);
      }
      p += rowLen;
      prev = row;
    }
    return out.result();
  }

  function lzwDecode(data: Uint8Array, early: boolean): Uint8Array {
    const out = new ByteBuf(data.length * 3);
    const dict: number[][] = [];
    const reset = (): void => {
      dict.length = 0;
      for (let i = 0; i < 256; i++) {
        dict.push([i]);
      }
      dict.push([]);
      dict.push([]);
    };
    reset();
    let codeLen = 9;
    let bitBuf = 0;
    let bitCnt = 0;
    let prev: number[] | null = null;
    for (let p = 0; p < data.length; p++) {
      bitBuf = (bitBuf << 8) | data[p];
      bitCnt += 8;
      while (bitCnt >= codeLen) {
        const code = (bitBuf >> (bitCnt - codeLen)) & ((1 << codeLen) - 1);
        bitCnt -= codeLen;
        bitBuf &= (1 << bitCnt) - 1;
        if (code === 256) {
          reset();
          codeLen = 9;
          prev = null;
          continue;
        }
        if (code === 257) {
          return out.result();
        }
        let entry: number[];
        if (code < dict.length) {
          entry = dict[code];
        } else if (prev !== null) {
          entry = prev.concat([prev[0]]);
        } else {
          return out.result();
        }
        for (let i = 0; i < entry.length; i++) {
          out.push(entry[i]);
        }
        if (prev !== null) {
          dict.push(prev.concat([entry[0]]));
        }
        prev = entry;
        const limit = dict.length + (early ? 1 : 0);
        if (limit >= 4096) {
          codeLen = 12;
        } else if (limit >= 2048) {
          codeLen = 12;
        } else if (limit >= 1024) {
          codeLen = 11;
        } else if (limit >= 512) {
          codeLen = 10;
        }
      }
    }
    return out.result();
  }

  function asciiHexDecode(data: Uint8Array): Uint8Array {
    const out: number[] = [];
    let hi = -1;
    for (let i = 0; i < data.length; i++) {
      const c = data[i];
      if (c === 62) {
        break;
      }
      const v = hexVal(c);
      if (v < 0) {
        continue;
      }
      if (hi < 0) {
        hi = v;
      } else {
        out.push(hi * 16 + v);
        hi = -1;
      }
    }
    if (hi >= 0) {
      out.push(hi * 16);
    }
    return new Uint8Array(out);
  }

  function ascii85Decode(data: Uint8Array): Uint8Array {
    const out: number[] = [];
    const group: number[] = [];
    let i = 0;
    if (data.length > 1 && data[0] === 60 && data[1] === 126) {
      i = 2; // <~
    }
    for (; i < data.length; i++) {
      const c = data[i];
      if (c === 126) {
        break; // ~>
      }
      if (c <= 32) {
        continue;
      }
      if (c === 122 && group.length === 0) {
        out.push(0, 0, 0, 0);
        continue;
      }
      if (c < 33 || c > 117) {
        continue;
      }
      group.push(c - 33);
      if (group.length === 5) {
        let v = 0;
        for (let k = 0; k < 5; k++) {
          v = v * 85 + group[k];
        }
        out.push((v >>> 24) & 0xff, (v >>> 16) & 0xff, (v >>> 8) & 0xff, v & 0xff);
        group.length = 0;
      }
    }
    if (group.length > 1) {
      const n = group.length;
      while (group.length < 5) {
        group.push(84);
      }
      let v = 0;
      for (let k = 0; k < 5; k++) {
        v = v * 85 + group[k];
      }
      const bytes = [(v >>> 24) & 0xff, (v >>> 16) & 0xff, (v >>> 8) & 0xff, v & 0xff];
      for (let k = 0; k < n - 1; k++) {
        out.push(bytes[k]);
      }
    }
    return new Uint8Array(out);
  }

  function runLengthDecode(data: Uint8Array): Uint8Array {
    const out = new ByteBuf(data.length * 2);
    let i = 0;
    while (i < data.length) {
      const n = data[i++];
      if (n === 128) {
        break;
      }
      if (n < 128) {
        for (let k = 0; k <= n && i < data.length; k++) {
          out.push(data[i++]);
        }
      } else if (i < data.length) {
        const b = data[i++];
        for (let k = 0; k < 257 - n; k++) {
          out.push(b);
        }
      }
    }
    return out.result();
  }

  function hexVal(c: number): number {
    if (c >= 48 && c <= 57) {
      return c - 48;
    }
    if (c >= 65 && c <= 70) {
      return c - 55;
    }
    if (c >= 97 && c <= 102) {
      return c - 87;
    }
    return -1;
  }

  // ===========================================================================
  // PDF-objekter
  // ===========================================================================
  class PName {
    n: string;
    constructor(n: string) {
      this.n = n;
    }
  }

  class PRef {
    num: number;
    gen: number;
    constructor(num: number, gen: number) {
      this.num = num;
      this.gen = gen;
    }
  }

  class PStr {
    s: string; // raa bytes som Latin-1-tegn
    constructor(s: string) {
      this.s = s;
    }
  }

  class PArr {
    a: PVal[];
    constructor(a: PVal[]) {
      this.a = a;
    }
  }

  class PDict {
    m: Map<string, PVal>;
    constructor() {
      this.m = new Map<string, PVal>();
    }
  }

  class PStream {
    d: PDict;
    raw: string;
    constructor(d: PDict, raw: string) {
      this.d = d;
      this.raw = raw;
    }
  }

  // En operator i en indholdsstroem - eller et strukturtegn (] >>).
  class POp {
    op: string;
    constructor(op: string) {
      this.op = op;
    }
  }

  type PVal = PName | PRef | PStr | PArr | PDict | PStream | number | boolean | null;
  type PTok = PVal | POp;

  function makeTable(chars: string): boolean[] {
    const t: boolean[] = [];
    for (let i = 0; i < 256; i++) {
      t.push(false);
    }
    for (let i = 0; i < chars.length; i++) {
      t[chars.charCodeAt(i)] = true;
    }
    return t;
  }

  const WS_TABLE = makeTable("\x00\t\n\x0c\r ");
  const DELIM_TABLE = makeTable("()<>[]{}/%");

  function isWs(c: number): boolean {
    return c < 256 && WS_TABLE[c];
  }

  function isDelimOrWs(c: number): boolean {
    return c < 256 && (WS_TABLE[c] || DELIM_TABLE[c]);
  }

  function decodeName(s: string): string {
    if (s.indexOf("#") < 0) {
      return s;
    }
    return s.replace(/#([0-9A-Fa-f]{2})/g, (m: string, h: string) => String.fromCharCode(parseInt(h, 16)));
  }

  function toNumber(w: string): number | null {
    if (!/^[+-]?(\d+\.?\d*|\.\d+)$/.test(w)) {
      return null;
    }
    return parseFloat(w);
  }

  class Lexer {
    s: string;
    p: number;
    end: number;
    constructor(s: string, p: number, end: number) {
      this.s = s;
      this.p = p;
      this.end = end;
    }

    skipWs(): void {
      const s = this.s;
      while (this.p < this.end) {
        const c = s.charCodeAt(this.p);
        if (isWs(c)) {
          this.p++;
          continue;
        }
        if (c === 37) {
          while (this.p < this.end) {
            const d = s.charCodeAt(this.p);
            if (d === 10 || d === 13) {
              break;
            }
            this.p++;
          }
          continue;
        }
        break;
      }
    }

    regular(): string {
      const s = this.s;
      const start = this.p;
      while (this.p < this.end && !isDelimOrWs(s.charCodeAt(this.p))) {
        this.p++;
      }
      return s.substring(start, this.p);
    }

    // refs: kend "N G R" (objekter). I en indholdsstroem er der ingen.
    read(refs: boolean): PTok | undefined {
      this.skipWs();
      if (this.p >= this.end) {
        return undefined;
      }
      const s = this.s;
      const c = s.charAt(this.p);
      if (c === "/") {
        this.p++;
        return new PName(decodeName(this.regular()));
      }
      if (c === "(") {
        return this.literal();
      }
      if (c === "<") {
        if (s.charAt(this.p + 1) === "<") {
          this.p += 2;
          return this.dict(refs);
        }
        return this.hex();
      }
      if (c === "[") {
        this.p++;
        return this.array(refs);
      }
      if (c === ">") {
        if (s.charAt(this.p + 1) === ">") {
          this.p += 2;
          return new POp(">>");
        }
        this.p++;
        return new POp(">");
      }
      if (c === "]" || c === "{" || c === "}" || c === ")") {
        this.p++;
        return new POp(c);
      }
      const word = this.regular();
      if (word === "") {
        this.p++;
        return new POp(c);
      }
      const n = toNumber(word);
      if (n !== null) {
        if (refs && /^\d+$/.test(word)) {
          const save = this.p;
          this.skipWs();
          const g = this.regular();
          if (/^\d+$/.test(g)) {
            this.skipWs();
            if (s.charAt(this.p) === "R" && (this.p + 1 >= this.end || isDelimOrWs(s.charCodeAt(this.p + 1)))) {
              this.p++;
              return new PRef(n, parseInt(g, 10));
            }
          }
          this.p = save;
        }
        return n;
      }
      if (word === "true") {
        return true;
      }
      if (word === "false") {
        return false;
      }
      if (word === "null") {
        return null;
      }
      return new POp(word);
    }

    literal(): PStr {
      const s = this.s;
      this.p++;
      let depth = 1;
      const out: number[] = [];
      while (this.p < this.end) {
        const c = s.charCodeAt(this.p++);
        if (c === 92) {
          if (this.p >= this.end) {
            break;
          }
          const d = s.charCodeAt(this.p++);
          if (d === 110) {
            out.push(10);
          } else if (d === 114) {
            out.push(13);
          } else if (d === 116) {
            out.push(9);
          } else if (d === 98) {
            out.push(8);
          } else if (d === 102) {
            out.push(12);
          } else if (d === 13) {
            if (s.charCodeAt(this.p) === 10) {
              this.p++;
            }
          } else if (d === 10) {
            // linjefortsaettelse
          } else if (d >= 48 && d <= 55) {
            let v = d - 48;
            for (let k = 0; k < 2 && this.p < this.end; k++) {
              const e = s.charCodeAt(this.p);
              if (e < 48 || e > 55) {
                break;
              }
              v = v * 8 + (e - 48);
              this.p++;
            }
            out.push(v & 0xff);
          } else {
            out.push(d);
          }
          continue;
        }
        if (c === 40) {
          depth++;
        } else if (c === 41) {
          depth--;
          if (depth === 0) {
            break;
          }
        }
        out.push(c & 0xff);
      }
      return new PStr(codesToString(out));
    }

    hex(): PStr {
      const s = this.s;
      this.p++;
      const out: number[] = [];
      let hi = -1;
      while (this.p < this.end) {
        const c = s.charCodeAt(this.p++);
        if (c === 62) {
          break;
        }
        const v = hexVal(c);
        if (v < 0) {
          continue;
        }
        if (hi < 0) {
          hi = v;
        } else {
          out.push(hi * 16 + v);
          hi = -1;
        }
      }
      if (hi >= 0) {
        out.push(hi * 16);
      }
      return new PStr(codesToString(out));
    }

    dict(refs: boolean): PDict {
      const d = new PDict();
      for (;;) {
        const k = this.read(refs);
        if (k === undefined) {
          break;
        }
        if (k instanceof POp) {
          if (k.op === ">>") {
            break;
          }
          continue;
        }
        if (!(k instanceof PName)) {
          continue;
        }
        const v = this.read(refs);
        if (v === undefined) {
          break;
        }
        if (v instanceof POp) {
          if (v.op === ">>") {
            break;
          }
          continue;
        }
        d.m.set(k.n, v);
      }
      return d;
    }

    array(refs: boolean): PArr {
      const a: PVal[] = [];
      for (;;) {
        const v = this.read(refs);
        if (v === undefined) {
          break;
        }
        if (v instanceof POp) {
          if (v.op === "]") {
            break;
          }
          continue;
        }
        a.push(v);
      }
      return new PArr(a);
    }
  }

  interface ObjEntry {
    pos: number;
    v: PVal;
  }

  interface ParsedObj {
    v: PVal;
    end: number;
  }

  interface PageInfo {
    d: PDict;
    res: PDict | null;
    rotate: number;
  }

  function nameOf(v: PVal | undefined): string {
    return v instanceof PName ? v.n : "";
  }

  class PdfDoc {
    s: string;
    objs: Map<number, ObjEntry>;
    trailers: ObjEntry[];

    constructor(s: string) {
      this.s = s;
      this.objs = new Map<number, ObjEntry>();
      this.trailers = [];
    }

    // Objekterne findes ved at LAESE filen, ikke ved at stole paa xref-
    // tabellen: den er tit forkert efter en tilfoejelse, og xref-stroemme
    // kraever det hele alligevel. Senere definitioner vinder.
    load(): void {
      const s = this.s;
      const re = /(\d+)\s+(\d+)\s+obj\b/g;
      let m = re.exec(s);
      while (m !== null) {
        const start = m.index + m[0].length;
        const r = this.parseObject(start);
        this.objs.set(parseInt(m[1], 10), { pos: m.index, v: r.v });
        re.lastIndex = Math.max(r.end, start);
        m = re.exec(s);
      }
      const tr = /trailer\s*<</g;
      let t = tr.exec(s);
      while (t !== null) {
        const lx = new Lexer(s, t.index + t[0].length - 2, s.length);
        const v = lx.read(true);
        if (v instanceof PDict) {
          this.trailers.push({ pos: t.index, v: v });
        }
        t = tr.exec(s);
      }
      const list = this.entries();
      for (let i = 0; i < list.length; i++) {
        const e = list[i];
        if (e.v instanceof PStream && nameOf(e.v.d.m.get("Type")) === "XRef") {
          this.trailers.push({ pos: e.pos, v: e.v.d });
        }
      }
      this.trailers.sort((a, b) => a.pos - b.pos);
      this.loadObjStreams(list);
    }

    entries(): ObjEntry[] {
      const out: ObjEntry[] = [];
      this.objs.forEach((e) => {
        out.push(e);
      });
      return out;
    }

    parseObject(start: number): ParsedObj {
      const s = this.s;
      const lx = new Lexer(s, start, s.length);
      const v = lx.read(true);
      if (v === undefined || v instanceof POp) {
        return { v: null, end: lx.p };
      }
      lx.skipWs();
      if (v instanceof PDict && s.substr(lx.p, 6) === "stream") {
        let p = lx.p + 6;
        if (s.charAt(p) === "\r") {
          p++;
        }
        if (s.charAt(p) === "\n") {
          p++;
        }
        let dataEnd = -1;
        const len = v.m.get("Length");
        if (typeof len === "number" && len >= 0 && p + len <= s.length) {
          if (/^\s*endstream/.test(s.substr(p + len, 24))) {
            dataEnd = p + len;
          }
        }
        if (dataEnd < 0) {
          const e = s.indexOf("endstream", p);
          if (e < 0) {
            return { v: new PStream(v, s.substring(p)), end: s.length };
          }
          dataEnd = e;
          if (dataEnd > p && s.charAt(dataEnd - 1) === "\n") {
            dataEnd--;
          }
          if (dataEnd > p && s.charAt(dataEnd - 1) === "\r") {
            dataEnd--;
          }
        }
        const raw = s.substring(p, dataEnd);
        const es = s.indexOf("endstream", dataEnd);
        let end = es < 0 ? dataEnd : es + 9;
        const eo = s.indexOf("endobj", end);
        if (eo >= 0 && eo - end < 64) {
          end = eo + 6;
        }
        return { v: new PStream(v, raw), end: end };
      }
      const eo = s.indexOf("endobj", lx.p);
      return { v: v, end: eo >= 0 && eo - lx.p < 256 ? eo + 6 : lx.p };
    }

    // Objektstroemme (PDF 1.5): mange smaa objekter pakket i een stroem.
    loadObjStreams(list: ObjEntry[]): void {
      for (let i = 0; i < list.length; i++) {
        const e = list[i];
        if (!(e.v instanceof PStream) || nameOf(e.v.d.m.get("Type")) !== "ObjStm") {
          continue;
        }
        const st = e.v;
        const n = this.num(st.d.m.get("N"));
        const first = this.num(st.d.m.get("First"));
        if (n === null || first === null) {
          continue;
        }
        let data = "";
        try {
          data = latin1(this.streamBytes(st));
        } catch {
          continue;
        }
        const lx = new Lexer(data, 0, Math.min(first, data.length));
        const pairs: number[] = [];
        for (let k = 0; k < n * 2; k++) {
          const t = lx.read(false);
          if (typeof t !== "number") {
            break;
          }
          pairs.push(t);
        }
        for (let k = 0; k + 1 < pairs.length; k += 2) {
          const ox = new Lexer(data, first + pairs[k + 1], data.length);
          const v = ox.read(true);
          if (v === undefined || v instanceof POp) {
            continue;
          }
          const old = this.objs.get(pairs[k]);
          if (!old || old.pos < e.pos) {
            this.objs.set(pairs[k], { pos: e.pos, v: v });
          }
        }
      }
    }

    resolve(v: PVal | undefined): PVal {
      let x: PVal | undefined = v;
      for (let i = 0; i < 16 && x instanceof PRef; i++) {
        const e = this.objs.get(x.num);
        x = e ? e.v : null;
      }
      if (x === undefined || x instanceof PRef) {
        return null;
      }
      return x;
    }

    dict(v: PVal | undefined): PDict | null {
      const r = this.resolve(v);
      if (r instanceof PDict) {
        return r;
      }
      if (r instanceof PStream) {
        return r.d;
      }
      return null;
    }

    arr(v: PVal | undefined): PVal[] {
      const r = this.resolve(v);
      return r instanceof PArr ? r.a : [];
    }

    num(v: PVal | undefined): number | null {
      const r = this.resolve(v);
      return typeof r === "number" ? r : null;
    }

    name(v: PVal | undefined): string {
      const r = this.resolve(v);
      return r instanceof PName ? r.n : "";
    }

    streamBytes(st: PStream): Uint8Array {
      let data = latin1ToBytes(st.raw);
      const f = this.resolve(st.d.m.get("Filter"));
      const filters: string[] = [];
      if (f instanceof PName) {
        filters.push(f.n);
      } else if (f instanceof PArr) {
        for (let i = 0; i < f.a.length; i++) {
          filters.push(this.name(f.a[i]));
        }
      }
      const dp = this.resolve(st.d.m.get("DecodeParms") || st.d.m.get("DP") || null);
      for (let i = 0; i < filters.length; i++) {
        const parms = dp instanceof PArr ? this.dict(dp.a[i]) : this.dict(dp);
        const pv = (k: string, def: number): number => {
          const x = parms === null ? null : this.num(parms.m.get(k));
          return x === null ? def : x;
        };
        const name = filters[i];
        if (name === "FlateDecode" || name === "Fl") {
          data = predict(inflate(data), pv("Predictor", 1), pv("Colors", 1), pv("BitsPerComponent", 8), pv("Columns", 1));
        } else if (name === "LZWDecode" || name === "LZW") {
          data = predict(lzwDecode(data, pv("EarlyChange", 1) !== 0), pv("Predictor", 1), pv("Colors", 1),
            pv("BitsPerComponent", 8), pv("Columns", 1));
        } else if (name === "ASCIIHexDecode" || name === "AHx") {
          data = asciiHexDecode(data);
        } else if (name === "ASCII85Decode" || name === "A85") {
          data = ascii85Decode(data);
        } else if (name === "RunLengthDecode" || name === "RL") {
          data = runLengthDecode(data);
        } else if (name !== "Crypt") {
          return new Uint8Array(0); // billeder (DCT, JPX, CCITT, JBIG2) - ingen tekst
        }
      }
      return data;
    }

    encrypted(): boolean {
      return this.trailers.some((t) => t.v instanceof PDict && t.v.m.has("Encrypt"));
    }

    catalog(): PDict | null {
      for (let i = this.trailers.length - 1; i >= 0; i--) {
        const t = this.trailers[i].v;
        if (t instanceof PDict) {
          const r = this.dict(t.m.get("Root"));
          if (r !== null) {
            return r;
          }
        }
      }
      const list = this.entries();
      let best: PDict | null = null;
      let bestPos = -1;
      for (let i = 0; i < list.length; i++) {
        const e = list[i];
        if (e.v instanceof PDict && nameOf(e.v.m.get("Type")) === "Catalog" && e.pos > bestPos) {
          best = e.v;
          bestPos = e.pos;
        }
      }
      return best;
    }

    pages(): PageInfo[] {
      const out: PageInfo[] = [];
      const seen: PDict[] = [];
      const cat = this.catalog();
      const root = cat === null ? null : this.dict(cat.m.get("Pages"));
      if (root !== null) {
        this.walkPages(root, null, 0, out, seen, 0);
      }
      if (out.length === 0) {
        // Reserve: alle sider i filens raekkefoelge.
        const list = this.entries().filter((e) => e.v instanceof PDict && nameOf(e.v.m.get("Type")) === "Page");
        list.sort((a, b) => a.pos - b.pos);
        for (let i = 0; i < list.length; i++) {
          const d = list[i].v;
          if (d instanceof PDict) {
            out.push({ d: d, res: this.dict(d.m.get("Resources")), rotate: this.num(d.m.get("Rotate")) || 0 });
          }
        }
      }
      return out;
    }

    walkPages(node: PDict, res: PDict | null, rotate: number, out: PageInfo[], seen: PDict[], depth: number): void {
      if (depth > 32 || seen.indexOf(node) >= 0) {
        return;
      }
      seen.push(node);
      const own = this.dict(node.m.get("Resources"));
      const r = own !== null ? own : res;
      const rv = this.num(node.m.get("Rotate"));
      const rot = rv === null ? rotate : rv;
      const kids = this.arr(node.m.get("Kids"));
      const type = this.name(node.m.get("Type"));
      if (type === "Page" || (kids.length === 0 && type !== "Pages")) {
        out.push({ d: node, res: r, rotate: rot });
        return;
      }
      for (let i = 0; i < kids.length; i++) {
        const kd = this.dict(kids[i]);
        if (kd !== null) {
          this.walkPages(kd, r, rot, out, seen, depth + 1);
        }
      }
    }

    contentOf(v: PVal | undefined): string {
      const c = this.resolve(v);
      const parts: string[] = [];
      const items: PVal[] = c instanceof PArr ? c.a : [c];
      for (let i = 0; i < items.length; i++) {
        const r = this.resolve(items[i]);
        if (r instanceof PStream) {
          try {
            parts.push(latin1(this.streamBytes(r)));
          } catch {
            // en beskadiget stroem springes over
          }
        }
      }
      return parts.join("\n");
    }
  }

  // ===========================================================================
  // Skrifttyper: fra tegnkoder til tekst og bredder
  // ===========================================================================
  class FontInfo {
    cid: boolean;
    ranges: number[][];          // [laengde, lav, hoej] - kodernes laengde i en CID-skrift
    cidMap: Map<number, number>; // kode -> CID, naar Encoding er en CMap-stroem
    toUni: Map<number, string>;  // noegle: laengde * 2^32 + kode
    enc: string[];               // simple skrifter: kode -> tegn
    widths: Map<number, number>; // simple: kode -> bredde, CID: CID -> bredde (1/1000 em)
    dw: number;                  // standardbredde (1/1000 em)
    scale: number;               // glyfenheder -> em (0.001, Type3 efter FontMatrix)
    spaceW: number;              // mellemrummets bredde i em
    constructor() {
      this.cid = false;
      this.ranges = [];
      this.cidMap = new Map<number, number>();
      this.toUni = new Map<number, string>();
      this.enc = [];
      this.widths = new Map<number, number>();
      this.dw = 500;
      this.scale = 0.001;
      this.spaceW = 0.278;
    }
  }

  const TWO32 = 4294967296;

  function codeOf(raw: string, i: number, n: number): number {
    let v = 0;
    for (let k = 0; k < n; k++) {
      v = v * 256 + (raw.charCodeAt(i + k) & 0xff);
    }
    return v;
  }

  interface CTok {
    kind: string; // h = hex, n = tal, [ ] = klammer, / = navn
    hex: string;
    num: number;
  }

  function cmapTokens(text: string): CTok[] {
    const out: CTok[] = [];
    const re = /<([0-9A-Fa-f\s]*)>|(\[)|(\])|(-?\d+)|\/([^\s\/\[\]<>()]+)/g;
    let m = re.exec(text);
    while (m !== null) {
      if (m[1] !== undefined) {
        out.push({ kind: "h", hex: m[1].replace(/\s+/g, ""), num: 0 });
      } else if (m[2] !== undefined) {
        out.push({ kind: "[", hex: "", num: 0 });
      } else if (m[3] !== undefined) {
        out.push({ kind: "]", hex: "", num: 0 });
      } else if (m[4] !== undefined) {
        out.push({ kind: "n", hex: "", num: parseInt(m[4], 10) });
      } else {
        out.push({ kind: "/", hex: m[5] || "", num: 0 });
      }
      m = re.exec(text);
    }
    return out;
  }

  function utf16Units(hex: string): number[] {
    const out: number[] = [];
    for (let i = 0; i + 3 < hex.length; i += 4) {
      out.push(parseInt(hex.substring(i, i + 4), 16));
    }
    if (hex.length === 2) {
      out.push(parseInt(hex, 16)); // en enkelt byte (sjusket CMap)
    }
    return out;
  }

  function unitsToString(u: number[]): string {
    return codesToString(u);
  }

  function parseCMap(text: string, f: FontInfo, toUnicode: boolean): void {
    const block = /begin(codespacerange|bfchar|bfrange|cidchar|cidrange)([\s\S]*?)end\1/g;
    let m = block.exec(text);
    while (m !== null) {
      const kind = m[1];
      const t = cmapTokens(m[2]);
      if (kind === "codespacerange") {
        for (let i = 0; i + 1 < t.length; i += 2) {
          if (t[i].kind === "h" && t[i + 1].kind === "h") {
            const len = Math.max(1, Math.floor(t[i].hex.length / 2));
            f.ranges.push([len, parseInt(t[i].hex, 16), parseInt(t[i + 1].hex, 16)]);
          }
        }
      } else if (kind === "bfchar" && toUnicode) {
        for (let i = 0; i + 1 < t.length; i += 2) {
          if (t[i].kind === "h" && t[i + 1].kind === "h") {
            const len = Math.max(1, Math.floor(t[i].hex.length / 2));
            f.toUni.set(len * TWO32 + parseInt(t[i].hex, 16), unitsToString(utf16Units(t[i + 1].hex)));
          }
        }
      } else if (kind === "bfrange" && toUnicode) {
        let i = 0;
        while (i + 2 < t.length) {
          if (t[i].kind !== "h" || t[i + 1].kind !== "h") {
            i++;
            continue;
          }
          const len = Math.max(1, Math.floor(t[i].hex.length / 2));
          const lo = parseInt(t[i].hex, 16);
          const hi = Math.min(parseInt(t[i + 1].hex, 16), lo + 65535);
          if (t[i + 2].kind === "h") {
            const base = utf16Units(t[i + 2].hex);
            for (let c = lo; c <= hi && base.length > 0; c++) {
              const u = base.slice();
              u[u.length - 1] += c - lo;
              f.toUni.set(len * TWO32 + c, unitsToString(u));
            }
            i += 3;
          } else if (t[i + 2].kind === "[") {
            let k = i + 3;
            let c = lo;
            while (k < t.length && t[k].kind !== "]") {
              if (t[k].kind === "h" && c <= hi) {
                f.toUni.set(len * TWO32 + c, unitsToString(utf16Units(t[k].hex)));
              }
              c++;
              k++;
            }
            i = k + 1;
          } else {
            i += 3;
          }
        }
      } else if (kind === "cidchar" && !toUnicode) {
        for (let i = 0; i + 1 < t.length; i += 2) {
          if (t[i].kind === "h" && t[i + 1].kind === "n") {
            f.cidMap.set(parseInt(t[i].hex, 16), t[i + 1].num);
          }
        }
      } else if (kind === "cidrange" && !toUnicode) {
        for (let i = 0; i + 2 < t.length; i += 3) {
          if (t[i].kind === "h" && t[i + 1].kind === "h" && t[i + 2].kind === "n") {
            const lo = parseInt(t[i].hex, 16);
            const hi = Math.min(parseInt(t[i + 1].hex, 16), lo + 65535);
            for (let c = lo; c <= hi; c++) {
              f.cidMap.set(c, t[i + 2].num + (c - lo));
            }
          }
        }
      }
      m = block.exec(text);
    }
  }

  // Glyfnavne -> tegn. WinAnsi-raekkefoelgen giver de fleste; resten staar under.
  const WINANSI_NAMES = ("space exclam quotedbl numbersign dollar percent ampersand quotesingle parenleft parenright "
    + "asterisk plus comma hyphen period slash zero one two three four five six seven eight nine colon semicolon less "
    + "equal greater question at A B C D E F G H I J K L M N O P Q R S T U V W X Y Z bracketleft backslash "
    + "bracketright asciicircum underscore grave a b c d e f g h i j k l m n o p q r s t u v w x y z braceleft bar "
    + "braceright asciitilde - Euro - quotesinglbase florin quotedblbase ellipsis dagger daggerdbl circumflex "
    + "perthousand Scaron guilsinglleft OE - Zcaron - - quoteleft quoteright quotedblleft quotedblright bullet endash "
    + "emdash tilde trademark scaron guilsinglright oe - zcaron Ydieresis space exclamdown cent sterling currency yen "
    + "brokenbar section dieresis copyright ordfeminine guillemotleft logicalnot hyphen registered macron degree "
    + "plusminus twosuperior threesuperior acute mu paragraph periodcentered cedilla onesuperior ordmasculine "
    + "guillemotright onequarter onehalf threequarters questiondown Agrave Aacute Acircumflex Atilde Adieresis Aring "
    + "AE Ccedilla Egrave Eacute Ecircumflex Edieresis Igrave Iacute Icircumflex Idieresis Eth Ntilde Ograve Oacute "
    + "Ocircumflex Otilde Odieresis multiply Oslash Ugrave Uacute Ucircumflex Udieresis Yacute Thorn germandbls "
    + "agrave aacute acircumflex atilde adieresis aring ae ccedilla egrave eacute ecircumflex edieresis igrave iacute "
    + "icircumflex idieresis eth ntilde ograve oacute ocircumflex otilde odieresis divide oslash ugrave uacute "
    + "ucircumflex udieresis yacute thorn ydieresis").split(" ");

  const EXTRA_GLYPHS: string[][] = [
    ["fi", "fi"], ["fl", "fl"], ["ff", "ff"], ["ffi", "ffi"], ["ffl", "ffl"], ["dotlessi", "\u0131"],
    ["Lslash", "\u0141"], ["lslash", "\u0142"], ["fraction", "/"], ["minus", "-"], ["nbspace", " "],
    ["nonbreakingspace", " "], ["sfthyphen", "-"], ["softhyphen", "-"], ["hyphenminus", "-"], ["quotesinglebase", ","],
    ["middot", "\u00b7"], ["Euro", "\u20ac"], ["euro", "\u20ac"], ["Ohm", "\u2126"], ["Omega", "\u03a9"],
    ["mu1", "\u00b5"], ["micro", "\u00b5"], ["degreesign", "\u00b0"], ["diameter", "\u2300"], ["approxequal", "\u2248"],
    ["lessequal", "\u2264"], ["greaterequal", "\u2265"], ["notequal", "\u2260"], ["infinity", "\u221e"],
    ["CR", ""], ["tab", " "], ["uni00A0", " "]
  ];

  let glyphMap: Map<string, string> | null = null;

  function glyphToUnicode(name: string): string {
    if (glyphMap === null) {
      const gm = new Map<string, string>();
      const win = winAnsi();
      for (let i = 0; i < WINANSI_NAMES.length; i++) {
        const n = WINANSI_NAMES[i];
        if (n !== "-" && !gm.has(n)) {
          gm.set(n, win[32 + i]);
        }
      }
      for (let i = 0; i < EXTRA_GLYPHS.length; i++) {
        gm.set(EXTRA_GLYPHS[i][0], EXTRA_GLYPHS[i][1]);
      }
      glyphMap = gm;
    }
    const hit = glyphMap.get(name);
    if (hit !== undefined) {
      return hit;
    }
    let m = /^uni([0-9A-Fa-f]{4})+$/.exec(name);
    if (m) {
      const units: number[] = [];
      for (let i = 3; i + 3 < name.length + 1; i += 4) {
        units.push(parseInt(name.substring(i, i + 4), 16));
      }
      return codesToString(units);
    }
    m = /^u([0-9A-Fa-f]{4,6})$/.exec(name);
    if (m) {
      const cp = parseInt(m[1], 16);
      if (cp > 0xffff) {
        const c = cp - 0x10000;
        return String.fromCharCode(0xd800 + (c >> 10), 0xdc00 + (c & 0x3ff));
      }
      return String.fromCharCode(cp);
    }
    const dot = name.indexOf(".");
    if (dot > 0) {
      return glyphToUnicode(name.substring(0, dot));
    }
    if (name.indexOf("_") > 0) {
      return name.split("_").map((p) => glyphToUnicode(p)).join("");
    }
    return "";
  }

  let winAnsiTable: string[] | null = null;

  function winAnsi(): string[] {
    if (winAnsiTable === null) {
      const t: string[] = [];
      for (let c = 0; c < 256; c++) {
        if (c < 32 || c === 127) {
          t.push("");
        } else if (c >= 128 && c < 160) {
          const u = CP1252_HIGH[c - 128];
          t.push(u ? String.fromCharCode(u) : "");
        } else {
          t.push(String.fromCharCode(c));
        }
      }
      winAnsiTable = t;
    }
    return winAnsiTable.slice();
  }

  const MAC_ROMAN_HIGH: number[] = [
    0xc4, 0xc5, 0xc7, 0xc9, 0xd1, 0xd6, 0xdc, 0xe1, 0xe0, 0xe2, 0xe4, 0xe3, 0xe5, 0xe7, 0xe9, 0xe8,
    0xea, 0xeb, 0xed, 0xec, 0xee, 0xef, 0xf1, 0xf3, 0xf2, 0xf4, 0xf6, 0xf5, 0xfa, 0xf9, 0xfb, 0xfc,
    0x2020, 0xb0, 0xa2, 0xa3, 0xa7, 0x2022, 0xb6, 0xdf, 0xae, 0xa9, 0x2122, 0xb4, 0xa8, 0x2260, 0xc6, 0xd8,
    0x221e, 0xb1, 0x2264, 0x2265, 0xa5, 0xb5, 0x2202, 0x2211, 0x220f, 0x3c0, 0x222b, 0xaa, 0xba, 0x3a9, 0xe6, 0xf8,
    0xbf, 0xa1, 0xac, 0x221a, 0x192, 0x2248, 0x2206, 0xab, 0xbb, 0x2026, 0xa0, 0xc0, 0xc3, 0xd5, 0x152, 0x153,
    0x2013, 0x2014, 0x201c, 0x201d, 0x2018, 0x2019, 0xf7, 0x25ca, 0xff, 0x178, 0x2044, 0x20ac, 0x2039, 0x203a, 0xfb01, 0xfb02,
    0x2021, 0xb7, 0x201a, 0x201e, 0x2030, 0xc2, 0xca, 0xc1, 0xcb, 0xc8, 0xcd, 0xce, 0xcf, 0xcc, 0xd3, 0xd4,
    0xf8ff, 0xd2, 0xda, 0xdb, 0xd9, 0x131, 0x2c6, 0x2dc, 0xaf, 0x2d8, 0x2d9, 0x2da, 0xb8, 0x2dd, 0x2db, 0x2c7
  ];

  function macRoman(): string[] {
    const t = winAnsi();
    for (let c = 128; c < 256; c++) {
      t[c] = String.fromCharCode(MAC_ROMAN_HIGH[c - 128]);
    }
    return t;
  }

  // Adobe StandardEncoding - kun det, der afviger fra WinAnsi.
  const STANDARD_HIGH: number[][] = [
    [0x27, 0x2019], [0x60, 0x2018], [0xa1, 0xa1], [0xa2, 0xa2], [0xa3, 0xa3], [0xa4, 0x2044], [0xa5, 0xa5],
    [0xa6, 0x192], [0xa7, 0xa7], [0xa8, 0xa4], [0xa9, 0x27], [0xaa, 0x201c], [0xab, 0xab], [0xac, 0x2039],
    [0xad, 0x203a], [0xae, 0xfb01], [0xaf, 0xfb02], [0xb1, 0x2013], [0xb2, 0x2020], [0xb3, 0x2021], [0xb4, 0xb7],
    [0xb6, 0xb6], [0xb7, 0x2022], [0xb8, 0x201a], [0xb9, 0x201e], [0xba, 0x201d], [0xbb, 0xbb], [0xbc, 0x2026],
    [0xbd, 0x2030], [0xbf, 0xbf], [0xc1, 0x60], [0xc2, 0xb4], [0xc3, 0x2c6], [0xc4, 0x2dc], [0xc5, 0xaf],
    [0xc6, 0x2d8], [0xc7, 0x2d9], [0xc8, 0xa8], [0xca, 0x2da], [0xcb, 0xb8], [0xcd, 0x2dd], [0xce, 0x2db],
    [0xcf, 0x2c7], [0xd0, 0x2014], [0xe1, 0xc6], [0xe3, 0xaa], [0xe8, 0x141], [0xe9, 0xd8], [0xea, 0x152],
    [0xeb, 0xba], [0xf1, 0xe6], [0xf5, 0x131], [0xf8, 0x142], [0xf9, 0xf8], [0xfa, 0x153], [0xfb, 0xdf]
  ];

  function standardEncoding(): string[] {
    const t = winAnsi();
    for (let c = 128; c < 256; c++) {
      t[c] = "";
    }
    for (let i = 0; i < STANDARD_HIGH.length; i++) {
      t[STANDARD_HIGH[i][0]] = String.fromCharCode(STANDARD_HIGH[i][1]);
    }
    return t;
  }

  // Helveticas bredder for tegn 32-126 - til de 14 standardskrifter, der
  // ikke har en /Widths.
  const HELVETICA_W: number[] = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667,
    611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278,
    278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556,
    333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584];

  function standardWidths(base: string, f: FontInfo): void {
    const courier = /courier/i.test(base);
    const factor = /times/i.test(base) ? 0.92 : /bold/i.test(base) ? 1.05 : 1;
    for (let c = 0; c < 256; c++) {
      if (courier) {
        f.widths.set(c, 600);
      } else if (c >= 32 && c <= 126) {
        f.widths.set(c, Math.round(HELVETICA_W[c - 32] * factor));
      } else {
        f.widths.set(c, Math.round(556 * factor));
      }
    }
    f.dw = courier ? 600 : 556;
  }

  function simpleEncoding(doc: PdfDoc, fd: PDict): string[] {
    const ev = doc.resolve(fd.m.get("Encoding"));
    let baseName = "";
    let diffs: PVal[] = [];
    if (ev instanceof PName) {
      baseName = ev.n;
    } else if (ev instanceof PDict) {
      baseName = doc.name(ev.m.get("BaseEncoding"));
      diffs = doc.arr(ev.m.get("Differences"));
    }
    const table = baseName === "MacRomanEncoding" ? macRoman()
      : baseName === "StandardEncoding" ? standardEncoding() : winAnsi();
    let code = 0;
    for (let i = 0; i < diffs.length; i++) {
      const d = doc.resolve(diffs[i]);
      if (typeof d === "number") {
        code = d;
      } else if (d instanceof PName) {
        if (code >= 0 && code < 256) {
          table[code] = glyphToUnicode(d.n);
        }
        code++;
      }
    }
    return table;
  }

  function loadFont(doc: PdfDoc, fd: PDict): FontInfo {
    const f = new FontInfo();
    const subtype = doc.name(fd.m.get("Subtype"));
    const base = doc.name(fd.m.get("BaseFont"));
    const tu = doc.resolve(fd.m.get("ToUnicode"));
    if (tu instanceof PStream) {
      try {
        parseCMap(latin1(doc.streamBytes(tu)), f, true);
      } catch {
        // uden ToUnicode bruges kodningen
      }
    }
    if (subtype === "Type0") {
      f.cid = true;
      const descs = doc.arr(fd.m.get("DescendantFonts"));
      const desc = descs.length > 0 ? doc.dict(descs[0]) : null;
      const enc = doc.resolve(fd.m.get("Encoding"));
      if (enc instanceof PStream) {
        const own = new FontInfo();
        try {
          parseCMap(latin1(doc.streamBytes(enc)), own, false);
        } catch {
          // Identity
        }
        f.cidMap = own.cidMap;
        if (own.ranges.length > 0) {
          f.ranges = own.ranges;
        }
      }
      f.dw = 1000;
      if (desc !== null) {
        const dw = doc.num(desc.m.get("DW"));
        if (dw !== null) {
          f.dw = dw;
        }
        const w = doc.arr(desc.m.get("W"));
        let i = 0;
        while (i < w.length) {
          const c1 = doc.num(w[i]);
          const nx = doc.resolve(w[i + 1]);
          if (c1 === null) {
            break;
          }
          if (nx instanceof PArr) {
            for (let k = 0; k < nx.a.length; k++) {
              const wv = doc.num(nx.a[k]);
              if (wv !== null) {
                f.widths.set(c1 + k, wv);
              }
            }
            i += 2;
          } else {
            const c2 = doc.num(w[i + 1]);
            const wv = doc.num(w[i + 2]);
            if (c2 === null || wv === null) {
              break;
            }
            for (let c = c1; c <= c2 && c - c1 < 65536; c++) {
              f.widths.set(c, wv);
            }
            i += 3;
          }
        }
      }
    } else {
      if (subtype === "Type3") {
        const fm = doc.arr(fd.m.get("FontMatrix"));
        const a = fm.length > 0 ? doc.num(fm[0]) : null;
        if (a !== null && a > 0) {
          f.scale = a;
        }
      }
      const fc = doc.num(fd.m.get("FirstChar"));
      const ws = doc.arr(fd.m.get("Widths"));
      const desc = doc.dict(fd.m.get("FontDescriptor"));
      const mw = desc === null ? null : doc.num(desc.m.get("MissingWidth"));
      if (ws.length > 0 && fc !== null) {
        let sum = 0;
        let n = 0;
        for (let k = 0; k < ws.length; k++) {
          const wv = doc.num(ws[k]);
          if (wv !== null) {
            f.widths.set(fc + k, wv);
            if (wv > 0) {
              sum += wv;
              n++;
            }
          }
        }
        f.dw = mw !== null && mw > 0 ? mw : n > 0 ? sum / n : 500;
      } else {
        standardWidths(base, f);
      }
      f.enc = simpleEncoding(doc, fd);
    }
    f.spaceW = spaceWidth(f);
    return f;
  }

  function spaceWidth(f: FontInfo): number {
    if (!f.cid) {
      const w = f.widths.get(32);
      if (w !== undefined && w > 0) {
        return w * f.scale;
      }
      return 0.278;
    }
    let found = -1;
    f.toUni.forEach((u, key) => {
      if (found < 0 && u === " ") {
        found = key % TWO32;
      }
    });
    if (found >= 0) {
      const cid = f.cidMap.size > 0 && f.cidMap.has(found) ? (f.cidMap.get(found) || found) : found;
      const w = f.widths.get(cid);
      return (w !== undefined && w > 0 ? w : 278) * f.scale;
    }
    return 0.278;
  }

  interface Glyph {
    uni: string;
    w: number;   // bredde i em
    sp: boolean; // enkeltbyte-kode 32: ordafstanden (Tw) gaelder
  }

  function decodeGlyphs(f: FontInfo, raw: string): Glyph[] {
    const out: Glyph[] = [];
    if (!f.cid) {
      for (let i = 0; i < raw.length; i++) {
        const c = raw.charCodeAt(i) & 0xff;
        let u = f.toUni.get(TWO32 + c);
        if (u === undefined) {
          u = f.enc[c] || "";
        }
        const wv = f.widths.get(c);
        out.push({ uni: u, w: (wv === undefined ? f.dw : wv) * f.scale, sp: c === 32 });
      }
      return out;
    }
    let i = 0;
    while (i < raw.length) {
      let len = 2;
      if (f.ranges.length > 0) {
        len = 0;
        for (let n = 1; n <= 4 && len === 0 && i + n <= raw.length; n++) {
          const code = codeOf(raw, i, n);
          for (let r = 0; r < f.ranges.length; r++) {
            const rg = f.ranges[r];
            if (rg[0] === n && code >= rg[1] && code <= rg[2]) {
              len = n;
              break;
            }
          }
        }
        if (len === 0) {
          len = 1;
        }
      }
      if (i + len > raw.length) {
        len = raw.length - i;
      }
      const code = codeOf(raw, i, len);
      const mapped = f.cidMap.size > 0 ? f.cidMap.get(code) : undefined;
      const cid = mapped === undefined ? code : mapped;
      const u = f.toUni.get(len * TWO32 + code);
      const wv = f.widths.get(cid);
      out.push({ uni: u === undefined ? "" : u, w: (wv === undefined ? f.dw : wv) * f.scale, sp: len === 1 && code === 32 });
      i += len;
    }
    return out;
  }

  // ===========================================================================
  // Indholdsstroemmen: hvor staar teksten?
  // ===========================================================================
  interface GState {
    ctm: number[];
    font: FontInfo | null;
    size: number;
    tc: number;
    tw: number;
    th: number;
    tl: number;
    ts: number;
  }

  interface RawWord {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
    size: number;
    text: string;
    angle: number;
    sp: number; // mellemrummets bredde i samme enheder som x
  }

  function mul(a: number[], b: number[]): number[] {
    return [
      a[0] * b[0] + a[1] * b[2],
      a[0] * b[1] + a[1] * b[3],
      a[2] * b[0] + a[3] * b[2],
      a[2] * b[1] + a[3] * b[3],
      a[4] * b[0] + a[5] * b[2] + b[4],
      a[4] * b[1] + a[5] * b[3] + b[5]
    ];
  }

  function cloneState(g: GState): GState {
    return { ctm: g.ctm.slice(), font: g.font, size: g.size, tc: g.tc, tw: g.tw, th: g.th, tl: g.tl, ts: g.ts };
  }

  const DEFAULT_FONT = (): FontInfo => {
    const f = new FontInfo();
    f.enc = winAnsi();
    standardWidths("Helvetica", f);
    return f;
  };

  function isBlankText(s: string): boolean {
    return /^[\s\u00a0\u2000-\u200b\u3000]*$/.test(s);
  }

  class TextRun {
    doc: PdfDoc;
    fonts: Map<PDict, FontInfo>;
    fallback: FontInfo;
    words: RawWord[];
    glyphs: number;
    unknown: number;

    constructor(doc: PdfDoc, fonts: Map<PDict, FontInfo>, fallback: FontInfo) {
      this.doc = doc;
      this.fonts = fonts;
      this.fallback = fallback;
      this.words = [];
      this.glyphs = 0;
      this.unknown = 0;
    }

    font(res: PDict | null, name: string): FontInfo | null {
      const fonts = res === null ? null : this.doc.dict(res.m.get("Font"));
      const fd = fonts === null ? null : this.doc.dict(fonts.m.get(name));
      if (fd === null) {
        return null;
      }
      let f = this.fonts.get(fd);
      if (f === undefined) {
        f = loadFont(this.doc, fd);
        this.fonts.set(fd, f);
      }
      return f;
    }

    run(content: string, res: PDict | null, start: GState, depth: number): void {
      const lx = new Lexer(content, 0, content.length);
      const stack: PVal[] = [];
      const saved: GState[] = [];
      let st = cloneState(start);
      let tm = [1, 0, 0, 1, 0, 0];
      let tlm = [1, 0, 0, 1, 0, 0];
      const num = (i: number): number => {
        const v = stack[stack.length - i];
        return typeof v === "number" ? v : 0;
      };
      for (;;) {
        const t = lx.read(false);
        if (t === undefined) {
          break;
        }
        if (!(t instanceof POp)) {
          stack.push(t);
          if (stack.length > 64) {
            stack.shift();
          }
          continue;
        }
        const op = t.op;
        if (op === "BT") {
          tm = [1, 0, 0, 1, 0, 0];
          tlm = [1, 0, 0, 1, 0, 0];
        } else if (op === "q") {
          saved.push(cloneState(st));
        } else if (op === "Q") {
          const back = saved.pop();
          if (back !== undefined) {
            st = back;
          }
        } else if (op === "cm" && stack.length >= 6) {
          st.ctm = mul([num(6), num(5), num(4), num(3), num(2), num(1)], st.ctm);
        } else if (op === "Tf" && stack.length >= 2) {
          const fn = stack[stack.length - 2];
          st.font = fn instanceof PName ? this.font(res, fn.n) : null;
          st.size = num(1);
        } else if (op === "Tc") {
          st.tc = num(1);
        } else if (op === "Tw") {
          st.tw = num(1);
        } else if (op === "Tz") {
          st.th = num(1) / 100;
        } else if (op === "TL") {
          st.tl = num(1);
        } else if (op === "Ts") {
          st.ts = num(1);
        } else if (op === "Td" || op === "TD") {
          if (op === "TD") {
            st.tl = -num(1);
          }
          tlm = mul([1, 0, 0, 1, num(2), num(1)], tlm);
          tm = tlm.slice();
        } else if (op === "Tm" && stack.length >= 6) {
          tlm = [num(6), num(5), num(4), num(3), num(2), num(1)];
          tm = tlm.slice();
        } else if (op === "T*") {
          tlm = mul([1, 0, 0, 1, 0, -st.tl], tlm);
          tm = tlm.slice();
        } else if (op === "Tj" || op === "'" || op === "\"") {
          if (op === "\"" && stack.length >= 3) {
            st.tw = num(3);
            st.tc = num(2);
          }
          if (op !== "Tj") {
            tlm = mul([1, 0, 0, 1, 0, -st.tl], tlm);
            tm = tlm.slice();
          }
          const sv = stack[stack.length - 1];
          if (sv instanceof PStr) {
            tm = this.show(sv.s, st, tm);
          }
        } else if (op === "TJ") {
          const av = stack[stack.length - 1];
          if (av instanceof PArr) {
            for (let i = 0; i < av.a.length; i++) {
              const e = av.a[i];
              if (e instanceof PStr) {
                tm = this.show(e.s, st, tm);
              } else if (typeof e === "number") {
                tm = mul([1, 0, 0, 1, -e / 1000 * st.size * st.th, 0], tm);
              }
            }
          }
        } else if (op === "Do" && depth < 6) {
          const xn = stack[stack.length - 1];
          const xo = res === null ? null : this.doc.dict(res.m.get("XObject"));
          const x = xo !== null && xn instanceof PName ? this.doc.resolve(xo.m.get(xn.n)) : null;
          if (x instanceof PStream && this.doc.name(x.d.m.get("Subtype")) === "Form") {
            const mx = this.doc.arr(x.d.m.get("Matrix"));
            const fm = mx.length === 6 ? mx.map((v) => {
              const n = this.doc.num(v);
              return n === null ? 0 : n;
            }) : [1, 0, 0, 1, 0, 0];
            const inner = cloneState(st);
            inner.ctm = mul(fm, st.ctm);
            const fr = this.doc.dict(x.d.m.get("Resources"));
            let body = "";
            try {
              body = latin1(this.doc.streamBytes(x));
            } catch {
              body = "";
            }
            this.run(body, fr !== null ? fr : res, inner, depth + 1);
          }
        } else if (op === "BI") {
          // Indlejret billede: spring de binaere data over.
          const id = content.indexOf("ID", lx.p);
          if (id < 0) {
            break;
          }
          const re = /\sEI(?=[\s]|$)/g;
          re.lastIndex = id + 3;
          const m = re.exec(content);
          lx.p = m === null ? content.length : m.index + m[0].length;
        }
        stack.length = 0;
      }
    }

    // Vis en streng: hvert tegn faar sin plads, og ordene samles.
    show(raw: string, st: GState, tm: number[]): number[] {
      const f = st.font !== null ? st.font : this.fallback;
      const glyphs = decodeGlyphs(f, raw);
      const fs = st.size;
      const th = st.th;
      const base = [fs * th, 0, 0, fs, 0, st.ts];
      let m = tm;
      let cur: RawWord | null = null;
      for (let i = 0; i < glyphs.length; i++) {
        const g = glyphs[i];
        const trm = mul(mul(base, m), st.ctm);
        const adv = (g.w * fs + st.tc + (g.sp ? st.tw : 0)) * th;
        const m2 = mul([1, 0, 0, 1, adv, 0], m);
        let ch = g.uni;
        this.glyphs++;
        if (ch === "") {
          ch = "\ufffd";
          this.unknown++;
        }
        if (isBlankText(ch)) {
          if (cur !== null) {
            this.words.push(cur);
            cur = null;
          }
        } else {
          const trm2 = mul(mul(base, m2), st.ctm);
          if (cur === null) {
            const size = Math.sqrt(trm[2] * trm[2] + trm[3] * trm[3]);
            cur = {
              x0: trm[4], y0: trm[5], x1: trm2[4], y1: trm2[5], size: size, text: ch,
              angle: Math.atan2(trm[1], trm[0]), sp: f.spaceW * size
            };
          } else {
            cur.text += ch;
            cur.x1 = trm2[4];
            cur.y1 = trm2[5];
          }
        }
        m = m2;
      }
      if (cur !== null) {
        this.words.push(cur);
      }
      return m;
    }
  }

  // ===========================================================================
  // Fra ord paa en side til linjer og celler
  // ===========================================================================
  interface Word {
    x0: number;
    x1: number;
    y: number;
    size: number;
    text: string;
    sp: number;
  }

  interface Cell {
    x0: number;
    x1: number;
    text: string;
  }

  interface TLine {
    page: number;
    y: number;
    size: number;
    words: Word[];
    cells: Cell[];
    text: string;
  }

  // Sidens rotation: til (X, Y nedad) som paa skaermen.
  function placeWords(raw: RawWord[], rotate: number): Word[] {
    const r = ((Math.round(rotate / 90) * 90) % 360 + 360) % 360;
    const tr = (x: number, y: number): number[] => {
      if (r === 90) {
        return [y, x];
      }
      if (r === 180) {
        return [-x, y];
      }
      if (r === 270) {
        return [-y, -x];
      }
      return [x, -y];
    };
    const out: Word[] = [];
    for (let i = 0; i < raw.length; i++) {
      const w = raw[i];
      const dx = Math.cos(w.angle);
      const dy = Math.sin(w.angle);
      const d = tr(dx, dy);
      // Kun vandret tekst, der laeses fra venstre: lodrette margintekster
      // ("Side 1 af 2" paa langs) hoerer ikke til tabellen.
      if (Math.abs(d[1]) > 0.17 || d[0] <= 0) {
        continue;
      }
      const a = tr(w.x0, w.y0);
      const b = tr(w.x1, w.y1);
      out.push({ x0: a[0], x1: Math.max(b[0], a[0]), y: a[1], size: w.size > 0 ? w.size : 10, text: w.text, sp: w.sp });
    }
    return out;
  }

  function buildLines(ws: Word[], page: number): TLine[] {
    const sorted = ws.filter((w) => w.text !== "");
    sorted.sort((a, b) => (a.y - b.y) || (a.x0 - b.x0));
    const lines: TLine[] = [];
    let cur: Word[] = [];
    let y0 = 0;
    let sz = 0;
    for (let i = 0; i < sorted.length; i++) {
      const w = sorted[i];
      if (cur.length > 0) {
        const tol = Math.max(1.0, 0.45 * Math.min(w.size, sz));
        if (Math.abs(w.y - y0) > tol) {
          lines.push(makeLine(cur, page));
          cur = [];
        }
      }
      if (cur.length === 0) {
        y0 = w.y;
        sz = w.size;
      }
      cur.push(w);
    }
    if (cur.length > 0) {
      lines.push(makeLine(cur, page));
    }
    return lines;
  }

  function makeLine(ws: Word[], page: number): TLine {
    ws.sort((a, b) => a.x0 - b.x0);
    const merged: Word[] = [];
    for (let i = 0; i < ws.length; i++) {
      const w = ws[i];
      const last = merged.length > 0 ? merged[merged.length - 1] : null;
      if (last !== null) {
        const size = Math.max(w.size, last.size);
        // Den samme tekst tegnet to gange lidt forskudt (falsk fed skrift).
        if (w.text === last.text && Math.abs(w.x0 - last.x0) < 0.3 * size) {
          continue;
        }
        const gap = w.x0 - last.x1;
        if (gap < 0.12 * size && gap > -0.5 * size) {
          last.text += w.text;
          last.x1 = Math.max(last.x1, w.x1);
          continue;
        }
      }
      merged.push({ x0: w.x0, x1: w.x1, y: w.y, size: w.size, text: w.text, sp: w.sp });
    }
    const cells: Cell[] = [];
    for (let i = 0; i < merged.length; i++) {
      const w = merged[i];
      if (i > 0 && cells.length > 0) {
        const prev = merged[i - 1];
        const gap = w.x0 - prev.x1;
        const lim = Math.max(1.6 * Math.max(prev.sp, w.sp), 0.45 * Math.max(prev.size, w.size));
        if (gap <= lim) {
          const c = cells[cells.length - 1];
          c.text += " " + w.text;
          c.x1 = w.x1;
          continue;
        }
      }
      cells.push({ x0: w.x0, x1: w.x1, text: w.text });
    }
    let y = 0;
    let size = 0;
    for (let i = 0; i < merged.length; i++) {
      y += merged[i].y;
      size = Math.max(size, merged[i].size);
    }
    return {
      page: page, y: merged.length > 0 ? y / merged.length : 0, size: size, words: merged, cells: cells,
      text: cells.map((c) => c.text).join("   ")
    };
  }

  // ===========================================================================
  // PDF-fakturaen
  // ===========================================================================
  function readPdfInvoice(bytes: Uint8Array, res: InvoiceResult): void {
    res.source = "pdf";
    res.format = "PDF";
    const doc = new PdfDoc(latin1(bytes));
    doc.load();
    if (doc.encrypted()) {
      res.error = "The PDF is protected (encrypted), so its text cannot be read. Save or print it again as an "
        + "unprotected PDF - or use the XML version of the invoice.";
      return;
    }
    const pages = doc.pages();
    res.pages = pages.length;
    const fonts = new Map<PDict, FontInfo>();
    const fallback = DEFAULT_FONT();
    const all: TLine[] = [];
    let glyphs = 0;
    let unknown = 0;
    for (let i = 0; i < pages.length; i++) {
      const pg = pages[i];
      const tr = new TextRun(doc, fonts, fallback);
      const st: GState = { ctm: [1, 0, 0, 1, 0, 0], font: null, size: 10, tc: 0, tw: 0, th: 1, tl: 0, ts: 0 };
      tr.run(doc.contentOf(pg.d.m.get("Contents")), pg.res, st, 0);
      glyphs += tr.glyphs;
      unknown += tr.unknown;
      const lines = buildLines(placeWords(tr.words, pg.rotate), i + 1);
      for (let k = 0; k < lines.length; k++) {
        all.push(lines[k]);
      }
    }
    if (pages.length === 0) {
      res.error = "The file is not a readable PDF.";
      return;
    }
    if (glyphs - unknown < 20) {
      res.warnings.push("The PDF has no text - it is probably a scanned image. A scan can only be read with OCR "
        + "(AI Builder, a premium feature). Use the supplier's PDF or XML invoice, or create the rows by hand.");
      return;
    }
    if (unknown > glyphs * 0.15) {
      res.warnings.push("Part of the text in the PDF could not be decoded (a font without a Unicode table). "
        + "Check descriptions and numbers carefully.");
    }
    const textParts: string[] = [];
    let page = 0;
    for (let i = 0; i < all.length; i++) {
      if (all[i].page !== page) {
        page = all[i].page;
        if (page > 1) {
          textParts.push("--- page " + page + " ---");
        }
      }
      textParts.push(all[i].text);
    }
    res.text = textParts.join("\n");
    const dec = detectDecimal(res.text);
    readHeader(all, res, dec);
    res.lines = readTable(all, dec);
    if (res.lines.length === 0) {
      res.lines = readLoose(all, dec);
    }
    res.plantHint = plantHint(fold(res.text));
  }

  // ---------------------------------------------------------------------------
  // Ordlister. Alt staar foldet (ae/oe/aa) og uden tegnsaetning - se normWord.
  // ---------------------------------------------------------------------------
  const COLUMN_WORDS: string[][] = [
    ["pos", "pos", "posnr", "pos nr", "linje", "linjenr", "line", "line no", "lin", "position", "lfd nr", "lfdnr", "rad"],
    ["itemNo", "varenr", "vare nr", "varenummer", "nr", "nummer", "artikelnr", "artikel nr", "artikelnummer", "art nr",
      "artnr", "item", "item no", "item nr", "item number", "item code", "part no", "part number", "product no",
      "product code", "productcode", "produktnr", "produkt nr", "sku", "katalognr", "bestillingsnr", "best nr",
      "materialenr", "materiale nr", "vores varenr", "our item no", "article", "article no", "materialnummer",
      "artikel", "varekode", "kode", "code", "ref", "reference", "itemno"],
    ["mfrPartNo", "producent varenr", "producentens varenr", "producent nr", "producentnr", "fabrikant nr",
      "fabrikat nr", "mfr part no", "mfr part number", "mfr no", "manufacturer part no", "manufacturer part number",
      "mpn", "herstellernr", "hersteller nr", "herstellernummer", "hersteller artikelnr", "tillverkarens artikelnr",
      "typenr", "type nr", "type no"],
    ["manufacturer", "producent", "fabrikat", "fabrikant", "manufacturer", "brand", "maerke", "hersteller", "marke",
      "tillverkare", "leverandoer"],
    ["desc", "beskrivelse", "varebeskrivelse", "varetekst", "tekst", "betegnelse", "varebetegnelse", "description",
      "item description", "product description", "product", "produkt", "specifikation", "bezeichnung",
      "artikelbezeichnung", "beschreibung", "text", "benaemning", "beskrivning", "spesifikasjon", "ydelse", "vare",
      "varer", "artikeltext", "leistung", "service description", "designation"],
    ["qty", "antal", "antall", "maengde", "qty", "quantity", "menge", "anzahl", "lev antal", "leveret antal",
      "leveret", "delivered", "faktureret antal", "invoiced qty", "invoiced quantity", "ant", "stk", "pcs", "kvantitet"],
    ["unit", "enhed", "enh", "unit", "uom", "um", "einheit", "me", "enhet", "eh", "unit of measure", "maaleenhed"],
    ["price", "enhedspris", "stk pris", "stkpris", "stykpris", "a pris", "apris", "pris", "unit price", "price",
      "price each", "einzelpreis", "preis", "e preis", "epreis", "ep", "pris enhet", "styckpris", "nettopris",
      "net price", "salgspris", "listepris", "list price", "bruttopris", "enhedspris dkk", "pris pr enhed", "a prix",
      "enhetspris", "pris per enhet", "a pris nok"],
    ["discount", "rabat", "rabat %", "rabat%", "discount", "disc", "rabatt", "nachlass", "rab", "rabatsats"],
    ["amount", "beloeb", "total", "line total", "amount", "net amount", "sum", "gesamt", "gesamtpreis", "betrag",
      "netto", "nettobeloeb", "belopp", "summa", "pris i alt", "i alt", "ialt", "linjebeloeb", "total price",
      "totalpris", "extended price", "ext price", "value", "vaerdi", "gesamtbetrag", "nettobetrag", "beloeb dkk",
      "linjetotal", "subtotal", "beloep", "beloep nok", "beloep eks mva"],
    ["vat", "moms", "moms %", "moms%", "vat", "vat %", "vat%", "mwst", "ust", "tax", "momskode", "moms kode", "mva"],
    ["date", "dato", "date", "datum", "leveringsdato", "delivery date", "lev dato", "levdato"]
  ];

  const NUMERIC_COLS = ["qty", "price", "discount", "amount", "vat"];

  let phraseMap: Map<string, string> | null = null;

  function phrases(): Map<string, string> {
    if (phraseMap === null) {
      const pm = new Map<string, string>();
      for (let i = 0; i < COLUMN_WORDS.length; i++) {
        const row = COLUMN_WORDS[i];
        for (let k = 1; k < row.length; k++) {
          pm.set(row[k], row[0]);
          pm.set(row[k].replace(/ /g, ""), row[0]);
        }
      }
      phraseMap = pm;
    }
    return phraseMap;
  }

  const UNIT_WORDS = ["stk", "st", "stck", "stueck", "pcs", "pc", "pce", "piece", "pieces", "ea", "each", "m", "mtr",
    "meter", "m2", "m3", "km", "cm", "mm", "kg", "g", "t", "l", "ltr", "liter", "ml", "saet", "set", "satz", "par",
    "pair", "paar", "pr", "pk", "pak", "pakke", "pack", "pck", "ks", "kasse", "box", "boks", "karton", "ctn", "rl",
    "rul", "rulle", "roll", "rolle", "time", "timer", "hour", "hours", "hrs", "h", "std", "ds", "daase", "fl",
    "flaske", "spand", "tube", "lbs", "lb", "ft", "gal", "sk", "stykke", "styk", "enhed", "unit", "units"];

  const CURRENCY_WORDS = ["dkk", "eur", "usd", "sek", "nok", "gbp", "chf", "kr", "pln"];

  const STOP_RE = /^(subtotal|sub total|total|totalt|i alt|ialt|moms|mva|vat|netto i alt|nettobeloeb|varebeloeb|beloeb i alt|at betale|til betaling|momsgrundlag|momsbeloeb|summe|zwischensumme|gesamt|gesamtbetrag|endbetrag|rechnungsbetrag|att betala|aa betale|invoice total|amount due|balance due|total due|total amount|grand total|sum|fakturabeloeb|faktura total)\b/;
  const SKIP_RE = /^(side|page|seite|sida)\s*\d+|\b(side|page|seite|sida)\s*\d+\s*(af|of|von|av|\/)\s*\d+|^(transport|overfoert|carried forward|brought forward|uebertrag|fortsaettes|continued)\b/;
  const NOTE_RE = /^(ordre|order|ordrenr|ordre nr|foelgeseddel|foelgesedler|levering|leveringsdato|delivery|your order|deres ordre|jeres ordre|vores ordre|lieferschein|auftrag|bestellung|rekvisition|requisition|sag|projekt|project|reference|ref|att|attention|kontakt)\b/;
  const CHARGE_RE = /\b(fragt|fragtgebyr|fragtomkostninger|forsendelse|forsendelsesgebyr|leveringsgebyr|porto|gebyr|ekspeditionsgebyr|faktureringsgebyr|administrationsgebyr|miljoegebyr|miljoetillaeg|olietillaeg|braendstoftillaeg|emballage|emballering|pallegebyr|engangspalle|freight|shipping|delivery charge|handling|surcharge|fuel|packaging|pallet|fee|told|afrunding|rounding|rabat|discount|kreditering|fracht|versand|verpackung|zuschlag|frakt|avgift|arbejdsloen|montage|montoer|koersel|rejsetid|labou?r|travel)\b/;

  function isUnitWord(s: string): boolean {
    return UNIT_WORDS.indexOf(normWord(s)) >= 0;
  }

  function isCurrencyWord(s: string): boolean {
    const w = normWord(s);
    return CURRENCY_WORDS.indexOf(w) >= 0 || /^[\u20ac$\u00a3]$/.test(s.trim());
  }

  // ---------------------------------------------------------------------------
  // Tabellen: overskriften giver kolonnerne, raekkerne laeses under den.
  // ---------------------------------------------------------------------------
  interface Col {
    type: string;
    x0: number;
    x1: number;
    label: string;
  }

  function headerCols(ln: TLine): Col[] | null {
    const ws = ln.words;
    if (ws.length < 2 || ws.length > 24) {
      return null;
    }
    const pm = phrases();
    const cols: Col[] = [];
    let i = 0;
    let matchedWords = 0;
    while (i < ws.length) {
      let matched = 0;
      let type = "";
      for (let n = Math.min(4, ws.length - i); n >= 1 && matched === 0; n--) {
        const parts: string[] = [];
        let close = true;
        for (let k = 0; k < n; k++) {
          parts.push(normWord(ws[i + k].text));
          if (k > 0 && ws[i + k].x0 - ws[i + k - 1].x1 > 0.9 * ws[i + k].size) {
            close = false;
          }
        }
        if (!close) {
          continue;
        }
        const hit = pm.get(parts.join(" ")) || pm.get(parts.join(""));
        if (hit !== undefined) {
          matched = n;
          type = hit;
        }
      }
      if (matched > 0) {
        const label = ws.slice(i, i + matched).map((w) => w.text).join(" ");
        cols.push({ type: type, x0: ws[i].x0, x1: ws[i + matched - 1].x1, label: label });
        matchedWords += matched;
        i += matched;
        continue;
      }
      const w = ws[i];
      const last = cols.length > 0 ? cols[cols.length - 1] : null;
      // "Enhedspris ekskl. moms": ordene efter et kendt ord hoerer til det.
      if (last !== null && w.x0 - last.x1 < 0.6 * w.size) {
        last.x1 = Math.max(last.x1, w.x1);
        last.label += " " + w.text;
      } else {
        cols.push({ type: "other", x0: w.x0, x1: w.x1, label: w.text });
      }
      i++;
    }
    const types: string[] = [];
    for (let k = 0; k < cols.length; k++) {
      if (cols[k].type !== "other" && types.indexOf(cols[k].type) < 0) {
        types.push(cols[k].type);
      }
    }
    const has = (t: string): boolean => types.indexOf(t) >= 0;
    const numbers = ws.filter((w) => /\d/.test(w.text) && parseNumber(w.text, ",") !== null).length;
    const others = cols.filter((c) => c.type === "other").length;
    if (numbers > 1 || others > types.length || matchedWords * 2 < ws.length) {
      return null;
    }
    const numeric = has("qty") || has("price") || has("amount");
    if (types.length >= 3 && numeric) {
      return cols;
    }
    if (types.length >= 2 && numeric && (has("desc") || has("itemNo"))) {
      return cols;
    }
    return null;
  }

  interface RowTok {
    w: Word;
    v: number | null;
  }

  interface Row {
    kind: string; // item, text, other
    line: InvoiceLine;
    text: string;
  }

  function emptyLine(): InvoiceLine {
    return {
      lineNo: 0, description: "", extraText: "", supplierPartNo: "", manufacturer: "", manufacturerPartNo: "",
      model: "", gtin: "", quantity: null, unit: "", unitPrice: null, priceUnit: null, discountPct: null,
      amount: null, isCharge: false, check: ""
    };
  }

  function numericCol(cols: Col[], w: Word): number {
    let best = -1;
    let bestD = Infinity;
    const mid = (w.x0 + w.x1) / 2;
    for (let i = 0; i < cols.length; i++) {
      const c = cols[i];
      if (NUMERIC_COLS.indexOf(c.type) < 0) {
        continue;
      }
      let d = Math.min(Math.abs(w.x1 - c.x1), Math.abs(w.x0 - c.x0), Math.abs(mid - (c.x0 + c.x1) / 2));
      if (w.x1 >= c.x0 && w.x0 <= c.x1) {
        d = 0;
      }
      const lim = Math.max(1.5 * w.size, (c.x1 - c.x0) * 0.6);
      if (d <= lim && d < bestD) {
        best = i;
        bestD = d;
      }
    }
    return best;
  }

  function textCol(cols: Col[], w: Word): number {
    let best = -1;
    for (let i = 0; i < cols.length; i++) {
      if (NUMERIC_COLS.indexOf(cols[i].type) >= 0) {
        continue;
      }
      if (cols[i].x0 <= w.x0 + 0.6 * w.size) {
        best = i;
      }
    }
    if (best < 0) {
      for (let i = 0; i < cols.length; i++) {
        if (NUMERIC_COLS.indexOf(cols[i].type) < 0) {
          return i;
        }
      }
      return 0;
    }
    return best;
  }

  // "1 245,00": tusindtal skrevet med mellemrum er to ord - og det foerste
  // ord ville havne i nabokolonnen. To tal med hoejst eet mellemrum imellem,
  // hvor det foerste er hele tusindtalsgrupper og det andet starter med tre
  // cifre, er eet tal. Kolonner staar laengere fra hinanden end eet mellemrum.
  function joinThousands(ws: Word[], dec: string): Word[] {
    const out: Word[] = [];
    for (let i = 0; i < ws.length; i++) {
      const w = ws[i];
      const prev = out.length > 0 ? out[out.length - 1] : null;
      if (prev !== null && /^-?\d{1,3}(\d{3})*$/.test(prev.text) && /^\d{3}([.,]\d+)?-?$/.test(w.text)
        && w.x0 - prev.x1 <= 1.6 * Math.max(prev.sp, w.sp, 0.2 * w.size)) {
        const text = prev.text + w.text;
        if (parseNumber(text, dec) !== null) {
          out[out.length - 1] = { x0: prev.x0, x1: w.x1, y: w.y, size: w.size, text: text, sp: w.sp };
          continue;
        }
      }
      out.push(w);
    }
    return out;
  }

  function joinThousandsText(t: string): string {
    return t.replace(/(\d)[ \u00a0\u202f](?=\d{3}(?:[.,]\d+)?\b)/g, "$1");
  }

  function readRow(ln: TLine, cols: Col[], dec: string): Row {
    const by: RowTok[][] = cols.map(() => []);
    const unitToks: string[] = [];
    const ws = joinThousands(ln.words, dec);
    let lastNumCol = -1;
    let lastNumX = -Infinity;
    for (let i = 0; i < ws.length; i++) {
      const w = ws[i];
      const v = /\d/.test(w.text) ? parseNumber(w.text, dec) : null;
      let ci = v !== null ? numericCol(cols, w) : -1;
      if (ci >= 0) {
        by[ci].push({ w: w, v: v });
        lastNumCol = ci;
        lastNumX = w.x1;
        continue;
      }
      // "2 stk": en enhed lige efter et tal i en talkolonne.
      if (lastNumCol >= 0 && cols[lastNumCol].type === "qty" && isUnitWord(w.text)
        && w.x0 - lastNumX < 2.5 * w.size) {
        unitToks.push(w.text);
        continue;
      }
      if (isCurrencyWord(w.text) || w.text === "%") {
        continue;
      }
      ci = textCol(cols, w);
      by[ci].push({ w: w, v: v });
    }
    const line = emptyLine();
    const textOf = (type: string): string => {
      const parts: string[] = [];
      for (let i = 0; i < cols.length; i++) {
        if (cols[i].type === type) {
          for (let k = 0; k < by[i].length; k++) {
            parts.push(by[i][k].w.text);
          }
        }
      }
      return collapse(parts.join(" "));
    };
    const numOf = (type: string, last: boolean): number | null => {
      let out: number | null = null;
      for (let i = 0; i < cols.length; i++) {
        if (cols[i].type !== type) {
          continue;
        }
        for (let k = 0; k < by[i].length; k++) {
          const v = by[i][k].v;
          if (v !== null && (out === null || last)) {
            out = v;
          }
        }
      }
      return out;
    };
    let desc = textOf("desc");
    let itemNo = textOf("itemNo");
    if (desc === "" && cols.every((c) => c.type !== "desc")) {
      desc = textOf("other");
    }
    if (desc === "" && itemNo.indexOf(" ") > 0) {
      const parts = itemNo.split(" ");
      itemNo = parts[0];
      desc = parts.slice(1).join(" ");
    }
    line.description = desc;
    line.supplierPartNo = itemNo;
    line.manufacturer = textOf("manufacturer");
    line.manufacturerPartNo = textOf("mfrPartNo");
    line.quantity = numOf("qty", false);
    line.unitPrice = numOf("price", true);
    line.discountPct = numOf("discount", false);
    line.amount = numOf("amount", true);
    const unit = textOf("unit");
    line.unit = cleanUnit(unit !== "" ? unit : unitToks.join(" "));
    const hasText = desc !== "" || itemNo !== "" || textOf("other") !== "";
    const anyNum = line.quantity !== null || line.unitPrice !== null || line.amount !== null;
    let kind = "other";
    if ((line.quantity !== null && (line.unitPrice !== null || line.amount !== null) && hasText)
      || (line.amount !== null && line.quantity === null && hasText && desc !== "")) {
      kind = "item";
    } else if (!anyNum && hasText) {
      kind = "text";
    } else if (!hasText && line.quantity !== null && (line.unitPrice !== null || line.amount !== null)) {
      // Kun tal: varen staar paa to linjer, teksten over tallene (readTable).
      kind = "numbers";
    }
    const all = collapse(ws.map((w) => w.text).join(" "));
    return { kind: kind, line: line, text: all };
  }

  function cleanUnit(u: string): string {
    const t = collapse(u).replace(/\.+$/, "");
    return t.length > 12 ? "" : t.toUpperCase();
  }

  // Laes "Varenr.: 123" o.l. i en fortsaettelseslinje ind i feltet.
  const LABELLED: string[][] = [
    ["supplierPartNo", "varenr", "vare nr", "varenummer", "art nr", "artnr", "artikelnr", "artikel nr", "item no",
      "item nr", "part no", "sku", "vores varenr", "our item no", "bestillingsnr", "best nr"],
    ["manufacturerPartNo", "producent varenr", "producentens varenr", "prod varenr", "producentnr", "producent nr",
      "mfr part no", "mfr no", "mpn", "manufacturer part no", "manufacturer part number", "hersteller nr",
      "herstellernr", "herst nr", "typenr", "type nr", "fabrikant nr", "fabrikat nr"],
    ["manufacturer", "producent", "fabrikat", "fabrikant", "manufacturer", "brand", "maerke", "hersteller", "marke"],
    ["gtin", "ean", "ean nr", "ean kode", "gtin", "ean code"],
    ["model", "model", "modelnr", "model nr", "type", "typebetegnelse"]
  ];

  function labelled(text: string): string[] {
    const ws = words(text);
    for (let n = Math.min(4, ws.length - 1); n >= 1; n--) {
      const key = ws.slice(0, n).map((w) => normWord(w)).join(" ");
      for (let i = 0; i < LABELLED.length; i++) {
        if (LABELLED[i].indexOf(key) <= 0) {
          continue;
        }
        // "Fabrikat: SKF" eller "Varenr. 123" - men ikke "Type 2 kugleleje".
        const colon = /:$/.test(ws[n - 1]) || /^:/.test(ws[n]);
        const last = normWord(ws[n - 1]);
        if (!colon && !/(nr|no|nummer)$/.test(last) && ["ean", "gtin", "mpn", "sku"].indexOf(last) < 0) {
          continue;
        }
        const value = collapse(ws.slice(n).join(" ").replace(/^[:#.\-\s]+/, ""));
        if (value !== "") {
          return [LABELLED[i][0], value];
        }
      }
    }
    return [];
  }

  function addContinuation(l: InvoiceLine, text: string): void {
    const lv = labelled(text);
    if (lv.length === 2) {
      const v = lv[1];
      if (lv[0] === "supplierPartNo" && l.supplierPartNo === "") {
        l.supplierPartNo = v;
        return;
      }
      if (lv[0] === "manufacturerPartNo" && l.manufacturerPartNo === "") {
        l.manufacturerPartNo = v;
        return;
      }
      if (lv[0] === "manufacturer" && l.manufacturer === "") {
        l.manufacturer = v;
        return;
      }
      if (lv[0] === "gtin" && l.gtin === "" && /^\d{8,14}$/.test(v.replace(/\s/g, ""))) {
        l.gtin = v.replace(/\s/g, "");
        return;
      }
      if (lv[0] === "model" && l.model === "") {
        l.model = v;
        return;
      }
    }
    l.extraText = collapse((l.extraText + " " + text));
  }

  interface Tail {
    last: InvoiceLine | null;
    y: number;
    page: number;
  }

  interface Pending {
    row: Row;
    ln: TLine;
  }

  function firstCellOf(ln: TLine): string {
    return ln.cells.length > 0 ? fold(ln.cells[0].text) : "";
  }

  // Den ventende tekstlinje var en fortsaettelse af forrige vare - hvis den
  // staar lige under den.
  function flushPending(hold: Pending[], tail: Tail): void {
    const p = hold.pop();
    if (p === undefined) {
      return;
    }
    const last = tail.last;
    if (last !== null && p.ln.page === tail.page && p.ln.y - tail.y < 2.6 * p.ln.size
      && !NOTE_RE.test(firstCellOf(p.ln))) {
      addContinuation(last, p.row.text);
      tail.y = p.ln.y;
    }
  }

  // En tekstlinje uden tal er ENTEN fortsaettelsen af forrige vare ELLER
  // teksten til den naeste, naar varen staar paa to linjer (tekst over
  // tallene). Det vides foerst ved naeste linje - derfor venter den (hold).
  function readTable(lines: TLine[], dec: string): InvoiceLine[] {
    const out: InvoiceLine[] = [];
    let cols: Col[] | null = null;
    let open = false;
    let headerPage = 0;
    const tail: Tail = { last: null, y: 0, page: 0 };
    const hold: Pending[] = [];
    for (let i = 0; i < lines.length; i++) {
      const ln = lines[i];
      const f = fold(ln.text);
      const h = headerCols(ln);
      if (h !== null) {
        flushPending(hold, tail);
        cols = h;
        open = true;
        headerPage = ln.page;
        tail.last = null;
        continue;
      }
      if (!open || cols === null) {
        continue;
      }
      if (SKIP_RE.test(f)) {
        continue;
      }
      const first = firstCellOf(ln);
      const row = readRow(ln, cols, dec);
      if (STOP_RE.test(first) || (STOP_RE.test(f) && row.line.quantity === null)) {
        flushPending(hold, tail);
        open = false;
        tail.last = null;
        continue;
      }
      if (row.kind === "numbers") {
        const p = hold.pop();
        if (p !== undefined) {
          const t = p.row.line;
          row.line.description = t.description !== "" ? t.description : p.row.text;
          row.line.supplierPartNo = t.supplierPartNo;
          row.line.manufacturer = t.manufacturer;
          row.line.manufacturerPartNo = t.manufacturerPartNo;
          row.kind = "item";
        }
      }
      if (row.kind === "item") {
        flushPending(hold, tail);
        finishLine(row.line);
        // Paa en side uden sin egen overskrift skal raekken kunne regnes efter:
        // ellers kunne et brevhoved med tal ligne en varelinje.
        if (ln.page !== headerPage && row.line.check !== "ok") {
          continue;
        }
        out.push(row.line);
        tail.last = row.line;
        tail.y = ln.y;
        tail.page = ln.page;
        continue;
      }
      flushPending(hold, tail);
      if (row.kind === "text") {
        hold.push({ row: row, ln: ln });
      }
    }
    flushPending(hold, tail);
    return out;
  }

  // Reserven, naar der ingen overskrift er: linjer, der ender paa antal,
  // pris og beloeb - og som kan regnes efter. Tal foran dem hoerer til
  // beskrivelsen ("Kileremme SPA 1250").
  function readLoose(lines: TLine[], dec: string): InvoiceLine[] {
    const out: InvoiceLine[] = [];
    for (let li = 0; li < lines.length; li++) {
      const ws = joinThousands(lines[li].words, dec);
      const at: number[] = [];
      const vals: number[] = [];
      let unit = "";
      let k = ws.length;
      while (k > 0) {
        const w = ws[k - 1];
        const v = /\d/.test(w.text) ? parseNumber(w.text, dec) : null;
        if (v !== null) {
          at.unshift(k - 1);
          vals.unshift(v);
          k--;
          continue;
        }
        if (unit === "" && vals.length > 0 && isUnitWord(w.text)) {
          unit = w.text;
          k--;
          continue;
        }
        if (isCurrencyWord(w.text) || w.text === "%") {
          k--;
          continue;
        }
        break;
      }
      const n = vals.length;
      if (n < 3) {
        continue;
      }
      const l = emptyLine();
      let first = -1;
      if (near(vals[n - 3] * vals[n - 2], vals[n - 1])) {
        first = n - 3;
        l.quantity = vals[n - 3];
        l.unitPrice = vals[n - 2];
        l.amount = vals[n - 1];
      } else if (n >= 4 && near(vals[n - 4] * vals[n - 3] * (1 - vals[n - 2] / 100), vals[n - 1])) {
        first = n - 4;
        l.quantity = vals[n - 4];
        l.unitPrice = vals[n - 3];
        l.discountPct = vals[n - 2];
        l.amount = vals[n - 1];
      } else {
        continue;
      }
      const desc = ws.slice(0, at[first]).map((w) => w.text);
      if (!/[A-Za-z\u00c0-\u00ff]{2}/.test(desc.join(" "))) {
        continue;
      }
      l.description = collapse(desc.join(" "));
      l.unit = cleanUnit(unit);
      finishLine(l);
      out.push(l);
    }
    return out;
  }

  // Fragt, gebyrer, rabatter og krediterede linjer er ikke materialer. De
  // tages med - men er ikke valgt, naar brugeren ser dem.
  function isChargeLine(l: InvoiceLine): boolean {
    return CHARGE_RE.test(fold(l.description + " " + l.extraText)) || (l.amount !== null && l.amount < 0);
  }

  function near(x: number, y: number): boolean {
    return Math.abs(x - y) <= Math.max(0.011, Math.abs(y) * 0.005);
  }

  // En foerste kolonne som "6205-2RS Kugleleje": nummeret ud af teksten -
  // kun naar det ligner et varenummer (mindst 5 tegn, 3 cifre, ingen smaa
  // bogstaver), saa "M12x50 bolt" ikke bliver et varenummer.
  function splitPartNo(l: InvoiceLine): void {
    if (l.supplierPartNo !== "") {
      return;
    }
    const ws = words(l.description);
    if (ws.length < 2) {
      return;
    }
    const first = ws[0];
    const digits = first.replace(/\D/g, "").length;
    const rest = ws.slice(1).join(" ");
    if (first.length >= 5 && digits >= 3 && !/[a-z\u00e6\u00f8\u00e5]/.test(first)
      && /^[A-Z0-9][A-Z0-9\-\/.]+$/.test(first) && /[A-Za-z\u00c0-\u00ff]{2}/.test(rest)) {
      l.supplierPartNo = first;
      l.description = rest;
    }
  }

  function finishLine(l: InvoiceLine): void {
    l.description = collapse(l.description);
    l.extraText = collapse(l.extraText);
    splitPartNo(l);
    const q = l.quantity;
    const p = l.unitPrice;
    const a = l.amount;
    if (q !== null && p === null && a !== null && q !== 0) {
      l.unitPrice = round(a / q, 4);
    }
    if (q !== null && p !== null && a === null) {
      l.amount = round(q * p * (1 - (l.discountPct || 0) / 100), 2);
    }
    if (q !== null && p !== null && a !== null) {
      const exp = q * p * (1 - (l.discountPct || 0) / 100);
      if (near(exp, a)) {
        l.check = "ok";
      } else if (near(exp / 100, a)) {
        l.priceUnit = 100;
        l.check = "ok";
      } else if (near(exp / 1000, a)) {
        l.priceUnit = 1000;
        l.check = "ok";
      } else {
        l.check = "mismatch";
      }
    } else {
      l.check = q !== null && l.unitPrice !== null && l.amount !== null ? "ok" : "incomplete";
    }
    l.isCharge = isChargeLine(l);
    if (l.description === "" && l.supplierPartNo !== "") {
      l.description = l.supplierPartNo;
    }
  }

  // ---------------------------------------------------------------------------
  // Fakturaens hoved: nummer, dato, ordre, leverandoer, valuta, subtotal
  // ---------------------------------------------------------------------------
  const LBL_INVOICE_NO = ["fakturanr", "faktura nr", "fakturanummer", "faktura no", "faktura nummer", "invoice no",
    "invoice nr", "invoice number", "invoice", "rechnungsnummer", "rechnungsnr", "rechnung nr", "rechnungs nr",
    "rechnung", "faktura", "kreditnota nr", "kreditnotanr", "kreditnota", "credit note no", "credit note", "bilagsnr",
    "dokumentnr", "document no", "fakturanumre"];
  const LBL_DATE = ["fakturadato", "faktura dato", "invoice date", "rechnungsdatum", "fakturadatum", "dato", "date",
    "datum", "udstedelsesdato", "issue date", "bilagsdato", "dokumentdato"];
  const LBL_ORDER = ["deres ordre", "deres ordrenr", "deres ordre nr", "deres rekvisition", "deres ref", "jeres ordre",
    "jeres ordrenr", "your order", "your order no", "your order number", "your po", "your ref", "customer order",
    "customer order no", "purchase order", "purchase order no", "po no", "po number", "po", "indkoebsordre",
    "indkoebsordrenr", "rekvisition", "rekvisitionsnr", "ihre bestellung", "ihre bestellnummer", "bestellnummer",
    "best nr", "kundeordre", "kundens ordre", "ordre nr", "ordrenr", "ordrenummer", "order no", "order number",
    "bestillingsnr", "bestilling", "deres bestilling"];
  const LBL_SUPPLIER = ["leverandoer", "supplier", "saelger", "seller", "lieferant", "vendor", "kreditor", "fra", "from"];
  const LBL_CURRENCY = ["valuta", "currency", "waehrung", "devise", "valutakode"];
  const LBL_NET = ["subtotal", "sub total", "netto", "nettobeloeb", "netto i alt", "varebeloeb", "beloeb ekskl moms",
    "beloeb excl moms", "total ekskl moms", "i alt ekskl moms", "subtotal ekskl moms", "total excl vat",
    "total excl", "total exkl moms", "net total", "total net", "net amount", "nettobetrag", "zwischensumme",
    "summe netto", "momsgrundlag", "momspligtigt beloeb", "total excluding vat", "netto beloeb", "ordretotal",
    "varer i alt", "total before vat", "amount excl vat", "i alt ekskl", "beloeb ekskl", "sum eks mva",
    "sum ekskl mva", "sum eksklusiv mva", "totalt eks mva", "netto eks mva", "summa exkl moms"];

  function labelLength(ws: string[], labels: string[]): number {
    for (let n = Math.min(5, ws.length); n >= 1; n--) {
      const key = ws.slice(0, n).map((w) => normWord(w)).filter((w) => w !== "").join(" ");
      if (key !== "" && labels.indexOf(key) >= 0) {
        return n;
      }
    }
    return 0;
  }

  // Vaerdien efter en etiket: i samme celle, i cellen til hoejre eller i
  // cellen lige under.
  function findLabelled(lines: TLine[], labels: string[], ok: (v: string) => string, pagesMax: number): string {
    for (let i = 0; i < lines.length; i++) {
      const ln = lines[i];
      if (ln.page > pagesMax) {
        break;
      }
      for (let c = 0; c < ln.cells.length; c++) {
        const cell = ln.cells[c];
        const ws = words(cell.text);
        const n = labelLength(ws, labels);
        if (n === 0) {
          continue;
        }
        const same = ok(ws.slice(n).join(" ").replace(/^[\s:#.\-]+/, ""));
        if (same !== "") {
          return same;
        }
        if (c + 1 < ln.cells.length) {
          const right = ok(ln.cells[c + 1].text.replace(/^[\s:#.\-]+/, ""));
          if (right !== "") {
            return right;
          }
        }
        for (let k = i + 1; k < lines.length && k <= i + 2; k++) {
          const below = lines[k];
          if (below.page !== ln.page || below.y - ln.y > 3 * ln.size) {
            break;
          }
          for (let b = 0; b < below.cells.length; b++) {
            const bc = below.cells[b];
            if (bc.x1 >= cell.x0 - ln.size && bc.x0 <= cell.x1 + 2 * ln.size) {
              const v = ok(bc.text);
              if (v !== "") {
                return v;
              }
            }
          }
        }
      }
    }
    return "";
  }

  function okInvoiceNo(v: string): string {
    const ws = words(v.replace(/^(nr|no|nummer|number)\.?\s*[:#]?\s*/i, ""));
    if (ws.length === 0) {
      return "";
    }
    const t = ws[0].replace(/[,;:]$/, "");
    if (!/\d/.test(t) || t.length > 25 || !/^[A-Za-z0-9][A-Za-z0-9\-\/._]*$/.test(t) || parseDate(t) !== "") {
      return "";
    }
    return t;
  }

  function okDate(v: string): string {
    return parseDate(v);
  }

  function okOrder(v: string): string {
    const ws = words(v.replace(/^(nr|no|nummer|number)\.?\s*[:#]?\s*/i, ""));
    if (ws.length === 0) {
      return "";
    }
    const t = ws[0].replace(/[,;:]$/, "");
    return /\d{3,}/.test(t) && t.length <= 30 && parseDate(t) === "" ? t : "";
  }

  function okCurrency(v: string): string {
    const m = /\b(DKK|EUR|USD|SEK|NOK|GBP|CHF|PLN)\b/i.exec(v);
    return m ? m[1].toUpperCase() : "";
  }

  const COMPANY_RE = /^(.{2,80}?\s(?:A\/S|ApS|I\/S|K\/S|P\/S|IVS|AMBA|A\.m\.b\.a\.|GmbH(?:\s*&\s*Co\.?\s*KG)?|AG|KG|AB|ASA|AS|Oyj|Oy|Ltd\.?|Limited|Inc\.?|LLC|B\.V\.|BV|N\.V\.|NV|S\.A\.S?|SAS|S\.p\.A\.|S\.r\.l\.|Sp\.\s?z\s?o\.o\.|plc|PLC|Corp\.?|Corporation))(?=$|[\s,.;:)|\u00b7\u2022-])/;
  const BUYER_RE = /oersted|orsted|dong energy/;
  const NOT_COMPANY_RE = /\bbank\b|sparekasse|nordea|handelsbanken|nykredit|danske bank|jyske|sydbank|spar nord/;
  const VAT_RES: RegExp[] = [
    /\b(?:CVR|C\.V\.R\.)[\s.\-]*(?:nr|no|nummer)?[.:\s\-]*(?:DK[\s\-]?)?(\d{2}\s?\d{2}\s?\d{2}\s?\d{2})\b/i,
    /\bSE[\s.\-]*(?:nr|no)[.:\s\-]*(?:DK[\s\-]?)?(\d{8})\b/i,
    /\b(?:VAT|Moms|MwSt|USt|Ust)[\s.\-]*(?:reg(?:istration)?[\s.\-]*)?(?:no|nr|number|id|idnr|id[\s.\-]*nr)?[.:\s\-]*([A-Z]{2}[\s\-]?[0-9A-Z]{8,12})\b/i,
    /\b(DK[\s\-]?\d{8})\b/,
    /\bOrg[\s.\-]*(?:nr|no)[.:\s\-]*(\d{3}\s?\d{3}\s?\d{3}|\d{6}-\d{4})\b/i
  ];
  // Oersteds eget CVR-nummer staar paa fakturaen som koeberens - ikke leverandoerens.
  const BUYER_VAT = ["36213728"];

  function companyIn(text: string): string {
    const m = COMPANY_RE.exec(collapse(text));
    if (!m) {
      return "";
    }
    let name = m[1].replace(/^(fra|from|leverand\u00f8r|leverandoer|supplier|s\u00e6lger|seller|lieferant)\s*:\s*/i, "");
    name = collapse(name);
    const f = fold(name);
    if (BUYER_RE.test(f) || NOT_COMPANY_RE.test(f) || !/[A-Za-z\u00c0-\u00ff]{2}/.test(name)) {
      return "";
    }
    return name;
  }

  function readHeader(lines: TLine[], res: InvoiceResult, dec: string): void {
    res.invoiceNo = findLabelled(lines, LBL_INVOICE_NO, okInvoiceNo, 1);
    res.invoiceDate = findLabelled(lines, LBL_DATE, okDate, 1);
    if (res.invoiceDate === "") {
      for (let i = 0; i < lines.length && lines[i].page === 1 && res.invoiceDate === ""; i++) {
        res.invoiceDate = parseDate(lines[i].text);
      }
    }
    res.orderNo = findLabelled(lines, LBL_ORDER, okOrder, 2);
    res.currency = findLabelled(lines, LBL_CURRENCY, okCurrency, 3);
    if (res.currency === "") {
      const counts: number[] = [];
      const codes = ["DKK", "EUR", "USD", "SEK", "NOK", "GBP", "CHF", "PLN"];
      const all = lines.map((l) => l.text).join("\n");
      let best = -1;
      for (let i = 0; i < codes.length; i++) {
        counts.push((all.match(new RegExp("\\b" + codes[i] + "\\b", "g")) || []).length);
        if (counts[i] > 0 && (best < 0 || counts[i] > counts[best])) {
          best = i;
        }
      }
      if (best >= 0) {
        res.currency = codes[best];
      } else if (/\u20ac/.test(all)) {
        res.currency = "EUR";
      } else if (/\bkr\.?\s?\d|\d\s?kr\b/i.test(all) && /moms|bel\u00f8b|i alt/i.test(all)) {
        res.currency = "DKK";
      }
    }
    const net = findLabelled(lines, LBL_NET, (v: string): string => {
      const ws = words(joinThousandsText(v));
      for (let k = ws.length - 1; k >= 0; k--) {
        const n = /\d/.test(ws[k]) ? parseNumber(ws[k], dec) : null;
        if (n !== null) {
          return String(n);
        }
      }
      return "";
    }, 99);
    res.netTotal = net === "" ? null : parseFloat(net);

    // Leverandoeren: en etiket, ellers navnet ved CVR-nummeret, ellers det
    // foerste firmanavn paa side 1, der ikke er koeberens eller bankens.
    let vatLine = -1;
    for (let i = 0; i < lines.length && res.supplierVatNo === ""; i++) {
      const f = fold(lines[i].text);
      if (BUYER_RE.test(f) || /kunde|customer|koeber|buyer|debitor|deres cvr|jeres cvr|your vat/.test(f)) {
        continue;
      }
      for (let r = 0; r < VAT_RES.length; r++) {
        const m = VAT_RES[r].exec(lines[i].text);
        if (m) {
          const v = m[1].replace(/[\s\-]/g, "").toUpperCase();
          if (BUYER_VAT.indexOf(v.replace(/^DK/, "")) < 0) {
            res.supplierVatNo = v;
            vatLine = i;
            break;
          }
        }
      }
    }
    const lbl = findLabelled(lines, LBL_SUPPLIER, (v: string): string => companyIn(v), 1);
    if (lbl !== "") {
      res.supplierName = lbl;
    }
    if (res.supplierName === "" && vatLine >= 0) {
      for (let d = 0; d <= 3 && res.supplierName === ""; d++) {
        const idx = [vatLine - d, vatLine + d];
        for (let k = 0; k < idx.length && res.supplierName === ""; k++) {
          const i = idx[k];
          if (i >= 0 && i < lines.length && lines[i].page === lines[vatLine].page) {
            for (let c = 0; c < lines[i].cells.length && res.supplierName === ""; c++) {
              res.supplierName = companyIn(lines[i].cells[c].text);
            }
          }
        }
      }
    }
    for (let i = 0; i < lines.length && lines[i].page === 1 && res.supplierName === ""; i++) {
      for (let c = 0; c < lines[i].cells.length && res.supplierName === ""; c++) {
        res.supplierName = companyIn(lines[i].cells[c].text);
      }
    }
    if (res.supplierName === "") {
      res.supplierName = letterhead(lines);
    }
  }

  // Sidste udvej: navnet i brevhovedet - den stoerste tekst i oeverste
  // tredjedel af side 1, der ikke er "FAKTURA", koeberen eller et tal.
  function letterhead(lines: TLine[]): string {
    const p1 = lines.filter((l) => l.page === 1 && l.cells.length > 0);
    if (p1.length < 3) {
      return "";
    }
    let minY = Infinity;
    let maxY = -Infinity;
    const sizes: number[] = [];
    for (let i = 0; i < p1.length; i++) {
      minY = Math.min(minY, p1[i].y);
      maxY = Math.max(maxY, p1[i].y);
      sizes.push(p1[i].size);
    }
    sizes.sort((a, b) => a - b);
    const median = sizes[Math.floor(sizes.length / 2)];
    let best: TLine | null = null;
    for (let i = 0; i < p1.length; i++) {
      const l = p1[i];
      const t = collapse(l.cells[0].text);
      const f = fold(t);
      if (l.y > minY + (maxY - minY) / 3 || l.size < median * 1.2 || !/[a-z]{3}/.test(f) || /\d{3}/.test(t)
        || /^(faktura|invoice|rechnung|kreditnota|credit note|gutschrift|tax invoice|proforma)/.test(f)
        || BUYER_RE.test(f) || NOT_COMPANY_RE.test(f)) {
        continue;
      }
      if (best === null || l.size > best.size) {
        best = l;
      }
    }
    return best === null ? "" : collapse(best.cells[0].text);
  }

  // ---------------------------------------------------------------------------
  // Vaerket ud fra leveringsadressen. Kun vaerkernes navne ("Studstrupvaerket",
  // "Herning Kraftvarmevaerk") - ikke bynavnene: en leverandoer kan sagtens
  // bo i Herning eller paa Avedoere Holme. Koderne er PlantList's.
  // ---------------------------------------------------------------------------
  const PLANTS: string[][] = [
    ["AVV", "avedoere"], ["ASV", "asnaes"], ["HEV", "herning"], ["KYV", "kyndby"], ["SKV", "skaerbaek"],
    ["SSV", "studstrup"]
  ];

  function plantHint(folded: string): string {
    const hits: string[] = [];
    for (let i = 0; i < PLANTS.length; i++) {
      const re = new RegExp(PLANTS[i][1] + "\\s?(kraft(varme)?)?\\s?(vaerk|verk)");
      if (re.test(folded)) {
        hits.push(PLANTS[i][0]);
      }
    }
    return hits.length === 1 ? hits[0] : "";
  }

  // ===========================================================================
  // XML: OIOUBL og Peppol BIS (UBL 2.x)
  // ===========================================================================
  class XNode {
    name: string;
    local: string;
    attrs: Map<string, string>;
    kids: XNode[];
    text: string;
    constructor(name: string) {
      this.name = name;
      const c = name.indexOf(":");
      this.local = c >= 0 ? name.substring(c + 1) : name;
      this.attrs = new Map<string, string>();
      this.kids = [];
      this.text = "";
    }
  }

  function decodeEntities(s: string): string {
    if (s.indexOf("&") < 0) {
      return s;
    }
    return s.replace(/&(#x[0-9a-fA-F]+|#\d+|amp|lt|gt|quot|apos);/g, (m: string, e: string): string => {
      if (e === "amp") {
        return "&";
      }
      if (e === "lt") {
        return "<";
      }
      if (e === "gt") {
        return ">";
      }
      if (e === "quot") {
        return "\"";
      }
      if (e === "apos") {
        return "'";
      }
      const cp = e.charAt(1) === "x" ? parseInt(e.substring(2), 16) : parseInt(e.substring(1), 10);
      if (cp > 0xffff) {
        const c = cp - 0x10000;
        return String.fromCharCode(0xd800 + (c >> 10), 0xdc00 + (c & 0x3ff));
      }
      return String.fromCharCode(cp);
    });
  }

  function tagEnd(s: string, p: number): number {
    let q = "";
    for (let i = p; i < s.length; i++) {
      const c = s.charAt(i);
      if (q !== "") {
        if (c === q) {
          q = "";
        }
      } else if (c === "\"" || c === "'") {
        q = c;
      } else if (c === ">") {
        return i;
      }
    }
    return s.length;
  }

  function parseXml(s: string): XNode {
    const root = new XNode("#document");
    const stack: XNode[] = [root];
    let p = 0;
    const n = s.length;
    while (p < n) {
      const top = stack[stack.length - 1];
      const lt = s.indexOf("<", p);
      if (lt < 0) {
        top.text += decodeEntities(s.substring(p));
        break;
      }
      if (lt > p) {
        top.text += decodeEntities(s.substring(p, lt));
      }
      if (s.substr(lt, 4) === "<!--") {
        const e = s.indexOf("-->", lt + 4);
        p = e < 0 ? n : e + 3;
        continue;
      }
      if (s.substr(lt, 9) === "<![CDATA[") {
        const e = s.indexOf("]]>", lt + 9);
        top.text += s.substring(lt + 9, e < 0 ? n : e);
        p = e < 0 ? n : e + 3;
        continue;
      }
      if (s.substr(lt, 2) === "<?") {
        const e = s.indexOf("?>", lt + 2);
        p = e < 0 ? n : e + 2;
        continue;
      }
      if (s.substr(lt, 2) === "<!") {
        let depth = 0;
        let q = lt + 2;
        while (q < n) {
          const ch = s.charAt(q);
          if (ch === "[") {
            depth++;
          } else if (ch === "]") {
            depth--;
          } else if (ch === ">" && depth <= 0) {
            break;
          }
          q++;
        }
        p = q + 1;
        continue;
      }
      const gt = tagEnd(s, lt + 1);
      const inner = s.substring(lt + 1, gt);
      p = gt + 1;
      if (inner.charAt(0) === "/") {
        const name = inner.substring(1).trim();
        for (let k = stack.length - 1; k > 0; k--) {
          if (stack[k].name === name) {
            stack.length = k;
            break;
          }
        }
        continue;
      }
      const selfClose = inner.charAt(inner.length - 1) === "/";
      const body = selfClose ? inner.substring(0, inner.length - 1) : inner;
      const m = /^([^\s\/>]+)/.exec(body);
      if (!m) {
        continue;
      }
      const node = new XNode(m[1]);
      const rest = body.substring(m[1].length);
      const ar = /([^\s=]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
      let a = ar.exec(rest);
      while (a !== null) {
        node.attrs.set(a[1], decodeEntities(a[2] !== undefined ? a[2] : (a[3] || "")));
        a = ar.exec(rest);
      }
      top.kids.push(node);
      if (!selfClose) {
        stack.push(node);
      }
    }
    return root;
  }

  function xKid(n: XNode | null, local: string): XNode | null {
    if (n === null) {
      return null;
    }
    for (let i = 0; i < n.kids.length; i++) {
      if (n.kids[i].local === local) {
        return n.kids[i];
      }
    }
    return null;
  }

  function xKids(n: XNode | null, local: string): XNode[] {
    return n === null ? [] : n.kids.filter((k) => k.local === local);
  }

  function xAt(n: XNode | null, path: string): XNode | null {
    let cur = n;
    const parts = path.split("/");
    for (let i = 0; i < parts.length && cur !== null; i++) {
      cur = xKid(cur, parts[i]);
    }
    return cur;
  }

  function xText(n: XNode | null, path: string): string {
    const x = path === "" ? n : xAt(n, path);
    return x === null ? "" : collapse(x.text);
  }

  function xNum(n: XNode | null, path: string): number | null {
    const t = xText(n, path);
    if (!/^-?\d+(\.\d+)?$/.test(t)) {
      return null;
    }
    return parseFloat(t);
  }

  function findDoc(n: XNode, depth: number): XNode | null {
    if (n.local === "Invoice" || n.local === "CreditNote") {
      return n;
    }
    if (depth > 6) {
      return null;
    }
    for (let i = 0; i < n.kids.length; i++) {
      const r = findDoc(n.kids[i], depth + 1);
      if (r !== null) {
        return r;
      }
    }
    return null;
  }

  // Al tekst i et element - men ikke indlejrede bilag (base64-PDF'er).
  function allText(n: XNode, out: string[]): void {
    if (n.local === "EmbeddedDocumentBinaryObject" || n.local === "Attachment") {
      return;
    }
    const t = collapse(n.text);
    if (t !== "") {
      out.push(t);
    }
    for (let i = 0; i < n.kids.length; i++) {
      allText(n.kids[i], out);
    }
  }

  // UN/ECE rec. 20 -> den enhed, folk kender.
  const UNECE: string[][] = [
    ["EA", "EA"], ["C62", "PC"], ["H87", "PC"], ["PCE", "PC"], ["NAR", "PC"], ["XPP", "PC"], ["MTR", "M"],
    ["CMT", "CM"], ["MMT", "MM"], ["KMT", "KM"], ["MTK", "M2"], ["MTQ", "M3"], ["KGM", "KG"], ["GRM", "G"],
    ["TNE", "T"], ["LTR", "L"], ["MLT", "ML"], ["PR", "PR"], ["NPR", "PR"], ["SET", "SET"], ["XST", "SET"],
    ["HUR", "H"], ["MIN", "MIN"], ["DAY", "DAY"], ["XPK", "PK"], ["PK", "PK"], ["XBX", "BOX"], ["BX", "BOX"],
    ["XRO", "ROLL"], ["RO", "ROLL"], ["XCT", "CT"], ["CT", "CT"], ["XBG", "BAG"], ["XTU", "TUBE"], ["ZZ", ""]
  ];

  function unitFromCode(code: string): string {
    const c = code.trim().toUpperCase();
    for (let i = 0; i < UNECE.length; i++) {
      if (UNECE[i][0] === c) {
        return UNECE[i][1];
      }
    }
    return c;
  }

  function readXmlInvoice(bytes: Uint8Array, res: InvoiceResult): void {
    res.source = "xml";
    let start = 0;
    if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
      start = 3;
    }
    const head = bytesToLatin1(bytes, start, Math.min(bytes.length, start + 200));
    const enc = /encoding\s*=\s*["']([^"']+)["']/i.exec(head);
    let text: string;
    if (enc && /^(iso-?8859-1|latin-?1|windows-1252|cp1252)$/i.test(enc[1])) {
      text = cp1252Decode(bytes, start);
    } else {
      const d = utf8Decode(bytes, start);
      text = d.invalid > 0 ? cp1252Decode(bytes, start) : d.text;
    }
    const doc = findDoc(parseXml(text), 0);
    if (doc === null) {
      res.error = "The XML file is not an invoice (no Invoice or CreditNote element).";
      return;
    }
    const credit = doc.local === "CreditNote";
    if (credit) {
      res.warnings.push("This is a credit note, not an invoice. Its lines are not selected.");
    }
    const cust = xText(doc, "CustomizationID").toLowerCase();
    res.format = cust.indexOf("oioubl") >= 0 ? "OIOUBL" : cust.indexOf("peppol") >= 0 ? "PEPPOL" : "UBL";
    res.invoiceNo = xText(doc, "ID");
    res.invoiceDate = parseDate(xText(doc, "IssueDate"));
    res.currency = xText(doc, "DocumentCurrencyCode").toUpperCase();
    res.orderNo = xText(doc, "OrderReference/ID");
    const party = xAt(doc, "AccountingSupplierParty/Party");
    res.supplierName = xText(party, "PartyName/Name") || xText(party, "PartyLegalEntity/RegistrationName");
    res.supplierVatNo = (xText(party, "PartyTaxScheme/CompanyID") || xText(party, "PartyLegalEntity/CompanyID")
      || xText(party, "EndpointID")).replace(/\s/g, "");
    res.netTotal = xNum(doc, "LegalMonetaryTotal/LineExtensionAmount");
    res.pages = 0;
    const textOut: string[] = [res.format + (credit ? " credit note " : " invoice ") + res.invoiceNo + " from "
      + res.supplierName + " dated " + res.invoiceDate];
    const lines = xKids(doc, credit ? "CreditNoteLine" : "InvoiceLine");
    for (let i = 0; i < lines.length; i++) {
      const ln = lines[i];
      const l = emptyLine();
      const qn = xKid(ln, credit ? "CreditedQuantity" : "InvoicedQuantity");
      const item = xKid(ln, "Item");
      const name = xText(item, "Name");
      const descs = xKids(item, "Description").map((d) => collapse(d.text)).filter((t) => t !== "");
      const notes = xKids(ln, "Note").map((d) => collapse(d.text)).filter((t) => t !== "");
      l.description = name !== "" ? name : descs.length > 0 ? descs[0] : notes.length > 0 ? notes[0] : "";
      l.extraText = descs.concat(notes).filter((t) => t !== l.description).join(" ");
      l.quantity = xNum(ln, credit ? "CreditedQuantity" : "InvoicedQuantity");
      l.unit = qn === null ? "" : unitFromCode(qn.attrs.get("unitCode") || "");
      l.amount = xNum(ln, "LineExtensionAmount");
      l.unitPrice = xNum(ln, "Price/PriceAmount");
      const base = xNum(ln, "Price/BaseQuantity");
      l.priceUnit = base !== null && base > 0 && base !== 1 ? base : null;
      l.supplierPartNo = xText(item, "SellersItemIdentification/ID");
      l.manufacturerPartNo = xText(item, "ManufacturersItemIdentification/ID");
      l.manufacturer = xText(item, "ManufacturerParty/PartyName/Name") || xText(item, "BrandName");
      l.model = xText(item, "ModelName");
      const std = xAt(item, "StandardItemIdentification/ID");
      if (std !== null && /^\d{8,14}$/.test(collapse(std.text))) {
        l.gtin = collapse(std.text);
      }
      if (credit) {
        if (l.amount !== null) {
          l.amount = -Math.abs(l.amount);
        }
      }
      const q = l.quantity;
      const p = l.unitPrice;
      if (q !== null && p !== null && l.amount !== null) {
        const exp = q * p / (l.priceUnit || 1);
        l.check = near(Math.abs(exp), Math.abs(l.amount)) || xKids(ln, "AllowanceCharge").length > 0 ? "ok" : "mismatch";
      } else {
        l.check = "incomplete";
      }
      l.isCharge = isChargeLine(l);
      res.lines.push(l);
      textOut.push([l.supplierPartNo, l.description, String(l.quantity) + " " + l.unit, String(l.unitPrice),
        String(l.amount)].join(" | "));
    }
    res.text = textOut.join("\n");
    const plain: string[] = [];
    allText(doc, plain);
    res.plantHint = plantHint(fold(plain.join(" ")));
  }

  return JSON.stringify(readInvoice(fileName, fileContent));
}

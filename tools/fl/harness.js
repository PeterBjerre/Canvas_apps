// -*- coding: utf-8 -*-
//
// FL-REGLERNE, KOERT AF DEN ORIGINALE KODE
//
//   node tools/fl/harness.js plan    skriv "Functional Location App/build/fl_rules.generated.json"
//   node tools/fl/harness.js seed    skriv sharepoint/seed/MD_FLKey.csv af html/lookups.generated.js
//   node tools/fl/harness.js test    testmatrixen (tools/fl/testmatrix.json) + differentialtest
//   node tools/fl/harness.js doc     testmatrixen som tabel i docs/31-functional-location-regler.md
//
// Hvad der koeres er de UAENDREDE filer fra html/:
//
//   text-utils.js, lookups.generated.js, fl-classification-data.js,
//   fl-spool-columns.js, fl-rule-engine.js, app-functional-location.js
//
// Controlleren (app-functional-location.js) er en IIFE uden eksport. Den
// laeses som tekst, IIFE-skallen skaeres af, og kroppen koeres i en funktion,
// der returnerer dens interne funktioner og konstanter. Intet i selve
// kroppen aendres - derfor er det HTML'ens regler, testene koerer, og ikke
// en afskrift af dem.
//
// Planen (fl_rules.generated.json) er den FLADE form af validateSpoolFields
// pr. klasse: en ordnet liste af tjek, som canvas-appens Power Fx evaluerer.
// Den er lavet ved at gaa validateSpoolFields' struktur igennem og kalde
// controllerens egne resolveDropdownOptions / resolveColumnLabel /
// resolveMaxLengthForField. At den flade form giver PRAECIS det samme som
// originalen, er ikke en paastand: "test" koerer begge over testmatrixen og
// over tusinder af genererede raekker og sammenligner beskederne ordret.
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const HTML = path.join(ROOT, "html");
const OUT_PLAN = path.join(ROOT, "Functional Location App", "build", "fl_rules.generated.json");

// ---------------------------------------------------------------------------
// Indlaes originalerne
// ---------------------------------------------------------------------------
function loadOriginals() {
  const window = {};
  const document = { addEventListener() {}, getElementById() { return null; } };
  const ctx = { window, document };
  const run = (file) => {
    const src = fs.readFileSync(path.join(HTML, file), "utf8").replace(/^﻿/, "");
    // eslint-disable-next-line no-new-func
    new Function("window", "document", src)(window, document);
  };
  run("text-utils.js");
  run("lookups.generated.js");
  run("fl-classification-data.js");
  run("fl-spool-columns.js");
  run("fl-rule-engine.js");

  let src = fs.readFileSync(path.join(HTML, "app-functional-location.js"), "utf8")
    .replace(/^﻿/, "").replace(/\r\n/g, "\n");
  const head = "(function () {\n";
  const tail = /\}\)\(\);\s*$/;
  if (!src.startsWith(head) || !tail.test(src)) {
    throw new Error("app-functional-location.js har ikke den forventede IIFE-form");
  }
  src = src.slice(head.length).replace(tail, "");
  const exported = [
    "state", "DEFAULT_SPOOL_COLUMNS", "CLASS_HELP", "READ_ONLY_SPOOL_COLUMNS",
    "DROPDOWN_TABLE_BY_FIELD", "DROPDOWN_TABLE_BY_SEARCH_KEY", "BUILTIN_ALLOWED_VALUES_BY_FIELD",
    "DATE_FIELD_SET", "CLASS_STEP_RULES", "MASTERDATA_FIELD_RULES", "STEP_FIELD_RULES",
    "CLASS_SPECIFIC_FIELD_RULES", "CLASS_TABLE_FIXED_COLUMNS", "COMPACT_COLUMN_ORDER",
    "addRow", "buildDuplicateCountMap", "applyLocalValidation", "buildSpoolRuleIndex",
    "distributeRowsIntoClasses", "getSpoolColumnValue", "resolveDropdownOptions",
    "resolveColumnLabel", "resolveMaxLengthForField", "resolveClassSteps",
    "resolveSpoolColumns", "isEditableSpoolColumn", "isValidWarrantyDate",
    "valueMatchesAllowedList", "resolveValidationIssueHelpText", "getSapStatusText",
    "isFunctionalLocationIssue", "isDescriptionIssue", "normalizeFlTyped",
    "setSpoolColumnValue", "revalidateRowsAndRender",
  ];
  // eslint-disable-next-line no-new-func
  const ctl = new Function("window", "document", "requestAnimationFrame",
    src + "\nreturn {" + exported.join(", ") + "};")(window, document, () => {});

  // init() uden DOM: det samme som init() goer, minus rendering.
  ctl.state.ruleData = window.FlRuleEngine.buildRuleData(window.FL_CLASSIFICATION_DATA, window.FL_LOOKUPS);
  ctl.buildSpoolRuleIndex();
  return { window, ctl, engine: window.FlRuleEngine, TU: window.TextUtils };
}

// ---------------------------------------------------------------------------
// Den flade plan pr. klasse
// ---------------------------------------------------------------------------
// Tjek-arterne. Samme navne staar i Power Fx'en (build/fl_validation.py).
//   MAX   vaerdi udfyldt og Len > Num                 "Max N characters."
//   DROP  vaerdi udfyldt og ikke i listen List        "Value must match dropdown options."
//   ALLOW som DROP, indbygget liste                   "Allowed values: X."
//   REQ   vaerdi tom                                  "Required field."
//   RGX   vaerdi udfyldt og ikke moenster List        "Invalid value format."
//   DATE  vaerdi udfyldt og ikke gyldig dato          "Use DD.MM.YYYY or YYYYMMDD."
//   UE    klasse MKP, key12=UE, vaerdi tom            "Required when aggregate key is UE."
//   UEFP  som UE og key17=FP                          "Required for UE/FP."
//   KKS   syntaksfejl paa FL                          KKS-motorens besked
function regexId(re) {
  const map = {
    "^[0-9.,\\-\\/+]*$": "NUMSIGN",
    "^[0-9,]*$": "NUMCOMMA",
    "^[0-9.,]*$": "NUMDOT",
  };
  const id = map[re.source];
  if (!id) throw new Error("Ukendt regex i JS-reglerne: " + re.source + " - tilfoej den i regexId og i fl_validation.py");
  return id;
}

function buildPlan(o) {
  const { ctl, TU } = o;
  const N = TU.normalizeUpper;
  const lists = new Map(); // noegle -> [vaerdier]
  const listId = (values) => {
    const key = JSON.stringify(values);
    for (const [id, v] of lists) if (JSON.stringify(v) === key) return id;
    const id = "L" + String(lists.size + 1).padStart(2, "0");
    lists.set(id, values);
    return id;
  };

  // Klasserne: alle, determineClass kan give, plus NO CLASS.
  const rd = ctl.state.ruleData;
  const classes = new Set(["NO CLASS", "KAB", "ELF"]);
  Object.values(rd.componentMap).forEach((c) => classes.add(c));
  Object.values(rd.aggregateMap).forEach((c) => classes.add(c));
  const classList = [...classes].sort();

  const plan = [];
  for (const C of classList) {
    let ord = 0;
    const seenItem = new Set();
    let rule = "";   // regel-id i docs/31 for de tjek, der tilfoejes nu
    // Et tjek, der staar ordret en gang til, kan aldrig give en NY besked -
    // beskederne dedupliceres, og den foerste vinder. Det springes derfor
    // over her; testen efterproever, at resultatet er det samme.
    const add = (field, chk, num, list, msg) => {
      const sig = [field, chk, num, list, msg].join("|");
      if (seenItem.has(sig)) return;
      seenItem.add(sig);
      ord += 1;
      plan.push({ Cls: C, Ord: ord, Rule: rule, Field: field, Label: ctl.resolveColumnLabel(C, field),
                  Chk: chk, Num: num || 0, List: list || "", Msg: msg });
    };
    const addDrop = (field) => {
      const opts = ctl.resolveDropdownOptions(C, N(field));
      if (opts.length) add(N(field), "DROP", 0, listId(opts), "Value must match dropdown options.");
    };
    const addRule = (field, rule) => {
      if (rule.required) add(field, "REQ", 0, "", "Required field.");
      if (rule.maxLength > 0) add(field, "MAX", rule.maxLength, "", `Max ${rule.maxLength} characters.`);
      if (rule.regex instanceof RegExp) add(field, "RGX", 0, regexId(rule.regex), "Invalid value format.");
    };
    const classRules = ctl.state.spoolRules.charByClass[C] || {};

    // A. Klassens Char-regler (validateSpoolFields:1183-1198)
    Object.keys(classRules).forEach((f) => {
      const r = classRules[f];
      rule = "FL30";
      if (r.maxLength > 0) add(f, "MAX", r.maxLength, "", `Max ${r.maxLength} characters.`);
      rule = "FL31";
      if (r.dropdown) addDrop(f);
    });
    // B. Stamdata (runMasterDataValidation:1231-1258)
    Object.keys(ctl.MASTERDATA_FIELD_RULES).forEach((f) => {
      const r = ctl.MASTERDATA_FIELD_RULES[f];
      rule = "FL32";
      if (r.required) add(f, "REQ", 0, "", "Required field.");
      rule = "FL33";
      if (r.maxLength > 0) add(f, "MAX", r.maxLength, "", `Max ${r.maxLength} characters.`);
      rule = "FL34";
      if (ctl.DATE_FIELD_SET.has(f)) add(f, "DATE", 0, "", "Use DD.MM.YYYY or YYYYMMDD.");
    });
    Object.keys(ctl.BUILTIN_ALLOWED_VALUES_BY_FIELD).forEach((f) => {
      const allowed = ctl.BUILTIN_ALLOWED_VALUES_BY_FIELD[f];
      rule = "FL35";
      add(f, "ALLOW", 0, listId(allowed), `Allowed values: ${allowed.join(", ")}.`);
    });
    // C. Trinene (validateSpoolFields:1202-1213)
    const stepFields = (step, id) => {
      rule = id;
      const rules = ctl.STEP_FIELD_RULES[step] || {};
      Object.keys(rules).forEach((f) => addRule(f, rules[f]));
      Object.keys(classRules).forEach((f) => {
        const r = classRules[f];
        if (!r || !r.dropdown) return;
        if (!ctl.DROPDOWN_TABLE_BY_SEARCH_KEY[N(r.searchKey)]) return;
        rule = "FL42";
        addDrop(f);
      });
      rule = id;
    };
    let hasTrm = false;
    for (const step of ctl.resolveClassSteps(C)) {
      if (step === "Design_pressure_") { stepFields(step, "FL37"); addDrop("DESIGN PRESSURE UOM"); }
      if (step === "Operating_pressure_") { stepFields(step, "FL38"); addDrop("OPERATING PRESSURE UOM"); }
      if (step === "Design_temperature_") { stepFields(step, "FL39"); addDrop("DESIGN TEMPERATURE UOM"); }
      if (step === "Operating_temperature_") { stepFields(step, "FL40"); addDrop("OPERATING TEMPERATURE UOM"); }
      if (step === "Design_flow_") { stepFields(step, "FL41"); addDrop("DESIGN FLOW UOM"); }
      if (step === "Typekreds") { rule = "FL43"; addDrop("TYPEKREDSE"); }
      if (step === "TestMethod") { rule = "FL44"; addDrop("TEST METHOD"); addDrop("TEST METHOD 2"); }
      if (step === "TRMNEW") {
        hasTrm = true;
        stepFields("TRMNEW", "FL45");
        rule = "FL46";
        addDrop("SAFETY CRITICAL EQUIPMENT");
        rule = "FL47";
        if (C === "MKP" || C === "NO CLASS") { addDrop("FIRE CLASSIFICATION"); addDrop("FIRE SEALING TYPE"); }
        if (C === "MKP") {
          rule = "FL50";
          add("FIRE CLASSIFICATION", "UE", 0, "", "Required when aggregate key is UE.");
          rule = "FL51";
          add("FIRE SEALING TYPE", "UEFP", 0, "", "Required for UE/FP.");
          add("FIRE SEALING PRODUCT", "UEFP", 0, "", "Required for UE/FP.");
        }
      }
      if (ctl.CLASS_SPECIFIC_FIELD_RULES[step]) {
        const rules = ctl.CLASS_SPECIFIC_FIELD_RULES[step];
        rule = "FL52";
        Object.keys(rules).forEach((f) => addRule(f, rules[f]));
      }
      if (step === "KKS_Syntax") { rule = "FL53"; } if (step === "KKS_Syntax") add("FUNCTIONAL LOCATION", "KKS", 0, "", "");
    }
    plan.push({ Cls: C, Ord: 0, Rule: hasTrm ? "FL48" : "", Field: "", Label: "", Chk: hasTrm ? "TRMSET" : "NOTRM",
                Num: 0, List: "", Msg: "" });
  }

  // Kolonnerne i klassetabellen og detaljeruden (resolveSpoolColumns) med
  // hver kolonnes editor (renderSpoolEditor).
  const columns = [];
  for (const C of classList) {
    ctl.resolveSpoolColumns(C).forEach((col, i) => {
      const f = N(col);
      const opts = ctl.resolveDropdownOptions(C, f);
      columns.push({ Cls: C, Ord: i + 1, Column: col, Field: f,
                     Editable: ctl.isEditableSpoolColumn(f),
                     List: opts.length ? listId(opts) : "",
                     MaxLen: ctl.resolveMaxLengthForField(C, f) });
    });
  }

  const listRows = [];
  for (const [id, values] of lists) values.forEach((v, i) => listRows.push({ List: id, Ord: i + 1, Value: v }));

  const L = o.window.FL_LOOKUPS;
  return {
    _kilde: "GENERERET af tools/fl/harness.js af html/*.js - ret ikke i haanden",
    classes: classList,
    plan,
    columns,
    lists: listRows,
    aggregate: Object.entries(rd.aggregateMap).map(([k, v]) => ({ Key: k, Cls: v })),
    component: Object.entries(rd.componentMap).map(([k, v]) => ({ Key: k, Cls: v })),
    br18: Object.entries(rd.br18ByAggregate).flatMap(([k12, set]) =>
      Object.entries(set).map(([k17, d]) => ({ Key12: k12, Key17: k17, Description: d }))),
    plants: [...rd.allowedPlantSet],
    functionKeyCount: rd.functionKeySet.size,
    classHelp: ctl.CLASS_HELP,
    compactColumns: ctl.COMPACT_COLUMN_ORDER,
    lookupsHeaders: Object.fromEntries(Object.entries(L).map(([k, v]) => [k, v.headers])),
  };
}

// ---------------------------------------------------------------------------
// Den flade evaluator - PRAECIS det, Power Fx'en goer
// ---------------------------------------------------------------------------
function flatValidate(rowsIn, P, o) {
  const { engine, TU } = o;
  const N = TU.normalizeUpper;
  const lists = {};
  P.lists.forEach((r) => { (lists[r.List] = lists[r.List] || []).push(r.Value); });
  const inList = (v, id) => {
    const allowed = new Set((lists[id] || []).map(N).filter(Boolean));
    if (!allowed.size) return true;
    const toks = TU.toText(v).split("|").map(TU.toText).filter(Boolean);
    return toks.every((t) => allowed.has(N(t)));
  };
  const rgx = { NUMSIGN: /^[0-9.,\-/+]*$/, NUMCOMMA: /^[0-9,]*$/, NUMDOT: /^[0-9.,]*$/ };
  const agg = Object.fromEntries(P.aggregate.map((r) => [r.Key, r.Cls]));
  const comp = Object.fromEntries(P.component.map((r) => [r.Key, r.Cls]));
  const br18 = {};
  P.br18.forEach((r) => { (br18[r.Key12] = br18[r.Key12] || {})[r.Key17] = r.Description; });
  const plants = new Set(P.plants);
  const fkeys = o.ctl.state.ruleData.functionKeySet; // i appen: MD_FLKey i SharePoint

  // Power Fx-udgaven af datotjekket - ren aritmetik, se fl_validation.py.
  const dateOk = (v) => {
    let y, m, d;
    if (/^\d{8}$/.test(v)) { y = +v.slice(0, 4); m = +v.slice(4, 6); d = +v.slice(6, 8); }
    else if (/^\d{2}\.\d{2}\.\d{4}$/.test(v)) { d = +v.slice(0, 2); m = +v.slice(3, 5); y = +v.slice(6, 10); }
    else return false;
    const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
    const dim = m === 2 ? (leap ? 29 : 28) : [4, 6, 9, 11].includes(m) ? 30 : 31;
    return y >= 100 && m >= 1 && m <= 12 && d >= 1 && d <= dim;
  };

  // Vaerdierne som appen gemmer dem: trimmet, tomme fjernet.
  const rows = rowsIn.map((r) => ({ ...r, vals: Object.fromEntries(Object.entries(r.vals || {})
    .map(([k, v]) => [N(k), TU.toText(v)]).filter(([, v]) => v)) }));
  const dup = {};
  rows.forEach((r) => { r.fl = engine.normalizeFunctionalLocation(r.fl); r.desc = TU.toText(r.desc);
                        if (r.fl) dup[r.fl] = (dup[r.fl] || 0) + 1; });
  return rows.map((r) => {
    const fl = r.fl; const desc = r.desc;
    if (!fl && !desc) return { status: "draft", blocking: [], warnings: [], cls: "", kks: "", vals: r.vals };
    const B = []; const W = [];
    if (!fl) B.push("FL required.");
    if (fl && dup[fl] > 1) B.push("Duplicate FL.");
    if (!desc) B.push("Description required before Ready for SAP.");
    if (desc.length > 40) B.push("Description > 40.");
    // KKS-syntaks
    let kks = ""; let syn = ""; let synIssue = "";
    if (fl) {
      const idx = PATTERNS.findIndex((p) => p.test(fl));
      if (idx < 0) {
        if (LEGACY.test(fl)) { kks = "KKS"; W.push("Legacy format."); }
        else { synIssue = "KKS invalid."; B.push(synIssue); }
      } else if (idx === 10 || idx === 11) { kks = "KKSKV"; syn = "KAB"; }
      else if (idx === 9) { kks = "KKSKA"; syn = "KAB"; }
      else kks = "KKS";
    }
    // Klassebestemmelse
    let cls = "";
    if (fl) {
      const k0 = fl.slice(0, 3), k7 = fl.slice(6, 9), k12 = fl.slice(11, 13), k17 = fl.slice(16, 18), k18 = fl.slice(17, 19);
      if (!plants.has(k0)) B.push("Plant key invalid.");
      if (fkeys.size && !fkeys.has(k7)) B.push("Function key invalid.");
      if (k12 === "UE" || k12 === "UF") {
        if (!k7 || k7[0] !== "U") B.push("UF/UE requires U function key.");
        if (!br18[k12]) B.push(`BR18 rules missing for ${k12}.`);
        else if (!br18[k12][k17]) B.push(`BR18 key17 invalid for ${k12}.`);
      }
      if (syn === "KAB") cls = "KAB";
      else if (k18.length === 2) {
        if (comp[k18] && agg[k12]) cls = comp[k18];
        else { if (!comp[k18]) B.push("Component key invalid."); if (!agg[k12]) B.push("Equipment key invalid."); }
      } else if (agg[k12]) cls = agg[k12];
      else if (MKPF.test(fl) || FPF.test(fl)) B.push("Equipment key invalid.");
      else if (SHORT.some((p) => p.test(fl))) cls = "NO CLASS";
      else if (ELF.test(fl)) cls = "ELF";
      else B.push("Class not determined.");
    }
    if (!cls && !B.length) cls = "NO CLASS";
    // Spool-planen
    const C = cls || "NO CLASS";
    const val = (f) => {
      if (f === "STRINDICATOR" || f === "STR. INDICATOR") return kks;
      if (f === "FUNCTIONAL LOCATION") return fl;
      if (f === "DESCRIPTION") return desc;
      if (f === "LONG TEXT") return r.vals[f] || desc;
      return TU.toText(r.vals[f] || "");
    };
    const k12 = fl.slice(11, 13), k17 = fl.slice(16, 18);
    const seen = new Set();
    let trm = "NOTRM";
    P.plan.filter((p) => p.Cls === C).sort((a, b) => a.Ord - b.Ord).forEach((p) => {
      if (p.Ord === 0) { trm = p.Chk; return; }
      const v = TU.toText(val(p.Field));
      let bad = false; let msg = p.Msg;
      switch (p.Chk) {
        case "MAX": bad = !!v && v.length > p.Num; break;
        case "DROP": case "ALLOW": bad = !!v && !inList(v, p.List); break;
        case "REQ": bad = !v; break;
        case "RGX": bad = !!v && !rgx[p.List].test(v); break;
        case "DATE": bad = !!v && !dateOk(v); break;
        case "UE": bad = k12 === "UE" && !v; break;
        case "UEFP": bad = k12 === "UE" && k17 === "FP" && !v; break;
        case "KKS": bad = !!fl && !!synIssue; msg = synIssue; break;
        default: throw new Error(p.Chk);
      }
      if (bad) { const m = `${p.Label}: ${msg}`; if (!seen.has(m)) { seen.add(m); B.push(m); } }
    });
    // TRM-automatikken (runTrmValidation:1304-1321) - EFTER tjekkene.
    const vals = { ...r.vals };
    if (trm === "TRMSET") {
      const any = ["EX-MARKING", "SAFETY CRITICAL EQUIPMENT", "FIRE CLASSIFICATION", "FIRE SEALING TYPE",
                   "FIRE SEALING PRODUCT"].some((f) => TU.toText(vals[f]));
      if (any) { vals["TRM ASSIGNMENT"] = "X"; vals["ABC INDIC."] = "A"; } else delete vals["TRM ASSIGNMENT"];
      if (C === "MKP" && k12 === "UE") vals["TRM ASSIGNMENT"] = "X";
    }
    const blocking = [...new Set(B)];
    const warnings = [...new Set(W)];
    return { status: blocking.length ? "invalid" : warnings.length ? "warning" : "valid",
             blocking, warnings, cls, kks, vals };
  });
}

// Moenstrene, som Power Fx'en bruger dem - fra motoren, ikke afskrevet:
// motoren eksporterer dem ikke, saa de laeses ud af kildeteksten.
function enginePatterns() {
  const src = fs.readFileSync(path.join(HTML, "fl-rule-engine.js"), "utf8");
  const grab = (name) => {
    const m = src.match(new RegExp("const " + name + " = \\[([\\s\\S]*?)\\];"));
    return [...m[1].matchAll(/\/(\^[^\n]*?\$)\//g)].map((x) => x[1]);
  };
  const one = (name) => src.match(new RegExp("const " + name + " = \\/(\\^[^\\n]*?\\$)\\/;"))[1];
  return {
    kks: grab("KKS_PATTERNS"), legacy: one("LEGACY_PATTERN"), short: grab("SHORT_PATTERN_SET"),
    elf: one("ELF_FALLBACK_PATTERN"), mkp: one("MKP_ERROR_PATTERN"), fp: one("FP_ERROR_PATTERN"),
  };
}
const PAT = enginePatterns();
const PATTERNS = PAT.kks.map((s) => new RegExp(s));
const LEGACY = new RegExp(PAT.legacy);
const SHORT = PAT.short.map((s) => new RegExp(s));
const ELF = new RegExp(PAT.elf);
const MKPF = new RegExp(PAT.mkp);
const FPF = new RegExp(PAT.fp);

// ---------------------------------------------------------------------------
// Originalen paa en liste raekker
// ---------------------------------------------------------------------------
function originalValidate(o, rowsIn) {
  const { ctl } = o;
  ctl.state.rows = rowsIn.map((r, i) => ({
    id: i + 1, functionalLocation: ctl.normalizeFlTyped(r.fl), description: r.desc || "",
    spoolValues: {},
    spoolFieldIssues: {}, kksType: "", assignedClass: "", candidateClasses: [], sapDescription: "",
    status: "draft", blockingIssues: [], warnings: [], notes: [],
  }));
  // Vaerdierne gaar ind ad samme vej som i siden: setSpoolColumnValue
  // (trimmer, og en tom vaerdi fjerner feltet).
  ctl.state.rows.forEach((row, i) => Object.entries(rowsIn[i].vals || {}).forEach(([f, v]) =>
    ctl.setSpoolColumnValue(row, o.TU.normalizeUpper(f), v)));
  const dupMap = ctl.buildDuplicateCountMap(ctl.state.rows);
  ctl.state.rows.forEach((row) => ctl.applyLocalValidation(row, dupMap));
  return ctl.state.rows.map((r) => ({ status: r.status, blocking: r.blockingIssues, warnings: r.warnings,
                                       cls: r.assignedClass, kks: r.kksType, vals: r.spoolValues }));
}

// ---------------------------------------------------------------------------
// Kommandoer
// ---------------------------------------------------------------------------
function cmdPlan() {
  const o = loadOriginals();
  const P = buildPlan(o);
  P.patterns = PAT;
  fs.writeFileSync(OUT_PLAN, JSON.stringify(P, null, 1) + "\n", "utf8");
  console.log(`Skrev ${path.relative(ROOT, OUT_PLAN)}: ${P.classes.length} klasser, ${P.plan.length} tjek, ` +
              `${P.columns.length} kolonner, ${new Set(P.lists.map((l) => l.List)).size} lister.`);
}

function csvCell(v) { return '"' + String(v).replace(/"/g, '""') + '"'; }
function cmdSeed() {
  const o = loadOriginals();
  const L = o.window.FL_LOOKUPS;
  const N = o.TU.normalizeUpper;
  const rows = [["KeyType", "KeyValue", "Value", "Description"]];
  const seen = new Set();
  const push = (t, k, v, d) => { const key = t + "|" + k + "|" + (t === "BR18" ? v : ""); if (seen.has(key)) return;
                                 seen.add(key); rows.push([t, k, v, d]); };
  L.BR18_Keys.rows.forEach((r) => push("BR18", N(r[0]), N(r[1]), o.TU.toText(r[2])));
  L.ClassDeterminationAggregateKey.rows.forEach((r) => push("Aggregate", N(r[0]), N(r[1]), o.TU.toText(r[2])));
  L.ClassDeterminationComponentKey.rows.forEach((r) => push("Component", N(r[0]), N(r[1]), o.TU.toText(r[2])));
  L.FunctionKeyDict.rows.forEach((r) => { const k = N(r[0]); if (k) push("Function", k, "", ""); });
  const out = path.join(ROOT, "sharepoint", "seed", "MD_FLKey.csv");
  fs.writeFileSync(out, "﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\n") + "\n", "utf8");
  console.log(`Skrev ${path.relative(ROOT, out)}: ${rows.length - 1} noegler.`);
}

function same(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

function cmdTest() {
  const o = loadOriginals();
  const P = JSON.parse(fs.readFileSync(OUT_PLAN, "utf8"));
  const fresh = buildPlan(o);
  if (!same(fresh.plan, P.plan) || !same(fresh.columns, P.columns) || !same(fresh.lists, P.lists)) {
    console.log("FEJL: fl_rules.generated.json er ikke i trit med html/*.js. Koer: node tools/fl/harness.js plan");
    process.exit(1);
  }
  let fail = 0;

  // 1. Testmatrixen: hver sag koeres ALENE, medmindre den har "group".
  const M = JSON.parse(fs.readFileSync(path.join(__dirname, "testmatrix.json"), "utf8"));
  const groups = {};
  M.cases.forEach((c) => { const g = c.group || c.id; (groups[g] = groups[g] || []).push(c); });
  let n = 0;
  const rd = o.ctl.state.ruleData;
  const saved = { br18: rd.br18ByAggregate, fk: rd.functionKeySet };
  for (const g of Object.keys(groups)) {
    const cases = groups[g];
    const rows = cases.map((c) => ({ fl: c.fl, desc: c.desc === undefined ? "Pumpe" : c.desc, vals: c.vals || {} }));
    // env: sager, der kraever andre opslagsdata end de nuvaerende.
    const env = cases[0].env || "";
    let PP = P;
    if (env === "noBr18UF") {
      rd.br18ByAggregate = { ...saved.br18 }; delete rd.br18ByAggregate.UF;
      PP = { ...P, br18: P.br18.filter((r) => r.Key12 !== "UF") };
    }
    if (env === "noFunctionKeys") rd.functionKeySet = new Set();
    const orig = originalValidate(o, rows);
    const flat = flatValidate(rows, PP, o);
    rd.br18ByAggregate = saved.br18; rd.functionKeySet = saved.fk;
    cases.forEach((c, i) => {
      n += 1;
      const got = orig[i];
      const probs = [];
      if (c.expect.status && got.status !== c.expect.status) probs.push(`status ${got.status} != ${c.expect.status}`);
      if (c.expect.cls !== undefined && got.cls !== c.expect.cls) probs.push(`klasse ${got.cls} != ${c.expect.cls}`);
      if (c.expect.kks !== undefined && got.kks !== c.expect.kks) probs.push(`kks ${got.kks} != ${c.expect.kks}`);
      if (c.expect.exact && !same(got.blocking, c.expect.exact)) probs.push(`blokerende ${JSON.stringify(got.blocking)} != ${JSON.stringify(c.expect.exact)}`);
      (c.expect.has || []).forEach((m) => { if (!got.blocking.includes(m) && !got.warnings.includes(m)) probs.push(`mangler "${m}"`); });
      (c.expect.hasNot || []).forEach((m) => { if (got.blocking.includes(m) || got.warnings.includes(m)) probs.push(`har "${m}"`); });
      if (c.expect.vals) Object.entries(c.expect.vals).forEach(([k, v]) => {
        if ((got.vals[k] || "") !== v) probs.push(`${k}=${got.vals[k] || ""} != ${v}`); });
      const f = flat[i];
      if (!same([f.status, f.blocking, f.warnings, f.cls, f.kks], [got.status, got.blocking, got.warnings, got.cls, got.kks])
          || !same(sortObj(f.vals), sortObj(got.vals)))
        probs.push("flad plan != original: " + JSON.stringify({ flat: f, orig: got }));
      if (probs.length) { fail += 1; console.log(`  ${c.id} ${c.rule}: ${probs.join("; ")}`); }
    });
  }
  console.log(`Testmatrix: ${n} sager, ${n - fail} groenne.`);

  // 2. Differentialtest: tilfaeldige raekker, original mod flad plan.
  const rnd = mulberry32(20260924);
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const flSeeds = M.fuzzFl;
  const valPool = ["", "", "", "X", "x", "A", "Y", "123", "12,5", "1.5", "-3/4+", "abc", "Bar", "bar|psi", "Bar|foo",
                   "°C", "20240229", "20230229", "31.12.2024", "32.01.2024", "0000", "Nr1: End to end test",
                   "1.1 Energi-/flowmåler", "BK EI 60 (60 min)", "Brandplade", "2.2 Trykbeholdere", " X ",
                   "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJ", "KKS", "AKS", "0001", "01.01.0099"];
  const fields = [...new Set(P.columns.map((c) => c.Field))].filter((f) => !["INFO", "SAP STATUS", "CLASS",
    "FUNCTIONAL LOCATION", "DESCRIPTION", "STRINDICATOR", "USER STATUS", "SYSTEM STATUS"].includes(f));
  let diffs = 0; const N = 4000;
  for (let i = 0; i < N; i += 1) {
    const rows = [];
    const k = 1 + Math.floor(rnd() * 4);
    for (let j = 0; j < k; j += 1) {
      const vals = {};
      const m = Math.floor(rnd() * 6);
      for (let q = 0; q < m; q += 1) vals[pick(fields)] = pick(valPool);
      let fl = pick(flSeeds);
      if (rnd() < 0.2) fl = mutate(fl, rnd);
      rows.push({ fl, desc: pick(["", "Pumpe", "x".repeat(41), "Beskrivelse"]), vals });
    }
    const a = originalValidate(o, rows);
    const b = flatValidate(rows, P, o);
    for (let j = 0; j < rows.length; j += 1) {
      const x = a[j], y = b[j];
      if (!same([x.status, x.blocking, x.warnings, x.cls, x.kks], [y.status, y.blocking, y.warnings, y.cls, y.kks])
          || !same(sortObj(x.vals), sortObj(y.vals))) {
        diffs += 1;
        if (diffs <= 5) console.log("  AFVIGELSE", JSON.stringify(rows[j]), "\n   original:", JSON.stringify(x), "\n   flad:    ", JSON.stringify(y));
      }
    }
  }
  console.log(`Differentialtest: ${N} saet, ${diffs} afvigelser mellem original og flad plan.`);
  if (fail || diffs) process.exit(1);
}

function sortObj(o) { return Object.fromEntries(Object.entries(o || {}).filter(([, v]) => v).sort()); }
function mulberry32(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function mutate(s, rnd) {
  const chars = "ABCUEFPDGHKX0123456789 -";
  const i = Math.floor(rnd() * (s.length + 1));
  const op = rnd();
  if (op < 0.4) return s.slice(0, i) + chars[Math.floor(rnd() * chars.length)] + s.slice(i + 1);
  if (op < 0.7) return s.slice(0, i) + s.slice(i + 1);
  return s.slice(0, i) + chars[Math.floor(rnd() * chars.length)] + s.slice(i);
}

// Testmatrixen som tabel i docs/31, mellem markoererne. Resultatet er det,
// ORIGINALEN giver - dokumentet kan derfor ikke paastaa noget, koden ikke goer.
function cmdDoc() {
  const o = loadOriginals();
  const M = JSON.parse(fs.readFileSync(path.join(__dirname, "testmatrix.json"), "utf8"));
  const groups = {};
  M.cases.forEach((c) => { const g = c.group || c.id; (groups[g] = groups[g] || []).push(c); });
  const res = {};
  const rd = o.ctl.state.ruleData;
  const saved = { br18: rd.br18ByAggregate, fk: rd.functionKeySet };
  for (const g of Object.keys(groups)) {
    const cases = groups[g];
    const env = cases[0].env || "";
    if (env === "noBr18UF") { rd.br18ByAggregate = { ...saved.br18 }; delete rd.br18ByAggregate.UF; }
    if (env === "noFunctionKeys") rd.functionKeySet = new Set();
    const out = originalValidate(o, cases.map((c) => ({ fl: c.fl, desc: c.desc === undefined ? "Pumpe" : c.desc, vals: c.vals || {} })));
    rd.br18ByAggregate = saved.br18; rd.functionKeySet = saved.fk;
    cases.forEach((c, i) => { res[c.id] = out[i]; });
  }
  const esc = (t) => String(t).replace(/\|/g, "\\|").replace(/\u00a0/g, "⍽");
  const lines = ["| Test | Regel | Gyldig/ugyldig | FL | Description | Felter | Forventet status | Klasse | Beskeder (ordret, i raekkefoelge) |",
                 "|---|---|---|---|---|---|---|---|---|"];
  M.cases.forEach((c) => {
    const r = res[c.id];
    const desc = c.desc === undefined ? "Pumpe" : c.desc;
    const vals = Object.entries(c.vals || {}).map(([k, v]) => `${k}=\`${v}\``).join("; ");
    const kind = r.status === "invalid" || r.status === "warning" ? "ugyldig" : "gyldig";
    const msgs = [...r.blocking, ...r.warnings].join(" · ");
    lines.push(`| ${c.id} | ${c.rule} | ${kind}${c.env ? " (" + c.env + ")" : ""}${c.group ? " (gruppe " + c.group + ")" : ""} | \`${esc(c.fl)}\` | ${desc.length > 20 ? desc.length + " tegn" : esc(desc) || "(tom)"} | ${esc(vals)} | ${r.status} | ${r.cls || "-"} | ${esc(msgs) || "-"} |`);
  });
  const docPath = path.join(ROOT, "docs", "31-functional-location-regler.md");
  const doc = fs.readFileSync(docPath, "utf8");
  const a = "<!-- TESTMATRIX:START -->", b = "<!-- TESTMATRIX:END -->";
  const next = doc.slice(0, doc.indexOf(a) + a.length) + "\n" + lines.join("\n") + "\n" + doc.slice(doc.indexOf(b));
  fs.writeFileSync(docPath, next, "utf8");
  console.log(`docs/31: testmatrix med ${M.cases.length} sager skrevet.`);
}

module.exports = { loadOriginals, buildPlan, flatValidate, originalValidate };

if (require.main === module) {
  const cmd = process.argv[2];
  if (cmd === "plan") cmdPlan();
  else if (cmd === "seed") cmdSeed();
  else if (cmd === "test") cmdTest();
  else if (cmd === "doc") cmdDoc();
  else { console.log("brug: node tools/fl/harness.js plan|seed|test|doc"); process.exit(2); }
}

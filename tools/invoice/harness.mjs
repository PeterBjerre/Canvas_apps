// -*- coding: utf-8 -*-
//
// FAKTURALAESEREN, KOERT PAA TESTFAKTURAERNE
//
//   node tools/invoice/harness.mjs test            kontrakten + fixtures mod expected.json
//   node tools/invoice/harness.mjs contract        kun kontrakten (kraever ingen TypeScript-stoette)
//   node tools/invoice/harness.mjs dump [fil ...]  vis, hvad laeseren faar ud af filerne
//
// INVOICE_PARTS / INVOICE_EXPECTED peger paa en anden fil end repoets -
// tests/test_checks.py planter fejl i en kopi og kraever, at de meldes.
//
// Det, der koeres, er DEN UAENDREDE fil flow/invoice-import/ReadInvoice.ts -
// den samme tekst, der kopieres ind i Excel som Office Script. Node fjerner
// typerne (module.stripTypeScriptTypes, Node 22.13+), og koden koeres i en
// funktion, der returnerer main - som Excel kalder den. Intet i scriptet
// aendres.
//
// KONTRAKTEN: feltnavnene i InvoiceLine og InvoiceResult skal staa ordret i
// "Material App/build/invoice_parts.py" (CONTRACT_LINE / CONTRACT_RESULT).
// Appen ParseJSON'er svaret paa navn - et omdoebt felt ville give tomme
// felter i appen uden en eneste fejl.
"use strict";

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as nodeModule from "node:module";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const SCRIPT = path.join(ROOT, "flow", "invoice-import", "ReadInvoice.ts");
const FIXTURES = path.join(HERE, "fixtures");
const EXPECTED = process.env.INVOICE_EXPECTED || path.join(HERE, "expected.json");
const PARTS = process.env.INVOICE_PARTS || path.join(ROOT, "Material App", "build", "invoice_parts.py");

function loadReader() {
  if (typeof nodeModule.stripTypeScriptTypes !== "function") {
    console.log("NB: Node " + process.version + " kan ikke fjerne TypeScript-typer "
      + "(kraever 22.13+) - fakturalaeseren er IKKE efterproevet.");
    return null;
  }
  const src = fs.readFileSync(SCRIPT, "utf8");
  if (/[^\x00-\x7f]/.test(src)) {
    throw new Error("ReadInvoice.ts skal vaere ren ASCII (brug \\u-koder) - den kopieres ind i Excel.");
  }
  const emit = process.emitWarning;
  process.emitWarning = () => {};
  let js;
  try {
    js = nodeModule.stripTypeScriptTypes(src);
  } finally {
    process.emitWarning = emit;
  }
  // eslint-disable-next-line no-new-func
  return new Function(js + "\nreturn { main: main };")();
}

function run(reader, file) {
  const b64 = fs.readFileSync(path.join(FIXTURES, file)).toString("base64");
  // Som flowet kalder det: main(workbook, fileName, fileContent) -> JSON-streng.
  const t0 = Date.now();
  const out = JSON.parse(reader.main(null, file, b64));
  out.__ms = Date.now() - t0;
  return out;
}

function same(want, got) {
  if (typeof want === "number" && typeof got === "number") {
    return Math.abs(want - got) < 0.0051;
  }
  return JSON.stringify(want) === JSON.stringify(got);
}

function compare(file, want, got, problems) {
  for (const [k, v] of Object.entries(want)) {
    if (k === "lines") {
      if (got.lines.length !== v.length) {
        problems.push(`${file}: ${got.lines.length} linjer, forventet ${v.length}`);
      }
      v.forEach((wl, i) => {
        const gl = got.lines[i] || {};
        for (const [lk, lv] of Object.entries(wl)) {
          if (!same(lv, gl[lk])) {
            problems.push(`${file}: linje ${i + 1}.${lk} = ${JSON.stringify(gl[lk])}, forventet ${JSON.stringify(lv)}`);
          }
        }
      });
    } else if (k === "warningsInclude") {
      for (const w of v) {
        if (!got.warnings.some((g) => g.includes(w))) {
          problems.push(`${file}: ingen advarsel med "${w}" (fik ${JSON.stringify(got.warnings)})`);
        }
      }
    } else if (!same(v, got[k])) {
      problems.push(`${file}: ${k} = ${JSON.stringify(got[k])}, forventet ${JSON.stringify(v)}`);
    }
  }
}

// Feltnavnene i TypeScript-interfacet.
function tsFields(src, name) {
  const m = new RegExp("interface " + name + " \\{([\\s\\S]*?)\\n\\s*\\}").exec(src);
  if (!m) {
    throw new Error("ReadInvoice.ts har ingen interface " + name);
  }
  return [...m[1].matchAll(/^\s*(\w+)\??:/gm)].map((x) => x[1]);
}

// Feltnavnene i Python-kontrakten: CONTRACT_X = ( "a", "b", ... )
function pyFields(src, name) {
  const m = new RegExp(name + "\\s*=\\s*\\(([\\s\\S]*?)\\)").exec(src);
  if (!m) {
    return null;
  }
  return [...m[1].matchAll(/"(\w+)"/g)].map((x) => x[1]);
}

function checkContract(problems) {
  const src = fs.readFileSync(SCRIPT, "utf8");
  if (!fs.existsSync(PARTS)) {
    problems.push("kontrakt: " + path.relative(ROOT, PARTS) + " findes ikke");
    return;
  }
  const py = fs.readFileSync(PARTS, "utf8");
  for (const [iface, const_] of [["InvoiceLine", "CONTRACT_LINE"], ["InvoiceResult", "CONTRACT_RESULT"]]) {
    const ts = tsFields(src, iface);
    const p = pyFields(py, const_);
    if (p === null) {
      problems.push(`kontrakt: ${const_} mangler i invoice_parts.py`);
      continue;
    }
    const missing = ts.filter((f) => !p.includes(f));
    const extra = p.filter((f) => !ts.includes(f));
    if (missing.length || extra.length) {
      problems.push(`kontrakt ${iface}: mangler i Python ${JSON.stringify(missing)}, `
        + `ukendt i TypeScript ${JSON.stringify(extra)}`);
    }
  }
}

function report(problems, ok) {
  if (problems.length) {
    console.log(`\n${problems.length} problem(er) i fakturalaeseren:\n`);
    for (const p of problems) {
      console.log("  " + p);
    }
    return 1;
  }
  console.log(ok);
  return 0;
}

function main() {
  const cmd = process.argv[2] || "test";
  // Kontrakten foerst: den kraever ingen TypeScript-stoette i Node.
  const problems = [];
  checkContract(problems);
  if (cmd === "contract") {
    return report(problems, "Fakturalaeserens kontrakt passer til invoice_parts.py.");
  }
  const reader = loadReader();
  if (reader === null) {
    return report(problems, "Kontrakten passer; selve laeseren er ikke koert (Node er for gammel).");
  }
  if (cmd === "dump") {
    const files = process.argv.slice(3).length ? process.argv.slice(3)
      : fs.readdirSync(FIXTURES).filter((f) => /\.(pdf|xml)$/i.test(f)).sort();
    for (const f of files) {
      const r = run(reader, path.basename(f));
      const { text, lines, ...head } = r;
      console.log("=".repeat(78) + "\n" + f);
      console.log(JSON.stringify(head, null, 1));
      for (const l of lines) {
        console.log("  " + JSON.stringify(l));
      }
      if (process.env.TEXT) {
        console.log(text);
      }
    }
    return 0;
  }
  const expected = JSON.parse(fs.readFileSync(EXPECTED, "utf8"));
  let n = 0;
  for (const [file, want] of Object.entries(expected)) {
    if (file.startsWith("_")) {
      continue;
    }
    n++;
    let got;
    try {
      got = run(reader, file);
    } catch (e) {
      problems.push(`${file}: laeseren kastede ${e && e.stack ? e.stack : e}`);
      continue;
    }
    compare(file, want, got, problems);
    console.log(`  ${file.padEnd(28)} ${String(got.lines.length).padStart(3)} linjer  ${got.__ms} ms`);
  }
  const untested = fs.readdirSync(FIXTURES).filter((f) => !(f in expected));
  for (const f of untested) {
    problems.push(`${f}: ligger i fixtures/, men har ingen forventning i expected.json`);
  }
  return report(problems, `Fakturalaeseren OK: ${n} fakturaer laest som forventet, kontrakten passer.`);
}

process.exit(main());

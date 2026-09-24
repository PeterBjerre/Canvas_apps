# -*- coding: utf-8 -*-
"""
Er regeltabellen i docs/31 sand?

    python3 tools/fl/check_rules_doc.py

docs/31-functional-location-regler.md er kontrakten for Functional
Location-appen: hver regel har et ID og en kolonne "Implementeret i". En
regel uden implementering er en fejl - og en henvisning til en funktion,
der er omdoebt eller slettet, er ogsaa en. Tjekket her efterproever:

  1. Hver regel (FLn) har en udfyldt "Implementeret i".
  2. Hvert navn i den kolonne findes: i den fil, der staar foran det
     (fl_validation.py, fl_parts.py ...), eller i appens byggede
     .pa.yaml (kontrolnavne som btnFlVerify).
  3. Hver regelkode, appen skriver i meddelelsestabellen (nfFlPlan og
     raekkebeskederne), har en raekke i tabellen.
  4. Hver valideringsregel har mindst to sager i testmatrixen, og hver
     UI-regel har et gyldigt og et ugyldigt eksempel.

Koeres af tools/build_all.py sammen med tools/fl/harness.js test.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "Functional Location App")
BUILD = os.path.join(APP, "build")
DOC = os.path.join(ROOT, "docs", "31-functional-location-regler.md")

# Regler uden noget at implementere - med begrundelsen i docs/31.
NO_IMPL = {"FL67"}
# Regler, der ikke kan udloeses i appen, og derfor kun har et gyldigt
# eksempel (docs/31, FL23 og FL24).
ONE_SIDED = {"FL23", "FL24"}
# UI-regler: efterproeves i Studio, har deres egen matrix i docs/31.
UI = {"FL2", "FL26", "FL27", "FL28", "FL29", "FL57", "FL58", "FL59", "FL60",
      "FL61", "FL62", "FL63", "FL64", "FL65", "FL66", "FL68", "FL69", "FL70"}


def rule_rows(text):
    """(id, sidste celle) for hver regelraekke i de to regeltabeller - ikke
    UI-matrixen, som ogsaa starter med '| FLn |'."""
    out = {}
    ui_start = text.index("| ID | Gyldigt eksempel")
    for m in re.finditer(r"^\| (FL\d+) \|(.*)\|\s*$", text, re.M):
        if m.start() > ui_start:
            continue
        cells = [c.strip() for c in m.group(2).split(" | ")]
        out[m.group(1)] = cells[-1]
    return out


def ui_rows(text):
    i = text.index("| ID | Gyldigt eksempel")
    j = text.index("\n\n", i)
    out = {}
    for m in re.finditer(r"^\| (FL\d+) \| (.*) \| (.*) \|$", text[i:j], re.M):
        out[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
    return out


def main():
    text = open(DOC, encoding="utf-8").read()
    rows = rule_rows(text)
    built = ""
    for f in os.listdir(APP):
        if f.endswith(".pa.yaml"):
            built += open(os.path.join(APP, f), encoding="utf-8").read()
    problems = []
    n_names = 0

    for rid, impl in sorted(rows.items(), key=lambda x: int(x[0][2:])):
        if rid in NO_IMPL:
            continue
        if not impl or impl in ("-", "–"):
            problems.append(f"{rid}: ingen 'Implementeret i'")
            continue
        current = None
        found = 0
        for tok in re.findall(r"`([^`]+)`", impl):
            t = tok.strip()
            if t.endswith((".py", ".json")):
                path = os.path.join(BUILD, t)
                if not os.path.isfile(path):
                    problems.append(f"{rid}: filen {t} findes ikke i {os.path.relpath(BUILD, ROOT)}")
                    current = None
                else:
                    current = open(path, encoding="utf-8").read()
                continue
            name = t.rstrip("()")
            if not re.fullmatch(r"[A-Za-z_][\w]*", name):
                continue          # et udtryk eller en vaerdi, ikke et navn
            n_names += 1
            hay = (current or "") + built
            if not re.search(r"\b%s\b" % re.escape(name), hay):
                problems.append(f"{rid}: '{name}' findes hverken i filen foran eller i den byggede app")
            else:
                found += 1
        if not found:
            problems.append(f"{rid}: 'Implementeret i' naevner intet navn, der kan efterproeves")

    # 3. Koderne, appen skriver, skal staa i tabellen.
    plan = json.load(open(os.path.join(BUILD, "fl_rules.generated.json"), encoding="utf-8"))
    codes = {p["Rule"] for p in plan["plan"] if p["Rule"]}
    sys.path.insert(0, BUILD)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fl_validation
    codes |= {c for _col, c, _f in fl_validation.ROW_MSGS} | {"FL9"}
    for c in sorted(codes - set(rows)):
        problems.append(f"{c}: appen skriver koden, men den har ingen raekke i docs/31")

    # 4. Testmatrixen.
    M = json.load(open(os.path.join(ROOT, "tools", "fl", "testmatrix.json"), encoding="utf-8"))
    per = {}
    for c in M["cases"]:
        per.setdefault(c["rule"], []).append(c["id"])
    ui = ui_rows(text)
    for rid in sorted(rows, key=lambda x: int(x[2:])):
        if rid in NO_IMPL:
            continue
        if rid in UI:
            g, b = ui.get(rid, ("", ""))
            if not g or g in ("-", "–") or not b or b in ("-", "–"):
                problems.append(f"{rid}: UI-reglen mangler et gyldigt eller ugyldigt eksempel")
            continue
        need = 1 if rid in ONE_SIDED else 2
        have = len(per.get(rid, []))
        if have < need:
            problems.append(f"{rid}: {have} sag(er) i testmatrixen - mindst {need}")

    if problems:
        print("docs/31 passer ikke med koden:\n")
        for p in problems:
            print("  " + p)
        return 1
    print(f"docs/31: {len(rows)} regler, {n_names} henvisninger efterproevet, "
          f"{len(M['cases'])} testsager, {len(codes)} koder i meddelelsestabellen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

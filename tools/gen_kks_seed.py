# -*- coding: utf-8 -*-
"""
KKS-opslagets data: html/kks*.generated.js -> SharePoint.

    python3 tools/gen_kks_seed.py           # skriv sharepoint/seed/MD_KksFunctionKey.csv
    python3 tools/gen_kks_seed.py --check   # er seedet og MD_FLKey i trit med HTML'en?

KKS-skaermen (KKS App/) laeser tre noegleomraader. To af dem findes
allerede i SharePoint, og de GENBRUGES:

    Aggregatnoegle   MD_FLKey, KeyType = "Aggregate", Description udfyldt
    Komponentnoegle  MD_FLKey, KeyType = "Component", Description udfyldt

MD_FLKey er Functional Location-appens noegleliste (docs/31). Dens
aggregat- og komponentraekker MED beskrivelse er ordret de raekker,
html/kks-aggregate.generated.js og kks-component.generated.js har - 98 og
60. Raekkerne UDEN beskrivelse (klassebestemmelsens ekstra noegler) viser
KKS-skaermen ikke.

Funktionsnoeglerne kan IKKE genbruges fra MD_FLKey: dens 6.441
Function-raekker er de gyldige noegler uden tekst, mens KKS-vejledningen
er 2.913 raekker MED tekst - med dubletter, noter ("*", "**"),
O-grupper der ikke er noegler, og 48 beskrivelser over 255 tegn. Den faar
sin egen liste, MD_KksFunctionKey (Provision-KksLists.ps1).

--check koeres af tools/build_all.py og fejler, hvis
  1. MD_KksFunctionKey.csv ikke laengere er det, kks.generated.js giver, eller
  2. MD_FLKey.csv's aggregat-/komponentraekker med beskrivelse ikke
     laengere er de raekker, KKS-HTML'en har. Saa ville skaermen vise noget
     andet end vejledningen - og genbruget var en fejl.
"""
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "html")
SEED = os.path.join(ROOT, "sharepoint", "seed")

FUNCTION_JS = os.path.join(HTML, "kks.generated.js")
REUSED_JS = {"Aggregate": os.path.join(HTML, "kks-aggregate.generated.js"),
             "Component": os.path.join(HTML, "kks-component.generated.js")}
FUNCTION_CSV = os.path.join(SEED, "MD_KksFunctionKey.csv")
FLKEY_CSV = os.path.join(SEED, "MD_FLKey.csv")

HEADER = ["SortNo", "Section", "Code", "Description"]
# Sektionen med de 25 overordnede bogstaver. Den staar FOERST, som i
# HTML-siden og den oprindelige app: "ALL" uden soegning viser den.
HOME = "HOME"


def load_js(path):
    """window.KKS_DATA = [...] -> listen af sektioner."""
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    return json.loads(text[text.index("["):text.rindex("]") + 1])


def function_rows():
    """[(SortNo, Section, Code, Description)] i visningsraekkefoelge."""
    sections = load_js(FUNCTION_JS)
    ordered = ([s for s in sections if s["key"] == HOME]
               + [s for s in sections if s["key"] != HOME])
    out = []
    for s in ordered:
        for r in s["rows"]:
            desc = " ".join(r["description"].split())
            out.append((len(out) + 1, s["key"], r["code"].strip(), desc))
    return out


def write():
    rows = function_rows()
    with io.open(FUNCTION_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(HEADER)
        w.writerows(rows)
    print("%s: %d raekker i %d sektioner" % (
        os.path.relpath(FUNCTION_CSV, ROOT), len(rows), len({r[1] for r in rows})))


def _read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check():
    problems = []
    want = [[str(x) for x in r] for r in function_rows()]
    if not os.path.exists(FUNCTION_CSV):
        problems.append("%s findes ikke" % os.path.relpath(FUNCTION_CSV, ROOT))
    else:
        have = [[r[h] for h in HEADER] for r in _read_csv(FUNCTION_CSV)]
        if have != want:
            problems.append("%s er ikke i trit med html/kks.generated.js"
                            % os.path.relpath(FUNCTION_CSV, ROOT))

    flkey = _read_csv(FLKEY_CSV)
    for key_type, path in REUSED_JS.items():
        js = {(r["code"].strip(), r["description"].strip())
              for s in load_js(path) for r in s["rows"]}
        sp = {(r["KeyValue"].strip(), r["Description"].strip())
              for r in flkey if r["KeyType"] == key_type and r["Description"].strip()}
        if js != sp:
            only_js = sorted(js - sp)[:5]
            only_sp = sorted(sp - js)[:5]
            problems.append(
                "MD_FLKey (%s) er ikke laengere KKS-vejledningens raekker:\n"
                "      kun i %s: %s\n      kun i MD_FLKey.csv: %s"
                % (key_type, os.path.basename(path), only_js, only_sp))

    if problems:
        print("KKS-data ikke i trit:")
        for p in problems:
            print("  " + p)
        print("Seedet skrives igen med: python3 tools/gen_kks_seed.py\n"
              "Skilles MD_FLKey og KKS-HTML'en ad, skal KKS-skaermen have sin egen\n"
              "liste til aggregat/komponent - se KKS App/README.md.")
        return 1
    print("KKS-data OK: %d funktionsraekker i seedet; aggregat og komponent "
          "genbruger MD_FLKey." % len(want))
    return 0


def main(argv):
    if "--check" in argv[1:]:
        return check()
    write()
    return check()


if __name__ == "__main__":
    sys.exit(main(sys.argv))

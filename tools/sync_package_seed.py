# -*- coding: utf-8 -*-
"""
Skriver sharepoint/seed/MD_StrategyPackage.csv ud fra det, der FAKTISK staar
i SharePoint.

    .\\Export-ListSchema.ps1 -SiteUrl "https://..."      # hent frisk udtraek
    python3 tools/sync_package_seed.py

HVORFOR
-------
Provision-StrategyLists.ps1 behandler csv'en som sandheden og OPDATERER
eksisterende pakkeraekker ud fra den. Det er rigtigt, naar rettelser sker i
csv'en - men forkert, hvis nogen har rettet direkte i SharePoint: saa ruller
naeste koersel rettelsen tilbage uden at sige noget.

Denne fil vender pilen om. Efter en manuel rettelse i listen koeres den, og
csv'en kommer til at matche virkeligheden igen. Saa er naeste
provisioneringskoersel en no-op i stedet for en tilbagerulning.
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sharepoint", "inspect", "out", "sample-MD_StrategyPackage.json")
OUT = os.path.join(ROOT, "sharepoint", "seed", "MD_StrategyPackage.csv")
COLS = ["Title", "StrategyKey", "PackageNo", "ShortCode", "CycleLength",
        "CycleUnit", "Hierarchy", "PackageText", "OffsetValue"]


def cell(v):
    # Choice-kolonner kommer som { "Value": "YR" } fra udtraekket.
    if isinstance(v, dict):
        v = v.get("Value", "")
    return "" if v is None else str(v)


def main():
    if not os.path.exists(SRC):
        print(f"Finder ikke {SRC}\n"
              f"Koer Export-ListSchema.ps1 foerst, saa der er et frisk udtraek.")
        return 2

    # Udtraekkets alder. Er det gammelt, beskriver det ikke listen som den ser
    # ud NU - og saa synkroniserer vi csv'en til en foraeldet tilstand.
    schema = os.path.join(os.path.dirname(SRC), "schema.json")
    stamp = None
    if os.path.exists(schema):
        try:
            stamp = json.load(open(schema, encoding="utf-8-sig")).get("exportedOn")
        except Exception:
            pass
    print(f"Udtraek fra: {stamp or 'ukendt'}")
    print("Er det aeldre end din seneste rettelse i SharePoint, saa koer")
    print("Export-ListSchema.ps1 igen FOER denne fil.\n")

    rows = json.load(open(SRC, encoding="utf-8-sig"))
    rows = rows if isinstance(rows, list) else [rows]
    rows.sort(key=lambda r: (cell(r.get("StrategyKey")), int(r.get("PackageNo") or 0)))

    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                old[(r.get("StrategyKey"), r.get("PackageNo"))] = r

    out, changed = [], []
    for r in rows:
        rec = {c: cell(r.get(c)) for c in COLS}
        out.append(rec)
        prev = old.get((rec["StrategyKey"], rec["PackageNo"]))
        if prev is None:
            changed.append(f"  NY      {rec['StrategyKey']}-{rec['PackageNo']}")
        else:
            diffs = [f"{c}: {prev.get(c)!r} -> {rec[c]!r}"
                     for c in COLS if prev.get(c, "") != rec[c]]
            if diffs:
                changed.append(f"  AENDRET {rec['StrategyKey']}-{rec['PackageNo']}: "
                               + "; ".join(diffs))

    for key in old:
        if not any((r["StrategyKey"], r["PackageNo"]) == key for r in out):
            changed.append(f"  VAEK    {key[0]}-{key[1]} (findes ikke i SharePoint)")

    # BOM: Windows PowerShell 5.1 laeser UTF-8 uden BOM som Windows-1252.
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\r\n") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(out)

    print(f"Skrev {OUT} - {len(out)} pakker fra SharePoint")
    if changed:
        print(f"\n{len(changed)} forskel(le) i forhold til csv'en foer:")
        for c in changed:
            print(c)
        print("\nCsv'en matcher nu listen. Naeste provisioneringskoersel "
              "aendrer ingenting.")
    else:
        print("Ingen forskelle - csv'en var allerede i sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
Laver sharepoint/seed/MD_StrategyPackage.csv ud af SAP-udtraekket
"Strategi pakker.xlsx" (fanen RawData) i roden af repoet.

    python3 tools/gen_package_seed.py [sti/til/fil.xlsx]

Kraever openpyxl (pip install openpyxl). Den OVERSKRIVER csv'en.

PAKKECYKLUS
-----------
SAP leverer pakkecyklus (PkCy.) i SEKUNDER. Den regnes om til den enhed,
pakken er angivet med (Unit), med SAP's egne faktorer:

    H    = 3.600 s           (time)
    D    = 86.400 s          (dag, taellerdage)
    DAY  = 86.400 s          (dag)
    WK   = 604.800 s         (7 dage)
    MON  = 2.592.000 s       (30 dage)
    YR   = 31.536.000 s      (365 dage)

Gaar en cyklus ikke op i et helt tal i sin enhed, stopper scriptet og
skriver raekken - saa bliver et forkert tal aldrig til en seed-vaerdi.

Tomme ST-kolonner (Hierarchy, OffsetValue) bliver 0, som provisioneringen
alligevel goer med [int]''.
"""
import csv, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Strategi pakker.xlsx")
OUT = os.path.join(ROOT, "sharepoint", "seed", "MD_StrategyPackage.csv")
STRATEGIES = os.path.join(ROOT, "sharepoint", "seed", "MD_Strategy.csv")
SHEET = "RawData"
COLS = ["Title", "StrategyKey", "PackageNo", "ShortCode", "CycleLength",
        "CycleUnit", "Hierarchy", "PackageText", "OffsetValue"]

SECONDS = {
    "H": 3600,
    "D": 86400,
    "DAY": 86400,
    "WK": 7 * 86400,
    "MON": 30 * 86400,
    "YR": 365 * 86400,
}

# Kolonnerne i udtraekket. Der er tre, der hedder "ST", saa de tages paa
# plads og ikke paa navn.
EXPECTED = ["Strat.", "StratD.", "Package", "ST", "PkCy.", "Unit", "ST",
            "Maintenance cycle text", "ST"]


def num(v):
    v = "" if v is None else str(v).strip()
    return str(int(v)) if v else "0"


def main():
    try:
        import openpyxl
    except ImportError:
        print("Mangler openpyxl: pip install openpyxl")
        return 2

    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    ws = openpyxl.load_workbook(src, read_only=True, data_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    header = [("" if c is None else str(c).strip()) for c in rows[0][:9]]
    if header != EXPECTED:
        print(f"Uventede kolonner i {SHEET}: {header}")
        return 2

    out, bad, seen = [], [], set()
    for lineno, r in enumerate(rows[1:], 2):
        if not r or r[0] in (None, ""):
            continue
        key, _, pkg, short, secs, unit, hier, text, offset = (list(r) + [None] * 9)[:9]
        key, unit = str(key).strip(), str(unit).strip()
        pkg_no = int(str(pkg).strip())
        if (key, pkg_no) in seen:
            bad.append(f"  raekke {lineno}: dublet {key}-{pkg_no}")
            continue
        seen.add((key, pkg_no))
        if unit not in SECONDS:
            bad.append(f"  raekke {lineno}: ukendt enhed {unit!r} ({key}-{pkg_no})")
            continue
        length, rest = divmod(int(secs), SECONDS[unit])
        if rest:
            bad.append(f"  raekke {lineno}: {key}-{pkg_no} {secs} s er ikke "
                       f"et helt antal {unit} ({int(secs) / SECONDS[unit]:.4f})")
            continue
        out.append({
            "Title": f"{key}-{pkg_no}",
            "StrategyKey": key,
            "PackageNo": str(pkg_no),
            "ShortCode": "" if short is None else str(short).strip(),
            "CycleLength": str(length),
            "CycleUnit": unit,
            "Hierarchy": num(hier),
            "PackageText": "" if text is None else str(text).strip(),
            "OffsetValue": num(offset),
        })

    if bad:
        print(f"{len(bad)} raekke(r) kan ikke omregnes - csv'en er IKKE skrevet:")
        print("\n".join(bad))
        return 1

    # Raekkefoelge som sync_package_seed.py, saa de to scripts giver samme fil.
    out.sort(key=lambda r: (r["StrategyKey"], int(r["PackageNo"])))

    # BOM: Windows PowerShell 5.1 laeser UTF-8 uden BOM som Windows-1252.
    with open(OUT, "w", encoding="utf-8-sig", newline="\r\n") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(out)

    keys = sorted({r["StrategyKey"] for r in out})
    print(f"Skrev {OUT}")
    print(f"  {len(out)} pakker fordelt paa {len(keys)} strategier")
    if os.path.exists(STRATEGIES):
        with open(STRATEGIES, encoding="utf-8-sig", newline="") as f:
            known = {r["Title"] for r in csv.DictReader(f)}
        missing = [k for k in keys if k not in known]
        if missing:
            print(f"  {len(missing)} strategier findes ikke i MD_Strategy.csv: "
                  f"{', '.join(missing)}")
            print("  Tilfoej dem i sharepoint/Strategier.txt og koer "
                  "tools/gen_strategy_seed.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

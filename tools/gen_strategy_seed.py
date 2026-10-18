# -*- coding: utf-8 -*-
"""
Laver sharepoint/seed/MD_Strategy.csv ud af SAP-udtraekket Strategier.txt.

    python3 tools/gen_strategy_seed.py

Koer den igen, naar der er hentet et nyt udtraek fra SAP. Den OVERSKRIVER
csv'en - saa ret ikke i csv'en i haanden, og ret slet ikke Hierarchical
der: den vedligeholdes i SharePoint-listen, ikke her (se nedenfor).

SchedulingIndicator GAETTES
---------------------------
Strateginavnet afsloerer typen: begynder det med "Taeller" eller "T.", er
det en taellerstrategi (PERFORMANCE), ellers er det tid (TIME). Det er et
kvalificeret gaet ud fra teksten - IKKE noget der er laest i SAP. Det skal
efterproeves mod IP11.

Hierarchical UDLEDES AF PAKKERNE
--------------------------------
Navnet siger intet om det, men pakkernes Hierarchy (fra "Strategi
pakker.xlsx", se tools/gen_package_seed.py) goer. I SAP kaldes kun pakken
med det hoejeste hierarki, naar flere forfalder samme dag - saa den skal
indeholde de lavere pakkers operationer. Det er det, appens "Fill by
hierarchy" goer. Reglen her:

    Ja             pakkerne har forskellige hierarkier og ingen offset
    Nej            ingen pakker har hierarki, alle har det samme, eller
                   pakkerne er forskudt med offset (fx JAN, FEB, ... eller
                   "Aar 1, 2, 3"), saa de aldrig forfalder samtidig
    Ikke afklaret  ingen pakker indlaest, eller kun nogle pakker har
                   hoejere hierarki end resten (fx 10, 20, 10, 10)

Koer gen_package_seed.py foerst, saa pakke-csv'en er frisk. Provisioneringen
retter kun raekker, der staar som "Ikke afklaret" i SharePoint, saa en
vaerdi sat i haanden bliver staaende.
"""
import csv, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sharepoint", "Strategier.txt")
OUT = os.path.join(ROOT, "sharepoint", "seed", "MD_Strategy.csv")

# "Taeller 250-1000..." og den forkortede "T. 250-500..." er begge taellere.
PACKAGES = os.path.join(ROOT, "sharepoint", "seed", "MD_StrategyPackage.csv")

COUNTER = re.compile(r"^\s*(Tæller|Taeller|T\.)", re.I)


def hierarchical_by_strategy():
    """StrategyKey -> Ja/Nej/Ikke afklaret ud fra pakkerne (se oeverst)."""
    pkgs = {}
    if os.path.exists(PACKAGES):
        with open(PACKAGES, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                pkgs.setdefault(r["StrategyKey"], []).append(
                    (int(r["Hierarchy"] or 0), int(r["OffsetValue"] or 0)))
    out = {}
    for key, p in pkgs.items():
        levels = {h for h, _ in p}
        if len(levels) == 1 or any(o for _, o in p):
            out[key] = "Nej"
        elif 0 in levels:
            out[key] = "Ikke afklaret"
        elif len(levels) == len(p):
            out[key] = "Ja"
        else:
            out[key] = "Ikke afklaret"
    return out


def main():
    hier = hierarchical_by_strategy()
    rows, seen = [], set()
    for lineno, line in enumerate(open(SRC, encoding="utf-8"), 1):
        line = line.rstrip("\r\n")
        if not line.strip():
            continue
        key, _, name = line.partition("\t")
        key, name = key.strip(), name.strip()
        if not key or not name:
            print(f"  linje {lineno}: springer over, ikke to kolonner: {line!r}")
            continue
        if key in seen:
            print(f"  linje {lineno}: DUBLET noegle {key} - springer over")
            continue
        seen.add(key)
        rows.append({
            "Title": key,
            "StrategyName": name,
            "SchedulingIndicator": "PERFORMANCE" if COUNTER.match(name) else "TIME",
            "Hierarchical": hier.get(key, "Ikke afklaret"),
            "PackagesLoaded": "FALSE",
            "Notes": "",
        })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # BOM: Windows PowerShell 5.1 laeser UTF-8 uden BOM som Windows-1252,
    # og saa bliver "Taeller" til "TÃ¦ller" i SharePoint.
    with open(OUT, "w", encoding="utf-8-sig", newline="\r\n") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)

    perf = sum(1 for r in rows if r["SchedulingIndicator"] == "PERFORMANCE")
    print(f"Skrev {OUT}")
    print(f"  {len(rows)} strategier")
    print(f"  {perf} gaettet som PERFORMANCE (taeller), {len(rows)-perf} som TIME")
    for v in ("Ja", "Nej", "Ikke afklaret"):
        keys = [r["Title"] for r in rows if r["Hierarchical"] == v]
        print(f"  Hierarchical = {v}: {len(keys)}"
              + (f" ({', '.join(keys)})" if v != "Ja" else ""))
    trunc = [r for r in rows if len(r["StrategyName"]) >= 30]
    if trunc:
        print(f"  {len(trunc)} navne er praecis 30 tegn - SAP afkorter her, "
              f"saa de kan vaere klippet midt i et ord")
    return 0


if __name__ == "__main__":
    sys.exit(main())

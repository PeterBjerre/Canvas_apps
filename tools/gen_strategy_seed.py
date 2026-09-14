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

Hierarchical GAETTES IKKE
-------------------------
Om en strategi undertrykker sine egne pakker, staar ikke i navnet, og der
er intet i udtraekket at udlede det af. Alle raekker faar derfor
"Ikke afklaret", og feltet saettes i haanden i SharePoint. Et forkert
default her ville forplante sig hele vejen til SAP uden at nogen opdagede
det.
"""
import csv, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sharepoint", "Strategier.txt")
OUT = os.path.join(ROOT, "sharepoint", "seed", "MD_Strategy.csv")

# "Taeller 250-1000..." og den forkortede "T. 250-500..." er begge taellere.
COUNTER = re.compile(r"^\s*(Tæller|Taeller|T\.)", re.I)


def main():
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
            "Hierarchical": "Ikke afklaret",
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
    print(f"  {len(rows)} med Hierarchical = 'Ikke afklaret' - saettes i haanden")
    trunc = [r for r in rows if len(r["StrategyName"]) >= 30]
    if trunc:
        print(f"  {len(trunc)} navne er praecis 30 tegn - SAP afkorter her, "
              f"saa de kan vaere klippet midt i et ord")
    return 0


if __name__ == "__main__":
    sys.exit(main())

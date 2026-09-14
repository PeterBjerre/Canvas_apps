# -*- coding: utf-8 -*-
"""
Tjekker at PowerShell-scripterne kan laeses af Windows PowerShell 5.1.

    python3 tools/check_ps1.py

HVORFOR
-------
Windows PowerShell 5.1 antager Windows-1252, naar en .ps1 ikke har en BOM.
Et UTF-8 em-dash (E2 80 94) bliver saa laest som tre tegn - hvoraf det ene
er et anfoerselstegn, der AABNER en streng. Resten af filen parses som
tekst, og fejlen dukker op et helt andet sted end tegnet staar:

    Expressions are only allowed as the first element of a pipeline

Det kostede en runde paa Export-ListSchema.ps1. To regler forhindrer det:

    1. Filen skal have en UTF-8 BOM.
    2. Filen skal alligevel vaere ren ASCII.

Regel 2 alene ville vaere nok, men BOM'en goer det ufarligt, hvis nogen
senere skriver et dansk tegn i en tekststreng. Brug ae/oe/aa i kildekoden
og gem de rigtige bogstaver til det, scripterne SKRIVER UD.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOM = b"\xef\xbb\xbf"


def main():
    problems = []
    checked = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            if not fn.lower().endswith(".ps1"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            checked += 1
            raw = open(path, "rb").read()

            if not raw.startswith(BOM):
                problems.append(f"{rel}: mangler UTF-8 BOM")

            body = raw[len(BOM):] if raw.startswith(BOM) else raw
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError as e:
                problems.append(f"{rel}: ikke gyldig UTF-8 ({e})")
                continue

            for lineno, line in enumerate(text.splitlines(), 1):
                bad = sorted({c for c in line if ord(c) > 127})
                if bad:
                    shown = ", ".join(f"{c!r} (U+{ord(c):04X})" for c in bad)
                    problems.append(f"{rel}:{lineno}: ikke-ASCII tegn: {shown}")

    if problems:
        print(f"{len(problems)} problem(er) i {checked} PowerShell-fil(er):\n")
        for p in problems:
            print("  " + p)
        print("\nBrug ae/oe/aa og '-' i stedet for em-dash. Gem filen som "
              "UTF-8 MED BOM.")
        return 1
    print(f"PowerShell-tjek OK: {checked} fil(er), alle med BOM og ren ASCII.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

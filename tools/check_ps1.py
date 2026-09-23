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

REGEL 3: INGEN LINJEFORTSAETTELSE MED BACKTICK
----------------------------------------------
Provision-HelpText.ps1 blev skrevet med `` i stedet for ` i enden af fem
linjer. To backticks er et ESCAPET backtick-tegn, ikke en fortsaettelse,
saa linjen slutter dér:

    New-HelpField 'AppArea' Choice -Choices 'FunctionalLocation',``
        'MeasuringPoint','Material','MaintenancePlan' -Indexed -Required

    Unexpected token '-Indexed' in expression or statement.

Scriptet kunne ikke koere, og tjekket her sagde god for filen: den havde
BOM og var ren ASCII.

TO TING FLAGGES, OG KUN TO
    ``  sidst paa en kodelinje   - altid en parsefejl
    `   med mellemrum efter      - ogsaa en parsefejl, og mellemrummet
                                   kan man ikke se

En REN enkelt backtick er gyldig og staar 18 steder i scripter, der
virker. Den flages ikke. Foerste udgave af reglen gjorde, og fandt 20
"fejl" - heraf to i KOMMENTARER (`#  Register-PnPEntraIDAppForInteractive
Login ``) og atten gyldige fortsaettelser. En vagt, der raaber 20 gange
om ingenting, bliver slaaet fra.

Kommentarlinjer og here-strings springes derfor over.

Der er ingen PowerShell-fortolker i byggeriet, saa en rigtig parsekontrol
er ikke mulig. Det her er den ene fejlklasse, der faktisk har ramt.
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

            in_here = None
            for lineno, line in enumerate(text.splitlines(), 1):
                bad = sorted({c for c in line if ord(c) > 127})
                if bad:
                    shown = ", ".join(f"{c!r} (U+{ord(c):04X})" for c in bad)
                    problems.append(f"{rel}:{lineno}: ikke-ASCII tegn: {shown}")

                # Here-strings og kommentarer er ikke kode. Se REGEL 3.
                if in_here:
                    if line.strip() == in_here:
                        in_here = None
                    continue
                if line.rstrip().endswith('@"'):
                    in_here = '"@'
                    continue
                if line.rstrip().endswith("@'"):
                    in_here = "'@"
                    continue
                if line.lstrip().startswith("#"):
                    continue

                stripped = line.rstrip()
                if stripped.endswith("``"):
                    problems.append(
                        f"{rel}:{lineno}: dobbelt backtick sidst paa linjen. "
                        f"`` er et ESCAPET backtick-tegn, ikke en "
                        f"fortsaettelse - linjen slutter der, og naeste linje "
                        f"parses for sig. Skriv den om uden fortsaettelse: en "
                        f"variabel foerst, eller et komma der selv fortsaetter")
                elif stripped.endswith("`") and line != stripped:
                    problems.append(
                        f"{rel}:{lineno}: backtick med mellemrum efter. "
                        f"Fortsaettelsen gaelder kun, naar backticken er det "
                        f"SIDSTE tegn paa linjen - og mellemrummet kan man "
                        f"ikke se. Fjern det, eller skriv linjen om")

    if problems:
        print(f"{len(problems)} problem(er) i {checked} PowerShell-fil(er):\n")
        for p in problems:
            print("  " + p)
        print("\nBrug ae/oe/aa og '-' i stedet for em-dash. Gem filen som "
              "UTF-8 MED BOM.\nOg skriv linjefortsaettelser om - en backtick "
              "sidst paa linjen er for let at braekke.")
        return 1
    print(f"PowerShell-tjek OK: {checked} fil(er), alle med BOM, ren ASCII "
          f"og uden braekkede linjefortsaettelser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

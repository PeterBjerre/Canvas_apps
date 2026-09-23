# -*- coding: utf-8 -*-
"""
Skriver sharepoint/seed/MD_HelpText.csv ud af build_help.py.

HVORFOR GENERERET OG IKKE SKREVET
---------------------------------
Teksterne findes allerede - de har staaet i build_help.py, siden appen
blev bygget. Skrev nogen dem af i haanden ind i en csv, ville dag eet
vaere to udgaver af den samme tekst, og den ene ville vaere forkert med
det samme.

Seedet er derfor et UDTRAEK. Foerste gang listen fyldes, indeholder den
ordret det, appen viste i forvejen. Derefter ejer SharePoint teksterne,
og build_help.py har ikke laengere en kopi (_check_no_static() nedenfor
efterproever det).

HVAD DER IKKE KOMMER MED
------------------------
De syv DYNAMISKE hints. De er ikke tekst, men Power Fx:

    "PlanText": If(
        !StartsWith(Upper(PlanText), Upper(Plant)),
        "Should start with the plant code " & varVhpPlan.Plant & " - ...",
        "Start with the plant code. ..."
    )

Den fortaeller HVORFOR feltet lyser lige nu og saetter vaerkskoden ind.
Den kan ikke vaere en raekke i en liste, og den bliver i koden.

DEN HER ER KOERT EEN GANG, OG DET VAR MENINGEN
----------------------------------------------
Scriptet er et FLYTTEVAERKTOEJ. Da teksterne var flyttet, havde
build_help.py ikke laengere en kopi at laese - og saa producerer
scriptet en TOM csv.

Det er ikke en teoretisk fare: koerer man den i dag, overskriver den
sharepoint/seed/MD_HelpText.csv med bare en overskriftslinje, og de 36
raekker er vaek. _refuse_to_empty() nedenfor stopper det.

Skal seedet laves om, er kilden nu LISTEN - ikke koden. Eksporter den
fra SharePoint.
"""
import ast
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELP = os.path.join(ROOT, "Maintenance Plan App", "build", "build_help.py")
OUT = os.path.join(ROOT, "sharepoint", "seed", "MD_HelpText.csv")

# Appen, raekkerne hoerer til. Samme vaerdier som Domain i MD_RequestIndex,
# saa de fem apps kan dele listen uden at laese hinandens tekster.
APP = "MaintenancePlan"

COLUMNS = ["HelpKey", "AppArea", "Kind", "Heading", "Body", "SortOrder"]


def _module():
    src = io.open(HELP, encoding="utf-8").read()
    return ast.parse(src)


def static_hints(tree):
    """De hints, der er EEN _q("...")-streng og intet andet.

    Alt andet er et udtryk - en If, en konkatenering - og hoerer i koden."""
    out = []
    for node in tree.body:
        if not (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "HINTS"):
            continue
        for k, v in zip(node.value.keys, node.value.values):
            if (isinstance(v, ast.Call) and getattr(v.func, "id", "") == "_q"
                    and len(v.args) == 1 and isinstance(v.args[0], ast.Constant)):
                out.append((k.value, v.args[0].value))
    return out


def panels(tree):
    for node in tree.body:
        if not (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "PANELS"):
            continue
        for k, v in zip(node.value.keys, node.value.values):
            lines = []
            for i, el in enumerate(v.elts):
                head = ast.literal_eval(el.elts[0])
                body = ast.literal_eval(el.elts[1])
                lines.append((i + 1, head, body))
            yield k.value, lines


def source_note(tree):
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "SOURCE_NOTE"):
            return ast.literal_eval(node.value)
    return None


def rows():
    tree = _module()
    out = []
    for key, text in static_hints(tree):
        out.append({"HelpKey": key, "AppArea": APP, "Kind": "Hint",
                    "Heading": "", "Body": text, "SortOrder": 0})
    for section, lines in panels(tree):
        for order, head, body in lines:
            out.append({"HelpKey": section, "AppArea": APP, "Kind": "Panel",
                        "Heading": head, "Body": body, "SortOrder": order})
    # Kildehenvisningen staar nederst i HVERT panel. Den er en raekke som
    # de andre, saa den ogsaa kan rettes uden en ny build.
    note = source_note(tree)
    if note:
        for section, lines in panels(tree):
            out.append({"HelpKey": section, "AppArea": APP, "Kind": "Panel",
                        "Heading": "", "Body": note, "SortOrder": 99})
    return out


def _refuse_to_empty(data):
    """Et flyttevaerktoej maa ikke oedelaegge det, det har flyttet.

    Foerste gang scriptet koerte, stod teksterne i build_help.py, og det
    skrev 36 raekker. Bagefter var de VAEK fra koden - det var hele
    pointen - saa anden gang ville det skrive nul raekker oven i dem.

    Der er ingen rigtig grund til at koere det igen, saa det siger fra i
    stedet for at goere skade."""
    if data:
        return
    had = 0
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8-sig", newline="") as f:
            had = max(0, sum(1 for _ in f) - 1)
    if not had:
        print("Ingen statiske hjaelpetekster i build_help.py, og intet seed "
              "i forvejen.\nDer er ingenting at flytte.")
        return
    raise SystemExit(
        "STOPPER: build_help.py har ingen statiske hjaelpetekster tilbage,\n"
        "men %s har %d raekke(r).\n\n"
        "Flytningen er gjort. Teksterne bor i SharePoint-listen MD_HelpText,\n"
        "og koden har ikke laengere en kopi at lave et seed ud af - saa det\n"
        "her ville skrive en TOM fil oven i dem.\n\n"
        "Skal listen fyldes, saa koer provisioneringen med det seed, der\n"
        "allerede ligger:\n"
        "    sharepoint/provision/Provision-HelpText.ps1 -SiteUrl <url> -Seed\n\n"
        "Skal seedet laves om, er kilden LISTEN - eksporter den fra SharePoint."
        % (os.path.relpath(OUT, ROOT), had))


def main():
    data = rows()
    _refuse_to_empty(data)
    if not data:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in data:
            w.writerow(r)
    n_hint = sum(1 for r in data if r["Kind"] == "Hint")
    n_panel = len(data) - n_hint
    print("Skrev %s" % os.path.relpath(OUT, ROOT))
    print("  %d hints, %d panelafsnit" % (n_hint, n_panel))
    print("\nLaeg dem i SharePoint med:")
    print("  sharepoint/provision/Provision-HelpText.ps1 -SiteUrl <url> -Seed")


if __name__ == "__main__":
    main()

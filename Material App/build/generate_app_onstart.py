# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml: navngivne formler + OnStart.

APPENS EGEN - de to domaeneapps maa nu afvige.

OnStart HENTER INGEN DATA
-------------------------
Her staar kun skemaet for de samlinger, appen skriver i, og de to
variabler, skaermen skal kunne laese, foer den er vist een gang.
Raekkerne hentes i skaermens OnVisible - se assemble_screen.py.

Opslagslisten staar som NAVNGIVEN FORMEL: den evalueres foerst, naar
dropdownen aabnes, og caches derefter.

Skemaet skrives eksplicit med ClearCollect + Clear. Uden det kender Power
Fx ikke kolonnetyperne, foer brugeren har tilfoejet noget, og formler mod
en tom samling fejler allerede i compile.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import design_tokens as tok
import layout_tokens as lay
import domain_config as cfg
from domain_parts import FIELDS

OUT_DIR = os.path.join(HERE, "..")

EMPTY = {"num": "0", "date": "Blank()", "long": '""', "choice": '""', "text": '""'}


def _row_schema():
    s = {"RowId": "0", "ItemKey": '""', "RequestNo": '""',
         "Status": '""', "FileCount": "0",
         cfg.C_TEXT: '""', "Plant": '""'}
    for col, _lab, kind, _ch in FIELDS:
        s[col] = EMPTY[kind]
    return s


COLLECTIONS = [
    # Spejlet af SharePoint-listen. ALDRIG sandheden - den hentes forfra
    # efter hver skrivning.
    ("colDomRows", _row_schema()),
    # Dokumenterne som de ligger i biblioteket. Identifier er den, en
    # sletning skal bruge; FileUrl er linket.
    ("colDomAttachments",
     {"RowId": "0", "FileName": '""', "FileUrl": '""', "Identifier": '""',
      "Selected": "false"}),
    # Hvad upload-flowet svarede pr. fil. Uden den kunne knappen kun
    # kvittere paa tro og love.
    ("colDomAttUp", {"Name": '""', "Ok": "false"}),
    # FL-soegningens resultat. Samme form som VH-plan-appens - se
    # build_flsearch.py for hvorfor der er baade Code, Description og
    # Display.
    ("colDomFl",
     {"Code": '""', "Description": '""', "Display": '""',
      "Maintainable": "false", "Level": '""'}),
    # Brugerens temavalg. Skrives af SaveData og laeses af LoadData - se
    # tools/design_tokens.py.
    tok.prefs_schema(),
]


def formulas_block():
    return (
        tok.formula() + "\n\n" + lay.formula() + "\n\n"
        "// Vaerkerne. Eneste opslagsliste appen laeser, og den laeses foerst,\n"
        "// naar dropdownen aabnes.\n"
        f"colDomPlants = Sort(ForAll({cfg.L_PLANTS} As R, {{ Value: R.Title }}), Value);"
    )


def collection_block():
    out = []
    for name, schema in COLLECTIONS:
        fields = ", ".join(f"{k}: {v}" for k, v in schema.items())
        out.append(f"ClearCollect({name}, {{ {fields} }});\nClear({name});")
    return "\n\n".join(out)


STATE = '''Set(varDomMe, Lower(User().Email));
Set(varDomRequestNo, "");
Set(varDomRequestGuid, "");
Set(varDomActiveRowId, Blank());
// Hvilken raekke detaljeruden viser. Blank = ruden er skjult.
Set(varDomDetailsId, Blank());
Set(varDomRowStatus, "valid");
Set(varDomAttJson, "");
Set(varDomFlMsg, "");
Set(varDomFlLast, "");
Set(varDomInfo, "");

// Er formularen blevet tjekket? Styrer om en kraevet feltkant maa vaere
// roed. false ved opstart: en tom formular, ingen har roert, skal ikke
// staa og lyse roedt. Saettes af Gem/Indsend - se domain_parts.REQUIRED.
Set(varDomValidated, false)'''


def main():
    # Temaet saettes FOER resten: skaermen tegner sig selv ud af C, og C
    # laeser darkModeEnabled.
    onstart = (collection_block() + "\n\n" + tok.onstart_block()
               + "\n\n" + STATE)

    lines = ["App:", "  Properties:", "    Formulas: |"]
    first = True
    for line in formulas_block().split("\n"):
        lines.append(("      =" if first else "      ") + line if line.strip() else "")
        first = False
    lines.append("    OnStart: |")
    first = True
    for line in onstart.split("\n"):
        if not line.strip():
            lines.append("")
            continue
        lines.append(("      =" if first else "      ") + line)
        first = False
    lines += ["    StartScreen: |-", f"        ={cfg.SCREEN}",
              "    Theme: |-", "        =PowerAppsTheme"]

    content = "\n".join(lines) + "\n"
    with open(os.path.join(OUT_DIR, "App.pa.yaml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(content)
    n = sum(onstart.count(x) for x in (cfg.L_ROWS, cfg.L_INDEX))
    print("App.pa.yaml skrevet.", content.count(chr(10)) + 1, "linjer,",
          len(COLLECTIONS), "arbejdssamlinger,", n, "datahentninger i OnStart.")


if __name__ == "__main__":
    main()

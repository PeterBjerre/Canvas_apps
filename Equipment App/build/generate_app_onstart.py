# -*- coding: utf-8 -*-
"""
Skriver ../App.pa.yaml: navngivne formler + OnStart.

Filen er ORDRET ens i de to domaene-build-mapper - alt det domaene-
specifikke staar i domain_config.py.

INGEN DATAHENTNING I OnStart
----------------------------
OnStart betales af hver bruger hver gang. Opslagslisterne staar som
NAVNGIVNE FORMLER: de evalueres foerst, naar noget faktisk laeser dem, og
cachet derefter. OnStart indeholder kun to ting - skemaet for de
samlinger, appen SKRIVER til, og de Set(), der styrer skaermen.

EEN undtagelse, og den er bevidst: er appen aabnet med ?reqid= fra
landingssiden, skal indmeldingen hentes, FOER skaermen tegnes. Den ligger
bag et If(IsBlank(Param(...))) og koster ingenting i det almindelige
tilfaelde.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import domain_config as cfg
import attflows as att
from build_domain import FIELDS

OUT_DIR = os.path.join(HERE, "..")


# ---------------------------------------------------------------------------
# Samlinger appen SKRIVER i. Skemaet skrives eksplicit, saa Power Fx kender
# kolonnetyperne, FOER brugeren har tilfoejet noget - ellers fejler formler
# mod en tom samling allerede i compile.
# ---------------------------------------------------------------------------
def _item_schema():
    s = {"LocalId": "0", "SpId": "0", "ItemKey": '""', "ItemText": '""'}
    for col, _lab, kind, _w, _ch in FIELDS:
        s[col] = {"num": "0", "bool": "false"}.get(kind, '""')
    return s


COLLECTIONS = [
    ("colDomItems", _item_schema()),
    # Dokumenterne som de ligger i biblioteket. Identifier er den, en
    # sletning skal bruge; FileUrl er linket.
    ("colDomAttachments",
     {"LocalId": "0", "FileName": '""', "FileUrl": '""', "Identifier": '""',
      "Selected": "false"}),
    # Hvad upload-flowet svarede pr. fil. Uden den kunne knappen kun
    # kvittere paa tro og love.
    ("colDomAttUp", {"Name": '""', "Ok": "false"}),
    # Arbejdsspand ved gem: hvilket SharePoint-id og hvilken noegle hver
    # post fik. Den kan foerst kendes EFTER raekken er skrevet.
    ("colDomSaved", {"LocalId": "0", "SpId": "0", "ItemKey": '""'}),
]


def formulas_block():
    """Navngivne formler. Raekkefoelgen er ligegyldig - Power Fx loeser selv
    afhaengighederne."""
    return (
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


STATE = f'''Set(varDomMe, Lower(User().Email));
Set(varDomStatus, "Kladde");
Set(varDomReqId, 0);
Set(varDomRequestNo, "");
Set(varDomGuid, GUID());
Set(varDomShortText, "");
Set(varDomPlant, "");
Set(varDomActiveItemId, Blank());
Set(varDomNextLocalId, 0);
Set(varDomAttJson, "");
Set(varDomPlayUrl, "{{PLAY_URL}}");'''


LOAD = f'''// Aabnet fra landingssiden med ?reqid=<guid>. Den ENESTE datahentning
// i OnStart, og den koerer kun i det tilfaelde.
If(
    !IsBlank(Param("reqid")),
    With(
        {{ hdr: LookUp({cfg.L_REQ}, RequestGuid = Param("reqid")) }},
        If(
            !IsBlank(hdr),
            Set(varDomReqId, hdr.ID);
            Set(varDomRequestNo, hdr.{cfg.C_REQ_NO});
            Set(varDomGuid, hdr.RequestGuid);
            Set(varDomStatus, hdr.Status.Value);
            Set(varDomShortText, hdr.ShortText);
            Set(varDomPlant, hdr.Plant);
            ClearCollect(
                colDomItems,
                ForAll(
                    Filter({cfg.L_ITEM}, {cfg.C_REQ_NO} = hdr.{cfg.C_REQ_NO}) As R,
                    {{
{{ITEM_LOAD}}
                    }}
                )
            );
            Set(varDomNextLocalId, Coalesce(Max(colDomItems, LocalId), 0))
        )
    )
)'''


def _load_fields():
    lines = [
        "                        LocalId: R.LineId,",
        "                        SpId: R.ID,",
        "                        ItemKey: R.ItemKey,",
        f"                        ItemText: R.{cfg.C_ITEM_TEXT},",
    ]
    for col, _lab, kind, _w, _ch in FIELDS:
        if kind == "choice":
            v = f'Coalesce(R.{col}.Value, "")'
        elif kind == "date":
            v = f'If(IsBlank(R.{col}), "", Text(R.{col}, "yyyy-mm-dd"))'
        elif kind == "num":
            v = f"Coalesce(R.{col}, 0)"
        elif kind == "bool":
            v = f"Coalesce(R.{col}, false)"
        else:
            v = f'Coalesce(R.{col}, "")'
        lines.append(f"                        {col}: {v},")
    lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines)


def main():
    onstart = "\n\n".join([
        collection_block(),
        STATE.replace("{PLAY_URL}", getattr(cfg, "PLAY_URL", "")),
        LOAD.replace("{ITEM_LOAD}", _load_fields()),
    ])

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
    n_fetch = onstart.count(f"{cfg.L_ITEM}") + onstart.count(f"{cfg.L_REQ}")
    print("App.pa.yaml skrevet.", content.count(chr(10)) + 1, "linjer,",
          len(COLLECTIONS), "arbejdssamlinger,", n_fetch,
          "datahentninger i OnStart (alle bag ?reqid-vagten).")


if __name__ == "__main__":
    main()

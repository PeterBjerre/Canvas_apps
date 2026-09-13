# -*- coding: utf-8 -*-
"""
Functional Location-soegning via Power Automate.

FLOW-KONTRAKTEN LIGGER HER OG KUN HER
-------------------------------------
Flowet BioSap-Integration-FunctionalLocations tager EET argument - hele
soegeteksten - og laver selv prefix og hex. Til gengaeld kender vi ikke
formen paa svaret uden at koere det. De fire konstanter nedenfor er det
eneste, der skal rettes, naar svaret er set:

    FLOW_OUTPUT      navnet paa outputtet i "Respond to a PowerApp or flow"
    JSON_ARRAY_PATH  tom streng hvis svaret ER et array, ellers feltnavnet
                     paa arrayet inde i svaret (fx "value")
    JSON_CODE_FIELD  feltet med FL-koden i hvert element
    JSON_DESC_FIELD  feltet med beskrivelsen

Ret dem, koer assemble_screen.py igen, og synkronisér. Alt andet foelger med.

SVARETS FORM (bekraeftet mod en koerende app)
---------------------------------------------
Outputtet hedder "json" og er et array:

    [ { "functionKey": "SSV10 KAB10AP001",
        "description": "Ball bearing house, pump area",
        "maintainable": true,
        "level": "3" }, ... ]

maintainable siger, om der overhovedet kan vedligeholdes paa lokationen.
Den baeres med og markeres i UI'et - en VH-plan paa en ikke-vedligeholdbar
FL giver ikke mening i SAP.

FORUDSAETNING: flowet skal vaere tilfoejet appen som datakilde i Studio,
FOER YAML'en synkroniseres. Ellers fejler compile paa et ukendt navn.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- flow-kontrakt -----------------------------------------------------------
FLOW_NAME = "BioSapIntegrationFunctionalLocations"
FLOW_OUTPUT = "json"
JSON_ARRAY_PATH = ""
JSON_MAINT_FIELD = "maintainable"
JSON_LEVEL_FIELD = "level"
JSON_CODE_FIELD = "functionKey"
JSON_DESC_FIELD = "description"

# Flowet kaldes foerst ved dette antal tegn.
MIN_SEARCH_LEN = 7

_RAW = "varVhpFlRaw"


def _array_expr():
    """Udtrykket der giver JSON-arrayet fra flow-svaret."""
    base = f"ParseJSON({_RAW}.{FLOW_OUTPUT})"
    if JSON_ARRAY_PATH:
        base = f"{base}.{JSON_ARRAY_PATH}"
    return f"Table({base})"


def collect_results(target_collection):
    """ClearCollect af flow-svaret ind i en (Code, Description)-samling."""
    return (
        f"ClearCollect(\n"
        f"    {target_collection},\n"
        f"    ForAll(\n"
        f"        {_array_expr()} As R,\n"
        f"        {{\n"
        f"            Code: Text(R.Value.{JSON_CODE_FIELD}),\n"
        f"            Description: Text(R.Value.{JSON_DESC_FIELD}),\n"
        f"            Maintainable: Boolean(R.Value.{JSON_MAINT_FIELD}),\n"
        f"            Level: Text(R.Value.{JSON_LEVEL_FIELD})\n"
        f"        }}\n"
        f"    )\n"
        f")"
    )


def search_action(search_text_expr, target_collection, last_search_var, msg_var,
                  label="Functional Locations"):
    """Kald flowet og fyld samlingen. Kaldes baade fra OnChange og fra
    Soeg-knappen, saa der kun findes een version af logikken.

    Kaldet springes over, naar soegeteksten er uaendret siden sidst - ellers
    ville hvert tastetryk koste et flow-kald."""
    return (
        f"With(\n"
        f"    {{ q: Trim({search_text_expr}) }},\n"
        f"    If(\n"
        f"        Len(q) < {MIN_SEARCH_LEN},\n"
        f"        Clear({target_collection});\n"
        f"        Set({last_search_var}, \"\");\n"
        f"        Set({msg_var}, \"Skriv mindst {MIN_SEARCH_LEN} tegn for at soege.\"),\n"
        f"\n"
        f"        If(\n"
        f"            q = {last_search_var},\n"
        f"            false,\n"
        f"            Set({msg_var}, \"Soeger efter \" & q & \" ...\");\n"
        f"            Set({last_search_var}, q);\n"
        f"            IfError(\n"
        f"                Set({_RAW}, {FLOW_NAME}.Run(q));\n"
        f"                If(\n"
        f"                    IsBlank({_RAW}) || IsBlank({_RAW}.{FLOW_OUTPUT}),\n"
        f"                    Clear({target_collection}),\n"
        f"                    {collect_results(target_collection)}\n"
        f"                );\n"
        f"                Set(\n"
        f"                    {msg_var},\n"
        f"                    If(\n"
        f"                        CountRows({target_collection}) = 0,\n"
        f"                        \"Ingen {label} fundet for \" & q & \".\",\n"
        f"                        Text(CountRows({target_collection})) & \" {label} fundet.\"\n"
        f"                    )\n"
        f"                ),\n"
        f"                Clear({target_collection});\n"
        f"                Set({last_search_var}, \"\");\n"
        f"                Set({msg_var}, \"Soegningen fejlede: \" & FirstError.Message)\n"
        f"            )\n"
        f"        )\n"
        f"    )\n"
        f")"
    )

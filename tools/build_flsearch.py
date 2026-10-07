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

SVARETS FORM (bekraeftet direkte i flowets definition, 2026-09-13)
-------------------------------------------------------------------
Handlingen "Respond to a Power App or flow" har eet outputfelt,
"functionallocationoutput" (schema.properties.functionallocationoutput,
title "FunctionalLocationOutput"). Feltets vaerdi er en JSON-STRENG
(ikke et allerede-parset objekt) med et array:

    [ { "functionKey": "SSV10 KAB10AP001",
        "description": "Ball bearing house, pump area",
        "maintainable": true,
        "level": "3" }, ... ]

maintainable siger, om der overhovedet kan vedligeholdes paa lokationen.
Den baeres med og markeres i UI'et - en VH-plan paa en ikke-vedligeholdbar
FL giver ikke mening i SAP.

FORUDSAETNING: flowet skal vaere tilfoejet appen som datakilde i Studio, OG
den tilfoejelse skal vaere GEMT (Ctrl+S / File > Save i Studio - blot at
tilfoeje flowet i Power Automate-panelet er ikke nok), FOER YAML'en
synkroniseres. Ellers fejler compile paa et ukendt navn.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- flow-kontrakt -----------------------------------------------------------
# Flowets Power Fx-navn er dets DISPLAY NAME, inklusive bindestregerne, ikke
# en "saneret" identifier. Fordi navnet indeholder bindestreger, skal det
# staa i lige anfoerselstegn i Power Fx: 'BioSap-Integration-FunctionalLocations'.
# Bekraeftet ved test 2026-09-13: "BioSapIntegrationFunctionalLocations" (uden
# bindestreger, uden anfoerselstegn) gav "'Run' is an unknown or unsupported
# function in namespace ...", mens denne form kompilerer rent.
FLOW_NAME = "'BioSap-Integration-FunctionalLocations'"
# Bekraeftet direkte i flowets "Respond to a Power App or flow"-handling
# (schema.properties) den 2026-09-13: outputtet hedder "functionallocationoutput",
# ikke "json". Se ogsaa Get-Bearer-Token/Call_FunctionalLocations_API-kaeden i
# flowet - "functionallocationoutput" er strengen med det JSON-array, som denne
# fil parser med ParseJSON().
FLOW_OUTPUT = "functionallocationoutput"
JSON_ARRAY_PATH = ""
JSON_MAINT_FIELD = "maintainable"
JSON_LEVEL_FIELD = "level"
JSON_CODE_FIELD = "functionKey"
JSON_DESC_FIELD = "description"

# Soegeknappen naegter at kalde flowet under dette antal tegn. Flowet svarer
# bredt - 819 traef for "SSV13 HFC10" - saa en kortere soegning er spild.
MIN_SEARCH_LEN = 7

# Over dette antal traef siger beskeden til, at der boer soeges smallere.
LONG_RESULT = 50

# Mellemvariablen, flowets svar lander i.
#
# HVORFOR DEN ER EN PARAMETER OG IKKE EN KONSTANT
# -----------------------------------------------
# Filen laa i TRE kopier - VH-plan, Equipment og Material - og kun den her
# ene linje skilte dem: VH-plan skrev varVhpFlRaw, de to andre varDomFlRaw.
# check_shared() i build_all.py kiggede aldrig paa build_flsearch.py, saa
# driften var usynlig. Da de tre kopier blev til een i tools/, fik VH-plan
# pludselig Equipment-appens variabelnavn.
#
# Navnet foelger appens egen konvention (varVhp* / varDom*), saa det hoerer
# hos KALDEREN - og det er derfor OBLIGATORISK. Her stod en standardvaerdi
# ("varDomFlRaw"), og en kalder, der glemte parameteren, fik stille og
# roligt en anden apps variabel: praecis den fejl, der er beskrevet ovenfor.


def _array_expr(raw_var):
    """Udtrykket der giver JSON-arrayet fra flow-svaret."""
    base = f"ParseJSON({raw_var}.{FLOW_OUTPUT})"
    if JSON_ARRAY_PATH:
        base = f"{base}.{JSON_ARRAY_PATH}"
    return f"Table({base})"


def collect_results(target_collection, *, raw_var):
    """ClearCollect af flow-svaret ind i en samling til comboboksen.

    Display er kode + beskrivelse i eet felt. Comboboksen soeger og viser paa
    netop det felt, saa brugeren kan skrive enten FL-koden eller et ord fra
    beskrivelsen i det SAMME felt, som valget sker i - der er ingen separat
    soegeboks og ingen separat dropdown."""
    return (
        f"ClearCollect(\n"
        f"    {target_collection},\n"
        f"    ForAll(\n"
        f"        {_array_expr(raw_var)} As R,\n"
        f"        {{\n"
        f"            Code: Text(R.Value.{JSON_CODE_FIELD}),\n"
        f"            Description: Text(R.Value.{JSON_DESC_FIELD}),\n"
        f"            Display: Text(R.Value.{JSON_CODE_FIELD}) & \" - \" & Text(R.Value.{JSON_DESC_FIELD}) &\n"
        f"                If(Boolean(R.Value.{JSON_MAINT_FIELD}), \"\", \"   (not maintainable)\"),\n"
        f"            Maintainable: Boolean(R.Value.{JSON_MAINT_FIELD}),\n"
        f"            Level: Text(R.Value.{JSON_LEVEL_FIELD})\n"
        f"        }}\n"
        f"    )\n"
        f")"
    )


def search_action(query_ctrl, target_collection, msg_var, *, raw_var,
                  label="Functional Locations",
                  busy_var=None, query_expr=None, last_var=None, on_start=None,
                  on_found=None, min_len=None):
    """Soegningen, som den ser ud bag en SOEGEKNAP.

    Hvem der kalder den: Search-knappen i FL-vaelgeren
    (tools/fl_picker.py). Soegningen koerer KUN der - naar brugeren
    filtrerer i svaret, sker det lokalt i comboboksen, uden nyt kald.

    busy_var: en variabel, der er true, MENS flowet koerer. Search-knappen
    viser en spinner saa laenge - uden den kunne brugeren ikke se, at et
    tryk paa Search overhovedet var registreret.
    Den saettes false igen ad BEGGE veje ud (svar og fejl), fordi IfError
    fanger fejlen og fortsaetter.

    query_expr: udtrykket, soegeteksten laeses af. Standard er feltets
    Text.

    last_var: faar soegeteksten, naar soegningen starter. FL-vaelgeren
    (fl_picker.py) bruger den til at vide, om brugeren filtrerer i det
    sidste svar eller skriver en ny soegning.

    on_start: koeres, naar soegningen starter - fx at rydde det valgte.

    on_found: koeres, naar soegningen har fundet mindst een raekke - fx at
    vaelge den foerste (issue #72).

    min_len: mindste antal tegn (trimmet) foer der soeges. Standard er
    MIN_SEARCH_LEN; VH-planens Item Editor kraever 8 (issue #144).

    GAMLE RESULTATER RYDDES, NAAR EN NY SOEGNING STARTER (issue #63)
    ----------------------------------------------------------------
    Ellers kunne man vaelge en raekke fra den forrige soegning, mens den
    nye koerte. Fejler soegningen, eller finder den intet, siger en kort
    Notify det - beskeden under feltet findes ikke i alle apps.
    """
    q_src = query_expr if query_expr else f"{query_ctrl}.Text"
    n_min = min_len or MIN_SEARCH_LEN
    busy_on = f"        Set({busy_var}, true);\n" if busy_var else ""
    busy_off = f";\n        Set({busy_var}, false)" if busy_var else ""
    return (
        f"With(\n"
        f"    {{ q: Upper(Trim({q_src})) }},\n"
        f"    If(\n"
        f"        Len(q) < {n_min},\n"
        f"        Notify(\n"
        f"            \"Type at least {n_min} characters before searching.\",\n"
        f"            NotificationType.Warning\n"
        f"        ),\n"
        f"\n"
        + busy_on
        + (f"        Set({last_var}, q);\n" if last_var else "")
        + f"        Clear({target_collection});\n"
        + (f"        {on_start};\n" if on_start else "")
        + f"        Set({msg_var}, \"Searching for \" & Upper(q) & \" ...\");\n"
        f"        IfError(\n"
        f"            Set({raw_var}, {FLOW_NAME}.Run(q));\n"
        f"            If(\n"
        f"                IsBlank({raw_var}) || IsBlank({raw_var}.{FLOW_OUTPUT}),\n"
        f"                Clear({target_collection}),\n"
        f"                {collect_results(target_collection, raw_var=raw_var)}\n"
        f"            );\n"
        f"            If(\n"
        f"                CountRows({target_collection}) = 0,\n"
        f"                Notify(\"No {label.lower()} found for \" & Upper(q) & \".\", NotificationType.Warning)"
        + (f",\n                    {on_found}\n" if on_found else "\n")
        + f"            );\n"
        f"            Set(\n"
        f"                {msg_var},\n"
        f"                With(\n"
        f"                    {{ n: CountRows({target_collection}) }},\n"
        f"                    If(\n"
        f"                        n = 0,\n"
        f"                        \"No {label} found for \" & Upper(q) & \".\",\n"
        f"                        Text(n) & \" {label} found for \" & Upper(q) & \". \" &\n"
        f"                            If(\n"
        f"                                n > {LONG_RESULT},\n"
        f"                                \"The list is long - type more characters to narrow it.\",\n"
        f"                                \"Select one from the list below.\"\n"
        f"                            )\n"
        f"                    )\n"
        f"                )\n"
        f"            ),\n"
        f"            Clear({target_collection});\n"
        f"            Set({msg_var}, \"Search failed: \" & FirstError.Message);\n"
        f"            Notify(\"The {label.lower()} search failed. Try again.\", NotificationType.Error)\n"
        f"        )"
        + busy_off + "\n"
        f"    )\n"
        f")"
    )

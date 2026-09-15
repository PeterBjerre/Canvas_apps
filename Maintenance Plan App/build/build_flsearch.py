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

# Flowet kaldes KUN naar soegeteksten er noejagtig dette antal tegn - ikke ved
# hvert tegn derover. Se timer_poll_action for hvorfor.
MIN_SEARCH_LEN = 7

_RAW = "varVhpFlRaw"


def _array_expr():
    """Udtrykket der giver JSON-arrayet fra flow-svaret."""
    base = f"ParseJSON({_RAW}.{FLOW_OUTPUT})"
    if JSON_ARRAY_PATH:
        base = f"{base}.{JSON_ARRAY_PATH}"
    return f"Table({base})"


def collect_results(target_collection):
    """ClearCollect af flow-svaret ind i en samling til comboboksen.

    Display er kode + beskrivelse i eet felt. Comboboksen soeger og viser paa
    netop det felt, saa brugeren kan skrive enten FL-koden eller et ord fra
    beskrivelsen i det SAMME felt, som valget sker i - der er ingen separat
    soegeboks og ingen separat dropdown."""
    return (
        f"ClearCollect(\n"
        f"    {target_collection},\n"
        f"    ForAll(\n"
        f"        {_array_expr()} As R,\n"
        f"        {{\n"
        f"            Code: Text(R.Value.{JSON_CODE_FIELD}),\n"
        f"            Description: Text(R.Value.{JSON_DESC_FIELD}),\n"
        f"            Display: Text(R.Value.{JSON_CODE_FIELD}) & \" - \" & Text(R.Value.{JSON_DESC_FIELD}) &\n"
        f"                If(Boolean(R.Value.{JSON_MAINT_FIELD}), \"\", \"   (ikke vedligeholdbar)\"),\n"
        f"            Maintainable: Boolean(R.Value.{JSON_MAINT_FIELD}),\n"
        f"            Level: Text(R.Value.{JSON_LEVEL_FIELD})\n"
        f"        }}\n"
        f"    )\n"
        f")"
    )


def timer_poll_action(query_expr, target_collection, last_search_var, msg_var,
                      label="Functional Locations"):
    """Soegningen, som den ser ud naar den drives af en Timer.

    query_expr er det udtryk, der skal soeges paa. For FL-feltet er det
    comboboksens egen SearchText; for objektlisten er det den valgte FL.

    HVORFOR TIMER OG IKKE OnChange
    ------------------------------
    En combobox har ingen "brugeren skrev noget"-haendelse. OnChange fyrer
    foerst, naar der VAELGES en raekke - men listen skal jo fyldes FOER der
    kan vaelges. Derfor poller en Timer (AutoStart, Repeat, Duration 500 ms)
    comboboksens SearchText. Det er samme moenster som Timer1/ComboBox1 i
    referenceappen, hvor det er bevist at virke.

    Timeren er usynlig. Det er dokumenteret understoettet: en Timer med
    AutoStart = true og Visible = false koerer alligevel.

    GENTAGELSESSPAERREN
    -------------------
    Soegningen udloeses ved HVER ny tekst paa mindst MIN_SEARCH_LEN tegn -
    ikke kun naar laengden er noejagtig MIN_SEARCH_LEN.

    Den foerste udgave brugte "noejagtig 7", ud fra at comboboksen selv kunne
    filtrere videre i det hentede resultat. Det var forkert paa to maader:

      1. En hurtig skribent naaede forbi 7 tegn mellem to timer-tik, og saa
         blev soegningen ALDRIG udloest.
      2. Skrev man videre efter 7 tegn, filtrerede comboboksen i resultatet
         for de 7 tegn. Returnerer flowet kun de foerste N traef, er der
         ingen af dem, der matcher 10 tegn - og saa stod dropdownen TOM,
         mens beskeden stadig sagde "50 Functional Locations fundet".
         Beskeden hoerte til en soegning, der ikke laengere blev vist.

    q <> last_search_var er nok til at holde antallet af kald nede: samme
    tekst soeges aldrig to gange, og timeren tikker kun hver 500 ms.

    Der ryddes bevidst IKKE selve target_collection, naar laengden afviger:
    naar brugeren vaelger en raekke, nulstiller comboboksen selv SearchText
    til "", og en oprydning af samlingen ville fjerne den netop valgte
    raekke fra Items og dermed smide valget vaek."""
    return (
        f"With(\n"
        f"    {{ q: Trim({query_expr}) }},\n"
        f"    If(\n"
        f"        Len(q) < {MIN_SEARCH_LEN},\n"
        f"        Set({last_search_var}, \"\"),\n"
        f"\n"
        f"        If(\n"
        f"            q <> {last_search_var},\n"
        f"            Set({last_search_var}, q);\n"
        f"            Set({msg_var}, \"Soeger efter \" & q & \" ...\");\n"
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
        f"                        Text(CountRows({target_collection})) & \" {label} fundet for \" & q &\n"
        f"                            \". Vaelg en i feltet.\"\n"
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


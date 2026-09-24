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
# hos KALDEREN. Nu er der ingen linje tilbage, der kan skille to apps ad.
DEFAULT_RAW = "varDomFlRaw"


def _array_expr(_RAW=DEFAULT_RAW):
    """Udtrykket der giver JSON-arrayet fra flow-svaret."""
    base = f"ParseJSON({_RAW}.{FLOW_OUTPUT})"
    if JSON_ARRAY_PATH:
        base = f"{base}.{JSON_ARRAY_PATH}"
    return f"Table({base})"


def collect_results(target_collection, raw_var=DEFAULT_RAW):
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


def search_action(query_ctrl, target_collection, msg_var,
                  label="Functional Locations", raw_var=DEFAULT_RAW):
    """Soegningen, som den ser ud bag en SOEGEKNAP.

    HVORFOR IKKE LAENGERE EN TIMER OG EN COMBOBOX
    ---------------------------------------------
    Foerste udgave lod en Timer polle Classic/ComboBox.SearchText og lod
    comboboksen selv filtrere resultatet. Det virkede ikke i praksis:
    flowet returnerede 819 raekker for "SSV13 HFC10", beskeden sagde det
    ogsaa - og dropdownen var alligevel TOM. Comboboksens indbyggede
    soegefiltrering viste ingen af de raekker, den havde faaet.

    Nu er der ingen skjult filtrering tilbage:

        et tekstfelt      brugeren skriver hvad der skal soeges paa
        en soegeknap      brugeren bestemmer HVORNAAR der soeges
        en dropdown       viser praecis det, samlingen indeholder

    Dropdownen har ingen egen soegning, saa der er ikke noget lag, der kan
    skjule raekker. Til gengaeld kan listen blive lang - derfor siger
    beskeden til, naar resultatet er stort nok til at brugeren boer soege
    smallere.
    """
    return (
        f"With(\n"
        f"    {{ q: Trim({query_ctrl}.Text) }},\n"
        f"    If(\n"
        f"        Len(q) < {MIN_SEARCH_LEN},\n"
        f"        Notify(\n"
        f"            \"Type at least {MIN_SEARCH_LEN} characters before searching.\",\n"
        f"            NotificationType.Warning\n"
        f"        ),\n"
        f"\n"
        f"        Set({msg_var}, \"Searching for \" & q & \" ...\");\n"
        f"        IfError(\n"
        f"            Set({raw_var}, {FLOW_NAME}.Run(q));\n"
        f"            If(\n"
        f"                IsBlank({raw_var}) || IsBlank({raw_var}.{FLOW_OUTPUT}),\n"
        f"                Clear({target_collection}),\n"
        f"                {collect_results(target_collection, raw_var)}\n"
        f"            );\n"
        f"            Set(\n"
        f"                {msg_var},\n"
        f"                With(\n"
        f"                    {{ n: CountRows({target_collection}) }},\n"
        f"                    If(\n"
        f"                        n = 0,\n"
        f"                        \"No {label} found for \" & q & \".\",\n"
        f"                        Text(n) & \" {label} fundet for \" & q & \". \" &\n"
        f"                            If(\n"
        f"                                n > {LONG_RESULT},\n"
        f"                                \"The list is long - type more characters to narrow it.\",\n"
        f"                                \"Select one from the list below.\"\n"
        f"                            )\n"
        f"                    )\n"
        f"                )\n"
        f"            ),\n"
        f"            Clear({target_collection});\n"
        f"            Set({msg_var}, \"Search failed: \" & FirstError.Message)\n"
        f"        )\n"
        f"    )\n"
        f")"
    )

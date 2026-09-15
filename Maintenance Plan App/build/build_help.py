# -*- coding: utf-8 -*-
"""
Al hjaelpetekst i appen. EEN fil.

Vejledningen fandtes i forvejen - men i to PowerPoints, som ingen har aabne,
mens de udfylder formularen. Teksten skal staa DER hvor feltet udfyldes.

TRE NIVEAUER
------------
    HINTS    een linje under feltet, altid synlig
    PANELS   3-8 linjer pr. sektion, foldet ud med et ? i overskriften
    kilde    naevnt nederst i panelet

Kilder: "Den gode VH-plan" (maj 2025) og "Planlaegning af en VH ordre"
(2026), sammenholdt med reglerne i BIO_SAP_Fields.xlsx. Se
docs/14-feltforklaringer.md.

DYNAMISKE HINTS
---------------
Hvor reglen afhaenger af noget, er hinten et Power Fx-udtryk og ikke en
konstant. "Paakraevet, fordi item 2 har activity type 110" er mere vaerd end
"udfyldes ved lovpligtige eftersyn" - den foerste fortaeller hvorfor feltet
lyser lige nu.
"""

# Items med lovpligtigt eftersyn. Bruges af flere hints og af valideringen.
STATUTORY_ITEMS = ("Filter(colVhpItems, "
                   "StartsWith(ActivityType, \"110\") || StartsWith(ActivityType, \"115\"))")
REVISION_ITEMS = "Filter(colVhpItems, !IsBlank(Revision))"


def _q(s):
    """Dansk tekst -> Power Fx-streng. Kun ASCII, som resten af builderne."""
    return '"' + s.replace('"', '""') + '"'


# ---------------------------------------------------------------------------
# NIVEAU 1: hints. Vaerdien er ET POWER FX-UDTRYK - ikke en raa streng.
# ---------------------------------------------------------------------------
HINTS = {
    # --- Plan Header ---
    "PlanType": _q("Strategiplan henter cyklus fra strategiens pakker."),

    "Strategy": ("If(varVhpPlan.PlanType = \"Strategy\", "
                 + _q("Pakkerne vises i Strategy Packages nedenfor.") + ", "
                 + _q("Kun relevant for strategiplaner.") + ")"),

    "Plant": _q("Vaerket bestemmer hvilke arbejdscentre og arbejdsplaner der kan vaelges."),

    "Status": _q("Ny, AEndre eller Slettes - hvad indmeldingen skal goere ved planen i SAP."),

    # Overskriften skal starte med vaerkets bogstavkode, saa planen kan findes
    # naar man ikke kan soege paa vaerk eller funktionsplads.
    "PlanText": ("If(\n"
                 "    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
                 "        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
                 "    " + _q("Boer starte med vaerkskoden ") + " & varVhpPlan.Plant & "
                 + _q(" - saa kan planen findes uden at soege paa vaerk.") + ",\n"
                 "    " + _q("Start med vaerkets bogstavkode. Teksten skal daekke alle opgaver planen kalder. Maks. 40 tegn.") + "\n"
                 ")"),

    "SortField": ("With(\n"
                  "    { n: CountRows(" + STATUTORY_ITEMS + ") },\n"
                  "    If(\n"
                  "        n > 0,\n"
                  "        " + _q("Paakraevet: ") + " & Text(n) & "
                  + _q(" item(s) har activity type 110 eller 115. Alle items i planen skal vaere samme lovpligtige eftersyn.") + ",\n"
                  "        " + _q("Bruges kun til lovpligtige eftersyn (activity type 110 og 115).") + "\n"
                  "    )\n"
                  ")"),

    "Cycle": _q("Hvor ofte planen kalder en ordre."),

    "Unit": _q("DAY, WK, MON eller YR - eller H for timetaeller."),

    "CallHorizon": ("With(\n"
                    "    { m: LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon) },\n"
                    "    If(\n"
                    "        IsBlank(m.Value),\n"
                    "        " + _q("Antal arbejdsdage ordren staar paa joblisten foer slutdatoen.") + ",\n"
                    "        Text(m.Days) & " + _q(" FCD, schedulering ") + " & Text(m.SchedPeriod) &\n"
                    "            " + _q(" aar. Sat automatisk ud fra cyklus.") + "\n"
                    "    )\n"
                    ")"),

    "SchedInd": _q("Time - key date kalder paa samme dato hvert aar. Vaelg den, hvis planen kalder primo januar."),

    # Revisionsopgaver kaldes 1/1 - ellers flytter kaldet sig og rammer
    # ikke revisionen.
    "FirstCall": ("If(\n"
                  "    CountRows(" + REVISION_ITEMS + ") > 0,\n"
                  "    " + _q("Laast til 01/01: et item har revisionsmaerke. Kun aaret kan vaelges.") + ",\n"
                  "    " + _q("Foerste kald. Vaelg dag, maaned og aar.") + "\n"
                  ")"),

    "StatutorySortField": _q("Udfyldes kun, hvis eftersynet har et eget lovpligtigt sorteringsfelt."),

    # --- Item Editor ---
    "ItemShortText": _q("Bliver VH-ordrens overskrift. Skriv hvad opgaven er - ikke hvad planen hedder. Maks. 40 tegn."),

    "FunctionalLocation": _q("Angiv saa detaljeret som muligt, helst komponentniveau. Her konteres omkostningen."),

    "ObjectList": _q("Skal starte med samme 2-bogstavsniveau som referenceobjektet."),

    "ActivityType": ("With(\n"
                     "    { a: LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType },\n"
                     "    If(\n"
                     "        StartsWith(a, \"110\") || StartsWith(a, \"115\"),\n"
                     "        " + _q("Lovpligtigt: der SKAL henvises til gaeldende lovgivning i langteksten, og arbejdscentret skal vaere *SUP.") + ",\n"
                     "        StartsWith(a, \"120\"),\n"
                     "        " + _q("Loebende opgave - maks. 1 aar. Prioritet bliver blaa.") + ",\n"
                     "        " + _q("101 forebyggende - 102 forudbestemt - 110 lovpligtigt - 115 myndighedsvilkaar - 120 loebende - 130 rengoering - 160 smoering.") + "\n"
                     "    )\n"
                     ")"),

    "MainWorkCenter": ("With(\n"
                       "    { a: LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType },\n"
                       "    If(\n"
                       "        StartsWith(a, \"110\") || StartsWith(a, \"115\"),\n"
                       "        " + _q("Bruges der eksterne leverandoerer, vaelg *SUP.") + "\n"
                       "    )\n"
                       ")"),

    "Revision": _q("REV betyder at opgaven loeses i revisionsperioden. Foerste kald laases saa til 01/01."),

    "OrstedResponsible": _q("Den ansvarlige. Udfyldt med dig som standard."),

    "Initials": _q("Initialer paa den ansvarlige, fx NIJUJ."),

    "ItemLongText": _q("Beskriv omfanget, og hvad der skal til for at udfoere opgaven sikkert. Det er det foerste udfoereren ser i ordren."),

    # --- Tasklist og operationer ---
    # Operationerne redigeres i et galleri, ikke i field_cell, saa denne hint
    # staar over tabellen og daekker hele linjen. Den er dynamisk: den peger
    # paa den regel der er broedt lige nu, og falder ellers tilbage paa
    # control key-reglen, som er den man oftest glemmer.
    "Operations": ("With(\n"
                   "    {\n"
                   "        ops: Filter(colVhpOperations, ItemId = varVhpActiveItemId),\n"
                   "        first: LookUp(Sort(Filter(colVhpOperations, ItemId = varVhpActiveItemId), Value(OperationNo)), true)\n"
                   "    },\n"
                   "    If(\n"
                   "        CountRows(ops) = 0, \"\",\n"
                   "        IsBlank(first.MainWorkCenter),\n"
                   "        \"Operation \" & first.OperationNo & \" skal baere det hovedansvarlige arbejdscenter.\",\n"
                   "        CountRows(Filter(ops, IsBlank(OperationShortText))) > 0,\n"
                   "        Text(CountRows(Filter(ops, IsBlank(OperationShortText)))) & \" operation(er) mangler short text.\",\n"
                   "        CountRows(Filter(ops, WorkHours <= 0)) > 0,\n"
                   "        \"Alle operationer skal time- og bemandingsestimeres - Work skal vaere over 0.\",\n"
                   "    )\n"
                   ")"),
}


# ---------------------------------------------------------------------------
# NIVEAU 2: paneler. (overskrift, broedtekst) pr. sektion.
# ---------------------------------------------------------------------------
PANELS = {
    "plan": [
        ("Overskriften",
         "Starter altid med lokationens bogstavkode (AVV, SKV, SSV ...), saa planen "
         "kan findes, naar man ikke kan soege paa vaerk eller funktionsplads."),
        ("Call horizon",
         "Antal ARBEJDSDAGE den genererede VH-ordre staar paa joblisten, foer basic "
         "finish naas. Saettes ud fra cyklussen. Revisionsopgaver har 65 FCD."),
        ("Scheduling period",
         "Hvor langt frem kaldene kan ses. Minimum 2 aar af hensyn til den "
         "oekonomiske simulering i BI-rapporten."),
        ("Sort field",
         "Bruges KUN ved lovpligtige eftersyn (activity type 110/115). Er der valgt "
         "Ladders, skal ALLE items i planen vaere lovpligtigt eftersyn af stiger."),
        ("Revision",
         "Opgaver der loeses til aarets revision maerkes REV og kaldes 1/1. "),
    ],
    "item": [
        ("Langteksten",
         "Det FOERSTE vedligeholdelsespersonalet ser i den genererede ordre. Beskriv "
         "omfanget. Er der krav om "
         "rengoering, lugemand, kran, stillads eller afspaerring, saa skriv det kort."),
        ("Referenceobjektet",
         "Der hvor omkostningen konteres. Angiv funktionspladsen paa "
         "komponentniveau. Er der objekter paa objektlisten, kan den vaere mindre "
         "detaljeret - men mindst 2-bogstavsniveau, fx SKV40 EB."),
        ("Objektlisten",
         "Cost center og business area skal vaere ens for alle funktionspladser paa "
         "listen. Gaelder dog ikke sikkerhedsventiler og roerstrenge. Ved lovpligtig "
         "besigtigelse af trykbaerende udstyr: EEN funktionsplads pr. item, "
         "objektlisten tom."),
        ("Aktivitetstyper",
         "101 forebyggende - 102 forudbestemt - 110 lovpligtigt eftersyn - "
         "115 myndighedsvilkaar - 120 loebende, maks. 1 aar - 130 rengoering - "
         "160 smoering. Bruges 110 eller 115 SKAL der henvises til gaeldende lovgivning."),
        ("Prioritet",
         "Foelger aktivitetsmatricen: roed ved 110/115 eller sikkerhedskritisk udstyr "
         "(SCEq), blaa ved 120, ellers gul."),
    ],
    "ops": [
        ("Del opgaven op, hvor der er ophold",
         "Stillads op og stillads ned er to operationer. Af-isolering og isolering er "
         "to. Ellers kan WOS-appen ikke vise forloebet rigtigt."),
        ("Kronologisk raekkefoelge",
         "Operationerne skal staa 0010, 0020, 0030 i den orden arbejdet udfoeres, saa "
         "det grafiske view i WOS afspejler opgaven."),
        ("Alle operationer time- og bemandingsestimeres",
         "Work er samlet antal mandetimer. No. er antal personer, 1 er standard. "
         "Duration udregner SAP selv."),
        ("Control keys",
         "ZB01 internt *SUP, taeller ikke med i schedulering - PM01 interne work "
         "centre - PM02 ekstern *LEV, der laves rekvisition - PM03 "
         "rammeaftaleleverandoer paa servicekatalog. Det hovedansvarlige "
         "arbejdscenter skal staa paa operation 0010."),
    ],
    "pkg": [
        ("Pakkerne hoerer til arbejdsplanen",
         "I SAP ejer strategien pakkerne, arbejdsplanen ejer allokeringen "
         "operation -> pakke, og vedligeholdsplanen peger paa begge."),
        ("Hierarki",
         "En hierarkisk strategi som 1-3-6-12 betyder, at den maanedlige opgave ogsaa "
         "skal laves ved kvartals- og aarsgennemgangen. En roterende strategi som "
         "aar 1-2-3 goer ikke - der skal hver pakke markeres for sig."),
        ("Hver operation skal have mindst een pakke",
         "En operation uden pakke bliver aldrig udfoert. En pakke uden operationer "
         "kalder en tom ordre."),
    ],
}

SOURCE_NOTE = ('Kilde: "Den gode VH-plan" (maj 2025) og "Planlaegning af en VH ordre" '
               "(2026). Spoerg SAPvedligehold@orsted.dk.")


def hint(key):
    """Power Fx-udtrykket for et felts hint. Ukendt noegle -> ingen hint."""
    return HINTS.get(key)

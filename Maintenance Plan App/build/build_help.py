# -*- coding: utf-8 -*-
"""
De hjaelpetekster, der ikke kan vaere tekst.

HVOR RESTEN AF DEM ER
---------------------
I SharePoint-listen MD_HelpText. 15 hints og 21 panelafsnit stod her og
kunne kun rettes af den, der kunne bygge appen; nu kan de rettes af dem,
der kender fagligheden. Se sharepoint/provision/Provision-HelpText.ps1.

    Kind = Hint     linjen under et felt. HelpKey er feltets navn.
    Kind = Panel    et afsnit i ?-panelet. HelpKey er sektionen.

En slettet raekke betyder INGEN tekst i appen - der falder ikke noget
tilbage paa en kopi her, for der ER ingen kopi. Det var et bevidst valg:
saa er det synligt, naar nogen har slettet noget.

HVAD DER STADIG STAAR HER, OG HVORFOR
-------------------------------------
De syv hints nedenfor er ikke tekst, men POWER FX. De fortaeller hvorfor
feltet lyser LIGE NU og saetter appens egne vaerdier ind:

    "Should start with the plant code " & varVhpPlan.Plant & " - ..."
    "Required: " & Text(n) & " item(s) have activity type 110 or 115 ..."

"Paakraevet, fordi item 2 har activity type 110" er mere vaerd end
"udfyldes ved lovpligtige eftersyn". Saadan en kan ikke vaere en raekke i
en liste.

tools/check_helptext.py naegter at bygge, hvis den samme noegle staar
BEGGE steder. To kilder til den samme tekst er praecis det, flytningen
skulle fjerne.

Kilder til indholdet: "Den gode VH-plan" (maj 2025) og "Planlaegning af en
VH ordre" (2026), sammenholdt med reglerne i BIO_SAP_Fields.xlsx. Se
docs/14-feltforklaringer.md.
"""

# Items med lovpligtigt eftersyn. Bruges af flere hints og af valideringen.
STATUTORY_ITEMS = ("Filter(colVhpItems, "
                   "StartsWith(ActivityType, \"110\") || StartsWith(ActivityType, \"115\"))")
REVISION_ITEMS = "Filter(colVhpItems, !IsBlank(Revision))"


def _q(s):
    """Dansk tekst -> Power Fx-streng. Kun ASCII, som resten af builderne."""
    return '"' + s.replace('"', '""') + '"'


# ---------------------------------------------------------------------------
# DE DYNAMISKE HINTS. Vaerdien er ET POWER FX-UDTRYK - ikke en raa streng.
# Staar en noegle her, maa den IKKE ogsaa staa i MD_HelpText.
# ---------------------------------------------------------------------------
HINTS = {
    "Strategy": ("If(varVhpPlan.PlanType = \"Strategy\", "
                 + _q("The packages are shown in Strategy Packages below.") + ", "
                 + _q("Only relevant for strategy plans.") + ")"),

    # Overskriften skal starte med vaerkets bogstavkode, saa planen kan findes
    # naar man ikke kan soege paa vaerk eller funktionsplads.
    "PlanText": ("If(\n"
                 "    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
                 "        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
                 "    " + _q("Should start with the plant code ") + " & varVhpPlan.Plant & "
                 + _q(" - so the plan can be found without searching by plant.") + ",\n"
                 "    " + _q("Start with the plant code. The text must cover every task the plan calls. Max 40 characters.") + "\n"
                 ")"),

    "SortField": ("With(\n"
                  "    { n: CountRows(" + STATUTORY_ITEMS + ") },\n"
                  "    If(\n"
                  "        n > 0,\n"
                  "        " + _q("Required: ") + " & Text(n) & "
                  + _q(" item(s) have activity type 110 or 115. All items in the plan must be the same statutory inspection.") + ",\n"
                  "        " + _q("Only used for statutory inspections (activity type 110 and 115).") + "\n"
                  "    )\n"
                  ")"),

    "CallHorizon": ("With(\n"
                    "    { m: LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon) },\n"
                    "    If(\n"
                    "        IsBlank(m.Value),\n"
                    "        " + _q("Working days the order stays on the job list before the finish date.") + ",\n"
                    "        Text(m.Days) & " + _q(" FCD, schedulering ") + " & Text(m.SchedPeriod) &\n"
                    "            " + _q(" years. Set automatically from the cycle.") + "\n"
                    "    )\n"
                    ")"),

    # Revisionsopgaver kaldes 1/1 - ellers flytter kaldet sig og rammer
    # ikke revisionen.
    "FirstCall": ("If(\n"
                  "    CountRows(" + REVISION_ITEMS + ") > 0,\n"
                  "    " + _q("Fixed to 01/01: an item is marked as outage work. Only the year can be chosen.") + ",\n"
                  "    " + _q("First call. Choose day, month and year.") + "\n"
                  ")"),

    "ActivityType": ("With(\n"
                     "    { a: LookUp(colVhpItems, ItemId = varVhpActiveItemId).ActivityType },\n"
                     "    If(\n"
                     "        StartsWith(a, \"110\") || StartsWith(a, \"115\"),\n"
                     "        " + _q("Statutory: the long text MUST reference the applicable legislation.") + ",\n"
                     "        StartsWith(a, \"120\"),\n"
                     "        " + _q("Running task - max 1 year. Priority becomes blue.") + ",\n"
                     "        " + _q("101 preventive - 102 predetermined - 110 statutory - 115 regulatory condition - 120 running - 130 cleaning - 160 lubrication.") + "\n"
                     "    )\n"
                     ")"),

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
                   "        \"Operation \" & first.OperationNo & \" must carry the main responsible work centre.\",\n"
                   "        CountRows(Filter(ops, IsBlank(OperationShortText))) > 0,\n"
                   "        Text(CountRows(Filter(ops, IsBlank(OperationShortText)))) & \" operation(s) are missing a short text.\",\n"
                   "        CountRows(Filter(ops, WorkHours <= 0)) > 0,\n"
                   "        \"Every operation needs a time and manning estimate - Work must be above 0.\"\n"
                   "    )\n"
                   ")"),
}


# Opslaget i listen. Findes noeglen ikke, giver LookUp blank, og Coalesce
# goer det til en tom streng - kontrollen staar der, men viser ingenting.
# Der er MED VILJE ingen fallback til koden.
LOOKUP = ('Coalesce(\n'
          '    LookUp(colVhpHelp, Key = %s && Kind = "Hint").Body,\n'
          '    ""\n'
          ')')


def hint(key):
    """Power Fx-udtrykket for et felts hint.

    Er noeglen dynamisk, kommer udtrykket herfra. Ellers slaas den op i
    MD_HelpText - ogsaa hvis ingen har skrevet den endnu. Det er hele
    pointen: en ny noegle kraever ikke en ny build, kun en ny raekke."""
    if key in HINTS:
        return HINTS[key]
    return LOOKUP % _q(key)


def panel(section):
    """Afsnittene i ?-panelet for en sektion, sorteret.

    Returnerer et Power Fx-udtryk, der giver en TABEL - panelet tegnes af
    et gallery, fordi antallet af afsnit ikke laengere kendes, naar appen
    bygges."""
    return ('Sort(\n'
            '    Filter(colVhpHelp, Key = %s && Kind = "Panel"),\n'
            '    Ord\n'
            ')') % _q(section)

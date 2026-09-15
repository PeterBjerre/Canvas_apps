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
    "PlanType": _q("A strategy plan takes its cycle from the strategy packages."),

    "Strategy": ("If(varVhpPlan.PlanType = \"Strategy\", "
                 + _q("The packages are shown in Strategy Packages below.") + ", "
                 + _q("Only relevant for strategy plans.") + ")"),

    "Plant": _q("The plant determines which work centres and task lists are available."),

    "Status": _q("New, Change or Delete - what this request should do to the plan in SAP."),

    # Overskriften skal starte med vaerkets bogstavkode, saa planen kan findes
    # naar man ikke kan soege paa vaerk eller funktionsplads.
    "PlanText": ("If(\n"
                 "    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
                 "        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
                 "    " + _q("Should start with the plant code ") + " & varVhpPlan.Plant & "
                 + _q(" - so the plan can be found without searching by plant.") + ",\n"
                 "    " + _q("Start with the plant code. The text must cover every task the plan calls. Maks. 40 tegn.") + "\n"
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

    "Cycle": _q("How often the plan calls an order."),

    "Unit": _q("DAY, WK, MON or YR - or H for a counter-based plan."),

    "CallHorizon": ("With(\n"
                    "    { m: LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon) },\n"
                    "    If(\n"
                    "        IsBlank(m.Value),\n"
                    "        " + _q("Working days the order stays on the job list before the finish date.") + ",\n"
                    "        Text(m.Days) & " + _q(" FCD, schedulering ") + " & Text(m.SchedPeriod) &\n"
                    "            " + _q(" years. Set automatically from the cycle.") + "\n"
                    "    )\n"
                    ")"),

    "SchedInd": _q("Time - key date calls on the same date every year. Use it when the plan calls in early January."),

    # Revisionsopgaver kaldes 1/1 - ellers flytter kaldet sig og rammer
    # ikke revisionen.
    "FirstCall": ("If(\n"
                  "    CountRows(" + REVISION_ITEMS + ") > 0,\n"
                  "    " + _q("Fixed to 01/01: an item is marked as outage work. Only the year can be chosen.") + ",\n"
                  "    " + _q("First call. Choose day, month and year.") + "\n"
                  ")"),

    "StatutorySortField": _q("Only fill this in if the inspection has its own statutory sort field."),

    # --- Item Editor ---
    "ItemShortText": _q("Becomes the heading of the maintenance order. Describe the task, not the plan. Max 40 characters."),

    "FunctionalLocation": _q("Be as specific as possible, ideally down to component level. This is where the cost is posted."),

    "ObjectList": _q("Must start at the same two-letter level as the reference object."),

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

    "MainWorkCenter": _q("If external suppliers are used, choose *SUP."),

    "Revision": _q("REV means the task is done during the outage. First call is then fixed to 01/01."),

    "OrstedResponsible": _q("The person responsible. Defaults to you."),

    "Initials": _q("Initials of the person responsible, e.g. NIJUJ."),

    "ItemLongText": _q("Describe the scope and what it takes to do the job safely. It is the first thing the technician sees in the order."),

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


# ---------------------------------------------------------------------------
# NIVEAU 2: paneler. (overskrift, broedtekst) pr. sektion.
# ---------------------------------------------------------------------------
PANELS = {
    "plan": [
        ("The plan text",
         "Always starts with the plant code (AVV, SKV, SSV ...), so the plan can be "
         "found when you cannot search by plant or functional location."),
        ("Call horizon",
         "The number of WORKING DAYS the generated order stays on the job list "
         "before basic finish is reached. Set from the cycle. Outage work uses "
         "65 FCD."),
        ("Scheduling period",
         "How far ahead the calls are visible. Minimum 2 years, because the cost "
         "simulation in the BI report depends on it."),
        ("Sort field",
         "Used ONLY for statutory inspections (activity type 110/115). If Ladders "
         "is selected, EVERY item in the plan must be a statutory ladder "
         "inspection."),
        ("Outage work",
         "Tasks carried out during the annual outage are marked REV and called on "
         "1/1."),
    ],
    "item": [
        ("The long text",
         "The FIRST thing the maintenance crew sees in the generated order. "
         "Describe the scope. If cleaning, a hole watch, a crane, scaffolding or "
         "barriers are needed, say so briefly."),
        ("The reference object",
         "Where the cost is posted. Give the functional location down to component "
         "level. If there are objects on the object list it can be less specific - "
         "but at least the two-letter level, e.g. SKV40 EB."),
        ("The object list",
         "Cost center and business area must be the same for every functional "
         "location on the list. This does not apply to safety valves and pipe "
         "runs. For statutory inspection of pressure equipment: ONE functional "
         "location per item, object list empty."),
        ("Activity types",
         "101 preventive - 102 predetermined - 110 statutory inspection - 115 "
         "regulatory condition - 120 running, max 1 year - 130 cleaning - 160 "
         "lubrication. If 110 or 115 is used, the applicable legislation MUST be "
         "referenced."),
        ("Priority",
         "Follows the activity matrix: red for 110/115 or safety critical "
         "equipment (SCEq), blue for 120, otherwise yellow."),
    ],
    "ops": [
        ("Split the job where there is a pause",
         "Scaffolding up and scaffolding down are two operations. Removing and "
         "refitting insulation are two. Otherwise the WOS app cannot show the "
         "sequence correctly."),
        ("Chronological order",
         "Operations must run 0010, 0020, 0030 in the order the work is carried "
         "out, so the graphical view in WOS reflects the job."),
        ("Every operation needs a time and manning estimate",
         "Work is the total number of man-hours. No. is the number of people, 1 is "
         "the default. SAP calculates Duration itself."),
        ("Control keys",
         "ZB01 internal *SUP, not counted in scheduling - PM01 internal work "
         "centres - PM02 external *LEV, a requisition is raised - PM03 framework "
         "agreement supplier on the service catalogue. The main responsible work "
         "centre must sit on operation 0010."),
    ],
    "pkg": [
        ("The packages belong to the task list",
         "In SAP the strategy owns the packages, the task list owns the operation "
         "to package allocation, and the maintenance plan points at both."),
        ("Hierarchy",
         "A hierarchical strategy such as 1-3-6-12 means the monthly job is also "
         "done at the quarterly and annual inspection. A rotating strategy such as "
         "year 1-2-3 does not - there each package must be ticked on its own."),
        ("Every operation needs at least one package",
         "An operation without a package is never carried out. A package without "
         "operations calls an empty order."),
    ],
}


SOURCE_NOTE = ('Source: "Den gode VH-plan" (May 2025) and "Planlaegning af en '
               'VH ordre" (2026). Ask SAPvedligehold@orsted.dk.')


def hint(key):
    """Power Fx-udtrykket for et felts hint. Ukendt noegle -> ingen hint."""
    return HINTS.get(key)

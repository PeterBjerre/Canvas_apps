# -*- coding: utf-8 -*-
"""
Hvor langt planen er - som NAVNGIVNE FORMLER i App.Formulas (issue #54).

Progressbaren (build_hero.py) og Submit-knappen laeser dem. De er rene
udtryk over varVhpPlan og samlingerne, saa Power Fx regner dem om, hver gang
data aendres eller gemmes - der er ingen knap, der skal trykkes, for at
status passer.

VALIDERINGEN ER FLYTTET HERTIL
------------------------------
Reglerne stod i Validate-knappen (Dispatch and Control), som SATTE
varVhpLastValidationErrors. Knappen og sektionen er fjernet; reglerne er de
samme og staar nu i VhpValidationErrors. Submit er graa, indtil den er tom.

Een forskel: reglerne ser kun paa de items, der ogsaa GEMMES
(VhpSaveableItems). Appen aabner med eet tomt item, og det skrives ikke i
SharePoint (build_save.SAVEABLE_ITEMS). Taltes det med, kunne en plan aldrig
blive klar til Submit, uden at brugeren slettede det.

TRINENE
-------
Et trin er GROENT, naar dets paakraevede felter er udfyldt OG gemt:

    Plan         gemt og laast (Save i Plan Header). Edit laaser op, og saa
                 er trinnet ikke faerdigt, foer det er gemt igen.
    Item         mindst eet item, og alle gemte items er valid. Usavede
                 aendringer i Item Editoren tjekkes paa skaermen
                 (build_hero.ITEM_DIRTY) - de kan ikke ses herfra.
    Task list    alle items har en tasklist.
    Operations   alle items har mindst een operation - og paa en
                 strategiplan har hver operation en pakke (S4).
    Save         planen staar i SharePoint, og intet er aendret siden:
                 VhpStateJson er den samme som ved sidste gemning.
"""

SAVEABLE = ("Filter(colVhpItems, !IsBlank(Trim(ShortText)) || "
            "!IsBlank(FunctionalLocation))")

# En strategi uden pakker i MD_StrategyPackage (IP11 er ikke indlaest endnu)
# har intet at allokere. Pakkereglen og trin 4 kraever derfor kun en pakke pr.
# operation, naar strategien HAR pakker - ellers kunne planen aldrig
# indsendes, mens pakkekortet sagde, at den godt kunne (build_strategy.py).
HAS_PKGS = ("!IsEmpty(Filter(colVhpStrategyPackages, "
            "StrategyKey = varVhpPlan.Strategy))")

# REGLERNE, PR. SEKTION (issue #123, #230). Hver regel staar under den
# sektion, den rettes i - saa sektionernes badge ikke behoever at laese
# beskedens begyndelse. Foer bar beskederne interne koder (S1, M1, R2 ...)
# og itemets SharePoint-ID ("Item 199"). Brugeren laeste "M1" som et item
# og kunne ikke finde item 199 nogen steder. Nu:
#
#   - ingen regelkoder i teksten,
#   - itemet hedder sit NUMMER i listen (Item 1, Item 2 ... - samme
#     raekkefoelge som Items-listen, Sort(colVhpItems, ItemId)) og dets
#     Item Short Text i parentes,
#   - operationsnummeret staar der stadig, og beskeden siger, hvilket felt
#     der skal udfyldes, og hvor.
#
# Alt laeses af de indlaeste samlinger (colVhpItems, colVhpOperations) -
# ingen datakald. Opslagene regnes kun for de raekker, der fejler.
# R3 er fjernet med vilje - se historikken i build_hero.py (git).


def join_lines(parts):
    """Power Fx-tekst: de ikke-tomme dele, een pr. linje (Char(10))."""
    rows = ", ".join("{ m: %s }" % p for p in parts)
    return f"Concat(Filter(Table({rows}), !IsBlank(m)), m, Char(10))"


def _nest(expr, pad="    "):
    """expr indrykket, naar den staar inde i et andet udtryk."""
    return expr.replace("\n", "\n" + pad)


IS_STRAT_PLAN = 'varVhpPlan.PlanType = "Strategy"'


def item_ref(item_id):
    """Power Fx-tekst: "Item <nr> (<Item Short Text>)" for itemet med
    ItemId = item_id. Nummeret er itemets plads i Items-listen (sorteret
    paa ItemId). Uden kort tekst kun "Item <nr>". item_id skal vaere et
    navn fra en With - ikke ItemId direkte, for inde i Filter(colVhpItems)
    er ItemId itemets egen kolonne."""
    return ("With(\n"
            f"    {{ ir: LookUp(colVhpItems, ItemId = {item_id}) }},\n"
            f"    \"Item \" & Text(CountRows(Filter(colVhpItems, ItemId <= {item_id}))) &\n"
            "        If(IsBlank(Trim(ir.ShortText)), \"\", \" (\" & Trim(ir.ShortText) & \")\")\n"
            ")")


def _per_row(table, msg, sep="Char(10)"):
    """Een besked pr. raekke i table. rid er raekkens ItemId, fanget FOER
    item_ref aabner sit eget Filter over colVhpItems."""
    return (f"Concat(\n    {_nest(table)},\n"
            f"    With(\n        {{ rid: ItemId }},\n        {_nest(msg, '        ')}\n    ),\n"
            f"    {sep}\n)")


REF = item_ref("rid")


def _items_list(table, msg):
    """Plan-regel, der udloeses af items: msg & listen over dem ("Item 1
    (...), Item 3"). Tom, naar intet item udloeser den."""
    return ("With(\n"
            f"    {{ l: {_nest(_per_row(table, REF, chr(34) + ', ' + chr(34)))} }},\n"
            f"    If(IsBlank(l), \"\", {msg} & l & \".\")\n"
            ")")


ITEM_RULE = _per_row(
    "Filter(\n"
    "    VhpSaveableItems,\n"
    "    IsBlank(ShortText) || IsBlank(MainWorkCenter) || IsBlank(ActivityType) || IsBlank(FunctionalLocation)\n"
    ")",
    "With(\n"
    "    {\n"
    "        f:\n"
    "            If(IsBlank(ShortText), \", Item Short Text\", \"\") &\n"
    "            If(IsBlank(MainWorkCenter), \", Main Work Center\", \"\") &\n"
    "            If(IsBlank(ActivityType), \", Maintenance Activity Type\", \"\") &\n"
    "            If(IsBlank(FunctionalLocation), \", Functional Location\", \"\")\n"
    "    },\n"
    f"    {_nest(REF)} &\n"
    "        \": fill in \" & Mid(f, 3) & \" in the Item Editor.\"\n"
    ")")

# (sektion, navn, udtryk) - navnet er kun til tests og laesning.
RULES = [
    ("Plan", "strategy",
     f"If(\n    {IS_STRAT_PLAN} && IsBlank(varVhpPlan.Strategy),\n"
     "    \"Choose a Maintenance Strategy in the Plan Header - a strategy plan needs one.\",\n"
     "    \"\"\n)"),
    ("Plan", "plant_prefix",
     "If(\n"
     "    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
     "        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
     "    \"Start the Plan Text in the Plan Header with the plant code \" & varVhpPlan.Plant &\n"
     "        \" - otherwise the plan cannot be found without searching by plant.\",\n"
     "    \"\"\n)"),
    ("Plan", "sort_field",
     "If(\n"
     "    IsBlank(varVhpPlan.SortField),\n"
     "    " + _nest(_items_list(
         "Filter(VhpSaveableItems, StartsWith(ActivityType, \"110\") || StartsWith(ActivityType, \"115\"))",
         "\"Choose a Sort Field in the Plan Header - it is required for activity type 110 or 115: \"")) + ",\n"
     "    \"\"\n)"),
    ("Plan", "first_call",
     "If(\n"
     "    varVhpPlan.FirstCallDay <> 1 || varVhpPlan.FirstCallMonth <> 1,\n"
     "    " + _nest(_items_list(
         "Filter(VhpSaveableItems, !IsBlank(Revision))",
         "\"Set First call to 01/01 (day 1, month 1) in the Plan Header - otherwise the outage work \" &\n"
         "        \"misses the outage. Marked as outage work (Revision): \"")) + ",\n"
     "    \"\"\n)"),
    ("Item", "item_fields", ITEM_RULE),
    ("Ops", "tasklist",
     f"If(\n    {IS_STRAT_PLAN},\n"
     "    " + _nest(_per_row(
         "Filter(VhpSaveableItems, IsBlank(TasklistKey))",
         REF + " &\n    \": choose a task list - the package allocation belongs to the task list.\"")) + ",\n"
     "    \"\"\n)"),
    ("Ops", "package",
     f"If(\n    {IS_STRAT_PLAN} && {HAS_PKGS},\n"
     "    " + _nest(_per_row(
         "Filter(colVhpOperations, Len(Coalesce(PackagesKey, \";\")) <= 1)",
         REF + " & \", operation \" & OperationNo &\n"
         "    \": choose a package - without one the operation is never carried out.\"")) + ",\n"
     "    \"\"\n)"),
    ("Ops", "empty_package",
     f"If(\n    {IS_STRAT_PLAN},\n"
     "    Concat(\n"
     "        Filter(\n"
     "            colVhpStrategyPackages As P,\n"
     "            P.StrategyKey = varVhpPlan.Strategy &&\n"
     "            CountRows(Filter(colVhpOperations, \";\" & Text(P.PackageNo) & \";\" in Coalesce(PackagesKey, \";\"))) = 0\n"
     "        ),\n"
     "        \"Package \" & ShortCode & \" (\" & Text(CycleLength) & \" \" & CycleUnit &\n"
     "            \"): allocate it to at least one operation - otherwise the plan calls an empty order.\",\n"
     "        Char(10)\n"
     "    ),\n"
     "    \"\"\n)"),
    ("Ops", "material_group",
     _per_row(
         "Filter(\n"
         "    colVhpOperations,\n"
         "    Upper(Trim(Coalesce(ControlKey, \"\"))) = \"PM02\" &&\n"
         "    IsBlank(Trim(Coalesce(MaterialGroup, \"\")))\n"
         ")",
         REF + " & \", operation \" & OperationNo &\n"
         "    \": fill in the material group - control key PM02 requires one.\"")),
]
SECTIONS = ("Plan", "Item", "Ops")


def _section_rules(section):
    """Sektionens regler, een linje pr. fejl - tom tekst, naar der ingen er."""
    pad = " " * 12
    rows = (",\n" + pad).join("{ m: %s }" % _nest(expr, pad)
                               for sec, _n, expr in RULES if sec == section)
    return ("Concat(\n    Filter(\n        Table(\n" + pad + rows +
            "\n        ),\n        !IsBlank(m)\n    ),\n    m, Char(10)\n)")


# Alle regler - tom = ingen fejl. Submit (VhpCanSubmit) kraever den tom.
VALIDATION = join_lines(["VhpPlanRuleErrors", "VhpItemRuleErrors", "VhpOpsRuleErrors"])


# HVAD DER MANGLER, PR. SEKTION (issue #220). Trinenes egne beskeder plus
# sektionens regler (VhpPlanRuleErrors osv.) - samme betingelser, som
# Submit, progressbaren og badgerne bruger. Ingen nye regler: hver linje
# er enten et trin, der ikke er faerdigt, eller en linje fra
# VhpValidationErrors. Usavede aendringer i Item Editoren laegges til paa
# skaermen (build_hero.ITEM_DIRTY).
IS_STRAT = 'varVhpPlan.PlanType = "Strategy"'
STEP_MISSING = {
    "Plan": [("!VhpStepPlanDone", '"Save the plan header."')],
    # Samme betingelse som foer (trin 2) - kun beskeden siger nu, hvilken
    # halvdel der mangler.
    "Item": [("!VhpStepItemDone",
              'If(IsEmpty(VhpSaveableItems), "Add at least one item.", '
              '"Save every item as valid in the Item Editor.")')],
    "Ops": [("!VhpStepTasklistDone", '"Choose a task list for every item."'),
            ("!VhpStepOpsDone",
             f'If({IS_STRAT}, "Give every item operations, each with a package.", '
             '"Give every item at least one operation.")')],
}
MISSING_NAMES = {"Plan": "VhpPlanMissing", "Item": "VhpItemMissing", "Ops": "VhpOpsMissing"}
RULE_NAMES = {"Plan": "VhpPlanRuleErrors", "Item": "VhpItemRuleErrors", "Ops": "VhpOpsRuleErrors"}


def _section_missing(section):
    parts = [f"If({cond}, {msg}, \"\")" for cond, msg in STEP_MISSING[section]]
    return join_lines(parts + [RULE_NAMES[section]])


def formulas():
    """(navn, udtryk, forklaring) - samme form som sp_config.named_formulas."""
    F = []

    def add(name, expr, why=None):
        F.append((name, expr, why))

    add("VhpSaveableItems", SAVEABLE,
        "De items, der gemmes: har en kort tekst eller en funktionsplads.")
    add("VhpValidationErrors", VALIDATION,
        "Reglerne fra den tidligere Validate-knap. Tom = ingen fejl.")
    add("VhpStepPlanDone", "varVhpPlanCommitted && varVhpPlanLocked",
        "Trin 1: planhovedet er gemt og laast.")
    add("VhpStepItemDone",
        "CountRows(VhpSaveableItems) > 0 && "
        "CountRows(Filter(VhpSaveableItems, Status <> \"valid\")) = 0",
        "Trin 2: alle items er gemt som valid.")
    add("VhpStepTasklistDone",
        "CountRows(VhpSaveableItems) > 0 && "
        "CountRows(Filter(VhpSaveableItems, IsBlank(TasklistKey))) = 0",
        "Trin 3: alle items har en tasklist.")
    add("VhpStepOpsDone",
        "CountRows(VhpSaveableItems) > 0 &&\n"
        "    CountRows(Filter(VhpSaveableItems, !(ItemId in colVhpOperations.ItemId))) = 0 &&\n"
        "    (varVhpPlan.PlanType <> \"Strategy\" || !(" + HAS_PKGS + ") || "
        "CountRows(Filter(colVhpOperations, Len(Coalesce(PackagesKey, \";\")) <= 1)) = 0)",
        "Trin 4: alle items har operationer - og paa en strategiplan med pakker "
        "en pakke pr. operation.")
    # SEKTIONERNES BADGE (issue #123): "Valid" kraever trinnet OG at ingen
    # regel peger paa sektionen. Naar Submit er aktiv, er alle tre sande.
    # Usavede aendringer i Item Editoren (build_hero.ITEM_DIRTY) kan kun
    # skaermen se - de laegges til paa skaermen.
    add("VhpPlanRuleErrors", _section_rules("Plan"),
        "Reglerne, der rettes i Plan Header.")
    add("VhpItemRuleErrors", _section_rules("Item"),
        "Reglerne, der rettes i Item Editoren.")
    add("VhpOpsRuleErrors", _section_rules("Ops"),
        "Reglerne, der rettes i Tasklist and Operations.")
    for sec, why in (("Plan", "Plan Header"), ("Item", "Items"), ("Ops", "Tasklist and Operations")):
        add(MISSING_NAMES[sec], _section_missing(sec),
            f"Det, der mangler i {why} (issue #220) - een linje pr. krav. Tom = intet.")
    add("VhpPlanValid", "VhpStepPlanDone && IsBlank(VhpPlanRuleErrors)",
        "Plan Header er gemt og opfylder sine regler.")
    add("VhpItemsValid", "VhpStepItemDone && IsBlank(VhpItemRuleErrors)",
        "Alle items er gemt som valid og opfylder deres regler.")
    add("VhpOpsValid", "VhpStepTasklistDone && VhpStepOpsDone && IsBlank(VhpOpsRuleErrors)",
        "Alle items har tasklist og operationer, og reglerne er opfyldt.")
    # Selected er afkrydsningen i tabellerne - den er ikke en aendring af
    # planen, og en markering maa ikke goere Save-trinnet graat.
    add("VhpStateJson",
        "JSON(\n"
        "    {\n"
        "        Plan: varVhpPlan,\n"
        "        Items: VhpSaveableItems,\n"
        "        Ops: DropColumns(colVhpOperations, Selected),\n"
        "        Objs: colVhpItemObjects,\n"
        "        Mats: DropColumns(colVhpMaterials, Selected)\n"
        "    }\n"
        ")",
        "Planen, som den ville blive gemt. Sammenlignes med varVhpSavedJson.")
    add("VhpStepSaveDone",
        "!IsBlank(varVhpPlanKey) && varVhpSavedJson = VhpStateJson",
        "Trin 5: planen staar i SharePoint, og intet er aendret siden.")
    # EFTER SUBMIT (issue #88): varVhpFlow er MaintenancePlans' Status og
    # ApprovalStage. Flowene flytter dem (docs/32-godkendelsesflow.md):
    #
    #   In Progress + System    systemgodkendelse pr. item
    #   In Progress + Cost      omkostningsgodkendelse
    #   In Progress + Quality   kvalitetsgodkendelse, hele planen
    #   Ready for creation in SAP + Done    Master Data opretter i SAP
    #   Published               oprettet i SAP
    #   Returned                tilbage hos rekvirenten - redigeres og
    #                           indsendes igen, saa den taeller som IKKE
    #                           indsendt.
    add("VhpSubmitted",
        'varVhpFlow.Status in ["In Progress", "Ready for creation in SAP", "Published"]',
        "Planen er indsendt og ligger i godkendelse eller SAP-oprettelse.")
    add("VhpApprovalDone",
        'varVhpFlow.Stage in ["Quality", "Done"] || '
        'varVhpFlow.Status in ["Ready for creation in SAP", "Published"]',
        "System- og omkostningsgodkendelsen er overstaaet.")
    add("VhpQualityDone",
        'varVhpFlow.Status in ["Ready for creation in SAP", "Published"]',
        "Kvalitetsgodkendelsen er overstaaet - planen venter paa SAP.")
    add("VhpInSap", 'varVhpFlow.Status = "Published"',
        "Planen er oprettet i SAP.")
    add("VhpCanSubmit",
        "!varVhpSaving && !VhpSubmitted && VhpStepPlanDone && VhpStepItemDone && VhpStepTasklistDone &&\n"
        "    VhpStepOpsDone && IsBlank(VhpValidationErrors)",
        "Submit er aktiv, naar trin 1-4 er faerdige, reglerne ingen fejl finder, "
        "og planen ikke allerede er indsendt.")
    return F

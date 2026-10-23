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
SharePoint (build_save.SAVEABLE_ITEMS, se SAVEABLE nedenfor). Taltes det med, kunne en plan aldrig
blive klar til Submit, uden at brugeren slettede det.

TRINENE
-------
Et trin er GROENT, naar dets paakraevede felter er udfyldt OG gemt:

    Plan         faerdigt og laast (Save i Plan header). Edit laaser op, og
                 saa er trinnet ikke faerdigt, foer der trykkes Save igen.
    Item         mindst eet item, og alle items har deres paakraevede
                 felter (ITEM_REQUIRED, issue #448). Item Editoren skriver
                 felterne i colVhpItems, naar de aendres - Save i editoren
                 er ikke et krav, og usavede aendringer (build_hero.
                 ITEM_DIRTY) er ikke en valideringsfejl.
    Task list    alle items har en tasklist.
    Operations   alle items har mindst een operation - og paa en
                 strategiplan har hver operation en pakke (S4).
    Save         planen staar i SharePoint, og intet er aendret siden:
                 VhpStateJson er den samme som ved sidste gemning.
"""

# ET ITEM GEMMES, SAA SNART BRUGEREN HAR SKREVET NOGET I DET (issue #566).
# Save draft gemmer kladden, som den staar - ogsaa et halvt udfyldt item,
# der kun har en aktivitetstype, et arbejdscenter, en lang tekst eller
# operationer. Foer talte et item foerst med, naar det havde en kort tekst
# eller en funktionsplads; alt andet blev stille sprunget over (og dets
# operationer med). Et item, der allerede staar i SharePoint (SpId > 0),
# taeller altid med - ellers slettede oprydningen (build_save trin 7) det,
# naar brugeren toemte kort tekst og funktionsplads.
#
# Det tomme item, appen aabner med (build_load.EMPTY_ITEM_FIELDS), har kun
# Initials (brugerens standard) og taeller ikke med. TasklistKey og
# ObjectList er med vilje ikke med: tasklisten saettes ogsaa af appen selv
# (build_load), og objektlisten foelger funktionspladsen.
#
# Gemningen (build_save.SAVEABLE_ITEMS) og reglerne nedenfor bruger SAMME
# definition, saa alt, der gemmes, ogsaa valideres foer Submit.
SAVEABLE = ("Filter(colVhpItems, !IsBlank(Trim(ShortText)) || "
            "!IsBlank(Trim(FunctionalLocation)) || !IsBlank(Trim(MainWorkCenter)) || "
            "!IsBlank(Trim(ActivityType)) || !IsBlank(Trim(LongText)) || "
            "Coalesce(SpId, 0) > 0 || ItemId in colVhpOperations.ItemId)")

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
    """Power Fx-tekst: "Item <nr> (<Item short text>)" for itemet med
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


# ITEMETS PAAKRAEVEDE FELTER (issue #448) - EEN liste, som reglen
# nedenfor, trin 2 (VhpStepItemDone) og itemets kort i Items-listen
# (build_items: "N to fix") alle bygges af. Foer talte kortet sine egne
# felter, trin 2 kraevede, at itemet var GEMT med Save (Status "valid"),
# og Submit ventede paa, at Item Editoren var gemt (ITEM_DIRTY). Kortet
# kunne derfor sige "4 to fix", mens felterne var udfyldt, og Submit blev
# staaende graa. Nu er det vaerdierne, der afgoer det: Item Editoren
# skriver hvert felt i colVhpItems, naar feltet aendres eller forlades
# (build_items.write_item), og reglerne laeser colVhpItems.
#
# Trim: et felt med kun mellemrum er tomt. IsBlank er sand for baade
# Blank() og "", saa en tom tekst og en tom kolonne er ens. Initials skal
# vaere fem tegn - det kraever Item Editorens Save, og feltet er markeret
# paakraevet (*).
#
# (navn i beskeden, betingelse for "mangler"; {r} er "ThisItem." eller "")
ITEM_REQUIRED = [
    ("Item short text", "IsBlank(Trim({r}ShortText))"),
    ("Main work center", "IsBlank(Trim({r}MainWorkCenter))"),
    ("Maintenance activity type", "IsBlank(Trim({r}ActivityType))"),
    ("Functional Location", "IsBlank(Trim({r}FunctionalLocation))"),
    ("Initials", "Len(Trim({r}Initials)) <> 5"),
]


def item_required(r=""):
    """[(navn, betingelse)] for itemets paakraevede felter; r er
    praefikset foran kolonnerne ("ThisItem." i et galleri)."""
    return [(n, c.format(r=r)) for n, c in ITEM_REQUIRED]


# Itemet mangler mindst eet paakraevet felt (raekkens egne kolonner).
ITEM_MISSING_ANY = " || ".join(c for _n, c in item_required())

# OPERATIONERNES REGLER (samme betingelser som RULES nedenfor), saa
# itemets kort kan sige, at dets operationer mangler noget. Kolonnerne er
# colVhpOperations'.
OP_NO_TEXT = "IsBlank(Trim(OperationShortText))"
OP_NO_MG = ('Upper(Trim(Coalesce(ControlKey, ""))) = "PM02" && '
            'IsBlank(Trim(Coalesce(MaterialGroup, "")))')
OP_NO_COST = 'Upper(Trim(Coalesce(ControlKey, ""))) = "PM02" && Coalesce(Cost, 0) <= 0'
OP_NO_PKG = 'Len(Coalesce(PackagesKey, ";")) <= 1'


# PLAN HEADERENS PLANT STYRER ALT, DER AFHAENGER AF VAERKET (issue #453).
# Foer laeste arbejdscentre, tasklister, FL-soegningen og reglerne den GEMTE
# varVhpPlan.Plant, saa et nyt valg i Plant-dropdownen foerst virkede efter
# Save i Plan header. Nu er VhpPlant det, der STAAR i dropdownen: Plant-
# dropdownens OnChange saetter varVhpLivePlant (build_plan_header), og den
# toemmes, naar planhovedet gemmes, nulstilles, eller en plan aabnes eller
# startes - saa gaelder den gemte vaerdi igen. Coalesce springer "" over.
# EEN navngiven formel, som filtre, standardvaerdier, regler og Save draft
# alle laeser - saa de aldrig kan vaere uenige om vaerket.
LIVE_PLANT_VAR = "varVhpLivePlant"
PLANT = "VhpPlant"
PLANT_FX = f"Coalesce({LIVE_PLANT_VAR}, varVhpPlan.Plant)"
# FL-koden starter med vaerket (SSV13 HFC10 hoerer til SSV).
PLANT_PREFIX = f"Upper(Left(Trim({PLANT}), 3))"


# VAERDIER FRA ET ANDET VAERK (issue #453) - MARKERES, SLETTES IKKE. Skifter
# Plant, beholder itemet sine vaerdier; de, der ikke hoerer til det nye
# vaerk, bliver en fejl paa itemet ("N to fix"), i Item Editoren og i
# reglerne, og Submit er blokeret, til de er rettet. Samme moenster som
# foer ved Save i Plan header ("de bliver roede ... i stedet for at blive
# slettet uden at nogen har bekraeftet det"). En tom vaerdi er ikke en
# konflikt - den er allerede et manglende felt (ITEM_REQUIRED).
#
# Opslagene er i de indlaeste samlinger (colVhpMainWorkCenters,
# colVhpTasklists) - ingen datakald, saa delegering er ikke i spil. As-
# navnene holder samlingens kolonner adskilt fra itemets.
#
# (navn, betingelse); {r} er "ThisItem." eller "", {p} er vaerket.
ITEM_PLANT_CONFLICTS = [
    ("Main work center",
     "!IsBlank(Trim({r}MainWorkCenter)) && !IsBlank({p}) && "
     "IsBlank(LookUp(colVhpMainWorkCenters As W, Upper(W.Plant) = Upper({p}) && "
     "W.Value = Trim({r}MainWorkCenter)).Value)"),
    ("Functional Location",
     "!IsBlank(Trim({r}FunctionalLocation)) && !IsBlank({p}) && "
     "Upper(Left(Trim({r}FunctionalLocation), 3)) <> Upper(Left(Trim({p}), 3))"),
]
TASKLIST_PLANT_CONFLICT = (
    "!IsBlank(Trim({r}TasklistKey)) && !IsBlank({p}) && "
    "IsBlank(LookUp(colVhpTasklists As TL, Upper(TL.Plant) = Upper({p}) && "
    "TL.Key = {r}TasklistKey).Key)")


def item_plant_conflicts(r="", p=PLANT):
    """[(navn, betingelse)] for itemets felter fra et andet vaerk end p."""
    return [(n, c.format(r=r, p=p)) for n, c in ITEM_PLANT_CONFLICTS]


def tasklist_plant_conflict(r="", p=PLANT):
    """Itemets tasklist hoerer til et andet vaerk end p."""
    return TASKLIST_PLANT_CONFLICT.format(r=r, p=p)


def any_plant_conflict(r="", p=PLANT):
    """Itemet har mindst een vaerdi fra et andet vaerk end p."""
    return " || ".join(f"({c})" for c in [c for _n, c in item_plant_conflicts(r, p)]
                       + [tasklist_plant_conflict(r, p)])


# ITEMETS BLOKERINGER (issue #448; flyttet hertil fra build_items i issue
# #530). Hver raekke er een ting, der holder Submit tilbage for itemet: de
# paakraevede felter, vaerdier fra et andet vaerk (issue #453), en tasklist,
# mindst een operation og operationernes egne regler. Alt laeses af
# samlingerne - ingen datakald.
_OP_PROBLEM = (f"{OP_NO_TEXT} || ({OP_NO_MG}) || ({OP_NO_COST}) || "
               f"(pk && {OP_NO_PKG})")


def _blocker_rows(row):
    return [(n, c) for n, c in item_required(row)] + [
        (f"{n} (other plant)", c) for n, c in item_plant_conflicts(row)] + [
        ("Task list", f"IsBlank(Trim({row}TasklistKey))"),
        ("Task list (other plant)", tasklist_plant_conflict(row)),
        ("Operations", "IsEmpty(ops)"),
        ("Operation details", f"!IsEmpty(Filter(ops, {_OP_PROBLEM}))"),
    ]


def item_blockers(row):
    """Itemets blokeringer som tabel { n, m } - row er praefikset paa
    itemets kolonner ("ThisItem." paa kortet, "ar." for det aktive item)."""
    return (
        "With(\n"
        "    {\n"
        f"        ops: Filter(colVhpOperations, ItemId = {row}ItemId),\n"
        f"        pk: IfError({IS_STRAT_PLAN}, false) && {HAS_PKGS}\n"
        "    },\n"
        "    Filter(\n"
        "        Table(\n"
        + ",\n".join(f'            {{ n: "{n}", m: {c} }}' for n, c in _blocker_rows(row)) + "\n"
        "        ),\n"
        "        m\n"
        "    )\n"
        ")")


# ISSUE #530: det item, Item Editoren viser, er gyldigt - samme betingelse
# som fluebenet paa dets kort i Items-listen. Uden aktivt item er raekken
# blank, felterne mangler, og den er falsk.
ACTIVE_ITEM_VALID = "VhpActiveItemValid"
ACTIVE_ITEM_VALID_FX = ("With({ ar: LookUp(colVhpItems, ItemId = varVhpActiveItemId) }, IsEmpty(\n"
                        + "    " + _nest(item_blockers("ar.")) + "\n))")


ITEM_RULE = _per_row(
    "Filter(\n"
    "    VhpSaveableItems,\n"
    f"    {ITEM_MISSING_ANY}\n"
    ")",
    "With(\n"
    "    {\n"
    "        f:\n"
    + " &\n".join(f'            If({c}, ", {n}", "")' for n, c in item_required()) + "\n"
    "    },\n"
    f"    {_nest(REF)} &\n"
    "        \": fill in \" & Mid(f, 3) & \" in the item editor.\"\n"
    ")")

# Felter fra et andet vaerk end Plan Headers Plant (issue #453) - een linje
# pr. item, med de felter, der skal rettes.
ITEM_PLANT_RULE = _per_row(
    "Filter(\n"
    "    VhpSaveableItems,\n"
    f"    {' || '.join(f'({c})' for _n, c in item_plant_conflicts())}\n"
    ")",
    "With(\n"
    "    {\n"
    "        f:\n"
    + " &\n".join(f'            If({c}, ", {n}", "")' for n, c in item_plant_conflicts()) + "\n"
    "    },\n"
    f"    {_nest(REF)} &\n"
    f"        \": \" & Mid(f, 3) & \" does not belong to plant \" & {PLANT} &\n"
    "        \" - choose one for that plant in the item editor.\"\n"
    ")")
TASKLIST_PLANT_RULE = _per_row(
    f"Filter(VhpSaveableItems, {tasklist_plant_conflict()})",
    REF + f" &\n    \": the task list \" & TasklistKey & \" belongs to another plant - choose the task list for \" & {PLANT} & \".\"")

# (sektion, navn, udtryk) - navnet er kun til tests og laesning.
RULES = [
    ("Plan", "strategy",
     f"If(\n    {IS_STRAT_PLAN} && IsBlank(varVhpPlan.Strategy),\n"
     "    \"Choose a Maintenance strategy in the Plan header - a strategy plan needs one.\",\n"
     "    \"\"\n)"),
    ("Plan", "plant_prefix",
     "If(\n"
     "    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&\n"
     "        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),\n"
     "    \"Start the Plan text in the Plan header with the plant code \" & varVhpPlan.Plant &\n"
     "        \" - otherwise the plan cannot be found without searching by plant.\",\n"
     "    \"\"\n)"),
    ("Plan", "sort_field",
     "If(\n"
     "    IsBlank(varVhpPlan.SortField),\n"
     "    " + _nest(_items_list(
         "Filter(VhpSaveableItems, StartsWith(ActivityType, \"110\") || StartsWith(ActivityType, \"115\"))",
         "\"Choose a Sort field in the Plan header - it is required for activity type 110 or 115: \"")) + ",\n"
     "    \"\"\n)"),
    ("Plan", "first_call",
     "If(\n"
     "    varVhpPlan.FirstCallDay <> 1 || varVhpPlan.FirstCallMonth <> 1,\n"
     "    " + _nest(_items_list(
         "Filter(VhpSaveableItems, !IsBlank(Revision))",
         "\"Set First call to January 1 (yyyy-01-01) in the plan header - otherwise the outage work \" &\n"
         "        \"misses the outage. Marked as outage work (Revision): \"")) + ",\n"
     "    \"\"\n)"),
    ("Item", "item_fields", ITEM_RULE),
    ("Item", "item_plant", ITEM_PLANT_RULE),
    ("Ops", "tasklist",
     f"If(\n    {IS_STRAT_PLAN},\n"
     "    " + _nest(_per_row(
         "Filter(VhpSaveableItems, IsBlank(TasklistKey))",
         REF + " &\n    \": choose a task list - the package allocation belongs to the task list.\"")) + ",\n"
     "    \"\"\n)"),
    ("Ops", "tasklist_plant", TASKLIST_PLANT_RULE),
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
    # OPERATIONENS KORTE TEKST (R2-009). SAP-ordrekontrakten kraever den
    # (schema/vhplan-sap-order.schema.json: shortText, minLength 1), men en
    # manuel operation starter tom. Kun operationer paa items, der gemmes.
    ("Ops", "op_text",
     _per_row(
         "Filter(\n"
         "    colVhpOperations,\n"
         "    ItemId in VhpSaveableItems.ItemId && IsBlank(Trim(OperationShortText))\n"
         ")",
         REF + " & \", operation \" & OperationNo &\n"
         "    \": fill in the operation short text - SAP requires one.\"")),
    ("Ops", "material_group",
     _per_row(
         "Filter(\n"
         "    colVhpOperations,\n"
         "    Upper(Trim(Coalesce(ControlKey, \"\"))) = \"PM02\" &&\n"
         "    IsBlank(Trim(Coalesce(MaterialGroup, \"\")))\n"
         ")",
         REF + " & \", operation \" & OperationNo &\n"
         "    \": fill in the material group - control key PM02 requires one.\"")),
    # PM02-BELOEBET (Peter 2026-10-16): en ny PM02-linje stod med 0, og 0
    # er et tal, saa intet holdt Submit tilbage. Beloebet skal vaere
    # stoerre end 0 - det er rekvisitionens pris.
    ("Ops", "pm02_cost",
     _per_row(
         "Filter(\n"
         "    colVhpOperations,\n"
         "    Upper(Trim(Coalesce(ControlKey, \"\"))) = \"PM02\" &&\n"
         "    Coalesce(Cost, 0) <= 0\n"
         ")",
         REF + " & \", operation \" & OperationNo &\n"
         "    \": fill in the cost - control key PM02 requires an amount above 0.\"")),
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
    "Plan": [("!VhpStepPlanDone", '"Press Save in the plan header."')],
    # Samme betingelse som foer (trin 2) - kun beskeden siger nu, hvilken
    # halvdel der mangler.
    # Issue #448: kun "intet item". Et item, der mangler et felt, staar
    # allerede som sin egen linje fra reglen (VhpItemRuleErrors) - Save i
    # Item Editoren er ikke laengere et krav for Submit.
    "Item": [("IsEmpty(VhpSaveableItems)", '"Add at least one item."')],
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

    add(PLANT, PLANT_FX,
        "Vaerket fra Plan Header, som det STAAR i dropdownen - ogsaa foer Save "
        "(issue #453). Filtre, standardvaerdier, regler og Save draft laeser den.")
    add("VhpSaveableItems", SAVEABLE,
        "De items, der gemmes: brugeren har skrevet noget i dem, de har "
        "operationer, eller de staar allerede i SharePoint (issue #566).")
    add("VhpValidationErrors", VALIDATION,
        "Reglerne fra den tidligere Validate-knap. Tom = ingen fejl.")
    add("VhpStepPlanDone", "varVhpPlanCommitted && varVhpPlanLocked",
        "Trin 1: planhovedet er gemt og laast.")
    add("VhpStepItemDone",
        "CountRows(VhpSaveableItems) > 0 && "
        f"IsEmpty(Filter(VhpSaveableItems, {ITEM_MISSING_ANY}))",
        "Trin 2: mindst eet item, og alle items har deres paakraevede felter "
        "(issue #448 - vaerdierne, ikke om itemet er gemt med Save).")
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
        "Reglerne, der rettes i Plan header.")
    add("VhpItemRuleErrors", _section_rules("Item"),
        "Reglerne, der rettes i Item Editoren.")
    add("VhpOpsRuleErrors", _section_rules("Ops"),
        "Reglerne, der rettes i Task list and operations.")
    for sec, why in (("Plan", "Plan header"), ("Item", "Items"), ("Ops", "Task list and operations")):
        add(MISSING_NAMES[sec], _section_missing(sec),
            f"Det, der mangler i {why} (issue #220) - een linje pr. krav. Tom = intet.")
    add("VhpPlanValid", "VhpStepPlanDone && IsBlank(VhpPlanRuleErrors)",
        "Plan header er gemt og opfylder sine regler.")
    add("VhpItemsValid", "VhpStepItemDone && IsBlank(VhpItemRuleErrors)",
        "Alle items er gemt som valid og opfylder deres regler.")
    add(ACTIVE_ITEM_VALID, ACTIVE_ITEM_VALID_FX,
        "Det aktive item har ingen blokeringer (issue #530) - fluebenet i Item-sektionen.")
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

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
# har intet at allokere. S4 og trin 4 kraever derfor kun en pakke pr.
# operation, naar strategien HAR pakker - ellers kunne planen aldrig
# indsendes, mens pakkekortet sagde, at den godt kunne (build_strategy.py).
HAS_PKGS = ("!IsEmpty(Filter(colVhpStrategyPackages, "
            "StrategyKey = varVhpPlan.Strategy))")

VALIDATION = """With(
    { isStrat: varVhpPlan.PlanType = "Strategy", hasPkgs: """ + HAS_PKGS + """ },
    With(
        {
            itemErr:
                Concat(
                    Filter(
                        VhpSaveableItems,
                        IsBlank(ShortText) || IsBlank(MainWorkCenter) || IsBlank(ActivityType) || IsBlank(FunctionalLocation)
                    ),
                    With(
                        {
                            f:
                                If(IsBlank(ShortText), ", short text", "") &
                                If(IsBlank(MainWorkCenter), ", main work center", "") &
                                If(IsBlank(ActivityType), ", activity type", "") &
                                If(IsBlank(FunctionalLocation), ", functional location", "")
                        },
                        "Item " & Text(ItemId) & " (" & Coalesce(ShortText, "no short text") & "): add " & Mid(f, 3) & "."
                    ),
                    Char(10)
                ),
            s1:
                If(isStrat && IsBlank(varVhpPlan.Strategy),
                    "S1: A strategy must be chosen on a strategy plan.", ""),
            s3:
                If(isStrat,
                    Concat(
                        Filter(VhpSaveableItems, IsBlank(TasklistKey)),
                        "S3: Item " & Text(ItemId) & " has no task list - the package allocation belongs to the task list.",
                        Char(10)
                    ), ""),
            s4:
                If(isStrat && hasPkgs,
                    Concat(
                        Filter(colVhpOperations, Len(Coalesce(PackagesKey, ";")) <= 1),
                        "S4: Item " & Text(ItemId) & " operation " & OperationNo &
                        " has no package and would never be carried out.",
                        Char(10)
                    ), ""),
            s5:
                If(isStrat,
                    Concat(
                        Filter(
                            colVhpStrategyPackages As P,
                            P.StrategyKey = varVhpPlan.Strategy &&
                            CountRows(Filter(colVhpOperations, ";" & Text(P.PackageNo) & ";" in Coalesce(PackagesKey, ";"))) = 0
                        ),
                        "S5: Package " & ShortCode & " (" & Text(CycleLength) & " " & CycleUnit &
                        ") has no operations - the plan would call an empty order.",
                        Char(10)
                    ), ""),
            m1:
                Concat(
                    Filter(colVhpOperations,
                        Upper(Trim(Coalesce(ControlKey, ""))) = "PM02" &&
                        IsBlank(Trim(Coalesce(MaterialGroup, "")))),
                    "M1: Item " & Text(ItemId) & " operation " & OperationNo &
                    " is PM02 and needs a material group.",
                    Char(10)
                ),
            r1:
                If(
                    !IsBlank(varVhpPlan.Plant) && !IsBlank(varVhpPlan.PlanText) &&
                        !StartsWith(Upper(varVhpPlan.PlanText), Upper(varVhpPlan.Plant)),
                    "R1: Plan Text should start with the plant code " & varVhpPlan.Plant &
                        " - otherwise the plan cannot be found without searching by plant.", ""),
            r2:
                With(
                    { n: CountRows(Filter(VhpSaveableItems, StartsWith(ActivityType, "110") || StartsWith(ActivityType, "115"))) },
                    If(
                        n > 0 && IsBlank(varVhpPlan.SortField),
                        "R2: Sort Field is required: " & Text(n) &
                            " item(s) have activity type 110 or 115.", "")),
            r4:
                With(
                    { n: CountRows(Filter(VhpSaveableItems, !IsBlank(Revision))) },
                    If(
                        n > 0 && (varVhpPlan.FirstCallDay <> 1 || varVhpPlan.FirstCallMonth <> 1),
                        "R4: " & Text(n) & " item(s) are marked as outage work. " &
                            "First call must be 01/01, otherwise the task misses the outage.", ""))
        },
        Concat(
            Filter(
                Table(
                    { t: itemErr }, { t: s1 }, { t: s3 }, { t: s4 }, { t: s5 },
                    { t: m1 }, { t: r1 }, { t: r2 }, { t: r4 }
                ),
                !IsBlank(t)
            ),
            t, Char(10)
        )
    )
)"""
# R3 er fjernet med vilje - se historikken i build_hero.py (git).

# HVILKEN SEKTION EN REGEL HOERER TIL (issue #123). Sektionernes badge
# skifter til "Valid", naar trinnet er faerdigt OG ingen af reglerne ovenfor
# peger paa sektionen. Reglerne er de samme - de sorteres kun efter
# beskedens begyndelse, saa der ikke opstaar en validering ved siden af
# VhpValidationErrors. R2 og R4 rettes i Plan Header (Sort Field og First
# Call), selv om det er items, der udloeser dem. tests/test_checks.py tjekker,
# at hver regel i VALIDATION har en sektion.
RULE_SECTIONS = {
    "Plan": ("S1:", "R1:", "R2:", "R4:"),
    "Item": ("Item ",),
    "Ops": ("S3:", "S4:", "S5:", "M1:"),
}


def _section_rules(section):
    """De linjer i VhpValidationErrors, der hoerer til sektionen - tom tekst,
    naar der ingen er."""
    cond = " || ".join(f'StartsWith(Value, "{p}")' for p in RULE_SECTIONS[section])
    return f"Concat(Filter(Split(VhpValidationErrors, Char(10)), {cond}), Value, Char(10))"


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


def join_lines(parts):
    """Power Fx-tekst: de ikke-tomme dele, een pr. linje (Char(10))."""
    rows = ", ".join("{ m: %s }" % p for p in parts)
    return f"Concat(Filter(Table({rows}), !IsBlank(m)), m, Char(10))"


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

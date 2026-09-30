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
                    "Item " & Text(ItemId) & " (" & Coalesce(ShortText, "no short text") & "): missing required fields.",
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
                            "First call must be 01/01, otherwise the task misses the outage.", "")),
            r5:
                With(
                    { m: LookUp(colVhpCallHorizonOptions, Value = varVhpPlan.CallHorizon) },
                    If(
                        !IsBlank(varVhpPlan.CallHorizon) && m.SchedPeriod < 2,
                        "R5: Scheduling period must be at least 2 years because of " &
                            "the cost simulation in the BI report.", ""))
        },
        Concat(
            Filter(
                Table(
                    { t: itemErr }, { t: s1 }, { t: s3 }, { t: s4 }, { t: s5 },
                    { t: r1 }, { t: r2 }, { t: r4 }, { t: r5 }
                ),
                !IsBlank(t)
            ),
            t, Char(10)
        )
    )
)"""
# R3 er fjernet med vilje - se historikken i build_hero.py (git).


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
    add("VhpCanSubmit",
        "!varVhpSaving && VhpStepPlanDone && VhpStepItemDone && VhpStepTasklistDone &&\n"
        "    VhpStepOpsDone && IsBlank(VhpValidationErrors)",
        "Submit er aktiv, naar trin 1-4 er faerdige, og reglerne ingen fejl finder.")
    return F

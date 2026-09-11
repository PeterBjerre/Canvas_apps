// =====================================================================
// 01 – Named formulas, opstart og navigation
// Indsættes i App.Formulas (named formulas) og App.OnStart (kun adfærd).
// =====================================================================

// ---------------------------------------------------------------------
// App.Formulas – deklarative, dovent evaluerede. Koster intet ved opstart.
//
// BEGRÆNSNING: named formulas må IKKE referere variabler sat med Set()
// eller UpdateContext(), og må ikke indeholde adfærdsfunktioner
// (Collect, Patch, Notify, Navigate). Alt hvad der afhænger af brugerens
// valg ligger derfor i collections, ikke i named formulas.
// ---------------------------------------------------------------------

nfStrategies =
    Sort(Filter(MD_Strategy, IsActive = true), SortOrder);

nfPlannerGroups =
    Sort(Filter(MD_ValueHelp, Domain = "PLANNERGROUP", IsActive = true), SortOrder);

nfOrderTypes =
    Sort(Filter(MD_ValueHelp, Domain = "ORDERTYPE", IsActive = true), SortOrder);

nfControlKeys =
    Sort(Filter(MD_ValueHelp, Domain = "CONTROLKEY", IsActive = true), SortOrder);

nfCycleUnits =
    Sort(Filter(MD_ValueHelp, Domain = "CYCLEUNIT", IsActive = true), SortOrder);

// Bemærk: Domain og IsActive er indekserede, så alle ovenstående er
// delegerbare. Sort() på et ikke-indekseret talfelt er det ikke, men
// listerne er små (< 500), så det er uden betydning.

// Matrix-layout. Defineres ét sted, så overskriftsrækken og datarækkerne
// altid flugter.
nfMatrixColWidth = 56;
nfMatrixRowLabelWidth = 320;

// Trin-definition. Bruges af cmpWizardHeader til at tegne stepperen.
// Skærmen kan IKKE ligge i tabellen: Navigate() tager en skærmreference,
// ikke en tekst, og en skærmreference kan ikke gemmes i en datakolonne.
// Selve navigationen sker derfor med en Switch nederst i filen.
nfSteps = Table(
    { Step: 1, Key: "Header",   Caption: "Hoveddata"       },
    { Step: 2, Key: "Cycle",    Caption: "Cyklus/strategi" },
    { Step: 3, Key: "Items",    Caption: "Positioner"      },
    { Step: 4, Key: "TaskList", Caption: "Arbejdsplan"     },
    { Step: 5, Key: "Matrix",   Caption: "Pakkematrix"     },
    { Step: 6, Key: "Params",   Caption: "Parametre"       },
    { Step: 7, Key: "Summary",  Caption: "Resumé"          }
);


// ---------------------------------------------------------------------
// App.OnStart – kun det, der SKAL ske ved opstart.
// ---------------------------------------------------------------------
Set(gblUser, User());
Set(gblIsPlanner,
    // Planlæggerrollen styres af medlemskab af en SharePoint-gruppe, som
    // et flow spejler ned i MD_ValueHelp (Domain = "ROLE_PLANNER").
    !IsBlank(LookUp(MD_ValueHelp,
        Domain = "ROLE_PLANNER" && Lower(Title) = Lower(gblUser.Email)))
);
Set(gblStep, 1);
Set(gblDirty, false);


// ---------------------------------------------------------------------
// Ny anmodning – nulstiller al tilstand. Kaldes fra scrHome.
// ---------------------------------------------------------------------
Set(gblRequest,
    {
        SpId:              Blank(),
        RequestGuid:       GUID(),           // idempotensnøgle – sættes ÉN gang
        Title:             "",
        Status:            "Kladde",
        PlanType:          "Strategy",
        PlanDescription:   "",
        PlanCategory:      "PM",
        PlanningPlant:     Blank(),
        StrategyKey:       Blank(),
        SingleCycleLength: Blank(),
        SingleCycleUnit:   Blank(),
        CycleStartDate:    Today(),
        CallHorizonPct:    Blank(),
        SchedPeriod:       Blank(),
        SchedPeriodUnit:   Blank(),
        Justification:     ""
    }
);
Clear(colItems); Clear(colItemObjects); Clear(colTaskLists);
Clear(colOperations); Clear(colPackages); Clear(colDeleted);
Set(gblStep, 1);
Navigate(scrStep1Header);


// ---------------------------------------------------------------------
// Indlæs pakker, når strategien vælges (drpStrategy.OnChange)
// ---------------------------------------------------------------------
Set(gblRequest, Patch(gblRequest, { StrategyKey: drpStrategy.Selected.Title }));

ClearCollect(colPackages,
    Sort(
        Filter(MD_StrategyPackage,
            StrategyKey = drpStrategy.Selected.Title,   // delegerbart: tekst + indeks
            IsActive = true
        ),
        PackageNo
    )
);

// Default planlægningsparametre fra strategien. Overskriver KUN felter,
// brugeren ikke selv har rørt – derfor Coalesce mod eksisterende værdi.
Set(gblRequest,
    Patch(gblRequest,
        {
            SchedIndicator:      drpStrategy.Selected.SchedIndicator,
            CallHorizonPct:      Coalesce(gblRequest.CallHorizonPct,      drpStrategy.Selected.CallHorizonPct),
            SchedPeriod:         Coalesce(gblRequest.SchedPeriod,         drpStrategy.Selected.SchedPeriod),
            SchedPeriodUnit:     Coalesce(gblRequest.SchedPeriodUnit,     drpStrategy.Selected.SchedPeriodUnit),
            ShiftFactorLatePct:  Coalesce(gblRequest.ShiftFactorLatePct,  drpStrategy.Selected.ShiftFactorLatePct),
            ShiftFactorEarlyPct: Coalesce(gblRequest.ShiftFactorEarlyPct, drpStrategy.Selected.ShiftFactorEarlyPct),
            ToleranceLatePct:    Coalesce(gblRequest.ToleranceLatePct,    drpStrategy.Selected.ToleranceLatePct),
            ToleranceEarlyPct:   Coalesce(gblRequest.ToleranceEarlyPct,   drpStrategy.Selected.ToleranceEarlyPct),
            FactoryCalendar:     Coalesce(gblRequest.FactoryCalendar,     drpStrategy.Selected.FactoryCalendar)
        }
    )
);

// Skift af strategi ugyldiggør matricen, fordi pakkenumrene kan betyde
// noget andet. Nulstil den bevidst frem for at efterlade skrald.
If(!IsBlank(gblPrevStrategyKey) && gblPrevStrategyKey <> drpStrategy.Selected.Title,
    UpdateIf(colOperations, true, { PackagesKey: ";", IsDirty: true });
    Notify("Strategien er ændret – pakkematricen er nulstillet.", NotificationType.Warning)
);
Set(gblPrevStrategyKey, drpStrategy.Selected.Title);


// ---------------------------------------------------------------------
// Navigation. Trin 5 (matrix) springes over, når den ikke er relevant.
// Ét sted, så reglen ikke divergerer mellem Næste og Tilbage.
// ---------------------------------------------------------------------

// Skal matricen vises?
// (Kan ikke være en named formula, da den afhænger af collections/variabler.)
// Læg den i en skjult label lblNeedsMatrix.Text eller gentag udtrykket.
//   gblRequest.PlanType = "Strategy"
//   && CountRows(Filter(colTaskLists, TaskListMode = "New")) > 0

// btnNext.OnSelect
With(
    { needsMatrix:
        gblRequest.PlanType = "Strategy"
        && CountRows(Filter(colTaskLists, TaskListMode = "New")) > 0
    },
    With({ target: If(gblStep + 1 = 5 && !needsMatrix, 6, gblStep + 1) },
        Set(gblStep, target);
        Navigate(
            Switch(target,
                1, scrStep1Header, 2, scrStep2Cycle,  3, scrStep3Items,
                4, scrStep4TaskList, 5, scrStep5Matrix, 6, scrStep6Params,
                scrStep7Summary
            ),
            ScreenTransition.None   // None = ingen animationsforsinkelse i en wizard
        )
    )
);

// btnBack.OnSelect – samme mønster med gblStep - 1 og 4 som fallback-mål.

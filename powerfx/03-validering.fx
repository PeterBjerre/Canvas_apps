// =====================================================================
// 03 – Validering
//
// Reglerne bygges som ÉN tabel af meddelelser. Det giver:
//   - en samlet liste på resuméskærmen, hvor hver linje kan navigere til
//     det trin, der skal rettes
//   - én sandhed at gen-implementere i submit-flowet (appen kan omgås,
//     fx via et delt link til listen, så serverside-validering er ikke
//     valgfri)
//
// Severity: "Fejl" blokerer submit. "Advarsel" skal kvitteres.
// =====================================================================

// Kaldes fra scrStep7Summary.OnVisible og fra btnSubmit.OnSelect.
ClearCollect( colValidation,

    // ---------- Hoveddata (trin 1) ----------
    If(IsBlank(gblRequest.PlanDescription),
        { Sev: "Fejl", Code: "H1", Step: 1,
          Msg: "Planbeskrivelse mangler." }),

    If(Len(gblRequest.PlanDescription) > 40,
        { Sev: "Fejl", Code: "H2", Step: 1,
          Msg: "Planbeskrivelse er " & Len(gblRequest.PlanDescription) &
               " tegn. SAP tillader maks. 40." }),

    If(IsBlank(gblRequest.PlanningPlant),
        { Sev: "Fejl", Code: "H3", Step: 1, Msg: "Planlægningsværk mangler." }),

    // ---------- Single cycle (trin 2) ----------
    If(gblRequest.PlanType = "SingleCycle" &&
       (IsBlank(gblRequest.SingleCycleLength) || gblRequest.SingleCycleLength <= 0),
        { Sev: "Fejl", Code: "C1", Step: 2, Msg: "Cykluslængde skal være større end 0." }),

    If(gblRequest.PlanType = "SingleCycle" && IsBlank(gblRequest.SingleCycleUnit),
        { Sev: "Fejl", Code: "C2", Step: 2, Msg: "Cyklusenhed mangler." }),

    // ---------- Strategi (trin 2) – regel S1/S2 ----------
    If(gblRequest.PlanType = "Strategy" && IsBlank(gblRequest.StrategyKey),
        { Sev: "Fejl", Code: "S1", Step: 2, Msg: "Strategi skal vælges på en strategiplan." }),

    If(gblRequest.PlanType = "Strategy" && CountRows(colPackages) < 2,
        { Sev: "Fejl", Code: "S2", Step: 2,
          Msg: "Strategien " & gblRequest.StrategyKey & " har færre end 2 aktive pakker. " &
               "Brug en single cycle-plan i stedet." }),

    If(IsBlank(gblRequest.CycleStartDate),
        { Sev: "Fejl", Code: "S7a", Step: 2, Msg: "Cyklusstart mangler." }),

    If(!IsBlank(gblRequest.CycleStartDate) && gblRequest.CycleStartDate < Today(),
        { Sev: "Advarsel", Code: "S7b", Step: 2,
          Msg: "Cyklusstart ligger i fortiden. SAP vil kalde forfaldne pakker med det samme." }),

    // ---------- Positioner (trin 3) ----------
    If(CountRows(colItems) = 0,
        { Sev: "Fejl", Code: "I1", Step: 3, Msg: "Der skal være mindst én position." }),

    ForAll(
        Filter(colItems,
            ObjectType <> "NoObject" &&
            IsBlank(FunctionalLocation) && IsBlank(EquipmentNo) && IsBlank(AssemblyNo)),
        { Sev: "Fejl", Code: "I2", Step: 3,
          Msg: "Position " & ItemNo & ": teknisk objekt mangler." }
    ),

    ForAll(
        Filter(colItems, IsBlank(PlannerGroupCode) || IsBlank(OrderType) || IsBlank(MainWorkCenter)),
        { Sev: "Fejl", Code: "I3", Step: 3,
          Msg: "Position " & ItemNo & ": planlæggergruppe, ordretype og hovedarbejdscenter er obligatoriske." }
    ),

    // ---------- Arbejdsplan (trin 4) – regel S3 ----------
    ForAll(
        Filter(colTaskLists, TaskListMode = "New" && StrategyKey <> gblRequest.StrategyKey),
        { Sev: "Fejl", Code: "S3", Step: 4,
          Msg: "Arbejdsplan """ & Title & """ har strategi " & StrategyKey &
               ", men planen har " & gblRequest.StrategyKey & ". De skal være ens." }
    ),

    ForAll(
        Filter(colItems, TaskListMode = "Existing" && (IsBlank(TaskListGroup) || IsBlank(TaskListCounter))),
        { Sev: "Fejl", Code: "T1", Step: 4,
          Msg: "Position " & ItemNo & ": gruppe og tællernummer skal udfyldes for en eksisterende arbejdsplan." }
    ),

    ForAll(
        Filter(colTaskLists, TaskListMode = "New" &&
            CountRows(Filter(colOperations, TaskListId = ThisRecord.TempId)) = 0),
        { Sev: "Fejl", Code: "T2", Step: 4,
          Msg: "Arbejdsplan """ & Title & """ har ingen operationer." }
    ),

    // ---------- Pakkematrix (trin 5) ----------

    // S4 – operation uden pakke. Ville betyde en operation, SAP aldrig kalder.
    If(gblRequest.PlanType = "Strategy",
        ForAll(
            Filter(colOperations, Len(PackagesKey) <= 1),
            { Sev: "Fejl", Code: "S4", Step: 5,
              Msg: "Operation " & OperationNo & " """ & Title &
                   """ er ikke tildelt nogen pakke og ville aldrig blive udført." }
        )
    ),

    // S5 – pakke uden operationer. Lovligt i SAP, men næsten altid en fejl.
    If(gblRequest.PlanType = "Strategy",
        ForAll(
            Filter(colPackages As P,
                CountRows(Filter(colOperations, ";" & Text(P.PackageNo) & ";" in PackagesKey)) = 0),
            { Sev: "Advarsel", Code: "S5", Step: 5,
              Msg: "Pakke " & P.ShortCode & " (" & P.CycleLength & " " & P.CycleUnit &
                   ") indeholder ingen operationer. Planen vil kalde en tom ordre." }
        )
    ),

    // S6 – enhedskonsistens mellem strategiens pakker og planlægningsindikatoren
    If(gblRequest.PlanType = "Strategy" && gblRequest.SchedIndicator = "PERFORMANCE" &&
       CountRows(Filter(colPackages, CycleUnit in ["DAY","WK","MON","YR"])) > 0,
        { Sev: "Fejl", Code: "S6", Step: 2,
          Msg: "Strategien er tællerbaseret, men indeholder tidsbaserede pakker." }),

    // ---------- Parametre (trin 6) ----------
    If(!IsBlank(gblRequest.CallHorizonPct) &&
       (gblRequest.CallHorizonPct < 0 || gblRequest.CallHorizonPct > 100),
        { Sev: "Fejl", Code: "P1", Step: 6, Msg: "Kaldshorisont skal være mellem 0 og 100 %." }),

    If(IsBlank(gblRequest.SchedPeriod) || gblRequest.SchedPeriod <= 0,
        { Sev: "Advarsel", Code: "P2", Step: 6,
          Msg: "Planlægningsperiode er ikke sat. SAP bruger strategiens standard." })
);

// Bemærk formmønsteret: hvert led er enten en If(), der giver Blank() når
// reglen er opfyldt, eller en ForAll() over de fejlende rækker. ClearCollect
// ignorerer Blank() og fletter ForAll-resultatet ind. Derfor kan hele
// regelsættet stå som én erklærende liste uden imperativ opbygning.


// ---------------------------------------------------------------------
// Afledte værdier til UI
// ---------------------------------------------------------------------
// lblErrorCount.Text
CountRows(Filter(colValidation, Sev = "Fejl"))

// btnSubmit.DisplayMode
If( CountRows(Filter(colValidation, Sev = "Fejl")) = 0
    && (CountRows(Filter(colValidation, Sev = "Advarsel")) = 0 || chkAckWarnings.Value),
    DisplayMode.Edit, DisplayMode.Disabled
)

// galValidation.OnSelect – hop til det trin, fejlen hører til.
// Navigate() kræver en skærmreference, ikke et skærmnavn som tekst, så
// opslaget kan ikke gå gennem nfSteps. Derfor en Switch – det ene sted i
// appen, hvor skærmene nævnes eksplicit (se også btnNext i 01-app-formulas.fx).
Set(gblStep, ThisItem.Step);
Navigate(
    Switch(ThisItem.Step,
        1, scrStep1Header, 2, scrStep2Cycle,   3, scrStep3Items,
        4, scrStep4TaskList, 5, scrStep5Matrix, 6, scrStep6Params,
        scrStep7Summary
    )
)

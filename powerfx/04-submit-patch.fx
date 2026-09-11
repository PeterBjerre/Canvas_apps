// =====================================================================
// 04 – Gem kladde og submit
//
// SharePoint har ingen transaktioner. Designet håndterer det ved at gøre
// hvert gem GENOPTAGELIGT frem for atomart:
//   - Status sættes ALTID til sidst. Fejler noget undervejs, står
//     anmodningen stadig som Kladde og kan gemmes igen.
//   - Hver collection-række bærer TempId (klientnøgle) og SpId
//     (SharePoint-ID). Er SpId tom, er rækken ny.
//   - Kun rækker med IsDirty skrives.
// =====================================================================


// ---------------------------------------------------------------------
// btnSaveDraft.OnSelect
// ---------------------------------------------------------------------
Clear(colSaveErrors);

// --- 1. Hovedet. Skal ligge først, fordi børnene skal bruge SpId. -----
IfError(
    Set(gblSavedRequest,
        Patch( VHP_Request,
            If(IsBlank(gblRequest.SpId), Defaults(VHP_Request),
               LookUp(VHP_Request, ID = gblRequest.SpId)),
            {
                RequestGuid:         gblRequest.RequestGuid,
                Status:              "Kladde",
                PlanType:            gblRequest.PlanType,
                PlanDescription:     gblRequest.PlanDescription,
                PlanCategory:        gblRequest.PlanCategory,
                PlanningPlant:       gblRequest.PlanningPlant,
                StrategyKey:         gblRequest.StrategyKey,
                SingleCycleLength:   gblRequest.SingleCycleLength,
                SingleCycleUnit:     gblRequest.SingleCycleUnit,
                SchedIndicator:      gblRequest.SchedIndicator,
                CycleStartDate:      gblRequest.CycleStartDate,
                CallHorizonPct:      gblRequest.CallHorizonPct,
                SchedPeriod:         gblRequest.SchedPeriod,
                SchedPeriodUnit:     gblRequest.SchedPeriodUnit,
                ShiftFactorLatePct:  gblRequest.ShiftFactorLatePct,
                ShiftFactorEarlyPct: gblRequest.ShiftFactorEarlyPct,
                ToleranceLatePct:    gblRequest.ToleranceLatePct,
                ToleranceEarlyPct:   gblRequest.ToleranceEarlyPct,
                CycleModFactor:      gblRequest.CycleModFactor,
                CompletionRequired:  gblRequest.CompletionRequired,
                FactoryCalendar:     gblRequest.FactoryCalendar,
                Justification:       gblRequest.Justification,
                // PlanSortField bærer sporbarheden tilbage til SAP.
                PlanSortField:       Left(gblRequest.RequestGuid, 8)
            }
        )
    ),
    Collect(colSaveErrors, { Where: "Hoved", Msg: FirstError.Message })
);

// Anmodningsnummer sættes i anden omgang, fordi det bruger det tildelte ID.
// Alternativet – en tællerliste – skaber en race, så snart to brugere
// opretter samtidig.
If( !IsBlank(gblSavedRequest) && IsBlank(gblSavedRequest.Title),
    Patch(VHP_Request, gblSavedRequest,
        { Title: "VHP-" & Text(Year(Now()), "0000") & "-" & Text(gblSavedRequest.ID, "00000") })
);
Set(gblRequest, Patch(gblRequest,
    { SpId: gblSavedRequest.ID, Title: gblSavedRequest.Title }));


// --- 2. Arbejdsplaner (før operationer, som refererer dem) ------------
ForAll( Filter(colTaskLists, IsDirty) As TL,
    IfError(
        With( { saved: Patch( VHP_TaskList,
                    If(IsBlank(TL.SpId), Defaults(VHP_TaskList),
                       LookUp(VHP_TaskList, ID = TL.SpId)),
                    { Title:            TL.Title,
                      RequestId:        gblRequest.SpId,
                      TaskListType:     TL.TaskListType,
                      StrategyKey:      TL.StrategyKey,
                      Plant:            TL.Plant,
                      UsageCode:        TL.UsageCode,
                      PlannerGroupCode: TL.PlannerGroupCode,
                      WorkCenter:       TL.WorkCenter,
                      SystemCondition:  TL.SystemCondition } ) },
            // Skriv SpId tilbage, så næste gem bliver en opdatering
            UpdateIf(colTaskLists, TempId = TL.TempId, { SpId: saved.ID, IsDirty: false })
        ),
        Collect(colSaveErrors, { Where: "Arbejdsplan " & TL.Title, Msg: FirstError.Message })
    )
);

// --- 3. Normalisér matricen FØR operationerne skrives -----------------
//     (se afsnittet "Normalisering" i 02-pakkematrix.fx)

// --- 4. Operationer --------------------------------------------------
ForAll( Filter(colOperations, IsDirty) As OP,
    IfError(
        With( { saved: Patch( VHP_Operation,
                    If(IsBlank(OP.SpId), Defaults(VHP_Operation),
                       LookUp(VHP_Operation, ID = OP.SpId)),
                    { Title:           OP.Title,
                      RequestId:       gblRequest.SpId,
                      TaskListId:      LookUp(colTaskLists, TempId = OP.TaskListTempId).SpId,
                      OperationNo:     OP.OperationNo,
                      LongText:        OP.LongText,
                      WorkCenter:      OP.WorkCenter,
                      ControlKey:      OP.ControlKey,
                      Plant:           OP.Plant,
                      Work:            OP.Work,
                      WorkUnit:        OP.WorkUnit,
                      NumberOfPeople:  OP.NumberOfPeople,
                      Duration:        OP.Duration,
                      DurationUnit:    OP.DurationUnit,
                      PackagesKey:     OP.PackagesKey,
                      PackagesDisplay: OP.PackagesDisplay,
                      SortOrder:       OP.SortOrder } ) },
            UpdateIf(colOperations, TempId = OP.TempId, { SpId: saved.ID, IsDirty: false })
        ),
        Collect(colSaveErrors, { Where: "Operation " & OP.OperationNo, Msg: FirstError.Message })
    )
);

// --- 5. Positioner og objektliste: samme mønster ----------------------

// --- 6. Slettede rækker ----------------------------------------------
ForAll( Filter(colDeleted, ListName = "VHP_Operation") As D,
    IfError( Remove(VHP_Operation, LookUp(VHP_Operation, ID = D.SpId)),
             Collect(colSaveErrors, { Where: "Sletning", Msg: FirstError.Message }) )
);
// ... tilsvarende for de øvrige lister. Ryd colDeleted ved succes.

// --- 7. Én samlet tilbagemelding -------------------------------------
If( CountRows(colSaveErrors) = 0,
    Set(gblDirty, false);
    Notify("Kladde gemt som " & gblRequest.Title, NotificationType.Success),
    Notify(CountRows(colSaveErrors) & " rækker kunne ikke gemmes. Prøv igen – " &
           "det gemte er bevaret.", NotificationType.Error)
);
// Aldrig én Notify pr. række. 24 pop-ups er ikke en fejlmeddelelse.


// =====================================================================
// btnSubmit.OnSelect
// =====================================================================

// 1. Valider (se 03-validering.fx). Stop ved fejl.
// 2. Normalisér matricen.
// 3. Gem kladde (hele blokken ovenfor).
// 4. Byg payload-snapshot og sæt status.

Set(gblPayload,
    JSON(
        {
            schemaVersion: "1.0",
            requestGuid:   gblRequest.RequestGuid,
            requestNo:     gblRequest.Title,
            submittedBy:   gblUser.Email,
            submittedOn:   Text(Now(), DateTimeFormat.UTC),
            plan: {
                planType:       gblRequest.PlanType,
                planCategory:   gblRequest.PlanCategory,
                description:    gblRequest.PlanDescription,
                planningPlant:  gblRequest.PlanningPlant,
                strategyKey:    gblRequest.StrategyKey,
                cycleStartDate: Text(gblRequest.CycleStartDate, "yyyy-mm-dd"),
                singleCycle:    If(gblRequest.PlanType = "SingleCycle",
                                   { length: gblRequest.SingleCycleLength,
                                     unit:   gblRequest.SingleCycleUnit }),
                scheduling: {
                    schedIndicator:      gblRequest.SchedIndicator,
                    callHorizonPct:      gblRequest.CallHorizonPct,
                    schedPeriod:         gblRequest.SchedPeriod,
                    schedPeriodUnit:     gblRequest.SchedPeriodUnit,
                    shiftFactorLatePct:  gblRequest.ShiftFactorLatePct,
                    shiftFactorEarlyPct: gblRequest.ShiftFactorEarlyPct,
                    toleranceLatePct:    gblRequest.ToleranceLatePct,
                    toleranceEarlyPct:   gblRequest.ToleranceEarlyPct,
                    cycleModFactor:      gblRequest.CycleModFactor,
                    completionRequired:  gblRequest.CompletionRequired,
                    factoryCalendar:     gblRequest.FactoryCalendar
                }
            },
            // Strategiens pakker fryses med. Ændrer masterdata sig i morgen,
            // skal vi stadig kunne se, hvad brugeren faktisk godkendte.
            packages: ForAll(colPackages As P,
                { packageNo: P.PackageNo, shortCode: P.ShortCode,
                  cycleLength: P.CycleLength, cycleUnit: P.CycleUnit,
                  hierarchy: P.Hierarchy, offset: P.Offset, text: P.PackageText }),
            items: ForAll(colItems As I,
                { itemNo: I.ItemNo, description: I.Title,
                  objectType: I.ObjectType,
                  functionalLocation: I.FunctionalLocation,
                  equipment: I.EquipmentNo,
                  plannerGroup: I.PlannerGroupCode, orderType: I.OrderType,
                  mainWorkCenter: I.MainWorkCenter, activityType: I.ActivityType,
                  taskListMode: I.TaskListMode,
                  taskList: { type: I.TaskListType, group: I.TaskListGroup,
                              counter: I.TaskListCounter },
                  objects: ForAll(Filter(colItemObjects, ItemTempId = I.TempId) As O,
                              { objectType: O.ObjectType, objectNo: O.ObjectNo }) }),
            taskLists: ForAll(colTaskLists As TL,
                { tempKey: TL.TempId, description: TL.Title, type: TL.TaskListType,
                  strategyKey: TL.StrategyKey, plant: TL.Plant,
                  usage: TL.UsageCode, workCenter: TL.WorkCenter,
                  operations: ForAll(Filter(colOperations, TaskListTempId = TL.TempId) As OP,
                      { operationNo: OP.OperationNo, description: OP.Title,
                        controlKey: OP.ControlKey, workCenter: OP.WorkCenter,
                        work: OP.Work, workUnit: OP.WorkUnit,
                        numberOfPeople: OP.NumberOfPeople,
                        duration: OP.Duration, durationUnit: OP.DurationUnit,
                        // Matricen udfoldes her til rene tal – modtageren
                        // skal aldrig kende til ";1;3;5;"-formatet.
                        packages: ForAll(
                            Filter(colPackages As P2,
                                ";" & Text(P2.PackageNo) & ";" in OP.PackagesKey),
                            { packageNo: P2.PackageNo }) }) })
        },
        JSONFormat.IndentFour
    )
);

// PayloadJson kan overskride 63.999 tegn ved meget store arbejdsplaner.
// Tjek det, i stedet for at opdage det som en afvist Patch i produktion.
If( Len(gblPayload) > 60000,
    Notify("Anmodningen er for stor til at indsendes i ét stykke. " &
           "Del den op i flere anmodninger.", NotificationType.Error),

    Patch( VHP_Request, LookUp(VHP_Request, ID = gblRequest.SpId),
        {
            Status:               "Indsendt",
            PayloadJson:          gblPayload,
            StrategyTextSnapshot: LookUp(nfStrategies, Title = gblRequest.StrategyKey).StrategyText,
            IntegrationStatus:    "NotSent"
        }
    );
    Patch( VHP_StatusLog, Defaults(VHP_StatusLog),
        { Title:    gblRequest.Title & " Indsendt",
          RequestId: gblRequest.SpId,
          FromStatus: "Kladde", ToStatus: "Indsendt",
          // Person-kolonner kan ikke patches med User() direkte – de kræver
          // den fulde SharePoint-brugerrecord med Claims.
          ActionBy: {
              '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser",
              Claims:      "i:0#.f|membership|" & gblUser.Email,
              DisplayName: gblUser.FullName,
              Email:       gblUser.Email,
              Department:  "", JobTitle: "", Picture: ""
          },
          ActionOn: Now() } );
    Set(gblDirty, false);
    Navigate(scrHome)
)

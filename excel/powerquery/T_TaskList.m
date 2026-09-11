// Query: T_TaskList
let
    Planer = Table.SelectColumns(T_Plan, {"RequestGuid"}),
    Kilde = fnListe("VHP_TaskList"),

    // Kun arbejdsplaner der hoerer til en godkendt anmodning
    Join = Table.Join(Kilde, "RequestId", Table.RenameColumns(
              fnListe("VHP_Request"), {{"ID", "RequestId"}}), "RequestId", JoinKind.Inner),
    KunGodkendte = Table.Join(Join, "RequestGuid", Planer, "RequestGuid", JoinKind.Inner),

    Valgt = Table.SelectColumns(KunGodkendte, {
        "RequestGuid", "ID", "Title", "TaskListType", "StrategyKey",
        "Plant", "UsageCode", "PlannerGroupCode", "WorkCenter"
    }),

    Omdoebt = Table.RenameColumns(Valgt, {
        {"ID", "TempKey"},                  // SharePoint-ID'et er noeglen
        {"Title", "Description"},
        {"TaskListType", "Type"},
        {"UsageCode", "Usage"},
        {"PlannerGroupCode", "PlannerGroup"}
    }),

    TekstNoegle = Table.TransformColumns(Omdoebt, {{"TempKey", Text.From, type text}}),

    MedStatus = Table.AddColumn(
        Table.AddColumn(
            Table.AddColumn(
                Table.AddColumn(TekstNoegle, "Equipment", each "", type text),
                "TL_Status", each "", type text),
            "TL_Group", each "", type text),
        "RunAt", each "", type text),

    Slut = Table.AddColumn(MedStatus, "RunMsg", each "", type text)
in
    Slut

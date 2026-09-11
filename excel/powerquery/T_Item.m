// Query: T_Item
let
    Kilde = fnListe("VHP_Item"),
    Anmodninger = Table.RenameColumns(
        Table.SelectColumns(fnListe("VHP_Request"), {"ID", "RequestGuid"}),
        {{"ID", "RequestId"}}),
    Planer = Table.SelectColumns(T_Plan, {"RequestGuid"}),

    Join = Table.Join(Kilde, "RequestId", Anmodninger, "RequestId", JoinKind.Inner),
    KunGodkendte = Table.Join(Join, "RequestGuid", Planer, "RequestGuid", JoinKind.Inner),

    Valgt = Table.SelectColumns(KunGodkendte, {
        "RequestGuid", "ItemNo", "Title", "ObjectType", "EquipmentNo",
        "FunctionalLocation", "PlannerGroupCode", "OrderType", "MainWorkCenter",
        "TaskListMode", "TaskListId", "TaskListType", "TaskListGroup", "TaskListCounter"
    }),

    Omdoebt = Table.RenameColumns(Valgt, {
        {"Title", "Description"},
        {"EquipmentNo", "Equipment"},
        {"PlannerGroupCode", "PlannerGroup"},
        {"MainWorkCenter", "WorkCenter"},
        {"TaskListId", "TaskListRef"}       // matcher T_TaskList.TempKey
    }),

    Tekst = Table.TransformColumns(Omdoebt, {{"TaskListRef", Text.From, type text}}),
    Slut = Table.AddColumn(Tekst, "Plant", each "", type text),
    Sorteret = Table.Sort(Slut, {{"RequestGuid", Order.Ascending}, {"ItemNo", Order.Ascending}})
in
    Sorteret

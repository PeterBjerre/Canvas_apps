// Query: T_Operation
//
// Kolonnerne staar i SKAERMRAEKKEFOELGE for IA01's operationsoversigt, ikke
// i datamodellens raekkefoelge. Det er med vilje: makroen bliver en simpel
// loekke, og fejlsoegning er at holde arket op mod skaermen.
let
    Kilde = fnListe("VHP_Operation"),
    Arbejdsplaner = Table.SelectColumns(T_TaskList, {"RequestGuid", "TempKey"}),

    MedNoegle = Table.TransformColumns(Kilde, {{"TaskListId", Text.From, type text}}),
    Join = Table.Join(MedNoegle, "TaskListId", Arbejdsplaner, "TempKey", JoinKind.Inner),

    Valgt = Table.SelectColumns(Join, {
        "RequestGuid", "TempKey", "OperationNo", "WorkCenter", "ControlKey",
        "Title", "Work", "WorkUnit", "NumberOfPeople", "Duration", "DurationUnit",
        "SortOrder"
    }),
    Omdoebt = Table.RenameColumns(Valgt, {{"Title", "Description"}}),

    Sorteret = Table.Sort(Omdoebt, {
        {"RequestGuid", Order.Ascending},
        {"TempKey", Order.Ascending},
        {"SortOrder", Order.Ascending},
        {"OperationNo", Order.Ascending}
    }),

    // SAP forventer foranstillede nuller: 10 -> "0010"
    Padded = Table.TransformColumns(Sorteret,
        {{"OperationNo", each Text.PadStart(Text.From(_), 4, "0"), type text}}),

    Slut = Table.RemoveColumns(Padded, {"SortOrder"})
in
    Slut

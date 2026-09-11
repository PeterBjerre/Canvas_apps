// Query: T_Plan  ->  indlaeses i arket som tabellen T_Plan
//
// KUN godkendte anmodninger. Filteret er det, der goer, at en ikke-godkendt
// anmodning aldrig kan naa til SAP - godkendelsen sker i SharePoint, og
// Excel ser kun resultatet.
let
    Kilde = fnListe("VHP_Request"),

    Godkendte = Table.SelectRows(Kilde, each [Status] = "KlarTilSAP"),

    Valgt = Table.SelectColumns(Godkendte, {
        "RequestGuid", "Title", "PlanType", "PlanDescription", "PlanCategory",
        "PlanningPlant", "StrategyKey", "PlanSortField", "CycleStartDate"
    }),

    Omdoebt = Table.RenameColumns(Valgt, {
        {"Title", "RequestNo"},
        {"PlanDescription", "Description"},
        {"PlanningPlant", "Plant"},
        {"PlanSortField", "SortField"}
    }),

    Typer = Table.TransformColumnTypes(Omdoebt, {
        {"RequestGuid", type text}, {"RequestNo", type text},
        {"PlanType", type text}, {"Description", type text},
        {"PlanCategory", type text}, {"Plant", type text},
        {"StrategyKey", type text}, {"SortField", type text},
        {"CycleStartDate", type date}
    }),

    // Statuskolonnerne skrives af makroen og maa IKKE komme fra SharePoint.
    // De tilfoejes tomme her, saa tabellens form er den samme foer og efter
    // en koersel - ellers flytter kolonnerne sig, naar queryen opdateres.
    MedStatus = Table.AddColumn(
        Table.AddColumn(
            Table.AddColumn(
                Table.AddColumn(Typer, "PLAN_Status", each "", type text),
                "PLAN_No", each "", type text),
            "RunMsg", each "", type text),
        "RunAt", each "", type text)
in
    MedStatus

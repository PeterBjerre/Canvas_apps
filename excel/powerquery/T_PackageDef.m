// Query: T_PackageDef
//
// Masterdata. Bruges to steder:
//   1. T_Package - til at oversaette pakkenummer til kolonneoverskrift
//   2. VBA - til at bestemme kolonneraekkefoelgen i IA01's table control
let
    Kilde = fnListe("MD_StrategyPackage"),
    Aktive = Table.SelectRows(Kilde, each [IsActive] = true),

    Valgt = Table.SelectColumns(Aktive, {
        "StrategyKey", "PackageNo", "ShortCode", "CycleLength", "CycleUnit", "Hierarchy"}),

    Typer = Table.TransformColumnTypes(Valgt, {
        {"StrategyKey", type text}, {"PackageNo", Int64.Type},
        {"ShortCode", type text}, {"CycleLength", type number},
        {"CycleUnit", type text}, {"Hierarchy", Int64.Type}}),

    Sorteret = Table.Sort(Typer, {
        {"StrategyKey", Order.Ascending}, {"PackageNo", Order.Ascending}})
in
    Sorteret

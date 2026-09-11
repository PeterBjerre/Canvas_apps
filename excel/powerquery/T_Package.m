// Query: T_Package
//
// HER sker udfoldningen af PackagesKey. Appen gemmer allokeringen som
// ";1;3;5;" paa operationsraekken; pakkeallokeringsskaermen i IA01 er et
// table control med EEN kolonne pr. pakke. Denne query oversaetter mellem de
// to former, saa hverken appen eller VBA behoever at kende det andet format.
//
// Resultat:
//   RequestGuid | TempKey | OperationNo | M1 | M3 | M6 | M12
//   ...         | 12      | 0010        | X  | X  | X  | X
let
    Kilde = fnListe("VHP_Operation"),
    Arbejdsplaner = Table.SelectColumns(T_TaskList, {"RequestGuid", "TempKey", "StrategyKey"}),

    MedNoegle = Table.TransformColumns(Kilde, {{"TaskListId", Text.From, type text}}),
    Join = Table.Join(MedNoegle, "TaskListId", Arbejdsplaner, "TempKey", JoinKind.Inner),

    // Operationer uden pakker filtreres fra. De fanges af regel S4 i
    // valideringen - de skal ikke bare forsvinde her.
    MedIndhold = Table.SelectRows(Join, each
        [PackagesKey] <> null and Text.Length(Text.From([PackagesKey])) > 1),

    // ";1;3;5;" -> {"1","3","5"}
    Splittet = Table.AddColumn(MedIndhold, "PkgNo", each
        List.Select(Text.Split(Text.From([PackagesKey]), ";"), each _ <> ""), type list),

    Udfoldet = Table.ExpandListColumn(Splittet, "PkgNo"),
    TilTal = Table.TransformColumns(Udfoldet, {{"PkgNo", Number.FromText, Int64.Type}}),

    // Pakkenummer -> ShortCode via masterdata
    Def = Table.SelectColumns(T_PackageDef, {"StrategyKey", "PackageNo", "ShortCode"}),
    MedKode = Table.Join(TilTal, {"StrategyKey", "PkgNo"}, Def, {"StrategyKey", "PackageNo"}, JoinKind.Inner),

    Valgt = Table.SelectColumns(MedKode, {
        "RequestGuid", "TempKey", "OperationNo", "ShortCode"}),
    Padded = Table.TransformColumns(Valgt,
        {{"OperationNo", each Text.PadStart(Text.From(_), 4, "0"), type text}}),
    MedMark = Table.AddColumn(Padded, "Mark", each "X", type text),

    // Kolonnerne SKAL staa i pakkenummerorden - det er den raekkefoelge
    // SAP viser dem i, og den raekkefoelge VBA falder tilbage paa, hvis
    // kolonnenavnene ikke kan matches.
    Koder = List.Distinct(Table.Column(
        Table.Sort(T_PackageDef, {{"PackageNo", Order.Ascending}}), "ShortCode")),

    Pivoteret = Table.Pivot(MedMark, Koder, "ShortCode", "Mark"),

    Sorteret = Table.Sort(Pivoteret, {
        {"RequestGuid", Order.Ascending},
        {"TempKey", Order.Ascending},
        {"OperationNo", Order.Ascending}})
in
    Sorteret

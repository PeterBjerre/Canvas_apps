// =====================================================================
// 02 – Pakkematricen
//
// Datamodel for én celle: operationens PackagesKey er en streng på formen
//   ";1;3;5;"
// Sentinel-separatoren i begge ender er ikke kosmetik. Uden den ville
// testen for pakke 1 (";1;") også matche inde i ";12;". Med den er en
// simpel substring-test korrekt, og vi undgår at parse i hver eneste celle.
//
// INVARIANT: PackagesKey er ALDRIG tom. En operation uden pakker har ";".
// =====================================================================


// ---------------------------------------------------------------------
// Kontrolhierarki
// ---------------------------------------------------------------------
//  conMatrix (horizontal container)
//  ├─ galHeader     Items = colPackages          As Pkg    (overskrifter)
//  └─ galOperations Items = colOperations        As OpRow  (vertikal)
//     ├─ lblOpNo / lblOpText
//     └─ galPackages  Items = colPackages        As Pkg    (horisontal)
//        └─ icoCheck
//
// Brug ALTID As-aliasser (OpRow / Pkg). Inde i den indre gallery er
// ThisItem pakken, og galOperations.Selected er ikke pålidelig, før
// brugeren rent faktisk har klikket. As-operatoren binder korrekt uanset.


// ---------------------------------------------------------------------
// galOperations
// ---------------------------------------------------------------------
// Items:
Sort(colOperations, SortOrder)
// TemplateSize: 44           <- fast højde. Auto height i en nested gallery
//                               tvinger relayout af alt ved hver scroll.
// TemplateFill: If(OpRow.IsSelected, ColorValue("#eef4ff"), Color.White)


// ---------------------------------------------------------------------
// galPackages (indre)
// ---------------------------------------------------------------------
// Items:        colPackages
// TemplateSize: nfMatrixColWidth
// WrapCount:    1  (horisontal)


// ---------------------------------------------------------------------
// icoCheck – visning
// ---------------------------------------------------------------------
// Icon:
If( ";" & Text(Pkg.PackageNo) & ";" in OpRow.PackagesKey,
    Icon.CheckBadge,
    Icon.CircleShape
)

// Color:
If( ";" & Text(Pkg.PackageNo) & ";" in OpRow.PackagesKey,
    ColorValue(Coalesce(Pkg.ColorHex, "#2d7ff9")),
    ColorValue("#d0d4dc")
)

// Bemærk: substring-testen udføres direkte mod strengen i stedet for et
// LookUp pr. celle. Med 8 pakker x 40 operationer er det 320 celler – et
// LookUp i hver ville betyde 320 tabelopslag ved hver eneste re-render.

// AccessibleLabel: (skærmlæser – matricen er ellers ubrugelig uden mus)
OpRow.OperationNo & " " & OpRow.Title & ", pakke " & Pkg.ShortCode & ", " &
If(";" & Text(Pkg.PackageNo) & ";" in OpRow.PackagesKey, "valgt", "ikke valgt")


// ---------------------------------------------------------------------
// icoCheck.OnSelect – slå pakken til/fra for operationen
// ---------------------------------------------------------------------
UpdateIf( colOperations,
    TempId = OpRow.TempId,
    {
        PackagesKey:
            With( { k: ";" & Text(Pkg.PackageNo) & ";" },
                If( k in ThisRecord.PackagesKey,
                    // Fjern: ";1;3;5;" minus ";3;" -> ";1;5;"
                    // Substitute fjerner den ene separator og genbruger den anden.
                    Substitute(ThisRecord.PackagesKey, k, ";"),
                    // Tilføj: tilføjes i enden, normaliseres ved gem.
                    ThisRecord.PackagesKey & Text(Pkg.PackageNo) & ";"
                )
            ),
        IsDirty: true
    }
);
Set(gblDirty, true)

// PackagesDisplay opdateres bevidst IKKE her. Den beregnes én gang ved gem
// (se 04-submit-patch.fx). At vedligeholde den pr. klik ville lægge en
// ekstra tabeloperation på hver eneste afkrydsning.


// ---------------------------------------------------------------------
// Hjælpehandlinger – de tre, der reelt sparer tid
// ---------------------------------------------------------------------

// A) Markér ALLE pakker for én operation  (btnRowAll.OnSelect)
UpdateIf( colOperations, TempId = OpRow.TempId,
    { PackagesKey: ";" & Concat(Sort(colPackages, PackageNo), Text(PackageNo) & ";"),
      IsDirty: true }
);

// B) Ryd rækken  (btnRowNone.OnSelect)
UpdateIf(colOperations, TempId = OpRow.TempId, { PackagesKey: ";", IsDirty: true });

// C) Markér én pakke for ALLE operationer  (btnColAll.OnSelect i galHeader)
UpdateIf( colOperations,
    !(";" & Text(Pkg.PackageNo) & ";" in ThisRecord.PackagesKey),
    { PackagesKey: ThisRecord.PackagesKey & Text(Pkg.PackageNo) & ";",
      IsDirty: true }
);

// D) Ryd én pakke for ALLE operationer
UpdateIf( colOperations,
    ";" & Text(Pkg.PackageNo) & ";" in ThisRecord.PackagesKey,
    { PackagesKey: Substitute(ThisRecord.PackagesKey, ";" & Text(Pkg.PackageNo) & ";", ";"),
      IsDirty: true }
);


// ---------------------------------------------------------------------
// E) Hierarki-udfyld – den vigtigste genvej
//
// Et 1/3/6/12-mønster fungerer sådan, at en operation, der hører til den
// månedlige pakke, næsten altid også skal udføres ved kvartals-, halvårs-
// og årsgennemgangen. Brugeren markerer derfor kun den LAVESTE pakke, og
// denne knap fylder resten ud efter hierarki.
//
// Sæt den som standardadfærd ved første afkrydsning, hvis jeres
// PM-key user bekræfter, at det er konventionen (se åbent spørgsmål 1).
// ---------------------------------------------------------------------
With(
    { minH: Min(
        Filter(colPackages As P, ";" & Text(P.PackageNo) & ";" in OpRow.PackagesKey),
        Hierarchy
      )
    },
    If( !IsBlank(minH),
        UpdateIf( colOperations, TempId = OpRow.TempId,
            { PackagesKey:
                ";" & Concat(
                        Sort(Filter(colPackages, Hierarchy >= minH), PackageNo),
                        Text(PackageNo) & ";"
                      ),
              IsDirty: true
            }
        ),
        Notify("Markér først mindst én pakke på operationen.", NotificationType.Warning)
    )
)


// ---------------------------------------------------------------------
// F) Kopiér allokering fra en anden operation  (drpCopyFrom + btnCopy)
// ---------------------------------------------------------------------
UpdateIf( colOperations, TempId = OpRow.TempId,
    { PackagesKey: LookUp(colOperations, TempId = drpCopyFrom.Selected.TempId).PackagesKey,
      IsDirty: true }
);


// ---------------------------------------------------------------------
// Normalisering – kaldes ÉN gang før gem/validering/payload.
// Sorterer numerisk og fjerner ukendte pakkenumre (fx rester fra en
// strategi, der er blevet ændret).
// ---------------------------------------------------------------------
UpdateIf( colOperations, true,
    { PackagesKey:
        ";" & Concat(
                Sort(
                    Filter(colPackages As P,
                        ";" & Text(P.PackageNo) & ";" in ThisRecord.PackagesKey),
                    PackageNo
                ),
                Text(PackageNo) & ";"
              ),
      PackagesDisplay:
        Concat(
            Sort(
                Filter(colPackages As P2,
                    ";" & Text(P2.PackageNo) & ";" in ThisRecord.PackagesKey),
                PackageNo
            ),
            ShortCode, ", "
        )
    }
)


// ---------------------------------------------------------------------
// Aflæsning – udpakning af PackagesKey til en tabel (til payload/eksport)
// ---------------------------------------------------------------------
// Pakkerne for én operation:
Filter(colPackages As P, ";" & Text(P.PackageNo) & ";" in OpRow.PackagesKey)

// Operationerne i én pakke:
Filter(colOperations, ";" & Text(Pkg.PackageNo) & ";" in PackagesKey)

// Ren talrække (til JSON):
ForAll(
    Filter(colPackages As P, ";" & Text(P.PackageNo) & ";" in OpRow.PackagesKey),
    { PackageNo: P.PackageNo }
)

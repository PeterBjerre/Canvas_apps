// =====================================================================
// 05 – HTML-tidslinje: hvornår forfalder pakkerne, og hvad kaldes?
//
// Dette er stedet, hvor HTML-komponenten hører hjemme. En indmelder kan
// ikke gennemskue, at "hver måned + hvert kvartal + hvert år" ikke
// betyder tre ordrer i marts. En kalender viser det på to sekunder.
//
// VIGTIGT OM HTML TEXT-KONTROLLEN:
//   - ingen JavaScript, ingen <script>
//   - ingen eksterne stylesheets/fonte – al styling skal være inline
//   - ingen events tilbage til appen (kontrollen er read-only)
//   - <svg> renderer ikke pålideligt på tværs af player-versioner;
//     brug <table>/<div> med inline styles
//   - sæt fast Height og Overflow = Scroll
// =====================================================================


// ---------------------------------------------------------------------
// TRIN 1 – beregn forfaldsdatoer. Kør ved knaptryk eller OnVisible,
// ALDRIG som en live formel i HtmlText. Beregningen er tung nok til at
// give mærkbar lag, hvis den genudregnes ved hver re-render.
// ---------------------------------------------------------------------
Set(gblTlYears, 3);
Set(gblTlMonths, gblTlYears * 12);
Set(gblTlStart, Date(Year(gblRequest.CycleStartDate), Month(gblRequest.CycleStartDate), 1));

ClearCollect( colDue,
    Ungroup(
        ForAll( colPackages As P,
            {
                Rows: ForAll(
                    // Antal kald, der skal til for at dække perioden.
                    // +2 som margin, så afrunding aldrig klipper sidste søjle.
                    Sequence(
                        RoundUp(
                            gblTlMonths /
                            Switch(P.CycleUnit,
                                "DAY", Max(P.CycleLength / 30.44, 0.01),
                                "WK",  Max(P.CycleLength * 7 / 30.44, 0.01),
                                "MON", Max(P.CycleLength, 0.01),
                                "YR",  Max(P.CycleLength * 12, 0.01),
                                999999   // tællerbaseret: kan ikke vises på en kalender
                            ), 0
                        ) + 2,
                        1
                    ) As S,
                    With(
                        { d: Switch(P.CycleUnit,
                                "DAY", DateAdd(gblTlStart, P.Offset + S.Value * P.CycleLength, TimeUnit.Days),
                                "WK",  DateAdd(gblTlStart, (P.Offset + S.Value * P.CycleLength) * 7, TimeUnit.Days),
                                "MON", DateAdd(gblTlStart, P.Offset + S.Value * P.CycleLength, TimeUnit.Months),
                                "YR",  DateAdd(gblTlStart, P.Offset + S.Value * P.CycleLength, TimeUnit.Years),
                                Blank()
                             )
                        },
                        {
                            PackageNo: P.PackageNo,
                            ShortCode: P.ShortCode,
                            Hierarchy: P.Hierarchy,
                            ColorHex:  Coalesce(P.ColorHex, "#2d7ff9"),
                            DueDate:   d,
                            // Månedsindeks 1..n relativt til startmåneden.
                            // Beregnes én gang her, så HTML-løkken kun laver
                            // en heltalssammenligning i stedet for datomatematik.
                            MonthIx:  (Year(d) - Year(gblTlStart)) * 12
                                      + (Month(d) - Month(gblTlStart)) + 1
                        }
                    )
                )
            }
        ),
        "Rows"
    )
);
RemoveIf(colDue, IsBlank(DueDate) || MonthIx < 1 || MonthIx > gblTlMonths);


// ---------------------------------------------------------------------
// TRIN 2 – hierarki-undertrykkelse.
//
// Når flere pakker forfalder samme dag, kalder SAP kun den pakke, der har
// det højeste hierarkiniveau; de lavere undertrykkes. Det er netop det,
// der gør et 1/3/12-mønster til 12 kald om året og ikke 16.
//
// >>> BEKRÆFT SEMANTIKKEN MED JERES PM-KEY USER (åbent spørgsmål 1). <<<
// Derfor en toggle: brugeren kan se begge fortolkninger side om side.
// ---------------------------------------------------------------------
ClearCollect( colCalls,
    ForAll( GroupBy(colDue, "DueDate", "MonthIx", "AtDate") As G,
        {
            DueDate: G.DueDate,
            MonthIx: G.MonthIx,
            Called:  If( tglUseHierarchy.Value,
                         // kun den højeste hierarkipakke kaldes
                         Filter(G.AtDate, Hierarchy = Max(G.AtDate, Hierarchy)),
                         // alle forfaldne pakker samles i ét kald
                         G.AtDate
                     )
        }
    )
);
ClearCollect(colCallFlat, Ungroup(colCalls, "Called"));


// ---------------------------------------------------------------------
// TRIN 3 – byg HTML. Resultatet lægges i gblTimelineHtml og bindes til
// htmlTimeline.HtmlText.
// ---------------------------------------------------------------------
Set( gblTimelineHtml,

    "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:11px;color:#20242c'>" &

    // ---- årsoverskrift ----
    "<table style='border-collapse:collapse;table-layout:fixed'>" &
    "<tr>" &
      "<td style='width:120px'></td>" &
      Concat( Sequence(gblTlYears, 0) As Y,
        "<td colspan='12' style='text-align:center;font-weight:600;" &
        "border-bottom:1px solid #d0d4dc;padding:2px'>" &
        Text(Year(gblTlStart) + Y.Value) & "</td>"
      ) &
    "</tr>" &

    // ---- månedsoverskrift ----
    "<tr>" &
      "<td style='width:120px;font-weight:600;padding:2px 4px'>Pakke</td>" &
      Concat( Sequence(gblTlMonths, 1) As M,
        "<td style='width:22px;text-align:center;color:#6b7280;padding:1px'>" &
        Left(Text(DateAdd(gblTlStart, M.Value - 1, TimeUnit.Months), "mmm"), 1) &
        "</td>"
      ) &
    "</tr>" &

    // ---- én række pr. pakke ----
    Concat( Sort(colPackages, PackageNo) As P,
      "<tr>" &
        "<td style='padding:2px 4px;white-space:nowrap'>" &
          "<span style='display:inline-block;width:9px;height:9px;border-radius:2px;" &
          "background:" & Coalesce(P.ColorHex, "#2d7ff9") & ";margin-right:5px'></span>" &
          P.ShortCode & " <span style='color:#6b7280'>(" &
          P.CycleLength & " " & P.CycleUnit & ")</span>" &
        "</td>" &
        Concat( Sequence(gblTlMonths, 1) As M,
          With( { n: CountRows(Filter(colDue, PackageNo = P.PackageNo, MonthIx = M.Value)) },
            "<td style='height:16px;border:1px solid #f0f1f4;text-align:center;" &
            "background:" & If(n > 0, Coalesce(P.ColorHex, "#2d7ff9"), "#fafbfc") &
            ";color:#fff;font-size:9px'>" &
            If(n > 1, Text(n), "") &
            "</td>"
          )
        ) &
      "</tr>"
    ) &

    // ---- kaldsrækken: hvad der faktisk udløses ----
    "<tr><td style='padding:6px 4px 2px;font-weight:600;white-space:nowrap'>" &
      "Kald" & If(tglUseHierarchy.Value, " (m. hierarki)", " (samlet)") &
    "</td>" &
    Concat( Sequence(gblTlMonths, 1) As M,
      With( { calls: Filter(colCallFlat, MonthIx = M.Value) },
        "<td style='height:18px;border:1px solid #f0f1f4;text-align:center;" &
        "background:" & If(CountRows(calls) > 0, "#20242c", "#fafbfc") &
        ";color:#fff;font-size:8px'>" &
        If(CountRows(calls) > 0, Text(CountRows(Distinct(calls, DueDate))), "") &
        "</td>"
      )
    ) &
    "</tr></table>" &

    // ---- opsummering i tal ----
    "<div style='margin-top:8px;padding:6px 8px;background:#f4f6f9;border-radius:4px'>" &
      "<b>" & CountRows(Distinct(colCallFlat, DueDate)) & "</b> kald over " &
      gblTlYears & " år &nbsp;&middot;&nbsp; " &
      "første kald <b>" & Text(Min(colCallFlat, DueDate), "dd-mm-yyyy") & "</b>" &
      If(!tglUseHierarchy.Value,
         " &nbsp;&middot;&nbsp; <span style='color:#b45309'>Uden hierarki samles " &
         "alle forfaldne pakker i én ordre pr. dato.</span>", "") &
    "</div></div>"
);

// ---------------------------------------------------------------------
// Performance
// ---------------------------------------------------------------------
// Løkken er 8 pakker x 36 måneder = 288 celler, hver med et Filter over
// colDue (~200 rækker). Det er ca. 0,5–1 sekund. Derfor:
//   - kør beregningen på en knap ("Vis forhåndsvisning") eller OnVisible
//   - bind htmlTimeline.HtmlText til gblTimelineHtml, ikke til udtrykket
//   - vis 3 år som standard; 5 år fordobler omkostningen

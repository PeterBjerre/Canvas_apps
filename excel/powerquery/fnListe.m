// Query: fnListe
//
// Henter en SharePoint-liste som tabel. Alle oevrige queries gaar gennem
// denne, saa connector-opsaetningen staar eet sted.
//
// Godkendelse: Organisationskonto (Office-loginnet). Ingen credentials i
// projektmappen - det er den vaesentligste grund til at bruge Power Query
// frem for VBA til datahentningen.
(listeNavn as text) as table =>
let
    Kilde = SharePoint.Tables(pSiteUrl, [Implementation = "2.0", ViewMode = "All"]),
    Liste = Kilde{[Title = listeNavn]}[Items]
in
    Liste

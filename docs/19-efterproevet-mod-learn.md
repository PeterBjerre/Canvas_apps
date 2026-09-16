# Antagelser efterprøvet mod Microsoft Learn

Hele projektet er bygget uden adgang til dokumentationen. Da adgangen kom,
gennemgik jeg det for alt, der var gættet. Det her er hvad der holdt, og
hvad der ikke gjorde.

## Det der var forkert

### `RemoveIf` mod SharePoint delegeres ikke

Gemningen ryddede de gamle rækker med fire `RemoveIf` mod SharePoint.
Delegeringstabellen for SharePoint siger `UpdateIf/RemoveIf`: **Number: Ja,
Text: Nej, Complex: Nej**. Alle fire kørte på en tekstkolonne eller på et
opslags underfelt — altså ingen af dem delegerede.

Værre: dokumentationen modsiger sig selv om *hvor meget* der hentes først.
Remove-siden siger *"all data matching the filter expression, up to 500 or
2000"*; UpdateIf-siden siger *"only the initial portion of the data source"*.
Den forskel afgør, om fejlen nogensinde rammer. Den slags tvetydighed er
ikke noget at bygge på.

Rettet til `Remove(kilde, Filter(kilde, betingelse))`. **`Filter` er
dokumenteret delegerbart** på SharePoint for `=` på tekst og på et opslags
underfelt, så filtreringen sker på serveren, og `Remove` får præcis de
rækker der skal væk. `Remove(DataSource, Table)` er en dokumenteret
signatur.

Konsekvensen hvis den var blevet: ved gensave af en plan i en liste, der er
vokset forbi grænsen, ville de gamle rækker ikke blive fundet og slettet —
og planen ville få dubletter. `TaskListMain` har allerede 313 rækker.

### Rækkegrænsen er 500, ikke 2000

Jeg skrev "delegeringsgrænsen ved 2000 rækker" i provisioneringen.
**Standarden er 500**, og 2000 er det højeste, den kan hæves til.

### En navngiven formel henter ikke "kun én gang"

`sp_config` sagde at navngivne formler *"evalueres dovent og caches: listen
hentes første gang en kontrol faktisk har brug for den, og kun een gang."*

Den første halvdel er rigtig — *"Named formulas are evaluated only when
their values are needed"*. Den anden er forkert. En navngiven formel er
ikke et engangs-cache men en definition, der altid er sand: den genberegnes,
når dens afhængigheder ændrer sig. Det er en fordel her, men det er ikke det
samme, og den der læser videre skal ikke regne med et fast øjebliksbillede.

### `OnStart` er ikke blokerende

*"A screen can render and become interactive before App.OnStart finishes
running."*

Fanebladene i Tasklist-sektionen styres af `varVhpOpsTab`, som sættes i
OnStart. Nåede skærmen at tegne først, var variablen tom — og så var
**ingen** fane synlig. Kortet ville stå tomt i det øjeblik. Tom regnes nu
som `ops`.

## Det der holdt

| Antagelse | Status |
|---|---|
| `Tooltip` findes ikke på `ModernText` | ✅ Bekræftet — den er ikke i kontrollens egenskabsliste |
| `ModernDropdown.OnChange` | ✅ Dokumenteret. Min flagede risiko var ubegrundet |
| `LayoutAlignItems.Stretch` klemmer i off-aksen | ✅ *"how child components are positioned in the container, in the **off axis** (opposite from LayoutDirection)"* — tjek 14 er korrekt |
| `FillPortions` fordeler langs forælderens retning | ✅ *"Minimum width … in the direction of the Fill portions (that is, the parent's Direction)"* — tjek 9 er korrekt |
| Power Fx binder SharePoint på visningsnavn | ✅ Allerede bevist empirisk i dette projekt to gange |
| `Remove(DataSource, Table)` | ✅ Dokumenteret signatur |

## Værd at vide, uden at være en fejl

**`OnChange` på tekstfelter fyrer nu ved fokus-tab, ikke pr. tastetryk.**
Fra *Recent updates to modern controls*: Text Input gik fra *"Every
keystroke"* til *"Focus out (blur) only"*, og Number Input til *"Focus out +
step button clicks"*. Appen bruger `OnChange` til at `Patch`e rækker i
gallerier, og dér er fokus-tab det rigtige tidspunkt — men hvis der senere
skal noget live (fx søgning mens man taster), skal det læse kontrollens
`.Text` direkte i stedet.

**Rich text-editoren i canvas kan ikke begrænses.** Ingen `toolbar`,
`plugins` eller `removePlugins` — de egenskaber findes kun på
model-driven-udgaven. Punktopstilling er altid tilgængelig, og indsæt fra
Word er udtrykkeligt understøttet. Se samtalen om langtekst til SAP.

**`FontWeight.Medium` findes ikke** på de moderne kontroller. Appen bruger
kun `Semibold` og `Normal`, så den er ikke ramt.

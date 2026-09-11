# Canvas app – opbygning

## 1. Skærmstruktur

Én skærm pr. wizard-trin frem for containere på én skærm. Canvas-appens
renderingstid vokser med antallet af kontroller på den aktive skærm, og en
monolitisk wizard-skærm med 150+ kontroller bliver mærkbart træg i både
Studio og player.

| Skærm | Indhold |
|---|---|
| `scrHome` | Mine anmodninger, filter på status, "Ny anmodning" |
| `scrStep1Header` | Plantype, beskrivelse, værk, planlæggergruppe, ordretype, begrundelse |
| `scrStep2Cycle` | **Single:** cyklus + enhed. **Strategi:** strategivalg + pakkeoverblik + startdato |
| `scrStep3Items` | Positioner (gallery) + sidepanel til redigering + objektliste |
| `scrStep4TaskList` | Eksisterende arbejdsplan eller ny + operationsgallery |
| `scrStep5Matrix` | Pakkematrix. Springes over hvis ikke `Strategy` + `New` |
| `scrStep6Params` | Planlægningsparametre, prefyldt fra strategien |
| `scrStep7Summary` | Valideringsliste, HTML-tidslinje, HTML-resumé, submit |
| `scrAdminMaster` | Kun for nøglebrugere: strategier og pakker |

Navigation styres af én funktion, så "spring trin 5 over"-logikken kun findes
ét sted — se `powerfx/01-app-formulas.fx`.

## 2. Tilstand

Al redigering sker mod **collections i hukommelsen**, ikke direkte mod
SharePoint. Først ved "Gem kladde" og ved submit skrives der.

| Variabel | Indhold |
|---|---|
| `gblRequest` | Record – anmodningshovedet |
| `colItems` | Positioner, hver med `TempId` (GUID) og `SpId` (SharePoint-ID, tom for nye) |
| `colItemObjects` | Objektliste |
| `colTaskLists` | Arbejdsplaner |
| `colOperations` | Operationer, inkl. `PackagesKey` |
| `colPackages` | Pakker for den valgte strategi (læst fra masterdata) |
| `gblStep` | Aktuelt trin |
| `gblDirty` | Er der ugemte ændringer |

**`TempId`-mønsteret er vigtigt.** Nye rækker har intet SharePoint-ID, men
matricen skal kunne pege på dem. Giv derfor hver række et klient-genereret
`TempId` ved oprettelse og brug det som join-nøgle i hele appen. Ved gem
mappes `TempId → SpId` én gang.

## 3. Masterdata: named formulas frem for `App.OnStart`

`App.OnStart` med `Collect()` af otte opslagslister forsinker appstart med
flere sekunder, og alle brugere betaler prisen — også dem, der bare skal se
deres kladder.

Brug i stedet **named formulas** (`App.Formulas`). De evalueres dovent og
caches, så en dropdown, der aldrig åbnes, aldrig koster et kald.

```powerfx
// App.Formulas
nfPlannerGroups = Sort(
    Filter(MD_ValueHelp, Domain = "PLANNERGROUP", IsActive = true),
    SortOrder
);
nfStrategies = Sort(Filter(MD_Strategy, IsActive = true), SortOrder);
```

Pakker for den *valgte* strategi kan ikke være en parameterløs named formula.
Enten en user-defined function (hvis `User-defined functions` er slået til i
miljøet) eller en almindelig `ClearCollect` i strategidropdownens `OnChange`.
Begge varianter står i `powerfx/01-app-formulas.fx`.

## 4. Pakkematricen – nested gallery

```
galOperations (vertikal, Items = colOperations)
├─ lblOpNo          Text = ThisItem.OperationNo
├─ lblOpText        Text = ThisItem.Title
└─ galPackages      (horisontal, Items = colPackages, TemplateSize = 56)
   └─ icoCheck      Icon = If(selected, Icon.CheckBadge, Icon.Blocked)
                    OnSelect = toggle
```

Den indre gallery løser det, der ellers er problemet: **antallet af kolonner
er dynamisk**, fordi det følger strategien. En canvas data table eller et sæt
faste toggles kan ikke det.

Kolonneoverskrifterne laves af en *tredje* horisontal gallery placeret lige
over `galOperations` med samme `Items` og samme `TemplateSize`, så
kolonnerne flugter. Læg begge i en horisontal container med samme bredde, og
lås `TemplateSize` til den samme named formula.

Fuld formelsamling: `powerfx/02-pakkematrix.fx`.

### Performance

Nested galleries koster. Med 8 pakker og 40 operationer er der 320
ikon-kontroller i DOM'en. Målte tommelfingerregler:

| Operationer × pakker | Oplevelse |
|---|---|
| ≤ 200 celler | Fint |
| 200–500 celler | Mærkbar, men brugbar forsinkelse ved scroll |
| > 500 celler | Skift til PCF eller opdel arbejdsplanen |

Afbødning i fase 1: sæt `galOperations.TemplateSize` fast (ikke `Auto height`),
undgå formler i `Visible` på celleniveau, og beregn "er pakken valgt" med en
simpel `in`-test frem for et `LookUp` pr. celle.

### Hjælpefunktioner i matricen

- **Vælg hele rækken / hele kolonnen.** To knapper. Sparer enormt mange klik
  ved et 1/3/6/12-mønster, hvor pakke 12 typisk indeholder alt.
- **Kopiér allokering fra en eksisterende operation.** Dropdown + knap.
- **Hierarki-udfyld.** Ét klik: kryds automatisk en operation af i alle
  pakker med hierarki ≥ den laveste, brugeren har valgt. Det er præcis det
  mønster, 90 % af strategiplanerne følger.

## 5. HTML-komponenterne

To steder, og kun to:

### 5.1 `cmpCycleTimeline` – forfaldskalender

Input: `HtmlText` bygget af en formel (se `powerfx/05-html-timeline.fx`).
Viser 3–5 år frem, én række pr. pakke, en markering pr. forfald, og en
"kald"-række nederst, der viser hvad der faktisk udløses, når
hierarki-undertrykkelse er slået til.

Det er den eneste måde, en indmelder kan **se**, at "hver måned + hvert
kvartal + hvert år" ikke betyder tre separate ordrer i marts.

Begrænsninger i HTML text-kontrollen, som designet respekterer:

- Ingen JavaScript. Ingen `<script>`.
- Ingen eksterne stylesheets eller webfonts — al styling inline.
- Ingen events tilbage til appen. Kontrollen er read-only.
- `<svg>` understøttes ikke pålideligt på tværs af player-versioner.
  **Brug `<table>` og `<div>` med inline styles** — det renderer ens overalt.
- Kontrollen skalerer ikke selv; sæt en fast højde og `Overflow = Scroll`.

### 5.2 `cmpRequestSummary` – resumé til godkendelse og print

Hele anmodningen som ét HTML-dokument. Samme streng kan sendes til et flow,
der laver PDF ("Convert HTML to PDF" via OneDrive-connectoren) og vedhæfter
den på godkendelsesmailen. Det er den billigste vej til et læsbart bilag.

## 6. Genbrugelige komponenter

| Komponent | Ind | Ud |
|---|---|---|
| `cmpWizardHeader` | `CurrentStep`, `Steps` (tabel), `ErrorCount` | `OnStepSelect` |
| `cmpValidationPanel` | `Messages` (tabel: Severity, Code, Text, Step) | `OnNavigateToStep` |
| `cmpLookupCombo` | `Domain`, `Plant`, `SelectedCode` | `SelectedItem` |
| `cmpPackageMatrix` | `Operations`, `Packages` | `UpdatedOperations` |
| `cmpCycleTimeline` | `Packages`, `StartDate`, `Years`, `UseHierarchy` | – |

`cmpLookupCombo` er den, der betaler sig hurtigst hjem: der er 12+ steder i
appen, hvor der skal vælges en kode fra `MD_ValueHelp`, og de skal alle
opføre sig ens mht. søgning, inaktive værdier og værkfiltrering.

## 7. Gem og submit

**Gem kladde** (kan køres når som helst):

1. Patch `VHP_Request` → få `SpId` og `Title`.
2. `Patch` børnelisterne med `ForAll` over collections, hvor `SpId` er tom
   (nye) eller `Modified`-flag er sat.
3. Slet rækker, brugeren har fjernet (`colDeleted`).
4. Skriv `SpId` tilbage i collections, så næste gem bliver en opdatering.

**Submit** (kun hvis validering er grøn):

1. Gem kladde (som ovenfor).
2. Byg `PayloadJson` med `JSON()` over en normaliseret record.
3. Patch `Status = "Indsendt"`, `PayloadJson`, `StrategyTextSnapshot`.
4. Flowet `VHP-Submit` tager over: gen-validerer serverside, skriver
   `VHP_StatusLog`, og starter godkendelsen.

Detaljerede formler: `powerfx/04-submit-patch.fx`.

> **Ingen transaktioner.** Hvis trin 2 fejler halvvejs, står anmodningen
> stadig som `Kladde` med en delvist gemt struktur — det er det korrekte,
> genoptagelige udfald. Derfor sættes `Status` altid **sidst**.

## 8. Fejlhåndtering

- Pak hvert `Patch` i `IfError` og opsaml i `colSaveErrors`.
- Vis en enkelt banner: "3 af 24 rækker kunne ikke gemmes – prøv igen".
  Aldrig en `Notify()` pr. række.
- Log `FirstError.Message` til en `VHP_ClientLog`-liste, når fejlen ikke er
  en simpel netværksfejl. Uden det er fejlsøgning i produktion gætteri.

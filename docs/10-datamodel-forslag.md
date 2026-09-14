# Forslag til datamodellen

Bygger på fundene i [`09-datamodel-fund.md`](09-datamodel-fund.md) og på to
svar: **appen skriver til listerne i dag**, og **ingen af os har bygget dem**.

Kort version: **behold de tre transaktionslister og skriv til dem.** De mangler
fem kolonner og har ét navnerod. Det er billigere at rette end at bygge om.
Lav i stedet om på det, der faktisk er galt: de seks kopierede tasklist-lister,
de manglende strategipakker, og løbenumrene.

## 1. Hvad jeg fandt, da jeg læste alle 306 operationer

Prøvefilen viste sig at indeholde hele `TaskListMain`, ikke bare otte rækker.
Det ændrer to ting, jeg skrev i §9.

**`TaskListMain` indeholder ikke skabeloner.** 305 af 306 rækker har
`MaintenanceItemNo`. Der er ingen skabelonrækker. Spørgsmålet var forkert
stillet.

**`TaskID` er overflødigt.** 81 forskellige `TaskID`, 81 forskellige
`MaintenanceItemNo`, og **ingen** `TaskID` spænder over mere end ét item. Den
er altså 1:1 med item'et og siger intet, som `MaintenanceItemNo` ikke allerede
siger. Den koster et løbenummer og en kolonne.

**Tre huller, der betyder noget for SAP:**

| Felt | Virkelighed |
|---|---|
| `OperationNo` | **Findes ikke.** Appen regner med `0010`, `0020`, `0030` |
| `Index` | Udfyldt på **90 af 306**. Rækkefølgen på operationer er reelt ikke gemt |
| `Num` | Er **ikke** operationsnummeret. 277 af 305 har værdien 1, og der er værdier som 1,2 og 1,5. Det er et antal, ikke en sekvens |

Uden et operationsnummer og en pålidelig rækkefølge kan GUI-scriptet ikke
lægge operationerne ind i IA01 i den rigtige orden. Det er den mest konkrete
fejl i modellen lige nu.

**Og til orientering:** `Duration` er udfyldt på 42 af 306, `WorkCtr` på 58.
De felter, appen viser som obligatoriske pr. operation, er i praksis tomme.
Det er værd at tage stilling til, før valideringen strammes.

## 2. Bliv ved de tre lister

Alternativet — nye indsendelseslister ved siden af — lyder rent, men koster
mere end det giver:

- Det er de **samme forretningsobjekter**. To sæt betyder to sandheder og et
  fletteproblem, der aldrig holder op.
- Mængderne er små: 34 planer, 58 items, 306 operationer. Der er intet
  ydelsesargument.
- Statussen på tværs af domæner ligger allerede i `MD_RequestIndex`. Den
  behøver ikke en kopi af selve indmeldingen.
- Den gamle app skal kunne køre videre, mens den nye bygges. Nye kolonner
  generer den ikke; en parallel model gør.

Så: **tilføj kolonner, lad være med at flytte data.**

## 3. Det der skal tilføjes (ingen risiko for den kørende app)

**Status: bygget.**

```powershell
.\Provision-VHPlanColumns.ps1 -SiteUrl "https://..." -WhatIfOnly   # tørløb
.\Provision-VHPlanColumns.ps1 -SiteUrl "https://..." -Backfill
```

`-Backfill` udfylder `OperationNo` på de 306 eksisterende rækker: 10, 20, 30
pr. maintenance item, sorteret efter `Index` hvor det findes og ellers efter
`ID`. Kun rækker uden `OperationNo` røres, så den kan køres igen.

Fordelingen i dag: 18 items har `Index` på alle deres rækker, 2 delvist, og
61 slet ikke. Dem med `Index` beholder den rækkefølge, nogen faktisk har
valgt; resten får ID-orden.


### `TaskListMain`

| Kolonne | Type | Hvorfor |
|---|---|---|
| `OperationNo` | Number, indekseret | SAP-operationsnummeret: 10, 20, 30. Findes ikke i dag |
| `PackagesKey` | Text | Pakkeallokeringen, `;1;3;5;`. Sentinel i begge ender, så `;1;` aldrig matcher inde i `;12;` |

`OperationNo` erstatter `Index` som rækkefølge — ét felt, der både sorterer og
er det, SAP skal bruge. `Index` bliver stående urørt, indtil den gamle app er
ude.

### `MaintenanceItems`

| Kolonne | Type | Hvorfor |
|---|---|---|
| `OrstedResponsibleEmail` | Text, indekseret | Person-kolonner kan ikke filtreres delegerbart. Sættes af samme flow som `OrstedResponsible` |

### `MaintenancePlans`

Ingen nye kolonner — `PlanType`, `StandardStrategy`, `Package` og
`MultiCounterStrategy` findes allerede. Men **ét navnerod skal ryddes**:

```
internt CallHorizon    ->  visningsnavn 'CallHorizonOLD'   (Choice, gammel)
internt CallHorizon0   ->  visningsnavn 'CallHorizon'      (Number, i brug)
```

Giv choice-kolonnen visningsnavnet `CallHorizonChoiceOLD`. Så er der ikke
længere et visningsnavn, der samtidig er en anden kolonnes interne navn. Det
ændrer intet for Power Fx (som allerede binder på `CallHorizonOLD`), men det
fjerner den fælde, et migreringsscript falder i.

## 4. Det der skal oprettes

Rene tilføjelser. Rører ikke noget bestående.

### `MD_Strategy` og `MD_StrategyPackage`

**Status: bygget.** Kør:

```powershell
python3 tools/gen_strategy_seed.py          # -> sharepoint/seed/MD_Strategy.csv
.\Provision-StrategyLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDEV"
```

Strategierne er hentet fra SAP og ligger i `sharepoint/Strategier.txt` —
**53 stykker**, nøgle 100 til 190. `MD_StrategyPackage` oprettes tom;
pakkerne kommer senere.

| `MD_Strategy` | Type | |
|---|---|---|
| `Title` → vises som `StrategyKey` | Text, indekseret | SAP-nøglen: `100`, `101` … |
| `StrategyName` | Text | `1-3-6-12-36 md eftersyn` |
| `SchedulingIndicator` | Choice: TIME, TIME_FACTOR, PERFORMANCE | **Gættet** — se nedenfor |
| `Hierarchical` | Choice: Ja, Nej, **Ikke afklaret** | Sættes i hånden |
| `PackagesLoaded` | Boolean | Sand, når strategiens pakker er indlæst |
| `Notes` | Note | |

Bemærk at `Title` får visningsnavnet `StrategyKey`. Power Fx binder på
visningsnavn, så appen skriver `ThisItem.StrategyKey` — mens et
migreringsscript skal bruge `Title`. Samme mønster som `RequestNo` i
`MD_RequestIndex`.

**`Hierarchical` gættes ikke.** Om en strategi undertrykker sine egne pakker,
står hverken i navnet eller i udtrækket. Alle 53 rækker får derfor
`Ikke afklaret`, og feltet sættes i hånden. Det er et **tre**-værdi-felt og
ikke ja/nej, netop så en strategi, ingen har taget stilling til, ikke ligner
et bevidst "nej" — og så appen kan advare frem for at gætte. Scriptet skriver
til sidst, hvor mange der mangler.

**`SchedulingIndicator` gættes derimod.** Begynder navnet med `Tæller` eller
`T.`, er det en tællerstrategi (`PERFORMANCE`), ellers tid (`TIME`). Det giver
13 PERFORMANCE og 40 TIME. Det er udledt af teksten, ikke læst i SAP, så det
skal efterprøves mod IP11. Jeg gætter her og ikke på `Hierarchical`, fordi der
faktisk *er* evidens i navnet.

**`PackagesLoaded`** er til den mellemtilstand, I står i nu: 53 strategier uden
pakker. Appen må kun tilbyde strategier, hvor den er sand — ellers vælger
brugeren en strategi, og pakkematricen står tom uden forklaring.

> **Om navnene.** Seks af de 53 er præcis 30 tegn — SAP afkorter der, og nogle
> er klippet midt i et ord (`6-12-24-30-36-60-72 md eftersy`). Behandl dem som
> nøgler med en etiket, ikke som prosa.

| `MD_StrategyPackage` | Type |
|---|---|
| `Title` → vises som `PackageLabel` | Text |
| `StrategyKey` | Text, indekseret |
| `PackageNo` | Number |
| `ShortCode` | Text — `M1`, `M3` |
| `CycleLength` / `CycleUnit` | Number / Choice |
| `Hierarchy` | Number — hvem kalder, når flere forfalder samme dag |
| `PackageText` | Text |
| `OffsetValue` | Number |

Nøglen er `StrategyKey` + `PackageNo`, ikke `Title`.

### `MD_StandardTaskOperations` — de seks bliver til én

**Status: bygget.**

```powershell
.\Provision-StandardTaskOperations.ps1 -SiteUrl "https://..." -WhatIfOnly   # tørløb
.\Provision-StandardTaskOperations.ps1 -SiteUrl "https://..." -Migrate
```

De seks `<VÆRK> Standard Tasklist` har 42 af 42 identiske kolonner (AVV har
én tom rest, `Test1`). De er oprettet med "opret liste fra Excel", så interne
navne er `field_1` … `field_36`, og visningsnavnene er SAP's egne overskrifter
— heriblandt `Un.`, `Uni.`, `Int. distr` og én kolonne, der hedder `/`.

**To ting, jeg først så, da jeg læste alle 176 rækker:**

1. **Operationsnummeret ligger i `Title`** — 10, 20, 30 … `field_1` (`SOp`),
   som man skulle tro var nummeret, er **tom i alle 176 rækker**. Hver af de
   seks lister er én arbejdsplan med én sekvens.
2. **13 af de 36 kolonner er tomme overalt:** `SOp`, `NorDur`, `Int. distr`,
   `Functional Location`, `Equipment`, `Assembly`, `Service Object`, `TT`,
   `Wage Group`, `WT`, `Suit`, `System Condition`, `PDT`. De tages ikke med.

Den nye liste får `Plant` (Choice, indekseret), `OperationNo` (Number,
indekseret) og de 23 kolonner med indhold:

| Ny kolonne | Fra | SAP |
|---|---|---|
| `WorkCenter` | `field_2` | Work Ctr |
| `ControlKey` | `field_4` | Ctrl |
| `OperationShortText` | `field_5` | Operation short text |
| `Work` / `WorkUnit` | `field_6` / `field_7` | Work / Un. |
| `DurationUnit` | `field_10` | Uni. |
| `ActivityType` | `field_15` | ActTyp |
| `StandardTextKey` | `field_16` | StTextKy |
| `SapPlant` | `field_3` | Plnt |
| *+ 15 øvrige* | | OrdQuantity, Price, Cost elem., Matl Group, PGr, Vendor, POrg … |

De ni øverste bruger appen. Resten tages med, fordi de har indhold, og fordi
det er uigenkaldeligt at smide dem væk.

**SAP's egen overskrift gemmes som kolonnens beskrivelse** (`SAP: Work Ctr
(var field_2 i kildelisten)`). Nogle af navnene — `NumberOfCapacities` for
`No.`, `CalculationKey` for `Calc`, `PriceUnit` for `/` — er **min tolkning**
af en SAP-forkortelse. Beskrivelsen gør, at den kan efterprøves og rettes uden
at grave i et script.

Migreringen **trimmer**: SAP-eksporten er polstret med mellemrum (`'SSVAP   '`,
`'FUN07 '`). Utrimmet matcher opslag ikke.

De seks kildelister røres ikke. De bliver stående, til den gamle app er
slukket.

## 5. Løbenumrene — jeg tog fejl

Jeg skrev, at `AppSettings` holder **tællere**, som appen læser, lægger én til
og skriver tilbage, og at to samtidige indsendelser derfor kunne få samme
nummer. **Det er forkert.** Jeg havde ikke efterprøvet det mod data.

Da jeg gjorde det, var mønsteret entydigt — uden en eneste undtagelse:

| Liste | Nøgle | Forhold til SharePoints `ID` | Rækker der passer |
|---|---|---|---|
| `MaintenancePlans` | `PlanID` | `ID - 5` | **34 af 34** |
| `MaintenanceItems` | `ItemID` | `ID - 6` | **58 af 58** |
| `TaskListMain` | `TaskItemID` | `ID - 1` | **306 af 306** |

Og de tre tal i `AppSettings` er præcis 5, 6 og 1. De er altså **offsets, ikke
tællere**. Den gamle app gør allerede dét, jeg anbefalede: nøglen kommer fra
SharePoints eget `ID`, som tildeles atomart. **Der er ingen kapløbstilstand.**

Offsettet findes, fordi listerne allerede indeholdt henholdsvis 5, 6 og 1
rækker, da nummereringen blev taget i brug.

### Hvad der så skal gøres

**Behold offsettet.** Numre som `MP0062` står sandsynligvis i SAP, i mails og
i folks hoveder. At fjerne offsettet ville forskyde hele serien med 5 for at
vinde en smule renhed. Den nye app læser offsettet fra `AppSettings` som i dag.

### Den ene nøgle, der ikke er ID-afledt

`TaskListMain.TaskID` (`TL0002`) følger **ikke** mønsteret — forskellen til
`ID` svinger fra 55 til 74 og opefter. Det er en selvstændig serie, og den er
det eneste sted, et rigtigt tællerproblem kunne opstå.

Men den er også overflødig: 80 forskellige `TaskID` mod 81 items, og ingen
`TaskID` spænder over mere end ét item (§1). Den siger intet, som
`MaintenanceItemNo` ikke allerede siger.

**Den nye app skriver den ikke.** Så forsvinder problemet i stedet for at
blive løst. Kolonnen bliver stående, til den gamle app er slukket.

### En ting der skal ordnes før TEST og PROD

`AppSettings` har seks rækker: tre app-URL'er (DEV, TEST, PROD) og tre
`RunningNo`-offsets — **alle tre for DEV**.

Kører appen i TEST eller PROD, findes offsettet ikke. Så bliver det blankt,
og nøglen bliver `ID` uden fratræk — altså en anden serie end i DEV, uden at
nogen har besluttet det.

Det er ikke et problem i dag, fordi vi arbejder i DEV. Men det skal afklares,
før appen flyttes: enten oprettes de manglende rækker med det rigtige offset
for hvert miljø, eller også skal appen fejle højlydt frem for at gætte på 0.

## 6. Navngivning

Jeg foreslår **ikke** at omdøbe de eksisterende lister. Det ville brække den
kørende app uden at give andet end pænere navne.

Men nye lister får `MD_`-præfiks for masterdata, som `MD_RequestIndex` allerede
har. Så vokser konventionen frem uden en stor omdøbning:

```
MD_*    masterdata, opdateres fra SAP, appen laeser kun
        MD_RequestIndex, MD_Strategy, MD_StrategyPackage,
        MD_StandardTaskOperations

(de oevrige)  transaktioner og opslag som de hedder i dag
```

## 7. Hvad der kan skrottes — men først når den gamle app er ude

| Liste / kolonne | Hvorfor |
|---|---|
| De seks `<VÆRK> Standard Tasklist` | Erstattet af `MD_StandardTaskOperations` |
| `AVV Standard Tasklist.Test1` | Tom rest |
| `StandardTaskList` | Tre rækker: Test1, Test2, Test3. Rene testdata |
| `TaskListMain.TaskID` | 1:1 med `MaintenanceItemNo`. Den nye app skriver den ikke |
| `MaintenancePlans.CallHorizon` (Choice) | Når alle rækker er på taltkolonnen |

Slet ingenting nu. Listen er til den dag, oprydningen er ufarlig.

## 8. Rækkefølge

1. ~~Tilføj de fire kolonner i §3 og ryd navnerodet.~~ **Gjort** —
   `Provision-VHPlanColumns.ps1`.
2. ~~Opret `MD_Strategy` og `MD_StrategyPackage`.~~ **Gjort** — kør
   `Provision-StrategyLists.ps1`. Sæt derefter `Hierarchical` i hånden, og
   efterprøv `SchedulingIndicator` mod IP11. Pakkerne indlæses, når de er
   hentet.
3. ~~Opret `MD_StandardTaskOperations` og migrér de 176 rækker.~~ **Gjort** —
   `Provision-StandardTaskOperations.ps1`.
4. Byg den nye app mod modellen, med de gamle lister urørte ved siden af.
5. ~~Vælg B til løbenumrene.~~ **Ikke nødvendigt** — den gamle app afleder
   dem allerede fra SharePoints `ID`. Se §5. Det eneste, der skal gøres, er
   at den nye app ikke skriver `TaskID`, og at offsets oprettes for TEST og
   PROD inden appen flyttes dertil.
6. Ryd op i §7, når den gamle app er slukket.

Trin 1-3 er skrevet. Kør dem med `-WhatIfOnly` først — begge siger hvad de
ville gøre uden at røre noget.

Trin 4 er den nye app. Den venter på, at `Hierarchical` er sat, og at
pakkerne er hentet fra IP11.

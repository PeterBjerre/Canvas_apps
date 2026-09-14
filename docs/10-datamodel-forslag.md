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

Strategipakkerne findes ikke. `StandardStrategyList` har kun `Title`, hvor
pakkestrukturen står som fritekst: `101 - 1-3-6-12-36 md eftersyn`.

| `MD_Strategy` | Type |
|---|---|
| `Title` (= `StrategyKey`) | Text, indekseret |
| `Name` | Text |
| `SchedulingIndicator` | Choice: TIME, TIME_FACTOR, PERFORMANCE |
| `SapStrategy` | Text — nøglen i SAP (IP11) |

| `MD_StrategyPackage` | Type |
|---|---|
| `StrategyKey` | Text, indekseret |
| `PackageNo` | Number |
| `ShortCode` | Text — `M1`, `M3` |
| `CycleLength` / `CycleUnit` | Number / Choice |
| `Hierarchy` | Number — hvem kalder, når flere forfalder samme dag |
| `PackageText` | Text |

**Værdierne skal hentes fra SAP (IP11), ikke opfindes.** De tre rækker i
`StandardStrategyList` er ikke nok, og de bærer ikke pakkerne. Det er den
eneste post på listen her, der kræver noget af jer ud over et script.

### `MD_StandardTaskOperations` — de seks bliver til én

De seks `<VÆRK> Standard Tasklist` har 42 af 42 identiske kolonner (AVV har én
tom rest, `Test1`). De er oprettet med "opret liste fra Excel", så de interne
navne er `field_1` … `field_36`, og visningsnavnene er SAP's egne overskrifter
— heriblandt `Un.`, `Uni.`, `Int. distr` og én kolonne, der hedder `/`.

Én liste med en indekseret `Plant`-kolonne og rigtige navne:

| Ny kolonne | Fra |
|---|---|
| `Plant` | listens navn (`SSV`, `ASV`, …), indekseret |
| `OperationNo` | `field_1` (SOp) |
| `WorkCenter` | `field_2` (Work Ctr) |
| `ControlKey` | `field_4` (Ctrl) |
| `OperationShortText` | `field_5` |
| `Work` / `WorkUnit` | `field_6` / `field_7` |
| `NormalDuration` / `DurationUnit` | `field_9` / `field_10` |
| `ActivityType` | `field_15` |
| `StandardTextKey` | `field_16` |

Det er de ni, appen bruger. De øvrige 27 SAP-felter kan tages med som de er
eller skæres væk — men det skal være et **valg**. Kom de med, får de rigtige
navne.

176 rækker i alt. Migreringen er triviel, og den gamle app rører ikke den nye
liste — de seks bliver stående, til den er ude.

## 5. Løbenumrene

`AppSettings` holder tællere pr. miljø:

```
{Environment: DEV, Option: RunningNoPlan, Value: 5}
{Environment: DEV, Option: RunningNoItem, Value: 6}
{Environment: DEV, Option: RunningNoTask, Value: 1}
```

Appen læser tallet, lægger én til, skriver tilbage og bruger resultatet som
`MP0062`. **To brugere, der indsender samtidig, læser det samme tal.** Så bliver
det to planer med samme nøgle, og det opdages først i SAP.

Tre veje:

| | Hvad | Vurdering |
|---|---|---|
| A | Flyt optællingen til et flow med **concurrency control = 1** | Virker. Serialiserer kaldene, men lægger et flow-kald ind i hver indsendelse |
| B | Drop tælleren. Opret rækken, og sæt bagefter `PlanID = "MP" & Text(ID, "0000")` | **Anbefales.** SharePoints `ID` er kollisionsfri pr. definition. Koster én ekstra `Patch` |
| C | Behold tælleren, tjek efter skrivning om nøglen er unik, prøv igen | Virker, men er den slags kode, ingen tør røre bagefter |

Data peger i øvrigt allerede på B: `MP0062` har `ID` 67, `MP0063` har 68,
`MP0066` har 71. Tælleren *er* i praksis `ID` minus 5 — den startede bare fem
for lavt. B gør det eksplicit i stedet for tilfældigt. Prisen er et hop i
nummerserien ved overgangen; det er kosmetik.

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

1. Tilføj de fire kolonner i §3 og ryd navnerodet. Additivt, den gamle app
   mærker intet.
2. Opret `MD_Strategy` og `MD_StrategyPackage` — tomme. Hent værdierne fra
   IP11.
3. Opret `MD_StandardTaskOperations` og migrér de 176 rækker.
4. Byg den nye app mod modellen, med de gamle lister urørte ved siden af.
5. Vælg B til løbenumrene, når indsendelsen alligevel skrives om.
6. Ryd op i §7, når den gamle app er slukket.

Trin 1-3 kan skrives som scripts med det samme. Sig til, så laver jeg dem — og
et migreringsscript til trin 3, der læser de seks lister og skriver den ene.

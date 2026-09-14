# Hvad listerne faktisk indeholder

Svar på de seks spørgsmål i [`08-datamapning.md`](08-datamapning.md) §5, baseret
på udtrækket i [`../sharepoint/inspect/out/`](../sharepoint/inspect/out):
21 lister, 452 kolonner, ingen fejlede. `FunctionalLocations` blev bevidst
sprunget over.

Site: `https://orsted.sharepoint.com/teams/BioSAPDEV`

## Kort svar

| Spørgsmål | Svar |
|---|---|
| 1. Har de seks `<VÆRK> Standard Tasklist` ens kolonner? | **Ja** — 42 af 42 identiske. AVV har én ekstra, `Test1`, som er en rest |
| 2. Hvor ligger operationerne? | **`TaskListMain`** (306). Bundet til item via `MaintenanceItemNo`, til plan via `MaintenancePlanID` |
| 3. Nøglen plan ↔ item? | `MaintenanceItems.MaintenancePlanNo` er et **opslag** på `MaintenancePlans.PlanID` (`MP0062`) |
| 4. Findes strategipakkerne? | **Nej.** `StandardStrategyList` har kun `Title`. Pakkestrukturen står som fritekst i strateginavnet |
| 5. Er `PlantList` mangelfuld? | **Ja.** 6 rækker, men `PlantsInitial` har 8 valg. Mine tre ekstra i testdata var delvist opfundet |
| 6. Hvad er de fire "løse" lister? | `LubricationTaskType` og `Vendors` er i brug. `StandardTaskList` er testdata. `UserAndGroups` er rolle­styring |

## 1. Det der skal rettes med det samme

### `MaintenancePlans` har to CallHorizon-kolonner, og de er byttet om

```
internt CallHorizon    ->  Power Fx ser 'CallHorizonOLD'   (Choice)
internt CallHorizon0   ->  Power Fx ser 'CallHorizon'      (Number)
```

Power Fx binder på **visningsnavn**. Så `ThisItem.CallHorizon` rammer den
kolonne, der hedder `CallHorizon0` internt — og `ThisItem.CallHorizonOLD`
rammer den, der hedder `CallHorizon`. Det er ikke en fejl i sig selv, men
det er en fælde, der garanteret bider den næste, der læser JSON-eksporten
eller skriver et migreringsscript, hvor **interne** navne gælder.

Værre: visningsnavnet `CallHorizon` er samtidig en *anden* kolonnes interne
navn. Det er den eneste egentlige kollision i hele modellen, og den ligger i
den mest centrale liste.

**Ryd op:** giv den gamle choice-kolonne et visningsnavn, der ikke kan
forveksles (fx `CallHorizonChoiceOLD`), eller slet den, hvis alle rækker er
migreret til taltkolonnen.

### `OrstedResponsible` er en Person-kolonne

`MaintenanceItems.OrstedResponsible` er type `User`. Person-kolonner **kan
ikke filtreres delegerbart** i SharePoint. Det er præcis derfor
`MD_RequestIndex` bruger indekseret tekst i stedet.

Skal man kunne slå op i "mine items" serverside, skal der en indekseret
tekstkolonne med e-mailen ved siden af. Feltet `InitialOrstedResponsible`
(tekst, indeholder `NOABJ`) ligner et forsøg på netop det, men det er
initialer og ikke e-mail.

### Hele modellen hænger på opslagskolonner

| Liste | Opslagskolonner |
|---|---|
| `MaintenancePlans` | `StandardStrategy`, `SortField` |
| `MaintenanceItems` | `MaintenancePlanNo`, `MaintenanceActivityType`, `LubricationTaskType`, `MainWorkCenter` |
| `TaskListMain` | `MaintenanceItemNo`, `MaintenancePlanID` |

Opslagskolonner er **ikke delegerbare**. Med 34 planer, 58 items og 306
operationer er det uden betydning — alt er langt under 2.000. Men det
betyder, at appen skal hente hele sættet ned og filtrere klientside, og at
loftet er 2.000 rækker pr. liste, ikke 30.000.

Det er en bevidst afvejning, ikke en fejl. Den skal bare være skrevet ned,
så ingen bliver overrasket den dag `TaskListMain` runder 2.000.

## 2. De seks tasklist-lister er den samme liste seks gange

42 af 42 kolonner er identiske. Kun `AVV Standard Tasklist` har en ekstra,
`Test1`, uden indhold.

Men de interne navne er `field_1` … `field_36` — de er oprettet med
**"opret liste fra Excel"**. Visningsnavnene er SAP's egne kolonneoverskrifter
fra IA01:

```
field_1  SOp        field_5  Operation short text   field_17 Functional Location
field_2  Work Ctr   field_6  Work                   field_30 /
field_4  Ctrl       field_9  NorDur                 field_32 Cost elem.
```

En kolonne, der hedder `/`. Og `Un.`, `Uni.`, `Int. distr`, `Matl Group`.
I Power Fx skal de stå i enkelte anførselstegn, og `/` er reelt ubrugelig.

**Anbefaling:** slå de seks sammen til én liste, `StandardTasklistOperations`,
med en indekseret `Plant`-kolonne og rigtige interne navne. Det er den
klareste gevinst i hele modellen:

- seks lister at vedligeholde bliver til én
- appen har allerede **én** samling, `colVhpTasklists`, med et `Plant`-felt —
  så koden bliver simplere, ikke mere kompliceret
- `field_23` bliver til `WorkTimeType`, og den næste, der læser koden, kan se
  hvad den gør
- 176 rækker i alt. Migreringen er triviel

Af de 36 kolonner er kun en håndfuld i brug i appen i dag: operationsnummer,
kort tekst, arbejde, varighed, arbejdscenter, styringsnøgle, værk. Resten er
SAP-felter, der fulgte med eksporten. De kan tages med eller skæres væk —
men det skal være et valg, ikke en tilfældighed.

## 3. Nøglerne

Modellen har sine egne forretningsnøgler ved siden af SharePoints `ID`:

```
MaintenancePlans.PlanID      MP0062
MaintenanceItems.ItemID      MI0073     -> MaintenancePlanNo opslag paa PlanID
TaskListMain.TaskItemID      TI0056     -> MaintenanceItemNo opslag paa ItemID
TaskListMain.TaskID          TL0002     -- grupperer operationerne i en arbejdsplan
TaskListMain.Index           sortering af operationerne
```

Numrene kommer fra `AppSettings`, som har en tæller pr. miljø:

```
{Environment: DEV, Option: RunningNoPlan, Value: 5}
{Environment: DEV, Option: RunningNoItem, Value: 6}
{Environment: DEV, Option: RunningNoTask, Value: 1}
```

**Det er en kapløbstilstand.** To brugere, der indsender samtidig, læser
samme tal og får samme `MP`-nummer. Med en håndfuld brugere sker det sjældent
— men når det sker, er det to planer med samme nøgle, og det opdages først i
SAP. Enten flyttes tællingen til et flow med en lås, eller nøglen gøres
kollisionsfri på anden vis (dato + bruger + løbenummer).

`AppSettings` indeholder også app-URL'er pr. miljø (DEV, TEST, PROD).

> **Rettelse.** Jeg skrev først, at URL'en i `hub_config.py` var forkert, fordi
> den ikke matchede nogen af dem. Det modsatte er tilfældet: `hub_config.py`
> er rigtig, og **`AppSettings` er ikke opdateret**. Rettes der noget, er det
> listen — ikke konfigurationen. Det er i øvrigt et argument for, at hubben
> henter `AppUrl` fra indeksrækken og ikke fra en central liste, ingen husker
> at vedligeholde.

## 4. Strategipakkerne findes ikke

`StandardStrategyList` har præcis én kolonne, `Title`, og tre rækker:

```
100 - Taeller 250-1000-1250 timer
101 - 1-3-6-12-36 md eftersyn
102 - 1-12 md. eftersyn
```

Pakkestrukturen står som **fritekst i navnet**. Der er ingen `PackageNo`,
ingen `ShortCode`, ingen `CycleLength`, intet `Hierarchy`. Der er heller
ingen liste, der binder en operation til en pakke.

`MaintenancePlans.Package` er en enkelt Choice — `Main pack. 1` … `Main pack. 7`
— altså **én** pakke pr. plan, ikke en matrix pr. operation.
`MultiCounterStrategy` er en separat choice med seks BIO-strategier
(`100001 - BIO 6 Mon or 166 Counter Days` osv.).

Det betyder, at hele pakkematricen i appen er **ny funktionalitet uden
backend**. Den skal bygges:

| Ny liste | Kolonner |
|---|---|
| `MD_StrategyPackage` | `StrategyKey`, `PackageNo`, `ShortCode`, `CycleLength`, `CycleUnit`, `Hierarchy`, `PackageText` |

og `TaskListMain` skal have en `PackagesKey`-tekstkolonne (`;1;3;5;`) til
allokeringen. Se `docs/02-datamodel-sharepoint.md`.

**Opdatering:** strategierne er hentet (53 stk., `sharepoint/Strategier.txt`),
og pakkerne for **strategi 128** er aflæst i IP11 og ligger i
`sharepoint/seed/MD_StrategyPackage.csv`. De øvrige 52 mangler stadig pakker.

## 5. Småting

- **`PlantList` har 6 rækker**, men `MaintenancePlans.PlantsInitial` har 8
  valg: ASV, AVV, HEV, HCV, KYV, SKV, SMV, SSV. `STV` fra mine testdata
  findes ikke — det var opfundet. Enten udfyldes listen, eller også droppes
  den til fordel for choice-kolonnen.
- **`MainWorkCenters`** bruger også `field_1`/`field_2` (Excel-import), og
  værdierne er **polstret med mellemrum**: `'SKVAP   '`, `'SKV Anlægsprioritering    '`.
  Det skal trimmes, ellers matcher opslag ikke.
- **Fritekst gemmes som HTML** med `ExternalClass…`-wrappere i `ItemDescription`
  og `LongText`. Det skal strippes, før det går til SAP — et langtekstfelt i
  IA01 vil ikke have `<div>`.
- **`ObjectList`** er en Note med `|||` som separator. Det matcher appens eget
  format.
- **`StandardTaskList`** (3 rækker: Test1, Test2, Test3) er rene testdata.
  `TaskListMain.StandardTaskItemID` peger på den — afklar om den er i brug
  eller en rest.
- **`Vendors`** har `VendorNumber` (`325439`), men `TaskListMain.Vendor` er
  **tekst** med hele strengen `101985 - PERSOLIT ENTREPRENØRFIRMA A/S`, og
  numrene matcher ikke serien i `Vendors`. To kilder til leverandører.
- **`UserAndGroups`** er `Title` (rolle) + `Member` (e-mail). Rollestyring.
  Kan genbruges til hubbens "Til behandling"-kø.

## 6. Hvad jeg foreslår

**Kobl på det der findes** — planer, items, operationer og opslagslisterne er
brugbare som de er. Det er ikke værd at bygge om.

**Lav om på tre ting:**

1. Slå de seks tasklist-lister sammen til én med rigtige kolonnenavne.
2. Ryd op i de to CallHorizon-kolonner, før nogen skriver et migreringsscript.
3. Opret `MD_StrategyPackage` og `PackagesKey` — de findes ikke, og
   strategidelen kan ikke virke uden.

**Afklar to ting, før jeg skriver mapningen færdig:**

1. Skal appen **skrive** til `MaintenancePlans`/`MaintenanceItems`/`TaskListMain`,
   eller er de læsekilder med en ny indsendelsesliste ved siden af? Det afgør,
   om løbenummer-kapløbet skal løses nu eller senere.
2. ~~Rummer `TaskListMain` både skabeloner og konkrete operationer?~~
   **Besvaret ved at læse alle 306 rækker:** nej. 305 af 306 har
   `MaintenanceItemNo` — listen indeholder kun konkrete operationer. Se
   [`10-datamodel-forslag.md`](10-datamodel-forslag.md) §1.

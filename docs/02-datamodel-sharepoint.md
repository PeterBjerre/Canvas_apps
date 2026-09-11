# SharePoint-datamodel

Konventioner:

- **Intern navn = vist navn uden mellemrum.** Opret altid kolonnen med det
  ønskede interne navn først; SharePoint låser det interne navn ved oprettelse
  (og laver `_x0020_` af mellemrum). PnP-scriptet i
  `sharepoint/provision/Provision-VHPlanLists.ps1` gør det rigtigt.
- **Relationer er `Number`, ikke `Lookup`.** Begrundelse i `01-loesningsoplaeg.md` §9.
- **Kodefelter er `Text`, ikke `Choice`,** når værdisættet kommer fra SAP
  (strategier, ordretyper, arbejdscentre). Choice-kolonner kan ikke
  vedligeholdes af et sync-flow. Choice bruges kun til appens egne,
  stabile domæner (status, plantype).
- **Ⓘ = indekseret kolonne.**

---

## 1. Masterdata

### `MD_Strategy` – vedligeholdsstrategier (IP11)

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text(6) Ⓘ | Strateginøgle, fx `Z-MONTH` |
| `StrategyText` | Text(255) | Beskrivelse |
| `SchedIndicator` | Choice | `TIME`, `TIME_KEYDATE`, `TIME_FACTCAL`, `PERFORMANCE` |
| `PerformanceUnit` | Text(3) | Kun ved `PERFORMANCE`, fx `H`, `KM` |
| `CallHorizonPct` | Number 0–100 | Kaldshorisont |
| `SchedPeriod` | Number | Planlægningsperiode |
| `SchedPeriodUnit` | Choice | `DAY`,`WK`,`MON`,`YR` |
| `ShiftFactorLatePct` | Number | Forskydningsfaktor ved sen udførelse |
| `ShiftFactorEarlyPct` | Number | Forskydningsfaktor ved tidlig udførelse |
| `TolerdanceLatePct` | Number | Tolerance sen |
| `ToleranceEarlyPct` | Number | Tolerance tidlig |
| `FactoryCalendar` | Text(2) | |
| `Plant` | Text(4) Ⓘ | Tom = gælder alle værker |
| `IsActive` | Yes/No Ⓘ | |
| `SortOrder` | Number | |

### `MD_StrategyPackage` – pakker pr. strategi

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text | Sammensat nøgle `Z-MONTH-02` – gør dubletter synlige |
| `StrategyKey` | Text(6) Ⓘ | **Tekst, ikke lookup** – filtreres delegerbart |
| `PackageNo` | Number Ⓘ | 1..n. Den værdi der står i `PackagesKey` |
| `CycleLength` | Number | |
| `CycleUnit` | Choice | `DAY`,`WK`,`MON`,`YR`,`H`,`KM` |
| `PackageText` | Text(60) | Fx "Kvartalsvis eftersyn" |
| `ShortCode` | Text(6) | Kolonneoverskrift i matricen, fx `M3` |
| `Hierarchy` | Number | Højere tal = mere omfattende pakke |
| `Offset` | Number | Forskydning af første forfald |
| `PrelimBufferDays` | Number | Forpuffer |
| `SubseqBufferDays` | Number | Efterpuffer |
| `ColorHex` | Text(7) | Bruges af HTML-tidslinjen, fx `#2d7ff9` |
| `IsActive` | Yes/No | |

> **Unikhed:** SharePoint kan kun håndhæve unikhed på én kolonne. Sæt
> "Enforce unique values" på `Title` og hold formatet `<strategi>-<pakkenr>`.

### `MD_ValueHelp` – generel opslagsliste

I stedet for otte små lister (planlæggergrupper, arbejdscentre, ordretyper,
aktivitetstyper, notifikationstyper, styringsnøgler, værker, enheder) bruges
**én** liste med et domænefelt. Det halverer provisioneringen, giver ét
sync-flow i stedet for otte, og holder appen under grænsen for antal
datakilder.

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text Ⓘ | Koden, fx `PM01` |
| `Domain` | Text(30) Ⓘ | `PLANNERGROUP`, `WORKCENTER`, `ORDERTYPE`, `CONTROLKEY`, `ACTTYPE`, `NOTIFTYPE`, `PLANT`, `CYCLEUNIT`, `TASKLISTUSAGE`, `SYSTEMCONDITION` |
| `DisplayText` | Text(255) | |
| `Plant` | Text(4) Ⓘ | Tom = globalt |
| `ParentCode` | Text | Til afhængige dropdowns (fx arbejdscenter under værk) |
| `IsActive` | Yes/No Ⓘ | |
| `SortOrder` | Number | |

Sammensat indeks på `Domain` + `IsActive` er det, der bærer alle appens
dropdowns.

---

## 2. Transaktionsdata

### `VHP_Request` – anmodningshoved

**Identitet og status**

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text Ⓘ | Anmodningsnr. `VHP-2026-00042`. Sættes i to trin: opret → patch `Title` med `"VHP-" & Year(Now()) & "-" & Text(ID,"00000")`. Undgår en race på en tællerliste |
| `RequestGuid` | Text(36) Ⓘ | Genereres i appen med `GUID()` **før** første skrivning. Idempotensnøgle mod SAP |
| `Status` | Choice Ⓘ | `Kladde`,`Indsendt`,`UnderBehandling`,`Afvist`,`KlarTilSAP`,`OprettetISAP`,`Fejlet`,`Annulleret` |
| `PlanType` | Choice Ⓘ | `SingleCycle`,`Strategy` (`MultipleCounter` reserveret) |

**Planhoved (IP41/IP42 header)**

| Kolonne | Type | Bemærkning |
|---|---|---|
| `PlanDescription` | Text(40) | SAP-feltlængde er 40 – valider i appen |
| `PlanCategory` | Text(2) | Fx `PM` |
| `PlanSortField` | Text(30) | Anbefaling: skriv `RequestGuid`-prefix her, så planen kan findes tilbage i SAP |
| `PlanningPlant` | Text(4) Ⓘ | |
| `StrategyKey` | Text(6) Ⓘ | Tom ved single cycle |
| `StrategyTextSnapshot` | Text(255) | Frosset ved submit |
| `SingleCycleLength` | Number | Kun single cycle |
| `SingleCycleUnit` | Text(3) | Kun single cycle |

**Planlægningsparametre** (defaultes fra strategien, kan overskrives)

| Kolonne | Type |
|---|---|
| `SchedIndicator` | Text(20) |
| `CycleStartDate` | DateTime (kun dato) |
| `CallHorizonPct` | Number |
| `SchedPeriod` / `SchedPeriodUnit` | Number / Text(3) |
| `ShiftFactorLatePct` / `ShiftFactorEarlyPct` | Number |
| `ToleranceLatePct` / `ToleranceEarlyPct` | Number |
| `CycleModFactor` | Number |
| `CompletionRequired` | Yes/No |
| `FactoryCalendar` | Text(2) |

**Proces og integration**

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Requester` | Person | |
| `RequesterDept` | Text | |
| `Justification` | Note (plain) | Hvorfor skal planen oprettes |
| `ApprovedBy` / `ApprovedOn` | Person / DateTime | |
| `RejectReason` | Note | |
| `PayloadJson` | Note (plain, **append = nej**) | JSON-snapshot ved submit. Note-kolonner rummer 63.999 tegn – rigeligt til ~200 operationer, men se advarslen nedenfor |
| `SapMaintPlanNo` | Text(12) Ⓘ | |
| `SapTaskListGroups` | Text(255) | Kommasepareret, hvis appen også fik oprettet arbejdsplaner |
| `SapCreatedOn` / `SapCreatedBy` | DateTime / Text | |
| `IntegrationStatus` | Choice | `NotSent`,`Sent`,`Ack`,`Error` |
| `IntegrationMessage` | Note | |
| `IntegrationRetries` | Number | |

> **Advarsel om `PayloadJson`:** Note-kolonner kan ikke læses delegerbart og
> gør galleriets datahentning tung. Vis den **aldrig** i en gallery. Hent den
> kun i integrationsflowet med en `Get item` på ID. Hvis payloaden kan
> overstige ~60 kB, læg den som en JSON-fil i et dokumentbibliotek
> `VHP_Payloads` og gem kun URL'en her.

### `VHP_Item` – vedligeholdspositioner

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text(40) | Positionstekst |
| `RequestId` | Number Ⓘ | |
| `ItemNo` | Number | Sorteringsrækkefølge, 10, 20, 30 |
| `ObjectType` | Choice | `FunctionalLocation`,`Equipment`,`Assembly`,`NoObject` |
| `FunctionalLocation` | Text(40) | |
| `EquipmentNo` | Text(18) | |
| `AssemblyNo` | Text(18) | |
| `PlannerGroupCode` | Text(3) | |
| `MainWorkCenter` | Text(8) | |
| `OrderType` | Text(4) | |
| `ActivityType` | Text(3) | |
| `BusinessArea` | Text(4) | |
| `Priority` | Text(1) | |
| `NotifType` | Text(2) | |
| `TaskListMode` | Choice | `Existing`,`New`,`None` |
| `TaskListType` | Text(1) | `A` generel, `E` udstyr, `T` funktionsplads |
| `TaskListGroup` | Text(8) | Kun ved `Existing` |
| `TaskListCounter` | Text(2) | Kun ved `Existing` |
| `TaskListId` | Number Ⓘ | Peger på `VHP_TaskList`, kun ved `New` |

### `VHP_ItemObject` – objektliste pr. position

Kun nødvendig, når én position dækker flere tekniske objekter.

| Kolonne | Type |
|---|---|
| `Title` | Text (objekttekst) |
| `ItemId` | Number Ⓘ |
| `RequestId` | Number Ⓘ |
| `ObjectType` | Choice |
| `ObjectNo` | Text(40) |
| `SortNo` | Number |

### `VHP_TaskList` – ønsket ny arbejdsplan

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text(40) | Arbejdsplanbeskrivelse |
| `RequestId` | Number Ⓘ | |
| `TaskListType` | Text(1) | |
| `StrategyKey` | Text(6) | **Skal matche `VHP_Request.StrategyKey`** – regel S3 |
| `Plant` | Text(4) | |
| `UsageCode` | Text(1) | |
| `PlannerGroupCode` | Text(3) | |
| `WorkCenter` | Text(8) | |
| `SystemCondition` | Text(1) | |
| `ExistingGroup` | Text(8) | Udfyldes af planlæggeren efter oprettelse i SAP |

### `VHP_Operation` – operationer og pakkeallokering

| Kolonne | Type | Bemærkning |
|---|---|---|
| `Title` | Text(40) | Operationens korttekst |
| `TaskListId` | Number Ⓘ | |
| `RequestId` | Number Ⓘ | Denormaliseret, så hele anmodningen kan hentes i ét kald |
| `OperationNo` | Text(4) | `0010`, `0020` ... |
| `LongText` | Note (plain) | |
| `WorkCenter` | Text(8) | |
| `ControlKey` | Text(4) | `PM01`, `PM02`, `PM03` |
| `Plant` | Text(4) | |
| `Work` | Number | Arbejde |
| `WorkUnit` | Text(3) | `H`, `MIN` |
| `NumberOfPeople` | Number | |
| `Duration` | Number | |
| `DurationUnit` | Text(3) | |
| `SystemCondition` | Text(1) | |
| **`PackagesKey`** | **Text(255)** | **`;1;3;5;` – matricens indhold. Altid mindst `;`** |
| `PackagesDisplay` | Text(255) | `M1, M3, M12` – kun til visning/eksport, genereres af appen |
| `SortOrder` | Number | |

`Text(255)` rummer op til ca. 60 pakkenumre. SAP-strategier har typisk 3–8,
så der er rigelig plads.

### `VHP_StatusLog`

| Kolonne | Type |
|---|---|
| `Title` | Text (auto: `<RequestNo> <Til-status>`) |
| `RequestId` | Number Ⓘ |
| `FromStatus` / `ToStatus` | Text |
| `ActionBy` | Person |
| `ActionOn` | DateTime |
| `Comment` | Note |

### `VHP_OperationPackage` *(valgfri, afledt)*

Oprettes **kun** hvis der kommer et rapporteringsbehov. Fyldes af et flow ved
submit ud fra `PackagesKey`, aldrig af appen. Kan altid genopbygges.

| Kolonne | Type |
|---|---|
| `Title` | Text |
| `RequestId` / `OperationId` | Number Ⓘ |
| `StrategyKey` | Text Ⓘ |
| `PackageNo` | Number Ⓘ |

---

## 3. Indekser der skal oprettes

SharePoint tillader maks. 20 indekser pr. liste, og et indeks skal oprettes,
**før** listen passerer 5.000 elementer — bagefter kræver det et
vedligeholdelsesvindue.

| Liste | Indekser |
|---|---|
| `MD_ValueHelp` | `Domain`, `IsActive`, `Plant` |
| `MD_StrategyPackage` | `StrategyKey`, `PackageNo` |
| `VHP_Request` | `Status`, `RequestGuid`, `PlanType`, `Created`, `SapMaintPlanNo` |
| `VHP_Item` | `RequestId`, `TaskListId` |
| `VHP_ItemObject` | `ItemId`, `RequestId` |
| `VHP_TaskList` | `RequestId` |
| `VHP_Operation` | `RequestId`, `TaskListId` |
| `VHP_StatusLog` | `RequestId` |

## 4. Sletning og oprydning

SharePoint har ingen cascade delete, når relationer er talfelter. To
mekanismer:

1. **I appen:** sletning af en anmodning i status `Kladde` sletter
   eksplicit børn i rækkefølgen operation → tasklist → itemobject → item →
   request. Kør det i ét `Concurrent()` pr. niveau.
2. **Natligt oprydningsflow:** find rækker i børnelisterne, hvis `RequestId`
   ikke længere findes i `VHP_Request`, og slet dem. Det fanger afbrudte
   sletninger og gør mekanisme 1 ikke-kritisk.

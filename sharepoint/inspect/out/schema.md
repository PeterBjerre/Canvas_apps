# SharePoint-lister bag VH-plan appen

Udtrukket 2026-09-14 22:21 fra https://orsted.sharepoint.com/teams/BioSAPDEV.
Data med: ja.

| Liste | Raekker | Kolonner |
|---|---:|---:|
| `AppSettings` | 6 | 13 |
| `ASV Standard Tasklist` | 26 | 42 |
| `AVV Standard Tasklist` | 37 | 43 |
| `CallHorizonMatrix` | 16 | 10 |
| `HEV Standard Tasklist` | 30 | 42 |
| `KYV Standard Tasklist` | 20 | 42 |
| `LubricationTaskTypeList` | 2 | 6 |
| `MaintenanceActivityTypeList` | 7 | 7 |
| `MaintenanceItems` | 58 | 33 |
| `MaintenancePlans` | 34 | 27 |
| `MainWorkCenters` | 53 | 8 |
| `MD_RequestIndex` | 18 | 23 |
| `PlantList` | 6 | 6 |
| `SKV Standard Tasklist` | 31 | 42 |
| `SortFieldList` | 28 | 6 |
| `SSV Standard Tasklist` | 32 | 42 |
| `StandardStrategyList` | 3 | 6 |
| `StandardTaskList` | 3 | 12 |
| `TaskListMain` | 306 | 28 |
| `UserAndGroups` | 7 | 7 |
| `Vendors` | 20 | 7 |

## `AppSettings`  -  6 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `Environment` | Environment | Choice |  |  | valg: DEV, TEST, PROD |
| `AppID` | AppID | Text |  |  |  |
| `Notes` | Notes | Note |  |  |  |
| `AppUrl` | AppUrl | URL |  |  |  |
| `Option` | Option | Choice |  |  | valg: RunningNoPlan, PowerApps, RunningNoItem, RunningNoTask |
| `Value` | Value | Number |  |  |  |
| `EnvironmentID` | EnvironmentID | Text |  | x |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `ASV Standard Tasklist`  -  26 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **SOp** | Number |  |  |  |
| `field_2` | **Work Ctr** | Text |  |  |  |
| `field_3` | **Plnt** | Number |  |  |  |
| `field_4` | **Ctrl** | Text |  |  |  |
| `field_5` | **Operation short text** | Text |  |  |  |
| `field_6` | **Work** | Number |  |  |  |
| `field_7` | **Un.** | Text |  |  |  |
| `field_8` | **No.** | Number |  |  |  |
| `field_9` | **NorDur** | Number |  |  |  |
| `field_10` | **Uni.** | Text |  |  |  |
| `field_11` | **Calc** | Number |  |  |  |
| `field_12` | **Pct** | Number |  |  |  |
| `field_13` | **Int. distr** | Number |  |  |  |
| `field_14` | **Fac** | Number |  |  |  |
| `field_15` | **ActTyp** | Text |  |  |  |
| `field_16` | **StTextKy** | Text |  |  |  |
| `field_17` | **Functional Location** | Number |  |  |  |
| `field_18` | **Equipment** | Number |  |  |  |
| `field_19` | **Assembly** | Number |  |  |  |
| `field_20` | **Service Object** | Number |  |  |  |
| `field_21` | **TT** | Number |  |  |  |
| `field_22` | **Wage Group** | Number |  |  |  |
| `field_23` | **WT** | Number |  |  |  |
| `field_24` | **Suit** | Number |  |  |  |
| `field_25` | **System Condition** | Number |  |  |  |
| `field_26` | **OrdQuantity** | Number |  |  |  |
| `field_27` | **Unit** | Text |  |  |  |
| `field_28` | **Price** | Number |  |  |  |
| `field_29` | **Crcy** | Text |  |  |  |
| `field_30` | **/** | Number |  |  |  |
| `field_31` | **PDT** | Number |  |  |  |
| `field_32` | **Cost elem.** | Number |  |  |  |
| `field_33` | **Matl Group** | Text |  |  |  |
| `field_34` | **PGr** | Text |  |  |  |
| `field_35` | **Vendor** | Number |  |  |  |
| `field_36` | **POrg** | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `AVV Standard Tasklist`  -  37 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **SOp** | Number |  |  |  |
| `field_2` | **Work Ctr** | Text |  |  |  |
| `field_3` | **Plnt** | Number |  |  |  |
| `field_4` | **Ctrl** | Text |  |  |  |
| `field_5` | **Operation short text** | Text |  |  |  |
| `field_6` | **Work** | Number |  |  |  |
| `field_7` | **Un.** | Text |  |  |  |
| `field_8` | **No.** | Number |  |  |  |
| `field_9` | **NorDur** | Number |  |  |  |
| `field_10` | **Uni.** | Text |  |  |  |
| `field_11` | **Calc** | Number |  |  |  |
| `field_12` | **Pct** | Number |  |  |  |
| `field_13` | **Int. distr** | Number |  |  |  |
| `field_14` | **Fac** | Number |  |  |  |
| `field_15` | **ActTyp** | Text |  |  |  |
| `field_16` | **StTextKy** | Text |  |  |  |
| `field_17` | **Functional Location** | Number |  |  |  |
| `field_18` | **Equipment** | Number |  |  |  |
| `field_19` | **Assembly** | Number |  |  |  |
| `field_20` | **Service Object** | Number |  |  |  |
| `field_21` | **TT** | Number |  |  |  |
| `field_22` | **Wage Group** | Number |  |  |  |
| `field_23` | **WT** | Number |  |  |  |
| `field_24` | **Suit** | Number |  |  |  |
| `field_25` | **System Condition** | Number |  |  |  |
| `field_26` | **OrdQuantity** | Number |  |  |  |
| `field_27` | **Unit** | Text |  |  |  |
| `field_28` | **Price** | Number |  |  |  |
| `field_29` | **Crcy** | Text |  |  |  |
| `field_30` | **/** | Number |  |  |  |
| `field_31` | **PDT** | Number |  |  |  |
| `field_32` | **Cost elem.** | Number |  |  |  |
| `field_33` | **Matl Group** | Text |  |  |  |
| `field_34` | **PGr** | Text |  |  |  |
| `field_35` | **Vendor** | Number |  |  |  |
| `field_36` | **POrg** | Number |  |  |  |
| `Test1` | Test1 | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `CallHorizonMatrix`  -  16 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **CycleOrUnit** | Text |  |  |  |
| `field_2` | **NewCallHorizonOrFCD** | Number |  |  |  |
| `field_3` | **SchedulingPeriod** | Text |  |  |  |
| `SchedulingPeriodNum` | SchedulingPeriodNum | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `HEV Standard Tasklist`  -  30 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **SOp** | Number |  |  |  |
| `field_2` | **Work Ctr** | Text |  |  |  |
| `field_3` | **Plnt** | Number |  |  |  |
| `field_4` | **Ctrl** | Text |  |  |  |
| `field_5` | **Operation short text** | Text |  |  |  |
| `field_6` | **Work** | Number |  |  |  |
| `field_7` | **Un.** | Text |  |  |  |
| `field_8` | **No.** | Number |  |  |  |
| `field_9` | **NorDur** | Number |  |  |  |
| `field_10` | **Uni.** | Text |  |  |  |
| `field_11` | **Calc** | Number |  |  |  |
| `field_12` | **Pct** | Number |  |  |  |
| `field_13` | **Int. distr** | Number |  |  |  |
| `field_14` | **Fac** | Number |  |  |  |
| `field_15` | **ActTyp** | Text |  |  |  |
| `field_16` | **StTextKy** | Text |  |  |  |
| `field_17` | **Functional Location** | Number |  |  |  |
| `field_18` | **Equipment** | Number |  |  |  |
| `field_19` | **Assembly** | Number |  |  |  |
| `field_20` | **Service Object** | Number |  |  |  |
| `field_21` | **TT** | Number |  |  |  |
| `field_22` | **Wage Group** | Number |  |  |  |
| `field_23` | **WT** | Number |  |  |  |
| `field_24` | **Suit** | Number |  |  |  |
| `field_25` | **System Condition** | Number |  |  |  |
| `field_26` | **OrdQuantity** | Number |  |  |  |
| `field_27` | **Unit** | Text |  |  |  |
| `field_28` | **Price** | Number |  |  |  |
| `field_29` | **Crcy** | Text |  |  |  |
| `field_30` | **/** | Number |  |  |  |
| `field_31` | **PDT** | Number |  |  |  |
| `field_32` | **Cost elem.** | Number |  |  |  |
| `field_33` | **Matl Group** | Text |  |  |  |
| `field_34` | **PGr** | Text |  |  |  |
| `field_35` | **Vendor** | Number |  |  |  |
| `field_36` | **POrg** | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `KYV Standard Tasklist`  -  20 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **SOp** | Number |  |  |  |
| `field_2` | **Work Ctr** | Text |  |  |  |
| `field_3` | **Plnt** | Number |  |  |  |
| `field_4` | **Ctrl** | Text |  |  |  |
| `field_5` | **Operation short text** | Text |  |  |  |
| `field_6` | **Work** | Number |  |  |  |
| `field_7` | **Un.** | Text |  |  |  |
| `field_8` | **No.** | Number |  |  |  |
| `field_9` | **NorDur** | Number |  |  |  |
| `field_10` | **Uni.** | Text |  |  |  |
| `field_11` | **Calc** | Number |  |  |  |
| `field_12` | **Pct** | Number |  |  |  |
| `field_13` | **Int. distr** | Number |  |  |  |
| `field_14` | **Fac** | Number |  |  |  |
| `field_15` | **ActTyp** | Text |  |  |  |
| `field_16` | **StTextKy** | Text |  |  |  |
| `field_17` | **Functional Location** | Number |  |  |  |
| `field_18` | **Equipment** | Number |  |  |  |
| `field_19` | **Assembly** | Number |  |  |  |
| `field_20` | **Service Object** | Number |  |  |  |
| `field_21` | **TT** | Number |  |  |  |
| `field_22` | **Wage Group** | Number |  |  |  |
| `field_23` | **WT** | Number |  |  |  |
| `field_24` | **Suit** | Number |  |  |  |
| `field_25` | **System Condition** | Number |  |  |  |
| `field_26` | **OrdQuantity** | Number |  |  |  |
| `field_27` | **Unit** | Text |  |  |  |
| `field_28` | **Price** | Number |  |  |  |
| `field_29` | **Crcy** | Text |  |  |  |
| `field_30` | **/** | Number |  |  |  |
| `field_31` | **PDT** | Number |  |  |  |
| `field_32` | **Cost elem.** | Number |  |  |  |
| `field_33` | **Matl Group** | Text |  |  |  |
| `field_34` | **PGr** | Text |  |  |  |
| `field_35` | **Vendor** | Number |  |  |  |
| `field_36` | **POrg** | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `LubricationTaskTypeList`  -  2 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `MaintenanceActivityTypeList`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `TypeNo` | TypeNo | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `MaintenanceItems`  -  58 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text | x |  |  |
| `Status` | Status | Choice |  |  | valg: New, Change, Deleted |
| `MaintenancePlanNo` | MaintenancePlanNo | Lookup | x |  | opslag -> 55c96ba9-52b8-4018-8945-f736b001d6a2 (PlanID) |
| `ItemDescription` | ItemDescription | Note | x |  |  |
| `FunctionalLocation` | FunctionalLocation | Text | x |  |  |
| `Priority` | Priority | Choice | x |  | valg: Red (Statutory and SCEq), Yellow (default), Blue (standing order), (Kun notification) 3 Within a week, (Kun notification) 4 Within a month |
| `Cosmetic` | Cosmetic | Text |  |  |  |
| `OrstedResponsible` | OrstedResponsible | User | x |  | opslag -> UserInfo (ImnName) |
| `FlowUserStatus` | FlowUserStatus | Choice |  |  | valg: REPL, REPR, RESC |
| `NonFlowUserStatus` | NonFlowUserStatus | Choice |  |  | valg: ZBOW |
| `ObjectList` | ObjectList | Note |  |  |  |
| `MaintenanceActivityType` | MaintenanceActivityType | Lookup | x |  | opslag -> 5af59bfc-14ec-486a-919b-f09b7801818e (Title) |
| `LubricationTaskType` | LubricationTaskType | Lookup |  |  | opslag -> ebae39cb-451f-4287-845f-2c76133e6489 (Title) |
| `MainWorkCenter` | MainWorkCenter | Lookup | x |  | opslag -> d940c836-7b7d-4797-b09f-35862054f887 (Title) |
| `RevisionMark` | RevisionMark | Choice |  |  | valg: REV - General Revision Mark |
| `TaskListGroup` | TaskListGroup | Text |  |  |  |
| `TaskListGroupCounter` | TaskListGroupCounter | Text |  |  |  |
| `WCMDispensation` | WCMDispensation | Choice |  |  | valg: Yes, No |
| `MeasuringPoint` | MeasuringPoint | Text |  |  |  |
| `PRODOSTAG` | PRODOSTAG | Text |  |  |  |
| `MeasurementCollectionFrequency` | MeasurementCollectionFrequency | Choice |  |  | valg: Daily, Weekly |
| `ItemID` | ItemID | Text |  |  |  |
| `UserStatus` | UserStatus | Choice |  |  | valg: REPL |
| `OrderType` | OrderType | Choice |  |  | valg: ZPRE |
| `Revision` | Revision | Boolean |  |  |  |
| `InitialOrstedResponsible` | InitialOrstedResponsible | Text |  |  |  |
| `SCEqFL` | SCEqFL | Text |  |  |  |
| `SCEqOL` | SCEqOL | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `MaintenancePlans`  -  34 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text | x |  |  |
| `Status` | Status | Choice | x |  | valg: Draft, In Progress, Ready for creation in SAP, Published |
| `MultiCounterStrategy` | MultiCounterStrategy | Choice |  |  | valg: 100001 - BIO 6 Mon or 166 Counter Days, 100002 - BIO 12 Mon or 166 Counter Days, 100003 - BIO 12 Mon or 208 Counter Days, 100004 - BIO 12 Mon or 250 Counter Days, 100005 - BIO 12 Mon or 333 Counter Days, 100006 - BIO 12 Mon or 354 Counter Days |
| `Cycle` | Cycle | Number | x |  |  |
| `Unit` | Unit | Choice | x |  | valg: H, DAY, WK, MON, YR |
| `PlannedDate` | PlannedDate | DateTime | x |  |  |
| `CallHorizon` | **CallHorizonOLD** | Choice |  |  | valg: 2 Days (1 WK), 7 Days (2 WK), 15 Days (1 MON), 20 Days (6 WK), 40 days (2-4 MON), 45 days (6 MON), 50 Days, 55 days (1 YR), 60 days (2 YR), 65 days (3 YR), 70 days (4 YR), 80 Days (5 & 6 YR) |
| `SchedulingIndicator` | SchedulingIndicator | Choice |  |  | valg: JA, NEJ |
| `Package` | Package | Choice |  |  | valg: Main pack. 1, Main pack. 2, Main pack. 3, Main pack. 4, Main pack. 5, Main pack. 6, Main pack. 7 |
| `PlantsInitial` | PlantsInitial | Choice | x |  | valg: ASV, AVV, HEV, HCV, KYV, SKV, SMV, SSV |
| `Cosmetic` | Cosmetic | Text |  |  |  |
| `StandardStrategy` | StandardStrategy | Lookup |  |  | opslag -> 118c22ce-bbc8-415f-bf1a-ce148361c9b1 (Title) |
| `SortField` | SortField | Lookup |  |  | opslag -> 33cb4a5b-7faa-4f8c-b42e-d5d5844201a8 (Title) |
| `EditLink` | EditLink | Text |  |  |  |
| `PlanID` | PlanID | Text |  |  |  |
| `CallHorizon0` | **CallHorizon** | Number |  |  |  |
| `CallHorizonUnit` | CallHorizonUnit | Choice |  |  | valg: FCD |
| `SchedulingPeriod` | SchedulingPeriod | Number |  |  |  |
| `SchedulingPeriodUnit` | SchedulingPeriodUnit | Choice |  |  | valg: YR |
| `PlanType` | PlanType | Choice |  |  | valg: PM |
| `InitialEmailSent` | InitialEmailSent | Boolean |  |  |  |
| `SAPNum` | SAPNum | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `MainWorkCenters`  -  53 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **Description                              ** | Text |  |  |  |
| `field_2` | **Plant Key** | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `MD_RequestIndex`  -  18 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **RequestNo** | Text | x | x |  |
| `Domain` | Domain | Choice | x | x | valg: FunctionalLocation, Equipment, MeasuringPoint, Material, MaintenancePlan |
| `Status` | Status | Choice | x | x | valg: Kladde, Indsendt, UnderBehandling, AfventerInfo, KlarTilSAP, OprettetISAP, Afvist, Annulleret |
| `StatusStep` | StatusStep | Number |  |  |  |
| `IsOpen` | IsOpen | Boolean |  | x |  |
| `RequestGuid` | RequestGuid | Text |  | x |  |
| `RequesterEmail` | RequesterEmail | Text | x | x |  |
| `RequesterName` | RequesterName | Text |  |  |  |
| `AssignedToEmail` | AssignedToEmail | Text |  | x |  |
| `AssignedToName` | AssignedToName | Text |  |  |  |
| `ShortText` | ShortText | Text |  |  |  |
| `Plant` | Plant | Text |  | x |  |
| `ItemCount` | ItemCount | Number |  |  |  |
| `SapObjectNo` | SapObjectNo | Text |  |  |  |
| `SourceItemId` | SourceItemId | Number |  |  |  |
| `AppUrl` | AppUrl | Text |  |  |  |
| `LastActionOn` | LastActionOn | DateTime |  | x |  |
| `LastActionBy` | LastActionBy | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `PlantList`  -  6 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `SKV Standard Tasklist`  -  31 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **SOp** | Number |  |  |  |
| `field_2` | **Work Ctr** | Text |  |  |  |
| `field_3` | **Plnt** | Number |  |  |  |
| `field_4` | **Ctrl** | Text |  |  |  |
| `field_5` | **Operation short text** | Text |  |  |  |
| `field_6` | **Work** | Number |  |  |  |
| `field_7` | **Un.** | Text |  |  |  |
| `field_8` | **No.** | Number |  |  |  |
| `field_9` | **NorDur** | Number |  |  |  |
| `field_10` | **Uni.** | Text |  |  |  |
| `field_11` | **Calc** | Number |  |  |  |
| `field_12` | **Pct** | Number |  |  |  |
| `field_13` | **Int. distr** | Number |  |  |  |
| `field_14` | **Fac** | Number |  |  |  |
| `field_15` | **ActTyp** | Text |  |  |  |
| `field_16` | **StTextKy** | Text |  |  |  |
| `field_17` | **Functional Location** | Number |  |  |  |
| `field_18` | **Equipment** | Number |  |  |  |
| `field_19` | **Assembly** | Number |  |  |  |
| `field_20` | **Service Object** | Number |  |  |  |
| `field_21` | **TT** | Number |  |  |  |
| `field_22` | **Wage Group** | Number |  |  |  |
| `field_23` | **WT** | Number |  |  |  |
| `field_24` | **Suit** | Number |  |  |  |
| `field_25` | **System Condition** | Number |  |  |  |
| `field_26` | **OrdQuantity** | Number |  |  |  |
| `field_27` | **Unit** | Text |  |  |  |
| `field_28` | **Price** | Number |  |  |  |
| `field_29` | **Crcy** | Text |  |  |  |
| `field_30` | **/** | Number |  |  |  |
| `field_31` | **PDT** | Number |  |  |  |
| `field_32` | **Cost elem.** | Number |  |  |  |
| `field_33` | **Matl Group** | Text |  |  |  |
| `field_34` | **PGr** | Text |  |  |  |
| `field_35` | **Vendor** | Number |  |  |  |
| `field_36` | **POrg** | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `SortFieldList`  -  28 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `SSV Standard Tasklist`  -  32 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **SOp** | Number |  |  |  |
| `field_2` | **Work Ctr** | Text |  |  |  |
| `field_3` | **Plnt** | Number |  |  |  |
| `field_4` | **Ctrl** | Text |  |  |  |
| `field_5` | **Operation short text** | Text |  |  |  |
| `field_6` | **Work** | Number |  |  |  |
| `field_7` | **Un.** | Text |  |  |  |
| `field_8` | **No.** | Number |  |  |  |
| `field_9` | **NorDur** | Number |  |  |  |
| `field_10` | **Uni.** | Text |  |  |  |
| `field_11` | **Calc** | Number |  |  |  |
| `field_12` | **Pct** | Number |  |  |  |
| `field_13` | **Int. distr** | Number |  |  |  |
| `field_14` | **Fac** | Number |  |  |  |
| `field_15` | **ActTyp** | Text |  |  |  |
| `field_16` | **StTextKy** | Text |  |  |  |
| `field_17` | **Functional Location** | Number |  |  |  |
| `field_18` | **Equipment** | Number |  |  |  |
| `field_19` | **Assembly** | Number |  |  |  |
| `field_20` | **Service Object** | Number |  |  |  |
| `field_21` | **TT** | Number |  |  |  |
| `field_22` | **Wage Group** | Number |  |  |  |
| `field_23` | **WT** | Number |  |  |  |
| `field_24` | **Suit** | Number |  |  |  |
| `field_25` | **System Condition** | Number |  |  |  |
| `field_26` | **OrdQuantity** | Number |  |  |  |
| `field_27` | **Unit** | Text |  |  |  |
| `field_28` | **Price** | Number |  |  |  |
| `field_29` | **Crcy** | Text |  |  |  |
| `field_30` | **/** | Number |  |  |  |
| `field_31` | **PDT** | Number |  |  |  |
| `field_32` | **Cost elem.** | Number |  |  |  |
| `field_33` | **Matl Group** | Text |  |  |  |
| `field_34` | **PGr** | Text |  |  |  |
| `field_35` | **Vendor** | Number |  |  |  |
| `field_36` | **POrg** | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `StandardStrategyList`  -  3 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `StandardTaskList`  -  3 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `OperationShortText` | OperationShortText | Text |  |  |  |
| `Work` | Work | Number |  |  |  |
| `Num` | Num | Number |  |  |  |
| `Duration` | Duration | Number |  |  |  |
| `Vendor` | Vendor | Number |  |  |  |
| `LongText` | LongText | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `TaskListMain`  -  306 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `OperationShortText` | OperationShortText | Text |  |  |  |
| `Work` | Work | Number |  |  |  |
| `Num` | Num | Number |  |  |  |
| `Duration` | Duration | Number |  |  |  |
| `Vendor` | Vendor | Text |  |  |  |
| `TaskID` | TaskID | Text |  |  |  |
| `MaintenanceItemNo` | MaintenanceItemNo | Lookup |  |  | opslag -> d0b2538e-c702-4375-b766-caf342259495 (ItemID) |
| `LongText` | LongText | Note |  |  |  |
| `PlantInitial` | PlantInitial | Text |  |  |  |
| `TaskItemID` | TaskItemID | Text |  |  |  |
| `StandardTaskItemID` | StandardTaskItemID | Number |  |  |  |
| `MaintenancePlanID` | MaintenancePlanID | Lookup |  |  | opslag -> 55c96ba9-52b8-4018-8945-f736b001d6a2 (PlanID) |
| `VendorID` | VendorID | Number |  |  |  |
| `Ctrl` | Ctrl | Text |  |  |  |
| `Materials` | Materials | Note |  |  |  |
| `AttachmentLink` | AttachmentLink | Text |  |  |  |
| `AttachmentHyperlink` | AttachmentHyperlink | URL |  |  |  |
| `Index` | Index | Number |  |  |  |
| `WorkCtr` | WorkCtr | Text |  |  |  |
| `CostElem` | CostElem | Number |  |  |  |
| `Price` | Price | Number |  |  |  |
| `Currency` | Currency | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `UserAndGroups`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `Member` | Member | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

## `Vendors`  -  20 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **VendorName** | Text |  |  |  |
| `VendorNumber` | VendorNumber | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (None); skrivebeskyttet |

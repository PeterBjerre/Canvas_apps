# SharePoint-lister bag VH-plan appen

Udtrukket 2026-10-08 23:09 fra https://orsted.sharepoint.com/teams/BioSAPDEV

| Liste | Raekker | Kolonner |
|---|---:|---:|
| `AppSettings` | 7 | 13 |
| `ASV Standard Tasklist` | 26 | 42 |
| `AVV Standard Tasklist` | 37 | 43 |
| `CallHorizonMatrix` | 16 | 10 |
| `EquipmentItems` | 3 | 32 |
| `FunctionalLocationItems` | 1 | 21 |
| `FunctionalLocationRequests` | 1 | 17 |
| `HEV Standard Tasklist` | 30 | 42 |
| `IB_AppSections` | 87 | 13 |
| `IB_TicketComments` | 9 | 20 |
| `IB_Tickets` | 6 | 30 |
| `KYV Standard Tasklist` | 20 | 42 |
| `LubricationTaskTypeList` | 2 | 6 |
| `MaintenanceActivityTypeList` | 7 | 7 |
| `MaintenanceItems` | 72 | 36 |
| `MaintenancePlans` | 50 | 40 |
| `MainWorkCenters` | 53 | 8 |
| `MaterialItems` | 2 | 32 |
| `MD_ApprovalLog` | 25 | 18 |
| `MD_Approver` | 31 | 10 |
| `MD_FLKey` | 6733 | 9 |
| `MD_HelpText` | 51 | 11 |
| `MD_KksFunctionKey` | 2913 | 9 |
| `MD_MpCharacteristic` | 7 | 12 |
| `MD_RequestIndex` | 34 | 24 |
| `MD_StandardTaskOperations` | 176 | 32 |
| `MD_Strategy` | 53 | 11 |
| `MD_StrategyPackage` | 3 | 14 |
| `MD_TasklistAttachment` | 1 | 13 |
| `MD_TasklistMaterial` | 7 | 14 |
| `MeasuringPointItems` | 0 | 41 |
| `PlantList` | 8 | 6 |
| `SKV Standard Tasklist` | 31 | 42 |
| `SortFieldList` | 28 | 6 |
| `SSV Standard Tasklist` | 32 | 42 |
| `StandardStrategyList` | 3 | 6 |
| `StandardTaskList` | 3 | 12 |
| `TaskListMain` | 364 | 32 |
| `UserAndGroups` | 7 | 7 |
| `Vendors` | 20 | 7 |
| `VHP_NoteToSelf` | 1 | 10 |

## `AppSettings`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `Environment` | Environment | Choice |  |  | valg: DEV, TEST, PROD |
| `AppID` | AppID | Text |  |  |  |
| `Notes` | Notes | Note |  |  |  |
| `AppUrl` | AppUrl | URL |  |  |  |
| `Option` | Option | Choice |  |  | valg: RunningNoPlan, PowerApps, RunningNoItem, RunningNoTask, CostApprovalThresholdDkk |
| `Value` | Value | Number |  |  |  |
| `EnvironmentID` | EnvironmentID | Text |  | x |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `EquipmentItems`  -  3 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **Description** | Text | x | x |  |
| `RowId` | RowId | Number |  |  |  |
| `RequestNo` | RequestNo | Text |  | x |  |
| `RequestGuid` | RequestGuid | Text |  | x |  |
| `ItemKey` | ItemKey | Text |  | x |  |
| `AttachmentFolder` | AttachmentFolder | Text |  |  |  |
| `FileCount` | FileCount | Number |  |  |  |
| `RequesterEmail` | RequesterEmail | Text |  | x |  |
| `RequesterName` | RequesterName | Text |  |  |  |
| `SubmittedOn` | SubmittedOn | DateTime |  | x |  |
| `RowStatus` | RowStatus | Choice |  | x | valg: valid, submitted |
| `RequestType` | RequestType | Text |  | x |  |
| `Plant` | Plant | Text |  | x |  |
| `EquipmentNumber` | EquipmentNumber | Text |  | x |  |
| `EquipmentCategory` | EquipmentCategory | Text |  |  |  |
| `Manufacturer` | Manufacturer | Text |  |  |  |
| `TypeDesignation` | TypeDesignation | Text |  |  |  |
| `SerialNumber` | SerialNumber | Text |  | x |  |
| `FunctionalLocation` | FunctionalLocation | Text |  | x |  |
| `FunctionalLocation1` | FunctionalLocation1 | Text |  |  |  |
| `FunctionalLocation2` | FunctionalLocation2 | Text |  |  |  |
| `ClassData` | ClassData | Text |  |  |  |
| `RoomCoordinates` | RoomCoordinates | Text |  |  |  |
| `Placement` | Placement | Text |  |  |  |
| `WarrantyStart` | WarrantyStart | DateTime |  |  |  |
| `WarrantyEnd` | WarrantyEnd | DateTime |  |  |  |
| `LongText` | LongText | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `FunctionalLocationItems`  -  1 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **RowGuid** | Text | x | x |  |
| `RequestGuid` | RequestGuid | Text | x | x |  |
| `RequestId` | RequestId | Number |  | x |  |
| `RowNo` | RowNo | Number |  |  |  |
| `FunctionalLocation` | FunctionalLocation | Text |  | x |  |
| `Description` | Description | Text |  |  |  |
| `KksType` | KksType | Text |  |  |  |
| `AssignedClass` | AssignedClass | Text |  | x |  |
| `RowStatus` | RowStatus | Choice |  | x | valg: draft, valid, warning, invalid |
| `FirstIssue` | FirstIssue | Text |  |  |  |
| `IssueCount` | IssueCount | Number |  |  |  |
| `TrmAssignment` | TrmAssignment | Text |  |  |  |
| `AbcIndic` | AbcIndic | Text |  |  |  |
| `SafetyCriticalEquipment` | SafetyCriticalEquipment | Text |  | x |  |
| `RequesterEmail` | RequesterEmail | Text |  | x |  |
| `SpoolValuesJson` | SpoolValuesJson | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `FunctionalLocationRequests`  -  1 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **RequestNo** | Text | x | x |  |
| `RequestGuid` | RequestGuid | Text | x | x |  |
| `Status` | Status | Choice |  | x | valg: Kladde, Indsendt, UnderBehandling, AfventerInfo, KlarTilSAP, OprettetISAP, Afvist, Annulleret |
| `RequesterEmail` | RequesterEmail | Text |  | x |  |
| `RequesterName` | RequesterName | Text |  |  |  |
| `RowCount` | RowCount | Number |  |  |  |
| `ReadyCount` | ReadyCount | Number |  |  |  |
| `IssueCount` | IssueCount | Number |  |  |  |
| `WarningCount` | WarningCount | Number |  |  |  |
| `SubmittedOn` | SubmittedOn | DateTime |  |  |  |
| `IndexItemId` | IndexItemId | Number |  |  |  |
| `PayloadJson` | PayloadJson | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `IB_AppSections`  -  87 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **Application** | Text | x | x |  |
| `Section` | Section | Text |  |  |  |
| `AppOrder` | AppOrder | Number |  |  |  |
| `SectionOrder` | SectionOrder | Number |  |  |  |
| `IsActive` | IsActive | Boolean |  | x |  |
| `ScreenKey` | ScreenKey | Text |  |  |  |
| `DomainColor` | DomainColor | Text |  |  |  |
| `IconRef` | IconRef | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `IB_TicketComments`  -  9 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `TicketId` | TicketId | Number |  | x |  |
| `TicketNo` | TicketNo | Text |  | x |  |
| `AuthorEmail` | AuthorEmail | Text |  |  |  |
| `AuthorName` | AuthorName | Text |  |  |  |
| `AuthorRole` | AuthorRole | Choice |  |  | valg: Reporter, Admin, System |
| `EventType` | EventType | Choice |  |  | valg: Comment, StatusChange, Assignment, PriorityChange, Attachment, Reopened, Closed, Archived, System |
| `Visibility` | Visibility | Choice |  |  | valg: Reporter, Internal |
| `Content` | Content | Note |  |  |  |
| `PreviousStatus` | PreviousStatus | Text |  |  |  |
| `NewStatus` | NewStatus | Text |  |  |  |
| `EventOn` | EventOn | DateTime |  | x |  |
| `FileName` | FileName | Text |  |  |  |
| `FileSizeKb` | FileSizeKb | Number |  |  |  |
| `AtSubmission` | AtSubmission | Boolean |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `IB_Tickets`  -  6 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `TicketNo` | TicketNo | Text |  | x |  |
| `Description` | Description | Note |  |  |  |
| `ReproSteps` | ReproSteps | Note |  |  |  |
| `ExpectedResult` | ExpectedResult | Note |  |  |  |
| `ActualResult` | ActualResult | Note |  |  |  |
| `Application` | Application | Text |  | x |  |
| `Section` | Section | Text |  | x |  |
| `OtherContext` | OtherContext | Text |  |  |  |
| `RelatedRequestNo` | RelatedRequestNo | Text |  |  |  |
| `LayoutContext` | LayoutContext | Text |  |  |  |
| `ClientContext` | ClientContext | Text |  |  |  |
| `Severity` | Severity | Choice |  |  | valg: Blocker, Major, Minor, Cosmetic |
| `Priority` | Priority | Choice |  |  | valg: Urgent, High, Normal, Low |
| `Status` | Status | Choice |  | x | valg: New, Reopened, Triaged, In progress, Ready for retest, Closed |
| `ReporterEmail` | ReporterEmail | Text |  | x |  |
| `ReporterName` | ReporterName | Text |  |  |  |
| `AssignedToEmail` | AssignedToEmail | Text |  | x |  |
| `AssignedToName` | AssignedToName | Text |  |  |  |
| `LastActivityOn` | LastActivityOn | DateTime |  | x |  |
| `ResolvedOn` | ResolvedOn | DateTime |  |  |  |
| `ClosedOn` | ClosedOn | DateTime |  |  |  |
| `IsArchived` | IsArchived | Boolean |  | x |  |
| `Resolution` | Resolution | Note |  |  |  |
| `SharedItemId` | SharedItemId | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `LubricationTaskTypeList`  -  2 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MaintenanceActivityTypeList`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `TypeNo` | TypeNo | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MaintenanceItems`  -  72 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text | x |  |  |
| `Status` | Status | Choice |  |  | valg: New, Change, Deleted |
| `MaintenancePlanNo` | MaintenancePlanNo | Lookup | x | x | opslag -> 55c96ba9-52b8-4018-8945-f736b001d6a2 (PlanID) |
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
| `OrstedResponsibleEmail` | OrstedResponsibleEmail | Text |  | x |  |
| `ItemGuid` | ItemGuid | Text |  | x |  |
| `SapItemNo` | SapItemNo | Text |  | x |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MaintenancePlans`  -  50 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text | x |  |  |
| `Status` | Status | Choice | x |  | valg: Draft, In Progress, Ready for creation in SAP, Published, Returned |
| `MultiCounterStrategy` | MultiCounterStrategy | Choice |  |  | valg: 100001 - BIO 6 Mon or 166 Counter Days, 100002 - BIO 12 Mon or 166 Counter Days, 100003 - BIO 12 Mon or 208 Counter Days, 100004 - BIO 12 Mon or 250 Counter Days, 100005 - BIO 12 Mon or 333 Counter Days, 100006 - BIO 12 Mon or 354 Counter Days |
| `Cycle` | Cycle | Number | x |  |  |
| `Unit` | Unit | Choice | x |  | valg: H, DAY, WK, MON, YR |
| `PlannedDate` | PlannedDate | DateTime | x |  |  |
| `CallHorizon` | **CallHorizonChoiceOLD** | Choice |  |  | valg: 2 Days (1 WK), 7 Days (2 WK), 15 Days (1 MON), 20 Days (6 WK), 40 days (2-4 MON), 45 days (6 MON), 50 Days, 55 days (1 YR), 60 days (2 YR), 65 days (3 YR), 70 days (4 YR), 80 Days (5 & 6 YR) |
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
| `StrategyKey` | StrategyKey | Text |  | x |  |
| `ApprovalStage` | ApprovalStage | Choice |  | x | valg: System, Cost, Quality, Done |
| `SubmittedOn` | SubmittedOn | DateTime |  |  |  |
| `StageRunId` | StageRunId | Text |  |  |  |
| `ReturnComment` | ReturnComment | Note |  |  |  |
| `MasterDataNotified` | MasterDataNotified | Boolean |  |  |  |
| `RequesterNotified` | RequesterNotified | Boolean |  |  |  |
| `SapOrderGuid` | SapOrderGuid | Text |  | x |  |
| `SapOrderFile` | SapOrderFile | Text |  |  |  |
| `SapCreatedOn` | SapCreatedOn | DateTime |  |  |  |
| `SapCreatedBy` | SapCreatedBy | Text |  |  |  |
| `NoteToApprover` | NoteToApprover | Note |  |  |  |
| `SubmittedBy` | SubmittedBy | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MainWorkCenters`  -  53 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `field_1` | **Description                              ** | Text |  |  |  |
| `field_2` | **Plant Key** | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MaterialItems`  -  2 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **MaterialDescription** | Text | x | x |  |
| `RowId` | RowId | Number |  |  |  |
| `RequestNo` | RequestNo | Text |  | x |  |
| `RequestGuid` | RequestGuid | Text |  | x |  |
| `ItemKey` | ItemKey | Text |  | x |  |
| `AttachmentFolder` | AttachmentFolder | Text |  |  |  |
| `FileCount` | FileCount | Number |  |  |  |
| `RequesterEmail` | RequesterEmail | Text |  | x |  |
| `RequesterName` | RequesterName | Text |  |  |  |
| `SubmittedOn` | SubmittedOn | DateTime |  | x |  |
| `RowStatus` | RowStatus | Choice |  | x | valg: valid, submitted |
| `Plant` | Plant | Text |  | x |  |
| `FunctionalLocation` | FunctionalLocation | Text |  | x |  |
| `Manufacturer` | Manufacturer | Text |  |  |  |
| `ModelNumber` | ModelNumber | Text |  |  |  |
| `ManufacturerPartNo` | ManufacturerPartNo | Text |  | x |  |
| `Supplier` | Supplier | Text |  |  |  |
| `SupplierPartNo` | SupplierPartNo | Text |  |  |  |
| `Price` | Price | Number |  |  |  |
| `PriceUnit` | PriceUnit | Text |  |  |  |
| `StockUnit` | StockUnit | Text |  |  |  |
| `DeliveringTime` | DeliveringTime | Number |  |  |  |
| `RecommendedStock` | RecommendedStock | Number |  |  |  |
| `StrategicPart` | StrategicPart | Text |  |  |  |
| `WearPart` | WearPart | Text |  |  |  |
| `LongText` | LongText | Note |  |  |  |
| `NoBomItem` | NoBomItem | Boolean |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_ApprovalLog`  -  25 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `RequestGuid` | RequestGuid | Text |  | x |  |
| `PlanId` | PlanId | Number |  | x |  |
| `Stage` | Stage | Text |  | x |  |
| `ItemGuid` | ItemGuid | Text |  | x |  |
| `ItemText` | ItemText | Text |  |  |  |
| `Fingerprint` | Fingerprint | Text |  |  |  |
| `Amount` | Amount | Number |  |  |  |
| `Decision` | Decision | Text |  |  |  |
| `Detail` | Detail | Text |  |  |  |
| `DecidedByEmail` | DecidedByEmail | Text |  |  |  |
| `DecidedOn` | DecidedOn | DateTime |  |  |  |
| `Comment` | Comment | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_Approver`  -  31 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **ApproverKey** | Text | x | x |  |
| `Approver1` | Approver1 | Text |  |  |  |
| `Approver2` | Approver2 | Text |  |  |  |
| `Approver1Absent` | Approver1Absent | Boolean |  |  |  |
| `Notes` | Notes | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_FLKey`  -  6733 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **KeyValue** | Text | x | x |  |
| `KeyType` | KeyType | Text | x | x |  |
| `Value` | Value | Text |  |  |  |
| `Description` | Description | Text |  |  |  |
| `Modified` | Modified | DateTime |  | x | skrivebeskyttet |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_HelpText`  -  51 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **HelpKey** | Text | x | x |  |
| `AppArea` | AppArea | Choice | x | x | valg: FunctionalLocation, Equipment, MeasuringPoint, Material, MaintenancePlan |
| `Kind` | Kind | Choice | x |  | valg: Hint, Panel |
| `Heading` | Heading | Text |  |  |  |
| `Body` | Body | Note | x |  |  |
| `SortOrder` | SortOrder | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_KksFunctionKey`  -  2913 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **Code** | Text | x | x |  |
| `Section` | Section | Text | x | x |  |
| `SortNo` | SortNo | Number | x | x |  |
| `Description` | Description | Note |  |  |  |
| `Modified` | Modified | DateTime |  | x | skrivebeskyttet |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_MpCharacteristic`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text | x | x |  |
| `Description` | Description | Text |  |  |  |
| `Unit` | Unit | Text | x |  |  |
| `UnitDescription` | UnitDescription | Text |  |  |  |
| `MeasuringPointType` | MeasuringPointType | Choice |  |  | valg: Counter, MeasuringPoint |
| `DefaultDecimalPlaces` | DefaultDecimalPlaces | Number |  |  |  |
| `Active` | Active | Boolean |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_RequestIndex`  -  34 raekker

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
| `HasApproverNote` | HasApproverNote | Boolean |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_StandardTaskOperations`  -  176 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **TaskLabel** | Text | x |  |  |
| `Plant` | Plant | Choice |  | x | valg: ASV, AVV, HEV, HCV, KYV, SKV, SMV, SSV |
| `OperationNo` | OperationNo | Number |  | x |  |
| `WorkCenter` | WorkCenter | Text |  |  |  |
| `ControlKey` | ControlKey | Text |  |  |  |
| `OperationShortText` | OperationShortText | Text |  |  |  |
| `Work` | Work | Number |  |  |  |
| `WorkUnit` | WorkUnit | Text |  |  |  |
| `DurationUnit` | DurationUnit | Text |  |  |  |
| `ActivityType` | ActivityType | Text |  |  |  |
| `StandardTextKey` | StandardTextKey | Text |  |  |  |
| `SapPlant` | SapPlant | Text |  |  |  |
| `NumberOfCapacities` | NumberOfCapacities | Number |  |  |  |
| `CalculationKey` | CalculationKey | Number |  |  |  |
| `PercentageWork` | PercentageWork | Number |  |  |  |
| `DistributionFactor` | DistributionFactor | Number |  |  |  |
| `OrderQuantity` | OrderQuantity | Number |  |  |  |
| `OrderUnit` | OrderUnit | Text |  |  |  |
| `Price` | Price | Number |  |  |  |
| `Currency` | Currency | Text |  |  |  |
| `PriceUnit` | PriceUnit | Number |  |  |  |
| `CostElement` | CostElement | Number |  |  |  |
| `MaterialGroup` | MaterialGroup | Text |  |  |  |
| `PurchasingGroup` | PurchasingGroup | Text |  |  |  |
| `VendorNo` | VendorNo | Text |  |  |  |
| `PurchasingOrg` | PurchasingOrg | Text |  |  |  |
| `ServiceNo` | ServiceNo | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_Strategy`  -  53 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **StrategyKey** | Text | x | x |  |
| `StrategyName` | StrategyName | Text | x |  |  |
| `SchedulingIndicator` | SchedulingIndicator | Choice |  |  | valg: TIME, TIME_FACTOR, PERFORMANCE |
| `Hierarchical` | Hierarchical | Choice |  |  | valg: Ja, Nej, Ikke afklaret |
| `PackagesLoaded` | PackagesLoaded | Boolean |  |  |  |
| `Notes` | Notes | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_StrategyPackage`  -  3 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **PackageLabel** | Text | x |  |  |
| `StrategyKey` | StrategyKey | Text | x | x |  |
| `PackageNo` | PackageNo | Number | x |  |  |
| `ShortCode` | ShortCode | Text |  |  |  |
| `CycleLength` | CycleLength | Number |  |  |  |
| `CycleUnit` | CycleUnit | Choice |  |  | valg: H, DAY, WK, MON, YR, COUNT |
| `Hierarchy` | Hierarchy | Number |  |  |  |
| `PackageText` | PackageText | Text |  |  |  |
| `OffsetValue` | OffsetValue | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_TasklistAttachment`  -  1 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **FileName** | Text | x |  |  |
| `PlanKey` | PlanKey | Text |  | x |  |
| `ItemKey` | ItemKey | Text |  | x |  |
| `OperationsKey` | OperationsKey | Text |  |  |  |
| `FileUrl` | FileUrl | Text |  |  |  |
| `FileSize` | FileSize | Number |  |  |  |
| `LineId` | LineId | Number |  |  |  |
| `UploadStatus` | UploadStatus | Choice |  |  | valg: Pending, Uploaded, Failed |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MD_TasklistMaterial`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **MaterialNo** | Text | x |  |  |
| `PlanKey` | PlanKey | Text |  | x |  |
| `ItemKey` | ItemKey | Text |  | x |  |
| `TaskItemID` | TaskItemID | Text |  | x |  |
| `OperationNo` | OperationNo | Text |  |  |  |
| `Quantity` | Quantity | Number | x |  |  |
| `MaterialText` | MaterialText | Text |  |  |  |
| `Unit` | Unit | Text |  |  |  |
| `LineId` | LineId | Number |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `MeasuringPointItems`  -  0 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **Description** | Text | x | x |  |
| `RowId` | RowId | Number |  |  |  |
| `RequestNo` | RequestNo | Text |  | x |  |
| `RequestGuid` | RequestGuid | Text |  | x |  |
| `ItemKey` | ItemKey | Text |  | x |  |
| `AttachmentFolder` | AttachmentFolder | Text |  |  |  |
| `FileCount` | FileCount | Number |  |  |  |
| `RequesterEmail` | RequesterEmail | Text |  | x |  |
| `RequesterName` | RequesterName | Text |  |  |  |
| `SubmittedOn` | SubmittedOn | DateTime |  | x |  |
| `RowStatus` | RowStatus | Choice |  | x | valg: draft, valid, submitted |
| `Plant` | Plant | Text |  | x |  |
| `FunctionalLocation` | FunctionalLocation | Text |  | x |  |
| `ExistsInSap` | ExistsInSap | Choice |  |  | valg: Yes, No |
| `MeasuringPoint` | MeasuringPoint | Text |  | x |  |
| `MeasuringPointType` | MeasuringPointType | Choice |  |  | valg: Counter, MeasuringPoint |
| `Characteristic` | Characteristic | Text |  | x |  |
| `CharacteristicDescription` | CharacteristicDescription | Text |  |  |  |
| `CharacteristicUnit` | CharacteristicUnit | Text |  |  |  |
| `CharacteristicUnitDescription` | CharacteristicUnitDescription | Text |  |  |  |
| `DecimalPlaces` | DecimalPlaces | Number |  |  |  |
| `IsCounter` | IsCounter | Boolean |  |  |  |
| `TargetValue` | TargetValue | Number |  |  |  |
| `LowerLimit` | LowerLimit | Number |  |  |  |
| `UpperLimit` | UpperLimit | Number |  |  |  |
| `ExpectedAnnualUsage` | ExpectedAnnualUsage | Number |  |  |  |
| `InProdos` | InProdos | Choice |  |  | valg: Yes, No |
| `ProdosTag` | ProdosTag | Text |  | x |  |
| `ProdosCounterExists` | ProdosCounterExists | Choice |  |  | valg: Yes, No |
| `CounterCreateIn` | CounterCreateIn | Choice |  |  | valg: PRODOS, SRO |
| `ApprovalRequired` | ApprovalRequired | Boolean |  |  |  |
| `CounterCreatedOn` | CounterCreatedOn | DateTime |  |  |  |
| `CounterCreatedBy` | CounterCreatedBy | Text |  |  |  |
| `CreatedMeasuringPointNo` | CreatedMeasuringPointNo | Text |  | x |  |
| `Remarks` | Remarks | Note |  |  |  |
| `SapResult` | SapResult | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `PlantList`  -  8 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `SortFieldList`  -  28 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `StandardStrategyList`  -  3 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

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
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `TaskListMain`  -  364 raekker

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
| `MaintenancePlanID` | MaintenancePlanID | Lookup |  | x | opslag -> 55c96ba9-52b8-4018-8945-f736b001d6a2 (PlanID) |
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
| `OperationNo` | OperationNo | Number |  | x |  |
| `PackagesKey` | PackagesKey | Text |  |  |  |
| `MaterialGroup` | MaterialGroup | Text |  |  |  |
| `ServiceNo` | ServiceNo | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `UserAndGroups`  -  7 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | Title | Text |  |  |  |
| `Member` | Member | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `Vendors`  -  20 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **VendorName** | Text |  |  |  |
| `VendorNumber` | VendorNumber | Text |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |

## `VHP_NoteToSelf`  -  1 raekker

| Internt navn | Visningsnavn | Type | Kraevet | Indeks | Noter |
|---|---|---|:-:|:-:|---|
| `Title` | **RequestNo** | Text |  |  |  |
| `RequestGuid` | RequestGuid | Text |  | x |  |
| `PlanId` | PlanId | Number |  |  |  |
| `OwnerEmail` | OwnerEmail | Text |  | x |  |
| `Note` | Note | Note |  |  |  |
| `ID` | ID | Counter |  |  | skrivebeskyttet |
| `Modified` | Modified | DateTime |  |  | skrivebeskyttet |
| `Created` | Created | DateTime |  |  | skrivebeskyttet |
| `Author` | **Created By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |
| `Editor` | **Modified By** | User |  |  | opslag -> UserInfo (); skrivebeskyttet |


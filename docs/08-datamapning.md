# Fra testdata til rigtige SharePoint-lister

Appen kører i dag på 21 samlinger, der fyldes med **hårdkodede tabeller** i
`App.OnStart`. Det her dokument er kortet over, hvad der skal erstattes med
hvad — og hvad der mangler svar på, før det kan gøres.

Kilden er `Maintenance Plan App/build/generate_app_onstart.py`. Ingen af
felterne nedenfor er gættet; de er trukket ud af den genererede
`App.pa.yaml`.

## 1. Planhovedet — appens vigtigste skriveretning

`varVhpPlan` er ikke en samling, men den record, hele skærmen redigerer. Den
skal gemmes og genindlæses:

| Felt | Eksempelværdi i testdata |
|---|---|
| `Plant` | `SSV` |
| `Status` | `Ny` |
| `PlanType` | `SingleCycle` / `Strategy` |
| `Strategy` | `Z-MONTH` (kun strategiplaner) |
| `PlanText` | `SSV Aarlig Rundering` |
| `SortField` | `080 - Boiler Control Category A` |
| `Cycle` | `12` |
| `Unit` | `MON` |
| `CallHorizon` | `55 Dage (1 YR)` |
| `SchedulingIndicator` | `TIME` / `PERFORMANCE` |
| `FirstCallDay` / `FirstCallMonth` / `FirstCallYear` | `1` / `1` / `2027` |
| `StatutorySortField` | |

**Formodning:** det er `MaintenancePlans` (34 rækker). Skal bekræftes.

## 2. De tre datasamlinger

| Samling | Felter | Formodet liste |
|---|---|---|
| `colVhpItems` | `ItemId`, `ShortText`, `FunctionalLocation`, `FlDescription`, `MainWorkCenter`, `ActivityType`, `ObjectList`, `Revision`, `OrstedResponsible`, `Initials`, `LongText`, `TasklistKey`, `TasklistName`, `Status` | `MaintenanceItems` (58) |
| `colVhpOperations` | `ItemId`, `OperationNo`, `OperationShortText`, `WorkHours`, `DurationHours`, `MainWorkCenter`, `Vendor`, `LongText`, `PackagesKey`, `Selected` | **?** |
| `colVhpTasklists` | `Plant`, `Key`, `Name`, `Description` + indlejret `Operations`: `OperationNo`, `OperationShortText`, `WorkHours`, `DurationHours`, `MainWorkCenter`, `Vendor`, `LongText`, `ControlKey`, `OpPlant` | `TaskListMain` (306) + de seks `<VÆRK> Standard Tasklist`? |

`colVhpTasklists` har en **indlejret tabel** pr. arbejdsplan. Det kan
SharePoint ikke levere direkte — enten er det to lister med en nøgle, eller
også bygges sammenkædningen i `OnStart`. Hvilken af delene afhænger af, hvad
der faktisk står i listerne i dag.

## 3. Opslagslisterne

Alle disse er i dag hårdkodede tabeller med ét felt, `Value`:

| Samling | Formodet liste |
|---|---|
| `colVhpPlantCodes` | `PlantList` (6) — men testdata har **9** værker (SSV, SKV, HEV, HCV, ASV, AVV, KYV, STV, SMV) |
| `colVhpActivityTypeOptions` | `MaintenanceActivityTypeList` (7) |
| `colVhpCallHorizonOptions` | `CallHorizonMatrix` (16) |
| `colVhpMainWorkCenterItemOptions` / `...TasklistOptions` | `MainWorkCenters` (53) — to forskellige udsnit? |
| `colVhpSortFieldOptions` | `SortFieldList` (28) |
| `colVhpCtrlOptions` | **?** styringsnøgler (ZB01, PM01, PM03 …) |
| `colVhpRevisionOptions` | **?** |
| `colVhpOrderTypeOptions` | **?** |
| `colVhpPriorityOptions` | **?** |
| `colVhpDocSystemOptions` | **?** |
| `colVhpStrategies` (`Key`, `Name`, `SchedIndicator`) | `StandardStrategyList` (3) |
| `colVhpStrategyPackages` (`StrategyKey`, `PackageNo`, `ShortCode`, `CycleLength`, `CycleUnit`, `Hierarchy`, `PackageText`) | **?** — ingen oplagt liste |

Disse fire bliver stående som hårdkodede, fordi de er faste SAP-værdier og
ikke masterdata nogen vedligeholder: `colVhpPlanTypeOptions`,
`colVhpPlanStatusOptions`, `colVhpYesNoOptions`, `colVhpUnitOptions`.

## 4. Det der ikke skal kobles på

| Samling | Hvorfor |
|---|---|
| `colVhpFunctionalLocations` | Erstattet af flowet `BioSap-Integration-FunctionalLocations`. Listen `FunctionalLocations` har **122.700 rækker** — 61 gange delegationsloftet. Den kan ikke bruges direkte fra appen uanset hvad. **Begge udtræksscripts springer den over**, fordi den kun koster ventetid; `-IncludeAll` tager den med, hvis den en dag skal ses |
| `colVhpFlSearch`, `colVhpItemObjects`, `colVhpPickerSelected` | Arbejdssamlinger. Fyldes under brug, ikke ved opstart |

## 5. Åbne spørgsmål

Disse afgør, om datamodellen skal laves om eller bare kobles på:

1. **Hvor ligger operationerne i dag?** `colVhpOperations` er den samling,
   pakkematricen hænger på (`PackagesKey`). Er `TaskListMain` (306) den
   liste — og hvad binder en operation til et item?
2. **Hvorfor seks `<VÆRK> Standard Tasklist`-lister?** Appen har én samling
   med en `Plant`-kolonne. Er de seks udsnit af det samme, eller har de
   forskellige kolonner?
3. **Skriver den nuværende app til `MaintenancePlans`/`MaintenanceItems`,
   eller er de kun læsekilder?** Og hvad er nøglen mellem plan og item?
4. **Hvor kommer strategipakkerne fra?** `StandardStrategyList` har 3 rækker
   — det matcher tre strategier, men ikke pakkerne under dem.
5. **Er `PlantList` (6) mangelfuld,** eller er de tre ekstra værker i
   testdata (HCV, STV, SMV) noget jeg selv har fundet på?
6. **Hvad er `LubricationTaskTypeList`, `StandardTaskList`, `UserAndGroups`
   og `Vendors` til?** `Vendors` matcher `colVhpOperations.Vendor`, men de
   tre andre har ingen modpart i appen.

## 6. Hvad der skal til for at svare

Der er to veje. **B virker og er den primære** — browser-vejen står som
reserve, hvis app-registreringen en dag forsvinder, eller hvis nogen uden
PowerShell skal kunne trække strukturen.

### A. Browseren (reserve, ingen opsætning)

SharePoints REST API gennem din egen indloggede session. Ingen app, intet
token, ingen IT-sag. Du kan præcis det, du kan i forvejen som bruger.

1. Åbn sitet i Edge eller Chrome og log ind.
2. F12 → fanen **Console**. Advarer den mod indsat kode, så skriv
   `allow pasting` og tryk Enter først.
3. Indsæt hele `sharepoint/inspect/browser-extract.js` og tryk Enter.
4. `sharepoint-schema.json` hentes til Downloads.
5. Læg den i `sharepoint/inspect/out/`, og kør:

```bash
python3 tools/schema_to_md.py sharepoint/inspect/out/sharepoint-schema.json
```

Sæt `SAMPLE_ROWS = 0` øverst i filen, hvis der ikke må komme data med.

### B. PnP PowerShell

`sharepoint/inspect/Export-ListSchema.ps1` gør det samme fra PowerShell — og
kan i modsætning til browser-vejen også **skrive**, hvilket
provisioneringsscripterne har brug for.

PnP.PowerShell 2.x har ikke længere en fælles app-registrering, så
`Connect-PnPOnline -Interactive` kræver et `ClientId`. Det findes allerede i
tenanten:

```
9bc3ab49-b65d-410a-85ad-de819febfddc
```

Sæt det én gang, så slipper både du og VS Code for at støde på det igen:

```powershell
[Environment]::SetEnvironmentVariable(
    "PNP_CLIENT_ID", "9bc3ab49-b65d-410a-85ad-de819febfddc", "User")
```

Åbn en **ny** terminal bagefter — miljøvariabler læses ved opstart. Begge
scripts falder tilbage på `PNP_CLIENT_ID`, så der skal ikke sendes noget med
på kommandolinjen længere. Alternativt pr. kørsel:

```powershell
.\Export-ListSchema.ps1 -SiteUrl "https://..." -ClientId "9bc3ab49-b65d-410a-85ad-de819febfddc"
```

Et **client id er ikke en hemmelighed** — det er offentligt ligesom et
brugernavn, og det er client *secret* eller certifikat, der skal beskyttes.
Derfor står det her i klartekst. Det giver ingen adgang i sig selv: du skal
stadig logge ind interaktivt, og appen kan kun det, du selv kan.

Skulle registreringen forsvinde, oprettes en ny — det kræver rollen
*Application Developer* eller højere i Entra:

```powershell
Register-PnPEntraIDAppForInteractiveLogin `
    -ApplicationName "PnP Masterdata" -Tenant <tenant>.onmicrosoft.com -Interactive
```

## 7. Migrering

Ændres datamodellen, skal eksisterende data med over. Rækkefølgen er:

1. Eksportér til JSON med scriptet ovenfor (det er allerede en fuld kopi,
   hvis `-SampleRows` sættes højt nok).
2. Opret de nye lister med et provisioneringsscript, som det findes for
   `MD_RequestIndex`.
3. Indlæs med et migreringsscript, der mapper gammel kolonne → ny kolonne.
4. Behold de gamle lister urørte, indtil den nye app er godkendt.

Trin 2 og 3 skrives, når spørgsmålene i afsnit 5 er besvaret — ikke før.

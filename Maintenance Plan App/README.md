# Maintenance Plan App (VH-plan)

Canvas app til oprettelse og styring af **vedligeholdelsesplaner (VH-planer)**
for SAP PM, med planhoved, items, tasklist-/operationsbinding og dispatch via
mailkladde. Bygget i samme visuelle stil som Materialer-appen i samme
Power Platform-miljø (Bioenergy Solutions DEV, solution BIO SAP).

Kildefilerne i denne mappe er eksporteret direkte fra en aktiv
[canvas-authoring coauthoring-session](https://learn.microsoft.com/power-platform/developer-guide-canvas-apps)
mod appen i Power Apps Studio:

> https://make.powerapps.com/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47/canvas/?action=edit&app-id=%2Fproviders%2FMicrosoft.PowerApps%2Fapps%2F11fa8d90-868a-45a4-ba23-28f2cf0671a2&solution-id=43fe3e8a-adbe-4e49-996b-42e9b7081b2d

## Filer

| Fil | Indhold |
|---|---|
| `App.pa.yaml` | `App.OnStart` — indlæser alle referencelister (Status, Unit, Call Horizon, Sort Field, Main Work Center m.fl.), tasklister pr. værk, funktionelle lokationer og en demo-plan med to items. |
| `ScreenVhPlan.pa.yaml` | Den ene skærm i appen: Hero (Validate/Export + procesindikator), Plan Header, Items + Item Editor, Tasklist & Operations (inkl. picker-modal), Dispatch/Control, samt "Send as email"-knap. |
| `_EditorState.pa.yaml` | Editor-metadata (skærmrækkefølge). |

## Datamodel (collections sat i `App.OnStart`)

- `colVhpPlan` (variabel, ikke collection) — selve planhovedet: Plant, Status, PlanText, Cycle, Unit, Call Horizon m.fl.
- `colVhpItems` — items under planen (FL, MainWorkCenter, ActivityType, TasklistKey/Name, Status).
- `colVhpOperations` — operationslinjer pr. item (OperationNo, OperationShortText, WorkHours, DurationHours, MainWorkCenter, Vendor, LongText, Selected).
- `colVhpTasklists` — tasklister pr. værk med indlejrede operationslinjer (bruges af "Add lines from tasklist"-picker).
- `colVhpFunctionalLocations` — reference-data til "Verify FL"-opslag (erstatning for en rigtig SAP OData-forbindelse).
- `colVhpPlantCodes`, `colVhpPlanStatusOptions`, `colVhpUnitOptions`, `colVhpCallHorizonOptions`, `colVhpSortFieldOptions`,
  `colVhpMainWorkCenterItemOptions`, `colVhpMainWorkCenterTasklistOptions`, `colVhpActivityTypeOptions`,
  `colVhpRevisionOptions`, `colVhpPriorityOptions`, `colVhpCtrlOptions`, `colVhpOrderTypeOptions`,
  `colVhpDocSystemOptions`, `colVhpYesNoOptions` — statiske dropdown-referencelister.

## Sådan importeres/åbnes koden

Filerne er i `.pa.yaml`-formatet, som bruges af Power Platform-værktøjernes
canvas-authoring coauthoring-flow (samme format som `pac canvas` /
Power Apps' "Save as code"). De kan bruges til at:

1. Genskabe skærmens fulde kontroltræ i en ny/eksisterende canvas app via en
   coauthoring-session (`sync_canvas` / tilsvarende `pac`-værktøj), eller
2. Læses direkte som reference for kontrolstruktur, navngivning og Power Fx-formler.

## Kendte begrænsninger

- "Verify FL" slår op i en lokal referencetabel (8 eksempler), da der ikke er
  konfigureret en SAP OData-forbindelse i miljøet.
- Tasklist-datasættet er et repræsentativt udsnit (8 tasklister, op til 6
  operationslinjer hver) for at holde `App.OnStart` under den størrelse hvor
  Power Apps Studio ellers får problemer med at rendere skærmen.

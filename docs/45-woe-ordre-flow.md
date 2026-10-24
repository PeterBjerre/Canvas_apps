# 45 — Flowet, der henter alt om en SAP-ordre (WOE + SAP Utility)

`BioSap-Integration-WoeOrder` er ét flow i solutionen, som ud fra et
SAP-ordrenummer kalder alle WOE-endpoints og de to SAP Utility-endpoints i
én omgang. Formålet er at kunne oprette en VH-plan med udgangspunkt i en
udført ordre og senere sammenligne ordrens data med VH-planens (en anden
API, der kommer senere), så brugeren kan tage stilling til, om ændringerne
på ordren skal med på planen næste gang.

Flowet bygger på token- og kaldmønstret fra `BioSap-Integration-WoeOrderObjects`
([docs/44](44-dev-api-test.md)) og på Excel-udgaven af samme idé, VBA-modulerne
fra `BIO SAP VH-plan lister.xlsm` (`excel/vba/vhplan-lister/mod*.bas`: `modExtractWorkOrder`,
`modHttpOData`, `modODataCatalog`, `modMain`, `modMovementParser`):

- `FetchWorkOrderAll` henter SAP's OData `WorkOrderHeaderSet('{aufnr}')` i ét
  kald og folder relationerne ud: `WorkOrderOperationsSet`, `Objects`,
  `Status`, `Partners`, `PMNotification`, `Attachment`, `Permit`,
  `TaskListItems`, `WorkOrderControlRooms`, `WorkOrderSafetyInformation`.
- `modMovementParser` henter vareudtag og returer på ordren fra inventory-
  OData'en (`MovementType` udtag/retur) som `Raw_Ordre_Components`.
- Mangler `Maintenance_item` (WAPOS) i headeren, slås den op i IW33, for den
  binder ordren til VH-planens item, som compare-motoren sammenligner mod.
- Formularen `ufOrderOverlay` (SPOOL-arket) viser det i fanerne Header,
  Operations, Components, Attachments og Decisions.

Flowet henter de samme data fra REST-API'erne. WOE har ikke `PMNotification`,
`Permit`, `WorkOrderControlRooms` og `WorkOrderSafetyInformation` som
endpoints; `activities`, `causes` og `feedback` er notifikationens data.

## Kaldene og rækkefølgen

| Trin | Kald | Id |
|---|---|---|
| 1 | `GET {woe}/workorders/{id}/header` | ordrenummeret |
| 2 (parallelt) | `GET {woe}/operations/{workOrderId}` | `workOrderId` fra headeren |
| 2 | `GET {woe}/operations/{workOrderId}/tasklistitems` | `workOrderId` |
| 2 | `GET {woe}/workorders/{id}/objects` | `workOrderId` |
| 2 | `GET {woe}/workorders/{objectId}/status` | `objectId` (ordrens objektnummer, `OR…`) |
| 2 | `GET {woe}/workorders/{id}/partner` | `workOrderId` |
| 2 | `GET {woe}/workorders/{id}/activities` | `workOrderId` |
| 2 | `GET {woe}/workorders/{id}/causes` | `workOrderId` |
| 2 | `GET {woe}/workorders/{workOrderId}/feedback` | `workOrderId` |
| 2 | `GET {inventory}/materialonstocks/movements/{workOrderNumber}` | ordrenummeret (vareudtag og returer, Excels `Raw_Ordre_Components`) |
| 3 | `GET {saputility}/attachments/{objectId}` | `objectId` |
| 3 | `GET {saputility}/descriptions/{operationObjectId}/OperationText` | én gang pr. operation, i serie |

`{woe}` er `https://dev.api.orsted.dk/woe/api`, `{inventory}` er
`https://dev.api.orsted.dk/inventorymanagement`, `{saputility}` er
`https://test.api.orsted.dk/saputility` (handlingen `Setup`). Hvert API får
sit eget token (eget scope), alle med samme app-registrering.

### Id'erne

Headeren er det eneste kald, der kun kender ordrenummeret. Flowet starter
med `WorkOrderId` = ordrenummeret og `ObjectId` = `OR` + ordrenummeret
fyldt op til 12 cifre (ordre 26436811 → `OR000026436811`, som i
API-teamets eksempel). Svarer headeren 200, erstattes de af headerens
felter: `workOrderId` (ellers `id`, `orderNumber`) og `objectId` (ellers
`objectNumber`, `objnr`). Findes ingen af felterne, bruges startværdierne,
så de otte kald kører alligevel. Operationernes objektnummer tages fra
`objectId`, `objectNumber` eller `objnr` på hver operation; mangler det,
springes OperationText over for den operation.

Feltnavnene i WOE-svarene er ikke set endnu (API-teamet har ikke åbnet
endpointene for app-registreringen). Første kørsel i kørselshistorikken
viser, om de skal rettes i `Set_variable_WorkOrderId`,
`Set_variable_ObjectId` og `Compose_operation_object_id`.

## Svaret til appen

Samme fire tekstfelter som de andre API-flows:

| Felt | Indhold |
|---|---|
| `ok` | `yes` når headeren svarede 200, ellers `no` |
| `status` | HTTP-status fra headeren (eller fra token-kaldet) |
| `message` | Tom ved 200, ellers en engelsk fejltekst |
| `result` | JSON-tekst med alle sektioner, også når nogle kald fejlede |

`result` er ét objekt:

```json
{
  "orderNumber": "26436811",
  "workOrderId": "…", "objectId": "OR000026436811",
  "maintenanceItem": "…",
  "header":        {"status": 200, "data": {…}},
  "operations":    {"status": 200, "data": [...]},
  "tasklistitems": {"status": 403, "data": {…}},
  "objects":       {"status": 200, "data": [...]},
  "status":        {"status": 200, "data": {…}},
  "partner":       {"status": 200, "data": [...]},
  "activities":    {"status": 200, "data": [...]},
  "causes":        {"status": 200, "data": [...]},
  "feedback":      {"status": 200, "data": {…}},
  "attachments":   {"status": 200, "data": [...]},
  "movements":     {"status": 200, "data": [...]},
  "operationTexts": [{"objectId": "OV…", "operation": "0010", "status": 200, "data": {…}}]
}
```

`maintenanceItem` er headerens vedligeholdelsespost (WAPOS: `maintenanceItem`,
`wapos` eller `maintenanceItemNumber`), tom hvis headeren ikke har den. Den
binder ordren til VH-planens item, når der senere skal sammenlignes.

Hver sektion har sin egen `status`, så et 403 på fx `tasklistitems` ikke
stopper resten: appen får de sektioner, der svarede, og kan vise hvilke
der mangler. `attachments.data` og `movements.data` er en tekst (ikke et
objekt), når nøglen til SAP Utility eller inventory ikke er sat, eller
tokenet ikke kunne hentes.

Eksempel i Power Fx (flowet skal først tilføjes som datakilde i appen):

```
Set(varOrder, 'BioSap-Integration-WoeOrder'.Run(Trim(txtOrderNumber.Text)));
If(
    varOrder.ok = "yes",
    Set(varOrderData, ParseJSON(varOrder.result));
    ClearCollect(
        colOrderOperations,
        ForAll(
            Table(varOrderData.operations.data),
            {ObjectId: Text(ThisRecord.Value.objectId)}
        )
    ),
    Notify(varOrder.message, NotificationType.Error)
)
```

Flowet er ikke koblet på nogen skærm endnu, og `result` gemmes ikke
direkte i SharePoint. Planen (Peter 2026-10-23): appen læser svaret ind og
lader brugeren oprette en VH-plan ud fra ordren, som så ender i de lister,
der findes i forvejen: ordrens header svarer til et item
(`MaintenanceItems`), operationerne til tasklisten. Planens header kan
ikke hentes fra ordren.

## Hemmeligheder og miljøvariabler

| Miljøvariabel | Bruges af | Værdi |
|---|---|---|
| `BioSap-WOC-Client-Secret` | begge | Som i docs/44: alle API'erne kører med samme app-registrering `6b699286-…` (Peter 2026-10-23). SAP Utility får sit eget token med scope `9ab1e626-…/.default` |
| `BioSap-WOE-Dev-ApiKey` | WOE | Som i docs/44 |
| `BioSap-Inventory-Dev-ApiKey` | inventory | Som i docs/44 (lagerflowet) |
| `BioSap-SapUtility-Test-ApiKey` | SAP Utility | `x-apikey` til SAP Utility i test, som i testflowet i [docs/37](37-fl-api-test.md) |

Mangler secret eller WOE-nøglen, svarer flowet `ok = no` med en besked og
stopper som Failed. Inventory- og SAP Utility-nøglen er valgfri: mangler
en af dem, kører resten alligevel, og `movements.data` eller
`attachments.data` fortæller, hvad der ikke er sat op (`operationTexts` er
så tom).

Token-kaldene har *Secure inputs* og *Secure outputs*, API-kaldene *Secure
inputs*.

## Handlinger

| Handling | Hvad den gør |
|---|---|
| `Setup` | Token-URL, client ID, de tre scopes og base-URL'er |
| `Check_environment_variables` | Svarer appen og stopper, hvis en WOE-variabel mangler |
| `Initialize_variable_*` | `WorkOrderId`, `ObjectId`, `OperationTexts`, `Attachments`, `Movements` |
| `Get_token` / `Token_ok` | Token til WOE; ved fejl `Respond_token_error` |
| `Call_header` / `Header_found` | Headeren; ved 200 sættes id'erne fra svaret |
| `Call_operations` … `Call_feedback` | De otte WOE-kald, parallelt efter headeren |
| `Inventory_configured` / `Get_token_inventory` / `Call_movements` | Vareudtag og returer, parallelt med headeren; kun når inventory-nøglen er sat |
| `SapUtility_configured` | Kun når SAP Utility-nøglen er sat |
| `Get_token_saputility` / `Token_saputility_ok` | Token til SAP Utility |
| `Call_attachments` / `Set_variable_Attachments` | Attachments på ordrens objektnummer |
| `Operations_found` / `For_each_operation` | OperationText pr. operation, i serie |
| `Result` / `Respond_result` | Samler alle sektioner og svarer appen |

Der er ingen genforsøg. Med mange operationer tager OperationText-løkken
længst (ét kald pr. operation); appen får svaret, når alt er hentet.

## Typiske fejl

| Hvor | `status` | Årsag |
|---|---|---|
| `Respond_token_error` | 400/401 | Forkert scope eller client secret til WOE |
| En sektion | 401 | Forkert `x-apikey`, eller tokenet passer ikke til API'et |
| En sektion | 403 | App-registreringen har ikke rollen til netop det endpoint (API-teamet skal åbne det) |
| `header` | 404 | Ordren findes ikke i DEV |
| `attachments` | 404 | Objektnummeret er forkert: tjek headerens `objectId`-felt |

Kontrakttest: `tests/test_woe_order_flow.py`.

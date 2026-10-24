# 45 — Flowet, der henter alt om en SAP-ordre (WOE + SAP Utility)

`BioSap-Integration-WoeOrder` er ét flow i solutionen, som ud fra et
SAP-ordrenummer kalder alle WOE-endpoints, inventory-API'ets
materialbevægelser og SAP Utility-endpoints i én omgang. Formålet er at kunne oprette en VH-plan med udgangspunkt i en
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

## Kaldene

Alle kald tager ordrenummeret (eller ordrens objektnummer) direkte, så de
kører parallelt; headeren behøver ikke gå først (Peter 2026-10-24).

| Kald | Id |
|---|---|
| `GET {woe}/workorders/{id}/header` | ordrenummeret |
| `GET {woe}/operations/{workOrderId}` | ordrenummeret |
| `GET {woe}/operations/{workOrderId}/tasklistitems` | ordrenummeret |
| `GET {woe}/workorders/{id}/objects` | ordrenummeret |
| `GET {woe}/workorders/{objectId}/status` | `objectId` (ordrens objektnummer, `OR…`) |
| `GET {woe}/workorders/{id}/partner` | ordrenummeret |
| `GET {woe}/workorders/{id}/activities` | ordrenummeret |
| `GET {woe}/workorders/{id}/causes` | ordrenummeret |
| `GET {woe}/workorders/{workOrderId}/feedback` | ordrenummeret |
| `GET {inventory}/materialonstocks/movements/{workOrderNumber}` | ordrenummeret (vareudtag og returer, Excels `Raw_Ordre_Components`) |
| `GET {saputility}/attachments/{objectId}` | `objectId` |
| `GET {saputility}/descriptions/{objectId}/HeaderText` | `objectId` (ordrens langtekst) |
| `GET {saputility}/descriptions/{operationObjectId}/OperationText` | én gang pr. operation, i serie, efter `operations` |

`{woe}`, `{inventory}` og `{saputility}` er miljøvariablerne
`BioSap-WOE-BaseUrl`, `BioSap-Inventory-BaseUrl` og `BioSap-SapUtility-BaseUrl`
(se nedenfor): de skifter, når solutionen flyttes til et andet miljø.
Hvert API får sit eget token (eget scope), alle med samme app-registrering;
scopes og token-URL står i handlingen `Setup`.

### Id'erne

`objectId` er `OR` + ordrenummeret fyldt op til 12 cifre (ordre 26436811 →
`OR000026436811`, som i API-teamets eksempel). Operationernes objektnummer
tages fra `objectId`, `objectNumber` eller `objnr` på hver operation;
mangler det, springes OperationText over for den operation. Passer
feltnavnet ikke til WOE's svar, rettes det i `Compose_operation_object_id`.

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
  "orderNumber": "26436811", "objectId": "OR000026436811",
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
  "headerText":    {"status": 200, "data": {…}},
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
objekt), når nøgle eller base-URL til SAP Utility eller inventory ikke er
sat, eller tokenet ikke kunne hentes.

### Sådan ses JSON-svaret

Åbn kørslen i Power Automate (flowet > kørselshistorik), klik på handlingen
`Result` og læs *Outputs*; er svaret stort, står der *Click to download*.
De enkelte kald (`Call_header`, `Call_operations` …) viser hver sit svar
under *Outputs > Body*. Handlingen `Respond_result` viser kun `result` som
én lang tekst, så den er sværere at læse.

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
| `BioSap-WOC-Client-Secret` | alle | Som i docs/44: alle API'erne kører med samme app-registrering `6b699286-…` (Peter 2026-10-23) |
| `BioSap-WOE-Dev-ApiKey` | WOE | Som i docs/44 |
| `BioSap-WOE-BaseUrl` | WOE | Base-URL uden afsluttende skråstreg, i DEV `https://dev.api.orsted.dk/woe/api` |
| `BioSap-Inventory-Dev-ApiKey` | inventory | Som i docs/44 (lagerflowet) |
| `BioSap-Inventory-BaseUrl` | inventory | I DEV `https://dev.api.orsted.dk/inventorymanagement` |
| `BioSap-SapUtility-Test-ApiKey` | SAP Utility | `x-apikey` til SAP Utility i test, som i testflowet i [docs/37](37-fl-api-test.md) |
| `BioSap-SapUtility-BaseUrl` | SAP Utility | I test `https://test.api.orsted.dk/saputility` |

Mangler secret, WOE-nøglen eller WOE-base-URL'en, svarer flowet `ok = no`
med en besked og stopper som Failed. Inventory og SAP Utility er valgfri:
mangler nøgle eller base-URL, kører resten alligevel, og `movements.data`
eller `attachments.data` fortæller, hvad der ikke er sat op
(`headerText` og `operationTexts` er så tomme).

Token-kaldene har *Secure inputs* og *Secure outputs*, API-kaldene *Secure
inputs*.

## Handlinger

| Handling | Hvad den gør |
|---|---|
| `Setup` | Token-URL, client ID og de tre scopes |
| `Check_environment_variables` | Svarer appen og stopper, hvis en WOE-variabel mangler |
| `Compose_object_id` | Ordrens objektnummer `OR…` |
| `Initialize_variable_*` | `OperationTexts`, `Attachments`, `HeaderText`, `Movements` |
| `Get_token` / `Token_ok` | Token til WOE; ved fejl `Respond_token_error` |
| `Call_header` … `Call_feedback` | De ni WOE-kald, parallelt |
| `Inventory_configured` / `Get_token_inventory` / `Call_movements` | Vareudtag og returer, parallelt med WOE-kaldene; kun når inventory-nøgle og base-URL er sat |
| `SapUtility_configured` | Efter `operations`; kun når SAP Utility-nøgle og base-URL er sat |
| `Get_token_saputility` / `Token_saputility_ok` | Token til SAP Utility |
| `Call_attachments` / `Call_header_text` | Attachments og ordrens langtekst på objektnummeret, parallelt |
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
| `attachments` / `headerText` | 404 | Objektnummeret `OR…` passer ikke til ordren |

Kontrakttest: `tests/test_woe_order_flow.py`.

# 44 — Flows til WOE- og lager-API'et i DEV

To flows i solutionen, som appen kan kalde. Hvert flow henter et JWT-token
med client credentials og kalder sit endpoint på API-gatewayen i DEV med
`x-apikey`. De afløser testflowet `BioSap-Test-DevApis` fra PR #549.

| Flow | Input fra appen | Endpoint |
|---|---|---|
| `BioSap-Integration-WoeOrderObjects` | `OrderNumber` | `GET https://dev.api.orsted.dk/woe/api/workorders/{OrderNumber}/objects` |
| `BioSap-Integration-MaterialStock` | `Plant`, `Material` | `GET https://dev.api.orsted.dk/inventorymanagement/materialonstocks/{Plant}/{Material}`, derefter `…/materialonstocks/{Plant}/{storageLocation}/{Material}` for hver lagerplacering i svaret |

API-teamet åbnede først kun lager-rollen for `materialonstocks/2806/1019`.
Peter har bedt om `inventories/{plantKey}` og begge `materialonstocks`-kald.
Indtil de er åbnet, giver de 403.

### Lagerflowets to kald

Det første kald giver lagerplaceringerne for materialet, fx
`[{"storageLocation": "99", "storageLocationDescription": "Værktøjslager", "storageBin": "4345"}]`.
Svarer det 200, kalder flowet
`materialonstocks/{Plant}/{storageLocation}/{Material}` for hver placering,
én ad gangen, med samme token. Resultatet samles i feltet `details`.

## Svaret til appen

Begge flows svarer altid med de samme fire tekstfelter, også ved fejl:

| Felt | Indhold |
|---|---|
| `ok` | `yes` når API'et svarede 200, ellers `no` |
| `status` | HTTP-status fra API'et, eller fra token-kaldet hvis tokenet fejlede |
| `message` | Tom ved 200, ellers en engelsk fejltekst til brugeren |
| `result` | API'ets svar som JSON-tekst (tom ved token-fejl). For lagerflowet: svaret fra det første kald |
| `details` | Kun lagerflowet: JSON-tekst med én række pr. lagerplacering: `storageLocation`, `storageLocationDescription`, `storageBin`, `status` (HTTP-status for det andet kald) og `stock` (dets svar). Tom liste `[]`, hvis det første kald ikke gav 200 |

Eksempel i Power Fx (flowet skal først tilføjes som datakilde i appen):

```
Set(
    varWoeAnswer,
    'BioSap-Integration-WoeOrderObjects'.Run(Trim(txtOrderNumber.Text))
);
If(
    varWoeAnswer.ok = "yes",
    Set(varWoeObjects, ParseJSON(varWoeAnswer.result)),
    Notify(varWoeAnswer.message, NotificationType.Error)
)
```

```
Set(
    varStockAnswer,
    'BioSap-Integration-MaterialStock'.Run("2806", "1019")
);
ClearCollect(
    colStockLocations,
    ForAll(
        Table(ParseJSON(varStockAnswer.details)),
        {
            StorageLocation: Text(ThisRecord.Value.storageLocation),
            Description: Text(ThisRecord.Value.storageLocationDescription),
            StorageBin: Text(ThisRecord.Value.storageBin),
            Status: Value(ThisRecord.Value.status),
            MaterialDescription: Text(ThisRecord.Value.stock.materialDescription),
            Total: Value(ThisRecord.Value.stock.total),
            Reserved: Value(ThisRecord.Value.stock.reserved),
            Available: Value(ThisRecord.Value.stock.available),
            Unit: Text(ThisRecord.Value.stock.unitMeasurement)
        }
    )
)
```

Det andet kald svarer med ét objekt pr. placering, fx:

```json
{
  "plantKey": 2806, "storageLocation": "99", "materialNumber": "1019",
  "materialDescription": "Vindejern Clou Ø45",
  "total": 4, "reserved": 0, "available": 4, "unitMeasurement": "PC",
  "reorderPoint": 0, "displayReorderPoint": false, "decimalsAllowed": false,
  "storageLocationDescription": "", "storageBin": "4345"
}
```

`storageLocationDescription` er tom i det andet svar, så beskrivelsen tages
fra det første kald.

Felterne i `result` bestemmes af API'et. Se API-dokumentationen (Scalar)
eller kør flowet én gang og læs svaret i kørselshistorikken.

## Hemmeligheder

Repoet er offentligt, så client secret og de to `x-apikey`-nøgler står kun
som *Current value* på miljøvariabler i miljøet:

| Miljøvariabel | Bruges af | Værdi |
|---|---|---|
| `BioSap-WOC-Client-Secret` | begge | Client secret til app-registreringen `6b699286-…` (den samme som `BioSap-Integration-Order-Objects`). Både KKTEO og PowerAppSecret4 virker |
| `BioSap-WOE-Dev-ApiKey` | WOE | `x-apikey` til WOE i DEV |
| `BioSap-Inventory-Dev-ApiKey` | lager | `x-apikey` til inventory management i DEV |

Mangler en værdi (tom eller `***REDACTED***`), svarer flowet appen med
`ok = no` og en besked om, hvilken variabel der skal sættes, og kørslen
ender som Failed. Token-kaldet har *Secure inputs* og *Secure outputs*,
API-kaldet *Secure inputs*, så secret, nøgle og token ikke kan ses i
kørselshistorikken.

Client ID, tenant, scope og base-URL står i handlingen `Setup` i hvert flow.
Ret dem der ved skift fra DEV til test eller produktion.

## Handlinger

| Handling | Hvad den gør |
|---|---|
| `Setup` | Token-URL, client ID, scope og base-URL |
| `Check_environment_variables` | Svarer appen og stopper, hvis en miljøvariabel mangler |
| `Get_token` | POST til Entra ID (skjult i historikken) |
| `Call_API` | GET med `Authorization: Bearer …` og `x-apikey` |
| `For_each_location` / `Call_API_location` | Kun lagerflowet: det andet kald pr. lagerplacering, i serie |
| `Append_location_stock` | Kun lagerflowet: lægger placering, status og svar i `StockDetails` |
| `Respond_result` | Svarer appen med status og svar, også når API'et ikke svarer 200 |
| `Respond_token_error` | Svarer appen med Entra ID's `error_description` og stopper kørslen som Failed |

Der er ingen genforsøg, så appen får svar med det samme.

## Typiske fejl

| `status` / besked | Årsag |
|---|---|
| `401` + "Token could not be fetched" | Forkert eller udløbet client secret |
| `400` + "Token could not be fetched" | Forkert scope i `Setup` |
| `401` fra API'et | Mangler eller forkert `x-apikey`, eller tokenet er til det forkerte scope |
| `403` fra API'et | App-registreringen har ikke rollen til netop det endpoint |
| `404` fra API'et | Ordren eller materialet findes ikke i DEV |

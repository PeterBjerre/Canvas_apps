# 37 — Testflow til FL-API'et (SAP Utility)

Et selvstændigt flow, der kalder API-teamets nye endpoint til opslag af
Functional Locations. Det er kun til test og er ikke koblet på nogen app.

```
GET https://test.api.orsted.dk/saputility/functionallocations/{objektId}
```

| Fil | Indhold |
|---|---|
| [`flow/fl-api-test/definition.json`](../flow/fl-api-test/definition.json) | Flowets definition (kilden) |
| [`flow/fl-api-test/FL-API-Test.zip`](../flow/fl-api-test/FL-API-Test.zip) | Importpakken, bygget med `python3 tools/build_fl_api_test.py` |

## Sådan kommer flowet ind

1. Power Automate → **My flows** → **Import** → **Import Package (Legacy)**.
2. Vælg `FL-API-Test.zip`. Pakken har ingen forbindelser, så der skal ikke
   vælges nogen. Tryk **Import**.
3. Åbn flowet `BioSap-Test-FL-API (SAP Utility)` og udfyld de to tomme
   variabler:
   - `Initialize variable ClientSecret` → *Value*: client secret fra API-teamet
   - `Initialize variable ApiKey` → *Value*: værdien til headeren `x-apikey`
4. Gem.

Hemmelighederne står kun i flowet i Power Automate, aldrig i repoet: repoet
er offentligt, og `tests/test_fl_api_test.py` fejler, hvis variablerne ikke
er tomme. Begge variabler og begge HTTP-kald har *Secure inputs* slået til,
så værdierne og tokenet ikke kan ses i kørselshistorikken.

Flowet bruger HTTP-handlingen, som er premium, ligesom
`BioSap-Integration-FunctionalLocations`.

## Kør testen

**Run** → skriv et FL objekt-ID, fx `IF00000000000000584237`. Lader du feltet
stå tomt, bruges det ID fra API-teamets mail.

| Handling | Hvad den viser |
|---|---|
| `Opsaetning` | Token-URL, client ID, scope og base-URL. Ret dem her |
| `Hent_token` | POST til Entra ID med client credentials (skjult i historikken) |
| `Token_fejl` | Kun ved fejl: status og `error_description` fra Entra ID |
| `Kald_API` | GET til endpointet med `Authorization: Bearer …` og `x-apikey` |
| `Svar` | Objekt-ID, URL, HTTP-status og hele svaret |
| `Fundet` | Ved 200: `functionKey`, `objectId`, `description`, `room`, `sortField` |

Kørslen ender som **Failed**, hvis tokenet eller API-kaldet ikke giver 200, så
en fejl er let at se i historikken. Der er ingen genforsøg, så fejlen kommer
med det samme.

Forventet svar for eksemplet (fra Postman):

```json
{
  "functionKey": "SSV13 HFC10AP001",
  "objectId": "IF00000000000000584237",
  "description": "Smøreoliepumpe Kulmølle 10",
  "room": "",
  "sortField": ""
}
```

## Typiske fejl

| Hvor | Status | Sandsynlig årsag |
|---|---|---|
| `Token_fejl` | 400/401 | `ClientSecret` er tom eller forkert (`invalid_client`) |
| `Svar` | 401 | `ApiKey` er tom eller forkert, eller tokenet passer ikke til API'et |
| `Svar` | 403 | App-registreringen mangler i autorisationsgruppen |
| `Svar` | 404 | Objekt-ID'et findes ikke |

## Når det skal i drift

Flowet er bygget til at teste. Når API'et skal bruges fra en app, bør secret og
API-nøgle flyttes til miljøvariabler i solution BIO SAP, som
`BioSap-WOC-Client-Secret` i `BioSap-Integration-FunctionalLocations`, og
triggeren skiftes til *Power Apps (V2)*.

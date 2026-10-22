# 44 — Testflow til WOE- og lager-API'et i DEV

Et testflow i solutionen, der henter et JWT-token med client credentials og
kalder to endpoints på API-gatewayen i DEV. Det er kun til test og er ikke
koblet på nogen app.

```
GET https://dev.api.orsted.dk/woe/api/workorders/{ordre}/objects
GET https://dev.api.orsted.dk/inventorymanagement/materialonstocks/{plant}/{materiale}
```

| Fil | Indhold |
|---|---|
| `solution/BIOSAP/src/Workflows/BioSap-Test-DevApis-8E2F4C71-….json` | Flowet `BioSap-Test-DevApis` |
| `solution/BIOSAP/src/environmentvariabledefinitions/orsted_BioSapWoeDevApiKey` | Miljøvariabel `BioSap-WOE-Dev-ApiKey` |
| `solution/BIOSAP/src/environmentvariabledefinitions/orsted_BioSapInventoryDevApiKey` | Miljøvariabel `BioSap-Inventory-Dev-ApiKey` |

## Hemmeligheder

Repoet er offentligt, så client secret og de to `x-apikey`-nøgler står kun
som *Current value* på miljøvariabler i miljøet:

| Miljøvariabel | Værdi |
|---|---|
| `BioSap-WOC-Client-Secret` | Client secret til app-registreringen `6b699286-…`. Det er den samme app-registrering, som `BioSap-Integration-Order-Objects` bruger, så secret'en deles. Har API-teamet givet en ny secret, så sæt den her; en gyldig secret virker for begge flows |
| `BioSap-WOE-Dev-ApiKey` | `x-apikey` til WOE i DEV |
| `BioSap-Inventory-Dev-ApiKey` | `x-apikey` til inventory management i DEV. Er det samme nøgle som til WOE, så sæt samme værdi i begge |

Mangler en værdi (tom eller `***REDACTED***`), stopper flowet med det samme
med en besked om, hvilke variabler der skal sættes. Token-kald og API-kald
har *Secure inputs* slået til, og token-kaldet også *Secure outputs*, så
secret, nøgler og token ikke kan ses i kørselshistorikken.

Client ID, tenant, scopes og URL'er er ikke hemmelige og står i handlingen
`Opsaetning`. Ret dem der, hvis API-teamet giver nye.

| Nøgle i `Opsaetning` | Værdi |
|---|---|
| `tokenUrl` | `https://login.microsoftonline.com/100b3c99-…/oauth2/v2.0/token` |
| `clientId` | `6b699286-72e8-4e8a-8e93-ce166f5c22d0` |
| `woeScope` | `https://Dongenergy.onmicrosoft.com/b6608a78-4d04-462b-a5da-d5488f8b164c/.default` |
| `lagerScope` | `https://Dongenergy.onmicrosoft.com/70b9b214-2a2b-41ed-a9e2-aa639525d063/.default` |

De to API'er har hver sit scope, så flowet henter to tokens.

## Kør testen

**Run** → udfyld ordrenummer, plant og materiale, eller lad felterne stå
tomme for at bruge eksemplerne fra API-teamet (ordre `25711067`, plant
`2806`, materiale `1019`). API-teamet har kun åbnet rollen for
`materialonstocks/2806/1019`, så andre plant/materiale-kombinationer kan
give 403, indtil de åbner mere.

De to API'er kaldes parallelt, så en fejl i det ene stopper ikke det andet.

| Handling | Hvad den viser |
|---|---|
| `Tjek_miljoevariabler` | Stopper, hvis en af de tre miljøvariabler mangler |
| `Hent_token_Woe` / `Hent_token_Lager` | POST til Entra ID (skjult i historikken) |
| `Token_fejl_Woe` / `Token_fejl_Lager` | Kun ved fejl: status og `error_description` fra Entra ID |
| `Kald_Woe` / `Kald_Lager` | GET med `Authorization: Bearer …` og `x-apikey` |
| `Svar_Woe` / `Svar_Lager` | URL, HTTP-status og hele svaret |
| `Begge_ok` | Kørslen ender som **Failed**, hvis ikke begge svarer 200, med fx `WOE: API 200, Lager: Token 401` |

Der er ingen genforsøg, så fejlen kommer med det samme.

## Typiske fejl

| Resultat | Årsag |
|---|---|
| `Token 401` / `invalid_client` | Forkert eller udløbet client secret |
| `Token 400` / `invalid_scope` | Forkert scope i `Opsaetning` |
| `API 401` | Mangler eller forkert `x-apikey`, eller tokenet er til det forkerte scope |
| `API 403` | App-registreringen har ikke rollen til netop det endpoint |
| `API 404` | Ordren eller materialet findes ikke i DEV |

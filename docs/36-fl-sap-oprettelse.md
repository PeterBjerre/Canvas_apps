# 36 — FL-anmodninger i SAP: samme opretter, samme mappe

**Beslutning (2026-10-03):** FL-anmodninger fra appen oprettes i SAP af den
samme projektmappe som VH-planerne. Den hedder nu **SAP Opretter** (før
*VH-plan Opretter*). Selve GUI-scriptet er SPOOL-arkets: samme transaktioner,
samme felt-ID'er og samme regler for klasser, karakteristikker og
tilladelser. Data kommer som én JSON-fil pr. anmodning i det samme bibliotek
`SAP-oprettelse` som VH-planerne ([`34-sap-oprettelse.md`](34-sap-oprettelse.md)).

| Hvad | Hvor |
|---|---|
| Opretteren | [`excel/opretter/`](../excel/opretter): `VhpFl` (regler og validering), `VhpFlSteps` (SAP), `VhpFlRun` (kørslen) |
| Ordren (JSON) | [`schema/fl-sap-order.schema.json`](../schema/fl-sap-order.schema.json), eksempel [`example-fl-sap-order.json`](../schema/example-fl-sap-order.json) |
| Kvitteringen (JSON) | [`schema/fl-sap-receipt.schema.json`](../schema/fl-sap-receipt.schema.json), eksempel [`example-fl-sap-receipt.json`](../schema/example-fl-sap-receipt.json) |
| De to flows | Afsnit 5 nedenfor, udtrykkene i [`flow/sap-ordre/fl-*`](../flow/sap-ordre) |
| Mapper og kolonner | [`Provision-SapCreation.ps1`](../sharepoint/provision/Provision-SapCreation.ps1) |
| SPOOL-arkets script, til sammenligning | [`excel/vba/spool-gui/`](../excel/vba/spool-gui) |
| Tests | `tests/test_sap_contract.py` (FL-afsnittet), `tests/test_vba_runner.py` |

## 1. Kort svar

For teamet er der intet nyt at lære. Listen på arket *Start* viser nu både
VH-planer og FL-anmodninger (kolonnen *Type*), og det er de samme tre knapper:
*Opdater liste*, *Vis detaljer* (før *Vis plan*) og *Opret i SAP*.

Når rekvirenten trykker *Submit* i appen, bliver anmodningen *Indsendt*. Et
flow skriver så hele anmodningen i én fil, fx `FL-000012_20261003-081500.json`,
i *Til oprettelse*. Opretteren laver hver FL med IL01, eller IL02, hvis den
findes i forvejen. Til sidst lægger den en kvittering i *Kvitteringer/FL*. Et
andet flow skriver resultatet på hver række, sætter anmodningen til
*OprettetISAP*, opdaterer landingssiden og sender rekvirenten en mail.

## 2. Sådan hænger det sammen

```
 App: Submit ─► FunctionalLocationRequests.Status = Indsendt
                    │
                    └─► flow BioSap-FL-SapOrder
                          skriver SAP-oprettelse/Til oprettelse/FL-000012_20261003-081500.json
                          og SapOrderGuid paa anmodningen
                                   │  OneDrive
                                   ▼
                      SAP Opretter (samme projektmappe som VH-planerne)
                      pr. raekke:  IL01 (eller IL02) → General → Location → Structure (KAB)
                                   → tilladelser → klasser → karakteristikker → Gem
                      statusfil efter hver FL
                                   │
                      SAP-oprettelse/Kvitteringer/FL/FL-000012_….kvittering.json
                                   │  OneDrive
                                   ▼
                      flow BioSap-FL-SapReceipt (hvert 10. minut)
                      SapResult paa raekkerne, Status = OprettetISAP,
                      landingssiden, mail til rekvirenten
```

FL-kvitteringerne har deres egen mappe og deres eget flow. VH-planernes
kvitteringsflow ser kun filerne direkte i *Kvitteringer*, så det skal ikke
røres.

## 3. Taget fra SPOOL-arket

Porten er lavet fra `FL indberetninger udgave SPOOL V3.xlsm` (i
`excel/artifact/`). De moduler, der opretter, er trukket ud til
[`excel/vba/spool-gui/`](../excel/vba/spool-gui).

| Trin | SPOOL | Opretteren |
|---|---|---|
| IL01 med mærke og strukturindikator. Findes FL'en ("already exists"), så IL02 | `FillMasterdataFields` | `VhpFlSteps.OpenFunctionalLocation` |
| Beskrivelse, objekttype `s`, producent, model, part- og serienummer | samme | `FillGeneral` |
| Rum, ABC, sorteringsfelt, garantidatoer og de to garantiflueben | samme | `FillLocation` |
| Overordnet FL, kun KAB | samme | `FillSuperior` |
| Tilladelser ATEX, Risiko, ASBEST, PTW. Ved IL02 ryddes de gamle først | samme | `FillPermits` |
| Ved IL02: de gamle klasser slettes | samme | `DeleteClasses` |
| Klassen, undtagen NO CLASS og SIGNAL. TRM, hvis *TRM assignment* = X. WCM på ELF. GIV_EXT på GIV, hvis *GIV_EXT assignment* = X | `RunGUIScript_Core` | `AssignClasses`, `VhpFl.ExtraClasses` |
| Karakteristikkerne efter navn på skærmen, side for side. *Remarks*, *Supply from* og *Safety Critical Equipment* med flere værdier i værdidialogen (F4) | `FillCharacteristicsBatch` | `FillCharacteristics` |
| Gem. En dialog betyder "ikke gemt" | `SaveFLAndGetStatus` | `SaveAndCheck` |

**Hvad der er det samme, og hvordan det er sikret:**

- **Felt-ID'erne** står i `VhpConfig.bas` (FL-afsnittet). Testen
  `test_fl_screen_ids_are_spools` tjekker, at alle 54 står ordret i SPOOL's
  `GUI_SCRIPT.bas`.
- **Tabellen over karakteristikker** er SPOOL's *DictionaryTable* med 130
  rækker: klasse → feltnavn. Den ligger i arket *Opslag* som tabellen
  *Karakteristikker*. `test_fl_characteristic_seed_is_spools` læser SPOOL-arket
  og sammenligner række for række. `test_fl_characteristics_are_app_fields`
  tjekker, at hvert felt findes i appen for klassen.
- **Feltnavnene** for stamdata (`FLF_*` i `VhpConfig`) findes i appen
  (`test_fl_app_fields_exist`).

**Hvad der er ændret, og hvorfor:**

| SPOOL | Opretteren | Hvorfor |
|---|---|---|
| En fejl gav en MsgBox og stoppede alt | Rækken fejler med SAP's tekst, og SAP efterlades på et kendt billede. De andre rækker oprettes | Én dårlig række skal ikke stoppe 50 gode |
| Listen over karakteristikfelter blev genbrugt efter en værdidialog | Siden læses forfra efter hver dialog | SAP tegner siden om, og en gammel liste peger forkert (docs/15) |
| En af de tre særlige karakteristikker kunne blive skrevet i sidens første felt, hvis den lå på en anden side | Den skrives aldrig et andet sted. Den bliver en advarsel i kvitteringen | Hellere en manglende værdi end en forkert |
| En karakteristik, der ikke fandtes, blev kun skrevet i Debug-vinduet | Advarsel i kvitteringen og under *Detaljer* | Så nogen ser det |
| Gem uden besked blev regnet for gemt | Se efter i IL03, før rækken regnes for gemt | Kvitteringen må ikke sige "oprettet" om noget, der ikke er |
| IL02 brugte altid strukturindikator KKS | IL02 bruger rækkens egen (KKS, KKSKV, KKSKA) | Samme som IL01 |
| Garantidato som Excel-dato | `YYYYMMDD` laves om til `DD.MM.YYYY` | Appen tillader begge (docs/31, FL34) |

**Et tomt felt bliver også tomt i SAP**, som i SPOOL. Ved IL02 betyder det, at
en værdi, der står i SAP, men ikke i anmodningen, bliver slettet. *Detaljer*
siger det øverst.

## 4. Ordren og kvitteringen

Ordren er anmodningen og dens rækker fra `FunctionalLocationItems`. Spool-felterne
står som par af felt og værdi, med appens feltnavne (`POWER [KW]`, versaler).
Opretteren sammenligner uden at skelne mellem store og små bogstaver, så
`POWER [KW]` i appen rammer *Power [kW]* på SAP-skærmen.

| Felt i appen | I SAP |
|---|---|
| Functional Location, StrIndicator (`KksType`) | IL01/IL02, indgangsbilledet |
| Description | Beskrivelse (40 tegn) |
| Manufacturer, Model Number, Manufacturer Part/Serial Number | Fanen General |
| Room, ABC Indic., Sort Field, Warranty Start/End | Fanen Location |
| Superior FL | Fanen Structure (kun KAB) |
| Atex, Risiko, Asbestos, PTW (`X`) | Tilladelser ATEX, Risiko, ASBEST, PTW |
| TRM assignment, GIV_EXT assignment (`X`) | Ekstra klasser TRM og GIV_EXT |
| Klassens felter, TRM's og GIV_EXT's | Karakteristikker, efter tabellen *Karakteristikker* |

**Overføres ikke**, heller ikke af SPOOL: *Long text*, *DLFL*,
dokumentfelterne (*Datasheet*, *Document number* …), *User status* og
*Switching location*. *Detaljer* viser for hver række, hvilke udfyldte felter
der ikke kommer med.

**Kvitteringen** har en række pr. FL: `done`, `result` (`Created` med IL01,
`Updated` med IL02), `sapMessage` (statuslinjen efter Gem) og `lastError`.
Anmodningen er `Created`, når alle rækker er gemt. Indtil da er den `Partial`,
og en ny kørsel tager kun de rækker, der mangler.

## 5. Flowene

To nye flows i solution BIO SAP, bygget som VH-planernes i
[`35-flow-sap-ordre.md`](35-flow-sap-ordre.md). Variablen
`FlowRunHistoryLink`, scopet `Try`, scopet `Catch` med fejlmail, ejer og
forbindelser er de samme. Afsnittet her siger kun, hvad der er anderledes.

**Før du begynder:**

1. Kør `Provision-SapCreation.ps1` igen. Den laver mapperne
   *Kvitteringer/FL*, *Kvitteringer/FL/Behandlet* og
   *Kvitteringer/FL/Afvist* og kolonnerne `SapOrderGuid`, `SapOrderFile`,
   `SapCreatedOn` og `SapCreatedBy` (FunctionalLocationRequests) samt
   `SapResult` og `SapMessage` (FunctionalLocationItems). FL-listerne skal
   findes i forvejen (`Provision-FunctionalLocationLists.ps1`).
2. To nye miljøvariabler af typen *Data source (liste)*:
   `BioSap-List-FunctionalLocationRequests` og
   `BioSap-List-FunctionalLocationItems`. `BioSap-Environment`,
   `BioSap-SapSystem`, `BioSap-SiteUrl` og `BioSap-ErrorNotifiers` findes
   allerede.

| Fil | Bruges i |
|---|---|
| `fl-ordre-0-trigger.txt` | C: triggerbetingelsen |
| `fl-ordre-1-select-rows.json` | C: *Select rows* |
| `fl-ordre-2-compose-order.json` | C: *Compose order* |
| `fl-ordre-3-merge-request.json` | C: gem ordren på anmodningen |
| `fl-ordre-4-merge-request-reset.json` | C: nulstil, når anmodningen sendes retur |
| `kvittering-0-filter.txt`, `kvittering-1-compose.txt` | D: de samme som i VH-planernes flow |
| `fl-kvittering-2-betingelse.txt` | D: er kvitteringen gyldig? |
| `fl-kvittering-3-merge-row.json` | D: resultatet på hver række |
| `fl-kvittering-4-merge-request.json` | D: anmodningen bliver *OprettetISAP* |
| `fl-kvittering-5-merge-index.json` | D: landingssiden (MD_RequestIndex) |
| `fl-kvittering-6-mail-row.txt` | D: en række i mailen til rekvirenten |

### Flow C — `BioSap-FL-SapOrder`

```
When an item is created or modified    FunctionalLocationRequests, betingelse: fl-ordre-0
Initialize variable  OrderGuid         guid()
Initialize variable  OrderFile         FL-000012_20261003-081500.json
Initialize variable  FlowRunHistoryLink
Try
  Condition  Ny ordre                  Status er Indsendt, UnderBehandling eller KlarTilSAP
    Ja
      Get items    Get items FunctionalLocationItems
      Select       Select rows                           fl-ordre-1
      Compose      Compose order                         fl-ordre-2
      Create file  Create file                           /SAP-oprettelse/Til oprettelse
      Send an HTTP request to SharePoint  Set SapOrderGuid     fl-ordre-3
    Nej
      Send an HTTP request to SharePoint  Clear SapOrderGuid   fl-ordre-4
Catch                                  fejlmail
```

1. **Triggeren:** *When an item is created or modified* på
   `BioSap-List-FunctionalLocationRequests`. Concurrency 1. Triggerbetingelsen
   er hele `fl-ordre-0-trigger.txt`:

   | `Status` | `SapOrderGuid` | Flowet |
   |---|---|---|
   | Indsendt, UnderBehandling eller KlarTilSAP | tom | skriver en ordre (Ja) |
   | Kladde, AfventerInfo, Afvist eller Annulleret | udfyldt | tømmer den (Nej) |
   | ellers | | kører ikke |

   En anmodning, Master Data sender retur (*AfventerInfo*), og som rekvirenten
   indsender igen, får altså en ny ordre. Opretteren bruger den nyeste og
   flytter den gamle til *Oprettet*, når den nye er gemt. Det er ufarligt for
   FL: en FL, der findes, bliver ændret med IL02, ikke oprettet to gange.
2. **Variablerne:** `OrderGuid` = `guid()`. `OrderFile` =
   `concat(triggerBody()?['Title'], '_', formatDateTime(utcNow(), 'yyyyMMdd-HHmmss'), '.json')`.
   `Title` er `RequestNo`.
3. **Betingelsen *Ny ordre*:**
   `contains(createArray('Indsendt', 'UnderBehandling', 'KlarTilSAP'), triggerBody()?['Status']?['Value'])`
   *is equal to* `true`.
4. **Get items FunctionalLocationItems:** *List Name*
   `BioSap-List-FunctionalLocationItems`, *Filter Query*
   `RequestGuid eq '@{triggerBody()?['RequestGuid']}'`, *Order By* `RowNo`,
   **Top Count `5000`**.
5. ***Select rows*** fra `body('Get_items_FunctionalLocationItems')?['value']`
   med `fl-ordre-1-select-rows.json` i teksttilstand. Spool-felterne står i
   `SpoolValuesJson` som tekst. `values` laver dem om til en liste.
6. ***Compose order*** med `fl-ordre-2-compose-order.json`, ***Create file***
   som i VH-flowet, og de to HTTP-kald som i docs/35, 7–8. Brug
   `_api/web/lists(guid'@{parameters('BioSap-List-FunctionalLocationRequests (orsted_BioSapListFunctionalLocationRequests)')}')/items(@{triggerBody()?['ID']})`
   og `fl-ordre-3` eller `fl-ordre-4` som *Body*.

Vil Master Data have en mail, når der er noget at oprette, så tilføj *Send an
email (V2)* til `BioSap-MasterDataEmail` efter *Create file*. Det er valgfrit,
for anmodningen står i listen i opretteren.

### Flow D — `BioSap-FL-SapReceipt`

```
Recurrence                             hvert 10. minut
Initialize variable  FlowRunHistoryLink
Try
  Get files (properties only)          SAP-oprettelse, mappen Kvitteringer/FL
  Filter array   Receipt files         kvittering-0
  Apply to each  Each receipt          én ad gangen
    Scope  Handle receipt
      Get file content   Get receipt content
      Compose            Receipt                      kvittering-1
      Get item           Get request                  FunctionalLocationRequests
      Condition          Valid receipt                fl-kvittering-2
        Ja
          Apply to each  Each row                     outputs('Receipt')?['rows']
            Send an HTTP request to SharePoint  Set row result       fl-kvittering-3
          Condition      Has index row                IndexItemId er udfyldt
            Ja: Send an HTTP request to SharePoint  Set index row    fl-kvittering-5
          Send an HTTP request to SharePoint    Set request created  fl-kvittering-4
          Move file  → Kvitteringer/FL/Behandlet
          Select         Mail rows                    fl-kvittering-6
          Send an email (V2)  → rekvirenten           (valgfri)
        Nej
          Move file  → Kvitteringer/FL/Afvist
          Send an email (V2)  → BioSap-ErrorNotifiers
    Move file  → Kvitteringer/FL/Afvist      kør efter: Handle receipt fejlede
    Send an email (V2)  → BioSap-ErrorNotifiers
Catch                                  fejlmail
```

Som VH-planernes kvitteringsflow (docs/35), med disse forskelle:

- ***Get files***: *Limit Entries to Folder* `/SAP-oprettelse/Kvitteringer/FL`.
- ***Get request***: *Get item* på `BioSap-List-FunctionalLocationRequests`,
  *Id* `outputs('Receipt')?['requestSpId']`.
- ***Valid receipt***: `fl-kvittering-2-betingelse.txt` *is equal to* `true`.
  Den tjekker `kind`, `state = Created`, `orderGuid` mod anmodningens
  `SapOrderGuid`, at anmodningen stadig er åben (Indsendt, UnderBehandling
  eller KlarTilSAP) og SAP-systemet.
- ***Each row*** over `outputs('Receipt')?['rows']`: MERGE på
  `_api/web/lists(guid'@{parameters('BioSap-List-FunctionalLocationItems (orsted_BioSapListFunctionalLocationItems)')}')/items(@{items('Each_row')?['spId']})`
  med `fl-kvittering-3-merge-row.json`.
- ***Set index row***: MERGE på landingssidens række,
  `_api/web/lists/GetByTitle('MD_RequestIndex')/items(@{body('Get_request')?['IndexItemId']})`,
  med `fl-kvittering-5-merge-index.json`. Den lukker anmodningen på
  landingssiden (`IsOpen = false`, trin 5). Betingelsen *Has index row* er
  `not(empty(body('Get_request')?['IndexItemId']))` *is equal to* `true`, så en
  anmodning uden indeksrække ikke stopper flowet.
- ***Set request created***: MERGE på anmodningen,
  `items(@{outputs('Receipt')?['requestSpId']})`, med
  `fl-kvittering-4-merge-request.json`. Den sættes efter rækkerne og
  landingssiden, så en fejl undervejs efterlader anmodningen åben, og
  kvitteringen kan køres igen.
- ***Mail rows*** og mailen kommer sidst, efter at kvitteringen er flyttet.
  Fejler mailen, er alt andet skrevet, og fejlmailen siger det. *Mail rows*
  er en *Select* fra `outputs('Receipt')?['rows']`. *Map* er udtrykket i
  `fl-kvittering-6-mail-row.txt`. Mailen går til
  `body('Get_request')?['RequesterEmail']` med emnet
  `FL-anmodning @{outputs('Receipt')?['requestNo']} er oprettet i SAP` og
  `<table>@{join(body('Mail_rows'), '')}</table>` i brødteksten.

**Rettigheder** som docs/35: de to flows kører med servicekontoen, som skal
kunne skrive i FL-listerne og i `MD_RequestIndex`. Biblioteket har allerede
de rigtige rettigheder.

## 6. Når noget går galt

- **"Kan ikke oprettes".** *Vis detaljer* viser fejlene. De fleste rettes i
  appen. Sæt anmodningen til *AfventerInfo* i SharePoint, så rekvirenten kan
  rette og indsende igen. Så kommer der en ny ordre.
- **En række fejlede ("Delvist oprettet").** Fejlen står i *Besked* og under
  *Detaljer*. Ret årsagen, i SAP eller i appen, og tryk *Opret i SAP* igen.
  Det, der er gemt, springes over.
- **Karakteristikken blev ikke fundet.** En advarsel i kvitteringen: navnet i
  tabellen *Karakteristikker* findes ikke på SAP-skærmen for klassen. Ret
  navnet i tabellen, så det står som i SAP.
- **En kvittering i *Kvitteringer/FL/Afvist*.** Mailen til
  `BioSap-ErrorNotifiers` siger hvorfor. Flyt den tilbage til *Kvitteringer/FL*
  for at prøve igen.

## 7. Afprøvning i SAP

Med *Bekræft hvert gem* slået til og DEV-anmodninger i GQ1:

1. En ny FL i *NO CLASS* uden TRM: kun stamdata. Se billedet igennem før *Ja*.
2. Den samme anmodning igen (indsend en kopi): nu IL02. Tilladelser og
   klasser ryddes og sættes igen.
3. GIV med TRM og GIV_EXT: tre klasser, *Owner*, *EX-Marking* og to værdier i
   *Safety Critical Equipment* (værdidialogen).
4. ELF: WCM tildeles. *Remarks* med to værdier (værdidialogen).
5. KAB med *Superior FL*.
6. En klasse med mange karakteristikker, fx MKP_HE med TRM, så der skal
   bladres.
7. En anmodning med en række, SAP afviser (fx en overordnet FL, der ikke
   findes). De andre rækker oprettes. Ret og kør igen.
8. Kvitteringsflowet: rækkerne får `SapResult`, anmodningen bliver
   *OprettetISAP*, landingssiden viser *Created in SAP*, og rekvirenten får
   mailen.

## 8. Ikke med

| | Hvorfor | I mellemtiden |
|---|---|---|
| *Initial Entry*-vejen i SPOOL (kun mærke, beskrivelse og klasse) | Appen sender altid de fulde data | — |
| *Switching location* (WCM) | SPOOL skriver den ikke, kun klassen WCM | Skal den med, så tilføj rækken *ELF – Switching location* i *Karakteristikker* og afprøv det i GQ1 |
| FL-styklister (IB11), materialer (ZSCM_MATUP), dokumenter | Egne funktioner i SPOOL, ikke en del af FL-oprettelsen | SPOOL-arket |
| RBR | Står i SPOOL's tabel, men appen kender ikke klassen | — |

## 9. De næste typer

Mønstret er det samme for hver type: et skema, to flows, et modul med
reglerne og et med SAP-skærmene. Det, der mangler, er GUI-scripts, der virker:

- **Material:** SPOOL-arket opretter materialer ved at uploade en udfyldt
  skabelon til `ZSCM_MATUP` og styklisten med IB11. Opretteren kan lave den
  samme fil ud fra appens data.
- **Equipment:** Der er intet script i repoet. Et optaget IE01-script eller
  det, I bruger i dag, er udgangspunktet.

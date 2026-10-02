# 35 — Flowene til oprettelse i SAP

To flows i solution BIO SAP flytter data mellem SharePoint og VH-plan Opretter
([`34-sap-oprettelse.md`](34-sap-oprettelse.md)):

| Flow | Starter | Gør |
|---|---|---|
| **A** `BioSap-VhPlan-SapOrder` | Når en plan ændres | Skriver ordrefilen, når planen bliver *Ready for creation in SAP* |
| **B** `BioSap-VhPlan-SapReceipt` | Hvert 10. minut | Læser opretterens kvitteringer og skriver numrene fra SAP tilbage |

Udtrykkene ligger som filer i [`flow/sap-ordre/`](../flow/sap-ordre) og sættes
ind med kopier/indsæt. Ret dem dér, ikke kun i flowet:
`tests/test_sap_contract.py` tjekker, at felterne er præcis skemaets, at
statusværdierne findes i `MaintenancePlans.Status`, og at parenteserne går op.

| Fil | Bruges i |
|---|---|
| `ordre-0-trigger.txt` | A: triggerbetingelsen |
| `ordre-1-select-items.json`, `ordre-2-…`, `ordre-3-…` | A: de tre *Select* |
| `ordre-4-compose-order.json` | A: *Compose order* |
| `ordre-5-merge-plan.json` | A: gem ordren på planen |
| `ordre-6-merge-plan-reset.json` | A: nulstil, når planen trækkes tilbage |
| `kvittering-0-filter.txt` | B: kun kvitteringsfiler |
| `kvittering-1-compose.txt` | B: læs kvitteringen |
| `kvittering-2-betingelse.txt` | B: er kvitteringen gyldig? |
| `kvittering-3-merge-item.json` | B: numrene på hvert item |
| `kvittering-4-merge-plan.json` | B: plannummer og *Published* |

## Før du begynder

1. **Bibliotek og kolonner.** Kør
   [`Provision-SapCreation.ps1`](../sharepoint/provision/Provision-SapCreation.ps1)
   mod sitet. Det opretter biblioteket `SAP-oprettelse` med mapperne og
   kolonnerne `SapOrderGuid`, `SapOrderFile`, `SapCreatedOn`, `SapCreatedBy`
   (MaintenancePlans) og `SapItemNo` (MaintenanceItems). Sæt rettighederne,
   se [Rettigheder](#rettigheder).
2. **Miljøvariabler.** Tre nye i solution BIO SAP:

   | Miljøvariabel | Type | DEV | TEST | PROD |
   |---|---|---|---|---|
   | `BioSap-Environment` | Text | `DEV` | `TEST` | `PROD` |
   | `BioSap-SapSystem` | Text | `GQ1` | `GQ1` | `GP1` |
   | `BioSap-List-TasklistMaterial` | Data source (liste) | `MD_TasklistMaterial` | samme | samme |

   Brug præcis de navne. Udtrykkene skriver dem med skemanavnet bagefter,
   fx `parameters('BioSap-Environment (orsted_BioSapEnvironment)')`.

   `BioSap-Environment` står i hver ordre, og opretteren sammenholder den med
   det SAP-system, I er logget på: DEV- og TEST-ordrer kan kun oprettes i et
   testsystem, PROD-ordrer kun i GP1. `BioSap-SapSystem` er kvitteringsflowets
   modstykke: en kvittering fra et andet system afvises.

   Disse findes i forvejen og bruges også: `BioSap-SiteUrl`,
   `BioSap-List-MaintenancePlans`, `BioSap-List-MaintenanceItems`,
   `BioSap-List-TaskListMain` og `BioSap-ErrorNotifiers`.
3. **Forbindelser og ejer.** Som de andre BioSap-flows: connection references
   `orsted_BioSapSharePointConn` og `orsted_BioSapOutlookConn`, og en
   servicekonto som ejer, ikke en navngiven bruger.
4. **Fejlhåndtering.** Byg begge flows som de eksisterende: variablen
   `FlowRunHistoryLink` øverst, arbejdet i scopet `Try` og scopet `Catch`
   (kør efter: `Try` mislykkedes, fik timeout eller blev sprunget over), der
   sender fejlmailen til `BioSap-ErrorNotifiers`. Det letteste er at kopiere
   variablen og `Catch` fra `BioSap-EmailNotification-PlanPublished`
   (*… → Copy action* og *Paste an action*).

**Navnene på handlingerne betyder noget**, for udtrykkene henviser til dem.
Power Automate skriver mellemrum som `_`, så handlingen *Select items* hedder
`Select_items` i et udtryk. Omdøb hver handling, før du sætter udtryk ind, der
bruger den.

## Flow A — `BioSap-VhPlan-SapOrder`

```
When an item is created or modified    MaintenancePlans, betingelse: ordre-0
Initialize variable  OrderGuid         guid()
Initialize variable  OrderFile         MP0133_20261002-084233.json
Initialize variable  FlowRunHistoryLink
Try
  Condition  Ny ordre                  Status = Ready for creation in SAP
    Ja
      Get items    Get items MaintenanceItems
      Get items    Get items TaskListMain
      Get items    Get items TasklistMaterial
      Select       Select items                           ordre-1
      Select       Select operations                      ordre-2
      Select       Select materials                       ordre-3
      Compose      Compose order                          ordre-4
      Create file  Create file                            /SAP-oprettelse/Til oprettelse
      Send an HTTP request to SharePoint  Set SapOrderGuid     ordre-5
    Nej
      Send an HTTP request to SharePoint  Clear SapOrderGuid   ordre-6
Catch                                  fejlmail
```

### 1. Triggeren

*SharePoint — When an item is created or modified*, *Site Address*
`BioSap-SiteUrl`, *List Name* `BioSap-List-MaintenancePlans`.

Under *Settings*: *Concurrency control* til, *Degree of parallelism* 1. Under
*Trigger conditions*: hele `ordre-0-trigger.txt` som én betingelse. Den står
på én linje og begynder med `@`.

Betingelsen lader flowet køre i to tilfælde:

| Planens `Status` | `SapOrderGuid` | Flowet |
|---|---|---|
| `Ready for creation in SAP` | tom | skriver en ordre (Ja) |
| hverken *Ready …* eller *Published* | udfyldt | tømmer den (Nej) |
| ellers | | kører ikke |

Der opstår ingen løkke. Ja-grenen udfylder `SapOrderGuid`, og Nej-grenen
tømmer den på en plan, der ikke er *Ready*. Den ændring trigger flowet igen,
men så er betingelsen falsk.

**Hvorfor Nej-grenen.** En plan, der trækkes tilbage fra *Ready* (sættes til
*Draft* eller *Returned* i SharePoint) og godkendes igen, skal have en ny
ordre med det rettede indhold. Det får den, fordi `SapOrderGuid` er tom igen.
Den gamle ordre bliver liggende i *Til oprettelse*, indtil den nye kommer. Så
viser opretteren den gamle som *Erstattet* og bruger den nye. Bliver den gamle
alligevel oprettet i mellemtiden, afviser kvitteringsflowet kvitteringen,
fordi `orderGuid` ikke passer. Opretteren nægter at oprette planen to gange
i samme SAP-system.

### 2. Variablerne

Øverst, uden for `Try`. Power Automate tillader kun *Initialize variable* på
øverste niveau.

| Name | Type | Value |
|---|---|---|
| `OrderGuid` | String | `guid()` |
| `OrderFile` | String | `concat(triggerBody()?['PlanID'], '_', formatDateTime(utcNow(), 'yyyyMMdd-HHmmss'), '.json')` |

### 3. Betingelsen *Ny ordre*

`triggerBody()?['Status']?['Value']` *is equal to* `Ready for creation in SAP`.

### 4. Ja: hent planens rækker

Tre *SharePoint — Get items*, alle med *Site Address* `BioSap-SiteUrl` og
**Top Count `5000`**:

| Navn | List Name | Filter Query | Order By |
|---|---|---|---|
| Get items MaintenanceItems | `BioSap-List-MaintenanceItems` | `MaintenancePlanNo/Id eq @{triggerBody()?['ID']}` | `ItemID` |
| Get items TaskListMain | `BioSap-List-TaskListMain` | `MaintenancePlanID/Id eq @{triggerBody()?['ID']}` | `OperationNo` |
| Get items TasklistMaterial | `BioSap-List-TasklistMaterial` | `PlanKey eq '@{triggerBody()?['PlanID']}'` | |

*Top Count* er ikke valgfri. Uden den henter *Get items* kun 100 rækker, og en
plan med 25 items med 5 operationer hver ville stille og roligt miste
operationer. 5000 er grænsen for én forespørgsel.

### 5. Ja: tre Select og én Compose

| Navn | From | Map |
|---|---|---|
| Select items | `body('Get_items_MaintenanceItems')?['value']` | `ordre-1-select-items.json` |
| Select operations | `body('Get_items_TaskListMain')?['value']` | `ordre-2-select-operations.json` |
| Select materials | `body('Get_items_TasklistMaterial')?['value']` | `ordre-3-select-materials.json` |

Skift *Map* til teksttilstand (ikonet til højre for *Map*) og sæt hele filen
ind. Derefter *Compose* **Compose order** med `ordre-4-compose-order.json` som
*Inputs*.

Værdierne er SharePoints egne. Al oversættelse til SAP sker i opretteren
(docs/34, afsnit 5), så ret ikke værdier til i flowet.

### 6. Ja: skriv filen

*SharePoint — Create file*:

| Felt | Værdi |
|---|---|
| Site Address | `BioSap-SiteUrl` |
| Folder Path | `/SAP-oprettelse/Til oprettelse` |
| File Name | `@{variables('OrderFile')}` |
| File Content | `@{outputs('Compose_order')}` |

### 7. Ja: gem ordren på planen

*SharePoint — Send an HTTP request to SharePoint*, navn **Set SapOrderGuid**:

| Felt | Værdi |
|---|---|
| Site Address | `BioSap-SiteUrl` |
| Method | `POST` |
| Uri | `_api/web/lists(guid'@{parameters('BioSap-List-MaintenancePlans (orsted_BioSapListMaintenancePlans)')}')/items(@{triggerBody()?['ID']})` |
| Headers | `Accept`: `application/json;odata=nometadata`<br>`Content-Type`: `application/json;odata=nometadata`<br>`IF-MATCH`: `*`<br>`X-HTTP-Method`: `MERGE` |
| Body | `ordre-5-merge-plan.json` |

Det er et HTTP-kald, fordi *Update item* kræver alle planens obligatoriske
kolonner og skriver dem igen. `MERGE` rører kun de to kolonner. Det er samme
greb, som `BioSap-EmailNotification-NewPlanCreated` bruger til
`InitialEmailSent`. Dér med `odata=verbose` og `__metadata`; med `nometadata`
skal listens entitetstype ikke med.

### 8. Nej: nulstil

Samme handling som i 7, navn **Clear SapOrderGuid**, med
`ordre-6-merge-plan-reset.json` som *Body*.

### 9. Når noget fejler

Så kommer fejlmailen. Ret årsagen og vælg *Resubmit* på kørslen. En ekstra
ordrefil gør ingen skade: opretteren bruger den nyeste, og kvitteringsflowet
godkender kun den, hvis `orderGuid` står på planen.

### 10. Filen i mailen (valgfrit)

Behold den mail, I får i dag, når en plan er klar. Den fortæller, at der er
noget at oprette, og filen ligger allerede i mappen. Skal filen med i mailen,
fx til en, der ikke har biblioteket synkroniseret, så tilføj efter *Create
file*:

1. *SharePoint — Get file content* med *File Identifier*
   `body('Create_file')?['Id']`.
2. *Office 365 Outlook — Send an email (V2)* til Master Datas fælles
   postkasse (`BioSap-MasterDataEmail`, docs/32) med *Attachments Name*
   `@{variables('OrderFile')}` og *Attachments Content*
   `body('Get_file_content')`.

Slå så den gamle mail fra, så I ikke får to. I opretteren lægges en vedhæftet
fil ind med *Importér fil…*.

## Flow B — `BioSap-VhPlan-SapReceipt`

```
Recurrence                             hvert 10. minut
Initialize variable  FlowRunHistoryLink
Try
  Get files (properties only)          SAP-oprettelse, mappen Kvitteringer
  Filter array   Receipt files         kvittering-0
  Apply to each  Each receipt          én ad gangen
    Scope  Handle receipt
      Get file content   Get receipt content
      Compose            Receipt                      kvittering-1
      Get item           Get plan
      Condition          Valid receipt                kvittering-2
        Ja
          Apply to each  Each item                    outputs('Receipt')?['items']
            Send an HTTP request to SharePoint  Set item numbers    kvittering-3
          Send an HTTP request to SharePoint    Set plan published  kvittering-4
          Move file  → Kvitteringer/Behandlet
        Nej
          Move file  → Kvitteringer/Afvist
          Send an email (V2)  → BioSap-ErrorNotifiers
    Move file  → Kvitteringer/Afvist         kør efter: Handle receipt fejlede
    Send an email (V2)  → BioSap-ErrorNotifiers
Catch                                  fejlmail
```

**Hvorfor hvert 10. minut og ikke "når en fil oprettes".** Kvitteringen kommer
til SharePoint via OneDrive-synkroniseringen, og Microsoft skriver, at
synkroniserede filer ikke udløser flows. Et flow, der selv kigger efter, er
ligeglad med, hvordan filen kom dertil. Planen bliver altså *Published* senest
10 minutter efter, at den er oprettet i SAP.

### 1. Find kvitteringerne

*SharePoint — Get files (properties only)*: *Site Address* `BioSap-SiteUrl`,
*Library Name* `SAP-oprettelse`, *Limit Entries to Folder*
`/SAP-oprettelse/Kvitteringer`, *Include Nested Items* `No`.

*Filter array* **Receipt files**: *From*
`body('Get_files_(properties_only)')?['value']`. Betingelsen er udtrykket i
`kvittering-0-filter.txt` *is equal to* `true`. Det sorterer mapperne
*Behandlet* og *Afvist* fra og alt andet end `*.kvittering.json`.

### 2. Én kvittering ad gangen

*Apply to each* **Each receipt** over `body('Receipt_files')`. Lad
*Concurrency control* være slået fra.

Inde i løkken: *Scope* **Handle receipt** med

1. *SharePoint — Get file content* **Get receipt content**, *File Identifier*
   `items('Each_receipt')?['{Identifier}']`.
2. *Compose* **Receipt** med udtrykket i `kvittering-1-compose.txt`. Det giver
   kvitteringen som et objekt, uanset om SharePoint leverer filen som tekst
   eller base64.
3. *SharePoint — Get item* **Get plan**, *List Name*
   `BioSap-List-MaintenancePlans`, *Id* `outputs('Receipt')?['planSpId']`.
4. *Condition* **Valid receipt**: udtrykket i `kvittering-2-betingelse.txt`
   *is equal to* `true`.

Betingelsen tjekker:

| Tjek | Fanger |
|---|---|
| `kind` er `vhplan-sap-receipt`, og `state` er `Created` | En fremmed fil |
| `sapPlanNo` er udfyldt | En kvittering uden plannummer |
| `orderGuid` er planens `SapOrderGuid` | En kvittering for en gammel ordre, fx fra før planen blev trukket tilbage |
| Planen er *Ready for creation in SAP* | En plan, der allerede er *Published* eller trukket tilbage |
| `sapSystem` er `BioSap-SapSystem` | En kvittering fra GQ1 på PROD-sitet |

### 3. Ja: skriv numrene — planen til sidst

1. *Apply to each* **Each item** over `outputs('Receipt')?['items']` med
   *Send an HTTP request to SharePoint* **Set item numbers**:
   - *Uri* `_api/web/lists(guid'@{parameters('BioSap-List-MaintenanceItems (orsted_BioSapListMaintenanceItems)')}')/items(@{items('Each_item')?['spId']})`
   - *Method*, *Headers* som i flow A, 7. *Body* `kvittering-3-merge-item.json`.
2. **Set plan published**: som flow A, 7, men med
   `items(@{outputs('Receipt')?['planSpId']})` i *Uri* og
   `kvittering-4-merge-plan.json` som *Body*.
3. *SharePoint — Move file*: *File to Move*
   `items('Each_receipt')?['{Identifier}']`, *Destination Folder*
   `/SAP-oprettelse/Kvitteringer/Behandlet`, *If another file is already
   there*: flyt med et nyt navn.

Planen sættes til *Published* til sidst. Fejler et item, er planen stadig
*Ready*, og kvitteringen kan køres igen. Når planen er *Published* med et
`SAPNum`, sender `BioSap-EmailNotification-PlanPublished` mailen til
rekvirenten. Har det flow ikke fået spærren fra docs/32 (afsnit 7.5), sender
det mailen igen ved hver senere ændring af planen.

### 4. Nej og fejl: Afvist og en mail

**Nej-grenen:** *Move file* til `/SAP-oprettelse/Kvitteringer/Afvist` og
*Send an email (V2)* til `BioSap-ErrorNotifiers`:

- *Subject*: `VH-plan Opretter: kvittering afvist - @{items('Each_receipt')?['{FilenameWithExtension}']}`
- *Body*: kvitteringens `planId`, `state`, `sapSystem` og `orderGuid`, planens
  `SapOrderGuid` og `Status`, og `FlowRunHistoryLink`. Så kan modtageren se,
  hvilket tjek der fejlede.

**Efter scopet**, stadig i løkken: samme *Move file* til *Afvist* og en mail
med filnavnet og `FlowRunHistoryLink`. Begge med *Configure run after*:
*Handle receipt has failed* og *has timed out*. Det fanger en fil, der ikke
kan læses, eller hvis plan ikke findes. Uden dem ville flowet fejle på den
samme fil hvert 10. minut.

**Kør en kvittering igen:** ret årsagen og flyt filen fra *Kvitteringer/Afvist*
tilbage til *Kvitteringer*. Alt, flowet skriver, kan skrives igen uden skade.

## Rettigheder

Biblioteket `SAP-oprettelse` får sine egne rettigheder (stop nedarvningen):

| Hvem | Rettighed |
|---|---|
| Master Data, der opretter i SAP | Bidrag (Contribute) |
| Flowenes servicekonto | Bidrag |
| Sitets ejere | Fuld kontrol, som i dag |
| Alle andre | Ingen adgang |

En fil i *Kvitteringer* kan sætte en plan til *Published* med et SAP-nummer.
Flowet tjekker `SapOrderGuid`, status og SAP-system, så en tilfældig fil
kommer ikke igennem. Men den, der kan læse ordrefilen, kan også se dens
`orderGuid`. Derfor er biblioteket forbeholdt dem, der alligevel opretter
planerne.

## Afprøvning

Med en DEV-plan, før opretteren bruges mod SAP:

1. Sæt planen til *Ready for creation in SAP*. Inden for et par minutter
   ligger `MP…_….json` i *Til oprettelse*, og planen har `SapOrderGuid` og
   `SapOrderFile`. Flowet har kørt én gang.
2. I opretteren: *Opdater liste* og *Vis plan*. Antallet af items, operationer
   og materialer er det samme som i appen, og æ, ø og å ser rigtige ud.
3. Sæt planen til *Draft*. `SapOrderGuid` bliver tom. Sæt den til *Ready*
   igen. Der kommer en ny fil, og opretteren viser den gamle som *Erstattet*.
4. Opret planen i GQ1 (docs/34, afsnit 9). Inden for 10 minutter er planen
   *Published* med `SAPNum`. Hvert item har `SapItemNo`, `TaskListGroup` og
   `TaskListGroupCounter`, kvitteringen ligger i *Behandlet*, og rekvirenten
   har fået mailen.
5. Kopiér kvitteringen fra *Behandlet* tilbage til *Kvitteringer*. Den havner
   i *Afvist*, fordi planen ikke længere er *Ready*, og der kommer en mail.

## Når et felt ændres

Et nyt felt i ordren skal tre steder hen: skemaet
(`schema/vhplan-sap-order.schema.json`), den rigtige fil i `flow/sap-ordre/`
og opretteren (`excel/opretter`). `tests/test_sap_contract.py` fejler, hvis
de ikke er enige. Ret flowet til sidst, med kopier/indsæt fra filen.

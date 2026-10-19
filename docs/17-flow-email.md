# VH-planens mails

**Kilden er flowet.** Mailens HTML står inline i
`BioSap-EmailNotification-NewPlanCreated`, handlingen
`Compose-EmailContent` (`solution/BIOSAP/src/Workflows/`). Den separate
skabelon `flow/email-plan-submitted.html` er slettet (R2-053, beslutning
(b)): den var allerede en anden end flowets, og en rettelse i den nåede
aldrig ud i en mail. `PlanPublished` og `ToMasterData` har deres egen kopi
af samme opbygning; de tre VH-godkendelsesflows sender korte
`<p>`-mails. Hvilke mails der findes, og hvordan de ser ud i dag, står i
[Mailene i forløbet](#mailene-i-forløbet).

Det fælles child flow til alle mailene, som denne side tidligere beskrev,
er **ikke bygget og bygges ikke nu**. Genopbygges VH-flowene en dag, er det
stedet at samle mailene (beslutning (a)) – se
[Hvis mailene skal samles](#hvis-mailene-skal-samles).

## Hvad der er anderledes

Den nuværende mail er en lodret nøgle/værdi-tabel med seks felter: Plan ID,
Title, Sort Field, Cycle, Unit, First Planned Date. Den fortæller hvad
planen *hedder*, ikke hvad den *indeholder* — modtageren kan ikke se hvor
mange items der kommer, hvilke funktionspladser de rammer, eller hvem der
har meldt den ind.

Den nye har fire dele:

1. **Nøgletal** — værk, antal items, cyklus. Tre tal man aflæser uden at læse.
2. **Planens stamdata** — som før, plus status, strategi, scheduling period
   og indmelder.
3. **Items-tabellen** — én række pr. item med funktionsplads, aktivitetstype
   og arbejdscenter. Det er den, der gør mailen brugbar uden at åbne appen.
4. **Operationer** — én række pr. operation, med timer i alt.

Plus en knap tilbage til appen og en skjult preheader, så indbakken viser
`AVV · 3 item(s) · Eftersyn af …` i stedet for den samme overskrift hver
gang.

## Felterne

Felterne er herunder skrevet `{{Navn}}` – i flowet står det tilsvarende
udtryk (`triggerBody()?['…']`, `outputs('…')`) direkte i HTML'en.

### Fra `MaintenancePlans`

I `NewPlanCreated` kommer planen fra triggeren (`triggerBody()`).

| Token | Kolonne | Bemærkning |
|---|---|---|
| `{{PlanID}}` | `PlanID` | fx `MP-0039` |
| `{{PlanText}}` | `Title` | |
| `{{Status}}` | udtryk | I ord, ud fra `Status` og `ApprovalStage` – se [Statusordet](#statusordet) |
| `{{Plant}}` | `PlantsInitial Value` | |
| `{{Cycle}}` | `Cycle` | |
| `{{Unit}}` | `Unit Value` | |
| `{{StrategyKey}}` | `StrategyKey` | tom ved ikke-strategiplaner |
| `{{SchedulingPeriod}}` | `SchedulingPeriod` | tal, i år |
| `{{SortField}}` | `SortField Value` | |
| `{{PlannedDate}}` | udtryk, se nedenfor | |

`{{PlannedDate}}` skal formateres — rå ISO-dato ser forkert ud i en mail:

```
formatDateTime(triggerOutputs()?['body/PlannedDate'], 'dd-MM-yyyy')
```

### Fra `MD_RequestIndex`

Slå rækken op med `RequestGuid` eller `RequestNo` = planens `PlanID`.

| Token | Kolonne |
|---|---|
| `{{RequestNo}}` | `RequestNo` |
| `{{RequesterName}}` | `RequesterName` |
| `{{RequesterEmail}}` | `RequesterEmail` |
| `{{ItemCount}}` | `ItemCount` |
| `{{AppUrl}}` | `AppUrl` |
| `{{SubmittedOn}}` | `convertFromUtc(…['LastActionOn'], 'Romance Standard Time', 'dd-MM-yyyy HH:mm')` – dansk tid; tilføj `Z`, hvis værdien mangler det (R2-085) |

`{{MasterDataEmail}}` i fodnoten er miljøvariablen `BioSap-MasterDataEmail`
(R2-052) – ikke en fast adresse, så DEV kan pege på en testpostkasse.

`{{ItemCount}}` kan også tages som `length(body('Get_items_MaintenanceItems')?['value'])`
— så er den garanteret i takt med tabellen lige nedenunder.

## Item- og operationsrækkerne

Det er den eneste del, der ikke bare er at trække et felt ind. Brug **ikke**
en `Apply to each` med en variabel, der får HTML lagt til — den er langsom og
rækkefølgen er ikke garanteret. Brug en **Select**, der laver hver række om
til en streng, og saml dem med `join`.

### 1. Hent items

`Get items` på `MaintenanceItems` med filter:

```
MaintenancePlanNo/Id eq <planens ID>
```

Sortér på `ItemID` stigende, så rækkefølgen i mailen er den samme som i appen.

### 2. Select → række-HTML

Skift Select-handlingen til **tekst-tilstand** (ikonet til højre for
`Map`) og indsæt:

```
<tr><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['ItemID']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;">@{item()?['Title']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;font-family:Consolas,monospace;font-size:12px;white-space:nowrap;">@{item()?['FunctionalLocation']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['MaintenanceActivityType']?['Value']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['MainWorkCenter']?['Value']}</td></tr>
```

### 3. Sæt den ind i mailen

`{{ItemRows}}` erstattes med:

```
join(body('Select_item_rows'), '')
```

Uden `join` sætter Power Automate et JSON-array ind, og mailen viser
firkantede parenteser og anførselstegn.

FL-cellen har `white-space:nowrap`. En FL som `ASV06 AEA10CE000 -T01` har
mellemrum inde i koden, og uden den brydes den efter `-`, så `T01` står på
næste linje og ligner en anden FL.

### 4. Det samme for operationer

`Get items` på `TaskListMain` med `MaintenancePlanID/Id eq <planens ID>`,
sorteret på `OperationNo`. Select-skabelon:

```
<tr><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['OperationNo']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;">@{item()?['OperationShortText']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['WorkCtr']}</td><td align="right" style="padding:7px 8px;border-bottom:1px solid #eef2f6;">@{item()?['Work']}</td><td align="right" style="padding:7px 8px;border-bottom:1px solid #eef2f6;">@{item()?['Duration']}</td></tr>
```

| Token | Udtryk |
|---|---|
| `{{OpRows}}` | `join(body('Select_op_rows'), '')` |
| `{{OpCount}}` | `length(body('Get_items_TaskListMain')?['value'])` |
| `{{TotalWork}}` | `sum(body('Select_work_values'))` — en Select mere, der kun mapper `@{item()?['Work']}` |

Har du ikke lyst til den tredje Select, så skriv `{{TotalWork}}` ud af
overskriften — resten virker uden.

## Emnelinjen

Én pr. mail – se tabellen i næste afsnit. Plannummeret står først, så
mailen kan søges frem.

## Mailene i forløbet

Teksterne er kopieret fra flowene (`solution/BIOSAP/src/Workflows/`); alle
er engelske (issue #162, `tools/check_language.py`).

| Mail | Sendes af (handling) | Til | Emne | Overskrift | Udseende i dag |
|---|---|---|---|---|---|
| **Submitted for approval** | `BioSap-EmailNotification-NewPlanCreated` (`Send_an_email_(V2)-EmailRequestor`) | Ejeren (indeksets RequesterEmail), cc indsenderen (R2-049) | `Maintenance plan MP0068 submitted for approval - SSV` | *Submitted for approval* – "The plan has been submitted for approval. You will be notified when the plan is approved or returned." | Fuld skabelon: header, nøgletal, items, operationer, knap og fodnote |
| **Returned** | F1, F2, F3 (`Send_returned_mail`), når mindst ét svar er *Send retur* | Rekvirenten | `Maintenance plan MP0068 returned - correct it and submit again` | "Maintenance plan MP0068 (…) was returned by the system approval:" + kommentarerne + "Correct the plan in the app and submit it again." | Kort `<p>`-mail: ingen header, knap eller fodnote |
| **Reminder** | F1, F2, F3 (`Send_reminder`) ved timeout (`P14D`) | Den godkender, der ikke har svaret | `Approval request for maintenance plan MP0068 expired without a response` | Godkendelsen er udløbet efter 14 dage og kan ikke længere besvares; en ny anmodning kommer (medmindre planen er returneret) og besvares i Teams under *Approvals* (R2-087) | Kort `<p>`-mail |
| **Ready for creation in SAP** | F4 `BioSap-VhPlan-ToMasterData` (`Send_to_master_data`) | `BioSap-MasterDataEmail` | `Maintenance plan MP0068 ready for creation in SAP - SSV` | *Ready for creation in SAP* | Skabelonens header, stamdata og items; knap, ingen fodnote |
| **Created in SAP** | `BioSap-EmailNotification-PlanPublished` (`Send_an_email_(V2)-EmailRequestor`) | Ejeren (indeksets RequesterEmail), cc indsenderen og Master Data ved SAP-advarsler (R2-048, R2-049) | `Maintenance plan MP0068 created in SAP (12345678) - SSV` | *Created in SAP* – SAP-plannummeret | Fuld skabelon med knap og fodnote |

Retur-mailene siger "returned by the system approval" (F1), "… cost
approval" (F2) og "… quality review" (F3).

**Tilbage i flowene** (Power Automate, ikke denne side): knappen "Open … in
the app" og fodnoten "This email was sent automatically …" mangler i
*Returned*, *Reminder* og (fodnoten) *Ready for creation in SAP*.

*Created in SAP* er bygget (R2-019): flowet henter `MD_RequestIndex`-rækken
**før** mailen (`Get_request_index`), så knappen kan pege på `AppUrl` – uden
række peger den på `BioSap-SiteUrl`. Datoen vises som `dd-MM-yyyy` i dansk tid
(`-`, hvis den mangler), og al fritekst escapes som i *Submitted for approval*.
Spærren `RequesterNotified`, loggen (`Stage = SapCreated`) og indeksopdateringen
kører bagefter som før. Testen er `tests/test_vh_plan_published_mail.py`.

**"Rekvirenten" er ejeren (R2-049).** Alle VH-mails til rekvirenten går til
indeksrækkens `RequesterEmail` (falder tilbage på planens `SubmittedBy` og
til sidst `Author`), og indsenderen (`SubmittedBy`) får Cc, når han ikke er
ejeren. Godkendelseskortene viser `RequesterName`. *Oprettet i SAP* har ikke
længere `Editor` på Cc (R2-048) – efter kvitteringsflowet er det
servicekontoen. Testen er `tests/test_vh_mail_owner.py`.

**Selve godkendelsesanmodningen bruger ikke skabelonen.** Den sendes af
Approvals-connectoren, hvis *Details* kun forstår Markdown – ikke HTML.
Godkenderen får den i Teams og som Power Automate-mail. *Reminder* er den
eneste anden mail, godkenderen får fra flowene.

### Hvis mailene skal samles

Skabelonen er 250 linjer HTML, og den står i dag i tre flows. Genopbygges
VH-flowene, kan de samles i **ét child flow** i solution BIO SAP (forslag,
ikke bygget), med trigger *Manually trigger a flow* og tre input:

| Input | Eksempel |
|---|---|
| `PlanId` | `68` – ID i `MaintenancePlans` |
| `MailType` | `Submitted`, `Returned`, `Reminder`, `ToMasterData`, `Published` |
| `To` | Modtagerens adresse. Tom = rekvirenten |

Child flowet henter planen, items, operationer, indeksrækken og (for
`Returned` og `ToMasterData`) `MD_ApprovalLog`, vælger emne, `{{Headline}}`,
`{{Banner}}` og `{{ButtonText}}` med en `Switch` på `MailType`, og sender.
De andre flows kalder det med **Run a Child Flow**. Child flows kræver, at
begge flows ligger i en solution – det gør de i BIO SAP.

### Statusordet

Viser forløbet i ord, ikke den rå kolonneværdi. Udtrykket i
`NewPlanCreated`:

```
if(equals(triggerBody()?['Status/Value'], 'Returned'), 'Returned',
if(equals(triggerBody()?['Status/Value'], 'Published'), 'Created in SAP',
if(equals(triggerBody()?['Status/Value'], 'Ready for creation in SAP'), 'Ready for creation in SAP',
if(equals(triggerBody()?['Status/Value'], 'In Progress'),
   concat('In approval - ',
     if(equals(triggerBody()?['ApprovalStage/Value'], 'System'), 'system',
     if(equals(triggerBody()?['ApprovalStage/Value'], 'Cost'), 'cost', 'quality'))),
'Draft'))))
```

### Statusord i mail og i appen

Mailen og hubben bruger ikke de samme ord. Hubben viser
`MD_RequestIndex.Status` med etiketten fra `tools/request_index.py`
(`STATUS`); trinnene står i [`32-godkendelsesflow.md`](32-godkendelsesflow.md) §4.

| `MaintenancePlans.Status` (+ `ApprovalStage`) | Statusord i mailen | `MD_RequestIndex.Status` | Etiket i hubben (`request_index.STATUS`) |
|---|---|---|---|
| `Draft` | Draft | `Kladde` | Draft |
| `In Progress` (`System`) | In approval - system | `Indsendt` → `UnderBehandling` | Submitted → In progress |
| `In Progress` (`Cost`) | In approval - cost | `UnderBehandling` | In progress |
| `In Progress` (`Quality`) | In approval - quality | `UnderBehandling` | In progress |
| `Returned` | Returned | `AfventerInfo` | Awaiting info |
| `Ready for creation in SAP` | Ready for creation in SAP | `KlarTilSAP` | Ready for SAP |
| `Published` | Created in SAP | `OprettetISAP` | Created in SAP |

### Bannerne

Tre farver. Hvert banner er en hel `<tr>`, som sættes ind i stedet for
`{{Banner}}`. Titel og tekst er `TITEL` og `TEKST` nedenfor.

**Info** (blå) – *Submitted for approval*, *Reminder*:

```html
<tr><td style="padding:18px 24px 18px 24px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr><td style="background-color:#e8f1f8;border-left:4px solid #1a6ea8;padding:12px 16px;
                   font-size:14px;color:#24313f;line-height:1.5;">
      <div style="font-weight:600;color:#12405f;padding-bottom:4px;">TITEL</div>
      TEKST
    </td></tr>
  </table>
</td></tr>
```

**Advarsel** (rav) – *Returned*: samme opbygning med
`background-color:#fdf4e3;border-left:4px solid #b7791f` og titelfarven
`#7a4f0e`.

**Succes** (grøn) – *Ready for creation in SAP*, *Created in SAP*: samme
opbygning med `background-color:#e7f5ec;border-left:4px solid #2f855a` og
titelfarven `#1f5e3d`.

### Kommentarerne i *Returned*

`TEKST` bygges af de `Return`-rækker i `MD_ApprovalLog`, der hører til
planen og er nyere end `SubmittedOn`. Samme mønster som item-rækkerne: en
**Select** i tekst-tilstand og `join`:

```
<div style="padding-top:8px;"><strong>@{item()?['ItemText']}</strong>
<span style="color:#6b7b8c;"> &middot; @{item()?['Stage']} &middot; @{item()?['DecidedByEmail']}</span><br>
@{replace(replace(replace(coalesce(item()?['Comment'],'(ingen kommentar)'),'&','&amp;'),'<','&lt;'),'>','&gt;')}</div>
```

Kommentaren er fri tekst fra godkenderen. Den **escapes**, før den sættes
ind i HTML'en – ellers kan et `<` i en kommentar ødelægge resten af mailen.
Det samme gælder `ItemText`, hvis korttekster kan indeholde `<` eller `&`.

### Godkenderne i *Ready for creation in SAP*

`TEKST` er én linje pr. trin fra `MD_ApprovalLog`, fx
"System 8 – ABCDE · Omkostning – ikke nødvendig · Kvalitet (ASV) – ABCDE".
Master Data kan så se, at planen har været hele vejen igennem, uden at åbne
appen.

## Felter jeg med vilje IKKE har taget med

Fire kolonner på `MaintenancePlans` ser relevante ud og er tomme i praksis.
Sætter du dem i mailen, står der en tom linje i hver eneste udsendelse:

| Kolonne | Hvorfor tom |
|---|---|
| `PlanType` | Eneste valgværdi er `PM`. Siger intet om IP41/IP42 — `StrategyKey` bærer det i stedet |
| `CallHorizon` | Appen skriver den ikke. Tom i alle 34 eksisterende planer, og listen har tre CallHorizon-kolonner efter oprydningen — hvilken der er den levende er ikke afklaret |
| `Package` | Én pakke pr. plan. Appens matrix er pr. operation og ligger i `PackagesKey` på operationslinjen |
| `MultiCounterStrategy` | Bruges ikke af appen |

Se `Maintenance Plan App/build/build_save.py`, afsnittet **DET DER IKKE
SKRIVES**, for den fulde begrundelse. Bliver de udfyldt senere, er det bare
at tilføje en række i stamdata-tabellen.

## Outlook

Skabelonen er skrevet til at overleve Outlook på Windows, som tegner HTML
med Words motor:

- kun tabeller til layout, ingen flexbox og ingen grid
- alle styles inline — `<style>` i `<head>` bliver delvist strippet
- ingen `border-radius`, den ignoreres alligevel og ser så skæv ud
- fast bredde `640` på den ydre tabel, fordi Outlook ikke regner procenter
  pålideligt på `td` i en tabel uden fast bredde
- knappen er en tabelcelle med baggrundsfarve, ikke et stylet `<a>` — et
  `<a>` med `padding` bliver ikke klikbart i hele fladen

Test den på en rigtig mail, før den sættes i drift. Gennemsyn i
flow-designeren viser ikke det samme som Outlook.

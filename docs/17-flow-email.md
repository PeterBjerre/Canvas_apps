# VH-planens mails

Skabelonen ligger i
[`../flow/email-plan-submitted.html`](../flow/email-plan-submitted.html).

Den startede som mailen, når en plan sendes til oprettelse. Nu er den
**fælles for alle VH-planens mails** i godkendelsesflowet
([`32-godkendelsesflow.md`](32-godkendelsesflow.md)). Mailene adskiller sig
kun ved tre tokens – se [Samme skabelon i alle mails](#samme-skabelon-i-alle-mails).

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

Tokens i skabelonen er skrevet `{{Navn}}`. Erstat hvert af dem med dynamisk
indhold. `{{Headline}}`, `{{Banner}}` og `{{ButtonText}}` afhænger af,
hvilken mail der sendes – se [Samme skabelon i alle mails](#samme-skabelon-i-alle-mails).

### Fra `MaintenancePlans`

I child flowet `BioSap-VhPlan-SendMail` kommer planen fra et *Get item* på
`PlanId`, ikke fra en trigger. Udtrykkene nedenfor skrevet med
`triggerOutputs()` bliver dermed til `body('Get_plan')`.

| Token | Kolonne | Bemærkning |
|---|---|---|
| `{{PlanID}}` | `PlanID` | fx `MP-0039` |
| `{{PlanText}}` | `Title` | |
| `{{Status}}` | udtryk | I ord, ud fra `Status` og `ApprovalStage` – se [`{{Status}}`](#status) |
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
| `{{SubmittedOn}}` | `formatDateTime(…['LastActionOn'], 'dd-MM-yyyy HH:mm')` |

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

## Samme skabelon i alle mails

### Hvilke mails

| Mail | Sendes af | Til | Emne | `{{Headline}}` | `{{Banner}}` | `{{ButtonText}}` |
|---|---|---|---|---|---|---|
| **Sendt til godkendelse** | `BioSap-EmailNotification-NewPlanCreated` (findes – ny brødtekst) | Rekvirenten | `VH-plan MP0068 sendt til godkendelse - SSV` | Sendt til godkendelse | Info: "Du får besked, når planen er godkendt eller sendt retur." | Åbn planen i appen |
| **Sendt retur** | F1, F2 eller F3, når mindst ét svar er *Send retur* | Rekvirenten | `VH-plan MP0068 sendt retur - ret og indsend igen` | Sendt retur | Advarsel med kommentarerne pr. item | Ret planen i appen |
| **Påmindelse** | F1, F2 eller F3 ved timeout (`P14D`) | Den godkender, der ikke har svaret | `Påmindelse: VH-plan MP0068 venter på din godkendelse` | Venter på din godkendelse | Info: sendt dato, og at der svares i Teams → *Approvals* eller i mailen fra Power Automate | Åbn planen i appen |
| **Klar til oprettelse i SAP** | F4 `BioSap-VhPlan-ToMasterData` (ny) | `sapvedligehold@orsted.com` | `VH-plan MP0068 klar til oprettelse i SAP - SSV` | Klar til oprettelse i SAP | Succes: hvem der godkendte system, omkostning og kvalitet | Åbn planen i appen |
| **Oprettet i SAP** | `BioSap-EmailNotification-PlanPublished` (findes – ny brødtekst) | Rekvirenten, cc sidste redaktør | `VH-plan MP0068 oprettet i SAP (12345678)` | Oprettet i SAP | Succes: SAP-plannummeret | Åbn planen i appen |

**Selve godkendelsesanmodningen bruger ikke skabelonen.** Den sendes af
Approvals-connectoren, hvis *Details* kun forstår Markdown – ikke HTML.
Godkenderen får den i Teams og som Power Automate-mail. Påmindelsen er den
eneste mail, godkenderen får fra skabelonen.

### Ét child flow i stedet for fem kopier

Skabelonen er 250 linjer HTML. Kopieres den ind i fem flows, glider de fra
hinanden ved første rettelse. Byg i stedet **ét child flow** i solution
BIO SAP, `BioSap-VhPlan-SendMail`, med trigger *Manually trigger a flow* og
tre input:

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

### `{{Status}}`

Viser forløbet i ord, ikke den rå kolonneværdi:

```
if(equals(body('Get_plan')?['Status']?['Value'], 'Returned'), 'Sendt retur',
if(equals(body('Get_plan')?['Status']?['Value'], 'Published'), 'Oprettet i SAP',
if(equals(body('Get_plan')?['Status']?['Value'], 'Ready for creation in SAP'), 'Klar til oprettelse i SAP',
if(equals(body('Get_plan')?['Status']?['Value'], 'In Progress'),
   concat('Til godkendelse - ',
     if(equals(body('Get_plan')?['ApprovalStage']?['Value'], 'System'), 'system',
     if(equals(body('Get_plan')?['ApprovalStage']?['Value'], 'Cost'), 'omkostning', 'kvalitet'))),
'Kladde'))))
```

### Bannerne

Tre farver. Hvert banner er en hel `<tr>`, som sættes ind i stedet for
`{{Banner}}`. Titel og tekst er `TITEL` og `TEKST` nedenfor.

**Info** (blå) – *Sendt til godkendelse*, *Påmindelse*:

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

**Advarsel** (rav) – *Sendt retur*: samme opbygning med
`background-color:#fdf4e3;border-left:4px solid #b7791f` og titelfarven
`#7a4f0e`.

**Succes** (grøn) – *Klar til oprettelse i SAP*, *Oprettet i SAP*: samme
opbygning med `background-color:#e7f5ec;border-left:4px solid #2f855a` og
titelfarven `#1f5e3d`.

### Kommentarerne i *Sendt retur*

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

### Godkenderne i *Klar til oprettelse i SAP*

`TEKST` er én linje pr. trin fra `MD_ApprovalLog`, fx
"System 8 – PKBJE · Omkostning – ikke nødvendig · Kvalitet (ASV) – PKBJE".
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

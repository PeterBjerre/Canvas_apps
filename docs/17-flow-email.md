# Mailen når en plan sendes til oprettelse

Skabelonen ligger i
[`../flow/email-plan-submitted.html`](../flow/email-plan-submitted.html).

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
indhold.

### Fra `MaintenancePlans` (trigger-elementet)

| Token | Kolonne | Bemærkning |
|---|---|---|
| `{{PlanID}}` | `PlanID` | fx `MP-0039` |
| `{{PlanText}}` | `Title` | |
| `{{Status}}` | `Status Value` | |
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
<tr><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['ItemID']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;">@{item()?['Title']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;font-family:Consolas,monospace;font-size:12px;">@{item()?['FunctionalLocation']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['MaintenanceActivityType']?['Value']}</td><td style="padding:7px 8px;border-bottom:1px solid #eef2f6;white-space:nowrap;">@{item()?['MainWorkCenter']?['Value']}</td></tr>
```

### 3. Sæt den ind i mailen

`{{ItemRows}}` erstattes med:

```
join(body('Select_item_rows'), '')
```

Uden `join` sætter Power Automate et JSON-array ind, og mailen viser
firkantede parenteser og anførselstegn.

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

```
VH-plan @{triggerOutputs()?['body/PlanID']} sendt til oprettelse - @{triggerOutputs()?['body/PlantsInitial/Value']}
```

Plannummeret først, så den kan søges frem.

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

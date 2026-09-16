# Materialer og dokumenter på arbejdsplanen

Tasklist-sektionen har fået faner. Pakkematricen, som lå som et kort for sig
(Step 4), er flyttet ind som en af dem.

## Fanerne

| Fane | Synlig |
|---|---|
| **Operations** | altid |
| **Maintenance packages** | kun når Plan Type = `Strategy` |
| **Materials** | altid |
| **Attachments** | altid |

De fire ting hører alle til arbejdsplanen — operationerne, pakkerne der
allokeres pr. operation, materialerne der bruges, og dokumenterne der skal
med. De lå før som to kort med hver sit trin, og der var ikke plads til to
mere.

**Én detalje der er lettere at overse end at opdage:** ændrer man planen fra
strategi- til tidsplan, mens man står på pakkefanen, forsvinder både knappen
og ruden — og kortet ville stå tomt. Operationsruden overtager derfor den
tilstand (`OPS_PANE_ON` i `build_tasklist.py`).

## Materialer

`colVhpMaterials` — én række pr. materialelinje.

| Felt | Kommer fra |
|---|---|
| `MaterialNo` | brugeren |
| `Quantity` | brugeren, 1 som standard |
| `OperationNo` | brugeren, valgt blandt itemets egne operationer. En ny linje arver den **første** operation — et materiale uden operation har ingen plads i SAP |
| `Description` | **materialeopslaget, senere** |
| `Unit` | **materialeopslaget, senere** |

Description og Unit står tomme og vises som `-`. Kolonnerne findes allerede,
så OData-opslaget kun skal fylde dem ud — ikke flytte rundt på tabellen
bagefter. Når opslaget kommer, er det ét kald pr. materialenummer og en
`Patch` på de to felter.

## Dokumenter

`colVhpAttachments` — én række pr. dokument.

Koblingen til operationer ligger i `OperationsKey`, `";0010;0020;"`, præcis
som `PackagesKey` på operationslinjen. Samme mønster, så der ikke er to
måder at gemme et mængdevalg på i den samme app. **Er ingen operation
markeret, hører dokumentet til hele itemet** — det er tilstanden `";"`, og
den er default.

Samlingen filtreres på `ItemId`, så omfanget er itemet, ikke planen. Teksten
sagde først "whole plan"; det var forkert, og det blev fanget af spørgsmålet
om hvor tingene egentlig hænger.

Afkrydsningerne ligger i et galleri inde i dokumentets række. Den indre
gallery kan ikke læse den ydre rækkes data (`ThisItem` er skygget), så den
ydre rækkes `LineId` bæres **med ind** i hver indre record:

```
With({ lid: ThisItem.LineId },
     ForAll(ops As O, { OperationNo: O.OperationNo, LineId: lid }))
```

Det er samme løsning som pakkematricen bruger. Ingen krydsreference mellem
to gallerier.

---

## Det der mangler: selve filvalget

Alt ovenfor virker. **Der er ingen filvælger endnu**, og det er med vilje —
valget afhænger af noget, der ikke er afklaret.

### Hvorfor det ikke bare er en knap

Power Apps kan ikke læse en vilkårlig fil fra stifinderen med en almindelig
kontrol. `AddMediaButton` tager billeder og video, ikke dokumenter. Den
eneste kontrol, der understøtter træk-og-slip af vilkårlige filer, er
**Attachment-kontrollen** — og den lever kun inde i en formular bundet til
en datakilde, der har vedhæftninger. I praksis en SharePoint-liste.

Det betyder, at filen skal **landes et sted i SharePoint først**, og derefter
kan flowet flytte den til dokumentbiblioteket.

### Spørgsmålet der skal afklares

Hvad vil jeres attachments-flow have ind? Det afgør designet:

| Hvis flowet vil have… | …så skal appen |
|---|---|
| **En SharePoint-vedhæftning** (listenavn + item-ID) | Landes på en listerække. Enklest: slå vedhæftninger til på `MaintenancePlans` og sæt en formular med Attachment-kontrollen på planens række |
| **Filindhold som base64 + filnavn** | Stadig hente filen gennem Attachment-kontrollen først — appen kan ikke få fat i bytes på anden vis. Derefter sendes de videre |
| **En URL til en fil der allerede ligger et sted** | Så er der ingen upload i appen. Brugeren lægger filen i biblioteket selv, og appen registrerer kun navn og operationskobling |

Den tredje mulighed er markant billigere end de to første. Er den brugbar i
praksis, er der ingen grund til at bygge upload ind i appen.

Uanset hvilken vej: **operationskoblingen hører hjemme i appen**, ikke i
flowet. Den del ligger klar.

---

## Én ubevist egenskab i denne ændring

`ModernDropdown.OnChange` bruges på operationsvalget i materialerækken.
Ingen anden dropdown i appen bruger den — de øvrige læses med `.Selected`,
når en knap kører. Fejler compile, er det den ene linje
(`drpVhpMatOp.OnChange` i `build_tasklist.py`), og alternativet er et
tekstfelt med `onchange`, som er bevist.

Alt andet i ændringen bruger egenskaber, appen allerede beviser virker —
efterprøvet ved at sammenligne hver ny kontrols egenskaber mod den forrige
version af skærmen.

## Datamodellen

Materialer og dokumenter hænger på **arbejdsplanen**, ikke på planen — derfor
`Tasklist` i navnet. `sharepoint/provision/Provision-TasklistLists.ps1`
opretter begge.

### `MD_TasklistMaterial` — én række pr. materialelinje

| Kolonne | Type | |
|---|---|---|
| `Title` → `MaterialNo` | Tekst, påkrævet | Materialenummeret. Title genbrugt, så standardvisningen viser noget brugbart |
| `PlanKey`, `ItemKey`, `TaskItemID` | Tekst, **indekseret** | Nøglerne. Indekseret, fordi appen filtrerer på dem, hver gang en plan åbnes |
| `OperationNo` | Tekst | |
| `Quantity` | Tal, påkrævet | |
| `MaterialText`, `Unit` | Tekst | Udfyldes af materialeopslaget, ikke af brugeren |
| `LineId` | Tal | Appens egen linjenummerering |

### `MD_TasklistAttachment` — én række pr. dokument

| Kolonne | Type | |
|---|---|---|
| `Title` → `FileName` | Tekst, påkrævet | |
| `PlanKey`, `ItemKey` | Tekst, **indekseret** | |
| `OperationsKey` | Tekst | `";0010;0020;"`. Tom (`";"`) = hele itemet |
| `FileUrl`, `FileSize` | Tekst / Tal | |
| `UploadStatus` | Valg: Pending · Uploaded · Failed | Appen skriver `Pending`; **flowet** retter den |
| `LineId` | Tal | |

### Hvorfor ikke bare kolonner på `TaskListMain`?

Det var det oplagte alternativ, og det holder ikke — men af to forskellige
grunde:

**Materialer.** Pakkekolonnen virker, fordi en pakke er en *reference* til en
række i en anden liste, og et sæt referencer fylder fint i `";1;3;"`. En
materialelinje bærer sine **egne** værdier — nummer, mængde, enhed. En mængde
pr. materiale kan ikke ligge i en semikolonstreng uden at opfinde et
miniformat, som hverken SharePoint, et flow eller en rapport kan filtrere på.

**Dokumenter.** Her er problemet et andet: et dokument kan hænge på **flere**
operationer og skal kunne hænge på **ingen**. En kolonne på `TaskListMain`
har ingen række at bo på i det tomme tilfælde, og ville duplikere dokumentet
i det fulde. Derfor egen liste — og så bliver operationskoblingen en
`OperationsKey`-kolonne dér, hvor den *er* et sæt referencer, og hvor
mønsteret passer.

Kort sagt: pakkemønsteret er rigtigt til referencer og forkert til rækker med
egne felter.

## Endnu ikke bygget

- **Gemning til SharePoint.** `colVhpMaterials` og `colVhpAttachments` bor
  stadig kun i appen. `build_save.py` skal udvides, når listerne er oprettet.
- **Materialeopslaget** mod SAP (OData).
- **Validering.** Fx materialelinje uden operation, eller mængde 0. Ingen af
  delene er meldt ud som en regel endnu.

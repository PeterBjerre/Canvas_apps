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

### Spørgsmålet er besvaret: flowene findes

Da dette blev skrevet, var det uklart, hvad flowet ville have ind. Nu ligger
solutionen i repoet, og kontrakten kan læses direkte af
`solution/BIOSAP/src/Workflows/`. Den er **målt, ikke gættet.**

Tre flows håndterer dokumenterne, og de udgør tilsammen en lille CRUD mod
biblioteket `TaskListDocuments`:

#### `BioSap-TaskListAttachment` — læg filen op

```
ind   text  = TaskListID        (bruges som mappenavn)
      file  = { name, contentBytes }
gør   SharePoint CreateFile i  /TaskListDocuments/<TaskListID>/<name>
      på sitet fra miljøvariablen BioSap-SiteUrl
ud    flowrunsuccess = "true"
```

Det afgør spørgsmålet i tabellen ovenfor: flowet vil have **filindhold som
bytes plus navn** — altså den midterste mulighed. Filen skal stadig hentes
gennem en Attachment-kontrol først, for appen kan ikke få fat i bytes på
anden vis.

#### `BioSap-GetSubmittedAttachments` — list mappen

```
ind   text  = mappesti
gør   tjekker at mappen findes med
      GetFolderByServerRelativeUrl('/teams/<BioSap-SiteName>/<text>'),
      henter så filerne med GetFileItems i biblioteket fra
      miljøvariablen BioSap-Library-TaskListDocuments
ud    files = en STRENG med et JSON-array af { Name, Link, Identifier }
```

Strengen skal parses med `ParseJSON` — samme mønster som FL-søgningen, og
dermed en konstruktion appen allerede beviser virker.

#### `BioSap-DeleteSubmittedAttachments` — slet én fil

```
ind   text  = Identifier   (feltet fra Get)
gør   SharePoint DeleteFile
```

#### `text` betyder ikke det samme i upload og get

Upload lægger selv `/TaskListDocuments/` foran værdien. Get bruger værdien,
som den er — både i mappetjekket og i `GetFileItems`. Samme app skal altså
sende **to forskellige former** af den samme oplysning. Det er ikke pænt,
men det er sådan, flowene er, og det er billigere at kende det end at rette
to flows.

### Flowet retter ikke `UploadStatus` — det troede vi ellers

`build_save.py` skriver `UploadStatus: Pending` med den begrundelse, at
*"det er FLOWET der retter den, naar filen ligger i biblioteket"*.

**Det gør flowet ikke.** Upload-flowet består af én handling — `CreateFile`
— og et svar. Det rører aldrig `MD_TasklistAttachment`. Hverken
`UploadStatus` eller `FileUrl` bliver sat af nogen i dag, så en række, der
skrives som `Pending`, bliver stående sådan for altid.

Det skal **appen** gøre. Den kender svaret: `flowrunsuccess` fortæller, om
filen kom op, og `Get`-flowets `Link` giver URL'en. Alternativet — at bygge
en `Update item` ind i flowet — ville kræve, at flowet kendte listerækkens
id, og det gør det ikke; appen opretter rækken først bagefter, ved Gem.

---

## Efterprøvet mod dokumentationen

`ModernDropdown.OnChange` stod her som den ene ubeviste egenskab. **Den er
nu bekræftet** — den er dokumenteret på den moderne Dropdown, og
dokumentationen viser endda samme mønster, jeg brugte:
`OnChange: =Set(varSelectedDept, Self.Selected)`. Ingen ændring nødvendig.

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

## VH-plan-regnearket henter dem nu

`modSharePointImport` henter begge lister ind i fanerne
`Maintenance_Materials` og `Maintenance_Attachments`. Nøglerne er dem,
`build_save.py` skriver — `PlanKey`, `ItemKey` og, kun for materialer,
`TaskItemID`. GUI-delen, der skal oprette dem i SAP, er ikke bygget endnu.

Detaljerne står i [`20-excel-vhplan-plan.md`](20-excel-vhplan-plan.md) under
*Bygget: materialer, dokumenter og de tre rettelser*.

## Endnu ikke bygget

- **Materialeopslaget** mod SAP (OData).
- **Validering.** Fx materialelinje uden operation, eller mængde 0. Ingen af
  delene er meldt ud som en regel endnu.

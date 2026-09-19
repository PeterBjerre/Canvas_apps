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

## Filvalget — bygget

Her stod, at filvælgeren manglede, og at den ventede på en afklaring.
Begge dele er overhalet.

### Antagelsen om formularen holdt ikke

Teksten sagde, at Attachment-kontrollen "kun lever inde i en formular bundet
til en datakilde, der har vedhæftninger". **Det er ikke rigtigt.** Den gamle
app `BioSap Maintenance Plans` bruger den frit på skærmen:

```yaml
- AttachmentControl:
    Control: Attachments@2.3.0
```

Ingen formular, ingen `DataField`. Og `.Attachments` giver `{ Name, Value }`,
hvor `Value` **er** filens indhold — præcis det, flowet vil have.

Det er værd at bemærke hvorfor fejlen kunne stå så længe: påstanden var
rimelig, den er udbredt, og der var ingen måde at efterprøve den på, før
solutionen lå i repoet. Nu kan konstruktioner slås op i stedet for at blive
husket.

### Sådan er det bygget

Kontrakten står ét sted: `Maintenance Plan App/build/build_attflows.py`.

| Knap | Gør |
|---|---|
| **Upload to SharePoint** | `ForAll(picker.Attachments, upload.Run(<ItemKey>, {file: {contentBytes: Value, name: Name}}))`, nulstiller vælgeren og henter listen forfra |
| **Refresh from SharePoint** | Kalder Get-flowet, `ParseJSON`, og genopbygger itemets rækker |
| **Remove document** | Kalder Delete-flowet med `Identifier` og fjerner rækken |

**Mappen er itemets nøgle** (`MI0007`). Den findes først, når planen er
gemt, så upload på en plan, der kun står i appen, ville skrive til en mappe
uden navn. Knappen siger det i stedet for at fejle.

**Filnavnet er nøglen på rækken**, ikke et løbenummer. SharePoint tillader
ikke to filer med samme navn i samme mappe, så navnet er unikt, stabilt og
kendt af begge sider. Et løbenummer skulle appen selv finde på og holde styr
på hen over en opdatering — og `ForAll` kan ikke tælle op undervejs uden at
risikere dubletter. Operationskoblingen bæres derfor også på filnavnet ind i
den indre gallery.

**Operationskoblingen overlever en opdatering.** Den findes kun i appen, ikke
i biblioteket, så den reddes over i `colVhpAttKeep`, før rækkerne skiftes ud,
og sættes tilbage på de filer, der stadig er der.

### Før det kan deployes

De tre flows skal tilføjes appen som datakilder i Studio. En formel, der
kalder et flow, fejler i compile, hvis kilden ikke er der, og det kan ikke
gøres fra YAML:

```
BioSap-TaskListAttachment
BioSap-GetSubmittedAttachments
BioSap-DeleteSubmittedAttachments
```

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

### Dokumentet lå der — galleriet kunne bare ikke sortere det

Første gang fanen blev prøvet af, kom filen op i biblioteket, og der skete
ingenting i appen. Ikke en fejl, ikke en tom besked — ingenting.

`Items` på `galVhpAttachments` stod som `Sort(..., LineId)`. **`LineId`
findes ikke på `colVhpAttachments`.** Materialerne har et løbenummer;
dokumenterne har filnavnet som nøgle, netop fordi SharePoint ikke tillader
to ens navne i samme mappe. Sorteringen pegede altså på en kolonne, der
aldrig har været der, `Items` gik i fejl, og galleriet stod tomt.

At beskeden *"No documents on this item yet."* heller ikke kom, er den
anden halvdel: den er synlig, når der er **nul** rækker, og rækkerne var der
jo. Fejlen ramte kun visningen. Sorteringen er nu `FileName`.

### To ting, der ikke kunne skelnes fra hinanden

Der var ikke nogen måde at se, hvad der var galt, og det var to steder:

**Flowet svarer det samme i to forskellige tilfælde.** `Condition_2` tjekker
`statusCode = 200` på mappeopslaget. Er mappen der ikke — eller peger
`BioSap-SiteName` et forkert sted hen — svarer `else`-grenen
`files: "[]"`. Er mappen der og tom, svarer den indre `Condition` også
`files: "[]"`. **En manglende mappe og en tom mappe ser ens ud fra appen.**
Det kan ikke rettes fra appen, så beskeden siger nu, hvilken sti der blev
spurgt om — `"No documents in TaskListDocuments/MI0007 yet."` — så den kan
holdes op mod biblioteket.

**Knappen kvitterede uden at have læst svaret.** `Notify("Document(s)
uploaded.")` lå efter `ForAll` og kørte, uanset hvad flowet sagde. Derfor
betød *"upload virker"* ikke, at noget var kommet op — kun at knappen var
trykket. Hver fil samles nu i `colVhpAttUp` med flowets eget
`flowrunsuccess`, og de filer, der ikke kom igennem, står med navn i
beskeden.


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

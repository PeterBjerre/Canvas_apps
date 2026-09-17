# VH-plan-regnearket: hvad der er galt, og hvad jeg foreslår

Gennemgang af `excel/artifact/BIO SAP VH-plan lister.xlsm` — 22.369 linjer
VBA i 31 moduler og 5 formularer.

Til gennemsyn **før** vi bygger om. Der er ikke rettet noget endnu.

---

## Kort: du har ret i begge halvdele

GUI-delen virker, og den er velbygget. SharePoint-delen virker ikke, og
grunden er ikke at koden er dårlig — **den forsøger noget, der ikke kan lade
sig gøre pålideligt.**

---

## Hvorfor SharePoint-hentningen ikke virker

### Godkendelsen kan ikke bære det

`GetSharePointAuthHeader` henter et **bearer-token** fra Windows Credential
Manager. Findes der intet token, og `CFG_SHAREPOINT_ALLOW_NO_TOKEN = True`
(det er sat), sendes kaldet **helt uden Authorization-header**.

Kommer der så 401 eller 403, gør `HttpGetText` dette:

```vb
If (http.Status = 401 Or http.Status = 403) And canDropAuthHeader Then
    currentAuthHeader = vbNullString   ' smid headeren væk og prøv igen
```

Den fjerner godkendelsen og prøver igen. Kommentaren i koden forklarer
håbet:

> `' XMLHTTP bruger WinINET-session (samme cookie-kontekst som Office/Edge)`

Det **kan** ramme rigtigt, hvis brugeren tilfældigvis har en frisk,
authentiseret SharePoint-cookie i WinINET-sessionen. Men den cookie er ikke
Excels — den hører til browseren, den udløber, og betinget adgang eller MFA
slår den fra. Derfor virker det nogle gange og ikke andre gange, uden at
noget synligt har ændret sig.

**Det er ikke en fejl man retter. Det er en mekanisme der skal skiftes.**

### Den læser fra et andet site, end appen skriver til

Otte steder i koden står der hårdkodet:

```
https://orsted.sharepoint.com/teams/BioSAP
```

VH-plan appen og alle vores lister ligger på **`/teams/BioSAPDEV`**.

Enten er `BioSAP` produktion og `BioSAPDEV` udvikling — og så skal det
afklares, hvilken vej data går — eller også har regnearket aldrig peget det
rigtige sted hen. **Det er det første spørgsmål, der skal besvares**, for
det ændrer resten af planen.

### 345 linjer gætter på tekststruktur

Modulet indeholder `IsLikelyHeadingLine`, `IsBulletLine`, `IsNumberedLine`,
`LooksLikeSentence`, `ShouldPromoteItemDescriptionTitle`,
`ApplyGenericListLayout` og et dusin til. **345 linjer, hvis eneste opgave
er at gætte, hvad en tekstlinje *var*, før formateringen gik tabt.**

Det er ikke overflødigt arbejde — det er nødvendigt, fordi teksten kommer
ind som vilkårlig HTML. Men det er også dømt til at ramme ved siden af, og
det er nøjagtig det, du beskrev som "virker ikke ret godt".

### 13 næsten ens importprocedurer

`ImportSharePointMaintenancePlans`, `…PlansAllFields`, `…Items`,
`…ItemsAllFields`, `…TLH`, `…TL`, `…TLAllFields` — samme forløb kopieret pr.
liste og pr. variant. Én rettelse skal laves syv steder.

---

## Det store fund: SAP-nøglerne findes allerede i din kode

Du skrev, at du ville finde SAP's formateringsnøgler til langteksten. **De
står i `GUI_Script.HtmlToSAPText`, i den del der virker:**

| HTML | SAP ITF |
|---|---|
| `<b>` / `<strong>` | `<H>` … `</>` |
| `<u>` | `<U>` … `</>` |
| `<br>`, `<p>` | linjeskift |
| `<span>`, `<div>`, `<ul>` | fjernes |
| `<li>` | linjeskift + `-` |

Det afgør gårsdagens spørgsmål: **fed og understreget overlever til SAP.**
Så det er hvidliste-vejen der er rigtig, ikke markør-varianten — og
hvidlisten er præcis `<b>`, `<u>`, `<br>`.

Læg mærke til linje 8: `<li>` bliver til linjeskift + bindestreg, **uden
nogen forestilling om dybde**. Det er dér underpunkter og
under-underpunkter forsvinder. Ikke en fejl i konverteringen — den kan ikke
vide bedre, når den får en flad streng.

---

## Hvad jeg foreslår

### Trin 1 — afklar de to ting, der styrer alt andet

1. **Hvilket site er det rigtige?** `BioSAP` eller `BioSAPDEV`, og skal
   regnearket læse fra samme sted som appen skriver til?
2. **Hvordan må Excel få fat i data?** Tre veje, og valget har konsekvenser
   langt ud over dette regneark. Se næste afsnit.

Jeg bygger ikke videre, før de to er på plads.

### Trin 2 — skift godkendelsen ud

| Vej | Hvordan | Hvad det koster |
|---|---|---|
| **A. Power Query** | Excels indbyggede SharePoint-konnektor henter listerne til tabeller. Brugeren logger ind én gang i Excel; Office fornyer selv | Ingen VBA til hentning overhovedet. ~1.500 linjer forsvinder. Men mindre kontrol over feltvalg |
| **B. Power Automate** | Et flow henter og lægger en fil i OneDrive/SharePoint, regnearket læser den. Der er allerede et `SendMultipleTablesToPowerAutomate` i koden | Robust godkendelse, ingen tokens i Excel. Men et ekstra led at drifte |
| **C. Rigtigt token** | Entra-app-registrering med et client credential, token fornyes i koden | Beholder al fleksibilitet. Men kræver en app-registrering, et hemmeligt token og en aftale med IT |

**Jeg anbefaler A.** Regnearket skal læse fire lister og lægge dem i fire
faner — det er præcis det, Power Query er til. Godkendelsen bliver Office's
problem i stedet for vores, og de 1.500 linjer hente-, side- og
genforsøgskode kan slettes. C er den rigtige, hvis der senere skal skrives
tilbage i stor stil.

### Trin 3 — fjern gætteriet ved at rette kilden

De 345 linjer tekstheuristik forsvinder, hvis teksten kommer ind i en form,
der ikke skal gættes på. To halvdele:

- **I appen:** saner langteksten til `<b>`, `<u>`, `<br>` ved gem — den
  hvidliste vi talte om i går, nu bekræftet som den rigtige.
- **I regnearket:** slet heuristikken og lad `HtmlToSAPText` køre direkte.
  Den håndterer allerede præcis de tre tags.

Det er også dét, der endeligt fjerner problemet med underpunkter: de kan
ikke opstå, hvis de aldrig kommer med.

### Trin 4 — saml de 13 importprocedurer til én

Én procedure, der tager liste, felter og målfane som parametre. Samme
mønster som `sp_config.py` i Python-delen: kontrakten mod SharePoint ét
sted. Bliver mest overflødig, hvis vi vælger A.

### Trin 5 — lad GUI-delen være

`GUI_Script`, `Export_Script` og ITF-konverteringen virker. De skal ikke
røres ud over ét sted: når heuristikken fjernes i trin 3, får
`ConvertHtmlToSAPITF_Dynamic` renere input — den skal ikke selv laves om.

---

## Oprydning, uafhængigt af resten

To Excel-låsefiler er committet med:

```
excel/artifact/~$BIO SAP VH-plan lister.xlsm
excel/artifact/~$FL indberetninger udgave SPOOL V3.xlsm
```

De opstår, når en projektmappe er åben, og hører ikke til i git. De bør
slettes og `~$*` tilføjes til `.gitignore`.

De to `.xlsm`-filer fylder 8 MB. Så længe VBA'en også ligger eksporteret i
`excel/src/`, er det til at leve med — men det er dér, ændringer skal laves
og læses, ikke i binæren.

---

## Rækkefølge og omfang

| Trin | Afhænger af | Omfang |
|---|---|---|
| 1. Afklar site og godkendelsesvej | **dig** | en samtale |
| 2. Skift godkendelsen | trin 1 | stor — men mest *sletning* |
| 3. Fjern tekstgætteriet | app-siden først | 345 linjer ud, ~20 ind |
| 4. Saml importprocedurerne | trin 2 | bortfalder ved vej A |
| 5. GUI-delen | — | ingen ændring |

Det meste af arbejdet er at **fjerne** kode, ikke skrive ny. Regnearket
bliver mindre, og den del der er svær at få til at virke, bliver til noget,
Office selv står for.

---

# Tillæg: skift mellem BioSAP og BioSAPDEV

Besvarer dit svar på spørgsmål 1. Og undervejs viste det sig, at spørgsmålet
allerede var besvaret én gang.

## Vælgeren fandtes — den blev designet væk

`Setup`-fanen har **allerede** celler til det hele:

| Celle | Indhold |
|---|---|
| `D3` | SAP-system: `GP1` (Production) eller `GQ1` (Quality) |
| `D5` | Flow-URL |
| `D6`–`D9` | SharePoint-URL for Plans, Items, TLH, TL |
| `D10`–`D11` | Credential target og token-fallback |

SAP-delen bruger sin: `GetSystemPrefix()` læser `D3` og vælger mellem
`"SAP  DECS GP1  Production"` og `"SAP  DECS GQ1  Quality"`. **Det er
derfor GUI-delen kan skifte miljø, og SharePoint-delen ikke kan.**

`modSharePointImport` ignorerer `D6`–`D11` og bruger sine egne konstanter.
Kommentaren i koden siger det selv:

```vb
' Code-based config (ingen Setup-ark afhængighed)
```

Nogen har bevidst flyttet konfigurationen fra arket ind i koden — og dermed
fjernet den omskiftelighed, der allerede var bygget. Det skal bare føres
tilbage.

## To miljø-akser, ikke én

Det er her, det bliver farligt. Efter ændringen har regnearket **to**
uafhængige miljøvalg:

| Akse | Hvor | Værdier |
|---|---|---|
| SharePoint-site | ny | BioSAP · BioSAPDEV |
| SAP-system | `Setup!D3` | GP1 (prod) · GQ1 (test) |

Fire kombinationer. To er fornuftige, én er en tørprøve, og **én er den, der
holder folk vågne om natten**:

| SharePoint | SAP | Betydning |
|---|---|---|
| DEV | GQ1 | Test. Fint |
| PROD | GP1 | Drift. Fint |
| PROD | GQ1 | Tørprøve: rigtige planer, oprettes i testsystemet. Brugbart |
| **DEV** | **GP1** | **Testdata oprettes i produktions-SAP.** Den må ikke ske ved et uheld |

Derfor foreslår jeg ikke bare en vælger, men tre ting omkring den.

## Forslaget

### 1. Én vælger, afledte URL'er

En celle på `Setup` bliver miljøvælgeren: `DEV` eller `PROD`. De fire liste-URL'er
**regnes ud** af site-URL plus listenavn i stedet for at stå som fire celler,
der kan drive fra hinanden:

```vb
GetListUrl("MaintenancePlans")
  -> GetSiteUrl() & "/_api/web/lists/getbytitle('MaintenancePlans')/items"
```

Én ting at skifte. Fire URL'er kan ikke længere pege hver sin vej.

Vælgeren sætter **også** `D3` som standard — DEV → GQ1, PROD → GP1 — men
`D3` kan stadig overstyres manuelt, så tørprøven PROD+GQ1 er mulig.

### 2. Miljøet stemples på de hentede data

Det her er den vigtige, og den er billig.

Hver import skriver miljøet ind på fanen. `CreateMaintenancePlansFromButton`
og `SyncSelectedCreatedRowsToSharePoint` **nægter at køre**, hvis stemplet
ikke svarer til den aktuelle vælger:

> *Arket indeholder data hentet fra **DEV**, men vælgeren står på **PROD**.
> Hent igen, eller skift tilbage.*

Uden det er der intet, der forhindrer: hent fra DEV → skift til PROD →
opret. Arket ser ens ud i begge tilfælde. Med stemplet er den vej lukket.

### 3. Miljøet er synligt, og PROD spørger

Den aktuelle kombination står øverst på hver relevant fane — ikke begravet i
`Setup`. Og de to handlinger, der ændrer noget uden for regnearket
(oprettelse i SAP, tilbageskrivning til SharePoint), beder om en bekræftelse,
der **nævner miljøet ved navn**, når det er PROD eller GP1.

Ikke en dialog for hver knap. Kun de to, der kan gøre skade.

## Hvad det betyder for spørgsmål 2

Vælgeren fungerer i begge veje, så valget står stadig åbent — men det er
blevet lettere:

**Power Query** læser samme celle som VBA via `Excel.CurrentWorkbook()`, så
der er fortsat én kilde til sandheden. Den henter sine data på en
godkendelse, Office selv vedligeholder.

**Token-vejen** bliver nu billigere end først antaget: cellerne til
credential target og token-fallback **findes allerede** i `Setup` (`D10`,
`D11`), så rørene er lagt. Det, der mangler, er en Entra-app-registrering og
et token, der fornys — og det er en aftale med IT, ikke kode.

Jeg anbefaler stadig **Power Query** til hentningen. Med ét forbehold, jeg
ikke vil tale udenom: den præcise kolonneform — hvordan opslags- og
valgfelter kommer ud, og om `FieldValuesAsText` er nødvendig — skal
efterprøves med én rigtig hentning, før jeg lover, at heuristikken kan
slettes. Det er én test, ikke en ombygning.

## Rækkefølge

| Trin | Omfang |
|---|---|
| Miljøvælger i `Setup` + `GetSiteUrl`/`GetListUrl` | lille — fører den eksisterende `Setup`-afhængighed tilbage |
| Stempling og spærre | lille, og det er den der beskytter |
| Synligt miljø + bekræftelse ved PROD | lille |
| Hentningen selv (Power Query eller token) | stor — men mest sletning |

**De tre første kan bygges nu og er uafhængige af, hvad du vælger i
spørgsmål 2.** Sig til, så går jeg i gang med dem.

---

# Bygget: miljøvælgeren

De tre første trin er lavet. Hentningen selv (spørgsmål 2) er urørt — den
venter stadig på dit valg, og intet herunder afhænger af det.

## Hvad du skal gøre først

Kør `modEnvironment.SetupEnvironmentCell` én gang. Den:

- skriver etiketten "SharePoint site" i `Setup!F2` og lægger en rulleliste på
  **`Setup!F3`** med `DEV` og `PROD`
- sætter `DEV` som startværdi, så cellen ikke står tom
- markerer de ark, der allerede ligger i mappen, som **`PROD`**

Den sidste er med vilje. Det, der ligger i arkene nu, er hentet med de gamle
hardkodede URL'er, og de pegede alle fire på BioSap. Stemplede jeg dem som
det, du lige har valgt i `F3`, ville jeg påstå noget om data, jeg ikke ved.
Hent én gang forfra, før du opretter noget.

`F3` er ny. `D3` (SAP-systemet) er som før, og `D5`–`D13` er urørte.

Jeg havde først lagt vælgeren i `D2`. Det var forkert: `D2` indeholder
etiketten **"SAP Client"** til `D3`. Jeg havde kun set celle-kortet gennem
`Constants.bas`, ikke selve arket. Kolonne F er fri på hele `Setup`, og
`F2`/`F3` følger samme mønster som `D2`/`D3` — etiket over værdi.

## De to celler

| Celle | Styrer | Tom betyder |
|---|---|---|
| `Setup!F3` | SharePoint-site: `DEV` → BioSapDEV, `PROD` → BioSap | **fejl** — ikke `DEV` |
| `Setup!D3` | SAP-system: `GQ1` eller `GP1` | følg `F3` |

En tom `F3` er ikke det samme som `DEV`. Et tomt felt, der stille blev læst
som "det ufarlige", er præcis den slags antagelse, der en dag rammer det
forkerte miljø. `D3` må derimod gerne stå tom — så følger den `F3`, og du kan
stadig overstyre den, når du vil køre tørprøven `PROD + GQ1`.

## Spærren

`DEV + GP1` kan ikke lade sig gøre. Ikke en advarsel man kan klikke forbi:

```
Spaerret.

Data er hentet fra SharePoint DEV, men SAP staar paa GP1 (Production).

Testdata maa ikke oprettes i produktions-SAP.
```

De tre andre kombinationer kører. `PROD` og `GP1` spørger én gang pr. kørsel
og nævner miljøet ved navn; `DEV + GQ1` spørger slet ikke — en bekræftelse,
man ser hver gang, holder man op med at læse.

Kontrollen sidder to steder, og kun to:

- `GUI_Script.StartExtract` — det eneste sted, der opretter noget i SAP
- `Update_Sharepoint_Lists.SyncSelectedCreatedRowsToSharePoint` — det eneste
  sted, der skriver tilbage til SharePoint

Den anden kaldes af den første. Den spørger ikke to gange: `StartExtract`
sætter et flag for kørslen. **Spærren mod `DEV + GP1` gælder uanset flaget.**

## Stemplingen

Hvert ark bærer, hvilket miljø dets data kom fra. Uden det er der intet, der
forhindrer: hent fra DEV, skift til PROD, opret — arket ser ens ud i begge
tilfælde.

Stemplet ligger som et skjult defineret navn (`EnvStamp_<CodeName>`) og ikke
i en celle, så fanernes layout er urørt — importkoden regner med bestemte
rækker og kolonner.

Det sættes ét sted: `WriteImportRows`. Alle importstier, både standard og
all-fields, skriver deres ark derigennem, og `Object_list` gør det også.
Også når der ingen rækker er — arket er ryddet, og det tomme resultat gælder
det valgte miljø.

Et **ustemplet** ark slipper igennem. Så er regnearket lige blevet bygget om,
og der er ikke noget at modsige.

## Hvad der ellers ændrede sig

- `modSharePointImport` har ikke længere fire hardkodede BioSap-URL'er. De
  fire lister står som **navne** (`MaintenancePlans`, `MaintenanceItems`,
  `TaskListMain`), og sitet kommer fra `GetSiteUrl()`. De kan ikke længere
  drive fra hinanden.
- `GUI_Session.GetSystemPrefix` læser stadig `Setup!D3`, men gennem
  `modEnvironment.GetSapPrefix()`. Før gav en tom `D3` et `systemId` på kun
  klientnummeret, og forbindelsen fejlede uden at sige hvorfor.
- Importens kvittering starter med miljøet, så du kan se, hvor det kom fra,
  uden at slå op i `Setup`.

## To ting jeg ikke gjorde

**Miljøet står ikke permanent på fanerne.** Det var trin 3 i forslaget
ovenfor. At skrive i en celle på datafanerne betyder at flytte noget, og
importkoden regner med faste rækker (`START_ROW_DEFAULT = 3`,
`START_ROW_TL = 2`). Miljøet vises i stedet i importkvitteringen og i begge
bekræftelser. Skal det stå fast på fanerne, skal vi vælge en celle, der er
fri på tværs af alle fem faner — sig til, så finder vi den.

**`TLH` og `TL` peger stadig begge på `TaskListMain`.** Det gjorde de også
før; det er ikke noget, jeg har indført, og jeg har ikke ændret det, fordi de
to importer læser forskellige kolonner ud af samme liste. Men det er værd at
kigge på, når vi alligevel er i importen.

## Kontrollen

`tools/check_vba.py` læser alle 44 moduler statisk og fanger det, der ellers
først dukker op i Excels egen kompilering: en procedure uden `End`, en `GoTo`
uden label, et `modX.Member`-kald til noget, der ikke findes eller ikke er
`Public`. Regnearket kan kun kompileres i Excel, og hver kompilering koster
en runde frem og tilbage.

Alle fire kontroller er efterprøvet ved at lægge den rigtige fejl ind og se
den blive fanget. Den kører rent på det, der ligger nu:

```
44 moduler, 636 procedurer
ingen problemer
```

---

# Tre svar

## Power Query: den skifter ikke miljø — og henter ikke fra SharePoint

Jeg pakkede `DataMashup` ud af regnearket og læste M-koden. Der er fem
queries: `Maintenance_Plans`, `Maintenance_Items`, `Maintenance_TLH`,
`Maintenance_TL` og `Object_list`. Alle fem begynder ens:

```m
Source = Excel.Workbook(File.Contents(
    "C:\Users\PKBJE\OneDrive - Ørsted\Documents - Sapvedligehold\Apps\Microsoft Lists\BIO SAP VH-plan lister.xlsx"))
```

De henter ikke fra BioSap. De henter ikke fra BioSapDEV. De læser **én
lokal fil på din OneDrive** — en manuel eksport af listerne, på din sti,
med dit brugernavn. På en anden maskine findes filen ikke.

Så svaret er "ingen af delene": der hentes ikke fra begge miljøer, og der
hentes ikke fra nogen af dem.

### De er heller ikke koblet på

Kun `Vendor_Spend` er indlæst i et ark. De fem VH-plan-queries er
**connection-only** — de kører, men lander ingen steder. Fanerne
`Maintenance_Plans`, `Maintenance_Items`, `Maintenance_TLH`,
`Maintenance_TL` og `Object_list` skrives af VBA (`WriteImportRows`), ikke
af Power Query. De to systemer har samme navne på alt og rører ikke
hinanden.

### Og de indeholder den samme logik som VBA

Det er den del, der bekymrer mig mest. Forretningsreglerne står **to
steder**:

| Regel | I M | I VBA |
|---|---|---|
| Planned date trukket én cyklus tilbage | `Date.AddYears(d, -c)` osv. | `ResolvePlanStartDate` |
| Sort field nulpolstret til 3 | `Text.PadStart(_, 3, "0")` | `Maintenance activity type` |
| Priority → nøgle (Red=1, Yellow=3, Blue=6) | `Added Conditional Column` | `ExtractPriorityKey` |
| `REV mærke`: true → REV | `Table.ReplaceValue` | `NormalizeItemRevisionValue` |
| Aktivitetstype før `" - "` | `Text.BeforeDelimiter` | `NormalizeItemIlartValue` |
| Object list splittet på `\|\|\|` | `Splitter.SplitTextByDelimiter` | `RefreshObjectListFromMaintenanceItems` |

To implementeringer af samme regel driver fra hinanden. Det er ikke et
spørgsmål om, hvornår — kun om hvilken der er den rigtige, den dag de er
uenige, og hvordan man opdager det.

**Anbefaling:** de fem queries skal enten skrives om til at hente fra
SharePoint gennem miljøvælgeren, eller slettes. Ikke ligge og køre på en
filsti, der kun findes på din maskine. Det er samtidig svaret på
spørgsmål 2: vælger vi Power Query-vejen, er det ikke noget nyt, vi bygger
— det er de her fem, der bliver rettet til. `Vendor_Spend` skal blive, som
den er.

## GUI-scriptet: to ting der betyder noget, og fire der er pænere

GUI-delen virker, og det er ikke lidt værd. Men der er to steder, hvor den
kan tage fejl uden at sige det.

### 1. Statuslinjen læses, men ikke dens type

Efter hver gem hentes `wnd[0]/sbar`, og nummeret trækkes ud med et
regulært udtryk:

```vb
statusText = objSess.FindById("wnd[0]/sbar").Text
regex.Pattern = "\d+"
If matches.Count > 0 Then
    itemNumber = matches(0).Value
    SetMapValue ws, i, sapOutCol, itemNumber
```

`sbar` har en `MessageType` (`S` succes, `E` fejl, `A` abend, `W`
advarsel). Den læses ikke. Kommer SAP tilbage med en **fejl**, der
indeholder et tal — og det gør fejlbeskeder ofte — bliver det tal skrevet
i SAP-nummer-kolonnen som om det var et oprettet item.

Rettelsen er to linjer: læs `objSBar.MessageType`, og accepter kun `S`.
Variablen `objSBar` er allerede sat i `CreateGlobalDictionaries` og bliver
ikke brugt.

### 2. Én fejl stopper hele kørslen

`CreateTLH`, `CreateItems` og `CreatePlans` har alle ét `myerr:` for hele
løkken. Fejler række 12 af 40, ryger man ud af løkken, får
"Der opstod en fejl under oprettelse af Items", og de resterende 28 bliver
aldrig forsøgt — uden at nogen får at vide hvilke.

`Update_Sharepoint_Lists` gør det allerede rigtigt: `On Error GoTo
ItemRowError` inde i løkken, skriv fejlen i rækkens statusfelt, `Resume
NextItem`. Samme mønster hører hjemme i de tre create-procedurer.

### De fire mindre

- **Ingen `ScreenUpdating = False`.** Hver `SetMapValue` er en
  celleskrivning med genoptegning, genberegning og `Worksheet_Change`
  ovenpå. På en kørsel med hundredvis af rækker er det mærkbart.
- **`ws.Activate`** i `CreateTLH` er ikke nødvendig — alt arbejdet går
  gennem `ws`-referencen alligevel.
- **Celler læses én ad gangen.** `GetMapValue` er ét COM-kald pr. felt. Ti
  felter gange fyrre rækker er fire hundrede kald, hvor ét
  `ws.Range(...).Value`-array ville gøre det. Men: det er småting mod SAP's
  svartid, så det er oprydning, ikke hastighed.
- **140 `FindById` med fulde stier.** De lange
  `subSUBSCREEN_MITEM:SAPLIWP3:8002/...`-stier står ordret flere gange.
  Trækkes de ud i konstanter, kan de rettes ét sted, når SAP ændrer et
  skærmbillede.

**Rækkefølge:** de to første. De andre fire kan vente, og ingen af dem
ændrer noget for brugeren.

## Tilbageskrivningen: mekanikken findes, kontrollen gør ikke

Du skal ikke bygge noget nyt. `SyncSelectedCreatedRowsToSharePoint` kører
allerede automatisk som sidste trin i `StartExtract`, og kan køres alene
fra sin egen knap bagefter. Den tager de planer, der er markeret med
`CreateInSAP`, slår SharePoint-`Id` op på rækken, og sender en `MERGE` med
`SAPNum` og `Status = Published`.

Det, der mangler, er kontrollen af, **hvad** der sendes:

```vb
If Left$(upperText, 7) = "SKIPPED" Then Exit Function
If Left$(upperText, 5) = "ERROR" Then Exit Function
If InStr(1, upperText, "INGEN TASK LIST", vbTextCompare) > 0 Then Exit Function
IsSyncableSapValue = True
```

Det er en liste over tre ting, der afvises. Alt andet accepteres — også
en hel SAP-fejlsætning, også det tilfældige tal fra fejlen i punkt 1
ovenfor. Og så skrives det til SharePoint, og planen får `Published`.

En blokliste kan kun afvise det, man har set før. Den skal vendes om: et
SAP-nummer er cifre, og intet andet. `IsDigitsOnly` findes allerede i
`GUI_Script`.

De to rettelser hænger sammen — den første forhindrer, at et forkert tal
opstår; den anden forhindrer, at det slipper ud. Jeg vil lave dem begge.

**Svaret på dit spørgsmål er altså:** du skal ikke gøre noget. Den skriver
selv tilbage, når GUI'en er færdig. Men jeg vil ikke anbefale dig at stole
på den, før de to rettelser er inde.

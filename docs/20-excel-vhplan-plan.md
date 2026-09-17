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

`Setup!D2` bliver miljøvælgeren: `DEV` eller `PROD`. De fire liste-URL'er
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

# 34 — Oprettelse i SAP: ordrefiler og SAP Opretter

> **2026-10-03:** Opretteren laver nu også FL-anmodninger og hedder **SAP
> Opretter** (før *VH-plan Opretter*). Knappen *Vis plan* hedder *Vis
> detaljer*. FL-delen står i [`36-fl-sap-oprettelse.md`](36-fl-sap-oprettelse.md).

**Beslutning (2026-10-02):** VH-planer oprettes i SAP af **VH-plan Opretter**.
Det er en lille, ny Excel-projektmappe med SAP GUI Scripting, bygget på
felt-ID'erne fra det gamle GUI-script, der virker. Data til oprettelsen kommer
som **én JSON-fil pr. plan**. Et flow skriver den i et SharePoint-bibliotek,
som er synkroniseret til jeres pc'er med OneDrive. Power Query og login i
Excel bruges ikke længere.

| Hvad | Hvor |
|---|---|
| Opretteren (VBA) | [`excel/opretter/`](../excel/opretter) — brugervejledning i [README](../excel/opretter/README.md) |
| Ordren (JSON) | [`schema/vhplan-sap-order.schema.json`](../schema/vhplan-sap-order.schema.json), eksempel [`example-sap-order.json`](../schema/example-sap-order.json) |
| Kvitteringen (JSON) | [`schema/vhplan-sap-receipt.schema.json`](../schema/vhplan-sap-receipt.schema.json), eksempel [`example-sap-receipt.json`](../schema/example-sap-receipt.json) |
| De to flows | [`35-flow-sap-ordre.md`](35-flow-sap-ordre.md) med udtrykkene i [`flow/sap-ordre/`](../flow/sap-ordre) |
| Bibliotek og kolonner | [`sharepoint/provision/Provision-SapCreation.ps1`](../sharepoint/provision/Provision-SapCreation.ps1) |
| Tests | `tests/test_vba_runner.py`, `tests/test_sap_contract.py`, `tools/vba_strict.py` |

## 1. Kort svar

**Metoden: stadig Excel og GUI Scripting, men ikke det gamle regneark.** Det
gamle regneark har 22.000 linjer VBA i 31 moduler. GUI-delen virker, men
hentningen fra SharePoint gør ikke (docs/20). Opretteren er de cirka 3.000
linjer, der skal til for at oprette en plan, og tre knapper, man skal kende:
*Opdater liste*, *Vis detaljer* og *Opret i SAP*.

**Data: JSON — og den bare *er* der.** Når en plan bliver *Ready for creation
in SAP*, skriver et flow hele planen i én fil: plan, items, operationer,
langtekster og materialer, som de blev godkendt. Filen lander i biblioteket
`SAP-oprettelse`, som OneDrive synkroniserer til Master Datas pc'er. Opretteren
læser mappen. Der er ingen Power Query, intet login i Excel og ingen
hemmelig flow-URL i projektmappen.

JSON frem for Markdown, fordi filen er et *maskinformat*. Den kan valideres
mod et skema, og felterne kan ikke misforstås. Det menneskelige overblik
har I allerede i mailen. I opretteren viser **Vis detaljer** desuden felt for felt,
hvad der kommer til at stå i SAP, før der trykkes på noget.

**Tilbage til SharePoint:** opretteren lægger en kvitteringsfil i samme
bibliotek. Et flow skriver plannummer, positionsnumre og arbejdsplaner tilbage
og sætter planen til *Published*. Så sender det eksisterende
`PlanPublished`-flow mailen til rekvirenten.

## 2. Sådan hænger det sammen

```
 App ─► godkendelse ─► MaintenancePlans.Status = "Ready for creation in SAP"
                          │
                          ├─► (som i dag) mail til sapvedligehold@
                          │
                          └─► flow BioSap-VhPlan-SapOrder
                                 skriver SAP-oprettelse/Til oprettelse/MP0133_20261002-084233.json
                                 og SapOrderGuid paa planen
                                          │  OneDrive
                                          ▼
                              SAP Opretter (Excel, paa jeres pc)
                              Opdater liste → Vis detaljer → Opret i SAP
                              pr. item:  IA05 arbejdsplan → IP04 position → IP05 langtekst
                              til sidst: IP01 plan
                              statusfil efter hvert gem
                                          │
                              SAP-oprettelse/Kvitteringer/MP0133_….kvittering.json
                                          │  OneDrive
                                          ▼
                              flow BioSap-VhPlan-SapReceipt (hvert 10. minut)
                              SAPNum, Status = Published, SapItemNo, TaskListGroup
                                          │
                              BioSap-EmailNotification-PlanPublished → rekvirenten
```

## 3. Hvorfor Excel — og ikke Python, PowerShell eller Power Automate Desktop

| | Excel + VBA | Python | PowerShell | Power Automate Desktop |
|---|---|---|---|---|
| Skal installeres på teamets pc'er | Nej | Ja (eller en .exe, som antivirus/AppLocker ofte stopper) | Nej | Ofte, og automatisk start kræver en RPA-licens |
| Bevist mod jeres SAP | **Ja** — felt-ID'erne er det gamle scripts | Nej | Nej | Nej |
| Kører på en styret pc | Makroer bruges allerede i teamet | Afhænger af IT | Constrained Language Mode spærrer typisk COM | Afhænger af IT |
| Vedligehold | Kildekode i git, bygges med ét script | Godt | Klodset: SAP's COM-objekter kræver `InvokeMember` overalt | Flows ligger i Dataverse, ikke i git |

**VBScript** (.vbs, som SAP's optager laver) er udelukket: Microsoft er ved at
fjerne det fra Windows.

Svagheden ved VBA er, at det kun kan kompileres i Excel. Den er afbødet her,
se afsnit 9: et strengt statisk tjek (Option Explicit, blokke, tegnsæt) og
LibreOffice, der oversætter alle moduler og kører de rene funktioner.

**Kontrakten gør valget billigt at ændre.** Ordren og kvitteringen er
JSON-filer med et skema. Skal opretteren en dag skrives i noget andet — eller
erstattes af en serverside-vej (BAPI, LSMW) — er det kun opretteren, der
skiftes. Appen, flowene og filerne bliver.

## 4. Hvorfor en synkroniseret mappe

| Vej | Problem |
|---|---|
| Power Query mod SharePoint | Login i Excel, kolonnerne kommer ud forskelligt, og de fem queries i det gamle regneark læste en lokal fil på én pc (docs/20) |
| VBA mod SharePoints REST-API | Login virker kun med en tilfældig cookie. Det er grunden til, at hentningen i dag "virker nogle gange" (docs/20) |
| HTTP-flow med signeret URL | URL'en *er* adgangen og ville ligge i projektmappen (docs/06) |
| **Bibliotek synkroniseret med OneDrive** | OneDrive står for login, filerne er bare der, og det virker begge veje uden hemmeligheder |

Mailen kan stadig bruges: en ordrefil vedhæftet mailen kan lægges ind med
*Importér fil…*. Se docs/35 for, hvordan flowet vedhæfter den.

**Kvitteringerne læses med et tidsstyret flow, ikke ved "ny fil".** Microsoft
skriver, at filer, der kommer ind via OneDrive-synkronisering, ikke
nødvendigvis udløser SharePoint-triggerne. Et flow, der kigger i mappen hvert
10. minut, er ligeglad med, hvordan filen kom dertil.

## 5. Ordren og kvitteringen

**Ordren er flad** — `plan`, `items`, `operations` og `materials` hver for
sig, ligesom listerne i SharePoint. Det gør flowet til tre *Select*-handlinger
og én *Compose*, uden løkker. Opretteren hænger selv operationerne på deres
item.

**Værdierne er SharePoints egne**, kun renset for opslags- og valgobjekter
(`"activityType": "102 - Predetermined Maintenance"`, ikke `"102"`). Al
oversættelse til SAP sker ét sted, i opretteren (`VhpMap.bas`). Det gamle
regneark havde de samme regler i både Power Query og VBA (docs/20), og så
glider de fra hinanden.

| I ordren | I SAP | Regel (VhpMap) |
|---|---|---|
| `plan.title` | IP01 planens tekst | 40 tegn |
| `plan.cycle` + `unit` | IP01 cyklus | `1` + `WK` |
| `plan.plannedDate` (første forfald) | IP01 startdato | **én cyklus før** (som det gamle `ResolvePlanStartDate`) |
| `plan.cycle` + `unit` | kaldshorisont, planlægningsperiode | opslag i arket *Opslag* |
| `plan.plant` | værk, arbejdsplanprofil | opslag (`SSV` → `2804`, `PMSSV`) |
| `plan.sortField(Id)` | sorteringsfelt | Id, Id med nuller, ellers teksten |
| `items[].title` | IP04 kort tekst og IA05 beskrivelse | 40 tegn |
| `items[].objectList` | IP04 objektliste | FL før `" - "`, delt ved `;` (ny app) eller `|||` (gammel) |
| `items[].activityType` | ILART | tre første tegn |
| `items[].priority` | prioritet | Red → 1, Yellow → 3, Blue → 6, ellers første ciffer |
| `items[].revision` / `revisionMark` | GV_REVNR | `REV` |
| `items[].longText` | IP05 langtekst | HTML → SAPscript (`VhpItf.bas`) |
| `operations[].controlKey` | STEUS | PM01, ZB01, PM02, PM03 |
| `operations[].price` | PREIS (PM02) | som det står i appen |
| `operations[].workCenter` (PM03) | ydelse fra modelydelsesspecifikationen | opslag på de fem sidste tegn (`XSTIL`) |

**Kvitteringen er statusfilen.** Under kørslen ligger den som
`<ordre>.status.json` ved siden af ordren og bliver skrevet efter hvert objekt,
SAP har gemt. Når planen er oprettet, kopieres den til `Kvitteringer` med
`state = Created`.

| `state` | Betyder | Hvad nu |
|---|---|---|
| `InProgress` | En kørsel er i gang (står hvem) | Vent |
| `Partial` | Noget er oprettet, resten mangler | Ret årsagen, tryk *Opret i SAP* igen — det oprettede springes over |
| `Failed` | Intet er oprettet | Ret årsagen, kør igen |
| `NeedsCheck` | SAP svarede uklart efter et gem | En person ser efter i SAP, se 8. |
| `Created` | Alt er oprettet | Flowet skriver tilbage |

## 6. Det, der sker i SAP

For hvert item, og til sidst planen. Felternes rækkefølge og ID'er er det
gamle scripts (`excel/src/Modules/GUI_Script.bas`), samlet i `VhpConfig.bas`.

| Trin | Transaktion | Gør |
|---|---|---|
| Arbejdsplan | IA05 | profil, nøgledato → beskrivelse, værk, arbejdscenter → operationer (arbejdscenter, kontrolnøgle, tekst, timer, antal; PM02 pris/varegruppe/leverandør; PM03 ydelse med timerne som mængde) → operationernes langtekster → gem |
| Position | IP04 | kategori PM, ingen ordreoprettelse, tekst, FL, ordreart, ILART, arbejdscenter, prioritet, arbejdsplan (A/gruppe/tæller), objektliste, status og revision → gem |
| Langtekst | IP05 | itemets langtekst → gem |
| Plan | IP01 | kategori PM uden strategi, tekst, cyklus, positionerne én for én, kaldshorisont, planlægningsperiode, startdato, sorteringsfelt → gem |

**Det, der er ændret i forhold til det gamle script, og hvorfor:**

- **Én arbejdsplan pr. item.** Det gamle script samlede operationer på
  `TaskID`, som appen ikke skriver længere. Nye planer fik derfor *ingen*
  arbejdsplan.
- **Operationsoversigten og ydelseslisten rulles.** Før fejlede et item med
  flere operationer, end der er synlige linjer.
- **PM02 får prisen og varegruppen fra appen.** Før blev feltet med timer
  ganget med 1000, og varegruppen var altid `B08.06`. Den er nu standarden i
  *Indstillinger*, når operationen ikke har én.
- **Et nummer læses kun fra et svar, der siger succes** (`S`/`W` på
  statuslinjen), og en dialog efter *Gem* giver `NeedsCheck` i stedet for et
  gæt. Det gamle script kunne skrive et tal fra en fejlbesked som
  plannummer (docs/20).
- **Valideringen sker før SAP.** Det gamle script opdagede en manglende
  kaldshorisont først ved planen, efter arbejdsplaner og positioner var
  oprettet.

## 7. Sikkerhed

| Risiko | Værn |
|---|---|
| Testdata i produktions-SAP | Ordren siger `DEV`, `TEST` eller `PROD`. DEV og TEST kan kun oprettes i et testsystem, PROD kun i produktion (*Indstillinger*, `ProdSystems`). Der spørges én gang pr. kørsel før produktion |
| En PROD-plan prøvet i GQ1 | Spærret. Kvitteringen ville ellers skrive et testnummer på en rigtig plan |
| Halvt oprettede planer | Validering før SAP. Statusfil efter hvert gem, så en ny kørsel fortsætter, hvor den slap |
| Dubletter | Et nummer læses kun fra et succes-svar. Ved et uklart svar stopper planen (`NeedsCheck`) i stedet for at prøve igen. En plan, der allerede er oprettet i samme SAP-system (ordren ligger i *Oprettet*), oprettes ikke igen |
| To kolleger på samme plan | Statusfilen siger, hvem der kører den. Den anden får besked |
| En gammel ordre efter en ny | Den nyeste ordre pr. plan bruges. Kvitteringsflowet afviser en kvittering, hvis `orderGuid` ikke er planens `SapOrderGuid` |
| En plan trukket tilbage og godkendt igen | Flowet tømmer `SapOrderGuid`, når planen forlader *Ready* uden at være oprettet. Den nye godkendelse giver derfor en ny ordre, som erstatter den gamle |
| En fremmed fil i Kvitteringer | Flowet tjekker også status og SAP-system. Biblioteket skal kun kunne skrives af Master Data og flowets servicekonto |
| Første gang | *Bekræft hvert gem* er slået til: opretteren stopper før hvert gem, så I kan se SAP-billedet igennem |

## 8. Når noget går galt

- **Planen står som "Kan ikke oprettes".** *Vis detaljer* viser alle fejl. De
  fleste rettes i appen (planen sendes retur og godkendes igen — så kommer
  der en ny ordre) eller i arket *Opslag* (en manglende kaldshorisont eller
  ydelse).
- **"Delvist oprettet".** Ret årsagen og tryk *Opret i SAP* igen. Det, der
  står i statusfilen, oprettes ikke igen.
- **"Kræver kontrol".** SAP svarede uklart efter et gem. Se i SAP (IA07,
  IP06, IP03), om objektet blev oprettet:
  - *Blev det ikke oprettet:* slet statusfilen ved siden af ordren. Så
    begynder planen forfra. Er noget andet allerede oprettet for planen, så
    skriv i stedet dets numre ind i statusfilen og sæt `state` til `Partial`.
  - *Blev det oprettet:* skriv nummeret ind i statusfilen og sæt `state` til
    `Partial`.

  Det er den eneste situation, hvor en fil skal rettes i hånden, og det
  hører hjemme hos den, der vedligeholder opretteren.
- **En plan skal have en ny ordre** (fx rettet efter, at ordren blev
  skrevet): tøm `SapOrderGuid` på planen i SharePoint. Flowet skriver en ny,
  og opretteren bruger den nyeste. Trækkes planen tilbage (*Draft* eller
  *Returned*) og godkendes igen, sker det af sig selv.
- **"Planen er allerede oprettet i …".** Opretteren opretter ikke den samme
  plan to gange i ét SAP-system. Det sker typisk, hvis en ordre blev
  oprettet, mens planen var trukket tilbage. Ret planen i SAP (IP02, IA02), skriv
  plannummeret i `SAPNum` og sæt *Status* til *Published* i SharePoint i
  hånden. Flyt så den nye ordre til *Oprettet*.

## 9. Afprøvning

**Afprøvet her (uden Excel og SAP):**

- `tools/check_vba.py` → `tools/vba_strict.py`: alle navne er erklæret
  (Option Explicit), alle blokke er lukket, private procedurer kaldes ikke
  på tværs, og kildekoden er ren ASCII. Afprøvet med plantede fejl.
- LibreOffice Basic oversætter hvert modul (syntaksfejl) og kører
  `VhpTest.SelfTestPure`: 85 tjek af oversættelserne, langteksten og FL-reglerne.
- `tests/test_sap_contract.py`: eksemplerne validerer mod skemaerne, flowets
  felter er præcis skemaets, opretteren læser kun felter, skemaet kender, og
  kolonnerne, flowene skriver, findes eller oprettes af
  provisioneringsscriptet.

**Skal afprøves i SAP, før det bruges i drift** (DEV-data mod GQ1, med
*Bekræft hvert gem* slået til):

1. *Selvtest* i arket *Indstillinger* (JSON-delen kræver Windows).
2. *Test SAP* på Start-arket.
3. Én plan med ét item og en PM01-operation. Se hvert billede igennem før
   *Ja*. Står gruppenummeret på IA05-hovedet før gem, som i det gamle script?
4. Et item med PM02 (pris, varegruppe, leverandør) og PM03 (ydelsen findes i
   modelydelsesspecifikationen, mængden er timerne).
5. Langtekster på en operation og et item: fed, understreget, punktopstilling
   med underpunkter.
6. Et item med objektliste og flere items i samme plan (IP01 knytter dem
   én for én).
7. Et item med flere operationer, end der er synlige linjer (rulning).
8. En fejl midtvejs: giv et item en FL, der ikke findes. Planen bliver
   *Delvist oprettet*. Ret den, kør igen, og se, at intet oprettes to gange.
9. Kvitteringsflowet: planen bliver *Published* med de rigtige numre, og
   rekvirenten får mailen.

Punkt 3–7 er dem, hvor SAP kan opføre sig anderledes end antaget. Er et felt-ID
forkert, siger opretteren hvilket og på hvilken skærm. Rettelsen er én linje i
`VhpConfig.bas`.

## 10. Ikke med i version 1

| | Hvorfor | I mellemtiden |
|---|---|---|
| Strategiplaner (IP42, pakker) | Pakkeallokeringen i IA05 er aldrig blevet kørt af et script mod jeres SAP. Opretteren afviser planen med en tydelig besked frem for at gætte | Opret dem i hånden |
| Materialer (komponenter) | Komponentskærmen i IA05 er ikke optaget | Står som advarsel i *Vis detaljer* og i kvitteringen: tilføj i IA06 |
| Dokumenter | Ligger i SharePoint, ikke i ordren | Som i dag |
| Omkostningsart | Kolonnens plads i operationsoversigten kendes ikke | SAP udleder den |
| Operationsnumre | SAP nummererer 0010, 0020 … i appens rækkefølge | — |

## 11. Udrulning

1. Kør `Provision-SapCreation.ps1` mod DEV-sitet (bibliotek, mapper,
   kolonner). Sæt rettighederne på biblioteket.
2. Byg de to flows efter docs/35 i solution BIO SAP og opret
   miljøvariablerne `BioSap-Environment` og `BioSap-SapSystem`.
3. Synkronisér biblioteket med OneDrive på jeres pc'er.
4. Byg projektmappen: `excel\opretter\Build-Opretter.ps1`. Udfyld arket
   *Opslag* (ydelsesnumrene og de værker, der mangler, fra det gamle
   regneark). Læg den, hvor teamet åbner den fra.
5. Afprøv efter 9. med DEV-planer i GQ1.
6. Gentag 1–3 mod PROD-sitet, og sæt *SAP-system* til GP1.
7. Når I stoler på den: sæt *Bekræft hvert gem* til Nej.

Det gamle regneark kan blive liggende til det, det ellers bruges til
(udtræk, sammenligning). Dets oprettelsesdel skal ikke bruges sideløbende
med opretteren, fordi de ikke kender hinandens status.

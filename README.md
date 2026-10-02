# SAP masterdata – canvas apps og indmeldinger

Canvas app og indmeldingsflow til SAP masterdata. **Én app:
[`BIO SAP App/`](BIO%20SAP%20App)**, med seks skærme — hub, VH-plan,
Equipments, Materials, Functional Location og KKS-opslaget. Sidebaren og
hubben navigerer mellem skærmene. Se [`BIO SAP App/README.md`](BIO%20SAP%20App/README.md).

De fem enkeltapps er udfaset (2026-10-01, [`docs/33`](docs/33-udfasning.md)).
Deres mapper indeholder stadig **byggerne** til hver skærm — BIO SAP bygges
af dem:

| Skærm | Byggere i | Rolle |
|---|---|---|
| **Masterdata Hub** | [`Masterdata Hub/`](Masterdata%20Hub) | Landingssiden. Alle indmeldinger på tværs af de fem domæner, med status. Én datakilde |
| **VH-plan** | [`Maintenance Plan App/`](Maintenance%20Plan%20App) | Indmelding af vedligeholdsplaner, inkl. strategiplaner med pakker |
| **Equipments** | [`Equipment App/`](Equipment%20App) | Indmelding af udstyr |
| **Materials** | [`Material App/`](Material%20App) | Indmelding af reservedele — også ud fra en leverandørfaktura (PDF eller OIOUBL/Peppol-XML), se [`docs/34`](docs/34-faktura-import.md) |
| **Functional Location** | [`Functional Location App/`](Functional%20Location%20App) | Functional Locations (SPOOL): KKS-syntaks, klasse og spool-felter pr. klasse. Reglerne er HTML-sidens (`html/functional-location.html` + JS) - se [`docs/31`](docs/31-functional-location-regler.md) |
| **KKS lookup** | [`KKS App/`](KKS%20App) | Opslag i KKS-vejledningen: funktions-, aggregat- og komponentnøgler. Kun en skærm i BIO SAP - den var aldrig en af de fem enkeltapps. Data i SharePoint; aggregat og komponent genbruger `MD_FLKey`. Se [`KKS App/README.md`](KKS%20App/README.md) |

> **Equipments og Materials deler byggeklodser, men er to apps.** De var
> engang den samme app med to konfigurationsfiler; nu skal de kunne to
> forskellige ting. Delene — bar, formular, dokumentrude, rækketabel,
> indsend — ligger ét sted i [`tools/domain_parts.py`](tools/domain_parts.py),
> mens **kompositionen** er hver apps egen. Skal kun den ene ændres, skrives
> ændringen i dens egen `build/`-mappe, ikke i de fælles dele.

Alle `.pa.yaml`-skærme er **genereret** af Python-builderne i den enkelte
apps `build/`-mappe og de fælles moduler i `tools/`. Byg og efterregn
layoutet med:

```bash
pip install -r requirements.txt  # første gang
python3 tools/build_all.py       # BIO SAP App + alle tjek
python3 tools/build.py           # det samme i én proces
```

### Forudsætninger

| Værktøj | Bruges til |
|---|---|
| Python 3.10+ med `requirements.txt` (PyYAML, openpyxl) | Byggeri og tjek |
| Node 22+ | Efterprøvning af Functional Location-reglerne mod `html/*.js` (uden Node bygges der, men reglerne er ikke efterprøvet) |
| .NET 10 (`dnx`) | Canvas authoring MCP-serveren bag `tools/canvas_mcp.py` — se docs/21 |
| PowerShell 7 (`pwsh`) med PnP.PowerShell 2.x+ — virker **ikke** i Windows PowerShell 5.1 (`Connect-PnPOnline` findes ikke dér) | `sharepoint/provision/*.ps1`, `sharepoint/inspect/*.ps1` |
| pac CLI | `tools/export_solution.ps1` (hentes med `dnx`, hvis den mangler) |

**Tjek en ny pc i én kommando** (også Windows — CI kan ikke køre i
Ørsteds repo, fordi hostede runnere er slået fra):

```powershell
python tools\doctor.py          # forudsætninger, byg, git-tjek, tests
python tools\doctor.py --fix    # sletter desuden gamle filer fra før udfasningen
```

Den gør det samme som `.github/workflows/build.yml` og siger præcis,
hvad der mangler (Python-pakker, Node, PowerShell 7, PnP.PowerShell).

Status på kendte fund og den prioriterede plan står i [`REVIEW.md`](REVIEW.md).

**Farver og breakpoints står ét sted for alle apps** og må ikke skrives
i en builder — byggeriet stopper, hvis nogen gør:

| Fil | Ejer |
|---|---|
| [`tools/design_tokens.py`](tools/design_tokens.py) | Alle farver, begge temaer. Mørk tilstand er den anden gren af samme `If`. Se [`docs/26-designtokens.md`](docs/26-designtokens.md) |
| [`tools/layout_tokens.py`](tools/layout_tokens.py) | Alle breakpoints. `LayoutContext` / `LayoutRank`. Se [`docs/27-layouttokens.md`](docs/27-layouttokens.md) |
| [`tools/build_helpers.py`](tools/build_helpers.py) `app_frame` / `top_bar` / `flow_row` | Rammen, bjælken og rækker der ombryder — ens i alle apps. Se [`docs/30-responsivt-layout.md`](docs/30-responsivt-layout.md) |

Arbejdsgangen står i [`.github/skills/canvas-build/SKILL.md`](.github/skills/canvas-build/SKILL.md).

Synkroniseringen til Power Apps Studio kan køres fra en terminal — samme
MCP-server som VS Code bruger, bare uden VS Code:

```powershell
python tools\canvas_mcp.py deploy --app biosap
```

Se [`docs/21-mcp-uden-vscode.md`](docs/21-mcp-uden-vscode.md).

Dokumenterne nedenfor er oplægget bag VH-plan-delen: udvidelsen fra single
cycle til **strategiplaner** (SAP PM, IP42) med de pakker, der hører til
strategien.

Backend: SharePoint-lister. Frontend: Canvas app i Power Apps, med
HTML-komponenten brugt der hvor den faktisk hjælper.

> Dokumenterne 01–05 er det **oprindelige oplæg** og markeret som historiske
> (den `VHP_*`-model, de beskriver, blev ikke bygget). Den byggede løsning
> er beskrevet i SKILL.md, docs/07, docs/21 og docs/26–32.

## Oplægget (historisk) og de levende dokumenter

| Fil | Indhold |
|---|---|
| [`docs/01-loesningsoplaeg.md`](docs/01-loesningsoplaeg.md) | Domæneforståelse, arkitektur, komponentvalg, åbne spørgsmål |
| [`docs/02-datamodel-sharepoint.md`](docs/02-datamodel-sharepoint.md) | Lister og kolonner, felt for felt |
| [`docs/03-canvas-app-design.md`](docs/03-canvas-app-design.md) | Skærme, komponenter, tilstand, gem/submit |
| [`docs/04-integration-sap.md`](docs/04-integration-sap.md) | Fire veje til SAP – kontrakt, idempotens, fejlhåndtering |
| [`docs/05-implementeringsplan.md`](docs/05-implementeringsplan.md) | Faser, risici, hvad der kan skæres væk |
| [`docs/06-excel-gui-scripting.md`](docs/06-excel-gui-scripting.md) | **Den valgte vej til SAP:** Excel + GUI Scripting |
| [`docs/07-landingsside.md`](docs/07-landingsside.md) | Landingsside for alle fem masterdata-domæner: hub vs. monolit, indekslisten, performanceregler |
| [`docs/32-godkendelsesflow.md`](docs/32-godkendelsesflow.md) | **Oplæg:** godkendelsesflow for nye VH-planer — system- og omkostningsgodkendelse pr. item (Power BI Plant Section Key + MD_Approver, 300.000 kr.), kvalitet pr. værk; statusmodel, kolonner, flows |
| [`docs/34-faktura-import.md`](docs/34-faktura-import.md) | **Fakturaimport i Materials:** en faktura bliver til kladderækker i en ny anmodning. Uden premium: et Office Script via Excel Online (Business). Opsætning af script og flow trin for trin |

## Kode og artefakter

| Sti | Indhold |
|---|---|
| `tools/canvas_mcp.py` | Byg, compile og synk til Studio via canvas-authoring MCP-serveren — uden VS Code |
| `flow/invoice-import/ReadInvoice.ts` | Fakturalæseren (Office Script): PDF-tekst og OIOUBL/Peppol-XML → fakturalinjer som JSON. Køres af flowet `BioSap-Material-ReadInvoice` |
| `tools/invoice/` | Testfakturaerne og `harness.mjs`, der kører læseren på dem ved hver bygning (kræver Node 22.13+) |
| `tools/export_solution.ps1` | Hent solution BIO SAP ned som læsbare filer — flows, miljøvariabler, connection references |
| `powerfx/*.fx` | **Designnoter** fra oplægget — ikke kode, der bygges. FL-builderne bruger 03/04 som mønster |
| `powerfx/01-app-formulas.fx` | Named formulas, opstart, navigation |
| `powerfx/02-pakkematrix.fx` | Pakkematricen – nested gallery, toggle, genveje |
| `powerfx/03-validering.fx` | Regelsæt S1–S9 som én meddelelsestabel |
| `powerfx/04-submit-patch.fx` | Genoptageligt gem + JSON-snapshot ved submit |
| `powerfx/05-html-timeline.fx` | Formel, der bygger HTML-forfaldskalenderen |
| `sharepoint/provision/Provision-*.ps1` | Idempotent PnP-provisionering af de lister, apperne bruger (se Hurtig start) |
| `sharepoint/provision/Provision-RequestIndex.ps1` | `MD_RequestIndex` — den fælles indeksliste bag landingssiden |
| `sharepoint/provision/Provision-VHPlanApproval.ps1` | Godkendelsesflowets fase 1: kolonner på `MaintenancePlans`, `MD_Approver`, `MD_ApprovalLog`, grænsen i `AppSettings` — se `docs/32` |
| `sharepoint/seed/*.csv` | Masterdata: strategier, pakker, hjælpetekster, godkendere, FL-nøgler |
| `schema/vhplan-request.schema.json` | Kontrakten mod SAP |
| `schema/example-strategy-request.json` | Udfyldt eksempel (kompressor, Z-MONTH) |
| `html/cycle-timeline-reference.html` | Referenceoutput – åbn i en browser |
| `excel/vba/*.bas` | VBA-moduler: kilde, kontrakt, SAP GUI Scripting, batch |
| `excel/powerquery/*.m` | SharePoint-lister → Excel-tabeller, inkl. pakkepivot |
| `excel/VHPlan-SAP-skabelon.xlsx` | Projektmappe med de rigtige tabeller og eksempeldata |

## Vejen til SAP

SharePoint er backend, fordi godkendelsesflowet hører hjemme der. Oprettelsen
i SAP sker med en **Excel-makro, der kører SAP GUI Scripting**.

Lagdelingen holder de tre ting adskilt, så hver kan skiftes for sig:

```
KILDE (vælg én)                FÆLLES KONTRAKT I VBA      UDFØRELSE
Power Query → arktabeller  ┐
JSON-fil (VBA-JSON)        ├─► Collection af         ──►  IA01 (arbejdsplan)
Manuelt udfyldt ark        ┘   Dictionary-poster          IP42 (plan)
```

JSON er den rigtige **kontrakt** — ét frosset dokument pr. anmodning, der
viser præcis hvad der blev godkendt. JSON er derimod det forkerte
**arbejdsformat for VBA**: der er ingen indbygget parser, og `ScriptControl`
findes kun i 32-bit Office. Power Query flader data ud til tabeller formet som
SAP-skærmene, og VBA laver kun det, VBA er god til: at trykke på knapper.

## De tre beslutninger, det hele hænger på

**1. Pakkerne hører til arbejdsplanens operationer, ikke til planen.**
I SAP ejer strategien pakkerne (masterdata), arbejdsplanen ejer allokeringen
operation→pakke, og vedligeholdsplanen peger bare på begge. Bygger man
matricen på planen, opdages fejlen først, når SAP-siden skal nøgle det.

**2. Allokeringen gemmes som én streng pr. operation, ikke som en junction-liste.**
`PackagesKey = ";1;3;5;"`. En junction-liste ville betyde op til 200
skrivninger pr. indsendelse — uden transaktioner i SharePoint, så en
halvvejs fejlet gemning efterlader en halv matrix. Sentinel-separatoren i
begge ender gør, at `;1;` aldrig matcher inde i `;12;`.

**3. HTML-komponenten bruges til visualisering, ikke til input.**
HTML text-kontrollen kan ikke sende events tilbage til appen. Matricen
bygges derfor som en nested gallery (ydre = operationer, indre = pakker),
mens HTML bruges til forfaldskalenderen og print-resuméet — to ting der
ikke kan laves i native kontroller.

## Hurtig start

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
$site = "https://<tenant>.sharepoint.com/sites/<site>"

# Indekslisten bag landingssiden. -AddSampleRows giver fire prøverækker.
.\sharepoint\provision\Provision-RequestIndex.ps1 -SiteUrl $site -AddSampleRows

# Domænernes lister
.\sharepoint\provision\Provision-EqMatLists.ps1              -SiteUrl $site
.\sharepoint\provision\Provision-FunctionalLocationLists.ps1 -SiteUrl $site
.\sharepoint\provision\Provision-StrategyLists.ps1           -SiteUrl $site
.\sharepoint\provision\Provision-TasklistLists.ps1           -SiteUrl $site
.\sharepoint\provision\Provision-StandardTaskOperations.ps1  -SiteUrl $site
.\sharepoint\provision\Provision-VHPlanColumns.ps1           -SiteUrl $site
.\sharepoint\provision\Provision-VHPlanApproval.ps1          -SiteUrl $site
.\sharepoint\provision\Provision-HelpText.ps1                -SiteUrl $site
# KKS-opslaget (efter FunctionalLocationLists - MD_FLKey genbruges)
.\sharepoint\provision\Provision-KksLists.ps1                 -SiteUrl $site -SeedMasterData
```

VH-planens egne lister (`MaintenancePlans`, `MaintenanceItems`,
`TaskListMain` …) findes i forvejen; scripterne ovenfor tilføjer kolonner og
de nye `MD_*`-lister. Det tidligere `Provision-VHPlanLists.ps1` ligger i
`archive/` — det oprettede den ubrugte `VHP_*`-model.

Åbn derefter `html/cycle-timeline-reference.html` i en browser for at se,
hvad forfaldskalenderen skal ende med at vise.

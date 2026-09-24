# SAP masterdata – canvas apps og indmeldinger

Canvas apps og indmeldingsflow til SAP masterdata. **Fem apps:**

| App | Mappe | Rolle |
|---|---|---|
| **Masterdata Hub** | [`Masterdata Hub/`](Masterdata%20Hub) | Landingssiden. Alle indmeldinger på tværs af de fem domæner, med status. Én datakilde |
| **VH-plan** | [`Maintenance Plan App/`](Maintenance%20Plan%20App) | Indmelding af vedligeholdsplaner, inkl. strategiplaner med pakker |
| **Equipments** | [`Equipment App/`](Equipment%20App) | Indmelding af udstyr |
| **Materials** | [`Material App/`](Material%20App) | Indmelding af reservedele |
| **Functional Location** | [`Functional Location App/`](Functional%20Location%20App) | Functional Locations (SPOOL): KKS-syntaks, klasse og spool-felter pr. klasse. Reglerne er HTML-sidens (`html/functional-location.html` + JS) - se [`docs/31`](docs/31-functional-location-regler.md) |

> **Equipments og Materials deler byggeklodser, men er to apps.** De var
> engang den samme app med to konfigurationsfiler; nu skal de kunne to
> forskellige ting. Delene — bar, formular, dokumentrude, rækketabel,
> indsend — ligger ét sted i [`tools/domain_parts.py`](tools/domain_parts.py),
> mens **kompositionen** er hver apps egen. Skal kun den ene ændres, skrives
> ændringen i dens egen `build/`-mappe, ikke i de fælles dele.

Alle `.pa.yaml`-skærme er **genereret** af Python-builderne i den enkelte
apps `build/`-mappe. Byg alle fire og efterregn layoutet med:

```bash
python3 tools/build_all.py       # alle fem
python3 tools/build_all.py --app equipment
```

**Farver og breakpoints står ét sted for alle fire apps** og må ikke skrives
i en builder — byggeriet stopper, hvis nogen gør:

| Fil | Ejer |
|---|---|
| [`tools/design_tokens.py`](tools/design_tokens.py) | Alle farver, begge temaer. Mørk tilstand er den anden gren af samme `If`. Se [`docs/26-designtokens.md`](docs/26-designtokens.md) |
| [`tools/layout_tokens.py`](tools/layout_tokens.py) | Alle breakpoints. `LayoutContext` / `LayoutRank`. Se [`docs/27-layouttokens.md`](docs/27-layouttokens.md) |
| [`tools/build_helpers.py`](tools/build_helpers.py) `app_frame` / `top_bar` / `flow_row` | Rammen, bjælken og rækker der ombryder — ens i alle fire apps. Se [`docs/30-responsivt-layout.md`](docs/30-responsivt-layout.md) |

Arbejdsgangen står i [`.github/skills/canvas-build/SKILL.md`](.github/skills/canvas-build/SKILL.md).

Synkroniseringen til Power Apps Studio kan køres fra en terminal — samme
MCP-server som VS Code bruger, bare uden VS Code:

```powershell
python tools\canvas_mcp.py deploy --app vhplan
```

Se [`docs/21-mcp-uden-vscode.md`](docs/21-mcp-uden-vscode.md).

Dokumenterne nedenfor er oplægget bag VH-plan-delen: udvidelsen fra single
cycle til **strategiplaner** (SAP PM, IP42) med de pakker, der hører til
strategien.

Backend: SharePoint-lister. Frontend: Canvas app i Power Apps, med
HTML-komponenten brugt der hvor den faktisk hjælper.

> Status: **oplæg til review.** Intet er besluttet. Åbne spørgsmål står i
> `docs/01-loesningsoplaeg.md` §10 – især de to i `docs/05-implementeringsplan.md`
> fase 0, som ændrer omfanget markant.

## Læs i denne rækkefølge

| Fil | Indhold |
|---|---|
| [`docs/01-loesningsoplaeg.md`](docs/01-loesningsoplaeg.md) | Domæneforståelse, arkitektur, komponentvalg, åbne spørgsmål |
| [`docs/02-datamodel-sharepoint.md`](docs/02-datamodel-sharepoint.md) | Lister og kolonner, felt for felt |
| [`docs/03-canvas-app-design.md`](docs/03-canvas-app-design.md) | Skærme, komponenter, tilstand, gem/submit |
| [`docs/04-integration-sap.md`](docs/04-integration-sap.md) | Fire veje til SAP – kontrakt, idempotens, fejlhåndtering |
| [`docs/05-implementeringsplan.md`](docs/05-implementeringsplan.md) | Faser, risici, hvad der kan skæres væk |
| [`docs/06-excel-gui-scripting.md`](docs/06-excel-gui-scripting.md) | **Den valgte vej til SAP:** Excel + GUI Scripting |
| [`docs/07-landingsside.md`](docs/07-landingsside.md) | Landingsside for alle fem masterdata-domæner: hub vs. monolit, indekslisten, performanceregler |

## Kode og artefakter

| Sti | Indhold |
|---|---|
| `tools/canvas_mcp.py` | Byg, compile og synk til Studio via canvas-authoring MCP-serveren — uden VS Code |
| `tools/export_solution.ps1` | Hent solution BIO SAP ned som læsbare filer — flows, miljøvariabler, connection references |
| `powerfx/01-app-formulas.fx` | Named formulas, opstart, navigation |
| `powerfx/02-pakkematrix.fx` | Pakkematricen – nested gallery, toggle, genveje |
| `powerfx/03-validering.fx` | Regelsæt S1–S9 som én meddelelsestabel |
| `powerfx/04-submit-patch.fx` | Genoptageligt gem + JSON-snapshot ved submit |
| `powerfx/05-html-timeline.fx` | Formel, der bygger HTML-forfaldskalenderen |
| `sharepoint/provision/Provision-VHPlanLists.ps1` | Idempotent PnP-provisionering af alle lister |
| `sharepoint/provision/Provision-RequestIndex.ps1` | `MD_RequestIndex` — den fælles indeksliste bag landingssiden |
| `sharepoint/seed/*.csv` | Eksempelmasterdata: fire strategier med pakker |
| `schema/vhplan-request.schema.json` | Kontrakten mod SAP |
| `schema/example-strategy-request.json` | Udfyldt eksempel (kompressor, Z-MONTH) |
| `html/cycle-timeline-reference.html` | Referenceoutput – åbn i en browser |
| `excel/vba/*.bas` | Ni VBA-moduler: kilde, kontrakt, SAP GUI Scripting, batch |
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

# Listerne bag VH-plan-appen
.\sharepoint\provision\Provision-VHPlanLists.ps1 `
    -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>" `
    -SeedMasterData

# Indekslisten bag landingssiden. -AddSampleRows giver fire prøverækker,
# så hubben kan åbnes, før de fem submit-flows er bygget.
.\sharepoint\provision\Provision-RequestIndex.ps1 `
    -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>" `
    -AddSampleRows
```

Åbn derefter `html/cycle-timeline-reference.html` i en browser for at se,
hvad forfaldskalenderen skal ende med at vise.

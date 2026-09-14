# VH-plans app – strategiplaner og pakker

Oplæg til udvidelse af den eksisterende single cycle-app, så den også kan tage
imod indmeldinger af **strategiplaner** (SAP PM, IP42) med de pakker, der hører
til strategien.

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
.\sharepoint\provision\Provision-VHPlanLists.ps1 `
    -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>" `
    -SeedMasterData
```

Åbn derefter `html/cycle-timeline-reference.html` i en browser for at se,
hvad forfaldskalenderen skal ende med at vise.

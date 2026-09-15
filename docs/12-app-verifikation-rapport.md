# Verifikation af VH-plan appen mod de rigtige lister

Udført mod miljøet Bioenergy Solutions DEV (`environment_id`
`e0f8f822-d16a-e878-ba4e-fb42bc617e47`, `app_id`
`11fa8d90-868a-45a4-ba23-28f2cf0671a2`), branch
`claude/vh-plans-strategy-packages-lu8w70`.

## Trin 0-2

- **Datakilder:** Alle ti lister + flowet `BioSap-Integration-FunctionalLocations`
  tilføjet i Studio og gemt (bekræftet af bruger).
- **Byg:** `python tools/build_all.py` — grønt hele vejen. `App.pa.yaml`: 101
  linjer, 13 navngivne formler, 0 datahentninger i `OnStart`. Layout-tjek OK
  for begge apps.
- **Compile:** `canvas-authoring-compile_canvas` → **✓ Validation PASSED**, 3
  filer valideret.
- **Sync:** Lykkedes. Værktøjet nægtede at synke direkte fra
  `Maintenance Plan App/`, fordi mappen indeholder `.md`-filer og `build/`
  ud over `.pa.yaml`-filerne ("The target directory contains files that are
  not .pa.yaml files"). Løst ved at kopiere de tre `.pa.yaml`-filer til en
  midlertidig undermappe, compile+sync derfra, og slette undermappen bagefter.
  Ingen kildefiler blev ændret.
- **Data row limit:** Sat til 2000 i Indstillinger → Generelt (bekræftet af
  bruger).

## App checker — ordret, 9 fund

- **2× [Medium] [Performance] `App.OnStart`: "Collection is initialized but
  never updated"** (regel `CollectingReadOnlyTable`). Gælder
  `colVhpYesNoOptions` og `colVhpPlanTypeOptions` — de to konstant-tabeller
  docs/11 selv beskriver som bevidst valgt som synlige konstanter frem for
  navngivne formler. **Dette er reelt en advarsel om `App.OnStart`, så
  kravet "der må ikke være advarsler om App.OnStart" er ikke opfyldt.**
- 5× [Medium] [Performance] `ForAllWithMutation` på `btnVhpCopyItem.OnSelect`,
  `btnVhpPickerAddSelected.OnSelect`, `btnVhpPkgHierarchy.OnSelect`,
  `btnVhpSaveItem.OnSelect`, `chkVhpPickerSelectAll.OnCheck`/`OnUncheck`.
- 1× [Medium] [Performance] `ScreenHasManyControls` på `ScreenVhPlan` (282
  kontroller).

**Accessibility:** ✓ Ingen fejl fundet.

## Manuel test (live i browser)

| # | Punkt | Resultat |
|---|---|---|
| 1 | Opstart < 2 sek | Ikke pålideligt målt — ca. 9-10 sek i mine logs, men målingen er forurenet af værktøjs-roundtrips og et samtykke-dialog-klik. Bør gentages med et reelt stopur. |
| 2 | Ingen App.OnStart-advarsler | ❌ Fejler — se de 2 advarsler ovenfor |
| 3 | Statuslinje: 6/53(52)/53 | ✅ Ordret: *"Data: 6 standardarbejdsplaner, 53 strategier (52 uden pakker), 53 arbejdscentre."* |
| 4 | Værk-dropdown: 6 værdier | ✅ ASV, AVV, HEV, KYV, SKV, SSV |
| 5 | Sorteringsfelt: 28 værdier | ✅ Talt og bekræftet |
| 6 | Call Horizon: 16 værdier | ✅ Talt og bekræftet |
| 7 | Enhed: H, DAY, WK, MON, YR | ✅ Bekræftet |
| 8 | Arbejdscenter uden værk = alle 53 | ✅ Bekræftet i koden: `If(IsBlank(varVhpPlan.Plant), colVhpMainWorkCenters, Filter(colVhpMainWorkCenters, Plant = varVhpPlan.Plant))` |
| 9 | Værk SSV → kun SSV, ingen mellemrum | ✅ Live: 7 værdier (SSVAP, SSVBRÆND, SSVPROD, SSVSERVE, SSVSERVI, SSVSERVM, SSVSUP) |
| 10 | Operationer fra MD_StandardTaskOperations, nummereret | ✅ Vist som 0010, 0020 … (4-cifret SAP-format) |
| 11 | SSV = 32 operationer | ✅ Ordret: *"Number of items in Tasklist line picker: 32"*, og *"Added 32 operation line(s) from tasklist."* |
| 12 | 53 strategier, 52 mærket | ✅ Talt: 53 i alt, kun 128 uden "(pakker mangler)" |
| 13 | Strategi 101: matrix IKKE tegnet, forklaring vist | ⚠️ Delvist — forklaringsteksten vises korrekt ordret: *"Strategi 101 har ingen pakker i MD_StrategyPackage endnu, saa der er ikke noget at tildele. Pakkerne hentes fra SAP (IP11). Planen kan godt gemmes og sendes uden pakketildeling."* **Men** knapperne Hierarki-udfyld/Alle pakker/Ryd pakker forblev synlige og aktive samtidig — se fund nedenfor. |
| 14 | Strategi 128: matrix med 3 kolonner 1Y/2Y/3Y | ✅ Live bekræftet, 32 operationsrækker × 3 pakkekolonner |
| 15 | Kryds bevares ved skift af item | Ikke testet — testen blev stoppet af bruger før dette punkt |
| 16 | Hierarki-udfyld grå + forklaringslinje | ❌ Se fund nedenfor |
| 17 | Alle pakker sætter kryds i alle 3 | ✅ Ordret: *"Alle pakker markeret paa alle operationer."* Advarslerne forsvandt bagefter (*"Alle operationer er tildelt mindst een pakke, og alle pakker har operationer."*) |
| 18 | FL-søgning: 7 tegn, ét flow-kald | Ikke testet live, men bekræftet i koden (`build_flsearch.py`): Timer poller hver 500ms, kalder kun flowet når `Len(q) = 7` og teksten er ny |
| 19 | Layout ved ~900px | Ikke testet live, men `check_layout.py` tester automatisk 420-1920px og var grøn |

## To fund i pakkematrix-logikken (punkt 13 og 16)

**Fund 1 (punkt 13):** For en strategi uden pakker (fx 101) forblev
handlingsknapperne `Hierarki-udfyld`, `Alle pakker` og `Ryd pakker` synlige og
aktive samtidig med tomtilstands-forklaringen. Ifølge docs/11 skal `CAN_DRAW`
styre matrix, handlingsknapper og tomtilstand samlet, så de aldrig vises
samtidig. Årsag fundet: i `Maintenance Plan App/build/build_strategy.py`
sættes `actionRow.vis = IfError(CAN_DRAW, false)`, men i den udskrevne
`ScreenVhPlan.pa.yaml` er der **ingen `Visible`-egenskab** på
`conVhpPkgActionRow` overhovedet — tildelingen ser ikke ud til at blive
skrevet igennem til YAML'en.

**Fund 2 (punkt 16):** Knappen `Hierarki-udfyld` var ikke effektivt
deaktiveret for strategi 128 (`Hierarchical = "Ikke afklaret"`). Test: satte
kryds i pakke `1Y` på operation 0010, klikkede `Hierarki-udfyld` — knappen
udførte handlingen og satte også `2Y` og `3Y` på samme operation. Det er
præcis det scenarie, docs/11 advarer imod ("en treårig opgave ville blive
årlig"). Forklaringslinjen under knappen ("Hierarki-udfyld er slået fra: det
er ikke afklaret …") blev heller ikke fundet i den fangede side.
**Forbehold:** klikket var et automatiseret klik via
tilgængeligheds-referencer, som i nogle tilfælde kan omgå en reel
knap-deaktivering, som et fysisk museklik ikke ville kunne. Bør bekræftes med
en rigtig mus, men samme mønster som Fund 1 (en `Visible`/`DisplayMode`-formel
i builderen, der ikke ser ud til at blive håndhævet i den synkede app) gør
det sandsynligt, at det er en reel fejl.

Ingen af disse blev rettet — opgaven var verifikation, ikke rettelse af
`build/*.py`.

## Data og sideeffekter

Alt testarbejde (plan, item, operationer, pakkekryds) skete kun i appens
lokale arbejdssamlinger (`colVhpItems`, `colVhpOperations` osv.), som pr.
design ikke skriver til `MaintenancePlans`/`MaintenanceItems`/`TaskListMain`.
Ingen SharePoint-data eller -lister blev ændret. `Hierarchical` blev ikke sat
på nogen strategier (alle 53 står stadig som "Ikke afklaret").

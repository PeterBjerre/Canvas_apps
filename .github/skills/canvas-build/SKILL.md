---
name: canvas-build
description: Arbejdsgang for canvas apperne i dette repo — "Maintenance Plan App" (VH-plan) og "Masterdata Hub" (landingssiden). Brug den ved ENHVER ændring af en skærm, App.OnStart, layout, Power Fx-formler, kontroller eller datakilder. Ret builderne i Python, generér .pa.yaml, kør layout-tjekket, og synkronisér først derefter til Power Apps Studio.
---

# Canvas apps: byg og deploy

## Den ene regel

`.pa.yaml`-filerne er **genereret**. `ScreenVhPlan.pa.yaml` er godt 9.700
linjer, `ScreenMdHub.pa.yaml` godt 3.000. `App.pa.yaml` er også genereret i
begge apps. Retter du direkte i dem, er ændringen væk, næste gang nogen
kører builderen — og du efterlader en fil, der ikke længere matcher sin kilde.

**Ret i `build/*.py`. Altid.**

Det gælder også, når ændringen er lille, og når du har travlt. Der findes
ingen undtagelse.

## To apps — hver med sin selvstændige build-mappe

| App | Mappe | Skærm | Byg |
|---|---|---|---|
| VH-plan | `Maintenance Plan App/` | `ScreenVhPlan.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |
| Landingsside | `Masterdata Hub/` | `ScreenMdHub.pa.yaml` | `generate_hub_onstart.py` + `assemble_hub.py` |

Hver build-mappe er **selvbærende**. Der er ingen `shared/`-mappe, og der
må ikke laves en: Power Apps' egen VS Code-værktøjskæde arbejder pr.
app-mappe, og et delt modul uden for mappen blev fjernet igen af den.

Tre filer er derfor **kopieret ordret** ind i begge build-mapper:

    gen_screen.py      DSL, stylingkonstanter, højde-algebra
    build_helpers.py   byggeklodser: card, group, button_row, inputs, combobox
    check_layout.py    layout-tjekket

**Retter du i en af de tre, skal du kopiere filen til den anden app med det
samme** og køre begge byg. `tools/build_all.py` nægter at bygge, hvis de er
gledet fra hinanden, og skriver hvilken app der har den nyest rettede udgave.

```bash
cp "Maintenance Plan App/build/build_helpers.py" "Masterdata Hub/build/"
```

## Arbejdsgangen

Alt på én gang — bruger denne, medmindre du har en grund til andet:

```bash
python3 tools/build_all.py
```

Den tjekker først, at de tre kopierede filer er ens, bygger derefter begge
apps og kører begge layout-tjek. Alt skal være grønt, før du synkroniserer.

Én app ad gangen:

```bash
cd "Maintenance Plan App/build"
python3 generate_app_onstart.py   # -> ../App.pa.yaml
python3 assemble_screen.py        # -> ../ScreenVhPlan.pa.yaml
python3 check_layout.py           # finder selv skærmen i mappen ovenfor
```

Kør altid begge generatorer for den app, du har rettet — en ændring i
`OnStart` og en i skærmen hænger ofte sammen.

Er `check_layout.py` rød, så **ret i builderen og kør igen**. Lap aldrig
YAML'en for at få tjekket grønt — så er det tjekket, du har slået fra, ikke
fejlen, du har rettet.

## Hvem ejer hvad — VH-plan

Ret i den builder, der ejer området — ikke i en tilfældig fil, der også
nævner kontrollen.

| Builder | Ejer |
|---|---|
| `sp_config.py` | **Datakilde-kontrakten**: hvilke SharePoint-lister og kolonner appen læser. Ret HER, ikke i formlerne |
| `gen_screen.py` | Kontroltræ-DSL, stylingkonstanter, **højde-algebra** (`stack_height`, `row_height`) |
| `build_helpers.py` | Byggeklodser: `card`, `group`, `field_cell`, `button_row`, inputs, `combobox` |
| `build_hero.py` | Hero, procesindikator, **Validate** og **Export JSON** |
| `build_plan_header.py` | Planhoved, plantype, strategivalg, `section_header` |
| `build_items.py` | Items-skinne, Item Editor, FL-felt, objektliste |
| `build_flsearch.py` | **Flow-kontrakten for FL-søgning** — outputnavn og feltnavne ligger kun her |
| `build_tasklist.py` | Tasklist, operationstabel, dispatch, mailknap |
| `build_strategy.py` | Pakkematricen (strategiplaner) |
| `build_modal.py` | Tasklist-picker |
| `build_save.py` | **Gemning i SharePoint** — de fire lister, nøglerne, og hvad der bevidst ikke udfyldes |
| `build_load.py` | **Indlæsning af en gemt plan** — dyblinket fra hubben (`?reqid=`), og hvilke felter der kan læses tilbage |
| `assemble_screen.py` | Samler skærmen → `../ScreenVhPlan.pa.yaml` |
| `generate_app_onstart.py` | `App.Formulas` + `App.OnStart` → `../App.pa.yaml` |

Disse fem er **historiske og bruges ikke**: `build_diag_screen.py`,
`build_vhplan_screen.py`, `gen_options.py`, `gen_tasklists.py`,
`rename_collections.py`. Ret ikke i dem, og lad dig ikke forvirre af dem.

## Hvem ejer hvad — Masterdata Hub

| Builder | Ejer |
|---|---|
| `hub_config.py` | **Al tilpasning**: listenavn, de fem domæner (navn, farve, app-URL) og statusordforrådet |
| `build_hub.py` | Toplinje, domænefliser, filtre, listen |
| `assemble_hub.py` | Samler skærmen → `../ScreenMdHub.pa.yaml` |
| `generate_hub_onstart.py` | `App.OnStart` → `../App.pa.yaml` |

Skal en ny domæneapp kobles på, eller skal en status skifte farve eller
tekst, så er svaret **altid `hub_config.py`** og aldrig `build_hub.py`.
Når en satellit-app er bygget, indsættes dens play-URL i `DOMAINS`, og
flisen skifter selv fra "Kommer snart" til "Opret ny".

### Landingssidens to ufravigelige ydelseskrav

1. **Én datakilde.** Skærmen læser kun `MD_RequestIndex`. Den må aldrig
   læse de fem domænelister og flette dem i klienten — det er fem
   forbindelser og en fletning, der ikke kan delegeres.
2. **Ingen datahentning i `App.OnStart`.** OnStart betales af hver bruger
   hver gang. Galleriet binder direkte til sit filter, og flisernes tal
   tælles på det samme, allerede afgrænsede sæt.

Begge grene af `SCOPE` skal blive ved at være delegerbare: `RequesterEmail`
er indekseret **tekst** (ikke en Person-kolonne), og køen filtrerer på det
indekserede boolske `IsOpen` — ikke på en række OR'ede statusværdier.

## Hvad check_layout.py fanger

Canvas-layout kan ikke renderes uden for Studio, så det regnes efter i
stedet, for skærmbredder fra 420 til 1920 px og for 0–8 items og 0–12
operationer:

1. Ingen `Height`-formel refererer en anden kontrols `.Height`
2. Lodrette containere er høje nok til børn + gaps + egen polstring
3. Vandrette containere er høje nok til deres højeste barn
4. Faste bredder i en række overstiger ikke rækkens bredde
5. HTML-tabeloverskrifter flugter med kontrollerne i rækken
6. Balancerede parenteser og anførselstegn i alle formler
7. Ingen formel refererer en kontrol, der ikke findes
8. Enhver `col*`, skærmen bruger, findes i `App.pa.yaml` — som navngiven
   formel eller som `ClearCollect`
9. Ingen **lodret** container har et barn med `FillPortions <> 0`

Punkt 7 fanger den klassiske: du sletter en kontrol og glemmer en
`Reset()` på den et andet sted. Det ville ellers først vælte i compile.

Punkt 8 fanger den samme fejl for data: flytter du en opslagsliste fra en
hårdkodet tabel til en navngiven formel, bliver referencerne let hængende.

Et barn med `Visible = false` regnes ikke med i højden — præcis som
AutoLayout gør det. Kun det *litterale* `false`; en `Visible`-formel kan jo
være sand, og så skal pladsen være der.

## Synkronisér til Studio

Uden agent, i en terminal — samme MCP-server, uden credits:

```powershell
python tools\canvas_mcp.py deploy --app vhplan
```

Den bygger, forbinder, compiler, synkroniserer og kører begge tjek i den
rigtige rækkefølge. Studio-fanen skal være åben med coauthoring slået til.
Hele fremgangsmåden står i `docs/21-mcp-uden-vscode.md`.

Kalder du værktøjerne i hånden, er rækkefølgen ikke valgfri. `directoryPath`
er den lokale sti til **app-mappen** (ikke `build/`).

```
canvas-authoring-connect
    environment_id = e0f8f822-d16a-e878-ba4e-fb42bc617e47
    app_id         = <appens eget id>

canvas-authoring-compile_canvas   directoryPath = <sti til app-mappen>
canvas-authoring-sync_canvas      directoryPath = <sti til app-mappen>
canvas-authoring-get_appchecker_errors
canvas-authoring-get_accessibility_errors
```

| App | `app_id` |
|---|---|
| VH-plan | `11fa8d90-868a-45a4-ba23-28f2cf0671a2` |
| Masterdata Hub | *(udfyldes når appen er oprettet i Studio)* |

**Compile før sync.** Fejler compile, så stop — synk ikke en app, der ikke
kan oversættes. Det er `compile_canvas`, der sender YAML'en ind i den åbne
coauthoring-session; `sync_canvas` skriver bagefter serverens tilstand
**ned** i mappen igen. Peger du den på app-mappen, overskriver den de
genererede kilder — derfor arbejder `tools/canvas_mcp.py` på en kopi i
`.canvas-deploy/`.

## Efter synk: skriv ikke Studios YAML tilbage

Power Apps normaliserer egenskaber, den betragter som standardværdier, væk.
Eksporterer du YAML'en tilbage, mangler den bl.a. `FillPortions` på nogle
containere, `LayoutAlignItems` på containere med `LayoutWrap = true`, og
eksplicitte `Height` på nogle blad-kontroller.

**Det er normalt.** Det er ikke en fejl, og det skal ikke rettes. Kopiér
aldrig den normaliserede YAML tilbage over kildefilerne — så mister du de
egenskaber, builderne bevidst sætter.

## Otte ting der aldrig må regressere

1. **Ingen `Height`-formel må referere en anden kontrol.** I en
   AutoLayout-container sætter forælderen børnenes størrelse, så en forælder
   der læser barnets `.Height`, læser sin egen udregning tilbage. Det gav
   både kaskade-vækst og klippede kort. Højder regnes i Python ud fra
   konstanter, `App.Width` og `CountRows()`.
2. **`LayoutAlignItems` virker ikke på en container med `LayoutWrap = true`.**
   Platformen fjerner egenskaben igen. Forsøg ikke at løse layoutproblemer
   med den dér.
3. **`FillPortions` fordeler plads LANGS containerens retning** — bredde i en
   vandret, **højde** i en lodret. Da hver containers højde her regnes ud af
   dens børn, er der ingen overskydende højde at fordele: et barn med
   `FillPortions <> 0` i en lodret container vokser, så snart forælderen selv
   bliver strakt, og så passer den udregnede højde ikke længere til det, der
   tegnes. Flytter du en celle fra en gitterrække ned i en kolonne, så **sæt
   `fill_portions=0`**. Check 9 håndhæver det.
4. **Stylingen skal være uændret.** Farver, radier, skriftstørrelser og
   polstring matcher Materialer-appen, og de to apps skal blive ved at ligne
   hinanden.
5. **Brug konstruktioner, der allerede findes i skærmen.** `ModernDropdown`,
   `Classic/ComboBox` til søg-og-vælg, gallery med `ModernCheckbox`, vandret
   gallery til dynamiske kolonner. Hver ubevist konstruktion i dette projekt
   har kostet en deploy-runde.
6. **`ctrl.vis` skriver `Visible` igennem.** Sæt synlighed med `visible=` i
   helperen eller `ctrl.vis = ...` — begge skriver egenskaben *og* fortæller
   højde-algebraen, at barnet kan være skjult. Sæt aldrig `props["Visible"]`
   direkte: så regner forælderen med plads til noget, der ikke er der.
7. **Ingen datahentning i `App.OnStart`.** Opslagslister bindes med
   **navngivne formler** (`App.Formulas`), som evalueres dovent og caches.
   `OnStart` betales af hver bruger hver gang; en navngiven formel gør ikke.
   Kun samlinger, appen **skriver** til, hører hjemme i `OnStart` — og der
   kun som tomt skema.

   Den ene undtagelse er dyblinket (`build_load.py`): åbnes appen med
   `?reqid=`, hentes netop den plan. Den er pakket ind i
   `If(IsBlank(Param("reqid")), ...)`, så alle andre betaler et
   `Collect` af én lokal record og ingen listeopslag.
8. **Padding tælles med i højden.** Det gør `stack_height()` automatisk —
   omgå den ikke ved at sætte `height=` manuelt på et kort.

### Brug ikke `Classic/ComboBox` til søgning

Den blev prøvet til FL-feltet, fordi den som den eneste eksponerer
`SearchText` og dermed muliggør søg-mens-du-skriver. **Det virkede ikke.**
Flowet returnerede 819 Functional Locations, beskeden sagde det — og
dropdownen var tom. Comboboksens indbyggede søgefiltrering viste ingen af de
rækker, den havde fået, og det lag kan ikke inspiceres udefra.

FL-feltet er nu **søgefelt + søgeknap + almindelig `ModernDropdown`**, hvor
dropdownen viser præcis det, samlingen indeholder. Objektlisten er et
**galleri med `ModernCheckbox`** — multi-select uden combobox, og samme
konstruktion som tasklist-pickeren og pakkematricen allerede bruger.

Det er også mere ensartet: alle felter i Item Editor ser nu ens ud.

Mønsteret er værd at huske ud over denne app: **når data er der, men ikke
vises, så mistænk kontrollens eget filter før dine egne formler.**

## Power Fx binder på VISNINGSNAVN

Det gælder hver eneste SharePoint-kolonne. Tre gange i dette projekt har den
fælde kostet en runde:

| Intern kolonne | Power Fx ser |
|---|---|
| `MD_RequestIndex.Title` | `RequestNo` |
| `MD_Strategy.Title` | `StrategyKey` |
| `MaintenancePlans.CallHorizon0` | `CallHorizon` |

Slår du en ny kolonne op, så tjek `sharepoint/inspect/out/schema.md` — den
fremhæver hver kolonne, hvor de to navne er forskellige. Navnene hører hjemme
i `build/sp_config.py`, ikke ude i formlerne.

## Datakilder skal findes i appen først

En formel, der kalder et flow eller en liste, fejler i compile, hvis kilden
ikke er tilføjet appen som datakilde. Det kan ikke gøres fra YAML.

Bruger din ændring et nyt flow, en ny liste eller en ny connector, så **bed
brugeren tilføje den i Studio først**, og gå ikke videre før det er bekræftet.

- VH-plan bruger flowet `BioSapIntegrationFunctionalLocations`. Svarer flowet
  anderledes end forventet, rettes de fire konstanter i `build_flsearch.py` —
  ikke formlerne ude i skærmen.
- Masterdata Hub bruger SharePoint-listen `MD_RequestIndex`. Den oprettes med
  `sharepoint/provision/Provision-RequestIndex.ps1`.

## Studio cacher datakildens skema

Power Apps gemmer kolonnenavne og -typer, **som de var, da listen blev
tilføjet som datakilde**. Omdøber eller ændrer du en kolonne i SharePoint
bagefter, arbejder appen videre på den gamle udgave.

Symptomet er en compile-fejl, der modsiger virkeligheden:

```
The type of this argument 'CallHorizon' does not match the expected
type 'Record'. Found type 'Number'.
```

— mens `schema.md` klart siger, at `CallHorizon` er et `Number`. Studio
huskede den gamle kolonne af samme navn, som var en `Choice`.

**Fix:** fjern listen som datakilde i Studio, tilføj den igen, og **gem**.
Ingen kodeændring hjælper, og `check_datasources.py` kan ikke se det — det
sammenholder koden med SharePoint, ikke med Studios hukommelse.

Sker det efter en omdøbning, så genkør også
`Export-ListSchema.ps1`, så udtrækket og virkeligheden følges ad.

## Når compile fejler

1. Læs fejlen. Den peger som regel på et kontrolnavn eller en egenskab.
2. Er det en **ukendt kontrol** → er datakilden tilføjet? Findes kontrollen
   stadig i builderen?
3. Er det en **ukendt egenskab** → brug `canvas-authoring-describe_control`
   til at se, hvad kontroltypen faktisk understøtter. Gæt ikke.
4. Ret i builderen, kør byg og `check_layout.py`, synk igen.

Lap aldrig YAML'en for at komme forbi en compile-fejl. Den kommer tilbage
ved næste build.

## Linjeskift

`.gitattributes` normaliserer alt til LF. Rører du filerne på Windows, så
lad være med at slå det fra — uden det gav et skift mellem VS Code og
byggescripterne en diff på hele filen, hvor kun få linjer var ændret.

## PowerShell: ASCII i kildekoden, BOM på filen

`.ps1`-filer køres af **Windows PowerShell 5.1**, som antager Windows-1252,
når filen ikke har en BOM. Et UTF-8 em-dash (`—`, bytes `E2 80 94`) læses så
som tre tegn — hvoraf det ene er et `"`, der **åbner en streng**. Resten af
filen parses som tekst, og fejlen dukker op et helt andet sted end tegnet
står:

```
Expressions are only allowed as the first element of a pipeline
```

To regler, begge håndhævet af `tools/check_ps1.py` (som `tools/build_all.py`
kører først):

1. `.ps1`-filer gemmes som **UTF-8 med BOM**.
2. Kildekoden er alligevel **ren ASCII** — brug `ae`/`oe`/`aa` og `-` i
   stedet for `æ`/`ø`/`å` og `—`.

Rigtige danske bogstaver hører hjemme i det, scripterne **skriver ud**
(`Write-Host`, genereret markdown), ikke i selve filen.

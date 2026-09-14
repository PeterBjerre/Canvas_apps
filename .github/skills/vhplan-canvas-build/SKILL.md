---
name: vhplan-canvas-build
description: Arbejdsgang for canvas apperne i dette repo — "Maintenance Plan App" (VH-plan) og "Masterdata Hub" (landingssiden). Brug den ved ENHVER ændring af en skærm, App.OnStart, layout, Power Fx-formler, kontroller eller datakilder. Ret builderne i Python, generér .pa.yaml, kør layout-tjekket, og synkronisér først derefter til Power Apps Studio.
---

# Canvas apps: byg og deploy

## Den ene regel

`ScreenVhPlan.pa.yaml` er **9.700 linjer genereret kode**. `App.pa.yaml` er
også genereret. Retter du direkte i dem, er ændringen væk, næste gang nogen
kører builderen — og du efterlader en fil, der ikke længere matcher sin kilde.

**Ret i `build/*.py`. Altid.**

Det gælder også, når ændringen er lille, og når du har travlt. Der findes
ingen undtagelse.

## To apps, samme arbejdsgang

| App | Mappe | Byg |
|---|---|---|
| VH-plan | `Maintenance Plan App/` | `generate_app_onstart.py` + `assemble_screen.py` |
| Landingsside | `Masterdata Hub/` | `generate_hub_onstart.py` + `assemble_hub.py` |

DSL, højde-algebra, byggeklodser og layout-tjek er **fælles** og ligger i
`shared/canvas/`. Retter du dér, rammer det begge apps — kør derfor begge
byg og begge layout-tjek bagefter.

## Hvem ejer hvad i VH-plan

Ret i den builder, der ejer området — ikke i en tilfældig fil, der også
nævner kontrollen.

| Builder | Ejer |
|---|---|
| `gen_screen.py` | Kontroltræ-DSL, stylingkonstanter, **højde-algebra** (`stack_height`, `row_height`) |
| `build_helpers.py` | Genbrugelige byggeklodser: `card`, `group`, `field_cell`, `button_row`, inputs |
| `build_hero.py` | Hero, procesindikator, **Validate** og **Export JSON** |
| `build_plan_header.py` | Planhoved, plantype, strategivalg, `section_header` |
| `build_items.py` | Items-skinne, Item Editor, FL-felt, objektliste |
| `build_flsearch.py` | **Flow-kontrakten for FL-søgning** — outputnavn og feltnavne ligger kun her |
| `build_tasklist.py` | Tasklist, operationstabel, dispatch, mailknap |
| `build_strategy.py` | Pakkematricen (strategiplaner) |
| `build_modal.py` | Tasklist-picker |
| `assemble_screen.py` | Samler skærmen → `../ScreenVhPlan.pa.yaml` |
| `generate_app_onstart.py` | `App.OnStart` → `../App.pa.yaml` |
| `../../shared/canvas/` | **Fælles**: DSL, højde-algebra, byggeklodser, layout-tjek |

Disse fem er **historiske og bruges ikke**: `build_diag_screen.py`,
`build_vhplan_screen.py`, `gen_options.py`, `gen_tasklists.py`,
`rename_collections.py`. Ret ikke i dem, og lad dig ikke forvirre af dem.

## Arbejdsgangen

```bash
# VH-plan
cd "Maintenance Plan App/build"
python3 generate_app_onstart.py   # -> ../App.pa.yaml
python3 assemble_screen.py        # -> ../ScreenVhPlan.pa.yaml
python3 ../../shared/canvas/check_layout.py ../ScreenVhPlan.pa.yaml

# Landingsside
cd "Masterdata Hub/build"
python3 generate_hub_onstart.py   # -> ../App.pa.yaml
python3 assemble_hub.py           # -> ../ScreenMdHub.pa.yaml
python3 ../../shared/canvas/check_layout.py ../ScreenMdHub.pa.yaml
```

Kør altid begge generatorer for den app, du har rettet — en ændring i
`OnStart` og en i skærmen hænger ofte sammen. Layout-tjekket **skal** være
grønt, før du synkroniserer.

Er `check_layout.py` rød, så **ret i builderen og kør igen**. Lap aldrig
YAML'en for at få tjekket grønt — så er det tjekket, du har slået fra, ikke
fejlen, du har rettet.

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

Punkt 7 fanger den klassiske: du sletter en kontrol og glemmer en
`Reset()` på den et andet sted. Det ville ellers først vælte i compile.

## Synkronisér til Studio

Rækkefølgen er ikke valgfri. `directoryPath` er den lokale sti til mappen
`Maintenance Plan App`.

```
canvas-authoring-connect
    environment_id = e0f8f822-d16a-e878-ba4e-fb42bc617e47
    app_id         = 11fa8d90-868a-45a4-ba23-28f2cf0671a2

canvas-authoring-compile_canvas   directoryPath = <sti>
canvas-authoring-sync_canvas      directoryPath = <sti>
canvas-authoring-get_appchecker_errors
canvas-authoring-get_accessibility_errors
```

**Compile før sync.** Fejler compile, så stop — synk ikke en app, der ikke
kan oversættes.

## Efter synk: skriv ikke Studios YAML tilbage

Power Apps normaliserer egenskaber, den betragter som standardværdier, væk.
Eksporterer du YAML'en tilbage, mangler den bl.a. `FillPortions` på nogle
containere, `LayoutAlignItems` på containere med `LayoutWrap = true`, og
eksplicitte `Height` på nogle blad-kontroller.

**Det er normalt.** Det er ikke en fejl, og det skal ikke rettes. Kopiér
aldrig den normaliserede YAML tilbage over kildefilerne — så mister du de
egenskaber, builderne bevidst sætter.

## Fem ting der aldrig må regressere

1. **Ingen `Height`-formel må referere en anden kontrol.** I en
   AutoLayout-container sætter forælderen børnenes størrelse, så en forælder
   der læser barnets `.Height`, læser sin egen udregning tilbage. Det gav
   både kaskade-vækst og klippede kort. Højder regnes i Python ud fra
   konstanter, `App.Width` og `CountRows()`.
2. **`LayoutAlignItems` virker ikke på en container med `LayoutWrap = true`.**
   Platformen fjerner egenskaben igen. Forsøg ikke at løse layoutproblemer
   med den dér.
3. **Stylingen skal være uændret.** Farver, radier, skriftstørrelser og
   polstring matcher Materialer-appen. Alle oprindelige kontroller er
   bevaret med uændrede style-egenskaber.
4. **Brug konstruktioner, der allerede findes i skærmen.** `ModernDropdown`,
   gallery med `ModernCheckbox`, vandret gallery til dynamiske kolonner. Hver
   ubevist konstruktion i dette projekt har kostet en deploy-runde.
5. **Padding tælles med i højden.** Det gør `stack_height()` automatisk —
   omgå den ikke ved at sætte `height=` manuelt på et kort.

## Datakilder skal findes i appen først

En formel, der kalder et flow, fejler i compile, hvis flowet ikke er tilføjet
appen som datakilde. Det kan ikke gøres fra YAML.

Bruger din ændring et nyt flow eller en ny connector, så **bed brugeren
tilføje den i Studio først**, og gå ikke videre før det er bekræftet.

FL-søgningen bruger `BioSapIntegrationFunctionalLocations`. Svarer flowet
anderledes end forventet, rettes de fire konstanter i `build_flsearch.py` —
ikke formlerne ude i skærmen.

## Når compile fejler

1. Læs fejlen. Den peger som regel på et kontrolnavn eller en egenskab.
2. Er det en **ukendt kontrol** → er datakilden tilføjet? Findes kontrollen
   stadig i builderen?
3. Er det en **ukendt egenskab** → brug `canvas-authoring-describe_control`
   til at se, hvad kontroltypen faktisk understøtter. Gæt ikke.
4. Ret i builderen, kør `assemble_screen.py` og `check_layout.py`, synk igen.

Lap aldrig YAML'en for at komme forbi en compile-fejl. Den kommer tilbage
ved næste build.

---
name: canvas-build
description: Arbejdsgang for de FIRE canvas apps i dette repo — "Maintenance Plan App" (VH-plan), "Masterdata Hub" (landingssiden), "Equipment App" (Equipments) og "Material App" (Materials). Brug den ved ENHVER ændring af en skærm, App.OnStart, layout, farver, breakpoints, Power Fx-formler, kontroller eller datakilder. Ret builderne i Python, generér .pa.yaml, kør layout-tjekket, og synkronisér først derefter til Power Apps Studio.
---

# Canvas apps: byg og deploy

## Den ene regel

`.pa.yaml`-filerne er **genereret**. `ScreenVhPlan.pa.yaml` er godt 15.000
linjer, `ScreenEquipment.pa.yaml` og `ScreenMaterial.pa.yaml` knap 6.000 hver,
`ScreenMdHub.pa.yaml` godt 3.000. `App.pa.yaml` er også genereret i alle fire. Retter du direkte i dem, er ændringen væk, næste gang nogen
kører builderen — og du efterlader en fil, der ikke længere matcher sin kilde.

**Ret i `build/*.py`. Altid.**

Det gælder også, når ændringen er lille, og når du har travlt. Der findes
ingen undtagelse.

## Den anden regel: farver er tokens, ikke tal

**Ingen builder må indeholde en farve.** Hverken `RGBA(...)` eller
`#rrggbb`. `tools/build_all.py` nægter at bygge, hvis nogen skriver en, og
den læser syntakstræet, så en kommentar må gerne nævne en farve.

Alle 31 farver står i `tools/design_tokens.py` — ét sted for alle fire
apps, i to udgaver. Builderne skriver en **tokenreference**:

```python
from gen_screen import C_CARD_BG, C_TITLE      # peger paa tokens
...
"Fill": C_CARD_BG                               # -> =C.'bg-card'
```

`C` er en navngiven formel i `App.Formulas`:

```
C = If(!darkModeEnabled, { ...lyse vaerdier... }, { ...moerke... });
```

Derfor er **mørk tilstand ikke en funktion**. Skifter `darkModeEnabled`,
genberegner Power Fx formlen, og hver kontrol, der læser
`C.'et-eller-andet'`, skifter med. Ingen kontrol ved, at mørk tilstand
findes.

Skal en farve ændres, rettes den **i begge temaer** i
`tools/design_tokens.py`, og alle fire apps skifter sammen.

Skal en farve bruges inde i en **HTML-streng** (`HtmlViewer`), så brug
`design_tokens.ref_hex()` — hex-værdierne afledes af de samme tokens og
kan derfor ikke glide fra dem.

Temaknappen er `build_helpers.theme_button()` og er **den samme kontrol i
alle fire apps**. Byg ikke en ny.

Det hele står i `docs/26-designtokens.md`, inkl. hvorfor farverne ikke kan
ligge i miljøvariabler, og hvordan valget huskes.

## Den tredje regel: breakpoints er tokens, ikke tal

**Ingen skærm må sammenligne `App.Width` med et tal.** `check_layout.py`
regel 8c stopper byggeriet. Aritmetik er fint — `SHELL_W` *er*
`(App.Width - 64)` — det er kun **sammenligningen**, der er en beslutning.

Alle breakpoints står i `tools/layout_tokens.py` og bliver til to
navngivne formler i `App.Formulas`:

```
LayoutContext = "Mobile" | "Tablet" | "Desktop" | "Wide"   (læses)
LayoutRank    =    1     |    2     |     3     |   4      (sammenlignes)
```

Tiers: Mobile 0, Tablet 720, Desktop **1024**, Wide 1600.

```python
from layout_tokens import below, if_below, at_least, fits, TWO_COL_MIN

TILE_W = if_below("Desktop", f"({SHELL_W} - 10) / 2", f"({SHELL_W} - 40) / 5")
```

### To slags grænser — vælg den rigtige

| Spørgsmålet | Værktøj |
|---|---|
| "Hvor stor er **skærmen**?" — fem fliser eller to, hero ved siden af eller ovenpå | `below("Desktop")` / `if_below()` / `at_least()` |
| "Er der plads i **denne kasse**?" — et 600 px kort stabler sine felter også på en 4K-skærm | `fits(container_w, needs, narrow, wide)` |

`fits()`' `needs` skal **regnes ud af indholdet**, ikke skrives af.
Topbjælken havde `900` skrevet i sig, mens højresiden fyldte 440 — da
temaknappen gjorde højresiden 542 bred, fulgte de 900 ikke med, og bjælken
ville have ombrudt på enhver skærmbredde.

### Tal, der skal være ens, skal komme fra det samme sted

Fire steder i repoet skulle to-tre tal passe sammen, og intet sagde det:
splittets højde vs. skinnens bredde vs. `EDITOR_W`; flisernes bredde vs.
deres beholders højde; knaprækkens bredde vs. venstresidens reservation
(to steder). Knapperækkerne regnes nu af `HERO_BTNS` / `BAR_RIGHT`, og
builderen **efterprøver sig selv** — tilføjer du en knap uden at skrive den
i tabellen, stopper byggeriet.

Det hele står i `docs/27-layouttokens.md`.

## Den fjerde regel: rammen, og ingen række der ombryder på må og få

Bjælker, der forsvandt, og knapper, der ikke kunne ses, havde tre årsager —
alle tre er nu spærret af byggeriet. Hele forklaringen står i
`docs/30-responsivt-layout.md`.

1. **Rammen.** Hver skærm er `build_helpers.app_frame(prefix, bjælke, kort)`:
   en header med fast højde (bjælken) og en krop, der scroller. **Byg
   aldrig en skal, hvis højde er summen af kortene** — kroppen scroller, og
   kortene står direkte i den.
2. **`SHELL_W` er en nedre grænse.** Padding, scrollbar (18 px) og luft
   (6 px) står i `RAMMEN` i `tools/layout_tokens.py`. Scrollbaren tager
   plads på Windows og ingen på Mac — derfor så fejlen tilfældig ud. Sæt
   aldrig paddingen op "så tallet passer"; det var præcis den fejl.
3. **To tilstande.** En række, der kan ombryde, bygges med
   `build_helpers.flow_row()`: enten vandret på én linje, eller lodret med
   ét barn pr. linje (`LayoutDirection = If(...)`). Skriv aldrig
   `wrap="true"` med en håndregnet højde. Bjælken er
   `build_helpers.top_bar()` i alle fire apps.
4. **`Parent.Width` er forælderens Width-EGENSKAB, ikke pladsen inden i
   den.** Padding og scrollbar er ikke trukket fra. Regn aldrig med den:
   resten af en række er `build_helpers.grow(ctrl)` (FillPortions), en
   bestemt bredde regnes af `SHELL_W`. Det var den fejl, der sendte
   bjælkens knapper ned under kanten i første udgave af rammen.
5. **Knapper er mindst 30 px høje**, og containere skjuler overløb
   (`LayoutOverflow.Hide`), med mindre de skal scrolle.
6. **Skriv aldrig `Parent.TemplateWidth`/`TemplateHeight` med vilje i
   forventning om galleriets bredde** — i Studio gav den 320. Skriv dem
   gerne i en builder; `gen_screen.resolve_templates()` erstatter dem med
   et udregnet udtryk, før skærmen skrives, og regel 26 sikrer, at ingen
   slipper igennem.
7. **En tekst er mindst 1,5 × sin skriftstørrelse høj** — ellers får den
   sin egen scrollbar. `text_ctrl()` sørger selv for det.
8. **Ingen `FillPortions` i en vandret række.** `grow(ctrl)` markerer den
   del, der tager resten; bredden regnes ud, når skærmen skrives. Ved
   siden af en FillPortions-del blev knapperne tegnet en linje for lavt.
9. **Equipment og Material: Details og Documents er popups** med hver sin
   række (`varDomDetailsId`, `varDomDocsId`). Rækken har fem knapper:
   Edit, Details, Docs, Copy, Delete.

| Du vil … | Gør |
|---|---|
| Tilføje en sektion | Læg kortet i listen til `app_frame(...)` |
| Tilføje en knap i bjælken | Tilføj den til listen til `top_bar(...)` — intet andet |
| Lave en række, der ombryder | `flow_row(...)` |
| Lade et felt tage resten af en række | `grow(ctrl)` — aldrig `Parent.Width - n` |
| Regne en højde | Konstanter, `App.Width`/`LayoutRank`, `CountRows(col…)`. Aldrig en datakilde |

## Fire apps — hver med sin selvstændige build-mappe

| App | Mappe | Skærm | Byg |
|---|---|---|---|
| VH-plan | `Maintenance Plan App/` | `ScreenVhPlan.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |
| Landingsside | `Masterdata Hub/` | `ScreenMdHub.pa.yaml` | `generate_hub_onstart.py` + `assemble_hub.py` |
| Equipments | `Equipment App/` | `ScreenEquipment.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |
| Materials | `Material App/` | `ScreenMaterial.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |

**De fælles filer ligger i `tools/` — i én udgave, ikke fire kopier.**

```
tools/gen_screen.py      DSL, højde-algebra, C_*-navnene der peger på tokens
tools/build_helpers.py   byggeklodser: card, group, button_row, inputs, theme_button
tools/check_layout.py    layout-tjekket
tools/build_domain.py    Equipments og Materials' fælles skærm
tools/attflows.py        flow-kontrakten for dokumenter
tools/build_flsearch.py  flow-kontrakten for FL-søgning
tools/design_tokens.py   alle farver
tools/layout_tokens.py   alle breakpoints
```

De lå før som ordrette kopier i hver `build/`-mappe — 5.863 af 14.825
linjer, 39 %. Begrundelsen var, at Power Apps' VS Code-værktøjskæde
fjernede et delt modul uden for app-mappen. **Den gælder ikke den vej, der
bruges i dag:** `canvas_mcp.stage()` kopierer kun `*.pa.yaml` over til
serveren, så hverken `build/` eller `tools/` når nogensinde derud.

`sys.path` er procesglobal, så det rækker at sætte `tools/` på den i
**indgangen** (`assemble_screen.py`, `generate_app_onstart.py`,
`check_layout.py`-shimmen). Alt, der importeres bagefter, finder dem selv.

Hver `build/`-mappe indeholder nu kun det, der er appens eget:

| App | Egne filer |
|---|---|
| VH-plan | `sp_config.py` + de ni `build_*.py`, der bygger dens skærm |
| Masterdata Hub | `hub_config.py`, `build_hub.py` |
| Equipments / Materials | **kun `domain_config.py`** + de to indgange |

> **To fælder, begge ramt under flytningen — og begge nu spærret:**
>
> 1. `gen_screen.OUT_DIR` regnede app-mappen ud af `__file__`. Da filen
>    flyttede til `tools/`, blev `HERE/..` til **repo-roden**. Alle fire
>    skærme blev skrevet dér, app-mapperne beholdt deres gamle, og
>    layout-tjekket sagde *"OK"* — fordi det læste de gamle filer.
>    `OUT_DIR` kommer nu af **indgangen** (`sys.argv[0]`), og `build_all`
>    fejler, hvis der ligger en `.pa.yaml` i roden.
> 2. `build_flsearch.py` lå i tre kopier, der **ikke var ens**: VH-plan
>    skrev `varVhpFlRaw`, de to andre `varDomFlRaw`. `check_shared()`
>    kiggede aldrig på den fil. Variabelnavnet er nu en parameter
>    (`raw_var=`), så der ikke er en linje tilbage, der kan skille to apps.

## `--app` bygger kun den ene

```
python3 tools/build_all.py                 alle fire
python3 tools/build_all.py --app equipment kun den
```

Nøglerne er `vhplan`, `hub`, `equipment`, `material`, eller mappenavnet.
`deploy` bruger den selv, så et Equipment-deploy kun bygger Equipment.

Det handler ikke om tid — hele byggeriet tager fire sekunder. Det handler
om, at de tre andre apps' output ikke skal rulle det væk, man faktisk
skulle se: en advarsel i VH-plan midt i et Equipment-deploy ligner en, der
hører til.

**To ting kører altid, også målrettet:** at de fælles filer er ordret ens,
og at app-id'erne ikke er gledet fra hinanden. De tager millisekunder, og
de handler netop om det, en målrettet bygning ellers ville springe over.
Datakilde-tjekket læser også alle skærme — de øvrige ligger på disken i
forvejen, og et kolonnenavn, der ændrer sig ét sted, kan brække en anden
app.

`check_ps1.py` springes over ved en målrettet bygning: PowerShell-scripterne
har intet med den app at gøre, og et deploy skal ikke stoppe på en kommentar
i et provisioneringsscript.

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
| `build_hero.py` | Topbjælken (**Validate**, **Export JSON**, hub, tema) og hero-kortet med procesindikatoren |
| `build_plan_header.py` | Planhoved, plantype, strategivalg, `section_header` |
| `build_items.py` | Items-skinne, Item Editor, FL-felt, objektliste |
| `build_flsearch.py` | **Flow-kontrakten for FL-søgning** — outputnavn og feltnavne ligger kun her |
| `build_attflows.py` | **Flow-kontrakten for dokumenter** — de tre attachment-flows, mappenavnet og de to former af `text` |
| `build_tasklist.py` | Tasklist, operationstabel, dispatch, mailknap |
| `build_strategy.py` | Pakkematricen (strategiplaner) |
| `build_modal.py` | Tasklist-picker |
| `build_save.py` | **Gemning i SharePoint** — de fire lister, nøglerne, og hvad der bevidst ikke udfyldes |
| `build_load.py` | **Indlæsning af en gemt plan** — dyblinket fra hubben (`?reqid=`), og hvilke felter der kan læses tilbage |
| `assemble_screen.py` | Samler skærmen → `../ScreenVhPlan.pa.yaml` |
| `generate_app_onstart.py` | `App.Formulas` + `App.OnStart` → `../App.pa.yaml` |

De fem historiske buildere (`build_diag_screen.py`, `build_vhplan_screen.py`,
`gen_options.py`, `gen_tasklists.py`, `rename_collections.py`) og deres fem
mellemresultat-`.txt` er **slettet** — 997 linjer, som ingenting importerede.
Git husker dem; mappen skal ikke.

## Hvem ejer hvad — Equipments og Materials

**De er IKKE længere den samme app.** De var det: de to build-mapper
indeholdt ordret de samme filer, og `build_all.py` nægtede at bygge, hvis
de gled fra hinanden. Det holdt, så længe de to kun havde forskellige
*felter*. Det gælder ikke længere — de skal kunne to forskellige ting.

| Fil | Ejer | Må afvige? |
|---|---|---|
| `tools/domain_parts.py` | **Byggeklodserne**: bar, formular, dokumentrude, rækketabel, indsend, og Power Fx'en bag gem/hent/slet | Fælles |
| `tools/attflows.py` | Flow-kontrakten for dokumenter | Fælles |
| `tools/build_flsearch.py` | Flow-kontrakten for FL-søgning | Fælles |
| `<App>/build/domain_config.py` | Felterne, listenavnet, præfikset | **Ja** |
| `<App>/build/assemble_screen.py` | **Kompositionen** — hvilke dele, i hvilken rækkefølge | **Ja** |
| `<App>/build/generate_app_onstart.py` | Samlingsskemaet og tilstandsvariablerne | **Ja** |

Der er **ingen vagt** der kræver at de to er ens. Det er med vilje.

### Hvordan en af dem afviger

1. **Komponer anderledes.** Lad appens `assemble_screen.py` kalde andre
   dele, i en anden rækkefølge, eller udelade en.
2. **Erstat en del.** Skriv funktionen i appens **egen** build-mappe og kald
   den i stedet. Delene kalder ikke hinanden på kryds — de returnerer
   kontroller, som assembleren sætter sammen.
3. **Er ændringen rigtig for BEGGE apps**, hører den i `tools/domain_parts.py`.
   Er den kun rigtig for den ene, hører den i appens egen mappe.

Den skelnen er hele grunden til, at delene ligger i `tools/` og ikke er
kopieret ind i hver mappe. Kopier dem ikke tilbage, fordi den ene app skal
have en lille ændring — skriv ændringen i den app.

**`SECTIONS` er kontrakten mod SharePoint.** Hver linje svarer til en
kolonne i `EquipmentItems` / `MaterialItems`, og `check_datasources.py`
efterprøver det ved hver bygning. Et felt til eller fra er **én linje i
`SECTIONS` og én i `sharepoint/provision/Provision-EqMatLists.ps1`** —
skærmen, samlingsskemaet og `Patch` følger med, fordi de alle tre læser
den samme liste.

**Rækken bor i SharePoint, ikke i hukommelsen.** `RowId` *er* rækkens `ID`,
og nøglen `EQ-000912` er lavet af det samme `ID`. Derfor skriver Gem
direkte i listen: nøglen er mappenavnet i `TaskListDocuments`, og uden den
er der ingen mappe at lægge dokumenter i.

**Datahentningen ligger i skærmens `OnVisible`, ikke i `App.OnStart`.**
Rækkerne hører til skærmen. `OnStart` indeholder kun samlingsskemaet og de
variabler, skærmen skal kunne læse, før den er vist én gang.

Se `docs/23-eq-mat-apps.md` og `docs/24-eq-mat-persistering.md`.

## Hvem ejer hvad — Masterdata Hub

| Builder | Ejer |
|---|---|
| `hub_config.py` | **Al tilpasning**: listenavn, `ENV_ID`, de fem domæner (navn, farve, `app_id`) og statusordforrådet |
| `build_hub.py` | Toplinje, domænefliser, filtre, listen |
| `assemble_hub.py` | Samler skærmen → `../ScreenMdHub.pa.yaml` |
| `generate_hub_onstart.py` | `App.OnStart` → `../App.pa.yaml` |

Skal en ny domæneapp kobles på, eller skal en status skifte farve eller
tekst, så er svaret **altid `hub_config.py`** og aldrig `build_hub.py`.
Når en satellit-app er bygget, indsættes dens `app_id` i `DOMAINS`, og
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
stedet, for 0–8 items og 0–12 operationer og for de skærmbredder,
`layout_tokens.test_widths()` giver — **hver breakpoint-grænse og pixlen
under den** (420, 719, 720, 1023, 1024, 1366, 1599, 1600, 1920). Før stod
der en håndplukket liste, der sprang henover 1023, og det er præcis dér,
layoutfejl bor:

1. Ingen `Height`-formel refererer en anden kontrols `.Height`
2. Lodrette containere er høje nok til børn + gaps + egen polstring
3. Vandrette containere er høje nok til deres højeste barn
4. Faste bredder i en række overstiger ikke rækkens bredde
5. HTML-tabeloverskrifter flugter med kontrollerne i rækken
6. Balancerede parenteser og anførselstegn i alle formler
7. Ingen formel refererer en kontrol, der ikke findes
8. Enhver `col*`, skærmen bruger, findes i `App.pa.yaml` — som navngiven
   formel eller som `ClearCollect`
8b. Enhver designtoken, skærmen bruger, findes i temaformlen `C`. Power Fx
   siger **ikke** fra ved et felt, en record ikke har — den giver blank, og
   blank er gennemsigtig. En stavefejl ville derfor ikke fejle i compile;
   kontrollen ville bare forsvinde, måske kun i det ene tema
8c. Ingen formel sammenligner `App.Width` med et tal — breakpoints hører i
   `tools/layout_tokens.py`
9. Ingen **lodret** container har et barn med `FillPortions <> 0` —
   undtagen rammens krop, som skal fylde skærmen under headeren
4c. Hver wrap-række **spilles**: børnene pakkes i linjer, som autolayout
   gør det, i den bredde containeren faktisk får — **med scrollbaren
   trukket fra**. Højden skal rumme de linjer, der kommer ud af det
23. Rammen: `con<X>Root` → header med fast højde + præcis én krop med
   `Scroll`. Headerens højde må ikke afhænge af data (23b), og padding +
   scrollbar + luft skal være mindst `SHELL_INSET` (23c)
4d. En række, der skifter retning, skal passe i sin vandrette tilstand —
   i den bredde, den faktisk får
24. `Parent.Width` må ikke indgå i et regnestykke. Den er forælderens
   Width-egenskab; padding og scrollbar er ikke trukket fra
25. En knap er mindst 30 px høj
26. Ingen `Parent.Template*` i den byggede skærm, og en gallerirække skal
   rumme sine celler fra Tablet og op
27. En tekst er mindst 1,5 × sin skriftstørrelse høj
28. Ingen `FillPortions` i en vandret række, der ikke ombryder

Punkt 7 fanger den klassiske: du sletter en kontrol og glemmer en
`Reset()` på den et andet sted. Det ville ellers først vælte i compile.

Punkt 8 fanger den samme fejl for data: flytter du en opslagsliste fra en
hårdkodet tabel til en navngiven formel, bliver referencerne let hængende.

Et barn med `Visible = false` regnes ikke med i højden — præcis som
AutoLayout gør det. Og et barn med en `Visible`-**formel** tælles kun med,
når formlen er sand *i netop det testtilfælde*: `stack_height` skriver
forælderens højde som `If(betingelse, gap + h, 0)`, så de to skal være
enige. Kan betingelsen ikke regnes ud, tælles barnet med — hellere et fund
for meget end en container, der klipper sit indhold.

## Feltkanten har ÉN regel

Alle fem inputtyper — `text_input`, `number_input`, `dropdown`,
`date_picker`, `combobox` — kalder `build_helpers.border_rule()` og
`input_fill()`. Byg ikke en sjette.

```
ikke krævet        ->  border-default   (eksplicit — ikke platformens standard)
krævet + tom       ->  state-error-fg
krævet + udfyldt   ->  state-ok-fg
```

**Grøn kun på krævede felter.** En grøn kant om hvert eneste udfyldt felt
gør farven meningsløs; grøn skal betyde "dette krav er opfyldt", ikke "du
har tastet noget".

**Rød betyder "jeg har tjekket".** VH-plan gater på `varVhpPlanValidated`
(Validér-knappen), Equipment og Material på `varDomValidated`, som sættes
når brugeren trykker Gem eller Indsend. Ingen app viser rødt, før brugeren
har bedt om et tjek — "rød fra første sekund" lærer brugeren at se bort fra
rødt.

Det hele står i `docs/28-feltfarvning.md`.

## Dropdown-`Default` er en RECORD, ikke en værdi

`ModernDropdown.Default` vil have en **record fra kontrollens egen
`Items`-tabel** — ikke værdien inde i den:

```
Default: =LookUp(colDomPlants, Value = varDomFPlant)     rigtigt
Default: =varDomFPlant                                    compile-fejl
```

Fejlen lyder `[Control 'drpX', Property 'Default'] Expected a valid input
matching Items`, og den koster en hel runde gennem Studio. **Regel 16** i
`check_layout.py` fanger den lokalt: en `Default`, der ikke indeholder
`LookUp(`, `First(`, `{`, `ThisItem` eller `Blank()`, er en skalar.

Og husk `OnChange`. En dropdown uden den lader brugeren vælge frit, mens
variablen står stille — formlen er gyldig, så hverken compile eller App
checker siger noget. Læses variablen af gem-knappen, kan der aldrig gemmes.

> Der lå kort en regel 17, der skulle fange netop det. Den er fjernet
> igen: elleve fund i VH-plan, alle falske, fordi de dropdowns læses som
> `drpVhpPlant.Selected.Value`, hvor variablen kun sætter startværdien.
> Elleve falske fund ville lære nogen at springe advarsler over — og så
> går regel 15's rigtige fund samme vej.

## Flere hentninger på én gang: `Concurrent()`

Uden den venter appen på **summen** af kaldene; med den kun på det
længste. Fem SharePoint-lister i kæde er fem rundture efter hinanden.

```python
from build_helpers import concurrent
concurrent(hent_a, hent_b, hent_c, indent=16)
```

**Men den hjælper kun formler med et connector- eller Dataverse-kald.**
`Set()` af en lokal variabel, eller `ClearCollect` af en literal tabel,
bliver ikke hurtigere — de tager mikrosekunder, og at pakke dem ind gør kun
formlen sværere at læse.

**Og den er farlig ved afhængigheder.** Rækkefølgen er ikke givet. To
formler inde i den samme `Concurrent` må ikke afhænge af hinanden. Det er
til gengæld sikkert at afhænge af noget **før** den, og at afhænge af den
**bagefter**.

> **Apperne henter ikke i `App.OnStart`** — det er den ældre og vigtigere
> regel, og den står nedenfor. VH-plan bruger navngivne formler, Equipment
> og Material henter i skærmens `OnVisible`. Den ene undtagelse er
> dyblinket (`?reqid=`), og netop dér henter den fem lister — de er nu
> samlet i én `Concurrent`.

`check_layout` regel 20 advarer, når to eller flere **uafhængige**
hentninger står i kæde. Den springer kæder over, hvor et senere led læser
et tidligere, og kilder der er en `col*` eller en literal — dem er der
ingenting at vinde på.

## Regel 15 er en advarsel, ikke en fejl

`check_layout.py` melder `Collect`, `Patch`, `Remove` og deres slægtninge
**inde i et `ForAll`** — men stopper ikke byggeriet.

Mod en samling er det én regelgenberegning pr. række; mod en **datakilde**
er det et netværkskald pr. række. App checker melder det samme ved deploy
som `ForAllWithMutation`. Forskellen er, at det står her, før en hel runde
gennem Studio.

`ForAll` returnerer en **tabel**, så skrivningen kan samles:

```
ClearCollect(col, ForAll(kilde, { ... }))
Patch(kilde, ForAll(raekker), ForAll(aendringer))
```

Flowkald og anden adfærd pr. række må gerne blive i løkken — det er kun
**skrivningen**, der skal ud.

VH-plan-appen har otte af dem og kører. Derfor er den en advarsel: at gøre
den til en stopklods ville betyde, at ingen kunne bygge noget, før de otte
var lavet om. De to domæneapps er rene.

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

App-id'erne står i `tools/canvas_apps.json` — kør `python3 tools/env_config.py`
for at se dem.

App-id'et står **ikke** i solution-eksporten. Det `Id`, en apps
`Properties.json` bærer, er *dokumentets* id, ikke appens — de to er
forskellige, og play-URL'en vil have appens. Hent det i Studio-URL'en
eller med `pac canvas list`.

**Publicér før eksport.** En canvas app i en solution eksporteres fra den
PUBLICEREDE udgave — gemt er ikke nok. To eksporter i træk viste to blanke
skabeloner, fordi apperne var gemt men ikke publiceret. `Status: Ready` i
`meta.xml` siger intet om, hvorvidt indholdet er med.

**Alle id'er står ét sted:** `tools/canvas_apps.json`, læst af
`tools/env_config.py`. De stod før fire steder — her, i `hub_config.py`, i
de to `domain_config.py` og i `sp_config.py` — holdt sammen af
`check_app_ids()` i `build_all.py`: 60 linjer, der læste tre af filerne med
**regex**. Vagten er slettet sammen med kopierne; den fejlklasse kan ikke
opstå længere.

```bash
python3 tools/env_config.py          # hvilket miljø og hvilke id'er?
python3 tools/build_all.py --env prod
```

Et nyt miljø er én blok mere under `environments`. `--env` sætter
`CANVAS_ENV` for byggescripterne, så alle fire apps bygges mod **det samme**
miljø — og `canvas_mcp.py` læser den samme fil, så man ikke kan bygge mod
ét miljø og deploye til et andet.

Equipment-appen er **`Equipments`** (`orsted_equipments_ebf7d`, i
solutionen). Den ældre `dd9544e2-…` uden for solutionen findes stadig, men
intet i repoet peger på den længere.

**Deploy efterprøver træet — og `--clean`, når en kontrol er flyttet.**
Studio flytter ikke pålideligt en kontrol fra én forælder til en anden:
da listekortet og bjælkens knapper blev flyttet, stod de i Studio i en
anden rækkefølge end i den byggede YAML, og listens rækker havde mistet
deres bredde. Driftrapporten kaldte det "normalisering".

`deploy` sammenligner nu TRÆET efter sync (`tools/deploy_verify.py`):
samme kontroller, samme forælder, samme rækkefølge, samme værdi, hvor
begge sider har egenskaben. Normalisering (fjernede egenskaber) tælles
ikke — efterprøvet mod en rigtig servereksport: 0 fund. Er der fund,
stopper den og siger:

```powershell
python tools\canvas_mcp.py deploy --app equipment --clean
```

`--clean` sender først en tom skærm og derefter den rigtige, så hele
træet bygges på ny i filens rækkefølge. Brug den altid, når en ændring
flytter en kontrol til en ny forælder.

**Compile før sync.** Fejler compile, så stop — synk ikke en app, der ikke
kan oversættes. `cmd_deploy` i `tools/canvas_mcp.py` håndhæver det nu selv:
den læser fejltallet ud af `compile_canvas`' svar og afbryder. Før stod
reglen kun her, og et deploy med to fejl så ud til at lykkes — `Synced 3
file(s)`, `No app checker issues found`, `Faerdig`. Fejlene stod fire
linjer længere oppe og blev rullet væk af resten.

Og driftrapporten bagefter var værre end ingenting: når compile afviser,
er serverens tilstand den **gamle** app, så rapporten sammenlignede det,
vi sendte, med noget der aldrig blev taget imod — og kaldte forskellen
normalisering. Det er `compile_canvas`, der sender YAML'en ind i den åbne
coauthoring-session; `sync_canvas` skriver bagefter serverens tilstand
**ned** i mappen igen. Peger du den på app-mappen, overskriver den de
genererede kilder — derfor arbejder `tools/canvas_mcp.py` på en kopi i
`.canvas-deploy/`.

## Solution-eksporten er læsestof, ikke en kilde

`solution/` er et øjebliksbillede af BIO SAP, hentet med
`tools/export_solution.ps1`. Den findes, så flows, miljøvariabler og
connection references kan læses her i repoet i stedet for i browseren.

**De to canvas apps bygges stadig af Python-builderne.** Eksporten
indeholder også appene som `.msapp` — de er *resultatet* af sidste deploy,
ikke kilden til den næste. Retter nogen i en `.msapp` eller pakker
solutionen tilbage, er ændringen væk ved næste `python3 tools/build_all.py`,
og så er der to sandheder om den samme skærm.

`.msapp`-filerne er derfor i `.gitignore`. Men så kunne YAML'en inde i dem
heller ikke læses fra repoet, og en app, der *kun* findes i solutionen —
Equipment, Materialer, KKS — var dermed en sort kasse for alle andre end
den, der sad ved maskinen. Derfor pakker `tools/unpack_msapp.py` hver
`.msapp` ud som tekst i en mappe ved siden af:

```
solution/BIOSAP/src/CanvasApps/<navn>.src/Src/*.pa.yaml
                                         /References/DataSources.json
                                         /Properties.json
```

`export_solution.ps1` kalder den selv, **før** rensningen — en formel kan
bære en URL eller en nøgle, og `scrub_solution.py` kan kun fjerne det, den
kan se.

**`<navn>.src` er læsestof på nøjagtig samme måde som resten af eksporten.**
For `orsted_maintenanceplan_82090.src` og `orsted_masterdatahub_1b09a.src`
betyder det, at den samme skærm nu står to steder i repoet: builderens
resultat i app-mappen, og deployets øjebliksbillede i eksporten. Rediger
altid builderen. Eksportkopien er kun god til ét: at se, om det, der ligger
i Studio, er det, vi sidst byggede.

Skal du se den kørende app *nu* — ikke som ved sidste eksport — så brug
`python tools/canvas_mcp.py pull`.

Eksporten er et øjebliksbillede: ændrer nogen et flow, ved repoet det først,
når den er hentet igen.

## Efter synk: skriv ikke Studios YAML tilbage

Power Apps normaliserer egenskaber, den betragter som standardværdier, væk.
Eksporterer du YAML'en tilbage, mangler den bl.a. `FillPortions` på nogle
containere, `LayoutAlignItems` på containere med `LayoutWrap = true`, og
eksplicitte `Height` på nogle blad-kontroller.

**Det er normalt.** Det er ikke en fejl, og det skal ikke rettes. Kopiér
aldrig den normaliserede YAML tilbage over kildefilerne — så mister du de
egenskaber, builderne bevidst sætter.

## Ni ting der aldrig må regressere

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
4. **Stylingen skal være uændret.** Radier, skriftstørrelser og polstring
   matcher Materialer-appen, og apperne skal blive ved at ligne hinanden.
   Farver er nu designtokens: de skal ændres i `tools/design_tokens.py` og
   **i begge temaer**, aldrig i en builder. En ny token uden en mørk værdi
   bliver gennemsigtig — og det ses kun af de brugere, der har slået mørk
   tilstand til.
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
9. **Bjælken står i rammens header, og `SHELL_W` lover aldrig mere, end der
   er.** Ingen skal-sum, ingen `wrap="true"` med håndregnet højde, ingen
   padding der æder scrollbarens plads. Regel 4c og 23 håndhæver det — se
   `docs/30-responsivt-layout.md`.

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

## Navigation mellem apps: `LaunchTarget.Replace`

De fem domæneapps er selvstændige apps, ikke skærme i hubben. Navigation
mellem dem er derfor `Launch`, ikke `Navigate` — og den skal ske i den
fane, brugeren står i:

```
Launch(url, { }, LaunchTarget.Replace)
```

Med `New` får man **en fane pr. klik**. Åbn tre indmeldinger, og der er
fire faner med Power Apps i, som alle ser ens ud i proceslinjen.

Målet står som `APP_TARGET` i `hub_config.py`, så det kun er ét sted.

**Temaet skal med i URL'en.** `SaveData`-lageret er isoleret pr. app-id, så
uden `?theme=dark` ville et klik fra en mørk hub lande i en lys satellit —
og brugeren ville se appen skifte farve som følge af sit eget klik. Både
hubbens fliser, dens "Open", og satellitternes "Til hubben" hænger
`design_tokens.theme_query()` på.

**Undtagelsen er dokumenter.** `btnDomAttOpen` åbner en fil fra
biblioteket i en **ny** fane. `Replace` ville smide appen væk — og en
halvudfyldt formular med den. Et dokument er ikke en app.

`mailto:`-linket i VH-plan sætter intet mål; en mailto åbner mailklienten
og rører ikke fanen.

## `Text(GUID())`, aldrig `GUID()`

En global variabels type låses ved **første** tildeling. Er den erklæret
som `""` i `App.OnStart`, er den tekst — og `GUID()` er sin egen type, ikke
tekst. Tildelingen går ikke igennem, variablen bliver stående tom, og
fejlen dukker op et helt andet sted:

```
Set(varDomRequestGuid, GUID());
Patch(MD_RequestIndex, Defaults(...), { RequestNo: varDomRequestGuid, … })

  -> [MD_RequestIndex] Field 'Title' is required.
```

Fejlen pegede på `Title` og handlede om en GUID. `RequestNo` **er** Title,
omdøbt, og den er obligatorisk — så en tom værdi blev afvist.

Der er **ingen regel** i `check_layout.py` for det her, og det er med
vilje: at fange det kræver typeudledning, og en regel der gætter, er
værre end ingen (se regel 17, der blev fjernet igen). `Text(GUID())` står
i stedet her og i VH-plan-appen, som har gjort det rigtigt hele tiden.

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

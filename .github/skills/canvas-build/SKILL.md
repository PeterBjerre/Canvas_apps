---
name: canvas-build
description: Arbejdsgang for canvas apps i dette repo — "Maintenance Plan App" (VH-plan), "Masterdata Hub" (landingssiden), "Equipment App" (Equipments), "Material App" (Materials), "Functional Location App" og den samlede test-app "BIO SAP App". Brug den ved ENHVER ændring af en skærm, App.OnStart, layout, farver, breakpoints, Power Fx-formler, kontroller eller datakilder. Ret builderne i Python, generér .pa.yaml, kør layout-tjekket, og synkronisér først derefter til Power Apps Studio.
---

# Canvas apps: byg og deploy

## Den ene regel

`.pa.yaml`-filerne er **genereret**. `ScreenVhPlan.pa.yaml` er knap 16.000
linjer, `ScreenEquipment.pa.yaml` og `ScreenMaterial.pa.yaml` godt 11.000 hver,
`ScreenFunctionalLocation.pa.yaml` godt 5.000 og `ScreenMdHub.pa.yaml` knap
4.000. `App.pa.yaml` er også genereret i alle apps. Retter du direkte i dem, er ændringen væk, næste gang nogen
kører builderen — og du efterlader en fil, der ikke længere matcher sin kilde.

**Ret i `build/*.py`. Altid.**

Det gælder også, når ændringen er lille, og når du har travlt. Der findes
ingen undtagelse.

## Den anden regel: farver er tokens, ikke tal

**Ingen builder må indeholde en farve.** Hverken `RGBA(...)` eller
`#rrggbb`. `tools/build_all.py` nægter at bygge, hvis nogen skriver en, og
den læser syntakstræet, så en kommentar må gerne nævne en farve.

Alle farver står i `tools/design_tokens.py` — ét sted for alle
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
`tools/design_tokens.py`, og alle apps skifter sammen.

Skal en farve bruges inde i en **HTML-streng** (`HtmlViewer`), så brug
`design_tokens.ref_hex()` — hex-værdierne afledes af de samme tokens og
kan derfor ikke glide fra dem.

**Felter arver aldrig Fluent-temaets farver** (issue #78). Byg dem med
`text_input` / `number_input` / `date_picker` / `dropdown` — de går alle
gennem `build_helpers.input_theme` — og afkrydsningsfelter med
`checkbox_theme`. Et låst felt er `DisplayMode.View` (`readonly_mode`),
aldrig `Disabled`: Fluent ignorerer vores `Color`/`Fill` i Disabled, og i
mørk tilstand blev det grå tekst på sort. `check_layout` regel 10c stopper
byggeriet. Tabeller får `table_surface` / `row_rule` — ikke galleriets fyld
i kantfarven. Se `docs/26-designtokens.md`.

**Et låst felt er Outline** (gennemsigtigt, dæmpet tekst) — aflæst i
Studio: i View tegnede tekstfelt og dropdown Fluents lyse baggrund under
vores lyse tekst. `input_theme` gør det; regel 10c tillader kun Outline i
den låste gren.

**En klikbar række er `build_helpers.row_hit()`** (issue #79): et
gennemsigtigt lag øverst i rækken med rækkens handling, tone ved hover og
tryk (`row-hover`/`row-pressed`), kant ved fokus. Kontroller under laget, der
gør det samme, får `TabIndex -1`, hvor typen kender den — `ModernButton`
gør ikke (regel 10). Bruges i hubbens liste,
Closed-preview og VH-planens items.

Temaknappen er `build_helpers.theme_button()` og er **den samme kontrol i
alle apps**. Den står i sidebarens fod (`tools/side_nav.py`). Byg ikke en ny.

Det hele står i `docs/26-designtokens.md`, inkl. hvorfor farverne ikke kan
ligge i miljøvariabler, og hvordan valget huskes.

## Den tredje regel: breakpoints er tokens, ikke tal

**Ingen skærm må sammenligne `App.Width` med et tal.** `check_layout.py`
regel 8c stopper byggeriet. Aritmetik er fint — `SHELL_W` *er*
`(App.Width - NAV_OFFSET - 64)` (sidebaren 56, eller 0 på mobil + rammen
64) — det er kun
**sammenligningen**, der er en beslutning.

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
   `build_helpers.top_bar()` i alle apps.
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
9. **En gallerirækkes bredde bestemmer Studio.** Aflæst i Studio: først
   320, siden `Parent.Width` — aldrig builderens udtryk. Vores tal er et
   **budget for cellerne**, og det skal være en nedre grænse:
   `GALLERY_RESERVE` trækkes fra, når bredden stammer fra en
   `Parent.Width`-kæde. Regel 26 måler cellerne mod budgettet.
9b. **Ingen containere i et galleri.** `gen_screen.flatten_galleries()`
   folder dem ud til celler med X/Y, når skærmen skrives — Studio ejer
   bredden på et galleris øverste container og gav den 320 px ved
   `--clean`. Skriv rækken som en container i builderen som før; regel
   26c stopper byggeriet, hvis en container når ud i YAML'en.
10. **Equipment og Material: Details og Documents er popups** med hver sin
   række (`varDomDetailsId`, `varDomDocsId`). Rækken har fem knapper:
   Details, Docs, Edit, Copy, Delete. Formularen og listen er HTML-projektets
   (issue #67/#68): et gitter med 4/2/1 kolonner, Compact/All columns, et
   værksfilter og en Documents-knap i formularen. Byggeklodserne står i
   `tools/domain_parts.py`; hvilke felter og kolonner er appens egne
   (`material_parts.py` / `equipment_parts.py`).

### Sidebaren

Alle fem apps har **den samme sidebar** til venstre: `tools/side_nav.py`,
efter HTML-sidens navigationsskinne (`html/shell.js` / `shell.css`). Logo,
en knap der åbner og lukker den, et punkt pr. app (den, man står i, er
markeret) og en fod med **Help**-kontakten (kun VH-plan) og **temaskiftet**.

- Lukket er den `NAV_W` = 56 px, og rammen starter dér: `con<X>Root` har
  `X = 56`, `Width = Parent.Width - 56`. Regel 23 kræver præcis det —
  udtrykkene er `ROOT_X`/`ROOT_Y`/`ROOT_W`/`ROOT_H` i `layout_tokens.py`.
- **Mobil (under Tablet, issue #65):** skinnen er skjult, og
  `con<X>MobileBar` (52 px: menu, logo, appens navn) står øverst. Rammen
  står under den i fuld bredde. Menuknappen åbner **det samme** panel —
  ingen anden navigation. `side_nav()` returnerer derfor `([skinne,
  bjælke], overlag)`, og skærmen skriver `[root, *nav, ..., *overlay]`.
- Den åbne sidebars lukkeknap er kun dobbeltpilen — ingen "Collapse"-tekst.
- Åbnet er et **separat panel**, `con<X>NavOpen` (`NAV_W_OPEN` = 232 px,
  `Visible = gblNavOpen`), der ligger **oven på** indholdet som i HTML-siden.
  Derfor regner `SHELL_W` kun med den lukkede bredde.
- **Ingen formel-bredde på sidebaren.** Første udgave var én container med
  `Width = If(gblNavOpen, 232, 56)`; i Studio blev den 57 px og klippede det
  åbne indhold, så panelet så ud til at folde sig ud bag skærmen. Skinne og
  panel har nu hver sin faste bredde.
- `side_nav()` returnerer `(skinne, overlag)`. Skinnen står **lige efter
  rammen**, overlaget (sløret + panelet) står **sidst** — i en `.pa.yaml`
  ligger det, der står senere, øverst:
  `[root, rail, backdrop, popups..., *overlay]`.
- Navigation er `Launch(url & ?theme=..., {}, LaunchTarget.Replace)`. Derfor
  har topbjælkerne ikke længere "To the hub".

| Du vil … | Gør |
|---|---|
| Tilføje en sektion | Læg kortet i listen til `app_frame(...)` |
| Tilføje en knap i bjælken | Tilføj den til listen til `top_bar(...)` — intet andet |
| Lave en række, der ombryder | `flow_row(...)` |
| Lade et felt tage resten af en række | `grow(ctrl)` — aldrig `Parent.Width - n` |
| Regne en højde | Konstanter, `App.Width`/`LayoutRank`, `CountRows(col…)`. Aldrig en datakilde |

## Apps — hver med sin egen build-mappe

| App | Mappe | Skærm | Byg |
|---|---|---|---|
| VH-plan | `Maintenance Plan App/` | `ScreenVhPlan.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |
| Landingsside | `Masterdata Hub/` | `ScreenMdHub.pa.yaml` | `generate_hub_onstart.py` + `assemble_hub.py` |
| Equipments | `Equipment App/` | `ScreenEquipment.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |
| Materials | `Material App/` | `ScreenMaterial.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` |
| Functional Location | `Functional Location App/` | `ScreenFunctionalLocation.pa.yaml` | `generate_app_onstart.py` + `assemble_screen.py` (reglerne: `docs/31`) |
| KKS-opslag | `KKS App/` | `ScreenKks.pa.yaml` (kun i BIO SAP) | `generate_app_onstart.py` + `assemble_screen.py` — se `KKS App/README.md` |
| BIO SAP (test) | `BIO SAP App/` | alle seks | `generate_app.py` + `build_screens.py` + `check_combined.py` — se `BIO SAP App/README.md` |

**De fælles filer ligger i `tools/` — i én udgave, ikke fire kopier.**

```
tools/gen_screen.py      DSL, højde-algebra, C_*-navnene der peger på tokens
tools/build_helpers.py   byggeklodser: card, group, button_row, inputs, theme_button
tools/side_nav.py        sidebaren - den samme i alle fem apps
tools/check_layout.py    layout-tjekket
tools/domain_parts.py    Equipments og Materials' fælles byggeklodser
tools/attflows.py        flow-kontrakten for dokumenter
tools/build_flsearch.py  flow-kontrakten for FL-søgning
tools/fl_picker.py       FL-vælgeren: én ModernCombobox + Search (VH-plan, Eq, Mat)
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
| VH-plan | `sp_config.py` + de elleve `build_*.py`, der bygger dens skærm |
| Masterdata Hub | `hub_config.py`, `build_hub.py` |
| Equipments | `domain_config.py`, `equipment_parts.py` (felternes rækkefølge og listens kolonner) + de to indgange |
| Materials | `domain_config.py`, `material_parts.py` (felternes rækkefølge, No BOM Item og listens kolonner) + de to indgange |
| Functional Location | `fl_config.py`, `fl_parts.py`, `fl_validation.py`, `fl_save.py`, `fl_rules.generated.json` (genereret af `tools/fl/harness.js plan`) |
| KKS-opslag | `kks_config.py` (lister, nøgleområder, bidder), `kks_parts.py` (skærmen, formlerne, hentningen). Data: `tools/gen_kks_seed.py` |
| BIO SAP | Ingen skærmbyggere — kun kompositionen af de fem |

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

## Én app: BIO SAP

De fem enkeltapps er udfaset (`"single_apps": "retired"` i
`tools/canvas_apps.json`, docs/33). Byggeriet og deploy arbejder kun med
`biosap`; `--app equipment` og de andre afvises med en besked. Skærmene
bygges stadig af byggerne i de fem mapper, og deres `App.pa.yaml` er
mellemprodukter, som ikke ligger i git.

```
python3 tools/build_all.py                 BIO SAP App + alle tjek
python3 tools/build_all.py --app biosap    det samme
```

Det handler ikke om tid — hele byggeriet tager godt ti sekunder. Det handler
om, at de tre andre apps' output ikke skal rulle det væk, man faktisk
skulle se: en advarsel i VH-plan midt i et Equipment-deploy ligner en, der
hører til.

**Farvevagten kører altid, også målrettet** (builderne og `tools/`). Den
tager millisekunder og handler netop om det, en målrettet bygning ellers
ville springe over. (Vagterne over kopierede filer og app-id'er er væk:
der er ikke længere kopier, og id'erne står ét sted.)
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

Den kører PowerShell-, solution- og hemmelighedstjekket, farvevagten og
FL-regeltjekket, bygger derefter alle apps og kører deres layout-tjek, og
slutter med datakilde-, sprog- og hjælpetekst-tjekket. Alt skal være grønt,
før du synkroniserer.

Samme kæde i **én proces** (`tools/build.py`, REVIEW.md C7) — samme tjek,
byte-identiske skærme, uden et nyt Python pr. script:

```bash
python3 tools/build.py [--app equipment] [--env test]
```

CI kører `build_all.py`, som isolerer med rigtige processer.

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
| `tools/gen_screen.py` | Kontroltræ-DSL, stylingkonstanter, **højde-algebra** (`stack_height`, `row_height`) — fælles |
| `tools/build_helpers.py` | Byggeklodser: `card`, `group`, `field_cell`, `button_row`, inputs — fælles |
| `build_hero.py` | Topbjælken med progressbaren: fem klikbare trin (Plan, Item, Task list, Operations/Packages, Save) og **Submit** til sidst, plus **Save draft** |
| `build_status.py` | **Trinenes status og valideringen** som navngivne formler (`VhpStep*Done`, `VhpValidationErrors`, `VhpCanSubmit`, `VhpStateJson`) — reglerne fra den tidligere Validate-knap |
| `build_plan_header.py` | Planhoved, plantype, strategivalg, `section_header` |
| `build_items.py` | Items-skinne (klikbare kort med Delete), Item Editor, FL-felt, Object List-popup'en |
| `tools/build_flsearch.py` | **Flow-kontrakten for FL-søgning** — outputnavn og feltnavne ligger kun her (fælles) |
| `build_attflows.py` | VH-planens udgave af dokumentruden — kun det, der afviger fra `tools/attflows.py` |
| `build_tasklist.py` | Tasklist, operationstabel, materialer, dokumenter |
| `build_strategy.py` | Pakkematricen (strategiplaner) |
| `build_modal.py` | Tasklist-picker |
| `build_save.py` | **Gemning i SharePoint** (Save draft / Submit) — de fire lister, nøglerne, og hvad der bevidst ikke udfyldes |
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
| `hub_config.py` | **Hubbens tilpasning**: de fem domæner (navn, farve, app-nøgle) og statusfarverne. Ordforrådet, domænenøglerne og indeksrækken står i `tools/request_index.py` (fælles for alle apps); beskederne i `tools/messages.py`. App-id'er og URL'er kommer fra `tools/canvas_apps.json` |
| `build_hub.py` | Toplinje, domænefliser, filtre, listen |
| `assemble_hub.py` | Samler skærmen → `../ScreenMdHub.pa.yaml` |
| `generate_hub_onstart.py` | `App.OnStart` → `../App.pa.yaml` |

Skal en ny domæneapp kobles på, eller skal en status skifte farve eller
tekst, så er svaret **altid `hub_config.py`** og aldrig `build_hub.py`.
Når en satellit-app er bygget, indsættes dens `app_id` i `DOMAINS`, og
punktet i "New request"-menuen skifter selv fra "Coming soon" til aktivt.
Fliserne har ingen "+ New" længere (issue #74) — hele flisen er
domænefilteret, og tallet følger både "My requests" og Open/Closed/All.

**Ikoner:** ét ikon pr. domæne i `tools/icons.py` (`DOMAIN`). Sidebaren,
hubbens fliser/rækker og sideoverskrifterne (`build_helpers.page_icon`,
`top_bar(..., icon=<nøgle>)`) slår alle op dér. Tegn aldrig et domæneikon
et andet sted.

### Landingssidens to ufravigelige ydelseskrav

1. **Én datakilde.** Skærmen læser kun `MD_RequestIndex`. Den må aldrig
   læse de fem domænelister og flette dem i klienten — det er fem
   forbindelser og en fletning, der ikke kan delegeres.
2. **Ingen datahentning i `App.OnStart`.** OnStart betales af hver bruger
   hver gang. Galleriet binder direkte til sit filter, og flisernes tal
   tælles på det samme, allerede afgrænsede sæt.

`SCOPE` er ét fladt `Filter`, og hver betingelse skal blive ved at være delegerbar: `RequesterEmail`
er indekseret **tekst** (ikke en Person-kolonne), og køen filtrerer på det
indekserede boolske `IsOpen` — ikke på en række OR'ede statusværdier.

## Hvad check_layout.py fanger

Canvas-layout kan ikke renderes uden for Studio, så det regnes efter i
stedet, for 0, 1, 3, 4, 8 og 12 rækker og for de skærmbredder,
`layout_tokens.test_widths()` giver — **hver breakpoint-grænse og pixlen
under den** (420, 719, 720, 1023, 1024, 1366, 1599, 1600, 1920). Før stod
der en håndplukket liste, der sprang henover 1023, og det er præcis dér,
layoutfejl bor:

<!-- rules:start - genereret af `python3 tools/check_layout.py --rules`; ret i check_layout.py -->
| Regel | Hvad |
|---|---|
| 0 | Hvert kontrolnavn findes kun een gang |
| 1 | Ingen kontrol-til-kontrol hoejdereferencer |
| 2/3 | Hoejde vs. indhold |
| 4c | Ombrydningen, som platformen faktisk laver den |
| 4d | En raekke, der skifter retning, skal passe, naar den er vandret |
| 24 | Parent.Width maa ikke indgaa i regnestykker |
| 25 | En knap skal vaere mindst 30 px hoej |
| 26 | Galleriernes skabeloner |
| 26c | Ingen container i et galleri |
| 30 | Delegerbare filtre: sammenlign mod noget KONSTANT |
| 29 | Overskriften og raekken skal have SAMME kolonnebredder |
| 27 | En tekst skal vaere mindst een linje hoej |
| 28 | Ingen FillPortions i en raekke, der ikke ombryder |
| 23 | Rammen |
| 4 | En vandret raekke skal kunne rumme sine boern |
| 4b | En wrap-raekke maa ikke have en KONSTANT hoejde |
| 5 | HTML-overskriften skal flugte med kontrollerne i raekken |
| 6 | Balancerede parenteser og anfoerselstegn i alle formler |
| 7 | Ingen formel maa referere en kontrol, der ikke findes |
| 9 | FillPortions i en lodret container |
| 8 | Samlinger skal findes i App.pa.yaml |
| 8c | Ingen skaerm maa sammenligne App.Width med et tal |
| 8b | Designtokens skal findes i temaformlen |
| 10 | Egenskaber kontroltypen ikke kender |
| 10c | Inputfelter faar ALDRIG Fluent-temaets farver (issue #78) |
| 10b | SetFocus kan ikke naa ind i en container |
| 31 | Kolonnenavne er navne, ikke strenge |
| 32 | IfError: begge grene skal ende i en skalar |
| 11 | Efterstillet komma i Power Fx |
| 12 | Uescapet anfoerselstegn i en Power Fx-streng |
| 13 | Parent.Template* uden for et galleris direkte barn |
| 14 | Vandret scroll under Stretch |
| 15 | Mutation inde i ForAll (ADVARSEL, ikke fejl) |
| 21 | ButtonAppearance.Secondary |
| 22 | Concurrent med en indbyrdes afhaengighed |
| 16 | Ingen Classic/DropDown |
| 33 | Navnets praefiks foelger kontroltypen (REVIEW.md A3/A4) |
| 18 | Enhver Gallery skal have TabIndex |
| 19 | AccessibleLabel maa ikke vaere kontrollens navn |
| 20 | Flere UAFHAENGIGE hentninger i kaede -> Concurrent |
| 34 | OnStart maa ikke toemme en samling, skaermens OnVisible fylder |
<!-- rules:end -->

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

## Navngivning

`<præfiks><App-infix><Navn>`, fx `btnDomSave`. Infix: `Md` (hub), `Vhp`,
`Dom` (Equipment/Material), `Fl`. Regel 33 holder præfikset.

| Kontrol | Præfiks | | Kontrol | Præfiks |
|---|---|---|---|---|
| GroupContainer | `con` | | ModernDropdown | `drp` |
| ModernText | `txt` | | ModernCombobox | `cmb` |
| ModernTextInput | `inp` | | ModernCheckbox / Toggle | `chk` / `tgl` |
| ModernNumberInput | `num` | | Gallery / HtmlViewer | `gal` / `htm` |
| ModernDatePicker | `dte` | | Rectangle | `rct` |

En kontrol, der er **afledt** af en anden (etiket, stjerne, hint, titel,
baggrund), får navn af basen via `gen_screen.child_name`: cellen
`conVhpCellPlant` giver `txtVhpCellPlantLbl` — ikke `conVhpCellPlantLbl`.

| Tilstand | Navn |
|---|---|
| Skærm-/app-tilstand | `var<X>*` (kun `Set`) — også hubbens (`varMdView`) |
| Delt på tværs af apps | `gbl*` (`gblNavOpen`, `gblNewSeq`, `gblFlReqId`) |
| Samling og navngiven tabelformel | `col<X>*` (`colFlPlan`, `colVhpPlantCodes`) |
| Navngiven skalarformel | `<X>Pascal` (`VhpCanSubmit`, `FlRulesLoaded`) |
| Faste stammer | `…Me`, `…Saving`, `…ConfirmSubmit`, `…Validated`, `…FlMsg`, `…RequestNo`, `…RequestGuid` |

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
(Save i Plan Header og i Item Editor), Equipment og Material på `varDomValidated`, som sættes
når brugeren trykker Gem. Ingen app viser rødt, før brugeren
har bedt om et tjek — "rød fra første sekund" lærer brugeren at se bort fra
rødt.

Det hele står i `docs/28-feltfarvning.md`.

## Én dropdown: `themed_dropdown` (ModernDropdown)

Alle dropdowns bygges af `build_helpers.themed_dropdown` som `ModernDropdown`:
den har runde hjørner, det har Classic/DropDown ikke. **Regel 16** i
`check_layout.py` afviser en `Classic/DropDown`.

**Listen er altid lys.** En moderne dropdown, combobox og datovælger åbner
en Fluent-flyout, som vi ikke kan farve. `Color` farver både feltets tekst
og listens, så al felttekst er tokenet `input-fg`: en mellemgrå i mørk
tilstand, der kan læses på det sorte felt og på den hvide liste (4,60 og
4,57:1). Kontrastvagten i `design_tokens.py` holder begge par.

Du giver `themed_dropdown` **teksten** i den viste kolonne. Den slår selv
recorden op, som `ModernDropdown.Default` vil have:

```
themed_dropdown("drpVhpUnit", "colVhpUnitOptions",
                "LookUp(colVhpUnitOptions, Value = varVhpPlan.Unit).Value")
Default: =LookUp(colVhpUnitOptions As _dd, _dd.Value = (…))
```

Viser listen en anden kolonne end den, der gemmes (fx `Name` over `Key`),
så giv `value_col="Key", display_col="Name"`.

Og husk `OnChange`. En dropdown uden den lader brugeren vælge frit, mens
variablen står stille — formlen er gyldig, så hverken compile eller App
checker siger noget. Læses variablen af gem-knappen, kan der aldrig gemmes.

> Der lå kort en regel 17, der skulle fange netop det. Den er fjernet
> igen: elleve fund i VH-plan, alle falske, fordi de dropdowns læses som
> `drpVhpPlant.Selected.Value`, hvor variablen kun sætter startværdien.
> Elleve falske fund ville lære nogen at springe advarsler over — og så
> går regel 15's rigtige fund samme vej.

## Delegering: sammenlign mod noget, der er ENS for alle rækker

SharePoint kan kun udføre filtreringen på serveren, når værdien er en
**global variabel**, en kontrolegenskab eller en konstant
([Delegable functions](https://learn.microsoft.com/power-apps/maker/canvas-apps/delegation-overview#delegable-functions)).
Et felt fra et `With`- eller `ForAll`-scope — `pl.ID`, `idx.SourceItemId`,
`IT.ActivityType` — er ikke konstant i den forstand. Så henter appen 500
rækker hjem og filtrerer selv: langsomt, og **forkert** så snart listen er
større end de 500.

VH-plan havde 24 delegeringsadvarsler ved compile. Alle sad i den slags
sammenligninger. Tre greb fjernede dem:

| Situation | Greb |
|---|---|
| `Filter(liste, Kol = pl.ID)` i OnStart | `Set(varX, pl.ID)` først, og filtrér mod `varX` |
| `LookUp(liste, Title = IT.Felt)` inde i et `ForAll` | Slå op i den **navngivne formel**, der i forvejen har rækkerne. Den er hentet én gang og cachet |
| `Filter(liste, Kol = P.Value)` pr. værk i en navngiven formel | Hent listen **én gang** til en samling, og del den op i hukommelsen |

**Regel 30** læser både skærmen og `App.pa.yaml` og stopper byggeriet, hvis
et filter mod en SharePoint-liste sammenligner mod et scope-felt.

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

Den er en advarsel, fordi VH-plan engang havde otte af dem. I dag har ingen
app nogen (efterprøvet i `REVIEW.md`), så reglen kan gøres til en fejl.
NB: den læser kun skærmen, ikke `App.pa.yaml`.

## Synkronisér til Studio

Uden agent, i en terminal — samme MCP-server, uden credits:

```powershell
python tools\canvas_mcp.py deploy --app biosap
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
`CANVAS_ENV` for byggescripterne, så alle apps bygges mod **det samme**
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
python tools\canvas_mcp.py deploy --app biosap --clean
```

`--clean` sender først en tom skærm og derefter den rigtige, så hele
træet bygges på ny i filens rækkefølge. Brug den altid, når en ændring
flytter en kontrol til en ny forælder.

Den tomme udgave sendes **uden `App.OnStart`**: OnStart sætter variabler
til `Blank()`, og deres type kan kun udledes af kontroller, der bruger dem
— på en tom skærm er der ingen. **Og en fejlet compile er ikke uden
virkning:** Studio tog imod den tomme skærm, selvom valideringen fejlede.
Derfor sendes den rigtige skærm altid bagefter, og det er dens compile,
der afgør, om deployet lykkedes.

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

**Apperne bygges af Python-builderne.** Eksporten
indeholder også appene som `.msapp` — de er *resultatet* af sidste deploy,
ikke kilden til den næste. Retter nogen i en `.msapp` eller pakker
solutionen tilbage, er ændringen væk ved næste `python3 tools/build_all.py`,
og så er der to sandheder om den samme skærm.

`.msapp`-filerne er derfor i `.gitignore` (og ikke i git). Men så kunne YAML'en inde i dem
heller ikke læses fra repoet, og en app, der *kun* findes i solutionen —
fx de ældre KKS- og BIOSAP-apps — var dermed en sort kasse for alle andre end
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
5. **Brug konstruktioner, der allerede findes i skærmen.** `themed_dropdown`,
   `ModernCombobox` til søg-og-vælg (`tools/fl_picker.py`), gallery med `ModernCheckbox`, vandret
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

### Functional Location: én `ModernCombobox` — `tools/fl_picker.py`

**`Classic/ComboBox` må stadig ikke bruges til søgning.** Den fik 819
Functional Locations fra flowet og viste nul — dens indbyggede filter lå i
et lag, der ikke kunne ses.

FL-feltet er nu **én `ModernCombobox` + Search-knap** i alle tre apps, der
har det (VH-plan, Equipments, Materials, issue #63/#68). Det er den samme
funktion, `fl_picker()`, og den samme flow-kontrakt, `build_flsearch.py`:

- Search er deaktiveret under 7 tegn. Search kalder flowet **én** gang;
  derefter filtrerer comboboksen svaret lokalt, uden nye kald.
- **Listen indeholder kun rigtige resultater** (issue #72) — ingen
  søgerække, ingen hjælpetekst. Derfor søger Enter ikke; Search gør.
- **Første resultat vælges automatisk** (`pick_var` + `Reset`), og valget
  bliver stående, til der søges igen, nulstilles lokalt eller vælges om.
- Status ("6 Functional Locations found for …", søger, ingen fund, fejl)
  står **under** feltet i alle tre apps.
- **Mens flowet kører**, står knappen stille (samme størrelse, deaktiveret,
  uden tekst), og én `ModernSpinner` drejer i en fast plads lige til højre.
  Rækken har 2 px luft over og under, så knappens fokusring ikke klippes.
- Comboboksen har samme hjørner (10), kant og fyld som de andre felter.
- **Reset er lokal:** `fl_picker.reset_fx()` rydder kun den vælgers egne
  variabler og samling.
- En ny søgning rydder gamle resultater, valget og (VH-plan) objektvalget.
- Objektlisten (VH-plan) er et **galleri med én `ModernCheckbox` pr.
  række** — koden og beskrivelsen er afkrydsningens egen etiket. Knappen
  viser antallet (`Object List (3)`), får den fælles grønne
  udfyldt-tilstand (`build_helpers.mark_done`), er deaktiveret uden en
  gyldig FL og viser de valgte som `Tooltip`.

**Efterprøv i Studio mod rigtige data**, hvis comboboksen nogensinde viser
færre rækker end samlingen har — mistænk kontrollens eget filter før dine
egne formler.

## Navigation mellem apps: `LaunchTarget.Replace`

> **Den samlede app (`BIO SAP App/`) er undtagelsen.** Dér er domænerne
> skærme, og navigationen er `Navigate()`. Dens bygger sætter
> `side_nav.SCREENS` og `build_hub.NEW_ACTION`/`OPEN_ACTION`. Uden dem
> (de fem enkelte apps) gælder alt nedenfor uændret. Ret aldrig et domæne
> i den samlede apps `build/`: den har ingen skærmbyggere, kun
> kompositionen. Se `BIO SAP App/README.md`.

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

- VH-plan, Equipment og Material bruger flowet `BioSap-Integration-FunctionalLocations`. Svarer flowet
  anderledes end forventet, rettes konstanterne i `tools/build_flsearch.py` —
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

# 25 – Standardisering af de fire apps og af Python-builderne

Oplæg til beslutning. **Intet er ændret endnu.** Alt nedenfor er målt på
repoet som det står i dag (bygget og efterprøvet med
`python3 tools/build_all.py` — alt grønt, og byggeriet er deterministisk:
`git status` er rent bagefter).

De fire apps er bygget løbende, og det kan ses. De er ikke *forkerte* —
de er *forskellige*, hvert sted hvor en beslutning blev taget i den ene app
en måned før den anden. Det her er listen over de steder.

---

## Sammenfatning: hvad der bør gøres, i den rækkefølge

| # | Emne | Hvorfor | Omfang | Risiko |
|---|---|---|---|---|
| 0 | **Client secret ligger i git** | Den er offentliggjort og kan ikke slettes bagud | Timer | Ingen kodeændring |
| 1 | **Ét farvemodul** (`palette.py`) | Farverne står 3 steder i dag, 2 af dem som rå tal | 1 dag | Lav |
| 2 | **Én regel for feltfarvning** | Fire forskellige regler i dag — se §3 | 1 dag | Lav, men **synlig** |
| 3 | **Ét sted for miljø og app-id'er** | Samme id står 3–4 steder, holdt sammen af en regex-vagt | ½ dag | Lav |
| 4 | **Fjern de duplikerede builder-filer** | 5.300 af 16.754 linjer Python er ordrette kopier | 2 dage | Middel |
| 5 | **check_layout er delvis blind i 3 af 4 apps** | Den regner kun VH-plans variabelnavne ud | 1 dag | Lav |
| 6 | **AccessibleLabel = kontrolnavnet** | 75 felter læser `inpManufacturer` op for en skærmlæser | ½ dag | Lav |
| 7 | **Døde filer og forældede dokumenter** | 996 linjer + README siger stadig "to apps" | 2 timer | Ingen |
| 8 | **Navngivning: `varVhp` / `varDom` / `gbl`** | Tre konventioner til samme slags tilstand | — | **Frarådes**, se §8 |

Punkt 0–3 er dem, spørgsmålet handlede om. Punkt 4–7 er det, gennemgangen
af builderne fandt undervejs.

---

## 0. Det haster: en client secret ligger i git-historikken

```
solution/BIOSAP/src/environmentvariabledefinitions/
    orsted_BioSapWOCClientSecret/environmentvariabledefinition.xml:
        <defaultvalue>9yk8Q~…</defaultvalue>
solution/BIOSAP/src/Workflows/BioSap-Integration-FunctionalLocations-….json:13
solution/BIOSAP/src/Workflows/BioSap-Integration-Order-Objects-….json:34
```

Samme værdi, tre filer, committet i `ad4128d "Solution-eksport 19-09-2026"`.

`tools/scrub_solution.py` skulle have fanget den, og gjorde det ikke.
Årsagen er præcis identificerbar: scriptet afgør hemmeligheden ud fra
**feltnavnet**, og felterne her hedder `defaultvalue` og `defaultValue` —
ord der ikke står i `SECRET_WORDS`. Det er variablens *navn*
(`…WOCClientSecret`), der afslører den, og det navn kigger scriptet ikke på.

**Forslag, i den rækkefølge:**

1. **Rul hemmeligheden i Entra ID.** Det er det eneste, der virker. At
   slette filen hjælper ikke — historikken bliver. Scriptets egen docstring
   siger det: *"Lander det paa GitHub, kan det ikke kaldes tilbage."*
2. Udvid `scrub_solution.py` med to regler:
   - **Mappe- og filsti tæller med.** Ligger et felt under en
     `environmentvariabledefinitions/<navn>/`-mappe, hvor `<navn>` matcher
     `SECRET_WORDS`, er værdien hemmelig — uanset hvad feltet hedder.
   - **`defaultvalue`/`defaultValue` er altid mistænkt** i en
     miljøvariabel-definition. En miljøvariabel *skal* ikke have sin værdi
     med i eksporten (Microsofts egen anbefaling: definitionen hører til
     solutionen, værdien til miljøet).
3. Kør `tools/scrub_solution.py solution --report-only` som et trin i
   byggeriet, ikke kun i hånden efter eksport.

---

## 1. Farverne: ét modul, ikke tre steder

### Sådan er det i dag

| Sted | Hvad | Form |
|---|---|---|
| `gen_screen.py` ×4 kopier | 20 navngivne konstanter (`C_TITLE`, `C_VALID_FG`, …) | Navne |
| `hub_config.py` | 8 statusfarvepar + 5 domænefarver | **Rå RGBA-tal** |
| `build_modal.py`, `build_diag_screen.py` | 8 løse literaler | **Rå RGBA-tal** |

Og de overlapper. Hver eneste statusfarve i `hub_config.py` er en farve,
der allerede har et navn i `gen_screen.py`:

```
RGBA(21, 127, 92, 1)    = C_VALID_FG     (grøn forgrund)
RGBA(232, 245, 238, 1)  = C_VALID_BG
RGBA(0, 83, 140, 1)     = C_INFO_FG
RGBA(222, 240, 252, 1)  = C_INFO_BG
RGBA(179, 50, 60, 1)    = C_INVALID_FG / C_REQUIRED
RGBA(253, 236, 236, 1)  = C_INVALID_BG
RGBA(89, 102, 122, 1)   = C_MUTED / C_NEUTRAL_FG   (står som C_MUTED_ i hub_config)
RGBA(228, 233, 241, 1)  = C_DIVIDER / C_NEUTRAL_BG
RGBA(0, 103, 174, 1)    = C_PRIMARY       (= FL-domænets flisefarve)
```

Otte ud af ni. Kun to par er nye og har ikke et navn i paletten:
advarselsparret `RGBA(138, 90, 0, 1)` / `RGBA(253, 243, 226, 1)`
("Afventer info") og de fire domænefarver for EQ, MP, MAT og VHP.

Konsekvensen er ikke teoretisk. Skifter nogen `C_VALID_FG`, fordi den grønne
er for mørk, skifter kanten om et udfyldt felt farve i alle fire apps — og
statuschippen "Created in SAP" på landingssiden gør det **ikke**. De var den
samme farve, og nu er de to grønne, der ligner hinanden næsten.

### Forslag

Ét modul, `palette.py`, som den eneste kilde:

```python
# palette.py
# --- rå ---------------------------------------------------------------
INK        = "RGBA(26, 34, 49, 1)"
MUTED      = "RGBA(89, 102, 122, 1)"
…
# --- semantiske roller ------------------------------------------------
OK_FG, OK_BG         = GREEN, GREEN_TINT
WARN_FG, WARN_BG     = AMBER, AMBER_TINT
ERROR_FG, ERROR_BG   = RED,   RED_TINT
INFO_FG, INFO_BG     = BLUE,  BLUE_TINT
NEUTRAL_FG, NEUTRAL_BG = MUTED, MIST
# --- domæner ----------------------------------------------------------
DOMAIN = {"FunctionalLocation": PRIMARY, "Equipment": TEAL, …}
```

`gen_screen.py` importerer den og beholder sine `C_*`-navne som aliaser, så
ingen builder skal røres i første omgang. `hub_config.py` holder op med at
have tal i sig og skriver `OK_FG` i stedet. De otte løse literaler i
`build_modal.py` og `build_diag_screen.py` får navne — `RGBA(15, 23, 42, 0.35)`
er "modal-sløret", og det bør den hedde.

Og så én ny regel, håndhævet af et tjek på linje med de andre:

> **Ingen builder må indeholde en `RGBA(`-literal.** Farver kommer fra
> `palette.py`.

Det er en femlinjers regex over `*/build/*.py` og kan ligge i
`tools/build_all.py` ved siden af `check_shared()`.

### Om miljøvariabler til farver — og hvorfor jeg fraråder det

Idéen er rigtig tænkt: farven hører til opsætningen, ikke til koden. Men
Power Platform kan ikke levere den den vej, uden at det koster mere end det
smager. Efterprøvet på Microsoft Learn:

- Miljøvariabler af typen **Data source** kan canvas apps bruge direkte —
  det er præcis dét, `orsted_BioSapListMaintenancePlans` og de andre 20
  gør i dag, og **det er rigtigt brugt.**
- Miljøvariabler af typen **Text** eller **JSON** kan en canvas app
  **ikke** læse fra Power Fx. De to eneste veje er (a) Dataverse-tabellerne
  `Environment Variable Definition`/`Value` som datakilde, eller (b) et
  cloud flow, der kalder `RetrieveEnvironmentVariableValue`. Begge er et
  **opslag ved opstart**.
- Oven i: *"It may take up to an hour to fully publish updated environment
  variables"* — værdien slår ikke igennem med det samme.

Et opslag ved opstart for at vide, hvilken grøn en kant skal have, bryder
med appernes egen vigtigste ydelsesregel (SKILL.md: *"Ingen datahentning i
App.OnStart"*), og indtil svaret er der, har felterne ingen farve. Farver
er heller ikke det, miljøvariabler er til: de er til det, der **er
forskelligt mellem DEV og PROD**. Den grønne er den samme begge steder.

**Farver hører i `palette.py` og bages ind ved bygning.** Skal de kunne
skiftes uden en udvikler, er det rigtige svar én rettelse i `palette.py`
plus `python3 tools/build_all.py` — fire sekunder, og fire apps skifter
sammen.

---

## 2. Feltfarvning: fire regler, hvor der skulle være én

Det her er den, der er mest synlig for brugeren, og den er værre end den ser
ud. Målt på de byggede skærme:

| Kontrol | Hvad `BorderColor` faktisk bliver |
|---|---|
| `text_input` **uden** `required` | **Ingen `BorderColor` overhovedet** → platformens standardkant |
| `text_input` **med** `required` | Rød når tom, grå når tom-og-ikke-krævet, **grøn når udfyldt** |
| `number_input` (altid) | Rød/grå/**grøn** — også når feltet ikke er krævet |
| `dropdown` (altid) | Rød/grå/**grøn** — også når feltet ikke er krævet |
| `ModernDatePicker` | **Fast grå.** Aldrig rød, aldrig grøn |
| `combobox` (ubrugt) | Kun rød/grå — **ingen grøn** |

Det er ikke en teoretisk uoverensstemmelse. I Equipment-appens formular
står de her fire ved siden af hinanden:

```
inpManufacturer      (tekst, ikke krævet)   → ingen farve, nogensinde
inpWarrantyStart     (dato)                 → altid grå
DeliveringTime       (tal, ikke krævet)     → bliver GRØN når man skriver i den
inpDomText           (tekst, krævet)        → rød med det samme
```

Årsagen sidder ét sted: `build_helpers.py` sætter kun `BorderColor` på
`text_input`, når `required_formula != "false"` — mens `number_input` og
`dropdown` sætter den ubetinget. Datovælgeren er slet ikke i
`build_helpers.py`; den er bygget i hånden inde i `build_domain.py` med en
fast `BorderColor` og **uden** den `Fill`-regel, alle andre felter har
("gråt = kan ikke redigeres"). En dato i visningstilstand ser derfor
redigerbar ud.

### Og en regel mere, der er forskellig mellem apperne

*Hvornår* bliver kanten rød?

- **VH-plan:** `varVhpPlanValidated && IsBlank(…)` — rød først når brugeren
  har trykket **Validér**.
- **Equipment/Material:** `true && IsBlank(…)` — rød fra det sekund
  formularen er tom, før brugeren har rørt noget.

Så den samme app-familie siger to forskellige ting om rødt: i VH-plan
betyder det "du har bedt mig tjekke, og det her mangler"; i Equipment
betyder det "der er et tomt felt". Den sidste lærer brugeren at se bort fra
rødt.

### Forslag: én funktion, fire tilstande

```python
def border_rule(kind, required="false", value_test=None):
    """Den ENE regel om, hvad en feltkant siger.

        krævet + tom         -> ERROR_FG    (der mangler noget)
        udfyldt              -> OK_FG       (den er i hus)
        tom + ikke krævet    -> CARD_BORDER (neutral)
        kan ikke redigeres   -> CARD_BORDER + grå Fill
    """
```

Alle fem inputbyggere — inkl. en ny `date_picker()` flyttet **ind** i
`build_helpers.py` — kalder den. Ingen kontrol sætter `BorderColor` selv.

Og så skal der træffes ét valg, som er et produktvalg og ikke et teknisk:

> **Skal grøn betyde "udfyldt" eller "valideret"?**
>
> - *Udfyldt* (som i dag): billigt, men et grønt felt kan indeholde vrøvl.
> - *Valideret* (VH-plans model, udvidet): grøn betyder "godkendt af
>   regelsættet". Dyrere, men farven betyder så noget.
>
> Min anbefaling: **grøn = udfyldt, rød = mangler efter Validér.** Altså
> VH-plans tidspunkt for rødt i alle fire apps, og den nuværende grønne
> betydning. Det er den mindste ændring, der gør de fire apps ens, og den
> fjerner "rød fra første sekund", som er den eneste af de fire regler,
> der aktivt skader.

**Det her er den ændring, der kan ses.** Den bør laves i én app først,
deployes, og ses på, før de tre andre følger efter.

---

## 3. Links og id'er: ét sted i stedet for fire

Miljø-id'et `e0f8f822-…` og de fire app-id'er står i dag i:

```
tools/canvas_apps.json              environment_id + 4 × app_id
Masterdata Hub/build/hub_config.py  ENV_ID + 5 × app_id (DOMAINS)
Equipment App/build/domain_config.py   PLAY_URL + HUB_URL
Material App/build/domain_config.py    PLAY_URL + HUB_URL
Maintenance Plan App/build/sp_config.py  HUB_URL
```

Det er erkendt i dag, og løsningen er `check_app_ids()` i `build_all.py`:
60 linjer, der læser `hub_config.py` med `import` og de tre andre filer med
**regex** — inklusive den her, som skal læse en streng, der er brækket over
tre linjer:

```python
joined = "".join(re.findall(r'"([^"]*)"',
                 re.search(r"HUB_URL\s*=\s*\((.*?)\)", f.read(), re.S).group(1)))
```

Den vagt er skrevet, fordi fejlen gør ondt (brugeren trykker "Open" og
lander i en tom app). Men en vagt over fire kopier er stadig fire kopier.
Bliver `HUB_URL` skrevet som én lang linje i stedet for tre, fejler regex'en
tavst, og vagten holder op med at vagte.

### Forslag

Én fil, `tools/environments.json`, som alle læser:

```json
{
  "default": "dev",
  "dev": {
    "environment_id": "e0f8f822-…",
    "environment_category": "prod",
    "sharepoint_site": "https://<tenant>.sharepoint.com/sites/<site>",
    "apps": {
      "hub":       { "navn": "Masterdata Hub", "folder": "Masterdata Hub",       "app_id": "f387047d-…" },
      "vhplan":    { "navn": "VH-plan",        "folder": "Maintenance Plan App", "app_id": "11fa8d90-…" },
      "equipment": { "navn": "Equipments",     "folder": "Equipment App",        "app_id": "24bf3bbc-…" },
      "material":  { "navn": "Materials",      "folder": "Material App",         "app_id": "d7762919-…" }
    }
  },
  "prod": { … }
}
```

- `hub_config.py`, `domain_config.py` og `sp_config.py` får `ENV_ID`,
  `PLAY_URL` og `HUB_URL` **derfra** i stedet for at have dem skrevet i sig.
- `check_app_ids()` **slettes** — 60 linjer forsvinder, og den fejlklasse,
  den vogtede over, kan ikke længere opstå.
- `tools/build_all.py --env prod` bygger med produktionsmiljøets id'er.
  Det er dén ALM-gevinst, spørgsmålet om miljøvariabler egentlig var ude
  efter, og den kommer uden et opslag ved opstart.

**Det, der bliver ved med at høre hjemme i rigtige miljøvariabler,** er
SharePoint-site og listenavne — og de er der allerede, som Data
source-variabler (`orsted_BioSapSiteUrl` + 20 listevariabler). Det er
korrekt brugt og skal ikke laves om.

---

## 4. Python-builderne: 32 % af koden er ordrette kopier

16.754 linjer Python i alt. Heraf er ca. **5.300 linjer kopier af noget,
der også står et andet sted:**

| Fil | Linjer | Kopier | Spildt |
|---|---|---|---|
| `check_layout.py` | 561 | 4 | 1.683 |
| `build_helpers.py` | 494 | 4 | 1.482 |
| `build_domain.py` | 877 | 2 | 877 |
| `gen_screen.py` | 228 | 4 | 684 |
| `build_flsearch.py` | 171 | 3 | 342 |
| `attflows.py` | 216 | 2 | 216 |
| `generate_app_onstart.py`, `assemble_screen.py` | ~100 | 2 | ~100 |

Det er bevidst, og begrundelsen står i `build_all.py`:

> *"Power Apps' egen VS Code-vaerktoejskaede arbejder pr. app-mappe, og et
> delt modul udenfor mappen blev fjernet igen af den."*

**Den begrundelse holder formentlig ikke længere.** Deploy går i dag gennem
`tools/canvas_mcp.py`, og `stage()` kopierer **kun `*.pa.yaml`** over i
`.canvas-deploy/`. MCP-serveren ser aldrig `build/`-mappen. Grunden til at
mappen skulle være selvbærende, gjaldt VS Code-arbejdsgangen — og den er
ikke længere den dokumenterede vej.

### Forslag: `shared/` som kilde, kopierne som resultat

Den sikre version, som holder *begge* dele:

1. De fælles filer flytter til `shared/` i roden og bliver **den eneste
   kilde**.
2. `tools/build_all.py` **kopierer** dem ud i hver `build/`-mappe, før den
   bygger — i stedet for at sammenligne dem, som den gør nu.
3. De udkopierede filer kommer i `.gitignore`.

Så er hver `build/`-mappe stadig selvbærende på disken (hvis
VS Code-værktøjskæden en dag skal bruges igen, virker den), men der er
kun ét sted at rette, og `check_shared()` kan slettes: drift er ikke
længere mulig, fordi kopien laves forfra hver gang.

**Prøv med én fil først.** Flyt `gen_screen.py` (den mindste og mest
stabile), kør fuld bygning, deploy én app, og se at intet ændrer sig.
Derefter resten.

### Undervejs: `build_domain.py` er også VH-plans kode

`build_flsearch.py` står i tre apps. `attflows.py` i Equipment og Material,
og `build_attflows.py` i VH-plan er en **nær** kopi af den — ikke en ordret
en, så `check_shared()` kigger ikke på den. To flow-kontrakter mod de samme
tre attachment-flows, der kan glide fra hinanden uden at nogen ser det.
De bør blive til én.

---

## 5. `check_layout.py` er delvis blind i tre af fire apps

Filen er ordret ens i alle fire build-mapper. Men dens `evaluate()` kender
kun **VH-plans** navne:

```python
e = e.replace("CountRows(colVhpItems)", str(n_items))
e = re.sub(r"\bvarVhp[A-Za-z0-9_]*\b", "True", e)
```

Møder den `varDomActiveRowId` eller `colDomRows`, kan udtrykket ikke
regnes ud, og funktionen returnerer `None` — hvilket betyder "spring over",
ikke "fejl". Målt:

| App | Height-formler | Kan efterregnes |
|---|---|---|
| Masterdata Hub | 83 | 79 (95 %) |
| Maintenance Plan App | 404 | 362 (89 %) |
| Equipment App | 151 | **134 (88 %)** |
| Material App | 148 | **130 (87 %)** |

12 % lyder harmløst. Det er det ikke, for det er ikke tilfældige 12 %.
De containere, der springes over i Equipment, er:

```
conDomShell      conDomSplit     conDomLeft      conDomRight
conDomFormCard   conDomRowsCard  conDomAttCard   galDomRows
```

Altså **skærmens skal og alle fire kort**. Netop de containere, hvis højde
afhænger af data og tilstand, og netop dem, hvor fejlen "kortet er 36 px
for lavt" opstod i første omgang. `check_layout.py` melder "Layout-tjek OK"
for Equipment og Material uden at have set på et eneste af de kort, der
bærer indholdet.

### Forslag

Substitutionerne flytter ud af `check_layout.py` og ind i en lille
app-specifik fil — `layout_fixtures.py` — som hver app ejer:

```python
# Equipment App/build/layout_fixtures.py
VAR_PREFIX = "varDom"
COUNTS = {
    "CountRows(colDomRows)": [0, 1, 3, 8],
    "CountRows(Filter(colDomAttachments, RowId = varDomActiveRowId))": [0, 1, 5],
}
```

`check_layout.py` bliver dermed *rigtigt* app-uafhængig — i dag er den kun
ordret ens, ikke ens i hvad den gør — og kan flytte til `shared/` sammen
med de andre.

Bagefter bør tjekket køres igen på Equipment og Material. **Det er
sandsynligt, at det finder noget**, for de kort har aldrig været efterregnet.

---

## 6. `AccessibleLabel` er kontrollens navn

`build_helpers.py` sætter på hvert input:

```python
"AccessibleLabel": f"\"{name}\"",
```

`name` er kontrolnavnet. En skærmlæser siger derfor "inp Manufacturer"
i stedet for "Fabrikat". Målt på de byggede skærme:

| App | AccessibleLabels | Heraf kontrolnavnet |
|---|---|---|
| Maintenance Plan App | 267 | **38** |
| Material App | 90 | **19** |
| Equipment App | 91 | **18** |
| Masterdata Hub | 50 | 0 |

Hubben gør det rigtigt — den har ingen råtekst-inputs. De tre andre har 75
felter tilsammen.

Rettelsen er lille og sidder ét sted: `field_cell()` kender allerede
etiketten (`label_text`) og bygger `<label>`-rækken af den. Den skal give
den videre til `input_ctrl`, og inputbyggerne skal tage imod et `label=`
i stedet for at falde tilbage på `name`.

`canvas-authoring-get_accessibility_errors` køres allerede ved hvert deploy
(`checkers()` i `canvas_mcp.py`) — så det er værd at se efter, om den
allerede melder det, og i så fald hvorfor det er blevet stående.

---

## 7. Døde filer og forældede dokumenter

**996 linjer, der ikke gør noget.** SKILL.md nævner de fem første som
"historiske og bruges ikke" — så de kan lige så godt slettes:

```
Maintenance Plan App/build/build_diag_screen.py    ikke importeret af noget
Maintenance Plan App/build/build_vhplan_screen.py  —
Maintenance Plan App/build/gen_options.py          —
Maintenance Plan App/build/gen_tasklists.py        —
Maintenance Plan App/build/rename_collections.py   —
Maintenance Plan App/build/colOptions.txt          mellemresultat
Maintenance Plan App/build/colOptions_renamed.txt  —
Maintenance Plan App/build/colTasklists.txt        —
Maintenance Plan App/build/colTasklists_renamed.txt —
Maintenance Plan App/build/diff_materialer.txt     —
```

Git husker dem. At lade dem ligge koster, at den næste, der læser mappen,
skal finde ud af, hvilke af de 27 filer der er levende.

**Tre dokumenter siger stadig "to apps":**

- `README.md` — *"Canvas apps og indmeldingsflow til SAP masterdata. To apps i dag"* og en tabel med to rækker
- `.github/copilot-instructions.md` — *"Repoet indeholder to Power Apps canvas apps"*
- `.github/skills/canvas-build/SKILL.md` — overskriften siger fire, men
  `description` i frontmatter nævner kun VH-plan og Hub, og teksten siger
  flere steder "begge apps", hvor der menes fire

`README.md` er den, en ny læser møder først. Den bør have en
fire-rækkers tabel og et afsnit om, at Equipment og Materials er **den
samme app med to konfigurationsfiler** — det er den enkeltoplysning, der
sparer mest tid.

`checkpoints/index.md` er en tom tabel med en overskrift. Enten bruges den,
eller også ryger den.

---

## 8. Navngivning: `varVhp` / `varDom` / `gbl` — lad den være

For fuldstændighedens skyld, siden gennemgangen var "alt ensartet":

| App | Variabler | Samlinger | Kontroller |
|---|---|---|---|
| Masterdata Hub | `gblMe`, `gblView`, `gblDomain` | (ingen) | `txt…`, `con…`, `btn…`, `gal…` |
| Maintenance Plan | `varVhp…` (1.518 forekomster) | `colVhp…` (591) | samme + `drp`, `num`, `chk` |
| Equipment/Material | `varDom…` (387/378) | `colDom…` (97) | samme, men `inp…` i stedet for `txt…` for inputs |

Tre konventioner. Kontrolpræfikserne er derimod ens overalt på nær én ting:
Equipment/Material bruger `inp` for inputs, hvor VH-plan bruger `txt`.

**Jeg fraråder at rette det.** Gevinsten er kosmetisk, og prisen er en
omdøbning af 2.900 navne fordelt over formler, der refererer hinanden på
kryds — nøjagtig den slags ændring, hvor en enkelt overset reference først
melder sig ved compile, og hvor `check_layout.py`'s regel 7 kun fanger
nogle af dem.

Det, der er værd at gøre i stedet: **skriv konventionen ned** i SKILL.md —
`gbl` = på tværs af skærme, `var` = skærmens tilstand, `col` = samlinger,
og app-præfikset (`Vhp`/`Dom`/ingen) fortæller hvilken app. Så vokser den
næste app ikke en fjerde konvention.

Hvis noget skal ensrettes, er det **`inp` vs `txt`** i de to domæneapps.
Det er ~15 navne pr. app og sidder ét sted i `build_domain.py`. Men det kan
vente til en gang, hvor de filer alligevel skal røres.

---

## Foreslået rækkefølge

**Runde 1 — koster ingen deploy, kan ikke gå galt** (½ dag)
- §0 rul hemmeligheden, udvid `scrub_solution.py`
- §7 slet de døde filer, ret README, copilot-instructions og SKILL.md

**Runde 2 — strukturen, uden at ændre en eneste genereret linje** (2 dage)
- §1 `palette.py`, med `C_*` bevaret som aliaser
- §3 `tools/environments.json`, `check_app_ids()` slettes
- §4 `shared/`, én fil ad gangen, `gen_screen.py` først

Efter hver af de to skal `python3 tools/build_all.py` give **ordret samme
YAML** som i dag. Det er kravet, og det er nemt at efterprøve: `git diff`
på `*.pa.yaml` skal være tom. Ingen deploy nødvendig.

**Runde 3 — nu ændrer skærmene sig** (2 dage + test)
- §5 `layout_fixtures.py`, kør tjekket på Equipment og Material, ret hvad
  det finder
- §6 `AccessibleLabel` fra etiketten
- §2 **den fælles feltfarvningsregel** — én app først (Equipment, som er
  den mindste og har den værste variant i dag), deploy, se på den, og så
  de tre andre

**Det, der ikke gøres:** farver i miljøvariabler (§1), omdøbning af
`varVhp`/`varDom` (§8).

---

## To ting der bør besluttes, før runde 3 går i gang

1. **Hvornår bliver en feltkant rød?** Efter Validér (VH-plan i dag) eller
   med det samme (Equipment i dag)? Min anbefaling er "efter Validér" — men
   det er et brugervalg, ikke et teknisk.
2. **Skal Equipment og Materials blive ved at være én app med to
   konfigurationer?** Alt nedenfor bygger på, at svaret er ja. Skal de
   udvikle sig hver for sig, er `shared/`-flytningen i §4 den forkerte
   retning, og så skal den diskuteres først.

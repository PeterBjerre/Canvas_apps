# Equipment- og Materials-appen

> **RETTELSE (senere samme dag).** Afsnittet nedenfor holder for
> solution-eksporten, men **ikke** for apperne, som de står i Studio.
> Et skærmbillede af Equipment-appen viser en udfyldt formular — Status,
> Plant, Fabrikat, typebetegnelse, tre functional-location-felter,
> garantidatoer, dokumenttype og en søgbar *Saved Rows*-liste.
>
> Eksporten viser altså ikke appen. Se **"Eksporten viser ikke appen"**
> nedenfor. Feltmodellen i `domain_config.py` er derfor stadig et forslag,
> og `folder` er sat til `null` i `tools/canvas_apps.json`, så et deploy
> ikke kan overskrive det, der er bygget i Studio.

## Hvad solution-eksporten indeholder

Første skridt var at læse dem. Det tog ingen tid:

```
orsted_equipments_ebf7d.src/Src/App.pa.yaml       App: Theme = PowerAppsTheme
orsted_equipments_ebf7d.src/Src/Screen1.pa.yaml   Screen1: LoadingSpinnerColor
orsted_materials_8feca.src/Src/...                byte for byte det samme
```

To filer hver, 628 og 667 bytes, `DataSources: []`. Det er den blanke
skabelon, Power Apps laver, når man trykker "Ny app" — én tom `Screen1`,
ingen kontroller, ingen datakilder. **Der var ikke noget at læse sig til.**

Solutionen indeholder desuden tre ældre skaller af samme slags:
`cr871_equipment_bd0a4` ("Equipment"), `cr871_kks_ca72e` ("KKS") og
`orsted_materialer_93a70` — den sidste hedder "Test" indeni. Alle tre er
byte for byte identiske med de to nye.

Felterne nedenfor er derfor **valgt her, ikke aftalt.** De følger SAP's
stamdatatransaktioner, og de står ét sted, så de er billige at rette.

## Eksporten viser ikke appen

Skærmbilledet og eksporten kan ikke begge have ret. Eksporten siger om
`orsted_equipments_ebf7d` ("Equipments"):

| Felt i `meta.xml` / `identity.json` | Equipments | VH-plan (til sammenligning) |
|---|---|---|
| `ConnectionReferences` | `{}` | 14 SharePoint-lister + et flow |
| `CdsDependencies` | `[]` | to afhængigheder |
| Kontroller i `identity.json` | **4** (`App`, `Host`, `Screen1`, `Test_…`) | flere hundrede |
| `Src/` i `.msapp` | `App.pa.yaml` + `Screen1.pa.yaml` | 3 filer, 778 KB |

En app med Status- og Plant-**dropdowns**, en søgbar liste og en
Export-knap kan ikke have `ConnectionReferences: {}`. Den eksporterede
`Equipments` er altså **ikke** appen på skærmen.

Og søgningen efter skærmbilledets egne tekster — `Equipment Drift`,
`Fabrikat`, `Garanti start`, `Rum koordinater` — giver **nul træffere i
hele eksporten**, på tværs af alle ni apps.

To forklaringer, og de kræver hver sin handling:

1. **Det er to forskellige apps.** App-id'et i Studio-URL'en er
   `24bf3bbc-…`, og den redigeres i solution `43fe3e8a-…`. Er det ikke
   BIOSAP, kommer appen aldrig med i en BIOSAP-eksport, uanset hvor mange
   gange den køres.
2. **Eksporten tog en ældre udgave.** En canvas app i en solution
   eksporteres fra den gemte/publicerede udgave — ikke fra det, der ligger
   i Studio-fanen lige nu.

Indtil det er afgjort, er `folder` sat til `null` i
`tools/canvas_apps.json`, og `app_dir()` i `canvas_mcp.py` afviser deploy
med en forklaring. **`pull` virker stadig** — den skriver i
`.canvas-sync/` og rører ikke `folder`:

```powershell
python tools\canvas_mcp.py pull --app equipment
python tools\canvas_mcp.py pull --app material
```

Det henter appen ned **fra den kørende Studio-session** og går dermed helt
uden om solution-eksporten. Det er den korteste vej til at se de rigtige
felter.

## Hvad der blev bygget

| | |
|---|---|
| `sharepoint/provision/Provision-EqMatLists.ps1` | De fire lister |
| `Equipment App/` | Builderne til EQ-appen |
| `Material App/` | Builderne til MAT-appen |
| `Masterdata Hub/build/hub_config.py` | Fliserne bygger nu URL'en af `ENV_ID` + `app_id` |

## Listerne

To pr. domæne — en header og en postliste. Det er den samme opdeling som
VH-plan-appen, og af samme grund: én indmelding dækker typisk flere
objekter, og de skal kunne redigeres hver for sig.

```
EquipmentRequests  ── RequestNo (EQ-000912), Status, Plant, ShortText, ...
      │
      └── EquipmentItems  ── ItemKey (EQ-000912-001), 36 SAP-felter
                                 │
                                 └── TaskListDocuments/EQ-000912-001/
```

`MaterialRequests` / `MaterialItems` er bygget ens, med 45 felter fra MM01.

**Headeren er ens for de to domæner** — derfor én PowerShell-funktion og
ikke to næsten ens blokke. Det er posterne, der er forskellige.

### Nummeret kommer fra SharePoint

`RequestNo` er `"EQ-" & Text(<rækkens ID>, "000000")`. Rækken oprettes
først, og dens ID bliver til nummeret.

Det kræver ingen tæller, intet flow, og ingen aftale mellem to apps om hvem
der uddeler numre — og to brugere, der gemmer samtidig, kan ikke få det
samme nummer. Prisen er et ekstra `Patch` lige efter oprettelsen.

### Postens nøgle er også mappenavnet

`ItemKey` er `<indmelding>-<linje>`: `EQ-000912-001`. Den er unik på tværs
af *alle* domæner, fordi præfikset er det — og det er nødvendigt, for de
tre apps deler ét dokumentbibliotek.

## Attachments: samme tre flows, samme bibliotek

De tre flows er **hårdkodede** til biblioteket `TaskListDocuments`:

```
BioSap-TaskListAttachment        CreateFile i /TaskListDocuments/<text>/
BioSap-GetSubmittedAttachments   text = "TaskListDocuments/<mappe>"
BioSap-DeleteSubmittedAttachments  text = Identifier
```

Et bibliotek pr. domæne ville kræve **tre nye flows pr. domæne — ni i alt**
— for at gøre præcis det samme. De tre apps deler derfor biblioteket og
holdes fra hinanden på mappenavnet: `MI0007`, `EQ-000912-001`,
`MAT-001233-002`.

Prisen er, at biblioteket hedder `TaskListDocuments`, selv om det nu også
rummer udstyr og materialer. Det er et navn, ikke en fejl.

`attflows.py` er ordret ens i de to build-mapper, og den er skrevet ud fra
det, VH-plan-appen lærte:

- **Svaret bliver læst.** `flowrunsuccess` samles pr. fil i `colDomAttUp`,
  og de filer, der ikke kom igennem, står med navn i beskeden. VH-plan-appen
  kvitterede først med et fast *"Document(s) uploaded."*, uanset hvad flowet
  sagde.
- **Stien står i den tomme besked.** Get-flowet svarer `files: "[]"` både
  når mappen mangler og når den er tom — de to kan ikke skelnes fra appen.
- **Galleriet sorterer på `FileName`.** VH-plan-appen sorterede på en
  `LineId`, dokumenterne ikke har; `Items` gik i fejl, og galleriet stod
  tomt, mens filerne lå i biblioteket.

## Én app, to konfigurationer

Equipment og Materials er den **samme** app. Fire filer er ordret ens i de
to build-mapper, og `tools/build_all.py` tjekker det:

```
build_domain.py           formen: bar, header, liste, detaljer, dokumenter, gem
attflows.py               dokumentruden
generate_app_onstart.py   samlingsskema + ?reqid-loaderen
assemble_screen.py        skærmen
```

Kun `domain_config.py` er forskellig. `SECTIONS` dér bestemmer **både**
kontrollen på skærmen, kolonnen i samlingen og formen i `Patch` — de tre
kan ikke komme til at sige noget forskelligt om det samme felt, fordi de
læser den samme liste.

Skal der et felt til eller fra, er det én linje i `SECTIONS` og én linje i
`Provision-EqMatLists.ps1`.

### Arten bestemmer formen

| art | kontrol | i `Patch` |
|---|---|---|
| `text` | `ModernTextInput` | `I.Col` |
| `num` | `ModernNumberInput` | `I.Col` |
| `choice` | `ModernDropdown` | `If(IsBlank(I.Col), Blank(), { Value: I.Col })` |
| `bool` | `ModernCheckbox` | `I.Col` |
| `date` | tekst + validering | `IfError(DateValue(I.Col), Blank())` |

**Datoer er tekst i appen.** Der er ingen datovælger i repoets kontrolsæt —
ingen af de to eksisterende apps bruger en, så den er ikke bevist her.
Feltet bliver til en dato ved `Patch`, og `ValidationState` siger fra med
det samme, hvis teksten ikke kan læses som en dato. Ellers ville fejlen
først vise sig ved Gem, som en tom dato uden forklaring.

En tom valgkolonne er `Blank()`, ikke `{ Value: "" }` — derfor `If`'en.

## Det der mangler

### ~~App-id'erne~~ — på plads

| App | `app_id` |
|---|---|
| Equipments | `24bf3bbc-601f-480d-a8fe-7cd3180906d1` |
| Materials | `d7762919-c716-4bd0-9abd-24bab436221f` |

De står **tre** steder, og det er ikke redundans — det er tre forskellige
spørgsmål:

| Fil | Svarer på |
|---|---|
| `tools/canvas_apps.json` | Hvor `canvas_mcp.py deploy` sender YAML'en hen |
| `Masterdata Hub/build/hub_config.py` | Hvad flisen på landingssiden åbner |
| `<App>/build/domain_config.py` → `PLAY_URL` | Hvad der skrives i `MD_RequestIndex.AppUrl`, så "Open" lander på den rigtige indmelding |

Glider de fra hinanden, **fejler ingenting**. Builderne deployer ét sted,
flisen åbner et andet, og dyblinket et tredje. Det ses først, når en bruger
trykker "Open" og lander i en tom app.

Derfor tjekker `tools/build_all.py` det nu ved hver bygning:

```
App-id'erne er gledet fra hinanden:

  material: PLAY_URL i Material App peger ikke paa d7762919-...
```

Bemærk at det **ikke** er dokumentets id. Det `Id`, en apps
`Properties.json` bærer, er dokumentets — play-URL'en vil have appens, og
de to er forskellige. Hent appens i Studio-URL'en efter `%2Fapps%2F`.

### Hvilken Equipment-app er den rigtige? — afgjort

Der er tre i miljøet:

| Solution-navn | Hedder | Rolle |
|---|---|---|
| `orsted_equipments_ebf7d` | Equipments | **Målet.** Tom i dag, ligger i solutionen |
| — (ikke i solutionen) | Equipment | Det hubben peger på i dag. Ældre, har indhold |
| `cr871_equipment_bd0a4` | Equipment | Tom skal fra tidligere — kan ryddes ud |

**Builderne deployer til `Equipments`.** Den ligger i solutionen og følger
derfor med ved eksport, hvilket den ældre ikke gør. EQ-flisen er flyttet
med, så deploy-mål og flise peger samme sted.

Den ældre app (`dd9544e2-a0aa-4713-a076-7637080a40fc`) er stadig der og
har stadig indhold — den er bare ikke længere den, noget i repoet peger på.

### Før der kan deployes

De tre flows og de fire lister skal tilføjes som datakilder i **begge**
apps i Studio. En formel, der kalder et flow eller en liste, fejler i
compile, hvis kilden ikke er der, og det kan ikke gøres fra YAML.

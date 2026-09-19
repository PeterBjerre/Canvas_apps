# Equipment- og Materials-appen

## De to apps var tomme

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

### App-id'erne

Fliserne og `AppUrl` skal bruge appens **play-id**, og det står **ikke** i
solution-eksporten. Det `Id`, der står i en apps `Properties.json`, er
*dokumentets* id — ikke appens. De to er forskellige, og play-URL'en vil
have appens.

Hent det i Studio-URL'en eller med `pac canvas list`, og sæt det to steder:

```
Masterdata Hub/build/hub_config.py     DOMAINS[...]["app_id"]
Material App/build/domain_config.py    PLAY_URL
tools/canvas_apps.json                 apps.material.app_id
```

Indtil da står MAT-flisen som "Kommer snart", og `AppUrl` skrives tom —
alt andet virker.

### Hvilken Equipment-app er den rigtige?

Der er tre i miljøet:

| Solution-navn | Hedder | Rolle |
|---|---|---|
| `orsted_equipments_ebf7d` | Equipments | **Målet.** Tom i dag, ligger i solutionen |
| — (ikke i solutionen) | Equipment | Det hubben peger på i dag. Ældre, har indhold |
| `cr871_equipment_bd0a4` | Equipment | Tom skal fra tidligere — kan ryddes ud |

**Builderne skal deploye til `Equipments`.** Den ligger i solutionen og
følger derfor med ved eksport, hvilket den ældre ikke gør.

Indtil dens app-id er fundet:

- `tools/canvas_apps.json` har `app_id: null`. Det er med vilje tomt og
  ikke gættet: et forkert id deployer ind i en anden app og overskriver
  den. **Tomt id stopper et deploy; forkert id ødelægger et.**
- Hubbens EQ-flise peger stadig på den ældre app, så et fungerende link
  ikke bliver til "Kommer snart" i mellemtiden.

De to skal flyttes **samtidig**, ellers deployer builderne ét sted og
flisen åbner et andet.

### Før der kan deployes

De tre flows og de fire lister skal tilføjes som datakilder i **begge**
apps i Studio. En formel, der kalder et flow eller en liste, fejler i
compile, hvis kilden ikke er der, og det kan ikke gøres fra YAML.

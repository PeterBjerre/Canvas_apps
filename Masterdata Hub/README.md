# Masterdata Hub

Landingssiden for SAP masterdata-indmeldinger. Viser dine egne indmeldinger på
tværs af funktionspladser, udstyr, målepunkter, materialer og VH-planer — og
afdelingens kø — og videresender til den rigtige domæneapp.

Beslutningen bag (hub vs. én samlet app) står i
[`../docs/07-landingsside.md`](../docs/07-landingsside.md).

## Nøgletal

| | |
|---|---|
| Kontroller | **95** (VH-plan-appen: 376) |
| Datakilder | **1** — `MD_RequestIndex` |
| `ClearCollect` i `App.OnStart` | **0** |
| `App.pa.yaml` | 12 linjer |

Det er ikke tilfældigt. Landingssiden er det sted, hvor alle kommer forbi
hver dag, så den er bygget efter de ni performanceregler i dokumentet.

## Designet

Efter `image.png`, med to afvigelser:

- **Hele flisen er filterknappen.** Der er ingen "Filter"-knap. Flisens
  forside (ikon, navn, tal) er ét SVG-billede med `OnSelect`, så et klik
  hvor som helst på den — undtagen "New" — filtrerer listen på domænet.
  Et klik mere viser alle igen.
- **Valgt = farvet kant, blød toning, let skygge** (issue #70). Den valgte
  flise får kanten i domænets farve (2 px), et fyld i domænets bløde tone
  (`domain-*-soft`) og `DropShadow.Light`. Hover og tryk toner forsiden i
  samme bløde tone, og tastaturfokus er en 2 px kant i domænets farve — ens
  for alle fem fliser. "New" er i domænets farve. Samme regel gælder "My
  requests" og Open / Closed / All: valgt er kanten og teksten i
  accentfarven.
- **Fliserækken har luft** — 12 px i hver side (det samme som mellem
  fliserne) og lidt foroven og forneden, så kant og skygge aldrig klippes.
- **Paletten** (issue #70): fem tydeligt adskilte farver — blå (FL), teal
  (Equipment), oliven-lime (Measuring point), orange (Material), violet
  (VH-plan). `design_tokens.py` stopper byggeriet, hvis to af dem kommer
  under ΔE 45 i et af temaerne. Measuring points lineal er spejlet, så den
  peger samme vej som Equipments skruenøgle.
- **Functional Location-ikonet** er et kraftværk i en lokationsnål — én
  definition i `tools/icons.py`, brugt af fliserne, menuen, tabellen og
  sidebaren i alle apps.
- **Tabellen er neutral.** Galleriet har kortets farve; stregen mellem
  rækkerne er en figur i hver række, og der er en streg under
  overskriften. Et aktivt domænefilter står som en lille knap i domænets
  farve over tabellen (klik = fjern filteret).

"New request" i bjælken åbner en menu med de fem domæner.

## Filer

| Fil | Indhold |
|---|---|
| `App.pa.yaml` | Fire `Set()` og intet andet |
| `ScreenMdHub.pa.yaml` | Skærmens kontroltræ |
| `build/hub_config.py` | **Domæner, app-URL'er og statusordforråd — tilpas her** |
| `build/build_hub.py` | Skærmen |
| `build/assemble_hub.py` | → `../ScreenMdHub.pa.yaml` |
| `build/generate_hub_onstart.py` | → `../App.pa.yaml` |
| `build/gen_screen.py` | DSL, stylingkonstanter, højde-algebra |
| `build/build_helpers.py` | Byggeklodser: `card`, `group`, `button_row`, inputs |
| `build/check_layout.py` | Layout-tjekket |

De tre sidste er **kopieret ordret** fra `Maintenance Plan App/build/`. Retter
du i en af dem, skal kopien opdateres i den anden app —
`tools/build_all.py` stopper og siger til, hvis de er gledet fra hinanden.

## Byg

```bash
python3 tools/build_all.py        # begge apps + begge layout-tjek
```

eller kun denne app:

```bash
cd "Masterdata Hub/build"
python3 generate_hub_onstart.py   # -> ../App.pa.yaml
python3 assemble_hub.py           # -> ../ScreenMdHub.pa.yaml
python3 check_layout.py           # finder selv skærmen
```

YAML'en er genereret. Ret i builderne — se
[`../.github/skills/canvas-build/SKILL.md`](../.github/skills/canvas-build/SKILL.md).

## Sådan tilpasses den

Alt der skal ændres, står i `build/hub_config.py`:

- **`DOMAINS`** — de fem domæner med farve og satellittens play-URL. Er `url`
  tom, står flisen som "Kommer snart" og kan ikke åbnes. Kun VH-plan har en
  URL i dag; de fire andre udfyldes efterhånden som apperne bygges.
- **`STATUS`** — det fælles ordforråd med trin 1–5 og farver. Alle fem apps
  skal bruge de samme værdier, ellers kan de ikke vises i samme oversigt.
- **`LIST`** — navnet på indekslisten.
- **`COL_NO`** — visningsnavnet på indmeldingsnummeret (`RequestNo`). Power Fx
  binder SharePoint-kolonner på visningsnavn, så den skal matche det navn,
  provisioneringsscriptet giver `Title`-kolonnen.

## Sådan hænger det sammen med de andre apps

Hubben **skriver ikke**. Hver domæneapp opdaterer sin række i
`MD_RequestIndex` fra sit **submit-flow** — ikke fra appen — så det også sker,
når en sagsbehandler ændrer status.

En række skal mindst indeholde `RequestNo` (den omdøbte `Title`), `Domain`,
`RequestGuid`, `Status`, `StatusStep`, `IsOpen`, `RequesterEmail`, `ShortText`,
`Plant`, `AppUrl` og `LastActionOn`.

Listen oprettes med:

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser        # kun første gang
.\Provision-RequestIndex.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>" -AddSampleRows
```

`-AddSampleRows` lægger fire prøverækker ind, så siden kan afprøves, før de
fem submit-flows er bygget. Scriptet er idempotent og kan køres igen.

`AppUrl` gemmes på rækken, så hubben ikke skal kende fem app-id'er. Den bygger
linket som `AppUrl & "?reqid=" & RequestGuid` (eller `&reqid=`, hvis URL'en
allerede har en query) og åbner i en ny fane, så hubben bliver liggende
indlæst.

## Delegation — det der skal verificeres

To udtryk skal tjekkes i Studio, fordi de afgør, om siden skalerer:

1. **Galleriets `Items`.** Den ydre `If` vælger mellem to `Filter` —
   `RequesterEmail = gblMe` og `IsOpen = true`. Begge grene er delegerbare
   hver for sig. Bekræft at Studio ikke sætter et delegationsadvarsels-ikon
   på selve `If`'et.
2. **Forfiningerne** (domæne, status, fritekst) køres bevidst klientside oven
   på det allerede afgrænsede sæt. Det er korrekt, så længe en bruger har
   under 2.000 indmeldinger og køen er under 2.000 åbne sager. Sæt appens
   **Data row limit til 2000**.

Bliver køen større end det, skal "Til behandling" filtreres yderligere
serverside — fx på `AssignedToEmail` eller på værk.

# Masterdata Hub

Landingssiden for SAP masterdata-indmeldinger. Viser dine egne indmeldinger på
tværs af funktionspladser, udstyr, målepunkter, materialer og VH-planer — og
afdelingens kø — og videresender til den rigtige domæneapp.

Beslutningen bag (hub vs. én samlet app) står i
[`../docs/07-landingsside.md`](../docs/07-landingsside.md).

## Nøgletal

| | |
|---|---|
| Kontroller | **102** (VH-plan-appen: 381) |
| Datakilder | **1** — `MD_RequestIndex` |
| Datahentning i `App.OnStart` | **0** |
| `App.pa.yaml` | ca. 190 linjer — designtokens (`C`), breakpoints og tema |

Det er ikke tilfældigt. Landingssiden er det sted, hvor alle kommer forbi
hver dag, så den er bygget efter de ni performanceregler i dokumentet.

## Designet

Efter `image.png`, med to afvigelser:

- **Hele flisen er filterknappen.** Der er ingen "Filter"-knap. Flisens
  forside (ikon, navn, tal) er ét SVG-billede med `OnSelect`, så et klik
  hvor som helst på den filtrerer listen på domænet (fliserne har ingen
  "New" længere, issue #74).
  Et klik mere viser alle igen.
- **Valgt = farvet kant, blød toning, let skygge** (issue #70). Den valgte
  flise får kanten i domænets farve (2 px), et fyld i domænets bløde tone
  (`domain-*-soft`) og `DropShadow.Light`. Hover og tryk toner forsiden i
  samme bløde tone, og tastaturfokus er en 2 px kant i domænets farve — ens
  for alle fem fliser. Samme regel gælder "My
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
| `App.pa.yaml` | Designtokens, breakpoints, tema og hubbens tilstand — ingen datahentning |
| `ScreenMdHub.pa.yaml` | Skærmens kontroltræ |
| `build/hub_config.py` | **Domæner, app-URL'er og statusordforråd — tilpas her** |
| `build/build_hub.py` | Skærmen |
| `build/assemble_hub.py` | → `../ScreenMdHub.pa.yaml` |
| `build/generate_hub_onstart.py` | → `../App.pa.yaml` |
| `build/check_layout.py` | Indgang til layout-tjekket i `tools/check_layout.py` |

DSL'en, byggeklodserne, sidebaren og tjekket ligger i `tools/` i én udgave
for alle apps (`gen_screen.py`, `build_helpers.py`, `side_nav.py`,
`check_layout.py`).

## Byg

```bash
python3 tools/build_all.py --app hub   # kun hubben + tjek
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

- **`DOMAINS`** — de fem domæner med farve, ikon og app-nøgle. Play-URL'en
  kommer fra `tools/canvas_apps.json`; har appen intet id, står den som
  "Coming soon" og kan ikke åbnes (i dag Measuring point).
- **`STATUS`** — det fælles ordforråd med trin 1–5 og farver. Alle fem apps
  skal bruge de samme værdier, ellers kan de ikke vises i samme oversigt.
- **`LIST`** — navnet på indekslisten.
- **`COL_NO`** — visningsnavnet på indmeldingsnummeret (`RequestNo`). Power Fx
  binder SharePoint-kolonner på visningsnavn, så den skal matche det navn,
  provisioneringsscriptet giver `Title`-kolonnen.

## Sådan hænger det sammen med de andre apps

Hubben **skriver ikke**. Domæneapperne (VH-plan, Equipment, Material,
Functional Location) skriver selv deres række i `MD_RequestIndex`, når der
gemmes som kladde og indsendes. Statusændringer derefter (sagsbehandling)
skrives af flows.

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

"Open" bygger linket af rækkens **domæne**: domænets play-URL (fra
`tools/canvas_apps.json`) `& "?reqid=" & RequestGuid & "&theme=…"`, og åbner
i **samme fane** (`LaunchTarget.Replace`). Rækkens `AppUrl` bruges kun, hvis
domænet er ukendt — den kan redigeres af alle med Contribute på listen.

## Delegation — det der skal verificeres

To udtryk skal tjekkes i Studio, fordi de afgør, om siden skalerer:

1. **Galleriets `Items`.** Ét fladt `Filter` på `MD_RequestIndex`, hvor hver
   betingelse er "konstant ELLER delegerbar sammenligning"
   (`gblView <> "mine" || RequesterEmail = gblMe`, `IsOpen = …`). Bekræft i
   Studio, at der ingen delegeringsadvarsel er.
2. **Forfiningerne** (domæne, status, fritekst) køres bevidst klientside oven
   på det allerede afgrænsede sæt. Det er korrekt, så længe en bruger har
   under 2.000 indmeldinger og køen er under 2.000 åbne sager. Sæt appens
   **Data row limit til 2000**.

Flisernes og tællerens tal er `CountRows` mod listen og stopper ved data row
limit (REVIEW.md B1, fase 2). Bliver køen større end det, skal den filtreres yderligere
serverside — fx på `AssignedToEmail` eller på værk.

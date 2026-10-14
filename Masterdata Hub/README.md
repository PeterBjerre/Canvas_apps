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

Efter skærmbilledet `image.png` (nu kun i git-historikken), med to afvigelser:

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

**UX-review 2026-10 (etape 1):**

- Undertitlen er "Requests for SAP master data".
- **REQUEST-kolonnen** har domænets ikon, nummeret og domænets navn i én
  celle (før tre gange). *Requester* skjules i *My requests*, og TEXT får
  pladsen.
- Godkendelsesstriben har ingen mikroetiketter (trinene står i
  tooltip'en), og "Not required" er "-".
- Status er den fælles statuschip (`tools/status_chip.py`). *Updated*
  viser datoen (dd-mm-yyyy); den relative tid står i rækkens tooltip.
- **Stuck** gælder kun Indsendt, UnderBehandling og AfventerInfo, efter
  `request_index.STUCK_DAYS` (5) dage.
- *Delete* står kun på kladder.
- Filterlinjen er grupperet: Open / Closed / All (i) | Waiting for me,
  Stuck — og søgefeltet er op til 360 px.
- Filtrene og søgningen huskes mellem besøg (`SaveData`, docs/26).
- En tom liste siger det og har *Clear filters*.

**UX-review 2026-10 (etape 2, M3):**

- Fliserne er 72 px høje: ikon, navn og "12 open requests" på to linjer.
  Til højre en (+)-knap, der starter en ny anmodning i domænet (samme
  handling som menuen). Flisen selv filtrerer stadig listen.
- "Continue where you left off" viser din senest ændrede kladde med
  *Continue* (åbner i Edit).
- REQUEST, PLANT, STATUS og UPDATED sorterer ved klik; et klik mere vender
  rækkefølgen. Standard er UPDATED, nyeste først.

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
- **`STATUS`** — farverne pr. status. Selve ordforrådet (værdi, etiket,
  trin) og domænenøglerne står i `tools/request_index.py`, som alle apps
  skriver indeksrækken med; `tests/` holder det op mod
  `Provision-RequestIndex.ps1`.
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
   (`varMdView <> "mine" || RequesterEmail = varMdMe`, `IsOpen = …`). Bekræft i
   Studio, at der ingen delegeringsadvarsel er.
2. **Forfiningerne** (domæne, status, fritekst) køres bevidst klientside oven
   på det allerede afgrænsede sæt. Det er korrekt, så længe en bruger har
   under 2.000 indmeldinger og køen er under 2.000 åbne sager. Sæt appens
   **Data row limit til 2000**.

Flisernes og tællerens tal tælles i `colMdScope` (kun domænet), som hentes
ved skærmvisning og når "My requests" eller Open/Closed/All skifter. Rammer
den data row limit, står der "500+". Bliver køen større end det, skal den filtreres yderligere
serverside — fx på `AssignedToEmail` eller på værk.

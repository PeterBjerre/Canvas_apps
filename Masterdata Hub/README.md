# Masterdata Hub

Landingssiden for SAP masterdata-indmeldinger. Viser dine egne indmeldinger på
tværs af funktionspladser, udstyr, målepunkter, materialer og VH-planer — og
afdelingens kø — og videresender til den rigtige domæneapp.

Beslutningen bag (hub vs. én samlet app) står i
[`../docs/07-landingsside.md`](../docs/07-landingsside.md).

## Nøgletal

| | |
|---|---|
| Kontroller | **83** (VH-plan-appen: 294) |
| Datakilder | **1** — `MD_RequestIndex` |
| `ClearCollect` i `App.OnStart` | **0** |
| `App.pa.yaml` | 12 linjer |

Det er ikke tilfældigt. Landingssiden er det sted, hvor alle kommer forbi
hver dag, så den er bygget efter de ni performanceregler i dokumentet.

## Filer

| Fil | Indhold |
|---|---|
| `App.pa.yaml` | Fire `Set()` og intet andet |
| `ScreenMdHub.pa.yaml` | Skærmens kontroltræ |
| `build/hub_config.py` | **Domæner, app-URL'er og statusordforråd — tilpas her** |
| `build/build_hub.py` | Skærmen |
| `build/assemble_hub.py` | → `../ScreenMdHub.pa.yaml` |
| `build/generate_hub_onstart.py` | → `../App.pa.yaml` |

DSL, højde-algebra, byggeklodser og layout-tjek deles med de øvrige canvas
apps og ligger i [`../shared/canvas/`](../shared/canvas).

## Byg

```bash
cd "Masterdata Hub/build"
python3 generate_hub_onstart.py
python3 assemble_hub.py
python3 ../../shared/canvas/check_layout.py ../ScreenMdHub.pa.yaml
```

YAML'en er genereret. Ret i builderne — se
[`../.github/skills/vhplan-canvas-build/SKILL.md`](../.github/skills/vhplan-canvas-build/SKILL.md).

## Sådan tilpasses den

Alt der skal ændres, står i `build/hub_config.py`:

- **`DOMAINS`** — de fem domæner med farve og satellittens play-URL. Er `url`
  tom, står flisen som "Kommer snart" og kan ikke åbnes. Kun VH-plan har en
  URL i dag; de fire andre udfyldes efterhånden som apperne bygges.
- **`STATUS`** — det fælles ordforråd med trin 1–5 og farver. Alle fem apps
  skal bruge de samme værdier, ellers kan de ikke vises i samme oversigt.
- **`LIST`** — navnet på indekslisten.

## Sådan hænger det sammen med de andre apps

Hubben **skriver ikke**. Hver domæneapp opdaterer sin række i
`MD_RequestIndex` fra sit **submit-flow** — ikke fra appen — så det også sker,
når en sagsbehandler ændrer status.

En række skal mindst indeholde `Title`, `Domain`, `RequestGuid`, `Status`,
`StatusStep`, `IsOpen`, `RequesterEmail`, `ShortText`, `Plant`, `AppUrl` og
`LastActionOn`. Se `sharepoint/provision/Provision-RequestIndex.ps1`.

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

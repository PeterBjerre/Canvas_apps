# Maintenance Plan App (VH-plan)

Canvas app til indmelding af **vedligeholdelsesplaner (VH-planer)** til SAP PM,
med planhoved, items, tasklist-/operationsbinding, **strategiplaner med
pakker**, og dispatch via mailkladde. Bygget i samme visuelle stil som
Materialer-appen i samme Power Platform-miljø (Bioenergy Solutions DEV,
solution BIO SAP).

## Filer

| Fil | Indhold |
|---|---|
| `App.pa.yaml` | `App.OnStart` — referencelister, tasklister pr. værk, **strategier og pakker**, funktionelle lokationer og en demo-plan |
| `ScreenVhPlan.pa.yaml` | Skærmens fulde kontroltræ |
| `_EditorState.pa.yaml` | Editor-metadata |
| `build/` | **Python-builderne, som YAML'en genereres fra** |

## YAML'en er genereret — ret builderne, ikke YAML'en

`ScreenVhPlan.pa.yaml` er 9.600 linjer og skrives af `build/assemble_screen.py`.
Retter du direkte i YAML'en, er ændringen væk næste gang nogen kører builderen.

```bash
cd build
python3 generate_app_onstart.py   # -> ../App.pa.yaml
python3 assemble_screen.py        # -> ../ScreenVhPlan.pa.yaml
python3 check_layout.py           # verificerer layoutet
```

| Modul | Ansvar |
|---|---|
| `gen_screen.py` | Kontroltræ-DSL, stylingkonstanter, **højde-algebra** |
| `build_helpers.py` | Genbrugelige kontroller: kort, felter, knapper, rækker |
| `build_hero.py` | Hero, procesindikator, Validate og Export JSON |
| `build_plan_header.py` | Planhoved inkl. plantype og strategivalg |
| `build_items.py` | Items-skinne og Item Editor |
| `build_tasklist.py` | Tasklist, operationstabel, dispatch, mailknap |
| `build_strategy.py` | **Pakkematricen** |
| `build_modal.py` | Tasklist-picker |
| `check_layout.py` | Efterregner layoutet — se nedenfor |

## Højdemodellen — og hvorfor Items-delen var i stykker

Canvas-containere kan ikke "hugge" deres indhold; en container får kun den
højde, dens `Height`-formel siger. Den oprindelige kode løste det ved at lade
hver container summere sine **børns** `.Height`:

```
conVhpShell.Height = 40 + conVhpHero.Height + 20 + conVhpPlanCard.Height + ...
conVhpItemsSplit.Height = IfError(Max(conVhpItemsCard.Height, conVhpEditorCard.Height), 700)
```

Det er en cirkelreference. I en AutoLayout-container er det **forælderen**, der
sætter børnenes størrelse — `LayoutAlignItems` er `Stretch` som standard, og på
en container med `LayoutWrap = true` fjerner platformen `LayoutAlignItems`
helt, så `Stretch` ikke kan slås fra. Når forælderen så læser barnets
`.Height`, læser den sin egen udregning tilbage. Resultatet var enten en
formelfejl, der faldt tilbage til `IfError`-konstanten, eller den kaskade-vækst
hvor containerne blev større for hver genberegning.

Derfor: **ingen `Height`-formel refererer længere en anden kontrol.** Højder
regnes i Python ud fra konstanter, `App.Width` og `CountRows()`, og
`stack_height()` tæller selv padding og gaps med, så de ikke kan glemmes ét
enkelt sted.

## `check_layout.py`

Layoutet kan ikke renderes uden for Studio, så det regnes efter i stedet.
Seks kontroller, kørt for skærmbredder fra 420 til 1920 px og for 0–8 items
og 0–12 operationer:

1. Ingen `Height`-formel refererer en anden kontrols `.Height`
2. Hver lodret container er høj nok til børn + gaps + egen polstring
3. Hver vandret container er høj nok til sit højeste barn
4. Faste bredder i en vandret række overstiger ikke rækkens bredde
5. HTML-tabeloverskrifterne flugter med kontrollerne i rækken
6. Balancerede parenteser og anførselstegn i alle formler

Kør den efter enhver ændring i builderne.

## Hvad der blev rettet

| # | Fejl | Konsekvens |
|---|---|---|
| 1 | Højder summerede andre kontrollers `.Height` | Cirkelreference → kaskade-vækst og klippet indhold |
| 2 | Kortenes højde talte ikke deres egen polstring med | Hvert kort 36 px for lavt |
| 3 | `conVhpItemButtonRow`: 336 px knapper i 324 px kort, højde låst til 36 | Ombrød til to linjer, "Remove item" blev klippet |
| 4 | Ops-toolbaren havde dropdown og 4 knapper i én 62 px høj række | Tasklist-dropdownen blev klippet helt væk |
| 5 | `conVhpEditorCard.Height` fast 652 px, uafhængig af det responsive felt-grid | Alt under første felt klippet på smalle skærme |
| 6 | Responsive brækpunkter målte på `App.Width` | Editoren er ~380 px smallere end skærmen, så felterne stod side om side længe efter der var plads |
| 7 | Gallerihøjde regnede kun `TemplateSize`, ikke `TemplatePadding` | Sidste item i skinnen blev klippet |
| 8 | Ops-tabellens HTML-overskrift havde andre kolonnebredder end rækken | Overskrifterne stod forskudt (914 px mod 918 px) |
| 9 | Picker-overskriften var 6 px forskudt pr. kolonne | Samme problem i modalen |
| 10 | `Filter(tl.Operations, CountRows(Filter(colVhpPickerSelected, OperationNo = OperationNo)) > 0)` | Navnekollision: altid sand, så **alle** tasklist-linjer blev tilføjet uanset markering |
| 11 | `conVhpLegend`: 123 px indhold i en 110 px række | "Skal udfyldes" klippet |
| 12 | `conVhpPickerListWrap` 4 px for lav | Sidste picker-række klippet |

## Strategiplaner

Pakkerne hører til **arbejdsplanens operationer**, ikke til planen. I SAP ejer
strategien pakkerne (IP11, masterdata), arbejdsplanen ejer allokeringen
operation→pakke (IA01), og vedligeholdsplanen peger bare på begge (IP42).
Derfor ligger matricen på `colVhpOperations`, og brugeren opfinder aldrig
pakker — de kommer fra `colVhpStrategyPackages`.

Allokeringen gemmes som én streng pr. operation, `PackagesKey`, på formen
`;1;3;5;`. Sentinel-separatoren i begge ender er ikke kosmetik: uden den ville
testen for pakke 1 (`;1;`) også matche inde i `;12;`.
**Invariant:** `PackagesKey` er aldrig tom — en operation uden pakker har `;`.

Nyt i appen:

- **Plan Type** på planhovedet: single cycle (IP41) eller strategiplan (IP42).
  Cycle og Unit er deaktiveret på en strategiplan, fordi cyklussen dér kommer
  fra pakkerne.
- **Maintenance Strategy** med fire strategier og deres pakker, de samme som i
  `sharepoint/seed/MD_StrategyPackage.csv`.
- **Strategy Packages**-kortet (Step 4, vises kun for strategiplaner) med
  matricen: én række pr. operation, én kolonne pr. pakke. Genvejene
  *Hierarki-udfyld*, *Alle pakker* og *Ryd pakker* dækker det mønster, de
  fleste strategiplaner følger.
- **PAKKER**-kolonne i operationstabellen, så allokeringen kan læses samme sted
  som operationslinjen.
- Validering **S1, S3, S4, S5** på Validate-knappen, og pakkerne med i både
  mailkladden og JSON-eksporten.

## Kendte begrænsninger

- "Verify FL" slår op i en lokal referencetabel (8 eksempler), da der ikke er
  konfigureret en SAP OData-forbindelse i miljøet.
- Tasklist-datasættet er et repræsentativt udsnit (8 tasklister, op til 6
  operationslinjer hver).
- Strategier og pakker er indlejret i `App.OnStart` som offline masterdata. De
  bør på sigt komme fra SharePoint-listerne `MD_Strategy` og
  `MD_StrategyPackage` (se `docs/02-datamodel-sharepoint.md`).
- Pakkematricen bruger et **horisontalt galleri** (`Variant: Horizontal`) til
  pakkekolonnerne. Det er den ene konstruktion i skærmen, der ikke fandtes i
  appen i forvejen — tjek den først, hvis importen brokker sig.

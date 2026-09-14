# Appen mod de rigtige lister

Testdataene er væk. Appen læser nu SharePoint.

## Det der ændrede sig

| | Før | Nu |
|---|---|---|
| `App.pa.yaml` | 465 linjer | **101** |
| Datahentning i `OnStart` | 21 `ClearCollect` med hårdkodede tabeller | **0** |
| Opslagslister | hårdkodet i `OnStart` | 13 **navngivne formler** mod SharePoint |
| Kontroller i skærmen | 281 | 281 — uændret |

## Hvorfor navngivne formler og ikke `ClearCollect`

`OnStart` betales af **hver bruger, hver gang**. Et `ClearCollect` pr.
opslagsliste ville være ti kald, før der overhovedet er tegnet noget — samme
fejl som landingssiden er bygget for at undgå.

Navngivne formler (`App.Formulas`) evalueres **dovent og caches**: listen
hentes første gang en kontrol faktisk har brug for den, og kun én gang.
Navnene er de samme `colVhp*`, som skærmen allerede brugte, så ingen af de
281 kontroller skulle ændres.

En navngiven formel kan til gengæld ikke skrives til. De samlinger, appen
**redigerer** — items, operationer, søgeresultater — er derfor stadig rigtige
samlinger og står i `OnStart` med tomt skema.

## Hvor data kommer fra

Alt står i `Maintenance Plan App/build/sp_config.py` og kun der.

| Samling | Kilde |
|---|---|
| `colVhpPlantCodes` | `PlantList` |
| `colVhpSortFieldOptions` | `SortFieldList` |
| `colVhpActivityTypeOptions` | `MaintenanceActivityTypeList` |
| `colVhpCallHorizonOptions` | `CallHorizonMatrix` |
| `colVhpMainWorkCenters` | `MainWorkCenters` — bærer værk, så listen kan afgrænses |
| `colVhpCtrlOptions` | `Distinct(MD_StandardTaskOperations, ControlKey)` |
| `colVhpPlanStatusOptions` | `Choices(MaintenanceItems.Status)` |
| `colVhpUnitOptions` | `Choices(MaintenancePlans.Unit)` |
| `colVhpRevisionOptions` | `Choices(MaintenanceItems.RevisionMark)` |
| `colVhpPriorityOptions` | `Choices(MaintenanceItems.Priority)` |
| `colVhpStrategies` | `MD_Strategy` |
| `colVhpStrategyPackages` | `MD_StrategyPackage` |
| `colVhpTasklists` | `MD_StandardTaskOperations`, grupperet pr. værk |

To ting bliver stående som konstanter: `colVhpYesNoOptions` (SAP's JA/NEJ) og
`colVhpPlanTypeOptions` (appens eget begreb). En liste med to rækker, ingen
rører, er dårligere end en konstant, man kan se.

## Strategier uden pakker

`MD_StrategyPackage` er tom, indtil pakkerne er hentet fra IP11. Appen skal
kunne bruges alligevel.

**Alle 53 strategier vises i dropdownen** — også dem uden pakker. De er mærket
i selve teksten:

```
101 - 1-3-6-12-36 md eftersyn   (pakker mangler)
```

Jeg byggede det først, så kun strategier med `PackagesLoaded = true` blev
tilbudt. Det var forkert: så længe `MD_StrategyPackage` er tom, ville
dropdownen være **helt tom**, og strategidelen kunne hverken bruges eller
testes.

Vælges en strategi uden pakker, tegnes matricen ikke som et tomt gitter. Der
står i stedet:

> Strategi 101 har ingen pakker i MD_StrategyPackage endnu, så der er ikke
> noget at tildele. Pakkerne hentes fra SAP (IP11). Planen kan godt gemmes og
> sendes uden pakketildeling.

Det samme udtryk, `CAN_DRAW`, styrer både matricen, handlingsknapperne og
tomtilstanden, så de aldrig kan vises samtidig.

## Strategi 128 er den første, der kan bruges

Pakkerne for **strategi 128** er aflæst i IP11 og ligger i
`sharepoint/seed/MD_StrategyPackage.csv`. `Provision-StrategyLists.ps1`
indlæser dem og sætter `PackagesLoaded` automatisk på de strategier, der får
pakker.

| Pakke | Cyklus | Kort | Hierarki | Offset | Tekst |
|---|---|---|---|---|---|
| 1 | 3 YR | 1Y | 1 | 0 | År 1 |
| 2 | 3 YR | 2Y | 2 | 1 | År 2 |
| 3 | 3 YR | 3Y | 3 | 2 | År 3 |

Læg mærke til mønsteret: **alle tre pakker har samme cykluslængde, 3 år, med
offset 0, 1 og 2.** Det er det, der giver "År 1, 2, 3, 1, 2, 3". Pakkerne
falder aldrig sammen.

### Når nogen retter direkte i SharePoint

`Provision-StrategyLists.ps1` behandler `sharepoint/seed/MD_StrategyPackage.csv`
som sandheden og **opdaterer** eksisterende pakkerækker ud fra den. Det er
rigtigt, når rettelser sker i csv'en — men forkert, hvis nogen har rettet
direkte i listen: så ville næste kørsel rulle rettelsen tilbage i stilhed.

To ting forhindrer det:

1. **Scriptet skriver hvad det ændrer**, felt for felt:
   `~ 128-2: OffsetValue '1' -> '0'`. Og `-WhatIfOnly` viser det uden at
   røre noget. En tilbagerulning kan ikke længere ske usynligt.
2. **`python3 tools/sync_package_seed.py`** vender pilen om og skriver
   csv'en ud fra et friskt udtræk. Kør den efter en manuel rettelse, så er
   næste provisioneringskørsel en no-op i stedet for en tilbagerulning.

Rækkefølgen efter en manuel rettelse i SharePoint er:

```powershell
.\Export-ListSchema.ps1 -SiteUrl "https://..."       # frisk udtræk
python3 tools\sync_package_seed.py                   # csv <- SharePoint
```

`sync_package_seed.py` skriver udtrækkets dato ud. Er det ældre end
rettelsen, beskriver det ikke listen som den ser ud nu — kør eksporten igen
først.

### Derfor er "Hierarki-udfyld" slået fra

Knappen fylder alle pakker med `Hierarchy >= den laveste markerede`. Den giver
mening på en **indlejret** strategi som 1-3-6-12, hvor den månedlige opgave
også skal laves ved kvartals- og årsgennemgangen.

På strategi 128 ville den være direkte forkert: markerer man "År 1", ville
"År 2" og "År 3" også blive markeret, og **en treårig opgave ville blive
årlig**.

Knappen er derfor bundet til `MD_Strategy.Hierarchical` og er kun aktiv, når
feltet står på `Ja`. `Ikke afklaret` er altså ikke det samme som `Nej` — det
betyder, at ingen har taget stilling, og så gættes der ikke. En grå knap uden
forklaring ligner en fejl, så der står en linje under den om hvorfor, og hvad
der skal gøres.

Det er samtidig svaret på, hvad feltet skal bruges til. Alle 53 står som
`Ikke afklaret`, som aftalt.

> Ud fra tallene *ser* 128 ikke hierarkisk ud — samme cykluslængde med
> forskudte offsets er per definition roterende. Men det er jeres kald, ikke
> mit, så feltet er ikke sat.

## Arbejdscentre afgrænses nu på værk

`MainWorkCenters` har 53 rækker for hele afdelingen, men kun en håndfuld hører
til det valgte værk. Dropdownen filtrerer på `varVhpPlan.Plant` — og viser dem
alle, hvis der ikke er valgt værk endnu. En tom dropdown uden forklaring er
værre end en lang.

Værdierne **trimmes**: SAP-eksporten er polstret med mellemrum (`'SSVAP   '`).

`MainWorkCenters.field_1` har visningsnavnet `Description` efterfulgt af **33
mellemrum**. Power Fx binder på visningsnavn, så kolonnen kun kan nås ved at
skrive præcis det antal mellemrum. Appen undgår den og bruger kun `Title` og
`'Plant Key'`. `Provision-VHPlanColumns.ps1 -FixMainWorkCenterNames` kan
omdøbe den — men den gamle app kan være afhængig af den, så det er et
bevidst valg.

## Nyt i layout-tjekket: check 8

En skærm, der bruger `colVhpNoget`, som ingen definerer, kompilerer ikke — men
fejlen dukker først op i Studio. Da opslagslisterne blev flyttet fra hårdkodede
tabeller til navngivne formler, blev **tre referencer hængende**
(`colVhpMainWorkCenterItemOptions`, `colVhpRevisionOptions`,
`colVhpFunctionalLocations`).

`check_layout.py` sammenholder nu hver `col*` i skærmen med det, `App.pa.yaml`
faktisk definerer — både navngivne formler og `ClearCollect`. Det fanges før
synk i stedet for i Studio.

## Det appen stadig ikke gør

**Den gemmer ikke til SharePoint.** Flowet er uændret: udfyld → validér →
eksportér JSON → Excel → GUI-scripting. `MaintenancePlans`,
`MaintenanceItems` og `TaskListMain` læses ikke og skrives ikke af den nye
app endnu.

Det er det næste stykke, og det hænger sammen med løbenummer-spørgsmålet i
[`10-datamodel-forslag.md`](10-datamodel-forslag.md) §5 — der er ingen grund
til at bygge en gemmefunktion oven på en nøglegenerering, der kan kollidere.

## Før synk til Studio

Datakilderne skal findes i appen, ellers fejler compile på et ukendt navn:

```
PlantList                    SortFieldList
MaintenanceActivityTypeList  CallHorizonMatrix
MainWorkCenters              MaintenanceItems
MaintenancePlans             MD_Strategy
MD_StrategyPackage           MD_StandardTaskOperations
```

plus flowet `BioSap-Integration-FunctionalLocations`.

Tilføj dem i Studio og **gem** (Ctrl+S) — at tilføje en datakilde uden at
gemme er ikke nok.

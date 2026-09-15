# Gemning i SharePoint

Appen skriver nu. Fire lister, i den rækkefølge:

```
MaintenancePlans   planhovedet          -> PlanID      MP0068
MaintenanceItems   ét pr. item          -> ItemID      MI0112
TaskListMain       ét pr. operation     -> TaskItemID  TI0341
MD_RequestIndex    ÉN opsummering       -> hubben læser kun den
```

To knapper i en ny **Step 6**-sektion:

| Knap | `MaintenancePlans.Status` | `MD_RequestIndex` |
|---|---|---|
| **Gem kladde** | `Draft` | `Kladde`, trin 1, åben |
| **Indsend** | `In Progress` | `Indsendt`, trin 2, åben |

## Nøglerne

`PlanID = ID − offset`. Den gamle app gør det allerede, og det holder i alle
398 eksisterende rækker. Da `ID` tildeles atomart af SharePoint, kan to
samtidige indsendelser ikke få samme nøgle.

**Offsettet udledes af data, ikke af `AppSettings`.** `AppSettings` har kun
værdier for DEV, og en manglende værdi i TEST eller PROD ville give en ny
nummerserie, uden at nogen opdagede det. I stedet tages nyeste række og
trækkes dens eget nummer fra sit `ID`. Det er selvkorrigerende og
miljøuafhængigt.

Kan offsettet ikke udledes — fordi en nøgle er misdannet — **gemmes der
ikke**. Der kommer en fejl i stedet. En forkert nummerserie er værre end en
fejlbesked.

## Gensave overskriver

Anden gang der gemmes, slettes planens items og operationer, og de skrives
forfra:

```
RemoveIf(TaskListMain, MaintenancePlanID.Id = planId);
RemoveIf(MaintenanceItems, MaintenancePlanNo.Id = planId);
```

Det er enklere og sikrere end at finde ud af hvilke linjer der er tilføjet,
ændret og slettet. Planhovedet **opdateres** derimod, så `PlanID` og rækkens
`ID` er de samme hele vejen.

> `RemoveIf` på et opslagsfelt kan ikke delegeres. Med 306 operationer i alt
> er det uden betydning, men appens **Data row limit skal være 2000**. Runder
> `TaskListMain` 2.000 rækker, skal oprydningen laves om.

## `MD_RequestIndex` — rækken hubben lever af

Skrives **hver gang** der gemmes, så oversigten aldrig viser noget forældet.
Den findes igen på `RequestGuid`, som sættes ved første gemning og bliver
stående.

`RequestNo` — ikke `Title`. Power Fx binder SharePoint-kolonner på
**visningsnavn**, og indekslistens `Title` er døbt om. Et `Patch` med
`{ Title: ... }` ville ramme ved siden af. Samme fælde som `CallHorizon`.

## Kolonner der bevidst ikke udfyldes

| Kolonne | Hvorfor |
|---|---|
| `MaintenancePlans.PlanType` | Eneste valgværdi er `PM`. Den siger intet om IP41/IP42 — **`StrategyKey`** bærer det i stedet: udfyldt = strategiplan |
| `MaintenancePlans.Package` | Én enkelt pakke pr. plan. Appens matrix er pr. operation og ligger i `TaskListMain.PackagesKey` |
| `CallHorizon` og `CallHorizonChoiceOLD` | **Ingen af dem skrives.** Se nedenfor |
| `MultiCounterStrategy` | Bruges ikke af appen |
| `TaskListMain.TaskID` | Overflødig — 1:1 med `MaintenanceItemNo`. Se `docs/10` §1 |

## Hvorfor Call Horizon ikke skrives

Jeg forsøgte først at skrive tallet til `CallHorizon`. Compile afviste det:

```
The type of this argument 'CallHorizon' does not match the expected
type 'Record'. Found type 'Number'.
```

Tre ting, i den rækkefølge de vejer:

1. **Kolonnen er tom i alle 34 eksisterende planer.** Det er
   `CallHorizonChoiceOLD` også. Den gamle app skriver ingen af dem, så
   ingen mangler dem.
2. Listen har **tre** CallHorizon-kolonner efter oprydningen — et tal, et
   valg, og en enhed. Hvilken der er den levende, er ikke afklaret.
3. Fejlen selv er en **cache-fejl i Studio**, ikke i koden: SharePoint
   siger `Number`, men appen husker den `Choice`, kolonnen var, før den
   blev omdøbt. Det kan løses ved at fjerne og gentilføje datakilden — men
   det ville løse et problem, ingen har.

`SchedulingPeriod` skrives derimod. Den er udfyldt i 9 af 34 planer, er et
rent tal, og har ingen navnetvivl.

Skal Call Horizon med til SAP, er første skridt at beslutte hvilken af de
tre kolonner der gælder — ikke at gætte fra appen.

## To ting der er sat, fordi listen kræver det

`MaintenanceItems.Priority` er **obligatorisk**, men appen har ikke feltet.
Alle items får `Yellow (default)` — som værdien bogstaveligt hedder. Skal
prioritet kunne vælges, er det et nyt felt i Item Editor.

`MaintenanceItems.OrstedResponsible` er en **obligatorisk Person-kolonne**.
Indsenderen skrives som ansvarlig, indtil appen får en rigtig personvælger.
`OrstedResponsibleEmail` sættes samtidig — det er den, der kan filtreres
delegerbart.

## Ny kolonne

`Provision-VHPlanColumns.ps1` opretter nu også
`MaintenancePlans.StrategyKey` (Text, indekseret). **Kør scriptet igen**,
før appen gemmer — ellers fejler `Patch` på et ukendt navn.

```powershell
.\Provision-VHPlanColumns.ps1 -SiteUrl "https://..." -WhatIfOnly
.\Provision-VHPlanColumns.ps1 -SiteUrl "https://..."
```

## Nye datakilder i Studio

`MD_RequestIndex` skal tilføjes som datakilde — og **gemmes**. Uden den
fejler compile.

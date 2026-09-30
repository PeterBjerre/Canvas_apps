# Gemning i SharePoint

> **Status: historisk.** Gemningen er siden ændret; den gældende står i `Maintenance Plan App/build/build_save.py`.

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

## Gensave opdaterer (REVIEW.md D7, D8)

Før blev planens items og operationer slettet og skrevet forfra ved hvert
gem. Det gav to fejl: items fik nyt ID og ny nøgle hver gang, så
dokumentmappen (opkaldt efter `ItemKey`) ikke længere passede, og en fejl
midt i gemmet efterlod planen uden items.

Nu husker appen hver rækkes ID (`SpId` på `colVhpItems` og
`colVhpOperations`), og gemmet går i otte trin (`build_save.py`):

1. Nøglerne — de tre offsets på én gang (`Concurrent`).
2. Konflikt — er planen gemt af en anden, siden den blev åbnet
   (`Modified`), stopper gemmet, før noget er skrevet.
3. Planhovedet — altid som kladde.
4. Items — eksisterende **opdateres**, nye oprettes. Et item beholder sit
   `ID` og sit `ItemKey`.
5. Operationer — samme model.
6. Materialer og dokumentrækker skrives forfra; de gamle rækkers ID huskes.
7. Oprydning — **kun når alt ovenfor lykkedes**: operationer og items, der
   ikke længere er i appen, og de gamle materiale- og dokumentrækker.
8. Status (`In Progress` ved Submit) og `MD_RequestIndex`.

Hvert trin har sin egen `IfError` og skriver i `colVhpSaveErrors`, og et
trin kører kun, når de foregående lykkedes. En fejl giver i værste fald en
række for meget — aldrig et tab — og planen står stadig som kladde.

Save draft og Submit er den samme gemning: Submit sætter
`varVhpSubmitting` og vælger Save draft-knappen med `Select`.

> Oprydningen filtrerer delegerbart på planen (`MaintenancePlanID.Id =
> varVhpPlanSpId`) og tager `in` i hukommelsen på planens egne rækker.

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

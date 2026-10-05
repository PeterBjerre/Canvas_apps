# Prompt til VS Code (Sonnet 5) — kør SharePoint-provisioneringen

Kopiér alt under linjen ind som din første besked i VS Code.

---

Du skal køre tre PowerShell-scripts mod SharePoint. De findes allerede —
**skriv dem ikke om, og opfind ikke dine egne.**

## Kilde

Repo `PeterBjerre/Canvas_apps`, branch
`claude/vh-plans-strategy-packages-lu8w70`. **Pull først.**

Læs `docs/10-datamodel-forslag.md` inden du går i gang — den forklarer hvad
hvert script laver og hvorfor.

## Opsætning

Site: `https://orsted.sharepoint.com/teams/BioSAPDEV`

PnP.PowerShell kræver et ClientId. Det findes i tenanten. Sæt det én gang:

```powershell
[Environment]::SetEnvironmentVariable(
    "PNP_CLIENT_ID", "9bc3ab49-b65d-410a-85ad-de819febfddc", "User")
```

Åbn en **ny** terminal bagefter — miljøvariabler læses ved opstart. Ellers
send `-ClientId "9bc3ab49-b65d-410a-85ad-de819febfddc"` med på hvert kald.

Hver kørsel åbner et browservindue til login. Bed brugeren logge ind og vent.

## Kør i denne rækkefølge

Scripterne er idempotente. To af dem har `-WhatIfOnly` — **kør altid tørløbet
først, vis brugeren hvad det siger, og få et ja, før du kører rigtigt.**

```powershell
cd sharepoint\provision

# 1. Strategierne. 53 rækker fra SAP-udtrækket.
python3 ..\..\tools\gen_strategy_seed.py
.\Provision-StrategyLists.ps1 -SiteUrl "<site>"

# 2. Nye kolonner paa de tre eksisterende lister.
.\Provision-VHPlanColumns.ps1 -SiteUrl "<site>" -WhatIfOnly
.\Provision-VHPlanColumns.ps1 -SiteUrl "<site>" -Backfill

# 3. De seks tasklist-lister -> een.
.\Provision-StandardTaskOperations.ps1 -SiteUrl "<site>" -WhatIfOnly
.\Provision-StandardTaskOperations.ps1 -SiteUrl "<site>" -Migrate
```

**Kør ikke `-FixMainWorkCenterNames`** uden at spørge først. Den omdøber en
kolonne, som den gamle app kan være afhængig af. Den nye app har ikke brug
for den.

## Kontrollér bagefter

```powershell
.\..\inspect\Export-ListSchema.ps1 -SiteUrl "<site>"
python3 ..\..\tools\schema_to_md.py ..\inspect\out\schema.json
```

Åbn `sharepoint/inspect/out/schema.md` og bekræft alle seks:

1. `MD_Strategy` findes med **53 rækker** og kolonnerne `StrategyKey`,
   `StrategyName`, `SchedulingIndicator`, `Hierarchical`, `PackagesLoaded`.
2. `MD_StrategyPackage` findes og er **tom**. Det er meningen — pakkerne
   kommer fra SAP senere.
3. `MD_StandardTaskOperations` findes med **176 rækker** fordelt på seks
   værker, og har `Plant` og `OperationNo`.
4. `TaskListMain` har `OperationNo` og `PackagesKey`. `OperationNo` er
   udfyldt på alle 306 rækker.
5. `MaintenanceItems` har `OrstedResponsibleEmail`.
6. `MaintenancePlans` har ikke længere en kolonne med visningsnavnet
   `CallHorizonOLD` — den skal nu hedde `CallHorizonChoiceOLD`.

Passer et af punkterne ikke, så **rapportér det og stop**. Lap ikke data i
hånden.

## Til sidst

Commit `sharepoint/inspect/out/` og push til
`claude/vh-plans-strategy-packages-lu8w70`. Opret ikke en pull request.

## Rapportér

- Hvad hvert tørløb sagde, og hvad der faktisk blev oprettet.
- De seks kontrolpunkter, ét for ét.
- Antal rækker i `MD_Strategy` og `MD_StandardTaskOperations`.
- Alt der så mærkeligt ud.

## Det du ikke skal

- Du må ikke ændre i scripterne for at komme videre. Fejler et af dem, så
  rapportér fejlen ordret og stop — den bliver rettet i kilden.
- Du må ikke slette de seks `<VÆRK> Standard Tasklist` eller nogen anden
  liste. Migreringen kopierer; kildelisterne skal blive stående, til den
  gamle app er slukket.
- Du må ikke sætte `Hierarchical` på strategierne. Det gøres i hånden senere.
- Du må ikke røre `Maintenance Plan App/` eller `Masterdata Hub/`.

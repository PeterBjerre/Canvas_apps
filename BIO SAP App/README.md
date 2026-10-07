# BIO SAP — de fem apps samlet i én app

De fem apps (hub, Functional Location, VH-plan, Equipments og Materials) som
**skærme i én canvas app**. Sidebaren og hubben navigerer mellem skærmene med
`Navigate()` i stedet for at starte en anden app med `Launch()`: der er ingen
kold start, og det, man var i gang med, ligger der stadig, når man kommer
tilbage.

> **Status: den app, der bruges.** De fem enkeltapps er udfaset
> (2026-10-01): repoet bygger og deployer kun denne app
> (`"single_apps": "retired"` i `tools/canvas_apps.json`). Skærmene bygges
> stadig af de fem appers byggere. Se [`docs/33-udfasning.md`](../docs/33-udfasning.md).

Baggrunden for beslutningen står i
[`../docs/07-landingsside.md`](../docs/07-landingsside.md) §9.

## Skærmene

| Skærm | Indhold |
|---|---|
| `ScreenMdHub` | Hubben. Startskærm |
| `ScreenFunctionalLocation` | Functional Location |
| `ScreenVhPlan` | VH-plan |
| `ScreenEquipment` | Equipments |
| `ScreenMaterial` | Materials |
| `ScreenKks` | KKS-opslaget. En **opslagsskærm**: ingen anmodninger, så hubben åbner den ikke, og den har intet `?reqid=`. Den henter nøglerne én gang, første gang den vises. Se [`../KKS App/README.md`](../KKS%20App/README.md) |
| `ScreenIssueBoard` | Issue Board (issue #114): testernes sager — *My issues*, *Shared issues* (anonym), for admins *All issues* (admin-boardet), ny sag, redigering, kommentarer, interne noter, vedhæftninger, arkivering og sletning. Også en opslagsskærm. Se [Issue Board](#issue-board-issue-114) nedenfor. Bygges **kun** når `features.issue_board` er slået til for miljøet i `tools/canvas_apps.json`; ellers findes skærmen, menupunktet og datakilderne ikke. Lister og flow: `sharepoint/provision/Provision-IssueBoard.ps1` og `BioSap-IssueBoard-Submit` |

Hver domæneskærm har én kontrol mere end i den enkelte app: ventespinneren.
Antallet pr. skærm skrives ud af `build/check_combined.py` ved hvert build
(ca. 1.150 i alt) — det står ikke her, fordi et tal i en README forælder.

## Hvorfor den ikke bliver langsom

- **`App.OnStart` henter ingen data og kender intet domæne.** Den har kun
  temaet og hubbens fire variabler, så appen starter omtrent som hubben i
  dag.
- **Hvert domæne klargøres først, når dets skærm åbnes.** Den OnStart, et
  domæne havde som selvstændig app, kører i skærmens `OnVisible` første gang,
  skærmen vises. Kommer man tilbage, sker der ingenting.
- **Forsinket indlæsning** (standard i Studio): en skærms kontroller oprettes
  først, når man går til den. VH-planen er én skærm som i dag. Den blev
  prøvet delt i to, men det er droppet.
- **De navngivne formler** (opslagslister, FL-regler) evalueres dovent. Et
  domæne, man ikke åbner, koster ingenting.

## Hvad der er anderledes end i de fem apps

| | De fem apps | Den samlede app |
|---|---|---|
| Sidebar | `Launch(<anden app>)` | `Navigate(<skærm>)` |
| Hubbens *New request* | Starter satellitten | Navigerer og starter en ny indmelding |
| Hubbens *Open* | `Launch(AppUrl & "?reqid=…")` | Navigerer ud fra `Domain` og åbner anmodningen |
| Tilbage til et domæne | Kold start. Formularen er tom | Formularen står, som man forlod den |
| Equipments/Materials | `varDom*`, `colDom*`, `conDom*` … | `varEq*`/`varMat*` osv. De to delte 177 kontrolnavne og alle variabler |
| Tema mellem apps | Sendes med i URL'en | Én app, ét `SaveData`-lager |

**Første besøg, *New request* og *Open*.** Hubben sætter `gbl<X>Want`
(`"new:<n>"` eller `"req:<RequestGuid>"`) og navigerer. Skærmen sammenligner
med det, den sidst blev klargjort til (`var<X>Opened`). Er det det samme, sker
der ingenting. Er det noget andet, kører domænets egen opstart. Se
`build/build_screens.py`, `open_block()`.

**Ventespinner.** Mens et domæne klargøres (første besøg, *New request*,
*Open* eller et dyblink), ligger et slør over skærmen med et roterende hjul
midt på, uden tekst. Det forsvinder, når dataene er hentet, og
imens kan man ikke trykke på en formular, der er ved at blive fyldt. Hjulet
er det samme som appernes gem-spinner — én komponent,
`tools/build_helpers.py` `loading_overlay()` — og det toner først ind efter
0,15 s, så en hurtig indlæsning ikke blinker. Skærmene har **ikke** Power
Apps' egen `LoadingSpinner`: den tegnede et hjul inden i hjulet (issue #64).

## Dyblinks

```
<play-url>?domain=vhplan&reqid=<RequestGuid>
```

`domain` er én af `functionallocation`, `vhplan`, `equipment` eller
`material`. Uden `domain` åbner appen på hubben.

**Indekslisten peger på den samlede app.** Når en indmelding gemmes — også
fra en af de fem enkeltapps — skriver den `AppUrl` =
`<play-url>?domain=<domæne>&reqid=<RequestGuid>` i `MD_RequestIndex`
(`tools/request_index.py`, `COMBINED_APP`). Den samlede hub bruger ikke
`AppUrl`: den navigerer ud fra `Domain`.

> **Mailflowet skal rettes uden for repoet.**
> `BioSap-EmailNotification-NewPlanCreated` læser ikke indekset, men
> `AppUrl` i SharePoint-listen `AppSettings` og tilføjer `&ID=<planens ID>`.
> Rækkerne dér peger på den gamle VH-app i et andet miljø. Flowet skal slå
> anmodningen op i `MD_RequestIndex` (`SourceItemId` = planens ID,
> `Domain` = `MaintenancePlan`) og bruge dens `AppUrl`.

## Sådan oprettes den i Studio

1. **Opret en tom canvas app** i solution *BIO SAP*, fx med navnet
   "BIO SAP". Lad den stå åben i Studio med *Settings → Updates →
   Coauthoring* slået til.
2. **Tilføj datakilderne.** De kan ikke tilføjes fra YAML (se
   `.github/skills/canvas-build/SKILL.md`, "Datakilder skal findes i appen
   først"). Det er foreningsmængden af de fem appers:

   *SharePoint-lister (21):* `CallHorizonMatrix`, `EquipmentItems`,
   `FunctionalLocationItems`, `FunctionalLocationRequests`, `MD_FLKey`,
   `MD_HelpText`, `MD_KksFunctionKey`,
   `MD_RequestIndex`, `MD_StandardTaskOperations`, `MD_Strategy`,
   `MD_StrategyPackage`, `MD_TasklistAttachment`, `MD_TasklistMaterial`,
   `MainWorkCenters`, `MaintenanceActivityTypeList`, `MaintenanceItems`,
   `MaintenancePlans`, `MaterialItems`, `PlantList`, `SortFieldList`,
   `TaskListMain`

   *Flows (5):* `BioSap-DeleteSubmittedAttachments`,
   `BioSap-GetSubmittedAttachments`, `BioSap-Integration-FunctionalLocations`,
   `BioSap-TaskListAttachment`, `BioSap-Material-ReadInvoice` (fakturaimporten,
   [`docs/34`](../docs/34-faktura-import.md) — flowet og Office Scriptet skal
   oprettes først)

   *Kun med Issue Board slået til (issue #114):* listerne `IB_Tickets`,
   `IB_TicketComments`, `IB_AppSections`, `IB_SharedIssues` og flowet
   `BioSap-IssueBoard-Submit` samt `UserAndGroups` (admins).
3. **Sæt app-id'et** under `biosap` i `tools/canvas_apps.json`. Det står i
   Studio-URL'en (`…%2Fapps%2F<app_id>`).
4. **Deploy:**

   ```powershell
   python tools\canvas_mcp.py deploy --app biosap --clean
   ```

   `--clean` første gang, så hele træet bygges på én gang. Den tomme apps
   `Screen1` kan slettes i Studio bagefter. Det samme gælder `ScreenVhTasks`, hvis appen
   blev deployet, mens VH-planen var delt i to: deploy fjerner ikke en
   skærm, der ikke længere findes i repoet.

## Testplan

1. Åbn appen: hubben vises, og ingen domæne henter data (Monitor i Studio).
2. Sidebar → VH-plan → udfyld planhovedet → sidebar → Equipments →
   sidebar → VH-plan. Planhovedet skal stå, som man forlod det.
3. Hub → *New request* på VH-plan, mens en plan er åben: en ny, tom plan.
4. Hub → *Open* på en gemt VH-plan: ventespinneren vises, og planen, dens
   items og operationer indlæses.
5. Equipments og Materials: udfyld formularen i den ene, skift til den anden
   og tilbage. Formularerne må ikke blande sig.
6. Dyblink: `?domain=vhplan&reqid=<guid>` åbner direkte i planen.
7. **Functional Location:**
   1. Hub → *New request* på Functional Location → tilføj tre rækker, heraf
      én ugyldig. Rækkerne valideres af sig selv, nummeret og de røde kanter
      står rigtigt, og Submit er spærret.
   2. Ret rækken, åbn detaljeruden på en række, ret et felt dér, og luk.
   3. *Save draft* → hubben viser anmodningen som kladde, og dens `AppUrl`
      er `…?domain=functionallocation&reqid=…`.
   4. Sidebar → VH-plan → sidebar → Functional Location: rækkerne står, som
      man forlod dem (ingen genindlæsning, D23).
   5. Hub → *New request* på Functional Location, mens en anmodning er
      åben: en ny, tom anmodning — ikke den gamle.
   6. Hub → *Open* på den gemte kladde: ventespinneren, og rækkerne og
      spool-værdierne indlæses. Slet én række, gem igen, og tjek i listen,
      at kun den række er væk.
   7. Dyblink `?domain=functionallocation&reqid=<guid>` åbner direkte i
      anmodningen.
   8. Submit med gyldige rækker → status *Indsendt*, og formularen låses.
8. Mål: tid til hubben vises og første besøg på hvert domæne, sammenlignet
   med de fem apps.
9. **Materials → Import invoice:** testplanen i
   [`docs/34`](../docs/34-faktura-import.md#testplan).

## Issue Board (issue #114)

Et midlertidigt sags- og feedbacksystem til udviklings- og testfasen. Koden
står i `Issue Board/build/` (`ib_config.py` har navne, lister og regler),
listerne i `sharepoint/provision/Provision-IssueBoard.ps1` og flowet i
`solution/BIOSAP/src/Workflows/BioSap-IssueBoard-Submit-*.json`.

- **Sikkerhed:** appen læser med brugerens egen forbindelse, og alt, der
  ændrer noget, går gennem flowet. Flowet tjekker admin (`UserAndGroups`,
  Title = Admin) og rapportør på serveren for hver handling. Rettighederne
  sidder på hver række: rapportøren *Read*, admins *Contribute*. En intern
  note får ingen rettighed for rapportøren.
- **Handlinger i flowet:** `create`, `comment` (også interne noter), `edit`
  (rapportøren mens sagen er *New*; admin altid, inkl. status, prioritet,
  tildeling og løsning), `reopen`, `archive` (og gendan), `delete` (kun med
  sagsnummeret) og `attach`. Hver ændring bliver sin egen række i
  `IB_TicketComments`.
- **Vedhæftninger** er SharePoint-vedhæftninger på sagens række i
  `IB_Tickets`, så de arver rækkens rettigheder. De vises aldrig på det delte
  board.
- **Mail** går kun til rapportøren: når en admin svarer synligt, når sagen er
  *Ready for retest*, og når den er *Closed*.
- **Det delte board** (`IB_SharedIssues`) holdes ajour af flowet. En arkiveret
  sag fjernes fra det; gendannes den, kommer den tilbage.

### Fjernelse før produktion

- [ ] Sæt `features.issue_board` til `false` (eller fjern linjen) for miljøet
  i `tools/canvas_apps.json`, byg og deploy. Så er skærmen, menupunktet,
  deeplinket og alle formlerne væk.
- [ ] Slet `ScreenIssueBoard` i Studio, hvis den står der fra et tidligere
  deploy (deploy fjerner ikke skærme).
- [ ] Fjern datakilderne `IB_Tickets`, `IB_TicketComments`, `IB_AppSections`,
  `IB_SharedIssues` og flowet `BioSap-IssueBoard-Submit` i Studio.
  `UserAndGroups` bliver; resten af appen bruger den.
- [ ] Slå flowet `BioSap-IssueBoard-Submit` fra, og slet det fra solution
  (inkl. `RootComponent` i `Solution.xml`). Det fjerner også mailene; der er
  ingen andre notifikationer.
- [ ] Eksportér de fire `IB_*`-lister, inkl. vedhæftninger på `IB_Tickets`,
  hvis historikken skal gemmes. Slet derefter listerne (`IB_SharedIssues` er
  den anonyme kopi; den har intet, der ikke også står i `IB_Tickets`).
- [ ] Fjern flowkontoens Full Control på listerne, hvis den er givet andre
  steder end på de slettede lister.
- [ ] Der er ingen miljøvariabler og ingen egne forbindelser at rydde op i:
  flowet bruger `BioSap-SiteUrl` og forbindelserne `orsted_BioSapSharePointConn`
  og `orsted_BioSapOutlookConn`, som resten af BIO SAP også bruger.
- [ ] Fjern `Issue Board/`, `sharepoint/provision/Provision-IssueBoard.ps1`,
  `sharepoint/seed/IB_AppSections.csv`, `tests/test_issue_board.py`,
  `issueboard` i `tools/canvas_apps.json` og ikonet i `tools/icons.py`.

## Byg

```bash
python3 tools/build_all.py              # alle apps, den samlede til sidst
python3 tools/build_all.py --app biosap # kun den samlede
```

| Fil | Indhold |
|---|---|
| `build/combined.py` | Domænerne, omdøbningen og indlæsningen af de fem appers `App.pa.yaml` |
| `build/generate_app.py` | → `../App.pa.yaml`: formlerne flettet, slank OnStart, StartScreen |
| `build/build_screens.py` | → de seks skærme. Hver app i sin egen proces |
| `build/check_combined.py` | Unikke navne i hele appen, ingen referencer på tværs af skærme, ingen delte variabler |
| `build/check_layout.py` | `tools/check_layout.py` på hver skærm |

**Der er ingen skærmbyggere her.** Skærmene bygges af de fem appers egne
byggere. Kun navigationen, navnene og opstarten ændres. Retter du noget i et
domæne, så ret det i domænets egen app. Byggeriet stopper med en besked, hvis
en af de fem apps ændrer sig, så den samlede app ikke længere passer, fx en
anden OnStart eller OnVisible.

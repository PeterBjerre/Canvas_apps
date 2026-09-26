# BIO SAP — de fem apps samlet i én app

De fem apps (hub, Functional Location, VH-plan, Equipments og Materials) som
**skærme i én canvas app**. Sidebaren og hubben navigerer mellem skærmene med
`Navigate()` i stedet for at starte en anden app med `Launch()`: der er ingen
kold start, og det, man var i gang med, ligger der stadig, når man kommer
tilbage.

> **Status: til test.** De fem enkelte apps bliver, som de er, indtil den
> samlede app er testet og godkendt. Begge dele bygges af de samme byggere,
> så en rettelse i en af de fem apps kommer også med her ved næste build.

Baggrunden for beslutningen står i
[`../docs/07-landingsside.md`](../docs/07-landingsside.md) §9.

## Skærmene

| Skærm | Indhold | Kontroller |
|---|---|---|
| `ScreenMdHub` | Hubben. Startskærm | 106 |
| `ScreenFunctionalLocation` | Functional Location | 114 |
| `ScreenVhPlan` | VH-plan **1/2**: plan og items (trin 1–2) + gem | 239 |
| `ScreenVhTasks` | VH-plan **2/2**: det aktive items task list, operationer, pakker, materialer, dokumenter, dispatch (trin 3–5) + gem | 210 |
| `ScreenEquipment` | Equipments | 208 |
| `ScreenMaterial` | Materials | 229 |
| | **I alt** | **1.106** |

Tallene skrives af `build/check_combined.py` ved hvert build.

## Hvorfor den ikke bliver langsom

- **`App.OnStart` henter ingen data og kender intet domæne.** Den har kun
  temaet og hubbens fire variabler, så appen starter omtrent som hubben i
  dag.
- **Hvert domæne klargøres først, når dets skærm åbnes.** Den OnStart, et
  domæne havde som selvstændig app, kører i skærmens `OnVisible` første gang,
  skærmen vises. Kommer man tilbage, sker der ingenting.
- **Forsinket indlæsning** (standard i Studio): en skærms kontroller oprettes
  først, når man går til den. Derfor er VH-planen delt i to. Hver af de to
  halvdele er omtrent på størrelse med de andre skærme.
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

**VH-planens to skærme.** Knappen *Task list* i topbjælken fører til skærm 2,
og *Plan and items* fører tilbage. Øverst på skærm 2 kan man skifte aktivt
item uden at gå tilbage. Gem-kortet står på begge skærme.

## Dyblinks

```
<play-url>?domain=vhplan&reqid=<RequestGuid>
```

`domain` er én af `functionallocation`, `vhplan`, `equipment` eller
`material`. Uden `domain` åbner appen på hubben.

> **Indekslisten peger stadig på de fem apps.** Når en indmelding gemmes,
> skriver den sin `AppUrl` i `MD_RequestIndex`, og i testperioden er det de
> fem appers URL'er. Den samlede hub bruger ikke `AppUrl`: den navigerer ud
> fra `Domain`. Mailflowet og den gamle hub åbner derfor stadig de enkelte
> apps. Når der skiftes over, skal `AppUrl` pege på den samlede app med
> `?domain=…`. URL'en står i `PLAY_URL` i Equipments', Materials' og
> Functional Locations `*_config.py` og i `APP_URL` i VH-planens
> `build_save.py`.

## Sådan oprettes den i Studio

1. **Opret en tom canvas app** i solution *BIO SAP*, fx med navnet
   "BIO SAP". Lad den stå åben i Studio med *Settings → Updates →
   Coauthoring* slået til.
2. **Tilføj datakilderne.** De kan ikke tilføjes fra YAML (se
   `.github/skills/canvas-build/SKILL.md`, "Datakilder skal findes i appen
   først"). Det er foreningsmængden af de fem appers:

   *SharePoint-lister (19):* `CallHorizonMatrix`, `EquipmentItems`,
   `FunctionalLocationItems`, `FunctionalLocationRequests`, `MD_HelpText`,
   `MD_RequestIndex`, `MD_StandardTaskOperations`, `MD_Strategy`,
   `MD_StrategyPackage`, `MD_TasklistAttachment`, `MD_TasklistMaterial`,
   `MainWorkCenters`, `MaintenanceActivityTypeList`, `MaintenanceItems`,
   `MaintenancePlans`, `MaterialItems`, `PlantList`, `SortFieldList`,
   `TaskListMain`

   *Flows (4):* `BioSap-DeleteSubmittedAttachments`,
   `BioSap-GetSubmittedAttachments`, `BioSap-Integration-FunctionalLocations`,
   `BioSap-TaskListAttachment`
3. **Sæt app-id'et** under `biosap` i `tools/canvas_apps.json`. Det står i
   Studio-URL'en (`…%2Fapps%2F<app_id>`).
4. **Deploy:**

   ```powershell
   python tools\canvas_mcp.py deploy --app biosap --clean
   ```

   `--clean` første gang, så hele træet bygges på én gang. Den tomme apps
   `Screen1` kan slettes i Studio bagefter.

## Testplan

1. Åbn appen: hubben vises, og ingen domæne henter data (Monitor i Studio).
2. Sidebar → VH-plan → udfyld planhovedet → sidebar → Equipments →
   sidebar → VH-plan. Planhovedet skal stå, som man forlod det.
3. Hub → *New request* på VH-plan, mens en plan er åben: en ny, tom plan.
4. Hub → *Open* på en gemt VH-plan: planen, dens items og operationer
   indlæses. Skift til skærm 2 med *Task list*, og skift item i vælgeren øverst.
5. Equipments og Materials: udfyld formularen i den ene, skift til den anden
   og tilbage. Formularerne må ikke blande sig.
6. Dyblink: `?domain=vhplan&reqid=<guid>` åbner direkte i planen.
7. Mål: tid til hubben vises og første besøg på hvert domæne, sammenlignet
   med de fem apps.

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
ny sektion i VH-planen eller en anden OnStart.

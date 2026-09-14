# Prompt til VS Code (Sonnet 5) — deploy VH-plan appen mod de rigtige lister

Kopiér alt under linjen ind som din første besked i VS Code.

---

VH-plan appen kører ikke længere på testdata. Den læser nu SharePoint gennem
navngivne formler. Din opgave er at få den i Power Apps Studio og verificere.

## Kilde

Repo `PeterBjerre/Canvas_apps`, branch
`claude/vh-plans-strategy-packages-lu8w70`. **Pull først.**

Læs `docs/11-app-mod-rigtige-lister.md` og
`.github/skills/canvas-build/SKILL.md` inden du går i gang.

| | |
|---|---|
| Miljø | Bioenergy Solutions DEV |
| `environment_id` | `e0f8f822-d16a-e878-ba4e-fb42bc617e47` |
| `app_id` | `11fa8d90-868a-45a4-ba23-28f2cf0671a2` |
| SharePoint | `https://orsted.sharepoint.com/teams/BioSAPDEV` |

## Trin 0 — datakilderne SKAL være der først

`compile_canvas` fejler på et ukendt navn, hvis en datakilde mangler. Bed
brugeren tilføje **alle ti lister** plus flowet i Studio:

```
PlantList                    SortFieldList
MaintenanceActivityTypeList  CallHorizonMatrix
MainWorkCenters              MaintenanceItems
MaintenancePlans             MD_Strategy
MD_StrategyPackage           MD_StandardTaskOperations
```

plus flowet `BioSap-Integration-FunctionalLocations`.

**Og så skal de GEMME (Ctrl+S).** At tilføje en datakilde uden at gemme er
ikke nok — det er den fælde, FL-søgningen ramte sidst. Gå ikke videre, før
brugeren har bekræftet at der er gemt.

## Trin 1 — byg og synk

```bash
python3 tools/build_all.py        # skal være grøn hele vejen
```

Derefter, med `directoryPath` = den lokale sti til mappen
`Maintenance Plan App` (ikke `build/`):

```
canvas-authoring-connect          environment_id = <ovenfor>, app_id = <ovenfor>
canvas-authoring-compile_canvas   directoryPath = <sti>
canvas-authoring-sync_canvas      directoryPath = <sti>
canvas-authoring-get_appchecker_errors
canvas-authoring-get_accessibility_errors
```

**Compile før sync.** Fejler compile, så stop og rapportér — synk ikke en app,
der ikke kan oversættes.

Ret aldrig i `.pa.yaml` — den er genereret. Skal noget laves om, så ret i
`Maintenance Plan App/build/*.py`, kør `tools/build_all.py` igen, og synk.
Datakilde-navne og kolonner står i `build/sp_config.py` og kun der.

## Trin 2 — appindstilling

Sæt **Data row limit til 2000** (Indstillinger → Generelt). Standarden på 500
er for lav: `MD_StandardTaskOperations` har 176 rækker, men `TaskListMain` har
306 og vokser.

## Trin 3 — test manuelt

Ingen automatiserede browsertests. Kør listen og rapportér hvert punkt.

**Opstart**

1. Åbn appen med stopur. Den skal være klar på **under 2 sekunder**.
   `App.OnStart` henter ingen data — er den langsom, er der noget galt.
2. App checker → Performance. Der må ikke være advarsler om `App.OnStart`.

**Data kommer fra de rigtige lister**

3. Under planhovedet står en statuslinje. Den skal vise
   **6 standardarbejdsplaner**, **53 strategier (52 uden pakker)** og
   **53 arbejdscentre**. Står der 0 et sted, er den datakilde ikke tilføjet.
4. **Værk**-dropdownen skal have 6 værdier fra `PlantList`.
5. **Sorteringsfelt** skal have 28 værdier fra `SortFieldList`.
6. **Call horizon** skal have 16 værdier fra `CallHorizonMatrix`.
7. **Enhed** skal vise H, DAY, WK, MON, YR — de kommer fra choice-kolonnen på
   `MaintenancePlans`, ikke fra en liste.

**Arbejdscentre afgrænses på værk**

8. Uden valgt værk: arbejdscenter-dropdownen på et item viser alle 53.
9. Vælg værk **SSV** → dropdownen skal kun vise SSV-arbejdscentre, og
   værdierne må **ikke** have efterstillede mellemrum.

**Arbejdsplaner**

10. Vælg en tasklist på et item → operationerne skal komme fra
    `MD_StandardTaskOperations`, nummereret 10, 20, 30 …
11. Antallet pr. værk skal være: ASV 26, AVV 37, HEV 30, KYV 20, SKV 31,
    SSV 32.

**Strategier — det vigtigste**

12. Skift plantype til **Strategiplan**. Strategi-dropdownen skal vise
    **alle 53**, og 52 af dem skal være mærket `(pakker mangler)`.
13. Vælg en strategi **med** mærket, fx `101`. Pakkematricen skal **ikke**
    tegnes. Der skal i stedet stå en forklaring om at strategien ikke har
    pakker i `MD_StrategyPackage` endnu.
14. Vælg strategi **128** (uden mærke). Nu skal matricen tegnes med **tre
    pakkekolonner**: `1Y`, `2Y`, `3Y`.
15. Tilføj mindst to operationer på det aktive item og sæt kryds i matricen.
    Krydsene skal blive stående, når du skifter item og skifter tilbage.
16. Knappen **Hierarki-udfyld** skal være **grå**, og der skal stå en linje
    under den om at det ikke er afklaret, om strategi 128 er hierarkisk.
    Det er meningen — se `docs/11` for hvorfor.
17. Knappen **Alle pakker** skal virke og sætte kryds i alle tre.

**FL-søgning**

18. Skriv 7 tegn i Functional Location-feltet. Flowet skal kaldes, og
    resultaterne skal komme i samme felt. Skriv videre — der må **ikke**
    komme et nyt flow-kald pr. tastetryk.

**Layout**

19. Træk vinduet ned til ~900 px bredde. Intet må blive klippet, og
    intet må vokse ukontrolleret.

## Rapportér

- Opstartstid i sekunder.
- Punkt for punkt: grønt eller hvad der fejlede.
- Ordret hvad compile og app checker sagde.
- Hvis et af tallene i punkt 3-6 og 11 er forkert: hvilket, og hvad der stod.

## Det du ikke skal

- Du må ikke rette i `.pa.yaml`. Den er genereret.
- Du må ikke ændre i SharePoint-listerne.
- Du må ikke sætte `Hierarchical` på strategierne.
- Commit og push kun til `claude/vh-plans-strategy-packages-lu8w70`.
  Opret ikke en pull request.

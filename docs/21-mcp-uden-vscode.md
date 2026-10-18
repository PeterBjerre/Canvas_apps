# Byg og synkronisér selv — uden VS Code

`tools/canvas_mcp.py` starter **den samme MCP-server**, VS Code starter, og
kalder dens værktøjer direkte. Ingen agent, ingen model, ingen credits: det
er ét Python-script, der taler JSON-RPC over stdio med serveren.

```powershell
# alt på én gang: byg -> compile -> sync -> app checker
python tools\canvas_mcp.py deploy --app biosap

# forudsætningerne tjekkes med
python tools\doctor.py
```

## Før du kører

1. **Åbn appen i Power Apps Studio** og lad browserfanen stå åben, mens
   scriptet kører.
2. **Coauthoring skal være slået til**: Settings → Updates → Coauthoring.
3. **.NET 10 SDK** skal være installeret — ikke kun runtime:

   ```powershell
   dotnet --list-sdks     # skal vise en 10.x
   ```

Serveren har ingen egen forbindelse til Power Apps. Den arbejder gennem
coauthoring-sessionen, der hører til den åbne fane. Lukker du fanen, holder
`compile` og `sync` op med at virke — det er ikke en fejl i scriptet.

## Hvad serveren er

| | |
|---|---|
| Pakke | `Microsoft.PowerApps.CanvasAuthoring.McpServer` (NuGet) |
| Startes med | `dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes` |
| Første kørsel | henter pakken ned — det tager et øjeblik |

`dnx` følger med .NET 10 SDK. Findes den ikke i PATH, kører scriptet
`dotnet dnx` i stedet. Du kan overskrive kommandoen helt:

```powershell
$env:CANVAS_MCP_COMMAND = "dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes"
```

## De tre trin, og hvad de hver især gør

```
python tools/build_all.py      genererer .pa.yaml + kører layout-tjekket
canvas-authoring compile_canvas validerer mappen MOD den åbne session
                                — det er her ændringen når Studio
canvas-authoring sync_canvas    skriver sessionens tilstand NED i mappen
```

**`sync_canvas` går fra serveren til disken, ikke omvendt.** Den overskriver
filerne i den mappe, den peges på. Derfor arbejder scriptet aldrig direkte i
app-mappen: `deploy` kopierer først `*.pa.yaml` til `.canvas-deploy/<app>/`
og sender derfra, og `pull` lander i `.canvas-sync/<app>/`. Begge mapper er
i `.gitignore`. Repoets genererede kilder bliver stående, som builderne
skrev dem.

Til sidst viser `deploy`, hvor meget serverens udgave afviger fra den, du
sendte. En forskel er **normalisering**, ikke en fejl: Power Apps fjerner de
egenskaber, den betragter som standardværdier. Kopiér den aldrig tilbage
over kilderne — se `.github/skills/canvas-build/SKILL.md`.

## Kommandoerne

| Kommando | Gør |
|---|---|
| `deploy` | byg → aftryk af Studio + drift-kontrol → compile → sync → app checker + tilgængelighed → forskelsrapport |
| `pull` | henter Studios nuværende tilstand ned i `.canvas-sync/<app>/` |
| `check` | kun app checker og tilgængelighedstjek |
| `tools` | viser serverens værktøjer og deres parametre |
| `raw` | kalder ét værktøj direkte: `raw --tool describe_control --args '{"name":"Label"}'` |

Nyttige flag: `--no-build` (spring byggeriet over), `--compile-only` (stop
før sync), `-v` (vis alt, der går over stdio), `--login-hint din@mail`,
`--auth-flow browser|broker|devicecode`, `--timeout 1800`, `--env dev`
(miljøet; uden `--env` er det `default_environment`, dvs. dev).

Sikkerhedsflag (R2-064/R2-065):

- `--no-build` sender kun YAML, der er **committet**. Har app-mappen
  ucommittede `*.pa.yaml`, stopper deployet før login — YAML'en er ikke
  builderens. `--allow-dirty` sender den alligevel.
- `--overwrite-studio` deployer, selvom drift-kontrollen har set, at appen
  er ændret i Studio siden sidste deploy (se nedenfor).

Deployets sidste linje nævner commit'en (`commit abc1234`, med `-dirty`,
hvis arbejdstræet har ucommittede ændringer), så et deploy kan knyttes til
en commit.

### Aftryk og drift-kontrol før deploy

Lige efter `connect` henter `deploy` Studios nuværende tilstand ned i en
tidsstemplet mappe, `.canvas-sync/<app>/ÅÅÅÅMMDD-TTMMSS/` (samme kald som
`pull`; de 5 seneste aftryk beholdes, mappen er i `.gitignore`). Det er
**aftrykket før deploy** — det, der stod i Studio, før noget blev sendt.

Aftrykket sammenlignes derefter med serverens tilstand lige efter **sidste**
deploy fra samme pc (`.canvas-deploy/<app>-sidst/`). Er en skærm eller
`App.pa.yaml` ændret i mellemtiden — en kollega har rettet en formel eller
tilføjet en kontrol i Studio — stopper deployet med kontrolnavn og
egenskab, før noget er sendt:

```
STOP: Studio er aendret siden sidste deploy. Koer 'pull', flyt
aendringen til builderen, eller deploy med --overwrite-studio.
```

Første deploy på en pc har ingen baseline og skriver kun en NB. Baselinen
gemmes kun, når et deploy når til sync; en afvist compile eller
`--compile-only` sletter den, så næste deploy ikke tager vores egen halve
ændring for en Studio-ændring.

Efter sync sammenlignes både skærmenes træ og `App.pa.yaml` (OnStart,
Formulas, OnError …) med det byggede (R2-092).

## Appene

`tools/canvas_apps.json` holder miljø- og app-id'erne:

```json
"vhplan": { "folder": "Maintenance Plan App", "app_id": "11fa8d90-..." }
```

Begge id'er står i Studio-URL'en:

```
https://make.powerapps.com/e/<environment_id>/canvas/?action=edit&app-id=...%2Fapps%2F<app_id>
```

`Masterdata Hub` har endnu ingen `app_id` — udfyld den, når appen er oprettet
i Studio. Scriptet siger til, før det bygger og logger ind.

### Miljøerne

| Miljø | Status | SharePoint-site | Solution-version |
|---|---|---|---|
| `dev` (standard) | i brug — både udvikling og brugernes app i dag | DEV-teamsitet (`site` i `sharepoint/inspect/out/schema.json`) | 1.1.0.8 (eksport 2026-10-13, `solution/BIOSAP/src/Other/Solution.xml`) |
| `test` | **skabelon** — findes ikke endnu | – | – |
| `prod` | **skabelon** — afventer IT (PROD-pipeline) | – | – |

`test` og `prod` står i `tools/canvas_apps.json` med pladsholdere (`<...>`)
i stedet for id'er og alle feature flags `false`. Et miljø med en
pladsholder kan ikke vælges: `build_all.py --env prod`, `canvas_mcp.py
--env prod` og `export_solution.ps1` stopper med "er en skabelon". Når et
miljø findes: udfyld `environment_id` og `apps.biosap.app_id`, slå de
features til, der er provisioneret dér, og ret tabellen her.

`default_environment` er stadig `dev`, så den kendte kommando
`python tools\canvas_mcp.py deploy --app biosap --clean` virker uændret. At
kræve `--env`, når der er flere miljøer, ville bryde den — det kan slås
til ved at fjerne `default_environment`, når PROD findes.

## Når noget går galt

| Symptom | Årsag |
|---|---|
| `Kunne ikke starte MCP-serveren` | .NET 10 SDK mangler, eller terminalen er ikke genstartet efter installationen |
| `connect` fejler med 401/403 | tilføj `--login-hint din@mail` eller `--auth-flow browser` |
| compile fejler med `Unknown property` på snesevis af kontroller | versionskonflikt på en kontroltype — kør `raw --tool describe_control` og ret creation keywords i builderen |
| compile er grøn, men Studio rører sig ikke | fanen er lukket, eller coauthoring er slået fra — genåbn appen og kør igen |
| Byggeriet stopper før login | layout-tjekket er rødt. Ret i `build/*.py` — lap aldrig YAML'en |
| `STOP: Studio er aendret siden sidste deploy` | nogen har ændret appen i Studio. Kør `pull`, flyt ændringen til builderen, byg, og deploy igen — eller `--overwrite-studio`, hvis ændringen skal væk |
| `--no-build: ... ucommittede .pa.yaml` | YAML'en er ikke builderens. Byg uden `--no-build`, eller commit først |
| Deploy hænger | serveren svarer ikke (lukket fane, mistet session). `--timeout` afbryder nu med serverloggen |
| compile afvist / træet forkert efter deploy (evt. tom skærm efter `--clean`) | se **Gendan** nedenfor |

### Gendan

Et deploy, der fejler efter compile, kan have efterladt appen **delvist
ændret** — Studio tager imod en skærm, også når valideringen fejler, og
efter `--clean` kan skærmen stå tom. Deployet skriver da stien til
aftrykket. To veje tilbage:

1. **Ret builderen og deploy igen** (repoet er facit).
2. **Gendan en tidligere version i Studio**: appens *Details → Versions*
   (make.powerapps.com) og *Restore* på versionen før deployet (om hvert
   deploy giver sin egen version, er ikke efterprøvet). Aftrykket i `.canvas-sync/<app>/<tidsstempel>/`
   viser, hvad der stod i Studio før — fx en datakilde, nogen havde tilføjet.

Compile-fejl rettes **i builderen**, aldrig i YAML'en. Den regel er den
samme her som i VS Code — se `.github/skills/canvas-build/SKILL.md`.

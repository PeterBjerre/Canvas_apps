# Byg og synkronisér selv — uden VS Code

`tools/canvas_mcp.py` starter **den samme MCP-server**, VS Code starter, og
kalder dens værktøjer direkte. Ingen agent, ingen model, ingen credits: det
er ét Python-script, der taler JSON-RPC over stdio med serveren.

```powershell
# alt på én gang: byg -> compile -> sync -> app checker
python tools\canvas_mcp.py deploy --app vhplan

# eller, med forudsætningstjek først
.\tools\Deploy-CanvasApp.ps1 -App vhplan
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
| `deploy` | byg → compile → sync → app checker + tilgængelighed → forskelsrapport |
| `pull` | henter Studios nuværende tilstand ned i `.canvas-sync/<app>/` |
| `check` | kun app checker og tilgængelighedstjek |
| `tools` | viser serverens værktøjer og deres parametre |
| `raw` | kalder ét værktøj direkte: `raw --tool describe_control --args '{"name":"Label"}'` |

Nyttige flag: `--no-build` (spring byggeriet over), `--compile-only` (stop
før sync), `-v` (vis alt, der går over stdio), `--login-hint din@mail`,
`--auth-flow browser|broker|devicecode`, `--timeout 1800`.

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

## Når noget går galt

| Symptom | Årsag |
|---|---|
| `Kunne ikke starte MCP-serveren` | .NET 10 SDK mangler, eller terminalen er ikke genstartet efter installationen |
| `connect` fejler med 401/403 | tilføj `--login-hint din@mail` eller `--auth-flow browser` |
| compile fejler med `Unknown property` på snesevis af kontroller | versionskonflikt på en kontroltype — kør `raw --tool describe_control` og ret creation keywords i builderen |
| compile er grøn, men Studio rører sig ikke | fanen er lukket, eller coauthoring er slået fra — genåbn appen og kør igen |
| Byggeriet stopper før login | layout-tjekket er rødt. Ret i `build/*.py` — lap aldrig YAML'en |

Compile-fejl rettes **i builderen**, aldrig i YAML'en. Den regel er den
samme her som i VS Code — se `.github/skills/canvas-build/SKILL.md`.

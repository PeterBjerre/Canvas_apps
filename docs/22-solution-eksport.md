# Solution-eksport — flows og miljøvariabler i repoet

MCP-serveren kan kun tale med den ene canvas app, der er åben i Studio.
Alt andet i solution BIO SAP — flows, miljøvariabler, connection
references, tabeller — findes kun i browseren, indtil det bliver hentet ned.

```powershell
.\tools\export_solution.ps1 -List                    # find det unikke navn
.\tools\export_solution.ps1 -Solution BIOSAP         # hent og rens
```

## Hvad kæden gør

```
pac auth create      log ind i miljøet (kun første gang)
pac solution list    find solutionens UNIKKE navn, ikke visningsnavnet
pac solution clone   hent den udpakket ned i .\solution
scrub_solution.py    fjern hemmeligheder FØR git ser dem
```

`pac` behøver ikke være installeret. Scriptet bruger den, hvis den ligger i
PATH, og henter den ellers på stedet med `dnx` — samme mekanisme som
MCP-serveren, og .NET 10 SDK er det eneste, der skal være der.

## Hvad du får ud af det

| Mappe | Indhold |
|---|---|
| `Workflows/` | Hvert flow som JSON — trigger, handlinger, udtryk, svarskema |
| `environmentvariabledefinitions/` | Variablernes navne og typer |
| `connectionreferences/` | Hvilke connectorer der bruges — også dem, der gør en app premium |
| `Other/Solution.xml` | Komponentlisten |

Det mest konkrete: `Maintenance Plan App/build/build_flsearch.py` har fire
konstanter, der beskriver flowets kontrakt — outputnavnet
`functionallocationoutput` og feltnavnene. De står der, fordi nogen åbnede
flowet i browseren og skrev dem af. Med eksporten i repoet kan de
efterprøves mod flowets faktiske svarskema.

## Rensningen er ikke valgfri

En eksporteret solution er ikke uskyldig tekst. Flow-definitioner bærer
endpoint-URL'er og nogle gange nøgler, og miljøvariablernes **værdier** er
præcis det sted, hvor en client secret ender. Lander det på GitHub, kan det
ikke kaldes tilbage — heller ikke ved at slette filen bagefter, for
historikken bliver.

`tools/scrub_solution.py` kører derfor altid mellem eksporten og git:

1. Miljøvariablernes **værdifiler slettes**. Definitionerne bliver — det er
   dem, der fortæller hvad en variabel hedder og gør. Værdien hører til
   miljøet, ikke til koden.
2. Felter, der ligner en hemmelighed, overskrives med `***REDACTED***`:
   `client_secret`, `password`, `x-functions-key`, `Authorization`,
   SAS-signaturer, JWT'er og en snes andre.
3. Alt, der blev rørt, skrives ud. Intet sker i stilhed.

Standarden er at **redigere**, ikke at advare og lade det ligge — så en
glemt gennemlæsning ikke er nok til at lave skaden. Vil du se listen først:

```powershell
.\tools\export_solution.ps1 -Solution BIOSAP -ReportOnly
python tools\scrub_solution.py solution --report-only
```

JSON'en er stadig gyldig efter redigeringen; kun værdien bag nøglen er
skiftet ud.

> **Det er et sikkerhedsnet, ikke en garanti.** Læs flow-definitionerne
> igennem, før du committer. Et hemmeligt felt kan hedde noget, ingen har
> tænkt på.

## Den ene regel

**Eksporten er læsestof. Builderne er kilden.**

`solution/` indeholder også de to canvas apps som `.msapp`. De er
*resultatet* af sidste deploy, ikke kilden til den næste. Retter nogen i en
`.msapp`, eller pakker solutionen tilbage med `pac solution pack`, er
ændringen væk ved næste `python3 tools/build_all.py` — og så er der to
sandheder om den samme skærm.

`.msapp`-filerne er derfor i `.gitignore`. Skal du se, hvad der faktisk
ligger i Studio lige nu, så brug den vej, der er beregnet til det:

```powershell
python tools\canvas_mcp.py pull --app vhplan
```

Og husk, at eksporten er et øjebliksbillede: ændrer nogen et flow, ved
repoet det først, når den er hentet igen.

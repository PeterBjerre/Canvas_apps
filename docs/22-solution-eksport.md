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

`.msapp`-filerne er derfor i `.gitignore`.

## Men så kunne app'erne ikke læses — det er rettet

`.msapp` er en zip, og inde i den ligger app'ens skærme som `.pa.yaml`.
Fordi zip'en aldrig nåede GitHub, gjorde YAML'en det heller ikke. En app,
der kun findes i solutionen — Equipment, Materialer, KKS — var dermed en
sort kasse for alle andre end den, der sad ved maskinen. Eksporten lovede
at være *hele* solutionen; canvas apps var i praksis undtaget.

`tools/unpack_msapp.py` pakker dem nu ud som tekst ved siden af zip'en:

```
solution/BIOSAP/src/CanvasApps/<navn>.src/Src/*.pa.yaml
                                         /References/DataSources.json
                                         /Properties.json
```

`export_solution.ps1` kalder den selv — **før** rensningen, for en formel
kan bære en URL eller en nøgle, og `scrub_solution.py` kan kun fjerne det,
den kan se.

Tre ting kommer bevidst ikke med:

| Springes over | Hvorfor |
| --- | --- |
| `_EditorState.pa.yaml` | Studiets eget bogholderi over markeringer og foldede noder. Støj i enhver diff. |
| `Controls/*.json` | Den samme app en gang til, i maskinform. Formlerne står allerede læsbart i `.pa.yaml`. |
| `.msapp` selv | Binær. Det var hele udgangspunktet. |

Mappen bygges forfra hver gang. Slettes en skærm i Studio, forsvinder filen
også her — ellers ville der stå en skærm i repoet, som app'en ikke har.

**Det ændrer ikke reglen.** `<navn>.src` er læsestof som resten af
eksporten. For `orsted_maintenanceplan_82090.src` og
`orsted_masterdatahub_1b09a.src` står den samme skærm nu to steder: builderens
resultat i app-mappen, og deployets øjebliksbillede i eksporten. Rediger
altid builderen. Eksportkopien er god til én ting: at se, om det, der ligger
i Studio, er det, vi sidst byggede.

Skal du se, hvad der faktisk ligger i Studio *lige nu*, så brug den vej, der
er beregnet til det:

```powershell
python tools\canvas_mcp.py pull --app vhplan
```

Og husk, at eksporten er et øjebliksbillede: ændrer nogen et flow, ved
repoet det først, når den er hentet igen.

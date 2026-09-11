# Excel → SAP via GUI Scripting

Modulerne her er skrevet til at blive **importeret i en eksisterende
projektmappe**, ikke til at være en færdig løsning. Ingen af dem afhænger af
den medfølgende skabelon; de afhænger kun af, at tabellerne hedder det, der
står i `modConfig`.

Arkitekturen er beskrevet i [`../docs/06-excel-gui-scripting.md`](../docs/06-excel-gui-scripting.md).

## Sådan tager du det i brug

1. Åbn `VHPlan-SAP-skabelon.xlsx` og **gem som `.xlsm`** (eller brug din
   eksisterende projektmappe og opret tabellerne der).
2. Alt+F11 → Filer → Importer fil → importér alle `.bas` fra `vba/`.
3. Kun hvis du vil bruge JSON-loaderen: importér også
   [JsonConverter.bas](https://github.com/VBA-tools/VBA-JSON) og sæt en
   reference til *Microsoft Scripting Runtime*.
4. Data → Hent data → Tom forespørgsel → Avanceret editor: indsæt hver fil fra
   `powerquery/` og indlæs i arket med **samme tabelnavn**.
5. Log ind i SAP manuelt. Makroen logger ikke ind — det ville kræve
   adgangskoden i klartekst i projektmappen.
6. Kør `modSapInspect.DumpScreen` på hver skærm og udfyld ID-konstanterne i
   `modConfig`.
7. Kør `modRunner.RunOne` med `DRY_RUN = True`, derefter på en batch.

## Modulerne

| Modul | Ansvar |
|---|---|
| `modConfig` | **Alt der skal tilpasses.** Felt-ID'er, arknavne, `DRY_RUN`, flow-URL |
| `modContract` | Den fælles datastruktur + validering (samme regler som appen) |
| `modLoadSheet` | Loader fra arktabellerne — primær kilde |
| `modLoadJson` | Loader fra en godkendt JSON-fil — alternativ kilde |
| `modSapSession` | Forbindelse, felt-, popup-, statuslinje- og table control-hjælpere |
| `modSapInspect` | Finder felt-ID'erne på den aktive skærm |
| `modSapTaskList` | IA01 inkl. pakkeallokering |
| `modSapMaintPlan` | IP42 / IP41 |
| `modRunner` | Batchkørsel, status, log, kvittering |

Afhængighederne går kun én vej: `modRunner → modSap* → modSapSession → modConfig`,
og `modRunner → modLoad* → modContract`. `modSapTaskList` og `modSapMaintPlan`
ved ikke, hvor data kom fra. Det er derfor kilden kan skiftes — eller hele
SAP-delen erstattes af en BAPI senere — uden at røre den anden ende.

## Hvad du skal regne med at rette

**Felt-ID'erne i `modConfig`.** De afhænger af release, skærmvariant,
brugerparametre og aktive faneblade. Værdierne i filen er pladsholdere fra en
typisk ECC-installation — gå ud fra at de er forkerte, indtil `DumpScreen` har
bekræftet dem.

**Operationsindtastningen i `modSapTaskList.EnterOperations`.** Hvor ofte der
skal trykkes Enter for at SAP tilføjer nye tomme rækker i table controlet
varierer. Det er den del, der oftest skal justeres.

**Flere positioner pr. plan.** `modSapMaintPlan` opretter én position og rejser
en tydelig fejl ved flere, frem for at oprette en plan der mangler positioner i
stilhed. Udvidelsespunktet og fremgangsmåden står i modulets sidehoved.

## Sikkerhed

`FLOW_URL` i `modConfig` peger på et HTTP-trigget Power Automate-flow.
**URL'en indeholder en signatur og er i sig selv adgangen** — alle med URL'en
kan kalde flowet. Lad flowet kun acceptere kendte `RequestGuid`-værdier og kun
skrive `Status`, `SapMaintPlanNo` og `SapCreatedOn`, og del ikke projektmappen
bredt med feltet udfyldt.

Makroen indeholder ingen SAP-credentials og skal ikke gøre det.

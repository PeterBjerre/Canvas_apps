# Excel + SAP GUI Scripting som udleveringsvej

> Denne fil erstatter anbefalingen i `04-integration-sap.md`. Vejen til SAP er
> besluttet: **Excel-makro, der kører SAP GUI Scripting.** SharePoint bliver
> liggende som backend, fordi det er der, godkendelsesflowet hører hjemme.

## 1. Kort svar på spørgsmålet

> *"Kan jeg gøre det smartere med en samlet JSON-fil, som kan vælges gennem
> Excel og oprettes med scriptet?"*

**Ja til JSON — men ikke som det, VBA læser.**

JSON er den rigtige *kontrakt*: ét frosset, versioneret dokument pr. anmodning,
der viser præcis hvad der blev godkendt. Den findes allerede
(`schema/vhplan-request.schema.json`) og skal blive.

JSON er derimod det forkerte *arbejdsformat for VBA*:

- VBA har ingen indbygget JSON-parser.
- `ScriptControl`-tricket, som de fleste eksempler på nettet bruger, findes
  **kun i 32-bit Office**. På 64-bit Office — standarden i dag — fejler det med
  "Cannot create an ActiveX component". Det er en fælde, der først viser sig,
  når makroen skal ud til den næste maskine.
- Selv med et bibliotek (VBA-JSON) ender du med at gå gennem
  `Dictionary("taskLists")(1)("operations")(3)("packages")` for at finde de tal,
  du skal bruge. GUI scripting er rækkedrevet: du looper rækker og trykker
  taster. Objektgrafer er den forkerte form til den opgave.

Så: **JSON som kontrakt og arkiv, flade tabeller som det makroen kører på.**

## 2. Lagdelingen

Det vigtigste greb er at skille *hvor data kommer fra* fra *hvad der sker i
SAP*. Så kan kilden skiftes senere uden at røre scriptet — og scriptet kan
skiftes ud (BAPI, LSMW) uden at røre kilden.

```
KILDE (vælg én)                  FÆLLES KONTRAKT I VBA        UDFØRELSE
─────────────────────────        ─────────────────────        ──────────────────
Power Query → arktabeller   ┐
JSON-fil (VBA-JSON)         ├──► Collection af           ──►  modSapTaskList  (IA01)
Manuelt udfyldt ark         ┘    Dictionary-poster            modSapMaintPlan (IP42)
                                 modContract.Validate         modRunner (batch + status)
```

Alle tre loadere producerer **den samme struktur**. `modRunner` ved ikke,
hvor data kom fra. Det er hele pointen: du kan starte med Power Query og
tilføje JSON-loaderen senere uden at ændre en linje i SAP-delen.

## 3. Datalaget: Power Query, ikke VBA

Du har tidligere skrevet VBA til at hente ud af listerne. Det kan udgå.

Power Query har en indbygget SharePoint-connector
(`SharePoint.Tables` / `SharePoint.Contents`), som:

- håndterer godkendelse med Office-loginnet — ingen hårdkodede credentials
- følger med, når der kommer kolonner til
- kan pivotere `PackagesKey` ud i én kolonne pr. pakke med to trin
- opdateres med én knap eller `ThisWorkbook.RefreshAll`

Det er 30 linjer M mod flere hundrede linjer VBA, og det er den del af
løsningen, der ellers ville gå i stykker hver gang datamodellen ændrer sig.
Queries ligger i `excel/powerquery/`.

VBA beholder kun det, VBA er god til: at trykke på knapper i SAP.

## 4. Arkene skal ligne SAP-skærmen, ikke datamodellen

Den fejl, der koster mest tid i GUI scripting, er at lægge data i arket, som
datamodellen ser ud, og så oversætte inde i makroen. Gør det modsatte: lad
Power Query levere **ét ark pr. SAP-transaktion, med kolonnerne i
skærmrækkefølge**. Så bliver makroen en simpel løkke, og fejlsøgning er at
kigge på arket ved siden af skærmen.

| Ark | Svarer til | Én række = |
|---|---|---|
| `T_Plan` | IP42 hoved | én vedligeholdsplan |
| `T_Item` | IP42 positioner | én position |
| `T_TaskList` | IA01 hoved | én arbejdsplan |
| `T_Operation` | IA01 operationsoversigt | én operation |
| `T_Package` | IA01 vedligeholdelsespakker | én operation, **én kolonne pr. pakke** |

`T_Package` er bevidst *bred*, ikke lang. Pakkeallokeringsskærmen i IA01 er et
table control med en kolonne pr. pakke og et flueben i cellen. Arket skal se
sådan ud, fordi makroen så kan mappe kolonne → kolonne direkte:

| OpNo | M1 | M3 | M6 | M12 |
|---|---|---|---|---|
| 0010 | X | X | X | X |
| 0020 |  | X | X | X |
| 0030 |  |  | X | X |
| 0040 |  |  |  | X |

Det er `PackagesKey` (`;1;3;5;`) pivoteret ud — og det er præcis derfor,
strengformatet ikke gør noget: udfoldningen sker i Power Query, ikke i VBA.

## 5. Kørselsmodellen: genstartbar, ikke atomar

En batch på 30 planer fejler på nummer 17. Det er ikke et hypotetisk scenarie,
det er normalen for GUI scripting. Designet skal tage højde for det fra start.

**Status pr. objekt, ikke pr. anmodning.** Hvis arbejdsplanen blev oprettet,
men planen fejlede, må en genkørsel ikke oprette arbejdsplanen igen:

| Kolonne | Skrives af makroen |
|---|---|
| `TL_Status` | `OK` / `FEJL` / tom |
| `TL_Group` | Gruppenummeret SAP tildelte |
| `PLAN_Status` | `OK` / `FEJL` / tom |
| `PLAN_No` | Plannummeret |
| `RunMsg` | Statuslinjens tekst ved fejl |
| `RunAt` | Tidsstempel |

Løkken springer over alt med `OK`. Genkørsel er dermed sikker og
er den normale fejlrettelse: ret arket, kør igen.

**Sporbarhed tilbage.** `RequestGuid` skrives i planens sorteringsfelt (feltet
er allerede i datamodellen). Så kan en dublet findes i SAP, og en kvittering kan
matches tilbage på anmodningen.

**Kvittering til SharePoint.** Når batchen er kørt, sender makroen resultatet
til et Power Automate-flow med HTTP-trigger, som sætter `Status`,
`SapMaintPlanNo` og `SapCreatedOn` på anmodningerne. Det er to linjer VBA
(`MSXML2.ServerXMLHTTP`) mod en hel SharePoint-REST-autentificering.

> **Bemærk:** URL'en til et HTTP-trigget flow indeholder en signatur og **er**
> adgangen — alle med URL'en kan kalde flowet. Læg den i et konfigurationsark i
> en mappe med begrænset adgang, og lad flowet kun acceptere kendte
> `RequestGuid`-værdier og kun skrive de tre felter. Del ikke projektmappen
> bredt med URL'en i.

## 6. GUI Scripting: det der faktisk vælter scripts

Disse fem punkter er årsag til langt de fleste fejl. De er alle håndteret i
modulerne i `excel/vba/`.

**1. Scripting skal være slået til to steder.** Serverside profilparameter
`sapgui/user_scripting = TRUE` (Basis-opgave, kræver genstart af instansen), og
klientside under Options → Accessibility & Scripting → Scripting. Slå også
"Notify when a script attaches to SAP GUI" og "...opens a connection" fra —
ellers kommer der en modal dialog midt i batchen, som scriptet ikke kan se.

**2. Table controls indeholder kun de *synlige* rækker.** Skal du sætte et
flueben på række 40 i pakkeallokeringen, findes den række slet ikke i
objekttræet, før du har scrollet. Mønstret er:

```
tbl.verticalScrollbar.position = absolutRække
Set tbl = session.FindById(tabelId)      ' <- SKAL hentes igen
tbl.GetCell(absolutRække - position, kolonneIndex).Selected = True
```

**3. Objektreferencer bliver ugyldige efter scroll og efter enhver
skærmændring.** Alt, hvad du har gemt i en variabel, skal hentes igen med
`FindById` efter `sendVKey`, `press` eller scroll. Det er årsag nummer ét til
"Objektet understøtter ikke denne egenskab".

**4. Uventede popups.** En låst ordre, en advarsel, et "Vil du gemme?" lander i
`wnd[1]`, og alt derefter fejler. Tjek `session.Children.Count > 1` efter hver
handling, log teksten og afbryd den ene række — ikke hele batchen.

**5. Statuslinjen er det eneste svar, du får.** Efter hvert `Gem`:
`session.FindById("wnd[0]/sbar").MessageType` giver `S`, `W`, `E` eller `A`, og
`.Text` giver beskeden. Nummeret på det oprettede objekt trækkes ud af den
tekst. Antag aldrig, at et gem lykkedes, fordi der ikke kom en exception.

## 7. Felt-ID'erne kan ikke skrives på forhånd

Skærm-ID'er i SAP afhænger af release, skærmvariant, brugerparametre og hvilke
faner der er aktive. Ingen kan skrive dem korrekt uden at sidde ved jeres system.

Derfor to ting i koden:

1. **Alle ID'er ligger som konstanter øverst i `modConfig`**, ét sted, med en
   kommentar om hvad feltet er. At tilpasse til jeres system er at rette i
   `modConfig` — ikke at gå på jagt i logikken.
2. **`modSapInspect.DumpScreen`** går objekttræet igennem på den aktive skærm
   og skriver hvert eneste ID, type, navn og indhold ud i et ark. Kør den, mens
   du står på skærmen, og læs ID'erne af. Det er hurtigere og mere pålideligt
   end script-optageren, fordi du får *alle* felter, ikke kun dem du rørte.

Fremgangsmåden er: opret én plan manuelt med optageren kørende, kør
`DumpScreen` på hver skærm undervejs, udfyld `modConfig`, kør på én række, og
først derefter på en batch.

## 8. Den ærlige fodnote

GUI scripting er skrøbeligt af natur: det kører i brugerens session, det bryder
ved skærmændringer og patches, og det kan ikke køre uovervåget. Hvis døren
senere åbner sig for en serverside-vej — en optaget BDC via SHDB, LSMW/LTMC
eller et Z-funktionsmodul — er skiftet billigt, netop fordi kontrakten
(JSON-payloaden) og datalaget (Power Query) ikke kender til SAP GUI.
Det er derfor, lagdelingen i afsnit 2 er arbejdet værd, selv når GUI scripting
er det eneste, der er til rådighed i dag.

Det ændrer ikke anbefalingen: byg det på GUI scripting nu.

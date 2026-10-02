# VH-plan Opretter

En projektmappe, der opretter godkendte VH-planer i SAP. Den læser de planer,
appen har gjort klar, og laver arbejdsplaner, positioner og selve planen i
SAP. Den gør det samme som det gamle regneark, men uden Power Query og uden
login i Excel.

Hvorfor og hvordan: [`docs/34-sap-oprettelse.md`](../../docs/34-sap-oprettelse.md).

## Første gang

**1. Synkronisér mappen.** Åbn biblioteket *SAP-oprettelse* på BIO SAP-sitet i
browseren og tryk *Synkroniser* (eller *Tilføj genvej til Mine filer*). Så
ligger planerne på din pc, og OneDrive holder dem opdateret.

**2. Slå SAP GUI Scripting til.** I SAP Logon: menuen øverst til venstre →
*Indstillinger* → *Tilgængelighed og scripting* → *Scripting*.

- Sæt flueben i *Aktivér scripting*.
- Fjern fluebenene i *Giv besked, når et script knytter sig til SAP GUI* og
  *Giv besked, når et script åbner en forbindelse*. Ellers spørger SAP hver
  gang.

Brugte du det gamle regneark, er det allerede slået til. Spørger SAP første
gang, om der må læses en fil (`SAP_PM_Longtext.itf`, langteksterne), så vælg
*Tillad* og *Husk min beslutning*.

**3. Hent projektmappen.** Den nyeste *VH-plan Opretter.xlsm* ligger øverst i
biblioteket *SAP-oprettelse*. Kopiér den til din pc, fx til *Dokumenter*, og
åbn kopien. Så arbejder I ikke i den samme fil på samme tid. Kommer der en ny
version, kopierer du den igen.

Viser Excel en **rød** bjælke om, at makroer er blokeret: luk filen, højreklik
på den → *Egenskaber* → sæt flueben i *Fjern blokering* → *OK*, og åbn den
igen. Ved en **gul** bjælke: tryk *Aktivér indhold*.

**4. Tjek, at det virker.** På arket *Start*:

- Under knapperne står mappen. Står der *ikke valgt*, så tryk *Vælg mappe…*
  og vælg den synkroniserede mappe *SAP-oprettelse*.
- Tryk *Test SAP*. Den skal sige, hvilket SAP-system du er logget på.

## Sådan opretter du planer

1. **Opdater liste.** Listen viser de planer, der venter i mappen *Til
   oprettelse*.
2. **Vis plan.** Klik på en plan og tryk *Vis plan*. Arket viser, hvad der
   kommer til at stå i SAP, og øverst eventuelle fejl og advarsler.
3. **Vælg.** Skriv `x` i kolonnen *Vælg* ud for de planer, der skal oprettes.
   Eller klik bare på én plan.
4. **Opret i SAP.** Opretteren åbner sit eget SAP-vindue og arbejder i det.
   Rør ikke SAP eller Excel, før den er færdig.
5. **Svar på spørgsmålene** (se nedenfor). Til sidst får du en opsummering.

Inden for 10 minutter bliver planen *Published* i appen med SAP-nummeret, og
den, der meldte planen ind, får en mail.

### Spørgsmålene undervejs

| Spørgsmål | Svar |
|---|---|
| *Opret … plan(er) i SAP?* | *Ja* for at gå i gang |
| *Du opretter nu i PRODUKTION* | Kun i GP1, én gang pr. kørsel. *Ja*, hvis det er meningen |
| *Skal det gemmes nu?* (før hvert gem) | Se SAP-vinduet igennem. **Ja** = gem. **Nej** = spring denne plan over. **Annuller** = stop det hele |

Det sidste spørgsmål kommer kun, mens *Bekræft hvert gem* står til *Ja* (arket
*Indstillinger*). Det gør den, indtil I stoler på opretteren.

## Hvad status betyder

| Status | Betyder | Gør |
|---|---|---|
| **Klar** | Kan oprettes | *Opret i SAP* |
| **Kan ikke oprettes** | Der mangler noget, eller noget er forkert | *Vis plan* viser hvad. Ret det i appen eller i arket *Opslag* |
| **I gang (navn)** | En kollega er ved at oprette den | Vent |
| **Delvist oprettet** | Noget er oprettet, resten mangler | Ret årsagen (står i *Besked*) og tryk *Opret i SAP* igen. Det, der er oprettet, oprettes ikke igen |
| **Fejlede** | Intet blev oprettet | Ret årsagen og prøv igen |
| **Kræver kontrol** | SAP svarede uklart efter et gem | Spørg den, der vedligeholder opretteren |
| **Erstattet** | Der er kommet en nyere udgave af planen | Ingenting. Den nyeste bruges |
| **Oprettet …** | Færdig, men ikke flyttet endnu | Flyttes til *Oprettet* ved næste kørsel |
| **Ugyldig fil** | Filen kan ikke læses | Spørg den, der vedligeholder opretteren |

Alt, der sker, står også på arket *Log*.

## Andre knapper

- **Importér fil…**: læg en ordrefil ind, fx en, der er gemt fra en mail.
- **Åbn mappen**: åbner *SAP-oprettelse* i Stifinder.
- **Selvtest** (arket *Indstillinger*): tjekker opretterens egne regler. Kør
  den, hvis noget opfører sig mærkeligt, og send resultatet videre.

---

## For den, der vedligeholder opretteren

### Byg projektmappen

Projektmappen bygges af modulerne i denne mappe og ligger ikke i git.

```powershell
.\Build-Opretter.ps1                                   # ny projektmappe
.\Build-Opretter.ps1 -From "...\VH-plan Opretter.xlsm" # nye moduler, Opslag og Indstillinger bevares
```

Kræver Excel og at *Tillid til adgang til VBA-projektobjektmodellen* er slået
til (Excel → *Filer* → *Indstillinger* → *Center for sikkerhed og
rettighedsadministration* → *Makroindstillinger*). Den kan slås fra igen
bagefter. Læg den færdige fil øverst i biblioteket *SAP-oprettelse* og sig til
teamet, at der er en ny version.

### Arket Opslag

Det SAP-specifikke, appen ikke ved noget om:

| Tabel | Indhold | Udfyld |
|---|---|---|
| Værker | Værk → SAP-værk, arbejdsplanprofil, modelydelsesspecifikation | HCV og SMV mangler |
| Kaldshorisont | Cyklus og enhed → kaldshorisont og planlægningsperiode | Som *Call_Horizon_Table* i det gamle regneark |
| Ydelser | PM03-arbejdscenter → ydelsesnummer og varegruppe | **Ydelsesnumrene mangler** — tag dem fra det gamle regneark |

Mangler en værdi, siger *Vis plan* hvilken, og planen står som *Kan ikke
oprettes*.

### Arket Indstillinger

Det vigtigste:

| Indstilling | Standard | Bemærk |
|---|---|---|
| SAP-system | `GQ1` | `GP1` i drift |
| Produktionssystemer | `GP1` | DEV- og TEST-ordrer kan ikke oprettes her, PROD-ordrer kun her |
| Bekræft hvert gem | `Ja` | Sæt til `Nej`, når I stoler på opretteren |
| Decimaltegn i SAP | `,` | Som i SAP-brugerprofilen |

### Rettelser i koden

Modulerne er ren ASCII. Dansk tekst til skærmen skrives med
`VhpUtil.Dk("V{ae}lg")`. SAP's felt-ID'er står alle i `VhpConfig.bas`: er et
felt-ID forkert, siger opretteren hvilket og på hvilken skærm, og rettelsen er
én linje dér.

Før en ny version lægges ud:

```
python3 tools/check_vba.py                  # Option Explicit, blokke, ASCII
python3 -m pytest -q tests/test_vba_runner.py tests/test_sap_contract.py
```

Testene oversætter alle moduler i LibreOffice og kører selvtestens rene del,
hvis LibreOffice findes. Det, der foregår i SAP, kan kun afprøves i SAP: se
tjeklisten i docs/34, afsnit 9.

| Modul | Gør |
|---|---|
| `VhpUi` | Arkene, knapperne og listen |
| `VhpRun` | En kørsel: kontrol, rækkefølge, statusfil, kvittering |
| `VhpSteps` | Skærmbillederne i SAP: IA05, IP04, IP05, IP01 |
| `VhpSap` | Forbindelsen til SAP og fælles greb på skærmen |
| `VhpOrder` | Indlæser og validerer en ordre |
| `VhpMap` | Oversættelsen fra appens værdier til SAP's |
| `VhpItf` | Langtekst fra HTML til SAPscript |
| `VhpLookup` | Arket *Opslag* |
| `VhpFiles` | Mapper og filer |
| `VhpConfig` | Konstanter, felt-ID'er og indstillinger |
| `VhpUtil` | Småting: JSON-opslag, datoer, dansk tekst |
| `VhpTest` | Selvtesten |
| `JsonConverter` | VBA-JSON (MIT), uændret |

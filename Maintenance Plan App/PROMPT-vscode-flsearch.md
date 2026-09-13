# Prompt til VS Code (Sonnet 5) — FL-søgning via Power Automate

Kopiér alt under linjen ind som din første besked i VS Code.

---

Du skal deploye en ændring til VH-plan canvas appen: Functional Location skal
søges via et Power Automate-flow i stedet for en lokal tabel. Koden er skrevet
og ligger i repoet — din opgave er at få flowets svar-format på plads, synke
til Studio, og verificere.

## Appen

| | |
|---|---|
| `environment_id` | `e0f8f822-d16a-e878-ba4e-fb42bc617e47` |
| `app_id` | `11fa8d90-868a-45a4-ba23-28f2cf0671a2` |
| Flow | `BioSap-Integration-FunctionalLocations` (Bioenergy Solutions DEV) |

Repo: `PeterBjerre/Canvas_apps`, branch
`claude/vh-plans-strategy-packages-lu8w70`, mappe `Maintenance Plan App/`.
Pull den først.

## Hvad der er bygget

- `txtVhpItemFL` er nu et **søgefelt**, ikke værdien. Dens `OnChange` kalder
  flowet, når teksten er **≥ 7 tegn**, og springer kaldet over hvis teksten er
  uændret siden sidst. `DelayOutput: true` samler tastetryk.
- `btnVhpFlSearch` ("Søg") kalder samme logik manuelt.
- `drpVhpItemFlPick` er hvor brugeren vælger **ét** FL. Det er den værdi, der
  gemmes på itemet — ikke søgeteksten.
- `galVhpObjList` er objektlisten: ubegrænset antal valg via checkbox,
  filtreret til FL der **starter med** det valgte, og det valgte selv er
  ekskluderet. Valgene ligger i `colVhpItemObjects` og skrives sammen til
  `ObjectList`-strengen ved gem.
- `txtVhpItemObjectList` og `btnVhpVerifyFl` findes ikke længere.

## Trin 0 — flowet skal tilføjes appen FØRST

`compile_canvas` fejler på et ukendt navn, hvis flowet ikke er en datakilde i
appen. Det kan ikke gøres fra YAML.

Bed brugeren om at gøre det i Studio: **Power Automate-panelet → Tilføj flow →
BioSap-Integration-FunctionalLocations**, og bekræfte at det hedder
`BioSapIntegrationFunctionalLocations` i Power Fx. Hedder det noget andet, så
ret `FLOW_NAME` i `build/build_flsearch.py`.

Gå ikke videre før det er på plads.

## Trin 1 — find flowets svar-format

Dette er den eneste reelle ubekendte. Fire konstanter i
`build/build_flsearch.py` beskriver svaret, og de er **gæt**:

```python
FLOW_OUTPUT      = "result"
JSON_ARRAY_PATH  = ""
JSON_CODE_FIELD  = "FunctionalLocation"
JSON_DESC_FIELD  = "Description"
```

Find de rigtige værdier sådan her:

1. Åbn flowet i Power Automate og se på **Respond to a PowerApp or flow**:
   hvad hedder outputtet? → `FLOW_OUTPUT`.
2. Kør flowet én gang (eller åbn seneste kørsel i Run history) og se på
   outputtets faktiske indhold:
   - Er svaret et JSON-**array** (`[{...},{...}]`)? → `JSON_ARRAY_PATH = ""`.
   - Er det et objekt med arrayet indeni (`{"value":[...]}`)? →
     `JSON_ARRAY_PATH = "value"`.
   - Hvad hedder felterne med FL-kode og beskrivelse i hvert element? →
     `JSON_CODE_FIELD` og `JSON_DESC_FIELD`.
3. Ret de fire konstanter, og kør:

```bash
cd "Maintenance Plan App/build"
python3 generate_app_onstart.py
python3 assemble_screen.py
python3 check_layout.py          # SKAL være grøn
```

**Hvis flowet ikke returnerer en tekst med JSON**, men fx flere separate
skalar-outputs, så stop og sig det. Så holder designet ikke, og vi skal enten
lave flowet om eller vælge en anden opbygning. Byg ikke udenom.

## Trin 2 — deploy

`canvas-authoring-connect` → `compile_canvas` → `sync_canvas` (alle med
`directoryPath` = mappen `Maintenance Plan App`) → `get_appchecker_errors` og
`get_accessibility_errors`.

Ret aldrig i YAML'en. Den er genereret af builderne under `build/`. Skal noget
laves om, så ret builderen, kør `assemble_screen.py` og `check_layout.py`, og
synk igen.

## Trin 3 — test manuelt i Studio

Ingen automatiserede browsertests. Kør denne liste i appen og rapportér hvert
punkt:

**Søgningen**

1. Åbn et item. Skriv **6 tegn** i Functional Location.
   → Intet flow-kald. Beskeden under feltet siger "Skriv mindst 7 tegn".
2. Skriv videre til **7 tegn**.
   → Flowet kaldes. Dropdownen fyldes. Beskeden viser antal fundne.
3. Klik ud af feltet og ind igen uden at ændre teksten.
   → **Intet nyt flow-kald** (gentagelsesspærren).
4. Søg på noget der ikke findes.
   → "Ingen Functional Locations fundet for …". Appen crasher ikke.
5. Åbn flowets **Run history** i Power Automate og tæl kørslerne.
   → Der skal være ca. én pr. søgning, ikke én pr. tastetryk. Er der én pr.
   tegn, virker `DelayOutput` ikke på ModernTextInput — sig til, så lægger vi
   en Timer-debounce ind i stedet.

**Valget**

6. Vælg et FL i dropdownen.
   → Linjen under viser "Valgt: <kode> - <beskrivelse>".
7. Tryk **Save** på itemet.
   → Itemet bliver `VALID`, og kortet i Items-skinnen viser det valgte FL.
8. Skift til et andet item og tilbage igen.
   → Dropdownen viser stadig itemets gemte FL.

**Objektlisten**

9. Efter FL-valget: er listen under Object List fyldt automatisk? Ellers tryk
   **Hent underliggende**.
   → Kun FL der starter med det valgte. Det valgte FL selv må **ikke** stå på
   listen.
10. Sæt flueben ved 3-4 stykker.
    → Meta-linjen tæller "X valgt af Y mulige".
11. Tryk **Save**, og se på mailkladden (Send as email) eller Export JSON.
    → De valgte FL står i `ObjectList`, adskilt af "; ".
12. Tryk **Ryd valg**.
    → Alle flueben forsvinder, tælleren går til 0.
13. **Copy item** på et item med objektliste.
    → Kopien har de samme objekter, men tomt Functional Location.
14. **Remove item**.
    → Itemets objekter forsvinder også (tjek at tælleren på et andet item er
    uændret).

**Fejlhåndtering**

15. Slå midlertidigt flowet fra (eller frakobl det), og søg.
    → "Søgningen fejlede: …". Appen crasher ikke, og dropdownen ryddes.

## Rapportér

- Hvilke værdier de fire konstanter endte med, og hvor du fandt dem.
- Resultatet af compile, sync, appchecker og accessibility.
- Punkt for punkt hvilke af de 15 test der er grønne, og hvad der fejlede.
- Antal flow-kørsler i Run history for punkt 5.

Commit og push kun til `claude/vh-plans-strategy-packages-lu8w70`. Opret ikke
en pull request.

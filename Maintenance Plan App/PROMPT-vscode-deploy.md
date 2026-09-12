# Prompt til VS Code (Sonnet 5) — deploy VH-plan appen til Power Apps Studio

Kopiér alt under linjen ind som din første besked i VS Code.

---

Du skal deploye en opdateret canvas app til Power Apps Studio via
canvas-authoring coauthoring-sessionen. Koden er skrevet og verificeret i
forvejen — din opgave er at få den ind i Studio og bekræfte, at den virker.

## Appen

| | |
|---|---|
| Miljø | Bioenergy Solutions DEV |
| `environment_id` | `e0f8f822-d16a-e878-ba4e-fb42bc617e47` |
| `app_id` | `11fa8d90-868a-45a4-ba23-28f2cf0671a2` |
| Solution | BIO SAP (`43fe3e8a-adbe-4e49-996b-42e9b7081b2d`) |

Kildekoden ligger i GitHub-repoet `PeterBjerre/Canvas_apps` på branchen
`claude/vh-plans-strategy-packages-lu8w70`, i mappen `Maintenance Plan App/`.

Klon eller pull den branch først. De tre filer, der skal synkroniseres, er:

```
Maintenance Plan App/App.pa.yaml          (458 linjer)
Maintenance Plan App/ScreenVhPlan.pa.yaml (9.660 linjer)
Maintenance Plan App/_EditorState.pa.yaml
```

## Fremgangsmåde

1. `canvas-authoring-connect` med `environment_id` og `app_id` ovenfor.
2. `canvas-authoring-compile_canvas` med `directoryPath` = den lokale sti til
   mappen `Maintenance Plan App`. **Compile før sync.** Går compile ikke rent,
   så stop og ret — se "Hvis compile fejler" nedenfor.
3. `canvas-authoring-sync_canvas` med samme `directoryPath`.
4. `canvas-authoring-get_appchecker_errors` og
   `canvas-authoring-get_accessibility_errors`. Begge skal være rene.
5. Verificér i Studio efter tjeklisten nedenfor.

Peg værktøjerne direkte på repo-mappen frem for at kopiere YAML'en til en
arbejdsmappe. Så er der kun ét sted, sandheden ligger.

## Vigtigst: YAML'en er genereret — ret aldrig i den

`ScreenVhPlan.pa.yaml` skrives af `Maintenance Plan App/build/assemble_screen.py`,
og `App.pa.yaml` af `build/generate_app_onstart.py`. Retter du direkte i
YAML'en, er ændringen væk næste gang nogen kører builderen.

Skal noget laves om:

```bash
cd "Maintenance Plan App/build"
python3 generate_app_onstart.py   # -> ../App.pa.yaml
python3 assemble_screen.py        # -> ../ScreenVhPlan.pa.yaml
python3 check_layout.py           # SKAL være grøn før du synkroniserer igen
```

Læs `Maintenance Plan App/README.md` før du ændrer noget. Den forklarer
højdemodellen og hvorfor den ser ud som den gør.

## Fire ting du ikke må gøre

1. **Lad aldrig en `Height`-formel referere en anden kontrols `.Height`**
   (fx `conVhpItemsSplit.Height = Max(conVhpItemsCard.Height, ...)`). Det var
   den oprindelige fejl: i en AutoLayout-container sætter forælderen børnenes
   størrelse, så forælderen læser sin egen udregning tilbage. Det gav enten en
   formelfejl, der faldt tilbage til `IfError`-konstanten, eller kaskade-vækst
   hvor containerne blev større for hver genberegning. Højder regnes nu i
   Python og refererer kun konstanter, `App.Width` og `CountRows()`.
2. **Prøv ikke at løse layout med `LayoutAlignItems` på en container med
   `LayoutWrap = true`.** Platformen fjerner egenskaben igen — det er
   dokumenteret i den gamle YAML, hvor netop den rettelse var forsvundet.
3. **Rør ikke stylingen.** Farver, radier, skriftstørrelser og polstring skal
   matche Materialer-appen. Alle 242 oprindelige kontroller er bevaret med
   uændrede style-egenskaber; det skal de blive ved med.
4. **Rør ikke den anden app** (`4fd2c087-78ec-46c7-be39-5809514440a8`). Den er
   kun reference.

## Tjekliste i Studio efter sync

Åbn appen og kontrollér i denne rækkefølge:

**Layout — det var det, der var i stykker**

- [ ] **Items**-kortet viser alle tre knapper (*Add item*, *Copy item*,
      *Remove item*) på én linje, ingen klippet af.
- [ ] Items-skinnen viser alle items; det sidste kort er ikke klippet i bunden.
- [ ] **Item Editor** viser alle felter hele vejen ned til *Item Long Text* og
      *Save*-knappen — ikke kun overskriften.
- [ ] **Tasklist and Operations**: dropdownen *Tasklist For Active Item* er
      synlig over knapperne. (Den var klippet helt væk før.)
- [ ] Kolonneoverskrifterne i operationstabellen flugter med felterne under dem.
- [ ] Kortene overlapper ikke hinanden, og intet vokser, når du klikker rundt.
- [ ] Træk browservinduet smalt (~800 px) og bredt igen — layoutet holder.

**Ny funktionalitet**

- [ ] Planhovedet har **Plan Type** og **Maintenance Strategy**.
- [ ] Vælg *Strategiplan (IP42)* + strategi `Z-MONTH`, tryk **Save**.
      → *Cycle* og *Unit* bliver deaktiveret, og kortet **Strategy Packages**
      dukker op mellem operationstabellen og *Dispatch and Control*.
- [ ] Matricen viser én række pr. operation og kolonnerne **M1 / M3 / M6 / M12**
      med cyklus under. Afkrydsninger kan slås til og fra.
- [ ] **Hierarki-udfyld**: markér kun M3 på en operation, tryk knappen
      → M6 og M12 bliver også markeret.
- [ ] **PAKKER**-kolonnen i operationstabellen opdaterer sig, når du krydser af.
- [ ] **Validate** viser S4 for en operation uden pakke og S5 for en pakke uden
      operationer.
- [ ] Skift tilbage til *Single cycle plan (IP41)* → Strategy Packages-kortet
      forsvinder, Cycle og Unit bliver aktive igen.

**Rettede fejl der skal blive ved med at være rettet**

- [ ] *Add lines from tasklist*: markér **kun to** linjer i pickeren og tryk
      *Add selected lines*. Der skal tilføjes **to** operationer — ikke hele
      tasklisten. (Formlen havde navnekollisionen `OperationNo = OperationNo`,
      som altid var sand.)
- [ ] Teksten *Skal udfyldes* i hero-området er ikke klippet.

## Hvis compile eller sync fejler

Tre konstruktioner i skærmen er nye i forhold til den app, der allerede kørte.
Tjek dem i den rækkefølge:

1. **`Variant: Horizontal` på et Gallery** — bruges til pakkekolonnerne
   (`galVhpPkgHead` og `galVhpPkgCells` i `conVhpStrategyCard`). Det er den
   eneste kontroltype i skærmen, der ikke fandtes i appen i forvejen. Brug
   `canvas-authoring-list_controls` og `canvas-authoring-describe_control` til
   at bekræfte det rigtige variantnavn.
2. **`LayoutOverflowX: LayoutOverflow.Scroll`** på `conVhpOpsTableWrap` og
   `conVhpPkgMatrixWrap`.
3. **`ModernCheckbox` inde i en gallery-skabelon** (`chkVhpPkgCell`).

Retter du noget: ret det i **builderne** under `build/`, kør
`assemble_screen.py` og `check_layout.py`, og synkronisér så igen. Lap aldrig
YAML'en direkte.

Er det kun den ene konstruktion i punkt 1, der driller, må du gerne erstatte
det horisontale galleri med en anden løsning — men matricen skal stadig have
**dynamisk antal kolonner**, ét pr. pakke i den valgte strategi. Et fast antal
kolonner er ikke en løsning.

## Forvent forskelle efter sync

Power Apps normaliserer egenskaber, den betragter som standardværdier, væk. Når
du eksporterer YAML'en tilbage, vil den mangle bl.a. `FillPortions` på nogle
containere, `LayoutAlignItems` på containere med `LayoutWrap = true`, og
eksplicitte `Height` på nogle blad-kontroller. **Det er normalt og ikke en
fejl.** Skriv ikke den normaliserede YAML tilbage over kildefilerne.

## Når du er færdig

Rapportér:

- Resultatet af compile, sync, appchecker og accessibility.
- Hvilke punkter på tjeklisten der er grønne, og hvilke der ikke er.
- Eventuelle ændringer du måtte lave i `build/`, og at `check_layout.py` stadig
  er grøn.
- Skærmbilleder af Items-delen, Tasklist-delen og Strategy Packages-kortet.

Commit og push kun til branchen `claude/vh-plans-strategy-packages-lu8w70`.
Opret ikke en pull request, medmindre du bliver bedt om det.

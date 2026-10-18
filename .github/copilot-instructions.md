# Canvas_apps

Svar på dansk. Al tekst i apperne er på engelsk.

## Læs dette før du retter noget

Repoet bygger Power Apps canvas-skærme, der er samlet i **én app, BIO SAP**
(`BIO SAP App/`). Det er den eneste app, der bygges til deploy og bruges.
De gamle enkeltapps er udfaset (`"single_apps": "retired"` i
`tools/canvas_apps.json`, se `docs/33-udfasning.md`). Deres mapper findes
stadig: de indeholder skærmens byggere, og BIO SAP bygges af dem.

| Skærm | Byggere | Skærm i BIO SAP |
|---|---|---|
| Masterdata Hub (landingsside for alle domæner) | `Masterdata Hub/build/` | `ScreenMdHub.pa.yaml` |
| Maintenance Plan (VH-plan, vedligeholdsplaner til SAP PM) | `Maintenance Plan App/build/` | `ScreenVhPlan.pa.yaml` |
| Equipments (udstyr) | `Equipment App/build/` | `ScreenEquipment.pa.yaml` |
| Materials (reservedele) | `Material App/build/` | `ScreenMaterial.pa.yaml` |
| Measuring Points (målepunkter) | `Measuring Point App/build/` | `ScreenMeasuringPoint.pa.yaml` |
| Functional Location (SPOOL) | `Functional Location App/build/` | `ScreenFunctionalLocation.pa.yaml` |
| KKS lookup | `KKS App/build/` | `ScreenKks.pa.yaml` |
| Issue Board (UAT-sager) | `Issue Board/build/` | `ScreenIssueBoard.pa.yaml` |

`BIO SAP App/build/` samler skærmene (`build_screens.py`, `generate_app.py`,
`check_combined.py`). App-listen, miljøer og id'er står ét sted:
`tools/canvas_apps.json`, læst af `tools/env_config.py`.

## Den ene regel: YAML'en er genereret

**Alle `.pa.yaml`-filer er genereret** af Python-builderne. Retter du direkte
i dem, er ændringen væk ved næste build, og CI afviser den
(`git diff --exit-code -- '*.pa.yaml'`).

Ret i `*/build/*.py` eller `tools/*.py`, og kør:

```bash
pip install -r requirements.txt     # første gang (Node bruges til FL-reglerne)
python3 tools/build_all.py          # alle skærme + alle tjek (det CI kører)
python3 tools/build_all.py --app biosap
python3 -m pytest -q tests          # tests og plantede fejl
```

Brug `python` i stedet for `python3` på Windows. Begge skal være grønne og
deterministiske, før noget committes eller synkroniseres til Studio. Den
genererede YAML committes sammen med byggerne.

Deploy til Studio (af brugeren):
`python tools\canvas_mcp.py deploy --app biosap`.

## Fælles moduler (`tools/`, én udgave – ingen kopier i app-mapperne)

- **Ramme og byggeklodser:**
  - `gen_screen.py`: Ctrl, render, højdealgebra; skriver `T.*`/`R.*` for størrelser og radier.
  - `build_helpers.py`: `group`, `card`, `button`, `text_input`, `number_field`, `date_picker`, `app_frame`, `top_bar`, `breadcrumb`, `request_actions`, `empty_state`, `skeleton_rows`, `validation_summary`, `sticky_actions`, `ensure_hit`/`hit_size` m.fl.
  - `side_nav.py`: sidebaren.
- **Domæneskærmene:**
  - `domain_parts.py` og `domain_app.py`: Equipments, Materials og Measuring Points deler byggeklodserne.
  - En ændring, der kun er rigtig for én af dem, hører i appens egen `build/`-mappe.
- **Tokens:**
  - `design_tokens.py`: farver som `C.'navn'` i to temaer, samt SaveData-præferencer (`prefs_save`/`pref_get`).
  - `layout_tokens.py`:
    - breakpoints og `LayoutRank`;
    - de navngivne formler `H` (højder, `H.hit`), `T` (typeskala) og `R` (radier);
    - `DATE_FMT`/`DATETIME_FMT` og `num_text`.
- **Fælles UI:**
  - `toast.py`: beskeder nederst til højre; `Notify` omskrives hertil.
  - `status_chip.py`: én statuschip.
  - `display_text.py`: `plural` og `short_text`.
  - `icons.py`, `feedback_popup.py`, `doc_upload.py`, `fl_picker.py`.
- **Data og flows:** `request_index.py` (MD_RequestIndex og Stuck-reglen), `attflows.py`, `permissions.py`.
- **Tjek:**
  - `check_layout.py`: regelregistret (`*/build/check_layout.py` er kun en indgang).
  - `check_language.py`: engelsk og sentence case.
  - `check_datasources.py`, `check_secrets.py`, `check_ps1.py`.
  - `fx.py`: Power Fx-scanneren.

## Faste regler (byggeriet stopper, hvis de brydes)

- **Ingen farver i byggerne**: hverken `RGBA(` eller `#rrggbb`, heller ikke i `tools/`. Brug tokens (`gen_screen.C_*`, `design_tokens.ref`/`ref_hex`).
- **Ingen breakpoints i byggerne**: ingen sammenligning mod `App.Width`. Brug `layout_tokens` (`below`, `at_least`, `if_below`, `fits`).
- **Ingen id'er eller play-URL'er i en builder.** De står i `tools/canvas_apps.json`.
- **Hemmeligheder**: en trigger-URL med `sig=`, en client secret eller en API-nøgle hører aldrig i git. `check_secrets.py` scanner hele repoet.
- **check_layout** (tabellen genereres af `python3 tools/check_layout.py --rules` ind i SKILL.md). De vigtigste:
  - 24: ingen aritmetik med `Parent.Width`; brug bredder af `SHELL_W`.
  - 25: knapper mindst 30 px.
  - 26c: ingen containere i gallerier.
  - 28: ingen FillPortions i en række, der ikke ombryder.
  - 29: overskrift og række har samme kolonnebredder.
  - 30: delegerbare filtre sammenligner kun mod konstanter/variabler.
  - 33: navnepræfiks efter kontroltype (`btn`, `txt`, `img`, `con`, `gal`, `inp`, `drp`, `dte`, `chk`, `tmr` …).
  - 37/38: billeder og figurer har TabIndex 0 og en AccessibleLabel.
  - 39: ingen `Notify`.
  - 40: ikonknapper og klikbare ikoner er mindst `H.hit` (32/44).
  - 41: ingen ModernNumberInput; tal er `number_field`/`num_value`.
  - 42: tekststørrelser er på typeskalaen (`lay.SIZE_*`).
- **Sprog** (`check_language`):
  - Engelsk og sentence case.
  - Teksten "New" alene på en knap er forbudt; en ny anmodning hedder præcis "New request".
  - Ingen emojis og ingen udråbstegn.
- **Designsystemet:**
  - Datoer er altid `dd-mm-yyyy` (`lay.DATE_FMT`). Tal vises med `lay.num_text`.
  - Låste felter er `DisplayMode.View`, ikke Disabled.
  - Validering vises først ved Validate/Save/Submit.
  - Statusetiketter er på engelsk; de gemte værdier er uændrede (Kladde, Indsendt …).
- **BIO SAP:** variabler og samlinger uden domænetag (fx `gbl*` delt af alle skærme) skal stå i `SHARED` i `BIO SAP App/build/check_combined.py`; hubbens `varMd*`/`colMd*` har tagget `Md` og kræver intet.

## Power Apps-begrænsninger, vi har ramt

- `SetFocus` kan ikke nå en kontrol i en container (regel 10b). "Gå til" betyder derfor: åbn rækken eller fremhæv sektionen.
- ModernNumberInput kan ikke skjule spin-pilene. ModernText har ingen Tooltip, og ModernButton har ingen TabIndex.
- Delegering til SharePoint:
  - `SortByColumns` med et variabelt kolonnenavn kan ikke delegeres; brug `Switch` med en konstant pr. gren.
  - `With({t: Filter(...)})` bryder delegeringen.
- Python skal kunne køre på 3.10: ingen backslash inde i f-string-udtryk.

## Arbejdsmetode: små pull requests

1. **Én PR pr. ændring**, så små som muligt (ét forslag eller én rettelse). Hellere fem små PR'er end én stor.
2. **Branch fra frisk `main`:**
   ```bash
   git fetch origin main
   git checkout -B <branch> origin/main     # fx ux/etape-3a-request-shell
   ```
   Byg aldrig videre på en branch, hvis PR er merget. Start forfra fra `main`.
3. **Ret i byggerne**, ikke i YAML'en. Tilføj tests i `tests/` for nye hjælpere og regler:
   - Læs den genererede YAML med `yaml.safe_load`, ikke med tekstudsnit.
   - Skal en test bruge `tools/check_layout.py`, så hent den via stien (`importlib`). Flere tests lægger en apps build-mappe forrest i `sys.path`, og den har sin egen `check_layout.py`.
4. **Kør før hver commit:**
   ```bash
   python3 tools/build_all.py
   python3 -m pytest -q tests
   ```
5. **Commit kun de filer, du bevidst har ændret.** Se `git status`:
   - Står `sharepoint/*.ps1`, `sharepoint/provision/_Common.psm1`, `sharepoint/seed/*.csv` eller `tools/*.ps1` som ændrede, er det kun linjeskift. De må aldrig committes.
   - Commit heller ikke `__pycache__/*.pyc`.
6. **Opdater status og dokumentation i samme PR:** `REVIEW.md` (statusafsnittet), og de berørte docs (`docs/26`–`30`) eller app-README'er. Tilføjer du en check_layout-regel, så regenerér regeltabellen i `.github/skills/canvas-build/SKILL.md`.
7. **Push og åbn PR'en mod `main`:**
   ```bash
   git push -u origin <branch>
   ```
   Brug `gh pr create`, GitHub Pull Requests-udvidelsen eller github.com. Merge ikke selv.
8. **PR-beskrivelsen er på dansk** og har:
   - hvad der er gjort, med ID'er (fx M1, L2 eller issue-numre);
   - hvad der er udskudt eller afviger, og hvorfor;
   - en Studio-tjekliste, der starter med `python tools\canvas_mcp.py deploy --app biosap`.
9. **Konflikter:**
   - Flere åbne PR'er rammer typisk samme tabel i `REVIEW.md`. Merge `main` ind i branchen, og behold begge linjer.
   - Genereret YAML i konflikt: tag `main`'s udgave, og byg forfra.
   - Kør build og tests igen, og push. Rewrite aldrig historikken på en delt branch.
10. **CI** (`.github/workflows/build.yml`) bygger alt, kræver at den committede YAML er det, byggerne laver, og kører testene. En merget branch slettes automatisk (`branch-cleanup.yml`).

## Mere

- Hele arbejdsgangen, ejerskabet pr. builder og de invarianter, der ikke må regressere, står i `.github/skills/canvas-build/SKILL.md`. Følg den ved enhver ændring.
- Status på kendte fund og UX-review 2026-10 står i `REVIEW.md`. Resten af UX-reviewet (M1/T3/T5 og etape 3) står i `docs/40-ux-review-copilot-prompt.md`.

# 40 – UX-review 2026-10: prompt til at færdiggøre etape 2 og 3

Prompten nedenfor holdes opdateret efter hver PR i UX-reviewet. Kopiér
alt i kodeblokken ind i GitHub Copilot (agent mode / coding agent).

Senest opdateret: efter #258. #251 og #253–#258 er åbne.

````markdown
# Opgave: Færdiggør UX-review 2026-10 for BIO SAP (etape 2 og 3)

Repo: PeterBjerre/Canvas_apps. Svar og PR-beskrivelser på dansk. Appens tekster er på engelsk.

## Status lige nu
- Merget:
  - #248 (etape 1)
  - #249 (2a, M7: pladsholder-rækker)
  - #250 (2b, M4: validation_summary)
- Åbne PR'er, som du ikke må ændre i:
  - #251 (2c, M3: hubbens fliser, Continue og sortering)
  - #253 (2d, T10: talfelter som tekst uden spin-pile — `number_field()`/`num_value()`, check_layout regel 41)
  - #254 (2e, M6: navngivne formler `T` (typeskala) og `R` (radier); `gen_screen` skriver navnet; check_layout regel 42: Size på typeskalaen)
  - #258 (2h, M8: fast bundbjælke under Desktop — `build_helpers.sticky_actions()` + `app_frame(footer=)`; Save draft/Submit som kopier, headerens skjult under Desktop)
  - #257 (2g2, M5 del 2: item-editoren viser hvilket item og har "Delete item" (`_delete_item_fx`); undertitlen er planens navn. "Documents (n)" pr. item og plan-niveau-arbejdscenter er udeladt — passer ikke til datamodellen.)
  - #256 (2g, M5 del 1: VH-planhovedet foldes til én opsummeringslinje med Show/Hide, når det er gemt — ændrer issue #192)
  - #255 (2f, M2: formularer i sektioner — `domain_parts.form_section()`/`sectioned()`; Equipments efter mockuppen, Materials og MP. FL og Issue Board får sektioner i M1-panelet.)

  Er de merget, når du starter, så byg ovenpå. Er de ikke, så start fra origin/main og forvent en lille konflikt i REVIEW.md-tabellen.
- Status står i REVIEW.md, afsnittet "UX-review 2026-10 — status", tabellen "Etape 2 — middel". Tilføj en linje i hver PR.
- Opdater også denne fil (`docs/40-ux-review-copilot-prompt.md`) i hver PR: flyt punktet fra "Rest" til "Status".

## Arbejdsform: små PR'er
- Én PR pr. punkt nedenfor. Lav branchen fra frisk origin/main: `claude/ux-etape-2d-...`, `2e`, … og `claude/ux-etape-3a-...` osv.
- Merge ikke selv.
- PR-beskrivelsen skal have:
  - proposal-ID'erne med hvad der er gjort;
  - hvad der er udskudt og hvorfor;
  - en Studio-tjekliste, der starter med `python tools\canvas_mcp.py deploy --app biosap`.
- Før hver push:
  - `python3 tools/build_all.py` skal være grøn og deterministisk.
  - `python3 -m pytest tests` skal bestå.
  - Tilføj tests for nye hjælpere og regler (se fx tests/test_ux_review_helpers.py, tests/test_ux_skeleton.py, tests/test_ux_validation_summary.py og tests/test_ux_hub_m3.py).
- Commit KUN de filer, du bevidst har ændret:
  - `sharepoint/*.ps1`, `*.csv`, `tools/*.ps1` og `sharepoint/provision/_Common.psm1` står som ændrede pga. linjeskift. De må ALDRIG committes.
  - Byggeriet sletter trackede `__pycache__/*.pyc`. Gendan dem med `git checkout -- '*.pyc'`, og commit dem ikke.

## Faste regler i repoet
- Ret i Python-byggerne (`tools/*.py`, `*/build/*.py`), aldrig i den genererede YAML (`*.pa.yaml`). YAML'en genereres af build_all og committes sammen med byggerne.
- Ingen `RGBA(` og ingen hex-farver i byggerne. Farver kommer fra tokens (`design_tokens.ref`/`ref_hex`, `gen_screen.C_*`).
- Breakpoints kun via `layout_tokens` (`below`, `at_least`, `if_below`, `LayoutRank`).
- Navnepræfikser efter kontroltype (`btn`, `txt`, `img`, `con`, `gal`, `inp`, `drp`, `num`, `dte`, `chk`, `tmr`, …). Regel 33 tjekker dem.
- check_layout-reglerne skal være grønne. Tabellen står i `.github/skills/canvas-build/SKILL.md`. Den genereres af `python3 tools/check_layout.py --rules` og skal regenereres, hvis du tilføjer en regel; behold headeren `| Regel | Hvad |`. Særligt:
  - 24: ingen aritmetik med `Parent.Width`. Brug bredder regnet af `SHELL_W`. `Parent.Width` alene må kun bruges, hvor forælderen er lodret og Stretch.
  - 25: knapper mindst 30 px høje.
  - 26c: ingen containere i gallerier. Placer kontroller med X/Y.
  - 28: ingen FillPortions i en vandret række, der ikke ombryder.
  - 29: header og række skal have samme kolonnebredder.
  - 30: delegerbare filtre sammenligner kun mod konstanter/variabler, aldrig rækkeafhængige udtryk.
  - 37/38: billeder og figurer skal have TabIndex 0 og en AccessibleLabel. Brug containere (`group`) til ren pynt.
  - 39: ingen `Notify`. Alt går via `tools/toast.py`; `Notify(...)` i byggerne omskrives automatisk.
  - 40: ikonknapper og klikbare ikoner skal være mindst `H.hit`. Brug `build_helpers.ensure_hit()` og `hit_size(n)`, og lad rækker og positioner følge med (`Self.Width`/`Self.Height`, ikke faste tal).
- `check_language`:
  - Al visningstekst på engelsk og i sentence case. Title Case-reglen har en liste over egennavne (`PROPER`).
  - Teksten "New" alene på en knap er forbudt (issue #243). Ny anmodning hedder præcis "New request".
- `BIO SAP App/build/check_combined.py`: variabler uden domænetag skal stå i `SHARED`; hubbens `varMd*` har tagget `Md` (R2-078).
- Designsystemet:
  - Segoe UI. Radier 10/12/14/16. Kontroller 36 px (`H.control` = 44 på touch).
  - Fokusring 2 px i brandfarve.
  - Datoer ALTID `dd-mm-yyyy` (`layout_tokens.DATE_FMT`/`DATETIME_FMT`). Tal med `layout_tokens.num_text`.
  - Ingen emojis og ingen udråbstegn.
  - Status-etiketter på engelsk; de gemte værdier er uændrede (Kladde, Indsendt …).
  - Validering vises kun ved Validate/Save/Submit. Låste felter er View, ikke Disabled.
  - Standardbeskeder som "Saved as EQ-000123 - see it on the landing page."
- F5 (anden mindstelængde i FL-søgningen) er bevidst. Rør den ikke.

## Faldgruber, vi har ramt (Power Apps-begrænsninger)
- `SetFocus` kan ikke nå en kontrol inde i en container (regel 10b, issue #59). "Gå til" betyder derfor åbn rækken eller fremhæv sektionen (VH: `varVhpFocusStep` og `focus_border`).
- ModernNumberInput kan ikke skjule spin-pilene; der er ingen egenskab til det.
- ModernText har ingen Tooltip. ModernButton har ingen TabIndex. Image har OnSelect, Tooltip, TabIndex og HoverFill.
- `SortByColumns` med et variabelt kolonnenavn kan ikke delegeres. Brug `Switch` med en konstant pr. gren (se `build_hub.ITEMS`).
- `With({t: Filter(...)})` bryder delegeringen. Gentag filteret i stedet.
- Brug ikke backslashes inde i f-string-udtryk (Python 3.10-kompatibilitet).

## Fælles hjælpere, der findes
I `tools/build_helpers.py`:
- `empty_state`, `breadcrumb`, `request_actions` (header: [New request ghost] | [Save draft] [Submit "N to fix"]), `with_fix_count`
- `ensure_hit`/`hit_size`, `skeleton_rows`, `validation_summary`, `sticky_actions` + `app_frame(footer=)` (efter #258), `number_field`/`num_value` (når #253 er merget; brug aldrig ModernNumberInput, regel 41)
- `group`, `card`, `button`, `text_ctrl`, `text_input`, `themed_dropdown`, `date_picker`, `segmented`, `confirm_modal`, `popup_head`

Andre steder:
- `tools/status_chip.py` (én statuschip)
- `tools/display_text.py` (`plural`, `short_text`)
- `tools/design_tokens.py` (`prefs_save`/`pref_get` til SaveData-præferencer, tokens inkl. `border-input`)
- `tools/layout_tokens.py` (navngivne formler `H.hit`/`H.control`/`H.buttonMin`/`H.badge` og, efter #254, `T.*`/`R.*`; `DATE_FMT`, `num_text`). Brug `lay.SIZE_*`/`lay.RADIUS_*` i byggerne — aldrig et tal uden for typeskalaen (regel 42).
- `tools/domain_parts.py` (Equipments/Materials/Measuring points), `Functional Location App/build/fl_parts.py`, `Maintenance Plan App/build/*.py`, `Issue Board/build/ib_parts.py`, `Masterdata Hub/build/build_hub.py`, `KKS App/build/kks_parts.py`
- Designmockups: designlærredet "BIO SAP — UX review" (Equipments-mockup og VH-plan-mockup). Følg dem så tæt, som Power Apps tillader, og skriv afvigelser i PR'en.

## Status for resten af etape 2
- **2i:** De fælles hjælpere `request_shell()`, `row_list()` og `row_editor_panel()` er implementeret og testet. Panelet viser rækkeposition, forrige/næste/luk, har separat scroll og fast footer; bredden er `Max(480, App.Width / 3)` (ca. 1/3 af skærmen) fra Desktop og fuld skærm under Desktop; et klik udenfor lukker panelet.
- **2j:** Equipment og Measuring Points åbner formularen i panelet, viser Documents med antal og har en More-menu med Copy row/Delete row. `ObjectList` og `ObjectListJson` er nu provisioneret på begge lister; builderintegration og genindlæsning af datakildeskema i Studio mangler.
- **2k:** Materials har fanerne Details/Objects/Documents med objektsøger og dokumentliste/upload indlejret i panelet.
- **2l:** FL har statuskolonne og et panel grupperet efter Master/Status/Class/TRM/Ext i to kolonner; Issue Board-detaljevisningen er et sidepanel (samme bredde) med Description/Activity/Attachments.
- **M3-rettelse:** Request-sorteringen bruger SharePoints interne `Title`; visningsnavnet `RequestNo` bruges fortsat i søgning og visning.

## Resterende etape 2
- **2j:** Objects-fanen/menuhandlingen i Equipment og Measuring Points skal kobles til de nu provisionerede `ObjectList`/`ObjectListJson`-felter. Studio skal have datakildeskemaet genindlæst efter ændringen.

## Etape 3 — én PR pr. linje
- **3a – L1:** ét `request_shell()` for alle domæner (header, breadcrumb, actions, liste, panel), så domæneskærmene kun er komposition.
- **3b – L2:** New-request-dialog, der husker plant / plan type / main work center (SaveData via `prefs_save`), plus *Duplicate* af en eksisterende anmodning.
- **3c – L3:** "Paste rows from Excel" (indsæt tab-separeret tekst, forhåndsvisning med validering pr. række, derefter Add).
- **3d – L4:** hub-visningerne "My requests" og "Queue" (det, der venter på mig som godkender/behandler).

## For hver PR
1. `git fetch origin main && git checkout -B <branch> origin/main`
2. Implementer i byggerne.
3. Kør `python3 tools/build_all.py`, `python3 -m pytest tests` og `git checkout -- '*.pyc'`.
4. Opdater REVIEW.md-tabellen (og docs/26/27/28/30 eller app-README, hvis de berøres) samt denne fil.
5. Commit kun de tilsigtede filer, og push med `git push -u origin <branch>`.
6. Åbn PR'en mod main med dansk beskrivelse: ID'er, gjort, udskudt/afvigelser og Studio-tjekliste.
````

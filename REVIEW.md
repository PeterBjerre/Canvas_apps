# Review af Canvas_apps – optimering og ensartethed

Dato: 2026-09-30 · Grundlag: branch `claude/power-app-mcp-script-0mr7uy` @ `764fbcb` · Intet i koden er ændret.

**Metode.** Syv parallelle gennemgange (Hub, VH-plan, Equipment/Material, Functional Location + BIO SAP, `tools/`, repo/SharePoint/sikkerhed, tværgående ensartethed). Alle fund er efterprøvet mod koden med fil:linje. De vigtigste er stikprøvekontrolleret en ekstra gang. Står der **(uverificeret)**, er koden efterprøvet, men den påståede virkning er ikke.

- `python3 tools/build_all.py` er kørt i en kopi. Den er grøn og **deterministisk**: 0 diff mod det committede output, også med `PYTHONHASHSEED=1` og `12345`.
- Delegeringsreglerne for SharePoint er slået op på Microsoft Learn:
  - `ID` kan kun sammenlignes med `=`.
  - `<>` er ikke delegerbart på tekst og boolean.
  - `in`, `Search`, `CountRows`, `IsBlank` og `Not` er ikke delegerbare.

Repoet har **seks** app-mapper: de fire nævnte (Masterdata Hub, Maintenance Plan App/VH-plan, Equipment App, Material App) plus **Functional Location App** og **BIO SAP App**. BIO SAP App er de fem apps samlet som skærme i én test-app. Begge er medtaget.


## Status efter fase 0, 1, 2 og 3 (2026-09-30)

Linjenumrene i fundene nedenfor henviser til udgangspunktet (`764fbcb`).

**Gennemført i repoet**
- *Fase 0:* signeret flow-URL fjernet fra VBA-kilden (D2, kildedelen); `tools/check_secrets.py` scanner hele repoet inkl. Office-filer; sessionsfiler og `.msapp` ude af git (E5, E6).
- *Byggesystem:* C1, C10 (byggetid ca. 27 → 13 s), C13, E11, D27, 100 ubrugte imports fjernet, `requirements.txt`.
- *VH-plan:* D4 (`APP_URL`), D9, D10, D11, D13, D14, D15, D16, A7 (inkl. strammere sprogtjek), A12, A14, B11; A16 for long text-popuppen.
- *Equipment/Material:* D19, D20, D21, A2, A8, A15, A17, B17; BIO SAP's regex-omdøbning fjernet.
- *Hub/FL/BIO SAP:* B2 (alle apps), B3, B9, D4 (Open ud fra domænet), D30 (blank RequestGuid), D16 (FL), D23, A6.
- *Dokumentation:* E1, E2, E3, E4, E7, E12 (`archive/` + historiske docs markeret).
- *Fase 2:*
  - Test og CI: `tests/` (pytest, plantede fejl for regel 0, 1, 8c, 16, 31 og 33) og `.github/workflows/build.yml` (byg, 0 diff i `*.pa.yaml`, pytest) (E10); C9 (N=0/1).
  - Data: dyblink `?reqid=` i Eq/Mat (D18), rækkespejl sorteret og med loftadvarsel (B4), hubtællinger fra `colMdScope` (B1).
  - Fælles moduler: `request_index.py` og `messages.py` i alle fem apps (A13, A6); `domain_app.py`, én `app_yaml`-writer med `App.OnError` (C5, D26); `cfg` som parameter og import uden sideeffekter (C2, C3).
  - App-listen ét sted i `canvas_apps.json` (C6); BIO SAP med eksplicitte kroge i stedet for monkeypatch (C4).
  - Navngivning: én dropdown, `themed_dropdown` (A1, regel 16). Efter A1 valgt ModernDropdown for de runde hjørner; felttekst i dark mode er mellemgrå `input-fg` (sort felt), så den kan læses i Fluents lyse liste; præfiks efter kontroltype og `child_name` (A3, A4, regel 33); `colFl*`/`Fl*`, `varVhpFlMsg`, `colVhpFl`, `varVhpMe`, `varMd*` (A5, A10). Tabellen står i SKILL.md.
  - Tokens: typeskala, radius, mål og `DATE_FMT` i `layout_tokens` (A9, A11, C8).
  - `sharepoint/provision/_Common.psm1` (E8) og indeks på VH-opslagskolonnerne (B14).
  - Udskudt fra fase 1: A16 for tasklist-vælgeren (vandret scroll) og D12 (SchedulingIndicator som JA/NEJ-dropdown, der gemmes; Statutory Sort Field fjernet).
- *Fase 3:*
  - VH-gem (D7, D8, B7, C15): items og operationer husker deres SharePoint-ID og **opdateres** i stedet for at blive slettet og oprettet igen, så `ItemKey` og dokumentmappen er stabile. Alt skrives, før noget slettes; `Modified`-tjek mod samtidige gem; otte trin med `IfError` og `colVhpSaveErrors`; status skrives sidst. Offsets i `Concurrent`, SortField-`Id` i den navngivne formel, og Submit vælger Save draft-knappen, så gemmet står én gang i appen. `save_action` er delt i én funktion pr. trin. Se docs/13.
  - FL (B5, B6, D24, D25): dubletter med én `GroupBy`, spool-tjek mod rækkens egne værdier, `Pos`/`FlBad`/`DescBad`/`Hint` regnet i valideringen og detaljeruden som samling. Gem sletter kun rækker, brugeren har slettet eller tømt. D25 er dokumenteret som uafklaret.
  - `check_layout` som regelregister (C7): 40 regelfunktioner i `RULES`, opdelt ud fra syntakstræet og efterprøvet byte-identisk på alle skærme og 18 plantede fejl. Opdelingen afslørede, at regel 22 aldrig så `App.OnStart` (rettet). Én Power Fx-scanner i `tools/fx.py`; regeltabellen i SKILL.md genereres af `check_layout --rules`.
  - `tools/build.py`: hele kæden i én proces, byte-identisk med `build_all.py`.

**Står tilbage**
- **Kræver handling uden for repoet:**
  - D1/D3: rotér client secret og x-apikeys, og skift miljøvariablen til Secret.
  - D2: ny trigger-signatur. `excel/artifact/BIO SAP VH-plan lister.xlsm`, som bar den gamle URL i VBA-projektet, er fjernet fra repoet (ligger stadig i historikken).
  - Omskrivning af git-historikken.
- **Kræver adgang til SharePoint:** E9 (nyt skemaudtræk).
- **Provisionering:** `_Common.psm1` er kørt med `Provision-VHPlanColumns.ps1` mod DEV (issue #83). De otte andre scripts er kun tjekket af `check_ps1` og `check_datasources`.
- **Fra E8 ikke gjort:** `-WhatIfOnly` i de scripts, der ikke har det. Deres øvrige PnP-kald (visninger, seed) respekterer det ikke, så et halvt tørløb ville skrive alligevel.
- **Ikke efterprøvet i Studio:** alle Power Fx-ændringer er bygget og layout-tjekket, men ikke compilet mod Studio. Kør `python tools\canvas_mcp.py deploy --app <nøgle>` pr. app, og efterprøv især:
  - `Ungroup` i VH-planens dyblink;
  - hubbens flade filter (delegeringsadvarsler);
  - slet-bekræftelsen i Equipment/Material;
  - ModernDropdown i alle apps (`Default` slås op fra teksten) og felttekst i `input-fg` i mørk tilstand, også i dropdownens og comboboksens lyse liste; JA/NEJ-feltet ved gem;
  - DatePicker med `Format = "yyyy-mm-dd"`;
  - tasklist-vælgeren på en smal skærm (vandret scroll);
  - VH-gem: gensave af en indlæst plan (items beholder ID og `ItemKey`), sletning af et item, Submit via bekræftelsen, og konflikttjekket med to brugere;
  - FL: galleriets nummer og røde kanter, detaljeruden efter en rettelse, og at en række, en anden har tilføjet, overlever et gem.
- **Fra fase 3 ikke gjort:**
  - FL-validering af KUN den ændrede række (B5). Dubletter, TRM og fanerne går på tværs af rækker; hele valideringen er nu O(n) i stedet for O(n²).
  - BIO SAP genbruger ikke enkeltappernes skærme (dobbeltbygningen). Det ville bryde isolationen mellem apps for ca. 3-4 s af 16.
- **BIO SAP App er den app, der bruges** (besluttet 2026-09-30, udfasningen af de fem enkeltapps slået til i repoet 2026-10-01 — `docs/33`). De fire ting, der blokerede, er løst i repoet: D23, C4, `AppUrl` i indekset (peger nu på den samlede app med `?domain=…&reqid=…`) og et FL-testscenarie i `BIO SAP App/README.md`. Tilbage står:
  - mailflowet `BioSap-EmailNotification-NewPlanCreated`, der læser `AppUrl` fra `AppSettings` (uden for repoet — se BIO SAP-README'en);
  - testplanen skal køres i Studio, før de fem enkeltapps udfases.
  
  Udfasningen er forberedt: `"single_apps": "retired"` i `tools/canvas_apps.json` bygger og deployer kun BIO SAP. Tjekliste og tilbagevejen står i `docs/33-udfasning.md`.

---

## 1. Arkitektur, som den er forstået

```
tools/canvas_apps.json ─► env_config.py          (miljø + app-id'er, --env)
tools/design_tokens.py ─► C (lys/mørk)            ┐
tools/layout_tokens.py ─► LayoutContext/Rank      ├─► App.Formulas i alle apps
tools/gen_screen.py     DSL, højde-algebra, render (sorteret, deterministisk)
tools/build_helpers.py  card/field_cell/inputs/app_frame/top_bar/flow_row/...
tools/side_nav.py, icons.py, fl_picker.py, build_flsearch.py, attflows.py
tools/domain_parts.py   Equipment+Material: formular, liste, gem/slet/indsend

<App>/build/*_config.py  kontrakt mod SharePoint (lister, kolonner)
<App>/build/generate_*   ─► <App>/App.pa.yaml     (Formulas + OnStart)
<App>/build/assemble_*   ─► <App>/Screen*.pa.yaml (én skærm pr. app)
<App>/build/check_layout.py  (shim → tools/check_layout.py)

tools/build_all.py: check_ps1 → scrub_solution → farvevagt → FL-harness (node)
                    → pr. app: generate → assemble → check_layout
                    → check_rules_doc → check_datasources → check_language → check_helptext
tools/canvas_mcp.py deploy: build → compile → sync → deploy_verify (på kopi i .canvas-deploy/)
```

| App | Builder-linjer | Genereret YAML | Kontroller | Data |
|---|---|---|---|---|
| Masterdata Hub | 1.059 | 4.115 | 102 | Kun `MD_RequestIndex`, bundet direkte i galleriet |
| VH-plan | 5.211 | 16.432 | 381 | 18 navngivne formler over opslagslister. Gemmer i `MaintenancePlans`/`MaintenanceItems`/`TaskListMain`/`MD_Tasklist*` og `MD_RequestIndex`. Dyblink `?reqid=` hentes i OnStart |
| Equipment / Material | 496 / 544 (+1.541 i `domain_parts.py`) | ~11.200 hver | 274 hver | `EquipmentItems`/`MaterialItems` hentes i OnVisible til `colDomRows` |
| Functional Location | 1.904 | 7.598 | 119 | `FunctionalLocationRequests`/`Items`. 541 regeltjek kompileret fra `html/*.js` til `nfFl*`-formler (231 KB) |
| BIO SAP App | 914 | 50.058 | 1.154 | Genbruger de fem appers byggere via monkeypatch. Kun til test |

Andre dele af repoet:

- **Fælles:** `tools/` indeholder 28 filer og 12.116 linjer.
- **Levende:** `sharepoint/provision` (10 PnP-scripts), `sharepoint/inspect/out/schema.json` (bruges af `check_datasources`), `docs/21, 26–31`.
- **Arkiv/historik:** `powerfx/`, `schema/`, `excel/powerquery`, `excel/vba`, docs 01–05 og 08–13, `Provision-VHPlanLists.ps1`.
- **Solution-eksport:** `solution/` er et læsestof-øjebliksbillede.

Farve- og layoutdisciplinen er høj. Uden for tokens findes kun `RGBA(0,0,0,0)` i skærmene, og breakpoints ligger kun i `layout_tokens`.

---

## 2. Fund

Kolonner: **ID** · **Alv.** (H/M/L) · **Placering** · **Problem** · **Forslag** · **Ind.** (indsats S/M/L) · **Flere** (påvirker flere apps).

### A. Ensartethed

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| A1 | H | `tools/build_helpers.py:1164` (`dropdown`→ModernDropdown) mod `:1187` (`themed_dropdown`→Classic). Bruges i `build_plan_header.py:161-189`, `build_items.py:444`, `build_tasklist.py:565,785`, `fl_parts.py:552` | Der er to dropdown-typer. Ifølge `themed_dropdown`'s egen docstring er ModernDropdowns liste ulæselig i mørk tilstand. Eq/Mat bruger Classic (6), men VH-plan (11) og FL (1) bruger Modern. `Default` har forskellig semantik: record over for tekst. | Gør `themed_dropdown` til eneste dropdown, og markér `dropdown()` som udfaset. (Visning i Studio er uverificeret.) | M | VH, FL |
| A2 | M | `tools/domain_parts.py:177` (`"inp" + col`), `:1055` (`f"con{c}"`) | 39 af 274 kontroller pr. app i Eq/Mat mangler `Dom`-infixet, fx `inpManufacturer`/`conManufacturer`. BIO SAP skal derfor omdøbe dem med regex (`BIO SAP App/build/build_screens.py:295-311`). | `inpDom{col}`/`conDom{c}`. Fjern derefter omdøbningen i BIO SAP. | S | Eq, Mat, BIO |
| A3 | M | `tools/build_helpers.py:1446,1451,1454,1489`, `build_plan_header.py:61,111`, `gen_screen.py:496,531` | 110 ModernText-/Gallery-/Rectangle-kontroller har præfikset `con`, fordi `Lbl`/`Star`/`Hint`/`Title`/`Gal`/baggrund hægtes på cellens `con…`-navn (VH 76, Eq 19, Mat 20, Hub 1). | Afled navnet af en base uden præfiks: `txt{base}Lbl`, `gal{base}Help`, `rct{base}Bg`. | M | Alle |
| A4 | M | `domain_parts.py:177,1414`, VH-builderne (`txtVhp…`), `build_hub.py` (`txtMdSearch`) | Tekstinput hedder `inp` 28 gange og `txt` 17 gange, men `txt` er også præfikset for ModernText. Number- og DatePicker-felter hedder `inp` i Eq/Mat, men `num` i VH. | `inp` = tekstinput, `num` = tal, `dte` = dato (se §3). | M | Alle |
| A5 | L | VH `sp_config.py`/`build_status.py` (`colVhp*` + `Vhp*`), FL `generate_app_onstart.py:81-117` (`nfFl*`) | Navngivne formler følger tre konventioner. `check_layout` regel 8 ("col* findes") dækker ikke `nfFl*`. | Tabelformel `col<X>*`, skalar `<X>Pascal`. Omdøb FL's 13 formler. | M | FL |
| A6 | M | `tools/domain_parts.py:509,565,957`, `fl_save.py:230,303-305`, `build_save.py:569` | Samme hændelse har forskellig tekst: "Save failed:" / "It failed:" / "Submit failed:". "Submitted as X." (FL), "… - see it on the landing page." (Eq/Mat) og "MP… submitted." (VH). FL's Submit viser desuden **to** Notify, fordi `save_fx` er inlinet (`fl_save.py:230,288,303`). | Lav et modul `tools/messages.py` med `msg_saved/submitted/failed`, og giv `save_fx(notify=False)`. | S | Alle 4 |
| A7 | M | `build_save.py:309`; `tools/check_language.py:55-82,127-134` | Den danske tekst "Gemning afbrudt - kontakt SAP masterdata." står i to Notify-kald og slipper igennem sprogtjekket, fordi enkeltordsreglen kræver højst 3 ord. Strenge efter `Value:` springes helt over. | Oversæt teksten. Lad enkeltord tælle uanset strengens længde, og udvid ordlisten. | S | VH |
| A8 | M | `domain_parts.py:1202-1213,1514`, `equipment_parts.py:63`, `material_parts.py:140` | "Save draft" gemmer hele anmodningen i VH/FL, men kun én række i Eq/Mat, hvor anmodningen gemmes med "Save as draft". Samme knap hedder "Save"/"New row" (Eq) og "Save row"/"Reset form" (Mat). | Reservér "Save draft" til anmodningen, og giv Eq og Mat samme knaptekster. | S | Eq, Mat |
| A9 | M | `build_plan_header.py:245`, `domain_parts.py:1311`, `build_helpers.py:1129,1147`, `domain_parts.py:804` | Datoer vises som `dd-mm-yyyy hh:mm` (VH), `yyyy-mm-dd` (Eq-listen) og i lokalformat (Eq/Mat-detaljer). DatePicker bruger `DatePickerFormat.Short` med placeholder `"dd/mm/yyyy"`. VH's First Call er tre talfelter. Priser har intet format. | Indfør én `DATE_FMT = "yyyy-mm-dd"` og én `num_text`. Afled placeholderen af formatet. | S | Alle |
| A10 | L | `build_items.py:377-380`, `generate_hub_onstart.py:34-38`, FL `varFlStale` | Samme betydning har forskellige navne: `varVhpFlMeta`/`varDomFlMsg`, `colVhpFlSearch`/`colDomFl`. VH har ingen `…Me` (5× inline `Lower(User().Email)`). Hubben bruger `gbl*` til skærmtilstand. FL har `varFlStale` med omvendt logik af `…Validated`. | Ret de billige: `varVhpFlMsg`, `colVhpFl`, `varVhpMe`, `varMd*`. Skriv tabel §3 ind i SKILL.md. | S | Alle |
| A11 | L | `build_plan_header.py:61` (19), `fl_parts.py:297` (16), `domain_parts.py:157,761,1410` (15/16/17), `build_hub.py:630` (10), `:331,589` (radius 12) | Der er ingen typografiske tokens. Korttitler har størrelse 16, 17 eller 19. Størrelse 10 og popup-radius 12 findes kun i hubben. | `SIZE_CARD_TITLE=17`, `SIZE_MICRO=11`, `RADIUS_MODAL=16` (se C8). | S | Alle |
| A12 | L | `build_save.py:295,312,555,568` | VH sætter `varVhpSaving` manuelt (2× true, 6× false). Eq/Mat/FL bruger `with_busy`. Ingen app har busy under upload af dokumenter. | Brug `with_busy` i VH og i `attflows`-upload. | S | VH (+alle for upload) |
| A13 | M | `domain_parts.py:841-920`, `fl_save.py:120-150`, `build_save.py:270-331`; domænestrenge i `domain_config.py:43/41`, `fl_config.py:34`, `Provision-RequestIndex.ps1:104-106` | Indeksrækken i `MD_RequestIndex` skrives tre steder med kopierede literaler ("Kladde"/"Indsendt", `StatusStep`, `IsOpen`) og tre fejlmodeller. Felterne er uens: EQ/MAT mangler `SourceItemId`, FL's submit opdaterer ikke `LastActionBy`, og FL's `Plant` er et KKS-præfiks (`Left(FL,3)`). FL nummererer efter egen liste, domænerne efter indeksets ID. Intet tjekker, at teksterne matcher `hub_config.STATUS`. | Lav `tools/request_index.py` med domænenøgler, STATUS flyttet fra `hub_config`, `index_record()` og `number_fx()`. Lad `check_datasources` sammenholde det med ps1-valgene. | M | Alle 5 |
| A14 | L | `build_tasklist.py:765,343,338,732…`, `build_plan_header.py:194-198`, `build_strategy.py:76,313` | Accessible labels står på dansk i en engelsk UI ("Materialenummer", "Foerste kald, dag"). `txtVhpOpMwc` har label "Plant", men viser Main Work Center. | Skriv labels på engelsk, og ret "Plant". | S | VH |
| A15 | L | `material_parts.py:170,173`, `equipment_parts.py:114`, `domain_parts.py:1381,1418` | Kolonneoverskrifter afviger fra formularens labels ("DELIVERING TIME"/"Delivery time (days)"). Eq har "VALIDATION", Mat har "STATUS". Statusværdierne vises råt (`draft`/`valid`). | Brug formularens label som overskrift og en `Switch` til visningstekst. | S | Eq, Mat |
| A16 | L | `build_modal.py:224,294` | Popups har fast bredde (740/620) og går ud over skærmen på mobil. De øvrige popups bruger `Min(620, App.Width - 40)`. | Brug samme `Min(...)`-mønster. | S | VH |
| A17 | L | `domain_parts.py` (ingen `Tooltip`) | Eq/Mat har 0 tooltips på 27/28 knapper (VH 4, FL 4, Hub 2). | Tooltip på ikonknapper og de tvetydige gem-knapper. | S | Eq, Mat |

### B. Power Fx-ydeevne

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| B1 | H | `Masterdata Hub/build/build_hub.py:432,486` (YAML 471…1149) | Flisetal og total er seks `CountRows(Filter(SCOPE…))` direkte mod SharePoint. De er ikke delegerbare og stopper ved 500/2000, især i "whole department + All". docs/07 §7 regel 6 forbyder netop dette. | Tæl i én `ClearCollect(colMdScope, SCOPE)` ved skift af view/status og vis "2000+" ved loftet, eller tæl på `galMdRequests.AllItems` før domænefiltret. | M | Hub, BIO |
| B2 | M | `tools/build_helpers.py:86` (`"AccessibleLabel": accessible if accessible else text`) | Tekstformlen kopieres til `AccessibleLabel` og beregnes derfor to gange, også hubbens `CountRows` og `Switch`/`DateDiff` pr. galleri-række. (At Power Apps ikke cacher er uverificeret.) | Udelad `AccessibleLabel` på ModernText, når der ikke er angivet et separat label. | S | Alle |
| B3 | M | `build_hub.py:162-176,599-611` | Galleriets kilde er `SortByColumns(Filter(If(gblView=…, If(…Filter…)…)))`. Om det ydre Filter/Sort delegeres gennem `If`, er **uverificeret** (README beder selv om at få det tjekket i Studio). | Ét fladt `Filter('MD_RequestIndex', gblView<>"mine" \|\| RequesterEmail=gblMe, …)`. Det fjerner også seks YAML-kopier af SCOPE. | S | Hub, BIO |
| B4 | M | `tools/domain_parts.py:318-349` (indsat 8× pr. skærm) | Rækkespejlet `ClearCollect(colDomRows, ForAll(Filter(L, RequesterEmail=varDomMe)…))` har intet statusfilter og ingen sortering. Det vokser for evigt og loftes af data row limit (tavst manglende rækker i liste, tælling og Submit). Hvert gem henter hele listen. | Filtrér `RowStatus.Value = "draft" \|\| = "valid"` (lighed er delegerbar), `Sort(ID, Descending)`, og vis en advarsel ved loftet. Efter gem: `Patch(colDomRows, …)` af den ene række. | M | Eq, Mat, BIO |
| B5 | M | `fl_parts.py:64` (REVERIFY), `fl_validation.py:147,203-211,250-292,325-348` | Hver feltændring genberegner hele FL-tabellen. Dublettjekket er O(n²), spool-tjek er O(n²·k) (`LookUp(colFlVals…)` pr. række × tjek), og `ClearCollect(colFlRows…)` udskifter galleriets kilde. (Mærkbar ydelse ved 100+ rækker er uverificeret.) | Revalidér kun den ændrede række og dens FL-dubletter. Beregn dubletter én gang med `GroupBy`. Patch ændrede felter i stedet for ClearCollect. | M | FL |
| B6 | L | `fl_parts.py:307,312,316,436,440,491-505,572-592` | Beregning pr. galleri-række: `RowNo` via `CountRows(Filter(RowNo<=…))` (O(n²)), 8× `exactin`-filtre pr. række, `hint_fx` 4× pr. række og `DET_ITEMS`' `ForAll` 4×. | Læg `Pos`/`FlBad`/`DescBad`/`Hint` som kolonner i STATUS-trinnet. Beregn detaljerne ved åbning. | S | FL |
| B7 | M | `build_save.py:299-301,183,603,612` | VH-gem er ca. 20 sekventielle kald. De tre offset-opslag er ikke parallelle, `LookUp(SortFieldList…)` går direkte mod listen, og hele `save_action` (415 linjer) indsættes **to gange** i YAML. | `Concurrent` for offsets, bær `Id` i `colVhpSortFieldOptions`, og lad Submit kalde én gem-knap via `Select`. | M | VH |
| B8 | L | `domain_parts.py:84,752-757,1247-1256`; `build_hero.py:59-71` | Gentagne udtryk: `LookUp(colDomRows, RowId=varDomDetailsId)` står 64–69 gange pr. skærm, `Trim(txtDomSearch.Text)` 80 gange, `ITEM_DIRTY` 23 gange i VH. Kører lokalt, men giver mange genberegninger og stor YAML. | Detaljepopup som galleri med ét element (`ThisItem`). Scope og position som navngivne formler (om de må læse kontroller er uverificeret). | M | Eq, Mat, VH |
| B9 | L | `build_hub.py:490,509-515,576` | Tooltip på "Closed" evaluerer `CLOSED_LATEST` (en forespørgsel) ved hver visning, og `galMdPeek` laver den samme. | Brug statisk tooltip, eller læs `galMdPeek.AllItems`. | S | Hub |
| B10 | L | `build_hub.py:638-642,669-674,691` | SVG-ikoner strengsammensættes og `EncodeUrl`'es pr. række (33×), selvom der kun er 14 forskellige. | Navngiven formel `MdIcons` i `App.Formulas`. | M | Hub (+side_nav) |
| B11 | L | `sp_config.py:143,205,218` | Døde navngivne formler: `colVhpYesNoOptions`, `colVhpPriorityOptions`, `colVhpCtrlOptions` (`Distinct` over listen) har 0 referencer. | Slet dem, eller brug YesNo i D8. | S | VH |
| B12 | L | `sp_config.py:166-331` | Opslagsformler over 10 hele lister har intet loft og ingen advarsel. Største i dag er 176 rækker. | Vis advarsel i `txtVhpPlanOptionsState`, når `CountRows` når grænsen. | S | VH |
| B13 | L | `fl_save.py:158-161,175,187,320-332` | FL henter samme `Filter(L, RequestGuid=…)` tre gange pr. gem, og den materialiseres (loft 500/2000). Over loftet oprettes eksisterende rækker som dubletter. | Hent én gang til `colFlSp` og genbrug den. Sæt et rækkeloft i appen. | S | FL |
| B14 | L | `schema.json` / `Provision-VHPlanColumns.ps1` | `MaintenanceItems.MaintenancePlanNo` og `TaskListMain.MaintenancePlanID` filtreres (7×), men er ikke indekseret. (Betydning over 5.000 rækker er uverificeret.) | Indeksér dem i provisioneringen. | S | VH, BIO |

### C. Python-builders

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| C1 | M | `tools/gen_screen.py:71-72`, `tools/check_layout.py:68` | `ROOT = dirname(dirname(HERE))` er en rest fra `build/`. Den peger på mappen **over** repoet, og `<forælder>/tools` indsættes først på `sys.path`. Verificeret: en fremmed `layout_tokens.py` dér blev importeret i stedet for repoets. | Brug `HERE`, eller fjern linjerne. | S | Alle |
| C2 | M | 52× `sys.path.insert` i 41 filer; `domain_parts.py:38-46,68,78,996,1246-1263`; `attflows.py:262` | `domain_parts` importerer appens `domain_config` på modulniveau via `sys.path`, og `FIELDS`/`SEARCH`/`CELL_W` fryses ved første import. Det virker kun, fordi hver app bygges i sin egen subprocess. Et script, der importerer begge, bygger tavst forkert. | Lad `domain_parts` tage `cfg` som parameter (`DomainParts(cfg)`). Gør `tools/` til en pakke, eller brug én `_bootstrap.py`. | M | Eq, Mat, BIO |
| C3 | M | `gen_screen.py:35-62,729-733`, `env_config.py:63,100`, `design_tokens.py:278,449,504,551` | Sideeffekter ved import: `OUT_DIR` fra `sys.argv[0]` og `ENV = resolve()` giver `SystemExit` ved import uden for en build-indgang (REPL/test). | Doven `out_dir()`, og undtagelser i biblioteker. `SystemExit` kun i `main()`. | S/M | Alle |
| C4 | M | `side_nav.py:116`, `BIO SAP App/build/build_screens.py:66-83,228-229,277-311`, `combined.py:113-123,156-179`, `generate_app.py:30-45` | BIO SAP bygger på monkeypatch af modulglobaler og `render_screen`, fjerner tekstblokke ordret og regex-omdøber `Dom`. Den kører de fem generatorer igen med `stdout=DEVNULL` og skriver dermed i de andre apps' output, også ved `--app biosap`. Byggeriet stopper højlydt ved afvigelse (godt), men hver OnStart-ændring kræver en ændring her. | Eksplicitte parametre: `side_nav(screens=…)`, `build_screen(render=…)`. Generatorer eksporterer `formulas()`/`onstart_parts()` som data. Fjern `regenerate_sources`. | M | Alle |
| C5 | M | Eq/Mat `generate_app_onstart.py` (145 l., 1 funktionel forskel: `EMPTY` l.34), `assemble_screen.py` (79 l., 8 forskellige linjer); 5 byte-identiske `check_layout.py`-shims; 5 forskellige `App.pa.yaml`-writers | Næsten ordrette kopier. `generate_hub_onstart.py:53-62` kører ved import uden `main()`. | Brug `tools/domain_app.py` (`build_app_yaml(cfg)`, `build_screen(cfg, parts)`) og én fælles App-writer. Se §4 fase 3. | M | Alle |
| C6 | M | `build_all.py:42-53,173-176`, `check_datasources.py:439-441`, `canvas_apps.json`, `side_nav.py:106-112`, `build_screens.py:33`, `icons.py:61-68` | App-listen står 7 steder, og `env_config.folder()` bruges ikke. En ny app kræver 6–7 rettelser. | Udvid `canvas_apps.json` med `scripts`, `screen`, `prefix`, `nav_order`, `icon`, og udled resten. | M | Alle |
| C7 | M | `check_layout.py:327-2058` | `main()` er én funktion på 1.732 linjer. Reglerne står i rækkefølgen 0,1,2/3,4c,4d,24,25,26,… med huller, og docstringen (l.2-56) nævner kun VH og mangler ~20 regler. Syv håndskrevne Power Fx-scannere håndterer strenge forskelligt (l.121,1184,1472,1507,1660,1771,1933,1960). | Regelregister (`RULES = {"4c": fn}`) i moduler, én fælles tokenizer i `tools/fx.py`, og docs/SKILL genereret fra registret. | L | Alle |
| C8 | M | `build_helpers.py:203,1085,1113,1151,1177,1578`, `fl_picker.py:159`, `check_layout.py:720,916` | Magic numbers: 138 rå `Size`, 56 radius, 256 højder og 161 gap/pad. Radius `"10"` gentages i 5 input-byggere, `"Size":"14"` er død (overskrives af `input_theme` l.948), og `check_layout` hardkoder 30 og 1,5 i stedet for at importere `TEXT_LINE`. | `type_scale`, `RADIUS_INPUT=10`, `RADIUS_CARD=14`, `CONTROL_H=36`, `BUTTON_MIN_H=30`, `CARD_PAD=18` i `layout_tokens`, og en fælles `_input_base()`. | M | Alle |
| C9 | M | `check_layout.py:106-108,208` | `evaluate` bruger `max(items, ops, pkgs)`, og `PKG_COUNTS=[3,4]`, så N er aldrig 0 eller 1. Tomme lister (fx `txtDomNoRows.Visible`) efterregnes aldrig, selv om SKILL.md:444 påstår "0–8 items". | Brug et tal pr. samling, eller test N ∈ {0,1,3,8,12}. | M | Alle |
| C10 | M | `check_layout.py:208`, løkker l.374-430 | `evaluate` kaldes 37× for meget: 125.227 kald mod 3.401 unikke for VH. `check_layout` står for 75 % af byggetiden (23 af 31 s). | Memoisér på `(expr, w, N)`. Afprøvet: VH går fra 4,5 til 1,1 s med samme resultat. | S | Alle |
| C11 | L | `build_helpers.py:1245,1309,1554,117,752`; `build_all.py:16,66`; `gen_screen.py:302`; `layout_tokens.py:260`; `env_config.py:120`; `canvas_mcp.py:48`; `check_datasources.py:143`; `hub_config.py:48,82,124-130`; `fl_config.py:43,50`; `domain_parts.py:342-345` | Død kode og døde parametre (~110 linjer), fx `combobox`, `poll_timer`, `two_col_row`, `switch_on_status`, `L_KEYS`, `HUB_URL`, `… if False else`. pyflakes melder 99 ubrugte imports, heraf 14/13/12 i VH's `build_save`/`build_items`/`build_strategy`. | Slet, og kør pyflakes/ruff i `build_all`. | S | Alle |
| C12 | L | `build_helpers.py:60` (`HINTS_ON = "IfError(varVhpShowHints…)"`), `gen_screen.py:145-154` (`RAIL_W`/`EDITOR_W`), `check_layout.py:229-232,1153` | VH-specifikt indhold ligger i fælles moduler. Et `hint_text` i andre apps ville læse VH's variabel. | Parametrisér (`hints_var=`), og flyt VH-konstanter til VH's `build/`. | S | Alle |
| C13 | L | `build_flsearch.py:83,86,94,120` | `raw_var=DEFAULT_RAW="varDomFlRaw"` er stadig default, selvom kommentaren l.71-82 beskriver netop den fejl. | Gør `raw_var` obligatorisk. | S | VH, Eq, Mat |
| C14 | L | `fl_parts.py:105-107,284,605`, `fl_save.py:35-38`, `fl_validation.py:28,33` | `LIVE` er defineret to gange med **forskellig** betydning, og `ERRS`/`READY`/`_q` er kopieret. | Saml i `fl_state.py`, og navngiv de to LIVE forskelligt. | S | FL |
| C15 | L | Alle `tools/*.py` undtagen `check_vba.py`; VH 67 funktioner | Stil: 0 % typehints, docstrings 0–100 %, `%` og f-strings blandet, `open().read()` uden `with`, `except Exception` → `None` (`check_layout.py:282`), `assert` som vagt (`layout_tokens.py:243`). Længste funktioner: `save_action` 415, `build_tasklist_section` 378, `build_strategy_body` 306, `build_item_editor` 290 linjer. | Fælles ruff/black-config og typehints på offentlige API'er (gen_screen, build_helpers, layout_tokens). Del `save_action` op pr. trin. `check_vba.py` er forbilledet. | M | Alle |
| C16 | L | `fl_parts.py:199-200,572,583,666`; `build_hub.py:210,335,592`; `domain_parts.py:711,1191` | Uforklarede tal: `SHELL_W - 36 - 4`, `HEADER_PAD_T + 52 + 6` (2×), `App.Height - 220`, `meta_w = 130+8+290`, håndafprøvede `ROW_BTN`-bredder. | Navngivne konstanter, og `fit_button_width()` til knapbredder. | S | Alle |

### D. Korrekthed, robusthed, sikkerhed og tilgængelighed

**Sikkerhed**

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| D1 | **H** | commit `ad4128d` (3 filer under `solution/…/orsted_BioSapWOCClientSecret/` og `Workflows/BioSap-Integration-FunctionalLocations-*.json`, `…Order-Objects-*.json`); fjernet i `05130a3`/`09c58fa` | En client secret og to `x-apikey`-værdier ligger stadig i **git-historikken** (17 af 18 grene). HEAD er ren. Commit `09c58fa` siger selv, at secret'en skal roteres, men repoet viser ikke, at det er sket. | Bekræft rotation i Entra ID og hos API-udbyderen. Omskriv derefter historikken (filter-repo/BFG) på alle grene. | M | FL-søgning (VH, Eq, Mat) |
| D2 | **H** | `excel/src/Modules/Constants.bas:103` | Power Automate-trigger-URL med `sig=`-signatur står i HEAD. Alle med URL'en kan starte flowet. `scrub_solution` scanner kun `solution/`. (Om den også ligger i `.xlsm` er uverificeret.) | Regenerér triggerens signatur, læs URL'en fra config uden for git, og kør scrub-mønstre over hele repoet i `build_all`. | S | Excel-værktøj |
| D3 | M | `solution/…/orsted_BioSapWOCClientSecret/environmentvariabledefinition.xml:9-10` | Miljøvariablen er `type 100000000` (String) og `secretstore 0`. Det er derfor, secret'en endte i eksporten. | Brug en miljøvariabel af typen Secret (Key Vault), også til `x-apikey`. | M | Flows |
| D4 | M | `build_hub.py:614-625`; `domain_parts.py:908`; `fl_save.py:102`; `build_save.py:76-77,284` | `AppUrl`-kontrakten er inkonsistent. Eq/Mat/FL skriver `?reqid=` ind i URL'en, og hubben tilføjer `&reqid=` igen (dobbelt parameter). VH hardkoder DEV-URL'en (`--env prod` skriver stadig DEV). Hubben launcher en URL fra en række, som enhver med Contribute kan redigere. | Byg Open ud fra `Domain` + `env_config` (som BIO SAP gør). Brug AppUrl højst som fallback. `APP_URL = env.play_url("vhplan")`. | M | Alle |
| D5 | L | `sharepoint/inspect/out/sample-*.json`, `seed/MD_Approver.csv`, `solution/` flows | Persondata: 12 navne og 12 @orsted.com-adresser i samples, initialer på godkendere i seed, 11 adresser i flows. | Pseudonymisér i `Export-ListSchema.ps1`, og flyt godkendernoter ud af seed. | S | – |
| D6 | L | `tools/unpack_msapp.py:424` | Zip-stier normaliseres ikke (`..` passerer). Lav risiko, da kilden er egne eksporter. | Afvis `..`, og brug `commonpath`. | S | – |

**Korrekthed – VH-plan**

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| D7 | **H** | `build_attflows.py:21`, `build_save.py:359-411`, `tools/attflows.py:108` | Dokumentmappen er opkaldt efter `ItemKey`. Items slettes og genskabes ved hvert gem og får nyt ID og ny nøgle, så dokumenterne ligger derefter i en mappe, intet peger på. Næste gem sletter deres rækker i `MD_TasklistAttachment`. | Giv items en stabil identitet: opdatér eksisterende rækker i stedet for delete+recreate, eller brug `ItemGuid` (findes, `Provision-VHPlanApproval.ps1:214`) som mappenavn. | M | VH |
| D8 | **H** | `build_save.py:296-571` (Remove l.359-366 før Patch) | VH-gem sletter først og skriver bagefter, uden transaktion. Fejl midtvejs efterlader planen uden items og operationer, og `MD_RequestIndex` bliver ikke opdateret. Samtidig redigering af to brugere giver dubletter, og der er intet `Modified`-tjek. (Om `IfError` fanger fejl midt i en `;`-kæde er uverificeret.) | Skriv nyt først og slet de gamle ID'er bagefter (fejl giver så dubletter, ikke tab). Tjek `Modified` og brug `IfError` pr. trin, som FL gør. | M/L | VH |
| D9 | **H** | `build_load.py:91-92`, `build_status.py:56-62,143-146,169-171` | Efter dyblink er `TasklistKey = ""`. Den indgår i S3 og trin 3, så en genåbnet kladde kan ikke indsendes, før alle items får valgt tasklist igen. Docstringen (l.35-39) påstår, at feltet kun bruges til visning. | Gem `TasklistKey` i `MaintenanceItems`, eller afled den ved load (`Plant & "-STD"`). | S | VH |
| D10 | **H** | `build_load.py:206-281`, `build_items.py:579` | `colVhpItemObjects` fyldes ikke ved load. "Save item" skriver derfor `ObjectList = ""` og sletter objektlisten i SharePoint ved næste gem. | Split `IT.ObjectList` ind i samlingen i `load_block` (samme udtryk som `btnVhpResetItem`). | S | VH |
| D11 | M | `build_load.py:59`, `build_save.py:204` | Planens status indlæses som `""`, og gem skriver `Coalesce(…,"New")`. Items med Change/Deleted bliver dermed til New efter dyblink. | Læs `Status` tilbage fra første item. | S | VH |
| D12 | M | `build_plan_header.py:192,199`, `build_save.py:167-187` | "Scheduling Indicator" (Choice JA/NEJ i SP) er et fritekstfelt, og "Statutory Sort Field" har ingen kolonne. Ingen af dem gemmes, og det er ikke dokumenteret. | Lav en dropdown over `colVhpYesNoOptions` og gem den. Fjern eller dokumentér Statutory. | S | VH |
| D13 | M | `build_items.py:200-212,267-271`, `build_tasklist.py:665`, `build_modal.py:190-211` | Tre fejl i item- og operationshåndteringen: sletning af item eller operation efterlader materialer og dokumenter, som gemmes med tom nøgle; Copy item mister 7 operationsfelter; samme tasklist-linje kan tilføjes to gange (dublet-`OperationNo`). | `RemoveIf` på materialer og dokumenter, én fælles feltliste for operationer, og filtrér eksisterende `OperationNo`. | S | VH |
| D14 | M | 38× `Set(varVhpRuntimeInfo…)` (fx `build_plan_header.py:288`, `build_items.py:151`), `build_hero.py:22` | Kontrollen, der viste `varVhpRuntimeInfo`, er slettet, så "Save the plan before adding items." m.fl. ses aldrig. | Brug `Notify`, deaktivér Add item ved `!varVhpPlanCommitted`, og fjern variablen. | S | VH |
| D15 | M | `build_strategy.py:349-351` mod `build_status.py:63-70,147-151` | Teksten siger "kan gemmes og indsendes uden pakkeallokering", men S4 kræver en pakke pr. operation, så Submit er umulig på en strategi uden pakker. | Lad S4 kun gælde, når strategien har pakker, eller ret teksten. | S | VH |
| D16 | M | `build_load.py:300-316`; `fl_save.py:312-365` | Dyblink uden `IfError`. "Ikke fundet" nulstiller ikke `varVhpRequestGuid`/`varVhpPlanSpId`, så næste gem rammer den gamle plan. FL opretter stille en tom anmodning med den fremmede GUID. Ingen spinner under load. | Nulstil i ikke-fundet-grenen, brug `IfError` + Notify og `with_busy` om load. | S | VH, FL |
| D17 | L | `build_save.py:14-17,114-129` | Nøgle-offset læses fra den nyeste række, som kan være en anden brugers halvskrevne række ("Cannot derive the keys"). Docstringen påstår, at der ikke er noget kapløb. | Udelad rækker uden nøgle i offset-opslaget. `IsBlank()` og `<>` på tekst er ikke delegerbare mod SharePoint, så det skal efterprøves i Studio (uverificeret). Alternativt: sæt nøglen i samme Patch som oprettelsen. Ret docstringen. | M | VH |

**Korrekthed – Equipment/Material**

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| D18 | **H** | `domain_parts.py:318-349,908`, `domain_config.py:59-61` | Eq/Mat læser aldrig `Param("reqid")` (0 forekomster). "Open" fra hubben virker derfor ikke. En ny session starter med tom `varDomRequestGuid`: kladde + Submit opretter en ny indeksrække, den gamle "Kladde" bliver stående, og alle ikke-afsendte rækker flyttes til den nye GUID. I BIO SAP læses `gblEqReqId` heller aldrig. | Bær `RequestGuid` i `colDomRows`, og læs `Param("reqid")` i OnVisible (som FL). Alternativt: slå brugerens åbne kladde op. | M | Eq, Mat, BIO, Hub |
| D19 | **H** | `domain_parts.py:856-920` | `varDomRequestGuid`/`varDomRequestNo` nulstilles aldrig efter Submit. En ny "Save as draft" i samme session sætter den **indsendte** anmodning tilbage til Kladde og overskriver `ItemCount`. | Nulstil efter vellykket Submit, eller afvis patch af en "Indsendt". | S | Eq, Mat, BIO |
| D20 | **H** | `domain_parts.py:395-416,573-595,1393-1401,140` | Indsendte rækker kan slettes: der er ingen `DisplayMode` på række-Delete, ingen bekræftelse og ingen `IfError` (brugeren får "Row deleted…" selv ved fejl). `ItemCount` i indekset opdateres ikke, og der er ingen busy-lås (dobbeltklik). | `DisplayMode` efter `Status`, `confirm_modal`, `IfError` + Notify og `with_busy`. | S | Eq, Mat, BIO |
| D21 | M | `domain_parts.py:525-556` | Gem sker i to trin: `varDomActiveRowId` sættes først efter nøgle-Patch nr. 2. Fejler den, laver næste Gem en dubletrække. (`;`-semantikken i `IfError` er uverificeret.) | Sæt id'et straks efter første Patch. | S | Eq, Mat |
| D22 | L | `domain_parts.py:499,918`; `attflows.py:55` | `EQ-000012` kan være både en række og en anmodning (to ID-rum, samme format). Docstringen nævner et format, der ikke bruges. | Andet format til anmodninger, fx `EQR-`. | S | Eq, Mat |

**Korrekthed – Functional Location og BIO SAP**

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| D23 | **H** | `BIO SAP App/build/build_screens.py:258-260`, `fl_parts.py:684-696`; YAML `BIO SAP App/ScreenFunctionalLocation.pa.yaml:82-83` | I BIO SAP kører FL's load ved hvert skærmbesøg (`varFlRequestGuid <> gblFlReqId`). "New request" nulstiller ikke `gblFlReqId`, så en ny anmodning overskrives af den gamle, når man navigerer væk og tilbage. | Flyt FL's load ind i `open_block`, eller nulstil `gblFlReqId` via en krog. Tilføj et FL-scenarie i testplanen. | S | BIO |
| D24 | M | `fl_save.py:185-193` | `Remove(…, Filter(ex, !(RowGuid in LIVE.RowGuid)))` sletter alle rækker, klienten ikke kender. Den sidste, der gemmer, sletter den andens nye rækker. | Slet kun eksplicit fjernede rækker (`colFlDeleted`), eller brug et `Modified`-tjek. | M | FL |
| D25 | M | `fl_save.py:14-20`, `docs/31:170` mod `domain_parts.py:922-936` | FL og docs/31 siger, at `{ID: …}` afvises som base-record i Patch. Eq/Mat bruger netop det. Det ene er forkert (hvilket er uverificeret). | Afklar i Studio. Virker det, kan FL-gem forenkles (B13). | S | FL, Eq, Mat |

**Robusthed og tilgængelighed – alle apps**

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| D26 | M | Alle `App.pa.yaml` (0× `OnError`) | Ingen global fejlhåndtering. Uventede fejl vises som platformens standardbanner. | Fælles `App.OnError` i `design_tokens.onstart_block`-stil, som logger og viser en venlig Notify. | S | Alle |
| D27 | M | `tools/export_solution.ps1:62` | `$cfg.environment_id` findes ikke i `canvas_apps.json` (kun under `environments`). Uden `-Environment` stopper scriptet altid. | `$cfg.environments.($cfg.default_environment).environment_id`. | S | – |
| D28 | M | `tools/canvas_mcp.py:150-161` | Timeout tjekkes kun mellem linjer, og `readline()` blokerer uendeligt, hvis serveren hænger. | Læsetråd + `queue.get(timeout=…)`. | S | Deploy |
| D29 | M | `build_hub.py:439,688-699,308-321,531-544`; `domain_parts.py:1393-1401,1466-1484`; `fl_parts.py:309-315,433-439` | Tilgængelighed: fliserne udtaler ikke deres tal, popovers kan ikke lukkes med tastatur, og rækkeknapperne har ens labels ("Delete" ×8). Eq/Mat har dobbelt handling (galleriets OnSelect + Edit) uden `row_hit`. | Labels med rækkeidentitet (`"Delete " & ThisItem.ItemKey`), `row_hit`, og et Close-punkt i popovers. | M | Alle |
| D30 | L | `build_hub.py:487,680-684`, `:614-625` mod `build_screens.py:215-217` | "1 requests", "Today" for blank dato, og standalone-Open tjekker ikke for blank `RequestGuid` (det gør BIO). | Småret. | S | Hub |

### E. Vedligeholdelse

| ID | Alv. | Placering | Problem | Forslag | Ind. | Flere |
|---|---|---|---|---|---|---|
| E1 | **H** | `.github/copilot-instructions.md:5-33` | Filen er helt forældet: "fire apps", "Equipments og Materials er den samme app", "kopieret ordret ind i alle fire … build_all stopper". Den læses først af agenter. | Omskriv, eller reducér til en henvisning til README/SKILL. | S | Alle |
| E2 | M | `SKILL.md:3,10-12,219-226,235,253-260,257,278,282,285,290-291,309,333-343,411,444,507,521,627,740,748,949` | Forældet eller modstridende: "FIRE apps" (FL mangler, også i beskrivelsen, der styrer skill-matchning), "knap 6.000 linjer" (10.955), `tools/build_domain.py` (findes ikke), "fire sekunder" (målt 27–31 s), vagter der er slettet, "otte" ForAll-mutationer (0), "0–8 items" (se C9). | Én oprydningsrunde. Generér app-tabeller og tal fra `build_all.APPS`/koden. | M | Alle |
| E3 | M | `README.md:27,34,41,61-76,84-96,139-154`; `Masterdata Hub/README.md:14,17,58,64-70,95,126`; `BIO SAP App/README.md:18-29`; `docs/07:76-138` | Forældet: "oplæg til review", Hurtig start kører den døde `Provision-VHPlanLists.ps1`, kontroltal og `LaunchTarget.New` passer ikke, og BIO-tabellen påstår at blive skrevet af build. | Del README op i "Byg og deploy" (levende) og "Baggrund". Ret hub-README og docs/07. | S | Alle |
| E4 | M | `tools/build_all.py:1-14,21,164-170,242,269/272`; `gen_screen.py:5-6`; `check_layout.py:2-56,71-73`; `layout_tokens.py:78,321`; `domain_config.py:5-9`; `canvas_apps.json:30-32`; `canvas_mcp.py:534-541` | Kommentarer og docstrings modsiger koden: kopi-vagter, `build_domain.py`, "fire apps" (37× i `tools/`, heraf én, der havner i genereret `App.pa.yaml`), `doc_check = True` sat to gange, og "biosap app_id er null" (den er sat). | Ryd op. | S | Alle |
| E5 | M | `events.jsonl` (8,5 MB), `session.db`, `workspace.yaml`, `checkpoints/` (commit `d27b33c`) | Copilot-sessionsfiler i roden. `events.jsonl` indeholder 1.019 lokale Windows-stier, 45 make.powerapps.com-URL'er og 5 e-mailadresser. Intet refererer til filerne. | Slet og føj til `.gitignore`. Fjern fra historikken sammen med D1. | S | – |
| E6 | M | `.gitignore:17`; 5× `solution/**/*.msapp` (1,27 MB) | Tracked trods ignore (lagt tilbage i `c10d355`, `59c9e7b`). SKILL.md:746 påstår det modsatte. | `git rm --cached` og en pre-commit-vagt. | S | – |
| E7 | **H** | `sharepoint/provision/Provision-VHPlanLists.ps1:89-136,285-311` mod `Provision-StrategyLists.ps1:99-138` | Begge opretter `MD_Strategy`/`MD_StrategyPackage` med forskellige kolonner (Title = `PackageKey` over for `PackageLabel`). README's Hurtig start giver et andet skema end det, apperne kører mod, og seed er ikke idempotent. 8 VHP_-lister bruges af ingen app. | Arkivér scriptet og `MD_ValueHelp.csv`. `StrategyLists` bliver eneste ejer. | S | VH, BIO |
| E8 | M | `sharepoint/provision/*.ps1` | `New-MdList` findes 4 gange, `New-MdField` i 3 forskellige udgaver, `Add-Col` 3 gange. ClientId-GUID'en står 10 steder, der er 3 forbindelsesmåder, og kun 5 af 10 scripts har WhatIf. `Provision-EqMatLists.ps1:59` henviser til `-WhatIfReport`, som ikke findes. | `_Common.psm1` (New-MdList/New-MdField/Rename-Title/Connect-Site/WhatIf). | M | Alle |
| E9 | M | `sharepoint/inspect/out/schema.md:3` (udtrukket 2026-09-20) | `FunctionalLocationItems`/`Requests`, `MD_HelpText`, `NoBomItem` og draft-valg mangler i udtrækket. Hele FL-datakontrakten er uprøvet af `check_datasources`. | Kør `Export-ListSchema.ps1` igen, og brug `--strict` til at fejle ved manglende lister. | S | FL, VH |
| E10 | M | Hele repoet | Ingen tests, ingen CI og ingen `requirements.txt`/`pyproject`. PyYAML (`check_layout.py:65`, `check_combined.py:27`, `canvas_mcp.py:457`) og openpyxl er udeklarerede. Node er valgfri (byggeriet er grønt uden FL-regeltjek, `build_all.py:262-272`). Harnessen sammenligner kun `plan`/`columns`/`lists` (`tools/fl/harness.js:503-509`). `check_vba.py` køres ikke. Versioner af PnP.PowerShell, .NET/dnx, MCP-pakke og pac står ingen steder samlet. | `requirements.txt`, et afsnit med forudsætninger, pytest med plantede fejl pr. regel, og et GitHub Actions-workflow (`build_all` + `git diff --exit-code`, Node påkrævet). Harnessen skal sammenligne hele planen. | M | Alle |
| E11 | L | `tools/build_all.py:100-102` | Farvevagten scanner kun `*/build/*.py`, ikke `tools/`, hvor det meste UI-kode nu bor (0 fund i dag). | Udvid til `tools/*.py` minus `design_tokens.py`. | S | Alle |
| E12 | L | `powerfx/*.fx`, `schema/`, `excel/powerquery`, `excel/vba`, docs 01–05/08–13/15–16/25, `seed/MD_FL{Class,Characteristic,ValueList}.csv`, `extract_spool_rules.py`, 6× `PROMPT-vscode-*.md`, 2× `_EditorState.pa.yaml`, `steps.html`, `solution/…/orsted_biosapnew_61bf5*`, `…ba408*`, `cr871_*`, `orsted_materialer_93a70*` | Historisk eller dødt indhold er ikke markeret. `04-submit-patch.fx` beskriver et andet gem-design, og PROMPT-filerne peger på stier, der ikke findes. | Flyt til `archive/` med en README, eller slet (git husker). | S | – |
| E13 | L | `.gitattributes`; `excel/artifact/*.xlsm` (8 MB), `Masterdata Hub/image.png` (1 MB), `html/lookups.generated.js` (1,8 MB) | `.xlsm`/`.msapp`/`.frx` er ikke markeret binære, og der bruges ikke LFS. Generatoren til `lookups.generated.js`, som er input til FL-byggeriet, findes ikke i repoet. | `binary`-markering, LFS, og læg generatoren i `tools/` eller dokumentér den i docs/31. | M | FL |
| E14 | L | `solution/…/orsted_masterdatahub_1b09a.src/Src/ScreenMdHub.pa.yaml` | Eksporten er en ældre hub (83 kontroller, `LaunchTarget.New`, ingen sidebar). Enten er den nye hub ikke publiceret, eller også er eksporten ikke hentet igen. | Deploy, publicér og eksportér igen. Tjek derefter B3 mod den rigtige udgave. | S | Hub |
| E15 | L | `docs/02` / lister | SharePoint-navngivningen er uens: `MD_` over for intet præfiks (EquipmentItems, FunctionalLocation*), `Tasklist` over for `TaskList`, Title omdøbt til 12 forskellige navne (EquipmentItems.Title = `Description`, MaterialItems.Title = `MaterialDescription`). docs/02:8 siger "Relationer er Number", men de rigtige lister bruger Lookup. | Skriv en konvention for **nye** lister (`MD_<Domæne><Ting>`, fast Title-rolle). Omdøb ikke eksisterende interne navne. | M | Alle |

---

## 3. Forslag til fælles standard

Standarden bygger på den **dominerende** eksisterende konvention, så den kræver færrest omdøbninger.

| Element | Standard | Eksempel | Nuværende afvigelser |
|---|---|---|---|
| App-infix | `Md` / `Vhp` / `Dom` / `Fl` lige efter præfikset | `btnDomSave` | Eq/Mat 39 hver uden infix; `cmbVhpItemFL` |
| GroupContainer | `con` | `conDomForm` | – |
| ModernText | `txt` | `txtVhpPlanTitle` | 110 med `con` (A3) |
| TextInput / NumberInput / DatePicker | `inp` / `num` / `dte` | `inpDomText`, `numVhpCycle`, `dteDomWarrantyStart` | 17 `txt`-input, Mat 3 `inp`-tal, Eq 2 `inp`-dato |
| Dropdown / Combobox / Checkbox / Toggle | `drp` / `cmb` / `chk` / `tgl` – dropdown **altid** `themed_dropdown` | `drpDomPlant` | VH 11 + FL 1 ModernDropdown |
| Gallery / HtmlViewer / Rectangle / Image / Button / Spinner / Timer / Attachments | `gal` / `htm` / `rct` / `img` / `btn` / `spn` / `tmr` / `att` | `htmVhpOpsHeader` | VH 4 `con…Gal`, 4 `con…Html`; 2 Rectangle med `con` |
| Skærm | `Screen<Domæne>` | `ScreenEquipment` | – |
| Skærm-/app-tilstand | `var<X>*` (kun `Set`, ingen `UpdateContext`) | `varDomSaving` | Hub 6× `gbl*` |
| Tilstand delt på tværs af apps | `gbl*` | `gblNavOpen` | `darkModeEnabled` (bevares, token-kontrakt) |
| Samling | `col<X>*` | `colDomRows` | `colAppPrefs` (bevidst fælles) |
| Navngiven formel | tabel `col<X>*`, skalar `<X>Pascal` | `colVhpPlantCodes`, `VhpCanSubmit` | FL 13× `nfFl*` |
| Faste stammer | `…Me`, `…Saving`, `…ConfirmSubmit`, `…Validated`, `…Info`, `…FlMsg`, `…RequestNo`, `…RequestGuid` | `varFlSaving` | `varVhpFlMeta`, `varVhpRuntimeInfo`, `varVhpPlanKey`, `varFlStale` |
| Notify-tekster | `tools/messages.py`: "Saved as X - see it on the landing page." / "Submitted as X - see it on the landing page." / "Save failed: …" | – | A6 |
| Busy | `with_busy(var<X>Saving)` + `loading_overlay(img<X>Saving)` om alle skrivninger og uploads | – | VH manuel, upload uden |
| Fejl | `IfError` pr. trin med samlet fejlliste (FL-modellen) + `App.OnError` | – | D8, D26 |
| Dato/tal | `DATE_FMT = "yyyy-mm-dd"`, `num_text` med kultur-lås | – | A9 |
| Typografi/mål | `type_scale` 11/12/13/14/17/22, `RADIUS_INPUT 10`, `RADIUS_CARD 14`, `RADIUS_MODAL 16`, `CONTROL_H 36`, `BUTTON_MIN_H 30`, `CARD_PAD 18` i `layout_tokens` | – | C8, A11 |
| Sprog | UI engelsk; SharePoint-valgværdier (Kladde/Indsendt/Ja/Nej) uændrede; AccessibleLabel engelsk | – | A7, A14 |
| SharePoint (nye lister) | `MD_<Domæne><Ting>`, fast Title-rolle, indeksér alt der filtreres på | `MD_RequestIndex` | E15 |

**Fælles moduler, der bør oprettes eller udvides**

| Modul | Indhold | Erstatter |
|---|---|---|
| `tools/request_index.py` | Domænenøgler, STATUS (flyttet fra `hub_config`), `index_record()`, `number_fx()`, `open_url()` | Tre indeks-writers (A13, D4) |
| `tools/messages.py` | Notify-tekster | A6 |
| `tools/domain_app.py` | `build_app_yaml(cfg)`, `build_screen(cfg, parts)`, `KINDS`-tabel | Eq/Mat-indgange og EMPTY/BLANK spredt 6 steder (C5) |
| `tools/app_yaml.py` | Én writer til `App.pa.yaml` (Formulas + OnStart + OnError) | Fem writers (C5, D26) |
| `tools/fx.py` | Power Fx-tokenizer, `split_args`, `_num` | Syv scannere (C7) |
| `canvas_apps.json` (udvidet) | `scripts`, `screen`, `prefix`, `nav_order`, `icon` | App-listen 7 steder (C6) |
| `sharepoint/provision/_Common.psm1` | New-MdList/New-MdField/Rename-Title/Connect-Site | E8 |
| `layout_tokens` (udvidet) | Typografi og komponentmål | C8 |

---

## 4. Prioriteret handlingsplan

### Fase 0 – nu (sikkerhed; uafhængig af resten)
1. **D1/D3**: bekræft rotation af client secret og x-apikeys, skift til en miljøvariabel af typen Secret, og omskriv historikken. Fjern samtidig **E5** (sessionsfiler) og **E6** (.msapp).
2. **D2**: regenerér trigger-signaturen, og flyt URL'en ud af `Constants.bas`.

### Fase 1 – quick wins (S, ingen arkitekturændring)
- **Datatab/brugerfejl:**
  - D9 (TasklistKey), D10 (ObjectList), D11 (Status), D19 (nulstil efter Submit).
  - D20 (slet-spærre + bekræftelse + IfError), D23 (BIO FL-reload), D21.
  - D14 (usynlige beskeder), D15, D16, D13.
- **Kontrakter:** D4 (`APP_URL` via `env_config` og Open ud fra Domain), D27 (`export_solution.ps1`), C1 (ROOT), C13 (`raw_var` obligatorisk).
- **Ydelse:** C10 (memoisering, ca. 15 s hurtigere byg), B2 (AccessibleLabel), B3 (fladt filter), B9, B11.
- **Ensartethed:** A2 (`Dom`-infix), A6 (Notify-tekster), A7 (dansk tekst + sprogtjek), A8 (knaptekster), A14–A17, A12, E11.
- **Dokumentation:** E1, E2, E3, E4 (én oprydningsrunde), E7 (arkivér VHPlanLists), E9 (nyt skemaudtræk), E12 (arkivmappe).
- **Byggeri:** `requirements.txt` og pyflakes/ruff i `build_all` (C11, del af E10).

### Fase 2 – fælles refaktorering (M)
- `tools/request_index.py` + `tools/messages.py` (A13, A6). Lad alle fem apps bruge dem.
- `tools/domain_app.py` + én `App.pa.yaml`-writer + `App.OnError` (C5, D26).
- `domain_parts` med `cfg` som parameter, ingen modulniveau-import (C2). Import uden sideeffekter (C3).
- Udvidet `canvas_apps.json` som eneste app-liste (C6), og BIO SAP med eksplicitte kroge i stedet for monkeypatch (C4).
- Navngivningsstandarden fra §3 (A1, A3, A4, A5, A10) og designtokens for typografi og mål (C8, A11, A9).
- Dyblink `?reqid=` i Eq/Mat (D18). Rækkespejl med statusfilter og loftadvarsel (B4). Hub-tællinger uden `CountRows` mod listen (B1).
- `_Common.psm1` til provisionering (E8). Indeksér VH-lookupkolonner (B14).
- CI-workflow og pytest med plantede fejl pr. regel (E10), og ret C9 (N=0/1).

### Fase 3 – større forbedringer (L)
- **VH-gem om til stabile items** (D7, D8): opdatér frem for delete+recreate, GUID som mappenavn, skriv-før-slet, `Modified`-tjek og `IfError` pr. trin. Del `save_action` op, og fjern dobbeltindlejringen (B7, C15).
- **FL:** inkrementel validering (B5, B6), gem uden "slet alt ukendt" (D24), og afklaring af `{ID}`-base (D25).
- **`check_layout.py` som regelregister** i moduler med én tokenizer (C7). Én indgang `tools/build.py --app X` in-process (skitse: config → generate → én writer → assemble → check), som også gør BIO SAP-dobbeltbygningen overflødig.
- **Beslutning om BIO SAP App:** hvis den samlede app er målet, blokerer D23, C4, AppUrl i indeks og mailflow samt manglende FL-testscenarie. Når de er løst, kan de fem enkeltapps udfases, og vedligeholdelsen halveres.

---

## 5. Det, der allerede er godt og bør bevares

- **Genereret, deterministisk output.** Der er ét sted at rette (`build/*.py`), render sorterer egenskaberne, og byggeriet gav 0 diff på tværs af hash-seeds.
- **Designtokens.** Alle farver ligger i `design_tokens.py` med lys og mørk gren. Kontrast, balance og ΔE efterprøves som kode, og `ref_hex` bruges i HTML/SVG. Skærmene indeholder ingen rå farver.
- **Layout-tokens.** Breakpoints (`below`/`if_below`/`fits`), `SHELL_W` som nedre grænse og testbredder udledt af breakpoints. `check_layout` fanger reelle fejlklasser før Studio (højdereferencer, wrap-rækker, manglende samlinger, `Default` som skalar, strengformede kolonnenavne).
- **Fælles ramme.** `app_frame`, `top_bar`, `side_nav`, `theme_button`, `loading_overlay`, `confirm_modal`, `row_hit` og `input_theme`/`readonly_mode` (låst = View/Outline). De 19 formler, der er ordret ens på tværs af apps, kommer alle herfra.
- **Én kilde til miljø og app-id'er** (`canvas_apps.json` + `env_config`, `--env`). Kun `build_save.py:76` går uden om.
- **Ingen datahentning i OnStart.** Opslag sker i dovne navngivne formler. Hubben har reelt kun én datakilde, og filtre mod SharePoint sammenligner med globale variabler på indekserede kolonner (`RequesterEmail`, `IsOpen`, `RequestGuid`).
- **Batchskrivning.** `Patch(liste, ForAll…, ForAll…)` og ingen mutation i `ForAll` (VH-plan har 0, SKILL.md siger 8).
- **FL-gem som model.** `IfError` pr. trin, klient-`RowGuid` mod dubletter og status skrevet til sidst.
- **Regler med én kilde.** FL-reglerne kompileres fra `html/*.js` og differentialtestes (108 sager, 4.000 sæt, fast seed).
- **`Text(GUID())`, `Coalesce` og kultur-låste talformater**, og `Launch(…, LaunchTarget.Replace)` med tema i URL'en.
- **Sikker deploy.** `canvas_mcp` arbejder på en kopi, stopper ved compile-fejl og efterprøver træet. `scrub_solution` ser på sti og JSON-forælder, og PowerShell-tjekket håndhæver BOM/ASCII.
- **Selvtjek i builderne.** Fx `check_form_order`, `check_mappings`/`check_plan_record` i VH, statusvagter i hubben og konfliktstop ved fletning i BIO SAP.
- **Kommentarer, der forklarer *hvorfor*,** med issue-numre. Det er værdifuld historik (ryd dog de forældede dele, E4).
- **`check_vba.py`** er forbilledet for Python-stilen (typehints, pathlib, små funktioner).

# 38 — Audit: moderne kontroller i BIO SAP App (issue #161)

Optalt i den genererede `BIO SAP App/*.pa.yaml` efter denne ændring.
Appen er allerede overvejende moderne: ModernText 673, GroupContainer 586,
ModernButton 329, ModernTextInput 72, ModernDropdown 32, ModernNumberInput
15, ModernCheckbox 8, ModernCombobox 4, ModernDatePicker 2.

Grundregel for auditten: **kun kontroltyper, som appen allerede deployer i
dag**. ModernAttachments gav "Unknown control type" i Peters Studio (#165),
så ingen nye `Modern*`-typer er indført. Ingen preview-kontrol er brugt.
Undtagelser, som Peter har godkendt bagefter: ModernAttachments@1.3.0,
ModernSpinner@1.1.0 (#302), ModernProgressBar@1.0.0 (#305) og
ModernIcon@1.1.0 (#306) — se "byttet" nederst i oversigten — samt
ModernBadge@1.0.0 (#304, #161 delt i #302–#307) — se "Mærker" nedenfor.
Desuden ModernTabList@1.0.0 (#303), se *Faner*.

## Hvad er ændret

| Skærm | Før | Efter | Hvorfor |
|---|---|---|---|
| MdHub (godkendelsesflow-popup) | `btnMdAprCard` — Classic/Button i `DisplayMode.View`, tom tekst | `txtMdAprCard` — ModernText uden tekst | Kortet er kun en flade bag trinets tekster. Som knap var det et tomt tabstop uden handling. Nu samme mønster som Issue Boards aktivitetskort (`txtIbActBg`): samme fyld, stiplede kant og hjørner. Klikket ligger uændret i `btnMdAprExpand` ovenpå. |

Ingen andre kontroller er byttet. Ingen logik, data, rettigheder,
View/Edit, flows, SAP eller vedhæftninger er rørt.

## Ikke-moderne kontroller, der er tilbage

Skærme: Eq = Equipment, FL = Functional Location, IB = Issue Board,
KKS, Mat = Material, Hub = MdHub, VHP = VH-plan.

### Classic/Button — 19 (var 28 før #307)

Kun klik-lag med gennemsigtig tekst er tilbage. Check_layout regel 16k
afviser enhver anden Classic/Button.

| Formål | Antal | Skærm(e) | Kontroller | Grund til at beholde |
|---|---|---|---|---|
| Klik-lag over en hel række (`row_hit`) | 18 | alle | `btn*FbSubjectPick` (8), `btnIbRowOpen`, `btnIbSimOpen`, `btnKksRowHit`, `btnKksPickHit`, `btnMdRowHit`, `btnMdPeekOpen`, `btnMdAprExpand`, `btnVhpItemOpen`, `btnVhpOpMHit`, `btnVhpMgHit` | Gennemsigtigt lag med `HoverFill`/`PressedFill` i tokens (row-hover/row-pressed). ModernButton har intet `Fill`, `HoverFill` eller `PressedFill`; Fluent-temaets egen hover-flade ville dække rækken. |
| Godkendelses-chevron i hubbens række | 1 | Hub | `btnMdRowApproval` | Pilleformet trykzone med `HoverFill`/`PressedFill` og højrestillet "›". Samme grund som rækkelaget. |

Alle har `TabIndex = 0` og læses via `Text`/`Tooltip` (Classic/Button har
ingen `AccessibleLabel`), jf. #168.

### Byttet til ModernButton (#307)

| Kontrol | Antal | Skærm(e) | Før | Efter |
|---|---|---|---|---|
| `btn*FbSubject` (feedback-vælgerens felt) | 8 | Eq, FL, IB, KKS, Mat, Hub, MP, VHP | Classic/Button, gennemsigtig, `Padding* = 0`, `Align.Left` | ModernButton, `ButtonAppearance.Transparent`, `Padding* = 0`, `Align.Left`, `BorderStyle.None`. Feltets flade og kant er stadig beholderens (`con*FbSubject`), så teksten flugter med listen under (#140). |
| `btnVhpPickerHeadPartial` ("nogle valgt – vælg alle") | 1 | VHP | Classic/Button 18 × 18 px i primærfarven med "−" | ModernButton 18 × 18 px, `ButtonAppearance.Primary` + `BasePaletteColor` = primærfarven, 1 px kant, radius 4, `Padding* = 0`, fed "−". |

Begge bygges af `build_helpers.flat_button`. OnSelect og synlighed er
uændrede (tests/test_modern_buttons.py). Typen skrives som `ModernButton`
uden `@`-version, som resten af appen og som Studio selv skriver den.
Regel 16k låser det og afviser egenskaber, Learn ikke dokumenterer for
den opdaterede knap. Regel 25 (mindst 30 px) undtager en knap med
`PaddingTop`/`PaddingBottom` = 0.

Det kan ModernButton **ikke** gengive (bevidst accepteret):

- **Hover og tryk.** Den klassiske knap havde egne `HoverFill`/`PressedFill`/
  `Hover*Color`, så fladen var ens i alle tilstande. ModernButton har ingen
  af dem; hover/tryk er Fluent-temaets. På feedback-feltet (Transparent)
  kan teksten skifte farve ved hover; på "−"-feltet bliver fladen en
  mørkere nuance af primærfarven.
- **Fokusramme.** `FocusedBorderColor`/`FocusedBorderThickness` (2 px i
  primærfarven) findes ikke; Fluent tegner sin egen fokusring.
- **TabIndex.** Findes ikke på ModernButton (regel 10); knappen er altid
  i tab-rækkefølgen, som før med `TabIndex = 0`.
- **18 px uden min.-størrelse er ikke afprøvet.** Fluent-knappen kan have
  en min.-bredde/-højde, der ignorerer `Width = 18`. Ser "−"-feltet
  forkert ud i Studio, rulles #307 tilbage.

Ny til gengæld: begge har nu `AccessibleLabel` (den klassiske knap har
ingen).

Bemærk: rækkelaget er en *klassisk* kontrol **oven på** moderne tekster,
ikke en klassisk kontrol skjult under en falsk moderne flade. Det er det,
issuet forbyder.

### Image — 304 ved auditten

Efter #302 er 6 Image-kontroller væk (`imgMdAprSpinner` og de 5
"Searching..."-billeder). Ventesløret (9) og fejlikonet i
"Opening request"-kortet (5) er stadig billeder, nu uden hjul. Tallene
herunder er auditens; de er ikke talt om.

Efter #304 er de 5 nummerpiller (`img…Number` og `imgMdAprNo`) ModernBadge;
tallene herunder er auditens og er ikke talt om.

| Formål | Antal | Skærm(e) | Grund til at beholde |
|---|---|---|---|
| Sidebar og temaskift (klikbare SVG'er, lukket + åben) | 190 | alle | `tools/side_nav.py` og `theme_button` (#37): en ModernButton tegner Fluent-temaets form og kan hverken have vores egne domæneikoner (`tools/icons.py`) eller accentstregen. |
| Øvrige klikbare ikoner (hubbens fliser og "New", række-ikoner Edit/Delete/Notes/Timeline, VH-trin, hjælp, objektliste) | 27 | Hub, VHP, … | Egne domæneikoner i tokenfarver. ModernButton.Icon tager kun Fluent-ikonnavne. |
| Feedback-vælgerens ikon/chevron | 21 | alle | Del af det samme felt som `btn*FbSubject`; egne SVG'er, ikke Fluent-ikoner. |
| Dekorative/status-ikoner (sidetitel, nummerbadge, status, domæne, rail, fil-miniature) | 34 | alle | 13 med et Fluent-sidestykke er byttet til ModernIcon@1.1.0 (#306); resten er domæneikoner eller tegninger med tekst — se "Ikoner — ModernIcon" nedenfor. |
| Slør bag popup (luk ved tryk udenfor) | 20 | alle | Fuldskærms trykflade; ingen moderne kontrol med `OnSelect` og gennemsigtig flade. |

### Rectangle — 22

| Formål | Antal | Skærm(e) |
|---|---|---|
| Skillestreg mellem rækker | 9 | FL (2), IB, KKS (2), Hub, VHP (3) |
| Rækkebaggrund | 6 | KKS (2), Hub (2), VHP (2) |
| Accentstreg i feedback-vælgeren | 7 | alle |

Ingen moderne figurkontrol findes. En ModernText uden tekst kan stå for en
flade (som `txtMdAprCard`), men at bytte 22 rene streger giver ingen
gevinst og flere kontroller at teste; de bliver.

### Gallery — 41 · Timer — 9 · HtmlViewer — 8

| Kontrol | Antal | Brug | Grund |
|---|---|---|---|
| Gallery | 41 (Eq 3, FL 5, IB 5, KKS 6, Mat 3, Hub 4, VHP 15) | lister, tabeller, faner, hjælp | Ingen GA-erstatning. ModernTable er preview og kan ikke det, galleriernes skabeloner gør (knapper, input og egne celler pr. række). |
| Timer | 9 (Eq 2, FL 1, KKS 2, Mat 2, VHP 2) | forsinket søgning, "loader langsomt"-besked | Ingen moderne Timer. |
| HtmlViewer | 8 (FL 1, VHP 7) | tabeloverskrifter, summer, FL-struktur | Ingen moderne erstatning. |

### Mærker — byttet til ModernBadge@1.0.0 (#304)

Status- og nummermærker, der var en ModernText med fyld og runde hjørner
eller et Image med en SVG-pille, er nu den moderne Badge. Én byggeklods:
`build_helpers.modern_badge`. Teksten er den samme, og farverne er vores
egne tokens: `Color` og `Fill` sættes altid (Learn: er de tomme, vælger
`Intent`/`Appearance` farven), så hver status har præcis sit farvepar fra
før, også i mørk tilstand. `Intent` er `BadgeIntent.Neutral`, så et mærke
aldrig falder tilbage til Fluents grønne standard. Ingen `OnSelect` og
ingen `TabIndex` (display-only). Navnene har fået præfikset `bdg`.

| Hvor | Antal | Før | Efter |
|---|---|---|---|
| Trin-mærket "Valid"/"Invalid" i VH-planens sektioner (`step_badge`) | 4 | `txtVhp…HeadBadge` (ModernText) | `bdgVhp…HeadBadge` — samme `Switch(Self.Content, …)` på state-ok/-error/-neutral |
| Nummerpillen ved sidetitlen (`number_badge`, Eq/Mat/MP/VHP) | 4 | `img…Number` (Image, 88 × 26 SVG: tekst i domænefarven på 12 % af den) | `bdg…Number` — `Color = ColorValue(hex)`, `Fill = ColorValue(hex & "1F")` (1F = 12 %); skjult, mens der intet nummer er (billedet var tomt) |
| Anmodningsnummeret i hubbens godkendelsesflow | 1 | `imgMdAprNo` (Image) | `bdgMdAprNo`, samme domænefarve-tone |
| Trinets status i godkendelsesflowet ("Approved", "Pending" …) | 1 | `txtMdAprChip` | `bdgMdAprChip`, samme `BADGE_FG`/`BADGE_BG` |
| Issue Board: sagsnummeret (række, kompakt række, detalje) | 3 | `txtIbRowNo`, `txtIbRowNoC`, `txtIbDetNo` | `bdgIb…No` |
| Issue Board: status og prioritet i detaljen | 2 | `txtIbDetStatus`, `txtIbDetPriority` | `bdgIbDetStatus`, `bdgIbDetPriority` — samme state-*-par; Normal/Low er stadig tekst uden pille (gennemsigtigt fyld, venstrestillet) |
| Issue Board: rollen i Activity | 1 | `txtIbActRole` | `bdgIbActRole` |

Check_layout regel 16e afviser enhver anden Badge-version, ukendte
egenskaber (fx `ThemeColor`, `FontSize`, `TabIndex`) og et mærke uden
`Color`, `Fill`, `Content` eller `AccessibleLabel`.

**Bevidst beholdt** (kan ikke byttes sikkert nu):

| Mærke | Antal | Hvor | Grund |
|---|---|---|---|
| Statuschippen i listerne (`tools/status_chip.py`): `img…RowStatus`/`…RowStatusC` (Eq, Mat, MP, Hub, IB) og IB's prioritet `imgIbRowPriority`/`…C` | 14 | lister/tabeller | Chippen er ikon **og** tekst (UX-review T4, #139: status ses på formen, ikke kun på farven). Ikonerne er vores egne (`tools/icons.py`); Badge.`Icon` tager kun Fluent-ikonnavne, og flere af vores statusser har ingen afprøvet Fluent-pendant. Et bytte ville enten fjerne ikonet eller gætte på ikonnavne, Studio ikke har set. Kan byttes, hvis Peter vil have mærker uden ikon. |
| View mode / Edit mode ved sidetitlen (`mode_badge`): `img…Mode` | 6 | alle domæneskærme | Samme grund: øje/blyant er egne ikoner foran teksten (#139). |
| Filtypen i dokumentlisterne (`doc_upload.type_badge`): `txt…AttType` | 4 | Eq, Mat, MP, VHP | `tools/doc_upload.py` bygges om i PR #323 (#300); røres ikke her. Kandidat bagefter. |
| `txtIbFileKind` | 1 | IB | En 44 × 44 fil-flise (miniature), ikke et mærke. |

Antal-mærker på faner og i sidebaren findes ikke som egne kontroller i
appen i dag (tallene står i knappernes tekst), så der var intet at bytte.

### Spinnere — byttet til ModernSpinner@1.1.0 (#302)

Auditten talte 12; en fuld optælling efter #302 fandt 20 Image-hjul (15
drejende SVG'er fra `spinner_svg` og 5 "Searching..."-billeder fra
`fl_picker.busy_box`). Alle 20 er byttet; regel 16c afviser fremover
ethvert Image med et drejende SVG (CSS `rotate(360…)` eller SMIL
`animateTransform type='rotate'`) og enhver anden Spinner-version.
De 7 gem/upload-slør i første række (`*Saving`, `imgIbBusy`,
`imgIbUploading`) er siden blevet ModernProgressBar (#305, nedenfor); kun
`imgKksLoading` og `imgMdNavigating` er stadig hjul der — 13 hjul i alt.

| Hvor | Antal | Før | Efter |
|---|---|---|---|
| Ventesløret ved gem/indlæsning (`loading_overlay`): `*Saving` (Eq, FL, Mat, MP, VHP), `imgIbBusy`, `imgIbUploading`, `imgKksLoading`, `imgMdNavigating` | 9 | Ét Image over hele skærmen med hjul (og evt. billedtekst) i SVG'en | Samme Image som slør (uden billede, tager stadig trykket) + `spn…` midt på skærmen, oven på sløret. Billedteksten ("Uploading files...", "Opening...") er spinnerens `Label` under hjulet |
| Kortet "Opening request" (`open_overlay`): `*LoadIcon` (Eq, FL, Mat, MP, VHP) | 5 | Ét 40 × 40-billede: hjul eller fejl-(!) | `spn…LoadIcon` (40 × 40) mens der hentes; `img…LoadIcon` viser kun (!) ved fejl, samme plads |
| Godkendelsesflow/aktivitet i hubben: `imgMdAprSpinner` → `spnMdAprSpinner` | 1 | Image 110 px høj | Spinner, samme plads og synlighed |
| FL-/leverandørsøgning: `img*FlBusy`/`imgVhpVenBusy` → `spn*…Busy` (Eq, Mat, MP, VHP ×2) | 5 | Ét billede: knapformet boks, hjul og "Searching..." | Spinner med "Searching..." til højre for hjulet i knappens faste plads (154 × 36). Boksen bag er væk |

Farve: `BasePaletteColor = C.'color-brand-primary'` (Fluent tegner hjulet
ud fra paletten), etiketten i `C.'text-primary'`. Sporets farve, hjulets
størrelse og den forsinkede indtoning kan ikke sættes på kontrollen
(ingen `SpinnerSize`/`Fill` på Learn). Bygger: `build_helpers.spinner`.

### Attachments — byttet til ModernAttachments@1.3.0 (#161)

| Kontrol | Antal | Brug | Status |
|---|---|---|---|
| ModernAttachments@1.3.0 | 5 (`attEqPicker`, `attMatPicker`, `attMpPicker`, `attVhpAttPicker`, `attIbFiles`) | vælg filer til upload | Byttet fra `Attachments@2.3.0`. Peters Studio (authoring 3.26101.10) kender typen og skriver `@1.3.0`. Stadig preview på Learn. Upload går uændret gennem flowene: `BioSap-TaskListAttachment` til biblioteket `TaskListDocuments` og `BioSap-IssueBoard-Submit` ("attach") til `IB_Tickets`. Regel 16b afviser den klassiske og enhver anden version. |

### Ikoner — byttet til ModernIcon@1.1.0 (#306)

En fuld optælling efter #306 fandt 13 rene pynt-/statusikoner, hvis form
har et Fluent-ikon. De er byttet; alle andre ikkeklikbare billeder er
bevidst beholdt (tabellen under). Regel 16i låser typen til
`ModernIcon@1.1.0` fra `build_helpers.fluent_icon`, kun Learns egenskaber
(intet `TabIndex`, intet `Style`), navnet `ico…`, en ikke-tom
`AccessibleLabel` og intet `OnSelect`. Fluent-navnene står i
`tools/icons.FLUENT`.

| Hvor | Antal | Før (stregikon i `tools/icons.py`) | Efter (Fluent) | Farve |
|---|---|---|---|---|
| Toast-beskeden: `ico{Eq,Fl,Ib,Kks,Mat,Md,Mp,Vhp}ToastIcon` | 8 | Ring med flueben / udråbstegn / kryds / "i" | `CheckmarkCircle` / `ErrorCircle` / `DismissCircle` / `Info` efter `gblToast.Kind` | `state-ok-fg` / `state-warn-fg` / `state-error-fg` / `state-info-fg` |
| Lup ved søgefeltet: `icoIbSearchIcon`, `icoKksFindIcon` | 2 | Lup | `Search` | `text-muted` |
| VH-plan: `icoVhpPlanFoldStatus` (sammenfoldet hoved), `icoVhpItemCardStatus` (item-kort) | 2 | Ring med flueben / udråbstegn | `CheckmarkCircle` / `ErrorCircle` | `state-ok-fg` / `state-error-fg` |
| Hubbens godkendelsesforløb: `icoMdAprPerson` | 1 | Hoved og skuldre | `Person` | `text-muted` |

Størrelse (20 × 20, personen 16 × 16), placering (`X`/`Y`,
`AlignInContainer`, `LayoutMinWidth`), synlighed og etiketter er
uændrede. `IconStyle.Outline` svarer til stregtegningen. Fluent tegner
glyffen med sin egen streg og indre luft, så den kan se en anelse
anderledes ud end vores 1,8 px-streg.

#### Beholdt som Image — og hvorfor

| Billede(r) | Antal | Grund |
|---|---|---|
| Sidetitlens ikon `img*TitleIcon` | 8 | Domæneikon fra `tools/icons.DOMAIN` på en tonet firkant i domænets farve. Ingen Fluent-sidestykke, og det skal være samme tegning som sidebaren (som bliver Image). |
| Tom-liste-ikon med domæneikon (`imgEqRowsEmptyIcon`, `imgMatRowsEmptyIcon`, `imgMpRowsEmptyIcon`, `imgIbEmptyIcon`, `imgMdEmptyIcon`, `imgVhpItemsEmptyIcon`, `imgVhpMatEmptyIcon`) | 7 | Domæneikon (samme grund). |
| Tom-liste-ikon med listeglyf (`imgVhpOpsEmptyIcon`, `imgVhpOpsEmptyMIcon`) | 2 | Samme `empty_state`-mønster som domæneikonerne: glyf på en 12 % tonet firkant. ModernIcon har `Fill`, men en tokenfarve med 12 % alfa kan ikke skrives uden at regne farven om, og mønsteret skal se ens ud på tværs af skærme. |
| Domæne i hubbens række/kig (`imgMdRowDomain`, `imgMdRowDomainC`, `imgMdPeekDomain`) | 3 | Domæneikon (samme grund). |
| Tilstandsmærker (`img*Mode`) | 5 | Pille med tekst og glyf i én tegning. ModernIcon kan ikke vise tekst. Nummerpillerne (`img*Number`, `imgMdAprNo`) er siden blevet ModernBadge (#304, se *Mærker*). |
| Statuspiller i rækkerne (`img*RowStatus(C)`, `imgIbRowPriority(C)`, `imgIbRowStatus(C)`, `imgIbSimStatus`, `imgMdRowStatus(C)`) | 13 | Pille med glyf og tekst — samme grund. |
| Godkendelsesstriben `imgMdRowApproval(C)` | 2 | Flere knuder og streger i én tegning; ikke ét ikon. |
| Godkendelsesforløbets rail `imgMdAprRail` | 1 | Lodret streg, fyldt knude og symbol i én tegning; ModernIcon kan ikke tegne forbindelseslinjen. |
| Fil-miniature `imgIbFileThumb` | 1 | Brugerens eget billede, ikke et ikon. |
| Fejlikonet i "Opening request" `img*LoadIcon` | 5 | Hører til ventekortet, som #302 (ModernSpinner) byggede om: hjulet blev `spn…LoadIcon`, fejl-(!) blev et billede. Ikke rørt af #306. Kan byttes til `ErrorCircle` senere. |
| `imgFlClsBlock`, `imgMdRowActionsZone` | 2 | Ikke ikoner: tom trykflade/hover-zone. |

### Faner — byttet til ModernTabList@1.0.0 (#303)

Alle faner bygges af `build_helpers.tab_list`. Fanerne læser og sætter den
**samme variabel** som de knapper, de afløser: `Default` er teksten for
variablens værdi, og `OnChange` oversætter den valgte tekst tilbage og
sætter variablen kun, når den faktisk skifter. Filtrering, ruder og
genindlæsning læser variablen som før. `Appearance` er
`TabListAppearance.Underline` (stregen under den valgte fane – ikke kun en
farve), `Color` er `text-primary` (læsbar i lys og mørk tilstand). Fanerne
ruller ikke (Learn), så hver række har en kort tekst, når kortet er for
smalt til de lange. Regel 16t afviser en anden version og enhver egenskab,
Learn ikke dokumenterer for typen (fx `TabIndex`, `Fill`, `Tooltip`).

| Skærm | Før | Efter | Variabel (uændret) |
|---|---|---|---|
| IB | `conIbScope` (`btnIbScopeAll/Mine/Assigned`) | `tabIbScope` – All issues · My issues · Assigned to me (kun admin); smalt: All · Mine · Assigned | `varIbScope` = all/mine/assigned |
| IB | `conIbState` (`btnIbStateOpen/Closed/Archived`) | `tabIbState` – Open · Closed · Archived | `varIbState` = open/closed/archived |
| VHP | `conVhpOpsTabBar` (`btnVhpTabOps/Pkg`) | `tabVhpOps` – Operations · Maintenance packages (smalt: Packages); kun på en strategiplan | `varVhpOpsTab` = ops/pkg |
| Hub | `conMdFltView` (`conMdFltViewMine/Dept`) | `tabMdFltView` – My requests · All requests (kort trin: Mine · All) | `varMdView` = mine/queue |
| Hub (telefon) | `btnMdViewMineM`, `btnMdViewAllM` | `tabMdViewM` – My · All | `varMdView` = mine/queue |

Tooltips pr. knap ("Show the issues you reported" osv.) er væk: Tab list
har ingen `Tooltip` og kun én `AccessibleLabel` for hele rækken. Fanernes
tekst siger det samme.

**Bevidst beholdt** (fanerækker, der ikke kan byttes sikkert):

| Skærm | Kontrol | Grund |
|---|---|---|
| FL | `galFlTabs` (klassefaner, Gallery med `btnFlTab`) | Hver fane har klassens hjælpetekst som tooltip (FL65) – Tab list har ingen `Tooltip`. Antallet af klasser er ubegrænset, og Tab list ruller ikke; galleriet ruller vandret. Teksten har tælleren ("ALL (12)"), som ville ændre `Items` ved hver validering. Kræver en Tab list med tooltip og rulning – eller at hjælpeteksten vises et andet sted. |
| Hub | `conMdFltStatus` (Open · Closed · All) | Ikke nævnt i #303. "Closed" har sin egen tooltip, der peger på (i)-knappen ved siden af; Tab list har ingen tooltip. Kan byttes, hvis tooltippen må gå. |
| IB (sagens popup) | `conIbDetTabs` (`btnIbTabDetails/Activity/Files`) | Ikke nævnt i #303. Tæller i fanens tekst og en fane kun for rapportør/admin – Tab list kan det (som `tabIbScope`), men "Attachments" henter filerne ved klik og hører under dokumentarbejdet (#300/#323). Næste kandidat. |
| Material/Eq/MP | `conDomEditorTabs` (Details · Objects · Documents) | Ikke nævnt i #303. "Documents" åbner dokumentruden, som bygges om i #323. |
| Material/Eq/MP, VHP | `conDom*Seg`, `conVhpItemRevisionSeg`, `conVhpItemNonFlowSeg` | Ikke faner, men feltværdier (Yes/No, None/ZBOW) i en formular. Kandidat til ModernRadio/ModernToggle, ikke Tab list. |

### Gem og upload — byttet til ModernProgressBar@1.0.0 (#305)

Gem-, send- og uploadsløret viste det samme hjul som indlæsningen (til
#302 et drejende SVG, derefter ModernSpinner). En gemning eller upload kører, uden at appen kender
fremskridtet, så det er nu Learns *ubestemte* Progress bar. Sløret er det
samme Image som før (samme farve, tager stadig trykket), nu uden billede.

| Kontrol (før → efter) | Skærm | Visible (uændret) | Tekst |
|---|---|---|---|
| `imgEqSaving` (slør) → + `prgEqSaving` | Eq | `IfError(varEqSaving, false)` | — |
| `imgMatSaving` → + `prgMatSaving` | Mat | `IfError(varMatSaving, false)` | — |
| `imgMpSaving` → + `prgMpSaving` | MP | `IfError(varMpSaving, false)` | — |
| `imgFlSaving` → + `prgFlSaving` | FL | `IfError(varFlSaving, false)` | — |
| `imgVhpSaving` → + `prgVhpSaving` | VHP | `IfError(varVhpSaving, false)` | — |
| `imgIbBusy` → + `prgIbBusy` ("Sending") | IB | `IfError((varIbBusy \|\| varIbPosting) && !varIbUploading, false)` | — |
| `imgIbUploading` → + `prgIbUploading` + `txtIbUploadingCaption` | IB | `IfError(varIbUploading, false)` | "Saving files..." under bjælken (stod før som hjulets `Label`) |

Bjælken: `Indeterminate = true`, `ProgressColor.Brand`,
`ProgressThickness.Large`, `ProgressShape.Rounded`, 8 px høj,
`Min(320, App.Width - 32)` bred, midt på skærmen. `AccessibleLabel` er
slørets tekst ("Saving, please wait" osv.). Learn: kontrollen viser ingen
tekst, så billedteksten er en ModernText. Farven kan kun være en af Fluents
semantiske farver (Brand = appens brandfarve); sporets farve kan ikke
sættes. Bygger: `tools/progress_overlay.py` (`progress_overlay`,
`progress_bar`). Regel 16f afviser en anden version, en udokumenteret
egenskab og `Indeterminate` ≠ `true`; præfikset er `prg` (regel 33).

Bevidst **ikke** byttet:

| Indikator | Hvorfor |
|---|---|
| Dokumentrudernes upload (Eq, Mat, MP, VHP: statuslinjen "Working... please wait." i `tools/attflows.py`/`tools/doc_upload.py`) | Ruderne bygges om i PR #323. Følger efter #323, så de to ikke konflikter. |
| Indlæsning: `imgKksLoading`, `imgMdNavigating` ("Opening..."), kortet "Opening request" (`*LoadIcon`), `imgMdAprSpinner`, "Searching..." | Ikke gem/upload, men indlæsning/søgning: de er hjul og hører til ModernSpinner (#302). |
| `loading_overlay` i `tools/build_helpers.py` | Bruges stadig af indlæsningen ovenfor; gem/upload kalder den ikke længere. |

## Versioner og egenskaber

- Kun `ModernAttachments@1.3.0`, `ModernSpinner@1.1.0`, `ModernIcon@1.1.0`
  (#306, Learns YAML-eksempler), `ModernProgressBar@1.0.0` (#305),
  `ModernBadge@1.0.0` (#304) og `ModernTabList@1.0.0` (#303) har en
  eksplicit version i YAML'en (indtil #161 var det `Attachments@2.3.0`).
  Badge-versionen er den, Learns YAML-eksempel skriver; den er ikke set i
  Peters Studio endnu. De øvrige moderne kontroller står uden `@`-version
  (Studio vælger sin egen).
- `ModernTabList@1.0.0` (#303) er versionen i Microsoft Learns
  YAML-eksempel for den opdaterede Tab list (med `Appearance`, `Default`,
  `Alignment`, `Color`/`Size`). Den er ikke set i Peters Studio endnu.
- Ingen af de omdøbte/fjernede egenskaber fra Microsoft Learn's
  *Recent updates to modern controls* findes i appen: ingen `FontColor`,
  `FontSize`, `FontItalic`, `BorderRadius`, `Weight`, `AcceptsFocus` eller
  `TriggerOutput`. Appen bruger allerede `Color`, `Size`, `FontWeight`,
  `Radius*` og enum-værdier (`ButtonAppearance.*`, `ButtonLayout.*`,
  `Align.*`, `FontWeight.*`). Intet at opdatere.
- `ModernButton` har stadig ingen `TabIndex` (check_layout regel 10) og
  intet `Fill`.
- `ModernProgressBar@1.0.0` (#305) har eksplicit version: den, Learns
  YAML-eksempel skriver. Ikke set i Peters Studio før; giver den "Unknown
  control type", rulles #305 tilbage.

## Kandidater — kræver Peters bekræftelse først

Ingen af disse er brugt. Tjek i Studio under **Settings → Updates →
Modern controls**, at typen findes og deployer, før den tages i brug.

| Kontrol | Kunne erstatte | Bemærkning |
|---|---|---|
| ModernLink | evt. links, der i dag er knapper | |
| ModernToggle, ModernRadio | par af Primary/Outline-knapper som vælgere | |
| ModernTable (preview) | simple læselister | Preview: ikke til kritiske lister. |

## Resterende arbejde

1. Peter bekræfter, hvilke kandidater hans Studio kender.
2. Derefter, én type ad gangen: ~~spinnere → ModernSpinner~~ (#302), ~~faner →
   ModernTabList~~ (#303) og ~~`btn*FbSubject` → ModernButton~~ (#307).
3. Rækkelag, sidebar, slør, Gallery, Timer og HtmlViewer bliver, til
   Microsoft giver ModernButton en styrbar flade eller en moderne
   erstatning går GA.

Intet i denne audit er afprøvet i Power Apps Studio.

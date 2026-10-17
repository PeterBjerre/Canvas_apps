# 38 — Audit: moderne kontroller i BIO SAP App (issue #161)

Optalt i den genererede `BIO SAP App/*.pa.yaml` efter denne ændring.
Appen er allerede overvejende moderne: ModernText 673, GroupContainer 586,
ModernButton 329, ModernTextInput 72, ModernDropdown 32, ModernNumberInput
15, ModernCheckbox 8, ModernCombobox 4, ModernDatePicker 2.

Grundregel for auditten: **kun kontroltyper, som appen allerede deployer i
dag**. ModernAttachments gav "Unknown control type" i Peters Studio (#165),
så ingen nye `Modern*`-typer er indført. Ingen preview-kontrol er brugt.

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

### Image — 304

| Formål | Antal | Skærm(e) | Grund til at beholde |
|---|---|---|---|
| Sidebar og temaskift (klikbare SVG'er, lukket + åben) | 190 | alle | `tools/side_nav.py` og `theme_button` (#37): en ModernButton tegner Fluent-temaets form og kan hverken have vores egne domæneikoner (`tools/icons.py`) eller accentstregen. |
| Øvrige klikbare ikoner (hubbens fliser og "New", række-ikoner Edit/Delete/Notes/Timeline, VH-trin, hjælp, objektliste) | 27 | Hub, VHP, … | Egne domæneikoner i tokenfarver. ModernButton.Icon tager kun Fluent-ikonnavne. |
| Feedback-vælgerens ikon/chevron | 21 | alle | Del af det samme felt som `btn*FbSubject`; egne SVG'er, ikke Fluent-ikoner. |
| Dekorative/status-ikoner (sidetitel, nummerbadge, status, domæne, rail, fil-miniature) | 34 | alle | Ingen moderne ikonkontrol i appen i dag. |
| Spinnere (animeret SVG) | 12 | alle | ModernSpinner bruges ikke i appen (kandidat, se nedenfor). |
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

### Attachments — byttet til ModernAttachments@1.3.0 (#161)

| Kontrol | Antal | Brug | Status |
|---|---|---|---|
| ModernAttachments@1.3.0 | 5 (`attEqPicker`, `attMatPicker`, `attMpPicker`, `attVhpAttPicker`, `attIbFiles`) | vælg filer til upload | Byttet fra `Attachments@2.3.0`. Peters Studio (authoring 3.26101.10) kender typen og skriver `@1.3.0`. Stadig preview på Learn. Upload går uændret gennem flowene: `BioSap-TaskListAttachment` til biblioteket `TaskListDocuments` og `BioSap-IssueBoard-Submit` ("attach") til `IB_Tickets`. Regel 16b afviser den klassiske og enhver anden version. |

## Versioner og egenskaber

- Kun `ModernAttachments@1.3.0` har en eksplicit version i YAML'en (indtil
  #161 var det `Attachments@2.3.0`). De øvrige moderne kontroller står
  uden `@`-version (Studio vælger sin egen).
- Ingen af de omdøbte/fjernede egenskaber fra Microsoft Learn's
  *Recent updates to modern controls* findes i appen: ingen `FontColor`,
  `FontSize`, `FontItalic`, `BorderRadius`, `Weight`, `AcceptsFocus` eller
  `TriggerOutput`. Appen bruger allerede `Color`, `Size`, `FontWeight`,
  `Radius*` og enum-værdier (`ButtonAppearance.*`, `ButtonLayout.*`,
  `Align.*`, `FontWeight.*`). Intet at opdatere.
- `ModernButton` har stadig ingen `TabIndex` (check_layout regel 10) og
  intet `Fill`.

## Kandidater — kræver Peters bekræftelse først

Ingen af disse er brugt. Tjek i Studio under **Settings → Updates →
Modern controls**, at typen findes og deployer, før den tages i brug.

| Kontrol | Kunne erstatte | Bemærkning |
|---|---|---|
| ModernSpinner | 12 Image-spinnere | GA ifølge Learn. Mister vores tokenfarver, hvis den ikke kan farves. |
| ModernIcon | 34 dekorative ikoner | Kun Fluent-ikoner; domæneikonerne (`tools/icons.py`) findes ikke der. |
| ModernBadge | nummer- og statusbadges (i dag ModernText/Image) | |
| ModernTabList | faner (`galFlTabs`, VHP's ops/pkg-knapper, IB's scope/state) | |
| ModernProgressBar | "Saving"/"Uploading"-billeder | |
| ModernLink | evt. links, der i dag er knapper | |
| ModernToggle, ModernRadio | par af Primary/Outline-knapper som vælgere | |
| ModernTable (preview) | simple læselister | Preview: ikke til kritiske lister. |

## Resterende arbejde

1. Peter bekræfter, hvilke kandidater hans Studio kender.
2. Derefter, én type ad gangen: spinnere → ModernSpinner, faner →
   ModernTabList (`btn*FbSubject` → ModernButton er gjort i #307).
3. Rækkelag, sidebar, slør, Gallery, Timer og HtmlViewer bliver, til
   Microsoft giver ModernButton en styrbar flade eller en moderne
   erstatning går GA.

Intet i denne audit er afprøvet i Power Apps Studio.

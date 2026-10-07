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

### Classic/Button — 25 (var 26)

| Formål | Antal | Skærm(e) | Kontroller | Grund til at beholde |
|---|---|---|---|---|
| Klik-lag over en hel række (`row_hit`) | 16 | alle | `btn*FbSubjectPick` (7), `btnIbRowOpen`, `btnIbSimOpen`, `btnKksRowHit`, `btnKksPickHit`, `btnMdRowHit`, `btnMdPeekOpen`, `btnMdAprExpand`, `btnVhpItemOpen`, `btnVhpOpMHit` | Gennemsigtigt lag med `HoverFill`/`PressedFill` i tokens (row-hover/row-pressed). ModernButton har intet `Fill`, `HoverFill` eller `PressedFill`; Fluent-temaets egen hover-flade ville dække rækken. |
| Feedback-vælgerens "dropdown"-felt | 7 | alle | `btn*FbSubject` | Venstrestillet tekst uden indre luft, gennemsigtig i alle tilstande, så teksten flugter med listen under (#140). ModernButton har ingen hover-/tryk-farver, vi kan sætte, og `Padding*` er kun dokumenteret for den *opdaterede* knap — ikke afprøvet i Peters Studio. |
| Godkendelses-chevron i hubbens række | 1 | Hub | `btnMdRowApproval` | Pilleformet trykzone med `HoverFill`/`PressedFill` og højrestillet "›". Samme grund som rækkelaget. |
| "Nogle valgt – vælg alle" i operationsvælgeren | 1 | VHP | `btnVhpPickerHeadPartial` | 18 × 18 px felt i primærfarven med "−". ModernCheckbox har ingen delvis tilstand, og den mindste ModernButton i appen er 30 px; Fluent-knappens min.-bredde/indre luft ved 18 px er ikke afprøvet. |

Alle har `TabIndex = 0` og læses via `Text`/`Tooltip` (Classic/Button har
ingen `AccessibleLabel`), jf. #168.

Bemærk: rækkelaget er en *klassisk* kontrol **oven på** moderne tekster,
ikke en klassisk kontrol skjult under en falsk moderne flade. Det er det,
issuet forbyder.

### Image — 304

| Formål | Antal | Skærm(e) | Grund til at beholde |
|---|---|---|---|
| Sidebar og temaskift (klikbare SVG'er, lukket + åben) | 190 | alle | `tools/side_nav.py` og `theme_button` (#37): en ModernButton tegner Fluent-temaets form og kan hverken have vores egne domæneikoner (`tools/icons.py`) eller accentstregen. |
| Øvrige klikbare ikoner (hubbens fliser og "New", række-ikoner Edit/Delete/Notes/Timeline, VH-trin, hjælp, objektliste) | 27 | Hub, VHP, … | Egne domæneikoner i tokenfarver. ModernButton.Icon tager kun Fluent-ikonnavne. |
| Feedback-vælgerens ikon/chevron | 21 | alle | Del af det samme felt som `btn*FbSubject`. |
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

### Gallery — 41 · Timer — 9 · HtmlViewer — 8 · Attachments@2.3.0 — 5

| Kontrol | Antal | Brug | Grund |
|---|---|---|---|
| Gallery | 41 (Eq 3, FL 5, IB 5, KKS 6, Mat 3, Hub 4, VHP 15) | lister, tabeller, faner, hjælp | Ingen GA-erstatning. ModernTable er preview og kan ikke det, galleriernes skabeloner gør (knapper, input og egne celler pr. række). |
| Timer | 9 (Eq 2, FL 1, KKS 2, Mat 2, VHP 2) | forsinket søgning, "loader langsomt"-besked | Ingen moderne Timer. |
| HtmlViewer | 8 (FL 1, VHP 7) | tabeloverskrifter, summer, FL-struktur | Ingen moderne erstatning. |
| Attachments@2.3.0 | 5 (Eq, IB 2, Mat, VHP) | vedhæftninger | ModernAttachments er preview og ukendt i Peters Studio (#165); byggeriet afviser den (regel 16b). |

## Versioner og egenskaber

- Kun `Attachments@2.3.0` har en eksplicit version i YAML'en. De moderne
  kontroller står uden `@`-version (Studio vælger sin egen); intet er
  ændret her.
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
| ModernAttachments (preview) | Attachments@2.3.0 | Gav "Unknown control type" (#165). |
| Opdateret ModernButton med `Padding*` og `BorderStyle` | `btn*FbSubject`, `btnVhpPickerHeadPartial` | Dokumenteret på Learn, men ikke brugt i appen; afprøv i Studio først. Rækkelagene kræver stadig `HoverFill`/`PressedFill`. |

## Resterende arbejde

1. Peter bekræfter, hvilke kandidater hans Studio kender.
2. Derefter, én type ad gangen: spinnere → ModernSpinner, faner →
   ModernTabList, og evt. `btn*FbSubject` → ModernButton med `Padding*`.
3. Rækkelag, sidebar, slør, Gallery, Timer og HtmlViewer bliver, til
   Microsoft giver ModernButton en styrbar flade eller en moderne
   erstatning går GA.

Intet i denne audit er afprøvet i Power Apps Studio.

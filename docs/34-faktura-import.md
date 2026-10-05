# 34 — Fakturaimport i Materials

Brugeren lægger en leverandørfaktura op i Materials. Fakturaens linjer bliver
til **kladderækker i en ny anmodning**, og brugeren udfylder det, en faktura
ikke kan vide: funktionsplads (eller No BOM Item), værk, lager, sliddel.
Derefter gemmes og indsendes rækkerne som altid.

Der bruges **ingen premium-connectors** — hverken i appen eller i flowet.

| Del | Hvor | Licens |
|---|---|---|
| Knappen og popuppen | BIO SAP App, skærmen Materials | Som i dag |
| Flowet `BioSap-Material-ReadInvoice` | Solution BIO SAP | Power Apps-udløser + Excel Online (Business) + Office 365 Outlook — alle **standard** |
| Fakturalæseren | Office Script [`flow/invoice-import/ReadInvoice.ts`](../flow/invoice-import/ReadInvoice.ts) | Microsoft 365-licens med Office Scripts (E3/E5 o.l.) |
| Rækkerne og anmodningen | `MaterialItems`, `MD_RequestIndex` | SharePoint, som i dag |

## Hvorfor et Office Script

Power Automate kan ikke selv læse en PDF. Der er ingen standardhandling, der
pakker en PDF-strøm ud eller finder dens tekst. AI Builders fakturamodel kan,
men **AI Builder er premium**: Microsoft skriver selv, at et flow med en AI
Builder-handling er et premium-flow og kræver Power Automate Premium
([AI Builder-licensering](https://learn.microsoft.com/ai-builder/administer-licensing)).
Det samme gælder HTTP, Azure Document Intelligence og alle tredjeparts
PDF-connectors.

**Excel Online (Business) er en standard-connector**, og dens handling *Run
script from SharePoint library* kører et Office Script — TypeScript, der
kører hos Microsoft. Læseren er skrevet som sådan et script: den pakker PDF'en
ud (FlateDecode m.fl.), læser teksten gennem skrifttypernes tegntabeller,
finder tabellen under kolonneoverskrifterne og regner hver linje efter.

Konsekvensen er grænsen nedenfor: et script kan læse tekst, ikke billeder.

## Hvad læseren kan — og ikke kan

| Faktura | Resultat |
|---|---|
| **PDF fra et økonomisystem** (e-conomic, Business Central, SAP, Word, Excel, …) | Linjerne findes ud fra kolonneoverskrifterne. Dansk, norsk, engelsk og tysk: *Varenr., Beskrivelse, Antal, Enhed, Enhedspris, Rabat %, Beløb* og deres pendanter |
| **OIOUBL- eller Peppol-XML** (NemHandel, e-faktura) | Præcis: hvert felt har sin plads. Også producentens varenummer, mærke, GTIN og prisenhed |
| PDF uden kolonneoverskrift | Reserve: linjer, der ender på *antal, pris, beløb*, og hvor antal × pris = beløb |
| **Scannet PDF** (et billede) | Ingen linjer — og en besked om, at den kun kan læses med OCR (AI Builder, premium) |
| Krypteret/beskyttet PDF | Ingen linjer — beskeden beder om en ubeskyttet PDF |

Er der en XML-udgave af fakturaen, så brug den. Den er altid mere præcis end
PDF'en.

Læseren gætter ikke stille. Hver linje regnes efter (`check`), linjernes sum
holdes op mod fakturaens subtotal, og det, der ikke passer, står som en
advarsel i popuppen. Fragt, gebyrer, rabatter og kreditnotaer kommer med i
listen, men er **ikke valgt**.

Afprøvet på otte PDF'er fra fire forskellige PDF-generatorer og tre XML-filer
— se [Testfakturaerne](#testfakturaerne). Det er syntetiske fakturaer; prøv
jeres egne leverandørers, før det tages i brug (testplanen nedenfor).

## Brugerens gang

1. **Materials → Import invoice** (knappen i formularens hoved).
2. Træk fakturaen ind, eller vælg den (PDF eller XML, højst 3 MB).
3. **Read invoice.** Ventehjulet kører, mens flowet læser. Det meste af
   ventetiden går med at starte Excel-sessionen; selve læsningen tager
   millisekunder.
4. Popuppen viser leverandør, fakturanummer, dato, ordrenummer, valuta og —
   hvis leveringsadressen nævner et af værkerne — værket. Under det
   linjerne med et flueben hver.
5. Fjern fluebenet fra det, der ikke er reservedele. **Create request.**
6. Der oprettes en **ny anmodning** (`MAT-000123`, status *Kladde* på
   landingssiden) med én **kladderække** pr. valgt linje. Fakturaen lægges
   som dokument på hver række, medmindre fluebenet *Attach the invoice …* er
   fjernet.
7. Åbn hver række (**Edit**), udfyld det, der mangler, og **Save row**. Så
   er rækken *valid*.
8. **Submit saved rows**, som altid.

## Hvad fakturaen udfylder

| Kolonne i `MaterialItems` | Fra fakturaen |
|---|---|
| `MaterialDescription` | Linjens tekst, de første 40 tegn (formularens grænse) |
| `Supplier` | Leverandørens navn |
| `SupplierPartNo` | Leverandørens varenummer |
| `Manufacturer` | Producent/mærke — kun hvis fakturaen har det (XML, eller en kolonne/linje *Fabrikat:*) |
| `ManufacturerPartNo` | Producentens varenummer — samme forbehold |
| `ModelNumber` | Model (XML) |
| `Price` | Enhedsprisen **i fakturaens valuta** (valutaen står i langteksten) |
| `PriceUnit` | Prisenheden, når prisen gælder fx pr. 100 stk. |
| `StockUnit` | Enheden, som den står på fakturaen (`STK`, `PC`, `M` …) |
| `Plant` | Værket, hvis leveringsadressen nævner *Studstrupværket*, *Herningværket* osv. Kun værkernes navne — ikke bynavne, for en leverandør kan sagtens ligge i Herning |
| `LongText` | Hvor rækken kommer fra: faktura, dato, leverandør, ordre, antal × pris = beløb, GTIN og den fulde tekst |
| `RowStatus` | `draft` |

**Brugeren udfylder:** `FunctionalLocation` (eller No BOM Item),
`DeliveringTime`, `RecommendedStock`, `StrategicPart`, `WearPart` — og
værket, hvis det ikke blev fundet. Det er `USER_FILLS` i
[`invoice_parts.py`](../Material%20App/build/invoice_parts.py). Kommer der et
nyt felt i `SECTIONS`, stopper byggeriet, indtil det står i enten
`FROM_INVOICE` eller `USER_FILLS`.

## Opsætning

Rækkefølgen betyder noget: appen kan ikke kompilere, før flowet findes som
datakilde, og flowet kan ikke vælge scriptet, før det ligger i SharePoint.

### 1. Office Scripts er slået til

Det er de som standard. Indstillingerne styres siden oktober 2025 i
**Microsoft 365 Cloud Policy service**, ikke længere i admin center
([Manage Office Scripts settings](https://learn.microsoft.com/microsoft-365/admin/manage/manage-office-scripts-settings)).
Spørg jeres Office Apps-administrator, om de to er ændret:

- [ ] *Let users automate their tasks in Excel*
- [ ] *Let users with access to Office Scripts run their scripts with Power Automate*

Er de begrænset til en gruppe, skal alle, der bruger Materials, være i den:
flowet kører scriptet **som brugeren selv** (se trin 3).

### 2. Scriptet og projektmappen i BIO SAP-sitet

Scriptet skal have en projektmappe at køre i, selv om det ikke rører den.

1. Opret mappen **InvoiceReader** i sitets **Documents** (Shared Documents).
2. Læg en tom projektmappe derind: **InvoiceReader.xlsx**. Brugerne skal have
   **redigeringsadgang** til den — det kræver Excel-connectoren af alle
   handlinger. Sitets medlemmer har det i forvejen.
3. Åbn `InvoiceReader.xlsx` i Excel på nettet → **Automate → New script →
   Create in Code Editor**.
4. Slet indholdet, og indsæt hele
   [`flow/invoice-import/ReadInvoice.ts`](../flow/invoice-import/ReadInvoice.ts)
   (knap 4.000 linjer — alt ligger inden i `main`, fordi Office Scripts kun
   kører `main`). Filen er ren ASCII, så den kan kopieres direkte fra GitHub.
5. Kald scriptet **ReadInvoice**, og gem.
6. Flyt det til SharePoint: klik på scriptets navn (som for at omdøbe det) →
   **Move** → vælg mappen **InvoiceReader**. Nu ligger
   `ReadInvoice.osts` ved siden af projektmappen og ejes af sitet, ikke af
   en person.

> **Ændres scriptet senere,** så ret i `ReadInvoice.ts` i repoet, kør
> `python3 tools/build_all.py`, og indsæt den nye udgave i Excel. Flowet
> skal ikke røres, så længe `main`'s parametre er de samme.

### 3. Flowet `BioSap-Material-ReadInvoice`

I solution **BIO SAP** → **New → Automation → Cloud flow → Instant**.

**Udløser:** *When Power Apps calls a flow (V2)* med to input:

| Input | Type | Navn | Krævet |
|---|---|---|---|
| 1 | Text | `FileName` | ja |
| 2 | File | `Invoice` | **nej** — `…` → *Make the field optional* |

Filen **skal** være valgfri. Appen kalder flowet som
`'BioSap-Material-ReadInvoice'.Run(navn, { file: … })`, præcis som
`BioSap-TaskListAttachment`. Er filen krævet, forventer Power Apps den som
andet argument for sig, og appen kompilerer ikke.

**Handlinger** — samme Try/Catch/Finally som de andre BioSap-flows:

1. **Initialize variable** `FlowRunHistoryLink` — kopiér den fra
   `BioSap-TaskListAttachment`.
2. **Scope `Try`**
   1. **Excel Online (Business) → Run script from SharePoint library**

      | Felt | Værdi |
      |---|---|
      | Workbook Location | BIO SAP-sitet |
      | Workbook Library | Documents |
      | Workbook | `/InvoiceReader/InvoiceReader.xlsx` |
      | Script Location | BIO SAP-sitet |
      | Script Library | Documents |
      | Script | `/InvoiceReader/ReadInvoice.osts` |
      | fileName | `triggerBody()?['text']` |
      | fileContent | `triggerBody()?['file']?['contentBytes']` |

   2. **Respond to a Power App or flow** — én Text-output, **`Result`**:

      ```
      outputs('Run_script_from_SharePoint_library')?['body/result']
      ```

      Power Apps ser den som `.result` (små bogstaver). Svaret er en
      JSON-**streng**; appen læser den med `ParseJSON`, som FL-søgningen.
3. **Scope `Catch`** — *Configure run after*: `Try` *has failed, is skipped,
   has timed out*.
   1. **Respond to a Power App or flow** — den **samme** Text-output
      `Result`, med værdien:

      ```
      {"ok":false,"error":"The invoice reader failed. The developers have been notified.","warnings":[],"lines":[]}
      ```

      Uden den får brugeren kun "flowet fejlede" — og ventehjulet står,
      til Power Apps giver op.
   2. **Convert time zone** og **Send an email (V2)** til
      `BioSap-ErrorNotifiers` — kopiér dem fra et af de andre flows.
4. **Scope `Finally`** — tom, som i de andre flows.

**Forbindelser:** Lav en connection reference til Excel Online (Business),
fx `orsted_BioSapExcelConn`. Under flowets **Run only users** sættes både
Excel og Outlook til **Provided by run-only user** — som de andre
BioSap-flows. Så kører scriptet som brugeren, og grænserne nedenfor gælder
pr. bruger. Næste gang brugerne åbner appen, beder den dem godkende
Excel-forbindelsen (samme dialog som for SharePoint og Outlook).

**DLP:** Har miljøet en datapolitik, skal Excel Online (Business) stå i
samme gruppe som Office 365 Outlook (typisk *Business*). Ellers kan flowet
ikke gemmes.

### 4. Appen

1. Åbn BIO SAP App i Studio → **Data → Add data → Power Automate** → tilføj
   **BioSap-Material-ReadInvoice**. **Gem** (Ctrl+S) — at tilføje flowet er
   ikke nok (se `tools/build_flsearch.py`).
2. Deploy, som altid:

   ```powershell
   python tools\canvas_mcp.py deploy --app biosap
   ```

   Knappen og popuppen er nye kontroller; ingen eksisterende kontrol er
   flyttet, så `--clean` burde ikke være nødvendig. Stopper deploy alligevel
   med *Studio har IKKE det byggede træ*, så kør den igen med `--clean`.

`BioSap-TaskListAttachment` (dokumentet på rækkerne) er datakilde i
forvejen.

## Testplan

1. **XML:** Importér en OIOUBL-faktura. Linjerne, leverandøren, nummer og
   dato står rigtigt; *Create request* giver en ny anmodning på
   landingssiden med status *Kladde* og én række pr. valgt linje.
2. **PDF:** Importér en PDF fra en af jeres faste leverandører. Tjek
   beskrivelse, varenummer, antal, enhed og pris mod PDF'en.
3. **Gebyr:** En faktura med fragt — fragtlinjen står i listen uden flueben.
4. **Scanning:** Importér en scannet faktura — beskeden siger, at den ikke har
   tekst, og popuppen bliver på første trin.
5. **Rækkerne:** Åbn en importeret række. Den er `DRAFT`; *Save row* uden
   funktionsplads siger, hvad der mangler; med funktionsplads og værk bliver
   den `VALID`.
6. **Dokumentet:** Rækkens **Docs** viser fakturaen.
7. **Indsend:** *Submit saved rows* → anmodningen bliver *Indsendt*.
8. **Fejl:** Slå flowet fra, og tryk *Read invoice* — popuppen siger, at
   fakturaen ikke kunne læses; appen hænger ikke.

## Grænser

| Grænse | Værdi | Kilde |
|---|---|---|
| Kørsler af *Run script* | 1.600 pr. bruger pr. døgn, højst 3 pr. 10 sek. | [Excel Online (Business)](https://learn.microsoft.com/connectors/excelonlinebusiness/) |
| Svartid | 120 sekunder pr. kørsel. Læseren selv bruger under 0,1 s på testfakturaerne | [Office Scripts-grænser](https://learn.microsoft.com/office/dev/scripts/testing/platform-limits) |
| Filstørrelse | 3 MB i appen. Connectoren tager 5 MB pr. kald, og filen fylder en tredjedel mere som base64 | Samme |
| Fakturaens layout | Kolonneoverskrifter på dansk, norsk, engelsk eller tysk. Et ukendt ord er én linje i `COLUMN_WORDS` i scriptet | — |

## Vedligehold

**Kontrakten står to steder, og de holdes sammen af byggeriet.** Scriptets
svar er `InvoiceLine`/`InvoiceResult` i `ReadInvoice.ts`; appens læsning er
`CONTRACT_LINE`/`CONTRACT_RESULT` i `invoice_parts.py`.
`tools/invoice/harness.mjs` stopper byggeriet, hvis de to lister ikke er ens
— et omdøbt felt ville ellers give tomme felter i appen uden en eneste fejl.

**Testfakturaerne.** `python3 tools/build_all.py` kører scriptet — den
uændrede `.ts`-fil — på alle filer i `tools/invoice/fixtures/` og holder
svaret op mod `tools/invoice/expected.json`. Kræver Node 22.13+.

```bash
node tools/invoice/harness.mjs dump da_reportlab.pdf   # hvad læseren får ud af en fil
TEXT=1 node tools/invoice/harness.mjs dump x.pdf        # også den læste tekst
```

En faktura, læseren ikke klarer: læg en **anonymiseret** udgave i
`fixtures/`, skriv det rigtige svar i `expected.json`, og ret scriptet, til
testen er grøn. Byggeriet melder en fixture uden forventning.

`tools/invoice/make_fixtures.py` laver de syntetiske PDF'er igen (kræver
reportlab, fpdf2, pikepdf og Chromium — ikke en del af `requirements.txt`).

### Testfakturaerne

| Fil | Hvad den afprøver |
|---|---|
| `da_reportlab.pdf` | Standardskrift (Helvetica, WinAnsi), rabatkolonne, fortsættelseslinjer med *Producent varenr.* og *Fabrikat*, fragtlinje |
| `da_objstm.pdf` | Samme faktura med objektstrømme og xref-strøm (PDF 1.5) |
| `en_chrome.pdf` | Chromium: indlejrede Type0-skrifter, 70 linjer over to sider med gentaget tabelhoved, engelske tal |
| `de_truetype.pdf` | TrueType-delmængde med egen kodning, tysk layout, `€` i cellerne, *Pos.*-kolonne |
| `da_fpdf_unicode.pdf` | Unicode-skrift (Identity-H), "2 stk" i én celle, æøå |
| `da_courier_loose.pdf` | Courier uden kolonneoverskrift — reservelæsningen |
| `no_twoline.pdf` | Norsk: varen på to linjer (tekst over tallene), "1 245,00" med mellemrum, leverandør uden A/S |
| `scanned.pdf` | Kun et billede — skal give beskeden om OCR, ikke et gæt |
| `oioubl_latin1.xml` | OIOUBL 2.02 i ISO-8859-1, prisenhed pr. 100, indlejret bilag |
| `peppol.xml` | Peppol BIS 3, GTIN, fragtlinje |
| `peppol_creditnote.xml` | Kreditnota — linjerne er ikke valgt |

## Hvis scanninger bliver almindelige

Så er AI Builders fakturamodel vejen — og det er premium. Kontrakten gør
skiftet lille: byt *Run script* ud med *Extract information from invoices*,
og byg det samme JSON-svar med en **Select**-handling. Appen ændres ikke, for
den kender kun svaret, ikke læseren.

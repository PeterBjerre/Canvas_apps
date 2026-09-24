# 31 – Functional Location: regelinventaret

Kontrakten for canvas-appen **Functional Location App**. Hver regel, der
står i `html/functional-location.html` og de scripts, siden indlæser, har et
ID her (FL1 …). Appen må ikke have en regel, der ikke står her, og en regel
her uden en implementering er en fejl.

## Kilden

`functional-location.html` er kun markup: en tabel (#, Functional Location,
Description, KKS Type, Assigned Class, Validation, Action), knapperne
**Verify**, **Export JSON**, **Add row** og et kort med klassefaner. Alle
regler står i de scripts, siden indlæser:

| Fil (i `html/`) | Indhold | Brugt som |
|---|---|---|
| `app-functional-location.js` | Controlleren: rækkevalidering, spool-felter pr. klasse, TRM-automatik, klassefaner, eksport | **Regelkilde** |
| `fl-rule-engine.js` | KKS-syntaks (12 mønstre) og klassebestemmelse (nøgler 0/7/12/17/18, BR18) | **Regelkilde** |
| `text-utils.js` | `toText` (trimmer), `normalizeUpper` | **Regelkilde** |
| `lookups.generated.js` | `FL_LOOKUPS`: 23 tabeller fra SPOOL-arket, bl.a. `Char`, `SCEq`, `Plant`, `FunctionKeyDict` (6.445), `ClassDetermination*Key`, `BR18_Keys` og værdilisterne | **Data** |
| `fl-classification-data.js` | `FL_CLASSIFICATION_DATA` - overskrives helt af `FL_LOOKUPS` i `applyLookupOverrides` (`fl-rule-engine.js:264`) | Ingen virkning |
| `fl-spool-columns.js` | `FL_SPOOL_COLUMNS`: kolonnerne pr. klasse | **Data** |
| `shell.js`, `functional-location-extract.html` | Navigation / en anden side (masseudtræk) | Ikke i omfang, se AQ3 |

VBA'en i `excel/vba/spool-validation/` er den oprindelige kilde, som JS'en er
en port af. **Hvor de to er uenige, vinder JS'en** - det er den, opgaven
siger skal bevares. Uenighederne står i afsnittet *Afvigelser mellem JS og
VBA* nederst, så de ikke går tabt.

## Hvordan reglerne er efterprøvet

Reglerne er ikke skrevet af. `tools/fl/harness.js` kører de **uændrede**
filer i Node. Controllerens IIFE bliver skåret op, så dens interne funktioner
kan kaldes, men selve kroppen ændres ikke. Harnessen har tre kommandoer:

```bash
node tools/fl/harness.js plan   # -> Functional Location App/build/fl_rules.generated.json
node tools/fl/harness.js seed   # -> sharepoint/seed/MD_FLKey.csv (fra FL_LOOKUPS)
node tools/fl/harness.js test   # testmatrixen + differentialtest
```

`plan` folder `validateSpoolFields` ud til en **flad, ordnet tjekliste pr.
klasse**: 541 tjek i 17 klasser. Det er den liste, Power Fx'en evaluerer.
`test` gør tre ting:

1. Den kører testmatrixen (nedenfor, 108 sager) gennem **originalen** og
   sammenligner med det forventede.
2. Den kører samme sager gennem den **flade evaluator**, som er en
   linje-for-linje-model af appens Power Fx, og kræver ordret samme
   beskeder, samme rækkefølge, samme status og samme klasse.
3. Den genererer 4.000 tilfældige rækkesæt (1-4 rækker, muterede FL'er og
   tilfældige feltværdier) og kræver 0 afvigelser mellem original og flad
   evaluator.

`tools/build_all.py` kører `test`, når Node findes. Er planen gået ud af
trit med `html/*.js`, stopper byggeriet.

## Regeltabellen

Alvor: **Fejl** blokerer ("Error not ready for SAP"), **Advarsel** gør
rækken gul men blokerer ikke, **Afledt** er en beregnet værdi eller en
UI-regel uden besked.

Filer i "Implementeret i" er under `Functional Location App/build/`.

### Rækken (Validation-tabellen)

| ID | Regel | Kilde | Besked (ordret) | Alvor | Power Fx | Implementeret i |
|---|---|---|---|---|---|---|
| FL1 | FL normaliseres: NBSP→mellemrum, CR/LF fjernes, VERSALER, trim | `app-functional-location.js:2368`, `fl-rule-engine.js:395` | – | Afledt | `inpFlRowFl.OnChange`: `Upper(Trim(Substitute(Substitute(Substitute(Self.Text, Char(160), " "), Char(13), ""), Char(10), "")))` | `fl_parts.py` `norm_fl` → `inpFlRowFl`, `inpFlCFl` |
| FL2 | FL og Description højst 40 tegn i inputfeltet | `:1508`, `:1511` (`maxlength="40"`) | – | Afledt | `MaxLength: 40` | `fl_parts.py` `inpFlRowFl`, `inpFlRowDesc` (`max_length=40`) |
| FL3 | Tom række (FL og Description tomme efter trim) er *Draft*: valideres ikke, kommer ikke i klassefanerne, gemmes ikke | `:1076-1083`, `:1479`, `:2278` | – | Afledt | `IsBlank` i `colFlCalc`; `Status = "draft"`; filtreret fra i gem | `fl_validation.py` `calc_rows` (`blankRow`), `STATUS`; `fl_save.py` `save_fx` (kun `Status <> "draft"`) |
| FL4 | FL mangler (Description udfyldt) | `:1085-1087` | `FL required.` | Fejl | Rækkebesked Ord 1 | `fl_validation.py` `ROW_MSGS` → `MFlReq` i `calc_rows` |
| FL5 | FL dublet - ALLE rækker med samme normaliserede FL | `:1047-1057`, `:1089-1091` | `Duplicate FL.` | Fejl | `CountRows(Filter(colFlRows, FL = fl)) > 1`, Ord 2 | `fl_validation.py` `MDup` i `calc_rows` |
| FL6 | Description mangler | `:1093-1095` | `Description required before Ready for SAP.` | Fejl | Ord 3 | `fl_validation.py` `MDescReq` i `calc_rows` |
| FL7 | Description over 40 tegn | `:1097-1099` | `Description > 40.` | Fejl | Ord 4 | `fl_validation.py` `MDescLen` i `calc_rows` |
| FL8 | KKS-syntaks: FL skal matche et af 12 mønstre. KKS-type: `KKSKV` (mønster 11-12), `KKSKA` (10), ellers `KKS`; de tre giver syntaksklassen `KAB` | `fl-rule-engine.js:6-19, 55-99` | – | Afledt | 12 × `IsMatch` med konstante mønstre | `fl_validation.py` `calc_rows` (`ok`, `kv`, `ka`, `KksType`); mønstrene i `fl_rules.generated.json` `patterns` |
| FL9 | Legacy-nummerering (`…[-A-Z]{2}\d{1,3}$`) uden gyldigt mønster: KKS-type `KKS` | `fl-rule-engine.js:21, 66-72` | `Legacy format.` | Advarsel | `IsMatch(fl, LEGACY)` → advarsel | `fl_validation.py` `calc_rows` (`legacy`), `issues_raw` (Warning, FL9) |
| FL10 | Intet mønster og ikke legacy | `fl-rule-engine.js:74-78` | `KKS invalid.` | Fejl | Ord 5 | `fl_validation.py` `MKks` i `calc_rows` |
| FL11 | Pos. 1-3 skal være et værk i `Plant` (AVV, ASV, HEV, KYV, SKV, SSV, HCV, SMV) | `fl-rule-engine.js:126-128, 267-270` | `Plant key invalid.` | Fejl | `in nfFlPlants.Key`, Ord 7 | `fl_validation.py` `MPlant`; `generate_app_onstart.py` `nfFlPlants` |
| FL12 | Pos. 7-9 skal findes i `FunctionKeyDict` - **kun hvis ordbogen ikke er tom** | `fl-rule-engine.js:130-132` | `Function key invalid.` | Fejl | `exactin` i navngiven formel med alle 6.441 nøgler (PX5); sprunget over når `nfFlHasFunctionKeys` er falsk, Ord 8 | `fl_validation.py` `fk_hit`, `MFunc`; `generate_app_onstart.py` `nfFlFunctionKeys`, `nfFlHasFunctionKeys` |
| FL13 | Aggregat (pos. 12-13) `UF`/`UE`: funktionsnøglen skal starte med `U` | `fl-rule-engine.js:243-249` | `UF/UE requires U function key.` | Fejl | Ord 9 | `fl_validation.py` `MU` i `calc_rows` |
| FL14 | `UF`/`UE` uden BR18-regelsæt | `:251-255` | `BR18 rules missing for <key12>.` | Fejl | `IsBlank(LookUp(nfFlBr18, Key12 = k12))`, Ord 10 | `fl_validation.py` `MBrMiss`; `generate_app_onstart.py` `nfFlBr18` |
| FL15 | Pos. 17-18 skal være tilladt for aggregatet (`UE`: FP/FD/FG/FH, `UF`: D/G/H) | `:257-259` | `BR18 key17 invalid for <key12>.` | Fejl | Ord 11 | `fl_validation.py` `MBrK17` i `calc_rows` |
| FL16 | Syntaksklasse `KAB` giver klassen `KAB` - nøgle 12/18 tjekkes ikke | `fl-rule-engine.js:138-142` | – | Afledt | Første gren i `cls` | `fl_validation.py` `calc_rows` (`synKab` → `"KAB"`) |
| FL17 | Pos. 18-19 har to tegn: både komponent (`ClassDeterminationComponentKey`) og aggregat skal findes; klassen er komponentens | `:144-155, 167-198` | `Component key invalid.` / `Equipment key invalid.` | Fejl | `nfFlComponent`, `nfFlAggregate`, Ord 12-13 | `fl_validation.py` `MComp`, `MEq18`, `p18`; `generate_app_onstart.py` `nfFlComponent` |
| FL18 | Ellers: aggregatet giver klassen | `:209-213` | – | Afledt | `LookUp(nfFlAggregate, Key = k12).Cls` | `fl_validation.py` `calc_rows` (`agg.Cls`); `generate_app_onstart.py` `nfFlAggregate` |
| FL19 | Ellers: MKP-/FP-mønster uden kendt aggregat | `:215-218` | `Equipment key invalid.` | Fejl | Ord 14 | `fl_validation.py` `MEq12`, `isMkp` |
| FL20 | Ellers: fem korte mønstre → `NO CLASS` | `:220-225` | – | Afledt | 5 × `IsMatch` | `fl_validation.py` `calc_rows` (`isShort` → `"NO CLASS"`) |
| FL21 | Ellers: `[A-B][A-Z]{2}\d{2}`-mønstret → `ELF` | `:227-231` | – | Afledt | `IsMatch` | `fl_validation.py` `calc_rows` (`isElf` → `"ELF"`) |
| FL22 | Ellers ingen klasse | `:233` | `Class not determined.` | Fejl | Ord 15 | `fl_validation.py` `MNoCls` i `calc_rows` |
| FL23 | Ingen klasse og ingen fejl → `NO CLASS` | `app-functional-location.js:1115-1118` | – | Afledt | `If(cls = "" && CountRows(msgs) = 0, "NO CLASS", cls)` | `fl_validation.py` `calc_rows` (`cls2`) |
| FL24 | Regeldata ikke indlæst | `fl-rule-engine.js:115-118` | `Rules data missing.` | Fejl | `nfFlRulesLoaded` (planen findes), Ord 6 | `fl_validation.py` `MRules`; `generate_app_onstart.py` `nfFlRulesLoaded` |
| FL25 | Status: `invalid` ved fejl, `warning` ved advarsler, ellers `valid`. SAP-status `Error not ready for SAP` / `Ready for SAP` / `Draft` | `:1129-1135`, `:2199-2203` | – | Afledt | `Status` i `colFlRows` | `fl_validation.py` `STATUS`; `fl_parts.py` `txtFlRowIssue`, `_status_color`; `fl_save.py` `SUBMIT_WHY` |
| FL26 | Valideringskolonnen viser første fejl, ellers første advarsel; statuschippen skjules ved en fejl | `:1547-1571` | – | Afledt | `FirstIssue`/`FirstWarning` | `fl_parts.py` `txtFlRowIssue` |
| FL27 | Hjælpetekst pr. besked (nøglens position og værdi) | `:1573-1630` | Ordret, fx `Function key is FL position 7-9 (<key7>). It must exist in FunctionKeyDict lookup.` | Afledt | `Tooltip` på `txtFlRowIssue` | `fl_validation.py` `hint_fx`; `fl_parts.py` `btnFlRowHint` (Tooltip) |
| FL28 | Klassefaner: rækker, der ikke er draft og har en klasse. `ALL (n)` + én fane pr. klasse, alfabetisk; rækker sorteret på FL; klasse-hjælpetekst som tooltip | `:1475-1495`, `:1632-1665`, `:2353-2357` | – | Afledt | `galFlTabs`, `galFlClassRows` | `fl_validation.py` `BUCKETS`, `TABS`; `fl_parts.py` `galFlTabs`, `galFlClassRows`, `VIEW_POS` |
| FL29 | Feltmarkering: FL rødt ved en besked med FL/KKS/Plant/Function/Component/Equipment/BR18/Class; Description ved "Description" | `:2284-2318` | – | Afledt | `BorderColor` på de to inputs | `fl_validation.py` `fl_bad`, `desc_bad`, `is_fl_issue` (exactin); `fl_parts.py` `_field_border` |

### Spool-felterne pr. klasse (klassefanerne og detaljeruden)

Beskeden er altid `<Etiket>: <besked>`. Etiketten kommer fra `Char`-tabellen,
ellers fra standardkolonnerne, ellers er det feltnavnet med versaler
(`resolveColumnLabel`, `:1464`). Samme besked tælles kun én gang.

| ID | Regel | Kilde | Besked (ordret) | Alvor | Power Fx | Implementeret i |
|---|---|---|---|---|---|---|
| FL30 | `Char`-tabellen: klassens felter med tal-`MaxLength` | `:806-828`, `:1183-1190` | `<felt>: Max N characters.` | Fejl | Tjek `MAX` i `nfFlPlan` | `fl_validation.py` `spool_issues` (`MAX`); `generate_app_onstart.py` `nfFlPlan` |
| FL31 | `Char`-tabellen: `Dropdown`-felter skal matche listen | `:1192-1197` | `<felt>: Value must match dropdown options.` | Fejl | Tjek `DROP` | `fl_validation.py` `spool_issues` (`DROP`), `in_list_bad`; `generate_app_onstart.py` `nfFlLists` |
| FL32 | Description er påkrævet (stamdata) | `:203-213`, `:1236-1238` | `Description: Required field.` | Fejl | Tjek `REQ` | `fl_validation.py` `spool_issues` (`REQ`) |
| FL33 | Stamdata-længder: Manufacturer 30, Description 40, Model Number 20, Manufacturer Part/Serial Number 30, Sort Field 30, Room 8, Warranty Start/End 10 | `:203-213`, `:1240-1242` | `<felt>: Max N characters.` | Fejl | Tjek `MAX` | `fl_validation.py` `spool_issues` (`MAX`) |
| FL34 | Warranty Start/End: `DD.MM.YYYY` eller `YYYYMMDD`, og en rigtig dato | `:179`, `:1244-1246`, `:1440-1462` | `<felt>: Use DD.MM.YYYY or YYYYMMDD.` | Fejl | Tjek `DATE` - ren aritmetik, ikke `Date()`, se PX4 | `fl_validation.py` `date_bad` |
| FL35 | Faste værdier: Atex/Risiko/Asbestos/PTW = X, ABC Indic. = A, StrIndicator ∈ KKS/AKS/ROS/KKSKV/KKSKA, TRM assignment = X | `:149-157`, `:1249-1257` | `<felt>: Allowed values: X.` (listen ordret) | Fejl | Tjek `ALLOW` | `fl_validation.py` `spool_issues` (`ALLOW`) |
| FL36 | Trinliste pr. klasse (`CLASS_STEP_RULES`, `DEFAULT` for ukendte) | `:181-201`, `:1222-1229` | – | Afledt | Foldet ind i `nfFlPlan` af harnessen | `fl_rules.generated.json` `plan` → `generate_app_onstart.py` `nfFlPlan` |
| FL37 | `Design_pressure_`: Design pressure maks. **8**, tegn `0-9 . , - / +`; uom mod `Design_pressure_uom` | `:216-218`, `:1260-1263` | `Max 8 characters.` / `Invalid value format.` / `Value must match dropdown options.` | Fejl | `MAX`, `RGX NUMSIGN`, `DROP` | `fl_validation.py` `spool_issues`, `rgx_bad` (`NUMSIGN`) |
| FL38 | `Operating_pressure_`: maks. 12, samme tegn; uom mod `Design_pressure_uom` | `:219-221`, `:1265-1268` | som FL37 | Fejl | samme | `fl_validation.py` `spool_issues`, `rgx_bad` |
| FL39 | `Design_temperature_`: maks. 8; uom mod `Design_Temp_uom` | `:222-224`, `:1270-1273` | som FL37 | Fejl | samme | `fl_validation.py` `spool_issues`, `rgx_bad` |
| FL40 | `Operating_temperature_`: maks. 10; uom mod `Design_Temp_uom` | `:225-227`, `:1275-1278` | som FL37 | Fejl | samme | `fl_validation.py` `spool_issues`, `rgx_bad` |
| FL41 | `Design_flow_`: maks. 10; uom mod `Design_flow_uom` | `:228-230`, `:1280-1283` | som FL37 | Fejl | samme | `fl_validation.py` `spool_issues`, `rgx_bad` |
| FL42 | I et trin: klassens `Dropdown`-felter med en kendt søgenøgle (K0210 …) tjekkes igen | `:1362-1371` | `Value must match dropdown options.` | Fejl | Falder sammen med FL31 (samme felt, samme liste - dedupliceret) | `fl_rules.generated.json` `plan` (samme tjek som FL31 - dedupliceret af harnessens buildPlan) |
| FL43 | `Typekreds`: Typekredse mod `TypekredsTabel` | `:1285-1287` | `Typekredse: Value must match dropdown options.` | Fejl | `DROP` | `fl_validation.py` `spool_issues` (`DROP`) |
| FL44 | `TestMethod`: Test Method og Test Method 2 mod `TestMethod` | `:1289-1292` | `<felt>: Value must match dropdown options.` | Fejl | `DROP` | `fl_validation.py` `spool_issues` (`DROP`) |
| FL45 | `TRMNEW`: EX-Marking maks. 30 | `:231-233`, `:1295` | `EX-Marking: Max 30 characters.` | Fejl | `MAX` | `fl_validation.py` `spool_issues` (`MAX`) |
| FL46 | `TRMNEW`: Safety Critical Equipment mod klassens egen `SCEq`-kolonne (ingen kolonne = intet tjek) | `:879-902`, `:1297`, `:1405-1407` | `Safety Critical Equipment: Value must match dropdown options.` | Fejl | `DROP` mod klassens liste | `fl_validation.py` `spool_issues` (`DROP`, klassens SCEq-liste) |
| FL47 | `TRMNEW`, kun MKP og NO CLASS: Fire Classification mod `FireClassification`, Fire Sealing Type mod `Table20` | `:1299-1302` | `FIRE CLASSIFICATION: …` / `FIRE SEALING TYPE: Value must match dropdown options.` | Fejl | `DROP` | `fl_validation.py` `spool_issues` (`DROP`) |
| FL48 | `TRMNEW`: udfyldt EX-Marking, SCE, Fire Classification, Fire Sealing Type eller Fire Sealing Product → TRM assignment = X og ABC Indic. = A. Ellers ryddes TRM assignment (ABC bliver). Sker **efter** tjekkene | `:1304-1313` | – | Afledt | Skrives i `colFlVals` efter meddelelsestabellen | `fl_validation.py` `TRM_SET`; `generate_app_onstart.py` `nfFlTrmClasses` |
| FL49 | MKP og aggregat `UE`: TRM assignment = X | `:1315-1321` | – | Afledt | samme | `fl_validation.py` `TRM_SET` (`Ue`) |
| FL50 | MKP og `UE`: Fire Classification påkrævet | `:1323-1325` | `FIRE CLASSIFICATION: Required when aggregate key is UE.` | Fejl | `UE` | `fl_validation.py` `spool_issues` (`UE`) |
| FL51 | MKP, `UE` og pos. 17-18 = `FP`: Fire Sealing Type og Product påkrævet | `:1327-1334` | `FIRE SEALING TYPE: Required for UE/FP.` / `FIRE SEALING PRODUCT: Required for UE/FP.` | Fejl | `UEFP` | `fl_validation.py` `spool_issues` (`UEFP`) |
| FL52 | Klassens egne felter (`CLASS_SPECIFIC_FIELD_RULES`, ELF … UNF): længde og tegn | `:236-341`, `:1339-1344`, `:1374-1388` | `<felt>: Max N characters.` / `<felt>: Invalid value format.` | Fejl | `MAX`, `RGX NUMCOMMA`/`NUMDOT` | `fl_validation.py` `spool_issues`, `rgx_bad` (`NUMCOMMA`, `NUMDOT`) |
| FL53 | `KKS_Syntax`-trinnet gentager syntaksfejlen på feltet | `:1346-1354` | `Functional Location: KKS invalid.` | Fejl | `KKS` | `fl_validation.py` `spool_issues` (`KKS`) |
| FL54 | Listematch: uden forskel på store og små bogstaver, trimmet, `|`-adskilte værdier skal ALLE være i listen; tom liste = intet tjek | `:1426-1438` | – | Afledt | `Split(v, "|")` + `in` | `fl_validation.py` `in_list_bad` |
| FL55 | Beskedformat `<etiket>: <besked>`; identiske beskeder én gang; feltets første besked vises ved feltet | `:1166-1177`, `:1464-1473`, `:2157-2186` | – | Afledt | `GroupBy(RowGuid, Msg)` + `Min(Ord)` | `fl_validation.py` `DEDUPE`, `field_issue` |
| FL56 | Værdier trimmes; en tom værdi fjerner feltet | `:582-606` | – | Afledt | `RemoveIf` + `Collect` kun ved ikke-tom | `fl_parts.py` `set_val_fx` |
| FL57 | Afledte felter: StrIndicator = KKS-type, Long text = Description som standard, User status = status med versaler, System status = `LOCAL`, Info = første fejl/advarsel, SAP status | `:2079-2096`, `:2205-2242` | – | Afledt | `Switch` i `val_fx()` | `fl_parts.py` `_display_val` |
| FL58 | Skrivebeskyttede kolonner: Class, SAP status, Info, StrIndicator, Str. Indicator, User status, System status | `:115-123`, `:2137-2139` | – | Afledt | `Editable` i `nfFlColumns` | `generate_app_onstart.py` `nfFlColumns` (`Editable`); `fl_parts.py` `txtFlDetRo` |
| FL59 | Editor: dropdown når feltet har en liste (også de faste lister), ellers tekst med maks.-længde (Char, FL 40, Description 40). En ugyldig gemt værdi vises stadig | `:2098-2135`, `:2188-2197` | – | Afledt | `drpFlDetVal` / `inpFlDetVal`, `MaxLength` | `fl_parts.py` `inpFlDetVal`, `drpFlDetVal`, `DD_ITEMS` |
| FL60 | Kolonnerne pr. klasse fra `FL_SPOOL_COLUMNS`. Kompakt visning: #, FL, Description, StrIndicator, Class, Info (SAP status skjult) | `:65-73`, `:1905-1958`, `:2036-2054` | – | Afledt | `nfFlColumns`; kompakt tabel | `generate_app_onstart.py` `nfFlColumns`; `fl_parts.py` `build_classes`, `C_COLS` |
| FL61 | Detaljeruden: alle klassens kolonner med editor og besked; "Show empty"/"Hide empty" (standard: skjul tomme uden besked) | `:1960-2034` | – | Afledt | `galFlDetail`, `varFlShowEmpty` | `fl_parts.py` `build_detail`, `DET_ITEMS`, `btnFlDetEmpty` |
| FL62 | Verify validerer alle rækker; ændring af FL/Description og af et spool-felt validerer igen | `:431-462`, `:570-580`, `:1014-1045` | – | Afledt | `Select(btnFlVerify)` i `OnChange` | `fl_parts.py` `REVERIFY`, `set_row_fx`; `fl_validation.py` `verify_fx` → `btnFlVerify` |
| FL63 | Add row; Delete row (sidste række væk → ny tom række); siden starter med én tom række | `:399`, `:423-429`, `:464-479`, `:917-935` | – | Afledt | `btnFlAddRow`, `btnFlRowDelete`, `OnVisible` | `fl_parts.py` `add_row_fx`, `btnFlAddRow`, `btnFlRowDelete`; `assemble_screen.py` `on_visible` |
| FL64 | Export JSON: `generatedAt`, `source`, `rows`, `classBuckets`, `ruleMeta` | `:2254-2276` | – | Afledt | `JSON()` → `Download` af data-URI + vist i ruden | `fl_save.py` `export_fx`, `payload_fx`; `fl_parts.py` `build_export` |
| FL65 | Klassernes hjælpetekster (`CLASS_HELP`) | `:75-113` | – | Afledt | `nfFlClassHelp` | `generate_app_onstart.py` `nfFlClassHelp`; `fl_parts.py` `btnFlTab` (Tooltip) |
| FL66 | Tællere: rækker i alt, klar (valid+warning), med fejl | `:2244-2252` | – | Afledt | Badges i bjælken | `fl_parts.py` `COUNTS` → `txtFlCount` |
| FL67 | Uden virkning i originalen: `FIELD_REGEX_RULES` bruges ingen steder; trinet `VerifyFunctionalLocationClasses` gør intet; `FL_CLASSIFICATION_DATA` overskrives af `FL_LOOKUPS` | `:159-177`, `:182-200`, `fl-rule-engine.js:264` | – | – | Bevidst ikke implementeret: det ville give en regel, originalen ikke har | – (efterprøvet af differentialtesten: 0 afvigelser uden dem) |

### Regler, appen lægger til (fra opgaven, ikke fra HTML'en)

| ID | Regel | Kilde | Besked | Alvor | Implementeret i |
|---|---|---|---|---|---|
| FL68 | Indsend blokeres, så længe en ikke-tom række er `invalid`, der ingen klar række er, eller der er ændret noget siden sidste Verify | Opgaven, §3 "blokér indsend ved fejl"; HTML'ens "Ready for SAP" | `Submit is blocked: N row(s) have errors.` | Fejl | `fl_save.py` `SUBMIT_OK`, `SUBMIT_DM`, `SUBMIT_WHY`, `submit_fx` |
| FL69 | Et indsendt sæt er låst (visning) | Samme mønster som Equipment/Material | – | Afledt | `fl_parts.py` `DM_EDIT` |
| FL70 | "New request" tømmer siden og starter en ny anmodning med én tom række | Appens livsforløb (siden har kun én anmodning pr. indlæsning) | – | Afledt | `fl_parts.py` `NEW_FX` → `btnFlNew` |

## Power Fx mod JavaScript

| # | Forskel | Hvad appen gør |
|---|---|---|
| PX1 | `IsMatch` kræver et **konstant** mønster. Mønstrene kan derfor ikke læses fra data | De 12 KKS-mønstre, legacy, de 5 korte, ELF, MKP og FP læses af harnessen ud af `fl-rule-engine.js` og skrives som konstanter i formlen. Feltmønstrene er tre (`NUMSIGN`, `NUMCOMMA`, `NUMDOT`) og vælges med `Switch`. Et nyt mønster i JS stopper `harness.js plan` med en fejl |
| PX2 | Power Fx' regex tillader ikke unødige escapes. `\/` er ulovligt, og et bindestreg i en klasse skal escapes | `[0-9.,\-\/+]` → `[0-9.,/+\-]` og `[-A-Z]` → `[\-A-Z]`. Tegnmængderne er de samme. `(FP)` → `FP`, uden gruppe |
| PX3 | `\d`, `\s` og `\w` er Unicode i Power Fx og ASCII/ECMAScript i JS | FL er normaliseret til versaler. Forskellen rammer kun ikke-latinske cifre (fx arabisk-indiske), som JS afviser, og som Power Fx kunne acceptere. Accepteret og dokumenteret |
| PX4 | `new Date(y, m-1, d)` i JS mod `Date()` i Power Fx: Power Fx lægger 1900 til år under 1900 | Datotjekket er ren aritmetik: år ≥ 100, måned 1-12, dag 1-dage i måneden (gregoriansk skudår). Det svarer præcis til JS' `getFullYear()`-sammenligning, også for år 100-1899, som JS accepterer. Efterprøvet i differentialtesten |
| PX5 | `FunctionKeyDict` har 6.445 rækker (6.441 efter normalisering) - over SharePoints delegeringsgrænse (500/2000). Et `LookUp` mod SharePoint med en værdi fra en `ForAll` kan ikke delegeres (`check_layout` regel 30), så SharePoint ville kun lede i de første 500-2000 rækker, og en gyldig nøgle længere nede ville blive afvist i stilhed | Nøglerne ligger i appen, som siden har dem i `lookups.generated.js`: én streng `0ABA0ABB0…0` i `nfFlFunctionKeys`, slået op med `exactin` (forskel på store og små bogstaver, som `Set.has`). Separatoren er et ciffer, fordi nøglerne er rene bogstaver (byggeriet stopper, hvis det ændrer sig). Aggregat (146), komponent (139), BR18 (7) og værker (8) ligger som navngivne tabeller. `MD_FLKey` i SharePoint er seedet med de samme nøgler til flows og serverside-validering, men appen læser den ikke |
| PX6 | SharePoint sammenligner tekst uden forskel på store og små bogstaver, `Set.has` i JS gør det med forskel | Alle nøgler i `FL_LOOKUPS` er versaler, og FL normaliseres til versaler før opslaget. Forskellen kan ikke opstå med de nuværende data |
| PX7 | Ingen funktioner med parametre (UDF er ikke slået til) | Verify-formlen er genereret af Python ét sted (`fl_validation.py`) og kaldt ét sted (`btnFlVerify`). Alle andre steder bruger `Select(btnFlVerify)` |
| PX8 | Klassetabellen med 30-50 dynamiske kolonner (`mode-all`) kan ikke laves som et canvas-galleri med dynamiske kolonner uden en celle pr. felt | Kompakt tabel i fanen, og "All columns" er detaljeruden (FL61), som viser og redigerer hver kolonne. Samme felter, samme editorer, samme beskeder - kun layoutet er et andet. Se AQ4 |
| PX9 | Hovertooltips (`data-hint`) | `Tooltip` findes kun på interaktive kontroller (`check_layout` regel 10). Hjælpeteksten sidder derfor på en lille `?`-knap ved beskeden (`btnFlRowHint`), der også viser teksten ved klik |
| PX10 | `Blob` + `<a download>` kan ikke laves i en canvas app | Export JSON viser JSON'en i en popup, hvor den kan kopieres. Indholdet er det samme som snapshottet |
| PX11 | Opdatering af mange SharePoint-rækker med `LookUp(Liste, ID = X.ID)` i en `ForAll` kan ikke delegeres | Gem peger de eksisterende rækker ud med `{ ID: … }` (listens primærnøgle) i én `Patch` med to tabeller, og sletter med `Remove(Liste, ForAll(…, { ID: … }))` |

## Afvigelser mellem JS og VBA (JS vinder)

Reglerne ovenfor følger JS'en. Her er det, en VBA-bruger vil opleve som
anderledes, så det ikke forsvinder i stilhed:

| Emne | VBA | JS (og appen) |
|---|---|---|
| Beskeder | `Invalid KKS code`, `Duplicate KKS-code`, `'XX' is not an accepted Equipment key` … | `KKS invalid.`, `Duplicate FL.`, `Equipment key invalid.` … |
| Legacy | Lang forklaring | `Legacy format.` |
| Dublet | Kun 2. forekomst (fuld Verify), store/små bogstaver tæller | Alle forekomster, efter normalisering |
| Design pressure | Maks. 12 | Maks. **8** i trinet (Char siger 12 - begge tjekkes, 8 bider først) |
| Voltage [V] i TAF | `^[0-9.,]*$` | Samme; ELF/KAB `^[0-9,]*$` |
| Fire Sealing Product | Maks. 30 i TRMNEW | Intet længdetjek (ikke i JS) |
| Warranty-dato | `^\d{8}$` = DDMMYYYY via `IsDate` | `YYYYMMDD` |
| Test Method 2 | Accepteres, når Test Method er tom | Tjekkes altid |
| TRM ryddet | TRM og ABC ryddes | Kun TRM ryddes |
| Klasse ved nøglefejl | Klassen skrives alligevel | Ingen klasse i key18-grenen |
| Equipment Numbers-fanen | Egne regler (Plant, kategori, garanti) | Findes ikke på siden - se AQ5 |

## Testmatrix

Kørt af `node tools/fl/harness.js test` mod de originale filer. Kolonnen
"Forventet" er det, originalen giver. Den flade evaluator (= appens Power
Fx) skal give ordret det samme, ellers er testen rød. Sager med samme
*gruppe* valideres sammen (dubletter). Hele listen står i
`tools/fl/testmatrix.json`.

<!-- TESTMATRIX:START -->
| Test | Regel | Gyldig/ugyldig | FL | Description | Felter | Forventet status | Klasse | Beskeder (ordret, i raekkefoelge) |
|---|---|---|---|---|---|---|---|---|
| T01a | FL1 | gyldig | ` ssv10⍽lac10ab001 ` | Pumpe |  | valid | MKP | - |
| T01b | FL1 | ugyldig | `SSV10-LAC10AB001` | Pumpe |  | invalid | MKP | KKS invalid. · Functional Location: KKS invalid. |
| T03a | FL3 | gyldig | `` | (tom) |  | draft | - | - |
| T03b | FL3 | ugyldig | `   ` | x |  | invalid | - | FL required. |
| T04a | FL4 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T04b | FL4 | ugyldig | `` | Pumpe |  | invalid | - | FL required. |
| T05a | FL5 | ugyldig (gruppe dup) | `SSV10 LAC10AB001` | Pumpe |  | invalid | MKP | Duplicate FL. |
| T05b | FL5 | ugyldig (gruppe dup) | `ssv10 lac10ab001` | Pumpe |  | invalid | MKP | Duplicate FL. |
| T05c | FL5 | gyldig (gruppe dup) | `SSV10 LAC10AH001` | Pumpe |  | valid | ELF | - |
| T06a | FL6 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T06b | FL6 | ugyldig | `SSV10 LAC10AB001` | (tom) |  | invalid | MKP | Description required before Ready for SAP. · Description: Required field. |
| T07a | FL7 | gyldig | `SSV10 LAC10AB001` | 40 tegn |  | valid | MKP | - |
| T07b | FL7 | ugyldig | `SSV10 LAC10AB001` | 41 tegn |  | invalid | MKP | Description > 40. · Description: Max 40 characters. |
| T08a | FL8 | gyldig | `SSV10 LAC1234` | Pumpe |  | valid | KAB | - |
| T08b | FL8 | gyldig | `SSV10 LAC10 1234` | Pumpe |  | valid | KAB | - |
| T08c | FL8 | gyldig | `SSV10 LAC   1234` | Pumpe |  | valid | KAB | - |
| T08d | FL8 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T09a | FL9 | gyldig | `SSV10 LAC10AB001 KA01` | Pumpe |  | valid | MKP_VA | - |
| T09b | FL9 | ugyldig | `SSV10 LAC10AB001 KA1` | Pumpe |  | warning | MKP_VA | Legacy format. |
| T10a | FL10 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T10b | FL10 | ugyldig | `SSV10 LAC10ZZ` | Pumpe |  | invalid | - | KKS invalid. · Class not determined. · Functional Location: KKS invalid. |
| T11a | FL11 | gyldig | `AVV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T11b | FL11 | ugyldig | `XXX10 LAC10AB001` | Pumpe |  | invalid | MKP | Plant key invalid. |
| T12a | FL12 | gyldig (noFunctionKeys) | `SSV10 ZZZ10AB001` | Pumpe |  | valid | MKP | - |
| T12b | FL12 | ugyldig | `SSV10 ZZZ10AB001` | Pumpe |  | invalid | MKP | Function key invalid. |
| T13a | FL13 | gyldig | `SSV10 UAB10UF001D` | Pumpe |  | valid | MKP | - |
| T13b | FL13 | ugyldig | `SSV10 LAC10UF001D` | Pumpe |  | invalid | MKP | UF/UE requires U function key. |
| T14a | FL14 | gyldig | `SSV10 UAB10UF001D` | Pumpe |  | valid | MKP | - |
| T14b | FL14 | ugyldig (noBr18UF) | `SSV10 UAB10UF001D` | Pumpe |  | invalid | MKP | BR18 rules missing for UF. |
| T15a | FL15 | gyldig | `SSV10 UAB10UF001G` | Pumpe |  | valid | MKP | - |
| T15b | FL15 | ugyldig | `SSV10 UAB10UF001A` | Pumpe |  | invalid | MKP | BR18 key17 invalid for UF. |
| T16a | FL16 | gyldig | `SSV10 LAC1234` | Pumpe |  | valid | KAB | - |
| T16b | FL16 | ugyldig | `XXX10 LAC1234` | Pumpe |  | invalid | KAB | Plant key invalid. |
| T17a | FL17 | gyldig | `SSV10 LAC10AB001 KA01` | Pumpe |  | valid | MKP_VA | - |
| T17b | FL17 | ugyldig | `SSV10 LAC10AB001 QQ01` | Pumpe |  | invalid | - | Component key invalid. |
| T17c | FL17 | ugyldig | `SSV10 LAC10ZZ001 KA01` | Pumpe |  | invalid | - | Equipment key invalid. |
| T18a | FL18 | gyldig | `SSV10 LAC10AH001` | Pumpe |  | valid | ELF | - |
| T18b | FL18 | ugyldig | `SSV10 LAC10QT001` | Pumpe |  | invalid | - | Class not determined. |
| T19a | FL19 | gyldig | `SSV10 UAB10UE001FD` | Pumpe | Fire Classification=`BK EI 60 (60 min)` | valid | MKP | - |
| T19b | FL19 | ugyldig | `SSV10 LAC10ZZ001FD` | Pumpe |  | invalid | - | KKS invalid. · Equipment key invalid. · Functional Location: KKS invalid. |
| T20a | FL20 | gyldig | `SSV10 LAC` | Pumpe |  | valid | NO CLASS | - |
| T20b | FL20 | ugyldig | `SSV10 LA2` | Pumpe |  | invalid | - | KKS invalid. · Function key invalid. · Class not determined. · Functional Location: KKS invalid. |
| T21a | FL21 | gyldig | `SSV10 ABC10` | Pumpe |  | valid | ELF | - |
| T21b | FL21 | ugyldig | `SSV10 1BC10` | Pumpe |  | invalid | - | KKS invalid. · Function key invalid. · Class not determined. · Functional Location: KKS invalid. |
| T22a | FL22 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T22b | FL22 | ugyldig | `SSV10 LAC10QT001` | Pumpe |  | invalid | - | Class not determined. |
| T23a | FL23 | gyldig | `SSV10 LAC` | Pumpe |  | valid | NO CLASS | - |
| T24a | FL24 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T25a | FL25 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T25b | FL25 | ugyldig | `SSV10 LAC10AB001 KA1` | Pumpe |  | warning | MKP_VA | Legacy format. |
| T25c | FL25 | ugyldig | `XXX10 LAC10AB001` | Pumpe |  | invalid | MKP | Plant key invalid. |
| T30a | FL30 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Remarks=`rrrrrrrrrrrrrrrrrrrrrrrrrrrrrr` | valid | GIV | - |
| T30b | FL30 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Remarks=`rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr` | invalid | GIV | Remarks: Max 30 characters. |
| T31a | FL31 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure uom=`Bar` | valid | GIV | - |
| T31b | FL31 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure uom=`Foo` | invalid | GIV | Operating pressure uom: Value must match dropdown options. |
| T32a | FL32 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T32b | FL32 | ugyldig | `SSV10 LAC10AB001` | (tom) |  | invalid | MKP | Description required before Ready for SAP. · Description: Required field. |
| T33a | FL33 | gyldig | `SSV10 LAC10AB001` | Pumpe | Manufacturer=`mmmmmmmmmmmmmmmmmmmmmmmmmmmmmm`; Room=`R1234567` | valid | MKP | - |
| T33b | FL33 | ugyldig | `SSV10 LAC10AB001` | Pumpe | Manufacturer=`mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm`; Room=`R12345678` | invalid | MKP | Manufacturer: Max 30 characters. · Room: Max 8 characters. |
| T34a | FL34 | gyldig | `SSV10 LAC10AB001` | Pumpe | Warranty Start=`29.02.2024`; Warranty End=`20241231` | valid | MKP | - |
| T34b | FL34 | ugyldig | `SSV10 LAC10AB001` | Pumpe | Warranty Start=`20230229`; Warranty End=`2024-12-31` | invalid | MKP | Warranty Start: Use DD.MM.YYYY or YYYYMMDD. · Warranty End: Use DD.MM.YYYY or YYYYMMDD. |
| T35a | FL35 | gyldig | `SSV10 LAC10AB001` | Pumpe | Atex=`x`; ABC Indic.=`A`; PTW=`X` | valid | MKP | - |
| T35b | FL35 | ugyldig | `SSV10 LAC10AB001` | Pumpe | Atex=`Y`; ABC Indic.=`B` | invalid | MKP | Atex: Allowed values: X. · ABC Indic.: Allowed values: A. |
| T36a | FL36 | gyldig | `SSV10 LAC1234` | Pumpe | EX-Marking=`eeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` | valid | KAB | - |
| T36b | FL36 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | EX-Marking=`eeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` | invalid | GIV | EX-Marking: Max 30 characters. |
| T37a | FL37 | gyldig | `SSV10 LAC10AB001 QT01` | Pumpe | Design pressure=`-1,5/+2`; Design pressure uom=`psi` | valid | MAA | - |
| T37b | FL37 | ugyldig | `SSV10 LAC10AB001 QT01` | Pumpe | Design pressure=`12345678a`; Design pressure uom=`foo` | invalid | MAA | Design pressure uom: Value must match dropdown options. · Design pressure: Max 8 characters. · Design pressure: Invalid value format. |
| T38a | FL38 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure=`123456789012` | valid | GIV | - |
| T38b | FL38 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure=`1234567890123` | invalid | GIV | Operating pressure: Max 12 characters. |
| T39a | FL39 | gyldig | `SSV10 LAC10AB001 QT01` | Pumpe | Design temperature=`12345678`; Design temperature uom=`K` | valid | MAA | - |
| T39b | FL39 | ugyldig | `SSV10 LAC10AB001 QT01` | Pumpe | Design temperature=`123456789`; Design temperature uom=`C` | invalid | MAA | Design temperature uom: Value must match dropdown options. · Design temperature: Max 8 characters. |
| T40a | FL40 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating temperature=`-10/+40`; Operating temperature uom=`°C` | valid | GIV | - |
| T40b | FL40 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating temperature=`1234567890A`; Operating temperature uom=`x` | invalid | GIV | Operating temperature: Max 10 characters. · Operating temperature uom: Value must match dropdown options. · Operating temperature: Invalid value format. |
| T41a | FL41 | gyldig | `SSV10 LAC10AB001 KN01` | Pumpe | Design flow=`10`; Design flow uom=`m³/h` | valid | MKP_FA | - |
| T41b | FL41 | ugyldig | `SSV10 LAC10AB001 KN01` | Pumpe | Design flow=`ti`; Design flow uom=`x` | invalid | MKP_FA | Design flow uom: Value must match dropdown options. · Design flow: Invalid value format. |
| T42a | FL42 | gyldig | `SSV10 LAC10AB001 QT01` | Pumpe | Design pressure uom=`Barg` | valid | MAA | - |
| T42b | FL42 | ugyldig | `SSV10 LAC10AB001 QT01` | Pumpe | Design pressure uom=`bar g` | invalid | MAA | Design pressure uom: Value must match dropdown options. |
| T43a | FL43 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Typekredse=`1.1 Energi-/flowmåler` | valid | GIV | - |
| T43b | FL43 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Typekredse=`9.9` | invalid | GIV | Typekredse: Value must match dropdown options. |
| T44a | FL44 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Test Method=`nr1: end to end test`; Test Method 2=`Nr4: Test af signalvej` | valid | GIV | - |
| T44b | FL44 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Test Method 2=`Nr9` | invalid | GIV | Test Method 2: Value must match dropdown options. |
| T45a | FL45 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | EX-Marking=`eeeeeeeeeeeeeeeeeeeeeeeeeeeeee` | valid | GIV | - |
| T45b | FL45 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | EX-Marking=`eeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` | invalid | GIV | EX-Marking: Max 30 characters. |
| T46a | FL46 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Safety Critical Equipment=`1.1 Evakuering-alarm/sirene` | valid | GIV | - |
| T46b | FL46 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Safety Critical Equipment=`2.4 Hængere` | invalid | GIV | Safety Critical Equipment: Value must match dropdown options. |
| T47a | FL47 | gyldig | `SSV10 LAC10AB001` | Pumpe | Fire Classification=`BK EI 60 (60 min)`; Fire Sealing Type=`brandplade` | valid | MKP | - |
| T47b | FL47 | ugyldig | `SSV10 LAC10AB001` | Pumpe | Fire Classification=`EI 60`; Fire Sealing Type=`Tape` | invalid | MKP | FIRE CLASSIFICATION: Value must match dropdown options. · FIRE SEALING TYPE: Value must match dropdown options. |
| T47c | FL47 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Fire Classification=`EI 60` | valid | GIV | - |
| T48a | FL48 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | EX-Marking=`Ex d` | valid | GIV | - |
| T48b | FL48 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | TRM assignment=`X`; ABC Indic.=`A` | valid | GIV | - |
| T48c | FL48 | gyldig | `SSV10 LAC1234` | Pumpe | TRM assignment=`X` | valid | KAB | - |
| T49a | FL49 | gyldig | `SSV10 UAB10UE001FD` | Pumpe | Fire Classification=`BK EI 60 (60 min)` | valid | MKP | - |
| T49b | FL49 | gyldig | `SSV10 UAB10UF001D` | Pumpe |  | valid | MKP | - |
| T50a | FL50 | gyldig | `SSV10 UAB10UE001FD` | Pumpe | Fire Classification=`BK EI 60 (60 min)` | valid | MKP | - |
| T50b | FL50 | ugyldig | `SSV10 UAB10UE001FD` | Pumpe |  | invalid | MKP | FIRE CLASSIFICATION: Required when aggregate key is UE. |
| T51a | FL51 | gyldig | `SSV10 UAB10UE001FP` | Pumpe | Fire Classification=`BK EI 60 (60 min)`; Fire Sealing Type=`Brandplade`; Fire Sealing Product=`Hilti CP 611A` | valid | MKP | - |
| T51b | FL51 | ugyldig | `SSV10 UAB10UE001FP` | Pumpe | Fire Classification=`BK EI 60 (60 min)` | invalid | MKP | FIRE SEALING TYPE: Required for UE/FP. · FIRE SEALING PRODUCT: Required for UE/FP. |
| T52a | FL52 | gyldig | `SSV10 LAC10AB001 -Q01` | Pumpe | Voltage [V]=`0.4` | valid | TAF | - |
| T52b | FL52 | ugyldig | `SSV10 LAC1234` | Pumpe | Voltage [V]=`0.4` | invalid | KAB | Voltage [V]: Invalid value format. |
| T52c | FL52 | ugyldig | `SSV10 LAC10AB001 -A01` | Pumpe | Power [kW]=`12.5` | invalid | ELF | Power [kW]: Invalid value format. |
| T53a | FL53 | gyldig | `SSV10 LAC10AB001` | Pumpe |  | valid | MKP | - |
| T53b | FL53 | ugyldig | `SSV10 LAC10ZZ` | Pumpe |  | invalid | - | KKS invalid. · Class not determined. · Functional Location: KKS invalid. |
| T54a | FL54 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure uom=` bar \| PSI ` | valid | GIV | - |
| T54b | FL54 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure uom=`Bar\|foo` | invalid | GIV | Operating pressure uom: Value must match dropdown options. |
| T55a | FL55 | gyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure=`123456789012` | valid | GIV | - |
| T55b | FL55 | ugyldig | `SSV10 LAC10AB001 -B01` | Pumpe | Operating pressure=`1234567890123` | invalid | GIV | Operating pressure: Max 12 characters. |
| T56a | FL56 | gyldig | `SSV10 LAC10AB001` | Pumpe | Atex=`   ` | valid | MKP | - |
| T56b | FL56 | ugyldig | `SSV10 LAC10AB001` | Pumpe | Atex=` XX ` | invalid | MKP | Atex: Allowed values: X. |
<!-- TESTMATRIX:END -->

UI-reglerne (FL2, FL26-FL29, FL57-FL66, FL68-FL69) kan ikke køres i Node.
De har deres egen matrix nedenfor og efterprøves i Studio efter deploy.

| ID | Gyldigt eksempel → forventet | Ugyldigt eksempel → forventet |
|---|---|---|
| FL2 | 40 tegn i FL → accepteres | 41. tegn → kan ikke tastes (`MaxLength`) |
| FL26 | Række med kun advarsel → gul chip "Warning" og "Legacy format." | Række med to fejl → ingen chip, kun den første fejl |
| FL27 | Musen over "Function key invalid." → `Function key is FL position 7-9 (ZZZ). It must exist in FunctionKeyDict lookup.` | Musen over "Duplicate FL." → ingen hjælpetekst |
| FL28 | 2 MKP + 1 GIV → faner `ALL (3)`, `GIV (1)`, `MKP (2)` | Tom række → i ingen fane |
| FL29 | "Plant key invalid." → FL-feltet rødt, Description ikke | "Description > 40." → kun Description rødt |
| FL57 | GIV-række → StrIndicator = `KKS`, System status = `LOCAL` | Long text tom → viser Description |
| FL58 | Detaljeruden: Remarks kan redigeres | Info/StrIndicator kan ikke redigeres |
| FL59 | Operating pressure uom → dropdown med 10 enheder | Remarks → tekstfelt med maks. 30 |
| FL60 | MKP-fane → kolonnerne #, FL, Description, StrIndicator, Class, Info | SAP status vises ikke |
| FL61 | Show empty → alle 45 MKP-kolonner | Hide empty → kun udfyldte og dem med besked |
| FL62 | Ret FL → rækken valideres igen med det samme | Ret Remarks til 31 tegn i detaljeruden → rækken bliver straks `invalid` med `Remarks: Max 30 characters.` |
| FL63 | Slet eneste række → én ny tom række | Slet den ene af to dubletter → den anden beholder `Duplicate FL.`, til Verify køres (som i JS, der ikke validerer ved sletning), og Submit er inaktiv imens |
| FL64 | Export JSON → popup med `rows`, `classBuckets`, `ruleMeta` | Kun en tom række → `rows: []` |
| FL65 | Musen over fanen `GIV (1)` → `GIV: TRANSDUSERS` | Fanen `NO CLASS` → ingen hjælpetekst |
| FL66 | 3 rækker, 1 med fejl → `Rows: 3`, `Ready: 2`, `Issues: 1` | En tom række → tæller i `Rows`, ikke i `Ready` eller `Issues` |
| FL68 | Ingen fejl, Verify kørt → Submit aktiv | En række `invalid` → Submit inaktiv og beskeden vist |
| FL69 | Indsendt → felterne er grå | Kladde → felterne kan redigeres |
| FL70 | New request → én tom række, intet nummer | Efter Submit → New request giver en ny, tom anmodning; den indsendte er uændret i SharePoint |

## Åbne spørgsmål

| # | Spørgsmål | Hvad appen gør indtil videre (den konservative fortolkning) |
|---|---|---|
| AQ1 | JS-filerne lå først ikke i repoet og blev lagt ind undervejs. Er `html/*.js` den endelige udgave? | Regler, plan og test er bygget på filerne, som de ligger nu. Ændres de, skal `node tools/fl/harness.js plan` køres igen - byggeriet stopper, hvis det er glemt |
| AQ2 | `FL_CLASSIFICATION_DATA` overskrives helt af `FL_LOOKUPS`. Er det meningen? | Appen bruger det, der faktisk gælder: `FL_LOOKUPS` |
| AQ3 | Skal masseudtrækket (`functional-location-extract.html`, "FL;ACT_CLASS" pr. linje) også være i appen? | Ikke med. Det er en anden side |
| AQ4 | Er detaljeruden god nok i stedet for "All columns"-tabellen? | Ja, indtil andet er besluttet (PX8) |
| AQ5 | Skal Equipment Numbers-reglerne fra VBA'en ind nogen steder? | Nej. De findes ikke i JS'en, og udstyr har sin egen app |
| AQ6 | JS'en har ingen gem/indsend - den eksporterer JSON. Appens gem og indsend (FL68/FL69, `MD_RequestIndex`) er nye | Bygget efter `powerfx/04-submit-patch.fx`. Selve valideringen er uændret |
| AQ7 | Skal key users kunne rette nøgler, lister og regler uden en ny udgave af appen? | Nej, ikke i denne udgave. Reglerne er bygget ind fra `html/*.js`, præcis som siden har dem. En ændring er: ret JS'en → `node tools/fl/harness.js plan` → byg → deploy. `MD_FLKey` er seedet, så et senere skift til SharePoint-opslag har data at stå på |
| AQ8 | Er `FL_LOOKUPS` og SPOOL-arket samme kilde? | Ja, for nøglerne: `node tools/fl/harness.js seed` genererer `sharepoint/seed/MD_FLKey.csv` ud af `FL_LOOKUPS`, og resultatet er **byte for byte** det samme som filen fra `tools/extract_spool_lists.py` (6.733 nøgler, heraf 6.441 funktionsnøgler efter normalisering). Afviger de en dag, er det `FL_LOOKUPS`, appen følger |

## Byg, provisionér og deploy

```bash
# Reglerne: planen genereres af html/*.js og efterprøves mod dem
node tools/fl/harness.js plan
node tools/fl/harness.js test
node tools/fl/harness.js doc        # testmatrixen herover

# Appen (build_all kører også harness-testen og dokumenttjekket)
python3 tools/build_all.py --app functionallocation
python3 tools/build_all.py          # alle fem - de fire andre må ikke ændre sig
```

```powershell
# SharePoint - listerne og nøglerne (idempotent; MD_FLKey seedes kun, når den er tom)
.\sharepoint\provision\Provision-FunctionalLocationLists.ps1 `
    -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>" -SeedMasterData
# Indekslisten bag hubben, hvis den ikke findes (domænet FunctionalLocation er der i forvejen)
.\sharepoint\provision\Provision-RequestIndex.ps1 -SiteUrl "https://<tenant>.sharepoint.com/sites/<site>"
```

Første deploy:

1. Opret en tom canvas app **Functional Location** i solution BIO SAP i
   Studio. Tilføj `FunctionalLocationRequests`, `FunctionalLocationItems`
   og `MD_RequestIndex` som datakilder, og gem.
2. Sæt appens id i `tools/canvas_apps.json` under `functionallocation` →
   `app_id` (det står i Studio-URL'en efter `app-id=`). Byg igen: så får
   `AppUrl` i `MD_RequestIndex` den rigtige play-URL, og hubbens flise
   skifter fra "Kommer snart" til "Opret ny".
3. Med Studio-fanen åben og coauthoring slået til:

   ```powershell
   python tools\canvas_mcp.py deploy --app functionallocation --compile-only
   python tools\canvas_mcp.py deploy --app functionallocation
   python tools\canvas_mcp.py deploy --app hub
   ```

**Ikke kompileret endnu.** `canvas_mcp.py` kræver .NET 10 SDK, en åben
coauthoring-session i Studio og appens id. Ingen af de tre findes i det
miljø, appen er bygget i, så compile er ikke kørt. Alt, der kan
efterprøves uden Studio, er grønt: layout-, datakilde-, sprog- og
PowerShell-tjekket, regeltesten mod de originale JS-filer og
dokumenttjekket. De Power Fx-konstruktioner, der ikke er brugt i repoet
før, og som derfor skal ses i den første compile: `GroupBy`/`Ungroup`
med kolonnenavne som strenge, `exactin` mod en lang streng,
`Patch(Liste, tabel af { ID }, tabel)` og `Remove(Liste, tabel af { ID })`.

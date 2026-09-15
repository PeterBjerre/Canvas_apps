# SPOOL-arkets regler — kortlægning

Reglerne i `FL_indberetninger_udgave_SPOOL_V3.20.xlsm`, oversat fra VBA til
noget der kan bygges. Kilden ligger i
[`../excel/vba/spool-validation/`](../excel/vba/spool-validation/) — 13
moduler, 4.535 linjer, kopieret ordret ud af arket.

> Kommentarerne i nogle af modulerne er ødelagte (`Hj?lpefunktioner`). Det er
> sket i selve projektfilen, før filen kom hertil — tegnene er tabt i kilden
> og kan ikke gendannes. Det rammer kun kommentarer, ikke regler.

## Det korte

Arket ser rodet ud, men reglerne er det ikke. **Al feltvalidering går gennem
én funktion** — `Verification_Functions.ValidateTable` — der tager to
ordbøger:

```vb
formatColumns.Add "Power [kW]", Array(13, "^[0-9,]*$")      ' maks. 13 tegn, kun tal og komma
formatColumns.Add "Description", Array(40, ".*", True)       ' påkrævet
specialColumns.Add "Fire Classification", FireClass          ' skal stå i en liste
```

Det er hele modellen: **maks. længde, mønster, påkrævet, tilladte værdier.**
Alt andet er hvilken klasse der får hvilke felter. Derfor er reglerne data,
ikke kode — og derfor kan de ligge i SharePoint som alt andet masterdata.

`tools/extract_spool_rules.py` trækker dem ud af VBA-kilden:

```
MD_FLClass.csv           19 klasser
MD_FLCharacteristic.csv 405 regler
trin uden regelblok:    KKS_Syntax
```

Scriptet kan køres igen, når arket ændrer sig, og forskellen ses i et diff.
Det er derfor det er en parser og ikke en tabel, jeg har skrevet af.

---

## Lag 1 — KKS-koden

`modInitialEntryValidation.ValidateRowIncremental`, kolonne A.

Koden skal matche **ét af 12 regex-mønstre** i `KKSRules.GetKKSPatterns()`.
Gør den ikke det, er der to udfald:

| | |
|---|---|
| Matcher *legacy*-mønsteret `…[-A-Z]{2}\d{1,3}$` | **Gul advarsel.** "Kun accepteret hvis anlægget allerede er nummereret sådan" |
| Ellers | **Rød fejl.** `Invalid KKS code` |

Dubletter i kolonne A er altid rød.

### Nøglerne i koden

Klassebestemmelsen læser faste positioner ud af KKS-koden:

| Nøgle | Position | Betydning | Valideres mod |
|---|---|---|---|
| `key0` | 1–3 | Værk | Fast liste: AVV, ASV, HEV, KYV, SSV, SKV, HCV, SMV |
| `key7` | 7–9 | Function key | `FunctionKeyDict` |
| `key12` | 12–13 | Aggregate key | `ClassDeterminationAggregateKey` |
| `key17` | 17–18 | BR18 Related key | `BR18_Keys`, pr. `key12` |
| `key18` | 18–19 | Component key | `ClassDeterminationComponentKey` |

Bemærk at `key17` og `key18` **overlapper på position 18**. Det er ikke en
fejl i min læsning — sådan står det i `Initial_Entry.DetermineClassEx`. De to
bruges i hver sin gren og aldrig samtidig.

---

## Lag 2 — klassebestemmelse

`Initial_Entry.DetermineClassEx`. Rækkefølgen betyder noget:

1. **`key0` skal være et kendt værk.** Ellers fejl, men kørslen fortsætter.
2. **`key7` skal findes i FunctionKeyDict.** Ellers fejl.
3. **BR18-reglen** — kun hvis `key12` er `UF` eller `UE`:
   - `key7` skal starte med `U`
   - `key17` skal være en tilladt værdi for netop det `key12`
4. **Er syntaksklassen allerede KAB, accepteres rækken.** Forretningsregel:
   et kabel må ikke afvises af nøgleopslagene.
5. Ellers, **hvis `key18` har længde 2**: både `key18` *og* `key12` skal slå
   op. Klassen bliver `dict1(key18)` — komponentnøglen vinder.
6. Ellers **`key12`-fallback**: slår `key12` op, bliver klassen den. Ellers
   sætter et par korte mønstre `NO CLASS`, ét sætter `ELF`, og ellers er det
   en fejl.

To mønstre (`FD|FG|FH|FW|FC` og `FP`) giver **altid fejl** i trin 6, selvom
de matcher. De findes for at give en bedre fejlbesked end "ingen klasse".

---

## Lag 3 — karakteristikker pr. klasse

Her ligger de 405 regler. En klasses regelsæt er **ikke** kun dens egen
blok: `Verification_StepsConfig.LegacyDefaultStepsFor` giver en ordnet
trinliste, og reglerne er foreningen af de blokke, listen peger på.

```
GIV = Verify_Master_Data_FL + GIV + TRMNEW + Operating_temperature_
    + Operating_pressure_ + TestMethod + Typekreds
    + VerifyFunctionalLocationClasses + KKS_Syntax
```

Derfor har GIV 34 regler, mens UNF har 14. Alle 19 klasser og deres
trinlister står i `sharepoint/seed/MD_FLClass.csv`.

### De fælles blokke

| Blok | Hvad den giver | Bruges af |
|---|---|---|
| `Verify_Master_Data_FL` | 13 felter alle FL'er har: Description (påkrævet, maks. 40), Manufacturer, Model Number, Sort Field, Room, Atex/Risiko/Asbestos/PTW (kun `X`), ABC Indic. (kun `A`), StrIndicator (KKS/AKS/ROS/KKSKV/KKSKA) | alle på nær Equipment Numbers |
| `TRMNEW` | Safety Critical Equipment, EX-Marking — **plus** Fire Classification, Fire Sealing Type og Fire Sealing Product, men **kun for MKP og NO CLASS** | 15 klasser |
| `Design_/Operating_pressure_`, `_temperature_`, `Design_flow_` | Værdi + enhed, enheden mod en tabel | efter behov |
| `Typekreds`, `TestMethod` | Værdi fra dropdown | kun GIV |
| `Equipment_Numbers` | 18 felter på udstyrsfanen, heraf 4 påkrævede | Equipment Numbers |

Klassehegnet på TRMNEW er let at overse, og det var den ene fejl, min første
parser lavede: uden det arvede ELF brandfelter, den ikke har.

### De automatiske felter

To regler **skriver** i stedet for at validere:

**TRM og ABC** (`Verification_KKS.AutoSetTRMAndABC`) — er bare ét af
EX-Marking, Safety Critical Equipment, Fire Classification, Fire Sealing
Type eller Fire Sealing Product udfyldt, sættes `TRM assignment = X` og
`ABC Indic. = A`. Er de alle tomme, ryddes begge igen.

**MKP + BR18** (`ApplyMKPBR18TRMRule`) — er `key12 = UE` på en MKP:
`TRM assignment = X` altid, og
- `key17 = FP` → Fire Classification, Fire Sealing Type **og** Fire Sealing
  Product er alle påkrævede
- ellers → kun Fire Classification

---

## Rækkens status

Kolonne E bliver `Ready for SAP`, hvis hverken KKS (A), beskrivelse (B)
eller klasse (C) har en blokerende fejl. Gule advarsler blokerer ikke.

Overførsel til klassefanen kræver desuden, at **A er grøn eller gul, og B er
grøn** — `TransferRowNotValidated`.

---

## Datamodellen

Samme mønster som `MD_Strategy` / `MD_StrategyPackage`, som allerede virker.

### `MD_FLClass` — 19 rækker

| Kolonne | Type | |
|---|---|---|
| `ClassKey` | Tekst | ELF, GIV, KAB, MAA, MKP, MKP_AC … NO CLASS, SIGNAL |
| `VerifySteps` | Tekst | Semikolonsepareret trinliste |
| `StepCount` | Tal | Til kontrol |

### `MD_FLCharacteristic` — 405 rækker

| Kolonne | Type | |
|---|---|---|
| `ClassKey` | Tekst | Peger på `MD_FLClass` |
| `Characteristic` | Tekst | Feltnavnet, som det står i SAP |
| `MaxLength` | Tal | Tom for listefelter |
| `Pattern` | Tekst | Regex. `.*` = fri tekst |
| `Required` | Ja/Nej | |
| `AllowedValues` | Tekst | Semikolonsepareret, når listen står i koden |
| `SourceTable` | Tekst | Navnet på Excel-tabellen, når listen kommer derfra |
| `FromStep` | Tekst | Hvilken blok reglen kom fra — sporbarhed |

**`SourceTable` er det uafklarede.** 44 af de 405 regler validerer mod en
værdiliste, der i dag ligger som en navngiven tabel på arket "List data":

`SCEq` · `FireClassification` · `Table20` · `Design_pressure_uom` ·
`Design_Temp_uom` · `Design_flow_uom` · `TypekredsTabel` · `TestMethod`

Dertil `Plant` og `EQ_Cat` på udstyrsfanen. Dem finder udtrækket ikke selv —
de hentes gennem `GetPlantAllowedValues` og
`GetEquipmentCategoryAllowedValues` i stedet for direkte fra en
`ListObjects(...)`, så deres `SourceTable` står tom i CSV'en. Ti lister i
alt.

De skal med over, før appen kan validere de felter. Det er en tredje liste —
`MD_FLValueList` (`ListName`, `Value`, `Sort`) — og indholdet kan trækkes ud
af arket med samme fremgangsmåde som `MD_Strategy`.

### Hvad der **ikke** kan ligge i en liste

| Regel | Hvorfor |
|---|---|
| De 12 KKS-mønstre | Regex mod hele koden, ikke mod et felt. Hører hjemme i en named formula |
| Nøgleudtræk og klassebestemmelse | Rækkefølgeafhængig logik med fallbacks |
| BR18-reglen | Kobler tre nøgler og en opslagstabel |
| TRM/ABC-automatikken | Skriver felter, validerer ikke |
| Dubletkontrol | Ser på hele indtastningen |

Det er fem stykker logik. Resten — 405 regler — er data.

---

## Afklaret undervejs

**De fire `Verification_EquipmentNumbers`-kopier.** Jeg spurgte tidligere,
hvilken der var den levende. Det behøver ikke afklares: de fire filer er
**byte for byte identiske** bortset fra `Attribute VB_Name`. Og begge kald
er modulkvalificerede —

```vb
Verification_EquipmentNumbers.Equipment_Numbers_Core Class
Verification_EquipmentNumbers.ApplyEquipmentNumbersDropdowns ws
```

— så det er det unummererede modul, der kører. `1`, `2` og `3` er døde
kopier. De kan slettes fra projektet uden virkning. (Havde kaldene været
ukvalificerede, ville VBA have nægtet at kompilere med *Ambiguous name
detected* — det er kvalifikationen, der har holdt dubletterne i live.)

**SCEq findes.** `Safety Critical Equipment` er et rigtigt felt her, med en
værdiliste pr. klasse. Det var den manglende brik til prioritetsreglen i
VH-plan appen (`docs/14`, punkt 1) — rød prioritet ved 110/115 **eller**
SCEq. Når FL-appen skriver SCEq til SharePoint, kan den regel laves færdig.

---

## Næste trin

1. **Træk de ti værdilister ud** af "List data" til `MD_FLValueList.csv`.
   Uden dem kan 44 af de 405 regler ikke håndhæves.
2. **Gennemgå `MD_FLCharacteristic.csv`** — 405 rækker, men kun 88 unikke
   feltnavne. Er der felter, der burde være påkrævede, og ikke er det i dag?
   `Required` er sat på præcis fem: Description, Beskrivelse, Plant,
   Equipment Category og Func. location. Alt andet må stå tomt — også
   Safety Critical Equipment og Fire Classification uden for BR18-reglen.
   Det er værd at få bekræftet, at det er med vilje.
3. **Provisionér de tre lister**, samme script-mønster som `MD_Strategy`.
4. **Byg appen** — samme byggekæde som VH-plan: Python-buildere,
   `check_layout`, `check_datasources`.

Punkt 2 er det, der er værd at bruge tid på. Resten er mekanik.

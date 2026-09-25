# Equipment- og Materials-appen

## Eksporten manglede en publicering

De første to eksporter viste to blanke skabeloner — én tom `Screen1`,
`DataSources: []`. Det passede ikke med, hvad der stod i Studio.

**En canvas app i en solution eksporteres fra den PUBLICEREDE udgave.**
Gemt er ikke nok. Apperne var bygget og gemt, men ikke publiceret, så
eksporten hentede den blanke oprindelse hver gang.

Efter publicering:

| | Før | Efter |
|---|---|---|
| `ScreenEquipment.pa.yaml` | — | 247 KB |
| `ScreenMaterialer.pa.yaml` | — | 266 KB |
| `ScreenDetails.pa.yaml` | — | 21 KB |
| `DataSources` | `[]` | 4 flows + 2 eksempelkilder |

> **Reglen herfra:** publicér før eksport, ellers beskriver `solution/`
> ikke det, der kører. `Status: Ready` i `meta.xml` siger intet om, hvorvidt
> indholdet er med — begge tomme eksporter stod som `Ready`.

## Apperne bygges nu herfra

`Equipment App/` og `Material App/` er buildere som de to andre apps. Det
er en omvej værd at forklare, for de har været fjernet én gang undervejs:

1. De blev skrevet, mens eksporten viste to tomme skabeloner.
2. Da det viste sig at være en manglende **publicering**, var de bygget på
   en forkert feltmodel — og farlige, fordi `deploy` erstatter en apps
   indhold. De blev fjernet.
3. Nu er feltmodellen læst af den håndbyggede formular, provisioneret som
   SharePoint-lister, og **verificeret**: `check_datasources.py` efterprøver
   307 kolonnereferencer mod `schema.md` ved hver bygning.

Kæden er altså **formular → liste → builder**, og intet led er gættet.

`folder` peger igen på repoet, så `deploy` virker. Husk at det **erstatter**
appens indhold — en skærm, nogen bygger i Studio uden om repoet, forsvinder
ved næste deploy. Det er prisen for at have én sandhed.

Skal du se, hvad der faktisk ligger i Studio lige nu:

```powershell
python tools\canvas_mcp.py pull --app equipment --out app-pull\equipment
```

## Felterne, som apperne faktisk skriver

Begge apps samler én flad formular op i en **hukommelsessamling** ved
"Save row". Kolonnerne nedenfor er linje for linje den `Collect()`.

### `colEquipmentRows` — `ScreenEquipment.pa.yaml`

| Felt | Kilde i appen |
|---|---|
| `RowId` | `varEqNextRowId`, appens eget løbenummer |
| `RequestType` | `varFormRequestType`, standard `"new"` |
| `Plant` | `drpEqPlant.Selected.Label` |
| `EquipmentNumber` | `txtEqEquipmentNumber` |
| `Description` | `txtEqDescription` |
| `EquipmentCategory` | `drpEqEquipmentCategory.Selected.Value` |
| `Manufacturer` | `txtEqManufacturer` |
| `TypeDesignation` | `txtEqTypeDesignation` |
| `SerialNumber` | `txtEqSerialNumber` |
| `FunctionalLocation` `…1` `…2` | tre selvstændige tekstfelter |
| `ClassData` | `txtEqClassData` |
| `RoomCoordinates` | `txtEqRoomCoordinates` |
| `Placement` | `txtEqPlacement` |
| `WarrantyStart` `WarrantyEnd` | `Text(…SelectedDate, "dd/mm/yyyy")` — **en streng** |
| `DocumentType` | `drpEqDocumentType.Selected.Value` |
| `DocumentLink` | `txtEqDocumentLink` |
| `Status` | `"valid"`, sættes til `"submitted"` ved Submit |

### `colMaterialRows` — `ScreenMaterialer.pa.yaml`

| Felt | Kilde i appen |
|---|---|
| `RowId` | `varNextRowId` |
| `Plant` | `varDetectedPlant` |
| `FunctionalLocation` | `txtMatFL` |
| `Manufacturer` · `ModelNumber` · `ManufacturerPartNo` | tekst |
| `MaterialDescription` | `txtMatDesc` |
| `Documentation` | `txtMatDoc` |
| `StockUnit` · `PriceUnit` | `drp….Selected.Code` |
| `Price` · `DeliveringTime` · `RecommendedStock` | `Value(…)` eller `Blank()` |
| `Supplier` · `SupplierPartNo` | tekst |
| `StrategicPart` · `WearPart` | `drp….Selected.Value` |
| `Status` | `"valid"` / `"submitted"` |

**Materials er ikke MM01.** Der er hverken materialenummer, materialetype
eller materialegruppe. Det, appen samler ind, er reservedelsoplysninger —
leverandør, pris, leveringstid, anbefalet lager — knyttet til en
funktionsplads. Den tidligere udgave af dette dokument gættede på MM01; det
var forkert.

## Tre fund

### 1. Ingen af apperne skriver til SharePoint

Der er **ikke ét `Patch` mod en datakilde** i nogen af de to apps. Alt
ligger i `colEquipmentRows` / `colMaterialRows`, og de er væk, når appen
lukkes. Submit sætter kun `Status` til `"submitted"` på rækkerne i
hukommelsen.

Det er præcis det hul, `Provision-EqMatLists.ps1` lukker — men listerne gør
det ikke alene. **Afgjort: Gem-knappen patcher direkte til listen**, ikke
først ved Submit. Rækken skal findes i SharePoint, før den har en `ItemKey`,
og uden `ItemKey` er der ingen dokumentmappe at lægge filer i.

Formlerne står i [`24-eq-mat-persistering.md`](24-eq-mat-persistering.md).

### 2. Seks dropdowns har ingen værdier

Disse samlinger bruges, men **defineres ingen steder** — hverken i
`App.OnStart` (som er tom) eller i en `OnVisible`:

```
colEqRequestTypeOptions   colEqCategoryOptions   colEqDocumentTypeOptions
colEqPlantOptions         colEqStatusOptions     colEqPlantFilterOptions
colPlantOptions           colStatusOptions       colStockUnits
colPriceUnits             colYesNo
```

Derfor står Status-, Plant- og dokumenttype-dropdownen tomme med røde
fejlmarkeringer i Studio. Det forklarer også, hvorfor ordforrådet ikke kan
læses af koden: det findes ikke. `RequestType` og `Status` er derfor
**tekstkolonner** i provisioneringen, ikke `Choice` — en valgkolonne med
gættede værdier ville afvise alt andet.

### 3. Attachment-flowene er tilknyttet, men aldrig kaldt

Begge apps har de tre flows som datakilder:

```
BioSap-TaskListAttachment
BioSap-GetSubmittedAttachments
BioSap-DeleteSubmittedAttachments
```

**Nul referencer** til dem i nogen skærm. Dokumenter håndteres i stedet med
to tekstfelter, `DocumentType` og `DocumentLink` — altså et link, brugeren
selv skal skaffe, ikke en fil der lægges op.

**Afgjort: ruden erstatter linket.** `DocumentType`, `DocumentLink` og
Materials' `Documentation` bliver ikke provisioneret, og de tre kontroller
fjernes fra formularerne. Power Fx'en står i
[`24-eq-mat-persistering.md`](24-eq-mat-persistering.md).

Materials' felt er i øvrigt værre end et link. Ved siden af det står
`addMatFilePicker`, som ved valg af en fil kører
`Set(varFormDocumentation, Self.FileName)` og intet andet — **filen bliver
aldrig lagt op.** Appen ser ud til at vedhæfte og gemmer et filnavn.

## Listerne

Én liste pr. domæne. Apperne har **intet indmeldingshoved** — der er én flad
formular og en liste af rækker — så en header-liste ville være en tom skal.
Det, der binder en portion rækker sammen, er `RequestNo` og `RequestGuid`
skrevet på hver række ved indsendelse, plus én række i `MD_RequestIndex`.

Ud over appens egne felter får hver liste:

| Kolonne | Hvorfor |
|---|---|
| `RequestNo` · `RequestGuid` | Binder portionen sammen, og dyblinker fra hubben |
| `ItemKey` (unik) | Rækkens nøgle **og** mappenavnet i `TaskListDocuments` |
| `AttachmentFolder` · `FileCount` | Så flowet ikke skal gætte, og listen kan læses i browseren |
| `RequesterEmail` · `RequesterName` · `SubmittedOn` | Tekst, ikke Person — Person kan ikke filtreres delegerbart |
| `RowStatus` | `valid` / `submitted`. **Ikke** det fælles statusordforråd fra `MD_RequestIndex` — det er to forskellige ting |

### Garantidatoerne bliver rigtige datoer

Appen gemmer i dag `Text(txtEqWarrantyStart.SelectedDate, "dd/mm/yyyy")` —
en formateret streng. Den kan ikke sorteres, ikke filtreres på interval, og
betyder noget forskelligt alt efter hvilket landeformat der læser den.
Kolonnerne er `DateTime` i provisioneringen, og appen skal sende
`.SelectedDate` direkte.

## Hubben

Begge fliser peger nu på apperne:

| App | `app_id` |
|---|---|
| Equipments | `24bf3bbc-601f-480d-a8fe-7cd3180906d1` |
| Materials | `d7762919-c716-4bd0-9abd-24bab436221f` |

Id'et står tre steder — `tools/canvas_apps.json`, `hub_config.py` og appens
`PLAY_URL` — og `tools/build_all.py` tjekker, at de er ens. Glider de fra
hinanden, fejler ingenting; det ses først, når en bruger trykker "Open" og
lander i en tom app.

Bemærk at app-id'et **ikke** står i solution-eksporten. Det `Id`, en apps
`Properties.json` bærer, er *dokumentets* id, ikke appens.

## Til sidst: en layoutfælde i Equipment-appen

```
conEqShell.Height =
  Coalesce(40 + conEqHero.Height + conEqFormPanel.Height + … , 1840)
```

En container, der læser sine børns `.Height`, er en cirkelreference i en
AutoLayout-container — det er forælderen, der sætter børnenes størrelse, så
den læser sin egen udregning tilbage. `Coalesce(…, 1840)` er ikke en
sikkerhedsventil; den er beviset på, at udtrykket fejler. Det er rule 1 i
`check_layout.py`, og grunden til at højderne i de repo-byggede apps regnes
i Python.

---

## Issue #29 – formularen i Materials (og Equipments)

Ændringerne ligger i de fælles dele (`tools/domain_parts.py`,
`tools/build_helpers.py`), så Equipments får dem også.

| Før | Nu |
|---|---|
| Danske feltnavne og sektioner (`Stamdata`, `Sliddel`, …) | Engelsk. `check_language.py` kender nu ordene |
| Celler voksede, så en sektion med tre felter fyldte hele rækken | Fire faste kolonner – en kort række slutter bare tidligere |
| FL-søgningen fyldte sin egen række i fuld bredde | To celler i gitteret: *Search functional location* og *Functional location* |
| Stjernen stod ude ved cellens højre kant | Labelen er så bred som sin tekst (`text_px`), stjernen står 3 px efter |
| Knapperne delte hele bredden | `fit_button_row`: hver knap så bred som sin tekst, venstrestillet |
| Dropdown-listen var hvid/grå i mørk tilstand | `themed_dropdown` (Classic/DropDown) – listen farves af tokens |
| Intet skete synligt ved tryk på Search | Knappen deaktiveres og viser tre levende prikker (`varDomFlBusy`) |
| Enter gjorde ingenting | Enter søger (`tmrDomFlEnter` – se `build_fl_cells`) |
| "Selected: SSV13 HFC10AA005" under dropdownen | Fjernet. En hentet/kopieret række lægger sin FL i `colDomFl`, så dropdownen viser den |

**Skal efterprøves i Studio:** Classic/DropDown er ny i disse to apps, og
Enter-søgningen bygger på, at et Multiline-felt lægger `Char(10)` i `Text`.

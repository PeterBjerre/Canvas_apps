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

## Apperne er håndbyggede i Studio, ikke bygget herfra

Derfor er der **ingen** `Equipment App/`- eller `Material App/`-mappe i
repoet. Der lå to, skrevet mens apperne så tomme ud; de er fjernet igen
(de kan hentes frem fra commit `44d9af5`, hvis skelettet skal bruges).

At lade dem ligge var ikke gratis: `deploy` **erstatter** en apps indhold
med repoets kilder, så en enkelt kommando ville have slettet det, der er
bygget i Studio. `folder` er `null` på begge i `tools/canvas_apps.json`, og
`app_dir()` i `canvas_mcp.py` afviser deploy med en forklaring.

Skal apperne læses igen, er vejen solution-eksporten (publicér først) eller:

```powershell
python tools\canvas_mcp.py pull --app equipment
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
det ikke alene. Gem-knappen skal have et `Patch` mod dem.

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

De to modeller kan sagtens leve side om side (linket peger på et dokument i
et andet system; ruden holder filer, der hører til indmeldingen), men de er
ikke det samme, og valget er ikke truffet endnu.

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

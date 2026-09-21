# Equipment og Materials: gem, indsend, dokumenter

Power Fx til at sætte direkte ind i Studio. Kontrolnavnene er appernes
egne, læst i solution-eksporten — ikke opfundet her.

## De to valg

**Gem-knappen patcher direkte til listen.** Rækken findes i SharePoint, så
snart der er trykket *Save row* — ikke først ved *Submit*.

> Dit svar var "Ja" til et enten-eller, så jeg har valgt den gren, der får
> dit andet svar til at virke. Dokumentmappen hedder rækkens `ItemKey`, og
> den findes først, når rækken er skrevet. Skrev vi først ved Submit, kunne
> man ikke vedhæfte noget, før indmeldingen var afsendt — og så er det for
> sent. Skulle det alligevel være VH-plan-modellen, er det `Submit`-formlen
> nedenfor, der skal gøre begge dele, og `Save row` der kun rører
> samlingen.

**Dokumentruden erstatter `DocumentLink`.** `DocumentType`, `DocumentLink`
og Materials' `Documentation` bliver **ikke** provisioneret. Fjern de tre
kontroller fra formularerne.

Materials' `Documentation` er i øvrigt værre end et link: ved siden af den
står `addMatFilePicker`, som ved valg af en fil kører

```
Set(varFormDocumentation, Self.FileName); Reset(txtMatDoc)
```

— altså gemmer **filnavnet** og intet andet. Filen bliver aldrig lagt op.
Appen ser ud til at vedhæfte.

## Identiteten flytter til SharePoint

I dag er `RowId` et tal, appen selv tæller op i `varEqNextRowId`. Det holder
ikke, når to brugere gemmer samtidig, og det siger intet om rækken i
SharePoint.

Herefter er **`RowId` = SharePoint-rækkens `ID`**. Så virker galleriet,
filtrene og detaljemodalen uændret — de slår alle op på `RowId` — og der er
kun ét tal at holde styr på.

`ItemKey` er `EQ-000912` / `MAT-000441`, dannet af samme `ID`. Den er
mappenavnet i `TaskListDocuments` og skal derfor være unik på tværs af
domæner. Det er den, fordi præfikset er det.

---

# Equipment

## 1. `ScreenEquipment.OnVisible`

Henter det, brugeren har liggende. Erstatter ingenting — der er ingen
`OnVisible` i dag.

```
Set(varEqMe, Lower(User().Email));
ClearCollect(
    colEquipmentRows,
    ForAll(
        Filter(EquipmentItems, RequesterEmail = varEqMe) As R,
        {
            RowId: R.ID,
            ItemKey: R.ItemKey,
            RequestType: R.RequestType,
            Plant: R.Plant,
            EquipmentNumber: R.EquipmentNumber,
            Description: R.Description,
            EquipmentCategory: R.EquipmentCategory,
            Manufacturer: R.Manufacturer,
            TypeDesignation: R.TypeDesignation,
            SerialNumber: R.SerialNumber,
            FunctionalLocation: R.FunctionalLocation,
            FunctionalLocation1: R.FunctionalLocation1,
            FunctionalLocation2: R.FunctionalLocation2,
            ClassData: R.ClassData,
            RoomCoordinates: R.RoomCoordinates,
            Placement: R.Placement,
            WarrantyStart: If(IsBlank(R.WarrantyStart), "", Text(R.WarrantyStart, "dd/mm/yyyy")),
            WarrantyEnd: If(IsBlank(R.WarrantyEnd), "", Text(R.WarrantyEnd, "dd/mm/yyyy")),
            Status: Coalesce(R.RowStatus.Value, "valid"),
            FileCount: Coalesce(R.FileCount, 0)
        }
    )
)
```

**Datoerne bliver tekst igen her — med vilje.** Galleriet viser dem som
tekst i dag, og det skal ikke laves om i samme ombæring. Det, der betyder
noget, er at SharePoint har en rigtig dato at sortere og filtrere på.

`Filter(… RequesterEmail = varEqMe)` er delegerbart: `=` på en indekseret
tekstkolonne. `RowStatus` er en valgkolonne, derfor `.Value`.

## 2. `Save row` → `btnEqSaveRow.OnSelect`

Erstatter blokken fra `Set(varEqDetectedPlant, …)` og ned til og med
`Set(varEqNextRowId, varEqNextRowId + 1)` / `Patch(colEquipmentRows, …)`.
Valideringsgrenen ovenover (`Set(varEqRowStatus, "Invalid")` …) bliver.

```
Set(varEqDetectedPlant, drpEqPlant.Selected.Label);
Set(
    varEqSpRow,
    Patch(
        EquipmentItems,
        If(
            IsBlank(varEqEditRowId),
            Defaults(EquipmentItems),
            LookUp(EquipmentItems, ID = varEqEditRowId)
        ),
        {
            Description: Trim(txtEqDescription.Text),
            RequestType: varFormRequestType,
            Plant: drpEqPlant.Selected.Label,
            EquipmentNumber: Trim(txtEqEquipmentNumber.Text),
            EquipmentCategory: drpEqEquipmentCategory.Selected.Value,
            Manufacturer: Trim(txtEqManufacturer.Text),
            TypeDesignation: Trim(txtEqTypeDesignation.Text),
            SerialNumber: Trim(txtEqSerialNumber.Text),
            FunctionalLocation: Trim(txtEqFunctionalLocation.Text),
            FunctionalLocation1: Trim(txtEqFunctionalLocation1.Text),
            FunctionalLocation2: Trim(txtEqFunctionalLocation2.Text),
            ClassData: Trim(txtEqClassData.Text),
            RoomCoordinates: Trim(txtEqRoomCoordinates.Text),
            Placement: Trim(txtEqPlacement.Text),
            WarrantyStart: txtEqWarrantyStart.SelectedDate,
            WarrantyEnd: txtEqWarrantyEnd.SelectedDate,
            RowStatus: { Value: "valid" },
            RequesterEmail: Lower(User().Email),
            RequesterName: User().FullName
        }
    )
);

// Noeglen kan foerst dannes, naar raekken findes - den er lavet af
// raekkens eget ID. Derfor to skrivninger paa en ny raekke og een paa en
// gammel.
If(
    IsBlank(varEqSpRow.ItemKey),
    Patch(
        EquipmentItems,
        varEqSpRow,
        {
            ItemKey: "EQ-" & Text(varEqSpRow.ID, "000000"),
            AttachmentFolder: "TaskListDocuments/EQ-" & Text(varEqSpRow.ID, "000000")
        }
    )
);

Set(varEqSaveRowId, varEqSpRow.ID);
```

Derefter bliver den eksisterende hale stående uændret — `Set(varEqSaveReceiptId, …)`,
`Set(varEqRowStatus, "Valid")`, nulstillingen af `varForm*` — med **én**
tilføjelse til sidst, så galleriet viser det, der faktisk står i listen:

```
Set(varEqEditRowId, If(false, 0));
Set(varEqRuntimeInfo, "Row " & varEqSaveRowId & " saved to SharePoint.");
Concurrent(
    ClearCollect(
        colEquipmentRows,
        ForAll(
            Filter(EquipmentItems, RequesterEmail = varEqMe) As R,
            { /* samme record som i OnVisible */ }
        )
    )
)
```

> `varEqNextRowId` bruges ikke længere. Lad `Set(varEqNextRowId, …)` stå,
> hvis andet peger på den — den gør ingen skade — men `RowId` kommer nu fra
> SharePoint.

## 3. `Submit` → `btnEqSubmit.OnSelect`

Erstatter `Set(varEqSubmitCount, …); UpdateIf(colEquipmentRows, Status = "valid", { Status: "submitted" })`.

```
If(
    CountRows(Filter(colEquipmentRows, Status = "valid")) = 0,
    Notify("Der er ingen gyldige raekker at indsende.", NotificationType.Warning),

    Set(varEqRequestGuid, GUID());

    // Indekset foerst: dets raekke-id bliver til indmeldingsnummeret.
    // Ingen taeller, intet flow, og to brugere der indsender samtidig kan
    // ikke faa det samme nummer.
    Set(
        varEqIdx,
        Patch(
            MD_RequestIndex,
            Defaults(MD_RequestIndex),
            {
                Domain: { Value: "Equipment" },
                Status: { Value: "Indsendt" },
                StatusStep: 2,
                IsOpen: true,
                RequesterEmail: Lower(User().Email),
                RequesterName: User().FullName,
                ShortText: "Equipment: " & CountRows(Filter(colEquipmentRows, Status = "valid")) & " raekke(r)",
                Plant: First(Filter(colEquipmentRows, Status = "valid")).Plant,
                ItemCount: CountRows(Filter(colEquipmentRows, Status = "valid")),
                RequestGuid: varEqRequestGuid,
                AppUrl: "https://apps.powerapps.com/play/e/e0f8f822-d16a-e878-ba4e-fb42bc617e47"
                        & "/a/24bf3bbc-601f-480d-a8fe-7cd3180906d1?reqid=" & varEqRequestGuid,
                LastActionOn: Now(),
                LastActionBy: Lower(User().Email)
            }
        )
    );
    Set(varEqRequestNo, "EQ-" & Text(varEqIdx.ID, "000000"));
    Patch(MD_RequestIndex, varEqIdx, { RequestNo: varEqRequestNo });

    ForAll(
        Filter(colEquipmentRows, Status = "valid") As R,
        Patch(
            EquipmentItems,
            LookUp(EquipmentItems, ID = R.RowId),
            {
                RequestNo: varEqRequestNo,
                RequestGuid: varEqRequestGuid,
                RowStatus: { Value: "submitted" },
                SubmittedOn: Now()
            }
        )
    );

    Set(varEqSubmitCount, CountRows(Filter(colEquipmentRows, Status = "valid")));
    UpdateIf(colEquipmentRows, Status = "valid", { Status: "submitted" });
    Notify("Indsendt som " & varEqRequestNo, NotificationType.Success)
)
```

`MD_RequestIndex.Domain` og `.Status` er **valgkolonner**, derfor
`{ Value: … }`. Værdierne skal være ordret dem, `hub_config.py` kender —
`"Equipment"` og `"Indsendt"`, ikke oversættelser.

---

# Dokumentruden

Den erstatter `DocumentType` og `DocumentLink`. Den hører til den **valgte,
gemte** række — ikke til formularen: mappen hedder rækkens `ItemKey`, og
den findes først efter Gem.

## Kontroller at tilføje

| Navn | Type |
|---|---|
| `attEqPicker` | Attachments (`Attachments@2.3.0`) |
| `btnEqAttUpload` | Button, "Upload to SharePoint" |
| `btnEqAttRefresh` | Button, "Refresh" |
| `btnEqAttRemove` | Button, "Remove document" |
| `galEqAttachments` | Gallery, `Items = Sort(Filter(colEqAttachments, RowId = varEqSelectedRowId), FileName)` |
| `txtEqAttEmpty` | Label |

**`Sort` på `FileName`, ikke på et løbenummer.** Der er ingen `LineId` på
dokumenter. VH-plan-appen sorterede på en kolonne, der ikke fandtes; `Items`
gik i fejl, galleriet stod tomt, og filerne lå i biblioteket hele tiden.

## Mappen

```
LookUp(colEquipmentRows, RowId = varEqSelectedRowId).ItemKey
```

Upload-flowet lægger selv `/TaskListDocuments/` foran. Get-flowet gør
**ikke** — det skal have hele stien. Samme oplysning, to former; det er
sådan flowene er.

## `btnEqAttUpload.OnSelect`

```
With(
    { key: LookUp(colEquipmentRows, RowId = varEqSelectedRowId).ItemKey },
    If(
        IsBlank(key),
        Notify("Gem raekken foerst - mappen hedder raekkens noegle.", NotificationType.Warning),

        If(
            CountRows(attEqPicker.Attachments) = 0,
            Notify("Vaelg en eller flere filer foerst.", NotificationType.Warning),

            Clear(colEqAttUp);
            ForAll(
                attEqPicker.Attachments As F,
                Collect(
                    colEqAttUp,
                    {
                        Name: F.Name,
                        Ok: IfError(
                            Lower(
                                Text(
                                    'BioSap-TaskListAttachment'.Run(
                                        key,
                                        { file: { contentBytes: F.Value, name: F.Name } }
                                    ).flowrunsuccess
                                )
                            ) = "true",
                            false
                        )
                    }
                )
            );
            Reset(attEqPicker);
            Select(btnEqAttRefresh);
            If(
                CountRows(Filter(colEqAttUp, Ok = false)) > 0,
                Notify(
                    "SharePoint afviste: " & Concat(Filter(colEqAttUp, Ok = false), Name, ", "),
                    NotificationType.Error
                ),
                Notify("Dokument(er) lagt op.", NotificationType.Success)
            )
        )
    )
)
```

**Svaret bliver læst.** VH-plan-appen sagde `Notify("Document(s) uploaded.")`
lige efter `ForAll`, uanset hvad flowet svarede — en kvittering, appen selv
fandt på. Her samles `flowrunsuccess` pr. fil, og de filer, der ikke kom
igennem, står med navn.

## `btnEqAttRefresh.OnSelect`

```
With(
    { key: LookUp(colEquipmentRows, RowId = varEqSelectedRowId).ItemKey },
    If(
        IsBlank(key),
        Notify("Gem raekken foerst - mappen hedder raekkens noegle.", NotificationType.Warning),

        Set(
            varEqAttJson,
            'BioSap-GetSubmittedAttachments'.Run("TaskListDocuments/" & key).files
        );
        RemoveIf(colEqAttachments, RowId = varEqSelectedRowId);
        Collect(
            colEqAttachments,
            ForAll(
                ParseJSON(Coalesce(varEqAttJson, "[]")) As J,
                {
                    RowId: varEqSelectedRowId,
                    FileName: Text(J.Name),
                    FileUrl: Text(J.Link),
                    Identifier: Text(J.Identifier),
                    Selected: false
                }
            )
        );
        Patch(
            EquipmentItems,
            LookUp(EquipmentItems, ID = varEqSelectedRowId),
            { FileCount: CountRows(Filter(colEqAttachments, RowId = varEqSelectedRowId)) }
        );
        UpdateIf(
            colEquipmentRows,
            RowId = varEqSelectedRowId,
            { FileCount: CountRows(Filter(colEqAttachments, RowId = varEqSelectedRowId)) }
        )
    )
)
```

`Coalesce(varEqAttJson, "[]")` er ikke pynt: svarer flowet ingenting, river
en tom værdi hele resten af kæden med sig, og brugeren ser hverken filer
eller fejl.

## `btnEqAttRemove.OnSelect`

```
If(
    CountRows(Filter(colEqAttachments, RowId = varEqSelectedRowId, Selected = true)) = 0,
    Notify("Vaelg et eller flere dokumenter foerst.", NotificationType.Warning),

    ForAll(
        Filter(colEqAttachments, RowId = varEqSelectedRowId, Selected = true) As D,
        If(!IsBlank(D.Identifier), 'BioSap-DeleteSubmittedAttachments'.Run(D.Identifier))
    );
    RemoveIf(colEqAttachments, RowId = varEqSelectedRowId, Selected = true);
    Select(btnEqAttRefresh)
)
```

## `txtEqAttEmpty.Text`

```
With(
    { key: LookUp(colEquipmentRows, RowId = varEqSelectedRowId).ItemKey },
    If(
        IsBlank(key),
        "Gem raekken foerst - mappen hedder raekkens noegle.",
        "Ingen dokumenter i TaskListDocuments/" & key & " endnu."
    )
)
```

**Stien står i beskeden med vilje.** Get-flowet svarer `files: "[]"` både
når mappen ikke findes og når den er tom — `Condition_2` tester
`statusCode = 200` på mappeopslaget, og else-grenen svarer det samme som
"mappen er tom". De to kan ikke skelnes fra appen, så stien skal kunne
holdes op mod biblioteket.

`Visible`: `IfError(CountRows(Filter(colEqAttachments, RowId = varEqSelectedRowId)) = 0, false)`

---

# Materials

Samme tre formler med `Mat`-navnene. Forskellene:

| | Equipment | Materials |
|---|---|---|
| Liste | `EquipmentItems` | `MaterialItems` |
| Samling | `colEquipmentRows` | `colMaterialRows` |
| Titel-kolonne | `Description` | `MaterialDescription` |
| Præfiks | `EQ-` | `MAT-` |
| Domæne i indekset | `"Equipment"` | `"Material"` |
| App-id i `AppUrl` | `24bf3bbc-601f-480d-a8fe-7cd3180906d1` | `d7762919-c716-4bd0-9abd-24bab436221f` |
| Redigerings-var | `varEqEditRowId` | `varEditRowId` |
| Valgt række | `varEqSelectedRowId` | `varSelectedRowId` |

`Save row` for Materials:

```
Set(
    varMatSpRow,
    Patch(
        MaterialItems,
        If(IsBlank(varEditRowId), Defaults(MaterialItems), LookUp(MaterialItems, ID = varEditRowId)),
        {
            MaterialDescription: Trim(txtMatDesc.Text),
            Plant: varDetectedPlant,
            FunctionalLocation: Trim(txtMatFL.Text),
            Manufacturer: Trim(txtMatManufacturer.Text),
            ModelNumber: Trim(txtMatModel.Text),
            ManufacturerPartNo: Trim(txtMatMfrPartNo.Text),
            Supplier: Trim(txtMatSupplier.Text),
            SupplierPartNo: Trim(txtMatSupplierPartNo.Text),
            StockUnit: drpMatStockUnit.Selected.Code,
            PriceUnit: drpMatPriceUnit.Selected.Code,
            Price: If(IsBlank(Trim(txtMatPrice.Text)), Blank(), Value(txtMatPrice.Text)),
            DeliveringTime: If(IsBlank(Trim(txtMatDelivery.Text)), Blank(), Value(txtMatDelivery.Text)),
            RecommendedStock: If(IsBlank(Trim(txtMatRecStock.Text)), Blank(), Value(txtMatRecStock.Text)),
            StrategicPart: drpMatStrategic.Selected.Value,
            WearPart: drpMatWear.Selected.Value,
            RowStatus: { Value: "valid" },
            RequesterEmail: Lower(User().Email),
            RequesterName: User().FullName
        }
    )
);
If(
    IsBlank(varMatSpRow.ItemKey),
    Patch(
        MaterialItems,
        varMatSpRow,
        {
            ItemKey: "MAT-" & Text(varMatSpRow.ID, "000000"),
            AttachmentFolder: "TaskListDocuments/MAT-" & Text(varMatSpRow.ID, "000000")
        }
    )
);
Set(varSaveRowId, varMatSpRow.ID);
```

---

# Før det virker

1. **Kør provisioneringen.**
   ```powershell
   .\sharepoint\provision\Provision-EqMatLists.ps1 -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDev"
   ```
   Den slutter med at slå `TaskListDocuments` op og skrive dets id ud —
   hold det op mod miljøvariablen `BioSap-Library-TaskListDocuments`.

   Lukker login-vinduet sig selv, eller siger PnP *"User canceled
   authentication"*, så brug enhedslogin i stedet:

   ```powershell
   .\sharepoint\provision\Provision-EqMatLists.ps1 `
       -SiteUrl "https://orsted.sharepoint.com/teams/BioSAPDev" -DeviceLogin
   ```

2. **Tilføj datakilder i hver app:** `EquipmentItems` (hhv.
   `MaterialItems`) og `MD_RequestIndex`. De tre flows er der allerede.

3. **Fjern dokumentkontrollerne** — se listen nedenfor. Det er ikke nok at
   slette dem: de er nævnt 20 steder tilsammen, og hver dinglende reference
   er en compile-fejl.

4. **Kør `Export-ListSchema.ps1` igen bagefter**, så
   `tools/check_datasources.py` kan efterprøve de nye kolonnenavne. Indtil
   da står listerne som "provisioneres, men findes ikke i udtrækket endnu",
   og kolonnerne er **ikke** kontrolleret.

## Det der stadig mangler

De elleve dropdown-samlinger defineres stadig ingen steder, så Status-,
Plant-, kategori- og enhedsdropdownene er tomme. Du skrev, at der kommer
lister til dem senere. Når de findes, er det en `OnVisible` i stil med:

```
ClearCollect(colEqPlantOptions, ForAll(PlantList As R, { Label: R.Title }));
```

Indtil da: `RequestType`, `EquipmentCategory`, `StockUnit`, `PriceUnit`,
`StrategicPart` og `WearPart` er **tekstkolonner** i SharePoint, ikke
valgkolonner. Det er med vilje — en valgkolonne med gættede værdier ville
afvise alt andet, og ordforrådet findes ikke nogen steder endnu.


---

# Punkt 3: hvad der skal væk

Det svære er ikke at slette kontrollerne — det er de **20 referencer**, der
bliver tilbage. Hver af dem er en compile-fejl, indtil den er ryddet.
Linjenumrene er fra solution-eksporten og flytter sig, når du retter;
brug navnene.

## Equipment

**Slet to containere** (de tager label og felt med sig):

| Container | Indeholder |
|---|---|
| `conEqCellDocumentType` | label + `drpEqDocumentType` |
| `conEqCellDocumentLink` | label + `txtEqDocumentLink` |

**Ryd derefter disse referencer:**

| Sted | Linje i eksporten | Gør |
|---|---|---|
| *Reset form*-knappen | 1710–1711 | slet `Reset(drpEqDocumentType);` og `Reset(txtEqDocumentLink);` |
| *Save row* — nulstilling efter gem | 1858–1859 | samme to linjer |
| *Edit*-knappen i Saved Rows | 2923–2924 | samme to linjer |
| *Reset form* — variabler | 1692–1693 | slet `Set(varFormDocumentType, "");` og `Set(varFormDocumentLink, "");` |
| *Save row* — variabler | 1840–1841 | samme to linjer |
| *Edit* — indlæs række | 2905–2906 | slet `Set(varFormDocumentType, ThisItem.DocumentType);` og `…DocumentLink…` |
| `Collect` / `Patch` | 1787–1788, 1814–1815 | `DocumentType:` og `DocumentLink:` — **væk allerede**, hvis du har erstattet Save-formlen |

> **Pas på semikolonnet ved linje 1859.** `Reset(txtEqDocumentLink)` er det
> **sidste** led i kæden og står uden semikolon. Sletter du begge linjer,
> skal `Reset(txtEqWarrantyEnd);` ovenover miste sit semikolon — ellers
> står der et `;` lige før `)`, og Power Fx afviser det. Det er samme fælde
> som regel 11 i `check_layout.py`.

## Materials

**Slet én container:** `conMatDocRow`. Den indeholder `txtMatDoc`,
`addMatFilePicker` og `btnMatSelectFile` — alle tre forsvinder med den, og
det tager to referencer med sig (`Reset(txtMatDoc)` inde i filvælgerens
`OnSelect`, og `Select(addMatFilePicker)` på knappen).

**Ryd derefter:**

| Sted | Linje i eksporten | Gør |
|---|---|---|
| `Collect` / `Patch` | 2190, 2215 | `Documentation: Trim(txtMatDoc.Text),` — væk allerede med den nye Save-formel |
| tre nulstillinger | 2254, 2306, 3254 | slet `Reset(txtMatDoc);` |
| to variabelnulstillinger | 2239, 2291 | slet `Set(varFormDocumentation, "");` |
| *Edit* — indlæs række | 3239 | slet `Set(varFormDocumentation, ThisItem.Documentation);` |

## Eller lad mig gøre det

Jeg kan lave rettelserne i YAML'en og lægge dem klar til `deploy` — så er
der ingen dinglende referencer, fordi en maskine tæller dem.

Det kræver appen **som den ser ud nu**. Solution-eksporten er fra før
formlerne blev sat ind, så et deploy af den ville rulle punkt 4 tilbage.
Hent den kørende app ned først:

```powershell
python tools\canvas_mcp.py pull --app equipment --out app-pull\equipment
python tools\canvas_mcp.py pull --app material  --out app-pull\material
git add app-pull
git commit -m "Pull af EQ og MAT foer oprydning"
git push
```

`--out` er ikke pynt: uden den lander pullet i `.canvas-sync\`, som står i
`.gitignore` — og så når det aldrig frem til mig.

`pull` rører ikke `folder`, så den virker, selv om deploy er spærret.
Coauthoring-fanen skal være åben på appen.


---

# Runde to: kladde, FL-søgning og layout

## Kladde og færdig er to knapper

`RowStatus` har fået en tredje værdi:

| | Kræver | |
|---|---|---|
| `draft` | kun beskrivelsen | Listens `Title` er obligatorisk, så helt tom kan rækken ikke være. Alt andet må mangle — det er hele pointen |
| `valid` | også værket | Det er **dem**, Indsend tager med |
| `submitted` | — | Afsendt, og dermed låst i appen |

Provisioneringen skal køres igen, før `draft` findes i listen.

## Gemte rækker kan åbnes

Hver række har nu en **Åbn**-knap. Galleriets `OnSelect` virkede også før,
men den er usynlig — der er intet, der siger at rækken *kan* åbnes, og så
er det de færreste der prøver.

## Functional location søges som i VH-plan

`build_flsearch.py` er kopieret ind i begge apps — samme fil, kun
variabelnavnet er skiftet. Flowet var allerede datakilde i begge.

Konstruktionen er tekstfelt + søgeknap + dropdown, **uden** skjult
filtrering. VH-plans første udgave brugte en combobox med indbygget
søgning; den fik 819 rækker fra flowet og viste nul.

## Layout

**Dokumenterne ligger nederst**, ikke i en skinne til højre. To grunde:
ruden hører til den *valgte* række, og rækken vælges i listen længere nede
— så øjet skulle hele vejen op igen for at se hvad der skete. Og skinnen
gjorde formularen smal, hvilket er dyrt, når den har fire kolonner.

Rækkefølgen følger nu arbejdet: udfyld → gem → vælg i listen → læg
dokumenter på → indsend.

**Topsektionen har fire kolonner.** Beskrivelse og værk hører til første
sektion — ikke til en række for sig — så rækken fyldes op med sektionens
to første felter.

**Toplinjens knapper blev klippet væk.** Venstre side stod som
`Parent.Width - 520` og højre som faste `500`; på et smalt vindue blev
venstre side negativ. Nu bryder linjen om i stedet.

## Rødt når der mangler, grønt når der står noget

Kun på de **krævede** felter. En grøn kant om hvert eneste udfyldt felt
gør farven meningsløs; det er stadig det ene spørgsmål, der afgør den —
mangler der noget her, før der kan gemmes?

Reglen ligger i `build_helpers.py`, som er delt af alle fire apps, så
VH-plan og hubben får den samme opførsel.

## Og en regel i datakilde-tjekket

En valgværdi, provisioneringen opretter men skemaudtrækket endnu ikke
kender, er ikke en kodefejl — den er en påmindelse om at køre scriptet.
`draft` gjorde byggeriet rødt af en god grund, og et tjek der er rødt af
gode grunde bliver ignoreret, næste gang det er rødt af en dårlig.
Afprøvet: en værdi, *ingen* provisionering opretter, fejler stadig.


---

# Runde tre: to slags kladde, og én indeksrække

## De to kladder er ikke det samme

Det var en misforståelse fra min side, og den er værd at holde adskilt:

| | Hvor | Hvad |
|---|---|---|
| **Gem kladde** | på rækken | Én række er ikke færdig. `RowStatus = draft`. Den bliver **ikke** sendt med ved Indsend |
| **Send som kladde** | på indmeldingen | Hele indmeldingen lægges på landingssiden med `Status = Kladde`, så den kan ses og arbejdes videre på. Rækkerne låses **ikke** |

Det var den nederste, du bad om. Den øverste beholder jeg — en halvfærdig
række skal kunne ligge uden at blive sendt med.

## Én indeksrække, ikke én pr. tryk

Rækken slås op på `RequestGuid` og oprettes kun, hvis den ikke findes:

```
Patch(
    MD_RequestIndex,
    Coalesce(
        LookUp(MD_RequestIndex, RequestGuid = varDomRequestGuid),
        Defaults(MD_RequestIndex)
    ),
    { … }
)
```

Uden `Coalesce` ville *Send som kladde* og derefter *Indsend* give **to**
rækker på landingssiden for den samme indmelding — og den første ville stå
som kladde for evigt. Det er samme konstruktion som VH-plan-appens gem.

Nummeret dannes kun første gang. Bagefter er det det samme, uanset hvor
mange gange der sendes.

**Kun Indsend låser rækkerne.** `RowStatus: submitted` står i præcis én
gren; en kladde skal stadig kunne rettes, ellers er det ikke en kladde.

## Beskrivelseskolonnen havde intet loft

`MAIN_W` var `Parent.Width - FIXED` — altså "tag resten". På en bred skærm
blev den over tusind pixels: de øvrige kolonner blev skubbet helt ud til
højre kant, og imellem dem lå en tom flade på halvdelen af vinduet.

```
MAIN_W = Min(Parent.Width - 650, 460)
```

En tabel skal være så bred som sit indhold, ikke som sin beholder.

**Inputfelterne står stadig øverst** — rækkefølgen er `bar → formular →
liste → dokumenter → indsend`, og det er den, arbejdet følger.


---

# Runde fire: bredderne

## Formularen regnede med en bredde, den ikke havde

Felterne lå spredt ud over rækken med huller imellem sig, en labelrad
højere oppe end den første, og inputfelter man ikke kunne finde.

Årsagen var én konstant. Cellerne blev regnet af `EDITOR_W`:

```
EDITOR_W = If(App.Width < 1000, SHELL_W, SHELL_W - 360 - 20)
```

Den stammer fra dengang formularen havde dokumentruden i en **skinne ved
siden af sig**. Skinnen er væk, kortet fylder hele bredden — og så regnede
hver eneste celle med 380 pixels, den ikke havde.

```
FORM_W = (SHELL_W - 36)      36 = kortets padding, 18 i hver side
```

En bredde skal regnes af den beholder, tingen faktisk står i. Det lyder
selvindlysende; fejlen opstod, fordi beholderen blev skiftet ud, og
konstanten blev stående.

## Listen og dokumenterne står side om side

Ruden hører til den række, der er valgt i listen. Står de under hinanden,
skal øjet hele vejen ned og op igen for at se, hvad valget gjorde.

Over **1600 px** deler de bredden; derunder stables de. Grænsen er ikke
valgt på følelse: listen har syv kolonner og ~540 px i faste bredder, så
under det bliver beskrivelseskolonnen smallere end sit eget gulv, og
rækken flyder ud over ruden i stedet for at dele sig.

## To knapper hed det samme

`Hent forfra` stod **begge** steder og betød to forskellige ting:

| Nu | Hvad den gør |
|---|---|
| **Hent dokumenter** | Spørger `BioSap-GetSubmittedAttachments` hvad der ligger i `TaskListDocuments/<ItemKey>` for den valgte række, og opdaterer listen + filtællingen |
| **Hent raekker forfra** | Læser `EquipmentItems` / `MaterialItems` forfra fra SharePoint, så skærmen viser det, der faktisk står i listen |

Den sidste er sjældent nødvendig — alt gem og indsend henter selv forfra
bagefter. Den er der til, når nogen **anden** har rettet i listen, mens
appen var åben.

## `Gem som kladde` er den første knap

Den hed `Send som kladde`. "Send" er misvisende, når hele pointen er, at
den *ikke* er sendt endnu — den ligger bare på landingssiden, så den kan
ses og arbejdes videre på.

# SPOOL-arket → en FL-indmeldingsapp

Første gennemgang af `FL_indberetninger_udgave_SPOOL_V3.20.xlsm`, så vi ved
hvad opgaven er, før der bygges.

## Hvad der er i filen

| | |
|---|---|
| Regneark | **35** |
| VBA | **15.588 linjer** fordelt på 85 moduler |
| Klasse-faner med karakteristikker | ELF, GIV, KAB, MAA, MKP (+ 8 undertyper), RBR, SIGNAL, TAF, UNF, NO CLASS |

Det er en betydeligt større opgave end VH-plan appen. Til sammenligning er
hele VH-plan appens byggekode ca. 3.400 linjer Python.

### Hvor logikken ligger

| Modul | Linjer | Indhold |
|---|---|---|
| `GUI_SCRIPT` | 1.992 | SAP GUI Scripting — oprettelsen |
| `JsonConverter` | 1.123 | Standardbibliotek, skal ikke oversættes |
| `Initial_Entry` | 896 | Indtastningsarket og dets regler |
| `ValidationMessages` | 662 | **Alle fejlbeskeder ét sted** — god struktur, genbruges |
| `modInitialEntryValidation` | 601 | Validering af indtastningen |
| `Verification_ClassBlocks` | 525 | Klasser og karakteristikker |
| `Verification_Functions` | 520 | Fælles valideringsfunktioner |
| `mMain` | 451 | Arbejdsgangen |
| `EXTRACT_FROM_SHAREPOINT_LISTS` | 308 | Henter masterdata |
| `Verification_*` (7 moduler) | ~1.200 | KKS-regler, udstyrsnumre, masterdata, trinstyring |
| `Material_*`, `GUI_*` (8 moduler) | ~1.000 | Materialer, stykliste, dokumenter |

`Verification_EquipmentNumbers` findes i **fire udgaver** (`.bas`, `1`, `2`,
`3`) à 266 linjer. **Afklaret:** de er byte for byte identiske bortset fra
modulnavnet, og begge kald er modulkvalificerede, så det er det unummererede
modul der kører. Se [`16-spool-regler.md`](16-spool-regler.md).

## Sådan foreslår jeg vi griber det an

Ikke som én oversættelse. Arket er vokset over tid, og en 1:1-omskrivning
ville tage rodet med.

**Trin 1 — kortlæg reglerne, ikke koden.** ✅ **Gjort.** Se
[`16-spool-regler.md`](16-spool-regler.md). Reglerne viste sig at være langt
mere ensartede end filen ser ud til: al feltvalidering går gennem én
funktion med fire parametre pr. felt. `tools/extract_spool_rules.py` trækker
dem ud af VBA-kilden, så tabellen kan genskabes når arket ændrer sig.

**Trin 2 — klasser og karakteristikker som data, ikke som ark.** ✅
**Modelleret.** 19 klasser og 405 regler ligger som
`sharepoint/seed/MD_FLClass.csv` og `MD_FLCharacteristic.csv`, samme mønster
som `MD_Strategy` / `MD_StrategyPackage`. Mangler: de ti værdilister fra
arket "List data" (`MD_FLValueList`).

**Trin 3 — appen.** Samme byggekæde som VH-plan: Python-buildere,
`check_layout`, `check_datasources`.

**Trin 4 — GUI-scriptet bliver, hvor det er.** Excel + SAP GUI Scripting er
stadig vejen til SAP. Appen erstatter *indtastningsarket* og *valideringen*,
ikke oprettelsen.

Trin 1 og 2 er lavet. Reglerne er det egentlige aktiv i den fil — skærmen er
den nemme del. Næste skridt står sidst i
[`16-spool-regler.md`](16-spool-regler.md).

---

# GUI-scriptet: hvorfor special characteristics fejler nogle gange

**Fundet.** Rettelsen ligger i
[`../excel/vba/GUI_SCRIPT-SpecialCharacteristics-FIX.bas`](../excel/vba/GUI_SCRIPT-SpecialCharacteristics-FIX.bas).

## Fejlen

I `WriteSpecialCharacteristicsOnCurrentPage`:

```vb
For i = 1 To countKeys
    ...
    Set metadata = GetCharacteristicPageMetadata(...)
    countKeys = CLng(metadata("countKeys"))   ' ingen virkning
    keys      = metadata("keys")              ' NYT array, anden længde
    i = 0                                     ' genstart scanningen
Next i
```

**VBA evaluerer `To countKeys` én gang**, når løkken startes. At sætte
`countKeys` inde i kroppen ændrer ikke, hvornår løkken stopper.

Og arrayet bliver faktisk en anden længde — `BuildCharacteristicPageMetadata`
dimensionerer det præcist til det, der står på skærmen:

```vb
ReDim arr(1 To values.count)
```

Efter en opdatering kører løkken altså `1 .. det gamle antal` hen over de
**nye** arrays:

| Popup'en ændrede siden til | Resultat |
|---|---|
| **færre** rækker | `keys(i)` rammer uden for arrayet → *Subscript out of range*, scriptet dør |
| **flere** rækker | de sidste besøges aldrig → karakteristikken skrives **aldrig**, og det ses kun i `Debug.Print` |
| **samme** antal | virker |

Det er præcis mønsteret "nogle gange virker det, andre gange ikke": det
afhænger af, om popup'en for den enkelte karakteristik indsatte eller
fjernede rækker på skærmen.

## Fejl nummer to, i samme procedure

`objContainer` hentes **én gang** i `FillCharacteristicsBatch`, før der
skrives. `WriteSpecialCharacteristicWithControl` åbner en popup
(`SendVKey 4`) og lukker den igen — og SAP genrenderer containeren. Den gamle
kode opdaterede metadata ud fra den samme, nu forældede reference.

`FillCharacteristicsBatch` henter selv containeren forfra bagefter — men først
når *alle* special characteristics på siden er forsøgt skrevet. Inde i
løkken bruges den gamle.

## Rettelsen

`For … To` er skiftet ud med en `Do`-løkke, så grænsen læses forfra i hvert
gennemløb, og der skrives **én** karakteristik ad gangen efterfulgt af en
fuld genopbygning af metadata. Containeren hentes forfra efter hver popup.
En tæller stopper efter 50 gennemløb, så en side, der aldrig ændrer sig, ikke
kan låse scriptet fast.

## Hvad der ikke var fejlen

`IsSpecialCharacteristic` sammenligner med `=` og ikke
`StrComp(..., vbTextCompare)`, og modulet har ikke `Option Compare Text` —
så den er versalfølsom, mens resten af modulet ikke er.

Jeg troede først, det var årsagen. **Det var det ikke:** jeg gennemgik alle
35 ark, og felterne staves ens overalt (`Remarks`, `Supply from`,
`Safety Critical Equipment`). Den er rettet alligevel i patchen, så en
fremtidig stavevariant ikke stille og roligt sender værdien ned ad den
forkerte vej — men den forklarer ikke det, I ser i dag.

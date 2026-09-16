# Feltforklaringer i VH-plan appen — oplæg

Bygget på **"Den gode VH-plan"** (49 slides, maj 2025) og **"Planlægning af
en VH ordre"** (49 slides, 2026), sammenholdt med reglerne i
`BIO_SAP_Fields.xlsx`.

## Princippet

Vejledningen findes allerede — men i to PowerPoints, som ingen har åbne,
mens de udfylder formularen. Forklaringen skal stå **dér hvor feltet
udfyldes**, ikke i et dokument ved siden af.

Tre niveauer, så teksten ikke drukner sig selv:

| Niveau | Hvor | Hvor meget |
|---|---|---|
| **1. Feltforklaring** | Bag et lille **ⓘ** ved feltets label | Én linje. Hvad feltet er, eller den regel der gælder lige nu |
| **2. Hjælpepanel** | Foldes ud pr. sektion med et **?** | 3–8 linjer. Hvorfor feltet betyder noget, og hvad der går galt |
| **3. Kilde** | Link nederst i panelet | Til SAP-portalen / præsentationen |

Niveau 1 bruger `field_cell(hint_text=...)`, som builderne allerede
understøtter. Teksten stod først som en fast linje **under** feltet — med 22
felter fyldte hjælpeteksten mere end formularen, og skærmen så rodet ud. Den
er nu skjult bag et lille **ⓘ** ved labelen og folder sig ud for netop det
felt, man trykker på. `varVhpTip` holder hvilket felt der er åbent, så der
aldrig står mere end én forklaring ad gangen.

**Hvorfor ikke en rigtig hover-tooltip?** Det var det første forsøg, og det
fejlede i compile 21 gange: appen er bygget udelukkende af moderne
kontroller, og `Tooltip` findes kun på de *interaktive* af dem — en
`ModernText` er en label og kender ikke egenskaben. Klik-varianten har til
gengæld en fordel, hover ikke har: den virker på touch. Tjek 10 i
`check_layout.py` fanger fejlen, hvis nogen prøver igen.

Niveau 2 er ét nyt mønster: en `?`-knap i sektionsoverskriften, der slår
`varVhpHelp<Sektion>` til og fra.

**Sproget er engelsk**, som resten af appens brugerflade. Kommentarerne i
byggekoden er stadig danske.

**Hint-teksten skal være dynamisk, hvor reglen er det.** En statisk tekst,
der siger "udfyldes kun ved lovpligtige eftersyn", er værd mindre end en, der
siger *"Påkrævet: item 2 har activity type 110"*.

---

## Plan Header

| Felt | Hint (niveau 1) |
|---|---|
| **Plan Type** | `Strategiplan henter cyklus fra strategiens pakker.` *(findes)* |
| **Maintenance Strategy** | `Pakkerne vises i Strategy Packages nedenfor.` *(findes)* |
| **Plant** | `Værket bestemmer hvilke arbejdscentre og arbejdsplaner der kan vælges.` |
| **Status** | `Ny, Ændre eller Slettes — hvad indmeldingen skal gøre ved planen i SAP.` |
| **Plan Text** | `Start med værkets bogstavkode. Teksten skal dække alle opgaver planen kalder. Maks. 40 tegn.` |
| **Sort Field** | Dynamisk: `Påkrævet, fordi item «X» har activity type 110/115.` ellers `Bruges kun til lovpligtige eftersyn.` |
| **Cycle / Unit** | `Hvor ofte planen kalder en ordre. DAY, WK, MON, YR — eller H for timetæller.` |
| **Call Horizon** | Dynamisk: `55 FCD for 1 år — sat automatisk ud fra cyklus.` |
| **Scheduling Indicator** | `Time – key date kalder på samme dato hvert år. Vælg den, hvis planen kalder primo januar.` |
| **First Call** | Dynamisk: `Låst til 01/01, fordi et item har revisionsmærke REV.` |

### Hjælpepanel — Plan Header

> **Overskriften**
> Starter altid med lokationens bogstavkode (AVV, SKV, SSV …), så planen kan
> findes, når man ikke kan søge på værk eller funktionsplads.
>
> **Call horizon** er det antal arbejdsdage, den genererede VH-ordre står på
> joblisten, før basic finish-datoen nås. Den sættes ud fra cyklussen —
> tallene kommer fra `CallHorizonMatrix`.
>
> **Scheduling period** er hvor langt frem kaldene kan ses. Minimum **2 år**
> af hensyn til den økonomiske simulering i BI-rapporten.
>
> **Time – key date** vælges, hvis planen kalder primo januar. Ellers kan
> kaldet flytte til året før, og omkostningen vises forkert i BI.
>
> **Sort field** bruges kun ved lovpligtige eftersyn (activity type 110/115).
> Er der valgt `Ladders`, skal **alle** items i planen være lovpligtigt
> eftersyn af stiger.
>
> **Revisionsopgaver** mærkes REV, kaldes 1/1 og har call horizon 55 FCD.

---

## Item Editor

| Felt | Hint (niveau 1) |
|---|---|
| **Item Short Text** | `Bliver VH-ordrens overskrift. Skriv hvad opgaven er — ikke hvad planen hedder. Maks. 40 tegn.` |
| **Functional Location** | `Angiv så detaljeret som muligt — helst KKS-komponentniveau. Her konteres omkostningen.` |
| **Object List** | `Skal starte med samme 2-bogstavsniveau som referenceobjektet. Som udgangspunkt ét objekt pr. item.` |
| **Maintenance Activity Type** | Dynamisk: `110 kræver henvisning til gældende lovgivning i langteksten.` |
| **Main Work Center** | `Bruges der eksterne leverandører, vælg *SUP.` |
| **Revision** | `REV betyder at opgaven løses i revisionsperioden. Første kald låses til 01/01.` |
| **Item Long Text** | `Beskriv omfanget, og hvad der skal til for at udføre opgaven sikkert. Det er det første udføreren ser.` |

### Hjælpepanel — Item

> **Langteksten** er det første vedligeholdelsespersonalet ser i den
> genererede ordre. Beskriv omfanget, og hvad der skal sikres — arbejdsmiljø
> og miljø. Er der krav om rengøring, lugemand, kran, stillads eller
> afspærring, så skriv det kort.
>
> **Referenceobjektet** er dér omkostningen konteres. Angiv funktionspladsen
> på KKS-komponentniveau. Er der objekter på objektlisten, kan den være
> mindre detaljeret — men mindst 2-bogstavsniveau, fx `SKV40 EB`.
>
> **Objektlisten**: cost center og business area skal være ens for alle
> funktionspladser på listen. Gælder dog ikke sikkerhedsventiler og
> rørstrenge. Ved lovpligtig besigtigelse af trykbærende udstyr: **én**
> funktionsplads pr. item, objektlisten tom.
>
> **Aktivitetstyper**
> `101` forebyggende · `102` forudbestemt · `110` lovpligtigt eftersyn ·
> `115` myndighedsvilkår · `120` løbende, maks. 1 år · `130` rengøring ·
> `160` smøring.
> Bruges 110 eller 115, **skal** der henvises til gældende lovgivning.
>
> **Prioritet** følger aktivitetsmatricen og sættes automatisk:
> rød ved 110/115 eller SCEq, blå ved 120, ellers gul.

---

## Tasklist og operationer

| Felt | Hint (niveau 1) |
|---|---|
| **Operation Short Text** | `Hvad operationen skal bruges til. Årsordrer starter med "ÅO".` |
| **Control Key** | Dynamisk pr. arbejdscenter: `*SUP → ZB01 · interne → PM01 · *LEV → PM02 · rammeaftale → PM03` |
| **Work** | `Samlet antal mandetimer for operationen.` |
| **No.** | `Antal personer. 1 er standard.` |
| **Duration** | `Varigheden. Udregnes af SAP.` |
| **Vendor** | Dynamisk: `PM03 kræver leverandørens vendor-nummer — det kommer ikke automatisk.` |
| **Long Text** | `Hvad der forventes udført. Ved ekstern leverandør overføres teksten til rekvisitionen.` |

### Hjælpepanel — Operationer

> **Del opgaven op, hvor der er ophold.** Stillads op og stillads ned er to
> operationer. Af-isolering og isolering er to. Ellers kan WOE-appen ikke
> vise forløbet rigtigt.
>
> **Operationerne skal stå i kronologisk rækkefølge** — 0010, 0020, 0030 —
> så det grafiske view i WOS afspejler arbejdet.
>
> **Alle operationer skal time- og bemandingsestimeres.**
>
> **Control keys**
> `ZB01` internt *SUP, tæller ikke med i schedulering ·
> `PM01` interne work centre ·
> `PM02` ekstern *LEV, der laves rekvisition ·
> `PM03` rammeaftaleleverandør på servicekatalog.
> Det hovedansvarlige arbejdscenter skal stå på **operation 0010**.
>
> **Materialegruppe 999 må ikke bruges til indkøb.** Den står som standard
> på standardarbejdsplanerne, fordi feltet er påkrævet — men den skal
> skiftes, før operationen frigives.
>
> Ved PM02/PM03: enheden er **AU**, mængde **1**, per **1**.

---

## Det appen kan tjekke automatisk

Disse regler står i `BIO_SAP_Fields.xlsx` og i "Den gode VH-plan". Flere af
dem er allerede i appen; resten bør ind i valideringen frem for kun at stå
som hjælpetekst:

| Regel | Status |
|---|---|
| Plan Text starter med værkets bogstavkode | **R1 — bygget** |
| Plan Text maks. 40 tegn | findes |
| Sort Field påkrævet, hvis et item har activity type 110/115 | **R2 — bygget** |
| ~~Activity type 110/115 ⇒ Main Work Center = `*SUP`~~ | **trukket tilbage — påstanden er forkert** |
| First Call låst til 01/01, hvis et item har `Revision = REV` | **R4 — bygget** |
| Scheduling period mindst 2 år | **R5 — bygget** |
| Call Horizon + Scheduling Period sat ud fra cyklus | findes |
| Order Type = ZPRE | findes |
| Operation 0010 bærer det hovedansvarlige arbejdscenter | hint (`Operations`), ikke blokerende |
| Objektliste-koder starter med samme 2-bogstavsniveau som FL | hint (`ObjectList`); håndhæves reelt af filteret på objektlisten |
| Prioritet sat af aktivitetstype og SCEq | **afventer** — kræver SCEq-feltet fra FL-flowet |
| Materialegruppe ≠ 999 på operationer med PM02/PM03 | **afventer** — materialegruppe findes ikke i datamodellen endnu |

R1, R2, R4 og R5 ligger i `build_hero.py` og skriver ind i den samme
fejltabel som den øvrige validering, så de vises i hero-panelet og blokerer
indsendelse på linje med de eksisterende regler.

**R3 er trukket tilbage.** Jeg læste "lovpligtigt eftersyn sendes altid til
`*SUP`" ud af materialet og byggede den som en blokerende regel. Peter har
bekræftet, at det ikke passer. En regel, der blokerer folk på noget, der
ikke er en regel, er værre end ingen validering — den lærer dem at ignorere
panelet. Nummereringen står urørt, så fejlen kan genkendes her og i
`TEST-manuelt.md`.

---

## Hvad der er bygget

| Del | Hvor | Status |
|---|---|---|
| 22 hints (niveau 1) | `build_help.py` → `HINTS` | bygget |
| 4 hjælpepaneler, 19 afsnit (niveau 2) | `build_help.py` → `PANELS` | bygget |
| `?`-knap i sektionsoverskriften | `build_plan_header.section_header(help_section=...)` | bygget |
| Panel-rendering | `build_plan_header.help_panel(name, section)` | bygget |
| `varVhpHelpPlan/Item/Ops/Pkg` | `generate_app_onstart.py` | bygget |
| R1–R5 | `build_hero.py` | bygget |

Panelerne sidder på **Plan Header**, **Item Editor**, **Tasklist and
Operations** og **Strategy Packages**.

**Dynamiske hints.** 8 af de 22 er Power Fx-udtryk og ikke faste strenge:
`Strategy`, `PlanText`, `SortField`, `CallHorizon`, `FirstCall`,
`ActivityType`, `MainWorkCenter` og `Operations`. De fortæller hvorfor
reglen gælder lige nu — fx *"Påkrævet: 2 item(s) har activity type 110/115"*
frem for *"udfyldes ved lovpligtige eftersyn"*.

Operationerne redigeres i et galleri og har derfor ingen `field_cell` at
hænge en hint på. `Operations`-hinten står i stedet over tabellen og peger
på den regel der er brudt lige nu (manglende arbejdscenter på første
operation, manglende short text, Work = 0) og falder ellers tilbage på
control key-reglen.

---

## Hvad der mangler

1. **Prioritetsreglen** (rød ved 110/115 eller SCEq, blå ved 120, ellers gul).
   I dag skriver appen altid `Yellow (default)`. SCEq kommer fra
   FL-indmeldingen, så reglen kan først laves helt, når SPOOL-appen er på
   plads. Aktivitetstype-delen kunne laves nu — men en halv regel, der
   sætter rød uden at kunne sætte blå, er værre end ingen.

   *Opdatering:* `Safety Critical Equipment` er nu fundet i SPOOL-arket, med
   en værdiliste pr. klasse — se [`16-spool-regler.md`](16-spool-regler.md).
   Feltet findes altså, og reglen kan laves færdig, så snart FL-appen
   skriver det til SharePoint.
2. **Materialegruppe ≠ 999.** `colVhpOperations` har ingen materialegruppe.
   Kræver et felt på operationslinjen og en kolonne i `TaskListMain`.
3. **Control key pr. operation.** Samme sag: feltet findes ikke i
   datamodellen. Reglen står indtil videre kun i ops-panelet og i hinten.

Punkt 2 og 3 er den samme udvidelse af operationslinjen og bør laves samlet.

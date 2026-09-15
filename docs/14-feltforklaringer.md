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
| **1. Hint** | Altid synlig under feltet | Én linje. Hvad feltet er, eller den regel der gælder lige nu |
| **2. Hjælpepanel** | Foldes ud pr. sektion med et **?** | 3–8 linjer. Hvorfor feltet betyder noget, og hvad der går galt |
| **3. Kilde** | Link nederst i panelet | Til SAP-portalen / præsentationen |

Niveau 1 bruger `field_cell(hint_text=...)`, som builderne allerede
understøtter — Plan Type og Maintenance Strategy har det i dag. Niveau 2 er
ét nyt mønster: en `?`-knap i sektionsoverskriften, der slår
`varVhpHelp<Sektion>` til og fra.

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
| **Maintenance Activity Type** | Dynamisk: `110 kræver henvisning til gældende lovgivning, og sendes altid til *SUP.` |
| **Main Work Center** | Dynamisk: `Lovpligtigt eftersyn — skal være *SUP.` ellers `Bruges der eksterne leverandører, vælg *SUP.` |
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
| Plan Text starter med værkets bogstavkode | **ny** |
| Plan Text maks. 40 tegn | findes |
| Sort Field påkrævet, hvis et item har activity type 110/115 | **ny** |
| First Call låst til 01/01, hvis et item har `Revision = REV` | **ny** |
| Call Horizon + Scheduling Period sat ud fra cyklus | findes |
| Scheduling period mindst 2 år | **ny** |
| Prioritet sat af aktivitetstype og SCEq | **ny** — kræver SCEq-feltet fra FL-flowet |
| Activity type 110/115 ⇒ Main Work Center = `*SUP` | **ny** |
| Objektliste-koder starter med samme 2-bogstavsniveau som FL | **ny** |
| Operation 0010 bærer det hovedansvarlige arbejdscenter | **ny** |
| Materialegruppe ≠ 999 på operationer med PM02/PM03 | **ny** |
| Order Type = ZPRE | findes |

De fem første er billige og rammer det, folk oftest glemmer. Jeg foreslår at
tage dem først.

---

## Hvad jeg foreslår vi gør

1. **Hints på alle felter i tabellerne ovenfor.** Bruger `hint_text`, som
   allerede findes. Ingen nye konstruktioner.
2. **Ét hjælpepanel pr. sektion**, slået til med et `?` i overskriften.
3. **De fem billige valideringsregler** ind i `Validate`.
4. Resten af reglerne, når SCEq er tilgængelig fra FL-flowet.

Punkt 1 og 2 er ren tekst og layout — de kan laves uden at røre datamodellen.
Punkt 3 rører kun valideringen.

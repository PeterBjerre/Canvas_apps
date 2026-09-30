# Manuel test af VH-plan appen

Køres i browseren efter synk. Ingen Copilot-tokens bruges.

Der er **fem ting** at se efter. Tag dem i rækkefølge — de bygger på hinanden.

---

## 1. Layoutet (30 sekunder)

| Hvor | Hvad du skal se |
|---|---|
| **Item Editor** | Tre kolonner i **kolonne-orden**: Item Short Text, Main Work Center, Activity Type · Revision, Initials, Item Long Text · Functional Location med **Object List**-knappen lige under |
| **Plan Header** | Kolonne-orden: Plan Type, Maintenance Strategy og Plant under hinanden i kolonne 1. **First Call** dag, måned og år på **én række** nederst i kolonne 4 |

Træk vinduet ned til ca. 900 px bredde. Intet må blive klippet.

---

## 2. Functional Location (2 minutter)

Feltet er **én combobox** med en **Search**-knap (issue #63) — den samme
som i Equipments og Materials (`tools/fl_picker.py`). Der er intet separat
søgefelt og ingen separat dropdown.

1. Vælg et item. Skriv under 7 tegn i comboboksen.
   → **Search** er deaktiveret, og der står ingen søgerække i listen.
2. Skriv `SSV13 HFC10` og klik **Search**.
   → Knappen bliver til en boks af samme størrelse med én spinner, indtil
     svaret er der. Intet i rækken flytter sig.
   → Comboboksen viser resultaterne.
3. Skriv videre (fx `SSV13 HFC10AA`).
   → Listen snævres ind **uden** et nyt kald (ingen spinner).
4. Skriv en ny søgning (fx `SSV13 KAB10`) og tryk **Enter**.
   → Den øverste række, *"SSV13 KAB10 - press Enter to search SAP"*, er
     valgt, og søgningen kører — som et klik på Search. De gamle resultater
     og det gamle valg er væk.
5. Vælg én Functional Location. Ikke-vedligeholdbare står med
   *(not maintainable)* bag teksten.
6. Søg på noget, der ikke findes → en kort advarsel (*No functional
   locations found*). Fejler flowet → en kort fejlnotifikation.

**Object List** — multi-select med afkrydsning. Der står **ingen** tekst
under knappen længere (issue #63): knappen viser antallet — *Object List
(3)* — og de valgte ses, når musen holdes over den. Uden data er den
deaktiveret.

7. **Uden** en FL valgt og uden valgte objekter: *Object List (0)* er
   deaktiveret. Den må **ikke** vise hele søgeresultatet.
8. Med en FL valgt: popup'en viser de underliggende objekter, ét pr. linje
   med et afkrydsningsfelt. *Use selected* → knappen tæller op, fx
   *Object List (2)*, og hover viser `Kode - beskrivelse` pr. linje.
9. Skift til et **andet item** og tilbage igen.
   → Krydserne skal stå som du efterlod dem. Hvert item har sin egen liste.
10. Med objekter valgt: vælg en **anden** Functional Location. Hover-teksten
    advarer om, at nogle af dem ikke ligger under den nye FL. De ryddes
    **ikke** i stilhed.

## 3. Strategidelen (1 minut)

1. Skift **Plan Type** til `Strategiplan (IP42)`.
2. Åbn **Maintenance Strategy**. Der skal stå **53** strategier, og **52** af
   dem skal være mærket `(pakker mangler)`.
3. Vælg **101** (mærket). Pakkematricen skal være **væk**, og knapperne
   *Hierarki-udfyld* / *Alle pakker* / *Ryd pakker* skal være **skjulte** —
   ikke bare grå. I stedet står forklaringen om at strategien ikke har pakker.
4. Vælg **128**. Nu tegnes matricen med tre kolonner: `1Y`, `2Y`, `3Y`.
5. *Hierarki-udfyld* skal være **grå**, og under den skal stå en linje om at
   det ikke er afklaret, om strategien er hierarkisk. **Klik på den med
   musen** — der må ikke ske noget.
6. *Alle pakker* skal virke og sætte kryds i alle tre.

---

## 4. Gemningen — det nye (5 minutter)

**Før du begynder:** noter det sidste `PlanID` i `MaintenancePlans`, fx
`MP0068`. Det skal du bruge i trin 3 nedenfor.

Byg en lille plan:

1. Værk `SSV`, Plan Type `Single cycle`, udfyld Plan Text, Cycle, Unit,
   Call Horizon og First Call.
2. Tilføj **ét** item: FL, Item Short Text, Main Work Center.
3. Tilføj tasklist-operationer til item'et.
4. Klik **Gem kladde** nederst (Step 6).

Der skal komme en grøn besked med et `MP`-nummer.

### Tjek i SharePoint

| Liste | Hvad der skal stå |
|---|---|
| `MaintenancePlans` | Ny række. `PlanID` = **næste nummer i serien** (havde du `MP0068`, skal den nye være `MP0069`). `Status` = `Draft`. `PlantsInitial` = SSV. `CallHorizon` = et **tal**. `StrategyKey` tom |
| `MaintenanceItems` | Én række. `MaintenancePlanNo` peger på planen. `ItemID` fortsætter `MI`-serien. `OrstedResponsibleEmail` = din mail i småt. `Priority` = `Yellow (default)` |
| `TaskListMain` | Én række pr. operation. `OperationNo` = 10, 20, 30 … `TaskID` skal være **tom** |
| `MD_RequestIndex` | **Én** ny række. `RequestNo` = `MP`-nummeret, `Domain` = `MaintenancePlan`, `Status` = `Kladde`, `StatusStep` = 1, `IsOpen` = ja, `ItemCount` = 1 |

> **Er `PlanID` ikke det næste i serien**, så stop og sig til. Så er offsettet
> udledt forkert, og det skal rettes før der gemmes mere.

### Gem igen

5. Klik **Gem kladde** igen uden at ændre noget.
   → Der må **ikke** komme en ny plan eller en ny indeksrække. De
   eksisterende opdateres, og antallet af items og operationer er uændret.
6. Tilføj et item mere og gem igen.
   → Nu to items, og `ItemCount` i indeksrækken følger med.
7. Klik **Indsend**.
   → `MaintenancePlans.Status` bliver `In Progress`, og indeksrækken
   `Indsendt` / trin 2.

---

## 5. Landingssiden (30 sekunder)

Åbn **Masterdata Hub**. Indmeldingen skal stå under "Mine indmeldinger" med
rigtigt nummer, tekst, værk og status.

Klik **Åbn** på rækken → VH-plan appen åbnes i en ny fane.

---

## 6. Feltforklaringer og de nye regler (3 minutter)

### Hjælpepanelerne

Der skal være en **? Help**-knap i overskriften på fire sektioner: Plan
Header, Item Editor, Tasklist and Operations, Strategy Packages.

1. Klik **? Help** på Plan Header.
   → Et lyseblåt panel folder sig ud under overskriften. Knappen skifter til
   **Hide help** og bliver blå. Nederst i panelet står kilden.
2. Klik igen → panelet forsvinder, knappen bliver grå igen.
3. Gentag på de tre andre sektioner. De fire paneler er uafhængige — alle
   fire kan være åbne samtidig.

### Feltforklaringerne

Tryk **Show field help** i hero-kortet, ved siden af `*  Required`.
→ Der kommer en forklaringslinje under **alle** felter på én gang, og
knappen bliver blå og skifter til **Hide field help**.

Tryk igen.
→ Alle linjerne forsvinder, og felterne rykker sammen igen. Ingen tomme
huller, hvor teksten stod.

Teksten skal **skifte**, når forudsætningen ændrer sig. Det er den vigtigste
del af testen — en forklaring, der står stille, er en statisk tekst, der er
sluppet forbi. Lad hjælpen være slået til, mens du går tabellen nedenfor
igennem.

| Gør dette | Forklaringen skal skifte til |
|---|---|
| Sæt Plan Type = `Strategy` | Strategy-forklaringen nævner pakkerne nedenfor |
| Skriv Plan Text uden værkskoden | PlanText-forklaringen siger, at teksten bør starte med værkskoden |
| Sæt et items Activity Type til `110` | Sort Field-forklaringen skifter til "Required: 1 item …" |
| Sæt Revision på et item | FirstCall-forklaringen siger 01/01 |
| Tilføj en operation uden Main Work Center | Linjen over operationstabellen nævner operation 0010 |
| Udfyld arbejdscentret, men lad short text stå tom | Samme linje skifter til "1 operation(er) mangler short text" |

### R1, R2, R4 og R5 i valideringen

Alle fire skal dukke op i fejlpanelet øverst og blokere **Indsend**.

1. **R1** — Plan Text der ikke starter med værkskoden.
2. **R2** — et item med activity type `110`, og Sort Field tomt på planen.
3. **R4** — et item med revisionsmærke, og First Call ≠ 01/01.
4. **R5** — Scheduling Period under 2 år.

> **R3 findes ikke.** Den blokerede på "activity type 110/115 skal have
> `*SUP`", og den påstand er forkert. Sæt gerne et 110-item til et
> arbejdscenter uden `SUP` og kontrollér, at der **ikke** kommer en fejl.

Ret hver fejl → beskeden skal forsvinde igen, og Indsend skal blive aktiv,
når den sidste er væk.

---

## Ryd op bagefter

Slet de rækker, testen oprettede, i alle fire lister — ellers ligger der en
testplan i systemet. Rækkefølgen: `TaskListMain`, `MaintenanceItems`,
`MaintenancePlans`, `MD_RequestIndex`.

---

## Hvis noget fejler

Noter **hvilket punkt**, hvad du gjorde, og hvad der stod — ordret hvis der
kom en fejlbesked. Det er nok til at finde fejlen i koden.

---

## Issue #54 — progressbar, Submit, Reset, Object List-popup

1. **Ny plan.** Progressbaren viser fem trin (Plan, Item, Task list,
   Operations, Save) og en **grå Submit**-knap. Ingen *Dispatch*. Ingen
   "Plan is open for editing"-linje, ingen Dispatch and Control, ingen Save to
   SharePoint-sektion.
2. **Kolonne-orden** i Plan Header og Item Editor. Tab går oppefra og ned.
3. **Required-teksten** står lige efter "Plan Header" og er hel. Stjernerne
   står lige efter labelteksten (`Plan Type *`).
4. Vælg **Plant = ASV**, Save. Items-kortet viser `Plant: ASV`; Main Work
   Center viser kun ASV-centre; søgefeltet under Functional Location starter
   med `ASV`; Tasklist-dropdownen viser kun ASV-lister.
5. Edit, skift Plant, Save. En advarsel siger, at vaerket er skiftet; et
   arbejdscenter/en tasklist fra det gamle vaerk står nu tomt. Intet item er slettet.
6. **Search**: knappen viser `.` `..` `...` og er grå under søgningen, også
   hvis søgningen fejler. Dropdownen viser bagefter `Select result (n)` —
   aldrig en tom linje — eller `No results found`.
7. **Object List**: knappen står under FL-dropdownen og åbner en centreret
   popup med sløret baggrund. Kryds et par objekter og tryk **Cancel** →
   intet ændret. Kryds igen og tryk **Use selected** → valget står under
   knappen.
8. **Item-kort**: klik hvor som helst på kortet → itemet åbnes (kanten bliver
   blå ved hover, og det aktive kort har en tyk kant). **Delete** på et kort
   sletter kortet uden at åbne det.
9. **Tasklist and Operations**: dropdownen til venstre; *Apply Tasklist · Add
   Lines from Tasklist · Add Manual Operation · Remove Selected Operation*
   samlet til højre i tekstbredde; tabellen i fuld bredde nedenunder. Træk
   vinduet smalt: knapgruppen flytter samlet ned under dropdownen.
   *Remove Selected Operation* er grå, til en linje er krydset af.
10. **Trin bliver grønne**: Save i Plan Header → trin 1 grønt. Gem et item →
    trin 2. Ret et felt i Item Editoren uden at gemme → trin 2 er ikke
    længere grønt. **Reset** → feltet er tilbage, trin 2 grønt igen.
11. Klik på et trin → sektionen, det hører til, får en tyk blå kant (Task list
    og Operations vælger også fanen). Siden scroller ikke selv - det kan canvas
    apps ikke, og SetFocus kan ikke nå ind i en container (issue #59).
12. Når trin 1–4 er grønne og reglerne (S1–S5, R1–R5) er opfyldt, bliver
    **Submit blå**. Hold musen over en grå Submit: tooltip siger hvad der mangler.
13. **Save draft** → trin 5 grønt. Ret noget → trin 5 ikke grønt længere.
14. Alt ovenfor i både lys og mørk tilstand. App checker: ingen fejl.

### Runde 2 (issue #54, opfølgning)

15. **Topbjælken**: "VH-plan" til venstre, progressbaren i midten, *Save
    draft* og *Submit* samlet til højre — med gem- og send-ikon.
16. **Sektionstitlerne** ("Plan Header", "Items", "Item Editor", "Tasklist and
    Operations") vises. Deploy med `--clean` — overskriftens kontroller er flyttet.
17. **Submit** i alle apps (VH-plan, Equipment, Material, Functional Location)
    åbner en bekræftelse. *Cancel* gør intet; *Submit* indsender.
18. **Gem** i alle apps: mens SharePoint svarer, dækker en drejende
    ventespinner skærmen (Save draft, Save, Save as draft, Submit).
19. **Revision** er en toggle (*Yes - outage work* / *No*). Tændt gemmes som
    `REV - General Revision Mark`, slukket som tom — som før.
20. **Item Long Text** er en knap med tekstens begyndelse; den åbner samme
    popup som operationernes lange tekst.
21. **Operationer**: hver linje har *Materials (n)* og *Docs (n)*. Materials
    viser kun linjens materialer; en ny linje får operationens nummer. Docs
    viser itemets dokumenter; *This operation* kobler til/fra, og en fil
    uploadet herfra kobles til operationen. Fanerne Materials og Attachments er væk.

